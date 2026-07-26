"""
digital_twin/services/stewardship.py — the Qur'anic Stewardship KPI scoring
engine.

Governance levels, kept strictly separate (never collapsed into one
LLM-generated statement):

    SacredSourceReference   (a citation locator; text left blank pending
                             real scholarly translation)
        -> StewardshipPrinciple (a plain-language principle statement +
                                  operational meaning; `approved_interpretation`
                                  only ever set by a real scholar)
            -> StewardshipKPI   (governed, versioned DEFINITION of a
                                  deterministic formula — documented here,
                                  never LLM-authored)
                -> StewardshipAssessment (one INSTANCE: this module's plain
                                           Python arithmetic against a real
                                           ModernisationScenario)

Every scorer function below is deterministic Python over fields already
stored on the scenario/intervention — no LLM call anywhere in this module.
Every StewardshipKPI seeded by the accompanying data migration ships with
`approval_status='requires_scholarly_review'`: the formulas can exist and be
tested, but are never presented as an approved religious judgement.
"""

HARM_KEYWORDS = {'injury', 'fatality', 'fatalities', 'death', 'displacement', 'exposure', 'harm', 'unsafe'}
VULNERABILITY_KEYWORDS = {'vulnerable', 'indigenous', 'resettlement', 'children', 'displaced', 'marginalised', 'marginalized'}


def _explanation(*lines):
    return ' '.join(lines)


def _text_contains_any(text, keywords):
    lowered = (text or '').lower()
    return sorted(k for k in keywords if k in lowered)


def _score_prevention_of_waste(scenario):
    inputs = {'waste_impact': scenario.waste_impact}
    if scenario.waste_impact is None:
        return {
            'score': None, 'confidence': None, 'warning': True,
            'warning_reason': 'No waste_impact recorded for this scenario — reduction cannot be verified.',
            'blocking': False, 'blocking_reason': '',
            'explanation': 'waste_impact is not set; this KPI requires a direct measurement of waste-quantity change.',
            'input_metrics': inputs,
        }
    score = 100.0 if scenario.waste_impact < 0 else (0.0 if scenario.waste_impact > 0 else 50.0)
    return {
        'score': score, 'confidence': scenario.confidence, 'warning': False, 'warning_reason': '',
        'blocking': False, 'blocking_reason': '',
        'explanation': _explanation(
            f'waste_impact = {scenario.waste_impact} (negative = reduction).',
            f'Score = 100 if reduced, 0 if increased, 50 if unchanged. Result: {score}.',
        ),
        'input_metrics': inputs,
    }


def _score_protection_from_harm(scenario):
    worker_hits = _text_contains_any(scenario.worker_impact, HARM_KEYWORDS)
    community_hits = _text_contains_any(scenario.community_impact, HARM_KEYWORDS)
    inputs = {'worker_impact': scenario.worker_impact, 'community_impact': scenario.community_impact}
    if worker_hits or community_hits:
        return {
            'score': 0.0, 'confidence': scenario.confidence, 'warning': True,
            'warning_reason': 'Harm-related language detected in worker or community impact text.',
            'blocking': True,
            'blocking_reason': f'Harm keywords found: {", ".join(worker_hits + community_hits)}. Requires specialist review before promotion.',
            'explanation': _explanation(
                'Deterministic keyword scan (never an LLM judgement) over worker_impact/community_impact text.',
                f'Matched keywords: {worker_hits + community_hits}.',
            ),
            'input_metrics': inputs,
        }
    documented = bool(scenario.worker_impact or scenario.community_impact)
    return {
        'score': 100.0 if documented else None,
        'confidence': scenario.confidence,
        'warning': not documented,
        'warning_reason': '' if documented else 'Neither worker_impact nor community_impact has been documented for this scenario.',
        'blocking': False, 'blocking_reason': '',
        'explanation': 'No harm keywords found in worker/community impact text.' + ('' if documented else ' Text fields are empty.'),
        'input_metrics': inputs,
    }


