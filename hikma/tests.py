"""
Regression tests for the Hikma Evidence Layer read surface.

Covers exactly the surface that exists today — no speculative behaviour:

  1. Models           — Evidence / AssessmentRun creation, extraction_method
                        derivation from source_type, and updated_at staying null
                        (the model has no such field).
  2. Ingestion        — idempotency: running it twice leaves Evidence /
                        AssessmentRun counts unchanged.
  3. Endpoints        — the four routes:
                          GET  assess/<slug>/latest/          200 + 404
                          GET  assess/<slug>/evidence/        200 + 404
                          GET  assess/<slug>/contradictions/  200 + 404
                          POST assess/<slug>/refresh/         auth gate + success
  4. Non-mutation     — repeated GETs leave row counts stable.
  5. Honesty guards   — scholar-review markers on ingested evidence, hedged
                        contradiction copy (no accusations / rulings / religious
                        framing), and every numeric figure in a response equal
                        to its stored AssessmentResult source.

Everything here is deterministic and offline: ingestion reads CompanyProfile
fields (no network) and scoring reuses mizan/scoring.py. There is no live-prose
layer in these endpoints to stub — the tests assert structure and guards, not
generated wording.
"""
from django.test import TestCase, Client
from django.core.cache import cache

from league.models import Company
from companies.models import CompanyProfile
from hikma.models import Evidence, AssessmentRun
from hikma.ingest import ingest_for_profile, extract_evidence
from hikma.assessment import build_assessment
from hikma.contradictions import extraction_method, analyze
from api.models import APIKey


# Worked-example fixture (modelled on the Schneider/Samruk specs): rich enough
# that ingestion yields a fully populated SAY / DO / SHOW split with known counts.
EXPECTED_SAY, EXPECTED_DO, EXPECTED_SHOW = 4, 5, 7


def make_company(slug="samruk-energy"):
    """Create a league.Company + CompanyProfile whose fields drive a known,
    deterministic SAY/DO/SHOW ingestion result."""
    company = Company.objects.create(
        name="Samruk Energy",
        slug=slug,
        sector="energy",
        country="KZ",
    )
    profile = CompanyProfile.objects.create(
        company=company,
        status="public",
        # SAY drivers
        ai_summary="Commits to a net-zero carbon transition and decarbonisation roadmap.",
        ai_modernization_report="Plan to modernise grid assets over the next decade.",
        emissions_reduction_target=42.0,
        sustainability_report_url="https://example.com/sustainability.pdf",
        # DO drivers
        modernization_investment=250_000_000,
        community_investment=12_000_000,
        renewable_energy_share=35.0,
        modernization_projects=["Grid upgrade", "Solar pilot"],
        # SHOW drivers
        estimated_emissions=1_200_000,
        pollution_level="medium",
        controversy_risk_score=28.0,
        transparency_score_detail=64.0,
        ecoiq_total_score=71.5,
        public_sources=[
            {"url": "https://reg.example/filing", "title": "Regulator filing"},
            {"url": "https://data.example/set", "title": "Emissions dataset"},
        ],
    )
    return company, profile


# ── 1. Models ─────────────────────────────────────────────────────────────────
class EvidenceModelTests(TestCase):
    def test_evidence_and_run_creation(self):
        company, profile = make_company()
        ev = Evidence.objects.create(
            company=profile, subject_ref=company.slug, kind="say",
            statement="Stated commitment.", source_type="company_disclosure",
            confidence_tier="ai-seeded", confidence_score=0.5,
        )
        self.assertEqual(ev.kind, "say")
        self.assertTrue(ev.scholar_review_required)  # default marker

        run = AssessmentRun.objects.create(
            company=profile, subject_ref=company.slug, status="done",
            result=build_assessment(profile),
        )
        self.assertEqual(run.status, "done")
        self.assertIn("composite_score", run.result)

    def test_extraction_method_derivation(self):
        self.assertEqual(extraction_method("ecoiq_assessment"), "ecoiq-computed")
        self.assertEqual(extraction_method("company_disclosure"), "profile-field-extraction")
        self.assertEqual(extraction_method("sustainability_report"), "profile-field-extraction")
        self.assertEqual(extraction_method("dataset"), "model-estimate")
        self.assertEqual(extraction_method("public_source"), "cited-source")
        self.assertEqual(extraction_method("unknown-thing"), "unspecified")

    def test_evidence_has_no_updated_at_field(self):
        field_names = {f.name for f in Evidence._meta.get_fields()}
        self.assertIn("created_at", field_names)
        self.assertNotIn("updated_at", field_names)


