"""
Object-level access control for uploaded audit documents.

AuditSession and AIAnalysisJob both hold user-uploaded documents and the
analysis derived from them. These tests pin the ownership rules for every
route that can list, read, preview, analyse or mutate one, so the isolation
cannot silently regress.

Three realistic principals throughout: two ordinary users who must never see
each other's work, and one staff user who deliberately sees both.
"""
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from audit.models import (
    AuditSession, AuditReport, AIAnalysisJob, AIFinding, AIScoreEstimate,
)

User = get_user_model()

# A minimal well-formed PDF — enough for FileField storage. Never a real document.
_PDF_BYTES = b'%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n'


def _pdf(name):
    return SimpleUploadedFile(name, _PDF_BYTES, content_type='application/pdf')


@override_settings(SECURE_SSL_REDIRECT=False)
class DocumentAccessTestCase(TestCase):
    """
    Shared fixtures: alice, bob (ordinary), sam (staff), plus a legacy row.

    SECURE_SSL_REDIRECT is disabled for these tests only. settings.py turns it
    on whenever DEBUG is False, which makes the Django test client receive a
    301 to https for every request instead of reaching the view — so an
    access-control assertion would pass for the wrong reason. Overriding it
    here means these tests assert real authorisation behaviour under both
    DEBUG=True (the local convention) and DEBUG=False (what CI sets). No
    production setting is changed.
    """

    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user('alice', 'alice@example.com', 'pw-alice-1')
        cls.bob   = User.objects.create_user('bob',   'bob@example.com',   'pw-bob-1')
        cls.sam   = User.objects.create_user('sam',   'sam@example.com',   'pw-sam-1',
                                             is_staff=True)

        cls.alice_session = AuditSession.objects.create(
            facility_name='Alice Plant', sector='manufacturing',
            status='complete', created_by=cls.alice,
            extracted_text='ALICE-CONFIDENTIAL-TEXT',
            uploaded_file=_pdf('alice.pdf'),
        )
        cls.bob_session = AuditSession.objects.create(
            facility_name='Bob Refinery', sector='oil_gas',
            status='complete', created_by=cls.bob,
            extracted_text='BOB-CONFIDENTIAL-TEXT',
            uploaded_file=_pdf('bob.pdf'),
        )
        # Predates the owner field — ownership is not recoverable.
        cls.legacy_session = AuditSession.objects.create(
            facility_name='Legacy Works', sector='metals',
            status='complete', created_by=None,
            extracted_text='LEGACY-CONFIDENTIAL-TEXT',
        )
        for s in (cls.alice_session, cls.bob_session, cls.legacy_session):
            AuditReport.objects.create(session=s, executive_summary=f'Summary for {s.pk}')

        cls.alice_job = AIAnalysisJob.objects.create(
            pdf_file=_pdf('alice-job.pdf'), original_filename='alice-job.pdf',
            status='completed', submitted_by=cls.alice,
            executive_summary='ALICE-JOB-SUMMARY',
        )
        cls.bob_job = AIAnalysisJob.objects.create(
            pdf_file=_pdf('bob-job.pdf'), original_filename='bob-job.pdf',
            status='completed', submitted_by=cls.bob,
            executive_summary='BOB-JOB-SUMMARY',
        )
        cls.legacy_job = AIAnalysisJob.objects.create(
            pdf_file=_pdf('legacy-job.pdf'), original_filename='legacy-job.pdf',
            status='completed', submitted_by=None,
        )

        cls.alice_finding = AIFinding.objects.create(
            job=cls.alice_job, finding_type='co2_metric',
            title='ALICE-FINDING', description='x', confidence_score=0.9,
        )
        cls.bob_finding = AIFinding.objects.create(
            job=cls.bob_job, finding_type='co2_metric',
            title='BOB-FINDING', description='x', confidence_score=0.9,
        )
        cls.bob_score = AIScoreEstimate.objects.create(job=cls.bob_job, confidence=0.8)

    def login(self, user):
        self.client.force_login(user)


# ── 1. Unauthenticated ────────────────────────────────────────────────────────

class UnauthenticatedAccessTests(DocumentAccessTestCase):

    def test_every_document_route_requires_login(self):
        s, j, f = self.bob_session.pk, self.bob_job.pk, self.bob_finding.pk
        routes = [
            reverse('audit_index'),
            reverse('audit_upload'),
            reverse('audit_detail',        args=[s]),
            reverse('audit_questionnaire', args=[s]),
            reverse('audit_analyse',       args=[s]),
            reverse('audit_report',        args=[s]),
            reverse('audit_report_pdf',    args=[s]),
            reverse('ai_jobs'),
            reverse('ai_job_detail',      args=[j]),
            reverse('ai_job_run',         args=[j]),
            reverse('ai_job_apply',       args=[j]),
            reverse('ai_score_action',    args=[j]),
            reverse('ai_bulk_action',     args=[j]),
            reverse('ai_job_save_note',   args=[j]),
            reverse('ai_job_set_company', args=[j]),
            reverse('ai_finding_action',  args=[f]),
        ]
        for url in routes:
            with self.subTest(url=url):
                resp = self.client.get(url)
                self.assertIn(resp.status_code, (302, 405),
                              f'{url} did not require authentication')
                if resp.status_code == 302:
                    self.assertIn('/login', resp['Location'])