def _score_honesty_accurate_measurement(scenario):
    has_evidence = bool(scenario.evidence_references)
    inputs = {'confidence': scenario.confidence, 'evidence_reference_count': len(scenario.evidence_references or [])}
    if scenario.confidence is None:
        return {
            'score': None, 'confidence': None, 'warning': True,
            'warning_reason': 'Scenario has no confidence value — cannot assess measurement honesty.',
            'blocking': False, 'blocking_reason': '', 'explanation': 'confidence is not set.', 'input_metrics': inputs,
        }
    return {
        'score': scenario.confidence, 'confidence': scenario.confidence,
        'warning': not has_evidence,
        'warning_reason': '' if has_evidence else 'No evidence_references recorded — the stated confidence is unverifiable.',
        'blocking': False, 'blocking_reason': '',
        'explanation': f'Score = scenario.confidence directly ({scenario.confidence}). Evidence references: {len(scenario.evidence_references or [])}.',
        'input_metrics': inputs,
    }


def _score_stewardship_of_natural_resources(scenario):
    values = {
        'energy_impact': scenario.energy_impact,
        'water_impact': scenario.water_impact,
        'emissions_impact': scenario.emissions_impact,
    }
    present = {k: v for k, v in values.items() if v is not None}
    if not present:
        return {
            'score': None, 'confidence': None, 'warning': True,
            'warning_reason': 'No energy/water/emissions impact recorded for this scenario.',
            'blocking': False, 'blocking_reason': '', 'explanation': 'No natural-resource impact fields are set.',
            'input_metrics': values,
        }
    reduced = sum(1 for v in present.values() if v < 0)
    score = round((reduced / len(present)) * 100, 2)
    return {
        'score': score, 'confidence': scenario.confidence, 'warning': False, 'warning_reason': '',
        'blocking': False, 'blocking_reason': '',
        'explanation': f'{reduced} of {len(present)} recorded natural-resource impacts are reductions (negative). Score = {score}.',
        'input_metrics': values,
    }


def _score_balance(scenario):
    intervention = scenario.intervention
    payback_months = intervention.estimated_payback_months
    inputs = {'estimated_payback_months': payback_months}
    if payback_months is None:
        return {
            'score': None, 'confidence': None, 'warning': True,
            'warning_reason': 'No payback estimate available — cannot assess cost/benefit balance.',
            'blocking': False, 'blocking_reason': '', 'explanation': 'estimated_payback_months is not set.',
            'input_metrics': inputs,
        }
    score = max(0.0, round(100 - min(100, payback_months / 120 * 100), 2))
    return {
        'score': score, 'confidence': scenario.confidence, 'warning': False, 'warning_reason': '',
        'blocking': False, 'blocking_reason': '',
        'explanation': f'Score = 100 - min(100, payback_months / 120 * 100). payback_months={payback_months} -> {score}.',
        'input_metrics': inputs,
    }


def _score_accountability(scenario):
    fields = {
        'evidence_references': scenario.evidence_references,
        'technical_risks': scenario.technical_risks,
        'dependencies': scenario.dependencies,
        'regulatory_requirements': scenario.regulatory_requirements,
    }
    populated = sum(1 for v in fields.values() if v)
    score = round((populated / len(fields)) * 100, 2)
    return {
        'score': score, 'confidence': scenario.confidence, 'warning': populated < len(fields),
        'warning_reason': '' if populated == len(fields) else 'Some governance-trail fields (evidence, risks, dependencies, regulatory requirements) are empty.',
        'blocking': False, 'blocking_reason': '',
        'explanation': f'{populated} of {len(fields)} accountability-trail fields are populated. Score = {score}.',
        'input_metrics': {k: bool(v) for k, v in fields.items()},
    }


def _score_fair_dealing(scenario):
    has_spec = bool(scenario.technical_specification)
    inputs = {'technical_specification_present': has_spec}
    return {
        'score': 100.0 if has_spec else None,
        'confidence': scenario.confidence, 'warning': not has_spec,
        'warning_reason': '' if has_spec else 'No supplier-neutral technical specification recorded — fair dealing cannot be verified.',
        'blocking': False, 'blocking_reason': '',
        'explanation': 'A documented, reviewable technical specification exists.' if has_spec else 'technical_specification is empty.',
        'input_metrics': inputs,
    }


