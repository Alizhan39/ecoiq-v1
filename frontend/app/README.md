# EcoIQ Visual Intelligence — React Islands (Phase 0)

The visual-intelligence layer for EcoIQ. React + Vite + TypeScript components
("islands") that mount into existing Django templates. **Django stays the
backend, the auth/security boundary, and the page shell.** This layer only
renders visuals from data Django gives it.

> **BUILD-TIME ONLY.** Node / Vite / React are never a Render runtime
> dependency. `npm run build` compiles a committed bundle into
> `../../static/dist/`, which WhiteNoise serves exactly like any other static
> file. Render runs Python only. This mirrors the `frontend/remotion/` rule.

## How it works (the "island" pattern)

1. A Django template embeds a mount point + JSON props:

   ```html
   {% load static %}
   <div
     data-island="ImpactGlobe"
     data-props='{"villages": 12, "homesUpgraded": 480, "co2ReducedTons": 1600, "sponsors": 7, "eyebrow": "Khalifa Tours", "ctaLabel": "Explore impact", "ctaHref": "/heating/"}'>
     <!-- optional server-rendered fallback here; shown until/if JS hydrates -->
   </div>
   ```

2. `base.html` loads the bundle once (already wired):

   ```html
   <script type="module" src="{% static 'dist/ecoiq-islands.js' %}" defer></script>
   ```

3. The loader (`src/main.tsx`) finds every `[data-island]`, looks the name up in
   `src/registry.ts`, parses `data-props` as JSON, and mounts the React
   component. Unknown islands or bad JSON log a warning and leave the
   server-rendered fallback untouched — **a page never breaks.**

## Commands

```bash
cd frontend/app
npm install          # one-time, local only
npm run dev          # Vite dev server for component work
npm run build        # typecheck + compile → ../../static/dist/ (commit the output)
npm run typecheck    # tsc --noEmit
```

After `npm run build`, **commit the regenerated files in `static/dist/`** so
Render serves them without Node. `collectstatic` (in `build.sh`) hashes them via
`ManifestStaticFilesStorage`; that's why Vite emits stable, unhashed names.

## Design system & motion

This layer has a **dark institutional design system** so every component looks
like one premium product, not a pile of widgets:

- `src/design/tokens.ts` — colors, spacing, radii, easing, durations, elevation
  (the JS source of truth, for SVG fills / motion values).
- `src/design/system.css` — the same values as CSS variables, scoped under
  `.eiq`, plus primitives: `.eiq-panel` (layered surface + luminous top edge),
  `.eiq-eyebrow`, `.eiq-num` (tabular numerics). The island loader adds the
  `eiq` class to every mount point so the variables cascade in.

**Framer Motion** powers entrances and micro-interactions, loaded efficiently
via `LazyMotion` (use the lightweight `m.*` components, not `motion.*`):

- `src/motion/MotionProvider.tsx` — wraps every island (applied in the loader);
  `reducedMotion="user"` makes all animation honor the OS setting.
- `src/motion/presets.ts` — shared variants (`fadeUp`, `scaleIn`, `stagger`,
  `staggerItem`, `hoverLift`) + transitions.
- `src/motion/Reveal.tsx` — scroll-triggered entrance wrapper.

## Adding a new component (future phases)

1. Create `src/components/MyWidget.tsx` with a typed props interface. Build on
   `.eiq-panel`, the `eiq-*` primitives, and the motion presets. Use `m.*`
   (LazyMotion) — never `motion.*` (it throws under `strict`).
2. Register it in `src/registry.ts`: `MyWidget,`.
3. `npm run build`, commit `static/dist/`, drop a `data-island="MyWidget"` div
   into any template.

## Roadmap

- **Phase 0:** foundation + `ImpactGlobe`.
- **Phase 1 (this):** design system + Framer Motion + reusable `Metric`,
  `Reveal`; `RiskRadar` added.
- **Phase 2:** `TransitionMap`, `ESGGraph`, `StakeholderMap`,
  `ScenarioSimulator`; cross-component linking.
- **Later:** `ImpactGlobe3D` (lazy three.js / React Three Fiber), reusing the
  existing props contract; deck.gl data layers.
