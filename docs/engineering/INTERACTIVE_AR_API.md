# Interactive UI and augmented reality API

This is an experimental Labs surface at `/labs/interactive/`, backed by the
existing same-origin Django API v2. React is already used in EcoIQ.
`@google/model-viewer` is the only new direct frontend dependency. It is pinned
in `frontend/web/package.json` and loaded after the user presses **Load 3D model**.
The other catalogue entries are integration options, not installed features.
The AR group includes rendering engines and helpers, not ten independent AR systems.

## Contract

All endpoints are anonymous, read-only JSON endpoints using existing DRF
authentication and throttling. They query no customer data and fetch no remote URLs.

| GET endpoint | Result |
| --- | --- |
| `/api/v2/interactive/libraries/` | Twenty curated options; `category=ui` or `category=ar` returns ten |
| `/api/v2/interactive/scenes/` | Explicitly labelled demo scene index |
| `/api/v2/interactive/scenes/stewardship-demo/?lang=ru` | Scene manifest and three interactive hotspots |

`lang` accepts `en`, `ru`, `kk`, `ar`; defaults to English. Unsupported explicit
languages or categories receive JSON 400. Unknown scenes receive JSON 404.
POST receives 405. Successful responses have `schema_version: 1`.

The demo manifest contains `is_demo: true`, `verified: false`,
`scale_is_measured: false`, a same-origin static `model_url`, supported AR modes,
and localized hotspot labels. Every hotspot has `measurement: null` and
`evidence_url: null`. The three blocks illustrate energy, water and materials;
their dimensions are design geometry, not measurements, impact or economic claims.
The original model has no external textures or data dependencies. Rebuild it with
`python scripts/build_stewardship_model.py` and commit the result.

## Ten interface libraries

| Library | Intended role | Integration |
| --- | --- | --- |
| [React](https://react.dev/) | Existing component interface | Integrated |
| [htmx](https://htmx.org/docs/) | Django HTML fragments | Option for server templates |
| [Alpine.js](https://alpinejs.dev/) | Small template interactions | Option for server templates |
| [TanStack Query](https://tanstack.com/query/latest) | Server state and caching | Option |
| [TanStack Table](https://tanstack.com/table/latest) | Interactive data tables | Option |
| [Radix UI](https://www.radix-ui.com/primitives) | Accessible UI primitives | Option |
| [Motion](https://motion.dev/docs) | Interface transitions | Option |
| [D3](https://d3js.org/) | Custom data graphics | Option |
| [Apache ECharts](https://echarts.apache.org/en/index.html) | Charts | Option |
| [Zustand](https://zustand.docs.pmnd.rs/) | Shared client state | Option |

htmx and Alpine are alternatives for Django template surfaces, not competing
owners of the React component tree. Keep the existing API client and `useApi`
until a concrete request caching requirement justifies replacing them.

## Ten AR / 3D libraries

| Library | Intended role | Integration |
| --- | --- | --- |
| [model-viewer](https://modelviewer.dev/docs/) | Model viewing and device AR handoff | Integrated, on demand |
| [Three.js](https://threejs.org/) | Custom scenes and WebXR | Option; also model-viewer's transitive engine |
| [React Three Fiber](https://r3f.docs.pmnd.rs/) | React renderer for Three.js | Option |
| [Drei](https://drei.docs.pmnd.rs/) | Fiber helpers | Option |
| [React XR](https://pmndrs.github.io/xr/docs/) | WebXR interactions with Fiber | Option |
| [Babylon.js](https://doc.babylonjs.com/features/featuresDeepDive/webXR/introToWebXR) | Alternative 3D / XR engine | Option |
| [A-Frame](https://aframe.io/docs/) | Declarative immersive scenes | Option |
| [AR.js](https://ar-js-org.github.io/AR.js-Docs/) | Marker and location AR | Option |
| [MindAR](https://hiukim.github.io/mind-ar-js-doc/) | Image and face tracking | Option |
| [PlayCanvas](https://developer.playcanvas.com/user-manual/xr/) | Alternative scene engine with XR | Option |

The viewer requests `webxr scene-viewer quick-look`. Device support is detected
at runtime; the server never claims a phone supports AR. HTTPS is required for
device AR. The camera is not requested on page load. The browser / native AR app
handles permission after the user chooses to start AR; this module does not
upload images or camera frames. Native Scene Viewer / Quick Look may not preserve
HTML hotspots, so the persistent text interface is the authoritative accessible
view. Quick Look uses model-viewer's generated USDZ; no private customer model
is handed to an external application by this demo.

The API does not mix sacred text with synthetic model metadata. Existing Islamic
catalogue source and citation rules remain authoritative for any future linkage.

## Checks and release gates

Run Django's `api.tests_v2_interactive` and `core.tests_spa`; run the frontend
typecheck, lint, tests and build. Commit `static/spa` because Render serves that
compiled output. Model/API checks cover demo flags, null evidence, read-only
methods, category validation, all four languages and the self-contained GLB.
UI checks cover on-demand loading, disabled AR before capability detection,
activation only from a user gesture on a secure supported device, viewer import
and model failure with a usable text fallback, retry, and Arabic RTL.

Local validation on 2026-10-09: the existing SPA suite (82 Django tests), eight
interactive API / route tests, the full frontend suite (558 tests before two
additional capability / import-retry checks), and the final six interactive
component tests passed. TypeScript, ESLint, repository Ruff and the production
build passed. The viewer is a separate ~300 kB gzip chunk; the route's JavaScript
is ~3.6 kB gzip. Keep the viewer on demand rather than loading it on navigation.
These sizes are build observations, not measured device performance.

Browser visual verification is still pending: the available Playwright browser
download returned truncated archives. No visual or physical-device pass is
claimed by these results.

Before production readiness, check on actual supported Android / iOS devices:
AR placement, permission refusal, exiting AR and native handoff. These hardware
checks cannot be certified by jsdom. Review Kazakh and Arabic copy with fluent
speakers. Check 375 px layout and keyboard focus; confirm the viewer's runtime
chunk is absent from the network until the load button is pressed.

Future real assets require publication and organisation authorization checks,
reviewed model uploads, format/size validation, and evidence links resolved
through the existing evidence permission boundary. Do not add arbitrary URL
fetching or expose private R2 URLs to this anonymous demonstration endpoint.

## Repeatable browser checks

From `frontend/web`, run `npm ci`, `npx playwright install chromium`,
`npm run build`, then `npm run test:browser`. The dedicated GitHub Actions
workflow runs the same checks and uploads screenshots/traces. These checks use
real compiled SPA/GLB assets and a local catalogue-backed API fixture server;
they do not replace the Django API tests or production HTTPS smoke checks.

The suite covers four-language 375 px overflow, keyboard part selection and
visible focus, deferred viewer download, chunk-failure focus recovery and actual
GLB loading. Screenshots require human inspection; passing numeric checks alone
is not visual sign-off. Permission rejection / AR status recovery also have
component regressions, but only physical devices can certify native handoff.
See [release verification](RELEASE_346_347.md) for the remaining release gates.
