"""
capital_guardian/services/red_flag_engine.py — a transparent, deterministic
rule engine. Every rule is plain Python over real, already-stored data
(gold_intelligence.EquipmentSpec/CapitalBudgetLine/MineTimelineMilestone,
GoldProject, CapitalTraceEntry, OperationalSnapshot) — never an LLM call,
never a fabricated prediction. Decision Studio may EXPLAIN an already-
detected RedFlag row; nothing here ever asks an LLM whether a flag exists.

Idempotent: re-running detect_red_flags() get_or_creates by (project,
rule_key), so a still-true condition is never duplicated. A condition that
is no longer true has its OPEN row removed (never a human-acknowledged or
resolved row — those are left alone, matching the same "never auto-
overwrite a human decision" convention as agent_training_evaluation_lab's
regression detector).

--- Phase 2: configurable thresholds ---
`get_thresholds(project, rule_key)` resolves, in order: a project-scoped
RedFlagRuleConfig row → a platform-wide default row (project=None) → the
rule's hardcoded MODULE-level fallback constant below. This is the ONLY
change to how the original 4 rules decide severity — their logic is
unchanged, just re-pointed at configurable numbers instead of hardcoded
ones. 8 new rule categories are added, each following the exact same
pattern (real stored value vs. a real configured/fallback threshold).
"""
from django.utils import timezone

from capital_guardian.models import RedFlag, RedFlagRuleConfig

CAPEX_VARIANCE_WARNING_THRESHOLD_PCT = 2.0
CAPEX_VARIANCE_CRITICAL_THRESHOLD_PCT = 10.0
INSURANCE_RENEWAL_WARNING_DAYS = 60
INSURANCE_RENEWAL_CRITICAL_DAYS = 30
EQUIPMENT_AVAILABILITY_WARNING_PCT = 90.0
EQUIPMENT_AVAILABILITY_CRITICAL_PCT = 80.0
RECOVERY_RATE_SHORTFALL_WARNING_PCT = 3.0
RECOVERY_RATE_SHORTFALL_CRITICAL_PCT = 6.0
WATER_RECYCLED_WARNING_PCT = 70.0
WATER_RECYCLED_CRITICAL_PCT = 55.0

_FALLBACKS = {
    'capex_variance': (CAPEX_VARIANCE_WARNING_THRESHOLD_PCT, CAPEX_VARIANCE_CRITICAL_THRESHOLD_PCT),
    'insurance_renewal_due': (INSURANCE_RENEWAL_WARNING_DAYS, INSURANCE_RENEWAL_CRITICAL_DAYS),
    'equipment_availability': (EQUIPMENT_AVAILABILITY_WARNING_PCT, EQUIPMENT_AVAILABILITY_CRITICAL_PCT),
    'recovery_rate': (RECOVERY_RATE_SHORTFALL_WARNING_PCT, RECOVERY_RATE_SHORTFALL_CRITICAL_PCT),
    'water_recycled': (WATER_RECYCLED_WARNING_PCT, WATER_RECYCLED_CRITICAL_PCT),
}


def get_thresholds(project, rule_key):
    """(warning, critical) — always real numbers, resolved project override
    → platform default → hardcoded fallback. Returns (None, None) only for
    an unknown rule_key with no fallback registered."""
    config = (
        RedFlagRuleConfig.objects.filter(project=project, rule_key=rule_key).first()
        or RedFlagRuleConfig.objects.filter(project__isnull=True, rule_key=rule_key).first()
    )
    fallback_warning, fallback_critical = _FALLBACKS.get(rule_key, (None, None))
    if config is None:
        return fallback_warning, fallback_critical
    if not config.enabled:
        return None, None
    warning = config.warning_threshold if config.warning_threshold is not None else fallback_warning
    critical = config.critical_threshold if config.critical_threshold is not None else fallback_critical
    return warning, critical


