"""
EcoIQ Evidence Harvester — pipeline (Slice 4, additive).

run_harvest(job) executes the full acquisition pipeline for one company and
records stats on the HarvestJob. Reuses Slices 1–3 unchanged:

  discover sources → ensure Source records → adapters.collect →
  dedup (canonical Evidence + EvidenceSourceRef + verification) →
  normalization (Datapoints).

Deterministic and offline-safe. Network adapters return nothing offline (the
honest NOT_FOUND path); nothing is ever fabricated. Idempotent: re-running a
harvest re-attaches sources and updates datapoints rather than duplicating.

No scoring, no Moral Compass, no Planetary Balance, no Executive Brief.
"""
from __future__ import annotations

from django.utils import timezone

from .adapters import get_adapter
from .company_documents import get_documents
from .dedup import deduplicate
from .normalization import normalize_evidence
from .verification import source_quality

# Source families consulted during discovery.
_NETWORK_SOURCE_TYPES = ("companies_house", "reuters")
_PROFILE_SOURCE_TYPES = ("company_website", "investor_relations")


def _ensure_source(profile, source_type, url, owner):
    """Create/refresh a company-scoped EvidenceSource (Source) record."""
    from .models import Source
    Source.objects.get_or_create(
        company=profile, source_type=source_type, source_url=url or "",
        defaults={
            "name": owner or source_type,
            "source_owner": owner or "",
            "confidence_base": source_quality(source_type),
            "update_frequency": "annual",
        },
    )


def run_harvest(job):
    """Run the harvesting pipeline for `job` (a HarvestJob). Records stats and
    sets status. Raises on failure (status captured on the job first)."""
    from .models import Evidence, Datapoint
    from companies.models import CompanyProfile

    slug = job.company_slug
    job.status = "running"
    job.started_at = timezone.now()
    job.save(update_fields=["status", "started_at"])

    try:
        profile = (CompanyProfile.objects
                   .filter(company__slug=slug).select_related("company").first())

        candidates = []
        discovered = set()

        # 1+2+3 — registered documents → adapters + EvidenceSource records
        docs_by_type: dict[str, list] = {}
        for d in get_documents(slug):
            docs_by_type.setdefault(d["source_type"], []).append(d)

        for source_type, docs in docs_by_type.items():
            adapter = get_adapter(source_type)
            if adapter is None:
                continue
            cands = adapter.collect(slug, documents=docs)
            candidates.extend(cands)
            if cands:
                discovered.add(source_type)
            for d in docs:
                _ensure_source(profile, source_type, d.get("url", ""),
                               d.get("source_owner", ""))

        # profile-derived sources (offline, from stored CompanyProfile fields)
        if profile is not None:
            for source_type in _PROFILE_SOURCE_TYPES:
                cands = get_adapter(source_type).collect(slug, profile=profile)
                candidates.extend(cands)
                if cands:
                    discovered.add(source_type)
                    _ensure_source(profile, source_type, "", "Company")

        # network-gated sources — attempted, inert offline (records NOT_FOUND,
        # never fabricates)
        for source_type in _NETWORK_SOURCE_TYPES:
            get_adapter(source_type).collect(slug)

        job.sources_discovered = len(discovered)
        job.documents_downloaded = len(candidates)

        # 4 — dedup + verification (verification runs inside deduplicate)
        deduplicate(candidates, profile=profile, harvest_job=job)

        canonical = Evidence.objects.filter(company_slug=slug)
        job.evidence_extracted = canonical.count()
        job.evidence_verified = canonical.filter(
            verification_status__in=("VERIFIED", "PARTIAL")).count()

        # 5+6 — normalization → Datapoints
        normalized = 0
        for ev in canonical:
            if normalize_evidence(ev):
                normalized += 1
        job.evidence_normalized = normalized
        job.evidence_stored = Datapoint.objects.filter(company_slug=slug).count()

        job.status = "done"
        job.completed_at = timezone.now()
        job.save()
    except Exception as exc:  # noqa: BLE001 — record failure on the job row
        job.status = "error"
        job.error_message = f"{type(exc).__name__}: {exc}"
        job.completed_at = timezone.now()
        job.save(update_fields=["status", "error_message", "completed_at"])
        raise

    return job
