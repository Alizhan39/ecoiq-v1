"""
TEMPORARY topology diagnostics for the Render proxy chain.

Why this exists
---------------
`TRUSTED_PROXY_COUNT` was set to 1 on the assumption that Render puts exactly
one proxy in front of the application. That assumption was never verified, and
production evidence contradicts it: both ecoiq.uk and ecoiq.onrender.com answer
with `server: cloudflare`, so there is at least one hop in front of Render's own
router. With the count too low the resolver selects an infrastructure address
instead of the client, every visitor behind the same edge shares one bucket, and
the per-origin rate limits never accumulate.

Guessing a new number would repeat the original mistake. This module measures it.

How it measures without handling addresses
------------------------------------------
Each X-Forwarded-For entry is reduced to a *class*, never a value:

    testnet    203.0.113.0/24 — RFC 5737 TEST-NET-3, which never appears in real
               traffic, so any entry in this range is one the probe injected and
               therefore client-controlled
    private    RFC1918 / loopback / link-local — our own infrastructure
    public     a routable address neither we nor the probe wrote
    malformed  not an address at all

Sending a probe with known TEST-NET-3 entries and reading back the classes tells
us exactly which positions a client can write and which the infrastructure
appends — the whole question — while never exposing, logging or returning a
single real address.

This endpoint is deliberately short-lived: it is removed once the topology is
settled. It returns classifications and counts only. No address, no header
value, no cookie, no token, and nothing about the requester beyond the shape of
the forwarding chain.
"""
import ipaddress

from django.conf import settings
from django.http import JsonResponse

from .client_origin import FORWARDED_FOR, REMOTE_ADDR, client_ip, normalise_ip, origin_fingerprint

# RFC 5737 TEST-NET-3. Reserved for documentation, never routed, so its presence
# proves an entry came from the probe rather than from real infrastructure.
PROBE_RANGE = ipaddress.ip_network('203.0.113.0/24')


def classify(value):
    """Reduce one forwarding entry to a class name. Never returns the value."""
    ip = normalise_ip(value)
    if not ip:
        return 'malformed'
    addr = ipaddress.ip_address(ip)
    if addr.version == 4 and addr in PROBE_RANGE:
        return 'testnet'
    if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_unspecified:
        return 'private'
    return 'public'


def describe_chain(request):
    """
    Structural description of a request's forwarding chain.

    Every field is a count, a class name, an index or a keyed digest. No raw
    address, header value or personal data can appear in the result.
    """
    raw = request.META.get(FORWARDED_FOR, '') or ''
    entries = [part.strip() for part in raw.split(',') if part.strip()]
    classes = [classify(part) for part in entries]

    resolved = client_ip(request)
    resolved_class = classify(resolved) if resolved else 'none'

    # Which position did the resolver land on, counting from the left?
    selected_index = None
    if resolved:
        for i, part in enumerate(entries):
            if normalise_ip(part) == resolved:
                selected_index = i
                break

    # Cloudflare's own client header, if it reaches us at all.
    cf = request.META.get('HTTP_CF_CONNECTING_IP', '')
    true_client = request.META.get('HTTP_TRUE_CLIENT_IP', '')
    real_ip = request.META.get('HTTP_X_REAL_IP', '')

    return {
        'xff_present': bool(raw),
        'xff_hop_count': len(entries),
        'xff_hop_classes': classes,
        'remote_addr_class': classify(request.META.get(REMOTE_ADDR, '')),
        'trusted_proxy_count': int(getattr(settings, 'TRUSTED_PROXY_COUNT', 0) or 0),
        'resolver_selected_index': selected_index,
        'resolver_selected_class': resolved_class,
        'resolver_origin_fingerprint': origin_fingerprint(resolved) if resolved else '',
        'cf_connecting_ip_present': bool(cf),
        'cf_connecting_ip_class': classify(cf) if cf else 'absent',
        'true_client_ip_present': bool(true_client),
        'true_client_ip_class': classify(true_client) if true_client else 'absent',
        'x_real_ip_present': bool(real_ip),
        'x_real_ip_class': classify(real_ip) if real_ip else 'absent',
        'forwarded_proto': request.META.get('HTTP_X_FORWARDED_PROTO', '')[:16],
    }


def origin_diagnostic_view(request):
    """
    TEMPORARY. Returns the structural description above and nothing else.

    Disabled unless ORIGIN_DIAGNOSTIC_ENABLED is on, so it cannot outlive the
    investigation by accident.
    """
    if not getattr(settings, 'ORIGIN_DIAGNOSTIC_ENABLED', False):
        return JsonResponse({'detail': 'not found'}, status=404)
    return JsonResponse(describe_chain(request))
