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
        self.assertTrue(actions["decision_studio"].startswith("/decision-studio/?q="))
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


class GlobeHeatmapEndpointTests(TestCase):
    """
    Global Intelligence Command Globe — Phase 2 heatmap. Real numeric scores
    reused from pandas_scoring_engine's country-level Geo Intelligence
    components; a country with no real data for a metric stays null
    ("neutral"), never a fabricated score to fill the map.
    """

    def setUp(self):
        self.client = Client(SERVER_NAME="localhost")
        self.kz = CountryProfile.objects.create(name="Kazakhstan", slug="kazakhstan", iso_code="KZ", is_published=True, national_ecoiq_index=29.8)
        CountryProfile.objects.create(name="United Kingdom", slug="united-kingdom", iso_code="GB", is_published=True)

    def test_country_with_no_data_is_neutral_not_fabricated(self):
        d = self.client.get("/api/globe/heatmap/").json()
        gb = next(c for c in d["countries"] if c["iso"] == "GB")
        for metric in d["metrics"]:
            self.assertIsNone(gb["scores"][metric])

    def test_ecoiq_score_reflects_real_national_ecoiq_index(self):
        d = self.client.get("/api/globe/heatmap/").json()
        kz = next(c for c in d["countries"] if c["iso"] == "KZ")
        self.assertEqual(kz["scores"]["ecoiq_score"], 29.8)

    def test_climate_risk_score_reflects_real_geo_risk_zones(self):
        from geo_intelligence.models import GeoRiskZone
        GeoRiskZone.objects.create(name="Test Zone", risk_type="drought", country=self.kz, latitude=43.2, longitude=76.9, severity="high")
        d = self.client.get("/api/globe/heatmap/").json()
        kz = next(c for c in d["countries"] if c["iso"] == "KZ")
        self.assertIsNotNone(kz["scores"]["climate_risk"])

    def test_ranges_computed_only_over_real_non_null_values(self):
        d = self.client.get("/api/globe/heatmap/").json()
        # only KZ has a real ecoiq_score in this fixture, so min == max == 29.8
        self.assertEqual(d["ranges"]["ecoiq_score"], {"min": 29.8, "max": 29.8})
        # no country has climate_risk data at all yet in this fixture
        self.assertIsNone(d["ranges"]["climate_risk"])

    def test_metrics_list_matches_the_five_named_heatmap_layers(self):
        d = self.client.get("/api/globe/heatmap/").json()
        self.assertEqual(
            set(d["metrics"]),
            {"climate_risk", "investment_opportunity", "modernisation_priority", "evidence_strength", "ecoiq_score"},
        )

    def test_read_only(self):
        from countries.models import CountryProfile as CP
        before = CP.objects.count()
        self.client.get("/api/globe/heatmap/")
        self.assertEqual(CP.objects.count(), before)


class GlobeCompareEndpointTests(TestCase):
    """
    Phase 3 country comparison — connects to intelligence_analytics_engine's
    real Country Similarity Engine (compare_countries()) rather than a new
    comparison engine. Only the 4 featured countries can be compared, and
    only 2-3 at a time.
    """

    def setUp(self):
        self.client = Client(SERVER_NAME="localhost")
        CountryProfile.objects.create(
            name="Kazakhstan", slug="kazakhstan", iso_code="KZ", is_published=True,
            national_ecoiq_index=29.8, industrial_modernization_score=38.0,
        )
        CountryProfile.objects.create(
            name="United Kingdom", slug="united-kingdom", iso_code="GB", is_published=True,
            national_ecoiq_index=62.4, industrial_modernization_score=55.0,
        )
        CountryProfile.objects.create(name="Saudi Arabia", slug="saudi-arabia", iso_code="SA", is_published=True)
        # compare_countries() (intelligence_analytics_engine) averages real
        # CompanyProfile pillar scores per country — real companies are the
        # data source it needs, matching how build_country_features() works.
        kz_co = Company.objects.create(name="KazMunayGas", slug="kazmunaygas-cmp", sector="energy", country="Kazakhstan")
        CompanyProfile.objects.create(company=kz_co, status="public", ecoiq_total_score=38.0)
        gb_co = Company.objects.create(name="National Grid plc", slug="national-grid-cmp", sector="energy", country="United Kingdom")
        CompanyProfile.objects.create(company=gb_co, status="public", ecoiq_total_score=62.0)

    def test_two_countries_returns_headline_metrics(self):
        d = self.client.get("/api/globe/compare/", {"iso": ["KZ", "GB"]}).json()
        self.assertTrue(d["available"])
        isos = {c["iso"] for c in d["countries"]}
        self.assertEqual(isos, {"KZ", "GB"})

    def test_requires_at_least_two_countries(self):
        r = self.client.get("/api/globe/compare/", {"iso": ["KZ"]})
        self.assertEqual(r.status_code, 400)
        self.assertFalse(r.json()["available"])

    def test_rejects_more_than_three_countries(self):
        r = self.client.get("/api/globe/compare/", {"iso": ["KZ", "GB", "SA", "TR"]})
        self.assertEqual(r.status_code, 400)

    def test_rejects_non_featured_country(self):
        r = self.client.get("/api/globe/compare/", {"iso": ["KZ", "FR"]})
        self.assertEqual(r.status_code, 400)

    def test_headline_intelligence_reuses_the_same_layer_logic_as_country_panel(self):
        d = self.client.get("/api/globe/compare/", {"iso": ["KZ", "GB"]}).json()
        kz = next(c for c in d["countries"] if c["iso"] == "KZ")
        self.assertIn("intelligence", kz)
        self.assertIn("climate_risk", kz["intelligence"])

    def test_key_differences_delegates_to_real_similarity_engine(self):
        d = self.client.get("/api/globe/compare/", {"iso": ["KZ", "GB"]}).json()
        self.assertIn("method", d["key_differences"])
        self.assertIn("sklearn", d["key_differences"]["method"])

    def test_read_only(self):
        from countries.models import CountryProfile as CP
        before = CP.objects.count()
        self.client.get("/api/globe/compare/", {"iso": ["KZ", "GB"]})
        self.assertEqual(CP.objects.count(), before)


