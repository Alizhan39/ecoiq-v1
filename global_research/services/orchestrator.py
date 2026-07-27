"""
global_research/services/orchestrator.py — the idempotent research pipeline.

Responsibilities (per the product spec): validate mission readiness,
generate/load an approved query plan, dispatch searches across every
evidence layer, deduplicate sources, classify source types, extract
structured claims, detect contradictions, evaluate evidence, create
technology/manufacturer/product candidates, run compatibility assessment,
prepare comparative evaluation. Repeated runs never create duplicate
sources, claims, or candidates — every write in this module goes through
an idempotent get_or_create/update_or_create.
"""
import hashlib
import logging

from django.utils import timezone

from global_research.models import RESEARCH_READY_STATUSES
from global_research.providers.registry import all_providers
from global_research.services import (
    claim_extraction, comparison, compatibility, contradiction, discovery, evidence_scoring,
)

logger = logging.getLogger('global_research.orchestrator')


class MissionNotReadyError(Exception):
    """Raised when run_mission() is called for a mission that hasn't been
    approved for research, or has no valid EcoIQ origin."""


def validate_mission_readiness(mission):
    """Returns (ready: bool, errors: list[str]). A mission must originate
    from a real EcoIQ entity and must have been explicitly approved for
    research — never started from a bare prompt or before human approval."""
    errors = []
    if not mission.has_valid_origin:
        errors.append('Mission has no origin EcoIQ entity (asset/twin/component/process/loss/data_gap) — refusing to research an unattributed problem.')
    if mission.status not in RESEARCH_READY_STATUSES:
        errors.append(
            f"Mission status is '{mission.status}' — research can only run once a mission is "
            f"'approved_for_research' or later (approved_by must be set)."
        )
    if mission.status in RESEARCH_READY_STATUSES and not mission.approved_by_id:
        errors.append('Mission is in a research-ready status but has no approved_by user recorded.')
    if not mission.requirements.filter(is_mandatory=True).exists():
        errors.append('Mission has no mandatory TechnicalRequirement — a supplier-neutral requirement set must exist before research runs.')
    return (len(errors) == 0, errors)


def generate_query_plan(mission, keywords=None, languages=None, target_countries=None):
    """A simple, deterministic query-plan builder — a human/Council can
    always author a richer ResearchQueryPlan by hand; this just ensures one
    always exists. Versioned: a later call creates version N+1, never
    silently overwrites an approved plan."""
    from global_research.models import ResearchQueryPlan

    existing_versions = mission.query_plans.count()
    plan = ResearchQueryPlan.objects.create(
        mission=mission,
        research_questions=[f'What technologies/manufacturers can address: {mission.problem_statement[:200]}?'],
        keywords=keywords or ([mission.industry] if mission.industry else []),
        languages=languages or ['en'],
        country_filters=target_countries if target_countries is not None else mission.target_countries,
        source_type_priorities=['regulator_publication', 'independent_test_report', 'peer_reviewed_paper', 'manufacturer_documentation'],
        freshness_requirement='high' if mission.required_evidence_level == 'capital_grade' else 'medium',
        evidence_standard=mission.required_evidence_level,
        generated_by='system',
        version=existing_versions + 1,
    )
    return plan


def _run_idempotency_key(mission, query_plan):
    raw = f'{mission.pk}::{query_plan.pk}::{query_plan.version}'
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def _log(run, event, detail=None):
    run.log = run.log + [{'event': event, 'detail': detail or {}, 'ts': timezone.now().isoformat()}]
    run.save(update_fields=['log', 'updated_at'])


