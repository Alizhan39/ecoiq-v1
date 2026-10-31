"""Synthetic ranking throughput/memory control, not retrieval-quality evaluation.

Run from the repository root: DEBUG=True python scripts/benchmarks/memory_ranking.py
Uses fresh generated ORM-shaped rows per iteration, including vector allocation.
It isolates Python fallback ranking; it measures neither SQL nor model quality.
"""
import argparse
import json
import os
from pathlib import Path
from statistics import median
import sys
from time import perf_counter
import tracemalloc
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecoiq.settings')

import django
import numpy as np

django.setup()

from evidence_memory.models import EMBEDDING_DIMENSIONS
from evidence_memory.services.embeddings import compute_embedding
from evidence_memory.services.memory import _cosine_similarity, _rank_candidates

QUERY = 'coal heating gas transition'


class Candidates:
    def __init__(self, count):
        self.count = count

    def filter(self, **kwargs):
        return self

    def __iter__(self):
        rng = np.random.default_rng(42)
        for pk in range(self.count):
            yield SimpleNamespace(pk=pk, embedding=rng.normal(size=EMBEDDING_DIMENSIONS).tolist())

    def iterator(self, chunk_size):
        return iter(self)


def reference(candidates, top_k):
    query = compute_embedding(QUERY)
    scored = [(_cosine_similarity(row.embedding, query), row) for row in candidates]
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [row for _, row in scored[:top_k]]


def measure(fn, repeats):
    durations, peaks, ids = [], [], None
    for _ in range(repeats):
        tracemalloc.start()
        start = perf_counter()
        rows = fn()
        durations.append(perf_counter() - start)
        peaks.append(tracemalloc.get_traced_memory()[1])
        tracemalloc.stop()
        current = [row.pk for row in rows]
        if ids is not None and current != ids:
            raise AssertionError('Ranking is not deterministic.')
        ids = current
    return {'median_seconds': round(median(durations), 6),
            'peak_traced_bytes': max(peaks), 'ids': ids}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--count', type=int, default=5000)
    parser.add_argument('--top-k', type=int, default=5)
    parser.add_argument('--repeats', type=int, default=3)
    args = parser.parse_args()
    if args.count <= 0 or args.top_k <= 0 or args.repeats <= 0:
        parser.error('count, top-k and repeats must be positive.')
    before = measure(lambda: reference(Candidates(args.count), args.top_k), args.repeats)
    after = measure(lambda: _rank_candidates(QUERY, Candidates(args.count), args.top_k), args.repeats)
    if before['ids'] != after['ids']:
        raise AssertionError('Streaming rank differs from full-sort reference.')
    print(json.dumps({'fixture': 'synthetic, seed 42, streamed ORM-shaped rows',
                      'documents': args.count, 'dimensions': EMBEDDING_DIMENSIONS,
                      'top_k': args.top_k, 'repeats': args.repeats,
                      'before': before, 'after': after}, indent=2))


if __name__ == '__main__':
    main()
