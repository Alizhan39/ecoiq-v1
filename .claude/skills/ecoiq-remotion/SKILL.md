---
name: ecoiq-remotion
description: Author or change EcoIQ's programmatic video briefs in frontend/remotion — evidence-based pilot explainers, before/after transition videos, KPI and impact animations, investor or government pitch videos, captions, and provenance overlays. Use when the deliverable is a rendered video file. Not for in-page motion, which belongs to docs/motion-style-guide.md and the React islands.
---

# EcoIQ Remotion briefs

## It is already set up — do not re-scaffold it

`frontend/remotion/` is a working workspace, not a placeholder:

- `remotion` and `@remotion/cli` pinned at exactly **4.0.190**, React 18.3.1,
  TypeScript 5.5.4 (`frontend/remotion/package.json`).
- Compositions registered via `registerRoot` in `src/index.ts` → `src/Root.tsx`.
- Three existing compositions: `CountryTransitionBrief`,
  `CompanyEsgRiskBrief`, `KhalifaToursImpactExplainer`.
- Shared pieces already factored: `src/components/Shared.tsx`,
  `src/lib/theme.ts`. Reuse them; a fourth composition should mostly be
  composition, not new primitives.

`node_modules/` is **not installed** in this checkout. `npm install` pulls
Remotion plus a headless Chromium (hundreds of MB, gitignored) — expect that
cost before promising a render.

## The isolation rule

Remotion is build-time only and must stay that way.

- Never add Remotion, Node, or Chromium to `requirements.txt`, `build.sh`,
  `predeploy.sh`, `start.sh`, `render.yaml`, or any CI workflow.
- Django only ever serves an **already-rendered** file from `static/video/`,
  through WhiteNoise, like any other static asset.
- Rendering happens on a developer machine. There is no server-side render
  path and adding one is an architecture change, not a task.

```bash
cd frontend/remotion
npm install          # once, locally
npm run studio       # preview
npm run render:country | render:company | render:tours | render:all
```

Outputs land in `frontend/remotion/out/` (gitignored). Only the final,
optimized file is copied into `static/video/`.

## Content rules — this is where video goes wrong

Video strips context: a number on screen for two seconds reads as fact, and
the clip outlives the deck it was made for.

1. **Every figure on screen is real or labelled.** Placeholder numbers in a
   composition become a published claim the moment someone renders it. If a
   value is illustrative, the frame says so.
2. **Provenance overlays are content, not decoration.** Source and date go on
   the frame that shows the number, legible at the size it will actually be
   watched — not in a credits card nobody reads.
3. **Impact claims pass `ecoiq-impact-claims`** — all six links. A
   before/after transition video is an impact claim with production values.
4. **Regulatory statements pass `ecoiq-regulatory-review`** — all eight
   fields, and nothing AI-authored presented as approved.
5. **AI-derived content is attributed as AI-derived**, with its review state,
   per `ecoiq-evidence-audit`.
6. **English on public video.** No Surah names, Arabic terminology, or
   Qur'anic references — same rule as every other public surface
   (`ecoiq-brand`).

## Brand and motion

Colours come from `src/lib/theme.ts`, which mirrors
`frontend/app/src/design/tokens.ts` — keep them in step rather than forking a
second palette. Duration and easing bounds in
[`docs/motion-style-guide.md`](../../../docs/motion-style-guide.md) apply to
video too; the frame-based exception is that a composition has a fixed
duration by definition, so "no infinite loops" is automatic.

## Captions and languages

Captions are burned in per composition. The site is English-only and the
assistant supports en/ar/ru with no Kazakh (see `ecoiq-brand`) — a captioned
language is a translation someone must actually review, not a font swap.
Arabic additionally needs RTL layout and shaping verified visually in the
studio, not assumed.

## Done when

- `npm run studio` renders the composition without errors (state whether you
  actually ran it — `node_modules` may not be installed).
- Every on-screen figure is real or visibly labelled illustrative.
- Nothing Remotion-related entered the Django runtime, CI, or `requirements.txt`.
- Only the final optimized file was added to `static/video/`.
