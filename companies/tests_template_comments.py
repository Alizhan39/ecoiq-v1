"""
Regression tests for the "visible Django template comment" defect.

Root cause: Django's template lexer regex ``({%.*?%}|{{.*?}}|{#.*?#})`` is
compiled WITHOUT ``re.DOTALL``, so ``{# ... #}`` only matches single-line
comments. Multi-line ``{# ... #}`` blocks are NOT recognised as comments and
render verbatim. The fix converts multi-line ``{# #}`` blocks to
``{% comment %}...{% endcomment %}`` (which fully strips, multi-line included).

These tests guard against regressions in two ways:
  1. A static scan: no template may contain a multi-line ``{# ... #}`` block.
  2. A render check: the company detail page exposes no developer-note text.
"""
import re
import pathlib

from django.conf import settings
from django.test import SimpleTestCase, TestCase

TEMPLATES_DIR = pathlib.Path(settings.BASE_DIR) / "templates"


class NoMultilineTemplateCommentsTests(SimpleTestCase):
    def test_no_multiline_hash_comments_in_templates(self):
        offenders = []
        for f in TEMPLATES_DIR.rglob("*.html"):
            txt = f.read_text(encoding="utf-8", errors="replace")
            for m in re.finditer(r"\{#(.*?)#\}", txt, flags=re.DOTALL):
                if "\n" in m.group(1):
                    offenders.append(str(f.relative_to(settings.BASE_DIR)))
                    break
        self.assertEqual(
            offenders, [],
            "Multi-line {# #} comments render verbatim in Django (no DOTALL). "
            "Use {% comment %}...{% endcomment %} instead. Offending files:\n"
            + "\n".join(offenders),
        )


class CompanyDetailNoLeakedCommentsTests(TestCase):
    LEAK_MARKERS = [
        "{#", "#}",
        "EcoIQ Improvement Roadmap Panel",
        "Matched Pathways Panel",
        "Financing Intelligence — Readiness",
        "Context variables required",
        "Include in company detail page",
    ]

    def test_company_detail_has_no_leaked_developer_notes(self):
        from companies.models import CompanyProfile
        p = (CompanyProfile.objects
             .filter(status__in=("public", "verified"))
             .select_related("company").first())
        if p is None:
            self.skipTest("No public CompanyProfile available to render")
        resp = self.client.get(f"/companies/{p.company.slug}/", SERVER_NAME="localhost")
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        for marker in self.LEAK_MARKERS:
            self.assertNotIn(marker, html, f"Leaked developer note in rendered page: {marker!r}")
