"""
global_research/services/council.py — Global Research Council integration.

Reuses `ai_agent_council`'s CouncilRun/AgentTask/CouncilDecision schema and
deterministic reasoning services unmodified — no new schema. Per
docs/adr/ADR-global-research-engine.md decision 10, the Stewardship role is
NOT re-added as a new persona: this Council reuses the "Stewardship Agent"
already shipped for the Digital Twin phase directly.

Like every CouncilRun in this repository, a Research Council review in this
phase is `is_simulated=True` — each agent's position is a scripted,
deterministic reasoning function over real stored data, not a live LLM
call (see docs/adr/ADR-global-research-engine.md decision 4).
"""
from django.utils.text import slugify

from global_research.services import stewardship_screen

TASK_CATEGORY = 'global_research_candidate_review'

COUNCIL_AGENT_ORDER = [
    'Problem Definition Agent',
    'Technical Requirements Agent',
    'Scientific Research Agent',
    'Patent and Innovation Agent',
    'Manufacturer Discovery Agent',
    'Product Specification Agent',
    'Independent Evidence Agent',
    'Compatibility Agent',
    'Commercial Intelligence Agent',
    'Supply Chain Risk Agent',
    'Regulatory Agent',
    'Stewardship Agent',
    'Evidence Auditor',
    'Research Synthesis Agent',
]


def _confidence_breakdown(evidence_coverage, missing_data_penalty, contradiction_penalty=0, historical_reliability_adjustment=0):
    from ai_agent_council.services.confidence import build_confidence_breakdown

    return build_confidence_breakdown(
        evidence_coverage=evidence_coverage, source_quality=evidence_coverage, consistency=evidence_coverage,
        missing_data_penalty=missing_data_penalty, contradiction_penalty=contradiction_penalty,
        historical_reliability_adjustment=historical_reliability_adjustment,
    )


def _position(summary, confidence_breakdown, evidence_refs, missing_data, risk_flags):
    return {
        'position_summary': summary, 'confidence': confidence_breakdown['final'],
        'confidence_breakdown': confidence_breakdown, 'evidence_refs': evidence_refs,
        'missing_data': missing_data, 'risk_flags': risk_flags,
    }


def _problem_definition_position(mission, technology_candidate, product_candidate, compat, contradictions):
    has_origin = mission.has_valid_origin
    breakdown = _confidence_breakdown(90 if has_origin else 20, missing_data_penalty=0 if has_origin else 60)
    return _position(
        f'Mission "{mission.title}" origin valid: {has_origin}. Status: {mission.get_status_display()}.',
        breakdown, [f'global_research.ResearchMission:{mission.pk}'],
        [] if has_origin else ['ResearchMission has no valid EcoIQ origin entity'],
        [] if has_origin else ['no_valid_origin'],
    )


def _technical_requirements_position(mission, technology_candidate, product_candidate, compat, contradictions):
    requirements = list(mission.requirements.all())
    measurable = [r for r in requirements if r.metric]
    breakdown = _confidence_breakdown(
        round((len(measurable) / len(requirements)) * 100, 2) if requirements else 0,
        missing_data_penalty=10 * (len(requirements) - len(measurable)),
    )
    return _position(
        f'{len(measurable)}/{len(requirements)} requirements have a measurable metric.',
        breakdown, [f'global_research.TechnicalRequirement:{r.pk}' for r in measurable],
        [] if len(measurable) == len(requirements) else ['some requirements lack a measurable metric'], [],
    )


def _scientific_research_position(mission, technology_candidate, product_candidate, compat, contradictions):
    sources = mission.sources.filter(evidence_tier__in=['A', 'B'])
    breakdown = _confidence_breakdown(80 if sources.exists() else 20, missing_data_penalty=0 if sources.exists() else 50)
    return _position(
        f'{sources.count()} Tier A/B authoritative source(s) found for this mission.',
        breakdown, [f'global_research.ResearchSource:{s.pk}' for s in sources],
        [] if sources.exists() else ['no Tier A/B authoritative source found'], [],
    )


def _patent_innovation_position(mission, technology_candidate, product_candidate, compat, contradictions):
    trl = technology_candidate.technology_readiness_level if technology_candidate else None
    early_stage = trl is not None and trl <= 5
    breakdown = _confidence_breakdown(70, missing_data_penalty=0)
    return _position(
        f'Technology readiness level: {trl if trl is not None else "not recorded"}. '
        + ('Early-stage — must not be presented as mature commercial availability.' if early_stage else 'Commercially mature evidence available.'),
        breakdown, [], [] if trl is not None else ['no technology_readiness_level recorded'],
        ['early_stage_technology'] if early_stage else [],
    )


