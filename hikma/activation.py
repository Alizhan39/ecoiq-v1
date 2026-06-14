"""
Hikma node activation (deterministic, keyword-based; embedding-ready).

Loads the committed Revelation Graph (docs/hikma_revelation_graph_full.json,
304 nodes) and matches an assessment's text signals (evidence statements,
dimension labels, risk flags) against each node's own vocabulary
(english_name, transliteration, short_definition keywords, positive/risk
signals). Returns the graph nodes that the evidence touches.

Constraints honoured:
- Only references node ids that already exist in the committed specs.
- Invents no new concepts or theological claims — it merely surfaces which
  existing nodes the supplied evidence relates to, with the matched terms shown.
- Deterministic: same input text -> same activated_nodes.
- Pluggable: `activate()` is the single entry point; an embedding matcher can
  replace `_keyword_score` later without changing callers.
"""
from __future__ import annotations

import functools
import json
import re
from pathlib import Path

from django.conf import settings

_GRAPH_FILE = Path(settings.BASE_DIR) / "docs" / "hikma_revelation_graph_full.json"

# generic words that would over-match; excluded from a node's keyword set
_STOPWORDS = {
    "the", "and", "for", "with", "that", "which", "from", "into", "over", "under",
    "this", "their", "its", "are", "not", "but", "all", "any", "one", "out",
    "decision", "score", "level", "high", "low", "medium", "value", "based",
    "company", "country", "system", "systems", "data", "impact", "risk", "risks",
    "of", "to", "in", "a", "an", "or", "is", "be", "by", "on", "as", "it",
}
_WORD = re.compile(r"[a-z][a-z\-]{3,}")


def _terms(*texts) -> set:
    out = set()
    for t in texts:
        for w in _WORD.findall((t or "").lower()):
            if w not in _STOPWORDS:
                out.add(w)
    return out


@functools.lru_cache(maxsize=1)
def _node_index():
    """Build {node_id: {'terms': set, 'name':, 'category':}} once per process."""
    nodes = json.loads(_GRAPH_FILE.read_text())
    idx = {}
    for n in nodes:
        terms = _terms(
            n.get("english_name", ""),
            n.get("transliteration", ""),
            n.get("short_definition", ""),
            " ".join(n.get("positive_signals", []) or []),
            " ".join(n.get("risk_signals", []) or []),
        )
        idx[n["id"]] = {
            "terms": terms,
            "name": n.get("english_name", n["id"]),
            "category": n.get("category", ""),
        }
    return idx


def _keyword_score(node_terms: set, input_terms: set):
    """Deterministic overlap score + the matched terms (sorted)."""
    hits = node_terms & input_terms
    if not hits:
        return 0.0, []
    # normalise by node vocabulary size so broad nodes don't dominate
    score = round(len(hits) / max(8, len(node_terms)), 4)
    return score, sorted(hits)


def activate(statements, dimension_labels=None, risk_flags=None, *, top_k=15, min_hits=1):
    """Return activated graph nodes for the supplied assessment signals.

    statements        : iterable of evidence statement strings
    dimension_labels  : iterable of scoring-dimension names (e.g. 'harm_reduction')
    risk_flags        : iterable of risk-flag strings

    Returns: list of {node, name, category, score, matched_terms} sorted desc.
    """
    input_terms = _terms(
        " ".join(statements or []),
        " ".join((dimension_labels or [])),
        " ".join((risk_flags or [])),
    )
    if not input_terms:
        return []

    results = []
    for node_id, meta in _node_index().items():
        score, hits = _keyword_score(meta["terms"], input_terms)
        if len(hits) >= min_hits and score > 0:
            results.append({
                "node": node_id,
                "name": meta["name"],
                "category": meta["category"],
                "score": score,
                "matched_terms": hits,
            })
    results.sort(key=lambda r: (-r["score"], -len(r["matched_terms"]), r["node"]))
    return results[:top_k]
