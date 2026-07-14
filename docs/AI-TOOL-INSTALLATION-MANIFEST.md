# AI Tool Installation Manifest

Full per-capability classification for the 2026-07-13 installation pass. See
[AI-DEVELOPMENT-STACK.md](AI-DEVELOPMENT-STACK.md) for narrative detail and
[AI-SKILL-ROUTER.md](AI-SKILL-ROUTER.md) for routing of everything installed
or already present.

**Classification key:** A = already installed & verified · B = real,
installable, installed this pass · C = real, needs user auth/payment · D =
real but incompatible · E = duplicate of an already-installed tool · F =
could not verify as a real installable tool · G = security review failed.

**Environment constraint that shaped every "installed this pass" row:** no
`claude` CLI binary is reachable from this session's shell. Installation
used the documented file-based mechanisms (`.mcp.json` for MCP servers,
`.claude/skills/<name>/` for skills) instead of `claude mcp add` /
`/plugin install`.

**Update (2026-07-13, integration audit):** functional correctness is now
verified for both, per-item detail below.
- Playwright MCP: confirmed to actually start, launch a real headless
  Chromium, and successfully navigate + snapshot the live EcoIQ dev server
  (`http://127.0.0.1:8731/`) via a raw MCP stdio JSON-RPC handshake
  (initialize → tools/list → `browser_navigate` → `browser_snapshot`), run
  independently of the Claude Code harness. What's *not* yet true is Claude
  Code's own approval of the connection: `~/.claude.json` →
  `projects["/Users/work.tazabekovgmail.com/ecoiq-v1"].enabledMcpjsonServers`
  is `[]` and `disabledMcpjsonServers` is also `[]` — i.e. the "playwright"
  entry in `.mcp.json` is in the pending/unapproved state. Claude Code will
  show a one-time approval prompt for it on the next session start; no
  other action is needed.
- Skills (`frontend-design`, `canvas-design`, `algorithmic-art`): directory
  structure and `SKILL.md` YAML frontmatter (`name`, `description`) verified
  correct against the required format. Unlike MCP servers, the per-project
  config has no approval-gate field for skills (only `enabledMcpjsonServers`
  /`disabledMcpjsonServers`/`hasClaudeMdExternalIncludesApproved` exist, and
  none of those apply to skills) — project-level skills are auto-loaded at
  session start with no user action required. This could not be observed
  from inside the same live session (skills load at session start, and this
  session already started), so "will load next session" is inferred from
  config structure + the documented mechanism, not directly witnessed.

## Design / Frontend

| Requested | Class | Source | Installed version/commit | Scope | Verification | Auth needed | Notes |
|---|---|---|---|---|---|---|---|
| UI/UX Pro Max | A | `github.com/nextlevelbuilder/ui-ux-pro-max-skill` | v2.6.2, commit `3da52ff` | User | Present in `~/.claude/plugins/`, listed in this session's available skills | No | Provides `ui-ux-pro-max:ui-ux-pro-max`, `ui-styling`, `design-system`, `brand`, `banner-design`, `slides` |
| frontend-design | B | `github.com/anthropics/skills` (official, Apache-2.0) | HEAD at fetch time, 2026-07-13 | Project-local (`.claude/skills/frontend-design/`) | File + license present, no scripts; live-discovery **not yet confirmed** (needs session restart) | No | Corrects prior audit's "not found" — search gap, not a naming gap |
| design-taste-frontend | F→(real 3rd-party match, not installed) | `github.com/Leonxlnx/taste-skill` | — | — | — | No | Real repo, matches "design-taste" closely; needs a full 3rd-party security review before adoption — out of scope for this pass. `ui-ux-pro-max:brand` covers the practical need meanwhile |
| redesign-existing-projects | F | — | — | — | Searched `anthropics/skills`, both installed marketplaces, general web search | — | No match found under this name anywhere |
| image-to-code | F | — | — | — | Same as above | — | No match found under this name |
| brandkit | A (+ real 3rd-party alt not installed) | `ui-ux-pro-max:brand`, `banner-design` (installed) / `Leonxlnx/taste-skill` bundles a `brandkit` sub-skill (not installed, see design-taste-frontend row) | — | User | Already present | No | |
| figma-implement | F (for Claude Code) | `github.com/openai/skills` has `figma-implement-design` | — | — | Exists, but is OpenAI's skill ecosystem/format — compatibility with Claude Code not confirmed | — | Not installed without a compatibility check |
| impressable | F | — | — | — | Searched, no match | — | No real product/repo found under this name |
| theme-factory | F | Referenced only as part of a third-party bundle (`mejba13/claude-skills-collection`) in secondary sources, not independently confirmed | — | — | Low-confidence secondary mention only | — | Not installed — confidence too low to treat as verified |
| designer-skills | F | — | — | — | Searched, no match | — | Generic term, no specific product found |

