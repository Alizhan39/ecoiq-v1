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
| 4 | Decide on the red baseline test suite | An honest CI signal | **Yes, for the repo** |
| 5 | Push and open the pull request | Review | Yes, if you want it reviewed |

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

## 4. Decide what to do about the red baseline

**This is the one item with a real deadline, and it is not caused by this
branch.**

The suite on the current working tree fails: **3067 tests, 1114 failures,
123 errors**, measured before any change on this branch. Separately, the
committed tree at `d8cb9bb` **cannot run tests at all**:

```
NodeNotFoundError: Migration league.0007_alter_evidence_file dependencies
reference nonexistent parent node ('league', '0006_company_day_change_pct_…')
```

`league/migrations/0006_…` is **untracked** while `0007` is committed and
depends on it. Anyone cloning this repository gets a tree that cannot
migrate. CI on `main` is green only because `main` predates the commit that
introduced the dependency.

**Two things to decide:**

1. **Commit `league/migrations/0006_…`** (and the other untracked migrations)
   so the committed tree is self-consistent. This is a normal `git add`, not
   a destructive change — but it is your call, since it is your in-flight
   work, and I did not stage files that are not mine.
2. **Triage the 1237 failing tests** before the `django.yml` "Run tests" step
   can mean anything. That workflow is blocking on `main`.

Not doing this is a choice too — but with the suite red, no future change can
be shown to be safe by running it.

---

## 5. Push the branch and open a pull request

Not done autonomously: pushing publishes work to a shared remote, and the
mission scope was to prepare the branch, not to publish it.

```bash
git push -u origin chore/ecoiq-ai-toolkit
gh pr create --base main --head chore/ecoiq-ai-toolkit \
  --title "chore: audited AI toolkit — third-party skills, Excel MCP boundary, context policy"
```

**Do not merge automatically.** Note that PR CI will run `manage.py test`,
which is red for the pre-existing reasons in item 4.
