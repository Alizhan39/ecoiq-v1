"""
good_agents/services/clustering.py — signal deduplication + clustering
(PR3 Phase 3). Deterministic only — no LLM, no embeddings. Two signals
cluster together when they share type + geography/region + sector and their
titles overlap enough on keywords; this catches the same real-world
situation reported by two different sources without claiming semantic
understanding it doesn't have.
"""
import re

from good_agents.models import SignalCluster, WorldSignal

_STOPWORDS = frozenset({
    'the', 'a', 'an', 'in', 'on', 'of', 'for', 'to', 'and', 'or', 'is', 'are', 'with', 'at', 'by',
})
TITLE_OVERLAP_THRESHOLD = 0.5


def extract_keywords(title):
    """Public: reused by services/matcher.py to require real keyword relevance before a generic-funding match."""
    words = re.findall(r'[a-z0-9]+', (title or '').lower())
    return {w for w in words if w not in _STOPWORDS and len(w) > 2}


def _titles_overlap(title_a, title_b):
    kw_a, kw_b = extract_keywords(title_a), extract_keywords(title_b)
    if not kw_a or not kw_b:
        return False
    overlap = len(kw_a & kw_b) / min(len(kw_a), len(kw_b))
    return overlap >= TITLE_OVERLAP_THRESHOLD


def find_cluster_candidate(signal):
    """Returns an existing open SignalCluster this signal likely belongs to, or None."""
    candidates = SignalCluster.objects.filter(
        status='open', signal_type=signal.signal_type,
        geography=(signal.region or ''), sector=(signal.sector or ''),
    )
    for cluster in candidates:
        if _titles_overlap(cluster.representative_title, signal.title):
            return cluster
    return None


def assign_to_cluster(signal):
    """
    Idempotent: a signal already assigned to a cluster is left alone. Returns
    (cluster, created_new_cluster: bool). Strengthens confidence_boost by
    real corroboration count, never a guessed number.
    """
    if signal.cluster_id is not None:
        return signal.cluster, False

    cluster = find_cluster_candidate(signal)
    created = False
    if cluster is None:
        cluster = SignalCluster.objects.create(
            representative_title=signal.title, signal_type=signal.signal_type,
            geography=signal.region, sector=signal.sector,
        )
        created = True

    signal.cluster = cluster
    signal.status = 'clustered'
    signal.save(update_fields=['cluster', 'status'])

    corroboration_count = cluster.signals.count()
    cluster.confidence_boost = min(30.0, (corroboration_count - 1) * 10.0)
    cluster.save(update_fields=['confidence_boost', 'updated_at'])
    return cluster, created


def deduplicate_and_cluster(signals):
    """
    Runs the FETCH_SIGNALS -> DEDUPLICATE -> CLUSTER stages over a list of
    already-persisted WorldSignal rows. Returns
    {'duplicates_removed': int, 'clusters': [SignalCluster, ...]}.

    "Duplicate" here means: an exact dedup_key match already clustered
    earlier in this same batch (same underlying event reported twice with
    identical normalised type/geography/sector/title) — it is folded into
    the same cluster rather than counted as a second independent signal.
    """
    seen_dedup_keys = {}
    duplicates_removed = 0
    clusters = []

    for signal in signals:
        if signal.dedup_key in seen_dedup_keys:
            duplicates_removed += 1
            signal.cluster = seen_dedup_keys[signal.dedup_key]
            signal.status = 'clustered'
            signal.save(update_fields=['cluster', 'status'])
            continue

        cluster, created = assign_to_cluster(signal)
        seen_dedup_keys[signal.dedup_key] = cluster
        if created:
            clusters.append(cluster)
        elif cluster not in clusters:
            clusters.append(cluster)

    return {'duplicates_removed': duplicates_removed, 'clusters': clusters}
