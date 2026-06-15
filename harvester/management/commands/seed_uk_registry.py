"""
Seed the UK Energy/Utilities/Water/Infrastructure target registry (idempotent).

Usage:
    python manage.py seed_uk_registry

Upserts the phase-1 (first 25) companies from harvester/uk_registry.py, keyed by
slug. Registry only — creates NO evidence and triggers NO harvesting. Re-running
creates no duplicates and refreshes metadata to catalog values.
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Seed/refresh the phase-1 UK target company registry (25 companies)."

    def handle(self, *args, **opts):
        from harvester.models import RegistryCompany
        from harvester.uk_registry import registry_rows

        created = updated = 0
        for row in registry_rows():
            _, was_created = RegistryCompany.objects.update_or_create(
                slug=row["slug"],
                defaults={k: v for k, v in row.items() if k != "slug"},
            )
            created += int(was_created)
            updated += int(not was_created)

        total = RegistryCompany.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f"UK registry seeded: {created} created, {updated} updated, {total} total."))
