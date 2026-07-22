"""
company_intelligence/services/known_sources.py — feat/stewardship-universe
(PR 13): the ONE place EcoIQ's curated, staff-verified official-source
registry lives.

Per the brief's own instruction ("if search-engine/API credentials are
unavailable, build the provider abstraction honestly and implement only
methods that can be verified now — no fake search results"), this repo has
no web-search API integration. Automated "discovery" here means exactly
three honest things:

1. A company has a stable regulatory identifier already mapped
   (US_COMPANY_CIKS / UK_COMPANY_NUMBERS) — SEC EDGAR / Companies House are
   real, deterministic, tier-1 sources.
2. A company's official sustainability/ESG report URL has been manually
   verified reachable on the company's own domain by a human during
   development (this dict — moved here, unchanged in content, from
   ingest_real_sustainability_evidence.py so BOTH that command and the new
   source-discovery service read the exact same curated list, never a
   second, possibly-drifting copy).
3. A staff member has already typed a URL into an existing CompanyProfile
   field (annual_report_url / sustainability_report_url) or the Register
   Document Source form — real, but NOT independently verified by EcoIQ,
   so it is surfaced as PROBABLE domain status requiring approval, never
   silently trusted as Tier 1/2.

No generic web crawling, no guessed domains, no third-party search API.
"""

KNOWN_SUSTAINABILITY_DOCUMENTS = {
    'apple': {
        'url': 'https://www.apple.com/environment/pdf/Apple_Environmental_Progress_Report_2024.pdf',
        'document_type': 'sustainability_report', 'publisher': 'Apple Inc.', 'domain': 'apple.com',
    },
    'microsoft': {
        'url': 'https://www.microsoft.com/en-us/corporate-responsibility/sustainability',
        'document_type': 'sustainability_report', 'publisher': 'Microsoft Corporation', 'domain': 'microsoft.com',
    },
    'walmart': {
        'url': 'https://corporate.walmart.com/purpose/sustainability',
        'document_type': 'sustainability_report', 'publisher': 'Walmart Inc.', 'domain': 'walmart.com',
    },
    # feat/global-stewardship-universe (PR 15) — three additional real
    # companies, each independently verified reachable (real HTTP 200,
    # checked live via the browser tool, not guessed) during this PR's own
    # development, matching the exact discipline PR11 established for the
    # three entries above.
    'exxonmobil': {
        'url': 'https://corporate.exxonmobil.com/publications/sustainability',
        'document_type': 'sustainability_report', 'publisher': 'Exxon Mobil Corporation', 'domain': 'exxonmobil.com',
    },
    'coca-cola': {
        'url': 'https://www.coca-colacompany.com/about-us/environment',
        'document_type': 'sustainability_report', 'publisher': 'The Coca-Cola Company', 'domain': 'coca-colacompany.com',
    },
    'national-grid': {
        'url': 'https://www.nationalgrid.com/responsibility',
        'document_type': 'sustainability_report', 'publisher': 'National Grid plc', 'domain': 'nationalgrid.com',
    },
}

# Real, manually-verified official domains for companies this repo already
# has identity data for (companies/management/commands/ingest_sec_edgar.py
# / ingest_companies_house.py) — used ONLY to mark an already-known source
# URL's domain_status as VERIFIED when it matches; never used to guess a
# URL that hasn't actually been found/registered some other way.
KNOWN_OFFICIAL_DOMAINS = {
    'apple': 'apple.com',
    'microsoft': 'microsoft.com',
    'walmart': 'walmart.com',
    'tesla': 'tesla.com',
    'exxonmobil': 'exxonmobil.com',
    'coca-cola': 'coca-colacompany.com',
    'national-grid': 'nationalgrid.com',
}


def domain_of(url):
    from urllib.parse import urlparse
    host = (urlparse(url).hostname or '').lower()
    return host[4:] if host.startswith('www.') else host


def domain_status_for(company_slug, url):
    """VERIFIED only when the URL's domain matches this company's curated,
    manually-confirmed official domain — PROBABLE otherwise (a real URL,
    just not independently cross-checked by EcoIQ)."""
    known = KNOWN_OFFICIAL_DOMAINS.get(company_slug)
    return 'verified' if known and domain_of(url) == known else 'probable'
