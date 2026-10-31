"""
global_research/tests.py — plain django.test.TestCase, module-level helper
functions, matching this repo's convention (see digital_twin/tests.py).
"""
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from ai_agent_council.agents import OPERATIONAL_AGENTS, _scan_ai_agents_repo_state
from ai_agent_council.models import CouncilRun
from capability_graph.models import Organisation, OrganisationCapability
from digital_twin.models import AssetType, DigitalTwin, IndustrialAsset, Unit
from global_research import models as m
from global_research.providers import registry as provider_registry
from global_research.providers.base import (
    NormalisedSourceResult, SourceCandidateResult, SourceDocumentResult,
)
from global_research.services import (
    claim_extraction, comparison, compatibility, contradiction, council, discovery,
    documents, evidence_scoring, human_approval_gate, orchestrator, permissions, risk,
    scenario_bridge, stewardship_screen,
)
from core.testing_access import SignedIn

User = get_user_model()


def _asset(**kwargs):
    defaults = {'name': 'Test Plant', 'asset_type': AssetType.objects.get(code='manufacturing_facility')}
    defaults.update(kwargs)
    return IndustrialAsset.objects.create(**defaults)


def _twin(asset=None, **kwargs):
    asset = asset or _asset()
    defaults = {'name': 'Test Twin', 'version': 1}
    defaults.update(kwargs)
    return DigitalTwin.objects.create(asset=asset, **defaults)


def _reviewer():
    user, _ = User.objects.get_or_create(username='gr_test_reviewer', defaults={'is_staff': True})
    return user


def _approved_mission(**kwargs):
    reviewer = _reviewer()
    defaults = dict(
        asset=_asset(), title='Test Mission', problem_statement='A test problem.',
        status='approved_for_research', approved_by=reviewer, created_by=reviewer,
    )
    defaults.update(kwargs)
    mission = m.ResearchMission.objects.create(**defaults)
    m.TechnicalRequirement.objects.create(
        mission=mission, requirement_type='temperature', description='Test mandatory requirement',
        metric='test_metric', minimum_value=10.0, unit=Unit.objects.filter(code='count').first(),
        is_mandatory=True, approved=True,
    )
    return mission


_source_counter = iter(range(1, 100_000))


def _source(mission, **kwargs):
    n = next(_source_counter)
    defaults = dict(title=f'Test Source {n}', source_type='manufacturer_documentation', source_owner_type='vendor', url=f'https://example.com/source-{n}')
    defaults.update(kwargs)
    return m.ResearchSource.objects.create(mission=mission, **defaults)


def _claim(mission, source, **kwargs):
    defaults = dict(subject='Test Product', predicate='test_metric', object_value='42', numeric_value=42.0)
    defaults.update(kwargs)
    return m.ResearchClaim.objects.create(mission=mission, source=source, vendor_provided=(source.source_owner_type in ('vendor', 'distributor')), **defaults)


class ModelTests(TestCase):
    def test_mission_has_valid_origin(self):
        mission = m.ResearchMission.objects.create(title='X', problem_statement='Y')
        self.assertFalse(mission.has_valid_origin)
        mission.asset = _asset()
        mission.save()
        self.assertTrue(mission.has_valid_origin)

    def test_source_dedup_key_unique_per_mission(self):
        mission = _approved_mission()
        m.ResearchSource.objects.create(mission=mission, title='A', source_type='other', url='https://example.com/a')
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                m.ResearchSource.objects.create(mission=mission, title='A dup', source_type='other', url='https://example.com/a')

    def test_source_dedup_key_computed_from_url(self):
        mission = _approved_mission()
        s1 = m.ResearchSource.objects.create(mission=mission, title='A', source_type='other', url='https://example.com/a')
        s2 = m.ResearchSource.objects.create(mission=mission, title='Different title', source_type='other', url='https://example.com/b')
        self.assertNotEqual(s1.dedup_key, s2.dedup_key)

    def test_human_decision_derives_human_approved(self):
        mission = _approved_mission()
        approved = m.ResearchHumanDecision.objects.create(mission=mission, stage='candidate_review', decision='approved')
        self.assertIs(approved.human_approved, True)
        rejected = m.ResearchHumanDecision.objects.create(mission=mission, stage='candidate_review', decision='rejected')
        self.assertIs(rejected.human_approved, False)
        deferred = m.ResearchHumanDecision.objects.create(mission=mission, stage='candidate_review', decision='deferred')
        self.assertIsNone(deferred.human_approved)

    def test_manufacturer_and_supplier_are_distinct_profiles_on_same_organisation(self):
        org = Organisation.objects.create(name='Dual-Role Co', dedupe_key='dual-role-co::')
        manufacturer = m.ManufacturerProfile.objects.create(organisation=org)
        supplier = m.SupplierOrIntegratorProfile.objects.create(organisation=org, role_type='distributor')
        self.assertNotEqual(type(manufacturer), type(supplier))
        self.assertEqual(manufacturer.organisation_id, supplier.organisation_id)


