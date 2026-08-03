"""
ai_gateway/management/commands/refresh_ai_models.py

    python manage.py refresh_ai_models
    python manage.py refresh_ai_models --explain
    python manage.py refresh_ai_models --dry-run

Fetches each configured provider's catalogue, applies that provider's free
policy and EcoIQ's allowlist, validates capabilities, and rebuilds the cached
runtime registry — reporting what was added, removed and changed since the
previous snapshot.

What it deliberately does NOT do:
  * make an inference request of any kind (catalogue endpoints only);
  * purchase credits or enable auto-reload;
  * auto-approve a model. A model absent from `settings.AI_MODEL_ALLOWLIST`
    stays out of the registry no matter how free it looks. `--explain` shows
    what a human could review, but approving it means editing the allowlist.

Safe to schedule (e.g. hourly) if a scheduler already exists. No scheduler is
created by this change — that would be a paid resource decision.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from ai_gateway.providers import PROVIDER_ORDER, all_providers, get_provider
from ai_gateway.registry import FRESH_CACHE_KEY, registry
from django.core.cache import cache

#: Fields a catalogue survey is allowed to echo. Anything else in an entry is
#: summarised as a key name only — a provider catalogue is third-party data and
#: could contain anything, so it is never dumped verbatim.
_SAFE_SURVEY_FIELDS = ('id', 'model', 'modelId', 'name', 'displayName', 'task',
                       'taskType', 'pipeline_tag', 'meter', 'meterName',
                       'serviceMeter', 'accessMeter', 'tier', 'params',
                       'parameters', 'parameterCount', 'modelSize', 'size',
                       'openSource', 'open_source', 'contextLength',
                       'context_length')


class Command(BaseCommand):
    help = 'Refresh the EcoIQ AI model registry from live provider catalogues.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--explain', action='store_true',
            help='Show why each allowlisted model was rejected.',
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Report what would change without writing the cached registry.',
        )
        parser.add_argument(
            '--provider', choices=list(PROVIDER_ORDER), default=None,
            help='Inspect a single provider. Combine with --dry-run --explain to '
                 'survey a provider catalogue before allowlisting anything.',
        )

    def handle(self, *args, **options):
        if options['provider']:
            return self._survey_provider(options['provider'], explain=options['explain'],
                                         dry_run=options['dry_run'])

        previous = cache.get(FRESH_CACHE_KEY) or {}
        previous_keys = {m['key']: m for m in previous.get('models', [])}

        self.stdout.write(self.style.MIGRATE_HEADING('EcoIQ AI model registry refresh'))

        # ── Provider configuration ────────────────────────────────────────────
        for provider in all_providers():
            if provider.is_configured:
                status = self.style.SUCCESS('configured')
            elif provider.enabled:
                status = self.style.WARNING(f'not usable ({provider.unavailable_reason()})')
            else:
                status = 'disabled'
            self.stdout.write(
                f'  {provider.provider_name:<12} {status}  '
                f'allowlisted={len(provider.allowlist())}'
            )

        # ── Build ─────────────────────────────────────────────────────────────
        snapshot = registry.build()

        current_keys = {m.key: m for m in snapshot.models}
        added = sorted(set(current_keys) - set(previous_keys))
        removed = sorted(set(previous_keys) - set(current_keys))
        changed = []
        for key in sorted(set(current_keys) & set(previous_keys)):
            before, after = previous_keys[key], current_keys[key]
            for field in ('display_name', 'free_policy', 'context_length'):
                if before.get(field) != getattr(after, field):
                    changed.append(f'{key}: {field} {before.get(field)!r} → '
                                   f'{getattr(after, field)!r}')

        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING(
            f'Approved free models: {len(snapshot.models)}'))
        for model in snapshot.models:
            visibility = 'preview/dev-only' if model.development_only else 'public'
            self.stdout.write(
                f'  {model.key:<38} {model.display_name:<24} '
                f'{model.free_policy:<28} {visibility}'
            )
        if not snapshot.models:
            self.stdout.write(self.style.WARNING(
                '  (none — check provider credentials and settings.AI_MODEL_ALLOWLIST)'))

        for label, entries, style in (
            ('Added', added, self.style.SUCCESS),
            ('Removed', removed, self.style.WARNING),
            ('Changed', changed, self.style.WARNING),
        ):
            if entries:
                self.stdout.write('')
                self.stdout.write(style(f'{label}:'))
                for entry in entries:
                    self.stdout.write(f'  {entry}')

        if snapshot.provider_errors:
            self.stdout.write('')
            self.stdout.write(self.style.ERROR('Provider errors (normalised categories):'))
            for provider_name, category in sorted(snapshot.provider_errors.items()):
                self.stdout.write(f'  {provider_name}: {category}')

        if options['explain'] and snapshot.rejected:
            self.stdout.write('')
            self.stdout.write(self.style.MIGRATE_HEADING(
                f'Rejected allowlisted models: {len(snapshot.rejected)}'))
            for model in snapshot.rejected:
                self.stdout.write(
                    f'  {model.provider}/{model.provider_model_id}: {model.rejection_reason}')

        # ── Persist ───────────────────────────────────────────────────────────
        if options['dry_run']:
            self.stdout.write('')
            self.stdout.write(self.style.WARNING('--dry-run: cached registry not written.'))
            return

        registry.invalidate()
        registry.get_snapshot(force_refresh=True)
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'Registry cached. refreshed_at={snapshot.refreshed_at}'))

    # ── Single-provider catalogue survey ──────────────────────────────────────

    def _survey_provider(self, provider_name, *, explain, dry_run):
        """
        Inspect ONE provider's live catalogue and report what its entries
        actually look like — the step that has to happen before a model can be
        allowlisted.

        Catalogue requests only. No inference request, no credit purchase, no
        allowlist write, no automatic approval: this command reports, a human
        decides, and approval happens by editing configuration.
        """
        from ai_gateway.exceptions import ProviderCallError

        provider = get_provider(provider_name)
        self.stdout.write(self.style.MIGRATE_HEADING(
            f'{provider_name} catalogue survey (read-only, no inference)'))

        if not provider.is_configured:
            reason = provider.unavailable_reason()
            self.stdout.write(self.style.WARNING(f'  Provider not usable: {reason}'))
            if reason == 'missing_credentials':
                env_var = provider.api_key_setting
                self.stdout.write('')
                self.stdout.write(f'  Set {env_var}, then run:')
                self.stdout.write(self.style.MIGRATE_LABEL(
                    f'    python manage.py refresh_ai_models --provider {provider_name} '
                    '--dry-run --explain'))
                self.stdout.write('  Review the reported fields, then add the confirmed ids to '
                                  'the provider allowlist')
                self.stdout.write('  (for Bytez: the BYTEZ_APPROVED_MODELS environment '
                                  'variable). Nothing is approved automatically.')
            return

        try:
            entries = provider.fetch_catalog()
        except ProviderCallError as exc:
            self.stdout.write(self.style.ERROR(
                f'  Catalogue unavailable ({exc.category}) — nothing changed.'))
            return

        self.stdout.write(f'  Catalogue returned {len(entries)} entry/entries.')

        # Report the ACTUAL schema, so free-eligibility fields can be confirmed
        # rather than guessed.
        observed = sorted({k for entry in entries for k in entry})
        self.stdout.write(f'  Fields present across entries: {", ".join(observed) or "(none)"}')
        recognised = [f for f in _SAFE_SURVEY_FIELDS if f in observed]
        self.stdout.write(f'  Recognised by the free-policy check: '
                          f'{", ".join(recognised) or "(none — schema differs from expectations)"}')

        allowlist = provider.allowlist()
        self.stdout.write(f'  Currently allowlisted: {len(allowlist)}')

        if not explain:
            self.stdout.write('')
            self.stdout.write('  Re-run with --explain to see the per-model verdict.')
            return

        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING('  Candidate verdicts'))
        accepted = rejected = 0
        for entry in entries:
            model_id = (entry.get('id') or entry.get('model')
                        or entry.get('modelId') or entry.get('name') or '(unnamed)')
            try:
                eligible, policy, reason = provider.evaluate_free_eligibility(entry)
            except Exception as exc:  # noqa: BLE001 — a survey must never crash
                eligible, policy, reason = False, '', f'could not evaluate ({type(exc).__name__})'

            in_allowlist = model_id in allowlist
            if eligible:
                accepted += 1
                note = 'ALLOWLISTED' if in_allowlist else 'candidate — NOT approved'
                self.stdout.write(self.style.SUCCESS(
                    f'    [free:{policy}] {model_id} — {note}'))
            else:
                rejected += 1
                self.stdout.write(f'    [reject]  {model_id} — {reason}')

        self.stdout.write('')
        self.stdout.write(f'  {accepted} would pass the free policy, {rejected} rejected.')
        self.stdout.write(self.style.WARNING(
            '  Nothing was approved. To approve a model, add its exact id to the '
            'provider allowlist'))
        self.stdout.write(self.style.WARNING(
            '  (Bytez: the BYTEZ_APPROVED_MODELS environment variable) and re-run '
            'check_ai_configuration.'))
        if dry_run:
            self.stdout.write('  --dry-run: nothing written.')
