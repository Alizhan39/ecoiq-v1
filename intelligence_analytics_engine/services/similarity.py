"""
intelligence_analytics_engine/services/similarity.py — Company Similarity
Engine + Country Similarity Engine.

Uses sklearn.neighbors.NearestNeighbors over standardized feature vectors —
a fully explainable classical technique: for any returned match, the exact
per-feature standardized distance is inspectable, so "most_similar_on" /
"most_different_on" in the result are not decoration, they are the actual
components of the distance sklearn computed.
"""
import numpy as np
from sklearn.neighbors import NearestNeighbors

from intelligence_analytics_engine.services.features import (
    COMPANY_CORE_COLUMNS, build_company_features, build_country_features,
)
from intelligence_analytics_engine.services.matrix import has_enough_variation, prepare_matrix


def _nearest_neighbors_explained(df, target_pk, feature_columns, top_n, name_column='name'):
    if target_pk not in df.index:
        return {'available': False, 'reason': f'{target_pk} not found in the feature set.'}
    if not has_enough_variation(df, feature_columns, minimum_rows=2):
        return {'available': False, 'reason': 'Not enough real data across the platform yet to compare against.'}

    matrix, imputed_mask, _scaler = prepare_matrix(df, feature_columns)
    n_neighbors = min(top_n + 1, len(df))
    model = NearestNeighbors(n_neighbors=n_neighbors, metric='euclidean')
    model.fit(matrix)

    target_row_pos = df.index.get_loc(target_pk)
    distances, indices = model.kneighbors(matrix[target_row_pos:target_row_pos + 1])

    results = []
    for distance, row_pos in zip(distances[0], indices[0]):
        candidate_pk = df.index[row_pos]
        if candidate_pk == target_pk:
            continue
        per_feature_diff = np.abs(matrix[target_row_pos] - matrix[row_pos])
        ranked_features = sorted(zip(feature_columns, per_feature_diff), key=lambda pair: pair[1])
        most_similar_on = [f for f, _ in ranked_features[:2]]
        most_different_on = [f for f, _ in ranked_features[-2:]]
        results.append({
            'id': int(candidate_pk),
            'name': df.loc[candidate_pk, name_column],
            'distance': round(float(distance), 3),
            'most_similar_on': most_similar_on,
            'most_different_on': most_different_on,
        })
        if len(results) >= top_n:
            break

    return {
        'available': True,
        'target_id': int(target_pk),
        'target_name': df.loc[target_pk, name_column],
        'features_used': feature_columns,
        'imputed_features_for_target': list(imputed_mask.loc[target_pk][imputed_mask.loc[target_pk]].index),
        'method': 'sklearn.neighbors.NearestNeighbors (euclidean, standardized features)',
        'results': results,
    }


def find_similar_companies(company_profile_id, top_n=5):
    df = build_company_features()
    return _nearest_neighbors_explained(df, company_profile_id, COMPANY_CORE_COLUMNS, top_n)


def find_similar_countries(country_profile_id, top_n=5):
    df = build_country_features()
    feature_columns = COMPANY_CORE_COLUMNS  # country-level averages of the same pillars
    return _nearest_neighbors_explained(df, country_profile_id, feature_columns, top_n)
