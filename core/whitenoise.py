"""
core/whitenoise.py — immutable caching for the Vite-built SPA assets.

WhiteNoise decides a file is immutable by recognising Django's own hashing
convention: `name.<md5>.ext`, produced by ManifestStaticFilesStorage. Vite
hashes with a DASH — `index-DkP2Xy1s.js` — so WhiteNoise does not recognise it
and serves the SPA's bundle with the default 60-second cache header.

That is the wrong answer for a file whose name changes whenever its contents
do. Every deploy already produces new filenames, so `immutable` is safe by
construction, and without it every returning visitor re-validates the whole
bundle on every navigation.

Only the assets directory is covered. `index.html` is served by core/spa.py
with `no-store`, because it is the one file whose name never changes and whose
contents must not be stale — it is what names the hashed assets.
"""
from __future__ import annotations

from whitenoise.middleware import WhiteNoiseMiddleware


class SpaAwareWhiteNoiseMiddleware(WhiteNoiseMiddleware):
    """WhiteNoise, plus recognition of Vite's content-hashed filenames."""

    def immutable_file_test(self, path, url) -> bool:
        if url.startswith(f'{self.static_prefix}spa/assets/'):
            return True
        return super().immutable_file_test(path, url)
