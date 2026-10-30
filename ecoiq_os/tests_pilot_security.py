"""Stage 8: staging preflight, synthetic model guard, retention inventory."""
from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone

from api.models import (
    ProcessAIProcessingReadiness, ProcessAIReviewCase,
    ProcessAIReviewEvent, ProcessAnalysisRun,
)
from ecoiq_os.grounded_ai import prepare_grounded_draft
from ecoiq_os.pilot_evaluation import synthetic_pilot_benchmark
from ecoiq_os.pilot_retention import retention_inventory
from ecoiq_os.pilot_security import assess_pilot_preflight
from evidence_memory.models import EvidenceMemory
from gold_intelligence.models import GoldProject, ProjectMembership


def safe_config():
    return SimpleNamespace(
        DATABASES={"default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": "ecoiq_pilot_stage8",
        }},
        DEBUG=False, ALLOWED_HOSTS=["pilot-stage8.example.invalid"],
        AI_ENABLED=False, ECOIQ_GROUNDED_AI_EXTERNAL_ENABLED=False,
        ECOIQ_BILLING_PROVIDER="none",
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        SESSION_COOKIE_SECURE=True, CSRF_COOKIE_SECURE=True,
        SECURE_SSL_REDIRECT=True,
    )


def safe_env():
    return {
        "ECOIQ_PILOT_STAGING_MODE": "true",
        "ECOIQ_PILOT_SYNTHETIC_ONLY": "true",
        "ECOIQ_PILOT_PRIVATE_ACCESS_ATTESTED": "true",
        "ECOIQ_PILOT_DB_ISOLATION_ATTESTED": "true",
        "ECOIQ_PILOT_JOBS_DISABLED_ATTESTED": "true",
        "AI_ENABLED": "false",
        "ECOIQ_GROUNDED_AI_EXTERNAL_ENABLED": "false",
    }


class PilotPreflightTests(SimpleTestCase):
    def test_all_explicit_prerequisites_only_allow_synthetic_preflight(self):
        result = assess_pilot_preflight(safe_config(), safe_env())
        self.assertEqual(result["passed"], result["total"])
        self.assertTrue(result["ready_for_synthetic_staging_preflight"])
        self.assertFalse(result["cloud_isolation_independently_verified"])
        self.assertFalse(result["production_deployment_authorised"])
        self.assertFalse(result["customer_data_authorised"])
        self.assertFalse(result["external_model_transfer_authorised"])

    def test_missing_isolation_attestation_blocks(self):
        env = safe_env()
        env.pop("ECOIQ_PILOT_DB_ISOLATION_ATTESTED")
        result = assess_pilot_preflight(safe_config(), env)
        self.assertFalse(result["checks"]["separate_database_attested"])
        self.assertFalse(result["ready_for_synthetic_staging_preflight"])

    def test_production_host_or_database_blocks(self):
        config = safe_config()
        config.ALLOWED_HOSTS = ["ecoiq.uk"]
        config.DATABASES = {"default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": "ecoiq",
        }}
        result = assess_pilot_preflight(config, safe_env())
        self.assertFalse(result["checks"]["staging_only_hosts"])
        self.assertFalse(result["checks"]["separate_postgres_name"])
        self.assertFalse(result["ready_for_synthetic_staging_preflight"])

    def test_external_ai_billing_debug_or_network_flag_blocks(self):
        config = safe_config()
        config.AI_ENABLED = True
        config.ECOIQ_GROUNDED_AI_EXTERNAL_ENABLED = True
        config.ECOIQ_BILLING_PROVIDER = "stripe"
        config.DEBUG = True
        config.EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
        env = safe_env()
        env["ECOIQ_PILOT_PRIVATE_ACCESS_ATTESTED"] = "false"
        result = assess_pilot_preflight(config, env)
        for check in (
            "debug_disabled", "private_access_attested", "external_model_disabled",
            "all_gateway_models_disabled", "billing_disabled",
            "email_transport_disabled",
        ):
            with self.subTest(check=check):
                self.assertFalse(result["checks"][check])

    def test_overriding_environment_is_not_silently_ignored(self):
        env = safe_env()
        env["ECOIQ_GROUNDED_AI_EXTERNAL_ENABLED"] = "true"
        env["AI_ENABLED"] = "true"
        result = assess_pilot_preflight(safe_config(), env)
        self.assertFalse(result["checks"]["external_model_disabled"])
        self.assertFalse(result["checks"]["all_gateway_models_disabled"])

    def test_synthetic_citation_dataset_is_fully_deterministic(self):
        result = synthetic_pilot_benchmark()
        self.assertEqual(result["total"], 14)
        self.assertEqual(result["passed"], result["total"])
        self.assertEqual(result["model_calls"], 0)
        self.assertFalse(result["measures_model_accuracy"])
        self.assertFalse(result["safe_to_use_with_customers"])


