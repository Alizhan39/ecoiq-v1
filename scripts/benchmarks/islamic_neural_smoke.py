"""Real offline encoder smoke, using authored non-religious control sentences.

Prepare the pinned weights first. This checks execution/vector integrity, not
retrieval quality on Quran, provider translations, tafsir or divine names.
"""
import json
import os
from pathlib import Path
import sys
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecoiq.settings')
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'

import django
import numpy as np

django.setup()

from islamic_knowledge.neural import DIMENSIONS, MODEL_VERSION, encode


def main():
    texts = ['Clean water and fair access.', 'Чистая вода и справедливый доступ.',
             'مياه نظيفة وعدالة في الوصول.', 'Computer network cable.']
    start = perf_counter()
    vectors = np.asarray(encode(texts))
    if (vectors.shape != (len(texts), DIMENSIONS) or not np.isfinite(vectors).all()
            or not np.allclose(np.linalg.norm(vectors, axis=1), 1)):
        raise AssertionError('Invalid neural vectors.')
    print(json.dumps({'model': MODEL_VERSION, 'shape': list(vectors.shape),
        'finite': True, 'unit_norms': True, 'offline': True,
        'elapsed_seconds': round(perf_counter() - start, 3),
        'en_ru_cosine': round(float(vectors[0] @ vectors[1]), 4),
        'en_ar_cosine': round(float(vectors[0] @ vectors[2]), 4),
        'unrelated_cosine': round(float(vectors[0] @ vectors[3]), 4),
        'religious_retrieval_quality_evaluated': False}))


if __name__ == '__main__':
    main()
