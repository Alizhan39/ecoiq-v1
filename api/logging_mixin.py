"""
api/logging_mixin.py — per-request audit logging for the new commercially-
metered endpoints (api/commercial_views.py). Applied via mixin rather than
global middleware so pre-existing endpoints' behaviour is untouched.
"""
import time

from core.client_origin import client_ip as _resolve_client_ip

from api.models import APIKey, APIRequestLog


class APIRequestLoggingMixin:
    """Mix into a DRF APIView/generic view to record every response to APIRequestLog."""

    def initialize_request(self, request, *args, **kwargs):
        self._ecoiq_start_time = time.monotonic()
        return super().initialize_request(request, *args, **kwargs)

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        try:
            elapsed_ms = int((time.monotonic() - getattr(self, '_ecoiq_start_time', time.monotonic())) * 1000)
            auth = getattr(request, 'auth', None)
            key = auth if isinstance(auth, APIKey) else None
            APIRequestLog.objects.create(
                key=key,
                endpoint=request.path,
                method=request.method,
                status_code=response.status_code,
                response_time_ms=elapsed_ms,
                ip_address=self._client_ip(request),
            )
        except Exception:
            pass  # logging must never break the actual response
        return response

    @staticmethod
    def _client_ip(request):
        """
        The trusted client address, via the single shared resolver.

        Deliberately NOT `X-Forwarded-For.split(',')[0]` — see
        core/client_origin.py for the measured production topology. Entry [0]
        is the client-supplied, forgeable end of the chain, so recording it
        would write an attacker-chosen address into the API audit log.
        """
        return _resolve_client_ip(request)
