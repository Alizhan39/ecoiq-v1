"""Local browser harness: real compiled assets, catalogue-backed API fixtures.

This is not Django integration, production HTTPS, or an AR hardware test.
"""
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from api.interactive_catalog import DEMO_PARTS, LIBRARIES  # noqa: E402


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        url = urlsplit(self.path)
        body = None
        if url.path == '/api/v2/interactive/libraries/':
            body = {'count': len(LIBRARIES), 'results': LIBRARIES}
        elif url.path == '/api/v2/interactive/scenes/stewardship-demo/':
            lang = parse_qs(url.query).get('lang', ['en'])[0]
            if lang not in ('en', 'ru', 'kk', 'ar'):
                self.send_error(400)
                return
            body = {'id': 'stewardship-demo', 'language': lang,
                    'direction': 'rtl' if lang == 'ar' else 'ltr',
                    'is_demo': True, 'verified': False, 'scale_is_measured': False,
                    'model_url': '/static/models/stewardship-demo.glb',
                    'ar_modes': ['webxr', 'scene-viewer', 'quick-look'],
                    'hotspots': [dict(id=p['id'], label=p['labels'][lang],
                                      position=p['position'], normal=p['normal'],
                                      measurement=None, evidence_url=None) for p in DEMO_PARTS]}
        elif url.path == '/labs/interactive/':
            self.path = '/static/spa/index.html'
        if body is not None:
            payload = json.dumps(body).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        else:
            super().do_GET()


if __name__ == '__main__':
    ThreadingHTTPServer(('127.0.0.1', 4173), Handler).serve_forever()
