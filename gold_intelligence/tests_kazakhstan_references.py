"""Sourced names are distinct from geographic occurrences and resource claims."""
from django.test import SimpleTestCase, TestCase
from django.contrib.auth import get_user_model

from gold_intelligence.services.kazakhstan_reference_deposits import named_gold_reference_catalog


class KazakhstanReferencesTests(SimpleTestCase):
    def test_no_made_up_site_coordinates_or_new_discoveries(self):
        result = named_gold_reference_catalog()
        self.assertEqual(result["record_count"], 8)
        self.assertFalse(result["ready_for_map_geocoding"])
        names = [r["name"] for r in result["records"]]
        self.assertIn("Shokpar", names)
        self.assertIn("Akbakay", names)
        for row in result["records"]:
            self.assertIsNone(row["verified_wgs84_geometry"])
            self.assertIsNone(row["target_au_score"])
            self.assertIsNone(row["available_for_application"])
            self.assertFalse(row["is_new_discovery"])
            self.assertTrue(row["source_url"].startswith("https://"))


class KazakhstanReferenceAPITests(TestCase):
    def test_signed_in_only(self):
        endpoint = "/gold-intelligence/targets/pilot/named-deposits.json"
        self.assertEqual(self.client.get(endpoint).status_code, 302)
        user = get_user_model().objects.create_user(username="deposit_reader", password="a_test_password_123")
        self.client.force_login(user)
        result = self.client.get(endpoint)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["record_count"], 8)
        self.assertIsNone(result.json()["records"][0]["verified_wgs84_geometry"])
