# EcoIQ AI-Native Development Stack

Audit and installation record for the AI-native design / frontend / motion /
browser-testing / creative-production / prompt-engineering / AI-safety stack.
Two passes: an initial audit (July 2026, documentation-only, superseded
below) and an installation pass (2026-07-13) that actually installed the
real, verified, compatible tools rather than only documenting them. See also
[AI-SKILL-ROUTER.md](AI-SKILL-ROUTER.md) and
[AI-QUALITY-GATES.md](AI-QUALITY-GATES.md).

**Governing finding, revised 2026-07-13:** most of the requested inventory
still isn't real (see §4/§9), and EcoIQ already covered a large share of what
*is* real. But three genuinely real, installable items had been wrongly
skipped in the prior pass (Playwright MCP as "duplicative," and three
official Anthropic skills as "not found" — a search-thoroughness gap, not a
naming gap). Those are corrected in §2. Full classification per item is in
[`AI-TOOL-INSTALLATION-MANIFEST.md`](AI-TOOL-INSTALLATION-MANIFEST.md).

---

## 1. What EcoIQ already has (Level 1 source of truth)

| Capability | Where it lives | Notes |
|---|---|---|
| Design tokens (color, radius, space, font, easing, duration, shadows) | [`frontend/app/src/design/tokens.ts`](../frontend/app/src/design/tokens.ts), `system.css` | Explicitly documented as "the single source of truth for the dark institutional design system." Do not fork or replace. |
| Motion system | [`docs/motion-library-v1.md`](motion-library-v1.md) (LOCKED) + [`motion-style-guide.md`](motion-style-guide.md), `frontend/app/src/motion/presets.ts`, `MotionProvider.tsx` | Framer Motion via `LazyMotion`/`domAnimation`. `MotionConfig reducedMotion="user"` already wires OS-level reduced-motion for every animation. Rules for when/how long animations run are already written down and locked. |
| React islands architecture | `frontend/app/` (Vite + TS, build-time only, output committed to `static/dist/`) | Django remains the runtime, auth boundary, and page shell. |
| Video authoring | `frontend/remotion/` (Remotion 4.0.190) | Offline/local only, never a Render runtime dependency. This already covers the "Remotion Superpowers" request. |
| Backend | Django 5.2, DRF, Anthropic SDK 0.104, WeasyPrint (PDF), Celery/Redis (optional) | Synchronous architecture, `python manage.py runserver`. |
| Dev server launch | `.claude/launch.json` → `ecoiq` config, port 8731 | Already wired for `preview_start`. |

Nothing in this section was touched. It remains Level 1–4 of the hierarchy.

## 2. Installed / configured this pass (2026-07-13)

| Item | Source | Scope | Purpose | Verification |
|---|---|---|---|---|
| Playwright MCP | `@playwright/mcp` (npm, official, `github.com/microsoft/playwright-mcp`, Microsoft-maintained, Apache-2.0) | Project (`.mcp.json`, gitignored? **no** — tracked-eligible, currently uncommitted) | Scripted/repeatable browser automation, complementary to the interactive Browser pane | `npm view` confirmed publisher (Microsoft team members) and clean `scripts` (no pre/postinstall). `npx -y @playwright/mcp@latest --version` executed successfully → `Version 0.0.78`, matching the published npm version. **Not yet confirmed discovered inside a live Claude Code session** — no `claude` CLI was reachable from this shell to reload; Claude Code will prompt for one-time connection approval on next session start because `.mcp.json` was added outside an interactive session. |
| `frontend-design` skill | `github.com/anthropics/skills` (official, Apache-2.0) | Project-local (`.claude/skills/frontend-design/`, gitignored, this machine only) | General frontend implementation guidance | File present, license present, no install scripts. Sparse-cloned, content-inspected (`file`, grep for `eval`/`exec`/network calls) before copying. Not live-session-verified (see limitation above). |
| `canvas-design` skill | `github.com/anthropics/skills` (official, Apache-2.0) | Project-local, gitignored | Static visual art generation (closest real match to the requested "canvas-design") | Same as above. |
| `algorithmic-art` skill | `github.com/anthropics/skills` (official, Apache-2.0) | Project-local, gitignored | Generative/procedural art (closest real match to the requested "algorithmic-art") | Same as above. |
| [`docs/AI-SKILL-ROUTER.md`](AI-SKILL-ROUTER.md) (updated) | — | Doc | Routing for the newly installed tools | N/A (doc) |
| Root `CLAUDE.md` (updated) | — | Doc | Two new standing rules on tool-claim honesty and minimal toolchain use | N/A (doc) |
| [`AI-TOOL-INSTALLATION-MANIFEST.md`](AI-TOOL-INSTALLATION-MANIFEST.md) (new) | — | Doc | Full per-capability classification (A–G) for the entire requested list | N/A (doc) |

