"""
ai_gateway/management/commands/check_ai_configuration.py

    python manage.py check_ai_configuration
    python manage.py check_ai_configuration --live-catalog

Safe, local validation of the EcoIQ AI gateway configuration. By default it
touches no network at all — it reads Django settings and the cached registry
and reports whether this deployment is safe to run.

Hard guarantees:
  * never makes an inference request, with or without --live-catalog;
  * never purchases credits or enables auto-reload;
  * never modifies settings, allowlists or the registry;
  * never prints a secret, in whole or in part — a configured key is reported
    only as the word "set".

Exit codes:
  0  safe (possibly with warnings)
  1  unsafe — at least one blocking error

The distinction matters operationally: a warning ("Bytez has no approved
models") means a capability is missing; an error ("paid models enabled") means
the deployment could spend money and must not ship.
"""
from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand

from ai_gateway.providers import all_providers
from ai_gateway.registry import registry
from ai_gateway.routing import AUDIENCE_PUBLIC, RoutingProfile, build_chain

PASS, WARN, FAIL = 'PASS', 'WARN', 'FAIL'

#: Never printed. Used only to assert that nothing else in this report echoes a
#: secret value back to the terminal.
_SECRET_SETTINGS = ('OPENROUTER_API_KEY', 'BYTEZ_API_KEY', 'NVIDIA_NIM_API_KEY',
                    'ANTHROPIC_API_KEY', 'SECRET_KEY', 'DJANGO_SECRET_KEY')


