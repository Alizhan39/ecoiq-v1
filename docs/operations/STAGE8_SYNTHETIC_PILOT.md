# EcoIQ Stage 8 — Enterprise security and controlled synthetic pilot

**Status: code/blueprint only; no service provisioned, no production deploy, no external AI/model call.** Stage 8 depends on the Stage 7 Human Review PR and its database migration.

## 0. Verify repository integration order

- Stage 6 PR #365 contains `ecoiq_os/grounded_ai.py`.
- Stage 7 PR #366 was initially merged into a feature branch rather than main.
- Main integration PR #367 must be reviewed and merged before Stage 8 can be independently merged to main.
- This PR is stacked on the Stage 7 feature branch; its CI must pass before retargeting to main.

Do not infer that GitHub test success means Render environment exists or is secure.

## 1. No-cost build and evaluation

With the pinned Python 3.11 dependencies installed:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test ecoiq_os.tests_pilot_security core.tests_ai_review ecoiq_os.tests_grounded_ai --noinput
python -m ecoiq_os.pilot_evaluation
```

These commands require NO provider API keys and do not contact AI systems. The synthetic benchmark exercises exact citation validation in EN/RU/AR, including malformed JSON, invented sources, invented quotations, excessive question length and unsupported approval fields. It does NOT measure model truthfulness, judgement, injection robustness or business results.

## 2. Separate staging infrastructure (manual, NOT provisioned)

Create a **separately billed and explicitly authorised** staging environment, not a preview tied to production secrets or the existing `ecoiq` web service. The currently known Render EcoIQ web, cron and worker services are suspended. Do not unsuspend, deploy or pay for resources automatically.

1. Use a new, **independent** database and credentials, with DB name `ecoiq_pilot_...`; never restore/copy the production database or use production staff accounts, customer data, API keys, Redis or S3.
2. Restrict web access to named testers with network access controls or a separate identity/SSO access layer. Application login alone is insufficient for a confidential pilot. Verify HTTPS/secure proxy and access logs; use a distinct hostname containing `pilot` or `staging`.
3. Create new staging-only secrets, session signing key, and role-based test users. Disable real email, billing, outbound AI, schedulers and external integrations. Block unnecessary egress at the infrastructure level; this document does NOT implement a firewall.
4. Start from `infra/staging/pilot.env.example`; **keep attestation flags false** until the operator has actually verified independent DB and cache, private access, egress firewall, disabled background jobs and synthetic-only data.
5. Choose `DJANGO_SETTINGS_MODULE=ecoiq.settings_pilot`. These settings force `DEBUG=False`, `AI_ENABLED=False`, `ECOIQ_GROUNDED_AI_EXTERNAL_ENABLED=False`, `ECOIQ_BILLING_PROVIDER=none`, local-memory email and secure cookies. Startup refuses if the fail-closed preflight does not pass.
6. Execute `python scripts/pilot/preflight.py` before starting any web server. It prints check names and booleans only; never DB credentials or source excerpts. A pass means configuration and operator attestations are present; it is **not an independent cloud security verification**.
7. Only after a change ticket and DB backup strategy, run migrations in **staging only**. Verify `/healthz/`, project role separation, CSRF, source revocation, view-source escaping, privacy/no-store and review audit. Confirm the browser shows zero customer records.
8. Have a named operator verify rollback steps, disaster recovery and logging redaction. Obtain explicit approval before any paid Render deployment.

## 3. Retention and deletion

This stage proposes review targets: pending AI-question drafts 30 days, decided drafts 90 days, readiness checklist expires after 7 days (already set in Stage 7). Targets are **not** an approved company retention policy.

```bash
python scripts/pilot/retention_audit.py
```

Read-only output: aggregate counts beyond target; no user/project IDs, document text, actor names or raw model outputs. It does not erase evidence or audit events. Audited deletion must have independently approved legal hold, retention, export, backups and referential-integrity design before activation. No automated purge exists in Stage 8.

## 4. Pilot gates: what can and cannot be concluded

| Gate | Minimum evidence |
|---|---|
| App code | CI Ruff, syntax, migration drift, Stage 6–8 tests |
| Identity | Reviewer/manager role and separate submitter/reviewer |
| Data | Synthetic fixture only, verified source path, no production copy |
| Privacy | No index, private/no-store, no analytics on review pages, retention plan |
| AI | `AI_ENABLED=False`, Stage 6 outbound latch false, no external network transfer |
| Model evaluation | Only static synthetic *validator* fixture; real LLM quality NOT measured |
| Operations | Manually inspected independent infra, rollback, backups, firewall |
| Go / no-go | Human security and data-protection signoff required |

## 5. Next controlled expansion (not part of Stage 8)

After a properly commissioned staging and security review, add a separate offline/approved local-model evaluation harness with realistic but **licensed, synthetic or explicitly permitted** documents. Measure statement-level citation precision, semantic fidelity, multilingual behaviour, prompt-injection attempts, abstention and latency. External inference requires an independent legally reviewed authorisation record, provider-specific controls and revocation; Stage 7 readiness fields alone must never enable transfer.

## Critical boundary

**Do not put personal or customer data in these fixtures.** This stage does not certify ISO 27001, ISO 42001, GDPR compliance or any cybersecurity assurance. The checklists and automation deliberately decline to make that claim.
