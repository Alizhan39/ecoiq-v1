"""
mizan/views.py — EcoIQ Mizan Engine API views.

Four endpoints:
  GET  /api/mizan/company/<slug>/  — company Mizan evaluation
  GET  /api/mizan/country/<slug>/  — country aggregate Mizan evaluation
  POST /api/mizan/project/         — project or transaction evaluation
  GET  /api/mizan/explain/         — scoring methodology reference

Authentication: EcoIQ API key (X-API-Key / Authorization: Bearer).
  /api/mizan/explain/ is public — no key required.
  All others follow standard EcoIQ access policy (public tier = limited).
"""
from __future__ import annotations

from rest_framework import status
from rest_framework.decorators import (
    api_view, authentication_classes, permission_classes,
)
from rest_framework.response import Response

from api.authentication import APIKeyAuthentication
from api.permissions import IsPublicOrAPIKey

from mizan.scoring import (
    score_company, score_country,
    DIMENSION_WEIGHTS, MIZAN_LABELS,
)
from mizan.project import ProjectInput, score_project


# ── Company ───────────────────────────────────────────────────────────────────

@api_view(['GET'])
@authentication_classes([APIKeyAuthentication])
@permission_classes([IsPublicOrAPIKey])
def mizan_company(request, slug: str):
    """
    GET /api/mizan/company/<slug>/

    Full Mizan Engine evaluation for a specific company profile.
    Returns six ethical dimension scores, risk flags, investor note,
    ethical finance note, due diligence note, and recommended actions.
    """
    from django.shortcuts import get_object_or_404
    from league.models import Company

    company = get_object_or_404(
        Company.objects.select_related('profile'), slug=slug
    )
    try:
        profile = company.profile
    except Exception:
        return Response(
            {'error': f'No company profile found for slug "{slug}".'},
            status=status.HTTP_404_NOT_FOUND,
        )

    result = score_company(profile)

    return Response({
        'company': slug,
        'name':    company.name,
        'country': company.country,
        'sector':  company.sector,
        **result.to_dict(),
        '_meta': {
            'engine':   'EcoIQ Mizan Engine v1',
            'endpoint': request.build_absolute_uri(),
            'note':     'Scores are AI-assisted and indicative. Not investment advice.',
        },
    })


# ── Country ───────────────────────────────────────────────────────────────────

