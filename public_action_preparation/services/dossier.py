"""
public_action_preparation/services/dossier.py — Phase 25: the printable
Founder Action Dossier. A pure read composition — missing stays Missing,
never filled with invented prose (same discipline as
good_agents.services.pilot_launchpad.build_dossier).
"""
from public_action_preparation.services.evidence_pack import build_evidence_pack
from public_action_preparation.services.founder_review import compute_recommendation
from public_action_preparation.services.readiness import READINESS_LABELS, compute_action_readiness

MISSING = 'Missing'


def build_founder_action_dossier(opportunity):
    decision = getattr(opportunity, 'action_type_decision', None)
    process = getattr(opportunity, 'verified_official_process', None)
    ethics = getattr(opportunity, 'ethics_review', None)
    latest_draft = decision.content_drafts.order_by('-version_number').first() if decision else None
    readiness = compute_action_readiness(opportunity)
    recommendation, reasons = compute_recommendation(opportunity)

    return {
        'opportunity': opportunity,
        'executive_summary': opportunity.problem_statement or MISSING,
        'evidence_pack': build_evidence_pack(opportunity),
        'action_type': decision.get_action_type_display() if decision and decision.action_type else MISSING,
        'action_rationale': decision.rationale if decision else MISSING,
        'official_process': process,
        'ethics_review': ethics,
        'ethics_passed': ethics.all_passed if ethics else False,
        'proposed_content': latest_draft,
        'readiness': readiness,
        'readiness_label': READINESS_LABELS[readiness],
        'recommendation': recommendation,
        'recommendation_reasons': reasons,
        'unknowns': (decision.beneficiary_basis_notes if decision and decision.action_type == 'refer_to_existing_service' else '') or 'See evidence pack missing_evidence.',
    }
