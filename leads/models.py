import os
import random
from django.db import models
from django.utils import timezone


INDUSTRY_CHOICES = [
    ('oil_gas',          'Oil & Gas / Refining'),
    ('manufacturing',    'Manufacturing (General)'),
    ('automotive',       'Automotive'),
    ('chemicals',        'Chemicals & Petrochemicals'),
    ('pharma',           'Pharmaceuticals'),
    ('food_beverage',    'Food & Beverage'),
    ('utilities',        'Utilities / Energy'),
    ('logistics',        'Logistics & Warehousing'),
    ('metals_mining',    'Metals & Mining'),
    ('other',            'Other Heavy Industry'),
]

COMPANY_SIZE_CHOICES = [
    ('1_50',       '1–50 employees'),
    ('51_200',     '51–200 employees'),
    ('201_1000',   '201–1,000 employees'),
    ('1001_5000',  '1,001–5,000 employees'),
    ('5001_plus',  '5,001+ employees'),
]

# Stakeholder role — optional self-identification on the access request form
ROLE_CHOICES = [
    ('investor',   'Investor'),
    ('company',    'Company'),
    ('government', 'Government'),
    ('consultant', 'Consultant'),
    ('analyst',    'Analyst'),
    ('other',      'Other'),
]

# Lead pipeline — Investor Readiness Report workflow stages
STATUS_CHOICES = [
    ('new',           'New'),
    ('reviewed',      'Reviewed'),
    ('sample_sent',   'Sample Sent'),
    ('call_booked',   'Call Booked'),
    ('proposal_sent', 'Proposal Sent'),
    ('won',           'Won'),
    ('lost',          'Lost'),
]

# Which EcoIQ product the requester is interested in
PRODUCT_INTEREST_CHOICES = [
    ('free_scan',           'Free Scan'),
    ('readiness_report',    'Investor Readiness Report'),
    ('institutional_pilot', 'Institutional Pilot'),
]


class AccessRequest(models.Model):
    # Contact
    full_name    = models.CharField(max_length=200)
    company      = models.CharField(max_length=200)
    work_email   = models.EmailField(db_index=True)

    # Profile — originally required for the industrial-audit form; now optional so
    # the simpler Investor Readiness Report form can reuse this model non-destructively.
    industry      = models.CharField(max_length=30, choices=INDUSTRY_CHOICES, blank=True)
    facility_type = models.CharField(max_length=200, blank=True, help_text='e.g. Continuous process refinery, Cold-chain warehouse')
    company_size  = models.CharField(max_length=20, choices=COMPANY_SIZE_CHOICES, blank=True)

    # Optional context — added non-destructively (all blank=True)
    country = models.CharField(max_length=100, blank=True, help_text='Country of operation (optional)')
    role    = models.CharField(
        max_length=30, choices=ROLE_CHOICES, blank=True,
        help_text='How the requester identifies themselves (optional)',
    )

    # Investor Readiness Report workflow fields (all optional, additive)
    target_entity    = models.CharField(
        max_length=300, blank=True,
        help_text='Company or project the requester wants assessed',
    )
    sector           = models.CharField(max_length=120, blank=True, help_text='Sector of the company/project (optional)')
    product_interest = models.CharField(
        max_length=30, choices=PRODUCT_INTEREST_CHOICES, blank=True,
        help_text='Which EcoIQ product the requester is interested in',
    )

    # Qualification — challenge now optional (simpler report form does not require it)
    challenge = models.TextField(blank=True, help_text='Main operational challenge (optional)')
    message   = models.TextField(blank=True, help_text='Optional additional context')

    # Security
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    # CRM
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    notes  = models.TextField(blank=True, help_text='Internal notes — not visible to the submitter')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering       = ['-created_at']
        verbose_name   = 'Access Request'
        verbose_name_plural = 'Access Requests'

    def __str__(self):
        return f'{self.full_name} — {self.company} ({self.get_status_display()})'


# ── ProfileClaim ──────────────────────────────────────────────────────────────

CLAIM_STATUS_CHOICES = [
    ('pending',   'Pending Review'),
    ('approved',  'Approved'),
    ('rejected',  'Rejected'),
    ('duplicate', 'Duplicate'),
]


def _generate_claim_ref():
    """Return a unique CLM-YYYYMMDD-XXXX reference string."""
    today  = timezone.now().strftime('%Y%m%d')
    suffix = ''.join(random.choices('ABCDEFGHJKLMNPQRSTUVWXYZ23456789', k=4))
    return f'CLM-{today}-{suffix}'


