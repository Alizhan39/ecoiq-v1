from django.test import TestCase

RAW_TEMPLATE_TOKENS = [
    '{% load', '{% for', '{% include', '{% intelligence_block', '{% extends', '{% block',
    '{% csrf_token', '{% if', '{{ ',
]


class ImpactMrvLayerPageTests(TestCase):
    def test_page_returns_200(self):
        response = self.client.get('/impact-mrv-layer/')
        self.assertEqual(response.status_code, 200)

    def test_page_mentions_title(self):
        response = self.client.get('/impact-mrv-layer/')
        self.assertContains(response, 'EcoIQ Impact MRV Layer')

    def test_page_mentions_subtitle(self):
        response = self.client.get('/impact-mrv-layer/')
        self.assertContains(response, 'Before, action, after — verified impact')

    def test_page_shows_evidence_warning(self):
        response = self.client.get('/impact-mrv-layer/')
        self.assertContains(
            response,
            'No project should be counted as verified impact without before/after evidence',
        )

    def test_page_mentions_maqasid_score_improvement(self):
        response = self.client.get('/impact-mrv-layer/')
        self.assertContains(response, 'Maqasid score improvement')

    def test_page_mentions_mizan_score_improvement(self):
        response = self.client.get('/impact-mrv-layer/')
        self.assertContains(response, 'Mizan score improvement')

    def test_page_mentions_evidence_quality(self):
        response = self.client.get('/impact-mrv-layer/')
        self.assertContains(response, 'Evidence Quality')

    def test_page_shows_cta_buttons(self):
        response = self.client.get('/impact-mrv-layer/')
        for label in (
            'Start MRV Tracking', 'Upload Before Evidence', 'Upload After Evidence',
            'Verify Impact', 'Generate MRV Report', 'Export Investor Proof', 'Share with Team',
        ):
            self.assertContains(response, label)

    def test_page_has_no_raw_template_tags(self):
        response = self.client.get('/impact-mrv-layer/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')


class PlatformPageImpactMrvLayerTeaserTests(TestCase):
    def test_platform_page_mentions_impact_mrv_layer(self):
        response = self.client.get('/platform/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'EcoIQ Impact MRV Layer')

    def test_platform_page_has_no_raw_template_tags(self):
        response = self.client.get('/platform/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')
