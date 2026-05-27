"""
EcoIQ CMS — StreamField block library.

Blocks are grouped by concern:
  Hero     — full-width page hero section
  Metrics  — KPI, CO₂, score breakdown, company comparison, metric grid
  Score    — pillar explanation
  Spotlights — company spotlight, country intelligence
  Projects — project showcase, timeline
  Evidence — evidence carousel, evidence source citation
  Editorial — recommendation, rich text, image, CTA
"""
from wagtail.blocks import (
    CharBlock, TextBlock, RichTextBlock, StructBlock, ListBlock,
    StreamBlock, ChoiceBlock, URLBlock, IntegerBlock, BooleanBlock,
    PageChooserBlock,
)
from wagtail.images.blocks import ImageChooserBlock
from wagtail.documents.blocks import DocumentChooserBlock


# ── Choice constants ───────────────────────────────────────────────────────────

TREND_CHOICES = [
    ('up',   '↑ Improving'),
    ('down', '↓ Declining'),
    ('flat', '→ Stable'),
]

COLOUR_CHOICES = [
    ('green', 'Green'),
    ('teal',  'Teal'),
    ('amber', 'Amber'),
    ('red',   'Red'),
    ('blue',  'Blue'),
]

PRIORITY_CHOICES = [
    ('high',   'High Priority'),
    ('medium', 'Medium Priority'),
    ('low',    'Low Priority'),
]

STATUS_CHOICES = [
    ('planned',   'Planned'),
    ('active',    'Active'),
    ('completed', 'Completed'),
    ('cancelled', 'Cancelled'),
]

VERIFICATION_CHOICES = [
    ('pending',  'Pending'),
    ('verified', 'Verified'),
    ('rejected', 'Rejected'),
]

PROJECT_TYPE_CHOICES = [
    ('coal_stove',    'Coal Stove Replacement'),
    ('gasification',  'Gasification'),
    ('power_modern',  'Power Plant Modernisation'),
    ('renewable',     'Renewable Energy'),
    ('water_cleanup', 'Water Clean-up'),
    ('waste',         'Waste Reduction'),
    ('tree_planting', 'Tree Planting'),
    ('filters',       'Industrial Filters'),
    ('methane',       'Methane Leak Reduction'),
    ('other',         'Other'),
]

DOC_TYPE_CHOICES = [
    ('audit_report',      'Audit Report'),
    ('government_report', 'Government Report'),
    ('satellite',         'Satellite Evidence'),
    ('photo',             'Photo / Video'),
    ('invoice',           'Invoice / Contract'),
    ('permit',            'Environmental Permit'),
    ('engineering_audit', 'Engineering Audit'),
    ('other',             'Other'),
]

RICH_TEXT_FEATURES = ['h2', 'h3', 'bold', 'italic', 'ol', 'ul', 'link', 'blockquote']


# ── Hero block ─────────────────────────────────────────────────────────────────

class HeroBlock(StructBlock):
    """Full-width institutional hero section — dark, branded, investor-grade."""
    headline            = CharBlock(max_length=255, help_text='Main headline text')
    subtitle            = TextBlock(required=False, help_text='Supporting paragraph')
    badge               = CharBlock(max_length=80, required=False, help_text='Small label above headline, e.g. "New Report"')
    cta_primary_label   = CharBlock(max_length=80, required=False, default='View Rankings')
    cta_primary_url     = URLBlock(required=False)
    cta_secondary_label = CharBlock(max_length=80, required=False)
    cta_secondary_url   = URLBlock(required=False)
    background_style    = ChoiceBlock(choices=[
        ('dark',  'Dark institutional (default)'),
        ('teal',  'Teal gradient'),
        ('light', 'Light / white'),
    ], default='dark')

    class Meta:
        icon     = 'title'
        label    = 'Hero Section'
        template = 'cms/blocks/hero.html'


# ── Metrics blocks ─────────────────────────────────────────────────────────────

