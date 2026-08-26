# Manual actions

Everything on this branch that is safe and automatable is **already done**.
This file lists only what genuinely requires a human — and, deliberately,
it is short.

**Nothing here requires a paid service, a new account, or an API key.** No
credential of any kind was created, requested or stored on this branch.

## Summary

| # | Action | Required for | Blocking? |
|---|---|---|---|
| 1 | Restart Claude Code | Nothing — already confirmed live | No |
| 2 | Approve + start the Excel MCP server | Excel MCP tools | Only if you want them |
| 3 | Install Obsidian | Graph view over `docs/knowledge/` | No — optional convenience |
| 4 | Nothing — baseline is green (6197 tests OK on main) | — | No |
| 5 | Push and open the pull request | Review | Yes, if you want it reviewed |

A non-destructive rollback procedure is at the end of this file. It never
uses `git reset --hard`, which would destroy the working tree.

---

## 1. Restart Claude Code — not actually needed

Skills installed into `.claude/skills/` were confirmed **live in this
session**: `systematic-debugging`, `theme-factory`, `web-artifacts-builder`,
`obsidian-markdown`, `context-optimization`, `context-compression` and
`ecoiq-khalifah-engine` all appeared in the available-skills list after
installation. No action needed. Listed only because the previous tooling pass
had to infer this rather than observe it.

**Verify:** `bash scripts/ai-tooling/install-third-party-skills.sh --check`
→ nine `ok` lines.

---

## 2. Excel MCP — approve the connection and start the server

**Why:** the safe transport is `streamable-http`, which Claude Code connects
to but does not launch. stdio would auto-start but has **no filesystem
confinement at all** — it would expose `.env`, `db.sqlite3` and `~/.ssh` to
read and write. That trade is not worth making, so the server stays manual.

**Exact steps:**

```bash
bash scripts/ai-tooling/start-excel-mcp.sh
```

Then add to `.mcp.json`:

```json
"excel": { "type": "http", "url": "http://127.0.0.1:8017/mcp" }
```

Claude Code shows a one-time **connection approval** prompt for the new
server. That is a trust prompt, not a credential — there is nothing to type.

**Settings involved** (all set by the script; do not change them):

| Name | Value | Consequence if changed |
|---|---|---|
| `EXCEL_FILES_PATH` | `data/mcp/excel` | Widens what the server can read/write |
| `FASTMCP_HOST` | `127.0.0.1` | `0.0.0.0` publishes an unauthenticated file API to your LAN |
| `FASTMCP_PORT` | `8017` | Cosmetic; change only for a port clash |
| transport | `streamable-http` | stdio removes the boundary entirely |

**Least privilege:** one directory, loopback only, no credentials, no
database, no network egress.

**Verify:**
```bash
claude mcp list                                                   # excel ✔ Connected
lsof -nP -iTCP:8017 -sTCP:LISTEN                                  # must show 127.0.0.1:8017
.venv-mcp/bin/python scripts/ai-tooling/verify-excel-mcp-boundary.py   # 15 passed, 0 failed
```

**Revoke:**
```bash
pkill -f "excel_mcp streamable-http"     # stop the server
claude mcp remove excel                  # or delete the .mcp.json entry
rm -rf .venv-mcp                         # remove the package entirely
```

---

## 3. Obsidian — optional, and genuinely optional

**Why:** only for backlinks and graph view over `docs/knowledge/`. The notes
are plain Markdown; every workflow works without it, and **EcoIQ's runtime
does not depend on Obsidian in any way**.

**Steps:** install Obsidian → **Open folder as vault** → select
`docs/knowledge/`. No plugins, no configuration, no account.

**Least privilege:** Obsidian reads local files only. Do not sign into
Obsidian Sync for this vault — `vault/` holds unreviewed research and
customer-discovery material.

**Verify:** wikilinks in `docs/knowledge/templates/` resolve in the app.

**Revoke:** close the vault. Nothing is left behind but an `.obsidian/`
folder you can delete.

---

## 4. Nothing — the baseline is green

