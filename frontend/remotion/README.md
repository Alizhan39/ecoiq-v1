# EcoIQ Video Studio (Remotion) — local / build-time only

> **This is NOT a Render runtime dependency.** Node + Remotion run only on a
> developer machine. Nothing here is installed or executed on Render. The live
> EcoIQ Django site only ever **plays already-rendered** video files.

## What this is
Offline authoring of short, branded EcoIQ "briefs" as code (React + Remotion).
You render them locally to optimized MP4/WebM and copy the final file into the
Django app's `static/video/` folder. The site serves that static file like any
other asset (WhiteNoise) — no Node, no Remotion, no headless Chromium in prod.

## Templates (compositions)
| id | Output | Purpose |
|----|--------|---------|
| `CountryTransitionBrief` | `country-transition-brief.mp4` | Country Transition Brief |
| `CompanyEsgRiskBrief` | `company-esg-risk-brief.mp4` | Company ESG Risk Brief |
| `KhalifaToursImpactExplainer` | `khalifa-tours-impact.mp4` | Khalifa Tours Impact Explainer |

## Install (once, locally)
```bash
cd frontend/remotion
npm install            # pulls Remotion + a headless Chromium (~hundreds of MB, gitignored)
```

## Preview
```bash
npm run studio         # opens the Remotion studio in the browser
```

## Render
```bash
npm run render:country
npm run render:company
npm run render:tours
npm run render:tours-webm   # VP8 WebM variant
npm run render:all
```
Output lands in `frontend/remotion/out/` (gitignored).

## Report-to-video workflow (data in via props)
Each composition reads its data from `defaultProps`. To generate a video for a
specific country/company/report, override the props at render time:
```bash
npm run render:country -- --props='{"country":"Türkiye","ecoiqScore":71.5,"maqasidScore":80,"headline":"Country Transition Intelligence","kpis":[{"label":"Coal share","value":"Medium"}]}'
```
(A future helper can export a Django report/lead to this JSON automatically.)

## Optimize + publish to the site
```bash
# example optimization (ffmpeg) — target small, web-friendly files
ffmpeg -i out/khalifa-tours-impact.mp4 -vcodec libx264 -crf 28 -preset slow -movflags +faststart \
       ../../static/video/khalifa-tours-impact.mp4
# then, in the Django repo:
python manage.py collectstatic --no-input
```
Commit only the **optimized final video** in `static/video/` — never `node_modules/`
or `out/` (both gitignored).
