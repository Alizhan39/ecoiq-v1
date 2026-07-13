# EcoIQ Motion Style Guide

**Companion to [motion-library-v1.md](motion-library-v1.md) (LOCKED).** This
document is the design-rules reference: when motion appears, how long it
lasts, and the constraints every future section must respect. Written in
the spirit of Apple's Human Interface Guidelines and Material Motion —
restrained, purposeful, never decorative for its own sake.

---

## 1. When animation appears

- **On first entrance into the viewport** — a section, card, or chip
  animates in the first time it crosses into view. This is the only
  trigger for content reveals.
- **On hover / focus** — cards and interactive elements get a hover
  response (lift or glow) and an equivalent `:focus-visible` state. Never
  hover-only; keyboard users get the same feedback.
- **On scroll position, only inside the pinned cinematic stage** — the
  homepage hero is the one place motion is continuously scroll-linked
  (`scrollYProgress`-driven). Nowhere else on the site scrubs animation to
  raw scroll position.
- **On a value becoming known** — count-up numbers animate once, when the
  real number is available and the element is on-screen.

## 2. When animation never appears

- **Never on every scroll pass.** Every reveal is once-per-page-visit
  (`viewport once: true` in React, `unobserve()` after first trigger in the
  vanilla system). Scrolling back up and down again does not replay a
  section intro, a card stagger, or a chip pop-in.
- **Never as a substitute for content.** No word-by-word or typewriter
  text animation, anywhere. Long-form copy appears as a single paragraph
  fade, never staged letter-by-letter.
- **Never on dates or non-numeric labels.** Count-up is for genuine
  cardinal numbers only — "Jul 9" or a status string never ramps.
  Formatting and exact values are never altered by the count-up hook.
- **Never blocking input.** No animation delays a click, a form submit, or
  navigation. Motion is decoration on top of an already-functional page,
  never a gate in front of it.
- **Never as an infinite/free-running loop.** Every animation in the
  system — including the cinematic hero's globe "rotation" and repair
  pulses — is bounded: it plays out over a fixed scroll range or a fixed
  number of iterations (e.g. `animation-iteration-count: 3`), then holds.
  Nothing on the page loops forever.

## 3. Duration

| Context | Duration |
|---|---|
| Hover / focus feedback | 0.18s (`duration.fast`) |
| Standard entrance (card, panel, chip) | 0.4–0.5s |
| Section heading reveal | 0.7–0.9s |
| SVG draw-in / large scale-in | 0.7s (`duration.slow`) |
| Count-up ramp | ~1.0–1.2s |

Nothing on the page animates slower than ~1.2s. Nothing faster than 0.18s
(below that, a state change should just be instant — there's no perceptual
value to a sub-180ms transition).

## 4. Maximum simultaneous animations

- **Per viewport, at rest:** at most one section's reveal sequence is
  running at a time (the once-per-visit + viewport-trigger model naturally
  enforces this — a user scrolling steadily triggers one section after
  another, not all at once).
- **Per card grid:** stagger delay is capped in practice around
  6–8 visible items before the tail-end delay becomes perceptually
  disconnected from the trigger. Grids larger than that (e.g. the AI Agent
  cards, 6 items) sit right at this ceiling — do not add more staggered
  siblings without re-checking the total delay budget
  (`items × ~90ms` should stay under ~700–800ms).
- **In the cinematic hero specifically:** at most 3 concurrent
  scroll-driven effect groups (background scale, one scene's
  labels/particles, one sub-effect like arm-glow or repair) — the scene
  sub-staging (rotation → arms → repair) is *sequential*, not simultaneous,
  specifically to keep concurrent motion low even in the densest part of
  the page.

## 5. Hover behavior

