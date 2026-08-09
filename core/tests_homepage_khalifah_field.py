"""Focused tests for the homepage Khalifah Field Intelligence section.

Layered the same way as the Product Architecture tests, and for the same
reason — the section is a React island and this repo has no JS test runner:

* **Rendered-HTML tests** cover what Django owns: the island is mounted with
  lazy loading, its video/poster/route props resolve server-side, and the no-JS
  fallback still carries the proposition and all three destinations.

* **Asset tests** check the actual encoded derivatives exist, are the sizes and
  codecs we intend, and are `+faststart` so playback can begin before the file
  finishes downloading.

* **Source-contract tests** pin the things that only exist at runtime: lazy
  video attachment, the four-stage sequence, reduced-motion completeness,
  the locked motion constraints, and — most importantly — the *operational
  honesty* rules. Khalifah Eco Tours is not confirmed operational, so
  "Book"/"Reserve"/"Available dates"/"Next departure" must not appear, and the
  Field Passport must never show an invented count.
"""

from __future__ import annotations

import re
import subprocess
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

def strip_comments(source: str) -> str:
    """Drop comments so scans test shipped code, not prose about the rules.

    These files deliberately *document* the forbidden strings — "no Book,
    Reserve, ..." — so a naive substring scan flags the documentation and
    passes the actual markup. Comments are removed first; what remains is what
    reaches the user.
    """
    source = re.sub(r'/\*.*?\*/', '', source, flags=re.DOTALL)   # /* block */ and JSDoc
    source = re.sub(r'^\s*//.*$', '', source, flags=re.MULTILINE)  # // line
    return source


def strip_html_comments(html: str) -> str:
    return re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)


#: Language that would assert an operating tour business. None of it may ship.
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


class KhalifahFieldRenderTests(TestCase):
    def setUp(self) -> None:
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.html = response.content.decode('utf-8')

    def test_section_island_is_mounted(self) -> None:
        self.assertIn('data-island="KhalifahFieldIntelligence"', self.html)

    def test_island_is_lazy_so_the_video_cannot_load_eagerly(self) -> None:
        marker = self.html.index('data-island="KhalifahFieldIntelligence"')
        tag = self.html[marker : marker + 260]
        self.assertIn('data-island-lazy', tag)

    def test_video_derivatives_and_poster_are_wired_from_static(self) -> None:
        self.assertIn('/static/video/khalifah-field-1080.mp4', self.html)
        self.assertIn('/static/video/khalifah-field-720.mp4', self.html)
        self.assertIn('/static/video/khalifah-field-poster.jpg', self.html)

    def test_cta_destinations_resolve_server_side(self) -> None:
        self.assertIn('"toursHref": "/khalifa-tours/"', self.html)
        self.assertIn('"intelligenceHref": "/platform/"', self.html)
        self.assertIn('"projectsHref": "/projects/"', self.html)
        self.assertIn('"stewardshipHref": "/stewardship/"', self.html)

    def test_all_cta_destinations_actually_resolve(self) -> None:
        for path in ('/khalifa-tours/', '/platform/', '/projects/', '/stewardship/'):
            with self.subTest(path=path):
                self.assertIn(self.client.get(path).status_code, (200, 301, 302))

    def test_nojs_fallback_carries_proposition_and_three_paths(self) -> None:
        start = self.html.index('eiq-kfi-nojs')
        block = self.html[start : start + 2600]
        self.assertIn('See what the data cannot show alone.', block)
        self.assertIn('/khalifa-tours/', block)
        self.assertIn('/platform/', block)
        self.assertIn('/projects/', block)
        self.assertIn('Illustrative field experience', block)

    def test_operational_disclaimer_is_present(self) -> None:
        self.assertIn('Illustrative field experience', self.html)

    def test_no_booking_language_anywhere_on_the_homepage(self) -> None:
        visible = strip_html_comments(self.html)
        for phrase in FORBIDDEN_OPERATIONAL:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, visible)

    def test_section_sits_below_the_commercial_core(self) -> None:
        """It is a differentiation layer, never above hero or Product Architecture."""
        hero = self.html.index('id="eiq-hero-title"')
        product = self.html.index('data-island="ProductArchitecture"')
        khalifah = self.html.index('data-island="KhalifahFieldIntelligence"')
        self.assertLess(hero, khalifah)
        self.assertLess(product, khalifah)