def _equipment_fat_dependency_flags(project):
    """Category: Equipment Delivery Delay risk (a delivery blocked on a
    Factory Acceptance Test that hasn't passed yet)."""
    findings = []
    for equipment in project.equipment_specs.all():
        blocking = equipment.fat_status not in ('passed', 'not_applicable')
        delivery_pending = equipment.delivery_status in ('not_started', 'in_progress')
        if blocking and delivery_pending:
            findings.append({
                'rule_key': f'equipment_fat_dependency_{equipment.pk}',
                'severity': 'medium', 'category': 'schedule',
                'description': f'{equipment} delivery depends on Factory Acceptance Test (currently {equipment.get_fat_status_display()}).',
                'capital_exposure_usd': equipment.capex_usd,
                'recommended_action': 'Confirm Factory Acceptance Test schedule with supplier before delivery date is finalised.',
                'responsible_party': equipment.supplier or 'Project team',
                'related_equipment': equipment,
            })
    return findings


def _capex_variance_flags(project):
    lines = list(project.capital_budget_lines.exclude(planned_usd__isnull=True).exclude(committed_usd__isnull=True))
    if not lines:
        return []
    total_planned = sum(line.planned_usd for line in lines)
    total_committed = sum(line.committed_usd for line in lines)
    if not total_planned:
        return []
    variance_pct = round((total_committed - total_planned) / total_planned * 100, 1)
    warning, critical = get_thresholds(project, 'capex_variance')
    if warning is None or abs(variance_pct) < warning:
        return []
    severity = 'high' if critical is not None and abs(variance_pct) >= critical else 'medium'
    return [{
        'rule_key': 'capex_variance',
        'severity': severity, 'category': 'budget',
        'description': f'CAPEX variance {"+" if variance_pct >= 0 else ""}{variance_pct}% (committed vs. planned across {len(lines)} budget categor{"y" if len(lines) == 1 else "ies"}), exceeding the {warning}% warning threshold.',
        'actual_value': variance_pct, 'threshold_value': warning,
        'capital_exposure_usd': round(total_committed - total_planned, 2),
        'recommended_action': 'Review committed spend against the approved budget with the project finance lead.',
        'responsible_party': 'Project finance lead',
    }]


def _insurance_renewal_flags(project):
    if project.insurance_expiry_date is None:
        return []
    days_remaining = (project.insurance_expiry_date - timezone.now().date()).days
    warning, critical = get_thresholds(project, 'insurance_renewal_due')
    if warning is None or days_remaining > warning or days_remaining < 0:
        return []
    severity = 'high' if critical is not None and days_remaining <= critical else 'medium'
    return [{
        'rule_key': 'insurance_renewal_due',
        'severity': severity, 'category': 'insurance',
        'description': f'Insurance renewal due in {days_remaining} day{"s" if days_remaining != 1 else ""} (warning threshold: {warning} days).',
        'actual_value': days_remaining, 'threshold_value': warning,
        'capital_exposure_usd': project.insurance_coverage_usd,
        'recommended_action': 'Confirm renewal terms with insurer before the policy lapses.',
        'responsible_party': 'Project insurance adviser',
    }]


def _pending_investor_approval_flags(project):
    """Category: Payment Awaiting Approval."""
    findings = []
    for entry in project.capital_trace_entries.filter(investor_approval_status='pending'):
        findings.append({
            'rule_key': f'pending_investor_approval_{entry.pk}',
            'severity': 'medium', 'category': 'approval',
            'description': f'Supplier payment "{entry.purpose}" ({entry.trace_id}) pending investor approval.',
            'capital_exposure_usd': entry.amount_usd,
            'recommended_action': 'Route to investor board representative for sign-off.',
            'responsible_party': 'Investor board representative',
            'related_trace_entry': entry,
        })
    return findings


def _governance_approval_missing_flags(project):
    """Category: Governance Approval Missing — capital that has actually
    been PAID despite its own internal approval never having been granted.
    A real governance-control gap, not a duplicate of investor-approval
    (a distinct workflow: approval_status vs. investor_approval_status)."""
    findings = []
    for entry in project.capital_trace_entries.filter(payment_status='paid').exclude(approval_status='approved'):
        findings.append({
            'rule_key': f'governance_approval_missing_{entry.pk}',
            'severity': 'high', 'category': 'governance',
            'description': f'"{entry.purpose}" ({entry.trace_id}) was paid without internal approval on record (status: {entry.get_approval_status_display()}).',
            'capital_exposure_usd': entry.amount_usd,
            'recommended_action': 'Escalate to project governance for retrospective approval or investigation.',
            'responsible_party': 'Project governance committee',
            'related_trace_entry': entry,
        })
    return findings


