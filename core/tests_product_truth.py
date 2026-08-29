"""
Product truth sweep — claims that must not reappear in user-facing copy.

These are not style rules. Each one was found in shipped templates:

  base.html promised "company rankings, ESG scores" in the og:description --
  the copy that appears whenever ANY page is shared -- while no organisation
  in the estate has a publishable score.

  press.html carried "219+ companies · 25+ countries" as a hand-maintained
  fact. It was stale (the estate holds 467 rows) and it counted TABLE ROWS,
  which is not a measure of anything assessed.

A claim in a meta tag is still a claim. It is often the only one a reader sees.
"""
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

TEMPLATES = Path(settings.BASE_DIR) / 'templates'


def _read(name: str) -> str:
    return (TEMPLATES / name).read_text(encoding='utf-8', errors='ignore')


class SharedSocialCopy(SimpleTestCase):
    """base.html is the widest-reach copy in the product."""

    def test_it_does_not_promise_rankings(self):
        source = _read('base.html')
        og = [line for line in source.splitlines() if 'og:description' in line]

        self.assertTrue(og)
        for line in og:
            with self.subTest(line=line):
                self.assertNotIn('company rankings', line.lower())

    def test_it_does_not_promise_esg_scores(self):
        for line in _read('base.html').splitlines():
            if 'og:description' in line:
                with self.subTest(line=line):
                    self.assertNotIn('esg scores', line.lower())

    def test_it_describes_what_the_product_actually_does(self):
        self.assertIn('Evidence-backed decision intelligence', _read('base.html'))

    def test_no_page_override_promises_scores_unconditionally(self):
        """
        base.html is only the DEFAULT. A page that overrides og_description
        can reintroduce the claim, and about.html did -- "EcoIQ scores
        companies globally", with no evidence condition attached.
        """
        import re

        offenders = []
        for path in TEMPLATES.rglob('*.html'):
            text = path.read_text(encoding='utf-8', errors='ignore')
            for match in re.finditer(
                    r'{%\s*block og_description\s*%}(.*?){%\s*endblock', text, re.S):
                body = match.group(1).lower()
                if 'scores companies' in body and 'evidence' not in body:
                    offenders.append(path.name)

        self.assertEqual(offenders, [],
                         f'unconditional score claim in meta: {offenders}')


class PressKit(SimpleTestCase):

    def test_it_carries_no_hand_maintained_company_count(self):
        """
        A count in copy drifts silently, which makes a stale figure
        indistinguishable from an invented one.
        """
        import re

        # Strip {% comment %} blocks: the historical figure is quoted inside
        # one, explaining what it was and why it went. The test must read what
        # RENDERS, not the note about what used to.
        body = re.sub(r'{%\s*comment\s*%}.*?{%\s*endcomment\s*%}', '',
                      _read('press.html'), flags=re.S)

        self.assertNotIn('219+ companies', body)
        self.assertNotIn('25+ countries', body)

    def test_the_boilerplate_states_the_evidence_condition(self):
        source = _read('press.html')

        self.assertIn('only where the underlying evidence supports one', source)

    def test_the_boilerplate_does_not_claim_it_scores_every_company(self):
        source = _read('press.html')

        self.assertNotIn(
            'platform that scores companies on climate transition readiness',
            source)


class ForbiddenClaims(SimpleTestCase):
    """
    Scanned across every template. Each phrase is one the canonical registry
    and the evaluation framework do not support.
    """

    FORBIDDEN = (
        '33 operational agents',
        '33 agents',
        '467 companies',
        '400 companies',
        'SOC 2 certified',
        'ISO certified',
        'GDPR certified',
    )

    def _templates(self):
        return [p for p in TEMPLATES.rglob('*.html')]

    def test_no_template_makes_a_forbidden_claim(self):
        offenders = []
        for path in self._templates():
            text = path.read_text(encoding='utf-8', errors='ignore').lower()
            for phrase in self.FORBIDDEN:
                if phrase.lower() in text:
                    offenders.append(f'{path.name}: {phrase}')

        self.assertEqual(offenders, [], f'unsupported claims found: {offenders}')

    def test_the_scan_covers_a_real_number_of_templates(self):
        """Guards the guard: a scan over zero files passes trivially."""
        self.assertGreater(len(self._templates()), 100)


class ReactSourceClaims(SimpleTestCase):
    """
    The same sweep, extended to the surface that now carries most of the copy.

    ForbiddenClaims above scans `templates/`, which was the whole product when
    it was written. It is not any more: the public pages are React, and a claim
    typed into a .tsx file is exactly as published as one typed into a .html
    file — and was, until this class existed, entirely unscanned.

    AFFIRMATIVE PATTERNS, NOT SUBSTRINGS
    ------------------------------------
    Unlike the template sweep, this one has to distinguish a claim from its
    denial. `TrustCenter.tsx` says "not SOC 2 audited" and "no such thing as
    GDPR certification"; those sentences are the reason the page can be
    trusted, and a substring ban on "SOC 2" would delete them. So each pattern
    below matches the assertion and not the negation, the same discipline
    TrustCenter.test.tsx already applies to that one page.
    """

    SRC = Path(settings.BASE_DIR) / 'frontend' / 'web' / 'src'

    #: Each is an affirmative credential claim. None has a truthful form.
    CLAIMS = (
        r'\bis (SOC 2|ISO ?27001|Cyber Essentials) certified\b',
        r'\bwe are (SOC|ISO|GDPR|Cyber Essentials)\b',
        r'\bcertified to ISO\b',
        r'\bfully compliant\b',
        r'\bgovernment[- ]approved\b',
        r'\bframework supplier\b',
        r'\bapproved supplier\b',
        r'\bon (the )?G-Cloud\b',
        # Counters that drift. The template sweep bans the literal figures;
        # here the shape is banned, because the SSOT in platform_registry is
        # the only thing allowed to produce one.
        r'\b33 (operational )?agents\b',
        r'\b467 companies\b',
    )

    def _sources(self):
        """Every non-test source file. Tests hold these patterns on purpose."""
        return [path for path in self.SRC.rglob('*.ts*')
                if '.test.' not in path.name]

    def test_the_scan_covers_a_real_number_of_files(self):
        """Guards the guard: a scan over zero files passes trivially."""
        self.assertGreater(len(self._sources()), 40)

    def test_no_source_file_makes_an_affirmative_credential_claim(self):
        import re

        offenders = []
        for path in self._sources():
            text = path.read_text(encoding='utf-8', errors='ignore')
            for pattern in self.CLAIMS:
                if re.search(pattern, text, re.IGNORECASE):
                    offenders.append(f'{path.name}: {pattern}')

        self.assertEqual(offenders, [],
                         f'unsupported claims in React source: {offenders}')

    def test_the_denials_that_justify_the_pattern_style_still_render(self):
        """
        If TrustCenter stopped denying its certifications, the affirmative-only
        patterns above would be needlessly permissive — and nobody would notice.
        """
        trust = (self.SRC / 'pages' / 'TrustCenter.tsx') \
            .read_text(encoding='utf-8')

        self.assertIn('not SOC 2 audited', trust)
        self.assertIn('no such thing as GDPR certification', trust)
