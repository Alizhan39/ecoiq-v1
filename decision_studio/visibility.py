"""
decision_studio/visibility.py — whose question is this?

A DecisionQuery records `session_key` and `user` because a question belongs to
the visitor who asked it. The studio list has always honoured that: it shows
`filter(session_key=...)`, never the whole table.

The detail view did not. `get_object_or_404(DecisionQuery, pk=query_id)` on
sequential integer ids meant anyone could walk /decision-studio/result/1/,
/2/, /3/ and read every question every visitor and every signed-in user had
ever asked — what they were investigating, which organisations they named.
The list filtered; the row it linked to did not.

One rule, in one place, so the list and the detail view cannot drift apart
again.
"""


def queries_visible_to(request, *, queryset=None):
    """
    The DecisionQuery rows this requester may read.

    Ownership is the session that asked, plus the account if they were signed
    in — an anonymous visitor who later signs in keeps their earlier questions
    through the session key, exactly as the studio list already behaves.

    Staff see everything. They can already read the whole table through Django
    admin, which is where this module's rule would otherwise be silently
    contradicted.
    """
    from django.db.models import Q

    from decision_studio.models import DecisionQuery

    qs = DecisionQuery.objects.all() if queryset is None else queryset
    user = getattr(request, 'user', None)
    if user is not None and user.is_authenticated and user.is_staff:
        return qs

    owner = Q(pk__in=[])          # matches nothing until an owner is proven
    session_key = request.session.session_key
    if session_key:
        owner |= Q(session_key=session_key)
    if user is not None and user.is_authenticated:
        owner |= Q(user=user)
    return qs.filter(owner)
