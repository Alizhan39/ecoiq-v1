"""
Core app tests — auth enforcement, share links, model integrity.
Run with: python manage.py test core --verbosity=2
"""
import uuid
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User

from .models import Assessment, Finding


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_assessment(company='Test Corp', status=Assessment.STATUS_COMPLETE):
    return Assessment.objects.create(company_name=company, status=status)


def _make_finding(assessment, overall=60):
    return Finding.objects.create(
        assessment=assessment,
        score_environment=55,
        score_social=60,
        score_governance=65,
        score_ethics=58,
        score_innovation=52,
        score_overall=overall,
        summary='Test summary paragraph.',
        pillar_notes={
            'environment': 'Env note.',
            'social':      'Social note.',
            'governance':  'Gov note.',
            'ethics':      'Ethics note.',
            'innovation':  'Innovation note.',
        },
    )


# ── Model tests ───────────────────────────────────────────────────────────────

class AssessmentModelTests(TestCase):

    def test_share_token_is_uuid(self):
        a = _make_assessment()
        self.assertIsNotNone(a.share_token)
        uuid.UUID(str(a.share_token))   # raises ValueError if malformed

    def test_share_tokens_are_unique(self):
        a1 = _make_assessment('Company A')
        a2 = _make_assessment('Company B')
        self.assertNotEqual(a1.share_token, a2.share_token)

    def test_str_repr(self):
        a = _make_assessment('ACME Refinery')
        self.assertIn('ACME Refinery', str(a))

    def test_finding_scores_stored(self):
        a = _make_assessment()
        f = _make_finding(a, overall=72)
        self.assertEqual(f.score_overall, 72)
        self.assertEqual(f.assessment, a)


# ── Public pages ──────────────────────────────────────────────────────────────

class PublicPageTests(TestCase):

    def setUp(self):
        self.c = Client(SERVER_NAME='localhost')

    def test_landing_200(self):
        self.assertEqual(self.c.get(reverse('home')).status_code, 200)

    def test_login_page_200(self):
        r = self.c.get(reverse('login'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Sign in')

    def test_request_access_200(self):
        self.assertEqual(self.c.get(reverse('leads:request_access')).status_code, 200)

    def test_success_page_200(self):
        self.assertEqual(self.c.get(reverse('leads:success')).status_code, 200)


# ── Auth enforcement ──────────────────────────────────────────────────────────

class AuthEnforcementTests(TestCase):
    """All internal ESG views must redirect anonymous users to /login/?next=…"""

    def setUp(self):
        self.c = Client(SERVER_NAME='localhost')
        self.assessment = _make_assessment()

    def _assert_login_redirect(self, url):
        r = self.c.get(url)
        self.assertEqual(r.status_code, 302,
                         msg=f"{url} should redirect anon to login, got {r.status_code}")
        self.assertIn('/login/', r['Location'])

    def test_esg_index_requires_login(self):
        self._assert_login_redirect(reverse('index'))

    def test_upload_requires_login(self):
        self._assert_login_redirect(reverse('upload'))

    def test_assessment_detail_requires_login(self):
        self._assert_login_redirect(
            reverse('assessment_detail', args=[self.assessment.pk]))

    def test_questionnaire_requires_login(self):
        self._assert_login_redirect(
            reverse('questionnaire', args=[self.assessment.pk]))

    def test_run_analysis_requires_login(self):
        self._assert_login_redirect(
            reverse('run_analysis', args=[self.assessment.pk]))

    def test_report_requires_login(self):
        _make_finding(self.assessment)
        self._assert_login_redirect(
            reverse('report', args=[self.assessment.pk]))

    def test_report_pdf_requires_login(self):
        _make_finding(self.assessment)
        self._assert_login_redirect(
            reverse('report_pdf', args=[self.assessment.pk]))


# ── Login flow ────────────────────────────────────────────────────────────────

class LoginFlowTests(TestCase):

    def setUp(self):
        self.c = Client(SERVER_NAME='localhost')
        self.user = User.objects.create_user(username='demo', password='testpass123')

    def test_valid_login_redirects_to_esg(self):
        r = self.c.post(reverse('login'), {
            'username': 'demo', 'password': 'testpass123',
        })
        self.assertEqual(r.status_code, 302)
        self.assertIn('/esg/', r['Location'])

    def test_invalid_login_stays_on_form(self):
        r = self.c.post(reverse('login'), {
            'username': 'demo', 'password': 'wrongpassword',
        })
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'incorrect')

    def test_logged_in_user_accesses_esg(self):
        self.c.login(username='demo', password='testpass123')
        self.assertEqual(self.c.get(reverse('index')).status_code, 200)

    def test_after_logout_esg_redirects(self):
        self.c.login(username='demo', password='testpass123')
        self.c.post(reverse('logout'))
        r = self.c.get(reverse('index'))
        self.assertEqual(r.status_code, 302)
        self.assertIn('/login/', r['Location'])


# ── Share links ───────────────────────────────────────────────────────────────

class ShareReportTests(TestCase):

    def setUp(self):
        self.c = Client(SERVER_NAME='localhost')
        self.assessment = _make_assessment()
        self.finding = _make_finding(self.assessment)

    def _share_url(self, assessment=None):
        a = assessment or self.assessment
        return reverse('share_report', kwargs={'token': a.share_token})

    def test_valid_token_is_public_200(self):
        r = self.c.get(self._share_url())
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, self.assessment.company_name)

    def test_shared_view_shows_print_not_share_button(self):
        r = self.c.get(self._share_url())
        # Share button and its JS handler must be absent in shared view
        self.assertNotContains(r, 'copyShareLink')
        self.assertNotContains(r, 'btn-share')
        self.assertContains(r, 'Print / Save as PDF')

    def test_invalid_uuid_token_returns_404(self):
        url = reverse('share_report', kwargs={'token': uuid.uuid4()})
        self.assertEqual(self.c.get(url).status_code, 404)

    def test_assessment_without_finding_returns_404(self):
        empty = _make_assessment('No Findings Ltd')
        self.assertEqual(self.c.get(self._share_url(empty)).status_code, 404)

    def test_shared_report_contains_overall_score(self):
        r = self.c.get(self._share_url())
        self.assertContains(r, str(self.finding.score_overall))

    def test_share_link_works_without_auth(self):
        # Explicitly not logged in — must still return 200
        self.c.logout()
        r = self.c.get(self._share_url())
        self.assertEqual(r.status_code, 200)


