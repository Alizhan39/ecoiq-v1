"""Focused tests for the homepage Sample Decision Brief section.

Two layers, matching the other homepage section suites — the section is a
React island and this repo has no JavaScript test runner:

* **Rendered-HTML tests** — the island mounts lazily, its CTA routes resolve
  server-side, the no-JS fallback carries the whole brief, and the two legacy
  CTA blocks it replaces are gone while the paid Review path stays reachable.

* **Source-contract tests** — the runtime behaviour: the causal reveal runs
  once, the disclosure is a real `aria-expanded`/`aria-controls` control, the
  scenario levers are `aria-pressed` buttons, reduced motion renders the whole
  brief open, and the locked motion constraints hold.

Every figure in the section is invented, so the honesty rules are asserted
too: an illustrative label, scenario framing, and no forecast language.

Scans run against comment-stripped source, since this file and the component
both *document* the forbidden words.
"""

from __future__ import annotations

import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase, TestCase

APP_SRC = Path(settings.BASE_DIR) / 'frontend' / 'app' / 'src'
COMPONENT = APP_SRC / 'components' / 'homepage' / 'DecisionBrief.tsx'
STYLESHEET = APP_SRC / 'decision-brief.css'
REGISTRY = APP_SRC / 'registry.ts'

DIMENSIONS = (
    ('Evidence Quality', 82),
    ('Transition Risk', 61),
    ('Implementation Readiness', 74),
    ('Capital Readiness', 68),
    ('Stewardship Alignment', 76),
)

LEVERS = ('Resolve evidence gaps', 'Improve energy pathway', 'Secure financing structure')

#: Words that would turn an illustration into a claim about the future.
FORBIDDEN_PREDICTION = ('forecast', 'predicted', 'guaranteed', 'will deliver', 'expected return')


def strip_comments(source: str) -> str:
    source = re.sub(r'/\*.*?\*/', '', source, flags=re.DOTALL)
    source = re.sub(r'^\s*//.*$', '', source, flags=re.MULTILINE)
    return source


def strip_html_comments(html: str) -> str:
    return re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)


class DecisionBriefRenderTests(TestCase):
    def setUp(self) -> None:
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.html = response.content.decode('utf-8')
        self.visible = strip_html_comments(self.html)

    def test_island_is_mounted_and_lazy(self) -> None:
        self.assertIn('data-island="DecisionBrief"', self.html)
        marker = self.html.index('data-island="DecisionBrief"')
        self.assertIn('data-island-lazy', self.html[marker : marker + 200])

    def test_cta_routes_resolve_server_side(self) -> None:
        self.assertIn('"reviewHref": "/request-access/review/"', self.html)
        self.assertIn('"methodologyHref": "/methodology/"', self.html)

    def test_cta_routes_actually_resolve(self) -> None:
        for path in ('/request-access/review/', '/methodology/'):
            with self.subTest(path=path):
                self.assertIn(self.client.get(path).status_code, (200, 301, 302))

    def test_nojs_fallback_carries_the_whole_brief(self) -> None:
        block = self.html[self.html.index('eiq-db-nojs') :][:3200]
        self.assertIn('See the decision, not the dashboard.', block)
        self.assertIn('71', block)
        self.assertIn('PROCEED — WITH CONDITIONS', block)
        for label, score in DIMENSIONS:
            with self.subTest(dimension=label):
                self.assertIn(label, block)
                self.assertIn(str(score), block)
        self.assertIn('Key finding', block)
        self.assertIn('Recommended next move', block)
        self.assertIn('Illustrative EcoIQ decision brief', block)

    def test_section_follows_product_architecture(self) -> None:
        """Journey order: what you are -> what an output looks like."""
        product = self.html.index('data-island="ProductArchitecture"')
        brief = self.html.index('data-island="DecisionBrief"')
        hero = self.html.index('id="eiq-hero-title"')
        self.assertLess(hero, product)
        self.assertLess(product, brief)

    # -- consolidation -----------------------------------------------------

    def test_legacy_cta_blocks_are_retired(self) -> None:
        """#18 Get started and #19 analytical review are out of composition."""
        for gone in (
            'Ready to see your EcoIQ score',
            'EcoIQ Analytical Review',
            'Get started',
        ):
            with self.subTest(removed=gone):
                self.assertNotIn(gone, self.visible)

    def test_unique_copy_from_the_retired_block_was_preserved(self) -> None:
        self.assertIn('No payment required to submit a review request', self.visible)

    def test_review_remains_reachable_from_three_surfaces(self) -> None:
        """Hero, Product Architecture and the Decision Brief."""
        hero_start = self.html.index('id="eiq-hero-title"')
        product_start = self.html.index('data-island="ProductArchitecture"')
        brief_start = self.html.index('data-island="DecisionBrief"')

        hero = self.html[hero_start:product_start]
        product = self.html[product_start:brief_start]
        brief = self.html[brief_start:]

        for name, region in (('hero', hero), ('product architecture', product), ('decision brief', brief)):
            with self.subTest(surface=name):
                self.assertIn('/request-access/review/', region, f'Review CTA missing from {name}')

    # -- honesty -----------------------------------------------------------

    def test_illustrative_labelling_is_present(self) -> None:
        self.assertIn('Illustrative EcoIQ decision brief', self.html)

    def test_no_prediction_language(self) -> None:
        lowered = self.visible.lower()
        for word in FORBIDDEN_PREDICTION:
            with self.subTest(word=word):
                self.assertNotIn(word, lowered)


class DecisionBriefSourceContractTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.source = COMPONENT.read_text(encoding='utf-8')
        cls.css = STYLESHEET.read_text(encoding='utf-8')
        cls.code = strip_comments(cls.source)
        cls.css_code = strip_comments(cls.css)

    def test_registered_as_an_island(self) -> None:
        self.assertIn('DecisionBrief,', REGISTRY.read_text(encoding='utf-8'))

    # -- the brief ---------------------------------------------------------

    def test_headline_score_and_decision(self) -> None:
        self.assertIn('const BASE_SCORE = 71', self.code)
        self.assertIn('Proceed — with conditions', self.code)
        self.assertIn('Industrial Portfolio — Transition Review', self.code)

    def test_five_dimensions_with_their_scores(self) -> None:
        for label, score in DIMENSIONS:
            with self.subTest(dimension=label):
                self.assertIn(f"label: '{label}', score: {score}", self.code)

    def test_finding_and_recommendation_present(self) -> None:
        self.assertIn('Key finding', self.code)
        self.assertIn('implementation risk remains concentrated', self.code)
        self.assertIn('Recommended next move', self.code)
        self.assertIn('before capital deployment', self.code)

    def test_three_scenario_levers(self) -> None:
        for lever in LEVERS:
            with self.subTest(lever=lever):
                self.assertIn(lever, self.code)

    def test_scenario_output_is_framed_as_illustrative(self) -> None:
        self.assertIn('Illustrative scenario', self.code)
        self.assertIn('Potential decision improvement', self.code)
        self.assertIn('not a forecast of any real outcome', self.code)

    # -- disclosure + accessibility ----------------------------------------

    def test_why_control_is_a_real_button_with_aria(self) -> None:
        self.assertIn('type="button"', self.code)
        self.assertIn('aria-expanded={breakdownOpen}', self.code)
        self.assertIn('aria-controls={`${baseId}-breakdown`}', self.code)
        self.assertIn('Why {headline}?', self.code)

    def test_aria_expanded_and_hidden_cannot_disagree(self) -> None:
        self.assertIn('const breakdownOpen = expanded || reduced', self.code)
        self.assertIn('hidden={!breakdownOpen}', self.code)

    def test_levers_are_toggle_buttons_not_clickable_divs(self) -> None:
        self.assertIn('aria-pressed={levers.has(lever.id)}', self.code)
        self.assertNotIn('onClick={() => toggleLever' + '}', self.code.replace(' ', ''))

    def test_focus_states_are_visible(self) -> None:
        for selector in (
            '.eiq-db-why:focus-visible',
            '.eiq-db-lever:focus-visible',
            '.eiq-db-cta:focus-visible',
        ):
            with self.subTest(selector=selector):
                self.assertIn(selector, self.css_code)
        self.assertNotIn('outline: none', self.css_code)

    def test_touch_targets(self) -> None:
        self.assertIn('min-height: 44px', self.css_code)

    # -- motion ------------------------------------------------------------

    def test_reveal_runs_once_and_does_not_loop(self) -> None:
        self.assertIn('const revealed = useRef(false)', self.code)
        self.assertIn('if (!entry.isIntersecting || revealed.current) return', self.code)
        self.assertIn('observer.disconnect()', self.code)
        self.assertNotIn('infinite', self.css_code)
        self.assertNotIn('animation:', self.css_code)

    def test_reveal_is_causal(self) -> None:
        self.assertIn("const STEPS = ['score', 'dimensions', 'finding', 'recommendation'] as const", self.code)

    def test_reduced_motion_renders_the_whole_brief(self) -> None:
        self.assertIn("useMediaQuery('(prefers-reduced-motion: reduce)')", self.code)
        self.assertIn("data-step={reduced ? 'all' : stepName}", self.code)
        block = self.css_code[self.css_code.index("[data-step='all']") :]
        self.assertIn('opacity: 1', block)
        reduced_block = self.css_code[self.css_code.index('@media (prefers-reduced-motion: reduce)') :]
        self.assertIn('transition: none !important', reduced_block)
        self.assertNotIn('display: none', reduced_block)

    def test_locked_motion_constraints(self) -> None:
        self.assertNotIn('motion.', self.code)
        self.assertNotIn('domMax', self.code)
        self.assertNotIn('layoutId', self.code)
        self.assertIn('0.18s cubic-bezier(0.22, 1, 0.36, 1)', self.css)
        self.assertIn('0.42s cubic-bezier(0.22, 1, 0.36, 1)', self.css)
        self.assertNotIn('transition: all', self.css_code)

    def test_mobile_stacks_the_reads(self) -> None:
        mobile = self.css_code[self.css_code.index('@media (max-width: 860px)') :]
        self.assertIn('grid-template-columns: 1fr', mobile)
