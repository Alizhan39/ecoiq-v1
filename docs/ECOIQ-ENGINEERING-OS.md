# EcoIQ Engineering OS

The domain, governance, and go-to-market layer of EcoIQ's agent tooling.
Sits beside the existing design/frontend/motion stack, which is unchanged:

- [`AI-SKILL-ROUTER.md`](AI-SKILL-ROUTER.md) — frontend/design/motion routing.
- [`AI-QUALITY-GATES.md`](AI-QUALITY-GATES.md) — what "done" means for a change.
- [`AI-DEVELOPMENT-STACK.md`](AI-DEVELOPMENT-STACK.md) — what is installed and why.
- [`AI-TOOL-INSTALLATION-MANIFEST.md`](AI-TOOL-INSTALLATION-MANIFEST.md) — per-tool classification.
- [`THIRD-PARTY-INTEGRATIONS.json`](THIRD-PARTY-INTEGRATIONS.json) — machine-readable provenance for everything below.

Entry point for routing: `.claude/skills/ecoiq-engineering-os/SKILL.md`.

---

## 1. Baseline, measured before any change

Recorded 2026-08-25 on `feat/ecoiq-engineering-os`, branched from
`feat/stripe-billing-integration` at `15183f0` with 113 pre-existing
working-tree changes preserved and untouched.

| Check | Command | Result |
|---|---|---|
| Django system check | `manage.py check` | **0 issues** |
| Migration drift | `manage.py makemigrations --check --dry-run` | **No changes detected** |
| Test suite | `manage.py test --parallel 4` | **2881 tests, OK, 2 skipped, 54.1s, exit 0** |
| Installed apps | — | 79 |
| Shell/eval surface in app Python | `grep subprocess/os.system/shell=True/eval` | **0 occurrences** |
| Lint / type-check / formatter | — | **None configured** (no ruff, black, flake8, or mypy config in the repo; CI runs check + migrations + tests only) |
| Frontend build | `frontend/app` Vite + tsc | Not run — no frontend source was changed by this work |

Everything below was added on top of that baseline. The final state is in §8.

---

## 2. Compatibility matrix — all ten candidates

Assessed from GitHub API metadata plus direct reads of each repository's own
installer, hook, and authentication files. **No candidate repository was
cloned, installed, or executed.**

