"""GeoJSON targeting: trust gates, visibility, geometry validation, no fake results."""
import json
from datetime import date

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client, TestCase

from countries.models import CountryProfile
from gold_intelligence.models import GoldProject, GoldTarget, ProjectMembership
from gold_intelligence.services.target_geojson import validate_geometry, target_feature


class GeometryTests(TestCase):
    def test_lon_lat_order_and_closed_polygon(self):
        self.assertEqual(validate_geometry({"type": "Point", "coordinates": [76.7, 43.6]})["type"], "Point")
        with self.assertRaises(ValueError):
            validate_geometry({"type": "Point", "coordinates": [999, 43]})
        with self.assertRaises(ValueError):
            validate_geometry({"type": "Polygon", "coordinates": [[[76, 43], [77, 43], [77, 44], [76, 44]]]})

    def test_missing_geological_features_stay_null(self):
        record = self._make_unsaved()
        data = target_feature(record)
        self.assertIsNone(data["properties"]["screening_score"])
        self.assertEqual(data["properties"]["rights_status"], "unknown")
        self.assertFalse(data["properties"]["drilling_authorized"])

    @staticmethod
    def _make_unsaved():
        return GoldTarget(
            target_id="ref-one", name="Sourced historical occurrence", region="Kalba",
            feature_kind="reference_occurrence",
            geometry={"type": "Point", "coordinates": [82.0, 49.0]},
            source_name="Archive", source_url="https://www.usgs.gov/",
            source_reference="archive-id", source_observed_on=date(1996, 1, 1),
            source_rights="public domain (operator to verify)",
            rights_status="unknown", review_state="pending", is_demo=False,
        )

    def test_positive_licence_status_requires_snapshot_evidence(self):
        record = self._make_unsaved()
        record.rights_status = "confirmed_available"
        with self.assertRaises(ValidationError):
            record.full_clean()


class TargetApiTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.reader = User.objects.create_user(username="geo-reader", password="strong-test-password")
        self.staff = User.objects.create_user(username="geo-admin", password="strong-test-password", is_staff=True)
        self.kz = CountryProfile.objects.create(
            name="Kazakhstan", slug="kazakhstan", iso_code="KZ", is_published=True
        )
        self.project = GoldProject.objects.create(
            name="Gold Atlas Project", slug="gold-atlas-project", country=self.kz
        )
        self.target = GoldTarget.objects.create(
            target_id="ref-001", name="Historical reference", region="Kalba",
            feature_kind="reference_occurrence",
            geometry={"type": "Point", "coordinates": [82.0, 49.0]},
            source_name="USGS", source_url="https://www.usgs.gov/",
            source_reference="example-only", source_observed_on=date(1996, 1, 1),
            source_rights="public-domain reference (example)",
            project=self.project, is_demo=True,
        )

    def test_anonymous_redirects_without_leaking(self):
        res = Client().get("/gold-intelligence/targets/geojson/")
        self.assertEqual(res.status_code, 302)

    def test_unassigned_not_visible_to_nonstaff(self):
        self.target.project = None
        self.target.save()
        self.client.force_login(self.reader)
        res = self.client.get("/gold-intelligence/targets/geojson/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["features"], [])

    def test_access_needs_active_project_membership(self):
        self.client.force_login(self.reader)
        url = "/gold-intelligence/targets/geojson/"
        self.assertEqual(self.client.get(url).json()["features"], [])
        membership = ProjectMembership.objects.create(project=self.project, user=self.reader, role="viewer")
        payload = self.client.get(url).json()
        self.assertEqual(len(payload["features"]), 1)
        self.assertIsNone(payload["features"][0]["properties"]["screening_score"])
        membership.is_active = False
        membership.save()
        self.assertEqual(self.client.get(url).json()["features"], [])

    def test_staff_view_and_provenance(self):
        self.client.force_login(self.staff)
        res = self.client.get("/gold-intelligence/targets/geojson/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["features"][0]["properties"]["source_name"], "USGS")
        self.assertEqual(self.client.get("/gold-intelligence/targets/").status_code, 200)
