"""LegacySafe AI — audit logging. Every retrieval, block, and revocation is recorded."""
from legacy_safe.models import AuditLog


def log_event(user=None, action='', question='', decision='', allowed_sources=None,
              blocked_sources=None, reason=''):
    return AuditLog.objects.create(
        user=user if (user is not None and getattr(user, 'is_authenticated', False)) else None,
        action=action,
        question=question,
        decision=decision,
        allowed_sources=allowed_sources or [],
        blocked_sources=blocked_sources or [],
        reason=reason,
    )