def _manufacturer_discovery_position(mission, technology_candidate, product_candidate, compat, contradictions):
    from global_research.models import ManufacturerProfile

    manufacturers = ManufacturerProfile.objects.filter(products__technology_candidate=technology_candidate).distinct() if technology_candidate else ManufacturerProfile.objects.none()
    countries = sorted({m.headquarters_country for m in manufacturers if m.headquarters_country})
    breakdown = _confidence_breakdown(
        min(100, 20 * len(countries)), missing_data_penalty=0 if len(countries) >= 3 else 20,
    )
    return _position(
        f'{manufacturers.count()} manufacturer(s) found across {len(countries)} countries: {", ".join(countries) or "none"}.',
        breakdown, [f'global_research.ManufacturerProfile:{m.pk}' for m in manufacturers],
        [] if len(countries) >= 3 else ['manufacturer country coverage is narrow — broaden search before shortlisting'], [],
    )


def _product_specification_position(mission, technology_candidate, product_candidate, compat, contradictions):
    if product_candidate is None:
        return _position('No specific product candidate under review — technology-level only.',
                          _confidence_breakdown(40, missing_data_penalty=30), [], ['no product_candidate specified'], [])
    claims = list(product_candidate.source_claims.all())
    verified = [c for c in claims if c.verified]
    breakdown = _confidence_breakdown(
        round((len(verified) / len(claims)) * 100, 2) if claims else 0, missing_data_penalty=10 * (len(claims) - len(verified)),
    )
    return _position(
        f'{product_candidate.product_name}: {len(verified)}/{len(claims)} specification claims independently verified.',
        breakdown, [f'global_research.ResearchClaim:{c.pk}' for c in claims],
        [] if verified else ['no independently verified specification claims yet'], [],
    )


def _independent_evidence_position(mission, technology_candidate, product_candidate, compat, contradictions):
    candidate = product_candidate or technology_candidate
    score = candidate.evidence_score if candidate else None
    breakdown = _confidence_breakdown(score or 0, missing_data_penalty=0 if score else 40)
    return _position(
        f'Aggregate evidence score: {score if score is not None else "not yet scored"}.',
        breakdown, [], [] if score and score >= 40 else ['evidence score below the threshold for a shortlist recommendation'],
        [] if score and score >= 40 else ['insufficient_independent_evidence'],
    )


def _compatibility_position(mission, technology_candidate, product_candidate, compat, contradictions):
    if compat is None:
        return _position('No CompatibilityAssessment available for this candidate.',
                          _confidence_breakdown(30, missing_data_penalty=40), [], ['no compatibility assessment run yet'], ['no_compatibility_data'])
    breakdown = _confidence_breakdown(compat.evidence_quality or 0, missing_data_penalty=0 if compat.mandatory_pass else 30)
    return _position(
        f'Overall status: {compat.get_overall_status_display()}. Mandatory pass: {compat.mandatory_pass}. '
        f'Failed: {compat.mandatory_requirements_failed or "none"}.',
        breakdown, compat.evidence_references, compat.warnings,
        [] if compat.mandatory_pass else ['mandatory_requirement_failed'],
    )


def _commercial_intelligence_position(mission, technology_candidate, product_candidate, compat, contradictions):
    if product_candidate is None:
        return _position('No product candidate — no commercial data to review.', _confidence_breakdown(20, missing_data_penalty=40), [], ['no product_candidate'], [])
    has_real_cost = product_candidate.indicative_cost_type not in ('unavailable', 'ecoiq_assumption')
    breakdown = _confidence_breakdown(70 if has_real_cost else 20, missing_data_penalty=0 if has_real_cost else 50)
    return _position(
        f'Cost data: {product_candidate.get_indicative_cost_type_display()}.',
        breakdown, [], [] if has_real_cost else ['no real commercial cost data on file — RFQ recommended'], [],
    )