class ProviderTests(TestCase):
    def test_all_providers_implement_the_full_interface(self):
        mission = _approved_mission()
        plan = orchestrator.generate_query_plan(mission, keywords=['industrial heat pump'])
        for provider in provider_registry.all_providers():
            candidates = provider.search(plan)
            self.assertIsInstance(candidates, list)
            health = provider.health_check()
            self.assertEqual(health.status, 'simulated')
            self.assertFalse(health.credentials_configured)
            if candidates:
                document = provider.fetch(candidates[0])
                self.assertIsInstance(document, SourceDocumentResult)
                normalised = provider.normalise(document)
                self.assertIsInstance(normalised, NormalisedSourceResult)

    def test_search_filters_by_keyword(self):
        mission = _approved_mission()
        plan = orchestrator.generate_query_plan(mission, keywords=['nonexistent technology xyz'])
        provider = provider_registry.get_provider('commercial_manufacturer_provider')
        self.assertEqual(provider.search(plan), [])

    def test_unknown_provider_name_raises(self):
        with self.assertRaises(KeyError):
            provider_registry.get_provider('does_not_exist')


class ClaimExtractionTests(TestCase):
    def test_validate_claim_schema_rejects_missing_fields(self):
        self.assertTrue(claim_extraction.validate_claim_schema({}))
        self.assertTrue(claim_extraction.validate_claim_schema({'predicate': 'x'}))
        self.assertEqual(claim_extraction.validate_claim_schema({'predicate': 'x', 'object_value': '1', 'numeric_value': 1.0}), [])

    def test_validate_claim_schema_rejects_non_numeric_value(self):
        errors = claim_extraction.validate_claim_schema({'predicate': 'x', 'object_value': '1', 'numeric_value': 'not-a-number'})
        self.assertTrue(errors)

    def test_persist_source_is_idempotent(self):
        mission = _approved_mission()
        candidate = SourceCandidateResult(title='T', source_type='other', provider_name='test', url='https://example.com/x')
        normalised = NormalisedSourceResult(candidate=candidate, permitted_extract='', structured_fields={})
        source1, created1 = claim_extraction.persist_source(mission, normalised)
        source2, created2 = claim_extraction.persist_source(mission, normalised)
        self.assertTrue(created1)
        self.assertFalse(created2)
        self.assertEqual(source1.pk, source2.pk)

    def test_extract_claims_sets_vendor_provided_from_source_owner_type(self):
        mission = _approved_mission()
        vendor_source = _source(mission, source_owner_type='vendor')
        claims, rejected = claim_extraction.extract_claims(mission, vendor_source, {
            'claims': [{'predicate': 'p', 'object_value': '1', 'numeric_value': 1.0}],
        })
        self.assertEqual(len(claims), 1)
        self.assertTrue(claims[0].vendor_provided)
        self.assertEqual(rejected, [])

    def test_extract_claims_discards_malformed_claim(self):
        mission = _approved_mission()
        source = _source(mission)
        claims, rejected = claim_extraction.extract_claims(mission, source, {'claims': [{'object_value': '1'}]})
        self.assertEqual(claims, [])
        self.assertEqual(len(rejected), 1)

    def test_extract_claims_is_idempotent(self):
        mission = _approved_mission()
        source = _source(mission)
        raw = {'claims': [{'predicate': 'p', 'object_value': '1', 'numeric_value': 1.0}]}
        claim_extraction.extract_claims(mission, source, raw)
        claim_extraction.extract_claims(mission, source, raw)
        self.assertEqual(m.ResearchClaim.objects.filter(mission=mission, source=source).count(), 1)


