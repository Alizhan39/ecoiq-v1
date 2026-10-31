"""
backend_intelligence_engine/services/http_client.py — one reusable, honest
external-intelligence HTTP client.

Not a rewrite of every existing `requests.get(...)` call in the codebase —
`ingestion/pipeline.py`, `intelligence/compute.py`, and the `companies`
ingestion commands each already set their own timeout and handle their own
errors, and changing six unrelated, working call sites is out of scope here.
This client exists for **new** Celery-task HTTP calls that need retry
behaviour none of the existing call sites have today (they each catch and
give up on the first failure) — a background task, unlike a request-response
view, can afford to wait a few seconds and try again before giving up.

Uses httpx (not requests) specifically for its built-in `Timeout` object
(separate connect/read timeouts) and typed exception hierarchy, which make
the retry/backoff logic below precise about what's actually being retried.

SSRF: REDIRECTS ARE FOLLOWED BY HAND
------------------------------------
This client previously called httpx with `follow_redirects=True`, which
delegates the entire redirect chain to the library and never shows the
intermediate targets to any validation. That was a live SSRF path, not a
theoretical one: staff register a document URL (validated once, at
registration, by company_intelligence.services.url_safety), the fetch happens
later from here, and a URL that passes validation can answer

    302 Location: http://169.254.169.254/latest/meta-data/iam/security-credentials/

whereupon httpx fetched it and the body was stored as evidence text.

So redirects are now followed one hop at a time with `follow_redirects=False`,
and EVERY hop's target is validated before it is requested — the initial URL,
each `Location`, and therefore the final destination, which is just the last
hop that did not redirect. Relative and scheme-relative Locations are resolved
against the current URL first, so `Location: /admin` cannot skip the check by
carrying no host of its own.

Validation is on by DEFAULT and the failure mode is refusal. A caller that
genuinely needs an internal address must pass `validate=False` and say why;
there is no way to reach one by accident.

WHAT THIS DOES NOT CLOSE
------------------------
A hostname is resolved during validation and resolved again by httpx when the
connection is made. A resolver that returns a public address to the first
lookup and a private one to the second (DNS rebinding) is not stopped by this,
because closing it means pinning the connection to the validated IP, which
needs a custom transport and correct SNI to keep TLS verification intact.
The window is small and the check is immediately before the request, but it is
a real residual risk and is recorded as such rather than described as solved.
"""
import logging
import time
from dataclasses import dataclass, field

import httpx

from company_intelligence.services.url_safety import validate_url

logger = logging.getLogger(__name__)

USER_AGENT = 'EcoIQ-Bot/1.0 (+https://ecoiq.uk/about)'
DEFAULT_TIMEOUT = httpx.Timeout(connect=5.0, read=15.0, write=5.0, pool=5.0)
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
MAX_RETRIES = 2  # 3 attempts total — a background task, never a user-facing wait
BACKOFF_BASE_SECONDS = 1.5

#: Enough for the http->https and bare->www hops a real document URL makes, and
#: few enough that a redirect loop dies quickly. A bounded count is also what
#: makes "every hop is validated" a finite claim rather than an aspiration.
MAX_REDIRECTS = 5

#: Cap on a body held in memory. Matches harvester/services/fetchers.py and
#: good_agents/services/safe_http.py rather than inventing a third number.
MAX_RESPONSE_BYTES = 5 * 1024 * 1024

#: What a caller is told when a URL is refused. The specific reason goes to the
#: log, never to the return value — see url_safety.PUBLIC_REJECTION.
BLOCKED_ERROR = 'blocked: destination not permitted'


class URLNotPermitted(Exception):
    """A URL or redirect target failed validation. Never escapes `fetch`."""

    def __init__(self, category, detail):
        super().__init__(detail)
        self.category = category
        self.detail = detail


def _require_permitted(url, hop):
    """Validate one URL, or raise. Logs a sanitised security event on refusal."""
    verdict = validate_url(url)
    if verdict.safe:
        return verdict
    # `detail` may name a hostname or a resolved address, which is precisely
    # why it goes here and not into the returned error string.
    logger.warning(
        'backend_intelligence_engine.http_client blocked url=%s hop=%s category=%s detail=%s',
        url, hop, verdict.category, verdict.detail,
    )
    raise URLNotPermitted(verdict.category, verdict.detail)


@dataclass
class HTTPFetchResult:
    success: bool
    status_code: int = None
    content: bytes = b''
    text: str = ''
    json_data: dict = None
    error: str = ''
    attempts: int = 0
    elapsed_seconds: float = 0.0
    headers: dict = field(default_factory=dict)
    #: Where the redirect chain actually ended. Recorded because "which URL did
    #: this evidence come from" and "which URL was registered" are now provably
    #: different questions.
    final_url: str = ''