class KPICardBlock(StructBlock):
    """Single KPI metric card (label + value + trend)."""
    label       = CharBlock(max_length=100,  help_text='Metric name, e.g. "CO₂ Reduced"')
    value       = CharBlock(max_length=50,   help_text='Value, e.g. "1.2M t"')
    unit        = CharBlock(max_length=30,   required=False, help_text='Unit label (shown below value)')
    description = TextBlock(required=False,  help_text='One-line explanation')
    trend       = ChoiceBlock(choices=TREND_CHOICES, required=False)
    colour      = ChoiceBlock(choices=COLOUR_CHOICES, default='green')

    class Meta:
        icon     = 'pick'
        label    = 'KPI Card'
        template = 'cms/blocks/kpi_card.html'


class MetricGridBlock(StructBlock):
    """Grid of KPI metric cards — ideal for stats bands and highlights."""
    title   = CharBlock(max_length=255, required=False, default='Key Metrics')
    metrics = ListBlock(KPICardBlock())

    class Meta:
        icon     = 'list-ul'
        label    = 'Metric Grid'
        template = 'cms/blocks/metric_grid.html'


class CO2MetricsBlock(StructBlock):
    """CO₂ reduction impact block with methodology note."""
    title                  = CharBlock(default='CO₂ Impact')
    annual_reduction_tonnes = IntegerBlock(help_text='Annual CO₂ reduction in tonnes')
    baseline_year          = IntegerBlock(help_text='Baseline comparison year')
    reduction_percent      = IntegerBlock(help_text='% reduction from baseline')
    methodology            = TextBlock(required=False, help_text='How this was calculated')
    verified               = BooleanBlock(required=False, default=False)

    class Meta:
        icon     = 'snippet'
        label    = 'CO₂ Metrics'
        template = 'cms/blocks/co2_metrics.html'


class ScoreBreakdownBlock(StructBlock):
    """
    Live EcoIQ score breakdown pulled from league.Company.
    The company_slug field links to a league Company record.
    """
    title            = CharBlock(default='EcoIQ Score Breakdown')
    company_slug     = CharBlock(max_length=255, help_text='Company slug from the Good Deeds League')
    show_trend_chart = BooleanBlock(required=False, default=True, help_text='Show 6-month trend chart')
    show_pillar_bars = BooleanBlock(required=False, default=True, help_text='Show pillar bar breakdown')

    class Meta:
        icon     = 'tasks'
        label    = 'Score Breakdown (live data)'
        template = 'cms/blocks/score_breakdown.html'

    def get_context(self, value, parent_context=None):
        ctx = super().get_context(value, parent_context=parent_context)
        slug = value.get('company_slug', '').strip()
        ctx['company'] = None
        if slug:
            try:
                from league.models import Company
                from league.scoring import get_tier
                company = Company.objects.prefetch_related('history').get(slug=slug)
                ctx['company'] = company
                ctx['tier']    = get_tier(float(company.ecoiq_score))
                ctx['pillars'] = [
                    {'name': 'Pollution',    'score': company.score_pollution_footprint, 'weight': 35},
                    {'name': 'Reduction',    'score': company.score_reduction_progress,  'weight': 25},
                    {'name': 'Investment',   'score': company.score_investment,           'weight': 20},
                    {'name': 'Transparency', 'score': company.score_transparency,         'weight': 10},
                    {'name': 'Community',    'score': company.score_community_impact,     'weight': 10},
                ]
                history = company.history.order_by('date')[:12]
                ctx['history_labels'] = [str(h.date) for h in history]
                ctx['history_scores'] = [float(h.ecoiq_score) for h in history]
            except Exception:
                pass
        return ctx


