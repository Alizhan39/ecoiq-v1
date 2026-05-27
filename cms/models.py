"""
EcoIQ CMS — Wagtail page models.

Page hierarchy (typical):
  Root
  └── HomePage (/)
      ├── CompanyIndexPage     (/companies/)
      │   ├── CompanyPage      (/companies/qazaqgaz/)
      │   └── CompanyPage      (/companies/kazatomprom/)
      ├── ArticlePage          (/insights/...)
      ├── InsightArticlePage   (/insights/climate-report-2025/)
      ├── CountryIntelligencePage (/intelligence/kz/)
      ├── ReportLibraryPage    (/reports/)
      ├── CaseStudyPage        (/case-studies/...)
      ├── MethodologyPage      (/methodology/)
      └── AboutPage            (/about/)

All pages are served under /pages/ in this deployment
(to preserve existing Django routes at / /companies/ /countries/ etc.)
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
    InsightPageBody,
    ReportPageBody,
    CaseStudyPageBody,
)


# ── Insight category choices ───────────────────────────────────────────────────

INSIGHT_CATEGORY_CHOICES = [
    ('analysis',    'Analysis'),
    ('report',      'Report'),
    ('news',        'News'),
    ('case_study',  'Case Study'),
    ('methodology', 'Methodology'),
    ('intelligence','Intelligence Brief'),
]


# ── HomePage ───────────────────────────────────────────────────────────────────

class HomePage(Page):
    """
    Root landing page — managed entirely through Wagtail CMS.
    Can contain KPI summaries, intro text, hero sections, and CTAs.
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
        'cms.InsightArticlePage',
        'cms.MethodologyPage',
        'cms.AboutPage',
        'cms.CountryIntelligencePage',
        'cms.ReportLibraryPage',
        'cms.CaseStudyPage',
    ]

    class Meta:
        verbose_name = 'Home Page'

    def get_context(self, request, *args, **kwargs):
        ctx = super().get_context(request, *args, **kwargs)
        # Inject top companies for optional hero widget
        try:
            from league.models import Company
            ctx['top_companies'] = Company.objects.order_by('rank')[:4]
        except Exception:
            ctx['top_companies'] = []
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
        try:
            from league.models import Company
            from league.scoring import get_tier
            companies = list(Company.objects.order_by('rank', '-ecoiq_score'))
            for co in companies:
                co.tier = get_tier(float(co.ecoiq_score))
            ctx['companies'] = companies
        except Exception:
            ctx['companies'] = []
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
    """News article, analysis piece, or insight report (legacy / simple variant)."""

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


# ── InsightArticlePage ─────────────────────────────────────────────────────────

class InsightArticlePage(Page):
    """
    Full-featured intelligence article — analysis, reports, briefings, case studies.
    Supports the complete block toolkit including hero, company spotlights, country
    intelligence, metric grids, and evidence sources.
    """

    category       = models.CharField(
        max_length=30, choices=INSIGHT_CATEGORY_CHOICES, default='analysis',
        help_text='Content category for filtering in listings',
    )
    featured       = models.BooleanField(
        default=False,
        help_text='Pin this article in the featured / hero position',
    )
    reading_time   = models.PositiveSmallIntegerField(
        default=5,
        help_text='Estimated reading time in minutes',
    )
    published_date = models.DateField(null=True, blank=True)
    author         = models.CharField(max_length=255, blank=True)
    intro          = models.TextField(
        blank=True, max_length=600,
        help_text='Short summary shown in listings (max 600 chars)',
    )
    body = StreamField(InsightPageBody(), blank=True, use_json_field=True)
    featured_image = models.ForeignKey(
        'wagtailimages.Image',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
    )

    content_panels = Page.content_panels + [
        MultiFieldPanel([
            FieldPanel('category'),
            FieldPanel('featured'),
            FieldPanel('published_date'),
            FieldPanel('author'),
            FieldPanel('reading_time'),
        ], heading='Publication Info'),
        FieldPanel('intro'),
        FieldPanel('featured_image'),
        FieldPanel('body'),
    ]

    search_fields = Page.search_fields + [
        index.SearchField('intro'),
        index.SearchField('body'),
        index.FilterField('published_date'),
        index.FilterField('category'),
    ]

    class Meta:
        ordering            = ['-published_date']
        verbose_name        = 'Insight Article'
        verbose_name_plural = 'Insight Articles'


