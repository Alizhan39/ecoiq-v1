"""Stage 3: access-controlled CSV upload and immutable private history."""
import json

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from api.models import ProcessAnalysisRun
from gold_intelligence.models import GoldProject, ProjectMembership


HEADER = ",".join((
    "record_id", "case_id", "domain", "process_name", "resource_type",
    "period", "unit", "flow_type", "quantity", "evidence_ref",
))


def csv_bytes(case="PRIVATE-CASE-1", loss="120", source="SECRET-DOC-1"):
    rows = [
        f"I1,{case},construction,Delivery,material,2026-10,kg,input,1000,{source}",
        f"L1,{case},construction,Delivery,material,2026-10,kg,loss,{loss},WASTE-REF-1",
    ]
    return (HEADER + "\n" + "\n".join(rows) + "\n").encode("utf-8")


def upload(data=None):
    return SimpleUploadedFile(
        "process.csv", data if data is not None else csv_bytes(),
        content_type="text/csv",
    )


@override_settings(ALLOWED_HOSTS=["testserver"])
class ProjectProcessHistoryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.p1 = GoldProject.objects.create(
            name="Private construction site", slug="construction-private-1",
            commodity="infrastructure", is_demo=False,
        )
        cls.p2 = GoldProject.objects.create(
            name="Other private site", slug="construction-private-2",
            commodity="infrastructure", is_demo=False,
        )
        users = {}
        for role in ProjectMembership.Role.values:
            u = get_user_model().objects.create_user(username=f"csv-{role}")
            ProjectMembership.objects.create(project=cls.p1, user=u, role=role)
            users[role] = u
        cls.users = users
        cls.stranger = get_user_model().objects.create_user(username="csv-stranger")
        cls.staff = get_user_model().objects.create_user(username="csv-staff", is_staff=True)

    def setUp(self):
        cache.clear()
        self.list_url = reverse(
            "api_v2:process_analyses", kwargs={"project_slug": self.p1.slug},
        )

    def _post(self, user, data=None, *, path=None, extra=None):
        self.client.logout()
        if user:
            self.client.force_login(user)
        payload = {"file": upload(data)}
        if extra:
            payload.update(extra)
        return self.client.post(path or self.list_url, payload)

    def test_analyst_can_upload_and_list_their_project(self):
        response = self._post(self.users["analyst"])
        self.assertEqual(response.status_code, 201, response.content)
        record = ProcessAnalysisRun.objects.get()
        self.assertEqual(record.project_id, self.p1.pk)
        self.assertEqual(record.created_by_id, self.users["analyst"].pk)
        self.assertEqual(record.summary["kpi"]["value"], 12)
        self.assertEqual(record.summary["next_stage"], "COLLECT_EVIDENCE")
        self.assertEqual(record.summary["import"]["source_authentication"], "NOT_VERIFIED")
        self.assertEqual(record.summary["import"]["raw_csv_stored"], False)
        self.assertEqual(len(record.file_fingerprint), 64)
        stored = json.dumps(record.summary)
        self.assertNotIn("SECRET-DOC-1", stored)
        self.assertNotIn("WASTE-REF-1", stored)

        listed = self.client.get(self.list_url)
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()["count"], 1)
        self.assertEqual(listed["Cache-Control"], "private, no-store, max-age=0")
        detail = self.client.get(reverse(
            "api_v2:process_analysis_detail",
            kwargs={"project_slug": self.p1.slug, "run_id": record.pk},
        ))
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["analysis"]["result"]["kpi"]["value"], 12)
        self.assertNotIn("file_fingerprint", detail.content.decode())

    def test_history_pages_are_bounded(self):
        self.assertEqual(self._post(self.users["analyst"]).status_code, 201)
        self.client.force_login(self.users["viewer"])
        self.assertEqual(self.client.get(self.list_url).json()["page"], 1)
        empty_second_page = self.client.get(self.list_url + "?page=2")
        self.assertEqual(empty_second_page.status_code, 200)
        self.assertEqual(empty_second_page.json()["results"], [])
        self.assertFalse(empty_second_page.json()["has_more"])
        self.assertEqual(self.client.get(self.list_url + "?page=0").status_code, 400)
        self.assertEqual(self.client.get(self.list_url + "?page=foo").status_code, 400)

    def test_history_cannot_be_deleted_or_edited_via_api(self):
        self.assertEqual(self._post(self.users["analyst"]).status_code, 201)
        run = ProcessAnalysisRun.objects.get()
        detail_url = reverse("api_v2:process_analysis_detail", kwargs={
            "project_slug": self.p1.slug, "run_id": run.pk,
        })
        self.assertEqual(self.client.delete(detail_url).status_code, 405)
        self.assertEqual(self.client.patch(detail_url, data={"verified": True},
                                           content_type="application/json").status_code, 405)
        self.assertEqual(ProcessAnalysisRun.objects.count(), 1)

    def test_revocation_before_persistence_blocks_write(self):
        from unittest.mock import patch
        self.client.force_login(self.users["analyst"])
        with patch("api.v2_process_analyses.access.can", return_value=False):
            response = self.client.post(self.list_url, {"file": upload()})
        self.assertEqual(response.status_code, 404)
        self.assertFalse(ProcessAnalysisRun.objects.exists())

    def test_duplicate_file_is_idempotent(self):
        actor = self.users["analyst"]
        self.assertEqual(self._post(actor).status_code, 201)
        response = self._post(actor)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["created"])
        self.assertEqual(ProcessAnalysisRun.objects.count(), 1)

    def test_viewer_and_reviewer_may_read_but_not_upload(self):
        self.assertEqual(self._post(self.users["analyst"]).status_code, 201)
        for role in ("viewer", "reviewer"):
            self.client.force_login(self.users[role])
            with self.subTest(role=role):
                self.assertEqual(self.client.get(self.list_url).status_code, 200)
                self.assertEqual(self._post(self.users[role]).status_code, 404)

    def test_manager_can_upload(self):
        response = self._post(self.users["manager"])
        self.assertEqual(response.status_code, 201)

    def test_staff_may_access_explicit_projects(self):
        response = self._post(self.staff)
        self.assertEqual(response.status_code, 201)
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(self.list_url).status_code, 200)

    def test_unauthenticated_and_stranger_cannot_access(self):
        for actor in (None, self.stranger):
            self.client.logout()
            if actor:
                self.client.force_login(actor)
            with self.subTest(actor=actor):
                self.assertIn(self.client.get(self.list_url).status_code, (403, 404))
                self.assertIn(self.client.post(self.list_url, {"file": upload()}).status_code, (403, 404))
        self.assertFalse(ProcessAnalysisRun.objects.exists())

    def test_another_project_is_invisible(self):
        self.assertEqual(self._post(self.users["analyst"]).status_code, 201)
        other_url = reverse(
            "api_v2:process_analyses", kwargs={"project_slug": self.p2.slug},
        )
        self.client.force_login(self.users["analyst"])
        self.assertEqual(self.client.get(other_url).status_code, 404)
        self.assertEqual(self._post(self.users["analyst"], path=other_url).status_code, 404)
        record = ProcessAnalysisRun.objects.get()
        wrong_detail = reverse("api_v2:process_analysis_detail", kwargs={
            "project_slug": self.p2.slug, "run_id": record.pk,
        })
        self.assertEqual(self.client.get(wrong_detail).status_code, 404)

    def test_role_revocation_blocks_existing_history(self):
        self.assertEqual(self._post(self.users["analyst"]).status_code, 201)
        self.client.force_login(self.users["analyst"])
        ProjectMembership.objects.filter(project=self.p1, user=self.users["analyst"]).update(
            is_active=False,
        )
        self.assertEqual(self.client.get(self.list_url).status_code, 404)
        self.assertEqual(self._post(self.users["analyst"]).status_code, 404)

    def test_demotion_to_viewer_blocks_new_upload(self):
        self.assertEqual(self._post(self.users["analyst"]).status_code, 201)
        ProjectMembership.objects.filter(project=self.p1, user=self.users["analyst"]).update(
            role="viewer",
        )
        self.assertEqual(self._post(self.users["analyst"], csv_bytes(loss="50")).status_code, 404)
        self.client.force_login(self.users["analyst"])
        self.assertEqual(self.client.get(self.list_url).json()["count"], 1)

    def test_reject_spoofed_actor_or_causal_status(self):
        for payload in (
            {"created_by": str(self.staff.pk)},
            {"project_id": str(self.p2.pk)},
            {"hypothesis_status": "REPLICATED_CAUSAL_SUPPORT"},
            {"verified": "true"},
        ):
            with self.subTest(payload=payload):
                response = self._post(self.users["analyst"], extra=payload)
                self.assertEqual(response.status_code, 400)
        self.assertFalse(ProcessAnalysisRun.objects.exists())

    def test_csv_validation_failure_writes_no_record(self):
        self.assertEqual(self._post(self.users["analyst"], b"not-valid-csv").status_code, 400)
        self.assertEqual(self._post(self.users["analyst"], b"\xff\xfe").status_code, 400)
        self.assertFalse(ProcessAnalysisRun.objects.exists())

    def test_oversized_file_rejected_without_persistence(self):
        self.assertEqual(
            self._post(self.users["analyst"], b"x" * (512 * 1024 + 1)).status_code, 400,
        )
        self.assertFalse(ProcessAnalysisRun.objects.exists())

    def test_missing_file_rejected(self):
        self.client.force_login(self.users["analyst"])
        result = self.client.post(self.list_url, {"case_id": "PRIVATE-CASE-1"})
        self.assertEqual(result.status_code, 400)
        self.assertFalse(ProcessAnalysisRun.objects.exists())

    def test_session_csrf_is_enforced(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.users["analyst"])
        response = csrf_client.post(self.list_url, {"file": upload()})
        self.assertEqual(response.status_code, 403)
        self.assertFalse(ProcessAnalysisRun.objects.exists())

    def test_file_is_not_added_to_model_or_public_urls(self):
        self.assertEqual(self._post(self.users["analyst"]).status_code, 201)
        obj = ProcessAnalysisRun.objects.get()
        self.assertFalse(hasattr(obj, "uploaded_file"))
        self.assertFalse(hasattr(obj, "original_csv"))
        self.client.logout()
        for path in (self.list_url, reverse(
            "api_v2:process_analysis_detail",
            kwargs={"project_slug": self.p1.slug, "run_id": obj.pk},
        )):
            self.assertNotEqual(self.client.get(path).status_code, 200)