@api_view(['GET'])
@authentication_classes([APIKeyAuthentication])
@permission_classes([IsPublicOrAPIKey])
def mizan_country(request, slug: str):
    """
    GET /api/mizan/country/<slug>/

    Aggregate Mizan score for all public company profiles in a country.
    Includes sector breakdown, label distribution, and top/bottom performers.
    """
    from collections import defaultdict
    from django.shortcuts import get_object_or_404
    from companies.models import CompanyProfile

    try:
        from countries.models import CountryProfile
        country_obj  = get_object_or_404(CountryProfile, slug=slug)
        country_name = country_obj.name
    except Exception:
        return Response(
            {'error': f'Country "{slug}" not found.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    profiles = list(
        CompanyProfile.objects
        .filter(
            company__country__iexact=country_name,
            status__in=('public', 'verified'),
        )
        .select_related('company')
    )

    if not profiles:
        return Response({
            'country':       slug,
            'name':          country_name,
            'company_count': 0,
            'message':       'No public company profiles found for this country.',
        })

    # Aggregate score
    agg_result = score_country(profiles)

    # Per-company scores for breakdown (lightweight — reuse score_company)
    scored_profiles = [
        {
            'name':   p.company.name,
            'slug':   p.company.slug,
            'sector': p.company.sector,
            'score':  round(score_company(p).final_mizan_score, 2),
        }
        for p in profiles
    ]
    scored_sorted = sorted(scored_profiles, key=lambda x: -x['score'])

    # Sector breakdown: average Mizan score per sector
    sector_totals: dict[str, list[float]] = defaultdict(list)
    for item in scored_profiles:
        sector_totals[item['sector']].append(item['score'])
    sector_breakdown = {
        s: round(sum(v) / len(v), 2)
        for s, v in sorted(sector_totals.items(), key=lambda x: -sum(x[1]) / len(x[1]))
    }

    # Label distribution
    from collections import Counter
    label_dist = dict(
        Counter(
            score_company(p).mizan_label for p in profiles
        ).most_common()
    )

    return Response({
        'country':       slug,
        'name':          country_name,
        'company_count': len(profiles),
        **agg_result.to_dict(),
        'sector_breakdown':  sector_breakdown,
        'label_distribution': label_dist,
        'top_performers':    scored_sorted[:5],
        'bottom_performers': scored_sorted[-5:],
        '_meta': {
            'engine':   'EcoIQ Mizan Engine v1',
            'endpoint': request.build_absolute_uri(),
            'note':     (
                'Country aggregate derived from AI-assisted company profiles. '
                'Independent verification required before capital allocation.'
            ),
        },
    })


# ── Project ───────────────────────────────────────────────────────────────────

@api_view(['POST'])
@authentication_classes([APIKeyAuthentication])
@permission_classes([IsPublicOrAPIKey])
def mizan_project(request):
    """
    POST /api/mizan/project/

    Evaluate a proposed project or transaction against the Mizan Engine.
    All scores are model estimates — independent ESIA required.

    Request body (JSON):
    {
        "name":                    "Solar Park Phase 2",    // optional
        "sector":                  "energy",                // REQUIRED
        "country":                 "Kazakhstan",            // optional
        "project_type":            "renewable_energy",      // optional
        "budget_usd":              50000000,                // optional float
        "duration_years":          5,                       // optional float
        "renewable_energy_share":  100,                     // 0-100
        "direct_jobs":             500,                     // integer
        "local_procurement_pct":   70,                      // 0-100
        "community_benefit":       "high",                  // high|medium|low|none
        "environmental_assessment": true,                   // bool
        "governance_framework":    "IFC",                   // IFC|EBRD|ADB|GBP|national|none
        "gender_inclusion_plan":   false,                   // bool
        "climate_risk_disclosure": true,                    // bool
        "description":             "..."                    // optional
    }
    """
    body = request.data
    if not body:
        return Response(
            {
                'error': 'Request body required.',
                'hint':  'Send JSON with at minimum {"sector": "energy"} to get a baseline score.',
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    sector = body.get('sector', '').strip()
    if not sector:
        return Response(
            {'error': '"sector" is required. Provide a sector slug (e.g. "energy", "oil_gas", "mining").'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        project_input = ProjectInput.from_dict(dict(body))
        result        = score_project(project_input)
    except (TypeError, ValueError) as exc:
        return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    return Response({
        'project': project_input.name,
        'sector':  project_input.sector,
        'country': project_input.country,
        **result.to_dict(),
        '_meta': {
            'engine':   'EcoIQ Mizan Engine v1',
            'endpoint': request.build_absolute_uri(),
            'note': (
                'Project score is a model estimate based on declared parameters. '
                'Independent Environmental and Social Impact Assessment (ESIA) '
                'and legal due diligence are required before any capital commitment.'
            ),
        },
    })


# ── Explain ───────────────────────────────────────────────────────────────────

@api_view(['GET'])
@authentication_classes([])
@permission_classes([])
def mizan_explain(request):
    """
    GET /api/mizan/explain/

    Public endpoint. Returns the Mizan Engine scoring methodology:
    dimension definitions, weights, label tiers, confidence levels,
    ML integration roadmap, and ethical finance alignment note.
    No API key required.
    """
    return Response({
        'engine':   'EcoIQ Mizan Engine',
        'version':  'v1',
        'paradigm': 'rule-based (scikit-learn integration planned — see ML-HOOK comments in mizan/scoring.py and mizan/project.py)',
        'description': (
            'The Mizan Engine evaluates climate transition activity across six ethical dimensions. '
            'It answers not only whether emissions are being reduced, but whether the transition '
            'is transparent, balanced, fair, evidence-based, and beneficial to society.'
        ),

        'dimensions': {
            'public_benefit': {
                'weight':      DIMENSION_WEIGHTS['public_benefit'],
                'description': 'Does the company or project create genuine public value — quality jobs, regional development, infrastructure, national value?',
                'inputs':      ['public_benefit_score', 'jobs_created_score', 'regional_development_score', 'national_value_score', 'infrastructure_contribution_score'],
            },
            'harm_reduction': {
                'weight':      DIMENSION_WEIGHTS['harm_reduction'],
                'description': 'Is the company actively reducing its pollution and controversy footprint? Inverted composite harm score, adjusted for energy transition trajectory.',
                'inputs':      ['pollution_level', 'controversy_risk_score', 'energy_transition_score', 'harm_penalty'],
            },
            'justice_distribution': {
                'weight':      DIMENSION_WEIGHTS['justice_distribution'],
                'description': 'Is value distributed equitably? Governance quality minus the gap between stated transparency and actual controversy exposure.',
                'inputs':      ['transparency_anti_corruption_score', 'anti_corruption_score', 'audit_quality_score', 'procurement_transparency_score'],
            },
            'transparency_accountability': {
                'weight':      DIMENSION_WEIGHTS['transparency_accountability'],
                'description': 'Does the company disclose honestly and maintain audit quality? Verified profiles receive a confidence uplift.',
                'inputs':      ['transparency_score_detail', 'audit_quality_score', 'procurement_transparency_score', 'is_verified'],
            },
            'stewardship': {
                'weight':      DIMENSION_WEIGHTS['stewardship'],
                'description': 'Is the company managing natural and human capital as a long-term custodian?',
                'inputs':      ['future_readiness_score', 'energy_transition_score', 'water_impact_score', 'biodiversity_impact_score', 'ethical_alignment_score', 'waste_management_score'],
            },
            'evidence_confidence': {
                'weight':      DIMENSION_WEIGHTS['evidence_confidence'],
                'description': 'How reliable is the underlying profile data? Returned as a score (0–100) and a tier label in every response.',
                'tiers': {
                    'verified':          92,
                    'analyst-reviewed':  75,
                    'ai-seeded':         55,
                    'model-estimate':    35,
                },
            },
        },

        'final_mizan_score': {
            'formula': 'Weighted sum of six dimension scores using DIMENSION_WEIGHTS',
            'range':   '0 – 100',
            'label_tiers': {lbl: f'>= {thr}' for thr, lbl in MIZAN_LABELS},
        },

        'endpoints': {
            'GET  /api/mizan/company/<slug>/': 'Full Mizan evaluation for a company (requires API key)',
            'GET  /api/mizan/country/<slug>/': 'Aggregate Mizan evaluation for all companies in a country (requires API key)',
            'POST /api/mizan/project/':        'Project or transaction evaluation — send sector + optional parameters (requires API key)',
            'GET  /api/mizan/explain/':         'This endpoint — scoring methodology. Public, no key required.',
        },

        'project_scoring_parameters': {
            'sector':                  'required — sector slug (energy, oil_gas, mining, metallurgy, chemical, transport, agriculture, renewables, finance, other)',
            'country':                 'optional — country name for governance context adjustment',
            'budget_usd':              'optional float — total project budget in USD',
            'duration_years':          'optional float — project duration for stewardship scoring',
            'renewable_energy_share':  '0-100 — % of energy output that is renewable',
            'direct_jobs':             'integer — number of direct jobs created',
            'local_procurement_pct':   '0-100 — % of budget sourced locally',
            'community_benefit':       'high | medium | low | none',
            'environmental_assessment': 'bool — EIA conducted?',
            'governance_framework':    'IFC | EBRD | ADB | World Bank | EU Taxonomy | GBP | TCFD | national | none',
            'gender_inclusion_plan':   'bool — gender inclusion plan in place?',
            'climate_risk_disclosure': 'bool — TCFD-aligned climate risk disclosure?',
        },

        'ml_integration': {
            'status': 'planned',
            'approach': (
                'Each dimension scorer contains a # ML-HOOK comment marking where '
                'a trained scikit-learn model (RandomForest or GradientBoosting) '
                'should replace the rule-based formula. The feature vector from '
                'project_feature_vector() in mizan/project.py is already StandardScaler-ready.'
            ),
            'training_data_required': [
                'Historical project outcomes with ground-truth dimension scores',
                'Company-level time-series for trajectory-based harm reduction scoring',
                'Country-level benchmark data for governance context calibration',
            ],
        },

        'ethical_finance_note': (
            'The Mizan Engine is compatible with responsible capital frameworks that evaluate '
            'justice, stewardship, public benefit, harm avoidance, and evidence-based transparency — '
            'including IFC Performance Standards, EBRD Environmental Policy, EU Taxonomy, '
            'Green Bond Principles, JETP country partnerships, and long-horizon stewardship '
            'investment criteria.'
        ),

        '_note': 'All scores are AI-assisted and indicative. Not investment advice.',
    })
