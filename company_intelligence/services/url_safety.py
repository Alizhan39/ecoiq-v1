"""
company_intelligence/services/url_safety.py — the single URL-safety authority.

ORIGIN
------
Added by feat/stewardship-universe (PR 13) as a GATE at the point a new URL is
ACCEPTED into the system (source registration time). That was the right first
move and it is still the first line of defence, but registration-time checking
alone has two holes, and both are now closed here and in the fetch layer:

  1. **Redirects.** A URL that passes at registration is fetched later by
     backend_intelligence_engine.services.http_client.fetch(), which followed
     redirects with no revalidation. A public URL that answers
     `302 Location: http://169.254.169.254/…` therefore reached the metadata
     service with the response body stored as evidence.
  2. **Time.** Registration and fetch are different moments. DNS can change
     between them, and `fetch_url_recheck` re-fetches stored URLs indefinitely.

The fetch layer now calls this module on the initial URL AND on every redirect
hop, so validation happens at the moment of connection rather than only once,
long before it.

ONE VALIDATOR, NOT TWO
----------------------
This is the only general-purpose URL validator in the repository and new code
must call it rather than re-deriving these rules.
`good_agents/services/safe_http.py` keeps its own stricter check on purpose: it
requires a per-adapter fixed host ALLOWLIST, which is a stronger claim than
"not obviously internal" and is only possible because that app never fetches a
user-supplied URL. An allowlist is not a competing implementation of a
denylist; it is a different and narrower trust decision.

WHAT THE CALLER IS TOLD, AND WHAT THE LOGS ARE TOLD
---------------------------------------------------
`public_reason` never names a resolved address, a port or a hostname's
resolution result. `detail` does, and is for logs only. This matters because
the registration form echoes the rejection back to whoever submitted it: a
message reading "resolves to 10.4.2.7" turns a blocked SSRF attempt into a
working internal port scanner with a helpful oracle.
"""
from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urlparse

ALLOWED_SCHEMES = {'http', 'https'}

#: Only the two ports a public document is ever served from. An allowlist, not
#: a denylist of "dangerous" ports: enumerating 6379/5432/11211/… is a game you
#: lose the first time an internal service listens somewhere unusual.
ALLOWED_PORTS = {80, 443}

# Conservative, explicit hostname denylist — never fetched regardless of
# what DNS/IP resolution says. 'localhost' and its common variants are
# blocked outright rather than relying solely on IP-range checks, since a
# misconfigured resolver could still hand back a private address for them.
BLOCKED_HOSTNAME_SUFFIXES = ('.local', '.internal', '.localhost')
BLOCKED_HOSTNAMES = {'localhost'}

#: Ranges Python's own `ipaddress` flags don't cover.
#:
#: 100.64.0.0/10 is RFC 6598 carrier-grade NAT — `is_private` returns False for
#: it, and it is routinely used for internal infrastructure. Checked explicitly
#: rather than trusted to a stdlib property that does not claim to cover it.
EXTRA_BLOCKED_NETWORKS = (
    ipaddress.ip_network('100.64.0.0/10'),   # RFC 6598 shared address space
    ipaddress.ip_network('192.0.0.0/24'),    # IETF protocol assignments
    ipaddress.ip_network('::ffff:100.64.0.0/106'),
)

#: Named so a log line says WHY, and so the fetch layer can count categories
#: without parsing prose.
CATEGORY_OK = 'ok'
CATEGORY_MALFORMED = 'malformed_url'
CATEGORY_SCHEME = 'blocked_scheme'
CATEGORY_CREDENTIALS = 'embedded_credentials'
CATEGORY_PORT = 'blocked_port'
CATEGORY_HOSTNAME = 'blocked_hostname'
CATEGORY_PRIVATE_IP = 'private_or_reserved_address'
CATEGORY_DNS = 'dns_resolution_failed'

#: Deliberately uninformative. Every rejection returns the SAME public string,
#: whatever the cause: a caller who can distinguish "blocked port" from
#: "resolves to a private address" from "DNS failed" can map an internal
#: network by watching which URLs come back with which message.
PUBLIC_REJECTION = 'This URL cannot be used as a source.'


@dataclass(frozen=True)
class UrlSafetyVerdict:
    safe: bool
    category: str
    #: Safe to show a user. Identical for every rejection — see PUBLIC_REJECTION.
    public_reason: str
    #: For logs only. May name the hostname, port or resolved address.
    detail: str
    #: Every address the hostname resolved to, so a caller can record what it
    #: actually validated. Empty for an IP literal's own value is not the case:
    #: a literal reports itself here.
    resolved_ips: frozenset[str] = frozenset()


def _is_private_or_reserved(ip_str):
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return True  # unparseable — conservatively treat as unsafe
    if any(ip in net for net in EXTRA_BLOCKED_NETWORKS if net.version == ip.version):
        return True
    # An IPv4-mapped IPv6 address (::ffff:127.0.0.1) must be judged on the IPv4
    # address it carries. CPython's ipaddress already does this for is_private
    # and is_loopback; unwrapping explicitly means the guarantee does not
    # silently depend on that continuing to be true.
    mapped = getattr(ip, 'ipv4_mapped', None)
    if mapped is not None:
        return _is_private_or_reserved(str(mapped))
    return (
        ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast
        or ip.is_reserved or ip.is_unspecified
    )


