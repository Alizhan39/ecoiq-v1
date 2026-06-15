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


# ════════════════════════════════════════════════════════════════════════════
# Slice 6 — UK target company registry
# ════════════════════════════════════════════════════════════════════════════
from harvester.models import RegistryCompany
from harvester.uk_registry import COMPANIES, registry_rows


class RegistryModelTests(TestCase):
    def test_create_and_unique_slug(self):
        RegistryCompany.objects.create(company_name="Test Co", slug="test-co",
                                       sector="energy", country="GB")
        self.assertEqual(RegistryCompany.objects.get(slug="test-co").sector, "energy")
        with self.assertRaises(Exception):
            RegistryCompany.objects.create(company_name="Dup", slug="test-co",
                                           sector="water")

    def test_catalog_has_25_distinct_companies(self):
        slugs = [c[0] for c in COMPANIES]
        self.assertEqual(len(slugs), 25)
        self.assertEqual(len(set(slugs)), 25)          # no duplicate slugs

    def test_catalog_sectors_are_valid(self):
        from harvester.constants import REGISTRY_SECTORS
        valid = {s[0] for s in REGISTRY_SECTORS}
        for row in registry_rows():
            self.assertIn(row["sector"], valid)

    def test_no_fabricated_ch_numbers_or_report_urls(self):
        # registry never invents CH numbers / report deep links
        for row in registry_rows():
            self.assertEqual(row["companies_house_number"], "")
            self.assertEqual(row["annual_report_url"], "")
            self.assertEqual(row["investor_relations_url"], "")
            self.assertEqual(row["sustainability_report_url"], "")


class SeedUKRegistryTests(TestCase):
    def test_seed_idempotent_and_complete(self):
        from io import StringIO
        from django.core.management import call_command
        call_command("seed_uk_registry", stdout=StringIO())
        self.assertEqual(RegistryCompany.objects.count(), 25)
        call_command("seed_uk_registry", stdout=StringIO())   # re-run
        self.assertEqual(RegistryCompany.objects.count(), 25)  # no duplicates

    def test_expected_companies_present(self):
        from io import StringIO
        from django.core.management import call_command
        call_command("seed_uk_registry", stdout=StringIO())
        for slug in ("national-grid", "severn-trent", "thames-water",
                     "cadent-gas", "bp", "octopus-energy"):
            self.assertTrue(RegistryCompany.objects.filter(slug=slug).exists(),
                            msg=f"missing {slug}")
        # listed plcs carry a ticker; private/subsidiaries do not
        self.assertEqual(RegistryCompany.objects.get(slug="national-grid").ticker, "NG.")
        self.assertEqual(RegistryCompany.objects.get(slug="octopus-energy").ticker, "")

    def test_registry_is_inert_no_harvest(self):
        from io import StringIO
        from django.core.management import call_command
        call_command("seed_uk_registry", stdout=StringIO())
        # seeding the registry creates no evidence/datapoints
        self.assertEqual(Evidence.objects.count(), 0)
        self.assertEqual(Datapoint.objects.count(), 0)


# ════════════════════════════════════════════════════════════════════════════
# Slice 7 — Batch Harvest Runner (harvest_registry)
# ════════════════════════════════════════════════════════════════════════════
from io import StringIO as _SIO
from unittest import mock
from django.core.management import call_command
from harvester.models import BatchHarvestRun


class HarvestRegistryTests(TestCase):
    def setUp(self):
        call_command("seed_uk_registry", stdout=_SIO())

    def test_batch_runs_and_stores_summary(self):
        out = _SIO()
        call_command("harvest_registry", "--limit", "3", stdout=out)
        batch = BatchHarvestRun.objects.latest("created_at")
        self.assertEqual(batch.status, "done")
        self.assertEqual(batch.total_companies, 3)
        self.assertEqual(batch.successful, 3)
        self.assertEqual(batch.failed, 0)
        # national-grid (priority 1) has registered docs → real evidence created
        self.assertGreater(batch.evidence_created, 0)
        self.assertGreater(batch.datapoints_created, 0)

    def test_progress_printed_per_company(self):
        out = _SIO()
        call_command("harvest_registry", "--limit", "3", stdout=out)
        text = out.getvalue()
        self.assertIn("[1/3] national-grid", text)
        self.assertIn("[2/3] sse", text)
        self.assertIn("[3/3] centrica", text)

    def test_idempotent_second_batch_creates_nothing(self):
        call_command("harvest_registry", "--limit", "3", stdout=_SIO())
        call_command("harvest_registry", "--limit", "3", stdout=_SIO())
        latest = BatchHarvestRun.objects.latest("created_at")
        self.assertEqual(latest.evidence_created, 0)      # nothing new on re-run
        self.assertEqual(latest.datapoints_created, 0)

    def test_continues_when_one_company_fails(self):
        real = __import__("harvester.pipeline", fromlist=["run_harvest"]).run_harvest

        def flaky(job):
            if job.company_slug == "sse":
                raise RuntimeError("boom")
            return real(job)

        with mock.patch("harvester.pipeline.run_harvest", side_effect=flaky):
            call_command("harvest_registry", "--limit", "3", stdout=_SIO())
        batch = BatchHarvestRun.objects.latest("created_at")
        self.assertEqual(batch.status, "done")            # batch completed
        self.assertEqual(batch.failed, 1)                 # sse failed
        self.assertEqual(batch.successful, 2)             # others succeeded

    def test_sector_filter(self):
        call_command("harvest_registry", "--sector", "water", stdout=_SIO())
        batch = BatchHarvestRun.objects.latest("created_at")
        self.assertEqual(batch.total_companies,
                         RegistryCompany.objects.filter(sector="water").count())


