"""Template helpers for the portfolio dashboard — pure presentation, no DB access."""
from django import template

register = template.Library()


@register.filter
def get_item(mapping, key):
    """Dict lookup by a variable key — Django templates have no built-in for this."""
    if mapping is None:
        return None
    return mapping.get(key)


@register.inclusion_tag('investor_portfolio/_watchlist_control.html', takes_context=True)
def watchlist_controls(context, company):
    """
    Renders the 'Add to watchlist' / 'Remove from watchlist' control used on
    companies/detail.html and companies/stock_profile.html. Lives here (not
    in the companies app) so companies — a foundational app — never has to
    import investor_portfolio; the dependency runs the other way, via this
    template tag being {% load %}ed from companies' own templates.
    """
    request = context.get('request')
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {
            'company': company, 'authenticated': False,
            'login_url': f"/login/?next={request.path if request else ''}",
        }

    from investor_portfolio.models import Watchlist, WatchlistItem

    watchlists = Watchlist.objects.filter(owner=user).order_by('name')
    member_of_ids = set(
        WatchlistItem.objects.filter(watchlist__owner=user, company=company).values_list('watchlist_id', flat=True)
    )
    return {
        'company': company, 'authenticated': True,
        'watchlists': watchlists, 'member_of_ids': member_of_ids,
        'next': request.path if request else '',
    }
