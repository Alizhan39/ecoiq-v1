"""SaaS directory filtering must preserve visibility and evidence semantics."""
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings

from api.v2_filters import CompanyDirectoryFilter
from companies.models import CompanyProfile
from league.models import Company


@override_settings(ALLOWED_HOSTS=["testserver"])
class DirectoryFilterIntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        entries = (
            ("Public Energy UK", "public-energy-uk", "Energy", "United Kingdom", "public"),
            ("Public Energy KZ", "public-energy-kz", "energy", "Kazakhstan", "public"),
            ("Public Logistics UK", "public-logistics-uk", "Logistics", "United Kingdom", "public"),
            ("Archived Energy UK", "archived-energy-uk", "Energy", "United Kingdom", "archived"),
        )
        for name, slug, sector, country, status in entries:
            company = Company.objects.create(
                name=name, slug=slug, sector=sector, country=country,
            )
            CompanyProfile.objects.create(company=company, status=status)
        cls.staff = get_user_model().objects.create_user(
            username="directory-filter-staff", is_staff=True,
        )

    def setUp(self):
        cache.clear()

    def slugs(self, query=None):
        response = self.client.get("/api/v2/companies/", query or {})
        self.assertEqual(response.status_code, 200, response.content)
        rows = response.json()["results"]
        # An unevidenced directory entry is NOT an automatically scored one.
        self.assertTrue(all(row["ecoiq_score"] is None for row in rows))
        return [row["slug"] for row in rows]

    def test_case_insensitive_sector_and_country_are_combined(self):
        self.assertEqual(self.slugs({"sector": "ENERGY", "country": "united kingdom"}),
                         ["public-energy-uk"])
        self.assertEqual(self.slugs({"sector": "energy"}),
                         ["public-energy-kz", "public-energy-uk"])
        self.assertEqual(self.slugs({"country": "kazakhstan"}),
                         ["public-energy-kz"])

    def test_keyword_search_remains_tokenised_before_filtering(self):
        self.assertEqual(self.slugs({"q": "public energy", "country": "United Kingdom"}),
                         ["public-energy-uk"])
        self.assertEqual(self.slugs({"q": "PUBLIC   energy", "sector": "energy"}),
                         ["public-energy-kz", "public-energy-uk"])

    def test_archived_remains_private_and_staff_can_review(self):
        self.assertNotIn("archived-energy-uk", self.slugs({"sector": "energy"}))
        self.client.force_login(self.staff)
        self.assertIn("archived-energy-uk", self.slugs({"sector": "energy"}))

    def test_filters_are_whitelisted_without_score_filtering(self):
        self.assertEqual(set(CompanyDirectoryFilter.base_filters), {"sector", "country"})
        before = self.slugs()
        after = self.slugs({"min_score": "90", "max_score": "100"})
        self.assertEqual(before, after)
        self.assertEqual(len(after), 3)