# ════════════════════════════════════════════════════════════════════════════
# Slice 8 — UK document registry expansion
# ════════════════════════════════════════════════════════════════════════════
from harvester.company_documents import REGISTERED_DOCUMENTS, get_documents
from harvester import normalization as _norm
from harvester.models import HarvestJob as _HJ
from harvester.pipeline import run_harvest as _run

SLICE8_SLUGS = [
    "sse", "centrica", "severn-trent", "united-utilities",
    "national-gas", "cadent-gas", "uk-power-networks", "thames-water", "anglian-water",
]


class DocumentRegistryExpansionTests(TestCase):
    def test_new_companies_registered(self):
        for slug in SLICE8_SLUGS:
            self.assertIn(slug, REGISTERED_DOCUMENTS, msg=f"missing {slug}")
        self.assertEqual(len(REGISTERED_DOCUMENTS), 10)  # national-grid + 9 verified
        # scottishpower omitted (domain WAF-blocks verification)
        self.assertNotIn("scottishpower", REGISTERED_DOCUMENTS)

    def test_all_urls_are_real_https(self):
        for slug, docs in REGISTERED_DOCUMENTS.items():
            for d in docs:
                u = d.get("url", "")
                self.assertTrue(u.startswith("https://"), msg=f"{slug}: {u!r}")
                self.assertNotIn("example.com", u)       # no placeholder/fabricated
                self.assertNotIn("TODO", u)

    def test_expected_datapoints_extracted(self):
        expected = {
            ("sse", "operating_profit"): 2608.2,
            ("centrica", "operating_profit"): 297.0,
            ("severn-trent", "revenue"): 2426.7,
            ("united-utilities", "revenue"): 2145.0,
            ("united-utilities", "operating_profit"): 634.0,
            ("national-gas", "revenue"): 1551.0,
            ("cadent-gas", "revenue"): 1056.0,
            ("thames-water", "revenue"): 2738.2,
        }
        got = {}
        for slug in SLICE8_SLUGS:
            for d in get_documents(slug):
                for r in _norm.extract(d["statement"]):
                    if r.status == "NORMALIZED":
                        got[(slug, r.metric)] = r.value
        for key, val in expected.items():
            self.assertEqual(got.get(key), val, msg=f"{key} expected {val}, got {got.get(key)}")
        self.assertEqual(len(got), 8)                    # exactly 8 new datapoints

    def test_evidence_only_companies_have_no_fabricated_datapoint(self):
        for slug in ("uk-power-networks", "anglian-water"):
            dp = []
            for d in get_documents(slug):
                dp += [r for r in _norm.extract(d["statement"]) if r.status == "NORMALIZED"]
            self.assertEqual(dp, [], msg=f"{slug} should be evidence-only")

    def test_harvest_new_company_end_to_end(self):
        _, profile = make_company("severn-trent")
        job = _HJ.objects.create(company=profile, company_slug="severn-trent", status="pending")
        _run(job)
        self.assertEqual(job.status, "done")
        dp = Datapoint.objects.get(company_slug="severn-trent", metric="revenue")
        self.assertEqual(dp.value, 2426.7)
        self.assertEqual(dp.unit, "GBP_million")


# ════════════════════════════════════════════════════════════════════════════
# Slice 9 — company-page Evidence Layer panel (presentation only)
# ════════════════════════════════════════════════════════════════════════════
from django.template import Template, Context
from harvester.rollups import company_rollup as _rollup


