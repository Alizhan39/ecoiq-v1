"""Read-only interactive API. No private assets, uploads or remote URL fetching."""
from django.templatetags.static import static
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from api.interactive_catalog import DEMO_PARTS, LIBRARIES

LANGUAGES = ('en', 'ru', 'kk', 'ar')


@api_view(['GET'])
@permission_classes([AllowAny])
def libraries(request):
    category = request.query_params.get('category')
    if category is not None and category not in ('ui', 'ar'):
        return Response({'detail': 'category must be ui or ar.'}, status=400)
    rows = [row for row in LIBRARIES if category is None or row['category'] == category]
    return Response({'schema_version': 1, 'count': len(rows), 'results': rows})


@api_view(['GET'])
@permission_classes([AllowAny])
def scenes(request):
    return Response({'schema_version': 1, 'count': 1, 'results': [{
        'id': 'stewardship-demo', 'is_demo': True, 'verified': False,
        'detail_url': '/api/v2/interactive/scenes/stewardship-demo/',
        'languages': list(LANGUAGES),
    }]})


@api_view(['GET'])
@permission_classes([AllowAny])
def scene(request, scene_id):
    if scene_id != 'stewardship-demo':
        return Response({'detail': 'Not found.'}, status=404)
    language = request.query_params.get('lang', 'en')
    if language not in LANGUAGES:
        return Response({'detail': 'lang must be en, ru, kk or ar.'}, status=400)
    return Response({
        'schema_version': 1, 'id': scene_id, 'language': language,
        'direction': 'rtl' if language == 'ar' else 'ltr',
        'is_demo': True, 'verified': False, 'status': 'EXPERIMENTAL',
        'model_url': static('models/stewardship-demo.glb'),
        'ar_modes': ['webxr', 'scene-viewer', 'quick-look'],
        'scale_is_measured': False,
        'hotspots': [{'id': part['id'], 'label': part['labels'][language],
                      'position': part['position'], 'normal': part['normal'],
                      'evidence_url': None, 'measurement': None}
                     for part in DEMO_PARTS],
    })
