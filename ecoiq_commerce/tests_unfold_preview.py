"""Preview-only admin smoke tests; default production test suite safely skips."""
from unittest import skipUnless

from django.conf import settings
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from ecoiq_commerce.models import Feature


@skipUnless(getattr(settings, "ECOIQ_UNFOLD_PREVIEW", False),
            "Unfold preview is disabled under production Django settings")
@override_settings(ALLOWED_HOSTS=["testserver"])
class UnfoldPilotTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superuser = get_user_model().objects.create_superuser(
            username="pilot-unfold-admin",
            email="pilot-admin@example.invalid",
            password="staging-test-only-password",
        )

    def test_unfold_is_loaded_before_django_admin(self):
        self.assertLess(settings.INSTALLED_APPS.index("unfold"),
                        settings.INSTALLED_APPS.index("django.contrib.admin"))
        from unfold.admin import ModelAdmin as UnfoldModelAdmin
        self.assertIsInstance(admin.site._registry[Feature], UnfoldModelAdmin)

    def test_anonymous_user_cannot_see_admin_or_features(self):
        for url in (reverse("admin:index"),
                    reverse("admin:ecoiq_commerce_feature_changelist")):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertIn("/admin/login/", response["Location"])

    def test_authorized_admin_can_render_index_list_and_add_form(self):
        self.client.force_login(self.superuser)
        for url in (reverse("admin:index"),
                    reverse("admin:ecoiq_commerce_feature_changelist"),
                    reverse("admin:ecoiq_commerce_feature_add")):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200, response.content[:500])

    def test_plain_non_staff_user_still_cannot_open_admin(self):
        user = get_user_model().objects.create_user("unfold-ordinary-user")
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("admin:index")).status_code, 302)