class KhalifahFieldAssetTests(SimpleTestCase):
    """The encoded derivatives, not the 4K HEVC master."""

    def test_derivatives_and_poster_exist(self) -> None:
        for path in (MP4_1080, MP4_720, POSTER):
            with self.subTest(asset=path.name):
                self.assertTrue(path.exists(), f'{path.name} is missing')

    def test_derivatives_are_web_deliverable_sizes(self) -> None:
        """The 32.4MB HEVC master must never be what ships."""
        self.assertLess(MP4_1080.stat().st_size, 10 * 1024 * 1024, '1080p over 10MB')
        self.assertLess(MP4_720.stat().st_size, 6 * 1024 * 1024, '720p over 6MB')
        self.assertLess(POSTER.stat().st_size, 250 * 1024, 'poster over 250KB')

    def test_mobile_derivative_is_smaller_than_desktop(self) -> None:
        self.assertLess(MP4_720.stat().st_size, MP4_1080.stat().st_size)

    def test_derivatives_are_h264_not_hevc(self) -> None:
        """HEVC does not decode in Chrome or Firefox; the master is HEVC."""
        for path in (MP4_1080, MP4_720):
            with self.subTest(asset=path.name):
                probe = subprocess.run(
                    ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                     '-show_entries', 'stream=codec_name,width,height,pix_fmt',
                     '-of', 'default=noprint_wrappers=1', str(path)],
                    capture_output=True, text=True, check=False,
                )
                if probe.returncode != 0:
                    self.skipTest('ffprobe unavailable')
                self.assertIn('codec_name=h264', probe.stdout)
                # 8-bit: 10-bit H.264 is not broadly decodable.
                self.assertIn('pix_fmt=yuv420p', probe.stdout)

    def test_derivatives_are_faststart(self) -> None:
        """moov before mdat, or playback waits for the whole file."""
        for path in (MP4_1080, MP4_720):
            with self.subTest(asset=path.name):
                head = path.read_bytes()[:2048]
                self.assertIn(b'moov', head, f'{path.name} is not +faststart')


class KhalifahFieldSourceContractTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.source = COMPONENT.read_text(encoding='utf-8')
        cls.css = STYLESHEET.read_text(encoding='utf-8')
        #: Comment-free views, for scans that must not match documentation.
        cls.code = strip_comments(cls.source)
        cls.css_code = strip_comments(cls.css)

    def test_registered_as_an_island(self) -> None:
        registry = REGISTRY.read_text(encoding='utf-8')
        self.assertIn('KhalifahFieldIntelligence,', registry)

    # -- delivery ----------------------------------------------------------

    def test_video_is_not_eagerly_loaded(self) -> None:
        self.assertIn('preload="none"', self.source)
        self.assertIn('playsInline', self.source)
        # <source> only rendered once the media has been near the viewport.
        self.assertIn('{sourcesReady && <source', self.source)

    def test_autoplay_is_muted_only(self) -> None:
        self.assertIn('const [muted, setMuted] = useState(true)', self.source)
        self.assertNotIn('autoPlay', self.source)

    def test_playback_is_visibility_driven_and_pauses_offscreen(self) -> None:
        self.assertIn('IntersectionObserver', self.source)
        self.assertIn('videoRef.current?.pause()', self.source)

    def test_observer_targets_the_media_not_the_section(self) -> None:
        """A section taller than the viewport can never reach the threshold."""
        self.assertIn('const node = mediaRef.current', self.source)

    def test_mobile_uses_the_smaller_derivative(self) -> None:
        self.assertIn("useMediaQuery('(min-width: 768px)')", self.source)
        self.assertIn('wide ? src1080 : src720', self.source)

    # -- the four-stage argument -------------------------------------------

    def test_stage_bounds_are_derived_from_the_real_cuts(self) -> None:
        self.assertIn('const STAGE_BOUNDS = [0.183, 0.449, 0.833] as const', self.source)
        self.assertIn("const STAGE_IDS = ['human', 'lens', 'brief', 'action'] as const", self.source)

    def test_stages_are_driven_by_actual_media_progress(self) -> None:
        self.assertIn('video.currentTime / video.duration', self.source)
        self.assertIn('onTimeUpdate', self.source)

    def test_each_stage_has_a_rendered_panel(self) -> None:
        for panel in ('human', 'lens', 'brief', 'action'):
            with self.subTest(panel=panel):
                self.assertIn(f'data-panel="{panel}"', self.source)
                self.assertIn(f"data-stage='{panel}'", self.css)

    def test_action_stage_offers_the_four_actions(self) -> None:
        for action in ('Protect', 'Restore', 'Finance', 'Experience'):
            with self.subTest(action=action):
                self.assertIn(f"label: '{action}'", self.source)

    # -- audience modes ----------------------------------------------------

    def test_four_audiences_with_distinct_headlines(self) -> None:
        for audience in ('traveller', 'student', 'investor', 'delegation'):
            with self.subTest(audience=audience):
                self.assertIn(f"id: '{audience}'", self.source)
        for headline in (
            'Experience nature with context.',
            'Turn the landscape into a living classroom.',
            'See projects and places beyond the spreadsheet.',
            'Understand transition challenges on the ground.',
        ):
            with self.subTest(headline=headline):
                self.assertIn(headline, self.source)

    def test_audience_switch_is_a_keyboard_operable_tablist(self) -> None:
        self.assertIn("role=\"tablist\"", self.source)
        self.assertIn("role=\"tab\"", self.source)
        self.assertIn('aria-selected={audience === option.id}', self.source)
        self.assertIn("event.key === 'ArrowRight'", self.source)

    # -- honesty -----------------------------------------------------------

    def test_no_booking_language_in_the_component(self) -> None:
        for phrase in FORBIDDEN_OPERATIONAL:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, self.code)

    def test_lens_and_brief_are_labelled_illustrative(self) -> None:
        self.assertIn('Illustrative EcoIQ lens', self.source)
        self.assertIn('Illustrative field experience', self.source)
        self.assertIn('not a claim about the footage', self.source)

    def test_no_fabricated_measurements_about_the_location(self) -> None:
        """No score, percentage or fabricated ecological finding may appear."""
        for pattern in (r'\d+\s*%', r'score[:=]\s*\d', r'\d+\s*/\s*100'):
            with self.subTest(pattern=pattern):
                self.assertIsNone(
                    re.search(pattern, self.code, re.IGNORECASE),
                    f'possible fabricated metric matching {pattern}',
                )

    def test_field_passport_is_a_labelled_concept_with_no_counts(self) -> None:
        self.assertIn('Concept preview', self.source)
        passport = self.source[self.source.index('PASSPORT_ROWS') :]
        passport = passport[: passport.index(']')]
        # Rows are labels only — any digit here would be an invented total.
        self.assertIsNone(re.search(r'\d', passport))
        self.assertIn("aria-label=\"not yet recorded\"", self.source)

    # -- accessibility + locked motion -------------------------------------

    def test_video_has_a_text_alternative_and_controls(self) -> None:
        self.assertIn('aria-label="Illustrative Khalifah field experience footage', self.source)
        self.assertIn('<figcaption', self.source)
        self.assertIn('aria-pressed={!muted}', self.source)

    def test_reduced_motion_shows_every_stage_complete(self) -> None:
        self.assertIn("const stageAttr = reduced ? 'all' : stage", self.source)
        self.assertIn("useMediaQuery('(prefers-reduced-motion: reduce)')", self.source)
        self.assertIn("data-stage='all'", self.css)
        block = self.css[self.css.index(".eiq-kfi[data-stage='all'] .eiq-kfi-stages") :]
        self.assertIn('flex-direction: column', block)
        self.assertIn('opacity: 1', block)
        self.assertNotIn('display: none;\n}', block.split('.eiq-kfi-progress')[0])

    def test_reduced_motion_does_not_autoplay(self) -> None:
        self.assertIn('if (!reduced && !userPaused.current)', self.source)

    def test_locked_motion_constraints(self) -> None:
        self.assertNotIn('motion.', self.code)
        self.assertNotIn('domMax', self.code)
        self.assertNotIn('layoutId', self.code)
        self.assertIn('0.18s cubic-bezier(0.22, 1, 0.36, 1)', self.css)
        self.assertIn('0.42s cubic-bezier(0.22, 1, 0.36, 1)', self.css)
        self.assertNotIn('transition: all', self.css_code)

    def test_touch_targets_and_focus_states(self) -> None:
        self.assertIn('min-height: 44px', self.css)
        for selector in (
            '.eiq-kfi-aud-btn:focus-visible',
            '.eiq-kfi-ctrl:focus-visible',
            '.eiq-kfi-cta:focus-visible',
        ):
            with self.subTest(selector=selector):
                self.assertIn(selector, self.css)
        self.assertNotIn('outline: none', self.css)

    def test_mobile_stacks_rather_than_overlaying_the_footage(self) -> None:
        mobile = self.css[self.css.index('@media (max-width: 860px)') :]
        self.assertIn('grid-template-columns: 1fr', mobile)

    # -- analytics ---------------------------------------------------------

    def test_analytics_are_vendor_free_and_carry_no_pii(self) -> None:
        self.assertIn('ecoiqAnalytics', self.source)
        for event in (
            'khalifah_field_video_started',
            'khalifah_field_video_completed',
            'khalifah_audience_selected',
            'khalifah_ecotours_clicked',
            'khalifah_intelligence_clicked',
            'khalifah_projects_clicked',
        ):
            with self.subTest(event=event):
                self.assertIn(event, self.source)
        # No third-party collector may be introduced.
        for vendor in ('gtag', 'dataLayer', 'plausible', 'mixpanel', 'segment'):
            with self.subTest(vendor=vendor):
                self.assertNotIn(vendor, self.code)
