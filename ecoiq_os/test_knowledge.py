from dataclasses import replace
from datetime import date
from unittest import TestCase

from ecoiq_os.evidence import ASSOCIATION_ONLY, REPLICATED_CAUSAL_SUPPORT
from ecoiq_os.kernel import (
    COLLECT_EVIDENCE, HUMAN_REVIEW_REQUIRED, RUN_FALSIFICATION,
    EcoIQOSCase, evaluate_case,
)
from ecoiq_os.flow import FlowEdge, FlowNode, UniversalFlowGraph
from ecoiq_os.test_kernel import valid_graph
from islamic_knowledge.contracts import KnowledgeBinding
from islamic_knowledge.principles import DRAFT_PRINCIPLES
from islamic_knowledge.test_contracts import approval, definition, source
from mizan.system_balance import (
    HEALTHY, INSUFFICIENT_DATA, BalanceDimension, MizanConstraint, assess_balance,
)


class KnowledgeKernelTests(TestCase):
    def case(self, **changes):
        return EcoIQOSCase(**dict(dict(case_id='TEST', domain='mining', objective='Test decision.',
            flow_graph=valid_graph(), mizan=assess_balance(scope_level='facility',
            dimensions=(BalanceDimension('justice', HEALTHY),)),
            hypothesis_status=REPLICATED_CAUSAL_SUPPORT), **changes))

    def test_draft_knowledge_blocks_even_replicated_real_world_evidence(self):
        case = self.case(knowledge=(KnowledgeBinding(DRAFT_PRINCIPLES[0]),))
        decision = evaluate_case(case)
        self.assertEqual(decision.next_stage, HUMAN_REVIEW_REQUIRED)
        self.assertTrue(decision.requires_human_review)
        self.assertIn('ecoiq.hikmah.v1:MISSING_SOURCES', decision.blocked_by)

    def test_reviewed_knowledge_never_upgrades_association(self):
        item = definition()
        sources = {'source-1': source()}
        receipt = approval(item, sources, reviewed_at=date(2000, 1, 1))
        case = self.case(hypothesis_status=ASSOCIATION_ONLY,
                         knowledge=(KnowledgeBinding(item, tuple(sources.values()), (receipt,)),))
        self.assertEqual(evaluate_case(case).next_stage, RUN_FALSIFICATION)

    def test_hard_constraints_remain_first(self):
        balance = assess_balance(scope_level='facility', dimensions=(BalanceDimension('justice', HEALTHY),),
            constraints=(MizanConstraint('worker_safety', True, 'safety', 'Test breach', 'Test evidence'),))
        decision = evaluate_case(self.case(mizan=balance, knowledge=(KnowledgeBinding(DRAFT_PRINCIPLES[0]),)))
        self.assertEqual(decision.blocked_by, ('worker_safety',))

    def test_known_dimension_cannot_hide_explicit_unknown_dimension(self):
        balance = assess_balance(scope_level='facility', dimensions=(
            BalanceDimension('economic', HEALTHY), BalanceDimension('justice', INSUFFICIENT_DATA)))
        self.assertEqual(balance.status, HEALTHY)  # descriptive balance remains compatible
        decision = evaluate_case(self.case(mizan=balance))
        self.assertEqual(decision.next_stage, COLLECT_EVIDENCE)
        self.assertIn('justice', decision.blocked_by)

    def test_all_bindings_are_checked_not_just_first(self):
        item = definition()
        sources = {'source-1': source()}
        receipt = approval(item, sources, reviewed_at=date(2000, 1, 1))
        decision = evaluate_case(self.case(knowledge=(
            KnowledgeBinding(item, tuple(sources.values()), (receipt,)),
            KnowledgeBinding(DRAFT_PRINCIPLES[1]),
        )))
        self.assertEqual(decision.next_stage, HUMAN_REVIEW_REQUIRED)
        self.assertTrue(any(reason.startswith('ecoiq.adl.v1:') for reason in decision.blocked_by))

    def test_legacy_cases_have_no_implicit_religious_dependency(self):
        self.assertEqual(self.case().knowledge, ())
        self.assertNotEqual(evaluate_case(self.case()).next_stage, HUMAN_REVIEW_REQUIRED)


class NumericAndGraphRegressionTests(TestCase):
    def test_nonfinite_and_non_numeric_flow_values_are_rejected(self):
        for value in (float('nan'), float('inf'), -float('inf'), True, '10'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                FlowEdge('e', 'a', 'b', 'water', value=value, unit='m3')

    def test_unknown_and_measured_zero_remain_distinct(self):
        self.assertIsNone(FlowEdge('e', 'a', 'b', 'water').value)
        self.assertEqual(FlowEdge('e', 'a', 'b', 'water', value=0, unit='m3').value, 0)
        self.assertIsNone(BalanceDimension('justice', INSUFFICIENT_DATA).current_value)
        self.assertEqual(BalanceDimension('justice', HEALTHY, current_value=0).current_value, 0)

    def test_nonfinite_mizan_values_and_thresholds_rejected(self):
        for field in ('current_value', 'threshold'):
            for value in (float('nan'), float('inf'), True, '10'):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    BalanceDimension('justice', HEALTHY, threshold_source='Test methodology', **{field: value})

    def test_duplicate_diagnostics_keep_order_and_missing_endpoints(self):
        node = FlowNode('a', 'Test', 'source')
        edge = FlowEdge('e', 'missing', 'a', 'water')
        graph = UniversalFlowGraph((node, node), (edge, edge))
        self.assertEqual([issue.code for issue in graph.validation_issues()],
                         ['DUPLICATE_NODE', 'DUPLICATE_EDGE', 'UNKNOWN_SOURCE', 'UNKNOWN_SOURCE'])
