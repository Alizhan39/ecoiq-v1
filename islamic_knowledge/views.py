from dataclasses import asdict

from django.http import JsonResponse
from django.views.decorators.http import require_GET

from companies.throttle import rate_limit
from .catalog import divine_names, surahs
from .models import KnowledgePassage
from .neural import MODEL_VERSION, NeuralUnavailable, semantic_search
from .providers import PROVIDERS, provider_catalog


def passage_json(row):
    return {'id': row.pk, 'provider': row.provider, 'external_id': row.external_id,
            'kind': row.kind, 'passage': row.passage, 'language': row.language,
            'source_url': row.source_url, 'work': row.work, 'edition': row.edition,
            'source_version': row.source_version, 'attribution': row.attribution,
            'surah': row.surah, 'ayah_start': row.ayah_start, 'ayah_end': row.ayah_end,
            'name_key': row.name_key or None, 'enumeration': row.enumeration or None,
            'rights': row.rights, 'source_digest': row.digest,
            'review_status': 'editorially_reviewed', 'religious_ruling': False}


def filters(request):
    provider = request.GET.get('provider')
    language = request.GET.get('language')
    if provider and provider not in PROVIDERS:
        raise ValueError('Unknown provider.')
    if language and (len(language) > 20 or not language.replace('-', '').isalnum()):
        raise ValueError('Invalid language code.')
    return provider, language


@require_GET
def sources(request):
    return JsonResponse({'providers': provider_catalog()})


@require_GET
def surah_index(request):
    return JsonResponse({'count': 114, 'authoritative': False, 'content_type': 'reference_metadata',
                         'source_url': 'https://quran.com',
                         'results': [asdict(row) for row in surahs().values()]})


@require_GET
def name_index(request):
    return JsonResponse({'count': 99, 'authoritative': False, 'content_type': 'reference_metadata',
                         'provider_sources': provider_catalog(),
                         'results': [asdict(row) for row in divine_names().values()]})


@require_GET
def passages(request):
    try:
        provider, language = filters(request)
        limit = int(request.GET.get('limit', 20))
        offset = int(request.GET.get('offset', 0))
        if not 1 <= limit <= 50 or not 0 <= offset <= 10000:
            raise ValueError('Invalid page size or offset.')
        rows = KnowledgePassage.published()
        if provider:
            rows = rows.filter(provider=provider)
        if language:
            rows = rows.filter(language=language)
        if 'surah' in request.GET:
            number = int(request.GET['surah'])
            if number not in surahs():
                raise ValueError('Invalid surah.')
            rows = rows.filter(surah=number)
        if 'name' in request.GET:
            key = request.GET['name']
            if key not in divine_names():
                raise ValueError('Unknown divine-name key.')
            rows = rows.filter(name_key=key)
        page = list(rows[offset:offset + limit + 1])
    except ValueError as exc:
        return JsonResponse({'error': str(exc)}, status=400)
    return JsonResponse({'results': [passage_json(row) for row in page[:limit]],
                         'next_offset': offset + limit if len(page) > limit else None})


@require_GET
@rate_limit('islamic_neural_search', json=True, anon_per_min=5, auth_per_min=10, staff_exempt=False)
def search(request):
    try:
        provider, language = filters(request)
        results = semantic_search(request.GET.get('q', ''), limit=int(request.GET.get('limit', 5)),
                                   provider=provider, language=language)
    except ValueError as exc:
        return JsonResponse({'error': str(exc)}, status=400)
    except NeuralUnavailable as exc:
        return JsonResponse({'status': 'unavailable', 'error': str(exc), 'method': 'neural_cosine',
                             'model': MODEL_VERSION}, status=503)
    return JsonResponse({'method': 'neural_cosine', 'model': MODEL_VERSION,
                         'similarity_is_confidence': False, 'religious_ruling': False,
                         'results': [{**passage_json(row), 'similarity': similarity}
                                     for similarity, row in results]})
