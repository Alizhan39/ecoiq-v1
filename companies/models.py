"""
EcoIQ Company Intelligence — Models.

CompanyProfile     Extended data layer linked OneToOne to league.Company.
                   Holds public-benefit scores, moral label, AI content,
                   pollution level, funding status, and all new EcoIQ dimensions.

CompanyGuidanceVideo   AI-generated video scripts and Higgsfield prompts.

CompanySource      Cited public sources for a company profile.
"""
from django.db import models
from django.utils.text import slugify


# ── Choice sets ────────────────────────────────────────────────────────────────

COMPANY_STATUS = [
    ('draft',    'Draft'),
    ('public',   'Public'),
    ('verified', 'Verified'),
    ('archived', 'Archived'),
]

SUBSCRIPTION_TIER = [
    ('free',       'Free'),
    ('verified',   'Verified'),
    ('enterprise', 'Enterprise'),
]

POLLUTION_LEVEL = [
    ('low',    'Low'),
    ('medium', 'Medium'),
    ('high',   'High'),
    ('severe', 'Severe'),
]

OWNERSHIP_TYPE = [
    ('private',       'Private'),
    ('state',         'State-Owned'),
    ('mixed',         'Mixed (State + Private)'),
    ('public_listed', 'Publicly Listed'),
    ('cooperative',   'Cooperative / NGO'),
]

FUNDING_STATUS = [
    ('not_seeking',      'Not Seeking Funding'),
    ('open_to_funding',  'Open to Funding'),
    ('seeking_partners', 'Actively Seeking Partners'),
    ('funded',           'Recently Funded'),
]

MORAL_LABEL_CHOICES = [
    ('regenerative_leader',    'Regenerative Leader'),
    ('responsible_builder',    'Responsible Builder'),
    ('public_benefit_oriented','Public-Benefit Oriented'),
    ('transitional_company',   'Transitional Company'),
    ('profit_first_operator',  'Profit-First Operator'),
    ('extractive_harmful',     'Extractive / Harmful'),
]

VIDEO_TYPE_CHOICES = [
    ('path_to_100',           'Path to 100% EcoIQ Score'),
    ('profit_to_public',      'Profit to Public Benefit'),
    ('hidden_harm_reduction', 'Hidden Harm Reduction'),
    ('modernization_roadmap', 'Modernization Roadmap'),
    ('transparency_trust',    'Transparency & Trust'),
    ('investor_readiness',    'Investor Readiness'),
    ('public_benefit_story',  'Public Benefit Story'),
    ('board_summary',         'Board-Level Summary'),
    ('what_100_looks_like',   'What a 100 EcoIQ Score Looks Like'),
]

VIDEO_STATUS_CHOICES = [
    ('draft',                 'Draft'),
    ('script_generated',      'Script Generated'),
    ('video_prompt_generated','Video Prompt Generated'),
    ('video_created',         'Video Created'),
    ('reviewed',              'Reviewed'),
    ('published',             'Published'),
    ('archived',              'Archived'),
]

VIDEO_VISIBILITY = [
    ('public',          'Public'),
    ('verified_only',   'Verified Only'),
    ('enterprise_only', 'Enterprise Only'),
    ('internal_only',   'Internal Only'),
]

SOURCE_TYPE_CHOICES = [
    ('annual_report',         'Annual Report'),
    ('sustainability_report', 'Sustainability Report'),
    ('government_registry',   'Government Registry'),
    ('regulator',             'Regulatory Filing'),
    ('news',                  'News Article'),
    ('research',              'Research / Analysis'),
    ('press_release',         'Press Release'),
    ('other',                 'Other'),
]


# ── CompanyProfile ─────────────────────────────────────────────────────────────