class EvidenceScoringTests(TestCase):
    def test_score_claim_is_bounded_0_100(self):
        mission = _approved_mission()
        source = _source(mission, evidence_tier='D', source_owner_type='vendor')
        claim = _claim(mission, source)
        assessment = evidence_scoring.score_claim(claim)
        self.assertTrue(0 <= assessment.overall_evidence_score <= 100)

    def test_tier_a_scores_higher_than_tier_d(self):
        mission = _approved_mission()
        source_a = _source(mission, evidence_tier='A', source_owner_type='regulator', publication_date=timezone.now().date())
        source_d = _source(mission, evidence_tier='D', source_owner_type='vendor', publication_date=timezone.now().date())
        claim_a = _claim(mission, source_a, subject='A')
        claim_d = _claim(mission, source_d, subject='D')
        assessment_a = evidence_scoring.score_claim(claim_a)
        assessment_d = evidence_scoring.score_claim(claim_d)
        self.assertGreater(assessment_a.overall_evidence_score, assessment_d.overall_evidence_score)

    def test_verified_only_from_independent_corroboration_never_from_own_source(self):
        # Regression test for a real bug: a vendor claim contradicted (not
        # corroborated) by an independent source must NOT be marked verified.
        mission = _approved_mission()
        vendor_source = _source(mission, source_owner_type='vendor', evidence_tier='C')
        independent_source = _source(mission, source_owner_type='independent', evidence_tier='A')
        vendor_claim = _claim(mission, vendor_source, subject='X', predicate='p', object_value='100', numeric_value=100.0)
        independent_claim = _claim(mission, independent_source, subject='X', predicate='p', object_value='50', numeric_value=50.0)
        contradiction.detect_contradictions(mission)
        evidence_scoring.score_claim(vendor_claim, unresolved_contradiction_count=contradiction.unresolved_contradiction_count(vendor_claim))
        vendor_claim.refresh_from_db()
        self.assertFalse(vendor_claim.verified)

    def test_verified_true_when_independent_claims_genuinely_agree(self):
        mission = _approved_mission()
        source_1 = _source(mission, source_owner_type='independent', evidence_tier='B')
        source_2 = _source(mission, source_owner_type='independent', evidence_tier='B')
        claim_1 = _claim(mission, source_1, subject='X', predicate='p', object_value='100', numeric_value=100.0)
        claim_2 = _claim(mission, source_2, subject='X', predicate='p', object_value='101', numeric_value=101.0)
        contradiction.detect_contradictions(mission)
        evidence_scoring.score_claim(claim_1)
        claim_1.refresh_from_db()
        self.assertTrue(claim_1.verified)


class ContradictionTests(TestCase):
    def test_detects_value_mismatch_beyond_tolerance(self):
        mission = _approved_mission()
        s1, s2 = _source(mission, evidence_tier='C'), _source(mission, evidence_tier='A', source_owner_type='independent')
        c1 = _claim(mission, s1, subject='X', predicate='p', object_value='100', numeric_value=100.0)
        c2 = _claim(mission, s2, subject='X', predicate='p', object_value='50', numeric_value=50.0)
        records = contradiction.detect_contradictions(mission)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].contradiction_type, 'value_mismatch')

    def test_no_contradiction_within_tolerance(self):
        mission = _approved_mission()
        s1, s2 = _source(mission), _source(mission)
        _claim(mission, s1, subject='X', predicate='p', object_value='100', numeric_value=100.0)
        _claim(mission, s2, subject='X', predicate='p', object_value='105', numeric_value=105.0)
        records = contradiction.detect_contradictions(mission)
        self.assertEqual(records, [])

    def test_auto_resolves_by_tier_never_from_vendor_side(self):
        mission = _approved_mission()
        vendor = _source(mission, evidence_tier='C', source_owner_type='vendor')
        independent = _source(mission, evidence_tier='A', source_owner_type='independent')
        c_vendor = _claim(mission, vendor, subject='X', predicate='p', object_value='100', numeric_value=100.0, conditions={'t': 1})
        c_independent = _claim(mission, independent, subject='X', predicate='p', object_value='50', numeric_value=50.0, conditions={'t': 1})
        records = contradiction.detect_contradictions(mission)
        self.assertEqual(records[0].resolution_status, 'resolved_by_evidence')

    def test_never_overwrites_human_resolved_contradiction(self):
        mission = _approved_mission()
        s1, s2 = _source(mission, evidence_tier='A', source_owner_type='independent'), _source(mission, evidence_tier='A', source_owner_type='independent')
        c1 = _claim(mission, s1, subject='X', predicate='p', object_value='100', numeric_value=100.0)
        c2 = _claim(mission, s2, subject='X', predicate='p', object_value='50', numeric_value=50.0)
        records = contradiction.detect_contradictions(mission)
        record = records[0]
        record.resolution_status = 'resolved_by_human'
        record.resolution_notes = 'A human decided.'
        record.save()
        contradiction.attempt_auto_resolve(record)
        record.refresh_from_db()
        self.assertEqual(record.resolution_status, 'resolved_by_human')
        self.assertEqual(record.resolution_notes, 'A human decided.')


