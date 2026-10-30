# Stage 7 — Human AI Question Review & Audit

## What is implemented
A **private, server-rendered** human review interface at
`/business-os/ai-review/` with a project-specific detail page. It does not
accept an arbitrary browser-uploaded AI draft or run a provider call.

- `ecoiq_os.human_review.queue_grounded_review` is a trusted internal
  integration point for Stage 6 `prepare_grounded_draft` outputs. It refuses
  model results that have not passed the Stage 6 exact-quote gate.
- `ProcessAIReviewCase` persists at most 3 untested research questions,
  their bounded exact citations, the manifest of source IDs and content
  digests, and current reviewer decision. No original CSV, full document,
  raw model answer, email or provider credential is stored.
- `ProcessAIReviewEvent` records one submission and each completed human
  decision with actor, time, reason code and digest.
- Users with active `gold_intelligence.access.APPROVE` role (reviewer,
  manager, or authorised staff) can view the queue and individual source
  excerpts; analysts and viewers cannot. A reviewer cannot decide their
  own submitted draft. Project permissions and source integrity are checked
  afresh on every review. Source revocation, document edits, expiry, legal
  dispute or degraded verification fail closed.
- Accept means **accepted as a falsifiable question for study**. Reject and
  needs-revision are separate choices. None authorises implementation,
  causal conclusions, savings, Mizan score or a religious ruling.
- `ProcessAIProcessingReadiness` records that a reviewer has evaluated
  source rights, data minimisation/privacy and provider terms. It expires
  after seven days and permanently records
  `authorises_external_transfer=False`. This does **not** activate external
  AI transmission, which remains disabled by default in Stage 6.

## Browser and security
Django GET/POST forms include CSRF, role-scoped queries, escaped source
excerpts, no-store/noindex headers, no third-party analytics, and
redirect-after-POST. There is no endpoint for creating review cases from
untrusted JSON, no public disclosure, no AI call or autonomous write.

## Audit and honesty boundary
Events are append-only **via the application services**, but are not
cryptographically immutable or an independently certified audit trail.
Store only bounded quotes, but treat even those as possibly confidential.
Define encryption/retention, subject access and deletion governance before
client usage. Access to the database and Django Admin remains a separate
operational privilege. The readiness checklist is not a substitute for legal
basis, provider contract, client authorisation or DPIA, where required.

## Run tests
```bash
python manage.py makemigrations --check --dry-run
python manage.py check
python manage.py test core.tests_ai_review ecoiq_os.tests_grounded_ai --noinput
```

## Explicitly deferred
- Do NOT enable external model transfer from the checklist. A separately
  designed and legally reviewed service-to-service permission token,
  provider allowlist, redaction and audit mechanism would be required.
- Real model evaluation on client documents, source export, irreversible
  deployment, AI-generated approval, operational interventions and
  implementation authorisation are out of scope.
- Verify migration against an isolated staging database, check browser
  accessibility, data retention and cross-tenant properties before merge.
