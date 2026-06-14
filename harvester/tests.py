"""
Evidence Harvester — Slice 1 tests (models + Source Registry).

Covers exactly what Slice 1 ships: the four additive models, the controlled
vocabularies, the dedup hash, and the idempotent source-registry seed command.
No harvesting / verification / normalization logic exists yet — those are later
slices and are not tested here.
"""
from io import StringIO

from django.test import TestCase
from django.core.management import call_command

from league.models import Company
from companies.models import CompanyProfile
from harvester.models import Source, HarvestJob, Evidence, Datapoint, content_hash
from harvester.constants import (
    EVIDENCE_CATEGORIES, VERIFICATION_STATUSES, SOURCE_TYPES, FUTURE_SOURCE_TYPES,
)
from harvester.source_registry import CATALOG, catalog_rows


def make_company(slug="national-grid"):
    company = Company.objects.create(name="National Grid plc", slug=slug,
                                     sector="energy", country="GB")
    profile = CompanyProfile.objects.create(company=company, status="public")
    return company, profile


# ── Vocabularies ─────────────────────────────────────────────────────────────
class VocabularyTests(TestCase):
    def test_25_evidence_categories(self):
        self.assertEqual(len(EVIDENCE_CATEGORIES), 25)
        # required anchors present
        vals = {c[0] for c in EVIDENCE_CATEGORIES}
        for needed in ("financial", "emissions", "climate", "water",
                       "cybersecurity", "contradictions"):
            self.assertIn(needed, vals)

    def test_absence_markers_exist(self):
        statuses = {s[0] for s in VERIFICATION_STATUSES}
        self.assertIn("NOT_FOUND", statuses)
        self.assertIn("INSUFFICIENT_EVIDENCE", statuses)
        self.assertIn("VERIFIED", statuses)
        self.assertIn("CONTRADICTED", statuses)

    def test_source_types_cover_request(self):
        vals = {s[0] for s in SOURCE_TYPES}
        for needed in ("annual_report", "companies_house", "ofgem", "cdp",
                       "sbti", "msci", "sustainalytics", "refinitiv"):
            self.assertIn(needed, vals)


# ── Models ───────────────────────────────────────────────────────────────────
class ModelTests(TestCase):
    def test_create_full_chain(self):
        company, profile = make_company()
        src = Source.objects.create(
            name="Annual Report", source_type="annual_report",
            source_owner="Company", confidence_base=0.85,
            update_frequency="annual", company=profile,
        )
        job = HarvestJob.objects.create(company=profile, company_slug="national-grid")
        ev = Evidence.objects.create(
            company=profile, company_slug="national-grid", source=src, harvest_job=job,
            title="FY2025 Results", url="https://example.com/fy25",
            category="financial", excerpt="Gross revenue 18,378",
        )
        dp = Datapoint.objects.create(
            evidence=ev, company=profile, company_slug="national-grid",
            metric="gross_revenue", value=18378.0, unit="GBP_million",
            period_year=2025, category="financial", confidence=0.9,
        )
        self.assertEqual(ev.verification_status, "UNVERIFIED")  # default before engine
        self.assertEqual(dp.evidence_id, ev.id)
        self.assertEqual(ev.source.confidence_base, 0.85)

    def test_dedup_hash_is_stable_and_distinct(self):
        h1 = content_hash("national-grid", "emissions", "u", "t", "e")
        h2 = content_hash("national-grid", "emissions", "u", "t", "e")
        h3 = content_hash("national-grid", "emissions", "u", "t", "DIFFERENT")
        self.assertEqual(h1, h2)
        self.assertNotEqual(h1, h3)

    def test_evidence_compute_hash_matches_helper(self):
        _, profile = make_company()
        ev = Evidence(company_slug="national-grid", category="climate",
                      url="https://x", title="t", excerpt="e")
        self.assertEqual(
            ev.compute_hash(),
            content_hash("national-grid", "climate", "https://x", "t", "e"),
        )

    def test_datapoint_requires_evidence_provenance(self):
        # FK is non-null → no orphan datapoints
        field = Datapoint._meta.get_field("evidence")
        self.assertFalse(field.null)


# ── Source Registry seed command ─────────────────────────────────────────────
class SeedSourcesTests(TestCase):
    def test_seed_is_idempotent(self):
        call_command("seed_sources", stdout=StringIO())
        first = Source.objects.filter(company__isnull=True).count()
        self.assertEqual(first, len(CATALOG))
        # re-run → no duplicates
        call_command("seed_sources", stdout=StringIO())
        self.assertEqual(Source.objects.filter(company__isnull=True).count(), first)

    def test_future_sources_seeded_inactive(self):
        call_command("seed_sources", stdout=StringIO())
        for st in FUTURE_SOURCE_TYPES:
            qs = Source.objects.filter(source_type=st, company__isnull=True)
            if qs.exists():
                self.assertFalse(qs.first().is_active,
                                 msg=f"{st} should be catalogued but inactive")

    def test_active_sources_have_base_confidence(self):
        for row in catalog_rows():
            self.assertGreaterEqual(row["confidence_base"], 0.0)
            self.assertLessEqual(row["confidence_base"], 1.0)
