"""
EcoIQ Sitemaps — companies/sitemaps.py

Registered in ecoiq/urls.py and served at /sitemap.xml.

A SITEMAP IS A REQUEST TO INDEX
-------------------------------
So it must agree with what the page itself says. A company page whose
assessment is not publishable carries `noindex` (see core/spa.company_spa_view),
and submitting a noindex URL in a sitemap is a direct contradiction — Search
Console reports it as an error, and every such URL spends crawl budget to be
told not to index.

This sitemap therefore lists only companies whose assessment is genuinely
publishable, using the SAME gate every other surface asks. Today that is zero
of 467, so /sitemap.xml contains the static pages and nothing else. That is the
correct answer, not a broken one: EcoIQ is not currently asking anyone to index
a company page, because it is not currently publishing anything on one.
"""
from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from league.models import Company


class CompanySitemap(Sitemap):
    """One URL per company with a PUBLISHABLE assessment."""
    changefreq = 'monthly'
    priority = 0.8

    def items(self):
        from companies.eligibility import publishable_company_ids

        candidates = list(
            Company.objects
            .filter(profile__status__in=('public', 'verified'))
            .select_related('profile')
            .distinct()
        )
        # Bounded by one query against the provenance table before the
        # per-company decision runs — see publishable_company_ids. Without that
        # bound this is two queries per company on a 467-row estate.
        publishable = publishable_company_ids(candidates)
        return [company for company in candidates
                if company.pk in publishable]

    def location(self, obj):
        return f'/companies/{obj.slug}/'


class StaticSitemap(Sitemap):
    """High-priority static pages."""
    priority = 0.9
    changefreq = 'weekly'

    #: Named URLs, so the list survives a route moving. Every entry is a page
    #: that exists, is public, and says something EcoIQ can support.
    _pages = [
        'home',
        'intelligence',
        'companies:directory',
        'projects_site:index',
        'tours',
        'khalifa_stewardship_tours',
        'about',
        'contact',
        'trust',
        'pricing',
        # The public-sector page. It states what EcoIQ can support on its
        # face, so it is indexable and asked for. There is only one URL to
        # list: the borough demonstration and the procurement detail are
        # sections of it, which is also why no separate demo URL can end up
        # in a search result carrying fictitious figures without its notice.
        'public_sector',
        'countries:directory',
        # 'methodology' is gone: it is a 301 to /trust/ now, and a sitemap
        # entry that redirects asks a crawler to fetch two URLs to reach one
        # page. /trust/ is listed above in its own right.
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
