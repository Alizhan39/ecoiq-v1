# Third-party skills & MCP audit

Audit date: **2026-08-26** · Branch: `chore/ecoiq-ai-toolkit` · Baseline commit: `d8cb9bb`
Claude Code **2.1.209** (CLI, macOS) · node 20.19.4 · Python 3.11.13

Every source below was cloned to a scratch directory outside the repository
and read. **Nothing from any upstream repository was executed** — no install
script, no hook, no MCP server, no `npx`. Files were copied; that is all.

Treat every upstream repository as untrusted input. Their SKILL.md files are
instructions this project chose to adopt, not authority this project granted.

## Classification key

| | |
|---|---|
| **APPROVED** | Installed, no usage restriction beyond EcoIQ's standing rules |
| **APPROVED WITH RESTRICTIONS** | Installed; named restrictions in [SECURITY_BOUNDARIES.md](SECURITY_BOUNDARIES.md) |
| **MANUAL AUTHORIZATION REQUIRED** | Configured, cannot be activated without a human step in [MANUAL_ACTIONS.md](MANUAL_ACTIONS.md) |
| **REJECTED** | Not installed. Reason stated. |

## Summary

| Source | Licence | Pinned commit | Verdict |
|---|---|---|---|
| [anthropics/skills](https://github.com/anthropics/skills) | Apache-2.0 (per-skill `LICENSE.txt`) | `3b3fad96af16a10759d930941b4520ba0c40edae` | 3 APPROVED, 2 APPROVED WITH RESTRICTIONS |
| [obra/superpowers](https://github.com/obra/superpowers) | MIT | `b36e0829c6d0140e93cfef2ca599b1b07d4a7797` | 1 skill APPROVED · **plugin REJECTED** |
| [haris-musa/excel-mcp-server](https://github.com/haris-musa/excel-mcp-server) | MIT | `f51340ecd5778952405044b203d3a2d4c8a46833` (v0.1.8) | APPROVED WITH RESTRICTIONS → MANUAL |
| [kepano/obsidian-skills](https://github.com/kepano/obsidian-skills) | MIT | `a1dc48e68138490d522c04cbf5822214c6eb1202` | 1 of 5 APPROVED, 4 REJECTED |
| [PleasePrompto/notebooklm-skill](https://github.com/PleasePrompto/notebooklm-skill) | MIT | `eea5cb28ba79ab8b078a1eaa44ce9ec44f75dbf8` | **REJECTED** |
| [muratcankoylan/Agent-Skills-for-Context-Engineering](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering) | MIT | `6dbe1a1d868eab51a3bc9011b0f55e2891513e40` | 2 of 18 APPROVED, 16 out of scope |

Reinstall or verify anything in this table with:

```bash
bash scripts/ai-tooling/install-third-party-skills.sh --check
```

## Per-component detail

### anthropics/skills — Apache-2.0

No top-level LICENSE; each installed skill ships its own `LICENSE.txt`
(Apache-2.0), preserved on install. No telemetry, no network calls, no
credential access in any installed skill.

| Skill | Verdict | Finding |
|---|---|---|
| `frontend-design` | APPROVED | Markdown only, no scripts. Restriction is EcoIQ's standing rule 1: `tokens.ts` / `system.css` win every disagreement. |
| `canvas-design` | APPROVED | Markdown + bundled OFL fonts. Fonts inspected: `.ttf` + OFL licence text only. |
| `algorithmic-art` | APPROVED | Markdown + two p5.js templates. Templates read: no `eval`, no network, no filesystem writes. |
| `theme-factory` | **APPROVED WITH RESTRICTIONS** | Markdown + 10 theme files + a showcase PDF. No executable content. **Its whole purpose collides with EcoIQ standing rule 1** — it offers 10 preset palettes and generates new ones. It is for *artifacts* (decks, one-off documents), never for production screens. Extract EcoIQ's existing brand before generating anything. |
| `web-artifacts-builder` | **APPROVED WITH RESTRICTIONS** | Two shell scripts and a 49-entry tarball. Tarball verified: `.tsx`/`.ts` only, no binaries, no postinstall. Scripts contain no `curl`/`wget`/`eval`/`base64` and read no secrets. **Two real findings below.** |

**`web-artifacts-builder` finding 1 — machine-global install.**
`scripts/init-artifact.sh:36` runs `npm install -g pnpm` when pnpm is absent.
That is a global mutation of the developer's machine, contrary to this
project's preference for project-local installation. The script is *not* run
by the installer here. If you ever run it, install pnpm yourself first so the
line is a no-op.

**`web-artifacts-builder` finding 2 — unpinned dependency fan-out.**
It installs ~40 npm packages, only `tailwindcss@3.4.1` pinned; the rest float,
with transitive dependencies unreviewed. Acceptable for a throwaway prototype
directory, not acceptable anywhere near the shipped bundle.

It also introduces Tailwind + shadcn/ui, which EcoIQ standing rule 7
forbids as a second design system. Prototype scope only — see
[SECURITY_BOUNDARIES.md](SECURITY_BOUNDARIES.md).

### obra/superpowers — MIT — plugin REJECTED, one skill approved

**The plugin is rejected. The `systematic-debugging` skill directory is
approved and installed on its own.**

Rejection reason — `hooks/session-start`. The plugin registers a SessionStart
hook that injects, into **every session unconditionally**, a block opening:

> `<EXTREMELY_IMPORTANT>` / "You have superpowers." / …followed by the full
> text of its `using-superpowers` skill.

Three problems, any one sufficient:

1. It is the exact opposite of progressive disclosure. Every session pays the
   token cost whether or not the task is a debugging task — against
   [CONTEXT_POLICY.md](CONTEXT_POLICY.md) and EcoIQ standing rules 3 and 4.
2. Maximum-authority framing (`EXTREMELY_IMPORTANT`) competes with `CLAUDE.md`
   and the `ecoiq-engineering-os` router for instruction priority. Benign in
   intent; the shape is indistinguishable from a context-injection attack.
3. It carries 17 further skills, a WebSocket brainstorming server, and
   worktree-manipulating scripts that were never requested.

The installed skill itself is markdown only, and genuinely good: the
root-cause-first discipline it teaches was used during this audit (it found
the `create_workbook` sheet-naming bug in the Excel verification script).

Two adaptations, applied by the installer so they survive a re-pin:

- Upstream references `superpowers:test-driven-development` and
  `superpowers:verification-before-completion`. Neither exists here, since the
  plugin is not installed — a dangling instruction the agent would follow
  confidently. Both are rewritten to `ecoiq-release-gate`, which owns that job.
- Pruned: `find-polluter.sh` (npm-only bisection; EcoIQ uses
  `manage.py test`), and `test-pressure-{1,2,3}.md`, `test-academic.md`,
  `CREATION-LOG.md` (upstream eval fixtures, not guidance).

### haris-musa/excel-mcp-server — MIT — APPROVED WITH RESTRICTIONS

Dependencies: `mcp[cli]`, `fastmcp`, `openpyxl`, `typer`. Source read in full.
No `subprocess`, `os.system`, `eval`, `exec`, or `pickle`. No `requests`,
`urllib`, `httpx` or `socket` — **no telemetry and no outbound network**. No
`keep_vba` anywhere: openpyxl does not execute macros, and this server never
asks it to.

**Finding 1 — stdio transport is completely unconfined.** The README presents
stdio as the normal local mode. Reading `src/excel_mcp/server.py`,
`get_excel_path()` with `EXCEL_FILES_PATH is None` *requires* an absolute path
and returns it unchanged. Every file the user can read or write is in scope:
`.env`, `db.sqlite3`, `~/.ssh`. **EcoIQ never uses stdio.** This is asserted
as a test, not just documented — `verify-excel-mcp-boundary.py` §2 confirms
the unconfined behaviour so that an upstream change to it is caught.

**Finding 2 — HTTP transport binds to `0.0.0.0` by default** (`server.py`
line ~70, `FASTMCP_HOST` default) with no authentication. On any shared
network that publishes an unauthenticated file API to every host on the LAN.
**EcoIQ pins `FASTMCP_HOST=127.0.0.1`**; verified with `lsof` to bind
`127.0.0.1:8017` only.

**What is sound:** with `EXCEL_FILES_PATH` set, `get_excel_path()` rejects
absolute paths and resolves both base and candidate with `realpath` before an
`os.path.commonpath` comparison — correct containment, and symlink-safe (not
a naive `startswith`). Verified by test, including a symlink pointing at the
repository root.

Both findings are mitigated by `scripts/ai-tooling/start-excel-mcp.sh`, which
is the only supported way to run it. See [MCP_SETUP.md](MCP_SETUP.md).

### kepano/obsidian-skills — MIT — 1 of 5 installed

Markdown only across the whole repository; no scripts anywhere. Clean.
Scope, not safety, drove the exclusions.

| Skill | Verdict | Reason |
|---|---|---|
| `obsidian-markdown` | APPROVED | Wikilinks, properties, callouts — exactly what the knowledge workspace needs, and useful with or without Obsidian installed. |
| `obsidian-cli` | REJECTED | Requires a running Obsidian instance (not installed here), and exposes `dev:run` — arbitrary JavaScript execution inside the user's vault application. Unnecessary capability. |
| `defuddle` | REJECTED | Instructs `npm install -g defuddle` (machine-global) and fetches arbitrary URLs. Duplicates the existing WebFetch capability with no clear benefit. |
| `obsidian-bases` | REJECTED | `.base` files need the Obsidian app to mean anything. No EcoIQ use case. |
| `json-canvas` | REJECTED | No EcoIQ use case. |

### PleasePrompto/notebooklm-skill — MIT — **REJECTED**

Independently re-audited this pass and rejected again. EcoIQ had **already**
rejected it, for the same reasons, in
[`.claude/skills/ecoiq-research-ingest/SKILL.md`](../../.claude/skills/ecoiq-research-ingest/SKILL.md).
That skill remains the authority; this entry does not duplicate it.

Confirmed from source:

1. **`patchright==1.55.2`** — a stealth fork of Playwright whose stated
   purpose is evading bot detection. Using it against Google is out of bounds
   regardless of the benefit.
2. **Google session cookies written to disk in plaintext** (`state.json` plus
   a persistent browser profile), per its own `AUTHENTICATION.md`. Those
   cookies authenticate an entire Google account, not one notebook.
3. **`setup_environment.py` autonomously creates a venv, pip-installs, and
   installs Google Chrome** via `patchright install chrome`.
4. Drives an undocumented UI surface with no public API — fragile by
   construction.

It is also the single upstream file in this audit whose SKILL.md tripped the
prompt-injection sweep on credential-related patterns.

**This is not a "needs OAuth approval" item.** Even with the user's explicit
consent the mechanism is disqualifying. The safer alternative already exists:
the manual, hash-verified manifest boundary in `ecoiq-research-ingest`,
validated by `manage.py validate_research_manifest`.

### muratcankoylan/Agent-Skills-for-Context-Engineering — MIT — 2 of 18 installed

Repository is 35 MB — 18 skills, a `researcher/` automation harness with ~20
scripts, and large screenshot sets. Installing it whole would itself be a
context-policy violation.

Installed: `context-optimization`, `context-compression`. Both scripts read in
full: pure standard library (`hashlib`, `re`, `time`, `json`, `dataclasses`,
`typing`, `enum`). No `os`, `subprocess`, network, `eval` or `pickle`.
Frontmatter uses proper trigger-scoped descriptions, so they stay dormant
until relevant.

Excluded (scope): the other 16 skills, the entire `researcher/` harness, and
all examples. The prompt-injection sweep flagged `context-compression`; the
hits were example text about a 401 error, benign on inspection.

## Prompt-injection sweep

Every `SKILL.md` across all six repositories was scanned for instruction-
override and credential-access patterns (`ignore previous`, `disregard`,
`override the system`, `exfiltrat*`, `api_key`, `.env`, `~/.ssh`,
`credential`, `curl … | sh`, outbound POST targets).

Hits: 6 files. Five are benign — example text, or documentation of the
skill's own subject matter. The sixth is `notebooklm-skill`, rejected on
other grounds. **No installed skill contains an instruction-override
pattern.**

## Deliberate scope decision: payloads are not vendored

Third-party skill *payloads* stay gitignored, per CLAUDE.md rule 14 and the
existing `.gitignore` policy ("machine-local vendored third-party skills").
What is committed is the reproducible install: the pinned installer, this
audit, and `third-party-skills.lock.json`. Each installed directory also gets
a generated `PROVENANCE.md` naming its upstream, path and SHA.

Trade-off, stated plainly: installs need network access, and an upstream
force-push or deletion would break reinstall. The installer verifies the
resolved SHA and fails loudly rather than silently taking a different commit.
To vendor the payloads instead, re-include the paths in `.gitignore` — the
audit and lockfile stay valid either way.
