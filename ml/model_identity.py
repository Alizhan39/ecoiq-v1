"""
ml/model_identity.py — stable identifiers for the committed model artefacts.

D3C-3f. `calculation_version` has to answer one question: *would this
calculation, run again, be the same calculation?* For the deterministic
calculators a hand-maintained version string answers it, because the formula
lives in the code and the code is the only thing that can change.

For an ML output that is not enough. The formula is a joblib file, it is
overwritten in place by every `train()` run, and nothing in the code changes
when it does. Two predictions with identical feature lineage and identical
version strings can come from entirely different models.

So the version carries a **content digest of the artefact bytes**. It changes
exactly when the model changes, and it is derived from the thing itself rather
than asserted alongside it.

Explicitly NOT a Git SHA. A repo SHA moves for every unrelated commit and does
not move when an untracked artefact is replaced — wrong in both directions.

WHAT THIS BUYS, AND WHAT IT DOES NOT
------------------------------------
It makes a retrain **detectable**: a prediction recorded under digest `a1b2c3…`
is visibly not the same calculation as one recorded under `d4e5f6…`.

It does NOT make the old model **retrievable**. `train()` overwrites the
artefact in place, so once it is replaced the previous model is gone and the
digest names something that no longer exists. Fixing that means versioned
artefact storage, which is a deployment decision, not a provenance one. See
`docs/product/CALCULATION_CONTEXT_PROVENANCE.md`.
"""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

#: Feature-set version. Hand-maintained, and it has to be: the feature list is
#: an ordered Python literal in ml/features.py, so nothing but discipline
#: connects a change there to a bump here.
#:
#: BUMP THIS whenever get_feature_names() changes — added, removed, renamed or
#: REORDERED. Order is part of the contract: the scaler and every tree split
#: address columns positionally, so a reordering that keeps the same names is
#: still a different feature set.
FEATURE_SET_VERSION = '1'

#: Length of the artefact digest used in version strings. Short enough to read
#: in a table, long enough that a collision is not a practical concern here.
_DIGEST_CHARS = 12


def artefact_digest(*paths: Path) -> str | None:
    """
    Content digest over one or more artefact files, in the order given.

    Returns None when any artefact is missing — a caller that cannot identify
    the model must not record provenance claiming it ran a known one.
    """
    digest = hashlib.sha256()
    for path in paths:
        try:
            digest.update(Path(path).read_bytes())
        except OSError as exc:
            logger.warning('Model artefact unreadable (%s): %s', path, exc)
            return None
    return digest.hexdigest()[:_DIGEST_CHARS]


def model_version(*paths: Path, feature_set: str = FEATURE_SET_VERSION) -> str | None:
    """
    The `calculation_version` string for a model-backed metric.

    Format: ``fs<feature-set>+<artefact-digest>`` — e.g. ``fs1+9c4a1e77b2d0``.

    Both halves matter and they fail independently. The artefact digest catches
    a retrain; the feature-set version catches a change in what the columns
    mean, which can leave the artefact bytes untouched while making every
    prediction mean something different.

    Returns None if the artefacts cannot be read, which propagates as "no
    provenance recorded" rather than as a version string naming nothing.
    """
    digest = artefact_digest(*paths)
    return None if digest is None else f'fs{feature_set}+{digest}'
