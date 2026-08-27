"""
companies/visibility.py — who may see which organisation profile.

ONE RULE, ONE PLACE
-------------------
`status__in=('public', 'verified', 'draft')` was written out as a literal in
`api/v2_views.py`, twice in `core/spa.py`, and in a different shape across the
analytics and scoring queries. Two endpoints did not write it at all:
`api/v2_kpi.company_kpi` looked a profile up with no status filter, and
`api/v2_principles.company_principles` copied that when it was added.

The effect was that an ARCHIVED organisation's full evidence chain answered 200
to an anonymous caller on `/api/v2/companies/<slug>/kpis/<id>/` and
`/api/v2/companies/<slug>/principles/`, while `/companies/<slug>/` — the page
built on those endpoints — answered 404 to everybody. A rule enforced in four
places and skipped in two is not a rule.

NOT PUBLIC IS NOT THE SAME AS NOT REVIEWABLE
--------------------------------------------
The other half of the same problem ran the other way. A staff reviewer could not
open an archived organisation's investigation at all, which made the nine
evidence candidates sitting in the review queue impossible to examine in the
workspace they are reviewed for.

So visibility is decided by WHO IS ASKING, not by the surface they happen to be
on: the published statuses for everyone, every status for staff. A profile being
withheld from the public and a profile being unreviewable are different
decisions, and only the first was ever intended.

WHY ARCHIVED IS NOT SIMPLY DELETED
----------------------------------
An archived profile keeps its evidence, its provenance and its review history.
That is the point of archiving rather than deleting — the record survives — and
it is exactly why the record must not be served to anonymous callers as though
it were current.
"""
from __future__ import annotations

from django.shortcuts import get_object_or_404

#: Statuses any caller may see. `draft` is included because it is a
#: work-in-progress profile that the product deliberately shows; `archived` is
#: not, because it is a withdrawn one.
PUBLICLY_VISIBLE_STATUSES = ('public', 'verified', 'draft')


def can_see_every_status(user) -> bool:
    """
    Staff see archived profiles. Deliberately `is_staff` rather than a bespoke
    permission: it is the same gate the Evidence Review Workbench already uses,
    and a second, subtly different notion of "reviewer" is how two answers to
    one question start.
    """
    return bool(user and user.is_authenticated and user.is_staff)


def visible_statuses(user) -> tuple[str, ...] | None:
    """
    The statuses this user may see, or None meaning "no restriction".

    None rather than a list of every status, so a caller cannot accidentally
    filter on a stale enumeration if a status is added later.
    """
    return None if can_see_every_status(user) else PUBLICLY_VISIBLE_STATUSES


def profile_for(slug: str, user=None, *, queryset=None):
    """
    The CompanyProfile for `slug` that this user is allowed to see, or 404.

    404 rather than 403 for a profile the caller may not see: whether an
    archived organisation exists is itself not public, and a 403 would confirm
    it. A staff caller gets the profile, which is what makes an archived
    organisation reviewable internally.
    """
    from companies.models import CompanyProfile

    queryset = queryset if queryset is not None else CompanyProfile.objects.all()
    statuses = visible_statuses(user)
    if statuses is not None:
        queryset = queryset.filter(status__in=statuses)
    return get_object_or_404(queryset, company__slug=slug)
