"""
intelligence_analytics_engine/services/evidence_distribution.py — Evidence
Quality Distribution.

Pure pandas/numpy descriptive statistics over evidence_memory.EvidenceMemory
confidence values — mean, median, std, quartiles and a histogram. No model
fitting involved; a distribution is inherently transparent, so this is
reported as real numbers directly rather than run through any estimator.
"""
import numpy as np
import pandas as pd


def evidence_quality_distribution(company=None, country=None, source_type=None, bins=5):
    """
    Scope with none of company/country/source_type given = whole-platform
    distribution. Returns {available, count, mean, median, std, min, max,
    quartiles, histogram, by_source_type} — by_source_type breaks the same
    stats down per EvidenceMemory.source_type so "which kind of evidence is
    weakest" is directly visible.
    """
    from evidence_memory.models import EvidenceMemory

    queryset = EvidenceMemory.objects.exclude(confidence__isnull=True)
    if company is not None:
        queryset = queryset.filter(company=company)
    if country is not None:
        queryset = queryset.filter(country=country)
    if source_type is not None:
        queryset = queryset.filter(source_type=source_type)

    rows = list(queryset.values('confidence', 'source_type'))
    if not rows:
        return {'available': False, 'reason': 'No EvidenceMemory records with a recorded confidence in this scope.'}

    df = pd.DataFrame(rows)
    confidences = df['confidence']

    counts, bin_edges = np.histogram(confidences, bins=bins, range=(0, 100))
    histogram = [
        {'range': f'{bin_edges[i]:.0f}-{bin_edges[i + 1]:.0f}', 'count': int(counts[i])}
        for i in range(len(counts))
    ]

    by_source_type = {}
    for source, group in df.groupby('source_type'):
        by_source_type[source] = {
            'count': len(group),
            'mean_confidence': round(float(group['confidence'].mean()), 1),
            'std_confidence': round(float(group['confidence'].std()) if len(group) > 1 else 0.0, 1),
        }

    return {
        'available': True,
        'count': len(df),
        'mean': round(float(confidences.mean()), 1),
        'median': round(float(confidences.median()), 1),
        'std': round(float(confidences.std()) if len(df) > 1 else 0.0, 1),
        'min': round(float(confidences.min()), 1),
        'max': round(float(confidences.max()), 1),
        'quartiles': {
            'p25': round(float(confidences.quantile(0.25)), 1),
            'p50': round(float(confidences.quantile(0.50)), 1),
            'p75': round(float(confidences.quantile(0.75)), 1),
        },
        'histogram': histogram,
        'by_source_type': by_source_type,
    }
