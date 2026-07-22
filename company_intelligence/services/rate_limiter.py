"""
company_intelligence/services/rate_limiter.py — feat/global-stewardship-
universe (PR 15), Section 17: "scale safely" — bounded expansion controls
for the batch refresh path (batch size, per-domain rate limits, source-type
limits per run).

Architecture audit finding (Task #169): before this module, the ONLY
outbound throttling anywhere in the repo was a hardcoded
`time.sleep(0.12)` local to companies/management/commands/
ingest_companies_house.py, and the two existing "throttle" modules
(companies/throttle.py, api/throttles.py) are both INBOUND request rate
limiters for EcoIQ's own views/API, unrelated to outbound fetches this app
makes to SEC EDGAR/Companies House/company websites. This module is the
first real, reusable, OUTBOUND per-domain limiter — every future outbound
fetch loop should call wait_for_domain_slot() before fetching, rather than
adding another local sleep() constant.

Deliberately process-local, in-memory state (a plain module-level dict) —
the same tradeoff the pre-existing ingest_companies_house.py sleep already
made (no cross-process/cross-worker coordination). This is a synchronous,
single-worker Django app (see CLAUDE.md) — a distributed rate limiter
(Redis, etc.) would be a real architecture change this PR was never asked
to make, and would be pure speculative complexity for a codebase that does
not run multiple worker processes today.
"""
import time

DEFAULT_MIN_INTERVAL_SECONDS = 1.0

# Regulatory APIs have their own documented rate limits (Companies House:
# 600 req/min = well under 1s apart; SEC EDGAR asks for <=10 req/sec but
# recommends much slower for courtesy) — 1s/domain is deliberately
# conservative for every domain, matching this PR's "NOT maximum scraping"
# discipline rather than tuning per-provider to shave off milliseconds.

DEFAULT_MAX_SOURCE_TYPE_PER_RUN = 20
# SEC EDGAR/Companies House registrations are typically one filing per
# company per refresh — capped low so a single mis-registered company
# can never dominate a shared per-run budget.
MAX_SOURCES_PER_TYPE_PER_RUN = {
    'sec_edgar': 5,
    'companies_house': 5,
}

DEFAULT_BATCH_SIZE = 25

_last_request_at = {}


def wait_for_domain_slot(domain, min_interval_seconds=None):
    """
    Blocks (time.sleep) just long enough that two requests to the same
    domain are never closer together than min_interval_seconds. A domain
    never seen before never blocks. Different domains never block each
    other — this bounds load on any ONE external provider without slowing
    down a refresh that touches many different domains.

    min_interval_seconds defaults to the module-level DEFAULT_MIN_INTERVAL_
    SECONDS looked up BY NAME on every call (not bound as a function
    default at import time) specifically so the test suite can override
    `rate_limiter.DEFAULT_MIN_INTERVAL_SECONDS = 0` once and have every
    refresh-orchestrator test run at full speed, without a real production
    codepath ever needing to know tests exist.
    """
    if not domain:
        return
    if min_interval_seconds is None:
        min_interval_seconds = DEFAULT_MIN_INTERVAL_SECONDS
    now = time.monotonic()
    last = _last_request_at.get(domain)
    if last is not None:
        remaining = min_interval_seconds - (now - last)
        if remaining > 0:
            time.sleep(remaining)
    _last_request_at[domain] = time.monotonic()


def reset_for_tests():
    """Test-only — clears process-local rate-limit state between test cases."""
    _last_request_at.clear()


class SourceTypeBudget:
    """
    Per-run cap on how many sources of a given type get fetched (Section
    17's "source-type limits"). Never a silent throttle: every skip is
    counted by the caller via the bool return value, never swallowed.
    """

    def __init__(self, limits=None, default_limit=DEFAULT_MAX_SOURCE_TYPE_PER_RUN):
        self.limits = dict(MAX_SOURCES_PER_TYPE_PER_RUN)
        if limits:
            self.limits.update(limits)
        self.default_limit = default_limit
        self._counts = {}

    def allow(self, source_type):
        limit = self.limits.get(source_type, self.default_limit)
        count = self._counts.get(source_type, 0)
        if count >= limit:
            return False
        self._counts[source_type] = count + 1
        return True


def bounded_batch(profiles, limit=None, default_batch_size=None):
    """
    Section 17's batch-size bound: an explicit --limit always wins;
    absent that, default_batch_size caps a --due-only/all-active run so a
    single invocation never silently tries to refresh an unbounded number
    of companies in one process. Returns (bounded_list, dropped_count) —
    the caller must report dropped_count rather than pretending the batch
    covered everything.

    default_batch_size defaults to the module-level DEFAULT_BATCH_SIZE
    looked up BY NAME on every call (not bound as a function default at
    import time) — same test-overridability discipline as
    wait_for_domain_slot()'s DEFAULT_MIN_INTERVAL_SECONDS above.
    """
    if default_batch_size is None:
        default_batch_size = DEFAULT_BATCH_SIZE
    effective_limit = limit if limit is not None else default_batch_size
    profiles = list(profiles)
    if len(profiles) <= effective_limit:
        return profiles, 0
    return profiles[:effective_limit], len(profiles) - effective_limit
