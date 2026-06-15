"""
Country Intelligence — Track A (Phase 1) tests.

Read-only intelligence bridge + country-page panel. Verifies harvester data is
surfaced per country, the data-expansion state is transparent, and no statistic
is fabricated (missing values render as 'unavailable').
"""
from django.test import TestCase, Client
from django.template import Template, Context

from league.models import Company
from companies.models import CompanyProfile
from countries.models import CountryProfile
from harvester.models import RegistryCompany, HarvestJob
from harvester.pipeline import run_harvest
from countries.intelligence import country_intelligence


def _country(slug, iso, **kw):
    return CountryProfile.objects.create(
        name=slug.replace("-", " ").title(), slug=slug, iso_code=iso,
        renewable_energy_share=kw.get("renew", 40.0),
        gdp_usd=kw.get("gdp", 1000), is_published=True,
    )


def _registry(slug, iso, sector="energy"):
    return RegistryCompany.objects.create(company_name=slug.title(), slug=slug,
                                          sector=sector, country=iso)


class CountryIntelligenceBridgeTests(TestCase):
    def test_uk_populated_from_harvester(self):
        gb = _country("united-kingdom", "GB")
        c = Company.objects.create(name="National Grid plc", slug="national-grid",
                                   sector="energy", country="GB")
        CompanyProfile.objects.create(company=c, status="public")
        _registry("national-grid", "GB", "utilities")
        run_harvest(HarvestJob.objects.create(company_slug="national-grid", status="pending"))

        d = country_intelligence(gb)
        self.assertEqual(d["iso"], "GB")
        self.assertEqual(d["companies_count"], 1)
        self.assertGreater(d["evidence_count"], 0)
        self.assertGreater(d["datapoint_count"], 0)
        self.assertFalse(d["data_expansion"])
        self.assertFalse(d["no_registry"])
        self.assertEqual(d["energy"]["renewable_energy_share"], 40.0)

    def test_seeded_but_unharvested_country_shows_data_expansion(self):
        kz = _country("kazakhstan", "KZ", renew=6.0)
        for s in ("kazmunaygas", "kegoc"):
            _registry(s, "KZ")
        d = country_intelligence(kz)
        self.assertEqual(d["companies_count"], 2)
        self.assertEqual(d["evidence_count"], 0)
        self.assertTrue(d["data_expansion"])
        self.assertFalse(d["no_registry"])

    def test_country_with_no_registry(self):
        fr = _country("france", "FR")
        d = country_intelligence(fr)
        self.assertEqual(d["companies_count"], 0)
        self.assertTrue(d["no_registry"])

    def test_missing_metric_is_none_not_fabricated(self):
        kz = _country("kazakhstan", "KZ")     # inflation_pct null
        d = country_intelligence(kz)
        self.assertIsNone(d["overview"]["inflation_pct"])


class CountryPanelRenderTests(TestCase):
    def setUp(self):
        self.client = Client(SERVER_NAME="localhost")

    def test_panel_tag_renders_data_expansion(self):
        kz = _country("kazakhstan", "KZ", renew=6.0)
        _registry("kazmunaygas", "KZ")
        html = Template(
            "{% load country_panels %}{% country_intelligence_panel c %}"
        ).render(Context({"c": kz}))
        self.assertIn("Country Intelligence", html)
        self.assertIn("evidence harvest in progress", html)   # data-expansion banner
        self.assertIn("companies tracked", html)

    def test_panel_labels_unavailable(self):
        sa = _country("saudi-arabia", "SA")   # inflation null → unavailable
        html = Template(
            "{% load country_panels %}{% country_intelligence_panel c %}"
        ).render(Context({"c": sa}))
        self.assertIn("unavailable", html)

    def test_country_detail_page_includes_panel(self):
        _country("kazakhstan", "KZ", renew=6.0)
        _registry("kazmunaygas", "KZ")
        r = self.client.get("/countries/kazakhstan/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("ci-intel", r.content.decode())
