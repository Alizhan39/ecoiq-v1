"""
Living Infrastructure Earth — Phase 0 globe endpoint tests.

Verifies the read-only /api/globe/layers/ endpoint returns live, real data with
representative (honestly flagged) markers and no fabricated statistics.
"""
from django.test import TestCase, Client

from league.models import Company
from companies.models import CompanyProfile
from countries.models import CountryProfile
from harvester.models import RegistryCompany, HarvestJob
from harvester.pipeline import run_harvest


class GlobeLayersEndpointTests(TestCase):
    def setUp(self):
        self.client = Client(SERVER_NAME="localhost")
        CountryProfile.objects.create(name="United Kingdom", slug="united-kingdom",
                                      iso_code="GB", is_published=True)
        # a harvested UK company (real evidence + datapoints)
        c = Company.objects.create(name="National Grid plc", slug="national-grid",
                                   sector="energy", country="GB")
        CompanyProfile.objects.create(company=c, status="public")
        RegistryCompany.objects.create(company_name="National Grid plc",
                                       slug="national-grid", sector="utilities", country="GB")
        run_harvest(HarvestJob.objects.create(company_slug="national-grid", status="pending"))
        # a registered-but-unharvested KZ company
        RegistryCompany.objects.create(company_name="KazMunayGas", slug="kazmunaygas",
                                       sector="energy", country="KZ")

    def _data(self):
        r = self.client.get("/api/globe/layers/")
        self.assertEqual(r.status_code, 200)
        return r.json()

    def test_stats_are_live_and_real(self):
        d = self._data()
        s = d["stats"]
        self.assertEqual(s["companies"], 2)          # NG + KazMunayGas
        self.assertGreater(s["datapoints"], 0)        # NG harvested
        self.assertGreater(s["evidence"], 0)
        self.assertEqual(s["countries"], 1)           # one published profile
        # verification_rate is a real fraction (or None), never a fabricated 98%
        self.assertTrue(s["verification_rate"] is None or 0 <= s["verification_rate"] <= 100)

    def test_markers_are_flagged_representative(self):
        d = self._data()
        self.assertTrue(d["markers_representative"])   # honesty flag
        self.assertIn("representative", d["disclaimer"])

    def test_markers_have_layers_and_real_counts(self):
        d = self._data()
        ng = next(m for m in d["markers"] if m["slug"] == "national-grid")
        self.assertIn("energy", ng["layers"])          # utilities → energy
        self.assertGreater(ng["evidence_count"], 0)    # real, harvested
        # carbon/capital layers only where real datapoints exist
        self.assertTrue({"carbon", "capital"} & set(ng["layers"]))

    def test_unharvested_company_has_no_fabricated_data(self):
        d = self._data()
        kmg = next(m for m in d["markers"] if m["slug"] == "kazmunaygas")
        self.assertEqual(kmg["evidence_count"], 0)     # honest zero
        self.assertEqual(kmg["datapoint_count"], 0)
        self.assertNotIn("carbon", kmg["layers"])      # no emissions datapoint → no carbon marker

    def test_featured_countries_present(self):
        d = self._data()
        isos = {c["iso"] for c in d["countries"]}
        self.assertEqual(isos, {"GB", "KZ", "SA", "TR"})

    def test_endpoint_is_read_only(self):
        from harvester.models import Evidence, Datapoint
        before = (Evidence.objects.count(), Datapoint.objects.count())
        self.client.get("/api/globe/layers/")
        self.assertEqual((Evidence.objects.count(), Datapoint.objects.count()), before)


class GlobeCountryEndpointTests(TestCase):
    def setUp(self):
        self.client = Client(SERVER_NAME="localhost")
        self.kz = CountryProfile.objects.create(
            name="Kazakhstan", slug="kazakhstan", iso_code="KZ", is_published=True,
            policy_environment_score=36.0, national_ecoiq_index=29.8)
        RegistryCompany.objects.create(company_name="KazMunayGas", slug="kazmunaygas",
                                       sector="energy", country="KZ")

    def test_scores_from_real_fields(self):
        d = self.client.get("/api/globe/country/kazakhstan/").json()
        gov = next(s for s in d["scores"] if s["key"] == "governance")
        self.assertEqual(gov["value"], 36.0)             # real CountryProfile field
        overall = next(s for s in d["scores"] if s["key"] == "overall")
        self.assertEqual(overall["value"], 29.8)

    def test_missing_score_is_null_not_fabricated(self):
        d = self.client.get("/api/globe/country/kazakhstan/").json()
        trans = next(s for s in d["scores"] if s["key"] == "transition")
        self.assertIsNone(trans["value"])               # field unset → null → "insufficient evidence"

    def test_why_checklist_is_evidence_grounded(self):
        # KZ has a registered but unharvested company → all checklist items false
        d = self.client.get("/api/globe/country/kazakhstan/").json()
        self.assertTrue(all(not k["ok"] for k in d["why"]["checklist"]))
        self.assertEqual(d["stats"]["evidence"], 0)
        self.assertTrue(d["data_expansion"])

    def test_unknown_country_404(self):
        self.assertEqual(self.client.get("/api/globe/country/nope/").status_code, 404)

    def test_read_only(self):
        from harvester.models import Evidence
        before = Evidence.objects.count()
        self.client.get("/api/globe/country/kazakhstan/")
        self.assertEqual(Evidence.objects.count(), before)
