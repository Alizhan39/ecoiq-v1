"""
EcoIQ Financing Intelligence Engine — Models.

CompanyFinancingProfile   Per-company readiness assessment and financing intelligence.
DirectFinancingMatch      Company ↔ FinancingOpportunity match (no roadmap required).
"""
from django.db import models


# ── Readiness tier choices ─────────────────────────────────────────────────────

READINESS_TIER = [
    ('investment_ready', 'Investment Ready'),
    ('nearly_ready',     'Nearly Ready'),
    ('developing',       'Developing'),
    ('early_stage',      'Early Stage'),
]

FUNDING_URGENCY = [
    ('critical', 'Critical — Immediate Need'),
    ('high',     'High — 1–2 Years'),
    ('medium',   'Medium — 2–5 Years'),
    ('low',      'Low — Long-term'),
]

MATCH_TIER = [
    ('eligible',  'Eligible'),
    ('likely',    'Likely Eligible'),
    ('potential', 'Potential'),
    ('unlikely',  'Unlikely'),
]


# ── CompanyFinancingProfile ────────────────────────────────────────────────────

class CompanyFinancingProfile(models.Model):
    """
    Per-company financing intelligence and readiness assessment.
    Computed from CompanyProfile scores — no additional data collection.
    Linked 1:1 to CompanyProfile via OneToOneField.
    """
    profile = models.OneToOneField(
        'companies.CompanyProfile',
        on_delete=models.CASCADE,
        related_name='financing_intel',
    )

    # ── Readiness scores (0–100) ───────────────────────────────────────────
    financing_readiness      = models.FloatField(default=0.0,
        help_text='Overall financing readiness 0–100')
    modernization_readiness  = models.FloatField(default=0.0,
        help_text='Industrial modernization preparedness 0–100')
    transparency_readiness   = models.FloatField(default=0.0,
        help_text='Disclosure and reporting quality for DFI compliance 0–100')
    climate_readiness        = models.FloatField(default=0.0,
        help_text='Climate transition progress and environmental commitment 0–100')
    governance_readiness     = models.FloatField(default=0.0,
        help_text='Governance and anti-corruption standards 0–100')
    evidence_completeness    = models.FloatField(default=0.0,
        help_text='Data completeness and source quality 0–100')

    # ── Overall tier and urgency ───────────────────────────────────────────
    readiness_tier   = models.CharField(max_length=20, choices=READINESS_TIER,
                        default='early_stage')
    funding_urgency  = models.CharField(max_length=15, choices=FUNDING_URGENCY,
                        default='medium')

    # ── Financial intelligence ─────────────────────────────────────────────
    estimated_capex_low_usd     = models.BigIntegerField(null=True, blank=True,
        help_text='Low-end capex estimate for priority modernization projects (USD)')
    estimated_capex_high_usd    = models.BigIntegerField(null=True, blank=True,
        help_text='High-end capex estimate (USD)')
    estimated_annual_impact_usd = models.BigIntegerField(null=True, blank=True,
        help_text='Estimated annual economic/environmental impact at full implementation (USD)')

    # ── Gap analysis ───────────────────────────────────────────────────────
    missing_requirements = models.JSONField(default=list, blank=True,
        help_text='List of {label, detail, priority, impact} dicts blocking financing')
    next_actions         = models.JSONField(default=list, blank=True,
        help_text='Ordered list of recommended next steps')

    # ── AI narrative (generated at compute time, revised by analyst) ───────
    ai_financing_narrative = models.TextField(blank=True,
        help_text='Plain-language financing pathway description')
    ai_gap_analysis        = models.TextField(blank=True,
        help_text='Gaps preventing optimal financing readiness')

    # ── Confidence ────────────────────────────────────────────────────────
    confidence = models.FloatField(default=0.5,
        help_text='0–1 confidence in readiness assessment')

    # ── Workflow ──────────────────────────────────────────────────────────
    last_computed    = models.DateTimeField(auto_now=True)
    analyst_reviewed = models.BooleanField(default=False)
    analyst_notes    = models.TextField(blank=True)

    class Meta:
        verbose_name        = 'Company Financing Profile'
        verbose_name_plural = 'Company Financing Profiles'

    def __str__(self):
        return f'{self.profile.company.name} — Financing Intelligence'

    # ── Derived properties ─────────────────────────────────────────────────

    @property
    def readiness_tier_display(self):
        return dict(READINESS_TIER).get(self.readiness_tier, 'Unknown')

    @property
    def readiness_tier_color(self):
        return {
            'investment_ready': '#00e89a',
            'nearly_ready':     '#58a6ff',
            'developing':       '#8b5cf6',
            'early_stage':      '#f4a261',
        }.get(self.readiness_tier, '#888')

    @property
    def urgency_color(self):
        return {
            'critical': '#e63946',
            'high':     '#f4a261',
            'medium':   '#58a6ff',
            'low':      '#00e89a',
        }.get(self.funding_urgency, '#888')

    @property
    def capex_range_label(self):
        def _fmt(v):
            if v >= 1_000_000_000: return f'${v / 1_000_000_000:.1f}B'
            if v >= 1_000_000:     return f'${v / 1_000_000:.0f}M'
            return f'${v / 1_000:.0f}K'
        lo, hi = self.estimated_capex_low_usd, self.estimated_capex_high_usd
        if lo and hi:
            return f'{_fmt(lo)} – {_fmt(hi)}'
        if hi:
            return f'up to {_fmt(hi)}'
        return 'Not estimated'

    @property
    def impact_label(self):
        if not self.estimated_annual_impact_usd:
            return '—'
        v = self.estimated_annual_impact_usd
        if v >= 1_000_000: return f'${v / 1_000_000:.0f}M / yr'
        return f'${v / 1_000:.0f}K / yr'

    @property
    def match_count(self):
        return self.profile.financing_matches.count()

    @property
    def top_matches(self):
        return self.profile.financing_matches.filter(
            match_tier__in=['eligible', 'likely']
        ).select_related('opportunity').order_by('-match_score')[:5]