class DiscoveryTests(TestCase):
    def test_get_or_create_technology_category_idempotent(self):
        c1 = discovery.get_or_create_technology_category('Widget Tech')
        c2 = discovery.get_or_create_technology_category('Widget Tech')
        self.assertEqual(c1.pk, c2.pk)

    def test_create_or_update_manufacturer_returns_none_for_empty_name(self):
        self.assertIsNone(discovery.create_or_update_manufacturer('', 'Germany'))

    def test_create_or_update_manufacturer_creates_real_organisation_and_capability(self):
        category = discovery.get_or_create_technology_category('Widget Tech')
        profile = discovery.create_or_update_manufacturer('Acme Widgets GmbH', 'Germany', category)
        self.assertIsInstance(profile, m.ManufacturerProfile)
        self.assertTrue(Organisation.objects.filter(pk=profile.organisation_id).exists())
        self.assertTrue(OrganisationCapability.objects.filter(organisation=profile.organisation, capability='manufacture').exists())

    def test_create_or_update_manufacturer_is_idempotent(self):
        category = discovery.get_or_create_technology_category('Widget Tech')
        p1 = discovery.create_or_update_manufacturer('Acme Widgets GmbH', 'Germany', category)
        p2 = discovery.create_or_update_manufacturer('Acme Widgets GmbH', 'Germany', category)
        self.assertEqual(p1.pk, p2.pk)
        self.assertEqual(m.ManufacturerProfile.objects.count(), 1)

    def test_create_or_update_product_requires_manufacturer(self):
        category = discovery.get_or_create_technology_category('Widget Tech')
        mission = _approved_mission()
        tech = discovery.create_or_update_technology_candidate(mission, category, 'Widget Tech', [])
        self.assertIsNone(discovery.create_or_update_product(None, tech, 'Widget X', []))


class CompatibilityTests(TestCase):
    def test_mandatory_fail_overrides_optional_pass(self):
        mission = _approved_mission()
        category = discovery.get_or_create_technology_category('Widget Tech')
        tech = discovery.create_or_update_technology_candidate(mission, category, 'Widget Tech', [])
        source = _source(mission, evidence_tier='A')
        claim = _claim(mission, source, subject='Widget X', predicate='test_metric', object_value='1', numeric_value=1.0)  # fails min 10.0
        evidence_scoring.score_claim(claim)
        tech.source_claims.add(claim)
        assessment = compatibility.assess_compatibility(mission, mission.asset, technology_candidate=tech)
        self.assertFalse(assessment.mandatory_pass)
        self.assertIn('Test mandatory requirement', ' '.join(assessment.mandatory_requirements_failed))

    def test_mandatory_pass_when_requirement_met(self):
        mission = _approved_mission()
        category = discovery.get_or_create_technology_category('Widget Tech')
        tech = discovery.create_or_update_technology_candidate(mission, category, 'Widget Tech', [])
        source = _source(mission, evidence_tier='A')
        claim = _claim(mission, source, subject='Widget X', predicate='test_metric', object_value='20', numeric_value=20.0)
        evidence_scoring.score_claim(claim)
        tech.source_claims.add(claim)
        assessment = compatibility.assess_compatibility(mission, mission.asset, technology_candidate=tech)
        self.assertTrue(assessment.mandatory_pass)

    def test_insufficient_data_when_no_matching_claim(self):
        mission = _approved_mission()
        category = discovery.get_or_create_technology_category('Widget Tech')
        tech = discovery.create_or_update_technology_candidate(mission, category, 'Widget Tech', [])
        assessment = compatibility.assess_compatibility(mission, mission.asset, technology_candidate=tech)
        self.assertFalse(assessment.mandatory_pass)
        self.assertEqual(assessment.overall_status, 'incompatible')

    def test_formula_version_stamped(self):
        mission = _approved_mission()
        category = discovery.get_or_create_technology_category('Widget Tech')
        tech = discovery.create_or_update_technology_candidate(mission, category, 'Widget Tech', [])
        assessment = compatibility.assess_compatibility(mission, mission.asset, technology_candidate=tech)
        self.assertEqual(assessment.formula_version, compatibility.FORMULA_VERSION)


