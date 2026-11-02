"""Isolated migration and route-boundary checks for legacy Wagtail 7.4.

Run only under ecoiq.settings_wagtail_audit. No state-changing APIs or
production database migrations are enabled by these tests.
"""
from unittest import skipUnless

from django.apps import apps
from django.conf import settings
from django.db import connection
from django.db.migrations.loader import MigrationLoader
from django.test import SimpleTestCase, TestCase
from django.urls import resolve

AUDIT = getattr(settings, "ECOIQ_WAGTAIL_AUDIT_MODE", False)
LATEST_CMS_MIGRATION = "0002_reportlibrarypage_alter_aboutpage_body_and_more"


@skipUnless(AUDIT, "Legacy Wagtail audit disabled in standard EcoIQ settings")
class WagtailSchemaContractTests(SimpleTestCase):
    def test_legacy_cms_is_registered_without_changing_production(self):
        self.assertTrue(apps.is_installed("cms"))
        self.assertTrue(apps.is_installed("wagtail"))
        self.assertLess(settings.INSTALLED_APPS.index("wagtail"),
                        settings.INSTALLED_APPS.index("cms"))

    def test_legacy_dependencies_exist_in_wagtail_migration_graph(self):
        loader = MigrationLoader(None)
        for key in (
            ("cms", "0001_initial"),
            ("cms", LATEST_CMS_MIGRATION),
            ("wagtailcore", "0097_baselogentry_uuid_action_timestamp_indexes"),
            ("wagtailimages", "0027_image_description"),
        ):
            with self.subTest(migration=key):
                self.assertIn(key, loader.disk_migrations)
        sequence = loader.graph.forwards_plan(("cms", LATEST_CMS_MIGRATION))
        self.assertIn(("cms", "0001_initial"), sequence)
        self.assertEqual(sequence[-1], ("cms", LATEST_CMS_MIGRATION))

    def test_wagtail_routes_remain_unpublished(self):
        # Wagtail's URLconf is NOT included; the SPA 404 catch-all owns
        # unknown URLs. No editorial endpoint is exposed to the public.
        for path in ("/cms/", "/cms/pages/", "/pages/"):
            match = resolve(path)
            self.assertEqual(match.url_name, "spa_catch_all", path)


@skipUnless(AUDIT, "Legacy Wagtail audit disabled in standard EcoIQ settings")
class WagtailDisposableSchemaTests(TestCase):
    def test_legacy_cms_tables_exist_after_disposable_test_migrations(self):
        tables = set(connection.introspection.table_names())
        self.assertIn("wagtailcore_page", tables)
        self.assertIn("cms_homepage", tables)
        self.assertIn("cms_reportlibrarypage", tables)

    def test_disposable_database_is_not_evidence_or_publication(self):
        from wagtail.models import Page
        # The test database may seed the root page; never infer that an
        # editorial CompanyPage or an evidence-linked KPI is published.
        self.assertGreaterEqual(Page.objects.count(), 1)
        from cms.models import CompanyPage
        self.assertEqual(CompanyPage.objects.count(), 0)
