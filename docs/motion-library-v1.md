# EcoIQ Motion Library v1

**Status: LOCKED**

This document is the canonical catalog of every reusable motion primitive in
the EcoIQ frontend. Everything described here is frozen — implemented,
reviewed, and approved across the cinematic homepage hero and every
homepage section beneath it.

## Lock rules

1. **Nothing in this catalog is edited.** Not timing, not easing, not
   spacing, not the interaction model of an existing primitive.
2. **Future sections reuse these primitives.** A new page or section needing
   a fade, a stagger, a hover, a counter, or a scroll trigger pulls from this
   catalog — it does not invent a new mechanism.
3. **A genuine new *need*** (a motion shape nothing here covers) is a
   deliberate, reviewed addition to v1.1+, proposed before it's built — it is
   never silently added inside unrelated feature work.
4. **Bug fixes that don't change visual behavior** (e.g. swapping a
   layout-triggering CSS property for a transform-based equivalent that
   looks identical) are the one exception — see the Performance section of
   the [Motion Style Guide](motion-style-guide.md).

---

## Architecture: two systems, one language

EcoIQ's frontend has two independent rendering paths that share one visual
motion language (same durations, same easing curve, same choreography
rules), implemented twice because they run in genuinely different
environments:

| | React islands | Django-rendered pages |
|---|---|---|
| Where | `frontend/app/src/components/**` | `templates/landing.html` and friends |
| Engine | Framer Motion (`m.*`, `useTransform`, `useScroll`) | Plain CSS transitions/keyframes + one `IntersectionObserver` |
| Why two | Framer Motion is a React runtime — it cannot attach to server-rendered HTML that isn't hydrated as a React tree | Most of the homepage below the hero is server-rendered Django/Tailwind, not React |
| Reduced motion | `MotionConfig reducedMotion="user"` (automatic) + explicit checks in count-up | One `@media (prefers-reduced-motion: reduce)` block, `!important` |

Both systems use the **same tokens** (`ease.out = cubic-bezier(.22,1,.36,1)`,
the same duration bands) so the choreography feels identical regardless of
which system is rendering a given section.

---

## Design tokens