def _supply_chain_risk_position(mission, technology_candidate, product_candidate, compat, contradictions):
    from global_research.models import SupplyChainRiskFlag

    flags = SupplyChainRiskFlag.objects.filter(mission=mission, product_candidate=product_candidate) if product_candidate else SupplyChainRiskFlag.objects.none()
    open_high = flags.filter(severity='high', resolution_status='open')
    breakdown = _confidence_breakdown(80 if not open_high.exists() else 30, missing_data_penalty=0)
    return _position(
        f'{flags.count()} risk flag(s) recorded, {open_high.count()} open high-severity.',
        breakdown, [f'global_research.SupplyChainRiskFlag:{f.pk}' for f in flags],
        [], ['open_high_severity_risk'] if open_high.exists() else [],
    )


def _regulatory_position(mission, technology_candidate, product_candidate, compat, contradictions):
    status = compat.local_standards_compatibility if compat else 'insufficient_data'
    breakdown = _confidence_breakdown(70 if status == 'compatible' else 20, missing_data_penalty=0 if status == 'compatible' else 40)
    return _position(
        f'Local standards compatibility: {status}.',
        breakdown, [], [] if status == 'compatible' else ['no certification evidence recorded for the deployment jurisdiction'], [],
    )


def _stewardship_position(mission, technology_candidate, product_candidate, compat, contradictions):
    result = stewardship_screen.screen_technology_candidate(technology_candidate) if technology_candidate else {'score': None, 'flags': []}
    breakdown = _confidence_breakdown(result['score'] or 0, missing_data_penalty=0 if result['score'] is not None else 30)
    return _position(
        f'Stewardship screen score: {result["score"]}. Flags: {result["flags"] or "none"}. '
        'This is a lightweight pre-scenario screen — the full governed Stewardship KPI engine runs once a real '
        'ModernisationScenario is created.',
        breakdown, [], [] if result['score'] is not None else ['worker/environmental implications not yet documented'],
        ['stewardship_concern'] if result['flags'] else [],
    )


def _evidence_auditor_position(mission, technology_candidate, product_candidate, compat, contradictions):
    unresolved = [c for c in contradictions if c.resolution_status == 'unresolved']
    breakdown = _confidence_breakdown(90 if not unresolved else 40, missing_data_penalty=10 * len(unresolved))
    return _position(
        f'{len(unresolved)} unresolved contradiction(s) among this mission\'s claims.',
        breakdown, [], [], ['unresolved_contradictions'] if unresolved else [],
    )


def _research_synthesis_position(mission, technology_candidate, product_candidate, compat, contradictions):
    mandatory_pass = compat.mandatory_pass if compat else False
    breakdown = _confidence_breakdown(70 if mandatory_pass else 30, missing_data_penalty=0)
    next_action = 'ready_to_shortlist' if mandatory_pass else 'incompatible_or_request_more_evidence'
    return _position(
        f'Recommended next step: {next_action}.', breakdown, [], [], [] if mandatory_pass else ['candidate_not_ready'],
    )


AGENT_POSITION_BUILDERS = {
    'Problem Definition Agent': _problem_definition_position,
    'Technical Requirements Agent': _technical_requirements_position,
    'Scientific Research Agent': _scientific_research_position,
    'Patent and Innovation Agent': _patent_innovation_position,
    'Manufacturer Discovery Agent': _manufacturer_discovery_position,
    'Product Specification Agent': _product_specification_position,
    'Independent Evidence Agent': _independent_evidence_position,
    'Compatibility Agent': _compatibility_position,
    'Commercial Intelligence Agent': _commercial_intelligence_position,
    'Supply Chain Risk Agent': _supply_chain_risk_position,
    'Regulatory Agent': _regulatory_position,
    'Stewardship Agent': _stewardship_position,
    'Evidence Auditor': _evidence_auditor_position,
    'Research Synthesis Agent': _research_synthesis_position,
}


def council_run_slug(mission, technology_candidate, product_candidate):
    subject = product_candidate.product_name if product_candidate else (technology_candidate.name if technology_candidate else 'mission')
    return slugify(f'global-research-{mission.pk}-{technology_candidate.pk if technology_candidate else 0}-{subject}')[:120]


def get_council_run(mission, technology_candidate=None, product_candidate=None):
    from ai_agent_council.models import CouncilRun

    return CouncilRun.objects.filter(slug=council_run_slug(mission, technology_candidate, product_candidate)).first()


