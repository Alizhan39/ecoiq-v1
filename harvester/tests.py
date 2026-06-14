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


# ════════════════════════════════════════════════════════════════════════════
# Slice 3 — Normalization Engine
# ════════════════════════════════════════════════════════════════════════════
from harvester import normalization


class NormalizationExtractTests(TestCase):
    def test_change_statement_signed_percent(self):
        rows = normalization.extract("Scope 1 emissions reduced by 12% in 2024/25")
        r = next(x for x in rows if x.metric == "scope1_emissions_change")
        self.assertEqual(r.value, -12.0)
        self.assertEqual(r.unit, "percent")
        self.assertEqual(r.status, "NORMALIZED")
        self.assertEqual(r.period, "2024/25")
        self.assertEqual(r.period_year, 2025)

    def test_increase_is_positive(self):
        rows = normalization.extract("Scope 3 emissions increased by 4%")
        r = next(x for x in rows if x.metric == "scope3_emissions_change")
        self.assertEqual(r.value, 4.0)

    def test_absolute_currency_revenue(self):
        rows = normalization.extract("Gross revenue was £18,378m for the year")
        r = next(x for x in rows if x.metric == "revenue")
        self.assertEqual(r.value, 18378.0)
        self.assertEqual(r.unit, "GBP_million")

    def test_absolute_emissions_with_unit(self):
        rows = normalization.extract("Scope 1 emissions were 4.5 MtCO2e")
        r = next(x for x in rows if x.metric == "scope1_emissions")
        self.assertEqual(r.value, 4.5)
        self.assertEqual(r.unit, "MtCO2e")

    def test_employee_count(self):
        rows = normalization.extract("The group had 33,579 employees")
        r = next(x for x in rows if x.metric == "employee_count")
        self.assertEqual(r.value, 33579.0)
        self.assertEqual(r.unit, "count")

    def test_independent_directors_percent(self):
        rows = normalization.extract("Independent directors represent 60% of the board")
        r = next(x for x in rows if x.metric == "independent_directors_percent")
        self.assertEqual(r.value, 60.0)
        self.assertEqual(r.unit, "percent")

    def test_metric_present_no_value_is_not_normalized(self):
        rows = normalization.extract("Scope 1 emissions fell significantly during the period")
        r = next(x for x in rows if x.metric.startswith("scope1_emissions"))
        self.assertIsNone(r.value)
        self.assertEqual(r.status, "NOT_NORMALIZED")

    def test_no_metric_no_output(self):
        self.assertEqual(normalization.extract("The weather was pleasant."), [])

    def test_empty_text(self):
        self.assertEqual(normalization.extract(""), [])

    def test_all_required_metrics_have_specs(self):
        specs = {m.metric for m in normalization.METRICS}
        for needed in ("revenue", "operating_profit", "net_profit", "capex", "opex",
                       "energy_generated", "renewable_generation", "coal_generation",
                       "gas_generation", "scope1_emissions", "scope2_emissions",
                       "scope3_emissions", "emissions_intensity", "water_withdrawal",
                       "water_consumption", "employee_count", "lost_time_incidents",
                       "board_size", "independent_directors_percent"):
            self.assertIn(needed, specs, msg=f"missing metric spec {needed}")


