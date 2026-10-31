# AI tooling

Third-party Claude Code skills and MCP servers installed for EcoIQ: what is
here, what was refused, and where the boundaries are.

This sits **beside**, not above, the two existing layers:

- [`docs/AI-SKILL-ROUTER.md`](../AI-SKILL-ROUTER.md) — design / frontend /
  motion routing
- [`.claude/skills/ecoiq-engineering-os/SKILL.md`](../../.claude/skills/ecoiq-engineering-os/SKILL.md)
  — EcoIQ domain and governance routing

## The documents

| File | Read it when |
|---|---|
| [THIRD_PARTY_SKILLS_AUDIT.md](THIRD_PARTY_SKILLS_AUDIT.md) | Adopting, re-pinning or questioning a third-party component |
| [SECURITY_BOUNDARIES.md](SECURITY_BOUNDARIES.md) | Before using any installed skill or MCP server |
| [MCP_SETUP.md](MCP_SETUP.md) | Configuring or verifying an MCP server |
| [CONTEXT_POLICY.md](CONTEXT_POLICY.md) | Budgeting context, compressing, or handing off |
| [MANUAL_ACTIONS.md](MANUAL_ACTIONS.md) | Something needs a human — start here |
| [third-party-skills.lock.json](third-party-skills.lock.json) | You need the exact pinned SHA |

## What is installed

Nine third-party skills in `.claude/skills/`, each pinned to a reviewed
commit and carrying a generated `PROVENANCE.md`:

| Skill | From | Use for |
|---|---|---|
| `frontend-design` | anthropics/skills | Production UI: dashboards, evidence graphs, KPI and geographic interfaces |
| `canvas-design` | anthropics/skills | Reports, posters, stakeholder communication assets |
| `algorithmic-art` | anthropics/skills | Explanatory environmental visuals — **never** presented as measured evidence |
| `theme-factory` | anthropics/skills | Artifact theming. Extract EcoIQ's brand first; never restyle production |
| `web-artifacts-builder` | anthropics/skills | Isolated prototypes, calculators, scenario tools. Never a shipping path |
| `systematic-debugging` | obra/superpowers | Root cause before fixes: reproduce → evidence → cause → minimal fix → regression test → verify |
| `obsidian-markdown` | kepano/obsidian-skills | Authoring notes in `docs/knowledge/` |
| `context-optimization` | Agent-Skills-for-Context-Engineering | Token budgeting, retrieval scoping, cache strategy |
| `context-compression` | Agent-Skills-for-Context-Engineering | Long sessions, handoff summaries |

Payloads are gitignored (CLAUDE.md rule 14). Reproduce or verify them with:

```bash
bash scripts/ai-tooling/install-third-party-skills.sh
bash scripts/ai-tooling/install-third-party-skills.sh --check
```

One EcoIQ-owned skill was added and **is** tracked, like every `ecoiq-*`
skill: [`ecoiq-khalifah-engine`](../../.claude/skills/ecoiq-khalifah-engine/SKILL.md)
— the twelve-stage reasoning contract and the epistemic labelling rules.

MCP servers: `playwright` (active, pre-existing) and `excel` (configured, one
manual step away — [MCP_SETUP.md](MCP_SETUP.md)).

## What was refused, and why it matters

Six rejections, each for a specific reason rather than a general worry:

- **`superpowers` plugin** — its SessionStart hook injects an
  `<EXTREMELY_IMPORTANT>` block into *every* session. That is the opposite of
  progressive disclosure, and it competes with `CLAUDE.md` for authority. The
  one skill worth having was installed on its own.
- **`notebooklm-skill`** — bot-detection evasion via `patchright`, plaintext
  Google session cookies on disk, autonomous Chrome install. EcoIQ had
  already reached this conclusion in `ecoiq-research-ingest`; this pass
  confirmed it from source.
- **Excel MCP over stdio** — no filesystem confinement at all.
- **`defuddle`**, **`obsidian-cli`**, and 16 further context-engineering
  skills — scope, duplication, or unnecessary capability.

## Two findings worth knowing even if you never read further

1. **Excel MCP stdio is unconfined.** The README presents it as the normal
   local mode. In that mode the server accepts any absolute path and returns
   it unchanged — `.env`, `db.sqlite3`, `~/.ssh`. EcoIQ uses
   `streamable-http` only, which does enforce containment (correctly, and
   symlink-safe).
2. **Excel MCP binds `0.0.0.0` by default**, with no authentication. EcoIQ
   pins `FASTMCP_HOST=127.0.0.1`. Both mitigations live in
   `scripts/ai-tooling/start-excel-mcp.sh` and are proven by
   `scripts/ai-tooling/verify-excel-mcp-boundary.py`.

## Knowledge workspace

[`docs/knowledge/`](../knowledge/README.md) — a plain-Markdown workspace for
architecture decisions, Khalifah Engine documentation, KPI research,
regulations, pilots and customer discovery. Obsidian is optional and is not
part of the runtime. Five templates enforce the separation that matters:
**source → claim → evidence → interpretation → decision**.

## Scripts

| Script | Does |
|---|---|
| `scripts/ai-tooling/install-third-party-skills.sh` | Installs the nine skills at pinned SHAs. `--check` verifies |
| `scripts/ai-tooling/start-excel-mcp.sh` | Starts Excel MCP inside its boundary. `--check` verifies config |
| `scripts/ai-tooling/verify-excel-mcp-boundary.py` | 15 assertions on path confinement + a synthetic read/write |

None of them install anything globally, and none execute upstream code.
