# ADR 0001 — Resolving the trusted client origin behind Render

**Status:** accepted, 2026-08-07

## Context

Rate limiting was correct in code and ineffective in production. 66 probe
requests against a 10-per-minute endpoint produced zero 429s.

`TRUSTED_PROXY_COUNT` was set to 1 on the assumption that Render puts exactly
one proxy in front of the application. The assumption was never verified.

## Measurement

Rather than guess a replacement, the topology was measured with a temporary
diagnostic that reported hop **classifications**, never addresses. Probes
carried RFC 5737 TEST-NET-3 entries, which never appear in real traffic, so any
hop in that range is provably one the probe wrote.

| Probe | Hops | Classes |
|---|---|---|
| no forwarding header | 2 | `public, public` |
| 1 forged entry | 3 | `testnet, public, public` |
| 3 forged entries | 5 | `testnet, testnet, testnet, public, public` |

Identical on `ecoiq.uk` and `ecoiq.onrender.com`. `REMOTE_ADDR` was a private
Render address every time.

The infrastructure appends exactly **two** entries:

```
[ client-supplied entries ... , real client , Cloudflare edge ]
                                ^^^^^^^^^^^ index -2
```

Cloudflare appends the address it received the connection from — the real
client. Render's router then appends the address it received from — the
Cloudflare edge.

Separately, a probe supplying `CF-Connecting-IP` was rejected by Cloudflare with
`HTTP 403, error code: 1000` before reaching the origin. That header therefore
cannot be client-forged.

## Why the old value broke rate limiting

With one trusted hop the resolver selected index -1: the **Cloudflare edge**.
Not forgeable, so not a spoofing hole — but Cloudflare answers from a large
rotating edge fleet, so consecutive requests from one person landed on different
edge addresses and therefore in different buckets. Counters never accumulated.

The failure mode was not "attacker bypasses the limit". It was "the limit never
counts anything", which is quieter and was only visible as an absence of 429s.

## Options considered

**A — fixed trusted hop count.** Matches the measurement, simple, testable.
Brittle if the chain changes: a new CDN silently shifts which entry is selected.

**B — walk in from the right, skipping private hops.** Attractive, but wrong
here. The entry Render appends is the *Cloudflare edge*, which is public, so
this selects the edge exactly as the broken configuration did. Rejected on
evidence.

**C — trust a header the edge guarantees.** `CF-Connecting-IP` is set by
Cloudflare and cannot be supplied by a client. Independent of chain length.

## Decision

Both A and C, each explicit, C preferred.

- `TRUSTED_CLIENT_IP_HEADER` names a header whose value the edge guarantees.
  Defaults to `CF-Connecting-IP` in production, empty elsewhere. Naming a header
  is an explicit assertion about the deployment.
- `TRUSTED_PROXY_COUNT` is the fallback and the answer for deployments without a
  CDN. Now **2** in production, from the measurement above.
- If the chain is shorter than the trusted count the resolver **fails closed**
  and returns no origin. It does not fall back to `REMOTE_ADDR`: that is the
  private Render address, identical for every visitor, so the fallback would
  merge all traffic into one bucket while looking like success.
- An unknown origin gets its own bounded shared bucket rather than escaping the
  limit.

Adding or removing a CDN requires a configuration change, and
`safe_origin_context()` emits `forwarded_hop_count` alongside
`trusted_proxy_count` so a mismatch is visible in the data.

## Correlation

`origin_fingerprint()` is a keyed HMAC-SHA256, truncated, prefixed with a key
version. Not a bare SHA-256 — the IPv4 space is small enough to enumerate, so an
unkeyed digest of an address is reversible in seconds.

The key is `REQUEST_ORIGIN_HMAC_KEY`, deliberately separate from `SECRET_KEY`:
rotating `SECRET_KEY` invalidates sessions and signed tokens, so nobody rotates
it to expire abuse correlation. There is no literal fallback — absent in
production, fingerprinting switches off and says so.

## Consequences

Raw addresses are never logged or stored by this module. Fingerprints live in
application logs (platform retention) and cache keys (expiring with their
rate-limit window, at most 24h). Rotating the key or bumping the version
invalidates all prior correlation, which is the intended way to expire it.