def _evidence_missing_flags(project):
    """Category: Evidence Missing — capital that has actually been PAID
    with zero supporting EvidenceMemory documents linked."""
    findings = []
    for entry in project.capital_trace_entries.filter(payment_status='paid'):
        if not entry.evidence_documents.exists():
            findings.append({
                'rule_key': f'evidence_missing_{entry.pk}',
                'severity': 'medium', 'category': 'evidence',
                'description': f'"{entry.purpose}" ({entry.trace_id}) has been paid but has no evidence documents on record.',
                'capital_exposure_usd': entry.amount_usd,
                'recommended_action': 'Request and attach supporting documentation (invoice, delivery note, or inspection report).',
                'responsible_party': 'Project finance lead',
                'related_trace_entry': entry,
            })
    return findings


def _schedule_delay_flags(project):
    """Category: Schedule Delay — a milestone genuinely marked 'delayed'."""
    findings = []
    today = timezone.now().date()
    for milestone in project.timeline_milestones.filter(status='delayed'):
        overdue_days = (today - milestone.planned_end).days if milestone.planned_end else None
        severity = 'high' if overdue_days and overdue_days > 60 else 'medium' if overdue_days and overdue_days > 0 else 'low'
        findings.append({
            'rule_key': f'schedule_delay_{milestone.pk}',
            'severity': severity, 'category': 'schedule',
            'description': (
                f'{milestone.get_phase_display()} is marked delayed'
                + (f' ({overdue_days} day(s) past planned end).' if overdue_days is not None else '.')
            ),
            'actual_value': overdue_days, 'threshold_value': 0,
            'capital_exposure_usd': milestone.capital_required_usd,
            'recommended_action': 'Request an updated schedule and root-cause from the responsible party.',
            'responsible_party': milestone.responsible_party or 'Project team',
            'related_milestone': milestone,
        })
    return findings


def _fat_failure_flags(project):
    """Category: Factory Acceptance Test Failure — a real recorded failure,
    distinct from _equipment_fat_dependency_flags (which fires on a test
    merely not yet passed)."""
    findings = []
    for equipment in project.equipment_specs.filter(fat_status='failed'):
        findings.append({
            'rule_key': f'fat_failure_{equipment.pk}',
            'severity': 'high', 'category': 'equipment',
            'description': f'{equipment} failed its Factory Acceptance Test.',
            'capital_exposure_usd': equipment.capex_usd,
            'recommended_action': 'Obtain a remediation plan and re-test date from the manufacturer before further payment.',
            'responsible_party': equipment.supplier or 'Project team',
            'related_equipment': equipment,
        })
    return findings


def _equipment_availability_flags(project):
    """Category: Low Equipment Availability — latest real OperationalSnapshot only."""
    snapshot = project.operational_snapshots.order_by('-date').first()
    if snapshot is None or snapshot.equipment_availability_pct is None:
        return []
    warning, critical = get_thresholds(project, 'equipment_availability')
    if warning is None or snapshot.equipment_availability_pct >= warning:
        return []
    severity = 'high' if critical is not None and snapshot.equipment_availability_pct < critical else 'medium'
    return [{
        'rule_key': 'equipment_availability_low',
        'severity': severity, 'category': 'operational',
        'description': f'Equipment availability is {snapshot.equipment_availability_pct}% (below the {warning}% warning threshold), as of {snapshot.date}.',
        'actual_value': snapshot.equipment_availability_pct, 'threshold_value': warning,
        'recommended_action': 'Review maintenance backlog and equipment downtime causes with the operations team.',
        'responsible_party': 'Operations manager',
    }]


