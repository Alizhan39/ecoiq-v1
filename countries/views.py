"""
EcoIQ Country Intelligence — Views.

/countries/           → country directory
/countries/<slug>/    → full country intelligence page
"""
from django.shortcuts import render, get_object_or_404

from countries.models import CountryProfile, REGION_CHOICES
from companies.models import CompanyProfile


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
            'desc':  'How prepared this country is for the industrial energy transition',
        },
        {
            'label': 'Policy Environment',
            'score': country.policy_environment_score,
            'icon':  '📋',
            'desc':  'Quality and ambition of industrial and climate policy framework',
        },
        {
            'label': 'Investment Climate',
            'score': country.investment_climate_score,
            'icon':  '💰',
            'desc':  'Attractiveness for ethical and transition finance investment',
        },
        {
            'label': 'Transparency',
            'score': country.transparency_score,
            'icon':  '🔍',
            'desc':  'National baseline for transparency and anti-corruption',
        },
        {
            'label': 'Industrial Modernization',
            'score': country.industrial_modernization_score,
            'icon':  '🏭',
            'desc':  'How modernized is the industrial and infrastructure base',
        },
    ]

    return render(request, 'countries/detail.html', {
        'country':      country,
        'companies':    companies,
        'score_cards':  score_cards,
    })
