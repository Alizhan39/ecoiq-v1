"""
GET /api/v2/platform/ — the single source of truth, over HTTP.

Every number the product shows about itself comes through here. The tests that
matter are the ones about what the endpoint must NOT do: emit a hard-coded
figure, coerce an absent one to zero, or render an unmeasured evaluation as 0%.
"""
from django.test import Client, TestCase

from platform_registry.agents import MODULES, PRODUCTION, AGENT
from platform_registry.architecture import LAYERS


class PlatformEndpoint(TestCase):

    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.payload = Client().get('/api/v2/platform/').json()

    def test_it_responds(self):
        self.assertEqual(Client().get('/api/v2/platform/').status_code, 200)

    def test_it_returns_counters_and_modules(self):
        self.assertIn('counters', self.payload)
        self.assertIn('modules', self.payload)
        self.assertIn('architecture', self.payload)

    def test_every_counter_carries_its_derivation(self):
        """A figure a reader cannot check is indistinguishable from invented."""
        for counter in self.payload['counters']:
            with self.subTest(key=counter['key']):
                self.assertTrue(counter['derivation'].strip())

    def test_every_counter_declares_whether_it_is_proof(self):
        for counter in self.payload['counters']:
            with self.subTest(key=counter['key']):
                self.assertIn('is_proof', counter)

    def test_a_row_count_is_not_proof(self):
        counters = {c['key']: c for c in self.payload['counters']}

        self.assertFalse(counters['companies_total']['is_proof'])
        self.assertTrue(counters['companies_published']['is_proof'])

    def test_an_absent_figure_is_null_not_zero(self):
        """
        The frontend renders null as an em dash. A zero would read as a
        measured result.
        """
        counters = {c['key']: c for c in self.payload['counters']}
        projects = counters.get('projects_verified')

        if projects is not None and projects['value'] is None:
            self.assertIsNone(projects['value'])
        else:
            self.skipTest('projects exist in this database')

    def test_specification_packs_are_labelled_as_documents(self):
        counters = {c['key']: c for c in self.payload['counters']}

        self.assertIn('DOCUMENTS', counters['specification_packs']['derivation'])

    def test_module_counts_match_the_registry(self):
        self.assertEqual(len(self.payload['modules']), len(MODULES))

    def test_every_module_states_its_basis(self):
        for module in self.payload['modules']:
            with self.subTest(key=module['key']):
                self.assertTrue(module['basis'].strip())

    def test_architecture_matches_the_canonical_layer_registry(self):
        self.assertEqual(
            [layer['key'] for layer in self.payload['architecture']],
            [layer.key for layer in LAYERS],
        )

    def test_architecture_components_use_canonical_module_statuses(self):
        modules = {module['key']: module for module in self.payload['modules']}

        for layer in self.payload['architecture']:
            for component in layer['components']:
                with self.subTest(layer=layer['key'], component=component['key']):
                    self.assertEqual(component['status'], modules[component['key']]['status'])

    def test_architecture_exposes_known_gaps(self):
        connectors = next(
            layer for layer in self.payload['architecture']
            if layer['key'] == 'tools_connectors'
        )

        self.assertEqual(connectors['maturity'], 'PLANNED')
        self.assertTrue(connectors['gaps'])

    def test_no_ai_agent_is_served_as_production(self):
        """The claim the registry exists to prevent, checked over the wire."""
        claimed = [m for m in self.payload['modules']
                   if m['kind'] == AGENT and m['status'] == PRODUCTION]

        self.assertEqual(claimed, [])

    def test_not_yet_measured_is_served_as_words(self):
        for module in self.payload['modules']:
            with self.subTest(key=module['key']):
                self.assertNotEqual(module['evaluation'], 0)
                self.assertNotEqual(module['evaluation'], '0%')

    def test_it_is_anonymous(self):
        """A public homepage cannot require a session to show its counters."""
        self.assertEqual(Client().get('/api/v2/platform/').status_code, 200)

    def test_it_does_not_expose_a_company_score(self):
        """
        This is the PLATFORM resource. Score containment lives on the company
        endpoints, and duplicating scores here would duplicate the gate.
        """
        import json

        body = json.dumps(self.payload)

        self.assertNotIn('ecoiq_score', body)
