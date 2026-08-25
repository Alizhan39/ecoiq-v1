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

## The four known weak spots — check these on every relevant change

### 1. SSRF in the ingestion fetcher (open, staff-gated)
[`ingestion/pipeline.py:100`](../../../ingestion/pipeline.py) `_fetch_url()`
calls `requests.get(url, allow_redirects=True)` with **no scheme allowlist
and no private/loopback/link-local IP check**. The URL is user-supplied via
`request.POST['url']` at
[`ingestion/views.py:35`](../../../ingestion/views.py).

Mitigation today is only `@staff_member_required`. Reachable targets include
`http://127.0.0.1:8731/`, RFC1918 ranges, and cloud metadata endpoints, and
`allow_redirects=True` means an allowed host can redirect into them.

**If you touch this path**: add a scheme allowlist (`http`/`https` only),
resolve the host and reject private/loopback/link-local/multicast addresses,
and re-check after each redirect. Do not widen who can submit a URL until
that exists.

### 2. Unvalidated file uploads
`FileField`s at `core/models.py:26`, `audit/models.py:72`,
`league/models.py:420`, `leads/models.py:271` have **no
`FileExtensionValidator`, no size cap, and no content-type check**. Uploaded
files are parsed downstream (`pypdf`, WeasyPrint). Adding a new upload field
without validation is a finding.

### 3. Media is on local disk, not object storage
`MEDIA_ROOT = BASE_DIR / 'media'` and there is **no `STORAGES`/
`DEFAULT_FILE_STORAGE` override, no `boto3`, no `django-storages`** in
`requirements.txt`. Cloudflare R2 is described in project docs but is not
configured in this repository. On Render's ephemeral filesystem this means
uploaded evidence does not survive a redeploy. Never describe R2 signed URLs
as an implemented control, and never assume an uploaded file will still be
there later.

### 4. Email is SMTP with a password, not Resend
`EMAIL_BACKEND`/`EMAIL_HOST_USER`/`EMAIL_HOST_PASSWORD` —
`ecoiq/settings.py` ~line 568. Resend is not integrated. Treat
`EMAIL_HOST_PASSWORD` as a live credential: never log it, never echo it,
never place it in a template context.

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
