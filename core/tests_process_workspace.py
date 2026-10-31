"""Business OS stage 4: role-filtered browser shell, no score publication."""
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from gold_intelligence.models import GoldProject, ProjectMembership


@override_settings(ALLOWED_HOSTS=["testserver"])
class ProcessWorkspaceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.first = GoldProject.objects.create(
            name="Site Alpha Confidential", slug="site-alpha-private",
            commodity="infrastructure", is_demo=False,
        )
        cls.second = GoldProject.objects.create(
            name="Site Bravo Classified", slug="site-bravo-private",
            commodity="infrastructure", is_demo=False,
        )
        cls.viewer = get_user_model().objects.create_user(username="workspace-viewer")
        cls.analyst = get_user_model().objects.create_user(username="workspace-analyst")
        cls.manager = get_user_model().objects.create_user(username="workspace-manager")
        cls.stranger = get_user_model().objects.create_user(username="workspace-stranger")
        cls.staff = get_user_model().objects.create_user(username="workspace-staff", is_staff=True)
        ProjectMembership.objects.create(
            project=cls.first, user=cls.viewer, role=ProjectMembership.Role.VIEWER,
        )
        ProjectMembership.objects.create(
            project=cls.first, user=cls.analyst, role=ProjectMembership.Role.ANALYST,
        )
        ProjectMembership.objects.create(
            project=cls.first, user=cls.manager, role=ProjectMembership.Role.MANAGER,
        )

    def setUp(self):
        cache.clear()
        self.url = reverse("process_workspace")

    def test_anonymous_get_redirects_to_existing_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/login/?next="))

    @override_settings(GTM_CONTAINER_ID="GTM-TEST-PRIVATE")
    def test_private_workspace_does_not_load_marketing_analytics(self):
        self.client.force_login(self.viewer)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "ecoiq-analytics-loader")
        self.assertNotContains(response, "googletagmanager.com")
        self.assertNotContains(response, "GTM-TEST-PRIVATE")

    def test_viewer_sees_only_their_project_with_read_only_marker(self):
        self.client.force_login(self.viewer)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Site Alpha Confidential")
        self.assertNotContains(response, "Site Bravo Classified")
        self.assertContains(response, 'value="site-alpha-private" data-upload="0"')
        self.assertContains(response, 'meta name="robots" content="noindex, nofollow"')
        cache_directives = {part.strip() for part in response["Cache-Control"].split(",")}
        self.assertTrue({"private", "no-store", "max-age=0"} <= cache_directives)
        self.assertNotIn("public", cache_directives)
        self.assertEqual(response["X-Robots-Tag"], "noindex, nofollow")
        self.assertContains(response, "process-workspace.js")
        self.assertContains(response, "process-workspace.css")
        self.assertContains(response, "csrfmiddlewaretoken")

    def test_decision_studies_are_hidden_until_requested(self):
        self.client.force_login(self.viewer)
        response = self.client.get(self.url)
        self.assertContains(response, 'id="po-decision-panel"')
        self.assertContains(response, "Hypotheses and Islah studies")
        self.assertContains(response, "deterministic list of questions")
        self.assertContains(response, "not a generative AI finding")
        self.assertNotContains(response, "120 kg")

    def test_analyst_and_manager_can_upload_but_not_approve(self):
        for actor in (self.analyst, self.manager):
            with self.subTest(actor=actor.username):
                self.client.force_login(actor)
                response = self.client.get(self.url)
                self.assertContains(response, 'value="site-alpha-private" data-upload="1"')
                self.assertNotContains(response, "Site Bravo Classified")
                self.assertNotContains(response, 'name="verified"')
                self.assertNotContains(response, 'name="hypothesis_status"')

    def test_staff_keeps_existing_cross_project_authority(self):
        self.client.force_login(self.staff)
        response = self.client.get(self.url)
        self.assertContains(response, "Site Alpha Confidential")
        self.assertContains(response, "Site Bravo Classified")
        self.assertContains(response, 'value="site-bravo-private" data-upload="1"')

    def test_ungranted_user_gets_explicit_empty_state_not_demo_metrics(self):
        self.client.force_login(self.stranger)
        response = self.client.get(self.url)
        self.assertContains(response, "No accessible projects yet")
        self.assertNotContains(response, "Site Alpha Confidential")
        self.assertNotContains(response, "Site Bravo Classified")
        self.assertNotContains(response, "12.0%")
        self.assertNotContains(response, "1000 kg")

    def test_revoked_role_disappears_on_next_request(self):
        self.client.force_login(self.analyst)
        self.assertContains(self.client.get(self.url), "Site Alpha Confidential")
        ProjectMembership.objects.filter(project=self.first, user=self.analyst).update(is_active=False)
        self.assertContains(self.client.get(self.url), "No accessible projects yet")

    def test_inactive_user_cannot_access_private_page(self):
        self.analyst.is_active = False
        self.analyst.save(update_fields=["is_active"])
        self.client.force_login(self.analyst)
        response = self.client.get(self.url)
        self.assertNotEqual(response.status_code, 200)

    def test_browser_shell_has_no_write_endpoint_or_business_data(self):
        self.client.force_login(self.analyst)
        self.assertEqual(self.client.post(self.url, {"file": "test.csv"}).status_code, 405)
        response = self.client.get(self.url)
        self.assertNotContains(response, "SECRET-DOC-1")
        self.assertNotContains(response, "WASTE-REF-1")
        self.assertContains(response, "No report selected")