# ── 2. Ingestion idempotency ──────────────────────────────────────────────────
class IngestionIdempotencyTests(TestCase):
    def test_extract_is_pure_no_writes(self):
        _, profile = make_company()
        before = Evidence.objects.count()
        out = extract_evidence(profile)
        self.assertEqual(Evidence.objects.count(), before)  # pure function
        self.assertEqual(len(out["records"]), EXPECTED_SAY + EXPECTED_DO + EXPECTED_SHOW)

    def test_double_ingest_creates_no_duplicates(self):
        _, profile = make_company()
        first = ingest_for_profile(profile)
        self.assertEqual(first["created"], EXPECTED_SAY + EXPECTED_DO + EXPECTED_SHOW)
        self.assertEqual(first["skipped"], 0)
        count_after_first = Evidence.objects.count()

        second = ingest_for_profile(profile)
        self.assertEqual(second["created"], 0)
        self.assertEqual(second["skipped"], count_after_first)
        self.assertEqual(Evidence.objects.count(), count_after_first)  # stable

    def test_known_say_do_show_split(self):
        _, profile = make_company()
        ingest_for_profile(profile)
        self.assertEqual(Evidence.objects.filter(kind="say").count(), EXPECTED_SAY)
        self.assertEqual(Evidence.objects.filter(kind="do").count(), EXPECTED_DO)
        self.assertEqual(Evidence.objects.filter(kind="show").count(), EXPECTED_SHOW)


# ── shared base for endpoint tests ────────────────────────────────────────────
class _EndpointBase(TestCase):
    def setUp(self):
        cache.clear()  # per-IP rate-limit/throttle state must not leak between tests
        self.client = Client(SERVER_NAME="localhost")
        self.company, self.profile = make_company()
        self.slug = self.company.slug
        ingest_for_profile(self.profile)
        self.run = AssessmentRun.objects.create(
            company=self.profile, subject_ref=self.slug, status="done",
            result=build_assessment(self.profile),
        )


# ── 3a. latest ────────────────────────────────────────────────────────────────
class LatestEndpointTests(_EndpointBase):
    def test_200_shape(self):
        r = self.client.get(f"/api/v1/assess/{self.slug}/latest/")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        for key in ("assessment_run_id", "composite_score", "dimensions",
                    "evidence_counts", "_meta"):
            self.assertIn(key, body)
        self.assertTrue(body["_meta"]["read_only"])

    def test_404_unknown(self):
        r = self.client.get("/api/v1/assess/does-not-exist/latest/")
        self.assertEqual(r.status_code, 404)

    def test_numbers_equal_stored_result(self):
        """Every numeric figure in the response equals its AssessmentResult source."""
        body = self.client.get(f"/api/v1/assess/{self.slug}/latest/").json()
        src = self.run.result
        self.assertEqual(body["composite_score"], src["composite_score"])
        self.assertEqual(body["evidence_counts"], src["evidence_counts"])
        self.assertEqual(body["dimensions"], src["dimensions"])


# ── 3b. evidence ──────────────────────────────────────────────────────────────
class EvidenceEndpointTests(_EndpointBase):
    def test_200_shape_and_grouping(self):
        r = self.client.get(f"/api/v1/assess/{self.slug}/evidence/")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertTrue(body["read_only"])
        self.assertEqual(body["evidence_counts"],
                         {"say": EXPECTED_SAY, "do": EXPECTED_DO, "show": EXPECTED_SHOW})
        say0 = body["evidence"]["say"][0]
        for key in ("id", "kind", "statement", "source_url", "source_type",
                    "confidence", "extraction_method", "metric",
                    "created_at", "updated_at"):
            self.assertIn(key, say0)
        self.assertIsNone(say0["updated_at"])  # no model field

    def test_404_unknown(self):
        r = self.client.get("/api/v1/assess/nope/evidence/")
        self.assertEqual(r.status_code, 404)

    def test_metric_values_equal_source_rows(self):
        body = self.client.get(f"/api/v1/assess/{self.slug}/evidence/").json()
        items = body["evidence"]["say"] + body["evidence"]["do"] + body["evidence"]["show"]
        for item in items:
            m = item["metric"]
            if m["value"] is not None:
                src = Evidence.objects.get(id=item["id"])
                self.assertEqual(m["value"], src.metric_value)
                self.assertEqual(m["name"], src.metric_name or None)

    def test_target_metric_present(self):
        body = self.client.get(f"/api/v1/assess/{self.slug}/evidence/").json()
        targets = [i for i in body["evidence"]["say"]
                   if i["metric"]["name"] == "emissions_reduction_target"]
        self.assertEqual(len(targets), 1)
        self.assertEqual(targets[0]["metric"]["value"], 42.0)


