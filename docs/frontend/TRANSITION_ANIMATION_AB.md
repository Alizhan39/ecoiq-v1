# Scroll-linked SVG transition: Variant A vs Framer Motion

**Decision: keep Variant A (zero-dependency). Experiment removed.**
Measured 2026-08-29 against `proto/industrial-transition`.

This record exists so the question does not get reopened from memory. It was a
real comparison with a real implementation, not a preference.

## What was compared

Only the **scroll-linked SVG transition layer**. The domain model, topology
engine, Canvas flow layer and semantic narrative were shared verbatim — both
variants imported the same `NODES`, `EDGES`, `presence()` and glyphs, so any
difference is a difference in the animation layer and nothing else.

Variant B used `framer-motion@^11.18.2` — the version already canonical in
`frontend/app` — lazy-loaded inside the preview chunk behind `?variant=b`.

The hypothesis worth testing: Variant A calls `setState` every scroll frame, so
React reconciles ~22 nodes and ~16 paths each time. A `MotionValue` writes to
the DOM outside React's render cycle, so B rendered every node and edge once
and drove opacity through `useTransform` — constant DOM, no per-frame
reconciliation.

## Measurements

| | Variant A | Variant B |
|---|---|---|
| Per-update cost | **0.555 ms** | 0.557 ms |
| Median frame | 16.7 ms | 16.7 ms |
| p95 frame | 17.0 ms | 16.8 ms |
| Max frame | **17.7 ms** | 33.5 ms |
| Long frames (>32 ms) | **0** | 1 |
| Scene DOM elements | **75** | 107 |
| Total DOM nodes | **311** | 345 |
| JS heap | **10.6 MB** | 12.6 MB |
| Main bundle (gzip) | 58.85 kB | 58.86 kB |
| Scene chunk (gzip) | **+0** | **+37.92 kB** |
| Reverse-scroll determinism | exact | exact |

Per-update cost was measured as a burst of 60 scroll updates each forcing a
style+layout read, median of five runs — not an rAF-paced sweep, which is
frame-bound and would have shown 16.7 ms for anything.

## Why the hypothesis did not hold

React reconciliation was never the bottleneck. Variant A's per-frame work is
~40 elements and `useScrollProgress` already coalesces to one rAF; the cost is
layout and paint, which both variants pay identically. Removing reconciliation
removed something that was not costing anything.

## The disqualifying finding

`pathLength` is implemented by setting `strokeDasharray` and
`strokeDashoffset`. This drawing uses dash patterns to distinguish flow kinds —
electricity solid, heat dashed, water dotted, fuel heavy — specifically so the
schematic survives greyscale and colour-blindness. Framer Motion's draw-in
overwrote them, and the edges rendered as disconnected fragments.

The one effect the library was supposed to be best at is the one that broke an
accessibility property of the design.

## Lines of code

Variant B's scene is 93 comment-free lines against Variant A's 171. That
comparison flatters B: it reimplements only the SVG layer, omitting the Canvas
painting setup, reduced-motion pinning, colour-token reading and pulse pool
that A carries. A's SVG-only equivalent is roughly 116 lines. The honest figure
is **~23 lines saved for 37.92 kB gzip**, and a broken dash encoding.

## What would change this answer

- A genuine morph requirement — interpolating one path shape into a different
  one. Framer Motion cannot do this either; that is `flubber` or GSAP
  MorphSVG, and neither is currently justified.
- Scene complexity growing by roughly an order of magnitude, so React
  reconciliation becomes the actual bottleneck rather than a theoretical one.
- Spring or inertial motion as a design requirement. Deliberately absent:
  scroll position is the source of truth and a spring would make the frame
  depend on velocity as well as position, which breaks the determinism every
  test in this feature relies on.

Until one of those is true, the dependency buys nothing measurable.
