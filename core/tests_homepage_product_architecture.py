"""Focused tests for the homepage Product Architecture section.

Two layers, because the section is a React island and this repository has no
JavaScript test runner (adding one was out of scope for this change):

* **Rendered-HTML tests** exercise everything Django is actually responsible
  for — that the island is mounted, that its CTA destinations are resolved
  server-side from the URL conf rather than hardcoded, that the no-JS fallback
  carries the full offer, and that the three legacy blocks it replaces are gone
  from the homepage while their deeper routes still resolve.

* **Source-contract tests** pin the parts that only exist at runtime in a
  browser: the disclosure ARIA wiring, one-panel-at-a-time state, the exact
  capability set per product, the reduced-motion fallback, and the locked
  motion constraints (no `motion.*`, no `domMax`, no `layoutId`, no new
  timing tokens). These assert on the component source. They are a guard
  against regression, not a substitute for the browser verification that was
  done separately — a source test cannot prove a panel visibly opens.
"""

from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

APP_SRC = Path(settings.BASE_DIR) / 'frontend' / 'app' / 'src'
COMPONENT = APP_SRC / 'components' / 'homepage' / 'ProductArchitecture.tsx'
STYLESHEET = APP_SRC / 'product-architecture.css'
REGISTRY = APP_SRC / 'registry.ts'

PRODUCTS = ('EcoIQ Review', 'EcoIQ Intelligence', 'EcoIQ Institutional')

CAPABILITIES = {
    'review': (
        'Evidence',
        'Transition Risk',
        'Governance',
        'Capital Readiness',
        'Ethical Finance',
        '90-Day Roadmap',
    ),
    'intelligence': (
        'Companies',
        'Countries',
        'Projects',
        'Rankings',
        'Comparisons',
        'Terminal',
    ),
    'institutional': (
        'Portfolio Intelligence',
        'Sector Analysis',
        'Sovereign Intelligence',
        'API / Data',
        'Monitoring',
        'Implementation',
    ),
}


class ProductArchitectureRenderTests(TestCase):
    """What the server actually sends for the homepage."""

    def setUp(self) -> None:
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.html = response.content.decode('utf-8')

    def test_island_is_mounted_on_the_homepage(self) -> None:
        self.assertIn('data-island="ProductArchitecture"', self.html)

    def test_section_heading_and_supporting_copy(self) -> None:
        self.assertIn('One platform. Three ways to use it.', self.html)
        self.assertIn(
            'EcoIQ combines evidence, risk, capital and stewardship intelligence',
            self.html,
        )

    def test_all_three_product_names_render(self) -> None:
        for name in PRODUCTS:
            with self.subTest(product=name):
                self.assertIn(name, self.html)

    def test_audiences_render(self) -> None:
        for audience in (
            'Companies &amp; projects',
            'Investors, funds &amp; analysts',
            'Banks, funds, corporations &amp; governments',
        ):
            with self.subTest(audience=audience):
                self.assertIn(audience, self.html)

    def test_review_shows_its_price_and_scope(self) -> None:
        self.assertIn('From £4,900', self.html)
        self.assertIn('Single company or project', self.html)

    def test_only_review_is_priced(self) -> None:
        """Intelligence and Institutional must not carry a price on the homepage."""
        self.assertEqual(self.html.count('From £4,900'), 1)

    def test_cta_destinations_come_from_the_url_conf(self) -> None:
        """The island receives resolved URLs, so routes cannot silently drift."""
        review = reverse('leads:request_review')
        enterprise = reverse('leads:enterprise_enquiry')
        self.assertIn(f'"reviewHref": "{review}"', self.html)
        self.assertIn('"intelligenceHref": "/platform/"', self.html)
        self.assertIn(f'"institutionalHref": "{enterprise}"', self.html)

    def test_nojs_fallback_carries_the_whole_offer(self) -> None:
        """With JavaScript off, all three products and their CTAs still render."""
        noscript = self.html[self.html.index('<noscript>') : self.html.index('</noscript>')]
        for name in PRODUCTS:
            self.assertIn(name, noscript)
        self.assertIn('From £4,900', noscript)
        self.assertIn(reverse('leads:request_review'), noscript)
        self.assertIn(reverse('leads:enterprise_enquiry'), noscript)
        self.assertIn('/platform/', noscript)

    # -- commercial safety -------------------------------------------------

    def test_review_is_reachable_from_both_hero_and_product_architecture(self) -> None:
        """The paid path must survive the legacy removal, from two places."""
        review = reverse('leads:request_review')
        hero_start = self.html.index('id="eiq-hero-title"')
        hero_end = self.html.index('data-island="ProductArchitecture"')
        hero = self.html[hero_start:hero_end]
        self.assertIn(review, hero, 'hero lost its Request Review link')

        after_hero = self.html[hero_end:]
        self.assertIn(review, after_hero, 'Product Architecture lost its Review CTA')

    def test_request_review_route_responds(self) -> None:
        self.assertIn(self.client.get(reverse('leads:request_review')).status_code, (200, 302))


