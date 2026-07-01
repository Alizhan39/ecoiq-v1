from django.test import TestCase


class AmanahAutopilotOverviewPageTests(TestCase):
    def test_page_returns_200(self):
        response = self.client.get('/amanah-autopilot/')
        self.assertEqual(response.status_code, 200)

    def test_page_mentions_title(self):
        response = self.client.get('/amanah-autopilot/')
        self.assertContains(response, 'EcoIQ Amanah Autopilot')

    def test_page_mentions_subtitle(self):
        response = self.client.get('/amanah-autopilot/')
        self.assertContains(response, 'AI agents that do good while you sleep.')

    def test_page_shows_overnight_timeline(self):
        response = self.client.get('/amanah-autopilot/')
        self.assertContains(response, 'Data scan started')
        self.assertContains(response, 'Morning briefing ready')

    def test_page_shows_all_eight_agents(self):
        response = self.client.get('/amanah-autopilot/')
        for agent in (
            'Harm Detection Agent', 'Waste Reduction Agent', 'Maqasid-Mizan Agent',
            'Modernisation Agent', 'Funding Agent', 'Supplier Agent', 'Report Agent',
            'Monitoring Agent',
        ):
            self.assertContains(response, agent)

    def test_page_shows_dashboard_card_title(self):
        response = self.client.get('/amanah-autopilot/')
        self.assertContains(response, 'Good Deeds Overnight Report')

    def test_page_shows_cta_button(self):
        response = self.client.get('/amanah-autopilot/')
        self.assertContains(response, 'Turn on Amanah Autopilot')

    def test_page_does_not_claim_religious_authority(self):
        response = self.client.get('/amanah-autopilot/')
        self.assertContains(response, 'not a religious ruling')
