"""Focused tests for the homepage How EcoIQ Works / Impact Engine section.

The section carries real product architecture — the twelve-stage
Decision-to-Impact Loop — presented as four macro phases with the detail behind
disclosure. These tests pin both halves: that the loop is complete and in
order, and that the homepage presentation stays compact and honest.

Layered like the other homepage suites (React island, no JS test runner):
rendered-HTML tests for what Django owns, source-contract tests for runtime
behaviour. Source scans strip comments, since the files document the rules
they enforce.
"""

from __future__ import annotations

import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase, TestCase

APP_SRC = Path(settings.BASE_DIR) / 'frontend' / 'app' / 'src'
COMPONENT = APP_SRC / 'components' / 'homepage' / 'HowEcoIQWorks.tsx'
STYLESHEET = APP_SRC / 'how-ecoiq-works.css'
REGISTRY = APP_SRC / 'registry.ts'

MACRO_PHASES = ('Understand', 'Decide', 'Act', 'Prove & Learn')

#: The full Decision-to-Impact Loop, in order. None of it may be dropped.
LOOP = (
    'Detect', 'Diagnose',
    'Generate', 'Simulate', 'Optimize',
    'Match', 'Finance', 'Execute',
    'Verify', 'Measure', 'Learn', 'Repeat',
)

TRUST_RAIL = ('Evidence', 'AI analysis', 'Verification', 'Analyst review', 'Decision')


def strip_comments(source: str) -> str:
    source = re.sub(r'/\*.*?\*/', '', source, flags=re.DOTALL)
    source = re.sub(r'^\s*//.*$', '', source, flags=re.MULTILINE)
    return source


def strip_html_comments(html: str) -> str:
    return re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)


class HowEcoIQWorksRenderTests(TestCase):
    def setUp(self) -> None:
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.html = response.content.decode('utf-8')
        self.visible = strip_html_comments(self.html)

    def test_island_is_mounted_and_lazy(self) -> None:
        self.assertIn('data-island="HowEcoIQWorks"', self.html)
        marker = self.html.index('data-island="HowEcoIQWorks"')
        self.assertIn('data-island-lazy', self.html[marker : marker + 220])

    def test_routes_resolve_server_side_and_actually_work(self) -> None:
        self.assertIn('"platformHref": "/platform/"', self.html)
        self.assertIn('"methodologyHref": "/methodology/"', self.html)
        self.assertIn('"agentsHref": "/ai-agents/"', self.html)
        for path in ('/platform/', '/methodology/', '/ai-agents/'):
            with self.subTest(path=path):
                self.assertIn(self.client.get(path).status_code, (200, 301, 302))

    def test_journey_order(self) -> None:
        """Decision Brief -> Outcomes -> How EcoIQ Works."""
        brief = self.html.index('data-island="DecisionBrief"')
        outcomes = self.html.index('data-island="Outcomes"')
        works = self.html.index('data-island="HowEcoIQWorks"')
        self.assertLess(brief, outcomes)
        self.assertLess(outcomes, works)

    def test_nojs_fallback_carries_the_whole_model(self) -> None:
        block = self.html[self.html.index('eiq-hw-nojs') :][:3600]
        self.assertIn('One system. From signal to verified impact.', block)
        self.assertIn('Impact Engine', block)
        for phase in MACRO_PHASES:
            with self.subTest(phase=phase):
                self.assertIn(phase.replace('&', '&amp;'), block)
        for stage in LOOP:
            with self.subTest(stage=stage):
                self.assertIn(stage, block)
        self.assertIn('does not stop at recommendation', block)

    # -- consolidation -----------------------------------------------------

    def test_legacy_blocks_are_retired(self) -> None:
        """#4 agents explainer, #9 how-it-works, #16 digital twin caption."""
        for gone in (
            'data-island="DigitalTwinPreview"',
            'Meet the EcoIQ AI Agents',
            'We read the evidence',
            'AI scores each company',
        ):
            with self.subTest(removed=gone):
                self.assertNotIn(gone, self.visible)

    def test_agents_destination_survives_the_retirement(self) -> None:
        """#4 owned the agents entry point; this section must keep one."""
        self.assertIn('/ai-agents/', self.visible)

    def test_paid_review_path_untouched(self) -> None:
        self.assertIn('/request-access/review/', self.html)
        self.assertIn('From £4,900', self.html)

    # -- honesty -----------------------------------------------------------

    def test_no_any_problem_claim(self) -> None:
        """Scope is 'complex real-world problems', never 'any problem'."""
        lowered = self.visible.lower()
        for phrase in ('any problem', 'solves anything', 'solve any '):
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, lowered)

    def test_human_review_is_stated_not_implied_away(self) -> None:
        self.assertIn('Analyst review', self.visible)


class HowEcoIQWorksSourceContractTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.source = COMPONENT.read_text(encoding='utf-8')
        cls.css = STYLESHEET.read_text(encoding='utf-8')
        cls.code = strip_comments(cls.source)
        cls.css_code = strip_comments(cls.css)
        #: Prose in JSX wraps across lines, so sentence assertions run against
        #: a whitespace-normalised view rather than the raw source.
        cls.prose = re.sub(r'\s+', ' ', cls.code)

    def test_registered_as_an_island(self) -> None:
        self.assertIn('HowEcoIQWorks,', REGISTRY.read_text(encoding='utf-8'))

    # -- the architecture --------------------------------------------------

    def test_four_macro_phases_in_order(self) -> None:
        positions = [self.code.index(f"name: '{p}'") for p in MACRO_PHASES]
        self.assertEqual(positions, sorted(positions), 'macro phases out of order')

    def test_all_twelve_loop_stages_present_and_in_order(self) -> None:
        positions = [self.code.index(f"name: '{s}',") for s in LOOP]
        self.assertEqual(positions, sorted(positions), 'loop stages out of order')

    def test_repeat_closes_the_loop(self) -> None:
        self.assertIn("name: 'Repeat'", self.code)
        self.assertIn('next decision starts better informed', self.code)

    def test_stage_counts_per_phase(self) -> None:
        """2 + 3 + 3 + 4 = the twelve stages, ranked not dropped."""
        self.assertEqual(len(LOOP), 12)

    def test_closed_loop_message(self) -> None:
        self.assertIn('does not stop at recommendation', self.prose)
        self.assertIn('feeds evidence back into the system', self.prose)
        self.assertIn('From problems to measurable progress', self.prose)

    def test_product_identity_and_differentiation(self) -> None:
        self.assertIn('EcoIQ Impact Engine', self.prose)
        self.assertIn('A conventional AI returns an answer', self.prose)

    def test_specialist_ai_is_examples_plus_a_link_not_a_roster(self) -> None:
        for domain in ('Climate', 'Finance', 'Governance', 'Stewardship'):
            with self.subTest(domain=domain):
                self.assertIn(f"'{domain}'", self.code)
        self.assertIn('Specialist AI investigates different parts of the decision', self.prose)
        self.assertIn('agentsHref', self.code)

    def test_human_review_trust_rail(self) -> None:
        for node in TRUST_RAIL:
            with self.subTest(node=node):
                self.assertIn(f"'{node}'", self.code)

    # -- disclosure + accessibility ----------------------------------------

    def test_phases_are_real_buttons_with_aria(self) -> None:
        self.assertIn('type="button"', self.code)
        self.assertIn('aria-expanded={reduced ? true : open === phase.id}', self.code)
        self.assertIn('aria-controls={`${baseId}-detail-${phase.id}`}', self.code)

    def test_headings_are_semantic(self) -> None:
        self.assertIn('<h2 id={`${baseId}-title`}', self.code)
        self.assertIn('<h3 className="eiq-hw-phase-h">', self.code)

    def test_full_loop_is_visible_without_opening_anything(self) -> None:
        """The collapsed state lists all twelve stages, so nothing is buried."""
        self.assertIn('PHASES.flatMap((phase) => phase.stages).map((stage)', self.code)

    def test_focus_states_and_touch_targets(self) -> None:
        for selector in ('.eiq-hw-phase-btn:focus-visible', '.eiq-hw-cta:focus-visible'):
            with self.subTest(selector=selector):
                self.assertIn(selector, self.css_code)
        self.assertIn('min-height: 44px', self.css_code)
        self.assertNotIn('outline: none', self.css_code)

    def test_opening_a_phase_costs_no_page_height(self) -> None:
        """One shared detail strip with a reserved box — the compaction trick."""
        self.assertIn('min-height: 7.5rem', self.css_code)

    # -- motion ------------------------------------------------------------

    def test_sequence_runs_once_and_never_loops(self) -> None:
        self.assertIn('const played = useRef(false)', self.code)
        self.assertIn('if (!entry.isIntersecting || played.current) return', self.code)
        self.assertIn('observer.disconnect()', self.code)
        self.assertNotIn('infinite', self.css_code)
        self.assertNotIn('animation:', self.css_code)

    def test_reduced_motion_exposes_every_stage(self) -> None:
        self.assertIn("useMediaQuery('(prefers-reduced-motion: reduce)')", self.code)
        self.assertIn("const detailState = reduced ? 'all' : (open ?? 'none')", self.code)
        block = self.css_code[self.css_code.index("[data-detail='all']") :]
        self.assertIn('flex-direction: column', block)
        reduced_block = self.css_code[self.css_code.index('@media (prefers-reduced-motion: reduce)') :]
        self.assertIn('transition: none !important', reduced_block)
        self.assertNotIn('display: none', reduced_block)

    def test_locked_motion_constraints_and_no_new_dependency(self) -> None:
        self.assertNotIn('motion.', self.code)
        self.assertNotIn('domMax', self.code)
        self.assertNotIn('layoutId', self.code)
        for dep in ('d3', 'three', 'reactflow', 'react-flow', 'gsap'):
            with self.subTest(dependency=dep):
                self.assertNotIn(dep, self.code.lower())
        self.assertIn('0.42s cubic-bezier(0.22, 1, 0.36, 1)', self.css)
        self.assertNotIn('transition: all', self.css_code)

    def test_mobile_is_vertical(self) -> None:
        mobile = self.css_code[self.css_code.index('@media (max-width: 860px)') :]
        self.assertIn('grid-template-columns: 1fr', mobile)

    def test_no_svg_graph(self) -> None:
        self.assertNotIn('<svg', self.code)
