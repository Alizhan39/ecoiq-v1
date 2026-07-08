"""
intelligence_analytics_engine/services/outliers.py — Outlier Detection.

Deliberately NOT IsolationForest/LocalOutlierFactor: those score by average
tree-split depth or local density ratio, which is a harder result to
explain plainly to a non-technical reader. This uses
sklearn.preprocessing.StandardScaler directly — its output IS the z-score
for every feature — and flags any |z| >= threshold. A flagged company/
country's explanation is literally "this feature is N standard deviations
from the platform mean", which anyone can verify by hand from the same
numbers. Real scikit-learn usage, maximally explainable.

Imputed cells (see matrix.prepare_matrix) sit exactly at the column mean by
construction, so they can never register as outliers — missing data is
never mistaken for anomalous data.
"""
from intelligence_analytics_engine.services.features import COMPANY_CORE_COLUMNS, build_company_features
from intelligence_analytics_engine.services.matrix import has_enough_variation, prepare_matrix

DEFAULT_Z_THRESHOLD = 2.0


def detect_company_outliers(z_threshold=DEFAULT_Z_THRESHOLD, feature_columns=None):
    feature_columns = feature_columns or COMPANY_CORE_COLUMNS
    df = build_company_features()
    if not has_enough_variation(df, feature_columns, minimum_rows=3):
        return {'available': False, 'reason': 'Not enough companies with real data to establish a meaningful mean/std.'}

    standardized, imputed_mask, _scaler = prepare_matrix(df, feature_columns)

    outliers = []
    for row_pos, pk in enumerate(df.index):
        flagged_features = []
        for col_pos, column in enumerate(feature_columns):
            z = standardized[row_pos, col_pos]
            if abs(z) >= z_threshold:
                flagged_features.append({
                    'feature': column, 'z_score': round(float(z), 2),
                    'direction': 'above' if z > 0 else 'below',
                })
        if flagged_features:
            outliers.append({
                'id': int(pk),
                'name': df.loc[pk, 'name'],
                'flagged_features': flagged_features,
                'explanation': '; '.join(
                    f'{f["feature"].replace("_", " ")} is {abs(f["z_score"]):.1f} standard deviations {f["direction"]} the platform average'
                    for f in flagged_features
                ),
            })

    outliers.sort(key=lambda o: max(abs(f['z_score']) for f in o['flagged_features']), reverse=True)

    return {
        'available': True,
        'method': f'sklearn.preprocessing.StandardScaler z-scores, |z| >= {z_threshold}',
        'companies_checked': len(df),
        'z_threshold': z_threshold,
        'outliers': outliers,
    }