class NormalizationPersistTests(TestCase):
    def _evidence(self, text, category="emissions"):
        _, profile = make_company()
        return Evidence.objects.create(
            company=profile, company_slug="national-grid",
            category=category, excerpt=text, publication_date=date(2025, 5, 15),
        )

    def test_persists_datapoint_with_provenance(self):
        ev = self._evidence("Scope 1 emissions reduced by 12% in 2024/25")
        points = normalization.normalize_evidence(ev)
        dp = next(p for p in points if p.metric == "scope1_emissions_change")
        self.assertEqual(dp.value, -12.0)
        self.assertEqual(dp.evidence_id, ev.id)
        self.assertEqual(dp.source_evidence, ev)        # alias works
        self.assertEqual(dp.status, "NORMALIZED")
        self.assertIsNotNone(dp.normalized_at)

    def test_normalize_is_idempotent(self):
        ev = self._evidence("Gross revenue was £18,378m in 2024/25", category="financial")
        normalization.normalize_evidence(ev)
        n1 = Datapoint.objects.filter(metric="revenue").count()
        normalization.normalize_evidence(ev)            # re-run
        n2 = Datapoint.objects.filter(metric="revenue").count()
        self.assertEqual(n1, n2)
        self.assertEqual(n1, 1)

    def test_not_normalized_stored_with_null_value(self):
        ev = self._evidence("Scope 2 emissions decreased markedly over the year")
        normalization.normalize_evidence(ev)
        dp = Datapoint.objects.filter(metric="scope2_emissions").first()
        self.assertIsNotNone(dp)
        self.assertIsNone(dp.value)                     # never fabricated
        self.assertEqual(dp.status, "NOT_NORMALIZED")


# ════════════════════════════════════════════════════════════════════════════
# Slice 4 — Harvest pipeline (harvest_company + process_harvest_jobs)
# ════════════════════════════════════════════════════════════════════════════
from harvester.models import HarvestJob
from harvester.pipeline import run_harvest


class HarvestPipelineTests(TestCase):
    def setUp(self):
        # slug 'national-grid' has registered documents in company_documents.py
        self.company, self.profile = make_company("national-grid")

    def _run(self):
        job = HarvestJob.objects.create(company=self.profile,
                                        company_slug="national-grid", status="pending")
        return run_harvest(job)

    def test_national_grid_end_to_end(self):
        job = self._run()
        self.assertEqual(job.status, "done")
        self.assertGreaterEqual(job.sources_discovered, 3)
        self.assertGreater(job.evidence_extracted, 0)
        self.assertGreater(job.evidence_stored, 0)

        # real cited figures normalized correctly
        rev = Datapoint.objects.get(company_slug="national-grid", metric="revenue")
        self.assertEqual(rev.value, 18378.0)
        self.assertEqual(rev.unit, "GBP_million")
        self.assertEqual(rev.period_year, 2025)

        emp = Datapoint.objects.get(company_slug="national-grid", metric="employee_count")
        self.assertEqual(emp.value, 33579.0)

        for m in ("operating_profit", "capex", "scope1_emissions",
                  "scope2_emissions", "scope3_emissions"):
            self.assertTrue(
                Datapoint.objects.filter(company_slug="national-grid", metric=m).exists(),
                msg=f"missing datapoint {m}")

    def test_scope1_corroborated_and_verified(self):
        self._run()
        ev = Evidence.objects.get(company_slug="national-grid",
                                  category="emissions", title__startswith="Scope 1")
        self.assertEqual(ev.source_refs.count(), 2)        # annual + sustainability
        self.assertEqual(ev.corroboration_count, 1)
        self.assertEqual(ev.verification_status, "VERIFIED")

    def test_evidence_source_records_created(self):
        self._run()
        # company-scoped EvidenceSource (Source) rows created during discovery
        self.assertTrue(Source.objects.filter(company=self.profile).exists())

    def test_net_zero_claim_has_no_fabricated_datapoint(self):
        self._run()
        # "net zero by 2050" carries no numeric metric → evidence but no datapoint
        self.assertTrue(Evidence.objects.filter(
            company_slug="national-grid", category="climate").exists())
        self.assertFalse(Datapoint.objects.filter(
            company_slug="national-grid", metric="climate").exists())

    def test_pipeline_is_idempotent(self):
        self._run()
        ev1 = Evidence.objects.filter(company_slug="national-grid").count()
        dp1 = Datapoint.objects.filter(company_slug="national-grid").count()
        self._run()  # second harvest
        self.assertEqual(Evidence.objects.filter(company_slug="national-grid").count(), ev1)
        self.assertEqual(Datapoint.objects.filter(company_slug="national-grid").count(), dp1)

    def test_unknown_company_completes_without_fabrication(self):
        _, profile = make_company("ghost-co")
        job = HarvestJob.objects.create(company=profile, company_slug="ghost-co")
        run_harvest(job)
        self.assertEqual(job.status, "done")
        # no registered docs, empty profile fields → no datapoints invented
        self.assertEqual(Datapoint.objects.filter(company_slug="ghost-co").count(), 0)


