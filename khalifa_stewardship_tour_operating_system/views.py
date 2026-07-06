from django.shortcuts import get_object_or_404, render

from khalifa_stewardship_tour_operating_system.models import (
    StewardshipProblem, StewardshipTour, TourFundingPlan, TourLocalPartner, TourMRVPlan, TourParticipantRole,
)

CORE_PHRASE = 'Tourists leave. EcoIQ stays.'
CORE_THESIS = 'Travel should leave a place better than you found it.'

TOUR_CATEGORY_CARDS = [
    {
        'title': 'Clean Heat Tour', 'tour_type': 'clean_heat',
        'problem': 'Coal heating, inefficient heating, heat loss, household air quality risk, energy cost burden.',
        'interventions': [
            'Clean heating upgrade', 'Insulation support', 'Boiler / heat pump / electric backup assessment',
            'Smart controls', 'Safety review',
        ],
    },
    {
        'title': 'Mountain Stewardship Tour', 'tour_type': 'mountain',
        'problem': 'Waste, erosion, damaged trails, nature degradation.',
        'interventions': ['Guided cleanup', 'Erosion control support', 'Habitat protection', 'Local ranger / expert review'],
    },
    {
        'title': 'Lake & Water Stewardship Tour', 'tour_type': 'lake_water',
        'problem': 'Water pollution, waste, unsafe access, unmanaged tourism impact.',
        'interventions': ['Shoreline cleanup', 'Waste mapping', 'Water stewardship', 'Community awareness', 'Monitoring'],
    },
    {
        'title': 'Food & Surplus Stewardship Tour', 'tour_type': 'food_surplus',
        'problem': 'Food surplus, cold-chain loss, meat/food waste, community need.',
        'interventions': [
            'Surplus prediction', 'Safe redistribution where lawful', 'Cold-chain support',
            'Community kitchen / food-bank support', 'Waste-to-value routing',
        ],
    },
    {
        'title': 'Community Greenhouse Tour', 'tour_type': 'greenhouse',
        'problem': 'Food insecurity, underused land, local resilience.',
        'interventions': ['Greenhouse materials', 'Irrigation support', 'Local operator setup', 'Training', 'Production monitoring'],
    },
    {
        'title': 'Wildlife & Nature Restoration Tour', 'tour_type': 'wildlife',
        'problem': 'Habitat loss, biodiversity risk, animal welfare concerns.',
        'interventions': ['Habitat restoration', 'Water access support', 'Expert-guided monitoring', 'No-harm wildlife protection'],
    },
]

WORLD_SCALE_SECTIONS = [
    {'country': 'Kazakhstan', 'status': 'Operational (demo)', 'focus': 'Clean heat, mountains, water, food, greenhouse.'},
    {'country': 'Saudi Arabia', 'status': 'Future expansion concept', 'focus': 'Water stewardship, desert restoration, food surplus, energy.'},
    {'country': 'Türkiye', 'status': 'Future expansion concept', 'focus': 'Agriculture, water, earthquake recovery legacy, coastal restoration.'},
    {'country': 'UK', 'status': 'Future expansion concept', 'focus': 'Food surplus, community heating, nature restoration, housing efficiency.'},
    {'country': 'Africa', 'status': 'Future expansion concept', 'focus': 'Water, solar, agriculture, cold chain, health infrastructure.'},
]

NO_HARM_GATE_CHECKS = [
    'Participant safety', 'Community dignity', 'Consent',
    'Child / vulnerable adult protection', 'Food safety', 'Technical safety',
    'Environmental harm', 'Local partner due diligence', 'Religious / ethical claim safety',
    'Public communication accuracy',
]

HUMAN_APPROVAL_REQUIRED_BEFORE = [
    'Participant recruitment', 'Collecting money', 'Supplier appointment', 'Local partner appointment',
    'Household intervention', 'Food redistribution', 'Public impact claim',
    'Filming vulnerable people', 'Publishing household/community story', 'Technical work', 'Travel launch',
]

CLAIM_SAFETY_PRINCIPLES = [
    'Estimated benefit is never the same as a verified outcome.',
    'A funding plan is never the same as funding secured.',
    'Sponsor interest is never the same as a confirmed sponsor.',
    'A tour being approved is never the same as technical installation being authorised.',
]

PIPELINE_VISUAL = [
    'Problem', 'Evidence', 'AI Agents', 'Intervention', 'Funding', 'Tour',
    'Human Participation', 'MRV', 'Legacy',
]

CTA_BUTTONS = [
    {'label': 'Open Khalifa Tours Operating System', 'url_name': 'khalifa_stewardship_tour_operating_system:overview'},
    {'label': 'See Kazakhstan Clean Heat Demo', 'url_name': 'khalifa_stewardship_tour_operating_system:kazakhstan_demo'},
    {'label': 'View All Tours', 'url_name': 'khalifa_stewardship_tour_operating_system:tours'},
    {'label': 'View Problems', 'url_name': 'khalifa_stewardship_tour_operating_system:problems'},
    {'label': 'View Funding', 'url_name': 'khalifa_stewardship_tour_operating_system:funding'},
    {'label': 'View MRV', 'url_name': 'khalifa_stewardship_tour_operating_system:mrv'},
    {'label': 'View Legacy Records', 'url_name': 'khalifa_stewardship_tour_operating_system:legacy'},
    {'label': 'Open Presentation Mode', 'url_name': 'khalifa_stewardship_tour_operating_system:presentation'},
]


