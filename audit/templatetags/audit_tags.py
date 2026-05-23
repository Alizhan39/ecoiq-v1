from django import template

register = template.Library()


@register.filter
def fmt_usd(value):
    """Format integer as $1,234,567"""
    try:
        return f"${int(value):,}"
    except (TypeError, ValueError):
        return "$0"


@register.filter
def fmt_num(value):
    """Format integer with comma separators"""
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "0"


@register.filter
def fmt_usd_compact(value):
    """Format as $1.2M or $450K for tight spaces"""
    try:
        v = int(value)
        if v >= 1_000_000:
            return f"${v / 1_000_000:.1f}M"
        elif v >= 1_000:
            return f"${v / 1_000:.0f}K"
        return f"${v:,}"
    except (TypeError, ValueError):
        return "$0"
