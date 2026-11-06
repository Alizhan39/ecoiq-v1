"""Compatibility smoke for the two PDF libraries pinned by EcoIQ.

A security update must not silently turn valid HTML exports into invalid PDFs.
This intentionally generates synthetic content and does not touch customer data,
external URLs, production storage, or live payment flows.
"""

from io import BytesIO

from django.test import SimpleTestCase
from pypdf import PdfReader
from weasyprint import HTML


class PDFDependencyCompatibilityTests(SimpleTestCase):
    def test_html_to_pdf_roundtrip_remains_readable(self):
        rendered = HTML(string=(
            "<!doctype html><html><body>"
            "<h1>EcoIQ Safety Report</h1>"
            "<p>Evidence status: review required.</p>"
            "<table><tr><th>KPI</th><th>Value</th></tr>"
            "<tr><td>Coverage</td><td>Unknown</td></tr></table>"
            "</body></html>"
        )).write_pdf()

        self.assertIsInstance(rendered, bytes)
        self.assertTrue(rendered.startswith(b"%PDF-"))

        reader = PdfReader(BytesIO(rendered))
        self.assertGreaterEqual(len(reader.pages), 1)
        extracted = reader.pages[0].extract_text()
        self.assertIn("EcoIQ Safety Report", extracted)
        self.assertIn("Unknown", extracted)
