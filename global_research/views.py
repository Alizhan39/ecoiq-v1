"""
global_research/views.py — minimal UI + API views for the 8 required
screens. Every page distinguishes OBSERVED (a stored field), CALCULATED (a
deterministic service's output), AI-SUGGESTED (a not-yet-human-reviewed
candidate/claim), MISSING (a data gap), and APPROVED (a real
ResearchHumanDecision) content — never rendering a suggestion with the
same visual weight as an approved decision. All views here are read-only;
approval actions happen via the Django admin or the service layer directly
(see docs/research_evidence_methodology.md §7) — this app never wires a
POST-triggered send/approve button that could be clicked without a real
review.
"""
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render

from global_research import models as m
from global_research.services import comparison as comparison_service


def mission_list(request):
    missions = m.ResearchMission.objects.order_by('-created_at')
    return render(request, 'global_research/mission_list.html', {'missions': missions})


def mission_dashboard(request, mission_id):
    mission = get_object_or_404(m.ResearchMission, pk=mission_id)
    sources = mission.sources.all()
    country_coverage = sorted({s.jurisdiction for s in sources if s.jurisdiction})
    language_coverage = sorted({s.get_language_display() for s in sources})
    evidence_scores = [c.confidence for c in mission.claims.all() if c.confidence is not None]
    avg_evidence_quality = round(sum(evidence_scores) / len(evidence_scores), 2) if evidence_scores else None
    unresolved_contradictions = mission.contradictions.filter(resolution_status='unresolved')
    return render(request, 'global_research/mission_dashboard.html', {
        'mission': mission, 'sources': sources, 'country_coverage': country_coverage,
        'language_coverage': language_coverage, 'avg_evidence_quality': avg_evidence_quality,
        'unresolved_contradictions': unresolved_contradictions,
        'requirements': mission.requirements.all(), 'runs': mission.runs.all()[:5],
    })


@login_required
def requirement_builder(request, mission_id):
    mission = get_object_or_404(m.ResearchMission, pk=mission_id)
    requirements = mission.requirements.order_by('-is_mandatory', 'requirement_type')
    return render(request, 'global_research/requirement_builder.html', {'mission': mission, 'requirements': requirements})


def global_discovery_view(request, mission_id):
    mission = get_object_or_404(m.ResearchMission, pk=mission_id)
    candidates = mission.technology_candidates.select_related('category').all()

    category = request.GET.get('category')
    status = request.GET.get('status')
    maturity = request.GET.get('maturity')
    if category:
        candidates = candidates.filter(category__name=category)
    if status:
        candidates = candidates.filter(status=status)
    if maturity:
        candidates = candidates.filter(commercial_maturity=maturity)

    categories = m.TechnologyCategory.objects.filter(candidates__mission=mission).distinct()
    return render(request, 'global_research/global_discovery_view.html', {
        'mission': mission, 'candidates': candidates, 'categories': categories,
        'status_choices': m.TechnologyCandidate.STATUS_CHOICES, 'maturity_choices': m.TechnologyCandidate.MATURITY_CHOICES,
    })


def evidence_view(request, mission_id):
    mission = get_object_or_404(m.ResearchMission, pk=mission_id)
    claims = mission.claims.select_related('source', 'assessment').order_by('subject', 'predicate')
    contradictions = mission.contradictions.select_related('claim_a', 'claim_b')
    return render(request, 'global_research/evidence_view.html', {'mission': mission, 'claims': claims, 'contradictions': contradictions})


def manufacturer_comparison(request, mission_id):
    mission = get_object_or_404(m.ResearchMission, pk=mission_id)
    evaluations = mission.comparative_evaluations.select_related(
        'product_candidate', 'product_candidate__manufacturer__organisation', 'technology_candidate', 'compatibility_assessment',
    ).order_by('rank', '-total_score')
    return render(request, 'global_research/manufacturer_comparison.html', {'mission': mission, 'evaluations': evaluations})


def technology_candidate_detail(request, candidate_id):
    candidate = get_object_or_404(m.TechnologyCandidate, pk=candidate_id)
    products = candidate.products.select_related('manufacturer__organisation')
    claims = candidate.source_claims.select_related('source', 'assessment')
    compatibility = candidate.compatibility_assessments.all()
    risk_flags = m.SupplyChainRiskFlag.objects.filter(mission=candidate.mission, product_candidate__technology_candidate=candidate)
    return render(request, 'global_research/candidate_detail.html', {
        'candidate': candidate, 'product': None, 'products': products, 'claims': claims,
        'compatibility': compatibility, 'risk_flags': risk_flags,
    })


def product_candidate_detail(request, candidate_id):
    product = get_object_or_404(m.ProductCandidate, pk=candidate_id)
    claims = product.source_claims.select_related('source', 'assessment')
    compatibility = product.compatibility_assessments.all()
    risk_flags = m.SupplyChainRiskFlag.objects.filter(product_candidate=product)
    return render(request, 'global_research/candidate_detail.html', {
        'candidate': product.technology_candidate, 'product': product, 'products': [product], 'claims': claims,
        'compatibility': compatibility, 'risk_flags': risk_flags,
    })


