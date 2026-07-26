"""
digital_twin/services/council.py — Digital Twin Agent Council integration.

Reuses `ai_agent_council`'s CouncilRun/AgentTask/CouncilDecision schema and
its deterministic reasoning services (confidence.build_confidence_breakdown,
disagreement.classify_conflict) unmodified — no new schema, no new
orchestration engine.

Per docs/adr/ADR-digital-twin-foundation.md decision 4: like every other
CouncilRun in this repository today (`ai_agent_council/models.py`'s own
docstring: "there is no live LLM execution runtime anywhere in this
repository"), a Digital Twin council review in this phase is
`is_simulated=True` — each agent's position is produced by a scripted,
deterministic reasoning function over real stored data (the scenario, its
simulation, its stewardship assessments, its guardrail verdict), not a live
LLM call. Wiring a live adapter through
`agent_runtime_model_router.services.execution` is a follow-on task, not a
foundation-slice blocker.
"""
from django.utils import timezone
from django.utils.text import slugify

from digital_twin.services import guardrails as guardrails_service
from digital_twin.services import scenario_simulation

TASK_CATEGORY = 'digital_twin_scenario_review'
COUNCIL_FORMULA_VERSION = '1.0.0'

# Finance/Risk/Capital Guardian roles reuse the three existing personas
# directly (ADR decision 4) rather than duplicating them.
COUNCIL_AGENT_ORDER = [
    'Digital Twin Agent',
    'Engineering Agent',
    'Energy and Resources Agent',
    'Worker Safety Agent',
    'Community Impact Agent',
    'Evidence Agent',
    'Finance Modelling Agent',
    'Risk Agent (Governance Agent)',
    'Stewardship Agent',
    'Capital Allocation Agent',
]


def _confidence_breakdown(evidence_coverage, missing_data_penalty, contradiction_penalty=0, historical_reliability_adjustment=0):
    from ai_agent_council.services.confidence import build_confidence_breakdown

    return build_confidence_breakdown(
        evidence_coverage=evidence_coverage, source_quality=evidence_coverage, consistency=evidence_coverage,
        missing_data_penalty=missing_data_penalty, contradiction_penalty=contradiction_penalty,
        historical_reliability_adjustment=historical_reliability_adjustment,
    )


def _digital_twin_agent_position(scenario, simulation, assessments, guardrail):
    twin = scenario.twin
    scores = [twin.completeness_score, twin.confidence_score, twin.data_freshness_score]
    missing = [name for name, v in zip(('completeness', 'confidence', 'freshness'), scores) if v is None]
    evidence_coverage = twin.confidence_score if twin.confidence_score is not None else 0
    breakdown = _confidence_breakdown(evidence_coverage, missing_data_penalty=10 * len(missing))
    open_gaps = list(twin.data_gaps.filter(status='open').values_list('affected_area', flat=True))
    return {
        'position_summary': (
            f'Twin "{twin.name}" v{twin.version}: completeness={twin.completeness_score}, '
            f'confidence={twin.confidence_score}, freshness={twin.data_freshness_score}, status={twin.status}.'
        ),
        'confidence': breakdown['final'],
        'confidence_breakdown': breakdown,
        'evidence_refs': [f'digital_twin.DigitalTwin:{twin.pk}'],
        'missing_data': open_gaps,
        'risk_flags': ['baseline_not_ready'] if twin.status != 'baseline_ready' and twin.status != 'active' else [],
    }


def _engineering_agent_position(scenario, simulation, assessments, guardrail):
    has_spec = bool(scenario.technical_specification)
    breakdown = _confidence_breakdown(90 if has_spec else 30, missing_data_penalty=0 if has_spec else 40)
    risk_flags = list(scenario.technical_risks or [])
    return {
        'position_summary': (
            f'Technical specification {"present" if has_spec else "MISSING"}; '
            f'{len(scenario.implementation_phases or [])} implementation phase(s) recorded.'
        ),
        'confidence': breakdown['final'],
        'confidence_breakdown': breakdown,
        'evidence_refs': [f'digital_twin.ModernisationScenario:{scenario.pk}'] if has_spec else [],
        'missing_data': [] if has_spec else ['technical_specification'],
        'risk_flags': risk_flags,
    }


def _energy_resources_agent_position(scenario, simulation, assessments, guardrail):
    impacts = {
        'energy_impact': scenario.energy_impact, 'water_impact': scenario.water_impact,
        'waste_impact': scenario.waste_impact, 'emissions_impact': scenario.emissions_impact,
    }
    present = {k: v for k, v in impacts.items() if v is not None}
    missing = [k for k, v in impacts.items() if v is None]
    breakdown = _confidence_breakdown(
        evidence_coverage=round((len(present) / len(impacts)) * 100, 2), missing_data_penalty=5 * len(missing),
    )
    return {
        'position_summary': f'{len(present)} of {len(impacts)} resource-impact figures recorded: {present}.',
        'confidence': breakdown['final'], 'confidence_breakdown': breakdown,
        'evidence_refs': [f'digital_twin.ModernisationScenario:{scenario.pk}'] if present else [],
        'missing_data': missing, 'risk_flags': [],
    }


