# EcoIQ AI Skill Router

How to pick tools for a task without invoking everything. See
[AI-DEVELOPMENT-STACK.md](AI-DEVELOPMENT-STACK.md) for what's installed and
why, and [AI-QUALITY-GATES.md](AI-QUALITY-GATES.md) for what "done" means.

**Rule of thumb: use the minimum chain below, in order, then stop.** Skills
are specialists consulted for their layer, not a checklist to exhaust. Level
1 (EcoIQ's own tokens/motion docs/architecture) always wins a disagreement
with any generic skill's default opinion.

## The hierarchy (Levels 1–7)

1. **EcoIQ source of truth** — `frontend/app/src/design/tokens.ts`,
   `system.css`, `docs/motion-library-v1.md` (LOCKED),
   `docs/motion-style-guide.md`, existing component/architecture patterns,
   accessibility requirements already in the codebase.
2. **UX & structure** — `ui-ux-pro-max:ui-ux-pro-max` (information
   architecture, responsive behavior, component hierarchy, usability).
3. **Visual quality** — `ui-ux-pro-max:ui-styling` / `ui-ux-pro-max:design-system`
   (visual refinement, composition, premium appearance) — applied *within*
   EcoIQ's existing token values, never replacing them.
4. **Motion** — EcoIQ's own `motion-style-guide.md` rules first; the
   `animation-components` family, `animejs`, `motion-framer`, or
   `core-3d-animation:gsap-scrolltrigger` for implementation, preferring
   `transform`/`opacity`, respecting `reducedMotion="user"`.
5. **Verification** — Browser pane tools (`mcp__Claude_Browser__*`):
   desktop/tablet/mobile viewports, console errors, network errors,
   interaction checks, reduced-motion check, layout-shift/overflow check.
6. **AI product behavior** — applied as documented methodology (see below),
   not an installed package: generative UI, progressive disclosure, feedback
   loops, conversation patterns, context-window design.
7. **Trust & safety** — applied as documented methodology (see
   AI-QUALITY-GATES.md §7): guardrails, trust calibration, transparency,
   constraint specification, quality rubrics, task decomposition, handoff
   protocols.

## Task → tool routing

**Frontend implementation**
→ EcoIQ tokens/architecture (L1) → `ui-ux-pro-max:ui-ux-pro-max` (L2) →
`ui-ux-pro-max:ui-styling` (L3) → Browser pane verification (L5)

**Existing page redesign**
→ Read the existing page/tokens first (L1) → `ui-ux-pro-max:ui-ux-pro-max`
(L2) → `ui-ux-pro-max:ui-styling` (L3) → Browser pane verification (L5)
*(No dedicated "redesign-existing-projects" skill exists — this chain is the
substitute. See AI-DEVELOPMENT-STACK.md §4.)*

**Screenshot / reference implementation**
→ Read the reference image directly and describe/implement by hand,
matching EcoIQ tokens (L1) → `ui-ux-pro-max:ui-ux-pro-max` (L2) → Browser
pane verification (L5) *(no dedicated "image-to-code" skill exists; this is
a manual-but-token-constrained substitute)*

**Animation task**
→ `docs/motion-style-guide.md` rules (L1/L4) → `animation-components` /
`animejs` / `motion-framer` for implementation → Browser pane: verify
reduced-motion honored, no layout thrash, animations bounded (L5)

**AI assistant feature (e.g. chat, agent UI)**
→ Progressive disclosure + conversation-pattern principles (L6, methodology
— see AI-QUALITY-GATES.md §6) → trust-calibration + guardrail principles
(L7) → Browser pane verification (L5)

**Investor dashboard**
→ `ui-ux-pro-max:ui-ux-pro-max` (L2) → generative-UI / progressive-disclosure
principles (L6) → transparency principles (L7) → Browser pane verification
(L5)

**Capital Guardian**
→ generative-UI principles (L6) → transparency + trust-calibration +
guardrail + quality-rubric principles (L7) → Browser pane verification (L5)

**Mining Digital Twin**
→ `ui-ux-pro-max:ui-ux-pro-max` (L2) → generative-UI principles (L6) →
animation tools per the Animation task chain above (L4) → Browser pane
verification (L5)

**Marketing visual**
→ `ui-ux-pro-max:brand` (brandkit equivalent) → `ui-ux-pro-max:ui-styling`
(canvas-design equivalent) → *(no algorithmic-art skill exists; use direct
SVG/canvas code if generative art is needed)*

## What "methodology, not a package" means in practice

For L6/L7 items with no installed skill (generative-ui, progressive-
disclosure, feedback-loops, conversation-patterns, context-window-design,
guardrail-design, trust-calibration, transparency-patterns, constraint-
specification, quality rubrics, task decomposition, handoff protocols):
apply them as design judgment while implementing, checked against the
concrete checklist in `AI-QUALITY-GATES.md` §6–7, rather than invoking a
tool call. If a real installable skill by one of these names later appears
in the plugin registry, audit it per `AI-DEVELOPMENT-STACK.md` §2 before
adopting it — don't assume the name implies the same behavior described
here.
