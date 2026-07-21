"""
company_intelligence/services/refresh_policy.py — feat/stewardship-
universe (PR 13): "check regulatory filings more often than a static
policy document" as an explicit, documented policy table — never one
hardcoded universal interval.

Deliberately NOT a single number: each source TYPE gets its own real
interval, based on how often that class of document genuinely changes in
the real world. A source with no recorded successful fetch yet has no
"last checked" to compute from — is_source_due() honestly treats that as
due immediately (there is nothing to wait on).
"""
import datetime

from django.utils import timezone

# Every source type in harvester.constants.SOURCE_TYPES gets an explicit,
# documented interval here — unmapped types fall back to DEFAULT_INTERVAL_DAYS,
# never a silently different number.
REFRESH_INTERVAL_DAYS = {
    # Regulatory filings — quarterly cadence in the real world (10-Q/10-K,
    # Companies House confirmation statements/accounts).
    'sec_edgar': 90,
    'companies_house': 90,
    'fca_filing': 90,
    'regulatory_filing': 90,
    'ofgem': 90,
    'environment_agency': 90,
    # Official annual/sustainability/ESG/TCFD reports — published on an
    # annual cycle; checking twice a year catches a new edition without
    # hammering a source that only changes once a year.
    'annual_report': 180,
    'sustainability_report': 180,
    'esg_report': 180,
    'tcfd_report': 180,
    # Longer-horizon strategic documents — genuinely static for years at a
    # time between major revisions.
    'transition_plan': 270,
    # Self-reported/marketing pages — lower authority, lower refresh
    # urgency; still checked, just not aggressively.
    'investor_relations': 120,
    'company_website': 120,
    'press_release': 30,
    'csv_dataset': 30,
}
DEFAULT_INTERVAL_DAYS = 180

# A source that failed its last attempt is retried sooner than its normal
# interval — a transient 500/timeout shouldn't wait a full quarter to be
# tried again, but also shouldn't be hammered every refresh cycle either.
FAILED_SOURCE_RETRY_DAYS = 14


def interval_days_for(source_type):
    return REFRESH_INTERVAL_DAYS.get(source_type, DEFAULT_INTERVAL_DAYS)


def next_refresh_due_for_source(source):
    """
    None means "due now" (no successful fetch on record yet, or its last
    attempt failed more than FAILED_SOURCE_RETRY_DAYS ago) — a source
    never sits at "no due date" once it exists; it's either due at a real
    computed timestamp, or due immediately.
    """
    if source.last_failure_at and (not source.last_success_at or source.last_failure_at > source.last_success_at):
        return source.last_failure_at + datetime.timedelta(days=FAILED_SOURCE_RETRY_DAYS)
    if not source.last_success_at:
        return None
    return source.last_success_at + datetime.timedelta(days=interval_days_for(source.source_type))


def is_source_due(source, *, now=None):
    now = now or timezone.now()
    due_at = next_refresh_due_for_source(source)
    return due_at is None or due_at <= now


def company_next_refresh_due_at(company_profile):
    """
    The EARLIEST due date among this company's active sources — refreshing
    a company means checking every source, so the company as a whole is
    due the moment its soonest-due source is due. None when the company
    has no active sources at all (nothing to schedule yet — see
    NEEDS_SOURCE_DISCOVERY in stewardship_state.py).
    """
    due_dates = []
    any_immediately_due = False
    for source in company_profile.harvest_sources.filter(is_active=True):
        due_at = next_refresh_due_for_source(source)
        if due_at is None:
            any_immediately_due = True
        else:
            due_dates.append(due_at)

    if any_immediately_due:
        return timezone.now()
    if not due_dates:
        return None
    return min(due_dates)


def is_company_due_for_refresh(company_profile, *, now=None):
    now = now or timezone.now()
    due_at = company_next_refresh_due_at(company_profile)
    return due_at is not None and due_at <= now