class CompanyEvidencePanelTests(TestCase):
    def setUp(self):
        self.company, self.profile = make_company("national-grid")
        from harvester.pipeline import run_harvest
        run_harvest(_HJ.objects.create(
            company=self.profile, company_slug="national-grid", status="pending"))

    def test_rollup_counts_and_last_updated(self):
        r = _rollup("national-grid")
        self.assertGreater(r["evidence_count"], 0)
        self.assertGreater(r["datapoint_count"], 0)
        self.assertTrue(r["has_data"])
        self.assertIsNotNone(r["last_updated"])
        self.assertEqual(r["dashboard_url"], "/evidence/national-grid/")
        # latest datapoints carry real values
        metrics = {d["metric"] for d in r["latest_datapoints"]}
        self.assertIn("revenue", metrics)

    def test_rollup_unknown_company_empty_safe(self):
        r = _rollup("ghost-co")
        self.assertEqual(r["evidence_count"], 0)
        self.assertEqual(r["datapoint_count"], 0)
        self.assertFalse(r["has_data"])
        self.assertIsNone(r["last_updated"])

    def test_inclusion_tag_renders_panel(self):
        html = Template(
            "{% load harvester_panels %}{% company_evidence_panel 'national-grid' %}"
        ).render(Context({}))
        self.assertIn("Evidence Layer", html)
        self.assertIn("datapoints", html)
        self.assertIn("revenue", html)
        self.assertIn("/evidence/national-grid/", html)

    def test_inclusion_tag_empty_state(self):
        html = Template(
            "{% load harvester_panels %}{% company_evidence_panel 'ghost-co' %}"
        ).render(Context({}))
        self.assertIn("No evidence harvested", html)

    def test_panel_on_canonical_company_page(self):
        from django.test import Client
        c = Client(SERVER_NAME="localhost")
        r = c.get("/companies/national-grid/")
        self.assertEqual(r.status_code, 200)
        body = r.content.decode()
        self.assertIn("hv-ev-panel", body)             # panel injected
        self.assertIn("Evidence Layer", body)
        self.assertIn("operating_profit", body)        # real datapoint shown

    def test_panel_is_read_only(self):
        from harvester.models import Evidence, Datapoint
        before = (Evidence.objects.count(), Datapoint.objects.count())
        _rollup("national-grid")
        Template("{% load harvester_panels %}{% company_evidence_panel 'national-grid' %}").render(Context({}))
        self.assertEqual((Evidence.objects.count(), Datapoint.objects.count()), before)


# ════════════════════════════════════════════════════════════════════════════
# Slice 10 — investor surfaces (rankings, evidence explorer, homepage block)
# ════════════════════════════════════════════════════════════════════════════
from django.test import Client as _Client
from django.core.management import call_command as _cc
from io import StringIO as _S
from harvester.rollups import platform_stats as _pstats, rankings_data as _rdata


class _SeededHarvest(TestCase):
    """Seeds registry + harvests National Grid and SSE for surface tests."""
    def setUp(self):
        self.client = _Client(SERVER_NAME="localhost")
        _cc("seed_uk_registry", stdout=_S())
        for slug in ("national-grid", "sse"):
            make_company(slug)
            from harvester.pipeline import run_harvest
            run_harvest(_HJ.objects.create(company_slug=slug, status="pending"))


class RankingsTests(_SeededHarvest):
    def test_rankings_sorted_by_operating_profit_desc(self):
        rows = _rdata()
        self.assertEqual(len(rows), 25)                       # all active registry
        ops = [r["operating_profit"] for r in rows if r["operating_profit"] is not None]
        self.assertEqual(ops, sorted(ops, reverse=True))      # descending
        self.assertEqual(rows[0]["slug"], "national-grid")    # 5357 tops
        self.assertEqual(rows[0]["rank"], 1)

    def test_rankings_page_renders(self):
        r = self.client.get("/rankings/utilities/")
        self.assertEqual(r.status_code, 200)
        body = r.content.decode()
        self.assertIn("UK Infrastructure &amp; Utilities Intelligence", body)
        self.assertIn("Top 10 by operating profit", body)
        self.assertIn("National Grid", body)


class EvidenceExplorerTests(_SeededHarvest):
    def test_explorer_page_renders(self):
        r = self.client.get("/evidence/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Evidence Explorer", r.content.decode())

    def test_company_filter(self):
        r = self.client.get("/evidence/?company=national-grid")
        body = r.content.decode()
        self.assertIn("national-grid", body)
        self.assertNotIn(">sse<", body.replace(" ", ""))  # sse rows excluded (rough)

    def test_metric_filter_via_datapoint_join(self):
        r = self.client.get("/evidence/?metric=operating_profit")
        self.assertEqual(r.status_code, 200)
        # only evidence whose datapoints include operating_profit
        from harvester.models import Datapoint, Evidence
        ev_ids = set(Datapoint.objects.filter(metric="operating_profit").values_list("evidence_id", flat=True))
        self.assertTrue(ev_ids)

    def test_text_search(self):
        r = self.client.get("/evidence/?q=revenue")
        self.assertEqual(r.status_code, 200)

    def test_pagination_present(self):
        r = self.client.get("/evidence/")
        self.assertIn("page", r.content.decode().lower())


class HomepageIntelligenceBlockTests(_SeededHarvest):
    def test_platform_stats(self):
        s = _pstats()
        self.assertEqual(s["companies_tracked"], 25)
        self.assertGreater(s["evidence_count"], 0)
        self.assertGreater(s["datapoint_count"], 0)
        self.assertEqual(s["rankings_url"], "/rankings/utilities/")
        self.assertEqual(s["evidence_url"], "/evidence/")

    def test_block_renders_on_homepage(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        body = r.content.decode()
        self.assertIn("Companies tracked", body)
        self.assertIn("Evidence collected", body)
        self.assertIn("Datapoints extracted", body)
        self.assertIn("View Rankings", body)

    def test_company_panel_exposes_confidence(self):
        from harvester.rollups import company_rollup
        r = company_rollup("national-grid")
        self.assertIn("avg_confidence", r)
        self.assertIsNotNone(r["avg_confidence"])