class CompanyProfile(models.Model):
    """
    Extended EcoIQ intelligence layer for a company.
    Linked OneToOne to league.Company — augments it with public-facing
    ethical scoring dimensions, AI content, and operational metadata.
    """

    company = models.OneToOneField(
        'league.Company',
        on_delete=models.CASCADE,
        related_name='profile',
    )

    # ── Status & tier ──
    status            = models.CharField(max_length=15, choices=COMPANY_STATUS, default='public')
    subscription_tier = models.CharField(max_length=15, choices=SUBSCRIPTION_TIER, default='free')
    is_verified       = models.BooleanField(default=False)

    # ── Financials ──
    annual_revenue         = models.BigIntegerField(null=True, blank=True,
                             help_text='Annual revenue in USD')
    profit                 = models.BigIntegerField(null=True, blank=True,
                             help_text='Net profit in USD')
    employees              = models.PositiveIntegerField(null=True, blank=True)
    taxes_paid             = models.BigIntegerField(null=True, blank=True,
                             help_text='Taxes paid in USD')
    ownership_type         = models.CharField(max_length=20, choices=OWNERSHIP_TYPE,
                             default='private', blank=True)
    state_owned_percentage = models.FloatField(null=True, blank=True,
                             help_text='% owned by government / sovereign entities')

    # ── Source documents ──
    public_sources            = models.JSONField(default=list, blank=True,
                                help_text='List of {url, title, type} source dicts')
    annual_report_url         = models.URLField(blank=True)
    sustainability_report_url = models.URLField(blank=True)

    # ── Environmental ──
    estimated_emissions        = models.BigIntegerField(null=True, blank=True,
                                 help_text='Estimated annual CO₂ equivalent in tonnes')
    pollution_level            = models.CharField(max_length=10, choices=POLLUTION_LEVEL,
                                 default='medium')
    pollution_notes            = models.TextField(blank=True)
    emissions_reduction_target = models.FloatField(null=True, blank=True,
                                 help_text='Target % reduction vs baseline year')
    renewable_energy_share     = models.FloatField(null=True, blank=True,
                                 help_text='% of energy from renewable sources')
    waste_management_score     = models.FloatField(default=50.0,
                                 help_text='0-100: quality of waste management practices')
    water_impact_score         = models.FloatField(default=50.0,
                                 help_text='0-100: water stewardship quality')
    biodiversity_impact_score  = models.FloatField(default=50.0,
                                 help_text='0-100: impact on biodiversity and ecosystems')

    # ── Social / Public Benefit ──
    jobs_created_score               = models.FloatField(default=50.0,
                                       help_text='0-100: quality and quantity of employment')
    regional_development_score       = models.FloatField(default=50.0,
                                       help_text='0-100: contribution to regional economy')
    community_investment             = models.BigIntegerField(null=True, blank=True,
                                       help_text='Annual community investment in USD')
    infrastructure_contribution_score= models.FloatField(default=50.0,
                                       help_text='0-100: infrastructure contribution')
    national_value_score             = models.FloatField(default=50.0,
                                       help_text='0-100: long-term national benefit')

    # ── Modernization ──
    modernization_investment      = models.BigIntegerField(null=True, blank=True,
                                    help_text='Annual modernization capex in USD')
    modernization_projects        = models.JSONField(default=list, blank=True,
                                    help_text='List of active modernization project names')
    energy_transition_score       = models.FloatField(default=50.0,
                                    help_text='0-100: energy transition progress')
    digitalization_score          = models.FloatField(default=50.0,
                                    help_text='0-100: digital transformation maturity')
    infrastructure_upgrade_score  = models.FloatField(default=50.0,
                                    help_text='0-100: physical infrastructure modernity')
    future_readiness_score        = models.FloatField(default=50.0,
                                    help_text='0-100: preparedness for future economy')

    # ── Transparency & Governance ──
    transparency_score_detail         = models.FloatField(default=50.0,
                                        help_text='0-100: reporting quality and openness')
    audit_quality_score               = models.FloatField(default=50.0,
                                        help_text='0-100: audit standards and independence')
    procurement_transparency_score    = models.FloatField(default=50.0,
                                        help_text='0-100: procurement process openness')
    anti_corruption_score             = models.FloatField(default=50.0,
                                        help_text='0-100: anti-corruption practices')
    controversy_risk_score            = models.FloatField(default=30.0,
                                        help_text='0-100: higher = more controversy risk')
    governance_notes                  = models.TextField(blank=True)

    # ── EcoIQ Composite Scores (computed + stored) ──
    profit_extraction_score          = models.FloatField(default=50.0,
                                       help_text='0-100: how much profit flows back to people vs. owners')
    profit_extraction_risk_score     = models.FloatField(default=30.0,
                                       help_text='0-100: risk indicator — higher = more concern')
    public_benefit_score             = models.FloatField(default=50.0)
    environmental_responsibility_score = models.FloatField(default=50.0)
    modernization_score              = models.FloatField(default=50.0)
    transparency_anti_corruption_score = models.FloatField(default=50.0)
    ethical_alignment_score          = models.FloatField(default=50.0)
    harm_penalty                     = models.FloatField(default=0.0,
                                       help_text='Points deducted for pollution/harm (0-30)')
    ecoiq_total_score                = models.FloatField(default=0.0)
    ecoiq_category                   = models.CharField(max_length=50, blank=True)
    moral_label                      = models.CharField(max_length=30,
                                       choices=MORAL_LABEL_CHOICES,
                                       default='transitional_company')

    # ── AI-generated content ──
    ai_summary               = models.TextField(blank=True,
                               help_text='AI-generated company summary (neutral, public-safe)')
    ai_modernization_report  = models.TextField(blank=True,
                               help_text='AI analysis of modernization opportunities')
    ai_investment_opportunity= models.TextField(blank=True,
                               help_text='AI-generated investor / funding opportunity summary')
    ai_risk_notes            = models.TextField(blank=True,
                               help_text='AI-flagged risks and transparency gaps')
    ai_recommendations       = models.JSONField(default=list, blank=True,
                               help_text='List of recommended improvement actions')

    # ── Funding ──
    funding_needed      = models.BigIntegerField(null=True, blank=True,
                          help_text='Estimated funding needed in USD')
    funding_status      = models.CharField(max_length=25, choices=FUNDING_STATUS,
                          default='not_seeking')
    investor_visibility = models.BooleanField(default=False,
                          help_text='Show this company in investor-facing views')
    project_pipeline    = models.JSONField(default=list, blank=True,
                          help_text='List of upcoming funded projects')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-ecoiq_total_score', 'company__name']
        verbose_name        = 'Company Profile'
        verbose_name_plural = 'Company Profiles'

    def __str__(self):
        return f'{self.company.name} — EcoIQ {self.ecoiq_total_score:.1f}'

    # ── Derived properties ─────────────────────────────────────────────────────

    @property
    def moral_label_display(self):
        return dict(MORAL_LABEL_CHOICES).get(self.moral_label, self.moral_label)

    @property
    def moral_label_color(self):
        colour_map = {
            'regenerative_leader':    '#00e89a',
            'responsible_builder':    '#58a6ff',
            'public_benefit_oriented':'#8b5cf6',
            'transitional_company':   '#f4a261',
            'profit_first_operator':  '#e63946',
            'extractive_harmful':     '#b91c1c',
        }
        return colour_map.get(self.moral_label, '#888')

    @property
    def pollution_color(self):
        return {
            'low': '#00e89a', 'medium': '#f4a261',
            'high': '#e63946', 'severe': '#b91c1c',
        }.get(self.pollution_level, '#888')

    @property
    def funding_color(self):
        return {
            'not_seeking': '#888', 'open_to_funding': '#f4a261',
            'seeking_partners': '#58a6ff', 'funded': '#00e89a',
        }.get(self.funding_status, '#888')

    @property
    def score_label(self):
        s = self.ecoiq_total_score
        if s >= 85: return 'Exceptional'
        if s >= 70: return 'Strong'
        if s >= 60: return 'Moderate'
        if s >= 50: return 'Fair'
        return 'Needs Improvement'

    @property
    def high_transition_need(self):
        return (
            self.pollution_level in ('high', 'severe') and
            self.modernization_score < 40
        )

    @property
    def low_transparency_warning(self):
        return self.transparency_score_detail < 30

    @property
    def profit_extraction_warning(self):
        return (
            self.profit_extraction_score > 75 and
            self.public_benefit_score < 50
        )

    @property
    def path_to_100_gap(self):
        return max(0, 100 - self.ecoiq_total_score)


