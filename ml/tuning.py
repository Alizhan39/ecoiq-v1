"""Bounded candidate-only GBR selection, evaluated on untouched outer folds."""
from sklearn.base import clone
from sklearn.dummy import DummyRegressor
from sklearn.model_selection import GridSearchCV, KFold, cross_validate
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


# Eight candidates, including the existing configuration. No all-core search.
SCORING_GRID = {
    'gradientboostingregressor__n_estimators': [100, 200],
    'gradientboostingregressor__learning_rate': [0.03, 0.05],
    'gradientboostingregressor__max_depth': [2, 4],
}
MIN_TUNING_SAMPLES = 30


def tune_scoring(estimator, X, y):
    """Return final fitted pipeline and nested-CV metrics, never selection scores as quality."""
    if len(X) < MIN_TUNING_SAMPLES:
        raise ValueError(f'Scoring tuning requires at least {MIN_TUNING_SAMPLES} eligible rows.')
    outer = KFold(n_splits=5, shuffle=True, random_state=42)
    inner = KFold(n_splits=3, shuffle=True, random_state=43)
    search = GridSearchCV(
        make_pipeline(StandardScaler(), clone(estimator)), SCORING_GRID,
        scoring='neg_mean_absolute_error', cv=inner, n_jobs=1,
        pre_dispatch=1, error_score='raise', refit=True,
    )
    scores = cross_validate(
        search, X, y, cv=outer, n_jobs=1,
        scoring={'r2': 'r2', 'mae': 'neg_mean_absolute_error'}, error_score='raise',
    )
    baseline = cross_validate(
        DummyRegressor(strategy='mean'), X, y, cv=outer, n_jobs=1,
        scoring='neg_mean_absolute_error', error_score='raise',
    )
    # Only after the outer evaluation: select and refit a deployment candidate
    # on all eligible rows. Its inner best_score_ is not a holdout estimate.
    search.fit(X, y)
    return search.best_estimator_, {
        'r2_mean': float(scores['test_r2'].mean()),
        'r2_std': float(scores['test_r2'].std()),
        'evaluation': {
            'status': 'MEASURED', 'method': 'nested cross-validation (5 outer / 3 inner folds)',
            'mae': float(-scores['test_mae'].mean()),
            'baseline_mae': float(-baseline['test_score'].mean()),
            'external_validation': False,
        },
        'tuning': {
            'selection_metric': 'inner_cv_mae', 'n_candidates': 8,
            'inner_random_state': 43, 'n_jobs': 1,
            'parameter_grid': SCORING_GRID,
            'selected_parameters': {key.split('__', 1)[1]: value
                                    for key, value in search.best_params_.items()},
        },
    }
