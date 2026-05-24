import uuid
from django.db import models


class Assessment(models.Model):
    STATUS_DRAFT = 'draft'
    STATUS_READY = 'ready'
    STATUS_PROCESSING = 'processing'
    STATUS_COMPLETE = 'complete'
    STATUS_ERROR = 'error'

    STATUS_CHOICES = [
        (STATUS_DRAFT,      'Draft'),
        (STATUS_READY,      'Ready'),
        (STATUS_PROCESSING, 'Processing'),
        (STATUS_COMPLETE,   'Complete'),
        (STATUS_ERROR,      'Error'),
    ]

    company_name = models.CharField(max_length=255)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    share_token    = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    uploaded_file = models.FileField(upload_to='uploads/', blank=True, null=True)
    extracted_text = models.TextField(blank=True)
    notes        = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.company_name} ({self.get_status_display()})"


class QuestionnaireResponse(models.Model):
    assessment  = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name='responses')
    question_key = models.CharField(max_length=100)
    question_text = models.TextField()
    answer      = models.TextField(blank=True)

    class Meta:
        unique_together = ('assessment', 'question_key')
        ordering = ['question_key']

    def __str__(self):
        return f"{self.assessment.company_name} — {self.question_key}"


class Finding(models.Model):
    assessment      = models.OneToOneField(Assessment, on_delete=models.CASCADE, related_name='finding')
    created_at      = models.DateTimeField(auto_now_add=True)

    # KPI scores 0–100 per pillar
    score_environment  = models.IntegerField(default=0)
    score_social       = models.IntegerField(default=0)
    score_governance   = models.IntegerField(default=0)
    score_ethics       = models.IntegerField(default=0)
    score_innovation   = models.IntegerField(default=0)
    score_overall      = models.IntegerField(default=0)

    summary         = models.TextField(blank=True)
    pillar_notes    = models.JSONField(default=dict, blank=True)
    raw_ai_response = models.TextField(blank=True)

    def __str__(self):
        return f"Finding for {self.assessment.company_name} (overall: {self.score_overall})"

