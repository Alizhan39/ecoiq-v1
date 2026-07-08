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
"""
import logging
import time
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)

USER_AGENT = 'EcoIQ-Bot/1.0 (+https://ecoiq.uk/about)'
DEFAULT_TIMEOUT = httpx.Timeout(connect=5.0, read=15.0, write=5.0, pool=5.0)
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
MAX_RETRIES = 2  # 3 attempts total — a background task, never a user-facing wait
BACKOFF_BASE_SECONDS = 1.5


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


def fetch(url, method='GET', *, timeout=DEFAULT_TIMEOUT, headers=None, max_retries=MAX_RETRIES, **kwargs):
    """
    Never raises. Retries on connection errors, timeouts, and 429/5xx
    responses with exponential backoff; does NOT retry 4xx (a bad request
    won't become a good one) or successful non-2xx responses the caller
    should handle explicitly (e.g. 404 meaning "not found, not an error").
    """
    request_headers = {'User-Agent': USER_AGENT}
    if headers:
        request_headers.update(headers)

    started = time.monotonic()
    last_error = ''
    for attempt in range(1, max_retries + 2):  # +2: first attempt + max_retries retries
        try:
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                response = client.request(method, url, headers=request_headers, **kwargs)

            if response.status_code in RETRYABLE_STATUS_CODES and attempt <= max_retries:
                last_error = f'HTTP {response.status_code} (attempt {attempt})'
                logger.warning('backend_intelligence_engine.http_client retryable status url=%s status=%s attempt=%s',
                               url, response.status_code, attempt)
                time.sleep(BACKOFF_BASE_SECONDS * attempt)
                continue

            try:
                json_data = response.json()
            except ValueError:
                json_data = None

            elapsed = round(time.monotonic() - started, 3)
            logger.info('backend_intelligence_engine.http_client fetch url=%s status=%s attempts=%s elapsed=%s',
                        url, response.status_code, attempt, elapsed)
            return HTTPFetchResult(
                success=response.status_code < 400,
                status_code=response.status_code,
                content=response.content, text=response.text, json_data=json_data,
                error='' if response.status_code < 400 else f'HTTP {response.status_code}',
                attempts=attempt, elapsed_seconds=elapsed, headers=dict(response.headers),
            )

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
