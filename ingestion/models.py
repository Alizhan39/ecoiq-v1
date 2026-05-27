"""
EcoIQ AI Company Ingestion — Models.

IngestionJob  — one ingestion run (company name → all data)
IngestionSource — URLs / documents discovered during the search step
"""
from django.db import models
from django.utils import timezone


class IngestionJob(models.Model):
    """
    Top-level record for one automated company ingestion run.
    Created when the user submits the form; updated by the pipeline thread.
    """

    STATUS_PENDING    = 'pending'
    STATUS_SEARCHING  = 'searching'
    STATUS_DOWNLOADING = 'downloading'
    STATUS_EXTRACTING = 'extracting'
    STATUS_SCORING    = 'scoring'
    STATUS_SAVING     = 'saving'
    STATUS_DONE       = 'done'
    STATUS_FAILED     = 'failed'

    STATUS_CHOICES = [
        (STATUS_PENDING,     'Pending'),
        (STATUS_SEARCHING,   'Searching'),
        (STATUS_DOWNLOADING, 'Downloading'),
        (STATUS_EXTRACTING,  'Extracting'),
        (STATUS_SCORING,     'Scoring'),
        (STATUS_SAVING,      'Saving'),
        (STATUS_DONE,        'Done'),
        (STATUS_FAILED,      'Failed'),
    ]

    company_name   = models.CharField(max_length=255, help_text='User-supplied name to look up')
    url            = models.URLField(blank=True, help_text='Optional: company website or document URL to seed the search')
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    progress_pct   = models.PositiveSmallIntegerField(default=0, help_text='0-100')
    progress_message = models.CharField(max_length=500, blank=True)

    # Output
    result_company = models.ForeignKey(
        'league.Company',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='ingestion_jobs',
        help_text='Created/updated company record',
    )
    error_message  = models.TextField(blank=True)

    # Raw AI outputs stored for debugging / reprocessing
    search_result     = models.JSONField(default=dict, blank=True,
                                         help_text='AI web search structured output')
    extraction_result = models.JSONField(default=dict, blank=True,
                                         help_text='AI extraction structured output')
    score_result      = models.JSONField(default=dict, blank=True,
                                         help_text='Computed pillar scores + reasoning')

    # Timestamps
    created_at   = models.DateTimeField(auto_now_add=True)
    started_at   = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering        = ['-created_at']
        verbose_name        = 'Ingestion Job'
        verbose_name_plural = 'Ingestion Jobs'

    def __str__(self):
        return f'[{self.status}] {self.company_name} ({self.created_at:%Y-%m-%d %H:%M})'

    @property
    def duration_seconds(self):
        if self.started_at and self.completed_at:
            return int((self.completed_at - self.started_at).total_seconds())
        return None


class IngestionSource(models.Model):
    """
    One URL or document discovered / used during an IngestionJob.
    Provides source traceability and confidence attribution.
    """

    SOURCE_WEB     = 'web'
    SOURCE_PDF     = 'pdf'
    SOURCE_ANNUAL  = 'annual_report'
    SOURCE_ESG     = 'esg_report'
    SOURCE_GOVT    = 'government'
    SOURCE_NEWS    = 'news'
    SOURCE_OTHER   = 'other'

    SOURCE_TYPE_CHOICES = [
        (SOURCE_WEB,    'Web Page'),
        (SOURCE_PDF,    'PDF Document'),
        (SOURCE_ANNUAL, 'Annual Report'),
        (SOURCE_ESG,    'ESG / Sustainability Report'),
        (SOURCE_GOVT,   'Government / Regulator'),
        (SOURCE_NEWS,   'News Article'),
        (SOURCE_OTHER,  'Other'),
    ]

    job         = models.ForeignKey(IngestionJob, on_delete=models.CASCADE,
                                    related_name='sources')
    url         = models.URLField(max_length=2000)
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPE_CHOICES,
                                   default=SOURCE_OTHER)
    title       = models.CharField(max_length=500, blank=True)
    snippet     = models.TextField(blank=True, help_text='Short excerpt from the source')
    downloaded  = models.BooleanField(default=False,
                                      help_text='Content was fetched and used')
    content_chars = models.PositiveIntegerField(default=0,
                                                 help_text='Characters extracted')
    used_in_analysis = models.BooleanField(default=False,
                                           help_text='Passed to Claude for extraction')
    confidence  = models.FloatField(default=0.0,
                                    help_text='0-1 relevance confidence assigned by AI')
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering        = ['-confidence', 'source_type']
        verbose_name        = 'Ingestion Source'
        verbose_name_plural = 'Ingestion Sources'

    def __str__(self):
        return f'{self.source_type}: {self.title or self.url[:60]}'
