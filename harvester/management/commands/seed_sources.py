"""
Seed the global Source Registry (idempotent).

Usage:
    python manage.py seed_sources

Upserts the global source catalog from harvester/source_registry.py, keyed by
(source_type, name, company=None). Re-running creates no duplicates and updates
base trust / cadence / active flag to the catalog values.
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Seed/refresh the global Evidence Harvester Source Registry."

    def handle(self, *args, **opts):
        from harvester.models import Source
        from harvester.source_registry import catalog_rows

        created = updated = 0
        for row in catalog_rows():
            obj, was_created = Source.objects.update_or_create(
                source_type=row["source_type"],
                name=row["name"],
                company=None,
                defaults={
                    "source_owner": row["source_owner"],
                    "source_url": row["source_url"],
                    "confidence_base": row["confidence_base"],
                    "update_frequency": row["update_frequency"],
                    "is_active": row["is_active"],
                },
            )
            created += int(was_created)
            updated += int(not was_created)

        self.stdout.write(self.style.SUCCESS(
            f"Source Registry seeded: {created} created, {updated} updated, "
            f"{Source.objects.filter(company__isnull=True).count()} global sources total."))
