# ML and evidence retrieval efficiency

The forecast and evidence retrieval services have separate performance boundaries.
Forecasting uses company snapshots and ingestion signals; retrieval ranks already
eligible evidence. An optimisation must preserve access checks, unknown values,
and the distinction between modelled outputs and measured inputs.

## Forecast read path

`ml/prediction.py` processes at most 128 companies per batch. A company queryset
joins the one-to-one profile, then two sliced prefetches load at most 12 history
snapshots and 50 RSS signals **per company**. The history is selected newest first
and reversed before fitting OLS. Signals are restricted to the last 90 days,
with ingestion time and primary key providing deterministic ordering.

For a supplied queryset without additional caller prefetches, forecast input reads
cost one company/profile query plus two queries per batch. Writes and provenance
transactions remain per company; the three-query regression test deliberately
mocks writes and measures only input reads. Caller lists and generators are also
supported, with a profile prefetch when needed. Private input snapshots are removed
after processing so reused instances cannot retain stale forecast inputs.

The previous default path tried to join the reverse `history` relation with
`select_related`, which raises `FieldError`. Single forecasts also selected the
oldest 24 history rows despite documenting the latest 12. Correcting that window
changes forecast values, so `PREDICTION_VERSION` is now `2`. There is no schema
migration or automatic backfill; new runs record version 2.

OLS, signal weights, clamping and atomic provenance writes retain their existing
behaviour. A missing fallback score stays unknown. Forecasts remain modelled, and
the existing partial history/signal lineage described in
`docs/product/CALCULATION_CONTEXT_PROVENANCE.md` remains a limitation.

## Evidence ranking

PostgreSQL continues to rank with pgvector in SQL. For SQLite, `_rank_candidates`
streams rows with `iterator(chunk_size=256)` and retains the top K with a heap,
instead of materialising all rows and sorting them. The query norm is computed
once. Equal similarities preserve candidate order. Eligibility filtering and
record access checks retain their existing behaviour.

When PostgreSQL has supplied distances, `_similarities_for` reuses them. It only
computes a query embedding when a row needs a cosine calculation. This removes
the second embedding computation from the annotation-only path.

## Reproducible ranking control

Run with the normal Django environment configured:

```bash
DEBUG=True python scripts/benchmarks/memory_ranking.py
```

The control uses 5,000 seeded synthetic rows, 256-dimensional vectors, top K = 5
and three repeats, including vector allocation. Both implementations return the
same ordered IDs. A local Python 3.11.16 run measured:

| Measure | Full sort | Streaming top K |
| --- | ---: | ---: |
| Median time | 0.828497 s | 0.497715 s |
| Peak Python memory traced | 43,073,131 bytes | 75,054 bytes |

These are synthetic Python ranking measurements, not production latency or total
database memory. SQL costs, ORM cursor buffers and retrieval quality are outside
this control. The embedding model and retrieval policy are unchanged; no accuracy
improvement is claimed.

Regression coverage lives in `ml/tests_forecast_batch.py` and
`evidence_memory/tests_ranking_efficiency.py`: latest-window selection, bounded
per-company inputs, read-query budget, batch/single agreement, reused inputs,
isolated write failures, unknown/zero handling, stable rankings and lazy embedding.
