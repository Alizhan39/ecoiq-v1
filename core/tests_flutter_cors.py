"""CORS regression tests for the separate Flutter Web origin.

A browser client uses Authorization: Bearer and needs a preflight response,
but untrusted origins must never receive allow-origin headers. CORS does not
grant API access to an unauthenticated caller.
"""

from django.test import SimpleTestCase, override_settings

from core.tests_deployment_safety import load_settings_module, production_env


class FlutterWebCORSSettingsTests(SimpleTestCase):
    def test_no_cross_origin_access_without_explicit_configuration(self):
        ns = load_settings_module(production_env())
        self.assertEqual(ns['CORS_ALLOWED_ORIGINS'], [])
        self.assertFalse(ns['CORS_ALLOW_ALL_ORIGINS'])
        self.assertFalse(ns['CORS_ALLOW_CREDENTIALS'])
        self.assertEqual(ns['CORS_URLS_REGEX'], r'^/api/')

    def test_explicit_https_origin_is_accepted(self):
        ns = load_settings_module(production_env(
            ECOIQ_CORS_ALLOWED_ORIGINS='https://app.ecoiq.uk',
        ))
        self.assertEqual(ns['CORS_ALLOWED_ORIGINS'], ['https://app.ecoiq.uk'])

    def test_wildcard_and_insecure_origins_refused_in_production(self):
        from django.core.exceptions import ImproperlyConfigured

        for origin in ('*', 'http://app.ecoiq.uk',
                       'https://*.ecoiq.uk',
                       'https://app.ecoiq.uk/anything',
                       'https://alice:pw@app.ecoiq.uk'):
            with self.subTest(origin=origin), self.assertRaises(ImproperlyConfigured):
                load_settings_module(production_env(
                    ECOIQ_CORS_ALLOWED_ORIGINS=origin,
                ))


class FlutterWebCORSResponseTests(SimpleTestCase):
    @override_settings(CORS_ALLOWED_ORIGINS=['https://app.ecoiq.uk'])
    def test_browser_preflight_is_allowed_only_for_trusted_origin(self):
        response = self.client.options(
            '/api/v1/app-config/',
            HTTP_ORIGIN='https://app.ecoiq.uk',
            HTTP_ACCESS_CONTROL_REQUEST_METHOD='GET',
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS='authorization,content-type',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Access-Control-Allow-Origin'], 'https://app.ecoiq.uk')
        self.assertIn('authorization', response['Access-Control-Allow-Headers'].lower())

        blocked = self.client.options(
            '/api/v1/app-config/',
            HTTP_ORIGIN='https://malicious.example',
            HTTP_ACCESS_CONTROL_REQUEST_METHOD='GET',
        )
        self.assertNotIn('Access-Control-Allow-Origin', blocked)

    @override_settings(CORS_ALLOWED_ORIGINS=['https://app.ecoiq.uk'])
    def test_cors_is_not_enabled_on_non_api_routes(self):
        response = self.client.options(
            '/healthz/',
            HTTP_ORIGIN='https://app.ecoiq.uk',
            HTTP_ACCESS_CONTROL_REQUEST_METHOD='GET',
        )
        self.assertNotIn('Access-Control-Allow-Origin', response)