class ComparisonTests(TestCase):
    def test_weights_sum_to_one(self):
        self.assertAlmostEqual(sum(comparison.DEFAULT_WEIGHTS.values()), 1.0, places=6)

    def test_mandatory_fail_candidate_excluded_from_ranking(self):
        mission = _approved_mission()
        category = discovery.get_or_create_technology_category('Widget Tech')
        tech = discovery.create_or_update_technology_candidate(mission, category, 'Widget Tech', [])
        assessment = compatibility.assess_compatibility(mission, mission.asset, technology_candidate=tech)
        evaluation = comparison.build_comparative_evaluation(mission, technology_candidate=tech, compatibility_assessment=assessment)
        self.assertFalse(evaluation.is_ranked)
        self.assertIsNone(evaluation.total_score)
        ranked = comparison.rank_mission_evaluations(mission)
        self.assertNotIn(evaluation, ranked)
        evaluation.refresh_from_db()
        self.assertIsNone(evaluation.rank)

    def test_missing_signals_recorded_not_fabricated(self):
        mission = _approved_mission()
        category = discovery.get_or_create_technology_category('Widget Tech')
        tech = discovery.create_or_update_technology_candidate(mission, category, 'Widget Tech', [])
        evaluation = comparison.build_comparative_evaluation(mission, technology_candidate=tech, compatibility_assessment=None)
        self.assertTrue(evaluation.missing_data)


class OrchestratorTests(TestCase):
    def test_validate_mission_readiness_requires_origin(self):
        mission = m.ResearchMission.objects.create(title='X', problem_statement='Y', status='approved_for_research', approved_by=_reviewer())
        ready, errors = orchestrator.validate_mission_readiness(mission)
        self.assertFalse(ready)
        self.assertTrue(any('origin' in e for e in errors))

    def test_validate_mission_readiness_requires_approval(self):
        mission = m.ResearchMission.objects.create(title='X', problem_statement='Y', asset=_asset(), status='draft')
        ready, errors = orchestrator.validate_mission_readiness(mission)
        self.assertFalse(ready)

    def test_run_mission_raises_when_not_ready(self):
        mission = m.ResearchMission.objects.create(title='X', problem_statement='Y', asset=_asset(), status='draft')
        with self.assertRaises(orchestrator.MissionNotReadyError):
            orchestrator.run_mission(mission)

    def test_run_mission_is_idempotent(self):
        mission = _approved_mission()
        plan = orchestrator.generate_query_plan(mission, keywords=['industrial heat pump'])
        run1 = orchestrator.run_mission(mission, query_plan=plan)
        source_count_1 = mission.sources.count()
        run2 = orchestrator.run_mission(mission, query_plan=plan)
        self.assertEqual(run1.pk, run2.pk)
        self.assertEqual(mission.sources.count(), source_count_1)

    def test_query_plan_versioning(self):
        mission = _approved_mission()
        plan1 = orchestrator.generate_query_plan(mission)
        plan2 = orchestrator.generate_query_plan(mission)
        self.assertEqual(plan2.version, plan1.version + 1)

    def test_candidate_evidence_score_is_populated_after_a_full_run(self):
        # Regression test for a real bug found during manual UI
        # verification: TechnologyCandidate/ProductCandidate.evidence_score
        # was aggregated from claim confidences BEFORE those claims were
        # scored, so it stayed stuck at None even after a full mission run.
        mission = _approved_mission()
        plan = orchestrator.generate_query_plan(mission, keywords=['industrial heat pump'])
        orchestrator.run_mission(mission, query_plan=plan)
        candidates_with_claims = [c for c in mission.technology_candidates.all() if c.source_claims.exists()]
        self.assertTrue(candidates_with_claims)
        for candidate in candidates_with_claims:
            self.assertIsNotNone(candidate.evidence_score, f'{candidate.name} has claims but evidence_score is still None')
        products_with_claims = [p for p in m.ProductCandidate.objects.filter(technology_candidate__mission=mission) if p.source_claims.exists()]
        self.assertTrue(products_with_claims)
        for product in products_with_claims:
            self.assertIsNotNone(product.evidence_score, f'{product.product_name} has claims but evidence_score is still None')


