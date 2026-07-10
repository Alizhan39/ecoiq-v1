"""
capital_guardian/services/red_flag_engine.py — a transparent, deterministic
rule engine. Every rule is plain Python over real, already-stored data
(gold_intelligence.EquipmentSpec/CapitalBudgetLine, GoldProject,
CapitalTraceEntry) — never an LLM call, never a fabricated prediction.

Idempotent: re-running detect_red_flags() get_or_creates by (project,
rule_key), so a still-true condition is never duplicated. A condition that
is no longer true has its OPEN row removed (never a human-acknowledged or
resolved row — those are left alone, matching the same "never auto-
overwrite a human decision" convention as agent_training_evaluation_lab's
regression detector).
"""
from django.utils import timezone

from capital_guardian.models import RedFlag

CAPEX_VARIANCE_WARNING_THRESHOLD_PCT = 2.0
INSURANCE_RENEWAL_WARNING_DAYS = 60


def _equipment_fat_dependency_flags(project):
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
    if abs(variance_pct) < CAPEX_VARIANCE_WARNING_THRESHOLD_PCT:
        return []
    severity = 'high' if abs(variance_pct) >= 10 else 'medium' if abs(variance_pct) >= 5 else 'low'
    return [{
        'rule_key': 'capex_variance',
        'severity': severity, 'category': 'budget',
        'description': f'CAPEX variance {"+" if variance_pct >= 0 else ""}{variance_pct}% (committed vs. planned across {len(lines)} budget categor{"y" if len(lines) == 1 else "ies"}).',
        'capital_exposure_usd': round(total_committed - total_planned, 2),
        'recommended_action': 'Review committed spend against the approved budget with the project finance lead.',
        'responsible_party': 'Project finance lead',
    }]


def _insurance_renewal_flags(project):
    if project.insurance_expiry_date is None:
        return []
    days_remaining = (project.insurance_expiry_date - timezone.now().date()).days
    if days_remaining > INSURANCE_RENEWAL_WARNING_DAYS or days_remaining < 0:
        return []
    severity = 'high' if days_remaining <= 14 else 'medium' if days_remaining <= 30 else 'low'
    return [{
        'rule_key': 'insurance_renewal_due',
        'severity': severity, 'category': 'insurance',
        'description': f'Insurance renewal due in {days_remaining} day{"s" if days_remaining != 1 else ""}.',
        'capital_exposure_usd': project.insurance_coverage_usd,
        'recommended_action': 'Confirm renewal terms with insurer before the policy lapses.',
        'responsible_party': 'Project insurance adviser',
    }]


def _pending_investor_approval_flags(project):
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


RULES = [
    _equipment_fat_dependency_flags,
    _capex_variance_flags,
    _insurance_renewal_flags,
    _pending_investor_approval_flags,
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