Recorded here because an earlier revision of this file claimed the opposite,
and a stale "known-red suite" note is exactly the kind of thing that gets a
real regression waved through.

This branch is cut from `origin/main` (`23decfb`). Measured on that commit
with the same interpreter and dependency set this branch uses:

| | Tests | Result | Skipped | Failures | Errors |
|---|---|---|---|---|---|
| `main` @ `23decfb` | 6197 | OK | 9 | 0 | 0 |
| this branch | 6216 | OK | 9 | 0 | 0 |

The +19 is `core/tests_ai_tooling.py`. No new failures, and nothing to triage.

The earlier "3067 tests, 1114 failures, 123 errors" figure came from a feature
branch 358 commits behind main whose migration graph could not even be built —
`league/0007_alter_evidence_file` depended on migrations that existed on main
but not in that branch's history. That was a property of the obsolete branch,
never of `main`. It does not apply here and should not be quoted as a
current-main result.

---

## Rollback — non-destructive

**Do not use `git reset --hard`, `git clean`, `git checkout --`, or
`git restore` to undo this work.** Those commands discard uncommitted
changes, and this repository is normally worked with a large dirty working
tree. `git reset --hard`
does **not** preserve a dirty working tree — it destroys it. Nothing about
undoing these six commits requires touching the working tree at all.

The branch point is `23decfb` (`origin/main`). The seven toolkit commits are
`23decfb..chore/ecoiq-ai-toolkit-main`.

### Option 1 — revert the commits on a separate branch (preferred)

Leaves history, the current branch, and the working tree intact. Produces a
reviewable revert commit rather than a silent erasure.

```bash
git switch -c revert/ecoiq-ai-toolkit-main chore/ecoiq-ai-toolkit-main
git revert --no-commit 23decfb..chore/ecoiq-ai-toolkit-main
git commit -m "revert: back out the AI toolkit branch"
```

`git revert --no-commit` stages only the inverse of those seven commits. It
does not stage, modify or discard any unrelated working-tree file. Verify
before committing:

```bash
git diff --cached --name-status     # must list only the 23 toolkit files
git status --short | wc -l          # unrelated changes still present
```

To abandon a revert midway: `git revert --quit` (keeps the working tree) —
not `git revert --abort`, which resets.

### Option 2 — inspect the pre-toolkit state in a separate worktree

Touches nothing in the working copy. Best when the goal is to compare rather
than to undo.

```bash
git worktree add --detach ../ecoiq-pre-toolkit 23decfb
# ...inspect ../ecoiq-pre-toolkit ...
git worktree remove ../ecoiq-pre-toolkit
```

### Option 3 — drop the commits but keep every file

If the branch itself should go away while the *content* stays on disk as
uncommitted changes:

```bash
git reset --soft 23decfb     # --soft only: moves HEAD, keeps index and tree
```

`--soft` is safe here where `--hard` is not: it changes no file on disk.

### Undoing the non-git side effects

All of these are gitignored and outside version control:

```bash
pkill -f "excel_mcp streamable-http"   # stop the server if running
rm -rf .venv-mcp                       # generated venv, safe to delete
```

Third-party skills under `.claude/skills/` are gitignored payloads. Removing
one is a plain directory delete; reinstall with
`bash scripts/ai-tooling/install-third-party-skills.sh`. Do **not** delete
`.claude/skills/ecoiq-*/` — those are tracked project source.

`data/mcp/excel/` may contain spreadsheets a human put there deliberately.
Inspect before deleting; nothing in this branch requires its removal.

---

## 5. Push the branch and open a pull request

Not done autonomously: pushing publishes work to a shared remote, and the
mission scope was to prepare the branch, not to publish it.

```bash
git push -u origin chore/ecoiq-ai-toolkit-main
gh pr create --base main --head chore/ecoiq-ai-toolkit-main \
  --title "chore: audited AI toolkit — third-party skills, Excel MCP boundary, context policy"
```

**Do not merge automatically.** PR CI runs Ruff, mypy, the frontend job and
`manage.py test`; all were reproduced green locally before pushing.
