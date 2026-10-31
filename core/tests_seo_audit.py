"""
Tests for core/management/commands/seo_audit.py.

Two layers:

  * the checks behave correctly on controlled input — including the two
    false-positive traps that a naive robots.txt reader falls into
  * the audit run against this repository reports the state we actually
    believe it to be in, so a regression in robots/sitemap/metadata fails the
    build rather than being discovered on a shared link

Offline throughout: the command renders through Django's test client and
reads files from disk, and must stay that way.
"""
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

from core.management.commands.seo_audit import (
    ERROR,
    OK,
    WARN,
    _robots_groups,
    run_audit,
)

BASE_DIR = Path(settings.BASE_DIR)


class RobotsGroupParsingTests(SimpleTestCase):
    """Group-awareness is the difference between a useful check and one that
    cries wolf on EcoIQ's deliberate per-bot blocks."""

    def test_rules_attach_to_the_preceding_user_agent(self):
        groups = _robots_groups(
            'User-agent: *\n'
            'Disallow: /admin/\n'
            '\n'
            'User-agent: Bytespider\n'
            'Disallow: /\n'
        )
        self.assertEqual(groups['*'], ['/admin/'])
        self.assertEqual(groups['bytespider'], ['/'])

    def test_consecutive_user_agents_share_one_rule_block(self):
        groups = _robots_groups(
            'User-agent: CCBot\n'
            'User-agent: PetalBot\n'
            'Disallow: /\n'
        )
        self.assertEqual(groups['ccbot'], ['/'])
        self.assertEqual(groups['petalbot'], ['/'])

    def test_comments_and_blank_lines_are_ignored(self):
        groups = _robots_groups(
            '# a comment\n'
            'User-agent: *   # trailing comment\n'
            '\n'
            'Disallow: /x/\n'
        )
        self.assertEqual(groups['*'], ['/x/'])

    def test_empty_disallow_means_allow_everything_and_is_not_a_rule(self):
        groups = _robots_groups('User-agent: *\nDisallow:\n')
        self.assertEqual(groups['*'], [])


class RobotsCheckTests(TestCase):
    """Run against the real templates/robots.txt."""

    def setUp(self):
        self.findings = run_audit()

    def _by_check(self, check):
        return [f for f in self.findings if f.check == check]

    def test_robots_serves_and_declares_a_sitemap(self):
        messages = [f.message for f in self._by_check('robots.txt') if f.level == OK]
        self.assertTrue(any('serves at /robots.txt' in m for m in messages))
        self.assertTrue(any('Sitemap:' in m for m in messages))

    def test_per_bot_blocks_are_not_reported_as_a_site_wide_deindex(self):
        # Bytespider, CCBot and PetalBot each carry `Disallow: /` in their own
        # group. That is deliberate. Flagging it would be a false positive.
        errors = [f for f in self._by_check('robots.txt') if f.level == ERROR]
        self.assertEqual(
            errors, [],
            f'per-bot blocks were misread as a site-wide de-index: '
            f'{[e.message for e in errors]}',
        )

    def test_fully_blocked_bots_are_still_reported_as_evidence(self):
        finding = next(
            f for f in self._by_check('robots.txt')
            if 'wildcard group' in f.message
        )
        self.assertIn('bytespider', finding.evidence)


class SitemapCheckTests(TestCase):

    def test_sitemap_serves_and_every_static_page_name_resolves(self):
        findings = [f for f in run_audit() if f.check == 'sitemap.xml']
        self.assertTrue(findings)
        errors = [f for f in findings if f.level == ERROR]
        self.assertEqual(
            errors, [],
            f'sitemap problems: {[e.message for e in errors]}',
        )

    def test_no_sitemap_url_is_blocked_by_the_wildcard_robots_group(self):
        findings = [f for f in run_audit() if f.check == 'robots vs sitemap']
        self.assertTrue(findings)
        self.assertEqual([f for f in findings if f.level == ERROR], [])


class HeadMetadataTests(TestCase):

    def test_all_required_head_tags_are_present(self):
        errors = [
            f for f in run_audit()
            if f.check == 'head metadata' and f.level == ERROR
        ]
        self.assertEqual(errors, [], f'missing head tags: {[e.message for e in errors]}')

    def test_missing_twitter_card_is_reported_as_a_warning(self):
        # A known, accepted gap. If someone adds twitter:card, this test fails
        # and should simply be deleted along with the warning.
        warnings = [
            f for f in run_audit()
            if f.check == 'head metadata' and f.level == WARN
        ]
        self.assertTrue(any('twitter:card' in f.message for f in warnings))


class CanonicalAndHreflangTests(TestCase):

    def test_single_canonical_host(self):
        findings = [f for f in run_audit() if f.check == 'canonical']
        self.assertTrue(findings)
        self.assertEqual([f for f in findings if f.level == ERROR], [])

    def test_hreflang_absence_is_correct_for_a_single_language_site(self):
        # The check is two-sided: it must also fail if languages are enabled
        # without hreflang. Assert the current, correct state.
        self.assertEqual([code for code, _ in settings.LANGUAGES], ['en'])
        findings = [f for f in run_audit() if f.check == 'hreflang']
        self.assertEqual([f.level for f in findings], [OK])


class StaticAssetReferenceTests(TestCase):
    """The check that found the live og:image bug."""

    def test_absolute_static_references_are_checked_against_disk(self):
        findings = [f for f in run_audit() if f.check == 'static asset']
        self.assertTrue(findings, 'the absolute-static-URL check produced nothing')

    def test_the_known_missing_og_image_is_reported(self):
        # templates/base.html and templates/contact.html both point at
        # /static/brand/ecoiq-og.png, which does not exist, so no social
        # preview renders anywhere. Documented in docs/ECOIQ-ENGINEERING-OS.md
        # §6 as a brand-asset decision. When the PNG is added this test fails
        # and should be inverted to assert the file exists.
        self.assertFalse(
            (BASE_DIR / 'static' / 'brand' / 'ecoiq-og.png').exists(),
            'ecoiq-og.png now exists — invert this test and clear the finding',
        )
        errors = [
            f for f in run_audit()
            if f.check == 'static asset' and f.level == ERROR
        ]
        self.assertTrue(any('ecoiq-og.png' in f.message for f in errors))


class CommandInterfaceTests(TestCase):

    def test_command_runs_without_strict(self):
        call_command('seo_audit')

    def test_explain_lists_what_cannot_be_checked_offline(self):
        from core.management.commands.seo_audit import NOT_CHECKED
        self.assertTrue(NOT_CHECKED)
        for line in NOT_CHECKED:
            self.assertTrue(line.strip().endswith('.'))

    def test_audit_makes_no_outbound_network_call(self):
        source = (
            BASE_DIR / 'core' / 'management' / 'commands' / 'seo_audit.py'
        ).read_text()
        for forbidden in ('requests.get', 'httpx.', 'urlopen', 'socket.'):
            self.assertNotIn(forbidden, source)
