"""
LegacySafe AI — deterministic, permission-aware access control.

BasedAI alignment: access is enforced BEFORE retrieval, with plain boolean
logic — never by asking an LLM whether a user is "allowed" to see something.
Nothing in this module calls a model. `can_access()` is pure and total: for
any (access_level, roles, is_revoked) triple there is exactly one answer.
"""
DEMO_ROLES = ['public', 'engineering', 'finance', 'executive']

# access_level -> roles allowed to see it (public is implicitly everyone)
_ACCESS_MATRIX = {
    'public':      {'public', 'engineering', 'finance', 'executive'},
    'engineering': {'engineering', 'executive'},
    'finance':     {'finance', 'executive'},
    'executive':   {'executive'},
}


def get_user_roles(user):
    """Map a Django user onto LegacySafe roles via auth groups.

    Superusers are treated as executive (they administer the whole platform).
    Everyone — including anonymous visitors — implicitly holds 'public'.
    """
    roles = {'public'}
    if user is not None and getattr(user, 'is_authenticated', False):
        group_names = set(user.groups.values_list('name', flat=True))
        roles |= (group_names & set(DEMO_ROLES))
        if user.is_superuser:
            roles.add('executive')
    return roles


def can_access(access_level, roles, is_revoked=False):
    """Deterministic access check. No LLM involved, ever.

    access_level: one of ACCESS_LEVEL_CHOICES keys.
    roles: a set of role strings the requester holds (see get_user_roles / DEMO_ROLES).
    is_revoked: True if the source (or the chunk/memory itself) has been revoked.
    """
    if is_revoked:
        return False
    allowed_roles = _ACCESS_MATRIX.get(access_level, set())
    return bool(allowed_roles & set(roles))


def roles_for_demo_role(role):
    """Simulate the role set a single demo persona holds (used by the permission demo page).

    Every persona implicitly has 'public'; naming the role again is harmless
    since sets dedupe, and it keeps the mapping obvious to read.
    """
    return {'public', role} if role != 'public' else {'public'}
