"""
partner_participation/services/routing.py — the routing engine upgrade
(Phase 18-20). Composes capability_graph's existing matcher with the new
participation signals (membership, opportunity preference, public route
availability) into RoutingCandidate rows, each with a transparent,
plain-language explanation and a confidence LABEL — never an opaque
numeric "AI confidence" score.

Participation is one signal, not universal authority (Phase 18's own
instruction): an organisation with a real, independently-verified
capability but no partner-portal engagement at all (e.g. a public
authority that has never claimed its EcoIQ organisation record) can still
rank as VERIFIED_CAPABILITY_MATCH — never unfairly excluded just for not
participating.
"""
from django.utils import timezone

from capability_graph.models import CapabilityConflict
from capability_graph.services.matcher import find_organisations_for_capability
from capability_graph.services.needs import required_capabilities_for_theme
from good_agents.models import GoodOpportunity
from partner_participation.models import (
    ROUTABLE_ACCEPTANCE_MODES, ROUTING_ALLOWED_TRANSITIONS, OpportunityPreference, OrganisationMembership,
    RoutingCandidate,
)


class IllegalRoutingTransitionError(Exception):
    pass


def _has_verified_membership(organisation):
    return OrganisationMembership.objects.filter(organisation=organisation, status='verified_member').exists()


def _matching_preference(organisation, theme):
    return OpportunityPreference.objects.filter(organisation=organisation, theme=theme).first()


def _has_open_route(edge):
    return edge.public_routes.filter(is_currently_open=True).exists()


def _has_unresolved_conflict(edge):
    return CapabilityConflict.objects.filter(capability=edge, resolution='unresolved').exists()


def score_candidate(organisation, edge, opportunity):
    """
    Returns (confidence_label, match_reasons, skip_reason). skip_reason is
    non-None when this organisation must NOT be routed as ready (Phase 8:
    never route to NOT_ACCEPTING/PAUSED as ready).
    """
    reasons = [
        f'Capability "{edge.get_capability_display()}" — {edge.get_verification_state_display()}.',
    ]
    if edge.jurisdiction:
        reasons.append(f'Jurisdiction: {edge.jurisdiction}.')
    if edge.topic_domain:
        reasons.append(f'Topic match: {edge.topic_domain}.')
    if edge.limitations:
        reasons.append(f'Limitations: {edge.limitations}')

    if _has_unresolved_conflict(edge):
        reasons.append('This capability has an unresolved conflict with other evidence.')
        return 'needs_review', reasons, None

    preference = _matching_preference(organisation, opportunity.theme)
    verified_member = _has_verified_membership(organisation)
    has_route = _has_open_route(edge)

    if preference is not None:
        reasons.append(
            f'Opportunity preference for "{preference.get_theme_display()}": {preference.get_acceptance_mode_display()}.'
        )
        if preference.acceptance_mode not in ROUTABLE_ACCEPTANCE_MODES:
            return None, reasons, f'Organisation preference is "{preference.get_acceptance_mode_display()}" — not routed as ready.'
    if verified_member:
        reasons.append('Organisation has a verified participating member.')
    if has_route:
        reasons.append('At least one public route is currently open.')
    else:
        reasons.append('No public route is currently open for this capability.')

    strong_capability = edge.verification_state == 'independently_verified'
    documented_capability = edge.verification_state in ('independently_verified', 'documented', 'human_reviewed')
    preference_routable = preference is not None and preference.acceptance_mode in ROUTABLE_ACCEPTANCE_MODES

    if strong_capability and verified_member and preference_routable and has_route:
        return 'strong_verified_match', reasons, None
    if documented_capability:
        return 'verified_capability_match', reasons, None
    if verified_member and preference_routable:
        return 'participation_match', reasons, None
    if not has_route:
        return 'no_verified_route', reasons, None
    return 'possible_responsible_party', reasons, None


def generate_routing_candidates(opportunity):
    """
    Real, deterministic routing — no ML/embeddings. Returns
    {'created': [...], 'skipped': [{'organisation': org, 'reason': str}]}
    so a caller can see exactly what was excluded and why (never a silent
    drop). Instrumented via AI Observatory (Phase 28) — no second
    telemetry system; 'partner_routing' reuses the exact same
    start_session/record_stage/finish_session PR4/6 already built.
    """
    from ai_observatory.services.recorder import finish_session, record_stage, start_session

    session = start_session(kind='partner_routing', human_review_required=True)
    capabilities = required_capabilities_for_theme(opportunity.theme)
    created, skipped, seen_orgs = [], [], set()

    with record_stage(session, 'score_candidates', 'Score capability + participation signals', category='deterministic') as info:
        for capability in capabilities:
            edges = find_organisations_for_capability(
                capability, jurisdiction=opportunity.region or None, min_verification='unverified',
            )
            for edge in edges:
                organisation = edge.organisation
                if organisation.pk in seen_orgs:
                    continue
                confidence_label, reasons, skip_reason = score_candidate(organisation, edge, opportunity)
                if skip_reason:
                    skipped.append({'organisation': organisation, 'reason': skip_reason})
                    continue
                seen_orgs.add(organisation.pk)
                candidate, _ = RoutingCandidate.objects.get_or_create(
                    organisation=organisation, opportunity=opportunity,
                    defaults=dict(confidence_label=confidence_label, match_reasons=reasons),
                )
                created.append(candidate)
        info['items_processed'] = len(created) + len(skipped)
        info['metadata'] = {'created': len(created), 'skipped': len(skipped)}

    finish_session(
        session, status='completed',
        final_recommendation_status='produced' if created else 'not_applicable',
    )
    return {'created': created, 'skipped': skipped}


def transition(candidate, new_status, *, actor=None, notes=''):
    allowed = ROUTING_ALLOWED_TRANSITIONS.get(candidate.status, set())
    if new_status not in allowed:
        raise IllegalRoutingTransitionError(
            f'Cannot move RoutingCandidate {candidate.pk} from {candidate.status!r} to {new_status!r}.'
        )
    if new_status in ('approved_to_share', 'shared') and (actor is None or not getattr(actor, 'is_staff', False)):
        raise IllegalRoutingTransitionError(
            f'Moving a candidate to {new_status!r} requires a real EcoIQ staff actor — '
            f'visibility to the organisation is always an explicit EcoIQ decision.'
        )

    candidate.status = new_status
    if new_status == 'shared':
        candidate.shared_by = actor
        candidate.shared_at = timezone.now()
    if new_status in ('viewed', 'interested', 'not_interested', 'needs_more_information', 'accepted_for_next_step'):
        candidate.responded_by = actor
        candidate.responded_at = timezone.now()
        if notes:
            candidate.response_notes = notes
    candidate.save()

    if new_status == 'ready_for_ecoiq_review':
        from partner_participation.services.notify import notify_opportunity_routed_for_review
        notify_opportunity_routed_for_review(candidate)
    return candidate
