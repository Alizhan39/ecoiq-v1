"""
EcoIQ Company Intelligence — Models.

CompanyProfile     Extended data layer linked OneToOne to league.Company.
                   Holds public-benefit scores, moral label, AI content,
                   pollution level, funding status, and all new EcoIQ dimensions.

CompanyGuidanceVideo   AI-generated video scripts and Higgsfield prompts.

CompanySource      Cited public sources for a company profile.

NOTE: The `Company` model (industrial companies, league scores) lives in
      league/models.py — NOT here.  Import it as:
          from league.models import Company
      This file exports: CompanyProfile, CompanyGuidanceVideo, CompanySource,
      CompanyScoreSnapshot, DataIngestionLog.
"""
from django.conf import settings
from django.db import models
from django.utils.text import slugify
from core.storage import upload_to_guidance_thumbnail


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

# feat/stewardship-universe (PR 13) — a governed, explicit tracking
# lifecycle for the Stewardship Universe. Deliberately SEPARATE from the
# richer, mostly-derived operational states in Section 2 of the brief
# (NEEDS_SOURCE_DISCOVERY / NEEDS_REFRESH / REVIEW_REQUIRED / CURRENT /
# PARTIAL) — those are computed live from real conditions (source counts,
# review queue depth, refresh-policy due dates) by
# company_intelligence.services.stewardship_state.compute_tracking_state(),
# never stored, since a stored copy would drift the moment conditions
# change underneath it. Only the process-level lifecycle below is
# genuinely stateful and worth persisting: whether this company is tracked
# at all, whether a refresh is actively running right now (so a second
# concurrent trigger can be refused), and whether staff has explicitly
# paused it (which must NOT be silently resumed by a routine refresh call).
TRACKING_STATUS_CHOICES = [
    ('not_tracked', 'Not Tracked'),
    ('active', 'Active'),
    ('refresh_in_progress', 'Refresh In Progress'),
    ('paused', 'Paused'),
    ('error', 'Error — Last Refresh Failed'),
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
    waste_management_score     = models.FloatField(null=True, blank=True,
                                 help_text='0-100: quality of waste management practices')
    water_impact_score         = models.FloatField(null=True, blank=True,
                                 help_text='0-100: water stewardship quality')
    biodiversity_impact_score  = models.FloatField(null=True, blank=True,
                                 help_text='0-100: impact on biodiversity and ecosystems')

    # ── Social / Public Benefit ──
    jobs_created_score               = models.FloatField(null=True, blank=True,
                                       help_text='0-100: quality and quantity of employment')
    regional_development_score       = models.FloatField(null=True, blank=True,
                                       help_text='0-100: contribution to regional economy')
    community_investment             = models.BigIntegerField(null=True, blank=True,
                                       help_text='Annual community investment in USD')
    infrastructure_contribution_score= models.FloatField(null=True, blank=True,
                                       help_text='0-100: infrastructure contribution')
    national_value_score             = models.FloatField(null=True, blank=True,
                                       help_text='0-100: long-term national benefit')

    # ── Modernization ──
    modernization_investment      = models.BigIntegerField(null=True, blank=True,
                                    help_text='Annual modernization capex in USD')
    modernization_projects        = models.JSONField(default=list, blank=True,
                                    help_text='List of active modernization project names')
    energy_transition_score       = models.FloatField(null=True, blank=True,
                                    help_text='0-100: energy transition progress')
    digitalization_score          = models.FloatField(null=True, blank=True,
                                    help_text='0-100: digital transformation maturity')
    infrastructure_upgrade_score  = models.FloatField(null=True, blank=True,
                                    help_text='0-100: physical infrastructure modernity')
    future_readiness_score        = models.FloatField(null=True, blank=True,
                                    help_text='0-100: preparedness for future economy')

    # ── Transparency & Governance ──
    transparency_score_detail         = models.FloatField(null=True, blank=True,
                                        help_text='0-100: reporting quality and openness')
    audit_quality_score               = models.FloatField(null=True, blank=True,
                                        help_text='0-100: audit standards and independence')
    procurement_transparency_score    = models.FloatField(null=True, blank=True,
                                        help_text='0-100: procurement process openness')
    anti_corruption_score             = models.FloatField(null=True, blank=True,
                                        help_text='0-100: anti-corruption practices')
    controversy_risk_score            = models.FloatField(null=True, blank=True,
                                        help_text='0-100: higher = more controversy risk')
    governance_notes                  = models.TextField(blank=True)

    # ── EcoIQ Composite Scores (computed + stored) ──
    profit_extraction_score          = models.FloatField(null=True, blank=True,
                                       help_text='0-100: how much profit flows back to people vs. owners')
    profit_extraction_risk_score     = models.FloatField(null=True, blank=True,
                                       help_text='0-100: risk indicator — higher = more concern')
    public_benefit_score             = models.FloatField(null=True, blank=True)
    environmental_responsibility_score = models.FloatField(null=True, blank=True)
    modernization_score              = models.FloatField(null=True, blank=True)
    transparency_anti_corruption_score = models.FloatField(null=True, blank=True)
    ethical_alignment_score          = models.FloatField(null=True, blank=True)
    harm_penalty                     = models.FloatField(null=True, blank=True,
                                       help_text='Points deducted for pollution/harm (0-30)')
    ecoiq_total_score                = models.FloatField(null=True, blank=True)
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

    # ── Stewardship Universe tracking (feat/stewardship-universe, PR 13) ──
    tracking_status = models.CharField(
        max_length=20, choices=TRACKING_STATUS_CHOICES, default='not_tracked',
        help_text='Process-level lifecycle only — see TRACKING_STATUS_CHOICES docstring above for '
                   'why the richer operational states are computed live, never stored here.',
    )
    last_source_discovery_at = models.DateTimeField(
        null=True, blank=True, help_text='When discover_sources_for_company() last ran for this company.',
    )
    last_refresh_at = models.DateTimeField(
        null=True, blank=True, help_text='When refresh_company_intelligence() last completed (any status).',
    )
    next_refresh_due_at = models.DateTimeField(
        null=True, blank=True,
        help_text='Computed by services/refresh_policy.py from this company\'s registered sources\' own '
                   'refresh intervals — null when no source is registered yet (nothing to schedule).',
    )

    class Meta:
        ordering = ['-ecoiq_total_score', 'company__name']
        verbose_name        = 'Company Profile'
        verbose_name_plural = 'Company Profiles'

    def __str__(self):
        # D4A: the composite becomes nullable, and a profile with no score must
        # still be nameable — in the admin, in logs, and in error messages.
        score = self.ecoiq_total_score
        suffix = 'EcoIQ not yet scored' if score is None else f'EcoIQ {score:.1f}'
        return f'{self.company.name} — {suffix}'

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
        """
        Band for the composite, or None when there is no composite.

        None rather than 'Needs Improvement'. The old code fell through to the
        worst band for a company nobody had scored, which reads as a finding.
        """
        s = self.ecoiq_total_score
        if s is None: return None
        if s >= 85: return 'Exceptional'
        if s >= 70: return 'Strong'
        if s >= 60: return 'Moderate'
        if s >= 50: return 'Fair'
        return 'Needs Improvement'

    # D4A — these three are WARNINGS. Each says something adverse about a
    # company, so an unknown input must produce False, not a warning and not a
    # crash. False here means "we are not raising this flag", which is the
    # honest reading of an absent input; it is not a claim that the company is
    # fine, and nothing downstream treats it as one.

    @property
    def high_transition_need(self):
        return (
            self.pollution_level in ('high', 'severe') and
            self.modernization_score is not None and
            self.modernization_score < 40
        )

    @property
    def low_transparency_warning(self):
        return (
            self.transparency_score_detail is not None and
            self.transparency_score_detail < 30
        )

    @property
    def profit_extraction_warning(self):
        return (
            self.profit_extraction_score is not None and
            self.public_benefit_score is not None and
            self.profit_extraction_score > 75 and
            self.public_benefit_score < 50
        )

    @property
    def path_to_100_gap(self):
        """
        Points remaining to 100, or None when there is no score.

        Not 100. A company with no assessment has not been shown to have the
        largest possible gap — that would be the harshest reading of an
        absence, presented as a measurement.
        """
        score = self.ecoiq_total_score
        return None if score is None else max(0, 100 - score)


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
    thumbnail  = models.ImageField(upload_to=upload_to_guidance_thumbnail, null=True, blank=True)

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


# ── CompanyScoreSnapshot ───────────────────────────────────────────────────────

SNAPSHOT_TRIGGER_CHOICES = [
    ('manual',            'Manual (Admin)'),
    ('annual_review',     'Annual Review'),
    ('report_update',     'New Report / Evidence'),
    ('verification',      'Profile Verification'),
    ('transition',        'Transition Milestone'),
    ('seed',              'Initial Seed Score'),
    ('background_refresh', 'Automated Background Refresh'),
]


class CompanyScoreSnapshot(models.Model):
    """
    Point-in-time EcoIQ score record for a company.
    Tracks score progression over time — the foundation for
    'Transition Journey' and 'Score Evolution' views.

    Snapshots are created manually by admin or via management command.
    They are NEVER auto-generated on every save (stable, low-noise).
    """
    profile   = models.ForeignKey(
        CompanyProfile, on_delete=models.CASCADE,
        related_name='score_snapshots',
    )
    date      = models.DateField(help_text='Date this score was recorded / effective from')
    trigger   = models.CharField(
        max_length=30, choices=SNAPSHOT_TRIGGER_CHOICES, default='manual',
    )

    # Full pillar snapshot at time of recording
    total_score                    = models.FloatField(null=True, blank=True)
    public_benefit_score           = models.FloatField(null=True, blank=True)
    environmental_score            = models.FloatField(null=True, blank=True)
    modernization_score            = models.FloatField(null=True, blank=True)
    governance_score               = models.FloatField(null=True, blank=True)
    anti_corruption_score          = models.FloatField(null=True, blank=True)
    ethical_alignment_score        = models.FloatField(null=True, blank=True)
    harm_penalty                   = models.FloatField(null=True, blank=True)

    moral_label = models.CharField(max_length=40, blank=True)
    notes       = models.TextField(blank=True,
                                   help_text='Context — event, data source, milestone')

    # ── EcoIQ Intelligence Score (pandas_scoring_engine, Phase 1) ─────────────
    # A separate, additive composite — NOT a replacement for the six-pillar
    # governance/ESG score above (total_score), which remains the one used
    # for ranking order. Every *_score field is null until a real value has
    # actually been computed for at least one contributing input; never
    # fabricated to fill a gap. See pandas_scoring_engine/services/scoring.py
    # for how each is derived and intelligence_score_explanation for the full
    # input -> normalized score -> weight -> contribution trace.
    intelligence_score              = models.FloatField(null=True, blank=True)
    climate_risk_score              = models.FloatField(null=True, blank=True)
    evidence_quality_score          = models.FloatField(null=True, blank=True)
    investment_opportunity_score    = models.FloatField(null=True, blank=True)
    modernisation_priority_score    = models.FloatField(null=True, blank=True)
    geo_exposure_score              = models.FloatField(null=True, blank=True)
    intelligence_confidence         = models.FloatField(null=True, blank=True)
    intelligence_score_explanation  = models.JSONField(default=dict, blank=True)

    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering            = ['-date']
        verbose_name        = 'Score Snapshot'
        verbose_name_plural = 'Score Snapshots'

    def __str__(self):
        return (
            f'{self.profile.company.name} — '
            f'{self.total_score:.1f} on {self.date}'
        )

    @property
    def tier_label(self):
        s = self.total_score
        if s >= 85: return 'Regenerative Leader'
        if s >= 70: return 'Responsible Builder'
        if s >= 60: return 'Public-Benefit Oriented'
        if s >= 50: return 'Transitional Company'
        if s >= 30: return 'Profit-First Operator'
        return 'Extractive / Harmful'

    @property
    def tier_color(self):
        s = self.total_score
        if s >= 85: return '#00e89a'
        if s >= 70: return '#58a6ff'
        if s >= 60: return '#8b5cf6'
        if s >= 50: return '#f4a261'
        if s >= 30: return '#e63946'
        return '#b91c1c'

    @classmethod
    def create_from_profile(cls, profile, trigger='manual', notes='', intelligence_scores=None):
        """
        Convenience factory — take current scores from a live profile.
        intelligence_scores: optional dict from pandas_scoring_engine.services.
        scoring.compute_company_intelligence_score() — every key is optional,
        so existing callers that never pass this keep working unchanged.
        """
        import datetime
        intelligence_scores = intelligence_scores or {}
        return cls.objects.create(
            profile                  = profile,
            date                     = datetime.date.today(),
            trigger                  = trigger,
            total_score              = profile.ecoiq_total_score,
            public_benefit_score     = profile.public_benefit_score,
            environmental_score      = profile.environmental_responsibility_score,
            modernization_score      = profile.modernization_score,
            governance_score         = profile.transparency_anti_corruption_score,
            anti_corruption_score    = profile.anti_corruption_score,
            ethical_alignment_score  = profile.ethical_alignment_score,
            harm_penalty             = profile.harm_penalty,
            moral_label              = profile.moral_label,
            notes                    = notes,
            intelligence_score             = intelligence_scores.get('intelligence_score'),
            climate_risk_score             = intelligence_scores.get('climate_risk_score'),
            evidence_quality_score         = intelligence_scores.get('evidence_quality_score'),
            investment_opportunity_score   = intelligence_scores.get('investment_opportunity_score'),
            modernisation_priority_score   = intelligence_scores.get('modernisation_priority_score'),
            geo_exposure_score              = intelligence_scores.get('geo_exposure_score'),
            intelligence_confidence         = intelligence_scores.get('confidence'),
            intelligence_score_explanation  = intelligence_scores.get('explanation', {}),
        )


# ── DataIngestionLog ──────────────────────────────────────────────────────────

class DataIngestionLog(models.Model):
    """
    Audit trail for every automated data ingestion event.
    Records what was fetched, from which source, which fields were updated,
    and whether the operation succeeded.  Linked to league.Company so that
    ingestion history is visible on any company detail page.
    """
    SOURCE_CHOICES = [
        ('companies_house', 'Companies House UK'),
        ('sec_edgar',       'SEC EDGAR US'),
        ('cdp',             'CDP Climate Disclosure'),
        ('yfinance',        'Yahoo Finance / Bloomberg'),
        ('rss',             'Regulatory RSS Feed'),
        ('manual',          'Manual Admin Entry'),
    ]

    # Nullable so we can log pipeline-level errors that aren't company-specific
    company = models.ForeignKey(
        'league.Company',
        on_delete=models.CASCADE,
        related_name='ingestion_logs',
        null=True, blank=True,
    )
    source         = models.CharField(max_length=30, choices=SOURCE_CHOICES)
    raw_data       = models.JSONField(default=dict, blank=True)
    fields_updated = models.JSONField(default=list, blank=True)
    success        = models.BooleanField(default=True)
    error_msg      = models.TextField(blank=True)
    ingested_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering     = ['-ingested_at']
        verbose_name = 'Data Ingestion Log'
        verbose_name_plural = 'Data Ingestion Logs'

    def __str__(self):
        co = self.company.name if self.company_id else '(no company)'
        ts = self.ingested_at.strftime('%Y-%m-%d') if self.ingested_at else '—'
        return f'{self.get_source_display()} → {co} ({ts})'

REPORT_STATUS_CHOICES = [
    ('draft',     'Draft'),
    ('reviewed',  'Reviewed'),
    ('published', 'Published'),
]

INVESTMENT_CLASSIFICATION_CHOICES = [
    ('lower_exposure',       'Lower Identified Exposure'),
    ('moderate_exposure',    'Moderate Identified Exposure'),
    ('elevated_exposure',    'Elevated Identified Exposure'),
    ('high_exposure',        'High Identified Exposure'),
    ('insufficient_evidence','Insufficient Evidence'),
]

REPORT_SECTION_KEYS = [
    'executive_assessment',
    'key_risks',
    'positive_signals',
    'transition_regulatory_exposure',
    'controversies_evidence_concerns',
    'sector_relative_context',
    'data_confidence',
    'due_diligence_questions',
]


class InvestmentRelevanceReport(models.Model):
    """
    EcoIQ Investment Relevance Report — a versioned, AI-assisted analysis of
    how a company's environmental/stewardship profile may be relevant to
    long-term investment risk. This is sustainability-risk intelligence, NOT
    investment advice: see companies.ai_helpers.PROHIBITED_INVESTMENT_TERMS
    and services/investment_report.py for the language the model is
    forbidden from using, and the deterministic check that enforces it
    before a report can be published.

    Never overwritten in place — a new generation creates the next `version`
    for the company, so historical reports remain auditable. Only
    status='published' reports are ever shown to public (non-staff) users;
    draft/reviewed stay staff-only, mirroring the human-approval-before-
    publish pattern already used by
    agent_runtime_model_router.services.human_approval_gate for other
    public-facing AI content.
    """
    company = models.ForeignKey(
        CompanyProfile, on_delete=models.CASCADE,
        related_name='investment_reports',
    )
    version = models.PositiveIntegerField(help_text='1-based, incremented per company on each generation')
    status  = models.CharField(max_length=10, choices=REPORT_STATUS_CHOICES, default='draft')

    classification = models.CharField(max_length=25, choices=INVESTMENT_CLASSIFICATION_CHOICES)

    # ── Structured report content ──
    # Keys: executive_assessment, key_risks, positive_signals,
    # transition_regulatory_exposure, controversies_evidence_concerns,
    # sector_relative_context, data_confidence, due_diligence_questions.
    # Each risk/signal entry is a dict that may include an `evidence` list
    # of {type, detail, source, date, confidence} citations — see
    # services/investment_report.py:EVIDENCE_TYPE_CHOICES for what `type`
    # ('verified_evidence' | 'company_reported' | 'external_allegation' |
    # 'ai_interpretation' | 'insufficient_evidence') means.
    content = models.JSONField(default=dict, blank=True)

    # ── Grounding / reproducibility ──
    source_snapshot = models.JSONField(
        default=dict, blank=True,
        help_text='Copy of the EcoIQ scores/fields the report was generated from, for audit')

    # ── Generation provenance ──
    model_name          = models.CharField(max_length=80, blank=True)
    model_provider       = models.CharField(max_length=30, blank=True,
                            help_text='Provider selected by agent_runtime_model_router for this generation')
    routing_reason       = models.TextField(blank=True,
                            help_text='Why the model router selected this provider/model')
    prompt_version       = models.CharField(max_length=20, default='v1')
    methodology_version  = models.CharField(max_length=20, default='v1')

    prohibited_language_flags = models.JSONField(
        default=list, blank=True,
        help_text='Findings from the prohibited-recommendation-language check; must be empty to publish')

    generated_at = models.DateTimeField(auto_now_add=True)
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='+',
        help_text='Admin/analyst who triggered generation')

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='+')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-version']
        unique_together = [('company', 'version')]
        verbose_name = 'Investment Relevance Report'
        verbose_name_plural = 'Investment Relevance Reports'

    def __str__(self):
        return f'{self.company.company.name} — Investment Relevance v{self.version} ({self.status})'

    @property
    def classification_display(self):
        return dict(INVESTMENT_CLASSIFICATION_CHOICES).get(self.classification, self.classification)

    @property
    def is_publishable(self) -> bool:
        """A report can only move to published when it carries no prohibited-language flags."""
        return not self.prohibited_language_flags