class GlobeSignalsEndpointTests(TestCase):
    """
    Phase 1 (signals) / Phase 9 (alerts, same feed) — every signal is a real,
    already-persisted EcoIQ record. Period filtering never fabricates a
    historical trend; when the real data doesn't reach back as far as the
    requested period, historical_coverage_developing is honestly True.
    """

    def setUp(self):
        self.client = Client(SERVER_NAME="localhost")
        self.kz = CountryProfile.objects.create(name="Kazakhstan", slug="kazakhstan", iso_code="KZ", is_published=True)
        CountryProfile.objects.create(name="United Kingdom", slug="united-kingdom", iso_code="GB", is_published=True)

    def test_invalid_period_falls_back_to_latest(self):
        d = self.client.get("/api/globe/signals/", {"period": "not-a-real-period"}).json()
        self.assertEqual(d["period"], "latest")

    def test_risk_zone_produces_a_real_risk_signal(self):
        from geo_intelligence.models import GeoRiskZone
        GeoRiskZone.objects.create(name="Almaty Heat Zone", risk_type="extreme_heat", country=self.kz, latitude=43.2, longitude=76.9, severity="high")
        d = self.client.get("/api/globe/signals/", {"period": "latest"}).json()
        risk_signals = [s for s in d["signals"] if s["type"] == "risk"]
        self.assertEqual(len(risk_signals), 1)
        self.assertEqual(risk_signals[0]["iso"], "KZ")

    def test_investment_opportunity_produces_a_real_opportunity_signal(self):
        from geo_intelligence.models import InvestmentGeoOpportunity
        InvestmentGeoOpportunity.objects.create(title="Clean heating", country=self.kz, latitude=43.2, longitude=76.9, investment_score=50.0)
        d = self.client.get("/api/globe/signals/", {"period": "latest"}).json()
        opp_signals = [s for s in d["signals"] if s["type"] == "opportunity"]
        self.assertEqual(len(opp_signals), 1)

    def test_modernisation_asset_produces_a_real_change_signal(self):
        from geo_intelligence.models import GeoAsset
        GeoAsset.objects.create(name="Boiler House #3", asset_type="heating_unit", country=self.kz, latitude=43.2, longitude=76.9, modernisation_priority="high")
        d = self.client.get("/api/globe/signals/", {"period": "latest"}).json()
        change_signals = [s for s in d["signals"] if s["type"] == "change"]
        self.assertEqual(len(change_signals), 1)

    def test_no_real_data_means_empty_signals_not_fabricated(self):
        d = self.client.get("/api/globe/signals/", {"period": "latest"}).json()
        self.assertEqual(d["signals"], [])
        self.assertEqual(d["signal_count"], 0)

    def test_historical_coverage_developing_is_honest(self):
        from geo_intelligence.models import GeoRiskZone
        GeoRiskZone.objects.create(name="Test Zone", risk_type="drought", country=self.kz, latitude=43.2, longitude=76.9)
        d = self.client.get("/api/globe/signals/", {"period": "1y"}).json()
        # the zone was just created (last_updated=now), so it's nowhere near
        # a year old — real 1-year coverage genuinely doesn't exist yet
        self.assertTrue(d["historical_coverage_developing"])

    def test_read_only(self):
        from geo_intelligence.models import GeoRiskZone
        before = GeoRiskZone.objects.count()
        self.client.get("/api/globe/signals/")
        self.assertEqual(GeoRiskZone.objects.count(), before)


