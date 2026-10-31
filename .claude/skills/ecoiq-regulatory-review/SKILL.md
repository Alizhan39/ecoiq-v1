---
name: ecoiq-regulatory-review
description: Required metadata and review state for anything that states or implies a regulatory, legal, or compliance position — CSRD, SFDR, TCFD, ISSB, national ESG rules, permits, sanctions, or jurisdiction-specific duties. Use when writing, ingesting, displaying, or generating such content for UK, Kazakhstan, Saudi Arabia, or Türkiye. Not for internal scoring that makes no compliance claim.
---

# Regulatory review

A regulatory statement is any output a reader could act on as "this rule
applies to us." That includes an AI summary, a table cell, a PDF line, and a
marketing page — not just a field called `regulation`.

## Eight fields, all required

No regulatory statement ships without all eight. Missing one is a blocker,
not a TODO.

| Field | Rule |
|---|---|
| `jurisdiction` | Specific: `GB`, `KZ`, `SA`, `TR`. Never "EU/UK" as one value, never "global". |
| `effective_date` | The date the obligation bites, not the publication date. |
| `primary_source` | The regulator's or legislature's own document. A consultancy summary is not a primary source. |
| `retrieved_date` | When the text was actually fetched. Regulations change; a citation without this is undated. |
| `applicability` | The test that decides whether it applies to *this* subject — turnover, employee count, listing status, sector. |
| `uncertainty` | Stated plainly. "Draft", "in consultation", "transposition pending", "our reading". |
| `reviewer` | A person. Not a model name, not "EcoIQ". |
| `review_state` | `unreviewed` → `reviewed` → `approved`. AI output enters at `unreviewed`. |

## Hard rules

1. **No AI-authored regulatory conclusion reaches a user at `approved`.**
   The gateway prompt already forbids inventing regulations and legal
   citations ([`ai_gateway/prompts.py`](../../../ai_gateway/prompts.py)); this
   skill adds that even a *correct* AI summary is `unreviewed` until a named
   human moves it.
2. **A citation you cannot open is not a citation.** If `primary_source` is a
   URL, it was fetched, not guessed from a plausible pattern. Deep links to
   regulator sites are frequently hallucinated — verify or cite the document
   title and issuing body instead.
3. **Do not state advice.** EcoIQ provides decision-support, not legal
   advice — the existing system prompt says this and user-facing copy must
   not contradict it.
4. **Priority jurisdictions are not equivalent.** UK post-Brexit rules,
   Kazakhstan's ESG framework, Saudi regulations, and Türkiye's are separate
   regimes. Never generalise one to another, and never present an EU rule as
   UK law.
5. **Expiry.** `evidence_memory.EvidenceMemory.expiry_date` exists — use it.
   A regulatory record with no expiry silently becomes stale advice.

## Where this attaches in code

Regulatory findings today live in `audit.Finding` / `audit.AIFinding`
([`audit/models.py`](../../../audit/models.py)) and, for evidence chunks, in
`evidence_memory.EvidenceMemory` with `verification_status` / `review_tier` /
`reviewer` / `expiry_date`. There is no dedicated `Regulation` model. If a
task needs one, that is a schema decision — surface it, do not improvise a
JSON blob in an existing table.

## Done when

- All eight fields present and honest.
- `review_state` reflects reality; nothing AI-authored is `approved`.
- Uncertainty is visible to the reader, not buried in a tooltip.
- No legal-advice phrasing anywhere in the surfaced copy.
