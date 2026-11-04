"""Typed index over canonical catalogues and pending review work.

An index entry is not necessarily a principle, formula or assessment. In
particular, a KPI/surah pair is an UNREVIEWED work item, not a verified link.
No database, external model, new interpretation or numerical score is created.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import hashlib
from itertools import islice
import json
from typing import Any, Iterator

from core.esg_principles_data import PRINCIPLES
from ecoiq_os.foundation_catalog import KPI_CATALOG, catalogue_summary, review_queue_page
from ecoiq_os.formula_registry import PROVISIONAL_KPI_FORMULAS
from intelligence_analytics_engine.reform_capabilities import REFORM_CAPABILITIES
from intelligence_analytics_engine.reform_kpi_crosswalk import proposed_kpi_context
from islamic_knowledge.catalog import divine_names, surahs
from islamic_knowledge.environmental_principles import stewardship_drafts
from islamic_knowledge.governance_domains import GOVERNANCE_DOMAINS
from islamic_knowledge.governance_kpi_crosswalk import candidate_kpis_for_domain
from islamic_knowledge.principles import DRAFT_PRINCIPLES

REGISTRY_VERSION = "ecoiq_review_registry_v1"
REGISTRY_KINDS = (
    "operational_principle", "candidate_kpi", "formula_candidate",
    "knowledge_definition", "governance_domain", "reform_capability",
    "surah_reference", "divine_name_reference", "kpi_surah_review_pair",
)
MAX_PAGE_SIZE = 100


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def _hash(value: object) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class RegistryEntry:
    id: str
    kind: str
    source_file: str
    source_key: str
    content_sha256: str
    review_status: str
    related_ids: tuple[str, ...] = ()
    source_verified: bool = False
    decision_ready: bool = False


def canonical_knowledge_definitions():
    """Deduplicate reused core/environmental definitions; reject ID conflicts."""
    definitions = {}
    for definition in (*DRAFT_PRINCIPLES, *stewardship_drafts()):
        previous = definitions.get(definition.id)
        if previous is not None and previous != definition:
            raise ValueError("Conflicting canonical knowledge definition.")
        definitions[definition.id] = definition
    return tuple(definitions.values())


def _entry(prefix, key, kind, source_file, content, status, related=()):
    return RegistryEntry(f"{prefix}:{key}", kind, source_file, str(key),
                         _hash(content), status, tuple(related))


def _entries() -> Iterator[RegistryEntry]:
    for row in PRINCIPLES:
        yield _entry("principle", f"{row['id']:03d}", "operational_principle",
                     "core/esg_principles_data.py", row, "NOT_ASSESSED")
    for row in KPI_CATALOG:
        yield _entry("kpi", row.key, "candidate_kpi", "ecoiq_os/foundation_catalog.py",
                     asdict(row), "DRAFT_REVIEW_REQUIRED")
    for row in PROVISIONAL_KPI_FORMULAS:
        yield _entry("formula", row.key, "formula_candidate", "ecoiq_os/formula_registry.py",
                     asdict(row), row.validation_status, (f"kpi:{row.key}",))
    for row in canonical_knowledge_definitions():
        # Stewardship drafts reuse core objects when concepts overlap.
        source = ("islamic_knowledge/principles.py" if row in DRAFT_PRINCIPLES
                  else "islamic_knowledge/environmental_principles.py")
        yield _entry("knowledge", row.id, "knowledge_definition", source,
                     asdict(row), "SCHOLAR_REVIEW_PENDING")
    for row in GOVERNANCE_DOMAINS:
        links = candidate_kpis_for_domain(row.code)
        yield _entry("governance", row.code, "governance_domain",
                     "islamic_knowledge/governance_domains.py",
                     {"definition": asdict(row), "crosswalk": links}, row.research_status,
                     (f"formula:{link['formula_key']}" for link in links))
    for row in REFORM_CAPABILITIES:
        crosswalk = proposed_kpi_context(row.slug)
        links = crosswalk["formula_links"]
        yield _entry("capability", row.slug, "reform_capability",
                     "intelligence_analytics_engine/reform_capabilities.py",
                     {"definition": asdict(row), "crosswalk": crosswalk}, row.maturity,
                     (f"formula:{link['formula_key']}" for link in links))
    for row in surahs().values():
        yield _entry("surah", f"{row.number:03d}", "surah_reference",
                     "content/islamic_knowledge/quran_index.json", asdict(row), "REFERENCE_ONLY")
    for row in divine_names().values():
        # An ordinal identifies a position in one enumeration, not all variants.
        yield _entry("name", f"{row.enumeration}:{row.key}", "divine_name_reference",
                     "content/islamic_knowledge/names99.json", asdict(row), row.review_status)
    # Reuse the existing bounded review queue; never invent 99 x 114 mappings.
    total = catalogue_summary()["potential_review_cells"]
    for start in range(0, total, MAX_PAGE_SIZE):
        page = review_queue_page(start=start, limit=MAX_PAGE_SIZE)
        for row in page["tasks"]:
            key = f"{row['candidate_kpi']}:{row['surah']:03d}"
            yield _entry("review-kpi-surah", key, "kpi_surah_review_pair",
                         "ecoiq_os/foundation_catalog.py", row, row["status"],
                         (f"kpi:{row['candidate_kpi']}", f"surah:{row['surah']:03d}"))


def registry_summary() -> dict[str, Any]:
    """Count and fingerprint actual typed records, checking all IDs and links.

    Only a small summary enters an AI result. Entry content (including sacred
    metadata) stays in the canonical source files, not in a provider prompt.
    """
    ids: set[str] = set()
    targets: set[str] = set()
    counts: Counter[str] = Counter({kind: 0 for kind in REGISTRY_KINDS})
    digest = hashlib.sha256(REGISTRY_VERSION.encode("utf-8"))
    for entry in _entries():
        if entry.id in ids:
            raise ValueError("Duplicate unified registry identifier.")
        ids.add(entry.id)
        targets.update(entry.related_ids)
        counts[entry.kind] += 1
        digest.update(b"\n" + _json(asdict(entry)).encode("utf-8"))
    if targets - ids:
        raise ValueError("Unified registry contains a dangling reference.")
    return {
        "version": REGISTRY_VERSION,
        "content_sha256": digest.hexdigest(),
        "total_entries": len(ids),
        "counts_by_kind": dict(counts),
        "count_semantics": "TYPED_INVENTORY_NOT_COMPLETED_ASSESSMENTS",
        "source_verified_entries": 0,
        "decision_ready": False,
    }


def registry_page(*, kind: str | None = None, start: int = 0, limit: int = 50) -> dict[str, Any]:
    """Internal/operator pagination. No endpoint or publication permission."""
    if kind is not None and kind not in REGISTRY_KINDS:
        raise ValueError("Unknown registry kind.")
    if type(start) is not int or start < 0 or type(limit) is not int or not 1 <= limit <= MAX_PAGE_SIZE:
        raise ValueError("Invalid registry page bounds.")
    summary = registry_summary()  # refuses duplicate IDs and dangling links
    entries = (row for row in _entries() if kind is None or row.kind == kind)
    rows = [asdict(row) for row in islice(entries, start, start + limit)]
    total = summary["total_entries"] if kind is None else summary["counts_by_kind"][kind]
    next_start = start + len(rows)
    return {
        "registry": summary, "kind": kind, "total": total,
        "start": start, "entries": rows,
        "next_start": next_start if next_start < total else None,
    }