class GlobeAgentActivityEndpointTests(TestCase):
    """
    Phase 6 — real "which agent has looked at this country" via the
    already-existing workbench_agent_slug soft reference on GeoAsset /
    InvestmentGeoOpportunity (GeoRiskZone has no such field and is correctly
    excluded — see core/globe.py _agent_activity_for_country). Never
    fabricates a run that didn't happen: has_run=False when the mapped agent
    genuinely has zero real AgentRun rows.
    """

    def setUp(self):
        self.client = Client(SERVER_NAME="localhost")
        self.kz = CountryProfile.objects.create(name="Kazakhstan", slug="kazakhstan", iso_code="KZ", is_published=True)
        CountryProfile.objects.create(name="United Kingdom", slug="united-kingdom", iso_code="GB", is_published=True)

    def test_no_geo_reference_means_empty_findings(self):
        d = self.client.get("/api/globe/agent-activity/").json()
        gb = next(c for c in d["countries"] if c["iso"] == "GB")
        self.assertEqual(gb["findings"], [])

    def test_unknown_agent_slug_is_skipped_not_fabricated(self):
        from geo_intelligence.models import GeoAsset
        GeoAsset.objects.create(
            name="Test Asset", asset_type="other", country=self.kz, latitude=43.2, longitude=76.9,
            workbench_agent_slug="not-a-real-agent-id",
        )
        d = self.client.get("/api/globe/agent-activity/").json()
        kz = next(c for c in d["countries"] if c["iso"] == "KZ")
        self.assertEqual(kz["findings"], [])

    def test_real_agent_with_no_runs_reports_has_run_false(self):
        from agent_runtime_model_router.models import AgentRegistryEntry
        from geo_intelligence.models import GeoAsset
        AgentRegistryEntry.objects.create(agent_id="research-agent", agent_name="Research Agent")
        GeoAsset.objects.create(
            name="Test Asset", asset_type="other", country=self.kz, latitude=43.2, longitude=76.9,
            workbench_agent_slug="research-agent",
        )
        d = self.client.get("/api/globe/agent-activity/").json()
        kz = next(c for c in d["countries"] if c["iso"] == "KZ")
        self.assertEqual(len(kz["findings"]), 1)
        self.assertFalse(kz["findings"][0]["has_run"])
        self.assertIsNone(kz["findings"][0]["last_run_id"])

    def test_real_agent_with_a_real_run_reports_it_honestly(self):
        from agent_runtime_model_router.models import AgentRegistryEntry, AgentRun
        from geo_intelligence.models import InvestmentGeoOpportunity
        entry = AgentRegistryEntry.objects.create(agent_id="capital-allocation-agent", agent_name="Capital Allocation Agent")
        run = AgentRun.objects.create(agent=entry, task_type="demo", execution_mode_requested="deterministic_test", status="completed")
        InvestmentGeoOpportunity.objects.create(
            title="Test Opportunity", country=self.kz, latitude=43.2, longitude=76.9,
            workbench_agent_slug="capital-allocation-agent",
        )
        d = self.client.get("/api/globe/agent-activity/").json()
        kz = next(c for c in d["countries"] if c["iso"] == "KZ")
        self.assertEqual(len(kz["findings"]), 1)
        self.assertTrue(kz["findings"][0]["has_run"])
        self.assertEqual(kz["findings"][0]["last_run_id"], run.pk)
        self.assertEqual(kz["findings"][0]["link"], "/ai-agents/agent/capital-allocation-agent/")

    def test_georiskzone_has_no_workbench_field_and_is_never_queried(self):
        # regression guard for the exact bug fixed on rebase: GeoRiskZone has
        # no workbench_agent_slug field at all, so it must never be queried
        # for one — this must not raise FieldError.
        from geo_intelligence.models import GeoRiskZone
        GeoRiskZone.objects.create(name="Test Zone", risk_type="drought", country=self.kz, latitude=43.2, longitude=76.9)
        r = self.client.get("/api/globe/agent-activity/")
        self.assertEqual(r.status_code, 200)