# ── DirectFinancingMatch ───────────────────────────────────────────────────────

class DirectFinancingMatch(models.Model):
    """
    Matched FinancingOpportunity for a company — computed directly from
    CompanyProfile scores without requiring a TransitionRoadmap.
    """
    profile     = models.ForeignKey(
        'companies.CompanyProfile',
        on_delete=models.CASCADE,
        related_name='financing_matches',
    )
    opportunity = models.ForeignKey(
        'transition.FinancingOpportunity',
        on_delete=models.CASCADE,
        related_name='direct_matches',
    )

    match_score  = models.FloatField(default=0.0,
        help_text='0–100 match quality')
    match_tier   = models.CharField(max_length=15, choices=MATCH_TIER,
        default='potential')
    match_rationale = models.TextField(blank=True)

    missing_requirements = models.JSONField(default=list, blank=True,
        help_text='Items blocking full eligibility for this instrument')
    next_steps           = models.JSONField(default=list, blank=True)

    recommended_amount_usd = models.BigIntegerField(null=True, blank=True)
    is_featured            = models.BooleanField(default=False)
    computed_at            = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ['-match_score']
        unique_together     = [('profile', 'opportunity')]
        verbose_name        = 'Direct Financing Match'
        verbose_name_plural = 'Direct Financing Matches'

    def __str__(self):
        return (
            f'{self.profile.company.name} ↔ '
            f'{self.opportunity.institution_name} ({self.match_tier})'
        )

    @property
    def tier_color(self):
        return {
            'eligible':  '#00e89a',
            'likely':    '#58a6ff',
            'potential': '#8b5cf6',
            'unlikely':  '#64748b',
        }.get(self.match_tier, '#888')

    @property
    def recommended_amount_label(self):
        if not self.recommended_amount_usd:
            return '—'
        v = self.recommended_amount_usd
        if v >= 1_000_000_000: return f'${v / 1_000_000_000:.1f}B'
        if v >= 1_000_000:     return f'${v / 1_000_000:.0f}M'
        return f'${v / 1_000:.0f}K'
