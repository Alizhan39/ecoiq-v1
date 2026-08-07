"""
Trusted resolution of a request's client address, and a safe way to log it.

Measured topology (2026-08-07)
------------------------------
Probes against production, recording hop *classes* only, established this:

    request with no forwarding header   -> 2 hops, both public
    request with 1 forged entry         -> 3 hops: [testnet, public, public]
    request with 3 forged entries       -> 5 hops: [testnet x3, public, public]

Identical on ecoiq.uk and ecoiq.onrender.com. Forged entries (RFC 5737
TEST-NET-3, which never occurs in real traffic) always appear to the LEFT, and
the infrastructure always appends exactly **two** entries on the right:

    [ client-supplied junk ... , real client , Cloudflare edge ]
                                  ^^^^^^^^^^^
                                  index len-2

Cloudflare appends the address it received the connection from — the real
client. Render's router then appends the address it received from — the
Cloudflare edge. REMOTE_ADDR is a private Render address in every case.

This is why rate limiting was ineffective. With TRUSTED_PROXY_COUNT=1 the
resolver selected index len-1, the *Cloudflare edge*. Nobody could forge it, so
it was not a spoofing hole — but Cloudflare answers from a large rotating edge
fleet, so consecutive requests from one person landed in different buckets and
the per-origin counters never accumulated. 66 probe requests produced zero 429s.

Two independent sources, both explicit
--------------------------------------
1. `CF-Connecting-IP`, when TRUSTED_CLIENT_IP_HEADER names it. Cloudflare sets
   this itself and **rejects any request that tries to supply it**: a probe
   sending the header got `HTTP 403, error code: 1000` before reaching the
   origin. It is therefore not client-forgeable, and it is immune to changes in
   chain length.
2. `X-Forwarded-For`, counting TRUSTED_PROXY_COUNT entries in from the right.

The header is preferred because it does not depend on hop arithmetic. The count
remains as the fallback and for deployments without Cloudflare. Neither is
implicit: adding or removing a CDN requires changing configuration, and the
structural fields emitted by `safe_origin_context()` make a mismatch visible
rather than silent.

Fail closed
-----------
If the chain is shorter than the trusted hop count, the request did not arrive
the way we believe it does, and no value in it can be trusted. The resolver
returns '' rather than falling back to REMOTE_ADDR — REMOTE_ADDR is the private
Render address, identical for every visitor, so falling back to it would put the
entire internet in one bucket while looking like a successful resolution.
Callers treat '' as "unknown origin", which gets its own bounded shared bucket.

What is safe to log
-------------------
Not the address. `origin_fingerprint()` returns a keyed HMAC-SHA256, truncated.
Nothing here reads cookies, sessions, Authorization headers, CSRF or captcha
tokens, and `safe_origin_context()` returns a fixed set of keys so a caller
cannot widen it by accident.

Retention: fingerprints appear only in application log lines (platform log
retention) and in cache keys (expiring with their rate-limit window, at most
24h). No raw address is written to a log or to any database column by this
module.
"""
import hashlib
import hmac
import ipaddress
import logging
from typing import TypedDict

from django.conf import settings
from django.http import HttpRequest


class OriginContext(TypedDict):
    """
    The complete set of origin fields that may be logged.

    A TypedDict rather than a plain dict so the closed key set is enforced by
    the type checker as well as by the function body: adding a key here is a
    deliberate act, and adding one anywhere else is an error. That is the point
    of the structure — it is what keeps a raw address or a header value from
    reaching a log line by accident.
    """
    origin_available: bool
    origin_fingerprint: str
    origin_resolution_status: str
    origin_private: bool
    origin_family: str
    forwarded_hop_count: int
    trusted_proxy_count: int
    trusted_header_configured: bool

logger = logging.getLogger(__name__)

FORWARDED_FOR = 'HTTP_X_FORWARDED_FOR'
REMOTE_ADDR = 'REMOTE_ADDR'

# Resolution outcomes, reported in structured logs so a topology change is
# visible in the data rather than only in a behaviour regression.
RESOLVED_TRUSTED_HEADER = 'trusted_header'
RESOLVED_FORWARDED_CHAIN = 'forwarded_chain'
RESOLVED_REMOTE_ADDR = 'remote_addr'
RESOLVED_CHAIN_TOO_SHORT = 'chain_too_short'
RESOLVED_UNAVAILABLE = 'unavailable'


def trusted_proxy_count() -> int:
    """Entries our own infrastructure appends to X-Forwarded-For."""
    return max(0, int(getattr(settings, 'TRUSTED_PROXY_COUNT', 0) or 0))


def trusted_client_ip_header() -> str:
    """
    META key of a header whose value the edge guarantees, or ''.

    Naming a header here is an explicit statement that a trusted proxy sets it
    and strips any client-supplied copy. Empty means "do not trust any header",
    which is correct for local development and any deployment without a CDN.
    """
    name = (getattr(settings, 'TRUSTED_CLIENT_IP_HEADER', '') or '').strip()
    if not name:
        return ''
    return 'HTTP_' + name.upper().replace('-', '_')


def normalise_ip(value: str | None) -> str:
    """
    Canonical address string, or '' if it is not one.

    Normalising matters: `2001:DB8::1`, `2001:db8:0:0:0:0:0:1` and
    `[2001:db8::1]:443` are one origin. Without this an IPv6 client evades every
    per-origin limit by varying the spelling.
    """
    text = (value or '').strip()
    if not text:
        return ''
    if text.startswith('['):
        text = text[1:].partition(']')[0]
    elif text.count(':') == 1:
        # Exactly one colon is IPv4:port. Bare IPv6 always has several.
        text = text.partition(':')[0]
    text = text.partition('%')[0]           # zone index is local to the sender
    try:
        return str(ipaddress.ip_address(text))
    except ValueError:
        return ''


