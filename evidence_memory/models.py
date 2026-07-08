"""
evidence_memory/models.py — EcoIQ Evidence Memory + Vector Search (Phase 1).

One model, not several: `EvidenceMemory` covers both "evidence memory" and
"intelligence memory" from the spec — a company report chunk, a country
report chunk, and an AgentRun finding are all the same shape (a real text
chunk, optionally scoped to a company/country, optionally produced by an
agent, with a confidence and an embedding). Splitting these into separate
models would just be the same fields duplicated three times.

Deliberately NOT built on harvester.Evidence / league.Evidence / hikma.Evidence
directly — those three already exist, are not duplicated here, and remain the
system of record for raw evidence. EvidenceMemory is a derived, searchable
index over chunks of text drawn from them (plus AgentRun outputs, which have
no existing Evidence-shaped model at all) — `source_reference` is a soft
pointer back to whichever real record a memory came from (e.g.
"harvester.Evidence:123"), not a hard cross-app ForeignKey, so this app never
creates a migration dependency on harvester/league/hikma/agent_runtime_model_router.

`embedding` uses pgvector.django.VectorField, which works transparently on
SQLite too (confirmed empirically: stores and returns a plain Python list,
no error) — only the SQL-level similarity search functions are Postgres-only,
which is why services/search.py branches on the database backend rather than
this model needing two different field types.
"""
from django.db import models
from pgvector.django import VectorField

EMBEDDING_DIMENSIONS = 256


class EvidenceMemory(models.Model):
    SOURCE_TYPE_CHOICES = [
        ('harvester_evidence', 'Evidence Harvester Record'),
        ('agent_output', 'AI Agent Output'),
        ('company_report', 'Company Report / Document'),
        ('country_report', 'Country Report / Document'),
        ('manual', 'Manual Entry'),
        ('other', 'Other'),
    ]
    EMBEDDING_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('embedded', 'Embedded'),
        ('failed', 'Failed'),
    ]

    text_chunk = models.TextField()
    source_url = models.URLField(max_length=2000, blank=True)
    source_type = models.CharField(max_length=30, choices=SOURCE_TYPE_CHOICES, default='other')

    company = models.ForeignKey(
        'companies.CompanyProfile', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='evidence_memories',
    )
    country = models.ForeignKey(
        'countries.CountryProfile', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='evidence_memories',
    )

    # Soft reference — which agent produced (or, for a retrieval-context
    # record, consumed) this memory. Not a FK: agent identity here is the
    # same plain agent_name string used across ai_agent_council/agent_runtime_
    # model_router, not a row in any one specific table.
    agent_name = models.CharField(max_length=150, blank=True)

    # Never fabricated — null until a real confidence value is known.
    confidence = models.FloatField(null=True, blank=True)
    date_collected = models.DateField(null=True, blank=True)

    embedding = VectorField(dimensions=EMBEDDING_DIMENSIONS, null=True, blank=True)
    embedding_status = models.CharField(max_length=10, choices=EMBEDDING_STATUS_CHOICES, default='pending')

    # e.g. "harvester.Evidence:123" or "agent_runtime_model_router.AgentRun:456"
    source_reference = models.CharField(max_length=200, blank=True, db_index=True)

    # Honesty flag, same convention as geo_intelligence/backend_intelligence_engine —
    # defaults False because the primary real-world path (memory built from
    # real harvester.Evidence / real AgentRun output) is genuinely real, not demo.
    is_demo = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['source_type', 'company']), models.Index(fields=['source_type', 'country'])]

    def __str__(self):
        preview = self.text_chunk[:60] + ('…' if len(self.text_chunk) > 60 else '')
        return f'{self.get_source_type_display()}: {preview}'
