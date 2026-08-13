"""Focused tests for the homepage Khalifah Field Intelligence section.

Three layers, because the section is a React island and this repo has no
JavaScript test runner (adding one was out of scope):

* **Rendered-HTML tests** — what Django owns: the island is mounted lazily,
  its video/poster/route props resolve server-side, the no-JS fallback carries
  the whole argument, and the homepage has exactly one Eco Tours entry point.

* **Asset tests** — the encoded derivatives exist, are H.264 8-bit (the master
  is HEVC, which Chrome and Firefox cannot decode), sit inside their size
  budgets, and are `+faststart`.

* **Source-contract tests** — the runtime behaviour: lazy source attachment,
  the four-step sequence, single-CTA discipline, no-layout-shift framing, and
  the operational honesty rules. The tour operation is NOT confirmed
  operational, so booking language must not ship and the section must describe
  a model in development.

Scans run against comment-stripped source: these files deliberately *document*
the forbidden strings, and a naive substring check would flag the
documentation while missing real markup.
"""

from __future__ import annotations

import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase, TestCase

APP_SRC = Path(settings.BASE_DIR) / 'frontend' / 'app' / 'src'
COMPONENT = APP_SRC / 'components' / 'homepage' / 'KhalifahFieldIntelligence.tsx'
STYLESHEET = APP_SRC / 'khalifah-field.css'
REGISTRY = APP_SRC / 'registry.ts'
VIDEO_DIR = Path(settings.BASE_DIR) / 'static' / 'video'

MP4_1080 = VIDEO_DIR / 'khalifah-field-1080.mp4'
MP4_720 = VIDEO_DIR / 'khalifah-field-720.mp4'
POSTER = VIDEO_DIR / 'khalifah-field-poster.jpg'

STEPS = ('Observe', 'Understand', 'Steward', 'Act')
PIPELINE = ('Field', 'Observe', 'Evidence', 'Assess', 'Decide', 'Stewardship')

#: Language that would assert an operating tour business. None may ship.
FORBIDDEN_OPERATIONAL = (
    'Book Now',
    'Book now',
    'Buy Tour',
    'Reserve',
    'Upcoming Dates',
    'Available dates',
    'Available Now',
    'Next departure',
    'Next Departure',
)


def strip_comments(source: str) -> str:
    source = re.sub(r'/\*.*?\*/', '', source, flags=re.DOTALL)
    source = re.sub(r'^\s*//.*$', '', source, flags=re.MULTILINE)
    return source


def strip_html_comments(html: str) -> str:
    return re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)


