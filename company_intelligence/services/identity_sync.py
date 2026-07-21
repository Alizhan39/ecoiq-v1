"""
company_intelligence/services/identity_sync.py — feat/global-stewardship-
universe (PR 15): makes company identity provenance inspectable.

Before this PR, a company's real regulatory identifiers (SEC CIK,
Companies House number) and its curated official domain existed ONLY as
hardcoded Python dicts — real data, but nowhere a UI or database query
could show "here is exactly which real identifier backs this company's
tracking." This module reads those SAME existing dicts (never a second,
independently-maintained identity source) and writes them onto a real,
queryable companies.models.CompanyListing row.

sync_company_identity() is idempotent and additive-only: it never
overwrites a field a human has since edited by hand unless that field is
still blank, and it never invents an identifier a company genuinely
doesn't have a mapping for.
"""
from django.utils import timezone

from company_intelligence.services import known_sources


def identity_sources_for_slug(slug):
    """
    Returns {'sec_cik', 'companies_house_number', 'official_domain',
    'domain_status', 'identity_source'} — every value is either real
    (from an existing, already-proven mapping) or blank/None. Never
    guesses an identifier from the company's name.
    """
    from companies.management.commands.ingest_companies_house import UK_COMPANY_NUMBERS
    from companies.management.commands.ingest_sec_edgar import US_COMPANY_CIKS

    cik = US_COMPANY_CIKS.get(slug)
    ch_number = UK_COMPANY_NUMBERS.get(slug)
    official_domain = known_sources.KNOWN_OFFICIAL_DOMAINS.get(slug, '')

    sources = []
    if cik:
        sources.append('SEC EDGAR CIK mapping')
    if ch_number:
        sources.append('Companies House number mapping')
    if official_domain:
        sources.append('EcoIQ-curated official domain registry')

    return {
        'sec_cik': cik or '',
        'companies_house_number': ch_number or '',
        'official_domain': official_domain,
        'domain_status': 'verified' if official_domain else '',
        'identity_source': '; '.join(sources),
    }


def sync_company_identity(company_profile, *, is_primary=True):
    """
    Populates (or reuses) this company's primary CompanyListing row from
    the existing identity mappings. Returns the CompanyListing instance,
    or None if genuinely no real identifier is known for this company
    (never creates an empty placeholder row).
    """
    from company_intelligence.models import CompanyListing

    slug = company_profile.company.slug
    identity = identity_sources_for_slug(slug)

    if not identity['identity_source']:
        return None

    listing, created = CompanyListing.objects.get_or_create(
        company=company_profile.company, is_primary=is_primary,
        defaults={'source': identity['identity_source']},
    )

    update_fields = []
    for field in ('sec_cik', 'companies_house_number', 'official_domain', 'domain_status', 'identity_source'):
        new_value = identity[field]
        if new_value and not getattr(listing, field):
            setattr(listing, field, new_value)
            update_fields.append(field)

    listing.verified_at = timezone.now()
    update_fields.append('verified_at')
    # BUG FIX (found via real `expand_stewardship_universe --limit 3` run,
    # not just unit tests): get_or_create's `defaults` only ever persists
    # the 'source' field for a brand-new row — sec_cik/official_domain/etc
    # were being setattr'd onto the in-memory object above but never saved
    # when created=True, since save() was previously gated on `not
    # created`. A save is required in BOTH cases whenever there are real
    # fields to persist.
    listing.save(update_fields=update_fields)
    return listing
