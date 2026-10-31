---
name: ecoiq-security-review
description: EcoIQ-specific security review for authentication, authorisation, API keys and tiers, file uploads, media storage, outbound URL fetching (SSRF), Celery/Redis, LLM input handling and prompt injection, secrets, logging, and audit trails. Use when changing any of those, or when asked to security-review a diff in this repo. Prefer it over the generic security-review, which carries no EcoIQ context. Not for third-party dependency auditing.
---

# EcoIQ security review

Start from what the codebase already does well, then check the four known
weak spots. Do not re-derive the whole model each time.

## Already solid — don't "fix" these

- **Production hardening** is set: `SECURE_SSL_REDIRECT`, HSTS 1y with
  preload, secure session/CSRF cookies, `SECURE_CONTENT_TYPE_NOSNIFF`,
  `SECURE_PROXY_SSL_HEADER` — [`ecoiq/settings.py`](../../../ecoiq/settings.py) ~line 616.
- **No shell surface.** Zero `subprocess`, `os.system`, `shell=True`, or
  `eval` in application Python. Keep it that way; a new one is a finding.
- **Prompt injection at the gateway.** `ai_gateway/service.py` refuses
  client `system`-role messages, so the single server-assembled prompt in
  [`ai_gateway/prompts.py`](../../../ai_gateway/prompts.py) is always index 0
  and unreachable from user input. Any new AI surface reuses this gateway.
- **Free-pool routing is structural**, not conventional — `ai_gateway/router.py`
  cannot express "fall back to a paid model." Don't add a path that can.
- **API keys** carry scope and tier: `api/permissions.py`
  (`IsAPIKeyAuthenticated`, `IsEnterpriseKey`, `RequiresFeature`) and
  per-tier throttling in `api/throttles.py`.
- **Harvester fetching** validates size, content-type, and robots.txt —
  `harvester/services/fetchers.py`.
- **Secrets in CI**: Gitleaks runs on every push and PR with `--redact` and
  no allowlist (`.github/workflows/secret-scan.yml`). A new `.gitleaks.toml`
  entry must be narrow and individually justified.

## The known weak spots — check these on every relevant change

### 1. Outbound fetching has one authority
[`company_intelligence/services/url_safety.py`](../../../company_intelligence/services/url_safety.py)
is the single URL validator: scheme and port allowlists, hostname denylist,
credentials refused, and every resolved address checked (including
100.64.0.0/10, which Python reports as public but holds Alibaba's metadata
endpoint). Crucially it separates `public_reason` from loggable `detail`, so a
rejection echoed back to a submitter cannot be used as an internal port
scanner.

[`backend_intelligence_engine/services/http_client.py`](../../../backend_intelligence_engine/services/http_client.py)
`fetch()` applies it to the initial URL **and every redirect hop**, caps the
chain, and caps the body. Every fetch of an externally supplied URL goes
through `fetch()` — `ingestion/pipeline.py`, `intelligence/compute.py` and
`companies/.../extract_pdf_kpis.py` all delegate to it.

**Do not write a second validator.** `good_agents/services/safe_http.py` keeps
its own per-adapter host allowlist on purpose — that is a narrower trust
decision, not a competing denylist.

Residual risk: DNS rebinding. Validation happens at connection time on every
hop, but neither requests nor httpx exposes a hook to pin the socket to an
already-validated address.

### 2. Uploads go through `core/upload_validation.py`
The four user-facing upload fields (`core.Assessment.uploaded_file`,
`audit.AuditSession.uploaded_file`, `league.Evidence.file`,
`leads.ReviewRequest.sustainability_report`) carry an `UploadValidator`: it
allowlists extensions, confirms type by **inspecting leading bytes**, refuses
extension/content mismatches and double extensions, sanitises filenames
against traversal under both separator conventions, rejects executables and
scripts, refuses active content in text files, inspects xlsx/docx ZIP members
for traversal and compression bombs, and caps image megapixels.

Validators run on `full_clean()` — ModelForms, the admin and DRF serializers
call it; a bare `.save()` does not. Existing stored files are untouched.
**A new upload field without a validator is a finding.**

Two fields are deliberately not validated: `audit.AIAnalysisJob.pdf_file` and
`companies…thumbnail` are written by EcoIQ, not uploaded by a user.

### 3. Storage belongs to `core/storage.py`
Object storage, key sanitisation and presigned URLs are already solved there
via `MEDIA_STORAGE_BACKEND` and the `upload_to_*` callables. **Do not add a
second storage mechanism**, a per-field `storage=`, or a parallel set of
environment variables — a test in `core/tests_upload_validation.py` asserts
the upload fields still resolve their path through `core.storage`.

### 4. Email is SMTP with a password, not Resend
## Checklist by area

- **Authz**: every new API view declares a permission class; staff-only views
  use `@staff_member_required`; no permission decision routed through an LLM.
- **Tenancy**: queries filter by the requesting key's company/scope — never
  rely on an unfiltered `objects.all()` plus template logic.
- **Celery/Redis**: task arguments are ids, not serialised secrets or full
  model payloads; `REDIS_URL` is never logged.
- **LLM input**: untrusted text (harvested pages, uploaded PDFs, form input)
  is *data*. It never becomes an instruction, and it never reaches a
  `system` message.
- **Logging**: no API key, token, cookie, password, or full prompt containing
  user PII in a log line.
- **Audit trail**: security-relevant state changes write to the existing
  `legacy_safe.AuditLog` / `capital_guardian.AuditLogEntry` — don't add a
  third audit table.

## Done when

- No new shell/eval surface, no new secret in code or logs.
- Every weak spot the change touches is either fixed or explicitly named as
  out of scope in the report.
- Findings are reported with file:line and a concrete failure scenario.