def council_view_technology(request, candidate_id):
    from global_research.services import council as council_service

    candidate = get_object_or_404(m.TechnologyCandidate, pk=candidate_id)
    return _render_council(request, candidate.mission, council_service.get_council_run(candidate.mission, technology_candidate=candidate))


def council_view_product(request, candidate_id):
    from global_research.services import council as council_service

    product = get_object_or_404(m.ProductCandidate, pk=candidate_id)
    run = council_service.get_council_run(product.technology_candidate.mission, technology_candidate=product.technology_candidate, product_candidate=product)
    return _render_council(request, product.technology_candidate.mission, run)


def _render_council(request, mission, council_run):
    tasks = council_run.tasks.all() if council_run else []
    decision_record = getattr(council_run, 'decision', None) if council_run else None
    return render(request, 'global_research/council_view.html', {
        'mission': mission, 'council_run': council_run, 'tasks': tasks, 'decision_record': decision_record,
    })


@login_required
def document_draft_list(request, mission_id):
    mission = get_object_or_404(m.ResearchMission, pk=mission_id)
    drafts = mission.document_drafts.order_by('document_type', '-version')
    return render(request, 'global_research/document_draft_list.html', {'mission': mission, 'drafts': drafts})


@login_required
def document_draft_detail(request, draft_id):
    draft = get_object_or_404(m.ResearchDocumentDraft, pk=draft_id)
    return render(request, 'global_research/document_draft_detail.html', {'draft': draft})


# ── API ────────────────────────────────────────────────────────────────────

def api_mission_list(request):
    missions = m.ResearchMission.objects.order_by('-created_at')
    return JsonResponse({'missions': [
        {'id': mm.pk, 'title': mm.title, 'status': mm.status, 'priority': mm.priority} for mm in missions
    ]})


def api_mission_detail(request, mission_id):
    mission = get_object_or_404(m.ResearchMission, pk=mission_id)
    return JsonResponse({
        'id': mission.pk, 'title': mission.title, 'status': mission.status,
        'origin_asset_id': mission.asset_id, 'origin_twin_id': mission.twin_id,
        'sources_count': mission.sources.count(), 'claims_count': mission.claims.count(),
        'technology_candidates_count': mission.technology_candidates.count(),
    })


def api_run_mission(request):
    return JsonResponse({'error': 'Not implemented via HTTP in this phase — run via management command or services.orchestrator.run_mission() directly, after human approval.'}, status=501)


def api_sources(request, mission_id):
    mission = get_object_or_404(m.ResearchMission, pk=mission_id)
    return JsonResponse({'sources': [
        {'id': s.pk, 'title': s.title, 'source_type': s.source_type, 'evidence_tier': s.evidence_tier,
         'source_owner_type': s.source_owner_type, 'language': s.language, 'content_safety_flagged': s.content_safety_flagged}
        for s in mission.sources.all()
    ]})


def api_claims(request, mission_id):
    mission = get_object_or_404(m.ResearchMission, pk=mission_id)
    return JsonResponse({'claims': [
        {'id': c.pk, 'subject': c.subject, 'predicate': c.predicate, 'object_value': c.object_value,
         'vendor_provided': c.vendor_provided, 'verified': c.verified, 'confidence': c.confidence}
        for c in mission.claims.all()
    ]})


def api_contradictions(request, mission_id):
    mission = get_object_or_404(m.ResearchMission, pk=mission_id)
    return JsonResponse({'contradictions': [
        {'id': c.pk, 'type': c.contradiction_type, 'delta': c.delta, 'resolution_status': c.resolution_status, 'explanation': c.explanation}
        for c in mission.contradictions.all()
    ]})


def api_comparison(request, mission_id):
    mission = get_object_or_404(m.ResearchMission, pk=mission_id)
    comparison_service.rank_mission_evaluations(mission)
    return JsonResponse({'evaluations': [
        {
            'id': e.pk, 'candidate': str(e.product_candidate or e.technology_candidate),
            'total_score': e.total_score, 'rank': e.rank, 'is_ranked': e.is_ranked,
            'evidence_score': e.evidence_score, 'missing_data': e.missing_data,
            'criteria_weights': e.criteria_weights, 'formula_version': e.formula_version,
        }
        for e in mission.comparative_evaluations.order_by('rank', '-total_score')
    ]})


def api_audit_trail(request, mission_id):
    mission = get_object_or_404(m.ResearchMission, pk=mission_id)
    decisions = mission.human_decisions.order_by('-decided_at')
    return JsonResponse({'human_decisions': [
        {'id': d.pk, 'stage': d.stage, 'decision': d.decision, 'human_approved': d.human_approved,
         'reviewer': d.reviewer.username if d.reviewer_id else None, 'decided_at': d.decided_at.isoformat()}
        for d in decisions
    ]})
