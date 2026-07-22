"""
good_agents/services/evidence_gate.py — the Evidence Gate (PR3 Phase 5).
Deterministic thresholds only — this is a quality check, not a reasoning
step, and it must be able to conclude INSUFFICIENT_EVIDENCE and stop. Never
rewards a cluster merely for having many signals; source diversity and
freshness matter more than volume.
"""
from dataclasses import dataclass

MIN_CONFIDENCE_TO_QUALIFY = 40.0
MIN_CONFIDENCE_TO_MONITOR = 15.0
MIN_SOURCE_DIVERSITY_FOR_FACT_LEVEL_CONFIDENCE = 2


@dataclass
class EvidenceGateResult:
    decision: str  # 'qualify' | 'reject' | 'monitor' | 'insufficient_evidence'
    reason: str
    confidence: float
    source_diversity: int
    has_contradictions: bool


def evaluate_cluster(cluster):
    """
    Evaluates one SignalCluster's evidence quality. Confidence is derived
    from the cluster's signals' own confidence fields plus the cluster's
    corroboration-based confidence_boost — never asserted independently.
    """
    signals = list(cluster.signals.all())
    if not signals:
        return EvidenceGateResult(
            decision='insufficient_evidence', reason='Cluster has no signals.',
            confidence=0.0, source_diversity=0, has_contradictions=False,
        )

    source_diversity = len({s.provider_id for s in signals if s.provider_id is not None}) or len(
        {s.publisher for s in signals if s.publisher}
    )
    base_confidence = max((s.confidence for s in signals), default=0.0)
    confidence = min(100.0, base_confidence + cluster.confidence_boost)
    has_contradictions = bool(cluster.contradiction_notes)
    max_freshness = max((s.freshness for s in signals), default=0.0)

    missing_geography = all(not (s.region or s.geography_id) for s in signals)
    missing_sector = all(not s.sector for s in signals)

    if confidence < MIN_CONFIDENCE_TO_MONITOR:
        return EvidenceGateResult(
            decision='insufficient_evidence',
            reason=f'Confidence {confidence:.0f}% is below the minimum monitoring threshold ({MIN_CONFIDENCE_TO_MONITOR:.0f}%).',
            confidence=confidence, source_diversity=source_diversity, has_contradictions=has_contradictions,
        )

    if missing_geography and missing_sector:
        return EvidenceGateResult(
            decision='insufficient_evidence',
            reason='No geography or sector recorded for this cluster — cannot assess relevance.',
            confidence=confidence, source_diversity=source_diversity, has_contradictions=has_contradictions,
        )

    if has_contradictions:
        return EvidenceGateResult(
            decision='monitor',
            reason=f'Contradicting evidence noted: {cluster.contradiction_notes[:200]}',
            confidence=confidence, source_diversity=source_diversity, has_contradictions=True,
        )

    if confidence < MIN_CONFIDENCE_TO_QUALIFY:
        return EvidenceGateResult(
            decision='monitor',
            reason=f'Confidence {confidence:.0f}% is below the qualification threshold ({MIN_CONFIDENCE_TO_QUALIFY:.0f}%); watching for more corroboration.',
            confidence=confidence, source_diversity=source_diversity, has_contradictions=False,
        )

    if source_diversity < 1 and max_freshness < 20:
        return EvidenceGateResult(
            decision='monitor',
            reason='Single stale source — needs corroboration or a fresher signal before qualifying.',
            confidence=confidence, source_diversity=source_diversity, has_contradictions=False,
        )

    return EvidenceGateResult(
        decision='qualify',
        reason=f'Confidence {confidence:.0f}% from {source_diversity} independent source(s), no unresolved contradictions.',
        confidence=confidence, source_diversity=source_diversity, has_contradictions=False,
    )