class ProfileClaim(models.Model):
    """
    Submitted when a company representative wants to claim / manage their
    EcoIQ profile.  Auto-generates a unique CLM-YYYYMMDD-XXXX reference on save.
    """

    # Auto-generated reference — shown to claimant and used in admin/email
    ref = models.CharField(
        max_length=20, unique=True, editable=False, db_index=True,
        help_text='Auto-generated claim reference (CLM-YYYYMMDD-XXXX)',
    )

    # Which EcoIQ company profile is being claimed
    company_slug = models.CharField(
        max_length=200, db_index=True, blank=True,
        help_text='Slug of the EcoIQ company profile being claimed',
    )
    company_name_reported = models.CharField(
        max_length=200, blank=True,
        help_text='Company name as entered by the claimant',
    )

    # Claimant contact details
    full_name  = models.CharField(max_length=200)
    work_email = models.EmailField(db_index=True)
    job_title  = models.CharField(max_length=200)
    phone      = models.CharField(max_length=50, blank=True)

    # Justification / context
    message = models.TextField(
        blank=True,
        help_text='Why the claimant is entitled to manage this profile',
    )

    # Security
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    # CRM pipeline
    status = models.CharField(
        max_length=20, choices=CLAIM_STATUS_CHOICES, default='pending',
    )
    notes = models.TextField(
        blank=True,
        help_text='Internal notes — not visible to the claimant',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ['-created_at']
        verbose_name        = 'Profile Claim'
        verbose_name_plural = 'Profile Claims'

    def __str__(self):
        target = self.company_name_reported or self.company_slug or '(unknown company)'
        return f'{self.ref} — {self.full_name} → {target} [{self.get_status_display()}]'

    def save(self, *args, **kwargs):
        if not self.ref:
            # Retry on the unlikely event of a collision
            for _ in range(5):
                candidate = _generate_claim_ref()
                if not ProfileClaim.objects.filter(ref=candidate).exists():
                    self.ref = candidate
                    break
            else:                     # pragma: no cover
                self.ref = _generate_claim_ref()
        super().save(*args, **kwargs)


# ── NewsletterSignup ──────────────────────────────────────────────────────────

# ── ReviewRequest ─────────────────────────────────────────────────────────────

REVIEW_REQUEST_TYPE_CHOICES = [
    ('company_assessment',   'Company EcoIQ Assessment'),
    ('country_intelligence', 'Country Transition Intelligence'),
    ('investor_readiness',   'Investor Readiness Review'),
    ('islamic_finance',      'Islamic & Ethical Finance Fit'),
    ('project_readiness',    'Project Readiness Review'),
    ('greenwashing_review',  'Greenwashing Risk Review'),
]

REVIEW_SECTOR_CHOICES = [
    ('renewables',     'Renewables / Clean Energy'),
    ('infrastructure', 'Infrastructure / Transport'),
    ('oil_gas',        'Oil & Gas / Extractives'),
    ('agriculture',    'Agriculture / Forestry'),
    ('manufacturing',  'Manufacturing / Industry'),
    ('finance',        'Financial Services / Banking'),
    ('government',     'Government / Public Sector'),
    ('development',    'Development Finance / NGO / Research'),
    ('other',          'Other'),
]

REVIEW_STATUS_CHOICES = [
    ('new',       'New'),
    ('reviewing', 'Under Review'),
    ('contacted', 'Contacted'),
    ('complete',  'Complete'),
    ('declined',  'Declined'),
]


class ReviewRequest(models.Model):
    """
    Submitted when an investor, company, or project owner requests
    an EcoIQ analytical review.  Supports optional PDF upload.
    """

    # Contact
    name         = models.CharField(max_length=200)
    organisation = models.CharField(max_length=200)
    email        = models.EmailField(db_index=True)
    country      = models.CharField(max_length=100)

    # Review specification
    sector       = models.CharField(max_length=30, choices=REVIEW_SECTOR_CHOICES)
    request_type = models.CharField(max_length=30, choices=REVIEW_REQUEST_TYPE_CHOICES)
    message      = models.TextField(blank=True, help_text='Context, questions, or specific focus areas')

    # Optional sustainability report upload
    sustainability_report = models.FileField(
        upload_to='review_reports/%Y/%m/',
        blank=True,
        null=True,
        help_text='PDF only · max 10 MB',
    )

    # Security
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    # CRM pipeline
    status = models.CharField(max_length=20, choices=REVIEW_STATUS_CHOICES, default='new')
    notes  = models.TextField(blank=True, help_text='Internal notes — not visible to the submitter')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ['-created_at']
        verbose_name        = 'Review Request'
        verbose_name_plural = 'Review Requests'

    def __str__(self):
        return f'{self.name} — {self.organisation} ({self.get_request_type_display()})'

    @property
    def report_filename(self):
        if self.sustainability_report:
            return os.path.basename(self.sustainability_report.name)
        return ''


# ── NewsletterSignup ──────────────────────────────────────────────────────────

class NewsletterSignup(models.Model):
    """
    Stores email addresses (and optional metadata) collected via the
    homepage popup and /newsletter/ page.  All signups are opt-in.
    """
    INTEREST_CHOICES = [
        ('investor',   'Investor'),
        ('company',    'Company'),
        ('government', 'Government'),
        ('researcher', 'Researcher'),
        ('other',      'Other'),
    ]

    email        = models.EmailField(unique=True, db_index=True)
    name         = models.CharField(max_length=200, blank=True)
    organisation = models.CharField(max_length=200, blank=True)
    interest     = models.CharField(
        max_length=50, choices=INTEREST_CHOICES, default='other',
    )
    signed_up_at = models.DateTimeField(auto_now_add=True)
    is_active    = models.BooleanField(default=True, help_text='Uncheck to unsubscribe without deleting the record.')
    source       = models.CharField(max_length=100, blank=True, help_text='Where the signup originated — popup, /newsletter/, API, etc.')

    class Meta:
        ordering            = ['-signed_up_at']
        verbose_name        = 'Newsletter Signup'
        verbose_name_plural = 'Newsletter Signups'

    def __str__(self):
        return self.email
