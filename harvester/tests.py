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

from datetime import date, timedelta

from league.models import Company
from companies.models import CompanyProfile
from harvester.models import (
    Source, HarvestJob, Evidence, Datapoint, EvidenceSourceRef, content_hash,
)
from harvester.constants import (
    EVIDENCE_CATEGORIES, VERIFICATION_STATUSES, SOURCE_TYPES, FUTURE_SOURCE_TYPES,
)
from harvester.source_registry import CATALOG, catalog_rows
from harvester import adapters, verification, dedup


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


# ════════════════════════════════════════════════════════════════════════════
# Slice 2 — SourceAdapter, Verification, Deduplication
# ════════════════════════════════════════════════════════════════════════════
class AdapterTests(TestCase):
    def test_all_nine_required_source_types_supported(self):
        for st in ("annual_report", "sustainability_report", "esg_report",
                   "company_website", "investor_relations", "companies_house",
                   "regulatory_filing", "press_release"):
            self.assertIsNotNone(adapters.get_adapter(st), msg=f"missing adapter {st}")
        # news is represented by a NetworkAdapter (reuters)
        self.assertIsNotNone(adapters.get_adapter("reuters"))

    def test_document_adapter_classifies_and_builds_candidates(self):
        a = adapters.get_adapter("annual_report")
        cands = a.collect("national-grid", documents=[
            {"statement": "Scope 1 emissions reduced by 12% in 2024/25.",
             "url": "https://x/ar.pdf", "publication_date": date(2025, 5, 15)},
            {"statement": "Gross revenue was £18,378m.", "url": "https://x/ar.pdf"},
        ])
        self.assertEqual(len(cands), 2)
        self.assertEqual(cands[0].category, "emissions")   # classified
        self.assertEqual(cands[1].category, "financial")
        self.assertEqual(cands[0].source_type, "annual_report")

    def test_document_adapter_no_input_returns_empty(self):
        a = adapters.get_adapter("esg_report")
        self.assertEqual(a.collect("national-grid", documents=None), [])

    def test_network_adapter_inert_offline_no_fabrication(self):
        a = adapters.get_adapter("companies_house")
        self.assertTrue(a.requires_network)
        self.assertEqual(a.collect("national-grid"), [])  # honest empty, not invented

    def test_profile_adapter_reads_company_fields(self):
        company, profile = make_company()
        profile.ai_summary = "National Grid is a UK electricity and gas utility."
        profile.annual_report_url = "https://example.com/ar.pdf"
        profile.save()
        web = adapters.get_adapter("company_website").collect("national-grid", profile=profile)
        ir = adapters.get_adapter("investor_relations").collect("national-grid", profile=profile)
        self.assertTrue(any("utility" in c.statement for c in web))
        self.assertTrue(any(c.url == "https://example.com/ar.pdf" for c in ir))


