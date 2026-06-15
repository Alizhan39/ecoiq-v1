"""
Seed the international target registry — Kazakhstan / Saudi Arabia / Türkiye
(idempotent). Registries first; documents and harvesting follow.

Usage:
    python manage.py seed_country_registries

Upserts the companies from harvester/intl_registry.py keyed by slug. Registry
only — creates NO evidence and triggers NO harvesting.
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Seed/refresh the KZ/SA/TR target company registry."

    def handle(self, *args, **opts):
        from harvester.models import RegistryCompany
        from harvester.intl_registry import registry_rows

        created = updated = 0
        for row in registry_rows():
            _, was_created = RegistryCompany.objects.update_or_create(
                slug=row["slug"],
                defaults={k: v for k, v in row.items() if k != "slug"},
            )
            created += int(was_created)
            updated += int(not was_created)

        from collections import Counter
        dist = dict(Counter(RegistryCompany.objects.exclude(country="GB")
                            .values_list("country", flat=True)))
        self.stdout.write(self.style.SUCCESS(
            f"Country registries seeded: {created} created, {updated} updated. "
            f"Non-UK distribution: {dist}"))
