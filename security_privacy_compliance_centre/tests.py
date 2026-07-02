from django.test import TestCase

RAW_TEMPLATE_TOKENS = [
    '{% load', '{% for', '{% include', '{% intelligence_block', '{% extends', '{% block',
    '{% csrf_token', '{% if', '{{ ',
]


class SecurityPrivacyComplianceCentrePageTests(TestCase):
    def test_page_returns_200(self):
        response = self.client.get('/security-privacy-compliance-centre/')
        self.assertEqual(response.status_code, 200)

    def test_page_mentions_title(self):
        response = self.client.get('/security-privacy-compliance-centre/')
        self.assertContains(response, 'EcoIQ Security, Privacy & Compliance Centre')

    def test_page_mentions_subtitle(self):
        response = self.client.get('/security-privacy-compliance-centre/')
        self.assertContains(
            response,
            'Protect industrial evidence, personal data, approvals and AI workflows',
        )

    def test_page_mentions_role_based_access_control(self):
        response = self.client.get('/security-privacy-compliance-centre/')
        self.assertContains(response, 'Role-Based Access Control')

    def test_page_mentions_privacy_pii_protection(self):
        response = self.client.get('/security-privacy-compliance-centre/')
        self.assertContains(response, 'Privacy / PII Protection')

    def test_page_mentions_consent_management(self):
        response = self.client.get('/security-privacy-compliance-centre/')
        self.assertContains(response, 'Consent Management')

    def test_page_mentions_audit_logs(self):
        response = self.client.get('/security-privacy-compliance-centre/')
        self.assertContains(response, 'Audit Logs')

    def test_page_mentions_no_harm_gate_for_security_and_privacy(self):
        response = self.client.get('/security-privacy-compliance-centre/')
        self.assertContains(response, 'No Harm Gate for Security & Privacy')

    def test_page_mentions_open_compliance_centre(self):
        response = self.client.get('/security-privacy-compliance-centre/')
        self.assertContains(response, 'Open Compliance Centre')

    def test_page_shows_cta_buttons(self):
        response = self.client.get('/security-privacy-compliance-centre/')
        for label in (
            'Open Compliance Centre', 'Review Access Permissions', 'Scan for PII',
            'Create Consent Record', 'View Audit Logs', 'Review Public Summary',
            'Revoke Access', 'Export Compliance Report', 'Send Review to Teams',
            'Check Data Room Permissions',
        ):
            self.assertContains(response, label)

    def test_page_has_no_raw_template_tags(self):
        response = self.client.get('/security-privacy-compliance-centre/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')


class PlatformPageSecurityPrivacyComplianceCentreTeaserTests(TestCase):
    def test_platform_page_mentions_security_privacy_compliance_centre(self):
        response = self.client.get('/platform/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'EcoIQ Security, Privacy & Compliance Centre')

    def test_platform_page_has_no_raw_template_tags(self):
        response = self.client.get('/platform/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')
