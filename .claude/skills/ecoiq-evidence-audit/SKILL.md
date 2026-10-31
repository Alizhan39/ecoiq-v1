---
name: ecoiq-evidence-audit
description: Trace or change the EcoIQ evidence chain — company to KPI/formula to evidence record to assessment to finding to remediation, including supports/conflicts relationships, confidence tiers, and review state. Use when adding, promoting, deleting, scoring, or displaying an evidence record, or when asked where a number on a page came from. Not for generic database work that happens to touch a model with "evidence" in its name.
---

# EcoIQ evidence audit

## There are four evidence tables, on purpose

Do not add a fifth. Pick the right one; if none fits, the answer is usually a
new field, not a new model.

| Model | Purpose | Key file |
|---|---|---|
| `harvester.Evidence` + `EvidenceSourceRef` | Raw harvested source material | `harvester/models.py:145` |
| `league.Evidence` | League/leaderboard-scoped evidence | `league/models.py:411` |
| `hikma.Evidence` | SAY / DO / SHOW records for a subject | `hikma/models.py` |
| `evidence_memory.EvidenceMemory` | Derived, searchable **chunks** over the above plus agent output | `evidence_memory/models.py` |

`EvidenceMemory.source_reference` is a soft pointer (`"harvester.Evidence:123"`),
deliberately not a ForeignKey — read the module docstring before changing it.

## The review-state rule

This is the invariant most likely to be broken by accident.

- `hikma.Evidence.confidence_tier` ∈ `verified` | `analyst-reviewed` |
  `ai-seeded` | `model-estimate`, **default `ai-seeded`**.
- `hikma.Evidence.scholar_review_required` **defaults to `True`**.
- `EvidenceMemory` carries `verification_status`, `review_tier`, `reviewer`,
  `expiry_date`.

**No code path may set a verified/analyst-reviewed tier as a side effect of an
AI call.** Promotion is a human action with a recorded reviewer. If you are
writing an ingestion or agent path, it writes `ai-seeded` and stops.

`EvidenceMemory.confidence` is nullable and stays null until a real value is
known — never default it to a plausible number.

## supports / conflicts

EcoIQ does not have one global `supports`/`conflicts` edge table. What exists:

- `EVIDENCE_SUPPORTS_CLAIM` and siblings in the knowledge-graph edge
  vocabulary — `knowledge_graph_relationship_map/views.py`.
- `SUPPORT / CONCERNS / CONFLICTS` grouping in the council orchestrator —
  `good_agents/services/orchestrator.py:186`.
- SAY vs DO vs SHOW disagreement in `hikma` is the domain-level "conflict":
  a `say` record that the `show` records contradict.

When asked to "show conflicting evidence", use the existing grouping above.
Do not invent a new edge type without checking the vocabulary lists first.

## Integrity references are not authenticity proofs

`EvidenceMemory.integrity_reference` is a SHA-256 of `text_chunk` computed on
save. It proves the stored text has not changed. It does **not** prove an
uploaded source document is genuine, and must never be surfaced as
blockchain, immutability, or tamper-proof in any UI or marketing copy — the
model docstring says this explicitly, and `ecoiq-impact-claims` enforces it.

## Tracing a displayed number (the common request)

1. Find the template/serializer field. 2. Walk back to the service that
computed it. 3. Confirm it terminates in an evidence row or a deterministic
formula in `ethics/` — not in an LLM response. 4. If it terminates in an LLM
response, that is a finding: report it rather than documenting it as fine.

## Done when

- No new evidence model, and no new AI→verified promotion path.
- Confidence and review state are honest (null over invented).
- Tests cover the review-state default, not just the happy path.
- `ecoiq-release-gate` run for the apps touched.