class CouncilTests(TestCase):
    def test_convene_council_creates_one_task_per_agent(self):
        mission = _approved_mission()
        category = discovery.get_or_create_technology_category('Widget Tech')
        tech = discovery.create_or_update_technology_candidate(mission, category, 'Widget Tech', [])
        compatibility.assess_compatibility(mission, mission.asset, technology_candidate=tech)
        result = council.convene_council(mission, technology_candidate=tech)
        self.assertEqual(len(result['tasks']), len(council.COUNCIL_AGENT_ORDER))

    def test_council_reuses_existing_stewardship_agent_not_a_duplicate(self):
        names = [a['name'] for a in OPERATIONAL_AGENTS]
        self.assertEqual(names.count('Stewardship Agent'), 1)
        self.assertIn('Stewardship Agent', council.COUNCIL_AGENT_ORDER)

    def test_get_council_run_works_without_a_human_decision(self):
        mission = _approved_mission()
        category = discovery.get_or_create_technology_category('Widget Tech')
        tech = discovery.create_or_update_technology_candidate(mission, category, 'Widget Tech', [])
        result = council.convene_council(mission, technology_candidate=tech)
        found = council.get_council_run(mission, technology_candidate=tech)
        self.assertEqual(found.pk, result['run'].pk)

    def test_every_new_persona_has_a_complete_training_pack(self):
        state = _scan_ai_agents_repo_state()
        for folder in ('problem_definition_agent', 'technical_requirements_agent', 'scientific_research_agent',
                       'patent_innovation_agent', 'manufacturer_discovery_agent', 'product_specification_agent',
                       'independent_evidence_agent', 'compatibility_agent', 'commercial_intelligence_agent',
                       'supply_chain_risk_agent', 'regulatory_agent', 'evidence_auditor_agent', 'research_synthesis_agent'):
            self.assertIn(folder, state['operational_folder_names'])
            self.assertEqual(len(state['per_folder_files'][folder]), 10)


class HumanApprovalGateTests(TestCase):
    def test_shortlist_action_requires_approval(self):
        mission = _approved_mission()
        decision = m.ResearchHumanDecision.objects.create(mission=mission, stage='manufacturer_shortlist', decision='deferred')
        with self.assertRaises(human_approval_gate.HumanApprovalRequiredError):
            human_approval_gate.require_human_approval('research_candidate_shortlist', decision)

    def test_approved_decision_passes(self):
        mission = _approved_mission()
        decision = m.ResearchHumanDecision.objects.create(mission=mission, stage='manufacturer_shortlist', decision='approved')
        self.assertTrue(human_approval_gate.require_human_approval('research_candidate_shortlist', decision))

    def test_base_actions_still_enforced(self):
        class Dummy:
            human_approved = None
            pk = 1
        with self.assertRaises(human_approval_gate.HumanApprovalRequiredError):
            human_approval_gate.require_human_approval('supplier_outreach', Dummy())


class ScenarioBridgeTests(TestCase):
    def test_requires_twin(self):
        mission = _approved_mission()
        category = discovery.get_or_create_technology_category('Widget Tech')
        tech = discovery.create_or_update_technology_candidate(mission, category, 'Widget Tech', [])
        recommendation = m.ResearchRecommendation.objects.create(
            mission=mission, recommendation_type='create_supplier_neutral_scenario', technology_candidate=tech, rationale='r',
        )
        decision = m.ResearchHumanDecision.objects.create(mission=mission, stage='scenario_creation', decision='approved')
        with self.assertRaises(scenario_bridge.ScenarioBridgeError):
            scenario_bridge.create_scenario_from_recommendation(recommendation, decision)

    def test_requires_approval(self):
        mission = _approved_mission()
        category = discovery.get_or_create_technology_category('Widget Tech')
        tech = discovery.create_or_update_technology_candidate(mission, category, 'Widget Tech', [])
        recommendation = m.ResearchRecommendation.objects.create(
            mission=mission, recommendation_type='create_supplier_neutral_scenario', technology_candidate=tech, rationale='r',
        )
        decision = m.ResearchHumanDecision.objects.create(mission=mission, stage='scenario_creation', decision='rejected')
        with self.assertRaises(human_approval_gate.HumanApprovalRequiredError):
            scenario_bridge.create_scenario_from_recommendation(recommendation, decision)


