# Stage 6: Evidence-Grounded AI Drafts (experimental, opt-in only)

## Scope and architectural boundary

Stage 6 is an **internal Python service**, not a public API. It connects
existing project-authorised `EvidenceMemory` rows and the existing `AIService.chat`
model gateway. No new provider client, database model, migration, vector
search implementation, or independent evidence registry is introduced.

- Entry: `ecoiq_os.grounded_ai.prepare_grounded_draft(project, user, run, ...)`
- Source selection: `collect_reviewed_sources(project, user)`
- Output validation: `validate_grounded_questions(model_answer, sources)`
- Benchmark: `python -m ecoiq_os.grounded_ai_eval`
- Tests: `python manage.py test ecoiq_os.tests_grounded_ai`

**Current default: outbound model calls disabled.** Merely importing or
invoking the service with defaults never transmits data. We have **not**
connected the flow to the user interface or deployed it.

## Source safeguards

Requests are anchored to an existing `GoldProject`, an authenticated
`ANALYSE` grant from `gold_intelligence.access`, and a `ProcessAnalysisRun`
with matching `project_id`. The source list is deliberately narrower than
the general retrieval policy:

1. Only source records linked to the **same** project with
   `visibility=project_private`, `verification_status=verified`,
   `review_tier=independently_verified`, a recorded reviewer and
   `is_demo=False`.
2. Reuse the authoritative `is_record_accessible` per row; deny rejected,
   expired, disputed or superseded records; exclude agent-generated output.
3. Require a nonempty source reference and validate the stored text's current
   SHA-256 against its stored integrity reference. This is **only** a check of
   stored text integrity, **not** proof of document authenticity.
4. At most four excerpts; at most 600 characters each; no source URL or
   original source reference forwarded. Text embedded in the prompt is marked
   **untrusted source data**, never instructions.

`ProcessAnalysisRun` itself intentionally retains only unverified aggregate
CSV figures; it cannot acquire independently-verified or causal status just
because separately reviewed documents exist in EvidenceMemory.

### External model transfer is separately guarded

Three conditions must hold:

- Current project ANALYSE permission for the actor.
- `external_transfer_approved=True` from a trusted, server-side invocation,
  representing documented approval for this *specific* data transfer.
- `ECOIQ_GROUNDED_AI_EXTERNAL_ENABLED=True` explicitly configured server-side.
  Default False.

Both project permission and eligible sources are recomputed immediately
before the call. No user-controlled HTTP route, query parameter, browser
switch or public model selection is provided in this stage.

**IMPORTANT:** A reviewed record may still contain personal, commercial or
confidential data. Do not enable external transfer until there is a real
legal basis and data-processing arrangement, provider retention and
training-use assessment, contractual authorisation, DPIA as appropriate,
redaction policy, consent/audit workflow and deletion policy. The
`external_transfer_approved` argument is NOT a replacement for these
institutional controls.

## Model contract: questions, not conclusions

When explicitly enabled, the existing `AIService.chat` receives a
bounded, labelled, JSON-encoded context and asks for:

```json
{
  "questions": [
    {
      "question": "Could reporting cut-offs explain part of the discrepancy?",
      "citations": [
        {"key": "S1", "quote": "An exact substring from source S1"}
      ]
    }
  ]
}
```

Validation requires a closed JSON schema, 1–3 questions, no unknown source
keys, and an **exact quote substring** for every citation. An invalid,
oversized, fabricated or structurally unsafe answer becomes
`MODEL_OUTPUT_REJECTED`; the raw model answer is not included in the result.
Accepted questions retain `UNTESTED`, `REVIEW_REQUIRED`,
`implementation_permitted=False`, `causal_conclusion=None`,
`savings_forecast=None` and `mizan_score=None`. No operational actions,
approval writes, or changes to existing kernel authorisation.

A quote-matching check cannot prove scientific accuracy, causal validity
or freedom from prompt injection. A human must independently inspect the
source and the question's interpretation.

## Current verification plan

1. GitHub Actions fast targeted tests and citation synthetic benchmark.
2. Full integration CI for the stage 2–5 dependency PR #363.
3. Browser review, cross-project and revocation tests in staging with
   synthetic non-personal documents.
4. Security review for external-provider outbound data; add auditable
   approval records before enabling it.
5. Only then a carefully scoped model benchmark covering citation
   precision, unsupported claims, abstention, injection handling, multilingual
   output and cost/latency.
6. Human acceptance and Mizan/Islah simulation before operational changes.

Do not present the synthetic benchmark's pass rate as AI model accuracy.
This module is not ready for production and not a verified business decision
engine.