**Known limitation of this pass:** this session has no `claude` CLI binary on
`PATH` (`which claude` → not found) — it's running inside the harness, not a
standalone install. MCP servers and skills were registered via their
documented file-based mechanisms (`.mcp.json`, `.claude/skills/`) rather
than `claude mcp add` / `/plugin install`.

**Update (2026-07-13 integration audit) — resolved as far as possible without
a session restart:**
- Playwright MCP is now **functionally proven**, not just present on disk: a
  direct MCP stdio JSON-RPC probe (independent of the Claude Code harness)
  spawned the server, listed its 24 tools, navigated it to the live EcoIQ
  dev server, and pulled a real accessibility snapshot back. The one thing
  that genuinely still requires the next session is Claude Code's own
  one-time approval of the `.mcp.json` connection — confirmed pending via
  `~/.claude.json`'s `enabledMcpjsonServers: []` for this project (not
  approved, but also not rejected).
- The three vendored skills have correct `SKILL.md` frontmatter (`name` +
  `description`) and directory structure. There is no approval-gate field
  for skills in the project config (unlike MCP servers), so — per the
  documented skill-loading mechanism — they should be auto-discovered at
  the next session start with no user action. This is inferred from config
  structure and the documented mechanism, since a skill's own discovery
  can only be witnessed at session start, and this session already started
  before they were added.

## 3. Already available, no action needed

These already exist as installed Claude Code plugins/skills (global to this
environment, not per-repo) and cover the requested capability without any
new install:

| Requested capability | Covered by |
|---|---|
| UI/UX Pro Max | `ui-ux-pro-max:ui-ux-pro-max`, `ui-ux-pro-max:ui-styling`, `ui-ux-pro-max:design-system` |
| brandkit | `ui-ux-pro-max:brand`, `ui-ux-pro-max:banner-design` |
| canvas-design (partial) | `ui-ux-pro-max:ui-styling` ("canvas-based visual designs") |
| animate | `animation-components` plugin family (animejs, react-spring-physics, lottie, scroll-reveal), `animejs`, `motion-framer` |
| design-motion-principles | `core-3d-animation:gsap-scrolltrigger`, `motion-framer`, plus EcoIQ's own locked `docs/motion-style-guide.md` (which takes precedence — it's project-specific, the plugins are generic) |
| Browser testing (interactive) | Built-in Browser pane tools (`mcp__Claude_Browser__*`): navigate, click/type, accessibility-tree read, console/network inspection, viewport resize, screenshots. **Playwright MCP is now also installed (§2)** for the scripted/repeatable case — the two are complementary, not duplicates; see the corrected reasoning in §4. |
| Data visualization | `dataviz` skill |
| Artifact/report generation | `artifact-design`, `anthropic-skills:web-artifacts-builder` |

## 4. Evaluated and explicitly skipped (revised 2026-07-13)

**Correction to the prior pass:** Playwright MCP and three of the "not
found" skills below were re-evaluated and are now installed (§2). The prior
pass's "duplicative" reasoning for Playwright MCP didn't hold up — a
scriptable, re-runnable MCP server and an interactively-driven Browser pane
serve different verification needs — and the prior "not found" conclusion
for `frontend-design`/`canvas-design`/`algorithmic-art` was a search gap:
they exist verbatim in the official `github.com/anthropics/skills` repo.

