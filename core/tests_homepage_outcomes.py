"""Focused tests for the homepage Outcomes section.

Same two layers as the other homepage section suites, because the section is a
React island and this repo has no JavaScript test runner:

* **Rendered-HTML tests** — the island mounts lazily, its CTA route resolves
  server-side, the no-JS fallback carries the full chain, and the three legacy
  blocks it replaces are gone while their unique content survives.

* **Source-contract tests** — the four stages exist in causal order, the chain
  activates once (no loop), every stage stays legible without animation, and
  the locked motion constraints hold.

Scans run against comment-stripped source, since these files document the
things they forbid.
"""

from __future__ import annotations

import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase, TestCase

APP_SRC = Path(settings.BASE_DIR) / 'frontend' / 'app' / 'src'
COMPONENT = APP_SRC / 'components' / 'homepage' / 'Outcomes.tsx'
STYLESHEET = APP_SRC / 'outcomes.css'
REGISTRY = APP_SRC / 'registry.ts'

#: The chain, in the only order that makes the argument.
STAGES = (
    ('risk', 'Risk', 'See the risk'),
    ('decision', 'Decision', 'Make the decision'),
    ('action', 'Action', 'Prioritise the action'),
    ('impact', 'Impact', 'Measure the impact'),
)

VALUE = (
    'Reduce avoidable risk',
    'Identify waste and inefficiency',
    'Prioritise capital and interventions',
    'Create evidence for boards, investors and stakeholders',
)

TRUST = 'EcoIQ does not replace management judgement'


def strip_comments(source: str) -> str:
    source = re.sub(r'/\*.*?\*/', '', source, flags=re.DOTALL)
    source = re.sub(r'^\s*//.*$', '', source, flags=re.MULTILINE)
    return source


def strip_html_comments(html: str) -> str:
    return re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)


class OutcomesRenderTests(TestCase):
    def setUp(self) -> None:
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.html = response.content.decode('utf-8')
        self.visible = strip_html_comments(self.html)

    def test_island_is_mounted_and_lazy(self) -> None:
        self.assertIn('data-island="Outcomes"', self.html)
        marker = self.html.index('data-island="Outcomes"')
        self.assertIn('data-island-lazy', self.html[marker : marker + 200])

    def test_enterprise_cta_resolves_server_side(self) -> None:
        self.assertIn('"enterpriseHref": "/request-access/enterprise/"', self.html)
        self.assertIn(self.client.get('/request-access/enterprise/').status_code, (200, 301, 302))

    def test_nojs_fallback_carries_the_whole_chain(self) -> None:
        block = self.html[self.html.index('eiq-oc-nojs') :][:3600]
        self.assertIn('From analysis to measurable outcomes.', block)
        for _id, step, label in STAGES:
            with self.subTest(stage=step):
                self.assertIn(step, block)
                self.assertIn(label.lower(), block.lower())
        for v in VALUE:
            with self.subTest(value=v):
                self.assertIn(v, block)
        self.assertIn(TRUST, block)
        self.assertIn('/request-access/enterprise/', block)

    def test_outcomes_follows_the_decision_brief(self) -> None:
        """Journey order: here is the decision -> here is what it produces."""
        brief = self.html.index('data-island="DecisionBrief"')
        outcomes = self.html.index('data-island="Outcomes"')
        self.assertLess(brief, outcomes)

    # -- consolidation -----------------------------------------------------

    def test_legacy_blocks_are_retired(self) -> None:
        """#5 triptych, #6 stats band and #7 country-flag chips."""
        for gone in (
            'Climate, ESG and transition readiness analysis.',   # #5
            'Globally tracked &amp; scored',                     # #6
            # #7's own markers. NOT the bare link text "View country
            # intelligence" — an unrelated block further down the page uses the
            # same wording, and asserting on it would fail for the wrong reason.
            '🇬🇧 United Kingdom',
            'data-island="GlobalIntelligence"',
        ):
            with self.subTest(removed=gone):
                self.assertNotIn(gone, self.visible)

    def test_unique_content_from_retired_blocks_survives(self) -> None:
        """#6's live company count moved to the hero rather than being lost."""
        hero_end = self.html.index('data-island="ProductArchitecture"')
        hero = self.html[:hero_end]
        self.assertIn('companies scored', hero)
        self.assertIn('focus markets', hero)
        # #7's destination is still linked from later sections.
        self.assertIn('/countries/', self.html)

    def test_countries_route_still_resolves(self) -> None:
        self.assertIn(self.client.get('/countries/').status_code, (200, 301, 302))

    def test_review_path_untouched_by_this_change(self) -> None:
        self.assertIn('/request-access/review/', self.html)
        self.assertIn('From £4,900', self.html)


class OutcomesSourceContractTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.source = COMPONENT.read_text(encoding='utf-8')
        cls.css = STYLESHEET.read_text(encoding='utf-8')
        cls.code = strip_comments(cls.source)
        cls.css_code = strip_comments(cls.css)

    def test_registered_as_an_island(self) -> None:
        self.assertIn('Outcomes,', REGISTRY.read_text(encoding='utf-8'))

    def test_four_stages_in_causal_order(self) -> None:
        positions = []
        for stage_id, step, label in STAGES:
            with self.subTest(stage=stage_id):
                self.assertIn(f"id: '{stage_id}'", self.code)
                self.assertIn(f"step: '{step}'", self.code)
                self.assertIn(f"label: '{label}'", self.code)
            positions.append(self.code.index(f"id: '{stage_id}'"))
        self.assertEqual(positions, sorted(positions), 'stages are declared out of order')

    def test_stage_copy_is_present(self) -> None:
        for phrase in (
            'before they become expensive surprises',
            'see what would change the outcome',
            'interventions, responsibilities and next steps',
            'feed new evidence back into the next decision cycle',
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.code)

    def test_value_statements_and_trust_line(self) -> None:
        for v in VALUE:
            with self.subTest(value=v):
                self.assertIn(v, self.code)
        self.assertIn(TRUST, self.code)

    def test_it_is_a_chain_not_a_card_grid(self) -> None:
        """An ordered list with connectors — the order is the argument."""
        self.assertIn('<ol className="eiq-oc-chain"', self.code)
        self.assertIn('eiq-oc-connector', self.code)

    def test_no_invented_statistics(self) -> None:
        """Outcome chips name kinds of result, never quantities."""
        for pattern in (r'\d+\s*%', r'\d+x\b', r'\$\d'):
            with self.subTest(pattern=pattern):
                self.assertIsNone(re.search(pattern, self.code), f'possible invented stat: {pattern}')

    # -- motion ------------------------------------------------------------

    def test_sequence_runs_once_and_never_loops(self) -> None:
        self.assertIn('const played = useRef(false)', self.code)
        self.assertIn('if (!entry.isIntersecting || played.current) return', self.code)
        self.assertIn('observer.disconnect()', self.code)
        self.assertNotIn('animation:', self.css_code)
        self.assertNotIn('infinite', self.css_code)
        self.assertNotIn('@keyframes', self.css_code)

    def test_stages_are_never_hidden_only_quietened(self) -> None:
        """Activation is emphasis, so no stage copy depends on the sequence."""
        rule = self.css_code[self.css_code.index('.eiq-oc-chain > li {') :][:400]
        self.assertIn('opacity: 0.55', rule)
        self.assertNotIn('opacity: 0;', rule)
        self.assertNotIn('display: none', rule)
        self.assertNotIn('visibility: hidden', rule)

    def test_reduced_motion_shows_the_complete_chain(self) -> None:
        self.assertIn("useMediaQuery('(prefers-reduced-motion: reduce)')", self.code)
        self.assertIn("data-active={reduced ? 'all' : String(active)}", self.code)
        block = self.css_code[self.css_code.index("[data-active='all']") :]
        self.assertIn('opacity: 1', block)
        reduced = self.css_code[self.css_code.index('@media (prefers-reduced-motion: reduce)') :]
        self.assertIn('transition: none !important', reduced)
        self.assertNotIn('display: none', reduced)

    def test_locked_motion_constraints(self) -> None:
        self.assertNotIn('motion.', self.code)
        self.assertNotIn('domMax', self.code)
        self.assertNotIn('layoutId', self.code)
        self.assertIn('0.18s cubic-bezier(0.22, 1, 0.36, 1)', self.css)
        self.assertIn('0.42s cubic-bezier(0.22, 1, 0.36, 1)', self.css)
        self.assertNotIn('transition: all', self.css_code)

    # -- accessibility -----------------------------------------------------

    def test_semantic_markup_no_clickable_divs(self) -> None:
        self.assertIn('<h3 className="eiq-oc-stage-label"', self.code)
        # The only interactive element is the CTA anchor.
        self.assertNotIn('onClick', self.code)

    def test_cta_focus_and_touch_target(self) -> None:
        self.assertIn('.eiq-oc-cta:focus-visible', self.css_code)
        self.assertIn('min-height: 44px', self.css_code)
        self.assertNotIn('outline: none', self.css_code)

    def test_mobile_is_a_vertical_progression(self) -> None:
        mobile = self.css_code[self.css_code.index('@media (max-width: 860px)') :]
        self.assertIn('grid-template-columns: 1fr', mobile)
