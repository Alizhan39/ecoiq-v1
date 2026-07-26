"""
Seed the "Industrial Heat Modernisation Pilot" Digital Twin demo (idempotent).

Usage:
    python manage.py seed_digital_twin_demo

Walks the full pipeline end to end against real, persisted rows: baseline ->
data gap -> loss detection -> human-approved promotion into a real
OperationalLoss -> three modernisation scenarios (no-change / low-cost /
strategic) -> deterministic simulation -> stewardship KPI assessment ->
Agent Council review (with a genuine disagreement) -> a human
approved-with-conditions decision -> promotion into a real
CapitalAllocationDecision -> one implementation action with a placeholder
measured outcome.
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from digital_twin.models import (
    AssetType, DigitalTwin, IndustrialAsset, LossDetection, MetricDefinition,
    ModernisationScenario, OperationalMetric, ProcessEdge, ProcessNode,
    ResourceFlow, TwinComponent, TwinDataGap, Unit,
)
from digital_twin.services import (
    baseline as baseline_service, council as council_service,
    guardrails as guardrails_service, loss_detection as loss_detection_service,
    outcomes as outcomes_service, promotion as promotion_service,
    scenario_simulation, stewardship as stewardship_service,
)


class Command(BaseCommand):
    help = 'Seed the Industrial Heat Modernisation Pilot Digital Twin demo end to end.'

    def handle(self, *args, **opts):
        User = get_user_model()
        reviewer, _ = User.objects.get_or_create(
            username='digital_twin_demo_reviewer',
            defaults={'is_staff': True, 'first_name': 'Founder', 'last_name': 'Reviewer'},
        )

        kwh = Unit.objects.get(code='kwh')
        m3 = Unit.objects.get(code='m3')
        kgco2e = Unit.objects.get(code='kgco2e')

        asset_type = AssetType.objects.get(code='energy_asset')
        asset, _ = IndustrialAsset.objects.get_or_create(
            name='Riverside District Heating Plant',
            defaults={
                'asset_type': asset_type, 'country': 'Kazakhstan', 'region': 'Almaty Region',
                'latitude': 43.238, 'longitude': 76.945, 'industry': 'District Heating',
                'lifecycle_stage': 'operational', 'operational_status': 'active',
                'description': (
                    'A district-heating plant serving a residential and light-industrial district, '
                    'running an ageing coal/gas boiler installed in the 1990s.'
                ),
                'owner': 'Riverside Municipal Heating Authority', 'source_system': 'manual', 'is_demo': True,
            },
        )

        twin, _ = DigitalTwin.objects.get_or_create(
            asset=asset, version=1,
            defaults={
                'name': 'Riverside District Heating Plant — Baseline Twin',
                'status': 'draft', 'baseline_date': timezone.now().date(), 'created_by': reviewer,
            },
        )

        boiler, _ = TwinComponent.objects.get_or_create(
            twin=twin, name='Boiler House #3',
            defaults={
                'component_type': 'boiler', 'manufacturer': 'Dorogobuzhkotlomash', 'model_reference': 'DKVR-10-13',
                'commissioning_date': timezone.datetime(1994, 3, 1).date(), 'expected_useful_life_years': 25,
                'condition': 'poor', 'criticality': 'high', 'operational_status': 'operational',
            },
        )
        backup_boiler, _ = TwinComponent.objects.get_or_create(
            twin=twin, name='Backup Gas Boiler',
            defaults={
                'component_type': 'boiler', 'manufacturer': 'Viessmann', 'model_reference': 'Vitomax 200-HS',
                'commissioning_date': timezone.datetime(2015, 1, 1).date(), 'expected_useful_life_years': 30,
                'condition': 'good', 'criticality': 'medium', 'operational_status': 'standby',
            },
        )
        distribution, _ = TwinComponent.objects.get_or_create(
            twin=twin, name='Heat Distribution Network',
            defaults={
                'component_type': 'energy_system', 'condition': 'fair', 'criticality': 'high',
                'operational_status': 'operational',
            },
        )

        combustion_node, _ = ProcessNode.objects.get_or_create(
            twin=twin, name='Coal/Gas Combustion', component=boiler,
            defaults={
                'node_type': 'heating', 'sequence_order': 1, 'capacity': 10.0, 'capacity_unit': None,
                'actual_throughput': 8.2, 'downtime_hours': 180.0, 'yield_pct': 72.0, 'utilisation_pct': 85.0,
                'energy_use': 12000.0, 'energy_unit': kwh, 'emissions': 9000.0, 'emissions_unit': kgco2e,
                'cost_per_unit': 22.0, 'confidence': 55.0,
            },
        )
        backup_node, _ = ProcessNode.objects.get_or_create(
            twin=twin, name='Backup Boiler (Standby)', component=backup_boiler,
            defaults={
                'node_type': 'heating', 'sequence_order': 2, 'capacity': 4.0,
                'utilisation_pct': 15.0, 'energy_use': 800.0, 'energy_unit': kwh, 'confidence': 50.0,
            },
        )
        distribution_node, _ = ProcessNode.objects.get_or_create(
            twin=twin, name='Heat Distribution Network', component=distribution,
            defaults={
                'node_type': 'transport', 'sequence_order': 3, 'utilisation_pct': 90.0,
                'downtime_hours': 20.0, 'yield_pct': 88.0, 'confidence': 60.0,
            },
        )
        ProcessEdge.objects.get_or_create(twin=twin, source_node=combustion_node, target_node=distribution_node, defaults={'label': 'Steam/hot water', 'sequence_order': 1})
        ProcessEdge.objects.get_or_create(twin=twin, source_node=backup_node, target_node=distribution_node, defaults={'label': 'Standby feed', 'sequence_order': 2})

        ResourceFlow.objects.get_or_create(
            twin=twin, resource_type='heat', source_node=distribution_node,
            defaults={
                'quantity': 50000.0, 'unit': kwh, 'loss_quantity': 8000.0, 'cost': 4000.0, 'currency': 'USD',
                'confidence': 55.0,
            },
        )
        ResourceFlow.objects.get_or_create(
            twin=twin, resource_type='emissions', source_node=combustion_node,
            defaults={'quantity': 10000.0, 'unit': kgco2e, 'loss_quantity': 1500.0, 'confidence': 45.0},
        )
        ResourceFlow.objects.get_or_create(
            twin=twin, resource_type='water', source_node=combustion_node,
            defaults={'quantity': 3000.0, 'unit': m3, 'loss_quantity': 0.0, 'confidence': 60.0},
        )

        metric_defs = {}
        for code, name, unit, higher_is_better in [
            ('energy_intensity', 'Energy Intensity', kwh, False),
            ('downtime', 'Downtime', None, False),
            ('emissions_intensity', 'Emissions Intensity', kgco2e, False),
            ('operating_cost', 'Operating Cost', None, False),
        ]:
            metric_defs[code], _ = MetricDefinition.objects.get_or_create(
                code=code, defaults={'name': name, 'default_unit': unit, 'higher_is_better': higher_is_better},
            )

        energy_intensity_metric, _ = OperationalMetric.objects.get_or_create(
            definition=metric_defs['energy_intensity'], twin=twin, process_node=combustion_node,
            defaults={'value': 1450.0, 'unit': kwh, 'source': 'utility meter', 'confidence': 60.0, 'verification_status': 'system_checked'},
        )
        OperationalMetric.objects.get_or_create(
            definition=metric_defs['downtime'], twin=twin, process_node=combustion_node,
            defaults={'value': 180.0, 'unit': Unit.objects.get(code='hour'), 'source': 'maintenance log', 'confidence': 65.0, 'verification_status': 'human_reviewed'},
        )
        # Emissions intensity is deliberately left with a low, honestly-stated
        # confidence and no evidence — this is the demo's "incomplete
        # evidence in at least one area."
        OperationalMetric.objects.get_or_create(
            definition=metric_defs['emissions_intensity'], twin=twin, process_node=combustion_node,
            defaults={'value': 780.0, 'unit': kgco2e, 'source': 'estimated from fuel purchase records', 'confidence': 30.0, 'verification_status': 'unverified'},
        )

        TwinDataGap.objects.get_or_create(
            twin=twin, affected_area='Worker exposure monitoring at Boiler House #3',
            defaults={
                'required_data': 'Personal exposure monitoring readings for boiler-room operators (particulate/CO).',
                'why_it_matters': 'Cannot assess worker-safety stewardship or regulatory compliance without this data.',
                'severity': 'high', 'status': 'open',
                'recommended_collection_method': 'Install personal air-quality monitors for the next maintenance cycle.',
            },
        )

        baseline_result = baseline_service.apply_baseline(twin)
        twin.refresh_from_db()
        twin.status = 'active'
        twin.approved_by = reviewer
        twin.approved_at = timezone.now()
        twin.save(update_fields=['status', 'approved_by', 'approved_at', 'updated_at'])

        candidates = [c for c, _ in loss_detection_service.detect_loss_candidates(twin)]
        heat_loss_candidate = next(c for c in candidates if c.loss_type == 'heat_loss')
        emissions_candidate = next(c for c in candidates if c.loss_type == 'avoidable_emissions')
        for candidate in (heat_loss_candidate, emissions_candidate):
            candidate.status = 'approved'
            candidate.reviewed_by = reviewer
            candidate.reviewed_at = timezone.now()
            candidate.review_notes = 'Reviewed against maintenance and utility records — approved for promotion.'
            candidate.save()
            loss_detection_service.promote_loss_detection(
                candidate, organisation=asset.owner, location=asset.region, country=asset.country, sector=asset.industry,
            )

        real_loss = heat_loss_candidate.promoted_loss

        scenario_specs = [
            {
                'scenario_type': 'no_change', 'intervention_type': 'do_nothing',
                'title': 'Continue current operation', 'technology_category': 'None (status quo)',
                'technical_specification': 'No equipment changes; continue operating Boiler House #3 as-is with reactive maintenance.',
                'capex': 0.0, 'opex_change': 6000.0, 'annual_savings': 0.0,
                'energy_impact': 0.0, 'water_impact': 0.0, 'waste_impact': 0.0, 'emissions_impact': 500.0,
                'production_impact_pct': 0.0, 'downtime_impact_hours': 0.0, 'worker_impact': '', 'community_impact': '',
                'operational_disruption': 'none', 'confidence': 70.0, 'evidence_references': [],
            },
            {
                'scenario_type': 'low_cost', 'intervention_type': 'operational_optimisation',
                'title': 'Efficiency retrofit and controls', 'technology_category': 'Combustion controls + steam-trap repair',
                'technical_specification': (
                    'Install automated combustion controls and repair/replace failed steam traps in the distribution '
                    'network to recover a portion of the recorded 8,000 kWh heat loss.'
                ),
                'capex': 45000.0, 'opex_change': -2000.0, 'annual_savings': 18000.0,
                'energy_impact': -3200.0, 'water_impact': 0.0, 'waste_impact': 0.0, 'emissions_impact': -1800.0,
                'production_impact_pct': 3.0, 'downtime_impact_hours': -40.0,
                'worker_impact': 'Two operators retrained on new control panel; no headcount change.',
                'community_impact': 'Reduced local flue-gas odour reported during pilot testing at comparable sites.',
                'operational_disruption': 'low', 'confidence': 65.0,
                'evidence_references': [],  # filled in below once energy_intensity_metric.pk is known
            },
            {
                'scenario_type': 'strategic', 'intervention_type': 'equipment_upgrade',
                'title': 'Transition to electric heat pumps', 'technology_category': 'Air/water-source heat pump array',
                'technical_specification': (
                    'Replace the coal/gas boiler with a supplier-neutral heat-pump array sized to the distribution '
                    'network\'s recorded peak load, retaining the backup gas boiler for extreme cold-snap redundancy.'
                ),
                'capex': 380000.0, 'opex_change': -8000.0, 'annual_savings': 52000.0,
                'energy_impact': -9000.0, 'water_impact': 0.0, 'waste_impact': -500.0, 'emissions_impact': -8500.0,
                'production_impact_pct': 5.0, 'downtime_impact_hours': -120.0,
                'worker_impact': (
                    'Requires a 6-week construction window with confined-space work during heat-pump installation; '
                    'risk of exposure during the retrofit window unless a specialist safety plan is in place.'
                ),
                'community_impact': 'Major local air-quality improvement expected; no resettlement or displacement.',
                'operational_disruption': 'high', 'confidence': 55.0, 'evidence_references': [],
            },
        ]
        for spec in scenario_specs:
            if spec['scenario_type'] == 'low_cost':
                spec['evidence_references'] = [f'digital_twin.OperationalMetric:{energy_intensity_metric.pk}']

        scenarios = []
        for spec in scenario_specs:
            intervention, _ = real_loss.interventions.get_or_create(
                title=spec['title'],
                defaults={
                    'intervention_type': spec['intervention_type'],
                    'description': spec['technical_specification'],
                    'capex_estimate': spec['capex'], 'opex_change': spec['opex_change'],
                    'estimated_loss_avoided': max(spec['annual_savings'], 0.0),
                    'estimated_annual_savings': spec['annual_savings'],
                    'technical_readiness': 'ready' if spec['scenario_type'] != 'strategic' else 'needs_review',
                    'finance_readiness': 'ready', 'risk_level': {'no_change': 'high', 'low_cost': 'low', 'strategic': 'medium'}[spec['scenario_type']],
                    'status': 'modelled',
                },
            )
            scenario, _ = ModernisationScenario.objects.get_or_create(
                intervention=intervention,
                defaults={
                    'twin': twin, 'component': boiler, 'process_node': combustion_node,
                    'loss_detection': heat_loss_candidate, 'scenario_type': spec['scenario_type'],
                    'technology_category': spec['technology_category'],
                    'technical_specification': spec['technical_specification'],
                    'implementation_phases': [
                        {'phase': 'Design', 'description': 'Engineering design and permitting', 'duration': '2 months'},
                        {'phase': 'Installation', 'description': 'Equipment installation', 'duration': '2 months'},
                        {'phase': 'Commissioning', 'description': 'Testing and handover', 'duration': '1 month'},
                    ] if spec['scenario_type'] != 'no_change' else [],
                    'energy_impact': spec['energy_impact'], 'energy_impact_unit': kwh,
                    'water_impact': spec['water_impact'], 'water_impact_unit': m3,
                    'waste_impact': spec['waste_impact'],
                    'emissions_impact': spec['emissions_impact'], 'emissions_impact_unit': kgco2e,
                    'production_impact_pct': spec['production_impact_pct'], 'downtime_impact_hours': spec['downtime_impact_hours'],
                    'worker_impact': spec['worker_impact'], 'community_impact': spec['community_impact'],
                    'operational_disruption': spec['operational_disruption'],
                    'dependencies': [] if spec['scenario_type'] == 'no_change' else ['Municipal permit approval'],
                    'technical_risks': [] if spec['scenario_type'] == 'no_change' else (
                        ['Confined-space work during installation'] if spec['scenario_type'] == 'strategic' else ['Steam-trap parts lead time']
                    ),
                    'regulatory_requirements': [] if spec['scenario_type'] == 'no_change' else ['Municipal heating tariff filing'],
                    'confidence': spec['confidence'], 'evidence_references': spec['evidence_references'],
                },
            )
            scenario_simulation.persist_scenario_cases(scenario)
            stewardship_service.run_stewardship_assessment(scenario)
            scenarios.append(scenario)

        council_reviews = {s.pk: council_service.convene_council(s) for s in scenarios}
        strategic_scenario = next(s for s in scenarios if s.scenario_type == 'strategic')
        low_cost_scenario = next(s for s in scenarios if s.scenario_type == 'low_cost')
        no_change_scenario = next(s for s in scenarios if s.scenario_type == 'no_change')

        # Human decision: approve the low-cost scenario with conditions —
        # the strategic scenario's Worker Safety disagreement (confined-space
        # risk) is exactly why it is NOT the one approved in this pilot phase.
        low_cost_review = council_reviews[low_cost_scenario.pk]
        human_decision, _ = low_cost_scenario.human_decisions.get_or_create(
            decision='approved_with_conditions',
            defaults={
                'council_run': low_cost_review['run'], 'reviewer': reviewer, 'reviewer_role': 'Founder',
                'comments': (
                    'Approved for the efficiency retrofit — strong payback with low disruption. The strategic '
                    'heat-pump transition remains promising but needs a specialist worker-safety review before '
                    'it can be brought back to Council.'
                ),
                'conditions': ['Confirm steam-trap supplier lead time before committing capital.'],
            },
        )
        human_decision.rejected_alternatives.add(strategic_scenario, no_change_scenario)

        capital_decision = promotion_service.promote_scenario(human_decision)

        action, _ = low_cost_scenario.implementation_actions.get_or_create(
            title='Install combustion controls and repair steam traps',
            defaults={
                'human_decision': human_decision, 'owner': 'Riverside Municipal Heating Authority — Ops Team',
                'planned_start_date': timezone.now().date(), 'status': 'in_progress',
                'budget': 45000.0, 'expected_outcome': 'Reduce recorded heat loss from 8,000 kWh toward 4,800 kWh within 6 months.',
            },
        )
        # Placeholder measured outcome: predicted value recorded, actual
        # measurement not yet taken — honestly represented as a pending
        # placeholder rather than a fabricated result.
        if not action.measured_outcomes.exists():
            outcomes_service.record_measured_outcome(
                action, predicted_value=4800.0, actual_value=None, metric_definition=metric_defs['energy_intensity'],
                unit=kwh, model_learning_note='Placeholder — first real measurement due after 6 months of operation.',
            )

        guardrail_summaries = {s.scenario_type: guardrails_service.evaluate_guardrails(s)['verdict'] for s in scenarios}

        self.stdout.write(self.style.SUCCESS(
            f'Digital Twin demo ready: asset="{asset.name}", twin v{twin.version} status={twin.status} '
            f'(completeness={baseline_result["completeness_score"]}, confidence={baseline_result["confidence_score"]}), '
            f'{len(candidates)} loss candidates detected, 2 promoted, {len(scenarios)} scenarios simulated, '
            f'guardrail verdicts={guardrail_summaries}, human decision={human_decision.get_decision_display()}, '
            f'capital allocation decision id={capital_decision.pk} (approval_status={capital_decision.approval_status}).'
        ))
