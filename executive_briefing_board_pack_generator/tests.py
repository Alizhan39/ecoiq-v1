from django.test import TestCase

RAW_TEMPLATE_TOKENS = [
    '{% load', '{% for', '{% include', '{% intelligence_block', '{% extends', '{% block',
    '{% csrf_token', '{% if', '{{ ',
]


class ExecutiveBriefingBoardPackGeneratorPageTests(TestCase):
    def test_page_returns_200(self):
        response = self.client.get('/executive-briefing-board-pack-generator/')
        self.assertEqual(response.status_code, 200)

    def test_page_mentions_title(self):
        response = self.client.get('/executive-briefing-board-pack-generator/')
        self.assertContains(response, 'EcoIQ Executive Briefing & Board Pack Generator')

    def test_page_mentions_subtitle(self):
        response = self.client.get('/executive-briefing-board-pack-generator/')
        self.assertContains(response, 'Generate investor, board, government and impact packs')

    def test_page_mentions_investor_memo(self):
        response = self.client.get('/executive-briefing-board-pack-generator/')
        self.assertContains(response, 'Investor Memo')

    def test_page_mentions_board_pack(self):
        response = self.client.get('/executive-briefing-board-pack-generator/')
        self.assertContains(response, 'Board Pack')

    def test_page_mentions_akimat_government_brief(self):
        response = self.client.get('/executive-briefing-board-pack-generator/')
        self.assertContains(response, 'Akimat / Government Brief')

    def test_page_mentions_islamic_finance_brief(self):
        response = self.client.get('/executive-briefing-board-pack-generator/')
        self.assertContains(response, 'Islamic Finance Brief')

    def test_page_mentions_verified_impact_report(self):
        response = self.client.get('/executive-briefing-board-pack-generator/')
        self.assertContains(response, 'Verified Impact Report')

    def test_page_mentions_no_harm_gate_for_briefings(self):
        response = self.client.get('/executive-briefing-board-pack-generator/')
        self.assertContains(response, 'No Harm Gate for Briefings')

    def test_page_mentions_generate_investor_memo_cta(self):
        response = self.client.get('/executive-briefing-board-pack-generator/')
        self.assertContains(response, 'Generate Investor Memo')

    def test_page_shows_cta_buttons(self):
        response = self.client.get('/executive-briefing-board-pack-generator/')
        for label in (
            'Generate Investor Memo', 'Create Board Pack', 'Generate Akimat Brief',
            'Create CSR Sponsor Pack', 'Prepare Islamic Finance Brief',
            'Export Country Transition Brief', 'Generate Verified Impact Report',
            'Send to Teams for Approval', 'Save to Data Room', 'Export PDF',
        ):
            self.assertContains(response, label)

    def test_page_has_no_raw_template_tags(self):
        response = self.client.get('/executive-briefing-board-pack-generator/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')


class PlatformPageExecutiveBriefingBoardPackGeneratorTeaserTests(TestCase):
    def test_platform_page_mentions_executive_briefing_board_pack_generator(self):
        response = self.client.get('/platform/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'EcoIQ Executive Briefing & Board Pack Generator')

    def test_platform_page_has_no_raw_template_tags(self):
        response = self.client.get('/platform/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')