def validate_url(url):
    """
    Full verdict for `url`, with the public and loggable reasons separated.

    Checks, in order, cheapest and most certain first:
      scheme → embedded credentials → hostname shape → port → IP literal → DNS.

    The DNS step resolves the hostname and rejects if **any** answer is
    private/reserved, not merely the first. A resolver returning one public and
    one internal address is the classic split-answer bypass, and "the first
    answer was fine" is exactly the wrong reading of it.

    This also closes the alternative-representation bypasses without needing to
    special-case them: `http://2130706433/`, `http://0x7f000001/` and
    `http://127.1/` are not parseable as IP literals, so they fall through to
    the DNS branch — where the resolver dutifully returns 127.0.0.1 and the
    address check rejects them. Tests pin all three.
    """
    if not url or not isinstance(url, str):
        return UrlSafetyVerdict(False, CATEGORY_MALFORMED, PUBLIC_REJECTION, 'No URL provided.')

    try:
        parsed = urlparse(url)
    except ValueError as exc:  # e.g. an invalid IPv6 literal in brackets
        return UrlSafetyVerdict(False, CATEGORY_MALFORMED, PUBLIC_REJECTION, f'URL could not be parsed: {exc}')

    if parsed.scheme not in ALLOWED_SCHEMES:
        return UrlSafetyVerdict(
            False, CATEGORY_SCHEME, PUBLIC_REJECTION,
            f'Scheme {parsed.scheme!r} is not http/https.')

    # Checked before the hostname is even looked at. `http://trusted.example.com@169.254.169.254/`
    # reads as a trusted host to a human and resolves to the metadata service;
    # credentials in a fetched URL are also a credential-leak vector in their
    # own right, since they travel to whatever the final hop turns out to be.
    if parsed.username is not None or parsed.password is not None:
        return UrlSafetyVerdict(
            False, CATEGORY_CREDENTIALS, PUBLIC_REJECTION,
            'URL contains embedded credentials.')

    try:
        hostname = (parsed.hostname or '').lower()
    except ValueError as exc:
        return UrlSafetyVerdict(False, CATEGORY_MALFORMED, PUBLIC_REJECTION, f'Invalid host in URL: {exc}')
    if not hostname:
        return UrlSafetyVerdict(False, CATEGORY_MALFORMED, PUBLIC_REJECTION, 'URL has no resolvable hostname.')

    if hostname in BLOCKED_HOSTNAMES or any(hostname.endswith(suf) for suf in BLOCKED_HOSTNAME_SUFFIXES):
        return UrlSafetyVerdict(
            False, CATEGORY_HOSTNAME, PUBLIC_REJECTION,
            f'Hostname {hostname!r} matches an internal/loopback name pattern.')

    try:
        port = parsed.port
    except ValueError as exc:
        return UrlSafetyVerdict(False, CATEGORY_MALFORMED, PUBLIC_REJECTION, f'Invalid port in URL: {exc}')
    if port is not None and port not in ALLOWED_PORTS:
        return UrlSafetyVerdict(
            False, CATEGORY_PORT, PUBLIC_REJECTION,
            f'Port {port} is not in the allowed set {sorted(ALLOWED_PORTS)}.')

    # A bare IP literal in the URL — check it directly without a DNS call.
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        if _is_private_or_reserved(hostname):
            return UrlSafetyVerdict(
                False, CATEGORY_PRIVATE_IP, PUBLIC_REJECTION,
                f'IP literal {hostname} is private/reserved.')
        return UrlSafetyVerdict(
            True, CATEGORY_OK, 'Bare IP literal, public range.',
            f'IP literal {hostname} is in a public range.', frozenset({hostname}))

    try:
        resolved = socket.getaddrinfo(hostname, None)
    except (socket.gaierror, UnicodeError) as exc:
        return UrlSafetyVerdict(
            False, CATEGORY_DNS, PUBLIC_REJECTION,
            f'Hostname {hostname!r} could not be resolved: {exc}')

    resolved_ips = {info[4][0] for info in resolved}
    if not resolved_ips:
        return UrlSafetyVerdict(
            False, CATEGORY_DNS, PUBLIC_REJECTION,
            f'Hostname {hostname!r} resolved to no addresses.')

    unsafe_ips = sorted(ip for ip in resolved_ips if _is_private_or_reserved(ip))
    if unsafe_ips:
        return UrlSafetyVerdict(
            False, CATEGORY_PRIVATE_IP, PUBLIC_REJECTION,
            f'Hostname {hostname!r} resolves to a private/reserved address ({unsafe_ips[0]}).',
            frozenset(resolved_ips))

    return UrlSafetyVerdict(
        True, CATEGORY_OK,
        f'Hostname resolves to {len(resolved_ips)} public address(es).',
        f'Hostname {hostname!r} resolves to {len(resolved_ips)} public address(es).',
        frozenset(resolved_ips))


def is_safe_external_url(url):
    """
    Returns (is_safe: bool, reason: str) — the long-standing two-value API.

    `reason` is the PUBLIC reason and is safe to show a user. It is deliberately
    the same sentence for every rejection; call `validate_url` when the caller
    needs the category or the loggable detail.
    """
    verdict = validate_url(url)
    return verdict.safe, verdict.public_reason
