# static/video/

Final, optimized EcoIQ video files live here and are served as plain static
assets (WhiteNoise) by the live site. They are produced **offline** with the
Remotion studio in `frontend/remotion/` — the Django app never renders video.

Expected files (drop them here after rendering + optimizing):
- `country-transition-brief.mp4`
- `company-esg-risk-brief.mp4`
- `khalifa-tours-impact.mp4`  (and optionally `.webm`)

Keep each file web-optimized (H.264 + `+faststart`, or VP8/VP9 WebM) and small.
