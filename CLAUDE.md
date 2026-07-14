# CLAUDE.md — EcoIQ

## What EcoIQ is

Django 5.2 monolith (server-rendered templates, WhiteNoise static,
synchronous — `python manage.py runserver`, no workers/containers required
to run it). Anthropic Claude + WeasyPrint power AI-generated audit reports.
Two build-time-only Node layers, never runtime dependencies: `frontend/app`
(Vite + React "islands" that hydrate into Django templates) and
`frontend/remotion` (offline video authoring). Dev server: `.claude/launch.json`
→ `ecoiq`, port 8731.

## AI-native dev stack

This repo has an AI-native design/frontend/motion/verification stack
documented in three files — **read them before doing frontend or AI-feature
work**:

- [`docs/AI-SKILL-ROUTER.md`](docs/AI-SKILL-ROUTER.md) — which tools/skills
  to use for which task, and in what order.
- [`docs/AI-QUALITY-GATES.md`](docs/AI-QUALITY-GATES.md) — the checklist a
  change must pass before it's "done."
- [`docs/AI-DEVELOPMENT-STACK.md`](docs/AI-DEVELOPMENT-STACK.md) — what's
  installed, what was skipped and why, security findings.

## Standing rules

1. **EcoIQ is the source of truth.** `frontend/app/src/design/tokens.ts`,
   `system.css`, and the locked `docs/motion-library-v1.md` /
   `motion-style-guide.md` define color, spacing, typography, and motion.
   No installed skill's generic opinion overrides them.
2. **Skills are specialists, not competing authorities.** Each has a layer
   in the hierarchy (see AI-SKILL-ROUTER.md). They advise within their
   layer; they don't get to redesign a layer above them.
3. **Use only the minimum relevant skills for a task.** Follow the routing
   table — don't invoke every skill "just in case."
4. **Never invoke every skill for every task.** If a task doesn't touch
   motion, don't touch the motion skills.
5. **Follow `AI-SKILL-ROUTER.md`** for task → tool routing.
6. **Preserve existing visual identity unless explicitly asked to
   redesign.** Default to matching what's already there.
7. **Never introduce a second competing design system** (no Tailwind,
   shadcn, or parallel token set alongside `tokens.ts`/`system.css`). Note:
   10 templates already load Tailwind via CDN as a pre-existing exception
   (see `AI-DEVELOPMENT-STACK.md` §7) — don't extend that pattern to new
   pages, and prefer migrating those 10 off it when touched.
8. **Never replace working architecture unnecessarily** — the Django +
   islands + Remotion split is deliberate (see each directory's README);
   don't "simplify" it away.
9. **Never sacrifice accessibility for visual effects.** Keyboard nav,
   focus-visible states, and reduced-motion support are non-negotiable —
   see `AI-QUALITY-GATES.md` §4.
10. **Never sacrifice performance for animation.** Prefer `transform`/
    `opacity`; respect the duration/looping bounds in
    `motion-style-guide.md`.
11. **Every meaningful frontend change requires browser verification**
    before being reported as done — use the Browser pane tools
    (`mcp__Claude_Browser__*`) for interactive/manual checks. A project-level
    Playwright MCP server (`.mcp.json`, `@playwright/mcp`) is also available
    for scripted/repeatable browser verification — see
    `AI-DEVELOPMENT-STACK.md` §2–3 for status (requires one-time connection
    approval since it was added outside an interactive session).
12. **Fix regressions found during verification** if the fix doesn't change
    intended product behavior — don't leave a known-broken state because it
    wasn't the original ask.
13. **Prefer evidence-based verification over claiming success.** Don't
    report tests, lint, build, or a UI change as working without having run
    it this session. Type checking and test suites verify code correctness,
    not feature correctness — if a UI change can't be checked in a browser,
    say so explicitly rather than asserting it works.
14. **Never expose secrets, API keys, or credentials** — in prompts, logs,
    commits, or client-visible payloads. `.env` and `.claude/` are
    gitignored; keep it that way.
15. **Ask before making destructive infrastructure changes** — deleting
    data, force-pushing, dropping migrations, rewriting deploy config, or
    similar. Confirm in chat first.
16. **Installed tools are specialists, not competing authorities. Use the
    minimum relevant toolchain for each task.**
17. **Never claim a skill, plugin, MCP server, or integration is available
    unless its installation and discovery have been verified.** See
    `docs/AI-TOOL-INSTALLATION-MANIFEST.md` for what's actually installed
    vs. requires user action vs. could not be verified as real.
