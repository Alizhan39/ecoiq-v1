"""
EcoIQ Sitemaps — companies/sitemaps.py

Registered in ecoiq/urls.py and served at /sitemap.xml.
Tells Google and other crawlers about all public company profiles
plus the main static pages.
"""
from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from league.models import Company


class CompanySitemap(Sitemap):
    """One URL per public company profile."""
    changefreq = 'monthly'
    priority = 0.8

    def items(self):
        # Only companies that have a public/verified CompanyProfile
        # Related name on CompanyProfile → Company is 'profile'
        return Company.objects.filter(
            profile__status__in=('public', 'verified')
        ).distinct()

    def location(self, obj):
        return f'/companies/{obj.slug}/'


class StaticSitemap(Sitemap):
    """High-priority static pages."""
    priority = 0.9
    changefreq = 'weekly'

    _pages = [
        'home',
        'companies:directory',
        'countries:directory',
        'methodology',
        'pricing',
        'about',
        'api_docs',
        # GCC investor SEO pages — English + Arabic
        'gcc_investors:hub_en',
        'gcc_investors:hub_ar',
        'gcc_investors:qatar_en',
        'gcc_investors:qatar_ar',
        'gcc_investors:saudi_en',
        'gcc_investors:saudi_ar',
        'gcc_investors:kuwait_en',
        'gcc_investors:kuwait_ar',
    ]

    def items(self):
        return self._pages

    def location(self, item):
        return reverse(item)
