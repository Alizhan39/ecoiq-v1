"""
khalifa_stewardship_tour_operating_system/services/tours.py — provisioning
for stewardship tours, problems, interventions, funding plans, participant
roles, local partners and MRV plans. Idempotent via get_or_create + explicit
field sync, matching every seed command in this repo — never
delete-then-recreate.
"""
from khalifa_stewardship_tour_operating_system.models import (
    StewardshipIntervention, StewardshipProblem, StewardshipTour, TourFundingPlan,
    TourLocalPartner, TourMRVPlan, TourParticipantRole,
)


def create_stewardship_tour(slug, title, tour_type, **fields):
    tour, _ = StewardshipTour.objects.get_or_create(slug=slug, defaults={'title': title, 'tour_type': tour_type})
    tour.title = title
    tour.tour_type = tour_type
    for field, value in fields.items():
        setattr(tour, field, value)
    tour.save()
    return tour


def create_stewardship_problem(tour, problem_type, title, **fields):
    problem, _ = StewardshipProblem.objects.get_or_create(
        tour=tour, title=title, defaults={'problem_type': problem_type},
    )
    problem.problem_type = problem_type
    for field, value in fields.items():
        setattr(problem, field, value)
    problem.save()
    return problem


def create_stewardship_intervention(problem, title, intervention_type, **fields):
    intervention, _ = StewardshipIntervention.objects.get_or_create(
        problem=problem, title=title, defaults={'intervention_type': intervention_type},
    )
    intervention.intervention_type = intervention_type
    for field, value in fields.items():
        setattr(intervention, field, value)
    intervention.save()
    return intervention


def create_funding_plan(tour, participant_contribution=0, sponsor_contribution=0, grant_contribution=0,
                         recovered_value_contribution=0, local_partner_contribution=0, total_required=0, **fields):
    """funding_gap is always computed here — never asserted independently by a caller."""
    plan, _ = TourFundingPlan.objects.get_or_create(tour=tour, defaults={})
    plan.total_required = total_required
    plan.participant_contribution = participant_contribution
    plan.sponsor_contribution = sponsor_contribution
    plan.grant_contribution = grant_contribution
    plan.recovered_value_contribution = recovered_value_contribution
    plan.local_partner_contribution = local_partner_contribution
    contributions = (
        participant_contribution + sponsor_contribution + grant_contribution
        + recovered_value_contribution + local_partner_contribution
    )
    plan.funding_gap = max(0, round(total_required - contributions, 2))
    for field, value in fields.items():
        setattr(plan, field, value)
    plan.save()
    return plan


def add_participant_role(tour, role_name, **fields):
    role, _ = TourParticipantRole.objects.get_or_create(tour=tour, role_name=role_name, defaults={})
    for field, value in fields.items():
        setattr(role, field, value)
    role.save()
    return role


def add_local_partner(tour, partner_name, **fields):
    partner, _ = TourLocalPartner.objects.get_or_create(tour=tour, partner_name=partner_name, defaults={})
    for field, value in fields.items():
        setattr(partner, field, value)
    partner.save()
    return partner


def create_mrv_plan(tour, **fields):
    plan, _ = TourMRVPlan.objects.get_or_create(tour=tour, defaults={})
    for field, value in fields.items():
        setattr(plan, field, value)
    plan.save()
    return plan