def _request_following_redirects(client_factory, method, url, request_headers, timeout, validate, **kwargs):
    """
    Perform one attempt, following redirects by hand and validating each hop.

    Returns (response, final_url). Raises URLNotPermitted if any hop is refused
    or the chain exceeds MAX_REDIRECTS — a loop and an over-long chain are the
    same refusal, because neither can be followed safely and neither should be
    retried.
    """
    current_url = url
    for hop in range(MAX_REDIRECTS + 1):
        if validate:
            _require_permitted(current_url, hop)

        with client_factory(timeout=timeout, follow_redirects=False) as client:
            response = client.request(method, current_url, headers=request_headers, **kwargs)

        if not getattr(response, 'is_redirect', False):
            return response, current_url

        location = response.headers.get('location', '')
        if not location:
            raise URLNotPermitted('malformed_redirect', 'Redirect response carried no Location header.')

        # Resolve against the current URL so a relative Location ('/admin') or a
        # scheme-relative one ('//169.254.169.254/') becomes absolute BEFORE it
        # is validated. Validating the raw header text would let a relative
        # target skip every host check by not containing a host.
        current_url = str(httpx.URL(current_url).join(location))
        # Query params belong to the caller's first request only; re-sending
        # them to a redirect target would leak them to a host the caller never
        # addressed.
        kwargs.pop('params', None)

    raise URLNotPermitted('too_many_redirects', f'Exceeded {MAX_REDIRECTS} redirect hops.')


def fetch(url, method='GET', *, timeout=DEFAULT_TIMEOUT, headers=None, max_retries=MAX_RETRIES,
          validate=True, **kwargs):
    """
    Never raises. Retries on connection errors, timeouts, and 429/5xx
    responses with exponential backoff; does NOT retry 4xx (a bad request
    won't become a good one) or successful non-2xx responses the caller
    should handle explicitly (e.g. 404 meaning "not found, not an error").

    Redirects are followed one hop at a time and every hop is validated against
    company_intelligence.services.url_safety — see the module docstring.

    A refused destination is NOT retried: it is a permanent verdict about where
    the URL points, and retrying it three times only means three log lines and
    three DNS lookups for the same answer.

    `validate=False` disables the SSRF checks and must only be used by a caller
    that deliberately needs a non-public address. There is no such caller today.
    """
    request_headers = {'User-Agent': USER_AGENT}
    if headers:
        request_headers.update(headers)

    started = time.monotonic()
    last_error = ''
    for attempt in range(1, max_retries + 2):  # +2: first attempt + max_retries retries
        try:
            response, final_url = _request_following_redirects(
                httpx.Client, method, url, request_headers, timeout, validate, **kwargs)

            if response.status_code in RETRYABLE_STATUS_CODES and attempt <= max_retries:
                last_error = f'HTTP {response.status_code} (attempt {attempt})'
                logger.warning('backend_intelligence_engine.http_client retryable status url=%s status=%s attempt=%s',
                               url, response.status_code, attempt)
                time.sleep(BACKOFF_BASE_SECONDS * attempt)
                continue

            content = response.content or b''
            if len(content) > MAX_RESPONSE_BYTES:
                # Refused rather than truncated: half a document silently
                # becoming evidence is worse than no document.
                logger.warning(
                    'backend_intelligence_engine.http_client oversize url=%s bytes=%s cap=%s',
                    url, len(content), MAX_RESPONSE_BYTES)
                elapsed = round(time.monotonic() - started, 3)
                return HTTPFetchResult(
                    success=False,
                    error=f'response exceeds {MAX_RESPONSE_BYTES} byte cap',
                    attempts=attempt, elapsed_seconds=elapsed, final_url=final_url)

            try:
                json_data = response.json()
            except ValueError:
                json_data = None

            elapsed = round(time.monotonic() - started, 3)
            logger.info('backend_intelligence_engine.http_client fetch url=%s status=%s attempts=%s elapsed=%s',
                        url, response.status_code, attempt, elapsed)
            return HTTPFetchResult(
                final_url=final_url,
                success=response.status_code < 400,
                status_code=response.status_code,
                content=response.content, text=response.text, json_data=json_data,
                error='' if response.status_code < 400 else f'HTTP {response.status_code}',
                attempts=attempt, elapsed_seconds=elapsed, headers=dict(response.headers),
            )

        except URLNotPermitted:
            # Deliberately not retried and deliberately not detailed. The real
            # reason was logged by _require_permitted; the caller gets a fixed
            # string so a rejection cannot be used to probe the network.
            elapsed = round(time.monotonic() - started, 3)
            return HTTPFetchResult(success=False, error=BLOCKED_ERROR,
                                   attempts=attempt, elapsed_seconds=elapsed)
        except (httpx.TimeoutException, httpx.ConnectError, httpx.ConnectTimeout) as exc:
            last_error = f'{type(exc).__name__}: {exc}'
            logger.warning('backend_intelligence_engine.http_client network error url=%s attempt=%s error=%s',
                           url, attempt, last_error)
            if attempt <= max_retries:
                time.sleep(BACKOFF_BASE_SECONDS * attempt)
                continue
            break
        except httpx.HTTPError as exc:
            last_error = f'{type(exc).__name__}: {exc}'
            break

    elapsed = round(time.monotonic() - started, 3)
    logger.error('backend_intelligence_engine.http_client fetch failed url=%s error=%s attempts=%s',
                 url, last_error, attempt)
    return HTTPFetchResult(success=False, error=last_error, attempts=attempt, elapsed_seconds=elapsed)
