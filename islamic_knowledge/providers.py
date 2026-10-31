"""Provider identities and a bounded adapter for agreed JSON export feeds.

No public Quran/content API was established for either provider. Operators must
configure an agreed feed URL or import an authorised normalised export file.
"""
from urllib.parse import urlsplit

import requests
from django.conf import settings

PROVIDERS = {
    'sajda': {
        'label': 'Sajda', 'homepage': 'https://sajda.com/en',
        'names_url': 'https://faq.sajda.app/en/question/113',
        'hosts': ('sajda.com', 'www.sajda.com', 'sajda.app', 'faq.sajda.app'),
    },
    'azan_kz': {
        'label': 'Azan.kz', 'homepage': 'https://azan.kz/',
        'names_url': 'https://azan.kz/durus/dars/99-imyon-Allaha-97',
        'hosts': ('azan.kz', 'www.azan.kz'),
    },
}
MAX_FEED_BYTES = 2 * 1024 * 1024


class ProviderUnavailable(RuntimeError):
    pass


def validate_source_url(provider, url):
    if provider not in PROVIDERS or not isinstance(url, str):
        raise ValueError('Unknown provider or invalid source URL.')
    parsed = urlsplit(url)
    if (parsed.scheme != 'https' or parsed.hostname not in PROVIDERS[provider]['hosts']
            or parsed.username or parsed.password or parsed.port not in (None, 443)):
        raise ValueError('Source URL must be HTTPS on the selected provider host.')
    return url


def provider_catalog():
    feeds = settings.ISLAMIC_KNOWLEDGE_FEEDS
    return [{'id': key, 'label': row['label'], 'homepage': row['homepage'],
             'names_url': row['names_url'], 'public_content_api_verified': False,
             'integration_status': 'configured_feed' if feeds.get(key) else 'awaiting_agreed_feed',
             'import_method': 'authorised_json_export'} for key, row in PROVIDERS.items()]


def fetch_feed(provider):
    if provider not in PROVIDERS:
        raise ValueError('Unknown provider.')
    url = settings.ISLAMIC_KNOWLEDGE_FEEDS.get(provider)
    if not url:
        raise ProviderUnavailable('No agreed feed configured for this provider.')
    validate_source_url(provider, url)
    # No redirects: a provider response cannot move the request to another host.
    try:
        with requests.get(url, timeout=(3, 10), allow_redirects=False, stream=True) as response:
            if response.status_code != 200:
                raise ProviderUnavailable('Provider feed did not return HTTP 200.')
            media_type = response.headers.get('Content-Type', '').split(';', 1)[0].strip().lower()
            if media_type != 'application/json':
                raise ProviderUnavailable('Provider feed must return JSON.')
            data = bytearray()
            for chunk in response.iter_content(chunk_size=8192):
                data.extend(chunk)
                if len(data) > MAX_FEED_BYTES:
                    raise ProviderUnavailable('Provider feed exceeds the import size limit.')
    except requests.RequestException as exc:
        # Callers get a stable error without echoing URLs or transport details.
        raise ProviderUnavailable('Provider feed could not be retrieved.') from exc
    import json
    try:
        return json.loads(data)
    except (ValueError, UnicodeError) as exc:
        raise ProviderUnavailable('Provider feed contains invalid JSON.') from exc