def _worker_safety_agent_position(scenario, simulation, assessments, guardrail):
    harm_assessment = next((a for a in assessments if a.kpi.slug == 'worker-community-harm-screen'), None)
    blocking = bool(harm_assessment and harm_assessment.blocking)
    breakdown = _confidence_breakdown(80 if scenario.worker_impact else 20, missing_data_penalty=0 if scenario.worker_impact else 40)
    return {
        'position_summary': harm_assessment.explanation if harm_assessment else 'No worker-harm screen result available.',
        'confidence': breakdown['final'], 'confidence_breakdown': breakdown,
        'evidence_refs': [f'digital_twin.StewardshipAssessment:{harm_assessment.pk}'] if harm_assessment else [],
        'missing_data': [] if scenario.worker_impact else ['worker_impact'],
        'risk_flags': ['worker_harm_signal'] if blocking else [],
    }


def _community_impact_agent_position(scenario, simulation, assessments, guardrail):
    vuln_assessment = next((a for a in assessments if a.kpi.slug == 'community-vulnerability-screen'), None)
    flagged = bool(vuln_assessment and vuln_assessment.warning and vuln_assessment.warning_reason)
    breakdown = _confidence_breakdown(80 if scenario.community_impact else 20, missing_data_penalty=0 if scenario.community_impact else 40)
    return {
        'position_summary': vuln_assessment.explanation if vuln_assessment else 'No community-vulnerability screen result available.',
        'confidence': breakdown['final'], 'confidence_breakdown': breakdown,
        'evidence_refs': [f'digital_twin.StewardshipAssessment:{vuln_assessment.pk}'] if vuln_assessment else [],
        'missing_data': [] if scenario.community_impact else ['community_impact'],
        'risk_flags': ['community_vulnerability_signal'] if flagged else [],
    }


def _evidence_agent_position(scenario, simulation, assessments, guardrail):
    has_evidence = bool(scenario.evidence_references)
    breakdown = _confidence_breakdown(90 if has_evidence else 20, missing_data_penalty=0 if has_evidence else 50)
    return {
        'position_summary': (
            f'{len(scenario.evidence_references or [])} evidence reference(s) attached; '
            f'stated scenario confidence is {scenario.confidence}.'
        ),
        'confidence': breakdown['final'], 'confidence_breakdown': breakdown,
        'evidence_refs': list(scenario.evidence_references or []),
        'missing_data': [] if has_evidence else ['evidence_references for stated confidence'],
        'risk_flags': [],
    }


def _finance_modelling_agent_position(scenario, simulation, assessments, guardrail):
    expected = simulation['cases']['expected']
    npv = expected['npv']['output']
    payback = expected['payback_years']['output']
    known = npv is not None and payback is not None
    breakdown = _confidence_breakdown(70 if known else 25, missing_data_penalty=0 if known else 35)
    missing = list(expected['npv']['missing_inputs']) + list(expected['payback_years']['missing_inputs'])
    return {
        'position_summary': f'Expected case: NPV={npv}, IRR={expected["irr_pct"]["output"]}%, payback={payback} years.',
        'confidence': breakdown['final'], 'confidence_breakdown': breakdown,
        'evidence_refs': [f'digital_twin.ModernisationScenario:{scenario.pk}'],
        'missing_data': missing, 'risk_flags': [],
    }


def _risk_agent_position(scenario, simulation, assessments, guardrail):
    downside = simulation['cases']['downside']
    breakdown = _confidence_breakdown(70, missing_data_penalty=10 if guardrail['verdict'] != 'pass' else 0)
    return {
        'position_summary': (
            f'Downside case NPV={downside["npv"]["output"]}. Guardrail verdict: {guardrail["verdict"]}.'
        ),
        'confidence': breakdown['final'], 'confidence_breakdown': breakdown,
        'evidence_refs': [f'digital_twin.ModernisationScenario:{scenario.pk}'],
        'missing_data': [],
        'risk_flags': [guardrail['verdict']] if guardrail['verdict'] != 'pass' else [],
    }


def _stewardship_agent_position(scenario, simulation, assessments, guardrail):
    scored = [a for a in assessments if a.calculated_score is not None]
    breakdown = _confidence_breakdown(
        round((len(scored) / len(assessments)) * 100, 2) if assessments else 0,
        missing_data_penalty=5 * (len(assessments) - len(scored)),
    )
    return {
        'position_summary': (
            f'{len(scored)}/{len(assessments)} stewardship KPIs scored. Guardrail verdict: {guardrail["verdict"]}. '
            'All seeded KPIs currently ship requires_scholarly_review — not yet approved for authoritative use.'
        ),
        'confidence': breakdown['final'], 'confidence_breakdown': breakdown,
        'evidence_refs': [f'digital_twin.StewardshipAssessment:{a.pk}' for a in assessments],
        'missing_data': [f'{a.kpi.name}: {a.warning_reason}' for a in assessments if a.warning],
        'risk_flags': [guardrail['verdict']] if guardrail['verdict'] in ('block', 'requires_specialist_review') else [],
    }


