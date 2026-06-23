"""
EcoIQ Quranic Decision Filter (QDF) — Models.

Thesis: "Create rizq without zulm." — create wealth without injustice.

Evaluates any company, investment, policy, infrastructure project, or
government decision through 10 Qur'anic decision questions, producing a
Decision Integrity Score (0–100), a risk level, and a verdict.

Models
======
DecisionQuestion    Registry of the 10 questions (definition, rubric, AI prompt,
                    evidence requirements, red flags, low-score actions, examples).
                    Seeded from qdf/seed/decision_questions.json.
DecisionAssessment  One assessment of a subject (company / investment / policy /
                    infrastructure / government). Holds the overall score, risk,
                    verdict, evidence posture, and the "rizq without zulm" summary.
QuestionScore       Per-question 0–10 result for an assessment (rationale,
                    evidence status, triggered red flags, recommended actions).

NOTE: QDF is an AI-assisted governance lens inspired by Qur'anic principles. It
is NOT fatwa, tafsir, or a Shariah ruling. Religious framing is non-authoritative
and pending qualified scholarly review. All computed scores are indicative and
evidence-gated, consistent with EcoIQ's intelligence-output disclaimers.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone


# ── Choice sets ────────────────────────────────────────────────────────────────

SUBJECT_TYPE_CHOICES = [
    ('company',        'Company'),
    ('investment',     'Investment Decision'),
    ('policy',         'Government Policy'),
    ('infrastructure', 'Infrastructure Project'),
    ('government',     'Government Decision'),
]

RISK_LEVEL_CHOICES = [
    ('low',      'Low'),
    ('moderate', 'Moderate'),
    ('elevated', 'Elevated'),
    ('high',     'High'),
    ('severe',   'Severe'),
]

VERDICT_CHOICES = [
    ('proceed',              'Proceed'),
    ('proceed_conditions',   'Proceed with Conditions'),
    ('revise',               'Revise Before Proceeding'),
    ('do_not_proceed',       'Do Not Proceed'),
]

EVIDENCE_STATUS_CHOICES = [
    ('verified',     'Verified'),
    ('partial',      'Partial'),
    ('insufficient', 'Insufficient'),
    ('unverified',   'Unverified'),
]

QUESTION_EVIDENCE_STATUS = [
    ('verified',     'Verified'),
    ('partial',      'Partial'),
    ('insufficient', 'Insufficient'),
    ('missing',      'Missing'),
]

SOURCE_CHOICES = [
    ('auto',    'Auto-computed from EcoIQ profile'),
    ('analyst', 'Analyst-authored'),
]


# ── DecisionQuestion (the 10-question registry) ─────────────────────────────────

class DecisionQuestion(models.Model):
    """One of the 10 Qur'anic decision questions. Seeded; rarely edited."""
    key           = models.SlugField(max_length=20, unique=True,
                        help_text='Stable key: niyyah, halal, adl, …')
    order         = models.PositiveSmallIntegerField(default=0)
    arabic_term   = models.CharField(max_length=40)
    title_en      = models.CharField(max_length=60)
    core_question = models.CharField(max_length=200)
    weight        = models.FloatField(default=1.0,
                        help_text='Relative weight in the Decision Integrity Score')

    definition        = models.TextField()
    plain_english     = models.TextField()
    evidence_required = models.JSONField(default=list, blank=True)
    red_flags         = models.JSONField(default=list, blank=True)
    scoring_rubric    = models.JSONField(default=dict, blank=True,
                            help_text='Band → description, e.g. {"0-2": "…"}')
    ai_prompt         = models.TextField(blank=True,
                            help_text='Prompt used by the AI reasoning engine')
    low_score_actions = models.JSONField(default=list, blank=True)

    example_company    = models.TextField(blank=True)
    example_policy     = models.TextField(blank=True)
    example_investment = models.TextField(blank=True)

    is_red_line = models.BooleanField(default=False,
                    help_text='Severe failure caps the overall score (justice not traded off)')
    is_active   = models.BooleanField(default=True)

    class Meta:
        ordering            = ['order']
        verbose_name        = 'Decision Question'
        verbose_name_plural = 'Decision Questions (the 10)'

    def __str__(self):
        return f'{self.order}. {self.arabic_term} — {self.title_en}'


# ── DecisionAssessment ──────────────────────────────────────────────────────────