def _recovery_rate_flags(project):
    """Category: Recovery Rate Below Target — target is the project's own
    declared recovery_rate_pct assumption (gold_intelligence.GoldProject),
    never an invented benchmark. Silent when no real target is set."""
    if project.recovery_rate_pct is None:
        return []
    snapshot = project.operational_snapshots.order_by('-date').first()
    if snapshot is None or snapshot.recovery_rate_pct is None:
        return []
    warning, critical = get_thresholds(project, 'recovery_rate')
    if warning is None:
        return []
    shortfall = round(project.recovery_rate_pct - snapshot.recovery_rate_pct, 1)
    if shortfall < warning:
        return []
    severity = 'high' if critical is not None and shortfall >= critical else 'medium'
    return [{
        'rule_key': 'recovery_rate_below_target',
        'severity': severity, 'category': 'operational',
        'description': f'Recovery rate is {snapshot.recovery_rate_pct}%, {shortfall} points below the {project.recovery_rate_pct}% target, as of {snapshot.date}.',
        'actual_value': snapshot.recovery_rate_pct, 'threshold_value': round(project.recovery_rate_pct - warning, 1),
        'recommended_action': 'Review processing plant performance and metallurgical assumptions with the technical team.',
        'responsible_party': 'Process/metallurgy lead',
    }]


def _water_recycled_flags(project):
    """Category: Water Recycling Below Threshold."""
    snapshot = project.operational_snapshots.order_by('-date').first()
    if snapshot is None or snapshot.water_recycled_pct is None:
        return []
    warning, critical = get_thresholds(project, 'water_recycled')
    if warning is None or snapshot.water_recycled_pct >= warning:
        return []
    severity = 'high' if critical is not None and snapshot.water_recycled_pct < critical else 'medium'
    return [{
        'rule_key': 'water_recycled_low',
        'severity': severity, 'category': 'environmental',
        'description': f'Water recycling is {snapshot.water_recycled_pct}% (below the {warning}% threshold), as of {snapshot.date}.',
        'actual_value': snapshot.water_recycled_pct, 'threshold_value': warning,
        'recommended_action': 'Review water management plan with the environmental/ESG lead.',
        'responsible_party': 'Environmental lead',
    }]


def _milestone_payment_risk_flags(project):
    """Category: Milestone Payment Risk — capital already released against a
    milestone whose required independent verification has not happened."""
    findings = []
    at_risk = project.timeline_milestones.filter(verification_required=True).exclude(verification_status='verified')
    for milestone in at_risk:
        if not milestone.capital_released_usd:
            continue
        findings.append({
            'rule_key': f'milestone_payment_risk_{milestone.pk}',
            'severity': 'high', 'category': 'milestone',
            'description': (
                f'{milestone.get_phase_display()}: ${milestone.capital_released_usd:,.0f} released before required '
                f'verification is complete (status: {milestone.get_verification_status_display()}).'
            ),
            'capital_exposure_usd': milestone.capital_released_usd,
            'recommended_action': 'Withhold further releases until the Independent Technical Adviser verifies this milestone.',
            'responsible_party': milestone.responsible_party or 'Independent Technical Adviser',
            'related_milestone': milestone,
        })
    return findings


RULES = [
    _equipment_fat_dependency_flags,
    _capex_variance_flags,
    _insurance_renewal_flags,
    _pending_investor_approval_flags,
    _governance_approval_missing_flags,
    _evidence_missing_flags,
    _schedule_delay_flags,
    _fat_failure_flags,
    _equipment_availability_flags,
    _recovery_rate_flags,
    _water_recycled_flags,
    _milestone_payment_risk_flags,
]


def detect_red_flags(project):
    """Runs every rule, upserts RedFlag rows, and removes OPEN rows whose
    condition is no longer true. Returns the list of currently-open
    RedFlag rows for this project (freshly re-detected)."""
    findings = []
    for rule in RULES:
        findings.extend(rule(project))

    current_rule_keys = set()
    results = []
    for finding in findings:
        rule_key = finding.pop('rule_key')
        current_rule_keys.add(rule_key)
        existing = RedFlag.objects.filter(project=project, rule_key=rule_key).first()
        if existing is not None and existing.resolution_status != 'open':
            # A human already acknowledged/resolved this condition — never
            # silently reopen it just because the same condition re-fires.
            results.append(existing)
            continue
        flag, _created = RedFlag.objects.update_or_create(project=project, rule_key=rule_key, defaults=finding)
        results.append(flag)

    # A condition that's no longer true: remove the OPEN row (never touch a
    # human-acknowledged/resolved row for a condition that's since changed).
    RedFlag.objects.filter(project=project, resolution_status='open').exclude(rule_key__in=current_rule_keys).delete()

    return results