class GlobeEconomicAndCapitalSignalsTests(TestCase):
    """
    Phase 2 — economic signals and capital flows reuse real CountryProfile
    macro/financing fields (never computed here). Government revenue
    composition and trade (exports/imports) have no real EcoIQ data source
    anywhere in the platform today — the honest, permanent "not yet
    available" stub must never be replaced with a fabricated figure.
    """

    def setUp(self):
        self.client = Client(SERVER_NAME="localhost")
        self.kz = CountryProfile.objects.create(
            name="Kazakhstan", slug="kazakhstan", iso_code="KZ", is_published=True,
            gdp_usd=259000000000, gdp_growth_pct=4.6, population_millions=21.1,
            estimated_transition_gap_usd=35000000000, green_finance_available_usd=2800000000,
        )
        CountryProfile.objects.create(name="United Kingdom", slug="united-kingdom", iso_code="GB", is_published=True)

    def test_economic_signals_are_real_countryprofile_fields(self):
        d = self.client.get("/api/globe/country/kazakhstan/").json()
        e = d["economic_signals"]
        self.assertEqual(e["gdp_usd"], 259000000000)
        self.assertEqual(e["gdp_growth_pct"], 4.6)
        self.assertEqual(e["population_millions"], 21.1)

    def test_unset_economic_field_is_null_not_fabricated(self):
        d = self.client.get("/api/globe/country/kazakhstan/").json()
        self.assertIsNone(d["economic_signals"]["inflation_pct"])

    def test_country_with_no_macro_data_is_all_null(self):
        d = self.client.get("/api/globe/country/united-kingdom/").json()
        e = d["economic_signals"]
        for key in ("gdp_usd", "gdp_growth_pct", "inflation_pct", "population_millions"):
            self.assertIsNone(e[key])

    def test_capital_flows_are_real_countryprofile_financing_fields(self):
        d = self.client.get("/api/globe/country/kazakhstan/").json()
        c = d["capital_flows"]
        self.assertEqual(c["estimated_transition_gap_usd"], 35000000000)
        self.assertEqual(c["green_finance_available_usd"], 2800000000)

    def test_capital_flows_surfaces_real_top_investment_opportunity(self):
        from geo_intelligence.models import InvestmentGeoOpportunity
        InvestmentGeoOpportunity.objects.create(
            title="Clean heating", country=self.kz, latitude=43.2, longitude=76.9,
            investment_score=50.0, estimated_impact="GBP 700 estimated annual benefit",
        )
        d = self.client.get("/api/globe/country/kazakhstan/").json()
        top = d["capital_flows"]["top_opportunity"]
        self.assertEqual(top["title"], "Clean heating")
        self.assertEqual(top["investment_score"], 50.0)

    def test_no_opportunity_means_null_top_opportunity_not_fabricated(self):
        d = self.client.get("/api/globe/country/united-kingdom/").json()
        self.assertIsNone(d["capital_flows"]["top_opportunity"])

    def test_trade_and_revenue_composition_is_an_honest_permanent_stub(self):
        d = self.client.get("/api/globe/country/kazakhstan/").json()
        t = d["trade_and_revenue_composition"]
        self.assertFalse(t["available"])
        self.assertIn("does not yet ingest", t["reason"])