- Two shapes only: **lift** (`hoverLift` / `.eiq-mo-hover-lift` —
  `translateY(-4px)` + shadow upgrade) for standalone cards, and **quiet
  glow** (`.eiq-mo-hover-glow` — border + inset glow, no transform) for
  cards inside a seamless/fused grid where a lift would clip against an
  `overflow:hidden` boundary or break a shared-border illusion. Choosing
  between them is layout-driven, not a style preference.
- `:focus-visible` always mirrors the mouse-hover state. No hover-only
  affordance exists anywhere in the system.
- Hover never changes layout (no width/height changes on hover) — only
  `transform` and `box-shadow`/`background`.

## 6. Scroll behavior

- Standard sections use viewport-entry triggers (IntersectionObserver /
  `whileInView`), not scroll-position scrubbing.
- Only the cinematic hero uses continuous scroll-scrubbing
  (`useScroll`/`useTransform`), and only within its own pinned stage —
  this is a deliberate, contained exception, not a pattern to extend
  elsewhere on the site.
- No scroll-jacking anywhere: native scrollbar stays visible, scroll speed
  is never overridden, and the user can always scroll past the pinned
  stage at their own pace.

## 7. Accessibility rules

- Every interactive element (card, CTA, chip link) remains a real
  `<a>`/`<button>` — motion is layered on top of semantic HTML, never a
  replacement for it.
- `:focus-visible` states are preserved and visible on every animated
  interactive element (verified: `.eiq-pillars__card:focus-visible`,
  `hoverLift`'s `whileFocus` binding, `.eiq-mo-hover-lift:focus-visible`,
  `.eiq-mo-hover-glow:focus-visible`).
- No information is conveyed by animation alone — a reduced-motion user
  sees the exact same content, just without the staged entrance.
- Screen-reader announcements are not spammed by staggered reveals —
  content exists in the DOM immediately (Django-rendered / React-rendered
  on mount); only *opacity/transform* is deferred, so assistive tech
  reading a static DOM snapshot is unaffected by the animation layer.

## 8. Reduced-motion rules

When `prefers-reduced-motion: reduce` is set:

- **React side**: `MotionConfig reducedMotion="user"` at the root handles
  Framer-driven transform animations automatically; `useCountUp` explicitly
  checks the media query and snaps to the target value; the cinematic
  hero's entire scroll-driven stage (`GlobeRotationOverlay`, `ArmEngagement`,
  `RepairSequence`, scroll-scrubbed evidence/repair lines) is **structurally
  absent** — it only exists inside `CinematicScrollStage`, which is never
  rendered when reduced motion is on. `CinematicStaticStack` (stacked cards,
  simple fades) renders instead.
- **Vanilla side**: one `@media (prefers-reduced-motion: reduce)` block
  forces every `.eiq-mo-*` primitive to its final state instantly
  (`opacity: 1 !important; transform: none !important; transition: none
  !important`), and neutralizes hover transforms/shadows too.
- **Net result**: a reduced-motion user gets 100% of the content, 0% of
  the choreography — nothing is hidden, shortened, or reordered.

## 9. Performance budget

- **Animate only `transform`, `opacity`, SVG `pathLength`, or gradient-based
  `mask`/`clip-path` effects.** Never animate `width`, `height`, `top`,
  `left`, or any other layout-triggering property on a per-frame basis.
- **IntersectionObserver reveals disconnect after firing once** —
  `io.disconnect()` / `unobserve()` is mandatory on every gated
  animation (count-up, section reveal), so completed reveals stop costing
  anything.
- **Particle-style decorative elements are capped** (the cinematic hero's
  evidence/repair particles: ~5 elements total, CSS `offset-path`-driven,
  not per-frame JS).

## 10. GPU acceleration rules

- `transform` and `opacity` are the only properties that should appear
  inside a `transition`/`animate`/`useTransform` binding — both are
  compositor-only properties in every evergreen browser, so every
  entrance/hover/scroll effect in the system is already on the GPU fast
  path.
