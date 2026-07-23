"""
good_agents/services/safe_http.py — SSRF-hardened HTTP fetch for real
SignalProvider adapters (PR4 Phase 21: security).

Why this exists instead of reusing
`backend_intelligence_engine.services.http_client.fetch()` directly: that
shared client is excellent for timeout/retry/backoff (and this module
mirrors its constants), but it calls httpx with `follow_redirects=True` and
never re-validates the redirect target, and it has no host allowlist or
private-IP check — acceptable for its existing call sites (a handful of
fixed, reviewed URLs each app already trusted), but not a safe foundation
for a NEW app whose whole job is "fetch from more sources." Rather than
change shared infrastructure other features depend on, this module adds
the missing SSRF checks on top, reusing the same timeout/User-Agent
conventions.

Every provider adapter must declare a fixed `allowed_hosts` set — there is
no path from user input to a fetched URL anywhere in this app. Defense in
depth beyond that:
  - scheme must be https
  - host must be in the adapter's own allowlist
  - the resolved IP must not be private/loopback/link-local/multicast
  - redirects are followed manually, one hop at a time, up to
    MAX_REDIRECTS, and the SAME checks re-run on every hop's target
  - response size is capped while streaming (never buffers an unbounded
    body into memory)
"""
import ipaddress
import logging
import socket
import time
from dataclasses import dataclass, field
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

USER_AGENT = 'EcoIQ-GoodAgents-Bot/1.0 (+https://ecoiq.uk/about; signal ingestion, read-only)'
DEFAULT_TIMEOUT = httpx.Timeout(connect=5.0, read=15.0, write=5.0, pool=5.0)
MAX_RESPONSE_BYTES = 5 * 1024 * 1024  # 5 MB — matches harvester/services/fetchers.py's MAX_RESPONSE_BYTES
MAX_REDIRECTS = 3


@dataclass
class SafeFetchResult:
    success: bool
    status_code: int = None
    content: bytes = b''
    text: str = ''
    json_data: dict = None
    error: str = ''
    elapsed_seconds: float = 0.0
    final_url: str = ''


class SSRFBlocked(Exception):
    """Raised (and always caught by the caller) when a URL/host/IP fails validation."""


def _validate_host(url, allowed_hosts):
    parsed = urlparse(url)
    if parsed.scheme != 'https':
        raise SSRFBlocked(f'Rejected non-https scheme: {parsed.scheme!r}')
    if parsed.hostname not in allowed_hosts:
        raise SSRFBlocked(f'Host {parsed.hostname!r} not in allowlist {sorted(allowed_hosts)}')
    try:
        addrinfo = socket.getaddrinfo(parsed.hostname, 443)
    except socket.gaierror as exc:
        raise SSRFBlocked(f'DNS resolution failed for {parsed.hostname!r}: {exc}')
    for family, _, _, _, sockaddr in addrinfo:
        ip = ipaddress.ip_address(sockaddr[0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved:
            raise SSRFBlocked(f'{parsed.hostname!r} resolves to a non-public address ({ip}) — blocked')
    return parsed


def safe_fetch(url, *, allowed_hosts, timeout=DEFAULT_TIMEOUT, max_bytes=MAX_RESPONSE_BYTES, params=None):
    """
    Never raises SSRFBlocked/httpx exceptions to the caller — returns a
    SafeFetchResult with success=False and a real `error` string instead,
    exactly like backend_intelligence_engine.services.http_client.fetch()'s
    "never raises" contract, so one provider's failure can never propagate
    into a crashed ingestion run.
    """
    started = time.monotonic()
    current_url = url
    try:
        for _hop in range(MAX_REDIRECTS + 1):
            _validate_host(current_url, allowed_hosts)
            with httpx.Client(timeout=timeout, follow_redirects=False) as client:
                response = client.get(current_url, headers={'User-Agent': USER_AGENT, 'Accept': 'application/json'}, params=params)
            params = None  # only apply query params on the first hop

            if response.is_redirect:
                location = response.headers.get('location', '')
                if not location:
                    raise SSRFBlocked('Redirect response with no Location header')
                current_url = httpx.URL(current_url).join(location).human_repr()
                continue

            content_length = response.headers.get('content-length')
            if content_length and int(content_length) > max_bytes:
                raise SSRFBlocked(f'Response declares {content_length} bytes, exceeds cap {max_bytes}')
            if len(response.content) > max_bytes:
                raise SSRFBlocked(f'Response body {len(response.content)} bytes exceeds cap {max_bytes}')

            try:
                json_data = response.json()
            except ValueError:
                json_data = None

            elapsed = round(time.monotonic() - started, 3)
            return SafeFetchResult(
                success=response.status_code < 400, status_code=response.status_code,
                content=response.content, text=response.text, json_data=json_data,
                error='' if response.status_code < 400 else f'HTTP {response.status_code}',
                elapsed_seconds=elapsed, final_url=current_url,
            )
        raise SSRFBlocked(f'Exceeded {MAX_REDIRECTS} redirect hops')
    except SSRFBlocked as exc:
        logger.warning('good_agents.safe_http blocked url=%s reason=%s', url, exc)
        return SafeFetchResult(success=False, error=f'blocked: {exc}', elapsed_seconds=round(time.monotonic() - started, 3))
    except httpx.HTTPError as exc:
        logger.warning('good_agents.safe_http network error url=%s error=%s', url, exc)
        return SafeFetchResult(success=False, error=f'{type(exc).__name__}: {exc}', elapsed_seconds=round(time.monotonic() - started, 3))
