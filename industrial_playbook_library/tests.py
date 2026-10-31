from django.test import TestCase
from core.staff_page_testcase import StaffPageTestCase

RAW_TEMPLATE_TOKENS = [
    '{% load', '{% for', '{% include', '{% intelligence_block', '{% extends', '{% block',
    '{% csrf_token', '{% if', '{{ ',
]


class IndustrialPlaybookLibraryPageTests(StaffPageTestCase):
    def test_page_returns_200(self):
        response = self.client.get('/industrial-playbook-library/')
        self.assertEqual(response.status_code, 200)

    def test_page_mentions_title(self):
        response = self.client.get('/industrial-playbook-library/')
        self.assertContains(response, 'EcoIQ Industrial Playbook Library')

    def test_page_mentions_subtitle(self):
        response = self.client.get('/industrial-playbook-library/')
        self.assertContains(response, 'Reusable modernisation pathways')

    def test_page_mentions_boiler_playbook(self):
        response = self.client.get('/industrial-playbook-library/')
        self.assertContains(response, 'Boiler Modernisation Playbook')

    def test_page_mentions_factory_playbook(self):
        response = self.client.get('/industrial-playbook-library/')
        self.assertContains(response, 'Factory Energy Efficiency Playbook')

    def test_page_mentions_smr_playbook(self):
        response = self.client.get('/industrial-playbook-library/')
        self.assertContains(response, 'SMR Feasibility Playbook')

    def test_page_mentions_maqasid_meaning(self):
        response = self.client.get('/industrial-playbook-library/')
        self.assertContains(response, 'Maqasid meaning')

    def test_page_mentions_mizan_meaning(self):
        response = self.client.get('/industrial-playbook-library/')
        self.assertContains(response, 'Mizan meaning')

    def test_page_shows_cta_buttons(self):
        response = self.client.get('/industrial-playbook-library/')
        for label in (
            'Explore Playbooks', 'Match My Asset to a Playbook', 'Generate Modernisation Plan',
            'Run What-If Simulation', 'Prepare Finance Memo', 'Start MRV Tracking',
        ):
            self.assertContains(response, label)

    def test_page_has_no_raw_template_tags(self):
        response = self.client.get('/industrial-playbook-library/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')