## Motion / Animation

| Requested | Class | Source | Installed version | Scope | Verification | Auth | Notes |
|---|---|---|---|---|---|---|---|
| animate | A | `animation-components` plugin family (Magic UI + React Bits, anime.js, Lottie, React Spring, AOS scroll-reveal) | v1.0.0, commit `1da73fe` | User | Present, listed in available skills | No | `claude-design-skillstack` marketplace |
| design-motion | A | `motion-framer`, `core-3d-animation:gsap-scrolltrigger` (installed) + EcoIQ's own locked `motion-style-guide.md` (wins disputes) | v1.0.0 | User | Present | No | |
| design-motion-principles | A (as methodology) | EcoIQ's `docs/motion-style-guide.md` + `motion-library-v1.md` (LOCKED) | — | Project | Already the enforced source of truth | No | Not a separate installable package by design |
| Claude Remotion tooling | A | `frontend/remotion/` (project's own Remotion setup) | `@remotion/cli` 4.0.190, `remotion` 4.0.190 | Project | `package.json` confirmed, real working scripts (`studio`, `render:*`) | No | Already real, not a placeholder |
| Remotion Superpowers | F | — | — | — | No skill/repo found under this exact name | — | Remotion itself already covered above |
| Blender Motion | F | — | — | — | No corresponding Claude-compatible product found | — | Blender desktop app itself not installed; out of scope to auto-install desktop software |
| After Effects Motion | F | — | — | — | No corresponding Claude-compatible product found | — | Same — AE is commercial desktop software, not auto-installed |

## Creative / Visual

| Requested | Class | Source | Installed version | Scope | Verification | Auth | Notes |
|---|---|---|---|---|---|---|---|
| canvas-design | B | `github.com/anthropics/skills` (official) | HEAD at fetch, 2026-07-13 | Project-local (`.claude/skills/canvas-design/`) | File + license + bundled fonts present, no scripts; live-discovery not yet confirmed | No | Corrects prior "not found" |
| algorithmic-art | B | `github.com/anthropics/skills` (official) | HEAD at fetch, 2026-07-13 | Project-local (`.claude/skills/algorithmic-art/`) | File + license present, one JS template inspected (no eval/exec/network); live-discovery not yet confirmed | No | Corrects prior "not found" |
| Nano Banana related Claude tooling | F (as named) | — | — | — | No dedicated skill found; a generic metered image/video MCP exists in this environment but wasn't requested by name | — | Not adopted — would consume paid credits without explicit consent |

## Browser / Testing

| Requested | Class | Source | Installed version | Scope | Verification | Auth | Notes |
|---|---|---|---|---|---|---|---|
| Playwright MCP | B | `@playwright/mcp`, npm, `github.com/microsoft/playwright-mcp` (official Microsoft) | server reports `1.62.0-alpha` internally (npm package pinned `0.0.78`, resolved via `@latest`) | Project (`.mcp.json`) | **Functionally verified live**: raw MCP stdio handshake succeeded (`initialize`, 24 tools listed including `browser_navigate`/`browser_snapshot`), `browser_navigate` to `http://127.0.0.1:8731/` returned the real EcoIQ homepage (title "EcoIQ — Climate Intelligence Platform \| UK ESG Scoring"), `browser_snapshot` returned a full 44KB accessibility tree of the real page. Claude Code's own approval of the `.mcp.json` entry is still pending (`enabledMcpjsonServers: []` in project config) — one-time prompt on next session start | No (one-time connection-approval prompt only, not credentials) | Corrects prior pass's "duplicative" skip — it's complementary to the Browser pane, not a duplicate. Config verified to exactly match `claude mcp add playwright npx @playwright/mcp@latest` output |

## Figma

| Requested | Class | Source | Installed version | Scope | Verification | Auth | Notes |
|---|---|---|---|---|---|---|---|
| Figma MCP | C | Figma's official Dev Mode MCP Server (runs inside Figma desktop app, local endpoint `http://127.0.0.1:3845/mcp`) | — | — | Figma desktop app confirmed **not installed** (`/Applications` has no Figma app); port 3845 confirmed not listening | **Yes** — requires: (1) Figma desktop app installed, (2) a Professional/Organization/Enterprise Figma plan with a Dev or Full seat, (3) enabling "Dev Mode MCP Server" in Figma preferences | See exact remaining steps below |

**Figma — what's required and where:** install the Figma desktop app (not
auto-installed here — it's third-party desktop software outside Claude
Code's scope), confirm the Figma account has a paid plan with Dev Mode
access, then in the Figma desktop app go to **Preferences → Enable Dev Mode
MCP Server**. Once that's on, add this to `.mcp.json`:
```json
"figma": { "url": "http://127.0.0.1:3845/mcp" }
```
Nothing was added to `.mcp.json` for Figma yet, since pointing at an
endpoint that doesn't exist would just fail on every session start.

## AI Product Design

| Requested | Class | Notes |
|---|---|---|
| generative-ui | F | Not an installable Claude Code skill. A same-named but unrelated community repo (`Anilturaga/Generative-UI`, an "Imagine with Claude" implementation) exists but is a standalone app, not a skill/package for this use case. Applied as methodology per `AI-QUALITY-GATES.md` §6 |
| progressive-disclosure | F | This is Anthropic's own documented *architecture principle* for how Skills load (metadata → full instructions → resources) — not itself an installable tool |
| feedback-loops | F | No matching installable product found |
| frustration-checks | F | No matching installable product found |
| turn-repair | F | No matching installable product found |

## Prompt Engineering

| Requested | Class | Notes |
|---|---|---|
| system-structure | F | No matching installable product found |
| persona-architecture | F | No matching installable product found |
| tone-calibration | F | No matching installable product found |
| emotional-design | F | No matching installable product found |
| template-design | F | No matching installable product found |
| few-shot-patterns | F | No matching installable product found |
| constraint-specification | F | No matching installable product found |

## AI Trust / Safety / Quality

| Requested | Class | Notes |
|---|---|---|
| guardrails | F (generic term) | Real *specific* guardrail repos exist (e.g. `dwarvesf/claude-guardrails`, a PostToolUse prompt-injection scanner) but "guardrails" as requested isn't a single named tool. Not installed without a specific target and explicit ask |
| guardrail-design | F | No installable product under this exact name |
| trust-calibration | F | No installable product under this exact name |
| transparency-patterns | F | No installable product under this exact name |
| quality-rubrics | F | No installable product under this exact name |
| task-decomposition | F | No installable product under this exact name |
| handoff-protocols | F | A same-concept but differently-scoped `handoff` skill exists (`ykdojo/claude-code-tips` — compresses a session into a handoff doc for the *next Claude Code session*, not an agent-trust protocol). Not installed — different capability than requested |

## Context / Agent Architecture

| Requested | Class | Notes |
|---|---|---|
| context-window-design | F | No installable product found |
| conversation-patterns | F | No installable product found |
| token-budgets | F | No installable product found |

All items in this section remain encoded as applied methodology in
`AI-SKILL-ROUTER.md` §"What methodology, not a package means" and
`AI-QUALITY-GATES.md` §6–7, per instruction not to silently convert an
unverifiable tool into a fake installation.

## Optional External Integrations

| Requested | Class | Source | Auth needed | Notes |
|---|---|---|---|---|
| Composio MCP | C | `composio.dev` — real integration platform with an MCP offering | **Yes** — requires a Composio account + API key | Not installed. Prohibited to create the account autonomously (account creation is a prohibited autonomous action regardless of tool merit). User can add it via a session where the `claude` CLI is available, or by hand-adding a `.mcp.json` entry once they have an API key |

---

## Summary counts

| Class | Count |
|---|---|
| A — already installed & verified | 7 (ui-ux-pro-max family, animation-components, animejs, motion-framer, core-3d-animation family, substance-3d-texturing, web3d-integration-patterns, Remotion, framer-motion) |
| B — installed this pass | 4 (Playwright MCP, frontend-design, canvas-design, algorithmic-art) |
| C — needs user auth | 2 (Figma MCP, Composio MCP) |
| D — incompatible | 0 |
| E — duplicate | 0 |
| F — could not verify as real | ~24 (see tables above) |
| G — security rejected | 0 |
