from django.test import TestCase

RAW_TEMPLATE_TOKENS = [
    '{% load', '{% for', '{% include', '{% intelligence_block', '{% extends', '{% block',
    '{% csrf_token', '{% if', '{{ ',
]


class KnowledgeGraphRelationshipMapPageTests(TestCase):
    def test_page_returns_200(self):
        response = self.client.get('/knowledge-graph-relationship-map/')
        self.assertEqual(response.status_code, 200)

    def test_page_mentions_title(self):
        response = self.client.get('/knowledge-graph-relationship-map/')
        self.assertContains(response, 'EcoIQ Knowledge Graph & Relationship Map')

    def test_page_mentions_subtitle(self):
        response = self.client.get('/knowledge-graph-relationship-map/')
        self.assertContains(
            response,
            'Connect assets, evidence, risks, finance, suppliers and verified impact',
        )

    def test_page_mentions_evidence_trace_graph(self):
        response = self.client.get('/knowledge-graph-relationship-map/')
        self.assertContains(response, 'Evidence Trace Graph')

    def test_page_mentions_process_improvement_engine(self):
        response = self.client.get('/knowledge-graph-relationship-map/')
        self.assertContains(response, 'Process Improvement Engine')

    def test_page_mentions_graph_completeness_score(self):
        response = self.client.get('/knowledge-graph-relationship-map/')
        self.assertContains(response, 'Graph Completeness Score')

    def test_page_mentions_no_harm_gate_for_knowledge_graph(self):
        response = self.client.get('/knowledge-graph-relationship-map/')
        self.assertContains(response, 'No Harm Gate for Knowledge Graph')

    def test_page_mentions_open_knowledge_graph(self):
        response = self.client.get('/knowledge-graph-relationship-map/')
        self.assertContains(response, 'Open Knowledge Graph')

    def test_page_shows_cta_buttons(self):
        response = self.client.get('/knowledge-graph-relationship-map/')
        for label in (
            'Open Knowledge Graph', 'View Project Relationship Map',
            'Trace Evidence to Claim', 'Find Missing Links',
            'Show Finance-Ready Clusters', 'Show No Harm Risk Paths',
            'Open Maqasid/Mizan Graph', 'Run Graph Health Check',
            'Send Missing Link Alert to Teams', 'Export Relationship Map',
        ):
            self.assertContains(response, label)

    def test_page_has_no_raw_template_tags(self):
        response = self.client.get('/knowledge-graph-relationship-map/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')


class PlatformPageKnowledgeGraphRelationshipMapTeaserTests(TestCase):
    def test_platform_page_mentions_knowledge_graph_relationship_map(self):
        response = self.client.get('/platform/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'EcoIQ Knowledge Graph & Relationship Map')

    def test_platform_page_has_no_raw_template_tags(self):
        response = self.client.get('/platform/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')
