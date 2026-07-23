"""
Central Admin Notification Hub.

A single AdminNotification model that aggregates every public form submission
across EcoIQ so staff can see new leads in one place (with an unread badge in
the admin header) instead of checking each model's changelist.
"""
import logging

from django.db import models
from django.urls import reverse
from django.utils import timezone

logger = logging.getLogger(__name__)


SOURCE_TYPE_CHOICES = [
    ('heating_household', 'Heating — Household Application'),
    ('heating_akimat',    'Heating — Akimat / Partnership'),
    ('heating_company',   'Heating — Company Sponsorship'),
    ('home_assessment',   'Heating — Home Assessment'),
    ('access_request',    'Investor Readiness / Access Request'),
    ('review_request',    'EcoIQ Review Request'),
    ('profile_claim',     'Company Profile Claim'),
    ('newsletter',        'Newsletter Signup'),
    ('contact',           'Contact Form'),
    ('background_task',   'Background Intelligence Task'),
    ('good_agents_opportunity', '114 Good Agents — Opportunity / Discovery Event'),
    ('other',             'Other'),
]

STATUS_CHOICES = [
    ('unread',   'Unread'),
    ('read',     'Read'),
    ('archived', 'Archived'),
]

PRIORITY_CHOICES = [
    ('low',    'Low'),
    ('normal', 'Normal'),
    ('high',   'High'),
    ('urgent', 'Urgent'),
]


class AdminNotification(models.Model):
    title             = models.CharField(max_length=255)
    message           = models.TextField(blank=True, help_text='Short summary of the submission')

    source_type       = models.CharField(max_length=40, choices=SOURCE_TYPE_CHOICES, default='other', db_index=True)
    source_model      = models.CharField(max_length=120, blank=True, help_text='app_label.model of the related object')
    source_object_id  = models.CharField(max_length=64, blank=True)
    admin_url         = models.CharField(max_length=300, blank=True, help_text='Admin change URL of the related object')

    status            = models.CharField(max_length=10, choices=STATUS_CHOICES, default='unread', db_index=True)
    priority          = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal', db_index=True)

    contact_name      = models.CharField(max_length=200, blank=True)
    contact_email     = models.EmailField(blank=True)
    phone             = models.CharField(max_length=50, blank=True)
    metadata          = models.JSONField(default=dict, blank=True)

    created_at        = models.DateTimeField(auto_now_add=True, db_index=True)
    read_at           = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        indexes = [models.Index(fields=['status', '-created_at'])]

    def __str__(self):
        return f'[{self.get_status_display()}] {self.title}'

    def mark_read(self):
        if self.status == 'unread':
            self.status = 'read'
            self.read_at = timezone.now()
            self.save(update_fields=['status', 'read_at'])

    @classmethod
    def unread_count(cls):
        return cls.objects.filter(status='unread').count()


def create_notification(title, *, source_type='other', message='', instance=None,
                        admin_url='', priority='normal', contact_name='',
                        contact_email='', phone='', metadata=None):
    """
    Create an AdminNotification. Never raises — a notification failure must not
    break the user-facing form submission. Returns the object or None.
    """
    try:
        source_model = ''
        source_object_id = ''
        if instance is not None:
            source_model = f'{instance._meta.app_label}.{instance._meta.model_name}'
            source_object_id = str(instance.pk)
            if not admin_url:
                try:
                    admin_url = reverse(
                        f'admin:{instance._meta.app_label}_{instance._meta.model_name}_change',
                        args=[instance.pk],
                    )
                except Exception:
                    admin_url = ''
        return AdminNotification.objects.create(
            title=(title or 'New submission')[:255],
            message=message or '',
            source_type=source_type,
            source_model=source_model,
            source_object_id=source_object_id,
            admin_url=admin_url,
            priority=priority,
            contact_name=(contact_name or '')[:200],
            contact_email=(contact_email or '')[:254],
            phone=(phone or '')[:50],
            metadata=metadata or {},
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception('create_notification failed: %s', exc)
        return None