class LegacyBlockRemovalTests(TestCase):
    """Blocks #12, #15 and #17 are gone from the homepage — and only from it."""

    def setUp(self) -> None:
        self.html = self.client.get('/').content.decode('utf-8')

    def test_intelligence_modules_block_is_not_rendered(self) -> None:
        """#12 — the ~1,142px five-module catalogue."""
        self.assertNotIn('Five intelligence modules', self.html)
        self.assertNotIn('id="intelligence-modules"', self.html)

    def test_intelligence_terminal_block_is_not_rendered(self) -> None:
        """#15 — the terminal / sovereign monitor teaser."""
        self.assertNotIn('Intelligence Terminal', self.html)

    def test_country_report_block_is_not_rendered(self) -> None:
        """#17 — the institutional country intelligence CTA block."""
        self.assertNotIn('Request Country Report', self.html)

    def test_unique_links_from_removed_blocks_are_preserved(self) -> None:
        """Nothing that only those blocks offered may be lost."""
        # #12's only deep anchor, now a Review capability.
        self.assertIn('/platform/#capital-integrity', self.html)
        # #15's terminal demo request, now an Intelligence capability.
        self.assertIn('Intelligence+Terminal+Demo+Request', self.html)
        # #17's destination, now an Institutional capability.
        self.assertIn('/countries/', self.html)

    def test_deeper_routes_still_exist(self) -> None:
        """Removing homepage composition must not remove any capability."""
        for path in ('/platform/', '/companies/', '/countries/'):
            with self.subTest(path=path):
                self.assertIn(
                    self.client.get(path).status_code,
                    (200, 301, 302),
                    f'{path} stopped resolving',
                )


class ProductArchitectureSourceContractTests(SimpleTestCase):
    """Runtime behaviour that has no server-side surface to assert against."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.source = COMPONENT.read_text(encoding='utf-8')
        cls.css = STYLESHEET.read_text(encoding='utf-8')

    def test_component_is_registered_as_an_island(self) -> None:
        registry = REGISTRY.read_text(encoding='utf-8')
        self.assertIn("import ProductArchitecture from './components/homepage/ProductArchitecture'", registry)
        self.assertIn('ProductArchitecture,', registry)

    def test_disclosure_uses_a_real_button_with_aria_wiring(self) -> None:
        self.assertIn('type="button"', self.source)
        self.assertIn('aria-expanded={open}', self.source)
        self.assertIn('aria-controls={panelId}', self.source)

    def test_aria_hidden_tracks_the_expanded_state(self) -> None:
        """State and exposure must never disagree."""
        self.assertIn('aria-hidden={!open}', self.source)

    def test_only_one_product_can_be_open(self) -> None:
        """A single `pinned` id, toggled — not a set of independent booleans."""
        self.assertIn('const [pinned, setPinned] = useState<string | null>(null)', self.source)
        self.assertIn('setPinned((current) => (current === id ? null : id))', self.source)
        self.assertIn('open={openId === product.id}', self.source)

    def test_hover_preview_is_gated_on_pointer_capability(self) -> None:
        """Touch devices must not depend on hover to reveal capabilities."""
        self.assertIn("useMediaQuery('(hover: hover) and (pointer: fine)')", self.source)
        self.assertIn('const hoverHandlers = canHover', self.source)

    def test_each_product_declares_exactly_its_own_capabilities(self) -> None:
        for product, labels in CAPABILITIES.items():
            block = self.source[self.source.index(f"id: '{product}'") :]
            block = block[: block.index('capabilities: [') + block[block.index('capabilities: ['):].index('],')]
            for label in labels:
                with self.subTest(product=product, capability=label):
                    self.assertIn(f"'{label}'", block)

    def test_capability_counts_are_six_each(self) -> None:
        self.assertEqual(self.source.count('capabilities: ['), 3)
        for product, labels in CAPABILITIES.items():
            with self.subTest(product=product):
                self.assertEqual(len(labels), 6)

    # -- locked motion constraints ----------------------------------------

    def test_does_not_import_full_motion_or_enable_dommax(self) -> None:
        self.assertNotIn('from \'framer-motion\'\nimport { motion', self.source)
        self.assertNotIn('motion.', self.source)
        self.assertNotIn('domMax', self.source)

    def test_does_not_introduce_layout_animation(self) -> None:
        self.assertNotIn('layoutId', self.source)

    def test_uses_only_locked_timing_values(self) -> None:
        """0.18s / 0.42s / ease.out — no new durations or curves."""
        self.assertIn('0.18s cubic-bezier(0.22, 1, 0.36, 1)', self.css)
        self.assertIn('0.42s cubic-bezier(0.22, 1, 0.36, 1)', self.css)
        for forbidden in ('0.3s', '0.5s', 'ease-in-out', 'linear'):
            with self.subTest(value=forbidden):
                self.assertNotIn(f' {forbidden}', self.css)

    def test_reduced_motion_still_exposes_the_information(self) -> None:
        """Transitions are removed; capability rows are not."""
        self.assertIn('@media (prefers-reduced-motion: reduce)', self.css)
        reduced = self.css[self.css.index('@media (prefers-reduced-motion: reduce)') :]
        self.assertIn('transition: none !important', reduced)
        self.assertIn('transform: none', reduced)
        self.assertNotIn('display: none', reduced)

    def test_animates_only_compositor_friendly_properties(self) -> None:
        """Per the motion style guide: transform/opacity, plus the grid collapse."""
        for prop in ('grid-template-rows 0.42s', 'opacity 0.', 'transform 0.'):
            with self.subTest(prop=prop):
                self.assertIn(prop, self.css)
        self.assertNotIn('transition: all', self.css)

    def test_focus_states_are_visible(self) -> None:
        for selector in ('.eiq-pa-toggle:focus-visible', '.eiq-pa-cta:focus-visible'):
            with self.subTest(selector=selector):
                self.assertIn(selector, self.css)
        self.assertNotIn('outline: none', self.css)

    def test_touch_targets_meet_the_minimum(self) -> None:
        self.assertIn('min-height: 44px', self.css)
        self.assertIn('minHeight: 44', self.source)