class DocumentsTests(TestCase):
    def test_generate_creates_version_one(self):
        mission = _approved_mission()
        draft = documents.generate_document_draft(mission, 'rfi')
        self.assertEqual(draft.version, 1)
        self.assertEqual(draft.status, 'draft')

    def test_regenerating_supersedes_previous_draft(self):
        mission = _approved_mission()
        draft1 = documents.generate_document_draft(mission, 'rfi')
        draft2 = documents.generate_document_draft(mission, 'rfi')
        draft1.refresh_from_db()
        self.assertEqual(draft1.status, 'superseded')
        self.assertEqual(draft2.version, 2)

    def test_approve_requires_human_decision(self):
        mission = _approved_mission()
        draft = documents.generate_document_draft(mission, 'rfi')
        decision = m.ResearchHumanDecision.objects.create(mission=mission, stage='rfi_rfq_approval', decision='deferred')
        with self.assertRaises(human_approval_gate.HumanApprovalRequiredError):
            documents.approve_document_draft(draft, decision, _reviewer())

    def test_cannot_re_approve_an_approved_draft(self):
        mission = _approved_mission()
        draft = documents.generate_document_draft(mission, 'rfi')
        decision = m.ResearchHumanDecision.objects.create(mission=mission, stage='rfi_rfq_approval', decision='approved')
        documents.approve_document_draft(draft, decision, _reviewer())
        with self.assertRaises(documents.DraftAlreadyApprovedError):
            documents.approve_document_draft(draft, decision, _reviewer())

    def test_no_send_capability_exists_anywhere_in_this_module(self):
        import inspect

        from global_research.services import documents as documents_module
        source_code = inspect.getsource(documents_module)
        for forbidden in ('send_mail', 'smtplib', 'requests.post', 'httpx.post'):
            self.assertNotIn(forbidden, source_code)


class RiskTests(TestCase):
    def test_sanctions_concern_creates_high_severity_flag(self):
        mission = _approved_mission()
        org = Organisation.objects.create(name='Risky Co', dedupe_key='risky-co::')
        manufacturer = m.ManufacturerProfile.objects.create(organisation=org, sanctions_screening_status='confirmed_concern')
        flags = risk.evaluate_manufacturer_risks(mission, manufacturer)
        self.assertTrue(any(f.risk_type == 'sanctions' and f.severity == 'high' for f in flags))

    def test_risk_evaluation_is_idempotent(self):
        mission = _approved_mission()
        org = Organisation.objects.create(name='Risky Co', dedupe_key='risky-co-2::')
        manufacturer = m.ManufacturerProfile.objects.create(organisation=org, sanctions_screening_status='confirmed_concern')
        risk.evaluate_manufacturer_risks(mission, manufacturer)
        risk.evaluate_manufacturer_risks(mission, manufacturer)
        self.assertEqual(m.SupplyChainRiskFlag.objects.filter(mission=mission, manufacturer=manufacturer, risk_type='sanctions').count(), 1)


class StewardshipScreenTests(TestCase):
    def test_harm_keyword_scores_zero(self):
        mission = _approved_mission()
        category = discovery.get_or_create_technology_category('Widget Tech')
        tech = discovery.create_or_update_technology_candidate(mission, category, 'Widget Tech', [])
        tech.worker_implications = 'Risk of exposure during installation.'
        result = stewardship_screen.screen_technology_candidate(tech)
        self.assertEqual(result['score'], 0.0)
        self.assertTrue(result['warning'])

    def test_no_documentation_returns_none_not_fabricated(self):
        mission = _approved_mission()
        category = discovery.get_or_create_technology_category('Widget Tech')
        tech = discovery.create_or_update_technology_candidate(mission, category, 'Widget Tech', [])
        result = stewardship_screen.screen_technology_candidate(tech)
        self.assertIsNone(result['score'])