# ── 2 & 3. AuditSession isolation ─────────────────────────────────────────────

class AuditSessionOwnerIsolationTests(DocumentAccessTestCase):

    def test_owner_can_list_and_open_own_session(self):
        self.login(self.alice)
        listing = self.client.get(reverse('audit_index'))
        self.assertEqual(listing.status_code, 200)
        self.assertContains(listing, 'Alice Plant')
        for name in ('audit_detail', 'audit_questionnaire', 'audit_report'):
            with self.subTest(view=name):
                r = self.client.get(reverse(name, args=[self.alice_session.pk]))
                self.assertEqual(r.status_code, 200)

    def test_list_excludes_other_users_sessions(self):
        self.login(self.alice)
        listing = self.client.get(reverse('audit_index'))
        self.assertNotContains(listing, 'Bob Refinery')
        self.assertNotContains(listing, 'Legacy Works')

    def test_cannot_read_another_users_session_metadata(self):
        self.login(self.alice)
        for name in ('audit_detail', 'audit_questionnaire', 'audit_report'):
            with self.subTest(view=name):
                r = self.client.get(reverse(name, args=[self.bob_session.pk]))
                self.assertEqual(r.status_code, 404)

    def test_cannot_download_another_users_report_pdf(self):
        self.login(self.alice)
        r = self.client.get(reverse('audit_report_pdf', args=[self.bob_session.pk]))
        self.assertEqual(r.status_code, 404)

    def test_cannot_analyse_another_users_session(self):
        # analyse is staff-only; an ordinary user is redirected, never served.
        self.login(self.alice)
        r = self.client.get(reverse('audit_analyse', args=[self.bob_session.pk]))
        self.assertEqual(r.status_code, 302)
        self.assertNotIn('BOB-CONFIDENTIAL-TEXT', r.content.decode(errors='ignore'))

    def test_id_enumeration_reveals_only_own_sessions(self):
        self.login(self.alice)
        for pk in AuditSession.objects.values_list('pk', flat=True):
            r = self.client.get(reverse('audit_detail', args=[pk]))
            expected = 200 if pk == self.alice_session.pk else 404
            self.assertEqual(r.status_code, expected,
                             f'session pk={pk} returned {r.status_code}')

    def test_upload_records_the_owner(self):
        self.login(self.alice)
        self.client.post(reverse('audit_upload'), {
            'facility_name': 'Newly Uploaded', 'sector': 'manufacturing',
            'location': '', 'notes': '',
        })
        created = AuditSession.objects.get(facility_name='Newly Uploaded')
        self.assertEqual(created.created_by, self.alice)


# ── 4–7. AIAnalysisJob isolation, including every mutating action ─────────────

class AIAnalysisJobOwnerIsolationTests(DocumentAccessTestCase):

    def test_owner_can_list_and_open_own_job(self):
        self.login(self.alice)
        listing = self.client.get(reverse('ai_jobs'))
        self.assertEqual(listing.status_code, 200)
        self.assertContains(listing, 'alice-job.pdf')
        detail = self.client.get(reverse('ai_job_detail', args=[self.alice_job.pk]))
        self.assertEqual(detail.status_code, 200)

    def test_list_excludes_other_users_jobs(self):
        self.login(self.alice)
        listing = self.client.get(reverse('ai_jobs'))
        self.assertNotContains(listing, 'bob-job.pdf')
        self.assertNotContains(listing, 'legacy-job.pdf')

    def test_cannot_read_another_users_job_metadata(self):
        self.login(self.alice)
        r = self.client.get(reverse('ai_job_detail', args=[self.bob_job.pk]))
        self.assertEqual(r.status_code, 404)

    def test_cannot_trigger_analysis_on_another_users_job(self):
        # Staff-only route: an ordinary user is redirected before any AI call.
        self.login(self.alice)
        r = self.client.post(reverse('ai_job_run', args=[self.bob_job.pk]))
        self.assertEqual(r.status_code, 302)
        self.bob_job.refresh_from_db()
        self.assertEqual(self.bob_job.status, 'completed')

    def test_every_mutating_action_is_denied_and_changes_nothing(self):
        """Each mutating route must 404 AND leave the target untouched."""
        self.login(self.alice)
        job = self.bob_job
        before_notes   = job.analyst_notes
        before_company = job.company_id
        before_status  = self.bob_finding.status
        before_score   = self.bob_score.approved

        cases = [
            ('ai_job_apply',       {'company_id': ''}),
            ('ai_score_action',    {'action': 'approve'}),
            ('ai_bulk_action',     {'action': 'approve_all'}),
            ('ai_job_save_note',   {'analyst_notes': 'INJECTED BY ALICE'}),
            ('ai_job_set_company', {'company_id': ''}),
        ]
        for name, payload in cases:
            with self.subTest(action=name):
                r = self.client.post(reverse(name, args=[job.pk]), payload)
                self.assertEqual(r.status_code, 404, f'{name} was not denied')

        job.refresh_from_db()
        self.bob_finding.refresh_from_db()
        self.bob_score.refresh_from_db()
        self.assertEqual(job.analyst_notes, before_notes)
        self.assertEqual(job.company_id, before_company)
        self.assertEqual(self.bob_finding.status, before_status)
        self.assertEqual(self.bob_score.approved, before_score)


