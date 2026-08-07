"""
Trusted resolution of a request's client address, and a safe way to log it.

The problem this fixes
----------------------
Five call sites independently read `X-Forwarded-For` and took the **leftmost**
entry. That entry is written by the client. Anyone can send::

    X-Forwarded-For: 203.0.113.9

and be counted as 203.0.113.9 — so a single host can present a fresh address on
every request and walk straight through any per-IP rate limit, while the logs
record whatever it chose to claim.

The header is an append-only chain: each proxy appends the address it received
the connection *from*. Only the hops your own infrastructure appended can be
trusted. With `TRUSTED_PROXY_COUNT = n`, the real client is the entry `n` places
from the right; everything to the left of it is client-supplied and worthless.

Getting `n` wrong in either direction is a real failure, so it is an explicit
setting rather than a guess:

  too high  you start trusting client-supplied entries again
  too low   every request resolves to your own load balancer, and one shared
            rate-limit bucket throttles all of your users at once

On Render there is exactly one proxy in front of the application, so
`TRUSTED_PROXY_COUNT = 1`. Locally there is none, so it is 0 and `REMOTE_ADDR`
is used directly.

What is safe to log
-------------------
Not the address. `origin_fingerprint()` returns a keyed, truncated HMAC — enough
to recognise the same origin across requests and to count repeat offenders,
useless to anyone who obtains the logs without SECRET_KEY. Nothing here reads
cookies, session identifiers, Authorization headers, CSRF tokens or captcha
tokens, and `safe_origin_context()` returns a fixed set of keys so a future
caller cannot widen it by accident.

Retention
---------
Fingerprints appear only in application log lines and in cache keys.

  application logs   retained by the platform's own log retention; EcoIQ
                     writes no separate origin log and no origin column
  cache keys         expire with their rate-limit window (see ANTISPAM_LIMITS),
                     at most 24 hours

Because the key is derived from SECRET_KEY, rotating SECRET_KEY invalidates
every previously emitted fingerprint — old log lines can no longer be correlated
with new ones. That is the intended failure mode.
"""
import ipaddress

from django.conf import settings

# Header names are fixed here rather than taken from a setting: a caller that
# could choose the header could choose one the proxy does not control.
FORWARDED_FOR = 'HTTP_X_FORWARDED_FOR'
REMOTE_ADDR = 'REMOTE_ADDR'


def trusted_proxy_count():
    """How many rightmost X-Forwarded-For entries our own infrastructure wrote."""
    return max(0, int(getattr(settings, 'TRUSTED_PROXY_COUNT', 0) or 0))


def normalise_ip(value):
    """
    Return a canonical address string, or '' if it is not one.

    Normalising matters: `2001:DB8::1`, `2001:db8:0:0:0:0:0:1` and
    `[2001:db8::1]:443` are the same origin and must produce the same
    fingerprint, or an IPv6 client gets a free pass on every rate limit by
    varying the spelling.
    """
    text = (value or '').strip()
    if not text:
        return ''
    # Bracketed IPv6, with or without a port: [2001:db8::1]:443
    if text.startswith('['):
        text = text[1:].partition(']')[0]
    elif text.count(':') == 1:
        # Exactly one colon means IPv4:port. Bare IPv6 always has several.
        text = text.partition(':')[0]
    # A zone index is local to the sending host and not part of the identity.
    text = text.partition('%')[0]
    try:
        return str(ipaddress.ip_address(text))
    except ValueError:
        return ''


def client_ip(request):
    """
    The address our own infrastructure observed the connection coming from.

    Returns '' when it cannot be established. Callers must treat '' as
    "unknown origin" and must not fall back to a client-supplied value.
    """
    if request is None:
        return ''

    hops = trusted_proxy_count()
    if hops:
        chain = [normalise_ip(part)
                 for part in (request.META.get(FORWARDED_FOR, '') or '').split(',')]
        chain = [ip for ip in chain if ip]
        # Walk in from the right past the hops we appended ourselves. With one
        # trusted proxy the client is the last entry; the proxy's own address
        # is in REMOTE_ADDR, not in the header.
        if len(chain) >= hops:
            index = len(chain) - hops
            if index < len(chain):
                return chain[index]
        # A chain shorter than the number of proxies we expect means the request
        # did not arrive the way we think it does. Fall through to REMOTE_ADDR
        # rather than trusting a truncated chain.

    return normalise_ip(request.META.get(REMOTE_ADDR, ''))


def is_private(ip):
    """True for loopback, link-local, private and unspecified addresses."""
    normalised = normalise_ip(ip)
    if not normalised:
        return False
    addr = ipaddress.ip_address(normalised)
    return (addr.is_private or addr.is_loopback
            or addr.is_link_local or addr.is_unspecified)


def origin_fingerprint(request_or_ip):
    """
    Keyed, truncated HMAC of the client address. Never the address itself.

    Accepts a request or an address string, so a caller that has already
    resolved the address does not resolve it twice.
    """
    from notifications.antispam.fingerprint import hashed_ip

    if request_or_ip is None:
        return ''
    if isinstance(request_or_ip, str):
        ip = normalise_ip(request_or_ip)
    else:
        ip = client_ip(request_or_ip)
    return hashed_ip(ip) if ip else ''


def safe_origin_context(request):
    """
    The only origin fields that may be logged, as a fixed dict.

    Deliberately a closed set. No cookie, session key, Authorization header,
    CSRF token, captcha token, referrer or user agent appears here, and a caller
    cannot add one without editing this function.
    """
    ip = client_ip(request)
    return {
        'origin_fp': origin_fingerprint(ip),
        'origin_known': bool(ip),
        'origin_private': is_private(ip),
        'origin_family': 'ipv6' if ip and ':' in ip else ('ipv4' if ip else 'none'),
        'proxy_hops_trusted': trusted_proxy_count(),
    }