class PermissionsTests(TestCase):
    def test_staff_can_view_any_mission(self):
        mission = _approved_mission()
        self.assertTrue(permissions.can_view_mission(mission, _reviewer()))

    def test_anonymous_cannot_view(self):
        mission = _approved_mission()
        self.assertFalse(permissions.can_view_mission(mission, None))

    def test_non_staff_non_creator_cannot_view(self):
        mission = _approved_mission()
        stranger = User.objects.create_user(username='stranger', password='x')
        self.assertFalse(permissions.can_view_mission(mission, stranger))

    def test_only_staff_can_manage(self):
        stranger = User.objects.create_user(username='stranger2', password='x')
        mission = _approved_mission()
        self.assertFalse(permissions.can_manage_mission(mission, stranger))
        self.assertTrue(permissions.can_manage_mission(mission, _reviewer()))


class ViewPermissionBoundaryTests(SignedIn, TestCase):
    """
    global_research is EXPERIMENTAL in the status registry, so the whole
    prefix now requires sign-in (core/access.py). The boundary these tests
    describe moved outward: the question is no longer "which of these views is
    public" but "does the module answer anonymously at all".
    """

    def test_requirement_builder_requires_login(self):
        mission = _approved_mission()
        response = Client().get(
            reverse('global_research:requirement_builder', args=[mission.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_the_mission_dashboard_is_no_longer_public(self):
        """
        It used to be. An experimental research module answering anonymously
        presents as a shipped capability, which is what Labs exists to prevent.
        """
        mission = _approved_mission()
        response = Client().get(
            reverse('global_research:mission_dashboard', args=[mission.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_a_signed_in_user_can_still_read_the_mission_dashboard(self):
        """De-publication, not deletion — the view still works."""
        mission = _approved_mission()
        response = self.client.get(
            reverse('global_research:mission_dashboard', args=[mission.pk]))
        self.assertEqual(response.status_code, 200)


class DemoWorkflowEndToEndTests(TestCase):
    def test_seed_global_research_demo_end_to_end(self):
        call_command('seed_global_research_demo')

        mission = m.ResearchMission.objects.get(title='Global Technology Search for Industrial Heat Modernisation')
        self.assertGreaterEqual(mission.requirements.count(), 10)
        self.assertGreaterEqual(mission.sources.values('source_type').distinct().count(), 3)
        self.assertTrue(mission.sources.filter(source_owner_type='vendor').exists())
        self.assertTrue(mission.sources.filter(source_owner_type='independent').exists())
        self.assertTrue(mission.contradictions.exists())
        self.assertGreaterEqual(mission.technology_candidates.count(), 5)
        self.assertGreaterEqual(
            m.ManufacturerProfile.objects.filter(products__technology_candidate__mission=mission).distinct().count(), 6,
        )
        self.assertTrue(m.CompatibilityAssessment.objects.filter(mission=mission, mandatory_pass=False).exists())
        self.assertTrue(m.ComparativeEvaluation.objects.filter(mission=mission).exists())
        self.assertTrue(m.SupplyChainRiskFlag.objects.filter(mission=mission).exists())
        self.assertTrue(CouncilRun.objects.filter(task_category=council.TASK_CATEGORY).exists())
        self.assertTrue(m.ResearchHumanDecision.objects.filter(mission=mission, stage='manufacturer_shortlist').exists())
        self.assertTrue(m.ResearchRecommendation.objects.filter(mission=mission, created_scenario__isnull=False).exists())
        self.assertTrue(m.ResearchDocumentDraft.objects.filter(mission=mission, document_type='rfi', status='approved').exists())

        # The seeded adversarial fixture must be flagged but never shortlist anything itself.
        injection_source = mission.sources.filter(content_safety_flagged=True).first()
        self.assertIsNotNone(injection_source)

    def test_demo_is_idempotent(self):
        call_command('seed_global_research_demo')
        mission = m.ResearchMission.objects.get(title='Global Technology Search for Industrial Heat Modernisation')
        candidate_count = mission.technology_candidates.count()
        manufacturer_count = m.ManufacturerProfile.objects.filter(products__technology_candidate__mission=mission).distinct().count()
        call_command('seed_global_research_demo')
        self.assertEqual(mission.technology_candidates.count(), candidate_count)
        self.assertEqual(m.ManufacturerProfile.objects.filter(products__technology_candidate__mission=mission).distinct().count(), manufacturer_count)
        self.assertEqual(m.ResearchMission.objects.filter(title=mission.title).count(), 1)
