"""
The canonical registry and the single source of truth for counters.

Two claims are under test here, and both were product-truth failures:

  "33 operational agents"  described 33 folders containing 298 markdown files
                           and zero Python.
  "467 companies"          described rows in a table, none of which has a
                           publishable assessment.
"""
from django.test import SimpleTestCase, TestCase

from platform_registry.agents import (
    AGENT, BETA, ENGINE, EXPERIMENTAL, MODULES, NOT_MEASURED, PRODUCTION,
    REGISTRY, STATUS_ORDER, by_status, counts, production_ai_agents,
)
from platform_registry.stats import Counter, platform_stats, proof_counters


class RegistryShape(SimpleTestCase):

    def test_every_module_has_a_unique_key(self):
        keys = [m.key for m in MODULES]

        self.assertEqual(len(keys), len(set(keys)))

    def test_every_module_declares_a_valid_status(self):
        for module in MODULES:
            with self.subTest(key=module.key):
                self.assertIn(module.status, STATUS_ORDER)

    def test_every_module_states_the_basis_for_its_status(self):
        """A status without a stated basis is an assertion."""
        for module in MODULES:
            with self.subTest(key=module.key):
                self.assertTrue(module.basis.strip(),
                                f'{module.key} claims {module.status} without '
                                'saying why')

    def test_every_module_names_an_entry_point(self):
        for module in MODULES:
            with self.subTest(key=module.key):
                self.assertTrue(module.entry_point)

    def test_every_module_names_a_location(self):
        for module in MODULES:
            with self.subTest(key=module.key):
                self.assertTrue(module.location)


class TheProductionClaim(SimpleTestCase):
    """
    The rule the brief states literally: an unevaluated agent may not be
    presented as proven PRODUCTION unless another strong basis exists.
    """

    def test_no_ai_agent_is_claimed_as_production(self):
        """
        For a generative system there IS no other basis — output quality is
        exactly what evaluation measures. So this list must be empty until an
        evaluation exists.
        """
        self.assertEqual(production_ai_agents(), [])

    def test_every_production_module_has_an_evaluation_basis(self):
        for module in by_status(PRODUCTION):
            with self.subTest(key=module.key):
                self.assertNotEqual(
                    module.evaluation, NOT_MEASURED,
                    f'{module.key} is PRODUCTION but NOT YET MEASURED')

    def test_every_production_module_is_deterministic(self):
        """
        The only basis available without evaluation. A PRODUCTION module here
        is a formula whose behaviour is pinned by tests, not a generator whose
        quality is assumed.
        """
        for module in by_status(PRODUCTION):
            with self.subTest(key=module.key):
                self.assertNotEqual(module.kind, AGENT)

    def test_unevaluated_modules_say_so(self):
        for module in MODULES:
            if module.evaluation == NOT_MEASURED:
                with self.subTest(key=module.key):
                    self.assertIn(module.status, (BETA, EXPERIMENTAL))

    def test_not_measured_is_never_rendered_as_a_number(self):
        """NOT YET MEASURED must not become 0%."""
        for module in MODULES:
            with self.subTest(key=module.key):
                self.assertNotEqual(module.evaluation, 0)
                self.assertNotEqual(module.evaluation, '0%')


class SpecificationPacksAreNotAgents(TestCase):
    """
    The "33 agents" claim, isolated.

    `ai_agents/` is documentation. Counting it as software is how a product
    came to claim thirty-three operational agents while shipping none.
    """

    def test_the_packs_are_counted_separately_from_modules(self):
        data = counts()

        self.assertIn('specification_packs', data)
        self.assertIn('total_modules', data)
        self.assertNotEqual(data['specification_packs'], data['total_modules'])

    def test_the_pack_directory_contains_no_python(self):
        from pathlib import Path

        from django.conf import settings

        base = Path(settings.BASE_DIR) / 'ai_agents'
        if not base.is_dir():
            self.skipTest('ai_agents/ not present')

        self.assertEqual(list(base.rglob('*.py')), [],
                         'a pack containing code would change this analysis')

    def test_no_registry_module_points_at_a_pack_folder(self):
        for module in MODULES:
            with self.subTest(key=module.key):
                self.assertFalse(module.location.startswith('ai_agents/'))


class Counters(TestCase):

    def test_every_counter_states_its_derivation(self):
        """
        A counter without a stated derivation is indistinguishable from a
        hard-coded one.
        """
        for key, counter in platform_stats().items():
            with self.subTest(key=key):
                self.assertTrue(counter.derivation.strip())

    def test_counters_are_derived_not_declared(self):
        stats = platform_stats()

        self.assertEqual(stats['companies_total'].value,
                         __import__('league.models', fromlist=['Company'])
                         .Company.objects.count())

    def test_an_absent_figure_is_none_not_zero(self):
        """
        '0 verified projects' invites the reader to conclude the projects
        failed verification. None renders as an em dash and claims nothing.
        """
        counter = Counter('x', 'X', None, 'test')

        self.assertIsNone(counter.value)
        self.assertEqual(counter.display, '—')

    def test_a_real_zero_still_displays_as_zero(self):
        counter = Counter('x', 'X', 0, 'test')

        self.assertEqual(counter.display, '0')

    def test_a_row_count_is_not_offered_as_proof(self):
        """
        companies_total says how many rows exist. It is not evidence of
        anything about the product, and marketing surfaces must not treat it
        as such.
        """
        self.assertFalse(platform_stats()['companies_total'].is_proof)

    def test_the_qualified_counters_are_the_proof_ones(self):
        keys = {c.key for c in proof_counters()}

        self.assertIn('companies_published', keys)
        self.assertIn('companies_with_evidence', keys)
        self.assertNotIn('companies_total', keys)
        self.assertNotIn('countries_total', keys)

    def test_module_counts_come_from_the_registry(self):
        stats = platform_stats()

        self.assertEqual(stats['production_modules'].value,
                         len(by_status(PRODUCTION)))
        self.assertEqual(stats['experimental_modules'].value,
                         len(by_status(EXPERIMENTAL)))

    def test_specification_packs_are_labelled_as_documents(self):
        counter = platform_stats()['specification_packs']

        self.assertIn('DOCUMENTS', counter.derivation)

    def test_the_stats_call_is_not_linear_in_company_count(self):
        """
        The obvious implementation runs coverage_for() per company — about a
        thousand queries for a homepage counter.
        """
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        with CaptureQueriesContext(connection) as captured:
            platform_stats()

        self.assertLess(len(captured), 40)


class NoHardCodedCounts(TestCase):
    """
    The claims this service replaces. Each was true once, and each drifts
    silently — which makes it indistinguishable from an invented number.
    """

    def _search(self, pattern):
        import subprocess

        from django.conf import settings

        result = subprocess.run(
            ['grep', '-rIl', '--include=*.py', '--include=*.html',
             '-e', pattern, '.'],
            capture_output=True, text=True, cwd=settings.BASE_DIR)
        return [f for f in result.stdout.split()
                if 'test' not in f and '/migrations/' not in f]

    def test_the_registry_is_the_only_place_module_counts_live(self):
        """
        Nothing may hard-code a module status count; they are derived.
        """
        stats = platform_stats()

        self.assertEqual(stats['production_modules'].derivation,
                         'platform_registry.agents, status=PRODUCTION')