class Command(BaseCommand):
    help = 'Validate the EcoIQ AI gateway configuration without calling any model.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--live-catalog', action='store_true',
            help='Additionally perform READ-ONLY provider catalogue checks. '
                 'Still never makes an inference request and never approves a model.',
        )

    # ── Reporting ─────────────────────────────────────────────────────────────

    def _record(self, status, message):
        self.results.append((status, message))

    def handle(self, *args, **options):
        self.results: list[tuple[str, str]] = []

        self._check_policy()
        self._check_routing()
        self._check_providers()
        self._check_registry()
        self._check_public_input_safety()

        if options['live_catalog']:
            self._check_live_catalog()

        return self._report()

    # ── Policy ────────────────────────────────────────────────────────────────

    def _check_policy(self):
        if getattr(settings, 'AI_ENABLED', True):
            self._record(PASS, 'AI gateway enabled')
        else:
            self._record(WARN, 'AI gateway disabled (AI_ENABLED=false)')

        if settings.AI_FREE_ONLY:
            self._record(PASS, 'Free-only policy enabled')
        else:
            self._record(FAIL, 'AI_FREE_ONLY is false — paid models could be reached')

        if not settings.AI_ALLOW_PAID_MODELS:
            self._record(PASS, 'Paid models disabled')
        else:
            self._record(FAIL, 'AI_ALLOW_PAID_MODELS is true — paid spend is possible')

    def _check_routing(self):
        selection = getattr(settings, 'AI_MODEL_SELECTION_MODE', 'automatic')
        routing = getattr(settings, 'AI_ROUTING_MODE', 'automatic')
        if selection == 'automatic' and routing == 'automatic':
            self._record(PASS, 'Automatic routing enabled')
        elif selection == 'user':
            self._record(WARN, 'AI_MODEL_SELECTION_MODE=user — public model selection is exposed')
        else:
            self._record(WARN, f'Routing mode is {selection}/{routing}, not automatic/automatic')

        attempts = int(getattr(settings, 'AI_MAX_PROVIDER_ATTEMPTS', 0))
        if attempts < 1:
            self._record(FAIL, f'AI_MAX_PROVIDER_ATTEMPTS={attempts} — no attempt would be made')
        elif attempts > 5:
            self._record(WARN, f'AI_MAX_PROVIDER_ATTEMPTS={attempts} is high; a failing '
                               'request will keep a worker busy')
        else:
            self._record(PASS, f'Provider attempts capped at {attempts}')

        if getattr(settings, 'AI_ALLOW_AUTOMATIC_FALLBACK', False):
            self._record(PASS, 'Free-pool fallback enabled')
        else:
            self._record(WARN, 'Automatic fallback disabled — a single failure ends the request')

        cache_seconds = int(getattr(settings, 'AI_MODEL_CATALOG_CACHE_SECONDS', 0))
        if cache_seconds <= 0:
            self._record(FAIL, 'AI_MODEL_CATALOG_CACHE_SECONDS must be positive — '
                               'provider catalogues would be refetched constantly')
        else:
            self._record(PASS, f'Catalogue cached for {cache_seconds}s')

    # ── Providers ─────────────────────────────────────────────────────────────

    def _check_providers(self):
        for provider in all_providers():
            name = provider.provider_name
            base_url = self._base_url(name)
            if base_url and not base_url.startswith('https://'):
                self._record(FAIL, f'{name}: base URL is not https')

            if not provider.enabled:
                self._record(WARN, f'{name} disabled')
                continue
            if not provider.api_key:
                # Reported as absence, never as a partial value.
                self._record(WARN, f'{name} enabled but its API key is not set')
                continue
            self._record(PASS, f'{name} configured')

        if settings.OPENROUTER_FREE_ROUTER_ENABLED:
            router_model = settings.OPENROUTER_FREE_ROUTER_MODEL
            if router_model in settings.AI_MODEL_ALLOWLIST.get('openrouter', set()):
                self._record(PASS, f'OpenRouter free router allowlisted ({router_model})')
            else:
                self._record(FAIL, f'OpenRouter free router {router_model} is enabled but '
                                   'not in AI_MODEL_ALLOWLIST — the public catch-all is missing')
        else:
            self._record(WARN, 'OpenRouter free router disabled — no public catch-all route')

        # Bytez
        bytez_allowlist = settings.AI_MODEL_ALLOWLIST.get('bytez', set())
        if not bytez_allowlist:
            self._record(WARN, 'Bytez has no approved models — run '
                               '`refresh_ai_models --provider bytez --dry-run --explain` '
                               'with BYTEZ_API_KEY set, then populate BYTEZ_APPROVED_MODELS')
        else:
            self._record(PASS, f'Bytez allowlist has {len(bytez_allowlist)} model(s)')
        if settings.AI_FREE_ONLY and settings.BYTEZ_ALLOW_PAID_CREDITS:
            self._record(FAIL, 'BYTEZ_ALLOW_PAID_CREDITS is true under AI_FREE_ONLY — '
                               'a "free" request could spend credits')

        # NVIDIA
        if settings.NVIDIA_NIM_PUBLIC_PRODUCTION_ENABLED:
            self._record(FAIL, 'NVIDIA_NIM_PUBLIC_PRODUCTION_ENABLED is true — NVIDIA '
                               'Developer Program endpoints are prototype access and need '
                               'separate licensing approval before public production traffic')
        else:
            self._record(PASS, 'NVIDIA public production disabled')
        if settings.NVIDIA_NIM_PROTOTYPE_ONLY:
            self._record(PASS, 'NVIDIA marked development-only')
        else:
            self._record(WARN, 'NVIDIA_NIM_PROTOTYPE_ONLY is false — the second safety '
                               'latch on NVIDIA access is off')

    @staticmethod
    def _base_url(provider_name):
        return {
            'openrouter': getattr(settings, 'OPENROUTER_BASE_URL', ''),
            'bytez': getattr(settings, 'BYTEZ_OPENAI_BASE_URL', ''),
            'nvidia_nim': getattr(settings, 'NVIDIA_NIM_BASE_URL', ''),
        }.get(provider_name, '')

    # ── Registry + routing reachability ───────────────────────────────────────

    def _check_registry(self):
        # peek_cached(), never get_snapshot(): the latter would fetch provider
        # catalogues on a cold cache, and this command must make no network
        # call unless --live-catalog was passed.
        snapshot = registry.peek_cached()
        if snapshot is None:
            self._record(WARN, 'Registry not cached yet — run `refresh_ai_models` to '
                               'validate the live model set (skipping registry checks)')
            return

        paid = [m for m in snapshot.models if not m.free_eligible]
        if paid:
            self._record(FAIL, f'{len(paid)} paid model(s) present in the registry')
        else:
            self._record(PASS, 'No paid models in the registry')

        public_models = registry.visible_models(None, snapshot=snapshot)
        dev_public = [m for m in public_models if m.development_only]
        if dev_public:
            self._record(FAIL, f'{len(dev_public)} development-only model(s) visible to '
                               'public users')
        else:
            self._record(PASS, 'No development-only models in public routing')

        profile = RoutingProfile(audience=AUDIENCE_PUBLIC)
        chain = build_chain(public_models, profile)
        if not chain:
            self._record(WARN, 'Default public routing has no available model right now '
                               '(requests will return FREE_MODELS_UNAVAILABLE)')
        else:
            self._record(PASS, f'Default public routing has {len(chain)} route(s)')

        # Loop check: a chain must never repeat a key, and must respect the cap.
        keys = [m.key for m in chain]
        if len(keys) != len(set(keys)):
            self._record(FAIL, 'Routing chain contains a repeated model — fallback could loop')
        elif len(keys) > int(settings.AI_MAX_PROVIDER_ATTEMPTS):
            self._record(FAIL, 'Routing chain is longer than AI_MAX_PROVIDER_ATTEMPTS')
        else:
            self._record(PASS, 'No fallback loop possible')

    def _check_public_input_safety(self):
        """
        Assert that the fields a browser could send cannot steer routing. This
        is a live check of the running code path, not a re-reading of settings.
        """
        import logging

        from ai_gateway.exceptions import InvalidAIRequest
        from ai_gateway.service import REJECTED_ROUTING_FIELDS, reject_untrusted_routing_fields

        # The probe deliberately trips the rejection path once per field, which
        # would otherwise emit a warning line each time and bury the report.
        gateway_logger = logging.getLogger('ecoiq.ai_gateway')
        previous_level = gateway_logger.level
        gateway_logger.setLevel(logging.ERROR)
        try:
            leaked = []
            for field in REJECTED_ROUTING_FIELDS:
                try:
                    reject_untrusted_routing_fields({field: 'x'})
                except InvalidAIRequest:
                    continue
                leaked.append(field)
        finally:
            gateway_logger.setLevel(previous_level)
        if leaked:
            self._record(FAIL, f'Public API accepts routing field(s): {", ".join(leaked)}')
        else:
            self._record(PASS, 'No raw provider/model input accepted from public API')

        # And that the report itself contains no secret.
        secrets = [str(getattr(settings, name, '')) for name in _SECRET_SETTINGS]
        secrets = [s for s in secrets if len(s) >= 8]
        printed = ' '.join(message for _status, message in self.results)
        if any(s in printed for s in secrets):
            self._record(FAIL, 'A secret value appeared in this report')
        else:
            self._record(PASS, 'No secrets exposed')

    # ── Optional read-only catalogue check ────────────────────────────────────

    def _check_live_catalog(self):
        """
        READ-ONLY. Fetches each configured provider's catalogue endpoint to
        confirm it is reachable and parseable. Makes no inference request,
        approves nothing, writes nothing.
        """
        from ai_gateway.exceptions import ProviderCallError

        self._record(PASS, '--live-catalog: read-only catalogue checks (no inference)')
        for provider in all_providers():
            if not provider.is_configured:
                self._record(WARN, f'{provider.provider_name}: skipped (not configured)')
                continue
            try:
                entries = provider.fetch_catalog()
            except ProviderCallError as exc:
                # Normalised category only — never the upstream body.
                self._record(WARN, f'{provider.provider_name}: catalogue unreachable '
                                   f'({exc.category})')
                continue
            except Exception:  # noqa: BLE001
                self._record(WARN, f'{provider.provider_name}: catalogue check failed')
                continue
            self._record(PASS, f'{provider.provider_name}: catalogue reachable '
                               f'({len(entries)} entries, nothing approved)')

    # ── Output ────────────────────────────────────────────────────────────────

    def _report(self):
        self.stdout.write('AI configuration check')
        styles = {PASS: self.style.SUCCESS, WARN: self.style.WARNING, FAIL: self.style.ERROR}
        for status, message in self.results:
            self.stdout.write(styles[status](f'[{status}] {message}'))

        warnings = sum(1 for s, _ in self.results if s == WARN)
        errors = sum(1 for s, _ in self.results if s == FAIL)

        if errors:
            summary = f'Result: UNSAFE — {errors} error(s), {warnings} warning(s)'
            self.stdout.write(self.style.ERROR(summary))
            # Non-zero exit for unsafe production configuration.
            raise SystemExit(1)

        if warnings:
            summary = f'Result: safe with {warnings} warning(s)'
        else:
            summary = 'Result: safe'
        self.stdout.write(self.style.SUCCESS(summary))
        return None
