"""Business OS formula pages are private, project-scoped, and read-only."""
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from gold_intelligence.models import GoldProject, ProjectMembership


@override_settings(ALLOWED_HOSTS=["testserver"], GTM_CONTAINER_ID="GTM-TEST")
class FormulaStudioBrowserTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.project = GoldProject.objects.create(
            name="Confidential Formula Lab", slug="confidential-formula",
            commodity="infrastructure", is_demo=False,
        )
        cls.other = GoldProject.objects.create(
            name="Other Tenant Formulas", slug="other-tenant-formulas",
            commodity="infrastructure", is_demo=False,
        )
        cls.viewer = get_user_model().objects.create_user(username="formula-studio-viewer")
        cls.stranger = get_user_model().objects.create_user(username="formula-studio-stranger")
        ProjectMembership.objects.create(
            project=cls.project, user=cls.viewer,
            role=ProjectMembership.Role.VIEWER,
        )

    def test_anonymous_redirect_and_cross_tenant_404(self):
        url = reverse("formula_studio", args=[self.project.slug])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.client.force_login(self.stranger)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_login(self.viewer)
        self.assertEqual(
            self.client.get(reverse("formula_studio", args=[self.other.slug])).status_code,
            404,
        )

    def test_page_has_twenty_six_unapproved_formulas_no_analytics(self):
        self.client.force_login(self.viewer)
        url = reverse("formula_studio", args=[self.project.slug])
        result = self.client.get(url)
        self.assertEqual(result.status_code, 200)
        self.assertContains(result, "Confidential Formula Lab")
        self.assertContains(result, "Initial Business Plan 2.0 KPI formulas (20)")
        self.assertContains(result, "Additional situation templates (6)")
        self.assertContains(result, "gross_margin")
        self.assertContains(result, "mining_recovery")
        self.assertContains(result, "AI Formula Designer")
        self.assertContains(result, "disabled by default")
        self.assertNotContains(result, "Other Tenant Formulas")
        self.assertNotContains(result, "googletagmanager.com")
        self.assertEqual(result["X-Robots-Tag"], "noindex, nofollow")
        self.assertIn("no-store", result["Cache-Control"])

    def test_no_mutations_from_browser_and_workspace_link(self):
        self.client.force_login(self.viewer)
        url = reverse("formula_studio", args=[self.project.slug])
        self.assertEqual(self.client.post(url, {"formula": "1+1"}).status_code, 405)
        self.assertEqual(self.client.delete(url).status_code, 405)
        page = self.client.get(reverse("process_workspace"))
        self.assertContains(page, 'id="po-formula-studio-link"')
        self.assertContains(page, url)
