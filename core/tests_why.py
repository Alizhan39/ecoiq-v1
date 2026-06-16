"""
WHY Engine tests — explainability, Boardroom Mode, Decision Defense Pack, API.
Read-only, evidence-derived; verifies honest defendability + no fabrication.
"""
from django.test import TestCase, Client

from league.models import Company
from companies.models import CompanyProfile
from countries.models import CountryProfile
from harvester.models import RegistryCompany, HarvestJob
from harvester.pipeline import run_harvest
from core.why import why_company, why_country


class WhyCompanyTests(TestCase):
    def setUp(self):
        c = Company.objects.create(name="National Grid plc", slug="national-grid",
                                   sector="energy", country="GB")
        CompanyProfile.objects.create(company=c, status="public")
        RegistryCompany.objects.create(company_name="National Grid plc",
                                       slug="national-grid", sector="utilities", country="GB")
        run_harvest(HarvestJob.objects.create(company_slug="national-grid", status="pending"))
        # an un-harvested company → honest "not yet defendable"
        RegistryCompany.objects.create(company_name="EDF Energy UK", slug="edf-energy-uk",
                                       sector="energy", country="GB")

    def test_covered_metric_has_evidence_and_defend_verdict(self):
        d = why_company("national-grid")
        rev = next(r for r in d["reports"] if r["metric_key"] == "revenue")
        self.assertEqual(rev["value"], 18378.0)
        self.assertTrue(rev["evidence_used"])                       # cited
        self.assertIn(rev["defendable"], ("YES", "WITH_CAVEATS"))   # has a verdict
        for k in ("1_trust", "2_origin", "3_supports", "4_missing", "5_improve", "6_defend"):
            self.assertIn(k, rev["boardroom"])                      # all 6 boardroom answers

    def test_missing_metric_is_insufficient_not_fabricated(self):
        d = why_company("edf-energy-uk")
        rev = next(r for r in d["reports"] if r["metric_key"] == "revenue")
        self.assertIsNone(rev["value"])
        self.assertEqual(rev["defendable"], "NOT_YET")              # honestly not defendable
        self.assertTrue(rev["evidence_missing"])

    def test_no_metric_is_ever_estimated(self):
        d = why_company("edf-energy-uk")
        for r in d["reports"]:
            if not r["evidence_used"]:
                self.assertIsNone(r["value"])                       # no evidence → no value


class WhyCountryTests(TestCase):
    def setUp(self):
        self.uk = CountryProfile.objects.create(
            name="United Kingdom", slug="united-kingdom", iso_code="GB",
            is_published=True, policy_environment_score=72.0, national_ecoiq_index=62.4)

    def test_sourced_score_labelled_and_not_recomputed(self):
        d = why_country("united-kingdom")
        gov = next(r for r in d["reports"] if r["metric_key"] == "policy_environment_score")
        self.assertEqual(gov["value"], 72.0)
        self.assertEqual(gov["score_type"], "SOURCED")              # external, not EcoIQ-computed
        self.assertIn("does NOT recompute", gov["methodology"])

    def test_unknown_country_returns_none(self):
        self.assertIsNone(why_country("nope"))


class WhyViewsTests(TestCase):
    def setUp(self):
        self.client = Client(SERVER_NAME="localhost")
        CountryProfile.objects.create(name="United Kingdom", slug="united-kingdom",
                                      iso_code="GB", is_published=True, national_ecoiq_index=62.4)
        c = Company.objects.create(name="National Grid plc", slug="national-grid",
                                   sector="energy", country="GB")
        CompanyProfile.objects.create(company=c, status="public")
        RegistryCompany.objects.create(company_name="National Grid plc",
                                       slug="national-grid", sector="utilities", country="GB")
        run_harvest(HarvestJob.objects.create(company_slug="national-grid", status="pending"))

    def test_boardroom_page_renders(self):
        r = self.client.get("/why/company/national-grid/")
        self.assertEqual(r.status_code, 200)
        body = r.content.decode()
        self.assertIn("Boardroom Mode", body)
        self.assertIn("Can I defend this to an IC", body)

    def test_api_returns_reports(self):
        r = self.client.get("/api/why/company/national-grid/")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["reports"])

    def test_decision_defense_pack_pdf(self):
        r = self.client.get("/why/company/national-grid/pack.pdf")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "application/pdf")
        self.assertEqual(r.content[:4], b"%PDF")

    def test_country_pack_pdf(self):
        r = self.client.get("/why/country/united-kingdom/pack.pdf")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content[:4], b"%PDF")
