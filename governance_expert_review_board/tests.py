from django.test import TestCase

RAW_TEMPLATE_TOKENS = [
    '{% load', '{% for', '{% include', '{% intelligence_block', '{% extends', '{% block',
    '{% csrf_token', '{% if', '{{ ',
]


class GovernanceExpertReviewBoardPageTests(TestCase):
    def test_page_returns_200(self):
        response = self.client.get('/governance-expert-review-board/')
        self.assertEqual(response.status_code, 200)

    def test_page_mentions_title(self):
        response = self.client.get('/governance-expert-review-board/')
        self.assertContains(response, 'EcoIQ Governance & Expert Review Board')

    def test_page_mentions_subtitle(self):
        response = self.client.get('/governance-expert-review-board/')
        self.assertContains(response, 'AI prepares. Experts review. Humans approve.')

    def test_page_mentions_human_approval_required(self):
        response = self.client.get('/governance-expert-review-board/')
        self.assertContains(response, 'Human Approval Required')

    def test_page_mentions_no_harm_gate_review(self):
        response = self.client.get('/governance-expert-review-board/')
        self.assertContains(response, 'No Harm Gate Review')

    def test_page_mentions_maqasid_mizan_reviewed(self):
        response = self.client.get('/governance-expert-review-board/')
        self.assertContains(response, 'Maqasid/Mizan Reviewed')

    def test_page_mentions_smr_feasibility_study(self):
        response = self.client.get('/governance-expert-review-board/')
        self.assertContains(response, 'SMR Feasibility Study')

    def test_page_shows_cta_buttons(self):
        response = self.client.get('/governance-expert-review-board/')
        for label in (
            'Submit for Expert Review', 'Request Technical Review',
            'Request Maqasid/Mizan Review', 'Approve for Supplier Outreach',
            'Approve for Funding Memo', 'Approve for Implementation',
            'Request More Evidence', 'Export Evidence Pack',
        ):
            self.assertContains(response, label)

    def test_page_has_no_raw_template_tags(self):
        response = self.client.get('/governance-expert-review-board/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')


class PlatformPageGovernanceExpertReviewBoardTeaserTests(TestCase):
    def test_platform_page_mentions_governance_expert_review_board(self):
        response = self.client.get('/platform/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'EcoIQ Governance & Expert Review Board')

    def test_platform_page_has_no_raw_template_tags(self):
        response = self.client.get('/platform/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')
