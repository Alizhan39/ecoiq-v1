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

--- Capital Guardian Phase 2 additions ---

`verification_status`/`review_tier`/`reviewer`/`expiry_date`/
`document_category`/`integrity_reference` extend this shared model (rather
than a second "capital_guardian evidence" model) so any app's evidence can
carry an honest verification lifecycle — not just Capital Guardian's. These
are additive/nullable/defaulted, so every existing caller (harvester,
agent outputs, company/country reports) is unaffected.

`integrity_reference` is a SHA-256 hex digest of `text_chunk`, computed on
save if not already set. This is a real, verifiable hash of THIS RECORD'S
stored text — it is NOT proof that an uploaded source document is
authentic, and is never described as blockchain/cryptographic-immutability
in any UI built on top of it.
"""
import hashlib

from django.conf import settings
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

    # --- Phase 2 verification workflow (Capital Guardian's Evidence Centre,
    # reusable by any other app) ---
    VERIFICATION_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
        ('requires_review', 'Requires Review'),
    ]
    # How this record's truth was established — never claim a tier stronger
    # than what actually happened to it.
    REVIEW_TIER_CHOICES = [
        ('uploaded', 'Uploaded'),
        ('system_checked', 'System Checked'),
        ('human_reviewed', 'Human Reviewed'),
        ('independently_verified', 'Independently Verified'),
    ]
    DOCUMENT_CATEGORY_CHOICES = [
        ('contract', 'Contract'),
        ('inspection_report', 'Inspection Report'),
        ('fat_certificate', 'Factory Acceptance Test Certificate'),
        ('insurance_certificate', 'Insurance Certificate'),
        ('governance_minute', 'Governance Decision / Minute'),
        ('payment_confirmation', 'Payment Confirmation'),
        ('technical_report', 'Technical Report'),
        ('other', 'Other'),
    ]

    verification_status = models.CharField(max_length=20, choices=VERIFICATION_STATUS_CHOICES, default='pending')
    review_tier = models.CharField(max_length=25, choices=REVIEW_TIER_CHOICES, default='uploaded')
    document_category = models.CharField(max_length=25, choices=DOCUMENT_CATEGORY_CHOICES, default='other')
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='reviewed_evidence_memories',
    )
    expiry_date = models.DateField(null=True, blank=True)
    # SHA-256 of text_chunk at save time — see module docstring for what this
    # is (and is not) evidence of.
    integrity_reference = models.CharField(max_length=64, blank=True, editable=False)

    # Honesty flag, same convention as geo_intelligence/backend_intelligence_engine —
    # defaults False because the primary real-world path (memory built from
    # real harvester.Evidence / real AgentRun output) is genuinely real, not demo.
    is_demo = models.BooleanField(default=False)

    # --- feat/evidence-memory-hardening: structured access model + provenance ---
    #
    # Before these fields, project linkage was only the free-text
    # source_reference string and cross-project retrieval was a global
    # similarity search (see the PR7 audit note in tests.py). These are all
    # additive/nullable/defaulted; source_reference remains for backward
    # compatibility and existing rows are classified by the accompanying
    # data migration (unresolvable rows default to the safest restricted
    # visibility, never guessed into a shareable one).
    #
    # `visibility` is the single access-control axis, enforced by
    # evidence_memory/services/retrieval_policy.py — never by scattered
    # checks in views:
    #   project_private          — only the linked project may retrieve it.
    #   organisation_shared      — retrievable by projects declaring the same
    #                              organisation (matched on the trimmed,
    #                              case-insensitive organisation string; blank
    #                              never matches blank).
    #   platform_learning_demo   — explicitly shared demo/illustrative
    #                              learning material; always labelled DEMO.
    #   platform_learning_verified — explicitly shared, independently
    #                              verified, non-demo learning evidence.
    #   restricted_unresolved    — provenance could not be resolved to a real
    #                              project; hidden from ALL cross-project
    #                              retrieval until a human resolves it.
    # A record is never platform-retrievable merely because it exists:
    # both platform_* states require an explicit human sharing action.
    VISIBILITY_CHOICES = [
        ('project_private', 'Project Private'),
        ('organisation_shared', 'Organisation Shared'),
        ('platform_learning_demo', 'Platform Learning (Demo)'),
        ('platform_learning_verified', 'Platform Learning (Verified)'),
        ('restricted_unresolved', 'Restricted — Unresolved Provenance'),
    ]
    visibility = models.CharField(max_length=30, choices=VISIBILITY_CHOICES, default='project_private')

    # Structured project link (nullable — company/country memories and rows
    # whose provenance could not be resolved have none). GoldProject is the
    # temporary generic project anchor per docs/adr-0001, same as the
    # source_reference convention this replaces as the primary link.
    project = models.ForeignKey(
        'gold_intelligence.GoldProject', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='evidence_memories',
    )
    # Free-text organisation, mirroring CapitalAllocationDecision.organisation's
    # existing convention (no Organisation model exists in this codebase yet —
    # see PR3 report). Only meaningful for visibility='organisation_shared'.
    organisation = models.CharField(max_length=200, blank=True)

    # Structured provenance back to the capital decision / verified outcome an
    # outcome-derived memory row came from. SET_NULL: deleting a decision or
    # outcome must never silently delete historical evidence, but the link is
    # honestly gone. source_reference (above) is retained in parallel for
    # backward compatibility with every existing caller and query.
    originating_decision = models.ForeignKey(
        'waste_to_value_capital_allocation_engine.CapitalAllocationDecision',
        null=True, blank=True, on_delete=models.SET_NULL, related_name='evidence_memories',
    )
    originating_outcome = models.ForeignKey(
        'waste_to_value_capital_allocation_engine.VerifiedCapitalOutcome',
        null=True, blank=True, on_delete=models.SET_NULL, related_name='evidence_memories',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['source_type', 'company']), models.Index(fields=['source_type', 'country'])]

    def __str__(self):
        preview = self.text_chunk[:60] + ('…' if len(self.text_chunk) > 60 else '')
        return f'{self.get_source_type_display()}: {preview}'

    def save(self, *args, **kwargs):
        # Always recomputed from the CURRENT text_chunk — an integrity
        # reference that stayed frozen after an edit would be worse than
        # useless, since it would silently claim content hadn't changed.
        self.integrity_reference = hashlib.sha256(self.text_chunk.encode('utf-8')).hexdigest() if self.text_chunk else ''
        # Model.save(update_fields=...) restricts the actual SQL UPDATE to
        # exactly that field list (e.g. QuerySet.update_or_create() passes
        # only its `defaults` keys) — without this, the recomputed value
        # above would be set in memory but silently dropped from the DB.
        update_fields = kwargs.get('update_fields')
        if update_fields is not None and 'integrity_reference' not in update_fields:
            kwargs['update_fields'] = set(update_fields) | {'integrity_reference'}
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        """Real date comparison only — never inferred from verification_status alone."""
        if self.expiry_date is None:
            return False
        from django.utils import timezone
        return self.expiry_date < timezone.now().date()
