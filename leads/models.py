from django.db import models


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

STATUS_CHOICES = [
    ('new',            'New'),
    ('contacted',      'Contacted'),
    ('qualified',      'Qualified'),
    ('demo_scheduled', 'Demo Scheduled'),
    ('pilot_active',   'Pilot Active'),
    ('declined',       'Declined'),
]


class AccessRequest(models.Model):
    # Contact
    full_name    = models.CharField(max_length=200)
    company      = models.CharField(max_length=200)
    work_email   = models.EmailField(db_index=True)

    # Profile
    industry      = models.CharField(max_length=30, choices=INDUSTRY_CHOICES)
    facility_type = models.CharField(max_length=200, help_text='e.g. Continuous process refinery, Cold-chain warehouse')
    company_size  = models.CharField(max_length=20, choices=COMPANY_SIZE_CHOICES)

    # Qualification
    challenge = models.TextField(help_text='Main operational challenge — minimum 30 characters')
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
