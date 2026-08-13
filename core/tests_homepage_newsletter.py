"""Focused tests for the homepage newsletter invitation.

The newsletter was a conversion defect, not a cosmetic one: a 320px fixed
panel on a 30-second timer with no mobile handling, observed covering the
Product Architecture, Khalifah and Impact Engine CTAs across several
iterations. It is now a collapsed pill that only becomes eligible once the
visitor has scrolled past the entire commercial core, and only expands when
they click it.

These tests pin the rules that keep it subordinate. The geometric proof that
it never overlaps a CTA is a browser measurement (boundingClientRect
intersection across the full scroll, at 1440x900 and 390x844) and is recorded
in the PR rather than here — Django cannot measure layout.
"""

from __future__ import annotations

import re

from django.test import TestCase

#: Every CTA that must never be covered.
CRITICAL_CTAS = (
    '/request-access/review/',
    '/request-access/enterprise/',
    '/khalifa-tours/',
    '/platform/',
)


class NewsletterPresentationTests(TestCase):
    def setUp(self) -> None:
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.html = response.content.decode('utf-8')

    # -- it must not open on its own ---------------------------------------

    def test_starts_hidden(self) -> None:
        self.assertIn('id="newsletter-invite"', self.html)
        marker = self.html.index('id="newsletter-invite"')
        self.assertIn('data-state="hidden"', self.html[marker : marker + 120])

    def test_no_timer_trigger(self) -> None:
        """The old behaviour was setTimeout(showNewsletter, 30000)."""
        self.assertNotIn('setTimeout(showNewsletter', self.html)
        self.assertNotIn('30000', self.html)

    def test_eligibility_is_engagement_based(self) -> None:
        """A sentinel after the commercial core gates the invitation."""
        self.assertIn('id="newsletter-sentinel"', self.html)
        self.assertIn('checkEligibility', self.html)
        sentinel = self.html.index('id="newsletter-sentinel"')
        for island in ('DecisionBrief', 'Outcomes', 'HowEcoIQWorks', 'KhalifahFieldIntelligence'):
            with self.subTest(section=island):
                self.assertLess(
                    self.html.index(f'data-island="{island}"'),
                    sentinel,
                    f'{island} must come before the newsletter becomes eligible',
                )

    def test_panel_is_closed_until_the_visitor_opens_it(self) -> None:
        panel = self.html[self.html.index('id="newsletter-panel"') :][:200]
        self.assertIn('hidden', panel)
        toggle = self.html[self.html.index('id="newsletter-toggle"') :][:200]
        self.assertIn('aria-expanded="false"', toggle)

    # -- dismissal ---------------------------------------------------------

    def test_dismissal_persists_with_an_expiry(self) -> None:
        """Stored as a timestamp so it lapses rather than lasting forever."""
        self.assertIn('ecoiq_newsletter_dismissed_at', self.html)
        self.assertIn('THIRTY_DAYS', self.html)
        self.assertIn('30 * 24 * 60 * 60 * 1000', self.html)

    def test_dismissal_is_guarded_against_private_mode(self) -> None:
        """localStorage throws in some privacy modes; it must not break the page."""
        self.assertIn('catch (err) { /* private mode */ }', self.html)

    # -- accessibility -----------------------------------------------------

    def test_controls_are_semantic_and_labelled(self) -> None:
        self.assertIn('aria-label="Dismiss newsletter invitation"', self.html)
        self.assertIn('aria-controls="newsletter-panel"', self.html)
        self.assertIn('<label class="eiq-nl-sr" for="newsletter-email">', self.html)
        # No inline onclick handlers left from the old implementation.
        self.assertNotIn('onclick="dismissNewsletter()"', self.html)

    def test_escape_collapses_without_trapping_focus(self) -> None:
        self.assertIn("e.key === 'Escape'", self.html)
        # Non-modal: it must not claim dialog semantics it does not implement.
        invite = self.html[self.html.index('id="newsletter-invite"') :][:400]
        self.assertNotIn('role="dialog"', invite)
        self.assertNotIn('aria-modal', invite)

    def test_does_not_steal_focus(self) -> None:
        block = self.html[self.html.index('id="newsletter-invite"') :]
        block = block[: block.index('</script>')]
        self.assertNotIn('newsletter-email\').focus()', block)
        self.assertNotIn('autofocus', block)

    def test_status_is_announced_politely(self) -> None:
        self.assertIn('role="status"', self.html)
        self.assertIn('aria-live="polite"', self.html)

    # -- it stays subordinate ---------------------------------------------

    def test_z_index_is_below_a_takeover_layer(self) -> None:
        """The old panel sat at 9999. It is now a modest layer."""
        self.assertNotIn('z-index:9999', self.html.replace(' ', ''))
        self.assertIn('z-index: 60', self.html)

    def test_mobile_rule_keeps_it_slim(self) -> None:
        self.assertIn('@media (max-width: 640px)', self.html)

    # -- the product it serves is unchanged --------------------------------

    def test_submission_endpoint_and_csrf_are_intact(self) -> None:
        self.assertIn("fetch('/newsletter/signup/'", self.html)
        self.assertIn("'X-CSRFToken'", self.html)
        self.assertIn('csrfmiddlewaretoken', self.html)

    def test_signup_endpoint_still_exists(self) -> None:
        response = self.client.post(
            '/newsletter/signup/',
            data='{"email": "test@example.com"}',
            content_type='application/json',
        )
        self.assertIn(response.status_code, (200, 400, 403))

    def test_critical_ctas_all_still_present(self) -> None:
        """Whatever the newsletter does, the commercial paths remain."""
        for cta in CRITICAL_CTAS:
            with self.subTest(cta=cta):
                self.assertIn(cta, self.html)

    def test_old_popup_markup_is_gone(self) -> None:
        self.assertNotIn('id="newsletter-popup"', self.html)
        self.assertIsNone(re.search(r'width:\s*320px', self.html))
