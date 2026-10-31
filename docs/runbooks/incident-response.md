# Runbook — Incident Response

**Mechanics live elsewhere and are not repeated here:** deploy, rollback,
database-failure and environment-variable procedure are in
`docs/operations/PRODUCTION_RUNBOOK.md`. This document covers *classification,
roles and communication* — deciding what is happening and who does what.

## Constraints that shape every incident here

Stated first because they determine what responses are actually available:

- **Single web instance**, no horizontal scaling, no zero-downtime deploy.
- **No read replica and no failover** — a database outage is a full outage.
- **No staging environment** — changes go from CI to production.
- **No uptime monitoring** beyond Render's own health check, so *detection is
  usually a human noticing*.
- **Error tracking**: `core/sentry_setup.py` is complete and `sentry-sdk` is
  pinned. `SENTRY_DSN` is reported as configured in the Render dashboard.
  It is deliberately absent from `render.yaml` — a DSN is a dashboard-managed
  secret, and its absence from the blueprint says nothing about whether it is
  set. Repository inspection cannot verify dashboard values either way, so
  during an incident confirm in Sentry itself that events are arriving before
  concluding that silence means no errors.

## Severity

| level | meaning | examples | response |
|---|---|---|---|
| **SEV1** | Public site down, or **wrong data published** | 5xx on `/`, a score shown for an organisation with no evidence | Drop everything. Roll back first, diagnose after. |
| **SEV2** | Core function broken, site up | AI gateway failing every request, ingestion stalled, `/readyz/` 503 while `/healthz/` 200 | Same day. |
| **SEV3** | Degraded or cosmetic | one Labs surface erroring, slow page | Next working day. |

**A published-but-unevidenced score is SEV1, not SEV3.** It is the one failure
this platform is built to prevent: it is silent, it looks like normal
operation, and it damages the claim the product rests on. Availability
incidents announce themselves; this one does not.

## Roles

At current team size one person usually holds all three. Naming them separately
still matters — it is a checklist against forgetting the non-technical half.

- **Incident lead** — decides severity, decides rollback, owns the timeline.
- **Comms** — tells affected users what is true so far.
- **Scribe** — records timestamps and commands as they happen, not afterwards.

## First ten minutes

1. **Establish what is actually broken.** `/healthz/` answers `200` without
   touching the database, so a green liveness probe is **not** evidence the
   system is healthy. Use readiness and a real query path:

   ```
   curl -s -o /dev/null -w '%{http_code}\n' https://ecoiq.uk/healthz/
   curl -s https://ecoiq.uk/readyz/
   curl -s -o /dev/null -w '%{http_code}\n' https://ecoiq.uk/api/v2/companies/
   ```

   `/healthz/` 200 + `/readyz/` 503 means the process is fine and a dependency
   is not — do not restart the service; that fixes nothing and loses state.
2. **Declare severity out loud** and write down the time.
3. **Decide rollback within the first ten minutes.** If the last deploy is a
   plausible cause, roll back before diagnosing — see PRODUCTION_RUNBOOK.
   Diagnosis is cheaper on a healthy system.
4. **Record the correlation id** from any failing request. Every request logs a
   `request_id` (`core/logging_middleware.py`); it is how a report becomes a
   log line.

## Evidence-integrity incidents

If the suspicion is that something untrue was published, the priority is
**stop publishing, then investigate** — not the other way round.

1. Identify the affected organisations and capture the payload *as served*.
2. Check the gate directly — `companies.eligibility.decide(profile)` is the
   single place that decides publishability:

   ```
   python manage.py shell -c "
   from companies.models import Company
   from companies.eligibility import decide
   c = Company.objects.get(slug='<slug>')
   print(decide(c))
   "
   ```

3. If the gate says not-publishable but the surface published anyway, that is a
   **serving** bug (cache, serializer, or a panel rendering a null as a value).
   Check caching first — see `docs/architecture/reliability.md`.
4. If the gate itself says publishable and it should not have, that is a
   **methodology or evidence** bug: capture the formula, methodology and
   evidence versions before changing anything, because a rerun overwrites them.
5. Do not "correct" a score by editing data. Fix the cause, then rerun, so the
   provenance trail records what happened.

## After the incident

Blameless, and short enough to actually get written:

- What a user experienced, and for how long.
- Detection: how it was noticed, and how long that took.
- Cause, and the decision or gap that allowed it.
- What was changed, including "nothing".
- **One** concrete follow-up, with an owner.

Prefer one fix that lands over five that do not.