class DecisionAssessment(models.Model):
    """A single QDF assessment of one subject."""
    # Optional link to a company profile (for company subjects / detail-page integration)
    profile = models.ForeignKey(
        'companies.CompanyProfile',
        on_delete=models.CASCADE,
        related_name='qdf_assessments',
        null=True, blank=True,
    )

    subject_type = models.CharField(max_length=20, choices=SUBJECT_TYPE_CHOICES,
                        default='company')
    subject_name = models.CharField(max_length=200,
                        help_text='e.g. "Carbon Tax Bill 2026", "Series A — SolarCo"')
    subject_ref  = models.CharField(max_length=300, blank=True,
                        help_text='Optional slug / id / URL for the subject')

    # ── Headline outputs ────────────────────────────────────────────────────
    decision_integrity_score = models.FloatField(default=0.0,
                        help_text='0–100 weighted Decision Integrity Score')
    risk_level   = models.CharField(max_length=10, choices=RISK_LEVEL_CHOICES,
                        default='moderate')
    verdict      = models.CharField(max_length=20, choices=VERDICT_CHOICES,
                        default='revise')
    evidence_status = models.CharField(max_length=12, choices=EVIDENCE_STATUS_CHOICES,
                        default='unverified')
    confidence   = models.FloatField(default=0.5, help_text='0–1 confidence')

    rizq_without_zulm_summary = models.TextField(blank=True,
                        help_text='One-line "Create Rizq Without Zulm" verdict')
    ai_narrative = models.TextField(blank=True)
    red_line_breached = models.BooleanField(default=False)

    # ── Workflow ────────────────────────────────────────────────────────────
    source           = models.CharField(max_length=10, choices=SOURCE_CHOICES, default='auto')
    analyst_reviewed = models.BooleanField(default=False)
    analyst_notes    = models.TextField(blank=True)
    created_by       = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                            on_delete=models.SET_NULL, related_name='qdf_assessments')
    created_at       = models.DateTimeField(default=timezone.now)
    last_computed    = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ['-last_computed']
        verbose_name        = 'Decision Assessment'
        verbose_name_plural = 'Decision Assessments'
        constraints = [
            # At most one auto-computed assessment per company profile
            models.UniqueConstraint(
                fields=['profile', 'source'],
                condition=models.Q(source='auto'),
                name='uniq_auto_assessment_per_profile',
            ),
        ]

    def __str__(self):
        return f'QDF · {self.subject_name} ({self.decision_integrity_score:.0f}/100)'

    # ── Derived display helpers ──────────────────────────────────────────────

    @property
    def integrity_band(self):
        s = self.decision_integrity_score
        if s >= 80: return 'Stewardship-Grade'
        if s >= 65: return 'Responsible'
        if s >= 50: return 'Transitional'
        if s >= 35: return 'Compromised'
        return 'Unsound'

    @property
    def integrity_color(self):
        s = self.decision_integrity_score
        if s >= 80: return '#00e89a'
        if s >= 65: return '#58a6ff'
        if s >= 50: return '#8b5cf6'
        if s >= 35: return '#f4a261'
        return '#e63946'

    @property
    def risk_color(self):
        return {
            'low':      '#00e89a',
            'moderate': '#58a6ff',
            'elevated': '#8b5cf6',
            'high':     '#f4a261',
            'severe':   '#e63946',
        }.get(self.risk_level, '#888')

    @property
    def verdict_display(self):
        return dict(VERDICT_CHOICES).get(self.verdict, self.verdict)

    @property
    def verdict_color(self):
        return {
            'proceed':            '#00e89a',
            'proceed_conditions': '#58a6ff',
            'revise':             '#f4a261',
            'do_not_proceed':     '#e63946',
        }.get(self.verdict, '#888')

    @property
    def evidence_status_color(self):
        return {
            'verified':     '#00e89a',
            'partial':      '#58a6ff',
            'insufficient': '#f4a261',
            'unverified':   '#94a3b8',
        }.get(self.evidence_status, '#888')

    @property
    def confidence_pct(self):
        return round((self.confidence or 0) * 100)

    @property
    def red_flag_count(self):
        return sum(len(qs.red_flags_triggered or []) for qs in self.question_scores.all())

    @property
    def ordered_scores(self):
        return self.question_scores.select_related('question').order_by('question__order')


# ── QuestionScore ───────────────────────────────────────────────────────────────

class QuestionScore(models.Model):
    """Per-question 0–10 result within a DecisionAssessment."""
    assessment = models.ForeignKey(DecisionAssessment, on_delete=models.CASCADE,
                        related_name='question_scores')
    question   = models.ForeignKey(DecisionQuestion, on_delete=models.PROTECT,
                        related_name='scores')

    score           = models.FloatField(default=0.0, help_text='0–10')
    rationale       = models.TextField(blank=True)
    evidence_status = models.CharField(max_length=12, choices=QUESTION_EVIDENCE_STATUS,
                        default='insufficient')
    red_flags_triggered  = models.JSONField(default=list, blank=True)
    recommended_actions  = models.JSONField(default=list, blank=True)

    class Meta:
        ordering            = ['question__order']
        unique_together     = [('assessment', 'question')]
        verbose_name        = 'Question Score'
        verbose_name_plural = 'Question Scores'

    def __str__(self):
        return f'{self.assessment.subject_name} · {self.question.title_en}: {self.score:.0f}/10'

    @property
    def score_color(self):
        if self.score >= 8: return '#00e89a'
        if self.score >= 6: return '#58a6ff'
        if self.score >= 4: return '#f4a261'
        return '#e63946'

    @property
    def score_pct(self):
        return round(min(max(self.score, 0), 10) * 10)

    @property
    def band(self):
        if self.score >= 9: return '9-10'
        if self.score >= 6: return '6-8'
        if self.score >= 3: return '3-5'
        return '0-2'