# ── Report context builder ────────────────────────────────────────────────────

class ReportContextBuilderTests(TestCase):

    def setUp(self):
        self.assessment = _make_assessment()
        _make_finding(self.assessment, overall=67)

    def test_ctx_has_required_keys(self):
        from .views import _build_report_ctx
        ctx = _build_report_ctx(self.assessment)
        for key in ('assessment', 'finding', 'pillars',
                    'radar_polygon', 'radar_grid', 'radar_axes', 'radar_labels', 'radar_dots'):
            self.assertIn(key, ctx, msg=f"Missing key: {key}")

    def test_five_pillars_returned(self):
        from .views import _build_report_ctx
        ctx = _build_report_ctx(self.assessment)
        self.assertEqual(len(ctx['pillars']), 5)
        names = [p['name'] for p in ctx['pillars']]
        self.assertIn('Environment', names)
        self.assertIn('Innovation', names)

    def test_radar_polygon_contains_coordinates(self):
        from .views import _build_report_ctx
        ctx = _build_report_ctx(self.assessment)
        polygon = ctx['radar_polygon']
        self.assertIsInstance(polygon, str)
        self.assertEqual(len(polygon.split(' ')), 5)   # 5 vertices

    def test_radar_dots_five_points(self):
        from .views import _build_report_ctx
        ctx = _build_report_ctx(self.assessment)
        dots = ctx['radar_dots']
        self.assertEqual(len(dots), 5)
        for x, y, score in dots:
            self.assertIsInstance(x, float)
            self.assertIsInstance(y, float)
            self.assertGreaterEqual(score, 0)
            self.assertLessEqual(score, 100)


# ── Audit auth enforcement ────────────────────────────────────────────────────

class AuditAuthTests(TestCase):
    """All audit views must redirect anonymous users to /login/"""

    def setUp(self):
        self.c = Client(SERVER_NAME='localhost')

    def _assert_login_redirect(self, url):
        r = self.c.get(url)
        self.assertEqual(r.status_code, 302,
                         msg=f"{url} should redirect anon to login, got {r.status_code}")
        self.assertIn('/login/', r['Location'])

    def test_audit_index_requires_login(self):
        self._assert_login_redirect('/audit/')

    def test_audit_upload_requires_login(self):
        self._assert_login_redirect('/audit/new/')

    def test_audit_detail_requires_login(self):
        self._assert_login_redirect('/audit/999/')

    def test_audit_questionnaire_requires_login(self):
        self._assert_login_redirect('/audit/999/questionnaire/')

    def test_audit_analyse_requires_login(self):
        self._assert_login_redirect('/audit/999/analyse/')

    def test_audit_report_requires_login(self):
        self._assert_login_redirect('/audit/999/report/')

    def test_audit_report_pdf_requires_login(self):
        self._assert_login_redirect('/audit/999/report/pdf/')
