from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

from evidence_memory.evaluation.benchmark import evaluate, load_dataset, metrics


class RetrievalEvaluationTests(SimpleTestCase):
    def test_metrics_have_known_denominators_and_no_answer_is_separate(self):
        result = metrics(['wrong', 'right', 'other'], ['right'])
        self.assertEqual(result['mrr_at_5'], 0.5)
        self.assertEqual(result['precision_at_3'], 1 / 3)
        self.assertEqual(result['recall_at_3'], 1)
        self.assertIsNone(metrics(['wrong'], []))
        self.assertEqual(metrics(['a'], ['a', 'b'])['recall_at_3'], 0.5)

    def test_ties_are_stable_and_no_answer_does_not_inflate_recall(self):
        data = {'documents': [{'id': 'b', 'text': 'B'}, {'id': 'a', 'text': 'A'}],
                'queries': [{'id': 'q1', 'question': 'A?', 'category': 'literal', 'relevant_ids': ['a']},
                            {'id': 'q2', 'question': 'Absent?', 'category': 'no_answer', 'relevant_ids': []}]}
        report = evaluate(data, lambda texts: [[1, 0]] * len(texts), {'name': 'test'})
        self.assertEqual(report['queries'][0]['ranked_ids'], ['a', 'b'])
        self.assertEqual(report['answerable']['recall_at_3'], 1)
        self.assertEqual(report['no_answer_with_candidates'], 1)

    def test_wrong_shape_and_nonfinite_vectors_are_rejected(self):
        data = {'documents': [{'id': 'a', 'text': 'A'}], 'queries': []}
        for vectors in ([], [[float('nan')]], [[1], [2]]):
            with self.subTest(vectors=vectors), self.assertRaises(ValueError):
                evaluate(data, lambda _, values=vectors: values, {})

    def test_control_set_has_resolvable_judgements_and_declares_its_limit(self):
        data = load_dataset(Path(settings.BASE_DIR) / 'evidence_memory/evaluation/control_set.json')
        self.assertEqual(len(data['documents']), 18)
        self.assertEqual(len(data['queries']), 35)
        self.assertIn('pending independent', data['label_status'])
        self.assertEqual(sum(not q['relevant_ids'] for q in data['queries']), 5)
