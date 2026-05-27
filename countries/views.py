"""
EcoIQ Country Intelligence — Views.

/countries/           → country directory
/countries/<slug>/    → full country intelligence page
"""
from django.shortcuts import render, get_object_or_404

from countries.models import CountryProfile, REGION_CHOICES
from countries.modernisation_data import get_actions as get_modernisation_actions
from companies.models import CompanyProfile


# ── Helpers ─────────────────────────────────────────────────────────────────────

def _get_dev_bank_compat(country):
    """
    Indicative development bank / climate finance compatibility.
    Returns list of dicts: {name, status, color, detail, mandate}
    status: 'eligible' | 'partial' | 'conditional'
    """
    items = []
    s = country.national_ecoiq_index
    t = country.transparency_score or 0
    i = country.investment_climate_score or 0
    r = country.region

    # IFC / World Bank Group
    if s >= 50 and t >= 50:
        items.append({
            'name': 'IFC / World Bank',
            'mandate': 'Private sector & development finance',
            'status': 'eligible',
            'color': '#00e89a',
            'detail': 'Transparency and investment climate meet IFC baseline criteria for transition finance.',
        })
    elif s >= 38:
        items.append({
            'name': 'IFC / World Bank',
            'mandate': 'Private sector & development finance',
            'status': 'partial',
            'color': '#f4a261',
            'detail': 'Partial eligibility — governance improvement required for full program access.',
        })
    else:
        items.append({
            'name': 'IFC / World Bank',
            'mandate': 'Private sector & development finance',
            'status': 'conditional',
            'color': '#e63946',
            'detail': 'Conditional access — significant governance and transparency reforms required.',
        })

    # EBRD (active in Europe, Central Asia, Middle East)
    ebrd_regions = ('western_europe', 'eastern_europe', 'central_asia', 'middle_east')
    if r in ebrd_regions:
        items.append({
            'name': 'EBRD',
            'mandate': 'European & transition economy finance',
            'status': 'eligible' if s >= 50 else 'partial',
            'color': '#58a6ff' if s >= 50 else '#f4a261',
            'detail': ('Geographic mandate match — EBRD transition finance programs active in this region.'
                       if s >= 50 else
                       'EBRD mandate match — enhanced country program under assessment.'),
        })

    # Asian Development Bank (Asia + Pacific mandate)
    adb_regions = ('east_asia', 'south_asia', 'southeast_asia', 'central_asia', 'oceania')
    if r in adb_regions:
        items.append({
            'name': 'Asian Development Bank',
            'mandate': 'Asia-Pacific infrastructure & development',
            'status': 'eligible' if s >= 45 else 'partial',
            'color': '#8b5cf6',
            'detail': ('ADB active country — infrastructure and clean energy programs available.'
                       if s >= 45 else
                       'ADB partial eligibility — energy transition program requires governance baseline.'),
        })

    # AIIB (Asian Infrastructure Investment Bank)
    aiib_regions = ('east_asia', 'central_asia', 'middle_east', 'south_asia', 'southeast_asia',
                    'western_europe', 'eastern_europe')
    if r in aiib_regions and i >= 40:
        items.append({
            'name': 'AIIB',
            'mandate': 'Infrastructure investment across Asia & beyond',
            'status': 'eligible' if i >= 55 else 'partial',
            'color': '#06b6d4',
            'detail': ('Investment climate meets AIIB eligibility for infrastructure co-financing.'
                       if i >= 55 else
                       'Partial eligibility — investment climate improvement would unlock full AIIB access.'),
        })

    # Green Climate Fund (GCF)
    ren = country.renewable_energy_share or 0
    if ren >= 25 or (s >= 55 and t >= 55):
        items.append({
            'name': 'Green Climate Fund',
            'mandate': 'Climate adaptation & mitigation finance',
            'status': 'eligible',
            'color': '#00e89a',
            'detail': 'Renewable commitment and governance profile meet GCF direct access criteria.',
        })
    elif s >= 35:
        items.append({
            'name': 'Green Climate Fund',
            'mandate': 'Climate adaptation & mitigation finance',
            'status': 'partial',
            'color': '#f4a261',
            'detail': 'GCF partial access via accredited entity intermediaries — direct access requires enhanced action plan.',
        })

    return items


