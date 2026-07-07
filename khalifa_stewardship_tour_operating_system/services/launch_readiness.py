"""
khalifa_stewardship_tour_operating_system/services/launch_readiness.py — the
auditable launch checklist and the computed, non-subjective answer to
"is this tour ready to launch?" Nothing here is an AI opinion — every
function reads real persisted model state and returns a deterministic result.
"""
from django.utils import timezone

from khalifa_stewardship_tour_operating_system.models import LaunchChecklistItem, SupplierQuote

# (checklist_category, item_key, label) — matches the spec's 7 categories (A-G) exactly.
CHECKLIST_DEFINITION = [
    ('beneficiary', 'real_household_identified', 'Real household identified'),
    ('beneficiary', 'intervention_consent', 'Intervention consent'),
    ('beneficiary', 'privacy_status_confirmed', 'Privacy status confirmed'),
    ('beneficiary', 'safeguarding_review_complete', 'Safeguarding review complete'),

    ('technical', 'technical_inspection_complete', 'Technical inspection complete'),
    ('technical', 'named_professional_verified', 'Named professional verified'),
    ('technical', 'real_supplier_quote_received', 'Real supplier quote received'),
    ('technical', 'quote_exclusions_reviewed', 'Quote exclusions reviewed'),
    ('technical', 'technical_scope_approved', 'Technical scope approved'),

    ('partner', 'local_partner_identified', 'Local partner identified'),
    ('partner', 'due_diligence_complete', 'Due diligence complete'),
    ('partner', 'contact_verified', 'Contact verified'),
    ('partner', 'role_agreed', 'Role agreed'),

    ('finance', 'line_item_budget_complete', 'Line-item budget complete'),
    ('finance', 'participant_contribution_confirmed', 'Participant contribution confirmed'),
    ('finance', 'sponsor_contribution_confirmed', 'Sponsor contribution confirmed'),
    ('finance', 'funding_gap_resolved_or_accepted', 'Funding gap resolved or explicitly accepted'),

    ('participant_safety', 'allowed_actions_defined', 'Allowed actions defined'),
    ('participant_safety', 'blocked_actions_defined', 'Blocked actions defined'),
    ('participant_safety', 'supervision_assigned', 'Supervision assigned'),
    ('participant_safety', 'emergency_escalation_defined', 'Emergency escalation defined'),
    ('participant_safety', 'waiver_process_complete', 'Waiver process complete'),

    ('mrv', 'baseline_collected', 'Baseline collected'),
    ('mrv', 'methodology_defined', 'Methodology defined'),
    ('mrv', 'after_data_plan_defined', 'After-data plan defined'),
    ('mrv', 'evidence_requirements_clear', 'Evidence requirements clear'),

    ('governance', 'human_approval_complete', 'Human approval complete'),
    ('governance', 'public_claim_restrictions_clear', 'Public claim restrictions clear'),
    ('governance', 'media_permissions_clear', 'Media permissions clear'),
    ('governance', 'technical_work_gate_resolved', 'Technical-work gate resolved'),
]


class LaunchNotReadyError(Exception):
    """Raised by mark_tour_ready_to_launch() when a blocking item remains incomplete."""


def ensure_launch_checklist(tour):
    """Idempotent: creates any missing checklist rows for `tour`, defaulting to status='missing'. Never overwrites an existing row's status."""
    items = []
    for category, item_key, label in CHECKLIST_DEFINITION:
        item, _ = LaunchChecklistItem.objects.get_or_create(
            tour=tour, item_key=item_key, defaults={'checklist_category': category, 'label': label},
        )
        items.append(item)
    return items


def update_checklist_item(tour, item_key, **fields):
    item = LaunchChecklistItem.objects.get(tour=tour, item_key=item_key)
    for field, value in fields.items():
        setattr(item, field, value)
    item.save()
    return item


def is_technical_work_authorized(tour):
    """
    True only if ALL of: a named, verified professional exists; technical
    inspection evidence exists; a supplier/installer scope has been
    selected (an APPROVED SupplierQuote — never just "a quote exists");
    the intervention's technical scope is approved; and a human has
    actually signed off. Participants must never be authorized for
    electrical/heating/plumbing/structural/unsupervised hazardous work —
    that boundary is enforced separately by TourParticipantRole.blocked_actions.
    """
    reasons = []

    def _item_complete(item_key):
        item = LaunchChecklistItem.objects.filter(tour=tour, item_key=item_key).first()
        return item is not None and item.status == 'complete'

    if not _item_complete('named_professional_verified'):
        reasons.append('No named, verified professional is on record.')
    if not _item_complete('technical_inspection_complete'):
        reasons.append('Technical inspection has not been completed.')
    if not SupplierQuote.objects.filter(intervention__problem__tour=tour, approval_status='approved').exists():
        reasons.append('No supplier quote has been approved (a quote existing is not the same as one being selected).')
    if not _item_complete('technical_scope_approved'):
        reasons.append('Technical scope has not been approved.')
    if tour.human_approved is not True:
        reasons.append('Human approval for technical work has not been recorded.')

    return (len(reasons) == 0, reasons)