class KhalifahFieldRenderTests(TestCase):
    def setUp(self) -> None:
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.html = response.content.decode('utf-8')
        self.visible = strip_html_comments(self.html)

    def test_island_is_mounted_and_lazy(self) -> None:
        self.assertIn('data-island="KhalifahFieldIntelligence"', self.html)
        marker = self.html.index('data-island="KhalifahFieldIntelligence"')
        self.assertIn('data-island-lazy', self.html[marker : marker + 260])

    def test_video_derivatives_and_poster_are_wired_from_static(self) -> None:
        self.assertIn('/static/video/khalifah-field-1080.mp4', self.html)
        self.assertIn('/static/video/khalifah-field-720.mp4', self.html)
        self.assertIn('/static/video/khalifah-field-poster.jpg', self.html)

    def test_cta_destinations_resolve_server_side(self) -> None:
        self.assertIn('"toursHref": "/khalifa-tours/"', self.html)
        self.assertIn('"howItWorksHref": "/methodology/"', self.html)

    def test_cta_destinations_actually_resolve(self) -> None:
        for path in ('/khalifa-tours/', '/methodology/'):
            with self.subTest(path=path):
                self.assertIn(self.client.get(path).status_code, (200, 301, 302))

    def test_nojs_fallback_carries_the_whole_argument(self) -> None:
        block = self.html[self.html.index('eiq-kfi-nojs') :][:3000]
        self.assertIn('Understand it.', block)
        for step in STEPS:
            with self.subTest(step=step):
                self.assertIn(step, block)
        self.assertIn('/khalifa-tours/', block)
        self.assertIn('/methodology/', block)
        self.assertIn('Illustrative field experience', block)
        self.assertIn('in development', block)

    # -- consolidation -----------------------------------------------------

    def test_homepage_has_exactly_one_eco_tours_entry_point(self) -> None:
        """The duplicate KhalifaPipeline strip was removed; one CTA remains."""
        self.assertNotIn('data-island="KhalifaPipeline"', self.html)
        # One island prop (the live section) ...
        self.assertEqual(self.html.count('"toursHref": "/khalifa-tours/"'), 1)
        # ... and one raw href, which is this same section's <noscript> fallback,
        # not a second Eco Tours block.
        self.assertEqual(self.visible.count('href="/khalifa-tours/"'), 1)

    def test_removed_blocks_are_gone(self) -> None:
        """Audience switch, three-path grid and Field Passport are consolidated."""
        for gone in ('Khalifah Field Passport', 'Concept preview', 'Plan a Private Delegation'):
            with self.subTest(removed=gone):
                self.assertNotIn(gone, self.visible)

    def test_section_sits_below_the_commercial_core(self) -> None:
        hero = self.html.index('id="eiq-hero-title"')
        product = self.html.index('data-island="ProductArchitecture"')
        khalifah = self.html.index('data-island="KhalifahFieldIntelligence"')
        self.assertLess(hero, khalifah)
        self.assertLess(product, khalifah)

    def test_paid_review_path_is_untouched(self) -> None:
        """Consolidating the field layer must not cost the commercial path."""
        self.assertIn('/request-access/review/', self.html)
        self.assertIn('From £4,900', self.html)

    # -- honesty -----------------------------------------------------------

    def test_operational_status_is_stated_not_implied(self) -> None:
        self.assertIn('Illustrative field experience', self.html)
        self.assertIn('The EcoIQ field model is in development', self.html)

    def test_no_booking_language_anywhere_on_the_homepage(self) -> None:
        for phrase in FORBIDDEN_OPERATIONAL:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, self.visible)


class KhalifahFieldAssetTests(SimpleTestCase):
    """The encoded derivatives, not the 4K HEVC master."""

    def test_derivatives_and_poster_exist(self) -> None:
        for path in (MP4_1080, MP4_720, POSTER):
            with self.subTest(asset=path.name):
                self.assertTrue(path.exists(), f'{path.name} is missing')

    def test_derivatives_are_web_deliverable_sizes(self) -> None:
        self.assertLess(MP4_1080.stat().st_size, 10 * 1024 * 1024, '1080p over 10MB')
        self.assertLess(MP4_720.stat().st_size, 6 * 1024 * 1024, '720p over 6MB')
        self.assertLess(POSTER.stat().st_size, 250 * 1024, 'poster over 250KB')

    def test_mobile_derivative_is_smaller_than_desktop(self) -> None:
        self.assertLess(MP4_720.stat().st_size, MP4_1080.stat().st_size)

    def test_derivatives_are_h264_8bit_not_hevc(self) -> None:
        """The master is HEVC Main 10, which Chrome and Firefox cannot decode.

        Read this from the MP4 boxes rather than shelling out to ffprobe. CI
        does not install ffmpeg, and `subprocess.run(['ffprobe', ...])` raises
        FileNotFoundError when the binary is absent — before any return-code
        check can skip it — so the previous version of this test errored on
        every CI run. Parsing the container needs no dependency, which means
        the guarantee is actually enforced in CI instead of skipped there.

        The sample entry names the codec (`avc1` = H.264, `hvc1`/`hev1` =
        HEVC), and the `avcC` configuration box carries AVCProfileIndication
        one byte after its version field: 100 is High (8-bit), 110 is High 10.
        `moov` sits at the front because these files are +faststart, so the
        first 64KB is enough.
        """
        for path in (MP4_1080, MP4_720):
            with self.subTest(asset=path.name):
                head = path.read_bytes()[:65536]
                self.assertIn(b'avc1', head, f'{path.name} is not H.264')
                for hevc in (b'hvc1', b'hev1'):
                    self.assertNotIn(
                        hevc, head, f'{path.name} is HEVC — undecodable in Chrome/Firefox'
                    )
                marker = head.find(b'avcC')
                self.assertNotEqual(marker, -1, f'{path.name} has no avcC configuration box')
                self.assertNotEqual(
                    head[marker + 5], 110, f'{path.name} is High 10 (10-bit) H.264'
                )

    def test_derivatives_are_faststart(self) -> None:
        for path in (MP4_1080, MP4_720):
            with self.subTest(asset=path.name):
                self.assertIn(b'moov', path.read_bytes()[:2048], f'{path.name} not faststart')


class KhalifahFieldSourceContractTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.source = COMPONENT.read_text(encoding='utf-8')
        cls.css = STYLESHEET.read_text(encoding='utf-8')
        cls.code = strip_comments(cls.source)
        cls.css_code = strip_comments(cls.css)

    def test_registered_as_an_island(self) -> None:
        self.assertIn('KhalifahFieldIntelligence,', REGISTRY.read_text(encoding='utf-8'))

    # -- delivery ----------------------------------------------------------

    def test_video_is_not_eagerly_loaded(self) -> None:
        self.assertIn('preload="none"', self.code)
        self.assertIn('playsInline', self.code)
        self.assertIn('{sourcesReady && <source', self.code)

    def test_autoplay_is_muted_only(self) -> None:
        self.assertIn('const [muted, setMuted] = useState(true)', self.code)
        self.assertNotIn('autoPlay', self.code)

    def test_playback_is_visibility_driven_and_pauses_offscreen(self) -> None:
        self.assertIn('IntersectionObserver', self.code)
        self.assertIn('videoRef.current?.pause()', self.code)
        # Section is taller than a viewport; the media frame is the target.
        self.assertIn('const node = mediaRef.current', self.code)

    def test_mobile_uses_the_smaller_derivative(self) -> None:
        self.assertIn("useMediaQuery('(min-width: 768px)')", self.code)
        self.assertIn('wide ? src1080 : src720', self.code)

    def test_media_frame_reserves_its_box_so_nothing_shifts(self) -> None:
        frame = self.css_code[self.css_code.index('.eiq-kfi-media') :]
        self.assertIn('aspect-ratio: 16 / 9', frame[:400])

    # -- the argument ------------------------------------------------------

    def test_stage_bounds_come_from_the_real_cuts(self) -> None:
        self.assertIn('const STAGE_BOUNDS = [0.183, 0.449, 0.833] as const', self.code)

    def test_stages_track_actual_media_progress(self) -> None:
        self.assertIn('video.currentTime / video.duration', self.code)
        self.assertIn('onTimeUpdate', self.code)

    def test_all_four_steps_are_declared(self) -> None:
        for step in STEPS:
            with self.subTest(step=step):
                self.assertIn(f"title: '{step}'", self.code)

    def test_pipeline_echoes_the_hero_spine(self) -> None:
        for node in PIPELINE:
            with self.subTest(node=node):
                self.assertIn(f"'{node}'", self.code)

    def test_steps_are_readable_without_playback(self) -> None:
        """Playback only emphasises; it must never reveal or hide a step."""
        steps_rule = self.css_code[self.css_code.index('.eiq-kfi-steps li') :][:600]
        self.assertNotIn('opacity: 0', steps_rule)
        self.assertNotIn('visibility: hidden', steps_rule)
        self.assertNotIn('display: none', steps_rule)

    # -- conversion discipline ---------------------------------------------

    def test_exactly_one_primary_cta(self) -> None:
        self.assertEqual(self.code.count('eiq-kfi-cta--primary'), 1)
        self.assertIn('>Explore Eco Tours<', self.code.replace('\n', '').replace('  ', ''))

    def test_only_two_links_in_the_section(self) -> None:
        """One primary, one secondary. The old version had six."""
        # Exact class match: `eiq-kfi-cta-row` is a layout wrapper, not a link.
        links = re.findall(r'className="eiq-kfi-cta(?: eiq-kfi-cta--primary)?"', self.code)
        self.assertEqual(len(links), 2, f'expected 2 CTAs, found {len(links)}')

    # -- honesty -----------------------------------------------------------

    def test_no_booking_language_in_the_component(self) -> None:
        for phrase in FORBIDDEN_OPERATIONAL:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, self.code)

    def test_states_the_model_is_in_development(self) -> None:
        self.assertIn('The EcoIQ field model is in development', self.code)
        self.assertIn('Illustrative field experience', self.code)

    def test_no_fabricated_measurements_about_the_location(self) -> None:
        for pattern in (r'\d+\s*%', r'score[:=]\s*\d', r'\d+\s*/\s*100'):
            with self.subTest(pattern=pattern):
                self.assertIsNone(
                    re.search(pattern, self.code, re.IGNORECASE),
                    f'possible fabricated metric matching {pattern}',
                )

    # -- accessibility + locked motion -------------------------------------

    def test_video_has_text_alternative_and_accessible_controls(self) -> None:
        self.assertIn('aria-label="Illustrative Khalifah field experience', self.code)
        self.assertIn('<figcaption', self.code)
        self.assertIn('aria-pressed={!muted}', self.code)
        self.assertIn('type="button"', self.code)

    def test_decorative_marker_is_hidden_from_assistive_tech(self) -> None:
        """Its words are permanent text in the step list, so it must not repeat."""
        marker = self.code[self.code.index('eiq-kfi-marker') :][:300]
        self.assertIn('aria-hidden="true"', marker)

    def test_reduced_motion_stills_transitions_without_hiding_content(self) -> None:
        self.assertIn("useMediaQuery('(prefers-reduced-motion: reduce)')", self.code)
        self.assertIn('if (!reduced && !userPaused.current)', self.code)
        block = self.css_code[self.css_code.index('@media (prefers-reduced-motion: reduce)') :]
        self.assertIn('transition: none !important', block)
        self.assertNotIn('display: none', block)
        self.assertNotIn('opacity: 0', block)

    def test_locked_motion_constraints(self) -> None:
        self.assertNotIn('motion.', self.code)
        self.assertNotIn('domMax', self.code)
        self.assertNotIn('layoutId', self.code)
        self.assertIn('0.18s cubic-bezier(0.22, 1, 0.36, 1)', self.css)
        self.assertIn('0.42s cubic-bezier(0.22, 1, 0.36, 1)', self.css)
        self.assertNotIn('transition: all', self.css_code)

    def test_touch_targets_and_focus_states(self) -> None:
        self.assertIn('min-height: 44px', self.css_code)
        for selector in ('.eiq-kfi-ctrl:focus-visible', '.eiq-kfi-cta:focus-visible'):
            with self.subTest(selector=selector):
                self.assertIn(selector, self.css_code)
        self.assertNotIn('outline: none', self.css_code)

    def test_mobile_stacks_video_above_narrative(self) -> None:
        mobile = self.css_code[self.css_code.index('@media (max-width: 860px)') :]
        self.assertIn('grid-template-columns: 1fr', mobile)

    # -- analytics ---------------------------------------------------------

    def test_analytics_are_vendor_free(self) -> None:
        self.assertIn('ecoiqAnalytics', self.code)
        for event in (
            'khalifah_field_video_started',
            'khalifah_field_video_completed',
            'khalifah_ecotours_clicked',
        ):
            with self.subTest(event=event):
                self.assertIn(event, self.code)
        for vendor in ('gtag', 'dataLayer', 'plausible', 'mixpanel', 'segment'):
            with self.subTest(vendor=vendor):
                self.assertNotIn(vendor, self.code)