| # | Candidate | Real capability | Licence | Maintained | Install method | Permissions it would need | Dependency conflict | Overlap with EcoIQ | Security risk | Decision | EcoIQ use case |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | [Superpowers](https://github.com/obra/superpowers) | 14 engineering-workflow skills + a SessionStart hook | MIT | Active (2026-08-19), 278k★ | Plugin dir + `hooks/` | Session hook execution; unconditional context injection | None technical | Generic engineering skills already available | Low code risk, **high architecture risk** — its hook injects a skill into *every* session as `EXTREMELY_IMPORTANT`, outranking EcoIQ's own CLAUDE.md | **ADAPT** | Verification-before-completion discipline → `ecoiq-release-gate` |
| 2 | [Marketing Skills](https://github.com/coreyhaines31/marketingskills) | Marketing skill collection | MIT | Active (2026-08-24), 46k★ | Plugin dir | Filesystem | None | No EcoIQ marketing tooling existed | Low — no installer or hook at top level | **ADAPT** | ICP/positioning/CRO structure → `ecoiq-growth`; its `validate-skills.sh` inspired `validate_skills` |
| 3 | [Anthropic brand-guidelines](https://github.com/anthropics/skills/tree/main/skills/brand-guidelines) | Document pattern for a brand skill | Per-skill LICENSE.txt | Active (2026-08-21) | Copy 2 files | None | None | `ui-ux-pro-max:brand` (generic) | None — two inert files | **ADAPT** | Section structure only → `ecoiq-brand`, populated from EcoIQ assets. Its *content* is Anthropic's brand and would be wrong here |
| 4 | [Claude SEO](https://github.com/AgriciDaniel/claude-seo) | 25 sub-skills + 18 sub-agents, technical SEO through GEO/AEO | MIT | Active (2026-08-25), 15k★ | `install.sh` / `install.ps1` | Write to `~/.claude/`, isolated Python runtime, Chromium download, executable hooks, Google API creds | Its own Python runtime | None — genuine gap | **Medium** — unreviewed installer provisions a runtime and registers executable hooks; 43 loaded units defeats progressive disclosure | **ADAPT** | Check coverage → native `manage.py seo_audit` |
| 5 | [Remotion](https://github.com/remotion-dev/remotion) | Programmatic video in React | **NOASSERTION — custom source-available** | Active (2026-08-25), 57k★ | Already in repo, pinned 4.0.190 | Local Node + headless Chromium | Would be severe if added to the Django runtime | Already the video path | Low technical; **commercial licence flag — see §6** | **ISOLATE** | Documented existing workspace → `ecoiq-remotion` |
| 6 | [Anthropic skill-creator](https://github.com/anthropics/skills/tree/main/skills/skill-creator) | Skill authoring mechanics | Per-skill LICENSE.txt | Active | **Already installed** in this environment | None | None | Direct — it is already available | None | **ADOPT** | Referenced by `ecoiq-skill-creator`, which adds only EcoIQ-specific rules |
| 7 | [MassGen](https://github.com/massgen/massgen) | Multi-agent orchestration runtime (~631 MB) | **NOASSERTION** | Stalest candidate (2026-06-12), 1.1k★ | pip/CLI | Shell, network, model API keys | Second agent runtime beside `langgraph_orchestration/` | Duplicates existing orchestration | Medium — unresolved licence, large surface, model-driving runtime | **REJECT** | None. Navigation stays native (`rg`) |
| 8 | [Agent Skills for Context Engineering](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering) | Context-engineering skill collection (~35 MB) | MIT | Active (2026-08-19), 18k★ | Plugin dir | Filesystem | None | Overlaps `AI-SKILL-ROUTER.md`, which already treats progressive disclosure as a principle | Low | **ADAPT** | Applied as methodology: narrow triggers, 500-char description cap enforced in CI, link-don't-restate |
| 9 | [Anthropic web-artifacts-builder](https://github.com/anthropics/skills/tree/main/skills/web-artifacts-builder) | React/Tailwind/shadcn artifact builder | Per-skill LICENSE.txt | Active | **Already installed** | None | None | None — no prototyping lane existed | None | **ADOPT** | Referenced by `ecoiq-prototype` with EcoIQ guardrails |
| 10 | [NotebookLM Skill](https://github.com/PleasePrompto/notebooklm-skill) | Browser-automated NotebookLM queries | MIT | 2025-11-21 (oldest), 7.7k★ | `requirements.txt` + browser setup | **Google account login; cookie persistence; Patchright stealth browser** | Playwright/Patchright | None | **High — see §5** | **REJECT** | Replaced by a manual, validated ingestion boundary |

**URL correction:** the supplied Marketing Skills URL
(`coreyhaines31/marketing-skills`) returns HTTP 404. The real repository is
`coreyhaines31/marketingskills`, confirmed against the owner's repository
listing before use.

Totals: 2 adopt · 5 adapt · 1 isolate · 0 defer · 2 reject.
Repositories cloned: 0. Installers executed: 0. Hooks registered: 0.
MCP servers added: 0. Runtime dependencies added: 0.

---

## 3. Architecture

Fourteen skills in `.claude/skills/ecoiq-*/`, each loaded only when its
triggers fire. The router is a map, not a preamble — it is not injected into
every session, which is the specific reason Superpowers' hook was rejected.

| Layer | Skills |
|---|---|
| A — Development workflow | `ecoiq-release-gate`, `ecoiq-skill-creator` |
| B — Product & domain | `ecoiq-evidence-audit`, `ecoiq-khalifah-loop`, `ecoiq-regulatory-review`, `ecoiq-impact-claims` |
| C — Marketing & SEO | `ecoiq-brand`, `ecoiq-seo-audit`, `ecoiq-growth` |
| D — Media generation | `ecoiq-remotion`, `ecoiq-prototype` |
| E — Research & ingestion | `ecoiq-research-ingest` |
| F — Security & validation | `ecoiq-security-review`, plus `validate_skills` and `validate_research_manifest` |
| Router | `ecoiq-engineering-os` |

Three backing commands, all Django-native, all offline, no new dependency:

- `manage.py validate_skills [--strict]`
- `manage.py seo_audit [--strict] [--explain]`
- `manage.py validate_research_manifest <path>...`

### Why the skills are committed

`.claude/` was wholly gitignored. Narrow negations now track **only**
`.claude/skills/ecoiq-*/`; `settings.local.json`, `launch.json`,
`worktrees/`, and the machine-local vendored third-party skills remain
ignored (verified with `git check-ignore`). The Engineering OS is project
source: it must be reviewable in pull requests and gated in CI, which is
impossible for an untracked file. Same negation precedent as the existing
`!static/dist/` rule in the same file.

**This is the one architectural decision here that changes an existing
convention.** To revert: restore `.claude/` as a single line in `.gitignore`.

---

## 4. Findings from the audit

Discovered while building; none introduced by it.

### Product vocabulary that the code does not implement
- **The twelve Khalifah loop stages exist nowhere in code.** No module,
  constant, or enum is named `DETECT`, `DIAGNOSE`, `SIMULATE`, `OPTIMIZE`, or
  `REPEAT`. The real pipeline is the LangGraph graph
  (`classify_intent → … → finalize`). `MATCH`, `EXECUTE`, and `MEASURE` are
  view-only scaffolds; `projects/` has 0 models and 0 tests; nothing
  implements loop re-entry. Full maturity table in `ecoiq-khalifah-loop`.
- **No 12,996-cell KPI-to-surah matrix exists** in the repository.
- **"33 KPIs" is 33 sub-formulas plus 3 master formulas** in
  `ethics/registry.py` (`NEI`, `TSS`, …).
- **Cloudflare R2 is not configured.** No `STORAGES` override, no `boto3`,
  no `django-storages`. `MEDIA_ROOT` is local disk — on Render's ephemeral
  filesystem, uploaded evidence does not survive a redeploy.
- **Resend is not integrated.** Email is SMTP with `EMAIL_HOST_PASSWORD`.
- **Kazakh is not supported by the assistant** (`en`/`ar`/`ru` only), and the
  site itself ships English only — `ru`/`kk`/`ar`/`tr` are commented out in
  `LANGUAGES`.

### Security
Findings from the original audit, reassessed against current `main`:
- **SSRF** — `backend_intelligence_engine/services/http_client.py` and
  `company_intelligence/services/url_safety.py` already solved this on main.
  Three call sites still bypassed them (`ingestion/pipeline.py`,
  `intelligence/compute.py`, `companies/.../extract_pdf_kpis.py`); this branch
  routes all three through the existing guarded client.
- **No upload validation** on six `FileField`s whose files are parsed by
  `pypdf`/WeasyPrint. **Fixed** by `core/upload_validation.py` on the four
  user-facing surfaces. `leads.ReviewRequest.sustainability_report` promised
  "PDF only · max 10 MB" with nothing enforcing it.
- **Evidence storage** — already solved on main by `core/storage.py`
  (`MEDIA_STORAGE_BACKEND`, key sanitisation, presigned URLs). This branch
  adds nothing there and deliberately does not duplicate it.
- Strong existing controls, left alone: no shell surface, server-assembled
  system prompt unreachable from user input, structurally free-only model
  routing, Gitleaks on every push and PR, full production hardening.

### SEO
- **Every page's `og:image` is a 404.** `templates/base.html:22` and
  `templates/contact.html:12` point at `/static/brand/ecoiq-og.png`, which
  does not exist. No social preview renders anywhere.
- No `twitter:card` meta.
- Verified healthy: robots.txt with a sitemap directive, 424 sitemap URLs,
  all nine required head tags, one canonical host, correctly no hreflang for a
  one-language site, JSON-LD on company detail, and deliberate per-bot blocks
  (Bytespider, CCBot, PetalBot) that are **not** a site-wide de-index.

### Coverage gaps
`ethics/` — the scoring core — has an empty `tests.py`, as do `transition/`
and `ingestion/`.

---

## 5. Why NotebookLM was rejected

Read from its own `AUTHENTICATION.md`, not inferred. Three independent
grounds, each sufficient:

1. It automates a **Google account login**. Performing an account login on a
   user's behalf is not something to do autonomously.
2. It persists **Google session cookies to disk** — a `browser_profile/`
   directory plus a plaintext `state.json`, re-injected each run. Those
   cookies authenticate an entire Google account, not a scoped notebook.
3. It uses **Patchright**, a stealth Playwright fork whose purpose is evading
   bot detection.

It is community-maintained, not an official integration, and depends on
undocumented internal endpoints.

**Replacement, built and tested:** a manual boundary —
[`research-ingest-manifest.schema.json`](research-ingest-manifest.schema.json),
`manage.py validate_research_manifest`, and `ecoiq-research-ingest`. It
enforces source inventory, source ids, summaries with a declared author,
citations, ingestion dates, SHA-256 document hashes, honest nullable
confidence, and human review state — including the two rules a JSON Schema
cannot express: promotion out of `unreviewed` requires a named human, and an
AI-written summary can never be `approved` without one.

---

## 6. Permissions and decisions still required

Nothing below was actioned; all are the user's to decide.

| Item | Why it is blocked | What is needed |
|---|---|---|
| **Remotion Company Licence** | Remotion's licence is free for individuals, nonprofits, and for-profit organisations of up to 3 employees. Above that, a paid Company Licence is required. EcoIQ is commercial. | A headcount check against the licence and, if applicable, a licence from remotion.pro. Nothing to change in code. |
| `og:image` asset | Fixing it means creating brand artwork — a 1200×630 PNG. `static/img/og-card.svg` exists but SVG is not a supported OG format. | A brand decision, then one file plus a one-line template change. |
| Google Search Console / CrUX | Index coverage, Core Web Vitals field data, and backlinks need credentials and network access. | Credentials, if these checks are wanted. `seo_audit --explain` lists exactly what it cannot see. |
| Playwright MCP approval | Pre-existing from the earlier pass — `.mcp.json` entry still unapproved in project config. | One-time approval prompt. |
| Figma / Composio MCP | Pre-existing — see `AI-TOOL-INSTALLATION-MANIFEST.md`. | Paid plan / API key. |

**Environment variables:** none added. The Engineering OS introduces no new
configuration. Every command runs offline against files already in the
repository. `.env.example` is unchanged.

---

## 7. Rollback

Everything is additive and independently reversible.

```bash
git checkout main -- .gitignore            # restore the single `.claude/` ignore line
rm -rf .claude/skills/ecoiq-*/
rm core/management/commands/validate_skills.py
rm core/management/commands/seo_audit.py
rm core/management/commands/validate_research_manifest.py
rm core/tests_engineering_os.py core/tests_seo_audit.py
rm docs/ECOIQ-ENGINEERING-OS.md docs/THIRD-PARTY-INTEGRATIONS.json
rm docs/research-ingest-manifest.schema.json
```

Then remove the `validate_skills` step from `.github/workflows/django.yml`
and the Engineering OS section from the root `CLAUDE.md`. No migration, no
data change, no dependency to uninstall.

---

## 8. Validation after the change

See §1 for the pre-change baseline. Post-change results are recorded in the
session report and re-runnable with:

```bash
.venv/bin/python manage.py check
.venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/python manage.py validate_skills --strict
.venv/bin/python manage.py seo_audit
.venv/bin/python manage.py test --parallel 4
```

`seo_audit` is intentionally **not** run with `--strict` in CI while the
`og:image` finding is open — a known, documented product bug should not block
unrelated pull requests. Turn on `--strict` once the asset exists.

**Production was not changed.** No deployment, no migration against a
non-local database, and no edit to `render.yaml`, `build.sh`, `predeploy.sh`,
or `start.sh`.
