"""
EcoIQ Quranic Decision Filter — Web views.

    /decisions/            Stewardship Dashboard (portfolio of decision integrity)
    /decisions/<slug>/     Decision Engine for one company (cards, queue, roadmap,
                           scenario re-scoring)
"""
from django.shortcuts import render, get_object_or_404
from django.db.models import Avg, Count

from league.models import Company
from companies.models import CompanyProfile
from qdf.models import DecisionAssessment, VERDICT_CHOICES, RISK_LEVEL_CHOICES
from qdf.scoring import get_or_compute
from qdf import engine


def _band_of(score):
    if score >= 80: return 'Stewardship-Grade'
    if score >= 65: return 'Responsible'
    if score >= 50: return 'Transitional'
    if score >= 35: return 'Compromised'
    return 'Unsound'


def stewardship_dashboard(request):
    """Portfolio view over all auto-computed decision assessments."""
    qs = (DecisionAssessment.objects
          .filter(source='auto', profile__isnull=False)
          .select_related('profile__company')
          .order_by('-decision_integrity_score'))

    total = qs.count()
    agg = qs.aggregate(avg=Avg('decision_integrity_score'),
                       conf=Avg('confidence'))
    avg_integrity = round(agg['avg'] or 0, 1)

    verdict_counts = {v[0]: 0 for v in VERDICT_CHOICES}
    risk_counts    = {r[0]: 0 for r in RISK_LEVEL_CHOICES}
    band_counts    = {}
    red_line       = 0
    for a in qs:
        verdict_counts[a.verdict] = verdict_counts.get(a.verdict, 0) + 1
        risk_counts[a.risk_level] = risk_counts.get(a.risk_level, 0) + 1
        band = _band_of(a.decision_integrity_score)
        band_counts[band] = band_counts.get(band, 0) + 1
        if a.red_line_breached:
            red_line += 1

    verdict_display = dict(VERDICT_CHOICES)
    verdict_summary = [
        {'key': k, 'label': verdict_display[k], 'count': verdict_counts.get(k, 0),
         'pct': round(verdict_counts.get(k, 0) / total * 100) if total else 0}
        for k in verdict_display
    ]

    return render(request, 'qdf/stewardship_dashboard.html', {
        'total':          total,
        'avg_integrity':  avg_integrity,
        'avg_confidence': round((agg['conf'] or 0) * 100),
        'red_line':       red_line,
        'verdict_summary': verdict_summary,
        'risk_counts':    risk_counts,
        'band_counts':    band_counts,
        'leaders':        qs[:10],
        'watchlist':      qs.order_by('decision_integrity_score')[:10],
    })


def decision_engine(request, slug):
    """Decision Engine for one company: cards, action queue, roadmap, scenario."""
    company = get_object_or_404(Company, slug=slug)
    profile = get_object_or_404(CompanyProfile, company=company,
                                status__in=('public', 'verified', 'draft'))
    assessment = get_or_compute(profile)
    if assessment is None:
        return render(request, 'qdf/decision_engine.html',
                      {'company': company, 'assessment': None})

    queue   = engine.build_action_queue(assessment)
    roadmap = engine.generate_roadmap(assessment)

    # ── Scenario re-scoring (server-side, no API key) ──────────────────────
    scenario = None
    overrides = {}
    for qs in assessment.ordered_scores:
        raw = request.GET.get(f'sim_{qs.question.key}')
        if raw not in (None, ''):
            try:
                overrides[qs.question.key] = max(0.0, min(10.0, float(raw)))
            except ValueError:
                pass
    if overrides:
        scenario = engine.simulate_scenario(assessment, overrides)

    return render(request, 'qdf/decision_engine.html', {
        'company':    company,
        'profile':    profile,
        'assessment': assessment,
        'queue':      queue,
        'roadmap':    roadmap,
        'scenario':   scenario,
        'overrides':  overrides,
    })
