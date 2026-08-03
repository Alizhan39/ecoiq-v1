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

from ai_gateway.providers import all_providers
from ai_gateway.registry import FRESH_CACHE_KEY, registry
from django.core.cache import cache


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

    def handle(self, *args, **options):
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