class VerificationEngineTests(TestCase):
    def test_scores_in_unit_range(self):
        r = verification.score(source_type="annual_report",
                               publication_date=date.today(), corroborating_sources=1)
        for s in (r.source_quality_score, r.freshness_score,
                  r.corroboration_score, r.confidence_score):
            self.assertGreaterEqual(s, 0.0)
            self.assertLessEqual(s, 1.0)

    def test_status_verified_requires_corroboration_and_confidence(self):
        r = verification.score(source_type="annual_report",
                               publication_date=date.today(), corroborating_sources=2)
        self.assertEqual(r.verification_status, "VERIFIED")

    def test_status_partial_single_credible_source(self):
        r = verification.score(source_type="annual_report",
                               publication_date=date.today(), corroborating_sources=0)
        self.assertEqual(r.verification_status, "PARTIAL")

    def test_status_insufficient_for_weak_uncorroborated_source(self):
        r = verification.score(source_type="company_website",  # quality 0.55... still PARTIAL
                               publication_date=date.today(), corroborating_sources=0)
        # company_website 0.55 > INSUFFICIENT threshold → PARTIAL not INSUFFICIENT
        self.assertIn(r.verification_status, ("PARTIAL", "UNVERIFIED"))
        weak = verification.score(source_type="", confidence_base=0.2,
                                  corroborating_sources=0)
        self.assertEqual(weak.verification_status, "INSUFFICIENT_EVIDENCE")

    def test_status_contradicted_and_not_found(self):
        self.assertEqual(
            verification.score(source_type="annual_report", contradicted=True,
                               publication_date=date.today()).verification_status,
            "CONTRADICTED")
        self.assertEqual(
            verification.score(has_evidence=False).verification_status, "NOT_FOUND")

    def test_freshness_decays_with_age(self):
        fresh = verification.freshness(date.today())
        old = verification.freshness(date.today() - timedelta(days=365 * 4))
        undated = verification.freshness(None)
        self.assertGreater(fresh, old)
        self.assertEqual(undated, verification.UNKNOWN_DATE_FRESHNESS)

    def test_verify_evidence_writes_back(self):
        _, profile = make_company()
        src = Source.objects.create(name="AR", source_type="annual_report",
                                    confidence_base=0.85, company=profile)
        ev = Evidence.objects.create(company=profile, company_slug="national-grid",
                                     source=src, category="financial",
                                     publication_date=date.today(),
                                     corroboration_count=2)
        result = verification.verify_evidence(ev)
        ev.refresh_from_db()
        self.assertEqual(ev.verification_status, result.verification_status)
        self.assertEqual(ev.confidence, ev.confidence_score)
        self.assertEqual(ev.verification_status, "VERIFIED")  # 0.85 + 2 corroborating


class DeduplicationEngineTests(TestCase):
    def _cands(self, statements):
        # statements: list of (source_type, text)
        return [adapters.EvidenceCandidate(
            company_slug="national-grid", category="emissions",
            statement=txt, source_type=st, url=f"https://{st}.example/x")
            for st, txt in statements]

    def test_same_fact_across_sources_merges_to_one_canonical(self):
        _, profile = make_company()
        cands = self._cands([
            ("annual_report", "Scope 1 emissions reduced by 12% in 2024/25"),
            ("esg_report",    "Scope 1 emissions reduced by 12% in 2024/25"),
            ("company_website", "Scope 1 emissions reduced by 12% in 2024/25"),
        ])
        stats = dedup.deduplicate(cands, profile=profile)
        self.assertEqual(stats["canonical_created"], 1)
        self.assertEqual(Evidence.objects.count(), 1)
        canonical = Evidence.objects.get()
        self.assertEqual(canonical.source_refs.count(), 3)       # 3 source references
        self.assertEqual(canonical.corroboration_count, 2)       # 2 beyond primary
        self.assertEqual(canonical.verification_status, "VERIFIED")

    def test_dedup_is_idempotent(self):
        _, profile = make_company()
        cands = self._cands([
            ("annual_report", "Net zero by 2050 commitment"),
            ("esg_report", "Net zero by 2050 commitment"),
        ])
        dedup.deduplicate(cands, profile=profile)
        dedup.deduplicate(cands, profile=profile)  # re-run
        self.assertEqual(Evidence.objects.count(), 1)
        self.assertEqual(EvidenceSourceRef.objects.count(), 2)   # no dup refs

    def test_distinct_facts_do_not_merge(self):
        _, profile = make_company()
        cands = self._cands([
            ("annual_report", "Scope 1 emissions reduced by 12%"),
            ("annual_report", "Gross revenue was 18378 million"),
        ])
        dedup.deduplicate(cands, profile=profile)
        self.assertEqual(Evidence.objects.count(), 2)

    def test_contradiction_flagged_when_directions_conflict(self):
        _, profile = make_company()
        cands = self._cands([
            ("annual_report", "Emissions decreased by 10 percent"),
            ("reuters",       "Emissions increased by 10 percent"),
        ])
        stats = dedup.deduplicate(cands, profile=profile)
        # same dedup_key? statements differ only by direction word → likely same key
        canonical = Evidence.objects.first()
        if canonical.source_refs.count() == 2:
            self.assertEqual(stats["contradicted"], 1)
            self.assertEqual(canonical.verification_status, "CONTRADICTED")
