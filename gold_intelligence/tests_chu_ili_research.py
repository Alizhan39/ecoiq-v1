"""No fake gold discoveries from a sourced regional research queue."""
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase

from gold_intelligence.services.chu_ili_research import pilot_reference_geojson, pilot_research_queue


class ChuIliResearchTests(SimpleTestCase):
    def test_priorities_are_explicitly_not_geological_scores(self):
        rows = pilot_research_queue()["ranked_research_workstreams"]
        self.assertEqual([r["workflow_rank"] for r in rows], [1, 2, 3])
        for row in rows:
            self.assertIsNone(row["mineral_prospectivity_score"])
            self.assertFalse(row["proven_drill_target"])
            self.assertEqual(row["licence_status"], "unknown")
            self.assertTrue(row["sources"])

    def test_orientation_and_envelope_not_mineral_occurrences(self):
        data = pilot_reference_geojson()
        self.assertEqual(data["type"], "FeatureCollection")
        self.assertEqual(len(data["features"]), 3)
        self.assertEqual(data["metadata"]["verified_gold_occurrences_included"], 0)
        for feature in data["features"]:
            self.assertIn(feature["properties"]["feature_kind"], ["orientation_point", "research_envelope"])
            self.assertFalse(feature["properties"]["gold_occurrence_confirmed"])


class PilotApiTests(TestCase):
    def test_pilot_api_private_and_explicitly_not_gold_score(self):
        path = "/gold-intelligence/targets/pilot/research-queue.json"
        self.assertEqual(self.client.get(path).status_code, 302)
        user = get_user_model().objects.create_user(username="pilotreader", password="testing_password_123")
        self.client.force_login(user)
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["ranked_research_workstreams"][0]["mineral_prospectivity_score"], None)
        self.assertFalse(response.json()["drilling_authorized"])
