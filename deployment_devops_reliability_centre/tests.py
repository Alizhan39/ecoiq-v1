from django.test import TestCase

RAW_TEMPLATE_TOKENS = [
    '{% load', '{% for', '{% include', '{% intelligence_block', '{% extends', '{% block',
    '{% csrf_token', '{% if', '{{ ',
]


class DeploymentDevopsReliabilityCentrePageTests(TestCase):
    def test_page_returns_200(self):
        response = self.client.get('/deployment-devops-reliability-centre/')
        self.assertEqual(response.status_code, 200)

    def test_page_mentions_title(self):
        response = self.client.get('/deployment-devops-reliability-centre/')
        self.assertContains(response, 'EcoIQ Deployment, DevOps & Reliability Centre')

    def test_page_mentions_subtitle(self):
        response = self.client.get('/deployment-devops-reliability-centre/')
        self.assertContains(
            response,
            'Operate EcoIQ safely with monitoring, backups, releases and incident response',
        )

    def test_page_mentions_deployment_monitoring(self):
        response = self.client.get('/deployment-devops-reliability-centre/')
        self.assertContains(response, 'Deployment Monitoring')

    def test_page_mentions_backup_and_restore(self):
        response = self.client.get('/deployment-devops-reliability-centre/')
        self.assertContains(response, 'Backup')
        self.assertContains(response, 'Restore')

    def test_page_mentions_incident_response(self):
        response = self.client.get('/deployment-devops-reliability-centre/')
        self.assertContains(response, 'Incident Response')

    def test_page_mentions_route_verification(self):
        response = self.client.get('/deployment-devops-reliability-centre/')
        self.assertContains(response, 'Route Verification')

    def test_page_mentions_no_harm_gate_for_reliability(self):
        response = self.client.get('/deployment-devops-reliability-centre/')
        self.assertContains(response, 'No Harm Gate for Reliability')

    def test_page_mentions_open_reliability_centre(self):
        response = self.client.get('/deployment-devops-reliability-centre/')
        self.assertContains(response, 'Open Reliability Centre')

    def test_page_shows_cta_buttons(self):
        response = self.client.get('/deployment-devops-reliability-centre/')
        for label in (
            'Open Reliability Centre', 'Check Route Health', 'View Deployment Status',
            'Review Release History', 'Check Database Health', 'Verify Backups',
            'Open Incident Log', 'Run Route Verification', 'Prepare Rollback Plan',
            'Send Incident Alert to Teams',
        ):
            self.assertContains(response, label)

    def test_page_has_no_raw_template_tags(self):
        response = self.client.get('/deployment-devops-reliability-centre/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')


class PlatformPageDeploymentDevopsReliabilityCentreTeaserTests(TestCase):
    def test_platform_page_mentions_deployment_devops_reliability_centre(self):
        response = self.client.get('/platform/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'EcoIQ Deployment, DevOps & Reliability Centre')

    def test_platform_page_has_no_raw_template_tags(self):
        response = self.client.get('/platform/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')