# ── 3c. contradictions ────────────────────────────────────────────────────────
HEDGED_PHRASES = (
    "requires verification", "possible greenwashing signal",
    "not independently verified", "potential gap", "indicative",
    "evidence confidence is limited",
)
# Accusatory / legal / religious tokens that must never appear in a payload.
# ("ruling" is deliberately excluded — the disclaimers legitimately say
#  "not a ruling".)
FORBIDDEN_TOKENS = (
    "guilty", "illegal", "fraud", "lying", "fatwa", "halal", "haram",
    "verdict", "sharia", "quran",
)


def _all_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _all_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _all_strings(v)


class ContradictionEndpointTests(_EndpointBase):
    def test_200_shape(self):
        r = self.client.get(f"/api/v1/assess/{self.slug}/contradictions/")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        for key in ("company_slug", "generated_at", "evidence_counts",
                    "contradiction_signals", "greenwashing_signals",
                    "verification_gaps", "recommended_next_questions",
                    "disclaimer", "read_only"):
            self.assertIn(key, body)
        self.assertTrue(body["read_only"])

    def test_404_unknown(self):
        r = self.client.get("/api/v1/assess/nope/contradictions/")
        self.assertEqual(r.status_code, 404)

    def test_language_is_hedged_never_accusatory(self):
        body = self.client.get(f"/api/v1/assess/{self.slug}/contradictions/").json()
        blob = " ".join(_all_strings(body)).lower()
        for tok in FORBIDDEN_TOKENS:
            self.assertNotIn(tok, blob, msg=f"accusatory/religious token leaked: {tok}")
        # at least one hedged phrase present (signals or disclaimer)
        self.assertTrue(any(p in blob for p in HEDGED_PHRASES),
                        msg="no hedged language found in contradiction payload")

    def test_no_religious_framing_in_any_endpoint(self):
        for path in ("latest", "evidence", "contradictions"):
            body = self.client.get(f"/api/v1/assess/{self.slug}/{path}/").json()
            blob = " ".join(_all_strings(body)).lower()
            for tok in FORBIDDEN_TOKENS:
                self.assertNotIn(tok, blob, msg=f"{tok} leaked in {path}")


# ── 4. Non-mutation ───────────────────────────────────────────────────────────
class NonMutationTests(_EndpointBase):
    def test_repeated_gets_do_not_change_row_counts(self):
        before = (Evidence.objects.count(), AssessmentRun.objects.count())
        for _ in range(3):
            self.client.get(f"/api/v1/assess/{self.slug}/evidence/")
            self.client.get(f"/api/v1/assess/{self.slug}/contradictions/")
            self.client.get(f"/api/v1/assess/{self.slug}/latest/")
        after = (Evidence.objects.count(), AssessmentRun.objects.count())
        self.assertEqual(before, after)


# ── 3d / 5. refresh auth gate + honesty markers ───────────────────────────────
class RefreshAuthTests(_EndpointBase):
    def test_unauthenticated_post_is_rejected(self):
        r = self.client.post(f"/api/v1/assess/{self.slug}/refresh/")
        self.assertIn(r.status_code, (401, 403))

    def test_authenticated_post_succeeds(self):
        _key, raw = APIKey.create_key(name="hikma-test")
        r = self.client.post(f"/api/v1/assess/{self.slug}/refresh/",
                             HTTP_X_API_KEY=raw)
        self.assertEqual(r.status_code, 202)
        body = r.json()
        self.assertEqual(body["status"], "done")
        # re-run is idempotent: nothing new created the second time
        self.assertEqual(body["evidence_created"], 0)

    def test_refresh_unknown_company_404(self):
        _key, raw = APIKey.create_key(name="hikma-test")
        r = self.client.post("/api/v1/assess/nope/refresh/", HTTP_X_API_KEY=raw)
        self.assertEqual(r.status_code, 404)


class HonestyMarkerTests(_EndpointBase):
    def test_ingested_evidence_flagged_for_scholar_review(self):
        self.assertTrue(all(
            e.scholar_review_required for e in Evidence.objects.all()
        ))

    def test_low_confidence_tiers_are_present_and_marked(self):
        low = Evidence.objects.filter(confidence_tier__in=["ai-seeded", "model-estimate"])
        self.assertTrue(low.exists())
        self.assertTrue(all(e.scholar_review_required for e in low))

    def test_assessment_flags_scholar_review(self):
        self.assertTrue(self.run.result["flags"]["scholar_review_required"])

    def test_disclaimers_are_indicative_not_rulings(self):
        for path in ("latest", "evidence", "contradictions"):
            body = self.client.get(f"/api/v1/assess/{self.slug}/{path}/").json()
            blob = " ".join(_all_strings(body)).lower()
            self.assertIn("indicative", blob)  # carries the "indicative" marker
            # disclaims being a ruling (singular "not a ruling" or plural "or rulings")
            self.assertTrue("not a ruling" in blob or "or rulings" in blob,
                            msg=f"{path} disclaimer does not disclaim rulings")