# ── 8 & 9. Nested identifiers and document-derived findings ───────────────────

class NestedIdentifierBypassTests(DocumentAccessTestCase):

    def test_finding_id_cannot_bypass_job_ownership(self):
        self.login(self.alice)
        r = self.client.post(reverse('ai_finding_action', args=[self.bob_finding.pk]),
                             {'action': 'approve'})
        self.assertEqual(r.status_code, 404)
        self.bob_finding.refresh_from_db()
        self.assertEqual(self.bob_finding.status, 'pending')

    def test_findings_inherit_source_document_restrictions(self):
        """A finding is only reachable through a job the caller may see."""
        self.login(self.alice)
        r = self.client.get(reverse('ai_job_detail', args=[self.bob_job.pk]))
        self.assertEqual(r.status_code, 404)
        own = self.client.get(reverse('ai_job_detail', args=[self.alice_job.pk]))
        self.assertContains(own, 'ALICE-FINDING')
        self.assertNotContains(own, 'BOB-FINDING')

    def test_finding_id_enumeration_reveals_only_own_findings(self):
        self.login(self.alice)
        for pk in AIFinding.objects.values_list('pk', flat=True):
            r = self.client.post(reverse('ai_finding_action', args=[pk]),
                                 {'action': 'approve'})
            if pk == self.alice_finding.pk:
                self.assertEqual(r.status_code, 302)
            else:
                self.assertEqual(r.status_code, 404)


# ── 10. Legacy ownerless rows fail closed ─────────────────────────────────────

class LegacyOwnerlessRowTests(DocumentAccessTestCase):

    def test_ordinary_users_cannot_reach_legacy_session(self):
        for user in (self.alice, self.bob):
            with self.subTest(user=user.username):
                self.login(user)
                r = self.client.get(reverse('audit_detail', args=[self.legacy_session.pk]))
                self.assertEqual(r.status_code, 404)
                pdf = self.client.get(reverse('audit_report_pdf',
                                              args=[self.legacy_session.pk]))
                self.assertEqual(pdf.status_code, 404)

    def test_ordinary_users_cannot_reach_legacy_job(self):
        self.login(self.alice)
        r = self.client.get(reverse('ai_job_detail', args=[self.legacy_job.pk]))
        self.assertEqual(r.status_code, 404)

    def test_legacy_rows_absent_from_ordinary_user_lists(self):
        self.login(self.alice)
        self.assertNotContains(self.client.get(reverse('audit_index')), 'Legacy Works')
        self.assertNotContains(self.client.get(reverse('ai_jobs')), 'legacy-job.pdf')

    def test_staff_retain_access_to_legacy_rows(self):
        self.login(self.sam)
        self.assertEqual(
            self.client.get(reverse('audit_detail', args=[self.legacy_session.pk])).status_code,
            200)
        self.assertEqual(
            self.client.get(reverse('ai_job_detail', args=[self.legacy_job.pk])).status_code,
            200)


# ── 11. Explicit staff policy ─────────────────────────────────────────────────

class StaffAccessPolicyTests(DocumentAccessTestCase):

    def test_staff_see_every_users_sessions_and_jobs_in_lists(self):
        self.login(self.sam)
        sessions = self.client.get(reverse('audit_index'))
        self.assertContains(sessions, 'Alice Plant')
        self.assertContains(sessions, 'Bob Refinery')
        jobs = self.client.get(reverse('ai_jobs'))
        self.assertContains(jobs, 'alice-job.pdf')
        self.assertContains(jobs, 'bob-job.pdf')

    def test_staff_can_open_any_users_detail(self):
        self.login(self.sam)
        for pk in (self.alice_session.pk, self.bob_session.pk):
            self.assertEqual(
                self.client.get(reverse('audit_detail', args=[pk])).status_code, 200)
        for pk in (self.alice_job.pk, self.bob_job.pk):
            self.assertEqual(
                self.client.get(reverse('ai_job_detail', args=[pk])).status_code, 200)

    def test_staff_only_routes_reject_ordinary_users(self):
        self.login(self.alice)
        for url in (reverse('audit_analyse', args=[self.alice_session.pk]),
                    reverse('ai_job_run',    args=[self.alice_job.pk])):
            with self.subTest(url=url):
                r = self.client.get(url)
                self.assertEqual(r.status_code, 302)
                self.assertIn('/login', r['Location'])


