"""
Regression tests for the homepage critical payload (PR B).

The homepage used to `<link rel=preload as=image>` a 2,592,714-byte lossless PNG
that had no alpha channel — the largest asset on the site, fetched at the highest
possible priority, directly in front of LCP. It is now a responsive AVIF/WebP
<picture> with a JPEG fallback.

These tests pin the properties that would silently undo that, without asserting
byte-perfect HTML:

  - the oversized PNG is not referenced by the page or the built bundle,
  - the preload points at a variant that actually exists on disk,
  - the preload and the <picture> stay in step (same widths, same format),
  - the font request stays on the variable range rather than growing a weight
    list back,
  - the homepage and /healthz/ still return 200.

Deliberately NOT asserted: exact byte sizes of the variants. Re-encoding with a
newer Pillow would change those by a few hundred bytes and fail a test that was
never really about correctness. Order-of-magnitude is asserted instead.
"""
import re
from pathlib import Path

from django.test import TestCase

REPO_ROOT = Path(__file__).resolve().parent.parent
HERO_DIR = REPO_ROOT / 'static' / 'img' / 'hero'

MASTER_PNG = 'ecoiq-better-way-hero.png'
WIDTHS = (768, 1152, 1536)

# The master is kept as the source for future re-encoding, so its size is the
# thing that must never reach a browser again.
MASTER_BYTES = 2_592_714


class HeroVariantFilesTests(TestCase):

    def test_every_variant_exists_and_is_non_empty(self):
        expected = [f'ecoiq-better-way-hero-{w}.{ext}'
                    for w in WIDTHS for ext in ('avif', 'webp')]
        expected.append('ecoiq-better-way-hero-1536.jpg')
        for name in expected:
            with self.subTest(name=name):
                path = HERO_DIR / name
                self.assertTrue(path.exists(), f'{name} missing — run manage.py build_hero_images')
                self.assertGreater(path.stat().st_size, 1024)

    def test_every_variant_is_dramatically_smaller_than_the_master(self):
        """
        The point of the change. A variant creeping back above ~25% of the
        master would mean an encoding setting was lost.
        """
        for path in HERO_DIR.glob('ecoiq-better-way-hero-*.*'):
            with self.subTest(name=path.name):
                self.assertLess(
                    path.stat().st_size, MASTER_BYTES * 0.25,
                    f'{path.name} is no longer meaningfully smaller than the master PNG')

    def test_master_png_is_retained_as_the_source(self):
        """Kept deliberately for future re-encoding — just never served."""
        self.assertTrue((HERO_DIR / MASTER_PNG).exists())


class HomepagePayloadTests(TestCase):

    def setUp(self):
        self.body = self.client.get('/').content.decode()

    def test_homepage_renders(self):
        self.assertEqual(self.client.get('/').status_code, 200)

    def test_homepage_does_not_reference_the_oversized_png(self):
        self.assertNotIn(MASTER_PNG, self.body)

    def test_homepage_preloads_an_avif_not_a_png(self):
        preloads = re.findall(r'<link[^>]*rel="preload"[^>]*>', self.body, re.S)
        self.assertTrue(preloads, 'hero preload disappeared entirely')
        joined = ' '.join(preloads)
        self.assertIn('as="image"', joined)
        self.assertIn('type="image/avif"', joined)
        self.assertIn('imagesrcset', joined)
        self.assertNotIn('.png', joined)

    def test_preloaded_variants_all_exist_on_disk(self):
        """A preload pointing at a missing file is worse than no preload."""
        preloads = re.findall(r'<link[^>]*rel="preload"[^>]*>', self.body, re.S)
        referenced = re.findall(r'/static/img/hero/([\w.-]+\.avif)', ' '.join(preloads))
        self.assertTrue(referenced, 'no AVIF variants found in the preload')
        for name in referenced:
            with self.subTest(name=name):
                self.assertTrue((HERO_DIR / name).exists(), f'preloaded {name} does not exist')

    def test_preload_covers_the_same_widths_as_the_picture_sources(self):
        """
        The preload and the <picture> in heroImage.ts must agree, or the browser
        preloads one variant and then downloads a different one.
        """
        preloads = ' '.join(re.findall(r'<link[^>]*rel="preload"[^>]*>', self.body, re.S))
        for width in WIDTHS:
            with self.subTest(width=width):
                self.assertIn(f'ecoiq-better-way-hero-{width}.avif', preloads)


class FontLoadingTests(TestCase):

    def setUp(self):
        self.body = self.client.get('/').content.decode()

    def test_uses_the_variable_weight_range(self):
        self.assertIn('family=Inter:wght@300..800', self.body)

    def test_does_not_request_a_long_discrete_weight_list(self):
        """
        The old form asked for seven discrete weights, which cost ~15 KB of
        extra @font-face CSS on a render-blocking request for no extra glyphs —
        Google serves Inter as one variable font either way.
        """
        self.assertNotIn('wght@300;400;500;600;700;800;900', self.body)

    def test_does_not_request_weight_900(self):
        """Nothing on the homepage uses 900; asking for it only grows the CSS."""
        match = re.search(r'family=Inter:wght@([^&"]+)', self.body)
        self.assertIsNotNone(match)
        self.assertNotIn('900', match.group(1))

    def test_preconnects_to_the_font_binary_host(self):
        """
        The stylesheet comes from fonts.googleapis.com but the font file from
        fonts.gstatic.com; without this hint that connection is only opened
        after the CSS is parsed.
        """
        self.assertIn('rel="preconnect" href="https://fonts.gstatic.com"', self.body)


class BuiltBundleTests(TestCase):
    """
    static/dist/ecoiq-islands.js is committed and is what production serves —
    build.sh does not run Vite. So the bundle has to be rebuilt when the hero
    components change, and these catch a forgotten rebuild.
    """

    def setUp(self):
        self.bundle = (REPO_ROOT / 'static' / 'dist' / 'ecoiq-islands.js').read_text(
            encoding='utf-8', errors='ignore')

    def test_bundle_no_longer_references_the_png(self):
        self.assertNotIn(MASTER_PNG, self.bundle)

    def test_bundle_declares_both_modern_formats(self):
        self.assertIn('image/avif', self.bundle)
        self.assertIn('image/webp', self.bundle)

    def test_bundle_references_the_hero_variant_basename(self):
        # The widths are concatenated from a constant at runtime, so assert the
        # shared stem and the extensions rather than whole filenames.
        self.assertIn('ecoiq-better-way-hero', self.bundle)
        self.assertIn('.avif', self.bundle)
        self.assertIn('.webp', self.bundle)


class LivenessUnaffectedTests(TestCase):
    def test_healthz_still_returns_ok(self):
        response = self.client.get('/healthz/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'ok')