def run_mission(mission, query_plan=None, providers=None):
    """The main entry point. Idempotent: re-running with the same mission +
    query plan version finds and continues the same ResearchRun rather than
    starting a duplicate one, and every downstream write is itself
    idempotent (get_or_create/update_or_create keyed on natural identity)."""
    from global_research.models import ResearchRun

    ready, errors = validate_mission_readiness(mission)
    if not ready:
        raise MissionNotReadyError('; '.join(errors))

    query_plan = query_plan or mission.query_plans.order_by('-version').first() or generate_query_plan(mission)
    providers = providers if providers is not None else all_providers()
    idempotency_key = _run_idempotency_key(mission, query_plan)

    run, created = ResearchRun.objects.get_or_create(
        mission=mission, idempotency_key=idempotency_key,
        defaults={'stage': 'validating'},
    )
    if not created and run.stage == 'completed':
        return run  # already ran to completion for this exact plan version

    mission.status = 'searching'
    mission.save(update_fields=['status', 'updated_at'])
    _log(run, 'mission_started', {'mission_id': mission.pk, 'query_plan_id': query_plan.pk})

    run.stage = 'searching'
    run.save(update_fields=['stage', 'updated_at'])

    technology_candidates_touched = set()
    products_touched = set()

    for provider in providers:
        health = provider.health_check()
        _log(run, 'provider_searched', {'provider': provider.name, 'layer': provider.layer, 'health': health.status})
        try:
            candidates = provider.search(query_plan)
        except Exception as exc:  # noqa: BLE001 — a provider failure must never abort the whole mission
            logger.exception('Provider %s failed', provider.name)
            _log(run, 'provider_failed', {'provider': provider.name, 'error': str(exc)})
            continue

        run.sources_found += len(candidates)
        for candidate in candidates:
            document = provider.fetch(candidate)
            normalised = provider.normalise(document)
            source, source_created = claim_extraction.persist_source(mission, normalised)
            if not source_created:
                run.sources_deduplicated += 1
                _log(run, 'source_deduplicated', {'source_id': source.pk, 'title': source.title})

            claims, rejected = claim_extraction.extract_claims(mission, source, normalised.structured_fields)
            run.claims_extracted += len(claims)
            if rejected:
                _log(run, 'claims_rejected', {'source_id': source.pk, 'count': len(rejected)})
            _log(run, 'source_created' if source_created else 'source_seen', {'source_id': source.pk, 'title': source.title})

            fields = normalised.structured_fields
            category_name = fields.get('technology_category')
            if category_name and claims:
                category = discovery.get_or_create_technology_category(category_name)
                tech_candidate = discovery.create_or_update_technology_candidate(mission, category, category_name, claims)
                technology_candidates_touched.add(tech_candidate.pk)
                run.candidates_created += 1

                manufacturer = discovery.create_or_update_manufacturer(
                    fields.get('manufacturer_name'), fields.get('manufacturer_country'), category,
                )
                if manufacturer and fields.get('product_name'):
                    product = discovery.create_or_update_product(manufacturer, tech_candidate, fields['product_name'], claims)
                    if product:
                        products_touched.add(product.pk)

    run.stage = 'deduplicating'
    run.save(update_fields=['stage', 'sources_found', 'sources_deduplicated', 'claims_extracted', 'candidates_created', 'updated_at'])

    run.stage = 'extracting'
    run.save(update_fields=['stage', 'updated_at'])

    mission.status = 'extracting'
    mission.save(update_fields=['status', 'updated_at'])

    contradictions = contradiction.detect_contradictions(mission)
    run.contradictions_found = len(contradictions)
    for record in contradictions:
        _log(run, 'contradiction_detected', {'id': record.pk, 'type': record.contradiction_type})
    run.save(update_fields=['contradictions_found', 'updated_at'])

    from global_research.models import ResearchClaim

    for claim in ResearchClaim.objects.filter(mission=mission):
        unresolved = contradiction.unresolved_contradiction_count(claim)
        evidence_scoring.score_claim(claim, unresolved_contradiction_count=unresolved)

    run.stage = 'evaluating'
    mission.status = 'evaluating'
    run.save(update_fields=['stage', 'updated_at'])
    mission.save(update_fields=['status', 'updated_at'])

    from global_research.models import ProductCandidate, TechnologyCandidate

    if mission.asset_id:
        for tech_candidate in TechnologyCandidate.objects.filter(pk__in=technology_candidates_touched):
            products = ProductCandidate.objects.filter(technology_candidate=tech_candidate)
            if products.exists():
                for product in products:
                    assessment = compatibility.assess_compatibility(
                        mission, mission.asset, technology_candidate=tech_candidate, product_candidate=product,
                        target_component=mission.component, target_process_node=mission.process_node,
                    )
                    comparison.build_comparative_evaluation(mission, technology_candidate=tech_candidate, product_candidate=product, compatibility_assessment=assessment)
                    if not assessment.mandatory_pass:
                        _log(run, 'compatibility_failed', {'product_id': product.pk, 'failed': assessment.mandatory_requirements_failed})
            else:
                assessment = compatibility.assess_compatibility(mission, mission.asset, technology_candidate=tech_candidate)
                comparison.build_comparative_evaluation(mission, technology_candidate=tech_candidate, compatibility_assessment=assessment)

        comparison.rank_mission_evaluations(mission)

    run.stage = 'completed'
    run.completed_at = timezone.now()
    run.save(update_fields=['stage', 'completed_at', 'updated_at'])

    mission.status = 'ready_for_review'
    mission.save(update_fields=['status', 'updated_at'])
    _log(run, 'mission_completed', {'sources_found': run.sources_found, 'claims_extracted': run.claims_extracted})

    return run