def _capital_allocation_agent_position(scenario, simulation, assessments, guardrail):
    expected = simulation['cases']['expected']
    breakdown = _confidence_breakdown(60, missing_data_penalty=0)
    return {
        'position_summary': (
            f'Recommends this scenario for governed ranking (annual savings={expected["annual_savings"]["output"]}). '
            'This is a recommendation for Council/human review, never an autonomous investment decision.'
        ),
        'confidence': breakdown['final'], 'confidence_breakdown': breakdown,
        'evidence_refs': [f'digital_twin.ModernisationScenario:{scenario.pk}'],
        'missing_data': [], 'risk_flags': [],
    }


AGENT_POSITION_BUILDERS = {
    'Digital Twin Agent': _digital_twin_agent_position,
    'Engineering Agent': _engineering_agent_position,
    'Energy and Resources Agent': _energy_resources_agent_position,
    'Worker Safety Agent': _worker_safety_agent_position,
    'Community Impact Agent': _community_impact_agent_position,
    'Evidence Agent': _evidence_agent_position,
    'Finance Modelling Agent': _finance_modelling_agent_position,
    'Risk Agent (Governance Agent)': _risk_agent_position,
    'Stewardship Agent': _stewardship_agent_position,
    'Capital Allocation Agent': _capital_allocation_agent_position,
}


def convene_council(scenario):
    """Creates (idempotently, by slug) one CouncilRun with one AgentTask per
    COUNCIL_AGENT_ORDER entry, classifies real disagreements between them
    with the existing deterministic `classify_conflict`, and produces a
    CouncilDecision. Requires `run_stewardship_assessment(scenario)` to have
    already been called (assessments are read, not (re)computed here)."""
    from ai_agent_council.models import AgentTask, CouncilDecision, CouncilDisagreement, CouncilRun
    from ai_agent_council.services.disagreement import classify_conflict

    simulation = scenario_simulation.simulate_scenario(scenario)
    assessments = list(scenario.stewardship_assessments.select_related('kpi'))
    guardrail = guardrails_service.evaluate_guardrails(scenario)

    slug = slugify(f'digital-twin-scenario-{scenario.pk}-{scenario.intervention.title}')[:120]
    run, created = CouncilRun.objects.get_or_create(
        slug=slug,
        defaults={
            'title': f'Digital Twin Review: {scenario.intervention.title}',
            'question': f'Should "{scenario.intervention.title}" proceed for {scenario.twin.asset.name}?',
            'task_category': TASK_CATEGORY,
            'is_simulated': True,
            'selected_agents': [{'agent_name': name, 'selected': True, 'reason': 'Digital Twin scenario review — always convened.'} for name in COUNCIL_AGENT_ORDER],
        },
    )
    if not created:
        run.tasks.all().delete()

    tasks = []
    for order, agent_name in enumerate(COUNCIL_AGENT_ORDER):
        builder = AGENT_POSITION_BUILDERS[agent_name]
        position = builder(scenario, simulation, assessments, guardrail)
        task = AgentTask.objects.create(
            run=run, agent_name=agent_name, collaboration_mode='parallel', status='completed',
            input_summary=f'Review ModernisationScenario #{scenario.pk} ({scenario.intervention.title}).',
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

    opposing_flags = {'block', 'requires_specialist_review', 'requires_evidence'}
    minority_agents = [t.agent_name for t in tasks if opposing_flags & set(t.risk_flags)]
    majority_agents = [t.agent_name for t in tasks if t.agent_name not in minority_agents]

    if guardrail['verdict'] == 'block':
        decision_status = 'rejected'
    elif guardrail['verdict'] in ('requires_specialist_review', 'requires_evidence'):
        decision_status = 'under_review'
    elif guardrail['verdict'] == 'pass_with_warning':
        decision_status = 'approved_with_conditions'
    else:
        decision_status = 'approved'

    avg_confidence = round(sum(t.confidence for t in tasks) / len(tasks), 2) if tasks else None
    decision_breakdown = _confidence_breakdown(
        avg_confidence or 0, missing_data_penalty=10 * len(minority_agents),
    )
    decision, _ = CouncilDecision.objects.update_or_create(
        run=run,
        defaults={
            'status': decision_status,
            'summary': (
                f'{len(tasks)} agents reviewed "{scenario.intervention.title}". Guardrail verdict: '
                f'{guardrail["verdict"]}. {"; ".join(guardrail["reasons"])}'
            ),
            'majority_agents': majority_agents,
            'minority_agents': minority_agents,
            'minority_reason': '; '.join(guardrail['reasons']) if minority_agents else '',
            'conditions': guardrail['reasons'] if guardrail['verdict'] == 'pass_with_warning' else [],
            'confidence': decision_breakdown['final'],
            'confidence_breakdown': decision_breakdown,
            'human_approval_required': True,
            'human_approved': None,
        },
    )
    run.status = 'decided'
    run.save(update_fields=['status', 'updated_at'])

    return {
        'run': run, 'tasks': tasks, 'disagreements': disagreements, 'decision': decision, 'guardrail': guardrail,
    }
