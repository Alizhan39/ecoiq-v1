"""
Living Infrastructure Earth — Phase 0 globe endpoint tests.

Verifies the read-only /api/globe/layers/ endpoint returns live, real data with
representative (honestly flagged) markers and no fabricated statistics.
"""
from django.test import TestCase, Client
from django.urls import reverse

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


class GlobeIntelligenceLayersTests(TestCase):
    """
    Interactive Globe Upgrade — Phase 1: the 5 "intelligence layers"
    (climate risk, investment opportunity, modernisation priority, evidence
    strength, stewardship/impact). Every layer is grounded in a real model
    that already carries a `country` FK (geo_intelligence, khalifa
    stewardship, harvester Evidence) — never a new score invented for the
    globe. A country with zero real rows in a given model must render
    `available=False` and an honest fallback string, never a fabricated value.
    """

    def setUp(self):
        self.client = Client(SERVER_NAME="localhost")
        self.kz = CountryProfile.objects.create(
            name="Kazakhstan", slug="kazakhstan", iso_code="KZ", is_published=True,
        )
        self.gb = CountryProfile.objects.create(
            name="United Kingdom", slug="united-kingdom", iso_code="GB", is_published=True,
        )

    def test_country_with_no_geo_intelligence_data_is_honestly_limited(self):
        d = self.client.get("/api/globe/country/united-kingdom/").json()
        for key in ("climate_risk", "investment_opportunity", "modernisation_priority"):
            layer = d["intelligence"][key]
            self.assertFalse(layer["available"])
            self.assertIsNone(layer["value"])
            self.assertEqual(layer["label"], "Limited EcoIQ coverage")

    def test_country_with_no_stewardship_data_is_honestly_developing(self):
        d = self.client.get("/api/globe/country/united-kingdom/").json()
        self.assertFalse(d["intelligence"]["stewardship_impact"]["available"])
        self.assertEqual(d["intelligence"]["stewardship_impact"]["label"], "Evidence still developing")

    def test_country_with_no_evidence_is_honestly_developing(self):
        d = self.client.get("/api/globe/country/united-kingdom/").json()
        self.assertFalse(d["intelligence"]["evidence_strength"]["available"])
        self.assertIsNone(d["intelligence"]["evidence_strength"]["value"])

    def test_climate_risk_reflects_real_geo_risk_zone(self):
        from geo_intelligence.models import GeoRiskZone
        GeoRiskZone.objects.create(
            name="Almaty Heat Zone", risk_type="extreme_heat", country=self.kz,
            latitude=43.2, longitude=76.9, severity="high", confidence=80.0, is_demo=True,
        )
        d = self.client.get("/api/globe/country/kazakhstan/").json()
        layer = d["intelligence"]["climate_risk"]
        self.assertTrue(layer["available"])
        self.assertEqual(layer["value"], "high")
        self.assertTrue(layer["is_demo"])   # honestly flagged, never presented as verified real-world data

    def test_investment_opportunity_surfaces_real_recommended_action(self):
        from geo_intelligence.models import InvestmentGeoOpportunity
        InvestmentGeoOpportunity.objects.create(
            title="Clean heating package", country=self.kz, latitude=43.2, longitude=76.9,
            opportunity_type="heating_replacement", investment_score=50.0, confidence=70.0,
            recommended_action="Review with Capital Allocation Agent before funder outreach.",
        )
        d = self.client.get("/api/globe/country/kazakhstan/").json()
        layer = d["intelligence"]["investment_opportunity"]
        self.assertTrue(layer["available"])
        self.assertEqual(layer["recommended_action"], "Review with Capital Allocation Agent before funder outreach.")
        # the top-level recommended action prefers this real, human-authored field
        self.assertEqual(d["recommended_next_action"], layer["recommended_action"])

    def test_modernisation_priority_reflects_real_geo_asset(self):
        from geo_intelligence.models import GeoAsset
        GeoAsset.objects.create(
            name="Boiler House #3", asset_type="heating_unit", country=self.kz,
            latitude=43.2, longitude=76.9, modernisation_priority="high",
        )
        d = self.client.get("/api/globe/country/kazakhstan/").json()
        layer = d["intelligence"]["modernisation_priority"]
        self.assertTrue(layer["available"])
        self.assertEqual(layer["value"], "high")

    def test_evidence_strength_is_a_real_verification_rate(self):
        # "national-grid" is the one slug with a real, harvestable pipeline in
        # this test environment (see harvester.pipeline.run_harvest / the
        # sibling GlobeLayersEndpointTests fixture) — assigned to GB here.
        c = Company.objects.create(name="National Grid plc", slug="national-grid", sector="energy", country="GB")
        CompanyProfile.objects.create(company=c, status="public")
        RegistryCompany.objects.create(company_name="National Grid plc", slug="national-grid", sector="utilities", country="GB")
        run_harvest(HarvestJob.objects.create(company_slug="national-grid", status="pending"))
        d = self.client.get("/api/globe/country/united-kingdom/").json()
        layer = d["intelligence"]["evidence_strength"]
        self.assertTrue(layer["available"])
        self.assertTrue(0 <= layer["value"] <= 100)

    def test_stewardship_impact_reflects_real_tour(self):
        from khalifa_stewardship_tour_operating_system.models import StewardshipTour
        StewardshipTour.objects.create(
            title="Kazakhstan Clean Heat Stewardship Tour", slug="kz-clean-heat-test", country=self.kz,
            tour_type="clean_heat", status="approved_with_conditions", participant_capacity=12,
        )
        d = self.client.get("/api/globe/country/kazakhstan/").json()
        layer = d["intelligence"]["stewardship_impact"]
        self.assertTrue(layer["available"])
        self.assertEqual(layer["value"], "approved_with_conditions")

    def test_recommended_action_falls_back_honestly_with_zero_data(self):
        d = self.client.get("/api/globe/country/united-kingdom/").json()
        self.assertTrue(d["recommended_next_action"])   # always a non-empty string
        self.assertIn("evidence", d["recommended_next_action"].lower())

    def test_actions_block_uses_real_existing_routes_only(self):
        d = self.client.get("/api/globe/country/kazakhstan/").json()
        actions = d["actions"]
        self.assertEqual(actions["country_intelligence"], "/countries/kazakhstan/")
        self.assertEqual(actions["geo_intelligence"], "/geo-intelligence/")
        self.assertEqual(actions["decision_studio"], "/decision-studio/")
        self.assertTrue(actions["ai_agents"].startswith("/ai-agents/workbench/?ask="))
        self.assertTrue(actions["evidence"].startswith("/evidence/"))

    def test_intelligence_block_never_modifies_data(self):
        from geo_intelligence.models import GeoRiskZone
        before = GeoRiskZone.objects.count()
        self.client.get("/api/globe/country/kazakhstan/")
        self.assertEqual(GeoRiskZone.objects.count(), before)