def _dashboard_stats():
    return {
        'upcoming_tours': StewardshipTour.objects.exclude(status__in=['completed', 'blocked']).count(),
        'problems_under_review': StewardshipProblem.objects.filter(status='under_review').count(),
        'approved_interventions': StewardshipTour.objects.filter(status='approved_with_conditions').count(),
        'funding_gaps_open': TourFundingPlan.objects.filter(funding_gap__gt=0).count(),
        'participant_capacity': sum(StewardshipTour.objects.values_list('participant_capacity', flat=True)),
        'local_partners': TourLocalPartner.objects.count(),
        'mrv_pending': TourMRVPlan.objects.exclude(verification_status='verified').count(),
        'verified_legacy_records': StewardshipTour.objects.filter(status='verified_legacy').count(),
    }


def overview(request):
    tours = StewardshipTour.objects.all()
    return render(request, 'khalifa_stewardship_tour_operating_system/overview.html', {
        'core_phrase': CORE_PHRASE, 'core_thesis': CORE_THESIS,
        'stats': _dashboard_stats(), 'tour_categories': TOUR_CATEGORY_CARDS,
        'tours': tours, 'cta_buttons': CTA_BUTTONS,
    })


def presentation(request):
    return render(request, 'khalifa_stewardship_tour_operating_system/presentation.html', {
        'core_thesis': CORE_THESIS, 'core_phrase': CORE_PHRASE,
        'pipeline_visual': PIPELINE_VISUAL, 'world_scale': WORLD_SCALE_SECTIONS,
    })


def tours(request):
    tours_qs = StewardshipTour.objects.select_related('country', 'funding_plan', 'mrv_plan')
    return render(request, 'khalifa_stewardship_tour_operating_system/tours.html', {
        'tours': tours_qs, 'tour_categories': TOUR_CATEGORY_CARDS,
    })


def tour_detail(request, slug):
    tour = get_object_or_404(StewardshipTour.objects.select_related('country'), slug=slug)
    problems = tour.problems.prefetch_related('interventions')
    funding_plan = getattr(tour, 'funding_plan', None)
    participant_roles = tour.participant_roles.all()
    local_partners = tour.local_partners.all()
    mrv_plan = getattr(tour, 'mrv_plan', None)
    legacy_record = getattr(tour, 'legacy_record', None)
    return render(request, 'khalifa_stewardship_tour_operating_system/tour_detail.html', {
        'tour': tour, 'problems': problems, 'funding_plan': funding_plan,
        'participant_roles': participant_roles, 'local_partners': local_partners,
        'mrv_plan': mrv_plan, 'legacy_record': legacy_record,
        'claim_safety_principles': CLAIM_SAFETY_PRINCIPLES,
    })


def problems(request):
    problems_qs = StewardshipProblem.objects.select_related('tour').prefetch_related('interventions')
    return render(request, 'khalifa_stewardship_tour_operating_system/problems.html', {'problems': problems_qs})


def funding(request):
    plans = TourFundingPlan.objects.select_related('tour')
    return render(request, 'khalifa_stewardship_tour_operating_system/funding.html', {
        'plans': plans, 'claim_safety_principles': CLAIM_SAFETY_PRINCIPLES,
    })


def mrv(request):
    plans = TourMRVPlan.objects.select_related('tour')
    return render(request, 'khalifa_stewardship_tour_operating_system/mrv.html', {'plans': plans})


def legacy(request):
    tours_with_legacy = StewardshipTour.objects.filter(legacy_record__isnull=False).select_related('legacy_record')
    return render(request, 'khalifa_stewardship_tour_operating_system/legacy.html', {
        'tours_with_legacy': tours_with_legacy,
    })


def kazakhstan_demo(request):
    from khalifa_stewardship_tour_operating_system.services.demo_flagship_pipeline import DEMO_RUN_SLUG
    from ai_agent_council.models import AgentTask, CouncilDecision, CouncilRun

    tour = StewardshipTour.objects.filter(slug='kazakhstan-clean-heat').select_related('country').first()
    council_run = CouncilRun.objects.filter(slug=DEMO_RUN_SLUG).first()
    decision = CouncilDecision.objects.filter(run=council_run).first() if council_run else None
    agent_tasks = AgentTask.objects.filter(run=council_run).order_by('order') if council_run else []
    problem = tour.problems.first() if tour else None
    ranked_interventions = []
    if problem:
        from khalifa_stewardship_tour_operating_system.services.capital_allocation_link import (
            rank_stewardship_interventions,
        )
        from khalifa_stewardship_tour_operating_system.services.demo_flagship_pipeline import (
            CAPITAL_AT_RISK_CEILING, INVENTORY_VALUE_CEILING,
        )
        ranked_interventions = rank_stewardship_interventions(problem, CAPITAL_AT_RISK_CEILING, INVENTORY_VALUE_CEILING)

    return render(request, 'khalifa_stewardship_tour_operating_system/kazakhstan_demo.html', {
        'tour': tour, 'decision': decision, 'agent_tasks': agent_tasks,
        'ranked_interventions': ranked_interventions,
        'no_harm_gate_checks': NO_HARM_GATE_CHECKS,
        'human_approval_required_before': HUMAN_APPROVAL_REQUIRED_BEFORE,
    })
