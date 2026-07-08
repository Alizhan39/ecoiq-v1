"""
evidence_memory/services/embeddings.py — text -> fixed-size vector.

Uses scikit-learn's HashingVectorizer, not a neural embedding model:
- No new ML model dependency — scikit-learn is already installed (the
  existing ML scoring pipeline in companies/ uses it).
- Stateless and deterministic: no .fit()/training/vocabulary, no model
  weights to version or ship, the exact same text always produces the exact
  same vector.
- Real, not fabricated: it's a genuine mathematical transform (the hashing
  trick — https://en.wikipedia.org/wiki/Feature_hashing) of the actual input
  text, so two evidence chunks that share real vocabulary will genuinely
  land close together in vector space. It is a lexical/statistical
  similarity, not deep semantic similarity — weaker than a transformer
  embedding, but honestly so, and a real capability nonetheless.

Phase 2 candidate: swap this for a hosted embedding API or local model once
that's a justified, separately-reviewed decision — nothing else in this app
needs to change if that swap happens, since every caller only ever sees
`compute_embedding(text) -> list[float]`.
"""
from sklearn.feature_extraction.text import HashingVectorizer

from evidence_memory.models import EMBEDDING_DIMENSIONS

_vectorizer = HashingVectorizer(n_features=EMBEDDING_DIMENSIONS, alternate_sign=True, norm='l2')


def compute_embedding(text):
    """Returns a fixed-length list[float] of EMBEDDING_DIMENSIONS, or None for empty/blank text."""
    if not text or not text.strip():
        return None
    vector = _vectorizer.transform([text]).toarray()[0]
    return vector.tolist()