| Tool requested | Reason skipped |
|---|---|
| design-taste-frontend, brandkit (as a *distinct* dedicated package beyond `ui-ux-pro-max:brand`) | **Real third-party match found, not installed.** `github.com/Leonxlnx/taste-skill` ("Taste-Skill") is a real, actively-referenced third-party skill collection that includes a `brandkit` sub-skill and matches "design-taste" closely. Not vendored this pass — it's third-party (not Anthropic-official) and needs a full repo-history/maintainer security review before adoption, which was out of scope for the "quick verification pass" this install pass was scoped to. `ui-ux-pro-max:brand` already covers the practical need. Candidate for a follow-up if a dedicated taste/brand skill is specifically wanted. |
| redesign-existing-projects, image-to-code, impressable, designer-skills | **Still not found** under these names in the official `anthropics/skills` repo, the two installed marketplaces, or the searches run this pass. `figma-implement` exists but only in `github.com/openai/skills` (OpenAI's skill format/ecosystem, not confirmed compatible with Claude Code) — not installed without a compatibility check. |
| generative-ui, progressive-disclosure, feedback-loops, conversation-patterns, context-window-design | **Not installable products.** These are interaction-design *principles*, not packages. No skill/plugin by these names exists to inspect or install. They are instead written into [AI-SKILL-ROUTER.md](AI-SKILL-ROUTER.md) and [AI-QUALITY-GATES.md](AI-QUALITY-GATES.md) as applied methodology for AI-feature and dashboard work. |
| guardrail-design, trust-calibration, transparency-patterns, constraint-specification, quality rubrics, task decomposition, handoff protocols | **Not installable products**, same reasoning as above — encoded as a checklist in AI-QUALITY-GATES.md §7 (AI Trust & Safety) rather than as software. |
| Figma MCP (`plugin:product-management:figma`) | **Exists but requires OAuth.** This session is non-interactive and cannot complete the connector authorization flow. Skip until the user authorizes it via claude.ai connector settings; then it becomes available with no further installation. |
| Remotion Superpowers (as a distinct skill) | **No such skill found.** Remotion itself is already installed and working in `frontend/remotion/` — the underlying capability already exists; only a specific named "Superpowers" skill package was not found. |
| Blender Motion, After Effects Motion | **No corresponding product found** in the installed plugin list or connector registry. Not invented. |
| Nano Banana-related tooling | **No dedicated skill found.** A generic paid image/video/audio generation MCP is available in this environment (Higgsfield-backed) but is a metered third-party service — not adopted automatically since it wasn't asked for by name and would consume the user's credits without consent. |
| Composio MCP | **Requires external account creation**, which is a prohibited autonomous action regardless of the tool's merit. Skip; the user can add it via `claude mcp add` in an interactive session if wanted. |

## 5. Failed installations

None. Nothing in §4 reached an install attempt — each was ruled out at the
audit/security-inspection stage before any install command was run, so there
is nothing to report as a runtime failure.

## 6. Security findings

- **This pass (2026-07-13) did introduce new third-party code**, reviewed
  before adoption: `@playwright/mcp` (npm, Microsoft-maintained team members
  as listed publishers, `microsoft/playwright-mcp` repo, Apache-2.0, `npm
  view @playwright/mcp scripts` shows no `preinstall`/`postinstall`/`install`
  hooks) and three official Anthropic skills (`frontend-design`,
  `canvas-design`, `algorithmic-art` from `github.com/anthropics/skills`,
  Apache-2.0, content-inspected for `eval`/`exec`/network calls before
  copying — none found beyond a benign regex `.exec()` call in one JS
  template). `@playwright/mcp` runs via `npx` (fetches/executes on demand,
  not vendored into the repo) and, when actually used, launches a real
  Chromium/browser process — that's inherent to what a browser-automation
  MCP server does, not a red flag specific to this package.
- Nothing else in this task introduced new third-party code — the remaining
  request items were either already-installed (§3), correctly not real (§4,
  §9 in the manifest), or blocked on user authentication (Figma, Composio —
  not installed, no code fetched).
- `.claude/` is correctly listed in `.gitignore` (line 2) and confirmed via
  `git ls-files .claude/` to be untracked — `settings.local.json` (a Bash
  permission allowlist, no secrets) is not committed.
- `.env` is gitignored and untracked; only `.env.example` (placeholder keys,
  no values) is tracked. Directly verified with `git grep -nE
  'sk-ant-api[0-9A-Za-z_-]{20,}'` across all tracked files: zero matches.
- No `package.json` install scripts were added or modified, so there is
  nothing new to audit for malicious `postinstall`/`preinstall` hooks.

## 7. Conflicts avoided

- Did **not** introduce Tailwind, shadcn/ui, or any second component/token
  system — EcoIQ's custom `design/tokens.ts` + `system.css` remains the only
  design system.
- **Pre-existing conflict found, not introduced by this task:** 10 templates
  (`templates/landing.html`, `platform.html`, `ethical_governance.html`,
  `governance_principles.html`, `registration/login.html`, and 5 templates
  under `templates/leads/`) load `cdn.tailwindcss.com` directly, which is
  both a browser-console warning in production and exactly the "second
  competing design system" CLAUDE.md rule 7 now prohibits going forward.
  Not fixed here — out of scope for an environment-tooling task and touches
  10 live templates — but flagged as a follow-up (see chip / `task_2f5e14a8`
  equivalent). New work should not add to this list.
- Did **not** add a second animation abstraction — Framer Motion via
  `MotionProvider` stays the only motion runtime; the installed animation
  plugins (GSAP, anime.js, etc.) are available for one-off needs but must
  read EcoIQ's tokens/durations/easing rather than inventing their own.
- Did **not** add a redundant browser-automation MCP server alongside the
  built-in Browser pane.
- Did **not** touch `legacy_safe/` (the hackathon AI-agents module) or any
  product code — this task is dev-environment tooling only.

## 8. Responsibilities (who owns what — see AI-SKILL-ROUTER.md for routing)

See the Level 1–7 hierarchy in root `CLAUDE.md` and the routing table in
`AI-SKILL-ROUTER.md`. In one line: EcoIQ's own tokens/motion docs are always
the source of truth; installed skills are specialists invoked per-task, not
competing authorities; the Browser pane is the final verification gate for
every meaningful frontend change.