class ComparisonTableBlock(StructBlock):
    """
    Side-by-side score table for multiple league companies.
    Editor enters one company slug per line.
    """
    title         = CharBlock(default='Company Comparison')
    company_slugs = TextBlock(help_text='One company slug per line (max 6)', rows=4)

    class Meta:
        icon     = 'list-ul'
        label    = 'Company Comparison Table'
        template = 'cms/blocks/comparison_table.html'

    def get_context(self, value, parent_context=None):
        ctx = super().get_context(value, parent_context=parent_context)
        slugs = [s.strip() for s in value.get('company_slugs', '').splitlines() if s.strip()][:6]
        ctx['companies'] = []
        if slugs:
            try:
                from league.models import Company
                from league.scoring import get_tier
                qs = Company.objects.filter(slug__in=slugs)
                companies = sorted(qs, key=lambda c: slugs.index(c.slug) if c.slug in slugs else 99)
                for co in companies:
                    co.tier = get_tier(float(co.ecoiq_score))
                ctx['companies'] = companies
            except Exception:
                pass
        return ctx


# ── Score explanation block ────────────────────────────────────────────────────

class ScoreExplanationBlock(StructBlock):
    """Explains one EcoIQ scoring pillar — icon, weight, and description."""
    pillar_name = CharBlock(max_length=100, help_text='Pillar name, e.g. "Environmental Stewardship"')
    icon        = CharBlock(max_length=10, required=False, help_text='Emoji or short icon character')
    weight      = IntegerBlock(help_text='Weight as an integer percentage, e.g. 25')
    description = TextBlock(help_text='Plain-language explanation of what this pillar measures')

    class Meta:
        icon     = 'tasks'
        label    = 'Score Pillar Explanation'
        template = 'cms/blocks/score_explanation.html'


# ── Spotlight blocks ───────────────────────────────────────────────────────────

class CompanySpotlightBlock(StructBlock):
    """
    Embeds a live company intelligence card from companies.CompanyProfile.
    Falls back gracefully if no matching profile exists.
    """
    company_slug = CharBlock(max_length=255, help_text='Slug from companies.CompanyProfile')
    headline     = CharBlock(max_length=255, required=False, help_text='Optional editorial headline override')
    summary      = TextBlock(required=False, help_text='Optional editorial summary override')

    class Meta:
        icon     = 'group'
        label    = 'Company Spotlight'
        template = 'cms/blocks/company_spotlight.html'

    def get_context(self, value, parent_context=None):
        ctx = super().get_context(value, parent_context=parent_context)
        slug = value.get('company_slug', '').strip()
        ctx['profile'] = None
        if slug:
            try:
                from companies.models import CompanyProfile
                ctx['profile'] = CompanyProfile.objects.get(slug=slug)
            except Exception:
                pass
        return ctx


class CountryIntelligenceBlock(StructBlock):
    """
    Embeds a live country intelligence card from countries.CountryProfile.
    Falls back gracefully if no matching profile exists.
    """
    country_code = CharBlock(max_length=4, help_text='ISO 2-letter country code, e.g. KZ')
    headline     = CharBlock(max_length=255, required=False, help_text='Optional editorial headline')
    summary      = TextBlock(required=False, help_text='Optional editorial summary')

    class Meta:
        icon     = 'site'
        label    = 'Country Intelligence'
        template = 'cms/blocks/country_intelligence.html'

    def get_context(self, value, parent_context=None):
        ctx = super().get_context(value, parent_context=parent_context)
        code = value.get('country_code', '').strip().upper()
        ctx['country'] = None
        if code:
            try:
                from countries.models import CountryProfile
                ctx['country'] = CountryProfile.objects.get(iso_code=code)
            except Exception:
                pass
        return ctx


# ── Project blocks ─────────────────────────────────────────────────────────────

class ProjectShowcaseBlock(StructBlock):
    """Rich editorial block for a single environmental project."""
    title              = CharBlock(max_length=255)
    project_type       = ChoiceBlock(choices=PROJECT_TYPE_CHOICES, default='other')
    status             = ChoiceBlock(choices=STATUS_CHOICES, default='active')
    location           = CharBlock(max_length=255, required=False)
    investment_usd     = IntegerBlock(required=False, help_text='Total investment in USD')
    co2_tonnes         = IntegerBlock(required=False, help_text='Annual CO₂ reduction in tonnes')
    households_helped  = IntegerBlock(required=False)
    pm25_kg            = IntegerBlock(required=False, help_text='Annual PM2.5 reduction in kg')
    description        = RichTextBlock(features=RICH_TEXT_FEATURES)
    image              = ImageChooserBlock(required=False)
    verified           = BooleanBlock(required=False, default=False)

    class Meta:
        icon     = 'folder-open-inverse'
        label    = 'Project Showcase'
        template = 'cms/blocks/project_showcase.html'


