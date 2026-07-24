"""
good_agents/services/project_bridge.py — the bridge into the EXISTING
project pipeline (PR5 Phase 10-11). Human approval is required before a
GoodOpportunity creates a real gold_intelligence.GoldProject — no code
path in this app creates one automatically. Once created, the project
flows through the existing, unmodified capital_guardian /
waste_to_value_capital_allocation_engine pipeline exactly like any other
GoldProject (see good_agents/services/pipeline.py, PR2, unchanged).

Per docs/adr-0001-canonical-project-architecture.md: GoldProject remains
the canonical project anchor. This module never creates a second project
model — it only creates rows in the ONE existing table, always additive.
"""
from django.utils import timezone

from good_agents.models import ProjectCandidate
from good_agents.services import notify
from good_agents.services.timeline import record_event


class ProjectCandidateNotApprovedError(Exception):
    pass


def propose_candidate(opportunity, *, action_pathway=None, rationale=''):
    candidate, created = ProjectCandidate.objects.get_or_create(
        opportunity=opportunity, defaults=dict(action_pathway=action_pathway, rationale=rationale),
    )
    if created:
        notify.notify_project_candidate_ready(candidate)
    return candidate


def approve_candidate(candidate, *, actor):
    if actor is None:
        raise ProjectCandidateNotApprovedError('Project candidate approval requires a real actor.')
    if candidate.status != 'proposed':
        raise ValueError(f'ProjectCandidate {candidate.pk} is {candidate.status!r}, not "proposed".')
    candidate.status = 'approved'
    candidate.approved_by = actor
    candidate.approved_at = timezone.now()
    candidate.save(update_fields=['status', 'approved_by', 'approved_at', 'updated_at'])
    return candidate


def reject_candidate(candidate, *, reason=''):
    candidate.status = 'rejected'
    candidate.rationale = f'{candidate.rationale}\n\nRejected: {reason}'.strip()
    candidate.save(update_fields=['status', 'rationale', 'updated_at'])
    return candidate


def create_project_from_candidate(candidate, *, slug, name, is_demo, region='', country=None, description=''):
    """
    The ONLY function in this app that creates a real GoldProject. Requires
    `candidate.status == 'approved'` (a human already signed off via
    `approve_candidate`). `is_demo` has NO default — the caller must state
    explicitly whether this is real or demo data, matching
    seed_clean_heating_pilot.py's own discipline. Every gold-specific/
    technical/financial field is left null; this function never fabricates
    a plausible-looking number for any of them. Idempotent: calling twice
    for the same candidate returns the existing project.
    """
    if candidate.created_project_id:
        return candidate.created_project  # idempotent — checked before the status guard below, since a
        # successful first call already advances status to 'created', which would otherwise wrongly look
        # like "never approved" on a second call with the exact same arguments.
    if candidate.status != 'approved':
        raise ProjectCandidateNotApprovedError(
            f'ProjectCandidate {candidate.pk} is {candidate.status!r}, not "approved" — cannot create a project. '
            f'Call approve_candidate(candidate, actor=...) first.'
        )

    from gold_intelligence.models import GoldProject
    project, _ = GoldProject.objects.get_or_create(
        slug=slug,
        defaults=dict(
            name=name, commodity='other', country=country, region=region, status='exploration',
            description=description, is_demo=is_demo,
            ore_grade_g_per_tonne=None, resource_tonnes=None, recovery_rate_pct=None,
            mine_life_years=None, expected_annual_production_oz=None,
            total_capex_usd=None, annual_opex_usd=None, cash_cost_usd_per_oz=None, aisc_usd_per_oz=None,
            gold_price_assumption_usd_per_oz=None, discount_rate_pct=None,
            total_committed_capital_usd=None, insurance_coverage_usd=None,
            insurance_expiry_date=None, data_last_updated=None,
        ),
    )
    candidate.created_project = project
    candidate.status = 'created'
    candidate.save(update_fields=['created_project', 'status', 'updated_at'])

    record_event(
        candidate.opportunity, 'project_created', actor=candidate.approved_by,
        source_object_reference=f'gold_intelligence.GoldProject:{project.pk}',
        notes=f'Created from ProjectCandidate {candidate.pk} (originating opportunity: "{candidate.opportunity.title}").',
    )
    return project