# ── CountryIntelligencePage ────────────────────────────────────────────────────

class CountryIntelligencePage(Page):
    """
    Country-level intelligence page — editorial layer over countries.CountryProfile.
    Editors write narrative analysis; live data is pulled from the CountryProfile model.
    """

    country_code   = models.CharField(
        max_length=4, blank=True,
        help_text='ISO 2-letter country code, e.g. KZ — links to CountryProfile',
    )
    intro          = models.TextField(
        blank=True, max_length=600,
        help_text='Short country summary for listings',
    )
    body           = StreamField(InsightPageBody(), blank=True, use_json_field=True)
    featured_image = models.ForeignKey(
        'wagtailimages.Image',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
    )

    content_panels = Page.content_panels + [
        MultiFieldPanel([
            FieldPanel('country_code'),
            FieldPanel('intro'),
        ], heading='Country Link'),
        FieldPanel('featured_image'),
        FieldPanel('body'),
    ]

    search_fields = Page.search_fields + [
        index.SearchField('intro'),
        index.SearchField('body'),
        index.FilterField('country_code'),
    ]

    class Meta:
        verbose_name        = 'Country Intelligence Page'
        verbose_name_plural = 'Country Intelligence Pages'

    def get_context(self, request, *args, **kwargs):
        ctx = super().get_context(request, *args, **kwargs)
        ctx['country'] = None
        if self.country_code:
            try:
                from countries.models import CountryProfile
                ctx['country'] = CountryProfile.objects.get(
                    iso_code=self.country_code.strip().upper()
                )
            except Exception:
                pass
        return ctx


# ── ReportLibraryPage ──────────────────────────────────────────────────────────

class ReportLibraryPage(Page):
    """
    Reports library — downloadable intelligence reports, data packs, white papers.
    Each report is a document linked via EvidenceSourceBlock or DocumentChooserBlock.
    """

    intro = models.TextField(
        blank=True, max_length=600,
        help_text='Short description of the report library',
    )
    body  = StreamField(ReportPageBody(), blank=True, use_json_field=True)

    content_panels = Page.content_panels + [
        FieldPanel('intro'),
        FieldPanel('body'),
    ]

    search_fields = Page.search_fields + [
        index.SearchField('intro'),
    ]

    class Meta:
        verbose_name = 'Report Library Page'


# ── CaseStudyPage ──────────────────────────────────────────────────────────────

class CaseStudyPage(Page):
    """
    Detailed case study — challenge, solution, outcomes, and rich body content.
    Used for NCTA, Sustainable Ventures, and company transition demonstrations.
    """

    category       = models.CharField(
        max_length=100, blank=True,
        help_text='Industry or topic category, e.g. "Energy Transition"',
    )
    company_name   = models.CharField(
        max_length=255, blank=True,
        help_text='Featured company or organisation name (if applicable)',
    )
    published_date = models.DateField(null=True, blank=True)
    challenge      = models.TextField(
        blank=True,
        help_text='The problem or challenge being addressed',
    )
    solution       = models.TextField(
        blank=True,
        help_text='The approach, methodology, or intervention',
    )
    outcomes       = models.TextField(
        blank=True,
        help_text='Key results, impact metrics, and lessons',
    )
    body           = StreamField(CaseStudyPageBody(), blank=True, use_json_field=True)
    featured_image = models.ForeignKey(
        'wagtailimages.Image',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
    )

    content_panels = Page.content_panels + [
        MultiFieldPanel([
            FieldPanel('category'),
            FieldPanel('company_name'),
            FieldPanel('published_date'),
        ], heading='Case Study Info'),
        MultiFieldPanel([
            FieldPanel('challenge'),
            FieldPanel('solution'),
            FieldPanel('outcomes'),
        ], heading='Narrative Summary'),
        FieldPanel('featured_image'),
        FieldPanel('body'),
    ]

    search_fields = Page.search_fields + [
        index.SearchField('challenge'),
        index.SearchField('solution'),
        index.SearchField('outcomes'),
        index.SearchField('body'),
        index.FilterField('published_date'),
    ]

    class Meta:
        ordering            = ['-published_date']
        verbose_name        = 'Case Study'
        verbose_name_plural = 'Case Studies'


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
