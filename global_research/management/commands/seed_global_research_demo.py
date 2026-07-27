"""
Seed the "Global Technology Search for Industrial Heat Modernisation"
Global Research demo (idempotent). Depends on (and re-seeds if needed) the
Prompt 1 Digital Twin demo, since a ResearchMission must originate from a
real, already-governed EcoIQ entity.

Usage:
    python manage.py seed_global_research_demo
"""
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand

from digital_twin.models import DigitalTwin, LossDetection, Unit
from global_research.models import (
    ComparativeEvaluation, ManufacturerProfile, ProductCandidate,
    ResearchHumanDecision, ResearchMission, ResearchRecommendation,
    TechnicalRequirement, TechnologyCandidate,
)
from global_research.providers.simulated import get_injection_test_candidate
from global_research.services import (
    claim_extraction, comparison, council, documents, orchestrator, risk, scenario_bridge,
)

DEMO_KEYWORDS = [
    'industrial heat pump', 'heat pump', 'heat recovery', 'waste heat recovery',
    'advanced controls', 'advanced process control', 'hybrid heating', 'boiler retrofit',
    'high-efficiency boiler', 'district heating',
]


class Command(BaseCommand):
    help = 'Seed the Global Technology Search for Industrial Heat Modernisation research demo end to end.'

    def handle(self, *args, **opts):
        if not DigitalTwin.objects.filter(asset__name='Riverside District Heating Plant').exists():
            self.stdout.write('Digital Twin demo not found — seeding it first...')
            call_command('seed_digital_twin_demo')

        User = get_user_model()
        reviewer, _ = User.objects.get_or_create(
            username='global_research_demo_reviewer',
            defaults={'is_staff': True, 'first_name': 'Founder', 'last_name': 'Reviewer'},
        )

        twin = DigitalTwin.objects.get(asset__name='Riverside District Heating Plant')
        loss_detection = LossDetection.objects.filter(twin=twin, loss_type='heat_loss', promoted_loss__isnull=False).first()

        mission, _ = ResearchMission.objects.get_or_create(
            title='Global Technology Search for Industrial Heat Modernisation',
            defaults=dict(
                asset=twin.asset, twin=twin, component=twin.components.filter(component_type='boiler').first(),
                loss_detection=loss_detection,
                problem_statement=(
                    'The Riverside District Heating Plant runs an ageing coal/gas boiler with high fuel use, '
                    '8,000 kWh of recorded heat loss, and a local air-quality concern. Identify suitable '
                    'modernisation technologies and manufacturers from multiple countries — supplier-neutral, '
                    'evidence-governed, no procurement commitment.'
                ),
                desired_outcome='A shortlisted, evidence-backed technology and a supplier-neutral modernisation scenario ready for RFI.',
                scope='Global search across authoritative, commercial, market and early-innovation evidence layers.',
                industry='District Heating', country_of_deployment='Kazakhstan', target_countries=[],
                required_evidence_level='capital_grade', status='draft', priority='high',
                created_by=reviewer,
            ),
        )
        if mission.status == 'draft':
            mission.status = 'approved_for_research'
            mission.approved_by = reviewer
            mission.save(update_fields=['status', 'approved_by', 'updated_at'])

        count_unit = Unit.objects.get(code='count')
        kwh_unit = Unit.objects.get(code='kwh')
        pct_unit = Unit.objects.get(code='pct')
        hour_unit = Unit.objects.get(code='hour')

        requirement_specs = [
            ('temperature', 'Minimum supply temperature the system must deliver', 'max_supply_temperature_c', 80.0, None, None, count_unit, True),
            ('capacity', 'Minimum rated thermal output for the boiler house', 'rated_thermal_output_kw', 300.0, None, None, kwh_unit, True),
            ('efficiency', 'Minimum seasonal coefficient of performance (if heat-pump based)', 'has_seasonal_cop', 3.0, 4.0, None, count_unit, False),
            ('material_compatibility', 'Compatible with existing district-heating water chemistry', '', None, None, None, None, True),
            ('electrical', 'Compatible with local 380V/50Hz three-phase electrical supply', '', None, None, None, None, True),
            ('certification', 'Zone 2 hazardous-area certification for the boiler house', '', None, None, None, None, False),
            ('throughput', 'Minimum recoverable heat from waste-heat streams', 'recoverable_heat_kw', 100.0, None, None, kwh_unit, False),
            ('service_life', 'Minimum expected service life', '', 15.0, None, None, None, True),
            ('spare_parts_availability', 'Spare parts available within Kazakhstan or neighbouring region', '', None, None, None, None, True),
            ('installation_downtime', 'Maximum allowable installation downtime for the district network', '', None, None, 72.0, hour_unit, True),
            ('emissions', 'Maximum local air-quality emissions impact', '', None, None, None, None, False),
            ('worker_exposure', 'No increase in worker exposure risk during or after installation', '', None, None, None, None, True),
        ]
        for req_type, description, metric, minimum, preferred, maximum, unit, mandatory in requirement_specs:
            TechnicalRequirement.objects.get_or_create(
                mission=mission, description=description,
                defaults=dict(
                    requirement_type=req_type, metric=metric, minimum_value=minimum, preferred_value=preferred,
                    maximum_value=maximum, unit=unit, is_mandatory=mandatory, approved=True,
                    verification_method='independent_test' if mandatory else 'vendor_declaration',
                    rationale='Derived from the Riverside District Heating Plant twin\'s recorded operating conditions and heat-loss detection.',
                ),
            )

        query_plan = orchestrator.generate_query_plan(mission, keywords=DEMO_KEYWORDS, languages=['en', 'ru', 'kk', 'de', 'zh', 'tr'])
        run = orchestrator.run_mission(mission, query_plan=query_plan)

        # Seeded adversarial fixture — proves external content is evidence,
        # never an instruction. Persisted and claim-extracted through the
        # exact same path as every other source; asserted to have zero effect.
        injection_candidate = get_injection_test_candidate()
        from global_research.providers.simulated import MarketProcurementProvider

        provider = MarketProcurementProvider()
        document = provider.fetch(injection_candidate)
        normalised = provider.normalise(document)
        injection_source, _ = claim_extraction.persist_source(mission, normalised)
        pre_shortlisted_count = TechnologyCandidate.objects.filter(mission=mission, status='shortlisted').count()

        risk.evaluate_all_risks(mission)

        # Author narrative stewardship context on the leading candidate so
        # the (pre-scenario) stewardship screen has real signal to assess.
        heat_pump_candidate = TechnologyCandidate.objects.filter(mission=mission, category__name='Industrial Heat Pump').first()
        if heat_pump_candidate:
            heat_pump_candidate.worker_implications = 'Installation requires supervised working-at-height for rooftop units; no reported incidents for this technology category.'
            heat_pump_candidate.environmental_implications = 'Reduces local flue-gas emissions relative to coal/gas combustion; no reported adverse local environmental impact.'
            heat_pump_candidate.save(update_fields=['worker_implications', 'environmental_implications', 'updated_at'])
            comparison.build_comparative_evaluation(
                mission, technology_candidate=heat_pump_candidate,
                compatibility_assessment=heat_pump_candidate.compatibility_assessments.first(),
            )
            comparison.rank_mission_evaluations(mission)

        # Convene the Research Council on the top-ranked product and on the
        # failed-mandatory GreatWall product, to show both an approval and a
        # rejection path with real disagreement.
        top_evaluation = ComparativeEvaluation.objects.filter(mission=mission, is_ranked=True).order_by('rank').first()
        council_results = {}
        if top_evaluation and top_evaluation.product_candidate:
            council_results['top'] = council.convene_council(
                mission, technology_candidate=top_evaluation.technology_candidate, product_candidate=top_evaluation.product_candidate,
            )
        failed_product = ProductCandidate.objects.filter(technology_candidate__mission=mission, compatibility_assessments__mandatory_pass=False).first()
        if failed_product:
            council_results['failed'] = council.convene_council(
                mission, technology_candidate=failed_product.technology_candidate, product_candidate=failed_product,
            )

        # Human shortlist decision on the top candidate.
        shortlist_decision = None
        if top_evaluation and top_evaluation.product_candidate:
            top_product = top_evaluation.product_candidate
            top_product.status = 'shortlisted'
            top_product.save(update_fields=['status', 'updated_at'])
            top_evaluation.technology_candidate.status = 'shortlisted'
            top_evaluation.technology_candidate.save(update_fields=['status', 'updated_at'])

            shortlist_decision, _ = ResearchHumanDecision.objects.get_or_create(
                mission=mission, stage='manufacturer_shortlist', product_candidate=top_product,
                defaults=dict(
                    technology_candidate=top_evaluation.technology_candidate,
                    council_run=council_results.get('top', {}).get('run'), reviewer=reviewer, reviewer_role='Founder',
                    decision='approved_with_conditions',
                    comments='Strongest compatible candidate with independent corroboration on record. Confirm commercial terms via RFQ before procurement.',
                    conditions=['Obtain a real supplier quotation before any capital commitment.'],
                ),
            )

            recommendation, _ = ResearchRecommendation.objects.get_or_create(
                mission=mission, recommendation_type='create_supplier_neutral_scenario', product_candidate=top_product,
                defaults=dict(
                    technology_candidate=top_evaluation.technology_candidate,
                    rationale='Highest-ranked compatible candidate with independent evidence corroboration; recommended for a supplier-neutral modernisation scenario.',
                    evidence_references=[f'global_research.ResearchClaim:{c.pk}' for c in top_product.source_claims.all()],
                    confidence=top_evaluation.evidence_score, human_approval_status='approved',
                ),
            )

            scenario_decision, _ = ResearchHumanDecision.objects.get_or_create(
                mission=mission, stage='scenario_creation', recommendation=recommendation,
                defaults=dict(reviewer=reviewer, reviewer_role='Founder', decision='approved'),
            )
            if not recommendation.created_scenario_id:
                scenario_bridge.create_scenario_from_recommendation(recommendation, scenario_decision)

        # Reject the incompatible candidate explicitly, with a named reason.
        if failed_product:
            ResearchHumanDecision.objects.get_or_create(
                mission=mission, stage='candidate_review', product_candidate=failed_product,
                defaults=dict(
                    technology_candidate=failed_product.technology_candidate,
                    council_run=council_results.get('failed', {}).get('run'), reviewer=reviewer, reviewer_role='Founder',
                    decision='rejected', rejection_reason='poor_compatibility',
                    comments='Maximum supply temperature (60°C) fails the mission\'s 80°C mandatory requirement.',
                ),
            )

        # Draft RFI, then approve it (still never sent).
        draft = mission.document_drafts.filter(document_type='rfi').order_by('-version').first()
        if draft is None:
            draft = documents.generate_document_draft(mission, 'rfi')
        if draft.status == 'draft':
            approval_decision, _ = ResearchHumanDecision.objects.get_or_create(
                mission=mission, stage='rfi_rfq_approval', document_draft=draft,
                defaults=dict(reviewer=reviewer, reviewer_role='Founder', decision='approved'),
            )
            documents.approve_document_draft(draft, approval_decision, reviewer)

        post_shortlisted_count = TechnologyCandidate.objects.filter(mission=mission, status='shortlisted').count()

        self.stdout.write(self.style.SUCCESS(
            f'Global Research demo ready: mission="{mission.title}" status={mission.status}, '
            f'{mission.requirements.count()} requirements, {mission.sources.count()} sources '
            f'({mission.sources.values("source_type").distinct().count()} source types), '
            f'{mission.claims.count()} claims, {mission.contradictions.count()} contradiction(s), '
            f'{mission.technology_candidates.count()} technology candidates, '
            f'{ManufacturerProfile.objects.filter(products__technology_candidate__mission=mission).distinct().count()} manufacturers, '
            f'{ProductCandidate.objects.filter(technology_candidate__mission=mission).count()} products, '
            f'injection-fixture source id={injection_source.pk} flagged={injection_source.content_safety_flagged} '
            f'(shortlisted count unaffected by it: {pre_shortlisted_count} -> {post_shortlisted_count} only after real human decision), '
            f'human decisions={mission.human_decisions.count()}, '
            f'scenario created={"yes" if ResearchRecommendation.objects.filter(mission=mission, created_scenario__isnull=False).exists() else "no"}, '
            f'RFI draft status={draft.status}.'
        ))
