# Dependency security and reproducibility

## What is now checked

The [Dependency Vulnerability Audit](../../.github/workflows/dependency-audit.yml)
runs on relevant dependency PRs, after dependency changes reach `main`, every
Monday, and on manual dispatch.

- Python: install **resolved** `requirements.txt` under Python 3.11.16 and
  run `pip-audit==2.10.1` against the installed environment.
- SPA: run `npm audit --omit=dev --audit-level=high` against the existing
  `frontend/web/package-lock.json`; no third-party install scripts are run.
- Any reported vulnerability or audit failure makes its individual job red.
  This is intentional. Do not add blanket ignore rules or `continue-on-error`
  to disguise known CVEs.
- [Dependabot](../../.github/dependabot.yml) proposes limited, weekly,
  reviewable updates to Python, the SPA, and GitHub Actions. It does **not**
  automatically merge anything.

## Scope and remaining work

A successful scan **does not** prove a package or image is free from
vulnerabilities; databases cover only known advisories. Python currently has
some permissive requirements (`>=`), so two clean CI installations can resolve
different transitive versions at different times. This PR *detects* known
vulnerabilities; it does not pretend to fix reproducibility.

Follow-on, separate from this audit: generate and review a reproducible
Python production resolution using a maintained dependency tool such as
`uv pip compile` or `pip-tools pip-compile`. Do not change every dependency
and the deployment path in the same PR: compare the resolved result to the
currently deployed versions, test all migrations and API contracts, then
switch the build to the lock in one reversible change.

Dependency findings should be triaged by package, transitive path, impact,
advisory, upgrade availability, and regression tests. An upstream warning
without a fixed version can remain visible and tracked rather than silently
suppressed.

The audit is a GitHub CI operation, not an additional Render service or a
paid runtime dependency. It never reads production credentials, changes
database plans, or deploys application code.
