"""
The capability statuses the industrial page shows, against the registry that
owns them.

WHY THIS CROSSES THE LANGUAGE BOUNDARY
--------------------------------------
`platform_registry/agents.py` defines the vocabulary EcoIQ uses to say how
finished a module is: PRODUCTION, BETA, EXPERIMENTAL, PLANNED, SPECIFICATION.
The industrial-modernisation page reports the same kind of claim about its own
seven workflow stages, and it does so in TypeScript.

Two lists of status names in two languages drift. This repository has already
paid for that: one visibility rule was written out by hand in six places, every
copy went stale on the same value, and the page and its own API ended up
disagreeing about whether an organisation was reachable. The same failure here
would be worse, because the thing being described IS how much exists.

So the TypeScript file is parsed and held to the Python.
"""
import pathlib
import re

from django.conf import settings
from django.test import SimpleTestCase

from platform_registry.agents import (
    BETA, EXPERIMENTAL, PLANNED, PRODUCTION, SPECIFICATION, STATUS_ORDER,
)

CAPABILITIES = (pathlib.Path(settings.BASE_DIR)
                / 'frontend/web/src/features/transition/domain/capabilities.ts')


def declared_statuses() -> set[str]:
    """The CapabilityStatus union members, as written in the .ts file."""
    source = CAPABILITIES.read_text(encoding='utf-8')
    block = re.search(r'export type CapabilityStatus =(.*?);', source, re.S)
    assert block, 'CapabilityStatus union not found'
    return set(re.findall(r"'([A-Z_]+)'", block.group(1)))


def assigned_statuses() -> set[str]:
    """Every status actually used by a workflow stage."""
    source = CAPABILITIES.read_text(encoding='utf-8')
    return set(re.findall(r"status:\s*'([A-Z_]+)'", source))


class VocabularyTests(SimpleTestCase):

    def test_the_file_is_where_this_expects(self):
        """If it moves, every assertion below silently stops guarding."""
        self.assertTrue(CAPABILITIES.exists(), f'{CAPABILITIES} is missing')

    def test_the_union_is_exactly_the_registry_vocabulary(self):
        self.assertEqual(
            declared_statuses(), set(STATUS_ORDER),
            'The industrial page declares a different set of statuses from '
            'platform_registry.agents. One vocabulary, or the page is making '
            'a claim the registry has no word for.')

    def test_every_assigned_status_is_a_real_one(self):
        for status in assigned_statuses():
            self.assertIn(status, STATUS_ORDER, f'{status!r} is not a registry status')

    def test_no_stage_claims_to_be_production(self):
        """
        The load-bearing assertion. Nothing in this workflow runs against a
        real facility, so nothing may carry the status that means it does.
        If a stage genuinely reaches PRODUCTION, this test is what someone
        must delete — which makes that a deliberate act.
        """
        assigned = assigned_statuses()
        self.assertNotIn(PRODUCTION, assigned)
        self.assertNotIn(BETA, assigned)

    def test_the_statuses_used_are_the_honest_ones(self):
        """Only the three that mean "not live" are in use."""
        self.assertTrue(
            assigned_statuses() <= {EXPERIMENTAL, PLANNED, SPECIFICATION},
            f'unexpected statuses: {assigned_statuses()}')

    def test_every_stage_states_a_basis(self):
        """
        platform_registry's own rule: "a status without a stated basis is an
        assertion". Applied to the page that borrows its vocabulary.
        """
        source = CAPABILITIES.read_text(encoding='utf-8')
        stages = re.findall(r"key:\s*'(\w+)'", source)
        bases = re.findall(r"basis:\s*\n?\s*'", source)
        self.assertEqual(
            len(stages), len(bases),
            f'{len(stages)} workflow stages but {len(bases)} stated bases')

    def test_no_basis_is_a_vague_reassurance(self):
        source = CAPABILITIES.read_text(encoding='utf-8')
        for phrase in ('coming soon', 'in progress', 'shortly', 'roadmap'):
            self.assertNotIn(
                phrase, source.lower(),
                f'{phrase!r} is a mood, not a basis someone can check')


class ContainmentTests(SimpleTestCase):
    """
    The four physical interventions belong to ENGINEER, and are not separate
    product stages. Collapsing the two axes is the failure this guards.
    """

    def test_engineer_contains_the_four_physical_interventions(self):
        source = CAPABILITIES.read_text(encoding='utf-8')
        engineer = source[source.index("key: 'engineer'"):source.index("key: 'simulate'")]
        contains = re.search(r'containsPhysicalStages:\s*\[(.*?)\]', engineer, re.S)
        assert contains
        found = set(re.findall(r"'(\w+)'", contains.group(1)))
        self.assertEqual(found, {'retrofit', 'electrify', 'recover', 'circularise'})

    def test_no_other_stage_claims_to_contain_a_physical_stage(self):
        source = CAPABILITIES.read_text(encoding='utf-8')
        blocks = re.findall(r"key: '(\w+)',.*?containsPhysicalStages:\s*\[(.*?)\]",
                            source, re.S)
        for key, contents in blocks:
            if key == 'engineer':
                continue
            self.assertEqual(
                re.findall(r"'(\w+)'", contents), [],
                f'{key} claims to contain physical stages; only ENGINEER does')