def _get_country_ai_confidence(country):
    """
    0–100 intelligence quality indicator for country profiles.
    Based on data completeness, AI content quality, and structured data richness.
    """
    score = 0

    # AI content completeness (40 pts)
    for field in ('ai_overview', 'ai_transition_narrative', 'ai_risk_summary', 'ai_investment_thesis'):
        val = getattr(country, field, '')
        if val and len(val) > 80:
            score += 10

    # Structured data richness (40 pts)
    if country.industrial_sectors:
        score += min(len(country.industrial_sectors) * 3, 12)
    if country.pollution_hotspots:
        score += min(len(country.pollution_hotspots) * 4, 12)
    if country.financing_gaps:
        score += min(len(country.financing_gaps) * 3, 8)
    if country.policy_highlights:
        score += min(len(country.policy_highlights) * 2, 8)

    # Macro data completeness (20 pts)
    macro_fields = ('gdp_usd', 'co2_megatonnes', 'renewable_energy_share',
                    'fossil_fuel_dependency', 'industrial_gdp_share',
                    'estimated_transition_gap_usd')
    score += sum(2 for f in macro_fields if getattr(country, f, None) is not None)  # up to 12
    if country.is_published:
        score += 8

    return min(round(score), 100)


def _get_corruption_exposure(country):
    """
    Derive a corruption exposure level from transparency score.
    Returns: {'level': str, 'score': int, 'color': str, 'detail': str}
    """
    t = country.transparency_score or 0
    exposure = round(100 - t)

    if t >= 75:
        return {
            'level': 'Low', 'score': exposure,
            'color': '#00e89a',
            'detail': 'Strong national transparency baseline — low institutional corruption risk for investors.',
        }
    elif t >= 55:
        return {
            'level': 'Moderate', 'score': exposure,
            'color': '#58a6ff',
            'detail': 'Moderate transparency — standard due diligence protocols recommended.',
        }
    elif t >= 40:
        return {
            'level': 'Elevated', 'score': exposure,
            'color': '#f4a261',
            'detail': 'Elevated corruption exposure — enhanced governance diligence required for investment decisions.',
        }
    else:
        return {
            'level': 'High', 'score': exposure,
            'color': '#e63946',
            'detail': 'High corruption risk environment — significant governance due diligence and contractual protections required.',
        }


# ── Views ────────────────────────────────────────────────────────────────────────

def country_directory(request):
    """
    /countries/ — browse all published country intelligence pages.
    """
    qs = CountryProfile.objects.filter(is_published=True).order_by(
        '-national_ecoiq_index'
    )

    region = request.GET.get('region', '')
    if region:
        qs = qs.filter(region=region)

    return render(request, 'countries/directory.html', {
        'countries':       qs,
        'region':          region,
        'region_choices':  REGION_CHOICES,
        'total_count':     CountryProfile.objects.filter(is_published=True).count(),
    })


def country_detail(request, slug):
    """
    /countries/<slug>/ — full country intelligence page.
    """
    country = get_object_or_404(CountryProfile, slug=slug, is_published=True)

    # Companies from this country (by Company.country field)
    companies = (
        CompanyProfile.objects
        .filter(
            status__in=('public', 'verified'),
            company__country__icontains=country.name,
        )
        .select_related('company')
        .order_by('-ecoiq_total_score')[:10]
    )

    # Score cards for display
    score_cards = [
        {
            'label': 'Transition Readiness',
            'score': country.transition_readiness_score,
            'icon':  '⚡',
            'color': '#00e89a',
            'desc':  'How prepared this country is for the industrial energy transition',
        },
        {
            'label': 'Policy Environment',
            'score': country.policy_environment_score,
            'icon':  '📋',
            'color': '#58a6ff',
            'desc':  'Quality and ambition of industrial and climate policy framework',
        },
        {
            'label': 'Investment Climate',
            'score': country.investment_climate_score,
            'icon':  '💰',
            'color': '#a855f7',
            'desc':  'Attractiveness for ethical and transition finance investment',
        },
        {
            'label': 'Transparency',
            'score': country.transparency_score,
            'icon':  '🔍',
            'color': '#06b6d4',
            'desc':  'National baseline for transparency and anti-corruption governance',
        },
        {
            'label': 'Industrial Modernization',
            'score': country.industrial_modernization_score,
            'icon':  '🏭',
            'color': '#f4a261',
            'desc':  'Modernisation of industrial base, infrastructure, and clean tech adoption',
        },
    ]

    # Intelligence helpers
    dev_bank_compat    = _get_dev_bank_compat(country)
    ai_confidence      = _get_country_ai_confidence(country)
    corruption_exposure = _get_corruption_exposure(country)

    # Radar scores (5 dimensions, 0–100)
    radar_scores = [
        round(country.transition_readiness_score, 1),
        round(country.policy_environment_score, 1),
        round(country.investment_climate_score, 1),
        round(country.transparency_score, 1),
        round(country.industrial_modernization_score, 1),
    ]

    modernisation_actions = get_modernisation_actions(slug)

    return render(request, 'countries/detail.html', {
        'country':               country,
        'companies':             companies,
        'score_cards':           score_cards,
        'dev_bank_compat':       dev_bank_compat,
        'ai_confidence':         ai_confidence,
        'corruption_exposure':   corruption_exposure,
        'radar_scores':          radar_scores,
        'modernisation_actions': modernisation_actions,
    })
