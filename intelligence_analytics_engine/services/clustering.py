"""
intelligence_analytics_engine/services/clustering.py — Climate Risk
Clustering + Investment Opportunity Clustering.

Uses sklearn.cluster.KMeans (fixed random_state — deterministic, not a
one-off random result) over country-level Geo Intelligence features.
Explainability: every cluster's centroid is inverse-transformed back into
real units (0-100 score scale, not standardized z-scores) so "cluster 1 is
characterized by high climate risk and low investment opportunity" is a
direct reading of real numbers, not an opaque label.
"""
from sklearn.cluster import KMeans

from intelligence_analytics_engine.services.features import build_country_features
from intelligence_analytics_engine.services.matrix import has_enough_variation, prepare_matrix

RANDOM_STATE = 42


def _cluster_countries(feature_columns, n_clusters, method_label):
    df = build_country_features()
    if not has_enough_variation(df, feature_columns, minimum_rows=n_clusters):
        return {
            'available': False,
            'reason': f'Fewer than {n_clusters} countries have real data for {feature_columns} — clustering would be meaningless.',
        }

    matrix, imputed_mask, scaler = prepare_matrix(df, feature_columns)
    model = KMeans(n_clusters=n_clusters, n_init=10, random_state=RANDOM_STATE)
    labels = model.fit_predict(matrix)
    centroids_real_units = scaler.inverse_transform(model.cluster_centers_)

    clusters = []
    for cluster_id in range(n_clusters):
        member_mask = labels == cluster_id
        members = df.index[member_mask]
        centroid = {col: round(float(val), 1) for col, val in zip(feature_columns, centroids_real_units[cluster_id])}
        # Characterize by the feature furthest from the overall mean — the
        # trait that most distinguishes this cluster from the others.
        overall_mean = {col: float(df[col].mean()) for col in feature_columns}
        deviations = {col: centroid[col] - overall_mean[col] for col in feature_columns}
        defining_feature = max(deviations, key=lambda c: abs(deviations[c]))
        direction = 'higher' if deviations[defining_feature] > 0 else 'lower'

        clusters.append({
            'cluster_id': int(cluster_id),
            'countries': [{'id': int(pk), 'name': df.loc[pk, 'name']} for pk in members],
            'centroid': centroid,
            'defining_feature': defining_feature,
            'explanation': f'This cluster has {direction} {defining_feature.replace("_", " ")} than the platform average.',
        })

    return {
        'available': True,
        'method': method_label,
        'n_clusters': n_clusters,
        'features_used': feature_columns,
        'countries_clustered': len(df),
        'imputed_cells': int(imputed_mask.sum().sum()),
        'clusters': clusters,
    }


def climate_risk_clusters(n_clusters=3):
    return _cluster_countries(
        ['climate_risk_score', 'geo_exposure_score'], n_clusters,
        'sklearn.cluster.KMeans over country-level climate risk + geo exposure scores',
    )


def investment_opportunity_clusters(n_clusters=3):
    return _cluster_countries(
        ['investment_opportunity_score', 'climate_risk_score', 'modernisation_priority_score'], n_clusters,
        'sklearn.cluster.KMeans over country-level investment opportunity, climate risk and modernisation priority scores',
    )
