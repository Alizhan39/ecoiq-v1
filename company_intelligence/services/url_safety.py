"""
company_intelligence/services/url_safety.py — feat/stewardship-universe
(PR 13): closes a real, previously-unaddressed SSRF gap identified during
this PR's architecture audit.

Every real HTTP fetch in this repo funnels through
backend_intelligence_engine.services.http_client.fetch(), which has NO
scheme/host validation at all — any URL reachable by staff typing it into
the existing "Register Document Source" form, or (new in this PR) any URL
a DiscoveredSource candidate carries, would otherwise be fetched exactly
as given, including internal/private/loopback addresses and the cloud
metadata endpoint.

This module is deliberately a thin, additive GATE at the point a new URL
is ACCEPTED into the system (source registration time) — not a rewrite of
the fetch stack itself. It never touches fetchers.py/http_client.py's
internals, so every existing, already-verified fetch path (SEC EDGAR,
Companies House, re-checking a URL EcoIQ already has on file) is
unaffected; only NEW URLs being registered for the first time are checked.
"""
import ipaddress
import socket
from urllib.parse import urlparse

ALLOWED_SCHEMES = {'http', 'https'}

# Conservative, explicit hostname denylist — never fetched regardless of
# what DNS/IP resolution says. 'localhost' and its common variants are
# blocked outright rather than relying solely on IP-range checks, since a
# misconfigured resolver could still hand back a private address for them.
BLOCKED_HOSTNAME_SUFFIXES = ('.local', '.internal', '.localhost')
BLOCKED_HOSTNAMES = {'localhost'}


def _is_private_or_reserved(ip_str):
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return True  # unparseable — conservatively treat as unsafe
    return (
        ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast
        or ip.is_reserved or ip.is_unspecified
    )


def is_safe_external_url(url):
    """
    Returns (is_safe: bool, reason: str). `reason` is always populated
    (even when safe, for observability) — never a silent True/False with
    no explanation of what was checked.

    Deliberately does NOT follow redirects itself (that's the fetch
    layer's job) — this only validates the URL a caller is about to
    register/trust, matching the trust boundary at registration time.
    """
    if not url or not isinstance(url, str):
        return False, 'No URL provided.'

    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES:
        return False, f'Scheme "{parsed.scheme}" is not allowed — only http/https URLs may be registered.'

    hostname = (parsed.hostname or '').lower()
    if not hostname:
        return False, 'URL has no resolvable hostname.'
    if hostname in BLOCKED_HOSTNAMES or any(hostname.endswith(suf) for suf in BLOCKED_HOSTNAME_SUFFIXES):
        return False, f'Hostname "{hostname}" is blocked (internal/loopback host name pattern).'

    # A bare IP literal in the URL — check it directly without a DNS call.
    try:
        ipaddress.ip_address(hostname)
        if _is_private_or_reserved(hostname):
            return False, f'IP address {hostname} is private/reserved and cannot be registered as a source.'
        return True, 'Bare IP literal, public range.'
    except ValueError:
        pass

    try:
        resolved = socket.getaddrinfo(hostname, None)
    except (socket.gaierror, UnicodeError) as exc:
        return False, f'Hostname "{hostname}" could not be resolved: {exc}'

    resolved_ips = {info[4][0] for info in resolved}
    if not resolved_ips:
        return False, f'Hostname "{hostname}" resolved to no addresses.'

    unsafe_ips = {ip for ip in resolved_ips if _is_private_or_reserved(ip)}
    if unsafe_ips:
        return False, f'Hostname "{hostname}" resolves to a private/reserved address ({sorted(unsafe_ips)[0]}).'

    return True, f'Hostname "{hostname}" resolves to {len(resolved_ips)} public address(es).'
