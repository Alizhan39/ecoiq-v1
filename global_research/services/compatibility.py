"""
global_research/services/compatibility.py — deterministic mandatory/optional
fit engine. A candidate failing ANY mandatory requirement can never be
`mandatory_pass=True`, regardless of what a weighted score would say
elsewhere (docs/adr/ADR-global-research-engine.md decision 7). Output
matches the product spec's exact shape:
{mandatory_pass, failed_requirements, warnings, optional_fit_score,
evidence_quality, overall_status}.
"""
FORMULA_VERSION = '1.0.0'


def _best_claim_for_metric(product_candidate, technology_candidate, metric):
    """The candidate's own highest-confidence claim for this exact metric —
    never inferred from anywhere else, never averaged across candidates."""
    claims_qs = None
    if product_candidate is not None:
        claims_qs = product_candidate.source_claims.filter(predicate=metric)
    elif technology_candidate is not None:
        claims_qs = technology_candidate.source_claims.filter(predicate=metric)
    if claims_qs is None:
        return None
    return claims_qs.exclude(numeric_value=None).order_by('-confidence').first()


def _check_requirement(requirement, product_candidate, technology_candidate):
    claim = _best_claim_for_metric(product_candidate, technology_candidate, requirement.metric)
    if claim is None:
        return 'insufficient_data', None, None
    value = claim.numeric_value
    if requirement.minimum_value is not None and value < requirement.minimum_value:
        return 'fail', value, claim
    if requirement.maximum_value is not None and value > requirement.maximum_value:
        return 'fail', value, claim
    return 'pass', value, claim


def assess_compatibility(mission, target_asset, technology_candidate=None, product_candidate=None,
                          target_component=None, target_process_node=None):
    """Idempotent (update_or_create keyed on mission+candidate+asset)."""
    from global_research.models import CompatibilityAssessment

    requirements = list(mission.requirements.exclude(metric=''))
    mandatory_passed, mandatory_failed, optional_passed = [], [], []
    blocking_issues, warnings, evidence_refs = [], [], []
    evidence_scores = []

    for req in requirements:
        status, value, claim = _check_requirement(req, product_candidate, technology_candidate)
        label = f'{req.get_requirement_type_display()}: {req.description[:80]}'
        if status == 'pass':
            (mandatory_passed if req.is_mandatory else optional_passed).append(label)
            if claim is not None:
                evidence_refs.append(f'global_research.ResearchClaim:{claim.pk}')
                if claim.confidence is not None:
                    evidence_scores.append(claim.confidence)
        elif status == 'fail':
            target = req.minimum_value if req.minimum_value is not None else req.maximum_value
            detail = f'{label} — required {target}, found {value}.'
            if req.is_mandatory:
                mandatory_failed.append(label)
                blocking_issues.append(detail)
            else:
                warnings.append(detail)
        else:  # insufficient_data
            warnings.append(f'{label} — no evidence found for this requirement.')
            if req.is_mandatory:
                mandatory_failed.append(f'{label} (insufficient data)')

    mandatory_requirement_count = sum(1 for r in requirements if r.is_mandatory)
    mandatory_pass = mandatory_requirement_count > 0 and len(mandatory_failed) == 0

    total_optional = sum(1 for r in requirements if not r.is_mandatory)
    optional_fit_score = round((len(optional_passed) / total_optional) * 100, 2) if total_optional else None
    evidence_quality = round(sum(evidence_scores) / len(evidence_scores), 2) if evidence_scores else None

    if mandatory_requirement_count == 0:
        overall_status = 'insufficient_data'
    elif not mandatory_pass:
        overall_status = 'incompatible'
    elif optional_fit_score is None or optional_fit_score >= 50:
        overall_status = 'compatible'
    else:
        overall_status = 'conditional'

    assessment_score = (optional_fit_score if optional_fit_score is not None else 100.0) if mandatory_pass else None

    defaults = dict(
        mandatory_requirements_passed=mandatory_passed, mandatory_requirements_failed=mandatory_failed,
        optional_requirements_passed=optional_passed, mandatory_pass=mandatory_pass,
        optional_fit_score=optional_fit_score, evidence_quality=evidence_quality, overall_status=overall_status,
        assessment_score=assessment_score, confidence=evidence_quality, blocking_issues=blocking_issues,
        warnings=warnings, evidence_references=evidence_refs, formula_version=FORMULA_VERSION,
        target_component=target_component, target_process_node=target_process_node,
    )
    assessment, _ = CompatibilityAssessment.objects.update_or_create(
        mission=mission, technology_candidate=technology_candidate, product_candidate=product_candidate,
        target_asset=target_asset, defaults=defaults,
    )
    return assessment
