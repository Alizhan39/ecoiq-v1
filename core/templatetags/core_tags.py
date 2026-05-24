"""
core_tags — custom template filters for the core app and landing page.
"""
from django import template

register = template.Library()


@register.filter(name='split')
def split_string(value, delimiter=','):
    """Split a string by delimiter and return a list of stripped parts.

    Usage:  {{ "a,b,c"|split:"," }}
    """
    if not isinstance(value, str):
        return []
    return [part.strip() for part in value.split(delimiter) if part.strip()]
