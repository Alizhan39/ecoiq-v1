# Grounded investigation principle review — first integration

## Runtime scope

`ecoiq_os.grounded_ai.prepare_grounded_draft` now must attach a server-created
`principle_review` to every authorised, structurally valid case result,
including disabled-model, missing-source and rejected-model outcomes. This is
an internal Python service, not a public HTTP endpoint. Access-denied and
invalid-case results do not disclose a case-specific report.

This does **not** complete platform-wide principle enforcement. Other gateway,
company audit and agent entry points are unchanged. No UI, database migration,
model training, external model enablement or deployment is part of this change.

## Reuse and honest gaps

The report walks the existing canonical inventories, not a copied catalogue:

- All 114 operational principles in `core/esg_principles_data.py`, with their
  questions and explicit `NOT_ASSESSED` / applicability `REVIEW_REQUIRED`.
- All 20 KPI candidates with their actual expressions and input-unit contracts.
  This inventory does not execute formulas or authenticate observations.
- The 12 governance domains and their existing contextual KPI crosswalks.
- The 12 proposed reform capabilities, their data requirements and safeguards.
  Legal access retains its explicit missing direct KPI.
- Existing core and environmental draft knowledge definitions, deduplicated by
  canonical ID; `assess_definition` supplies their existing missing-source and
  scholarly-review reasons. No approved source or receipt is fabricated.

`inventory_counts` counts entries visited, **not** completed assessments.
`assessed_operational_principles` remains zero. The report cannot mark an item
compliant or not applicable from an LLM's statement. Domain-specific relevance,
measurements and review decisions need a separate trusted workflow.

## Output barrier

After existing project isolation, outbound consent and exact-citation checks,
`require_principle_review` produces the final envelope. It rebuilds the report
instead of accepting one from stored JSON or a model, requires human review,
sets decision/publication/implementation permission to false and withholds
causal conclusions, savings forecasts and Mizan scores. The original citation
validator still rejects invented source IDs and quotations.

This is a deterministic coverage/permission barrier, **not** semantic validation
of an LLM question, an applicability assessment, a fatwa, a legal finding or a
new score. Accepted questions remain untested investigation drafts. Company
publication eligibility, the OS kernel and scholarly review receipts keep their
existing authority.

Project permission and source freshness are checked again after a model call.
Revoked access withholds the whole result; changed/expired evidence withholds
questions and citations. The external model flag remains off by default.

## Reproduction

The v2 report also includes `extended_registry`: typed counts and a content
fingerprint for the [unified review inventory](UNIFIED_REVIEW_REGISTRY.md).
It covers the broader 33-KPI catalogue, 114-surah and 99-name references and
3,762 existing unreviewed KPI/surah work items. These are different record kinds,
not thousands of assessed principles. The five detailed lists remain operational
questions, formulas, domains, capabilities and knowledge-review gaps.

`subject_sha256` binds the sanitised service result, server-owned project/run/
period and case ID. `inventory_sha256` binds the emitted operational questions,
KPI contracts, crosswalks, safeguards, definition content hashes and the extended
registry fingerprint. These are
reproducibility identifiers, **not** signatures or durable approval receipts.
The report omits source passages, Quran locators and divine-name metadata.
Existing bounded evidence excerpts remain in the model prompt; no religious
source metadata or full registry is added to it. No extra model call is
introduced.

```bash
DEBUG=True python manage.py test ecoiq_os.tests_principle_review \
  ecoiq_os.tests_grounded_ai api.tests_v2_decision_islah \
  api.tests_os_pilot_journey --noinput
python -m ecoiq_os.grounded_ai_eval
```

The tests cover complete inventory traversal, honest unknowns, canonical reuse,
forged approval flags, hash changes, rejected model output and revocation/source
changes during a model call. All model calls in tests use mocks; no provider
credentials or production records are needed.

## Next integration boundary

Before promoting this to a platform-wide recommendation gate, define reviewed
principle applicability, source-bound observations (distinct from source record
review), content-bound expert review and durable audit lineage. Adapt each
remaining AI entry point explicitly and test bypass attempts. Neither this
report nor pending measurement claims in PR #391 establish those approvals.
