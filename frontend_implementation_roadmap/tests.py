from django.test import TestCase

RAW_TEMPLATE_TOKENS = [
    '{% load', '{% for', '{% include', '{% intelligence_block', '{% extends', '{% block',
    '{% csrf_token', '{% if', '{{ ',
]


class FrontendImplementationRoadmapPageTests(TestCase):
    def test_page_returns_200(self):
        response = self.client.get('/frontend-implementation-roadmap/')
        self.assertEqual(response.status_code, 200)

    def test_page_mentions_title(self):
        response = self.client.get('/frontend-implementation-roadmap/')
        self.assertContains(response, 'EcoIQ Frontend Implementation Roadmap')

    def test_page_mentions_subtitle(self):
        response = self.client.get('/frontend-implementation-roadmap/')
        self.assertContains(response, 'Plan Django, Next.js, Microsoft and Google Stitch frontend delivery')

    def test_page_mentions_phase_1(self):
        response = self.client.get('/frontend-implementation-roadmap/')
        self.assertContains(response, 'Phase 1 — Strengthen Django Frontend')

    def test_page_mentions_phase_3(self):
        response = self.client.get('/frontend-implementation-roadmap/')
        self.assertContains(response, 'Phase 3 — Next.js SaaS Frontend')

    def test_page_mentions_microsoft_enterprise_frontend(self):
        response = self.client.get('/frontend-implementation-roadmap/')
        self.assertContains(response, 'Microsoft Enterprise Frontend')

    def test_page_mentions_google_stitch_to_production_workflow(self):
        response = self.client.get('/frontend-implementation-roadmap/')
        self.assertContains(response, 'Google Stitch to Production Workflow')

    def test_page_mentions_frontend_library_decision_matrix(self):
        response = self.client.get('/frontend-implementation-roadmap/')
        self.assertContains(response, 'Frontend Library Decision Matrix')

    def test_page_mentions_microsoft_ready_industrial_intelligence_demo(self):
        response = self.client.get('/frontend-implementation-roadmap/')
        self.assertContains(response, 'Microsoft-ready Industrial Intelligence Demo')

    def test_page_mentions_open_frontend_roadmap(self):
        response = self.client.get('/frontend-implementation-roadmap/')
        self.assertContains(response, 'Open Frontend Roadmap')

    def test_page_shows_cta_buttons(self):
        response = self.client.get('/frontend-implementation-roadmap/')
        for label in (
            'Open Frontend Roadmap', 'View Phase 1 Django Plan', 'View Next.js SaaS Plan',
            'View Microsoft UI Plan', 'View Google Stitch Workflow', 'View Library Matrix',
            'Open Command Centre UI Plan', 'Open Mobile PWA Plan', 'Export Frontend Roadmap',
        ):
            self.assertContains(response, label)

    def test_page_has_no_unsupported_microsoft_certification_claim(self):
        response = self.client.get('/frontend-implementation-roadmap/')
        content = response.content.decode()
        idx = content.find('Microsoft certified')
        while idx != -1:
            context = content[max(0, idx - 60):idx + 40]
            self.assertIn('not', context, 'unsupported "Microsoft certified" claim found without a negation nearby')
            idx = content.find('Microsoft certified', idx + 1)

    def test_page_describes_google_stitch_as_prototyping(self):
        response = self.client.get('/frontend-implementation-roadmap/')
        self.assertContains(response, 'Google Stitch is for design prototyping, not production guarantee')

    def test_page_has_no_raw_template_tags(self):
        response = self.client.get('/frontend-implementation-roadmap/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')


class PlatformPageFrontendImplementationRoadmapTeaserTests(TestCase):
    def test_platform_page_mentions_frontend_implementation_roadmap(self):
        response = self.client.get('/platform/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'EcoIQ Frontend Implementation Roadmap')

    def test_platform_page_has_no_raw_template_tags(self):
        response = self.client.get('/platform/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')
