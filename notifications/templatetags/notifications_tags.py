from django import template

from notifications.models import AdminNotification

register = template.Library()


@register.simple_tag
def notifications_unread_count():
    """Unread AdminNotification count for the admin header badge / dashboard card."""
    try:
        return AdminNotification.unread_count()
    except Exception:
        return 0
