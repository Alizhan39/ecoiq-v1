# static/video/

Final, optimized EcoIQ video files live here and are served as plain static
assets (WhiteNoise) by the live site. They are produced **offline** — the
Django app never renders or transcodes video at runtime.

Keep each file web-optimized (H.264 + `+faststart`, or VP8/VP9 WebM) and small.

## Khalifah Field Intelligence (homepage)

Derivatives of a 4K HEVC Main-10 master (3840x2160, 24fps, 15.04s, 32.4MB,
bt709 SDR, AAC stereo). The master is **not** committed: HEVC does not decode
in Chrome or Firefox, and 32MB has no place on a homepage.

| File | Resolution | Codec | Size | Used for |
|---|---|---|---|---|
| `khalifah-field-1080.mp4` | 1920x1080 | H.264 High, yuv420p, CRF 26 | 7.88 MB | `min-width: 768px` |
| `khalifah-field-720.mp4` | 1280x720 | H.264 High, yuv420p, CRF 27 | 3.75 MB | narrow viewports |
| `khalifah-field-poster.jpg` | 1600w | JPEG q5 | 80 KB | poster, and the no-JS still |

Both MP4s are `+faststart` (moov before mdat) so playback can begin before the
file finishes downloading.

No WebM: VP9 at matched quality encoded **larger** than H.264 here (8.69 MB vs
7.88 MB), so it would have been a duplicate master with no delivery benefit.

Regenerate with:

```
ffmpeg -i MASTER.mp4 -vf "scale=1920:1080:flags=lanczos,format=yuv420p" \
  -c:v libx264 -profile:v high -level 4.0 -crf 26 -preset slow \
  -c:a aac -b:a 96k -ar 48000 -movflags +faststart khalifah-field-1080.mp4
```

`core/tests_homepage_khalifah_field.py` asserts these files exist, are H.264
8-bit, are under their size budgets, and are faststart.