def _score_protection_of_vulnerable_people(scenario):
    hits = _text_contains_any(scenario.community_impact, VULNERABILITY_KEYWORDS)
    inputs = {'community_impact': scenario.community_impact}
    if hits:
        return {
            'score': 50.0, 'confidence': scenario.confidence, 'warning': True,
            'warning_reason': f'Vulnerability-related language detected in community_impact: {", ".join(hits)}. Requires specialist review.',
            'blocking': False, 'blocking_reason': '',
            'explanation': f'Deterministic keyword scan matched: {hits}. Score set to a neutral 50 pending specialist review, never auto-approved.',
            'input_metrics': inputs,
        }
    return {
        'score': 100.0 if scenario.community_impact else None,
        'confidence': scenario.confidence,
        'warning': not scenario.community_impact,
        'warning_reason': '' if scenario.community_impact else 'community_impact has not been documented.',
        'blocking': False, 'blocking_reason': '', 'explanation': 'No vulnerability-related keywords found.',
        'input_metrics': inputs,
    }


def _score_benefit_to_future_generations(scenario):
    inputs = {'emissions_impact': scenario.emissions_impact}
    if scenario.emissions_impact is None:
        return {
            'score': None, 'confidence': None, 'warning': True,
            'warning_reason': 'No emissions_impact recorded — long-term legacy cannot be assessed.',
            'blocking': False, 'blocking_reason': '', 'explanation': 'emissions_impact is not set.', 'input_metrics': inputs,
        }
    score = 100.0 if scenario.emissions_impact < 0 else (0.0 if scenario.emissions_impact > 0 else 50.0)
    return {
        'score': score, 'confidence': scenario.confidence, 'warning': False, 'warning_reason': '',
        'blocking': False, 'blocking_reason': '',
        'explanation': f'emissions_impact = {scenario.emissions_impact} (negative = reduction). Score = {score}.',
        'input_metrics': inputs,
    }


def _score_justice(scenario):
    documented = [bool(scenario.worker_impact), bool(scenario.community_impact)]
    score = round((sum(documented) / len(documented)) * 100, 2)
    return {
        'score': score, 'confidence': scenario.confidence, 'warning': score < 100,
        'warning_reason': '' if score == 100 else 'Worker and/or community impact has not been documented — distribution of costs/benefits is not fully disclosed.',
        'blocking': False, 'blocking_reason': '',
        'explanation': (
            'This is an operational documentation-completeness indicator, not a religious or moral judgement. '
            f'Worker impact documented: {documented[0]}. Community impact documented: {documented[1]}. Score = {score}.'
        ),
        'input_metrics': {'worker_impact_documented': documented[0], 'community_impact_documented': documented[1]},
    }


KPI_SCORERS = {
    'prevention-of-waste-reduction': _score_prevention_of_waste,
    'worker-community-harm-screen': _score_protection_from_harm,
    'evidence-backed-confidence': _score_honesty_accurate_measurement,
    'net-natural-resource-footprint': _score_stewardship_of_natural_resources,
    'capex-benefit-balance': _score_balance,
    'decision-trail-accountability': _score_accountability,
    'supplier-neutral-specification-check': _score_fair_dealing,
    'community-vulnerability-screen': _score_protection_of_vulnerable_people,
    'long-term-emissions-legacy': _score_benefit_to_future_generations,
    'equitable-impact-disclosure': _score_justice,
}


def run_stewardship_assessment(scenario, kpi_queryset=None):
    """Runs every active, applicable StewardshipKPI's scorer against
    `scenario` and persists one StewardshipAssessment per KPI
    (get_or_create, idempotent — re-running updates the existing row rather
    than accumulating duplicates)."""
    from digital_twin.models import StewardshipAssessment, StewardshipKPI

    kpis = kpi_queryset if kpi_queryset is not None else StewardshipKPI.objects.filter(is_active=True)
    results = []
    for kpi in kpis:
        scorer = KPI_SCORERS.get(kpi.slug)
        if scorer is None:
            continue
        outcome = scorer(scenario)
        assessment, _ = StewardshipAssessment.objects.get_or_create(scenario=scenario, kpi=kpi)
        assessment.input_metrics = outcome['input_metrics']
        assessment.calculated_score = outcome['score']
        assessment.confidence = outcome['confidence']
        assessment.warning = outcome['warning']
        assessment.warning_reason = outcome['warning_reason']
        assessment.blocking = outcome['blocking']
        assessment.blocking_reason = outcome['blocking_reason']
        assessment.explanation = outcome['explanation']
        assessment.formula_version = kpi.formula_version
        assessment.save()
        results.append(assessment)
    return results