@override_settings(ECOIQ_GROUNDED_AI_EXTERNAL_ENABLED=False)
class PilotNoExternalDataTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.project = GoldProject.objects.create(
            name="Fictional construction site",
            slug="synthetic-pilot-stage8", commodity="infrastructure", is_demo=True,
        )
        cls.analyst = get_user_model().objects.create_user(username="pilot-stage8-analyst")
        cls.reviewer = get_user_model().objects.create_user(username="pilot-stage8-reviewer")
        ProjectMembership.objects.create(
            project=cls.project, user=cls.analyst, role=ProjectMembership.Role.ANALYST,
        )
        cls.analysis = ProcessAnalysisRun.objects.create(
            project=cls.project, created_by=cls.analyst,
            case_id="SYN-8", domain="construction", process_name="Material delivery",
            resource_type="material", period="2026-10", unit="kg",
            file_fingerprint="8" * 64,
            summary={"kpi": {"numerator": 120, "denominator": 1000}},
        )

    def test_synthetic_pilot_never_contacts_gateway_even_when_requested(self):
        EvidenceMemory.objects.create(
            project=self.project, visibility="project_private",
            verification_status="verified",
            review_tier="independently_verified", reviewer=self.reviewer,
            is_demo=False, source_type="manual", source_reference="fixture:one",
            text_chunk="A fictional signed ledger records 1000 kg on the test day.",
        )
        gateway = Mock()
        result = prepare_grounded_draft(
            project=self.project, user=self.analyst, run=self.analysis,
            external_transfer_approved=True, gateway=gateway,
        )
        self.assertEqual(result["status"], "EXTERNAL_MODEL_DISABLED")
        self.assertFalse(result["model_called"])
        self.assertFalse(result["implementation_permitted"])
        gateway.chat.assert_not_called()

    def test_retention_report_counts_only_and_never_deletes(self):
        current = timezone.now()
        stale = current - timedelta(days=130)
        case = ProcessAIReviewCase.objects.create(
            project=self.project, analysis=self.analysis, submitted_by=self.analyst,
            questions=[{"question": "Could the dated stock records reconcile?"}],
            source_manifest=[], content_sha256="a" * 64,
        )
        ProcessAIReviewCase.objects.filter(pk=case.pk).update(created_at=stale)
        event = ProcessAIReviewEvent.objects.create(
            case=case, actor=self.analyst, action="submitted", content_sha256="a" * 64,
        )
        ProcessAIReviewEvent.objects.filter(pk=event.pk).update(created_at=stale)
        ProcessAIProcessingReadiness.objects.create(
            project=self.project, analysis=self.analysis, recorded_by=self.reviewer,
            source_rights_reviewed=True, privacy_reviewed=True,
            provider_terms_reviewed=True, expires_at=current - timedelta(days=3),
        )
        before = (
            ProcessAIReviewCase.objects.count(), ProcessAIReviewEvent.objects.count(),
            ProcessAIProcessingReadiness.objects.count(),
        )
        audit = retention_inventory(now=current)
        self.assertEqual(audit["pending_exceeding_target"], 1)
        self.assertEqual(audit["expired_readiness_records"], 1)
        self.assertEqual(audit["events_older_than_decided_target"], 1)
        self.assertFalse(audit["delete_performed"])
        self.assertFalse(audit["approved_purge_workflow_available"])
        self.assertEqual(before, (
            ProcessAIReviewCase.objects.count(), ProcessAIReviewEvent.objects.count(),
            ProcessAIProcessingReadiness.objects.count(),
        ))
        self.assertNotIn("Fictional construction site", str(audit))