# ── 12. Cache isolation ───────────────────────────────────────────────────────

class DocumentCacheIsolationTests(DocumentAccessTestCase):

    def test_no_document_view_is_wrapped_in_a_shared_response_cache(self):
        """
        companies.throttle.cache_response keys purely on the request path, which
        is correct for company/sector artifacts but would leak private documents
        between users. Assert it is not applied to any audit/core document view.
        """
        import audit.views as av
        import core.views as cv

        watched = [
            (av, ['index', 'detail', 'report', 'report_pdf', 'questionnaire',
                  'ai_jobs', 'ai_job_detail']),
            (cv, ['questionnaire']),
        ]
        for module, names in watched:
            for name in names:
                view = getattr(module, name, None)
                if view is None:
                    continue
                with self.subTest(view=f'{module.__name__}.{name}'):
                    chain = []
                    fn = view
                    for _ in range(10):
                        chain.append(getattr(fn, '__qualname__', ''))
                        fn = getattr(fn, '__wrapped__', None)
                        if fn is None:
                            break
                    self.assertNotIn(
                        'cache_response', ' '.join(chain),
                        f'{module.__name__}.{name} is wrapped in a path-keyed cache',
                    )

    def test_two_users_never_receive_each_others_document_content(self):
        """Same URL, two users — the second must not be served the first's data."""
        url = reverse('audit_detail', args=[self.alice_session.pk])
        self.login(self.alice)
        first = self.client.get(url)
        self.assertEqual(first.status_code, 200)

        self.client.logout()
        self.login(self.bob)
        second = self.client.get(url)
        self.assertEqual(second.status_code, 404)
        self.assertNotIn('ALICE-CONFIDENTIAL-TEXT', second.content.decode(errors='ignore'))


# ── AI context ownership ──────────────────────────────────────────────────────

class AIContextOwnershipTests(DocumentAccessTestCase):

    def test_ai_analysis_routes_resolve_through_the_scoped_queryset(self):
        """
        The two routes that build an AI context from a document (`analyse`,
        `ai_job_run`) must re-check access server-side at object resolution —
        not rely on the staff decorator alone.
        """
        import inspect
        import audit.views as av
        for name, helper in (('analyse', '_audit_sessions_visible_to'),
                             ('ai_job_run', '_ai_jobs_visible_to')):
            with self.subTest(view=name):
                src = inspect.getsource(getattr(av, name))
                self.assertIn(f'{helper}(request.user)', src,
                              f'{name} does not resolve its object through {helper}')


# ── 13. Existing authorised flows still work ──────────────────────────────────

class AuthorisedWorkflowRegressionTests(DocumentAccessTestCase):

    def test_owner_end_to_end_session_flow(self):
        self.login(self.alice)
        pk = self.alice_session.pk
        self.assertEqual(self.client.get(reverse('audit_index')).status_code, 200)
        self.assertEqual(self.client.get(reverse('audit_questionnaire', args=[pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse('audit_detail', args=[pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse('audit_report',  args=[pk])).status_code, 200)

    def test_owner_can_act_on_own_job(self):
        self.login(self.alice)
        r = self.client.post(reverse('ai_job_save_note', args=[self.alice_job.pk]),
                             {'analyst_notes': 'my own note'})
        self.assertEqual(r.status_code, 200)
        self.alice_job.refresh_from_db()
        self.assertEqual(self.alice_job.analyst_notes, 'my own note')

    def test_owner_can_approve_own_finding(self):
        self.login(self.alice)
        r = self.client.post(reverse('ai_finding_action', args=[self.alice_finding.pk]),
                             {'action': 'approve'})
        self.assertEqual(r.status_code, 302)
        self.alice_finding.refresh_from_db()
        self.assertEqual(self.alice_finding.status, 'approved')
        self.assertEqual(self.alice_finding.reviewed_by, self.alice)

    def test_staff_can_still_run_the_full_review_workflow(self):
        self.login(self.sam)
        r = self.client.post(reverse('ai_bulk_action', args=[self.bob_job.pk]),
                             {'action': 'approve_all'})
        self.assertEqual(r.status_code, 302)
        self.bob_finding.refresh_from_db()
        self.assertEqual(self.bob_finding.status, 'approved')
