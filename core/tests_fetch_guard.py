"""
Tests that the three remaining externally-supplied fetch sites stay behind the
shared, SSRF-validating client.

The SSRF rules themselves live in company_intelligence.services.url_safety and
are tested there and in backend_intelligence_engine.tests_ssrf. Nothing is
re-tested here. What these assert is the property that actually regressed
before: a call site quietly going back to `requests.get(...)` and bypassing the
guard entirely, which no amount of coverage on the validator would catch.

`ingestion/pipeline.py` is the one that mattered. Its URL arrives from
`request.POST['url']`, and it previously called
`requests.get(..., allow_redirects=True)` with no destination check — so a
permitted host answering `302 Location: http://169.254.169.254/…` reached the
cloud metadata service and the response body was stored as evidence.
"""
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.test import SimpleTestCase

from backend_intelligence_engine.services.http_client import HTTPFetchResult

BASE_DIR = Path(settings.BASE_DIR)

GUARDED_CALL_SITES = (
    'ingestion/pipeline.py',
    'intelligence/compute.py',
    'companies/management/commands/extract_pdf_kpis.py',
)


class NoDirectFetchTests(SimpleTestCase):
    """No guarded call site may reach the network on its own."""

    def _calls(self, relative):
        """Every call expression in the module, as AST nodes.

        Parsed rather than grepped on purpose: a docstring that *describes* the
        old `requests.get(..., allow_redirects=True)` is not a call to it, and
        a test that cannot tell the difference would forbid explaining the bug
        it exists to prevent.
        """
        import ast

        tree = ast.parse((BASE_DIR / relative).read_text())
        return [n for n in ast.walk(tree) if isinstance(n, ast.Call)]

    def _dotted(self, node):
        import ast

        parts = []
        while isinstance(node, ast.Attribute):
            parts.append(node.attr)
            node = node.value
        if isinstance(node, ast.Name):
            parts.append(node.id)
        return '.'.join(reversed(parts))

    def test_no_guarded_call_site_calls_requests_or_httpx_directly(self):
        forbidden = {
            'requests.get', 'requests.post', 'requests.request',
            'http_requests.get', 'http_requests.post',
            'httpx.get', 'httpx.post', 'httpx.request',
            'urlopen', 'urllib.request.urlopen',
        }
        for relative in GUARDED_CALL_SITES:
            with self.subTest(path=relative):
                for call in self._calls(relative):
                    name = self._dotted(call.func)
                    self.assertNotIn(
                        name, forbidden,
                        f'{relative} calls {name}() instead of the shared '
                        'SSRF-validating client',
                    )

    def test_every_guarded_call_site_imports_the_shared_client(self):
        for relative in GUARDED_CALL_SITES:
            with self.subTest(path=relative):
                source = (BASE_DIR / relative).read_text()
                self.assertIn(
                    'http_client', source,
                    f'{relative} does not use backend_intelligence_engine http_client',
                )

    def test_allow_redirects_is_never_re_enabled_at_a_call_site(self):
        # The shared client follows redirects one hop at a time, validating
        # each. A call site passing allow_redirects/follow_redirects=True would
        # hand the chain back to the library and undo that.
        import ast

        for relative in GUARDED_CALL_SITES:
            with self.subTest(path=relative):
                for call in self._calls(relative):
                    for kw in call.keywords:
                        if kw.arg in ('allow_redirects', 'follow_redirects'):
                            self.assertNotEqual(
                                getattr(kw.value, 'value', None), True,
                                f'{relative} re-enables library redirect following',
                            )


class IngestionFetchTests(SimpleTestCase):
    """The highest-risk path: a staff-submitted URL from request.POST."""

    def test_a_refused_destination_returns_none_rather_than_bytes(self):
        from ingestion import pipeline

        refused = HTTPFetchResult(
            success=False,
            error="URLNotPermitted('blocked_destination', ...)",
        )
        with patch.object(pipeline.http_client, 'fetch', return_value=refused) as mock_fetch:
            self.assertIsNone(pipeline._fetch_url('http://169.254.169.254/latest/meta-data/'))
        mock_fetch.assert_called_once()

    def test_a_successful_public_fetch_still_returns_bytes(self):
        from ingestion import pipeline

        ok = HTTPFetchResult(success=True, status_code=200, content=b'<html>ok</html>')
        with patch.object(pipeline.http_client, 'fetch', return_value=ok):
            self.assertEqual(pipeline._fetch_url('https://example.com/'), b'<html>ok</html>')

    def test_a_non_200_response_is_not_treated_as_content(self):
        from ingestion import pipeline

        not_found = HTTPFetchResult(success=True, status_code=404, content=b'nope')
        with patch.object(pipeline.http_client, 'fetch', return_value=not_found):
            self.assertIsNone(pipeline._fetch_url('https://example.com/missing'))


class MonitorWatchFetchTests(SimpleTestCase):
    """A refused MonitorWatch URL must count as an error, not crash the run."""

    def test_refusal_is_handled_like_any_other_failed_fetch(self):
        import intelligence.compute as compute

        refused = HTTPFetchResult(success=False, error='blocked')

        class _Watch:
            pk = 1
            url = 'http://127.0.0.1:6379/'
            consecutive_errors = 0
            last_content_hash = ''

        with patch(
            'backend_intelligence_engine.services.http_client.fetch',
            return_value=refused,
        ):
            with patch('intelligence.models.MonitorWatch.objects') as objects:
                result = compute.check_monitor_target(_Watch())

        self.assertFalse(result)
        # The watch is marked as errored rather than silently left alone.
        objects.filter.assert_called_once_with(pk=1)
