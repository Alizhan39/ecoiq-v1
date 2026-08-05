"""
Map the STRIPE_PRICE_* environment variables onto local Plan rows.

Why a command rather than a migration or a literal in source: price ids
differ between the test-mode and live-mode Stripe accounts, so baking them
into a migration would either be wrong in one environment or force a code
change to switch. This copies whatever the running environment is configured
with onto the catalogue, and reports honestly on anything it could not map.

Entitlements depend on this. A Stripe subscription whose price is not mapped
to a Plan is still recorded with its Stripe ids, but grants no features —
stripe_sync.upsert_subscription() skips provisioning and says so — because
EcoIQ has no way to know which features were bought.
"""
from django.conf import settings
from django.core.management.base import BaseCommand

from ecoiq_commerce.models import Plan
from ecoiq_commerce.services import stripe_gateway


class Command(BaseCommand):
    help = 'Copy configured STRIPE_PRICE_* ids onto matching ecoiq_commerce Plan rows.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Report what would change without writing anything.')
        parser.add_argument(
            '--plan-key-template', default='{tier}-{interval}',
            help='How a (tier, interval) pair maps to a Plan.key. '
                 'Default: "{tier}-{interval}" → starter-monthly, pro-yearly, …')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        template = options['plan_key_template']

        configured = stripe_gateway.configured_subscription_prices()
        if not configured:
            self.stdout.write(self.style.WARNING(
                'No STRIPE_PRICE_* environment variables are set — nothing to sync. '
                'Create the prices in the Stripe Dashboard first.'))
            return

        updated = unchanged = missing = 0

        for (tier, interval), price_id in sorted(configured.items()):
            plan_key = template.format(tier=tier, interval=interval)
            plan = Plan.objects.filter(key=plan_key).first()

            if plan is None:
                missing += 1
                self.stdout.write(self.style.WARNING(
                    f'  no Plan with key "{plan_key}" — {tier}/{interval} '
                    f'({price_id}) left unmapped'))
                continue

            if plan.stripe_price_id == price_id:
                unchanged += 1
                self.stdout.write(f'  {plan_key}: already {price_id}')
                continue

            previous = plan.stripe_price_id or '(unset)'
            if not dry_run:
                plan.stripe_price_id = price_id
                plan.save(update_fields=['stripe_price_id', 'updated_at'])
            updated += 1
            self.stdout.write(self.style.SUCCESS(
                f'  {plan_key}: {previous} → {price_id}'
                + (' [dry run]' if dry_run else '')))

        # State the live-mode fact plainly rather than leaving it implied.
        mode = 'LIVE' if settings.STRIPE_SECRET_KEY.startswith('sk_live_') else 'test'
        self.stdout.write('')
        self.stdout.write(
            f'{updated} updated, {unchanged} already correct, {missing} unmapped '
            f'(Stripe {mode} mode).')
        if missing:
            self.stdout.write(self.style.WARNING(
                'Unmapped prices grant no entitlements. Create the matching Plan '
                'rows, or pass --plan-key-template to match your existing keys.'))