class GlobeLayersAvailabilityTests(TestCase):
    """
    /api/globe/layers/ reports which of the 5 intelligence layers have ANY
    real data across the 4 featured countries — the front end never renders
    a toggle for a layer that is empty everywhere.
    """

    def setUp(self):
        self.client = Client(SERVER_NAME="localhost")
        CountryProfile.objects.create(name="United Kingdom", slug="united-kingdom", iso_code="GB", is_published=True)
        CountryProfile.objects.create(name="Kazakhstan", slug="kazakhstan", iso_code="KZ", is_published=True)
        CountryProfile.objects.create(name="Saudi Arabia", slug="saudi-arabia", iso_code="SA", is_published=True)
        CountryProfile.objects.create(name="Turkey", slug="turkey", iso_code="TR", is_published=True)

    def test_all_layers_unavailable_with_zero_real_data(self):
        d = self.client.get("/api/globe/layers/").json()
        self.assertEqual(
            d["intelligence_layers_available"],
            {k: False for k in ["climate_risk", "investment_opportunity", "modernisation_priority", "evidence_strength", "stewardship_impact"]},
        )

    def test_layer_becomes_available_once_one_country_has_real_data(self):
        from geo_intelligence.models import GeoRiskZone
        kz = CountryProfile.objects.get(iso_code="KZ")
        GeoRiskZone.objects.create(name="Test Zone", risk_type="drought", country=kz, latitude=43.2, longitude=76.9)
        d = self.client.get("/api/globe/layers/").json()
        self.assertTrue(d["intelligence_layers_available"]["climate_risk"])
        # unrelated layers with no data anywhere stay unavailable
        self.assertFalse(d["intelligence_layers_available"]["stewardship_impact"])

    def test_intelligence_layers_list_matches_the_five_named_layers(self):
        d = self.client.get("/api/globe/layers/").json()
        self.assertEqual(
            set(d["intelligence_layers"]),
            {"climate_risk", "investment_opportunity", "modernisation_priority", "evidence_strength", "stewardship_impact"},
        )


class LivingEarthTemplateTests(TestCase):
    """Homepage markup for the globe upgrade — quick jump, intelligence layer
    toggles, accessibility labels, reduced-motion support. No raw template
    tags, and no fabricated per-country claims baked into static markup."""

    def setUp(self):
        self.client = Client(SERVER_NAME="localhost")

    def test_quick_jump_select_present_with_accessible_label(self):
        r = self.client.get(reverse("home"))
        self.assertEqual(r.status_code, 200)
        content = r.content.decode()
        self.assertIn('id="le-jump"', content)
        self.assertIn('aria-label="Jump to a country"', content)
        for label in ("Jump to United Kingdom", "Jump to Kazakhstan", "Jump to Saudi Arabia", "Jump to Türkiye"):
            self.assertIn(label, content)

    def test_intelligence_layer_toggles_present_and_hidden_by_default(self):
        r = self.client.get(reverse("home"))
        content = r.content.decode()
        for key in ("climate_risk", "investment_opportunity", "modernisation_priority", "evidence_strength", "stewardship_impact"):
            self.assertIn('data-intel-layer="%s"' % key, content)
        # hidden until JS confirms real data exists — never shown unconditionally
        self.assertIn('class="le-layer le-intel" data-intel-layer="climate_risk" aria-pressed="false" hidden', content)

    def test_country_panel_has_accessible_dialog_role(self):
        r = self.client.get(reverse("home"))
        content = r.content.decode()
        self.assertIn('role="dialog"', content)
        self.assertIn('aria-label="Country intelligence"', content)
        self.assertIn('aria-label="Close country panel"', content)

    def test_reduced_motion_is_respected(self):
        r = self.client.get(reverse("home"))
        content = r.content.decode()
        self.assertIn("prefers-reduced-motion", content)

    def test_no_horizontal_overflow_rule_present_for_mobile(self):
        r = self.client.get(reverse("home"))
        content = r.content.decode()
        self.assertIn("overflow-x:hidden", content)

    def test_no_raw_template_tags_leak(self):
        r = self.client.get(reverse("home"))
        content = r.content.decode()
        self.assertNotIn("{%", content)
        self.assertNotIn("{{", content)