- `will-change` is intentionally **not** applied blanket-wide — it's a
  scarce resource (each use reserves a compositor layer) and every
  animation here is either short-lived (an entrance that finishes and
  never re-triggers) or scroll-bound (already compositor-promoted by the
  browser's own scroll-linked-animation heuristics). Add `will-change`
  only if a specific, measured jank case demands it — not preemptively.

## 11. Mobile / tablet / desktop limitations

| | Mobile (<760px) | Tablet (760–1024px) | Desktop (>1024px) |
|---|---|---|---|
| Cinematic hero | `CinematicStaticStack` — stacked cards, simple fades, **no** pinned stage, **no** scroll-scrubbing, **no** particles/rotation/repair sequence | Full pinned `CinematicScrollStage`, same as desktop, with simplified overlay density | Full pinned `CinematicScrollStage`, full overlay density |
| Rationale | A pinned 100vh stage with continuous scroll-linked transforms is expensive on mobile GPUs/CPUs and fights momentum scrolling — mobile gets the content, not the mechanism | Motion allowed; screen real estate is tighter so fewer simultaneous overlays | No constraint |
| Vanilla `.eiq-mo-*` sections | Same reveal mechanism at all sizes — CSS-only, negligible cost | Same | Same |
| Stagger distance / delay | Same values as desktop (CSS-based, resolution-independent) — no separate mobile timing table exists; the *content* changes (stacked vs. pinned), not the per-primitive timing | Same values | Same values |

---

## Performance audit (Phase 4)

Run against the local dev server (`manage.py runserver`, `DEBUG=True`,
production JS/CSS bundle via `vite build`):

| Check | Result |
|---|---|
| **CLS** | `0` — measured via `PerformanceObserver({type:'layout-shift'})` over a 3s window on page load. No layout shift detected. |
| **Layout-triggering animated properties** | One found and fixed: `ScenarioSimulator.tsx`'s progress bar animated `width` directly (triggers reflow every frame). Converted to `scaleX` + `transform-origin: left` — **identical visual result**, zero layout cost. This is the one Phase-4 code change in this pass, made under the explicit "fix performance regressions without changing visual behavior" allowance. |
| **GPU compositing** | Confirmed — every other animated property across `frontend/app/src/**` and `templates/landing.html` is `transform`, `opacity`, `pathLength`, or a gradient/mask property. No other `width`/`height`/`top`/`left` animation exists in anything reachable from the live homepage. |
| **IntersectionObserver cleanup** | Confirmed `unobserve`/`once: true` present everywhere a viewport-gated reveal exists (`ScoreRing`, `ImpactGlobe`, `PillarsSection`, `CountUpValue`, the vanilla `.eiq-mo-*` observer, `main.tsx`'s lazy-island loader) — 9 distinct call sites checked. |
| **Lighthouse / LCP** | **Not measured** — this environment's headless browser tooling doesn't populate `paint`/`largest-contentful-paint` performance entries (confirmed via direct `performance.getEntriesByType()` calls returning empty arrays despite `navigation` timing populating normally), and the `lighthouse` CLI isn't installed in this project. Recommend running Lighthouse from Chrome DevTools directly against a deployed/staging URL for the official LCP/performance score — this is a tooling gap in the verification environment, not a finding about the page itself. |
| **Known, out-of-scope item** | `components/stories/scenes/TimelineScene.tsx` animates an SVG `<rect>`'s `height` attribute. This component is **dead code** — confirmed unreachable from `registry.ts` or any current import — predates this work, and isn't part of Motion Library v1. Left untouched per the freeze (no refactoring of anything outside what's live and reviewed). |

---

## Status

**EcoIQ Motion Library v1 — LOCKED.**

All future storytelling sections and pages build on top of the primitives
in [motion-library-v1.md](motion-library-v1.md) and follow the rules above.
No new animation library, no new timing scale, no new easing curve is
introduced without a deliberate, reviewed v1.1 proposal.
