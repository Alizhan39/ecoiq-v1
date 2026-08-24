"""
core/throttling.py — one trusted client identity for every DRF throttle.

THE BUG THIS FIXES
------------------
DRF's `BaseThrottle.get_ident()` is the default identity for every
`SimpleRateThrottle` in this repository. With `NUM_PROXIES` unset — which it is
— its final line reads:

    return ''.join(xff.split()) if xff else remote_addr

That is the WHOLE `X-Forwarded-For` chain, concatenated, including any entries
the client supplied. Behind Cloudflare and Render the real chain is

    [ client-supplied junk ... , real client , Cloudflare edge ]

so the identity a throttle counts against is partly attacker-controlled. Adding
one junk entry produces a different ident, a fresh counter, and no limit at all.
`mobile_auth.throttles.LoginRateThrottle` — the brute-force protection on
`/api/v1/auth/login/` — was keyed this way, so its `10/hour` was bypassable by
varying a header.

Even without an attacker it did not work: Cloudflare answers from a large
rotating edge fleet, so consecutive requests from one person produced different
idents and the counters never accumulated. `core/client_origin.py` documents 66
probe requests producing zero 429s for exactly this reason.

THE FIX
-------
`core.client_origin.client_ip` already resolves the real client correctly and is
measured against this deployment's actual topology: it prefers
`CF-Connecting-IP`, which Cloudflare sets itself and **rejects if a client tries
to supply it** (a forged one gets HTTP 403 at the edge, verified in
production), and falls back to counting `TRUSTED_PROXY_COUNT` entries from the
right of the chain. Neither is client-forgeable.

This module does not implement a second rate limiter. It replaces one method so
the existing throttles count against an identity that is real.
"""
from __future__ import annotations

from rest_framework.throttling import AnonRateThrottle

from core import client_origin

#: Every unidentifiable origin shares one bucket, on purpose. A request whose
#: source cannot be established is throttled together with every other such
#: request rather than being waved through — the same choice
#: `companies/throttle.py` already makes.
UNKNOWN_IDENT = 'unknown'


class TrustedIdentThrottleMixin:
    """
    Mix in BEFORE the DRF throttle class so this `get_ident` wins.

    Every throttle that keys on a client address should use this. A throttle
    keyed on `super().get_ident()` is counting a string the caller can change.
    """

    def get_ident(self, request):  # noqa: D102 - overrides DRF
        return client_origin.client_ip(request) or UNKNOWN_IDENT


class TrustedAnonRateThrottle(TrustedIdentThrottleMixin, AnonRateThrottle):
    """
    DRF's `AnonRateThrottle`, keyed on the real client.

    Registered in `DEFAULT_THROTTLE_CLASSES` in place of the stock class. The
    stock one is not wrong in general — it is wrong *behind this topology*,
    where its identity is the concatenated forwarded chain.

    Same `anon` scope and rate: this changes WHO is counted, not HOW MANY.
    """