class TimelineEventBlock(StructBlock):
    year         = IntegerBlock()
    title        = CharBlock(max_length=255)
    description  = TextBlock()
    status       = ChoiceBlock(choices=STATUS_CHOICES, default='completed')
    investment   = CharBlock(max_length=60, required=False, help_text='e.g. "$380M"')


class TimelineBlock(StructBlock):
    """Horizontal/vertical milestone timeline."""
    title  = CharBlock(default='Project Timeline')
    events = ListBlock(TimelineEventBlock())

    class Meta:
        icon     = 'date'
        label    = 'Timeline'
        template = 'cms/blocks/timeline.html'


# ── Evidence blocks ────────────────────────────────────────────────────────────

class EvidenceItemBlock(StructBlock):
    title               = CharBlock(max_length=255)
    doc_type            = ChoiceBlock(choices=DOC_TYPE_CHOICES, default='other')
    issuer              = CharBlock(max_length=255, required=False)
    year                = IntegerBlock(required=False)
    url                 = URLBlock(required=False, help_text='Link to public document')
    document            = DocumentChooserBlock(required=False, help_text='Or upload directly')
    verification_status = ChoiceBlock(choices=VERIFICATION_CHOICES, default='pending')
    notes               = TextBlock(required=False)

    class Meta:
        icon  = 'doc-empty'
        label = 'Evidence Item'


class EvidenceCarouselBlock(StructBlock):
    """List of evidence documents with verification status."""
    title = CharBlock(default='Evidence & Documentation')
    items = ListBlock(EvidenceItemBlock())

    class Meta:
        icon     = 'folder-open-inverse'
        label    = 'Evidence Carousel'
        template = 'cms/blocks/evidence_carousel.html'


class EvidenceSourceBlock(StructBlock):
    """Inline citation / source reference — lighter-weight than EvidenceCarousel."""
    title       = CharBlock(max_length=255)
    source_url  = URLBlock(required=False, help_text='Public URL for this source')
    year        = IntegerBlock(required=False)
    description = TextBlock(required=False, help_text='Brief context about this source')

    class Meta:
        icon     = 'doc-empty'
        label    = 'Evidence Source'
        template = 'cms/blocks/evidence_source.html'


# ── Editorial blocks ───────────────────────────────────────────────────────────

class RecommendationBlock(StructBlock):
    """A single actionable recommendation with priority, impact, and timeline."""
    title            = CharBlock(max_length=255)
    priority         = ChoiceBlock(choices=PRIORITY_CHOICES, default='medium')
    description      = RichTextBlock(features=RICH_TEXT_FEATURES)
    investment_range = CharBlock(max_length=100, required=False, help_text='e.g. "$10M–$50M"')
    expected_impact  = CharBlock(max_length=255, required=False)
    timeline         = CharBlock(max_length=100, required=False, help_text='e.g. "2–3 years"')

    class Meta:
        icon     = 'tick'
        label    = 'Recommendation'
        template = 'cms/blocks/recommendation.html'


class RichTextSectionBlock(StructBlock):
    content = RichTextBlock(features=RICH_TEXT_FEATURES)

    class Meta:
        icon     = 'doc-full'
        label    = 'Rich Text'
        template = 'cms/blocks/rich_text.html'


class ImageBlock(StructBlock):
    image      = ImageChooserBlock()
    caption    = CharBlock(max_length=255, required=False)
    full_width = BooleanBlock(required=False, default=False)

    class Meta:
        icon     = 'image'
        label    = 'Image'
        template = 'cms/blocks/image_block.html'