# ── CompanyGuidanceVideo ───────────────────────────────────────────────────────

class CompanyGuidanceVideo(models.Model):
    """
    AI-generated guidance video script and Higgsfield prompt for a company.
    Admin generates the script; video URL is pasted manually after Higgsfield creation.
    """
    company    = models.ForeignKey(
        CompanyProfile, on_delete=models.CASCADE, related_name='guidance_videos'
    )
    title      = models.CharField(max_length=255)
    slug       = models.SlugField(max_length=255, blank=True)
    video_type = models.CharField(max_length=30, choices=VIDEO_TYPE_CHOICES,
                                  default='path_to_100')

    # Video assets (filled manually by admin after Higgsfield production)
    video_url  = models.URLField(blank=True, help_text='Paste Higgsfield / Vimeo / YouTube URL')
    thumbnail  = models.ImageField(upload_to='guidance_videos/thumbnails/', null=True, blank=True)

    # AI-generated content
    script             = models.TextField(blank=True,
                         help_text='60-90 second narration script')
    higgsfield_prompt  = models.TextField(blank=True,
                         help_text='Higgsfield visual / scene prompt')
    recommended_actions= models.JSONField(default=list, blank=True,
                         help_text='3-7 recommended improvement actions')
    executive_summary  = models.TextField(blank=True,
                         help_text='Short 2-3 sentence summary for video card')

    # Score context (snapshot at time of generation)
    current_score_snapshot = models.FloatField(null=True, blank=True)
    target_score           = models.FloatField(null=True, blank=True)
    target_score_improvement = models.FloatField(null=True, blank=True)

    # Visibility & control
    visibility               = models.CharField(max_length=20, choices=VIDEO_VISIBILITY,
                               default='public')
    status                   = models.CharField(max_length=25, choices=VIDEO_STATUS_CHOICES,
                               default='draft')
    allow_download           = models.BooleanField(default=False)
    company_can_request_update = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name        = 'Company Guidance Video'
        verbose_name_plural = 'Company Guidance Videos'

    def __str__(self):
        return f'{self.company.company.name} — {self.title}'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)[:250]
        super().save(*args, **kwargs)

    @property
    def status_color(self):
        return {
            'draft': '#888', 'script_generated': '#f4a261',
            'video_prompt_generated': '#f4a261', 'video_created': '#58a6ff',
            'reviewed': '#58a6ff', 'published': '#00e89a', 'archived': '#555',
        }.get(self.status, '#888')

    @property
    def is_published(self):
        return self.status == 'published'

    @property
    def has_video(self):
        return bool(self.video_url)


# ── CompanySource ──────────────────────────────────────────────────────────────

class CompanySource(models.Model):
    """Cited public source for a CompanyProfile."""
    company     = models.ForeignKey(CompanyProfile, on_delete=models.CASCADE,
                                    related_name='cited_sources')
    url         = models.URLField()
    title       = models.CharField(max_length=255)
    source_type = models.CharField(max_length=25, choices=SOURCE_TYPE_CHOICES, default='other')
    date_accessed = models.DateField(null=True, blank=True)
    notes       = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ['source_type', 'title']
        verbose_name        = 'Company Source'
        verbose_name_plural = 'Company Sources'

    def __str__(self):
        return f'{self.company.company.name} — {self.title}'