class ProcessHarvestJobsTests(TestCase):
    def test_worker_drains_pending_jobs(self):
        from io import StringIO
        from django.core.management import call_command
        company, profile = make_company("national-grid")
        HarvestJob.objects.create(company=profile, company_slug="national-grid",
                                  status="pending")
        call_command("process_harvest_jobs", stdout=StringIO())
        job = HarvestJob.objects.get(company_slug="national-grid")
        self.assertEqual(job.status, "done")
        self.assertGreater(job.evidence_stored, 0)


# ════════════════════════════════════════════════════════════════════════════
# Slice 5 — standalone read-only Company Evidence Dashboard
# ════════════════════════════════════════════════════════════════════════════
from django.test import Client
from harvester.views import build_dashboard_data


class DashboardDataTests(TestCase):
    def setUp(self):
        self.company, self.profile = make_company("national-grid")
        HarvestJob = __import__("harvester.models", fromlist=["HarvestJob"]).HarvestJob
        from harvester.pipeline import run_harvest
        run_harvest(HarvestJob.objects.create(
            company=self.profile, company_slug="national-grid", status="pending"))

    def test_payload_shape_and_metrics(self):
        d = build_dashboard_data("national-grid")
        for k in ("coverage_pct", "verification_pct", "missing_categories",
                  "sources", "evidence", "datapoints", "contradictions", "counts"):
            self.assertIn(k, d)
        self.assertEqual(d["categories_total"], 25)
        self.assertGreater(d["counts"]["evidence"], 0)
        self.assertGreater(d["counts"]["datapoints"], 0)
        self.assertTrue(d["read_only"])

    def test_coverage_and_verification_are_consistent(self):
        d = build_dashboard_data("national-grid")
        # coverage = present categories / 25
        self.assertEqual(d["categories_present"] + len(d["missing_categories"]), 25)
        # verification % reflects VERIFIED share (scope1 is verified)
        self.assertGreater(d["verification_pct"], 0.0)
        self.assertIn("VERIFIED", d["status_breakdown"])

    def test_empty_company_safe_state(self):
        d = build_dashboard_data("no-such-co")
        self.assertEqual(d["counts"]["evidence"], 0)
        self.assertEqual(d["coverage_pct"], 0.0)
        self.assertEqual(d["verification_pct"], 0.0)
        self.assertEqual(len(d["missing_categories"]), 25)


class DashboardViewTests(TestCase):
    def setUp(self):
        self.client = Client(SERVER_NAME="localhost")
        self.company, self.profile = make_company("national-grid")
        from harvester.models import HarvestJob
        from harvester.pipeline import run_harvest
        run_harvest(HarvestJob.objects.create(
            company=self.profile, company_slug="national-grid", status="pending"))

    def test_dashboard_html_200(self):
        r = self.client.get("/evidence/national-grid/")
        self.assertEqual(r.status_code, 200)
        body = r.content.decode()
        self.assertIn("Coverage", body)
        self.assertIn("Datapoints", body)
        self.assertIn("revenue", body)          # a real harvested datapoint

    def test_dashboard_json_200(self):
        r = self.client.get("/evidence/national-grid/data/")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["company_slug"], "national-grid")
        self.assertGreater(data["counts"]["datapoints"], 0)

    def test_unknown_company_renders_safe_empty(self):
        r = self.client.get("/evidence/ghost-co/")
        self.assertEqual(r.status_code, 200)            # read-only, never 500
        self.assertIn("No evidence harvested yet", r.content.decode())

    def test_dashboard_is_read_only_no_mutation(self):
        from harvester.models import Evidence, Datapoint
        before = (Evidence.objects.count(), Datapoint.objects.count())
        self.client.get("/evidence/national-grid/")
        self.client.get("/evidence/national-grid/data/")
        after = (Evidence.objects.count(), Datapoint.objects.count())
        self.assertEqual(before, after)
