# Retrieval controls and versioned citations

## Measured comparison

The checked-in `retrieval-controls-v1.json` contains every question, expected
source ID, ranking and metric. Its corpus digest identifies the exact
`evidence_memory/evaluation/control_set.json` used in the run.

The corpus has 18 synthetic project documents, 30 answerable questions and five
questions with no answer in the corpus. Labels were authored for this diagnostic
set and still need independent domain review. This is not a production accuracy
estimate. No customer evidence was sent to an embedding provider.

| Metric (30 answerable questions) | Current hashing, 256 dimensions | Semantic ONNX, 384 dimensions |
|---|---:|---:|
| Correct source at rank 1 | 43.3% (13/30) | 93.3% (28/30) |
| Recall at 3 | 63.3% | 100.0% |
| MRR at 5 | 0.5594 | 0.9667 |
| nDCG at 5 | 0.5824 | 0.9727 |
| No-answer questions still receiving candidates | 5/5 | 5/5 |

Both encoders use the same permitted synthetic corpus, cosine ranking, top 5
and ID tie-breaking. The hashing side calls the actual production
`compute_embedding`. This evaluates encoders/ranking, not the PostgreSQL query
planner, HNSW recall, access policy or end-to-end answer correctness. Access
boundaries are tested separately with Django requests and current project roles.

The semantic candidate is the official
[paraphrase-multilingual-MiniLM-L12-v2](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2)
ONNX `model_quint8_avx2.onnx` at revision
`e8f8c211226b894fcb81acc59f3b34ba3efd5f42`. It uses attention-mask mean pooling,
128-token truncation and cosine normalisation. Model artifacts and package
versions are recorded in the report. This is the quantized candidate, not a
claim about every semantic embedding model.

A nearest neighbour is always returned by raw top-k search, even when a question
is unanswerable. Neither model's similarity is an answer-confidence score. Do
not use these results to automatically approve decisions or swap the production
index. Next evaluation should use independently reviewed, project-authorised
examples, calibrated abstention and a held-out corpus. Changing production
encoders requires a separate versioned index/re-embedding plan; 256-dimensional
hashing and 384-dimensional semantic vectors must never be mixed.

## Reproduce

```bash
pip install -r requirements-dev.txt -r requirements-evaluation.txt
python scripts/evaluation/download_semantic_model.py /tmp/ecoiq-semantic-model
DEBUG=True python manage.py evaluate_retrieval \
  --semantic-model-dir /tmp/ecoiq-semantic-model \
  --output /tmp/retrieval-report.json
```

The download is an explicit step; evaluation only reads local model files and
the labelled JSON dataset. Omit `--semantic-model-dir` to evaluate hashing alone;
the semantic result will say `not_run`, never silently substitute another
encoder. Use `--dataset` for a separately prepared evaluation corpus. Never put
private project documents in this public fixture/report directory.

## Citation contract

`EvidenceCitationSnapshot` stores an append-only snapshot of indexed text and
source metadata. Each citation identifies a document/source record, its known
content version, an exact quoted fragment and character offsets within the
stored chunk. It includes hashes of the text, quoted fragment and full snapshot.
Existing `harvester.SourceDocument` remains the authority for original documents.
When an indexed harvester chunk still matches its source Evidence, citations use
its document title, source location and recorded document content hash. Otherwise
they honestly identify a **stored chunk version**, with the original document
version unavailable. A chunk digest is never represented as a PDF file hash.

Decision Studio links each retrieved quotation to a permission-checked detail
page. It rechecks both question ownership and current project/evidence access.
The detail page also shows the full stored chunk and offers an authorised JSON
download containing the exact snapshot and quotation. To verify the snapshot
SHA-256 independently, encode the `snapshot` object as UTF-8 JSON with sorted
keys, `ensure_ascii=False` and separators `(',', ':')`, then hash those bytes.
Quotation offsets use Python Unicode character indices, not byte offsets.
Edits create new snapshots; old quotations remain readable as historical versions
and are labelled when the source has changed or expired. Invalid hashes, changed
quotes, foreign source IDs and revoked sharing fail closed. Revoking sharing
also removes cached quotes and derived result content when that answer is read.
Old answers without versioned citations are labelled unavailable for verification.

Source quotations and material conclusions have different support states. An
exact quotation can be attributed to its snapshot; this does not establish its
truth or entail a recommendation. Score comparisons and agent findings have no
verified document-to-claim mapping yet, so they explicitly report insufficient
evidence. Decision Studio withholds a substantive recommendation in that state;
project-scoped LangGraph findings require human review. Search proximity never
creates a supporting citation automatically.

The new policy covers Decision Studio results, LangGraph source context and
project findings, and the background AI task's prompt/source trail. It does not
retrofit every historical Council report or implement an automated entailment
judge. Snapshot hashes detect inconsistency, not a malicious database operator
rewriting the data and hashes together. Source authenticity and independent
verification remain separate controls.

## Release

Validation for this change: 279 Django tests passed across `evidence_memory`,
`decision_studio`, `langgraph_orchestration`, project access, and background AI
analysis. Ruff passed for all changed Python files; `makemigrations --check
--dry-run` found no missing migrations. The semantic comparison above was run
with the pinned local model, not simulated.

Browser verification is pending: the managed browser rejected the local
preview with `net::ERR_BLOCKED_BY_CLIENT`. Server-side template rendering,
citation routes, JSON download integrity and access revocation are covered by
tests, but desktop/mobile layout and keyboard interactions have not been
visually verified. Keep this PR in draft until that gate is completed.

Apply additive migration `evidence_memory.0006_citation_snapshots` before using
the new code. Production has not been migrated by this change. Referenced
EvidenceMemory rows are protected from deletion to preserve cited versions;
retention/redaction must follow an explicit data-governance procedure. Existing
snapshots are not backfilled from changed sources. The semantic benchmark
requirements and model weights are not production dependencies.