def calculate_mrv_baseline_readiness(tour):
    """Reads real TourMRVPlan/ConsentRecord/StewardshipTour state — never the mere existence of the 'required' intent flags."""
    mrv_plan = getattr(tour, 'mrv_plan', None)
    reasons = []

    methodology_defined = bool(mrv_plan and mrv_plan.methodology.strip())
    if not methodology_defined:
        reasons.append('MRV methodology has not been defined.')

    evidence_requirements_defined = bool(mrv_plan and mrv_plan.evidence_required)
    if not evidence_requirements_defined:
        reasons.append('MRV evidence requirements have not been listed.')

    intervention_date_set = tour.start_date is not None
    if not intervention_date_set:
        reasons.append('Intervention date has not been set.')

    baseline_data_collected = bool(mrv_plan and mrv_plan.verification_status != 'not_started')
    if not baseline_data_collected:
        reasons.append('Baseline data has not actually been collected yet (verification_status is still not_started).')

    photography_consent_granted = tour.consent_records.filter(consent_type='photography', status='granted').exists()

    return {
        'methodology_defined': methodology_defined,
        'evidence_requirements_defined': evidence_requirements_defined,
        'intervention_date_set': intervention_date_set,
        'baseline_data_collected': baseline_data_collected,
        'photography_consent_granted': photography_consent_granted,
        'ready': methodology_defined and evidence_requirements_defined and baseline_data_collected,
        'reasons_not_ready': reasons,
    }


def calculate_tour_launch_readiness(tour):
    """
    The single computed, auditable answer. Never a subjective AI opinion —
    every field here traces to real persisted model state.
    """
    ensure_launch_checklist(tour)
    required_items = LaunchChecklistItem.objects.filter(tour=tour, required=True)
    total_required_items = required_items.count()
    completed_items = required_items.filter(status='complete').count()
    blocked_items = list(required_items.filter(status='blocked'))
    missing_evidence = [
        {'item_key': item.item_key, 'label': item.label, 'status': item.status, 'blocking_reason': item.blocking_reason}
        for item in required_items.exclude(status='complete')
    ]

    technical_authorized, technical_reasons = is_technical_work_authorized(tour)
    mrv_readiness = calculate_mrv_baseline_readiness(tour)

    reasons_not_ready = []
    if completed_items < total_required_items:
        reasons_not_ready.append(
            f'{total_required_items - completed_items} of {total_required_items} required launch checklist items are not complete.'
        )
    if blocked_items:
        reasons_not_ready.append(f'{len(blocked_items)} checklist item(s) are explicitly blocked.')
    if tour.human_approved is not True:
        reasons_not_ready.append('Human sign-off (StewardshipTour.human_approved) has not been recorded.')
    reasons_not_ready.extend(technical_reasons)
    reasons_not_ready.extend(mrv_readiness['reasons_not_ready'])

    ready_to_launch = (
        completed_items == total_required_items
        and not blocked_items
        and tour.human_approved is True
        and technical_authorized
        and mrv_readiness['ready']
    )

    return {
        'ready_to_launch': ready_to_launch,
        'total_required_items': total_required_items,
        'completed_items': completed_items,
        'blocked_items': blocked_items,
        'missing_evidence': missing_evidence,
        'human_approval_status': tour.human_approved,
        'technical_authorization_status': technical_authorized,
        'mrv_baseline_status': mrv_readiness,
        'reasons_not_ready': reasons_not_ready,
    }


def mark_tour_ready_to_launch(tour):
    """Refuses to flip status to 'ready_to_launch' unless calculate_tour_launch_readiness() says so — the concrete code-level gate."""
    readiness = calculate_tour_launch_readiness(tour)
    if not readiness['ready_to_launch']:
        raise LaunchNotReadyError(
            f"Tour '{tour.title}' is not ready to launch: " + '; '.join(readiness['reasons_not_ready'])
        )
    tour.status = 'ready_to_launch'
    tour.save(update_fields=['status'])
    return tour
