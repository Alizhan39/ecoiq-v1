"""Curated integration options, not a claim that twenty engines are installed.

Only React and model-viewer are direct runtime dependencies in frontend/web.
Alternatives are discoverable through the API without importing their code.
"""


def _library(key, name, category, purpose, docs, status='OPTION'):
    return {'id': key, 'name': name, 'category': category,
            'purpose': purpose, 'documentation_url': docs, 'status': status}


LIBRARIES = (
    _library('react', 'React', 'ui', 'Component interface', 'https://react.dev/', 'INTEGRATED'),
    _library('htmx', 'htmx', 'ui', 'Django HTML fragment updates', 'https://htmx.org/docs/'),
    _library('alpine', 'Alpine.js', 'ui', 'Small template interactions', 'https://alpinejs.dev/'),
    _library('query', 'TanStack Query', 'ui', 'Server state and request caching', 'https://tanstack.com/query/latest'),
    _library('table', 'TanStack Table', 'ui', 'Filtering and sorting tables', 'https://tanstack.com/table/latest'),
    _library('radix', 'Radix UI', 'ui', 'Accessible interaction primitives', 'https://www.radix-ui.com/primitives'),
    _library('motion', 'Motion', 'ui', 'Motion and transitions', 'https://motion.dev/docs'),
    _library('d3', 'D3', 'ui', 'Custom interactive data graphics', 'https://d3js.org/'),
    _library('echarts', 'Apache ECharts', 'ui', 'Interactive charts', 'https://echarts.apache.org/en/index.html'),
    _library('zustand', 'Zustand', 'ui', 'Shared client state', 'https://zustand.docs.pmnd.rs/'),
    _library('model-viewer', 'model-viewer', 'ar', '3D models and device AR handoff', 'https://modelviewer.dev/docs/', 'INTEGRATED'),
    _library('three', 'Three.js', 'ar', 'Custom 3D and WebXR scenes', 'https://threejs.org/'),
    _library('fiber', 'React Three Fiber', 'ar', 'React renderer for Three.js', 'https://r3f.docs.pmnd.rs/'),
    _library('drei', 'Drei', 'ar', 'Helpers for React Three Fiber', 'https://drei.docs.pmnd.rs/'),
    _library('xr', 'React XR', 'ar', 'WebXR interactions for React Three Fiber', 'https://pmndrs.github.io/xr/docs/'),
    _library('babylon', 'Babylon.js', 'ar', '3D engine with WebXR support', 'https://doc.babylonjs.com/features/featuresDeepDive/webXR/introToWebXR'),
    _library('aframe', 'A-Frame', 'ar', 'Declarative immersive scenes', 'https://aframe.io/docs/'),
    _library('arjs', 'AR.js', 'ar', 'Marker and location based AR', 'https://ar-js-org.github.io/AR.js-Docs/'),
    _library('mindar', 'MindAR', 'ar', 'Image and face tracking', 'https://hiukim.github.io/mind-ar-js-doc/'),
    _library('playcanvas', 'PlayCanvas', 'ar', 'Interactive 3D engine with XR support', 'https://developer.playcanvas.com/user-manual/xr/'),
)

# The dimensions are design geometry in metres, never measured asset data.
DEMO_PARTS = (
    {'id': 'energy', 'position': '-0.8 0.35 0', 'normal': '0 1 0',
     'labels': {'en': 'Energy', 'ru': 'Энергия', 'kk': 'Энергия', 'ar': 'الطاقة'}},
    {'id': 'water', 'position': '0 0.6 0', 'normal': '0 1 0',
     'labels': {'en': 'Water', 'ru': 'Вода', 'kk': 'Су', 'ar': 'المياه'}},
    {'id': 'materials', 'position': '0.8 0.25 0', 'normal': '0 1 0',
     'labels': {'en': 'Materials', 'ru': 'Материалы', 'kk': 'Материалдар', 'ar': 'المواد'}},
)
