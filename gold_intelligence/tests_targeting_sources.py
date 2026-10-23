"""Offline regression tests: official-source stages, dated rights overlay and access."""
from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from countries.models import CountryProfile
from gold_intelligence.models import GoldCadastreSnapshot, GoldProject, ProjectMembership
from gold_intelligence.management.commands.fetch_usgs_mrds_gold import collect_source_pages
from gold_intelligence.management.commands.convert_usgs_mrds_gold import convert_mrds_features

SQUARE = {
    "type": "Polygon",
    "coordinates": [[[76.7, 43.8], [76.8, 43.8], [76.8, 43.9],
                     [76.7, 43.9], [76.7, 43.8]]],
}


class OfficialDataPipelineTests(TestCase):
    def test_fetcher_collects_page_without_contacting_network(self):
        def local_page(bbox, offset):
            self.assertEqual(offset, 0)
            self.assertEqual(bbox, (74.0, 42.0, 80.0, 46.0))
            return {
                "type": "FeatureCollection",
                "features": [
                    {"type": "Feature", "geometry": {"type": "Point", "coordinates": [76.2, 44.3]},
                     "properties": {"dep_id": "G-1", "site_name": "archive record", "code_list": "Au"}},
                ],
            }
        result = collect_source_pages(page_loader=local_page)
        self.assertEqual(len(result["features"]), 1)
        normalized, discarded = convert_mrds_features(result, bounds=(74, 42, 80, 46))
        self.assertEqual(discarded, 0)
        self.assertEqual(normalized["features"][0]["properties"]["feature_kind"], "reference_occurrence")
        self.assertIsNone(normalized["features"][0]["properties"]["source_observed_on"])
        self.assertEqual(normalized["features"][0]["properties"]["evidence"], {})

    def test_fake_gold_code_and_outside_bbox_are_rejected(self):
        raw = {
            "type": "FeatureCollection", "features": [
                {"type": "Feature", "geometry": {"type": "Point", "coordinates": [76.3, 44.2]},
                 "properties": {"dep_id": "C-1", "code_list": "Cu"}},
                {"type": "Feature", "geometry": {"type": "Point", "coordinates": [90.5, 44.2]},
                 "properties": {"dep_id": "A-2", "code_list": "Au"}},
            ],
        }
        normalized, discarded = convert_mrds_features(raw, bounds=(74, 42, 80, 46))
        self.assertEqual(len(normalized["features"]), 0)
        self.assertEqual(discarded, 2)


class CadastreAccessTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="cadastral-reader", password="test-password-123")
        self.staff = User.objects.create_user(username="cadastral-staff", password="test-password-123", is_staff=True)
        self.kz = CountryProfile.objects.create(name="Kazakhstan", slug="kazakhstan", iso_code="KZ", is_published=True)
        self.project = GoldProject.objects.create(name="Cadastre Pilot", slug="cadastre-pilot", country=self.kz)
        self.row = GoldCadastreSnapshot.objects.create(
            parcel_id="example-official-id",
            snapshot_on=date(2026, 10, 1),
            geometry=SQUARE, recorded_status="licenced",
            source_name="Official snapshot (fixture only)",
            source_url="https://minerals.e-qazyna.kz/en/start",
            source_reference="fixture-not-a-real-record",
            reuse_terms="Test fixture rights confirmation",
            source_sha256="a" * 64, project=self.project,
            review_state="pending",
        )

    def test_cadastre_is_hidden_until_internal_review(self):
        self.client.force_login(self.staff)
        url = "/gold-intelligence/targets/cadastre.geojson"
        self.assertEqual(self.client.get(url).json()["features"], [])
        self.row.review_state = "reviewed"
        self.row.full_clean()
        self.row.save()
        data = self.client.get(url).json()
        self.assertEqual(len(data["features"]), 1)
        self.assertFalse(data["features"][0]["properties"]["current_status_verified"])
        self.assertIsNone(data["features"][0]["properties"]["available_for_application"])
        self.assertFalse(data["features"][0]["properties"]["drilling_authorized"])

    def test_unassigned_or_ungranted_records_are_invisible(self):
        self.row.review_state = "reviewed"
        self.row.save()
        self.client.force_login(self.user)
        url = "/gold-intelligence/targets/cadastre.geojson"
        self.assertEqual(self.client.get(url).json()["features"], [])
        member = ProjectMembership.objects.create(project=self.project, user=self.user, role="viewer")
        self.assertEqual(len(self.client.get(url).json()["features"]), 1)
        member.is_active = False
        member.save()
        self.assertEqual(self.client.get(url).json()["features"], [])

    def test_anonymous_cannot_access_rights(self):
        self.assertEqual(self.client.get("/gold-intelligence/targets/cadastre.geojson").status_code, 302)

    def test_point_not_allowed_as_cadastral_boundary(self):
        self.row.geometry = {"type": "Point", "coordinates": [76.7, 43.8]}
        with self.assertRaises(ValidationError):
            self.row.full_clean()