# ── DataIngestionLog ──────────────────────────────────────────────────────────


# ── CompanyMetricProvenance (D3A) ──────────────────────────────────────────────

class CompanyMetricProvenance(models.Model):
    """
    Where one metric on one CompanyProfile came from.

    D3A — provenance foundation. Answers "where did this value come from?", and
    deliberately nothing else. It does not decide whether a value may be
    published (D5), and it does not touch the score columns' nullability (D4).

    Shaped after company_intelligence.CompanyFinancialFactSource, which already
    solved this problem for financial facts: an ENUMERATED metric key, evidence
    by ForeignKey, and a `value` property that RESOLVES the number rather than
    storing a second copy of it. Following an existing, working pattern beats
    inventing a parallel one — see docs/product/PROVENANCE_ARCHITECTURE.md.

    Three things this model deliberately does NOT do:

    1.  It does not copy the value. `CompanyProfile.public_benefit_score = 72`
        and a provenance row storing `value = 72` would be two numbers free to
        drift. The `value` property reads through instead.

    2.  It does not duplicate EvidenceMemory. Source URL, source type,
        verification status, review tier, reviewer and expiry all already live
        there, and are reached through `evidence`.

    3.  It does not conflate ORIGIN with EVIDENCE QUALITY. Those vary
        independently — a MODELLED value can rest on excellent sources, and a
        MEASURED one on poor ones — so origin lives here and quality is read
        from the linked evidence.

    Append-only: a partial unique constraint allows exactly one `is_current` row
    per (company, metric_key) while history accumulates behind it. Overwriting
    in place would destroy the previous provenance, which is precisely what
    makes an audit trail impossible.
    """
    company = models.ForeignKey(
        CompanyProfile, on_delete=models.CASCADE, related_name='metric_provenance',
    )
    metric_key = models.CharField(
        max_length=60,
        help_text='Registered metric key. Validated against '
                  'companies.metric_registry on save — a typo is rejected '
                  'rather than becoming a silently orphaned row. Material keys '
                  'are bare CompanyProfile field names; derived keys are '
                  'namespaced (ethics.nei, mizan.score).',
    )

    # ── Origin: HOW the value was created ────────────────────────────────────
    origin = models.CharField(
        max_length=30,
        help_text='One of companies.evidence.PROVENANCE_CHOICES. No default: a '
                  'value whose origin nobody stated must not silently become '
                  'MEASURED, which is the strongest claim in the vocabulary.',
    )

    # ── Supporting evidence, by reference ────────────────────────────────────
    evidence = models.ForeignKey(
        'evidence_memory.EvidenceMemory', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='metric_provenance',
        help_text='SET_NULL rather than CASCADE: losing the evidence record '
                  'must not erase the fact that this value once had a stated '
                  'origin. The row survives and says so.',
    )
    source_quality = models.CharField(
        max_length=20, blank=True,
        help_text='Optional analyst override for cases with no EvidenceMemory '
                  'row. Where evidence IS linked, its own source_type and '
                  'review_tier are authoritative and this stays blank.',
    )

    # ── Confidence — nullable, never defaulted ───────────────────────────────
    confidence = models.FloatField(
        null=True, blank=True,
        help_text='0-100. NULL means unknown confidence — never fabricated, and '
                  'never 50. A genuine 0.0 stays distinguishable from unknown.',
    )

    # ── Method and versioning ────────────────────────────────────────────────
    methodology = models.TextField(
        blank=True,
        help_text='How the value was produced. Expected for ESTIMATED, MODELLED '
                  'and INFERRED, where the number is only as defensible as the '
                  'method behind it.',
    )
    calculation_version = models.CharField(
        max_length=30, blank=True,
        help_text='Version of the model or formula that produced a MODELLED or '
                  'ESTIMATED value, so a later change is attributable.',
    )
    observed_at = models.DateTimeField(
        null=True, blank=True,
        help_text='When the underlying observation was made — distinct from '
                  'created_at, which is when EcoIQ recorded it.',
    )

    # ── Human review: independent of origin ──────────────────────────────────
    review_status = models.CharField(
        max_length=25, default='proposed',
        help_text="Reuses company_intelligence.CompanyKPIEvidenceLink's review "
                  'vocabulary rather than inventing a sixth. Independent of '
                  'origin: MEASURED is not auto-reviewed, and MODELLED is not '
                  'auto-distrusted.',
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='+',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    #: D3C-2 — the value, ONLY for ephemeral derived metrics.
    #:
    #: D3A's rule stands for everything with a home: no duplicate value, because
    #: two copies can drift. But Mizan, responsible-finance and greenwashing are
    #: recomputed per request and never stored, so provenance that recorded only
    #: their method could not reconstruct what was actually computed — the
    #: lineage would describe a number nobody could see again.
    #:
    #: Enforced in clean(): NULL unless the metric is registered as ephemeral.
    recorded_value = models.FloatField(
        null=True, blank=True,
        help_text='The computed value, for ephemeral derived metrics only. '
                  'Must be NULL for any metric whose value has a persisted home '
                  '— that value is resolved through the registry instead.',
    )

    #: D3C-2 — lineage AS COMPUTED.
    #:
    #: Points at the specific provenance ROWS a calculation consumed, not at
    #: metric keys. Keys would resolve to whatever is current when asked, which
    #: answers "what would this metric's lineage be if computed now?" — not
    #: "what was it when computed?". Only the second is an audit trail.
    inputs = models.ManyToManyField(
        'self', symmetrical=False, blank=True, related_name='derived_from',
        help_text='The provenance rows this calculation consumed. Empty for '
                  'material metrics, which have no inputs.',
    )

    notes = models.TextField(blank=True)

    is_current = models.BooleanField(
        default=True,
        help_text='Exactly one current row per company+metric, enforced by a '
                  'partial unique constraint. Superseded rows stay for audit.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='+',
    )
    written_by = models.CharField(
        max_length=100, blank=True,
        help_text="Machine writer that created this row (e.g. 'seed_companies', "
                  "'ingest_sec_edgar', 'companies.scoring'). Populated by D3C.",
    )

    class Meta:
        ordering = ['metric_key', '-created_at']
        verbose_name = 'Company Metric Provenance'
        verbose_name_plural = 'Company Metric Provenance'
        constraints = [
            # Partial unique index — supported on both SQLite and PostgreSQL.
            # History accumulates; the current state stays unambiguous.
            models.UniqueConstraint(
                fields=['company', 'metric_key'],
                condition=models.Q(is_current=True),
                name='companies_unique_current_metric_provenance',
            ),
        ]
        indexes = [
            # The only access pattern D3A has. Deliberately NOT indexing origin,
            # review_status or created_at: no query needs them yet, and an
            # unused index is a write cost with no reader.
            models.Index(fields=['company', 'metric_key'],
                         name='companies_prov_company_metric'),
        ]

    def __str__(self):
        return f'{self.company} — {self.metric_key} ({self.origin})'

    @property
    def value(self):
        """
        The number this row is provenance FOR.

        Resolved through the registry for anything with a persisted home — a
        stored copy could drift from the field it describes. For an ephemeral
        metric there is no field to read, so the recorded value is returned:
        that is the whole reason recorded_value exists.
        """
        from companies.metric_registry import get_metric_definition

        definition = get_metric_definition(self.metric_key)
        if definition is None:
            return None
        if definition.is_ephemeral:
            return self.recorded_value
        return definition.resolve(self.company)

    def clean(self):
        from django.core.exceptions import ValidationError

        from companies.evidence import PROVENANCE_CHOICES
        from companies.metric_registry import get_metric_definition

        valid_origins = {code for code, _ in PROVENANCE_CHOICES}
        if self.origin not in valid_origins:
            raise ValidationError({'origin': f'Unknown provenance state: {self.origin!r}.'})

        definition = get_metric_definition(self.metric_key)
        if definition is None:
            raise ValidationError({
                'metric_key': f'{self.metric_key!r} is not a registered EcoIQ metric. '
                              'Register it in companies/metric_registry.py — '
                              'provenance never accepts an unregistered key.',
            })

        # An origin must be honest for the KIND of metric. This is the guard
        # against the mislabel D3C-1 identified as most likely to slip through:
        # a derived composite recorded as MEASURED, claiming an observation that
        # never happened however good its inputs were.
        if self.origin not in definition.allowed_origins:
            raise ValidationError({
                'origin': f'{self.origin!r} is not an honest origin for '
                          f'{self.metric_key!r} ({definition.kind}). Allowed: '
                          f'{", ".join(sorted(definition.allowed_origins))}.',
            })

        if self.recorded_value is not None and not definition.is_ephemeral:
            raise ValidationError({
                'recorded_value': f'{self.metric_key!r} has a persisted value at '
                                  f'{definition.value_location}; storing a second '
                                  f'copy here would let the two drift.',
            })

    def save(self, *args, **kwargs):
        # Validate on every save, including programmatic ones. full_clean() is
        # not called by Model.save() in Django, so an unvalidated metric_key
        # would otherwise reach the database from a script.
        self.clean()
        return super().save(*args, **kwargs)