def convene_council(mission, technology_candidate=None, product_candidate=None):
    """Creates (idempotently, by slug) one CouncilRun with one AgentTask per
    COUNCIL_AGENT_ORDER entry and a CouncilDecision synthesising them."""
    from ai_agent_council.models import AgentTask, CouncilDecision, CouncilDisagreement, CouncilRun
    from ai_agent_council.services.disagreement import classify_conflict

    from global_research.models import CompatibilityAssessment, ContradictionRecord

    compat = CompatibilityAssessment.objects.filter(
        mission=mission, technology_candidate=technology_candidate, product_candidate=product_candidate,
    ).first()
    contradictions = list(ContradictionRecord.objects.filter(mission=mission))

    subject_name = product_candidate.product_name if product_candidate else (technology_candidate.name if technology_candidate else mission.title)
    run, created = CouncilRun.objects.get_or_create(
        slug=council_run_slug(mission, technology_candidate, product_candidate),
        defaults={
            'title': f'Global Research Review: {subject_name}',
            'question': f'Should "{subject_name}" be shortlisted for "{mission.title}"?',
            'task_category': TASK_CATEGORY, 'is_simulated': True,
            'selected_agents': [{'agent_name': n, 'selected': True, 'reason': 'Global Research candidate review — always convened.'} for n in COUNCIL_AGENT_ORDER],
        },
    )
    if not created:
        run.tasks.all().delete()

    tasks = []
    for order, agent_name in enumerate(COUNCIL_AGENT_ORDER):
        position = AGENT_POSITION_BUILDERS[agent_name](mission, technology_candidate, product_candidate, compat, contradictions)
        task = AgentTask.objects.create(
            run=run, agent_name=agent_name, collaboration_mode='parallel', status='completed',
            input_summary=f'Review candidate "{subject_name}" for mission "{mission.title}".',
            output_summary=position['position_summary'], position_summary=position['position_summary'],
            confidence=position['confidence'], confidence_breakdown=position['confidence_breakdown'],
            evidence_refs=position['evidence_refs'], missing_data=position['missing_data'],
            risk_flags=position['risk_flags'], order=order,
        )
        tasks.append(task)

    disagreements = []
    for i in range(len(tasks)):
        for j in range(i + 1, len(tasks)):
            conflict_type, resolution_method = classify_conflict(tasks[i], tasks[j])
            if conflict_type in ('risk_tolerance', 'domain') or (tasks[i].risk_flags and tasks[j].risk_flags and tasks[i].risk_flags != tasks[j].risk_flags):
                disagreements.append(CouncilDisagreement.objects.create(
                    run=run, position_a=tasks[i], position_b=tasks[j], conflict_type=conflict_type,
                    evidence_used=sorted(set(tasks[i].evidence_refs) & set(tasks[j].evidence_refs)),
                    resolution_method=resolution_method,
                    final_decision_summary=f'{tasks[i].agent_name} vs {tasks[j].agent_name}: {conflict_type} — {resolution_method}.',
                    minority_opinion_retained=True,
                ))

    blocking_flags = {'mandatory_requirement_failed', 'no_valid_origin', 'open_high_severity_risk'}
    minority_agents = [t.agent_name for t in tasks if blocking_flags & set(t.risk_flags)]
    majority_agents = [t.agent_name for t in tasks if t.agent_name not in minority_agents]

    mandatory_pass = compat.mandatory_pass if compat else False
    if minority_agents:
        decision_status = 'rejected' if not mandatory_pass else 'under_review'
    else:
        decision_status = 'approved'

    avg_confidence = round(sum(t.confidence for t in tasks) / len(tasks), 2) if tasks else None
    decision_breakdown = _confidence_breakdown(avg_confidence or 0, missing_data_penalty=10 * len(minority_agents))
    decision, _ = CouncilDecision.objects.update_or_create(
        run=run,
        defaults=dict(
            status=decision_status,
            summary=f'{len(tasks)} agents reviewed "{subject_name}". Mandatory compatibility pass: {mandatory_pass}.',
            majority_agents=majority_agents, minority_agents=minority_agents,
            minority_reason='; '.join(f'{a}: blocking flag raised' for a in minority_agents) if minority_agents else '',
            conditions=[], confidence=decision_breakdown['final'], confidence_breakdown=decision_breakdown,
            human_approval_required=True, human_approved=None,
        ),
    )
    run.status = 'decided'
    run.save(update_fields=['status', 'updated_at'])

    return {'run': run, 'tasks': tasks, 'disagreements': disagreements, 'decision': decision}
