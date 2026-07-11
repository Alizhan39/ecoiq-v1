from django.test import TestCase
from django.utils import timezone

from audit.ai_engine import apply_approved_findings
from audit.models import AIAnalysisJob, AIFinding, AIScoreEstimate
from evidence_memory.models import EvidenceMemory
from league.models import Company, Evidence


class ApplyApprovedFindingsTests(TestCase):
    """
    Phase 1A regression coverage for audit.ai_engine.apply_approved_findings —
    previously had zero test coverage, which is how a real bug (see
    test_missing_score_estimate_does_not_crash) went unnoticed.
    """

    def setUp(self):
        self.company = Company.objects.create(name='Audit Test Corp', sector='mining')
        self.job = AIAnalysisJob.objects.create(
            company=self.company, original_filename='report.pdf', status='completed',
            model_used='test-model', pages_analyzed=3, input_tokens=100, output_tokens=50,
            executive_summary='Summary of findings.', completed_at=timezone.now(),
        )

    def test_creates_evidence_for_the_analyzed_document(self):
        summary = apply_approved_findings(self.job, self.company)
        self.assertEqual(summary['evidence_created'], 1)
        self.assertTrue(Evidence.objects.filter(company=self.company).exists())

    def test_creates_project_from_approved_project_finding(self):
        AIFinding.objects.create(
            job=self.job, finding_type='project', title='Solar Rollout',
            description='Installed solar panels across 3 facilities.',
            status='approved', extra_data={'project_type': 'renewable', 'investment_usd': 500000},
        )
        summary = apply_approved_findings(self.job, self.company)
        self.assertEqual(summary['projects_created'], 1)

    def test_missing_score_estimate_does_not_crash(self):
        """
        Regression test: apply_approved_findings previously raised a bare
        NameError ('AIScoreEstimate' was referenced in an except clause but
        never imported) any time a job had no linked AIScoreEstimate — the
        common case, since a score estimate is optional. Fixed by importing
        AIScoreEstimate alongside the other local imports in this function.
        """
        summary = apply_approved_findings(self.job, self.company)
        self.assertEqual(summary['errors'], [])
        self.assertFalse(summary['score_applied'])

    def test_approved_score_estimate_is_applied(self):
        AIScoreEstimate.objects.create(
            job=self.job, est_pollution=80, est_reduction=70, est_investment=60,
            est_transparency=90, est_community=75, approved=True,
        )
        summary = apply_approved_findings(self.job, self.company)
        self.assertTrue(summary['score_applied'])
        self.company.refresh_from_db()
        self.assertEqual(self.company.score_pollution_footprint, 80)

    def test_evidence_synced_into_evidence_memory(self):
        apply_approved_findings(self.job, self.company)
        evidence = Evidence.objects.filter(company=self.company).first()
        self.assertTrue(
            EvidenceMemory.objects.filter(source_reference=f'league.Evidence:{evidence.pk}').exists()
        )
