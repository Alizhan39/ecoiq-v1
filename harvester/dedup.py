"""
EcoIQ Evidence Harvester — Deduplication Engine (Slice 2, additive).

Merges the same fact appearing across multiple sources (annual reports, ESG
reports, websites, news) into ONE canonical Evidence row, recording every
contributing source as an EvidenceSourceRef. The count of distinct sources
drives the verification corroboration score.

Deterministic and idempotent: the dedup_key is source-independent, so re-running
the harvester re-attaches sources to the same canonical row rather than creating
duplicates. Conservative by design — only near-identical statements merge, so it
never collapses two genuinely different facts.
"""
from __future__ import annotations

import re

from .models import content_hash, Evidence, EvidenceSourceRef
from .verification import source_quality, verify_evidence

# Opposing-direction keyword pairs — a conservative contradiction heuristic.
# If one source says "increased" and another "decreased" for the same dedup_key,
# the canonical item is flagged CONTRADICTED for analyst review (refined in the
# normalization slice, which compares actual numeric values).
_INCREASE = ("increase", "increased", "rose", "grew", "higher", "up by", "growth")
_DECREASE = ("decrease", "decreased", "reduced", "fell", "lower", "down by", "cut by", "decline")

_PUNCT = re.compile(r"[^a-z0-9%]+")
_NUM = re.compile(r"\d+(?:\.\d+)?")


def normalize_text(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace. Source-independent."""
    t = _PUNCT.sub(" ", (text or "").lower())
    return " ".join(t.split())


def dedup_key(company_slug: str, category: str, statement: str) -> str:
    """Source-independent fact key. Two near-identical statements about the same
    company+category collapse to the same key regardless of which source they
    came from. Uses the normalized statement (first 160 chars) so phrasing noise
    from a particular document does not block merging."""
    norm = normalize_text(statement)[:160]
    return content_hash(company_slug, category, norm)


def _direction(text: str):
    t = (text or "").lower()
    up = any(k in t for k in _INCREASE)
    down = any(k in t for k in _DECREASE)
    if up and not down:
        return "up"
    if down and not up:
        return "down"
    return None


def _group_contradicted(candidates) -> bool:
    """True if the group contains both an 'increase' and a 'decrease' claim."""
    dirs = {d for d in (_direction(c.statement) for c in candidates) if d}
    return "up" in dirs and "down" in dirs


def deduplicate(candidates, *, profile=None, harvest_job=None, verify=True, document=None):
    """Merge EvidenceCandidates into canonical Evidence rows + source refs.

    `document` (feat/company-discovery-ranking, PR 11): an optional
    harvester.SourceDocument every canonical Evidence row created THIS call
    is linked to (never overwritten on an existing row from a prior run) —
    lets a multi-chunk document's evidence units be traced back to the
    exact document they came from. None for every pre-PR11 caller (SEC
    EDGAR, Companies House, CSV, URL recheck), which is unaffected.

    Returns a dict of stats: {canonical_created, refs_created, refs_skipped,
    contradicted}. Idempotent across re-runs.
    """
    # group by (company_slug, dedup_key)
    groups: dict[tuple, list] = {}
    for c in candidates:
        key = (c.company_slug, c.category, dedup_key(c.company_slug, c.category, c.statement))
        groups.setdefault(key, []).append(c)

    stats = {"canonical_created": 0, "refs_created": 0, "refs_skipped": 0,
             "contradicted": 0, "verified": 0}

    for (company_slug, category, dkey), members in groups.items():
        contradicted = _group_contradicted(members)
        # primary = highest source-quality member (stable, deterministic tie-break)
        primary = max(members, key=lambda m: (source_quality(m.source_type), m.statement))

        canonical, created = Evidence.objects.get_or_create(
            company_slug=company_slug, category=category, dedup_key=dkey,
            defaults={
                "company": profile,
                "harvest_job": harvest_job,
                "document": document,
                "source_location": getattr(primary, "source_location", "") or "",
                "title": primary.title or primary.statement[:120],
                "url": primary.url,
                "publication_date": primary.publication_date,
                "excerpt": primary.excerpt,
                "full_text": primary.full_text,
                "document_type": primary.document_type,
                "content_hash": content_hash(company_slug, category, primary.url,
                                             primary.title, primary.excerpt),
            },
        )
        stats["canonical_created"] += int(created)

        # attach one ref per contributing source (idempotent on type+url)
        for m in members:
            _, ref_created = EvidenceSourceRef.objects.get_or_create(
                canonical_evidence=canonical,
                source_type=m.source_type,
                url=m.url,
                defaults={
                    "source_owner": m.source_owner,
                    "publication_date": m.publication_date,
                    "excerpt": m.excerpt,
                    "source_quality_score": source_quality(m.source_type),
                },
            )
            stats["refs_created" if ref_created else "refs_skipped"] += 1

        # corroboration = distinct independent sources beyond the first
        distinct_sources = canonical.source_refs.count()
        canonical.corroboration_count = max(0, distinct_sources - 1)
        canonical.save(update_fields=["corroboration_count"])

        if contradicted:
            stats["contradicted"] += 1

        if verify:
            result = verify_evidence(canonical, contradicted=contradicted)
            if result.verification_status == "VERIFIED":
                stats["verified"] += 1

    return stats
