"""
intelligence_analytics_engine/services/matrix.py — shared NaN-safe matrix
prep for every sklearn-facing service (similarity, clustering, outliers).

scikit-learn estimators cannot accept NaN. Mean-imputing is the simplest
correct fix, but silently mean-imputing without recording *which* cells
were imputed would quietly turn "no real data" into "an invented average" —
exactly what this platform's honesty conventions forbid. prepare_matrix()
therefore returns both the imputed matrix AND a same-shape boolean mask, so
every caller can report "this feature was estimated (no real data for this
row)" rather than presenting an imputed value as if it were measured.
"""
import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler


def prepare_matrix(df, columns):
    """
    df: pandas DataFrame. columns: list of column names to use as features.
    Returns (standardized_matrix, imputed_mask_df, scaler) — scaler is
    returned so callers can inverse_transform centroids/distances back into
    real units for explanations.
    """
    raw = df[columns].astype(float)
    imputed_mask = raw.isna()

    # keep_empty_features=True: without it, SimpleImputer silently DROPS any
    # column that is 100% NaN (e.g. modernisation_priority_score when no
    # country has one yet) — that desyncs `columns` against the output
    # matrix's column count/order for every downstream caller that zips them
    # together. Keeping the column (filled at 0, i.e. the standardized mean)
    # guarantees the output always has exactly len(columns) columns in the
    # same order as the input.
    imputer = SimpleImputer(strategy='mean', keep_empty_features=True)
    imputed_values = imputer.fit_transform(raw)

    scaler = StandardScaler()
    standardized = scaler.fit_transform(imputed_values)

    return standardized, imputed_mask, scaler


def has_enough_variation(df, columns, minimum_rows=2):
    """
    Guards every service below from a degenerate call (e.g. clustering with
    fewer real data points than clusters) — returns False rather than
    letting sklearn raise or silently return a meaningless result.
    """
    if len(df) < minimum_rows:
        return False
    non_null_rows = df[columns].dropna(how='all')
    return len(non_null_rows) >= minimum_rows