class CompareCountriesServiceTests(TestCase):
    """intelligence_analytics_engine.services.similarity.compare_countries()
    — the Interactive Globe's country comparison calls straight into this
    real, existing engine rather than a duplicate one."""

    def setUp(self):
        self.kz = CountryProfile.objects.create(
            name="Kazakhstan", slug="kazakhstan", iso_code="KZ", is_published=True,
            industrial_modernization_score=38.0,
        )
        self.gb = CountryProfile.objects.create(
            name="United Kingdom", slug="united-kingdom", iso_code="GB", is_published=True,
            industrial_modernization_score=55.0,
        )
        self.sa = CountryProfile.objects.create(name="Saudi Arabia", slug="saudi-arabia", iso_code="SA", is_published=True)
        kz_co = Company.objects.create(name="KazMunayGas", slug="kazmunaygas-svc", sector="energy", country="Kazakhstan")
        CompanyProfile.objects.create(company=kz_co, status="public", ecoiq_total_score=38.0)
        gb_co = Company.objects.create(name="National Grid plc", slug="national-grid-svc", sector="energy", country="United Kingdom")
        CompanyProfile.objects.create(company=gb_co, status="public", ecoiq_total_score=62.0)
        sa_co = Company.objects.create(name="Saudi Aramco", slug="saudi-aramco-svc", sector="energy", country="Saudi Arabia")
        CompanyProfile.objects.create(company=sa_co, status="public", ecoiq_total_score=30.0)

    def test_requires_two_or_three_countries(self):
        from intelligence_analytics_engine.services.similarity import compare_countries
        result = compare_countries([self.kz.pk])
        self.assertFalse(result["available"])

    def test_rejects_more_than_three(self):
        from intelligence_analytics_engine.services.similarity import compare_countries
        result = compare_countries([self.kz.pk, self.gb.pk, self.sa.pk, 9999])
        self.assertFalse(result["available"])

    def test_two_real_countries_returns_a_real_pairwise_difference(self):
        from intelligence_analytics_engine.services.similarity import compare_countries
        result = compare_countries([self.kz.pk, self.gb.pk])
        self.assertTrue(result["available"])
        self.assertEqual(len(result["pairs"]), 1)
        self.assertEqual({result["pairs"][0]["a"], result["pairs"][0]["b"]}, {"Kazakhstan", "United Kingdom"})

    def test_three_real_countries_returns_three_pairs(self):
        from intelligence_analytics_engine.services.similarity import compare_countries
        result = compare_countries([self.kz.pk, self.gb.pk, self.sa.pk])
        self.assertTrue(result["available"])
        self.assertEqual(len(result["pairs"]), 3)

    def test_method_names_the_real_reused_technique(self):
        from intelligence_analytics_engine.services.similarity import compare_countries
        result = compare_countries([self.kz.pk, self.gb.pk])
        self.assertIn("same engine as find_similar_countries", result["method"])


class DecisionStudioPrefillTests(TestCase):
    """Optional ?q= prefill added for the globe's "Ask EcoIQ about the
    world" action — never auto-submits, never bypasses the existing
    rate-limit/cost-control path in ask()."""

    def test_no_prefill_by_default(self):
        r = self.client.get(reverse("decision_studio:studio"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'value=""')

    def test_prefill_appears_in_the_input_value(self):
        r = self.client.get(reverse("decision_studio:studio"), {"q": "Where are the strongest modernisation opportunities?"})
        self.assertContains(r, "Where are the strongest modernisation opportunities?")

    def test_prefill_is_escaped_not_a_stored_or_executed_value(self):
        r = self.client.get(reverse("decision_studio:studio"), {"q": '<script>alert(1)</script>'})
        self.assertNotContains(r, "<script>alert(1)</script>")

    def test_prefill_is_truncated_to_max_question_length(self):
        from decision_studio.views import MAX_QUESTION_LENGTH
        long_q = "a" * (MAX_QUESTION_LENGTH + 50)
        r = self.client.get(reverse("decision_studio:studio"), {"q": long_q})
        content = r.content.decode()
        self.assertNotIn("a" * (MAX_QUESTION_LENGTH + 1), content)


class LivingEarthPhase2TemplateTests(TestCase):
    """Homepage markup for Phase 2: Ask-the-planet CTA, live signals feed +
    timeline control, reset view, and the new country panel sections."""

    def setUp(self):
        self.client = Client(SERVER_NAME="localhost")

    def test_ask_planet_cta_links_to_decision_studio(self):
        r = self.client.get(reverse("home"))
        content = r.content.decode()
        self.assertIn('id="le-ask-planet"', content)
        self.assertIn('href="/decision-studio/?q=', content)

    def test_signals_feed_present_with_timeline_control(self):
        r = self.client.get(reverse("home"))
        content = r.content.decode()
        self.assertIn('id="le-signals-list"', content)
        for period in ("latest", "7d", "30d", "1y"):
            self.assertIn('data-period="%s"' % period, content)

    def test_signal_type_legend_present(self):
        r = self.client.get(reverse("home"))
        content = r.content.decode()
        for tag in ("risk", "opportunity", "change", "evidence_update", "agent_finding"):
            self.assertIn('le-sig-tag %s' % tag, content)

    def test_reset_view_control_present(self):
        r = self.client.get(reverse("home"))
        content = r.content.decode()
        self.assertIn('id="le-reset-view"', content)

    def test_new_panel_sections_present(self):
        r = self.client.get(reverse("home"))
        content = r.content.decode()
        for el_id in ("le-panel-economic", "le-panel-capital", "le-panel-trade"):
            self.assertIn('id="%s"' % el_id, content)

    def test_no_raw_template_tags_leak(self):
        r = self.client.get(reverse("home"))
        content = r.content.decode()
        self.assertNotIn("{%", content)
        self.assertNotIn("{{", content)