class CallToActionBlock(StructBlock):
    text         = CharBlock(max_length=255)
    button_label = CharBlock(max_length=80, default='Learn More')
    url          = URLBlock(required=False, help_text='External URL (overrides page)')
    page         = PageChooserBlock(required=False, help_text='Internal page link')
    style        = ChoiceBlock(choices=[
        ('primary',   'Primary (Green)'),
        ('secondary', 'Secondary (Outline)'),
        ('dark',      'Dark'),
    ], default='primary')

    class Meta:
        icon     = 'link'
        label    = 'Call to Action'
        template = 'cms/blocks/cta.html'


# ── Composite StreamBlocks for each page type ──────────────────────────────────

class HomePageBody(StreamBlock):
    """Used by the CMS HomePage — broad editorial toolkit."""
    hero                 = HeroBlock()
    rich_text            = RichTextSectionBlock()
    kpi_card             = KPICardBlock()
    metric_grid          = MetricGridBlock()
    company_spotlight    = CompanySpotlightBlock()
    country_intelligence = CountryIntelligenceBlock()
    cta                  = CallToActionBlock()
    image                = ImageBlock()

    class Meta:
        icon = 'placeholder'


class ArticlePageBody(StreamBlock):
    """Used by ArticlePage and MethodologyPage."""
    rich_text      = RichTextSectionBlock()
    image          = ImageBlock()
    kpi_card       = KPICardBlock()
    evidence_source = EvidenceSourceBlock()
    cta            = CallToActionBlock()

    class Meta:
        icon = 'placeholder'


class InsightPageBody(StreamBlock):
    """Used by InsightArticlePage — full intelligence editorial toolkit."""
    hero                 = HeroBlock()
    rich_text            = RichTextSectionBlock()
    image                = ImageBlock()
    kpi_card             = KPICardBlock()
    metric_grid          = MetricGridBlock()
    score_explanation    = ScoreExplanationBlock()
    company_spotlight    = CompanySpotlightBlock()
    country_intelligence = CountryIntelligenceBlock()
    evidence_source      = EvidenceSourceBlock()
    evidence_carousel    = EvidenceCarouselBlock()
    recommendation       = RecommendationBlock()
    timeline             = TimelineBlock()
    project_showcase     = ProjectShowcaseBlock()
    cta                  = CallToActionBlock()

    class Meta:
        icon = 'placeholder'


class ReportPageBody(StreamBlock):
    """Used by ReportLibraryPage — download-oriented research reports."""
    hero            = HeroBlock()
    rich_text       = RichTextSectionBlock()
    image           = ImageBlock()
    kpi_card        = KPICardBlock()
    metric_grid     = MetricGridBlock()
    evidence_source = EvidenceSourceBlock()
    cta             = CallToActionBlock()

    class Meta:
        icon = 'placeholder'


class CaseStudyPageBody(StreamBlock):
    """Used by CaseStudyPage — narrative + data for a company or project."""
    hero                 = HeroBlock()
    rich_text            = RichTextSectionBlock()
    image                = ImageBlock()
    kpi_card             = KPICardBlock()
    metric_grid          = MetricGridBlock()
    company_spotlight    = CompanySpotlightBlock()
    evidence_source      = EvidenceSourceBlock()
    timeline             = TimelineBlock()
    recommendation       = RecommendationBlock()
    cta                  = CallToActionBlock()

    class Meta:
        icon = 'placeholder'


class CompanyPageBody(StreamBlock):
    """Used by CompanyPage (editorial layer around a league company)."""
    rich_text         = RichTextSectionBlock()
    kpi_card          = KPICardBlock()
    metric_grid       = MetricGridBlock()
    co2_metrics       = CO2MetricsBlock()
    project_showcase  = ProjectShowcaseBlock()
    evidence_carousel = EvidenceCarouselBlock()
    recommendation    = RecommendationBlock()
    timeline          = TimelineBlock()
    score_breakdown   = ScoreBreakdownBlock()
    comparison_table  = ComparisonTableBlock()
    evidence_source   = EvidenceSourceBlock()
    cta               = CallToActionBlock()
    image             = ImageBlock()

    class Meta:
        icon = 'placeholder'
