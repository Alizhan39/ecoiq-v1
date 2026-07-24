"""
capability_graph/services/organisations.py — the ONLY sanctioned way to
create or resolve an Organisation row. Every caller that "finds" an
organisation (from a signal publisher, a company record, a manual staff
entry) MUST go through `get_or_create_organisation()` so the same
real-world org is never duplicated across opportunities/missions — the
exact flat-directory problem this app replaces.
"""
from django.utils.text import slugify

from capability_graph.models import Organisation


def get_or_create_organisation(name, *, org_type='other', jurisdiction='', website='', linked_company=None, notes=''):
    """
    Resolves an organisation by its normalised (name, jurisdiction) key.
    A second call with the same name/jurisdiction always returns the SAME
    row — never a fresh duplicate — regardless of which opportunity,
    mission, or funding match is asking.
    """
    dedupe_key = f'{slugify(name)}::{slugify(jurisdiction)}'
    organisation, created = Organisation.objects.get_or_create(
        dedupe_key=dedupe_key,
        defaults=dict(
            name=name, org_type=org_type, jurisdiction=jurisdiction,
            website=website, linked_company=linked_company, notes=notes,
        ),
    )
    if not created and linked_company is not None and organisation.linked_company_id is None:
        # Additive enrichment only — a later, more-informed caller may
        # supply the real company link an earlier caller didn't have.
        # Never overwrites an existing link with a different one.
        organisation.linked_company = linked_company
        organisation.save(update_fields=['linked_company', 'updated_at'])
    return organisation


def find_organisation(name, *, jurisdiction=''):
    """Read-only lookup — never creates. Returns None if this exact org hasn't been resolved yet."""
    dedupe_key = f'{slugify(name)}::{slugify(jurisdiction)}'
    return Organisation.objects.filter(dedupe_key=dedupe_key).first()