def forwarded_chain(request: HttpRequest | None) -> list[str]:
    """
    Validated X-Forwarded-For entries, malformed ones discarded.

    Accepts None and returns an empty chain. Both callers already guard for it,
    so this was never reachable, but the guard belonged here: a helper that
    dereferences request.META while its own signature admits None hands the next
    caller an AttributeError instead of the empty result it plainly means.
    """
    if request is None:
        return []
    raw = request.META.get(FORWARDED_FOR, '') or ''
    return [ip for ip in (normalise_ip(p) for p in raw.split(',')) if ip]


def resolve_origin(request: HttpRequest | None) -> tuple[str, str]:
    """
    Returns (address, status). Address is '' when nothing can be trusted.

    Status is one of the RESOLVED_* constants and is safe to log.
    """
    if request is None:
        return '', RESOLVED_UNAVAILABLE

    header_key = trusted_client_ip_header()
    if header_key:
        candidate = normalise_ip(request.META.get(header_key, ''))
        if candidate:
            return candidate, RESOLVED_TRUSTED_HEADER

    hops = trusted_proxy_count()
    if hops:
        chain = forwarded_chain(request)
        if len(chain) >= hops:
            # Walk in from the right past the entries our infrastructure wrote.
            return chain[len(chain) - hops], RESOLVED_FORWARDED_CHAIN
        # Fail closed. REMOTE_ADDR here is the private Render address, the same
        # for every visitor; using it would silently merge all traffic.
        logger.warning('client_origin_chain_too_short',
                       extra={'forwarded_hop_count': len(chain),
                              'trusted_proxy_count': hops})
        return '', RESOLVED_CHAIN_TOO_SHORT

    # No trusted proxy configured: the socket peer is the client.
    direct = normalise_ip(request.META.get(REMOTE_ADDR, ''))
    return (direct, RESOLVED_REMOTE_ADDR) if direct else ('', RESOLVED_UNAVAILABLE)


def client_ip(request: HttpRequest | None) -> str:
    """The trusted client address, or '' when it cannot be established."""
    return resolve_origin(request)[0]


def is_private(ip: str | None) -> bool:
    """True for loopback, link-local, private and unspecified addresses."""
    normalised = normalise_ip(ip)
    if not normalised:
        return False
    addr = ipaddress.ip_address(normalised)
    return (addr.is_private or addr.is_loopback
            or addr.is_link_local or addr.is_unspecified)


# ── privacy-preserving correlation ──────────────────────────────────────────

def _origin_key() -> bytes | None:
    """
    Dedicated HMAC key, or None when fingerprinting must be disabled.

    Deliberately separate from SECRET_KEY: rotating SECRET_KEY invalidates
    sessions and signed tokens, so nobody rotates it to expire abuse
    fingerprints, and reusing it spreads one secret across unrelated purposes.

    There is no literal fallback. If the key is absent in production,
    fingerprinting is switched off and said so in the logs, rather than every
    deployment sharing a value that is public in the source tree.
    """
    key = (getattr(settings, 'REQUEST_ORIGIN_HMAC_KEY', '') or '').strip()
    if key:
        return key.encode('utf-8')
    if getattr(settings, 'IS_PRODUCTION', False):
        return None
    # Development and tests: derive from SECRET_KEY so fingerprints are stable
    # within a run without requiring anyone to configure a second secret.
    secret = (getattr(settings, 'SECRET_KEY', '') or '').encode('utf-8')
    return secret or None


def origin_key_version() -> str:
    """Opaque version label, emitted alongside fingerprints so a rotation is legible."""
    return (getattr(settings, 'REQUEST_ORIGIN_HMAC_KEY_VERSION', '') or 'v1').strip()[:16]


def origin_fingerprint(request_or_ip: HttpRequest | str | None) -> str:
    """
    Keyed HMAC-SHA256 of the client address, truncated. Never the address.

    Returns '' when the address is unknown or no key is configured — an empty
    fingerprint is honest about "cannot correlate", where a plain hash of an
    empty string would look like a real, shared identity.

    Not a bare SHA-256: the address space is small enough to enumerate
    exhaustively, so an unkeyed digest of an IP is reversible in seconds.
    """
    if request_or_ip is None:
        return ''
    ip = (normalise_ip(request_or_ip) if isinstance(request_or_ip, str)
          else client_ip(request_or_ip))
    if not ip:
        return ''
    key = _origin_key()
    if key is None:
        return ''
    digest = hmac.new(key, f'origin:{origin_key_version()}:{ip}'.encode('utf-8'),
                      hashlib.sha256).hexdigest()
    return f'{origin_key_version()}:{digest[:16]}'


def fingerprinting_available() -> bool:
    """False when no key is configured, so callers can log the reason once."""
    return _origin_key() is not None


def safe_origin_context(request: HttpRequest | None) -> OriginContext:
    """
    The only origin fields that may be logged, as a fixed dict.

    A closed set by construction. No cookie, session key, Authorization header,
    CSRF token, captcha token, referrer, user agent, raw address or raw
    forwarding header appears here, and a caller cannot add one without editing
    this function.
    """
    ip, status = resolve_origin(request)
    chain = forwarded_chain(request)
    return {
        'origin_available': bool(ip),
        'origin_fingerprint': origin_fingerprint(ip),
        'origin_resolution_status': status,
        'origin_private': is_private(ip),
        'origin_family': 'ipv6' if ip and ':' in ip else ('ipv4' if ip else 'none'),
        'forwarded_hop_count': len(chain),
        'trusted_proxy_count': trusted_proxy_count(),
        'trusted_header_configured': bool(trusted_client_ip_header()),
    }
