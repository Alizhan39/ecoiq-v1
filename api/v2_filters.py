"""Explicit, public directory filters for API v2.

Filtering is applied *after* companies.visibility restricts the queryset.
No score-based range filters: unevidenced scores remain in the directory.
"""
import django_filters

from league.models import Company


class CompanyDirectoryFilter(django_filters.FilterSet):
    # Preserve the established case-insensitive exact-match contract.
    sector = django_filters.CharFilter(field_name="sector", lookup_expr="iexact")
    country = django_filters.CharFilter(field_name="country", lookup_expr="iexact")

    class Meta:
        model = Company
        fields = ("sector", "country")
