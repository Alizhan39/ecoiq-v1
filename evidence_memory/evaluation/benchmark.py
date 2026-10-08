"""Identical corpus, cosine scoring and stable tie-breaking for both encoders."""
import hashlib
import json
import math
from importlib.metadata import version
from pathlib import Path
from time import perf_counter

import numpy as np

MODEL_ID = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
MODEL_REVISION = 'e8f8c211226b894fcb81acc59f3b34ba3efd5f42'
MODEL_ARTIFACT = 'onnx/model_quint8_avx2.onnx'


def load_dataset(path):
    raw = Path(path).read_bytes()
    data = json.loads(raw)
    ids = [d['id'] for d in data['documents']]
    questions = [q['id'] for q in data['queries']]
    if len(ids) != len(set(ids)) or len(questions) != len(set(questions)):
        raise ValueError('Document and question IDs must be unique.')
    for q in data['queries']:
        if not set(q['relevant_ids']).issubset(ids):
            raise ValueError('A judgement refers to a missing source.')
    data['sha256'] = hashlib.sha256(raw).hexdigest()
    return data


def metrics(ranked, relevant, k=5):
    relevant = set(relevant)
    if not relevant:
        return None  # no-answer cases are reported separately, never inflate recall
    hits = [int(doc_id in relevant) for doc_id in ranked[:k]]
    first = next((i for i, hit in enumerate(hits, 1) if hit), None)
    dcg = sum(hit / math.log2(i + 2) for i, hit in enumerate(hits))
    ideal = sum(1 / math.log2(i + 2) for i in range(min(len(relevant), k)))
    return {'precision_at_1': float(bool(hits and hits[0])),
            'precision_at_3': sum(hits[:3]) / 3,
            'recall_at_3': sum(hits[:3]) / len(relevant),
            'mrr_at_5': 1 / first if first else 0.0, 'ndcg_at_5': dcg / ideal}


def evaluate(data, encoder, identity):
    documents = sorted(data['documents'], key=lambda d: d['id'])
    texts = [d['text'] for d in documents] + [q['question'] for q in data['queries']]
    started = perf_counter()
    vectors = np.asarray(encoder(texts), dtype=np.float64)
    if vectors.ndim != 2 or vectors.shape[0] != len(texts) or not np.isfinite(vectors).all():
        raise ValueError('Encoder must return one finite vector per input.')
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    vectors = vectors / np.maximum(norms, 1e-12)
    scores = vectors[len(documents):] @ vectors[:len(documents)].T
    rows = []
    for q, similarities in zip(data['queries'], scores):
        order = sorted(range(len(documents)), key=lambda i: (-similarities[i], documents[i]['id']))[:5]
        ranked = [documents[i]['id'] for i in order]
        rows.append({'query_id': q['id'], 'category': q['category'], 'question': q['question'],
                     'relevant_ids': q['relevant_ids'], 'ranked_ids': ranked,
                     'scores': [round(float(similarities[i]), 6) for i in order],
                     'metrics': metrics(ranked, q['relevant_ids'])})
    def aggregate(items):
        values = [r['metrics'] for r in items if r['metrics'] is not None]
        return {key: round(sum(v[key] for v in values) / len(values), 6) for key in values[0]} if values else {}
    no_answer = [r for r in rows if not r['relevant_ids']]
    return {'status': 'measured', 'encoder': identity, 'dimensions': vectors.shape[1],
            'encode_and_rank_seconds': round(perf_counter() - started, 4), 'answerable': aggregate(rows),
            'by_category': {c: aggregate([r for r in rows if r['category'] == c]) for c in sorted({r['category'] for r in rows})},
            'no_answer_count': len(no_answer),
            'no_answer_with_candidates': sum(bool(r['ranked_ids']) for r in no_answer),
            'abstention_note': 'Raw top-k retrieval has no answerability threshold; candidates are not evidence that a question is answerable.',
            'queries': rows}


def hashing_encoder(texts):
    from evidence_memory.services.embeddings import compute_embedding
    return [compute_embedding(text) for text in texts]


class LocalSemanticEncoder:
    """Pinned official ONNX transformer, attention-mask mean pooling, L2 cosine.

    Local files only: downloads are a separate explicit operator action. No
    remote Python/model code is executed. Production vectors are untouched.
    """
    def __init__(self, model_dir):
        import onnxruntime as ort
        from tokenizers import Tokenizer
        model_dir = Path(model_dir)
        manifest = json.loads((model_dir / 'manifest.json').read_text())
        if manifest['model_id'] != MODEL_ID or manifest['revision'] != MODEL_REVISION:
            raise ValueError('Semantic model does not match the benchmark revision.')
        for filename in ('model.onnx', 'tokenizer.json'):
            actual = hashlib.sha256((model_dir / filename).read_bytes()).hexdigest()
            if manifest['sha256'][filename] != actual:
                raise ValueError('Semantic model artifact digest mismatch.')
        self.identity = {**manifest, 'onnxruntime': version('onnxruntime'), 'tokenizers': version('tokenizers'),
                         'pooling': 'attention-mask mean', 'max_tokens': 128}
        self.tokenizer = Tokenizer.from_file(str(model_dir / 'tokenizer.json'))
        self.tokenizer.enable_truncation(max_length=128)
        pad_token = '[PAD]' if self.tokenizer.token_to_id('[PAD]') is not None else '<pad>'
        pad_id = self.tokenizer.token_to_id(pad_token)
        if pad_id is None:
            raise ValueError('Model tokenizer has no recognised padding token.')
        self.tokenizer.enable_padding(pad_id=pad_id, pad_token=pad_token)
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        self.session = ort.InferenceSession(str(model_dir / 'model.onnx'), sess_options=options, providers=['CPUExecutionProvider'])

    def __call__(self, texts):
        output = []
        for offset in range(0, len(texts), 8):
            encoded = self.tokenizer.encode_batch(texts[offset:offset + 8])
            inputs = {'input_ids': np.array([e.ids for e in encoded], dtype=np.int64),
                      'attention_mask': np.array([e.attention_mask for e in encoded], dtype=np.int64),
                      'token_type_ids': np.array([e.type_ids for e in encoded], dtype=np.int64)}
            states = self.session.run(None, {i.name: inputs[i.name] for i in self.session.get_inputs()})[0]
            mask = inputs['attention_mask'][..., None]
            if states.ndim != 3:
                raise ValueError('Expected token embeddings for explicit mean pooling.')
            output.extend((states * mask).sum(axis=1) / np.maximum(mask.sum(axis=1), 1))
        return output
