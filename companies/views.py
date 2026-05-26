"""
EcoIQ Company Intelligence — Public Views.

/companies/           → directory with search + filters
/companies/<slug>/    → full public company profile
"""
from django.shortcuts import render, get_object_or_404

from companies.models import CompanyProfile, CompanyGuidanceVideo, MORAL_LABEL_CHOICES
from companies.scoring import get_path_to_100_actions
from league.models import Company, SECTOR_CHOICES


# ── Helpers ────────────────────────────────────────────────────────────────────

MORAL_DISPLAY = dict(MORAL_LABEL_CHOICES)

DISCLAIMER_FULL = (
    "This company profile is based on publicly available information and "
    "AI-assisted analysis. It has not been verified or endorsed by the company "
    "unless marked as Verified."
)
DISCLAIMER_LIGHT = (
    "EcoIQ scores are indicative and designed to support transparency, "
    "modernization, and responsible investment dialogue."
)


# ── Company Directory ──────────────────────────────────────────────────────────

def directory(request):
    """
    /companies/ — searchable, filterable company directory.
    Shows all public CompanyProfile records with EcoIQ cards.
    """
    qs = CompanyProfile.objects.filter(
        status__in=('public', 'verified')
    ).select_related('company').order_by('-ecoiq_total_score')

    # Search
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(company__name__icontains=q)

    # Filters
    sector    = request.GET.get('sector', '')
    country   = request.GET.get('country', '')
    label     = request.GET.get('label', '')
    verified  = request.GET.get('verified', '')
    funding   = request.GET.get('funding', '')
    pollution = request.GET.get('pollution', '')

    if sector:
        qs = qs.filter(company__sector=sector)
    if country:
        qs = qs.filter(company__country__icontains=country)
    if label:
        qs = qs.filter(moral_label=label)
    if verified == '1':
        qs = qs.filter(is_verified=True)
    if funding:
        qs = qs.filter(funding_status=funding)
    if pollution:
        qs = qs.filter(pollution_level=pollution)

    # Distinct countries for filter dropdown
    countries = (
        CompanyProfile.objects
        .filter(status__in=('public', 'verified'))
        .values_list('company__country', flat=True)
        .distinct()
        .order_by('company__country')
    )

    return render(request, 'companies/directory.html', {
        'profiles':       qs,
        'total_count':    CompanyProfile.objects.filter(status__in=('public','verified')).count(),
        'result_count':   qs.count(),
        'q':              q,
        'sector':         sector,
        'country':        country,
        'label':          label,
        'verified':       verified,
        'funding':        funding,
        'pollution':      pollution,
        'sector_choices': SECTOR_CHOICES,
        'moral_choices':  MORAL_LABEL_CHOICES,
        'countries':      countries,
        'disclaimer_light': DISCLAIMER_LIGHT,
    })


# ── Company Detail ─────────────────────────────────────────────────────────────

def company_detail(request, slug):
    """
    /companies/<slug>/ — full public EcoIQ company profile.
    """
    company = get_object_or_404(Company, slug=slug)
    profile = get_object_or_404(CompanyProfile, company=company,
                                status__in=('public', 'verified', 'draft'))

    # Score breakdown for display
    score_cards = [
        {
            'label':  'Public Benefit',
            'score':  profile.public_benefit_score,
            'weight': '25%',
            'icon':   '🌍',
            'desc':   'Employment quality, regional development, community investment, national value',
        },
        {
            'label':  'Environmental Stewardship',
            'score':  profile.environmental_responsibility_score,
            'weight': '25%',
            'icon':   '♻️',
            'desc':   'Pollution intensity, waste management, water stewardship, biodiversity',
        },
        {
            'label':  'Responsible Modernization',
            'score':  profile.modernization_score,
            'weight': '20%',
            'icon':   '⚡',
            'desc':   'Energy transition, digitalization, infrastructure upgrades, future readiness',
        },
        {
            'label':  'Transparent Governance',
            'score':  profile.transparency_anti_corruption_score,
            'weight': '15%',
            'icon':   '🔍',
            'desc':   'Reporting quality, audit standards, procurement transparency',
        },
        {
            'label':  'Anti-Corruption',
            'score':  profile.anti_corruption_score,
            'weight': '10%',
            'icon':   '⚖️',
            'desc':   'Anti-corruption practices, ethical procurement, governance integrity',
        },
        {
            'label':  'Ethical Alignment',
            'score':  profile.ethical_alignment_score,
            'weight': '5%',
            'icon':   '✦',
            'desc':   'Long-term ethical value creation, controversy management, stakeholder trust',
        },
    ]

    # Path to 100%
    path_actions = get_path_to_100_actions(profile)

    # Guidance videos — only show what visibility allows
    videos = CompanyGuidanceVideo.objects.filter(
        company=profile, status='published', visibility='public',
    ).order_by('-created_at')[:4]

    # Transition Engine integration
    roadmaps = []
    active_roadmap = None
    has_roadmap = False
    try:
        from transition.models import TransitionRoadmap
        roadmaps = list(company.roadmaps.order_by('-created_at')[:3])
        active_roadmap = roadmaps[0] if roadmaps else None
        has_roadmap = bool(roadmaps)
    except Exception:
        pass

    # Financing matches
    financing_matches = []
    if active_roadmap:
        try:
            financing_matches = list(
                active_roadmap.financing_matches
                .select_related('opportunity')
                .order_by('-match_score')[:4]
            )
        except Exception:
            pass

    # AI briefing
    briefing = None
    try:
        from intelligence.models import ExecutiveBriefing
        briefing = ExecutiveBriefing.objects.filter(company=company).order_by('-created_at').first()
    except Exception:
        pass

    # Sources
    sources = profile.cited_sources.all()[:8]

    return render(request, 'companies/detail.html', {
        'company':          company,
        'profile':          profile,
        'score_cards':      score_cards,
        'path_actions':     path_actions,
        'videos':           videos,
        'roadmaps':         roadmaps,
        'active_roadmap':   active_roadmap,
        'has_roadmap':      has_roadmap,
        'financing_matches': financing_matches,
        'briefing':         briefing,
        'sources':          sources,
        'disclaimer_full':  DISCLAIMER_FULL,
        'disclaimer_light': DISCLAIMER_LIGHT,
        'moral_display':    profile.moral_label_display,
    })
