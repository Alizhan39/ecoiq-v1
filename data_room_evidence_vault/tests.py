from django.test import TestCase

RAW_TEMPLATE_TOKENS = [
    '{% load', '{% for', '{% include', '{% intelligence_block', '{% extends', '{% block',
    '{% csrf_token', '{% if', '{{ ',
]


class DataRoomEvidenceVaultPageTests(TestCase):
    def test_page_returns_200(self):
        response = self.client.get('/data-room-evidence-vault/')
        self.assertEqual(response.status_code, 200)

    def test_page_mentions_title(self):
        response = self.client.get('/data-room-evidence-vault/')
        self.assertContains(response, 'EcoIQ Data Room & Evidence Vault')

    def test_page_mentions_subtitle(self):
        response = self.client.get('/data-room-evidence-vault/')
        self.assertContains(response, 'Investor-grade storage for evidence')

    def test_page_mentions_evidence_pack_builder(self):
        response = self.client.get('/data-room-evidence-vault/')
        self.assertContains(response, 'Evidence Pack Builder')

    def test_page_mentions_evidence_completeness_score(self):
        response = self.client.get('/data-room-evidence-vault/')
        self.assertContains(response, 'Evidence Completeness Score')

    def test_page_mentions_investor_due_diligence_pack(self):
        response = self.client.get('/data-room-evidence-vault/')
        self.assertContains(response, 'Investor Due Diligence Pack')

    def test_page_mentions_no_harm_gate_for_evidence(self):
        response = self.client.get('/data-room-evidence-vault/')
        self.assertContains(response, 'No Harm Gate for Evidence')

    def test_page_mentions_open_data_room(self):
        response = self.client.get('/data-room-evidence-vault/')
        self.assertContains(response, 'Open Data Room')

    def test_page_shows_cta_buttons(self):
        response = self.client.get('/data-room-evidence-vault/')
        for label in (
            'Open Data Room', 'Upload Evidence', 'Create Evidence Pack',
            'Generate Investor Pack', 'Generate MRV Pack', 'Request Expert Review',
            'Share with Investor', 'Send to Teams', 'Export to SharePoint',
            'Check Evidence Completeness',
        ):
            self.assertContains(response, label)

    def test_page_has_no_raw_template_tags(self):
        response = self.client.get('/data-room-evidence-vault/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')


class PlatformPageDataRoomEvidenceVaultTeaserTests(TestCase):
    def test_platform_page_mentions_data_room_evidence_vault(self):
        response = self.client.get('/platform/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'EcoIQ Data Room & Evidence Vault')

    def test_platform_page_has_no_raw_template_tags(self):
        response = self.client.get('/platform/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')
