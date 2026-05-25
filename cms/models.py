"""
EcoIQ CMS — Wagtail page models.

Page hierarchy (typical):
  Root
  └── HomePage (/)
      ├── CompanyIndexPage  (/companies/)
      │   ├── CompanyPage   (/companies/qazaqgaz/)
      │   └── CompanyPage   (/companies/kazatomprom/)
      ├── ArticlePage       (/insights/...)
      ├── MethodologyPage   (/methodology/)
      └── AboutPage         (/about/)

All pages are served under /pages/ in this deployment
(to preserve existing Django routes at / /league/ /audit/ etc.)
"""
from django.db import models
from django.utils.text import slugify

from modelcluster.fields import ParentalKey
from wagtail.models import Page, Orderable
from wagtail.fields import RichTextField, StreamField
from wagtail.admin.panels import FieldPanel, MultiFieldPanel, InlinePanel
from wagtail.search import index
from wagtail.images.models import AbstractImage, AbstractRendition, Image

from .blocks import (
    CompanyPageBody,
    ArticlePageBody,
    HomePageBody,
)


# ── HomePage ───────────────────────────────────────────────────────────────────

class HomePage(Page):
    """
    Root landing page — managed entirely through Wagtail CMS.
    Can contain KPI summaries, intro text, and CTAs.
    """
    intro = RichTextField(blank=True, help_text='Lead paragraph shown below the hero title')
    body  = StreamField(HomePageBody(), blank=True, use_json_field=True)

    content_panels = Page.content_panels + [
        FieldPanel('intro'),
        FieldPanel('body'),
    ]

    search_fields = Page.search_fields + [
        index.SearchField('intro'),
    ]

    subpage_types = [
        'cms.CompanyIndexPage',
        'cms.ArticlePage',
        'cms.MethodologyPage',
        'cms.AboutPage',
    ]

    class Meta:
        verbose_name = 'Home Page'

    def get_context(self, request, *args, **kwargs):
        ctx = super().get_context(request, *args, **kwargs)
        # Inject top companies for optional hero widget
        from league.models import Company
        ctx['top_companies'] = Company.objects.order_by('rank')[:4]
        return ctx


# ── CompanyIndexPage ───────────────────────────────────────────────────────────

class CompanyIndexPage(Page):
    """
    Directory listing all editorial CompanyPages.
    Also shows live league ranking from league.Company for browsability.
    """
    intro = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('intro'),
    ]

    subpage_types = ['cms.CompanyPage']

    class Meta:
        verbose_name        = 'Company Index Page'
        verbose_name_plural = 'Company Index Pages'

    def get_context(self, request, *args, **kwargs):
        ctx = super().get_context(request, *args, **kwargs)
        from league.models import Company
        from league.scoring import get_tier
        companies = list(Company.objects.order_by('rank', '-ecoiq_score'))
        for co in companies:
            co.tier = get_tier(float(co.ecoiq_score))
        ctx['companies'] = companies
        return ctx


# ── CompanyPage ────────────────────────────────────────────────────────────────

class CompanyPage(Page):
    """
    Rich editorial page for one Good Deeds League company.
    Combines Wagtail CMS content with live KPI data from league.Company.
    Editors can add narrative, project showcases, evidence, and recommendations.
    """

    # ── Link to structured data ──
    company_slug = models.SlugField(
        max_length=255, blank=True,
        help_text='Slug matching a league.Company record — pulls live scores and projects',
    )

    # ── Hero section ──
    hero_intro = RichTextField(
        blank=True,
        help_text='Lead paragraph shown under the company name in the page header',
    )

    # ── CMS body ──
    body = StreamField(CompanyPageBody(), blank=True, use_json_field=True)

    content_panels = Page.content_panels + [
        MultiFieldPanel([
            FieldPanel('company_slug'),
            FieldPanel('hero_intro'),
        ], heading='Company Link & Hero'),
        FieldPanel('body'),
    ]

    search_fields = Page.search_fields + [
        index.SearchField('hero_intro'),
        index.SearchField('body'),
        index.FilterField('company_slug'),
    ]

    parent_page_types = ['cms.CompanyIndexPage', 'cms.HomePage']

    class Meta:
        verbose_name        = 'Company Page'
        verbose_name_plural = 'Company Pages'

    def get_context(self, request, *args, **kwargs):
        ctx = super().get_context(request, *args, **kwargs)

        ctx['company'] = None
        if self.company_slug:
            try:
                from league.models import Company
                from league.scoring import get_tier
                company = Company.objects.prefetch_related(
                    'projects', 'evidence', 'history',
                ).get(slug=self.company_slug)
                ctx['company'] = company
                ctx['tier']    = get_tier(float(company.ecoiq_score))

                # Pillar breakdown
                ctx['pillars'] = [
                    {'name': 'Pollution',    'score': company.score_pollution_footprint, 'weight': 35},
                    {'name': 'Reduction',    'score': company.score_reduction_progress,  'weight': 25},
                    {'name': 'Investment',   'score': company.score_investment,           'weight': 20},
                    {'name': 'Transparency', 'score': company.score_transparency,         'weight': 10},
                    {'name': 'Community',    'score': company.score_community_impact,     'weight': 10},
                ]

                # Trend chart data (6 months)
                history = list(company.history.order_by('date')[:12])
                ctx['history_labels'] = [str(h.date) for h in history]
                ctx['history_scores'] = [float(h.ecoiq_score) for h in history]

            except Exception:
                pass  # company_slug set but no matching record — graceful fallback

        return ctx


# ── ArticlePage ────────────────────────────────────────────────────────────────

class ArticlePage(Page):
    """News article, analysis piece, or insight report."""

    published_date = models.DateField(null=True, blank=True)
    author         = models.CharField(max_length=255, blank=True)
    intro          = models.TextField(
        blank=True, max_length=500,
        help_text='Short summary (shown in listings, max 500 chars)',
    )
    body = StreamField(ArticlePageBody(), blank=True, use_json_field=True)
    featured_image = models.ForeignKey(
        'wagtailimages.Image',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
    )

    content_panels = Page.content_panels + [
        MultiFieldPanel([
            FieldPanel('published_date'),
            FieldPanel('author'),
        ], heading='Publication Info'),
        FieldPanel('intro'),
        FieldPanel('featured_image'),
        FieldPanel('body'),
    ]

    search_fields = Page.search_fields + [
        index.SearchField('intro'),
        index.SearchField('body'),
        index.FilterField('published_date'),
    ]

    class Meta:
        ordering     = ['-published_date']
        verbose_name = 'Article'


# ── MethodologyPage ────────────────────────────────────────────────────────────

class MethodologyPage(Page):
    """Explains the EcoIQ scoring formula and data sources."""
    intro = RichTextField(blank=True)
    body  = StreamField(ArticlePageBody(), blank=True, use_json_field=True)

    content_panels = Page.content_panels + [
        FieldPanel('intro'),
        FieldPanel('body'),
    ]

    class Meta:
        verbose_name = 'Methodology Page'


# ── AboutPage ──────────────────────────────────────────────────────────────────

class AboutPage(Page):
    """About EcoIQ — mission, team, approach."""
    intro = RichTextField(blank=True)
    body  = StreamField(ArticlePageBody(), blank=True, use_json_field=True)

    content_panels = Page.content_panels + [
        FieldPanel('intro'),
        FieldPanel('body'),
    ]

    class Meta:
        verbose_name = 'About Page'