Source of truth: `frontend/app/src/design/tokens.ts` (mirrored as CSS custom
properties in `frontend/app/src/design/system.css`, and mirrored again as
literal values in `templates/landing.html`'s `.eiq-mo-*` block since that
page can't import the TS module).

### Easing

| Token | Value | Use |
|---|---|---|
| `ease.out` | `cubic-bezier(0.22, 1, 0.36, 1)` | Default for every entrance — confident deceleration |
| `ease.inOut` | `cubic-bezier(0.65, 0, 0.35, 1)` | Hover holds / bidirectional loops |

### Duration

| Token | Value | Use |
|---|---|---|
| `duration.fast` | `0.18s` | Hover, focus, small pop-ins |
| `duration.base` | `0.42s` | Standard entrance (fade-up, cards) |
| `duration.slow` | `0.7s` | SVG draw-ins, large scale-ins |

### Vanilla-system (Django page) durations

These are hand-tuned to the same easing curve but a slightly wider band,
per the explicit spec for that system (section headings read slower than
component-level fades):

| Element | Duration | Delay pattern |
|---|---|---|
| Section eyebrow / heading / lede | `0.8s` | 0s / 0.1s / 0.2s stagger |
| Divider draw | `0.7s` (transform), `0.5s` (opacity) | `0.32s` fixed |
| Card / row stagger | `0.5s` | `var(--i) * 90ms` |
| Chip pop-in | `0.4s` | `var(--i) * 140ms` |
| Sub-reveal (icon→title→desc) | `0.45s` | `var(--i)*90ms + {70,160,250}ms` |
| CTA-last | `0.5s` | fixed `0.75s` |

---

## React / Framer Motion primitives

All exported from `frontend/app/src/motion/` (barrel: `frontend/app/src/motion/index.ts`).

### `MotionProvider` (`motion/MotionProvider.tsx`)
Wraps every mounted island. `LazyMotion(domAnimation)` (smaller bundle than
importing full `motion`) + `MotionConfig(reducedMotion="user")`. Every
island gets automatic OS-level reduced-motion support for free — no
per-component opt-in.

### `Reveal` (`motion/Reveal.tsx`)
The standard **page reveal** primitive. `whileInView` fade-up wrapper,
`viewport={{ once: true, amount: 0.25 }}` by default. Use for any
section-level entrance. Accepts `variants`, `as` (div/section/li/ul).

### `fadeUp`, `scaleIn`, `staggerItem` (variants, `motion/presets.ts`)
Static `Variants` objects — `hidden`/`show` pairs. `fadeUp` is the default
panel/card entrance (`opacity 0→1, y 18→0`). `scaleIn` is for visuals/globes
(`opacity 0→1, scale 0.94→1`). `staggerItem` is the child half of the
**stagger reveal** pattern (`opacity 0→1, y 14→0`).

### `stagger(gap = 0.08, delay = 0)` (factory, `motion/presets.ts`)
The **stagger reveal** parent. Returns a `Variants` object with
`staggerChildren`/`delayChildren` — pair with `staggerItem` (or a
component-local variant) on each child.

### `drawPath(transition = tSlow)` (factory, `motion/presets.ts`)
The **line-draw** primitive for discrete (mount/viewport-triggered) SVG
strokes — `pathLength 0→1`. For *scroll-scrubbed* line draws (the cinematic
hero's evidence/repair connection lines), the same visual effect is done via
a raw `style={{ pathLength: someMotionValue }}` binding driven by
`useTransform` — that's the scroll-linked sibling of this preset, not a
separate primitive.

### `popIn(transition = tFast, fromScale = 0)` (factory, `motion/presets.ts`)
Scale + fade **pop-in** for nodes, pins, and chips. `fromScale` lets a
caller start from e.g. `0.85` instead of `0` when a fuller pop isn't wanted.

### `hoverLift` (static object, `motion/presets.ts`)
The **hover glow/lift** primitive. `{ rest, hover }` pair —
`y: -4`, upgraded box-shadow, `tFast` transition. Apply via
`whileHover={hoverLift.hover}` / `whileFocus={hoverLift.hover}`.

### `useCountUp(target, run, ms = 1000)` (`hooks/useCountUp.ts`)
The **counter animation** primitive. Cubic ease-out rAF tween from 0→target.
**Reduced-motion aware**: checks `matchMedia('(prefers-reduced-motion: reduce)')`
and snaps straight to `target` when active, in addition to the `run` gate
(callers use `run` to wait until on-screen via `IntersectionObserver`,
disconnecting after the first trigger — never replays).

### `CountUpValue` (`components/cinematic/CountUpValue.tsx`)
The progressive-enhancement wrapper around `useCountUp` for numeric badges
inside server-rendered Django templates: Django renders the real number as
static fallback text, this island hydrates and animates it in place.

### `useMediaQuery(query)` (`hooks/useMediaQuery.ts`)
SSR-safe `matchMedia` hook, defaults `false` until mount. Drives the
mobile/desktop **scroll-trigger** branch (see below).

### `useCinematicScroll` (`components/cinematic/useCinematicScroll.ts`)
The **scroll trigger** primitive for the pinned cinematic stage.
`useScroll({ target, offset: ['start start', 'end end'] })` → continuous
`scrollYProgress`, plus a derived discrete `activeScene` index via
`useMotionValueEvent` for the pieces that need a boolean rather than a
continuous value (chip pop-ins, particle gating).

---

## Vanilla `.eiq-mo-*` primitives (Django-rendered pages)

All defined in `templates/landing.html`'s `<style>` block, driven by one
`IntersectionObserver` in the bottom `<script>` block (`threshold: 0.15`,
`unobserve` after first trigger — reveals run once per page visit).

| Class | Primitive | Behavior |
|---|---|---|
| `.eiq-mo-root` | Reveal trigger | Marks the observed element; adds `.eiq-mo-in` once, permanently |
| `.eiq-mo-eyebrow` / `.eiq-mo-heading` / `.eiq-mo-lede` | **Page reveal** (section intro) | Staged fade-up, 0/0.1s/0.2s delay |
| `.eiq-mo-divider` | **Divider animation** | `scaleX(0)→scaleX(1)`, origin left, `0.32s` delay |
| `.eiq-mo-stagger > *` | **Stagger reveal** | Auto-indexed via `--i` (JS sets it), `y+scale` entrance |
| `.eiq-mo-chip-row` / `.eiq-mo-chip` | Chip pop-in | Same auto-index mechanism, `scale(.85)→1` |
| `.eiq-mo-arrow` | Connector reveal | Fades in slightly after its neighboring chip |
| `.eiq-mo-sub-a/b/c` | 3-step sub-reveal | Inherits parent's `--i` via CSS custom-property inheritance — icon→title→description, or badge→…→CTA, entirely in CSS |
| `.eiq-mo-line-draw` | **Line draw** (card accent) | `scaleX(0)→1`, after the card |
| `.eiq-mo-hover-lift` | **Hover glow** (translateY variant) | `y:-4`, shadow upgrade — for cards not in a fused/seamless grid |
| `.eiq-mo-hover-glow` | **Hover glow** (quiet variant) | Border + inset glow only, no transform — for cards inside an `overflow:hidden` fused grid where a lift would clip or break the shared-border look |
| `.eiq-mo-kpi-label` | Label-follows-value | Pairs with a `CountUpValue` island; label fades in after the number starts |
| `.eiq-mo-cta-last` | **CTA reveal** | Fixed `0.75s` delay — always the last thing in a group to appear |

**Reduced motion**: one `@media (prefers-reduced-motion: reduce)` block
forces every primitive above to `opacity: 1 !important; transform: none
!important; transition: none !important` — content appears instantly, in
final position, no exceptions.

---

## v1.1 addition: hero canvas particle system

Per the lock rules above ("a genuine new need... is a deliberate, reviewed
addition to v1.1+, proposed before it's built"): the cinematic hero's Earth-
depth and arm-intervention effects (atmospheric particles, directional waste/
repair extraction, organic restoration spread, verify-beat data arcs) are
rendered on a single `<canvas>` (`components/cinematic/HeroCanvas.tsx` +
`canvasEngine.ts`) — a motion shape nothing in the DOM/SVG catalog above
covers. Two rules specific to this addition:

- **No independent animation loop.** `paintHero` is a pure function of
  `progress` (the raw `scrollYProgress`, 0–1) — every particle's position
  comes from a deterministic function of `(seed, progress)`, never
  `(seed, elapsedMs)`. It's called synchronously from the same
  `useMotionValueEvent(scrollYProgress, 'change', ...)` pattern every other
  overlay in this tree already uses. No `requestAnimationFrame`, no
  `setInterval`, anywhere in the canvas system.
- **Particle budget: 60 total**, allocated once in a fixed pool and mutated
  in place (`buildParticlePool`) — never recreated per paint call. The style
  guide's earlier "~5 particles" figure was a proxy for "no per-frame-JS DOM
  elements"; canvas draws don't carry that cost, but the number is a stated
  budget here rather than a silent increase past that figure. Unchanged by
  the refinement pass below — no new particles were added, only a new
  geometric draw function reusing the existing `REPAIR_TARGETS` points.

### Refinement pass (calibration, not a new addition)

A follow-up audit found the whole waste→repair→verify sequence compressed
into ~21vh of real scroll (too fast to read as distinct beats) and the two
arms sharing near-identical particle motion (failing to read as
differentiated interventions). Fixes, none of which change the rules above:
`AGENTS_SUB_RANGES` widened (Scene 3's own span grew 0.14→0.21 of the
timeline — scenes 4-8, still unimplemented, absorbed the difference);
repair's particles switched from smooth converge-with-jitter to discrete
stepped waypoints plus a new `paintRepairReconstruct` geometric-scaffold pass
(precise/staged, vs. waste's organic/converging, per the brief's
differentiation ask); the globe's arm-response glow moved from one uniform
whole-globe ring to two localized spot-glows at the actual intervention
points; the redundant dashed-SVG "connection lines" in `WasteRestoration.tsx`
/`RepairSequence.tsx` were removed (the canvas particle stream already
carries that signal, more directionally). Also added: a documented, reusable
`imageSpaceToCanvasPoint()` helper in `sceneLayout.ts` for deriving a virtual-
canvas point from a pixel measured directly in the source PNG (replacing
guesswork for the 6 arm-joint points specifically) — see that file for the
flagged, not-yet-resolved discrepancy on the older `LEFT_ARM_CLAW`/
`RIGHT_ARM_CLAW`/`GLOBE_CENTER` constants.

## Where things live (quick index)

```
frontend/app/src/design/tokens.ts              — color/space/radius/ease/duration
frontend/app/src/design/system.css             — CSS custom properties mirroring tokens.ts
frontend/app/src/motion/
  MotionProvider.tsx                            — root LazyMotion + reduced-motion config
  Reveal.tsx                                    — page reveal wrapper
  presets.ts                                    — fadeUp, scaleIn, stagger, staggerItem,
                                                   drawPath, popIn, hoverLift, tBase/tFast/tSlow
frontend/app/src/hooks/
  useCountUp.ts                                 — counter animation (reduced-motion aware)
  useMediaQuery.ts                              — responsive branch hook
frontend/app/src/components/cinematic/
  CinematicHomeHero.tsx                         — orchestrator (motion/mobile branch)
  useCinematicScroll.ts                         — scroll-trigger hook
  sceneRanges.ts / sceneLayout.ts                — timeline + screen-space constants
  CinematicBackground.tsx                        — hero image + GlobeRotationOverlay + HeroCanvas
  GlobeRotationOverlay.tsx                       — fake-rotation + response-glow overlay (circular mask)
  canvasEngine.ts / HeroCanvas.tsx                — v1.1 particle system (see above)
  scenes/*.tsx                                   — Intro / Evidence / Agents scenes,
                                                    ArmEngagement, WasteRestoration, RepairSequence,
                                                    ArmJointLights, ContactFlash
  CinematicStaticStack.tsx                       — reduced-motion + mobile fallback
  PillarsSection.tsx                             — five-pillar cards
  CountUpValue.tsx                               — KPI count-up island
  content.ts                                     — shared copy (both render paths)
frontend/app/src/cinematic.css                  — all cinematic-hero-specific styles
templates/landing.html                          — .eiq-mo-* system (style block + script block)
templates/harvester/_intelligence_block.html    — CountUpValue usage example
```
