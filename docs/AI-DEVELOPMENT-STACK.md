# EcoIQ AI-Native Development Stack

Audit and installation record for the AI-native design / frontend / motion /
browser-testing / creative-production / prompt-engineering / AI-safety stack
requested in July 2026. See also [AI-SKILL-ROUTER.md](AI-SKILL-ROUTER.md) and
[AI-QUALITY-GATES.md](AI-QUALITY-GATES.md).

**Governing finding: EcoIQ already had most of this stack.** The audit below
is the reason almost nothing new was installed — Phase 1 of the request
("do not reinstall or duplicate existing tools") ruled most of the requested
items out before Phase 2 security review even applied.

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

## 2. Installed / configured this pass

| Item | Purpose | Verification |
|---|---|---|
| [`docs/AI-SKILL-ROUTER.md`](AI-SKILL-ROUTER.md) | Task → tool routing so skills don't compete | N/A (doc) |
| [`docs/AI-QUALITY-GATES.md`](AI-QUALITY-GATES.md) | Checklist gating frontend/AI changes | N/A (doc) |
| Root `CLAUDE.md` | Permanent standing instructions | N/A (doc) |

No npm packages, pip packages, MCP servers, or Claude Code plugins were
installed. See §4 for why.

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
| Browser testing / "Playwright MCP" | Built-in Browser pane tools (`mcp__Claude_Browser__*`): navigate, click/type, accessibility-tree read, console/network inspection, viewport resize for responsive + dark-mode checks, screenshots. Functionally equivalent to a Playwright MCP server for this environment. |
| Data visualization | `dataviz` skill |
| Artifact/report generation | `artifact-design`, `anthropic-skills:web-artifacts-builder` |

## 4. Evaluated and explicitly skipped

| Tool requested | Reason skipped |
|---|---|
| Playwright MCP (`@playwright/mcp`, real Microsoft package, verified to exist) | **Duplicative.** The Browser pane already provides equivalent capability (navigation, DOM/a11y tree, console, network, screenshots, viewport resize) with no install and no added supply-chain surface. Adding a second, redundant browser-automation server would violate the explicit "do not duplicate existing functionality" instruction. If a future need arises for automation *outside* this harness (e.g. a CI pipeline), add `@playwright/mcp` there specifically, not here. |
| design-taste-frontend, redesign-existing-projects, image-to-code, canvas-design, algorithmic-art (as named, distinct skills) | **Not found.** No installed Claude Code skill, marketplace plugin, or npm/pip package with these exact names exists in this environment or the connector registry searched. Per "do not invent commands or repository URLs," nothing was installed under these names. The overlapping real capability (visual refinement, screenshot-to-code, canvas rendering) is already served by `ui-ux-pro-max:*` and general-purpose coding, so the gap is small. |
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

- **No new third-party code was introduced**, so no new supply-chain,
  postinstall-script, or exfiltration surface was added by this task.
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
