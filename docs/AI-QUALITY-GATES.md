# EcoIQ AI Quality Gates

Checklist for meaningful frontend or AI-behavior changes. Pair with
[AI-SKILL-ROUTER.md](AI-SKILL-ROUTER.md) (which tools to use) and
[AI-DEVELOPMENT-STACK.md](AI-DEVELOPMENT-STACK.md) (what's installed).

A gate applies when the change is *observable* — it touches something a
user sees, clicks, or an AI feature responds to. Skip gates that don't apply
(e.g. a pure backend data-pipeline change has no motion gate).

## 1. UX
- [ ] Information architecture matches existing navigation patterns — no new
      nav paradigm introduced without reason
- [ ] Component hierarchy is consistent with sibling pages/components
- [ ] Empty, loading, and error states are designed, not just the happy path

## 2. Visual quality
- [ ] Colors, spacing, radii, shadows come from `design/tokens.ts` /
      `system.css` — no new hard-coded hex/px values duplicating a token
- [ ] Typography matches existing scale
- [ ] Consistent with the "premium AI visual-intelligence platform" aesthetic
      target already documented in `tokens.ts` (dark institutional, not
      generic SaaS)

## 3. Responsive behavior
- [ ] Verified at desktop (1280px), tablet (768px), and mobile (375px) via
      Browser pane `resize_window`
- [ ] No horizontal overflow at any breakpoint
- [ ] Touch targets ≥ 44px on mobile for interactive elements

## 4. Accessibility
- [ ] Keyboard-only navigation reaches every interactive element
- [ ] `:focus-visible` state present wherever `:hover` is (per
      `motion-style-guide.md` — never hover-only feedback)
- [ ] Color contrast holds against the dark token palette
      (`ink`/`inkStrong` on `bg900`/`surface`, not custom greys)
- [ ] `prefers-reduced-motion` / OS reduced-motion respected — verify via
      Browser pane by emulating reduced motion or inspecting
      `MotionConfig reducedMotion="user"` is still the active provider
- [ ] Semantic HTML / ARIA roles used before reaching for `div`+JS

## 5. Motion (see `docs/motion-style-guide.md` for the full ruleset — this is the gate summary)
- [ ] Entrance animations trigger once per viewport visit (`viewport once:
      true`), never replay on re-scroll
- [ ] Animates only `transform`/`opacity` unless there's a specific,
      justified exception
- [ ] Duration within documented bounds (0.18s hover, 0.4–0.9s entrance,
      ≤1.2s max — nothing slower)
- [ ] No infinite/free-running loops; every animation is bounded
- [ ] Motion never blocks input, form submit, or navigation
- [ ] Concurrent animation count stays within the density budget in
      `motion-style-guide.md` §4

## 6. AI product behavior (for AI-assistant / agent-facing features)
- [ ] Complexity is progressively disclosed — advanced controls aren't
      dumped on first view
- [ ] The system communicates what it's doing/why when it takes a
      non-obvious action (generative-UI / transparency principle)
- [ ] Conversation or interaction patterns are consistent with existing
      EcoIQ AI surfaces (Capital Guardian, LegacySafe, audit flows) —
      don't invent a new interaction paradigm per feature
- [ ] Context passed to the model is scoped to what's needed — no
      unbounded dumping of unrelated repo/user data into a prompt

## 7. AI trust, transparency & guardrails
- [ ] Every AI-derived number, recommendation, or claim shown to a user is
      traceable to its source (mirrors LegacySafe's lineage-tracking
      pattern already in this codebase — reuse that discipline, don't
      invent a separate one)
- [ ] Confidence/uncertainty is surfaced where the underlying data or model
      output is uncertain — never presented with false precision
- [ ] Deterministic checks (permissions, access control, financial
      calculations) are never delegated to an LLM decision — matches the
      existing rule in `legacy_safe/services/permissions.py`
- [ ] Destructive or financial actions require explicit human confirmation
      in the UI, not silent AI execution
- [ ] No secrets, API keys, or credentials appear in a prompt, log, or
      client-visible payload

## 8. Performance
- [ ] No new render-blocking script on the critical path (islands stay
      `defer`red per the existing pattern in `base.html`)
- [ ] Bundle size change is proportionate — check `npm run build` output
      size, not just that it builds
- [ ] No obvious new layout thrash (animating `width`/`height`/`top`/`left`
      instead of `transform`)

## 9. Browser verification (gate of last resort — run before calling a frontend change done)
- [ ] Dev server started via `.claude/launch.json` (`ecoiq`, port 8731)
- [ ] Page loads with zero new console errors (`read_console_messages`)
- [ ] No failed network requests introduced (`read_network_requests`)
- [ ] Desktop, tablet, mobile screenshots taken and reviewed
- [ ] Interactive elements exercised (`computer` click/type) and confirmed
      via `read_page`, not assumed from reading the source
- [ ] If motion changed: confirmed reduced-motion path still works

## Evidence over claims
Per root `CLAUDE.md`: never report a frontend change as "done" without the
Browser-pane evidence in §9. Never report tests/build as passing without
having actually run them this session.
