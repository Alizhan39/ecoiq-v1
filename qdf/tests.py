"""
Tests for the EcoIQ Quranic Decision Filter (QDF) module.

Covers: seed integrity, scoring + evidence gating, the red-line cap, the
decision engine (cards / queue / roadmap / scenario), the web pages, and the API.
"""
import json

from django.test import TestCase, SimpleTestCase
from django.urls import reverse

from qdf.scoring import (
    load_seed, ensure_questions, compute_for_profile, compute_and_save,
    compute_from_scores, get_or_compute, RED_LINE_KEYS, RED_LINE_CAP,
)
from qdf import engine


# ── Seed / schema integrity ─────────────────────────────────────────────────────

class SeedIntegrityTests(SimpleTestCase):
    REQUIRED = {'niyyah', 'halal', 'adl', 'rahmah', 'mizan',
                'amanah', 'maslahah', 'darar', 'shura', 'akhirah'}

    def test_seed_has_exactly_ten_questions(self):
        data = load_seed()
        keys = {q['key'] for q in data['questions']}
        self.assertEqual(keys, self.REQUIRED)
        self.assertEqual(len(data['questions']), 10)

    def test_every_question_fully_specified(self):
        data = load_seed()
        for q in data['questions']:
            for field in ('definition', 'plain_english', 'ai_prompt',
                          'evidence_required', 'red_flags', 'scoring_rubric',
                          'low_score_actions', 'example_company',
                          'example_policy', 'example_investment'):
                self.assertTrue(q.get(field), f'{q["key"]} missing {field}')

    def test_red_line_keys_present(self):
        self.assertEqual(RED_LINE_KEYS, {'halal', 'adl', 'darar'})


# ── Helpers ─────────────────────────────────────────────────────────────────────

def _make_profile(**overrides):
    from league.models import Company
    from companies.models import CompanyProfile
    co = Company.objects.create(name=overrides.pop('name', 'Test Co'),
                                slug=overrides.pop('slug', 'test-co'),
                                sector='energy', country='UK')
    defaults = dict(company=co, status='public')
    defaults.update(overrides)
    return CompanyProfile.objects.create(**defaults)


# ── Scoring ──────────────────────────────────────────────────────────────────────

class ScoringTests(TestCase):
    def test_ensure_questions_idempotent(self):
        from qdf.models import DecisionQuestion
        ensure_questions(); ensure_questions()
        self.assertEqual(DecisionQuestion.objects.count(), 10)

    def test_compute_for_profile_produces_ten_scores(self):
        p = _make_profile()
        result = compute_for_profile(p)
        self.assertEqual(len(result['questions']), 10)
        self.assertTrue(0 <= result['overall'] <= 100)
        for row in result['questions']:
            self.assertTrue(0 <= row['score'] <= 10)

    def test_low_evidence_yields_low_confidence(self):
        p = _make_profile()  # no sources, unverified
        result = compute_for_profile(p)
        self.assertLess(result['confidence'], 0.6)
        self.assertEqual(result['evidence_status'], 'unverified')

    def test_get_or_compute_persists_and_is_stable(self):
        from qdf.models import DecisionAssessment, QuestionScore
        p = _make_profile()
        a1 = get_or_compute(p)
        a2 = get_or_compute(p)
        self.assertEqual(a1.pk, a2.pk)
        self.assertEqual(DecisionAssessment.objects.filter(profile=p, source='auto').count(), 1)
        self.assertEqual(QuestionScore.objects.filter(assessment=a1).count(), 10)


class RedLineTests(TestCase):
    def test_red_line_caps_overall_score(self):
        ensure_questions()
        # Strong everywhere except a red-line dimension (adl) set to 1
        scores = {k: 9 for k in ('niyyah', 'halal', 'rahmah', 'mizan', 'amanah',
                                 'maslahah', 'darar', 'shura', 'akhirah')}
        scores['adl'] = 1
        result = compute_from_scores(scores, subject_name='X')
        self.assertTrue(result['red_line'])
        self.assertLessEqual(result['overall'], RED_LINE_CAP)
        self.assertEqual(result['verdict'], 'do_not_proceed')

    def test_no_red_line_when_all_strong(self):
        ensure_questions()
        result = compute_from_scores({k: 9 for k in (
            'niyyah', 'halal', 'adl', 'rahmah', 'mizan', 'amanah',
            'maslahah', 'darar', 'shura', 'akhirah')}, subject_name='X')
        self.assertFalse(result['red_line'])
        self.assertGreater(result['overall'], RED_LINE_CAP)


# ── Decision engine ──────────────────────────────────────────────────────────────

class EngineTests(TestCase):
    def setUp(self):
        self.profile = _make_profile()
        self.assessment = get_or_compute(self.profile)

    def test_cards_only_for_under_target(self):
        cards = engine.build_decision_cards(self.assessment, target=8.0)
        for c in cards:
            self.assertLess(c['current_score'], 8.0)
            self.assertIn('owner', c)
            self.assertGreaterEqual(c['expected_impact_points'], 0)

    def test_action_queue_sorted_by_priority(self):
        queue = engine.build_action_queue(self.assessment)
        priorities = [c['priority'] for c in queue]
        self.assertEqual(priorities, sorted(priorities, reverse=True))
        self.assertEqual([c['rank'] for c in queue], list(range(1, len(queue) + 1)))

    def test_roadmap_projects_upward(self):
        rm = engine.generate_roadmap(self.assessment)
        self.assertGreaterEqual(rm['target_integrity'], rm['baseline_integrity'])
        self.assertEqual(len(rm['trajectory']), 4)

    def test_scenario_redline_drops_score(self):
        sc = engine.simulate_scenario(self.assessment, {'darar': 1, 'adl': 1})
        self.assertTrue(sc['red_line'])
        self.assertLess(sc['delta'], 0)


# ── Web + API ────────────────────────────────────────────────────────────────────

class WebAndApiTests(TestCase):
    def setUp(self):
        self.profile = _make_profile(name='Web Co', slug='web-co')
        get_or_compute(self.profile)

    def test_dashboard_renders(self):
        resp = self.client.get('/decisions/', SERVER_NAME='localhost')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Stewardship Dashboard', resp.content)

    def test_engine_page_renders(self):
        resp = self.client.get('/decisions/web-co/', SERVER_NAME='localhost')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Action Queue', resp.content)
        self.assertIn(b'Create Rizq Without Zulm', resp.content)

    def test_scenario_via_querystring(self):
        resp = self.client.get('/decisions/web-co/?sim_adl=1&sim_darar=1',
                               SERVER_NAME='localhost')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'RED LINE BREACHED', resp.content)

    def test_api_questions_public(self):
        resp = self.client.get('/api/qdf/questions/', SERVER_NAME='localhost')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()['questions']), 10)

    def test_api_company_engine(self):
        resp = self.client.get('/api/qdf/companies/web-co/engine/',
                               SERVER_NAME='localhost')
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn('action_queue', body)
        self.assertIn('roadmap', body)

    def test_page_has_no_leaked_template_comments(self):
        resp = self.client.get('/decisions/web-co/', SERVER_NAME='localhost')
        html = resp.content.decode()
        self.assertNotIn('{#', html)
        self.assertNotIn('#}', html)
