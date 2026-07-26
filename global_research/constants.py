"""
global_research/constants.py — shared vocabularies for the Global Research,
Technology & Manufacturer Discovery Engine.

`EVIDENCE_TIER_BY_SOURCE_TYPE` adapts `harvester.verification.SOURCE_TIER_BY_TYPE`'s
4-tier hierarchy to this module's own source-type vocabulary (peer-reviewed
paper, patent, manufacturer documentation, ...) rather than harvester's
company-filing vocabulary (annual report, SEC EDGAR, ...) — see
docs/adr/ADR-global-research-engine.md decision 3.
"""

SOURCE_TYPE_CHOICES = [
    ('peer_reviewed_paper', 'Peer-Reviewed Paper'),
    ('patent', 'Patent'),
    ('technical_standard', 'Technical Standard'),
    ('government_publication', 'Government Publication'),
    ('regulator_publication', 'Regulator Publication'),
    ('manufacturer_documentation', 'Manufacturer Documentation'),
    ('product_datasheet', 'Product Datasheet'),
    ('engineering_case_study', 'Engineering Case Study'),
    ('university_report', 'University Report'),
    ('independent_test_report', 'Independent Test Report'),
    ('tender', 'Tender'),
    ('public_procurement_record', 'Public Procurement Record'),
    ('conference_paper', 'Conference Paper'),
    ('certification_record', 'Certification Record'),
    ('news_article', 'News Article'),
    ('distributor_listing', 'Distributor Listing'),
    ('commercial_database', 'Commercial Database'),
    ('other', 'Other'),
]

EVIDENCE_TIER_CHOICES = [('A', 'Tier A'), ('B', 'Tier B'), ('C', 'Tier C'), ('D', 'Tier D')]

# Ceiling tier per source type — a peer-reviewed paper is upgraded from B to
# A only when ResearchSource.independently_reproduced=True (see
# services/evidence_scoring.py), never assumed.
EVIDENCE_TIER_BY_SOURCE_TYPE = {
    'regulator_publication': 'A',
    'certification_record': 'A',
    'independent_test_report': 'A',
    'government_publication': 'A',
    'technical_standard': 'A',
    'peer_reviewed_paper': 'B',
    'patent': 'B',
    'engineering_case_study': 'B',
    'university_report': 'B',
    'conference_paper': 'B',
    'public_procurement_record': 'B',
    'manufacturer_documentation': 'C',
    'product_datasheet': 'C',
    'distributor_listing': 'C',
    'tender': 'C',
    'news_article': 'D',
    'commercial_database': 'D',
    'other': 'D',
}
DEFAULT_EVIDENCE_TIER = 'D'

SOURCE_OWNER_TYPE_CHOICES = [
    ('vendor', 'Vendor'),
    ('independent', 'Independent'),
    ('regulator', 'Regulator'),
    ('academic', 'Academic'),
    ('government', 'Government'),
    ('distributor', 'Distributor'),
    ('unknown', 'Unknown'),
]

VENDOR_OWNER_TYPES = {'vendor', 'distributor'}

LANGUAGE_CHOICES = [
    ('en', 'English'),
    ('ru', 'Russian'),
    ('kk', 'Kazakh'),
    ('ar', 'Arabic'),
    ('zh', 'Chinese'),
    ('fr', 'French'),
    ('de', 'German'),
    ('tr', 'Turkish'),
    ('other', 'Other'),
]

COMPATIBILITY_STATUS_CHOICES = [
    ('compatible', 'Compatible'),
    ('conditional', 'Conditional'),
    ('incompatible', 'Incompatible'),
    ('insufficient_data', 'Insufficient Data'),
]

VERIFICATION_STATUS_CHOICES = [
    ('unverified', 'Unverified'),
    ('self_declared', 'Self-Declared'),
    ('evidence_supported', 'Evidence Supported'),
    ('human_reviewed', 'Human Reviewed'),
]
