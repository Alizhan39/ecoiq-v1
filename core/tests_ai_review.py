"""Stage 7 private human review, audit, CSRF, independence and provenance."""
import json
from datetime import date, timedelta
from unittest.mock import Mock

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from api.models import (
    ProcessAIProcessingReadiness, ProcessAIReviewCase, ProcessAIReviewEvent,
    ProcessAnalysisRun,
)
from ecoiq_os.grounded_ai import prepare_grounded_draft
from ecoiq_os.human_review import ReviewBlocked, queue_grounded_review
from evidence_memory.models import EvidenceMemory
from gold_intelligence.models import GoldProject, ProjectMembership


def _answer(quote="recorded receipt of 1000 kg"):
    return json.dumps({"questions": [{
        "question": "Could stock cutoffs explain the reported discrepancy?",
        "citations": [{"key": "S1", "quote": quote}],
    }]})


@override_settings(ALLOWED_HOSTS=["testserver"])
class HumanReviewWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.project = GoldProject.objects.create(
            name="Private Stage 7 project", slug="stage7-project",
            commodity="infrastructure", is_demo=False,
        )
        cls.other = GoldProject.objects.create(
            name="Other confidential project", slug="stage7-other",
            commodity="infrastructure", is_demo=False,
        )
        user_model = get_user_model()
        cls.analyst = user_model.objects.create_user(username="stage7-analyst")
        cls.reviewer = user_model.objects.create_user(username="stage7-reviewer")
        cls.manager = user_model.objects.create_user(username="stage7-manager")
        cls.viewer = user_model.objects.create_user(username="stage7-viewer")
        cls.stranger = user_model.objects.create_user(username="stage7-stranger")
        for user, role in (
            (cls.analyst, ProjectMembership.Role.ANALYST),
            (cls.reviewer, ProjectMembership.Role.REVIEWER),
            (cls.manager, ProjectMembership.Role.MANAGER),
            (cls.viewer, ProjectMembership.Role.VIEWER),
        ):
            ProjectMembership.objects.create(
                project=cls.project, user=user, role=role,
            )
        cls.analysis = ProcessAnalysisRun.objects.create(
            project=cls.project, created_by=cls.analyst,
            case_id="SYNTHETIC-1", domain="construction",
            process_name="Material handling", resource_type="material",
            period="2026-10", unit="kg", file_fingerprint="b" * 64,
            summary={"kpi": {"numerator": 120.0, "denominator": 1000.0}},
        )

    def setUp(self):
        self.source = EvidenceMemory.objects.create(
            project=self.project, source_type="manual",
            source_reference="synthetic:document-7",
            text_chunk="A signed synthetic ledger recorded receipt of 1000 kg during October.",
            visibility="project_private",
            verification_status="verified",
            review_tier="independently_verified",
            reviewer=self.reviewer, is_demo=False,
        )
        self.queue_url = reverse("ai_review_queue")

    def make_case(self, *, author=None, quote="recorded receipt of 1000 kg"):
        actor = author or self.analyst
        gateway = Mock()
        gateway.chat.return_value = {"answer": _answer(quote)}
        with override_settings(ECOIQ_GROUNDED_AI_EXTERNAL_ENABLED=True):
            validated = prepare_grounded_draft(
                project=self.project, user=actor, run=self.analysis,
                external_transfer_approved=True, gateway=gateway,
            )
        self.assertEqual(validated["status"], "REVIEW_REQUIRED")
        return queue_grounded_review(
            project=self.project, user=actor, run=self.analysis,
            model_result=validated,
        )

    def detail_url(self, case, *, project=None):
        return reverse("ai_review_detail", kwargs={
            "project_slug": (project or self.project).slug, "review_id": case.pk,
        })

    def test_queue_can_only_be_seeded_from_validated_internal_draft(self):
        case = self.make_case()
        self.assertEqual(case.status, ProcessAIReviewCase.Status.PENDING)
        self.assertEqual(case.submitted_by_id, self.analyst.pk)
        self.assertEqual(case.events.count(), 1)
        self.assertEqual(case.events.first().action, "submitted")
        self.assertNotIn("synthetic ledger recorded", str(case.source_manifest))
        self.assertFalse(hasattr(case, "implementation_permitted"))
        with self.assertRaises(ReviewBlocked):
            queue_grounded_review(
                project=self.project, user=self.analyst, run=self.analysis,
                model_result={"status": "REVIEW_REQUIRED", "questions": []},
            )

    def test_reviewer_only_queue_and_private_headers(self):
        case = self.make_case()
        self.client.force_login(self.reviewer)
        response = self.client.get(self.queue_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Private Stage 7 project")
        self.assertNotContains(response, "Other confidential project")
        self.assertContains(response, self.detail_url(case))
        self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(response["X-Robots-Tag"], "noindex, nofollow")
        self.assertNotContains(response, "googletagmanager.com")

        for actor in (self.viewer, self.analyst, self.stranger):
            self.client.force_login(actor)
            response = self.client.get(self.queue_url)
            self.assertNotContains(response, "Private Stage 7 project")
            self.assertNotContains(response, case.questions[0]["question"])

    def test_business_os_shows_review_link_only_to_authorised_reviewers(self):
        for actor, permitted in (
            (self.analyst, False), (self.viewer, False),
            (self.reviewer, True), (self.manager, True),
        ):
            with self.subTest(actor=actor.username):
                self.client.force_login(actor)
                page = self.client.get(reverse("process_workspace"))
                self.assertEqual(page.status_code, 200)
                self.assertEqual(
                    self.queue_url in page.content.decode("utf-8"), permitted,
                )

    def test_detail_requires_review_role_and_same_project(self):
        case = self.make_case()
        self.assertEqual(self.client.get(self.detail_url(case)).status_code, 302)
        for actor in (self.viewer, self.analyst, self.stranger):
            self.client.force_login(actor)
            self.assertEqual(self.client.get(self.detail_url(case)).status_code, 404)
        self.client.force_login(self.reviewer)
        self.assertEqual(self.client.get(self.detail_url(
            case, project=self.other,
        )).status_code, 404)
        detail = self.client.get(self.detail_url(case))
        self.assertContains(detail, "Current reviewed source excerpts")
        self.assertContains(detail, "UNTESTED")
        self.assertContains(detail, "Source quotes and their context checked")

    def test_second_person_accept_is_study_only_and_audited(self):
        case = self.make_case()
        self.client.force_login(self.reviewer)
        response = self.client.post(self.detail_url(case), {
            "action": "decision", "decision": "accept",
            "reason_code": "citations_checked",
        })
        self.assertEqual(response.status_code, 302)
        case.refresh_from_db()
        self.assertEqual(case.status, ProcessAIReviewCase.Status.ACCEPTED)
        self.assertEqual(case.reviewed_by_id, self.reviewer.pk)
        self.assertIsNotNone(case.reviewed_at)
        self.assertEqual(list(case.events.values_list("action", flat=True)),
                         ["submitted", "accept"])
        self.assertEqual(ProcessAIReviewEvent.objects.count(), 2)
        self.assertEqual(self.analysis.ai_review_cases.count(), 1)
        self.assertNotIn("implementation_permitted", case.questions[0]["citations"][0])
        replay = self.client.post(self.detail_url(case), {
            "action": "decision", "decision": "accept",
            "reason_code": "citations_checked",
        })
        self.assertEqual(replay.status_code, 409)
        self.assertEqual(case.events.count(), 2)

    def test_reject_and_needs_revision(self):
        for decision, expected in (
            ("reject", ProcessAIReviewCase.Status.REJECTED),
            ("revise", ProcessAIReviewCase.Status.REVISION),
        ):
            with self.subTest(decision=decision):
                case = self.make_case()
                self.client.force_login(self.reviewer)
                response = self.client.post(self.detail_url(case), {
                    "action": "decision", "decision": decision,
                    "reason_code": "needs_more_evidence",
                })
                self.assertEqual(response.status_code, 302)
                case.refresh_from_db()
                self.assertEqual(case.status, expected)

    def test_self_review_and_accept_without_citation_check_forbidden(self):
        case = self.make_case(author=self.manager)
        self.client.force_login(self.manager)
        self.assertEqual(self.client.post(self.detail_url(case), {
            "action": "decision", "decision": "accept",
            "reason_code": "citations_checked",
        }).status_code, 409)
        self.client.force_login(self.reviewer)
        self.assertEqual(self.client.post(self.detail_url(case), {
            "action": "decision", "decision": "accept",
            "reason_code": "needs_more_evidence",
        }).status_code, 409)
        self.assertEqual(case.events.count(), 1)

    def test_stale_or_revoked_evidence_blocks_review(self):
        case = self.make_case()
        EvidenceMemory.objects.filter(pk=self.source.pk).update(
            text_chunk="Silently changed evidence text",
        )
        self.client.force_login(self.reviewer)
        page = self.client.get(self.detail_url(case))
        self.assertContains(page, "Review blocked")
        self.assertNotContains(page, "Current reviewed source excerpts")
        posted = self.client.post(self.detail_url(case), {
            "action": "decision", "decision": "accept",
            "reason_code": "citations_checked",
        })
        self.assertEqual(posted.status_code, 409)
        self.assertEqual(case.events.count(), 1)

    def test_revoked_reviewer_cannot_read_or_decide(self):
        case = self.make_case()
        self.client.force_login(self.reviewer)
        ProjectMembership.objects.filter(
            project=self.project, user=self.reviewer,
        ).update(is_active=False)
        self.assertEqual(self.client.get(self.detail_url(case)).status_code, 404)
        self.assertNotContains(self.client.get(self.queue_url), "Private Stage 7 project")
        self.assertEqual(self.client.post(self.detail_url(case), {
            "action": "decision", "decision": "accept",
            "reason_code": "citations_checked",
        }).status_code, 404)

    def test_http_review_creation_not_exposed_and_unknown_post_rejected(self):
        case = self.make_case()
        self.client.force_login(self.reviewer)
        self.assertEqual(self.client.post(self.queue_url, {
            "questions": _answer(),
        }).status_code, 405)
        self.assertEqual(self.client.post(self.detail_url(case), {
            "action": "generate", "model_key": "secret",
        }).status_code, 409)
        self.assertEqual(self.client.post(self.detail_url(case), {
            "action": "decision", "decision": "accept",
            "reason_code": "citations_checked", "implementation_permitted": "true",
        }).status_code, 409)

    def test_csrf_required_for_decisions_and_readiness(self):
        case = self.make_case()
        strict = Client(enforce_csrf_checks=True)
        strict.force_login(self.reviewer)
        self.assertEqual(strict.post(self.detail_url(case), {
            "action": "decision", "decision": "accept",
            "reason_code": "citations_checked",
        }).status_code, 403)
        self.assertEqual(strict.post(self.detail_url(case), {
            "action": "readiness", "source_rights": "on",
            "privacy": "on", "provider_terms": "on",
        }).status_code, 403)

    def test_readiness_records_approval_checks_but_never_transfers(self):
        case = self.make_case()
        self.client.force_login(self.reviewer)
        bad = self.client.post(self.detail_url(case), {
            "action": "readiness", "source_rights": "on",
            "privacy": "on",
        })
        self.assertEqual(bad.status_code, 409)
        self.assertFalse(ProcessAIProcessingReadiness.objects.exists())
        good = self.client.post(self.detail_url(case), {
            "action": "readiness", "source_rights": "on",
            "privacy": "on", "provider_terms": "on",
        })
        self.assertEqual(good.status_code, 302)
        item = ProcessAIProcessingReadiness.objects.get()
        self.assertEqual(item.recorded_by_id, self.reviewer.pk)
        self.assertEqual(item.project_id, self.project.pk)
        self.assertFalse(item.authorises_external_transfer)
        self.assertTrue(timezone.now() < item.expires_at < timezone.now() + timedelta(days=8))
        self.client.force_login(self.stranger)
        self.assertEqual(self.client.get(self.detail_url(case)).status_code, 404)

    def test_escaped_source_preview_and_no_raw_html(self):
        self.source.text_chunk = (
            "<script>alert('xss')</script> synthetic source: "
            "recorded receipt of 1000 kg with documented notes."
        )
        self.source.save(update_fields=["text_chunk"])
        case = self.make_case()
        self.client.force_login(self.reviewer)
        response = self.client.get(self.detail_url(case))
        self.assertContains(response, "&lt;script&gt;alert")
        self.assertNotContains(response, "<script>alert")

    def test_expiry_and_downgrade_block_review(self):
        for field, value in (
            ("expiry_date", date(2020, 1, 1)),
            ("review_tier", "uploaded"),
            ("legal_status", "disputed"),
        ):
            with self.subTest(field=field):
                self.source.refresh_from_db()
                EvidenceMemory.objects.filter(pk=self.source.pk).update(
                    expiry_date=None, review_tier="independently_verified",
                    legal_status="",
                )
                case = self.make_case()
                EvidenceMemory.objects.filter(pk=self.source.pk).update(**{field: value})
                self.client.force_login(self.reviewer)
                self.assertEqual(self.client.post(self.detail_url(case), {
                    "action": "decision", "decision": "accept",
                    "reason_code": "citations_checked",
                }).status_code, 409)
