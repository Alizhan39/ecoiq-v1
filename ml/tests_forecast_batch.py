"""Forecast window correctness, bounded prefetch and batch read-query budget."""
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from companies.models import DataIngestionLog
from league.models import Company, ScoreHistory
from ml.prediction import (
    HISTORY_LIMIT, PREDICTION_VERSION, SIGNAL_LIMIT,
    _history_for, apply_predictions, predict_12m,
)


def company(slug, score=50):
    record = Company.objects.create(name=slug, slug=slug, country='UK')
    # Company.save() computes the score from pillars; supply the known test input
    # directly so these tests exercise forecasting rather than score calculation.
    Company.objects.filter(pk=record.pk).update(ecoiq_score=score)
    record.ecoiq_score = Decimal(str(score)) if score is not None else None
    return record


def snapshot(company, date, score):
    return ScoreHistory.objects.create(company=company, date=date, ecoiq_score=score,
        score_pollution_footprint=50, score_reduction_progress=50, score_investment=50,
        score_transparency=50, score_community_impact=50)


class ForecastBatchTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.today = self.now.date()

    def test_default_batch_no_longer_joins_reverse_history_relation(self):
        record = company('batch-default')
        with patch('ml.prediction._write_prediction') as write:
            self.assertEqual(apply_predictions(), {'updated': 1, 'failed': 0})
        self.assertEqual(write.call_args.args[0].pk, record.pk)

    def test_uses_latest_twelve_rows_in_chronological_order(self):
        record = company('recent-window')
        for i in range(30):
            snapshot(record, self.today - timedelta(days=(30 - i) * 30), 20 if i < 18 else 70)
        history = _history_for(record)
        self.assertEqual(len(history), HISTORY_LIMIT)
        self.assertEqual(history, sorted(history))
        self.assertEqual({score for _, score in history}, {Decimal('70')})
        self.assertAlmostEqual(predict_12m(record), 70)
        self.assertEqual(PREDICTION_VERSION, '2')

    def test_batch_and_single_predictions_match(self):
        trend = company('trend')
        fallback = company('fallback')
        for i in range(15):
            snapshot(trend, self.today - timedelta(days=(15 - i) * 30), 40 + i)
        for kind in ('positive', 'positive', 'harm'):
            DataIngestionLog.objects.create(company=fallback, source='rss', raw_data={'signal_type': kind})
        expected = {item.pk: round(predict_12m(item), 1) for item in (trend, fallback)}
        with patch('ml.prediction._write_prediction') as write:
            result = apply_predictions(Company.objects.filter(pk__in=expected))
        actual = {call.args[0].pk: call.args[1] for call in write.call_args_list}
        self.assertEqual(result, {'updated': 2, 'failed': 0})
        self.assertEqual(actual, expected)

    def test_read_queries_do_not_grow_per_company_within_a_batch(self):
        records = [company(f'query-budget-{i}') for i in range(16)]
        for record in records:
            for i in range(3):
                snapshot(record, self.today - timedelta(days=(3 - i) * 30), 50 + i)
        with patch('ml.prediction._write_prediction'), CaptureQueriesContext(connection) as queries:
            result = apply_predictions(Company.objects.filter(pk__in=[row.pk for row in records]))
        self.assertEqual(result, {'updated': 16, 'failed': 0})
        self.assertEqual(len(queries), 3, [query['sql'] for query in queries])

    def test_prefetch_limits_are_per_company(self):
        records = [company(f'bounded-{i}') for i in range(2)]
        for record in records:
            for i in range(20):
                snapshot(record, self.today - timedelta(days=i * 30), 50)
            for _ in range(55):
                DataIngestionLog.objects.create(company=record, source='rss', raw_data={'signal_type': 'positive'})
        lengths = []
        def observe(record):
            lengths.append((len(record._forecast_history), len(record._forecast_signals)))
            return 50
        with patch('ml.prediction.predict_12m', side_effect=observe), patch('ml.prediction._write_prediction'):
            apply_predictions(Company.objects.filter(pk__in=[row.pk for row in records]))
        self.assertEqual(lengths, [(HISTORY_LIMIT, SIGNAL_LIMIT)] * 2)

    def test_signal_cutoff_source_and_latest_fifty_match_single_path(self):
        record = company('signals')
        old = DataIngestionLog.objects.create(company=record, source='rss', raw_data={'signal_type': 'harm'})
        DataIngestionLog.objects.filter(pk=old.pk).update(ingested_at=self.now - timedelta(days=100))
        DataIngestionLog.objects.create(company=record, source='manual', raw_data={'signal_type': 'harm'})
        for i in range(55):
            log = DataIngestionLog.objects.create(company=record, source='rss',
                                                 raw_data={'signal_type': 'harm' if i < 5 else 'positive'})
            DataIngestionLog.objects.filter(pk=log.pk).update(ingested_at=self.now - timedelta(hours=55 - i))
        with patch('django.utils.timezone.now', return_value=self.now):
            self.assertEqual(predict_12m(record), 60)
            with patch('ml.prediction._write_prediction') as write:
                apply_predictions([record])
            self.assertEqual(write.call_args.args[1], 60)

    def test_caller_instances_do_not_retain_stale_input_snapshots(self):
        record = company('repeat-input')
        with patch('ml.prediction._write_prediction') as write:
            apply_predictions([record])
            self.assertEqual(write.call_args.args[1], 50)
            self.assertFalse(hasattr(record, '_forecast_history'))
            self.assertFalse(hasattr(record, '_forecast_signals'))
            DataIngestionLog.objects.create(company=record, source='rss', raw_data={'signal_type': 'harm'})
            apply_predictions([record])
            self.assertEqual(write.call_args.args[1], 49.5)

    def test_batches_are_bounded_and_accept_generators(self):
        records = [company(f'generator-{i}') for i in range(5)]
        with patch('ml.prediction.BATCH_SIZE', 2), patch('ml.prediction._write_prediction') as write:
            result = apply_predictions(iter(records))
        self.assertEqual(result, {'updated': 5, 'failed': 0})
        self.assertEqual(write.call_count, 5)
        self.assertTrue(all(not hasattr(record, '_forecast_history') for record in records))

    def test_failure_isolated_and_private_snapshots_cleared(self):
        records = [company('failed-write'), company('successful-write')]
        with patch('ml.prediction._write_prediction', side_effect=[RuntimeError('test'), None]):
            result = apply_predictions(records)
        self.assertEqual(result, {'updated': 1, 'failed': 1})
        self.assertTrue(all(not hasattr(record, '_forecast_signals') for record in records))

    def test_unknown_base_stays_unknown_and_zero_is_valid_for_explicit_input(self):
        unknown = company('unknown-input')
        unknown.ecoiq_score = None
        zero = company('zero-input', score=0)
        with patch('ml.prediction._write_prediction') as write:
            result = apply_predictions([unknown, zero])
        self.assertEqual(result, {'updated': 1, 'failed': 0})
        self.assertEqual(write.call_args.args[0].pk, zero.pk)
        self.assertEqual(write.call_args.args[1], 0)
