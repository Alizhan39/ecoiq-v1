"""
company_intelligence/services/source_discovery.py — feat/stewardship-
universe (PR 13): "Company -> discover authoritative sources" — the actual
gap identified by this PR's architecture audit (PR9-12 only ever resolved
identity via hardcoded dicts or a staff member manually typing a URL).

Three honest, deterministic discovery methods (see known_sources.py's own
docstring for why there are only three, and never a fourth "generic web
search" method): SEC EDGAR identity, Companies House identity, and
EcoIQ's own curated official-domain sustainability-document registry.
A fourth, lower-trust method surfaces a company's own pre-existing,
staff-entered CompanyProfile fields (annual_report_url /
sustainability_report_url) as CANDIDATES requiring approval — real URLs,
just never independently verified as the company's true official domain.

Every discovered source is recorded as a DiscoveredSource row — idempotent
by (company, url): re-running discovery never creates a duplicate
candidate for a URL already on file, and a candidate that was previously
approved/rejected/registered is never silently reset back to 'candidate'.
"""
from django.utils import timezone

from company_intelligence.models import DiscoveredSource
from company_intelligence.services.known_sources import (
    KNOWN_SUSTAINABILITY_DOCUMENTS,
    domain_of,
    domain_status_for,
)
from harvester.verification import source_tier


def _get_or_create_candidate(company_profile, *, url, discovery_method, source_type='',
                              publisher='', domain_status='unverified', confidence=None, status='candidate'):
    domain = domain_of(url)
    tier = source_tier(source_type) if source_type else 4
    obj, created = DiscoveredSource.objects.get_or_create(
        company=company_profile, url=url,
        defaults={
            'domain': domain, 'publisher': publisher, 'source_type': source_type, 'tier': tier,
            'discovery_method': discovery_method, 'domain_status': domain_status,
            'confidence': confidence, 'status': status,
        },
    )
    return obj, created


def _discover_sec_edgar(company_profile, slug):
    from companies.management.commands.ingest_sec_edgar import US_COMPANY_CIKS

    cik = US_COMPANY_CIKS.get(slug)
    if not cik:
        return None
    url = f'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=10-K'
    obj, created = _get_or_create_candidate(
        company_profile, url=url, discovery_method='sec_edgar_identity', source_type='sec_edgar',
        publisher='U.S. Securities and Exchange Commission', domain_status='verified', confidence=1.0,
        status='approved',
    )
    return obj


def _discover_companies_house(company_profile, slug):
    from companies.management.commands.ingest_companies_house import UK_COMPANY_NUMBERS

    number = UK_COMPANY_NUMBERS.get(slug)
    if not number:
        return None
    url = f'https://find-and-update.company-information.service.gov.uk/company/{number}'
    obj, created = _get_or_create_candidate(
        company_profile, url=url, discovery_method='companies_house_identity', source_type='companies_house',
        publisher='Companies House', domain_status='verified', confidence=1.0, status='approved',
    )
    return obj


def _discover_curated_document(company_profile, slug):
    doc = KNOWN_SUSTAINABILITY_DOCUMENTS.get(slug)
    if not doc:
        return None
    obj, created = _get_or_create_candidate(
        company_profile, url=doc['url'], discovery_method='curated_official_domain',
        source_type=doc['document_type'], publisher=doc['publisher'],
        domain_status=domain_status_for(slug, doc['url']), confidence=0.9, status='approved',
    )
    return obj


def _discover_staff_entered_fields(company_profile, slug):
    """
    Surfaces annual_report_url/sustainability_report_url IF a staff member
    already set them on this CompanyProfile — real URLs EcoIQ already has
    on file, but never independently domain-verified, so these are always
    CANDIDATES (status='candidate') requiring explicit staff approval
    before being trusted as a registered source, never auto-approved like
    the three methods above.
    """
    found = []
    field_map = {
        'annual_report_url': 'annual_report',
        'sustainability_report_url': 'sustainability_report',
    }
    for field_name, doc_type in field_map.items():
        url = getattr(company_profile, field_name, '') or ''
        if not url:
            continue
        obj, created = _get_or_create_candidate(
            company_profile, url=url, discovery_method='staff_registered_field', source_type=doc_type,
            domain_status=domain_status_for(slug, url), confidence=None, status='candidate',
        )
        found.append(obj)
    return found


def discover_sources_for_company(company_profile):
    """
    Runs every real discovery method for one company and returns the full
    list of DiscoveredSource rows found (created this run or already on
    file — never re-fetches the network; this only consults identity
    mappings and curated/staff-entered data already known to EcoIQ).
    Updates company_profile.last_source_discovery_at unconditionally (even
    if nothing new was found — a discovery attempt genuinely happened).
    """
    slug = company_profile.company.slug
    discovered = []

    edgar = _discover_sec_edgar(company_profile, slug)
    if edgar:
        discovered.append(edgar)

    ch = _discover_companies_house(company_profile, slug)
    if ch:
        discovered.append(ch)

    doc = _discover_curated_document(company_profile, slug)
    if doc:
        discovered.append(doc)

    discovered += _discover_staff_entered_fields(company_profile, slug)

    company_profile.last_source_discovery_at = timezone.now()
    company_profile.save(update_fields=['last_source_discovery_at'])

    return discovered
