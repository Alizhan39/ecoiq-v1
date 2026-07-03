from django.test import TestCase

RAW_TEMPLATE_TOKENS = [
    '{% load', '{% for', '{% include', '{% intelligence_block', '{% extends', '{% block',
    '{% csrf_token', '{% if', '{{ ',
]


class DocumentReaderAgentTrainingPackPageTests(TestCase):
    def test_page_returns_200(self):
        response = self.client.get('/document-reader-agent-training-pack/')
        self.assertEqual(response.status_code, 200)

    def test_page_mentions_title(self):
        response = self.client.get('/document-reader-agent-training-pack/')
        self.assertContains(response, 'EcoIQ Document Reader Agent Training Pack')

    def test_page_mentions_subtitle(self):
        response = self.client.get('/document-reader-agent-training-pack/')
        self.assertContains(
            response,
            'Train the agent that reads bills, PDFs, reports, supplier quotes and MRV evidence',
        )

    def test_page_mentions_energy_bill(self):
        response = self.client.get('/document-reader-agent-training-pack/')
        self.assertContains(response, 'Energy bill')

    def test_page_mentions_supplier_quote(self):
        response = self.client.get('/document-reader-agent-training-pack/')
        self.assertContains(response, 'Supplier quote')

    def test_page_mentions_mrv_evidence_document(self):
        response = self.client.get('/document-reader-agent-training-pack/')
        self.assertContains(response, 'MRV evidence document')

    def test_page_mentions_required_output_schema(self):
        response = self.client.get('/document-reader-agent-training-pack/')
        self.assertContains(response, 'Required Output Schema')

    def test_page_mentions_golden_test_cases(self):
        response = self.client.get('/document-reader-agent-training-pack/')
        self.assertContains(response, 'Golden Test Cases')

    def test_page_mentions_no_harm_gate_for_document_reading(self):
        response = self.client.get('/document-reader-agent-training-pack/')
        self.assertContains(response, 'No Harm Gate for Document Reading')

    def test_page_mentions_open_document_reader_training_pack(self):
        response = self.client.get('/document-reader-agent-training-pack/')
        self.assertContains(response, 'Open Document Reader Training Pack')

    def test_page_shows_cta_buttons(self):
        response = self.client.get('/document-reader-agent-training-pack/')
        for label in (
            'Open Document Reader Training Pack', 'Create Golden Test Case',
            'Run Extraction Evaluation', 'Review Failed Extraction',
            'Open Required Output Schema', 'Check PII Risk',
            'Link Document to Asset Passport', 'Send to Human Review',
            'Train on Energy Bill', 'Train on Supplier Quote', 'Train on MRV Evidence',
        ):
            self.assertContains(response, label)

    def test_page_has_no_claim_extraction_is_verification(self):
        response = self.client.get('/document-reader-agent-training-pack/')
        self.assertContains(response, 'Document Reader Agent extracts facts; it does not verify truth by itself.')

    def test_page_has_no_claim_supplier_quote_is_endorsement(self):
        response = self.client.get('/document-reader-agent-training-pack/')
        self.assertContains(response, 'Supplier quotes are not supplier endorsements.')

    def test_page_has_no_unsupported_microsoft_certification_claim(self):
        response = self.client.get('/document-reader-agent-training-pack/')
        content = response.content.decode()
        self.assertNotIn('Microsoft certified', content)
        self.assertNotIn('official partner', content)

    def test_page_has_no_unsupported_fatwa_or_shariah_claim(self):
        response = self.client.get('/document-reader-agent-training-pack/')
        content = response.content.decode()
        self.assertNotIn('is a fatwa', content)
        self.assertNotIn('Shariah certified', content)
        self.assertNotIn('Shariah certification', content)

    def test_page_has_no_raw_template_tags(self):
        response = self.client.get('/document-reader-agent-training-pack/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')


class PlatformPageDocumentReaderAgentTrainingPackTeaserTests(TestCase):
    def test_platform_page_mentions_document_reader_agent_training_pack(self):
        response = self.client.get('/platform/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'EcoIQ Document Reader Agent Training Pack')

    def test_platform_page_has_no_raw_template_tags(self):
        response = self.client.get('/platform/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')
