"""
EcoIQ LegacySafe AI — Models.

Hackathon module (started 2026-07-01) inside the existing EcoIQ platform.
LegacySafe AI is a permission-aware agentic change-management layer for
enterprise legacy systems: it retrieves only content a user is allowed to
see, tracks lineage from source document to derived memory, propagates
revocation, and logs every access decision for audit.

Aligned with the Conduct AI bounty (legacy modernisation, dependency mapping,
controlled change proposals) and the BasedAI bounty (permission-aware memory,
deterministic access checks before retrieval, lineage, revocation, audit logs).
"""
from django.conf import settings
from django.db import models
from django.utils import timezone

ACCESS_LEVEL_CHOICES = [
    ('public',      'Public'),
    ('engineering', 'Engineering'),
    ('finance',     'Finance'),
    ('executive',   'Executive'),
]

DOCUMENT_TYPE_CHOICES = [
    ('esg_report',         'ESG Report'),
    ('solar_battery',      'Solar & Battery Feasibility'),
    ('heat_pump_boiler',   'Heat Pump & Boiler Replacement'),
    ('insulation',         'Insulation & Heat Loss Reduction'),
    ('smart_meters_iot',   'Smart Meters & IoT Sensors'),
    ('grid_optimisation',  'Grid & Load Optimisation'),
    ('budget',             'Investment Budget'),
    ('procurement',        'Equipment Procurement'),
    ('capex_opex',         'CAPEX/OPEX & ROI'),
    ('strategy_memo',      'Strategy Memo'),
    ('worker_community',   'Worker & Community Transition'),
    ('justice_maqasid',    'Justice & Maqasid Review'),
    ('other',              'Other'),
]

PROPOSAL_STATUS_CHOICES = [
    ('draft',            'Draft'),
    ('pending_approval', 'Pending Approval'),
    ('approved',         'Approved'),
    ('rejected',         'Rejected'),
]


class LegacyProject(models.Model):
    """A legacy modernisation engagement (e.g. one client, one facility)."""
    name         = models.CharField(max_length=200)
    organisation = models.CharField(max_length=200, blank=True)
    sector       = models.CharField(max_length=100, blank=True)
    description  = models.TextField(blank=True)
    created_at   = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering            = ['-created_at']
        verbose_name        = 'LegacySafe Project'
        verbose_name_plural = 'LegacySafe Projects'

    def __str__(self):
        return self.name


class SourceDocument(models.Model):
    """A raw legacy artefact: an ESG report, maintenance log, budget, memo, etc."""
    project        = models.ForeignKey(LegacyProject, on_delete=models.CASCADE,
                          related_name='source_documents')
    title          = models.CharField(max_length=200)
    document_type  = models.CharField(max_length=20, choices=DOCUMENT_TYPE_CHOICES,
                          default='other')
    text_content   = models.TextField()
    access_level   = models.CharField(max_length=12, choices=ACCESS_LEVEL_CHOICES,
                          default='public')
    is_revoked     = models.BooleanField(default=False)
    created_at     = models.DateTimeField(default=timezone.now)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ['project', 'created_at']
        verbose_name        = 'Source Document'
        verbose_name_plural = 'Source Documents'

    def __str__(self):
        return f'{self.title} ({self.get_access_level_display()})'


class MemoryChunk(models.Model):
    """A retrievable slice of a SourceDocument. Inherits access level from its source."""
    source_document = models.ForeignKey(SourceDocument, on_delete=models.CASCADE,
                          related_name='chunks')
    text            = models.TextField()
    chunk_index     = models.PositiveIntegerField(default=0)
    access_level    = models.CharField(max_length=12, choices=ACCESS_LEVEL_CHOICES,
                          default='public')
    lineage         = models.JSONField(default=list, blank=True,
                          help_text='List of {"source_document_id", "source_document_title"}')
    is_revoked      = models.BooleanField(default=False)
    created_at      = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering            = ['source_document', 'chunk_index']
        unique_together     = [('source_document', 'chunk_index')]
        verbose_name        = 'Memory Chunk'
        verbose_name_plural = 'Memory Chunks'

    def __str__(self):
        return f'{self.source_document.title} · chunk {self.chunk_index}'


class DerivedMemory(models.Model):
    """A summary/insight synthesised from one or more MemoryChunks (or documents).

    Must inherit the most restrictive access level of everything in its
    lineage, and must be revoked the moment any lineage source is revoked.
    """
    project      = models.ForeignKey(LegacyProject, on_delete=models.CASCADE,
                       related_name='derived_memories')
    title        = models.CharField(max_length=200)
    summary      = models.TextField()
    access_level = models.CharField(max_length=12, choices=ACCESS_LEVEL_CHOICES,
                       default='executive')
    lineage      = models.JSONField(default=list, blank=True,
                       help_text='List of {"source_document_id", "source_document_title"}')
    is_revoked   = models.BooleanField(default=False)
    created_at   = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering            = ['-created_at']
        verbose_name        = 'Derived Memory'
        verbose_name_plural = 'Derived Memories'

    def __str__(self):
        return self.title

    @property
    def lineage_source_ids(self):
        return {entry.get('source_document_id') for entry in (self.lineage or [])}


class AuditLog(models.Model):
    """Every question, retrieval, blocked/allowed source, and revocation is logged here."""
    user            = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                          on_delete=models.SET_NULL, related_name='legacy_safe_audit_logs')
    action          = models.CharField(max_length=30,
                          help_text='e.g. ask, permission_demo, revoke')
    question        = models.TextField(blank=True)
    decision        = models.CharField(max_length=20, blank=True,
                          help_text='e.g. allowed, blocked, partial, revoked')
    allowed_sources = models.JSONField(default=list, blank=True)
    blocked_sources = models.JSONField(default=list, blank=True)
    reason          = models.TextField(blank=True)
    created_at      = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering            = ['-created_at']
        verbose_name        = 'Audit Log'
        verbose_name_plural = 'Audit Logs'

    def __str__(self):
        return f'{self.action} · {self.decision} · {self.created_at:%Y-%m-%d %H:%M}'


class ChangeProposal(models.Model):
    """A controlled modernisation change proposal awaiting human-in-the-loop approval."""
    project             = models.ForeignKey(LegacyProject, on_delete=models.CASCADE,
                              related_name='change_proposals')
    title               = models.CharField(max_length=200)
    affected_systems    = models.JSONField(default=list, blank=True)
    risks               = models.JSONField(default=list, blank=True)
    recommended_actions = models.JSONField(default=list, blank=True)
    required_roles      = models.JSONField(default=list, blank=True)
    evidence            = models.JSONField(default=list, blank=True)
    status              = models.CharField(max_length=20, choices=PROPOSAL_STATUS_CHOICES,
                              default='draft')
    created_at          = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering            = ['-created_at']
        verbose_name        = 'Change Proposal'
        verbose_name_plural = 'Change Proposals'

    def __str__(self):
        return f'{self.title} ({self.get_status_display()})'
