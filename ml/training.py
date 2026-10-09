"""Training input gates and reproducible candidate artefacts.

This validates numerical completeness, not the truth of source evidence.
Publication and independent label review remain separate requirements.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import platform

import numpy as np

from ml.features import (
    MATERIAL_FEATURE_SOURCES, company_to_vector, get_feature_names, missing_material_features,
)
from ml.model_identity import FEATURE_SET_VERSION


def training_rows(companies, *, supervised=False):
    rows, targets, ids = [], [], []
    skipped = Counter()
    seen = set()
    for company in companies:
        key = company.pk
        if key is None or key in seen:
            skipped['duplicate_or_missing_id'] += 1
            continue
        seen.add(key)
        if missing_material_features(company):
            skipped['unknown_material_inputs'] += 1
            continue
        try:
            material_valid = all(np.isfinite(float(getattr(company.profile, field)))
                                 for field in MATERIAL_FEATURE_SOURCES)
        except (TypeError, ValueError):
            material_valid = False
        if not material_valid:
            skipped['invalid_material_inputs'] += 1
            continue
        try:
            vector = company_to_vector(company)
            if vector.shape != (len(get_feature_names()),) or not np.isfinite(vector).all():
                skipped['invalid_features'] += 1
                continue
            target = float(company.ecoiq_score) if supervised else 0.0
            if not np.isfinite(target) or not 0 <= target <= 100:
                skipped['invalid_target'] += 1
                continue
        except (TypeError, ValueError, AttributeError):
            skipped['feature_extraction_error'] += 1
            continue
        rows.append(vector)
        targets.append(target)
        ids.append(key)
    return (np.asarray(rows, dtype=np.float64).reshape(-1, len(get_feature_names())),
            np.asarray(targets, dtype=np.float64), ids, dict(skipped))


def training_metadata(X, y, skipped):
    digest = hashlib.sha256()
    digest.update(FEATURE_SET_VERSION.encode())
    digest.update(np.asarray(X, dtype='<f8').tobytes())
    digest.update(np.asarray(y, dtype='<f8').tobytes())
    return {'schema_version': 1, 'feature_set_version': FEATURE_SET_VERSION,
            'features': get_feature_names(), 'input_sha256': digest.hexdigest(),
            'n_samples': len(X), 'skipped': skipped,
            'random_state': 42, 'independent_evidence_validated': False}


def artifact_directory(output_dir, default_dir, *, apply):
    if output_dir is not None:
        if apply:
            raise ValueError('Candidate output cannot be applied to company records.')
        target = Path(output_dir).resolve()
        if target == Path(default_dir).resolve() or target.exists():
            raise ValueError('Use a new candidate directory; existing artefacts are not replaced.')
        return target
    return Path(default_dir)


def save_training_run(artifacts, directory, name, result, *, exclusive=False):
    """Save only trusted locally fitted objects, with hashes and package versions."""
    import joblib
    import sklearn

    directory.mkdir(parents=True, exist_ok=not exclusive)
    hashes = {}
    for filename, estimator in artifacts.items():
        target = directory / filename
        joblib.dump(estimator, target)
        hashes[filename] = hashlib.sha256(target.read_bytes()).hexdigest()
    result['artifacts'] = hashes
    result['model_kind'] = name
    result['runtime'] = {'python': platform.python_version(),
                         'numpy': np.__version__, 'sklearn': sklearn.__version__,
                         'joblib': joblib.__version__}
    (directory / f'{name}_training.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
