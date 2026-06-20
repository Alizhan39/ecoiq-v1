"""
Validate the Tazkiyah 114 pathway mapping (content/tazkiyah114/pathways.json).

Lightweight guardrail for the product-navigation metadata that links user
struggles and Qur'an life pathways to suggested surah numbers. Pure validation —
reads JSON only; touches no models, routes, or views. Exits non-zero on failure.

Run:
    python manage.py validate_tazkiyah114_pathways

Validation logic lives in ``validate_pathways()`` (in the seeds command module)
so tests can reuse it (see core/tests_tazkiyah_pathways.py).
"""
from django.core.management.base import BaseCommand, CommandError

from core.management.commands.validate_tazkiyah114_seeds import (
    DEFAULT_PATHWAYS_PATH,
    validate_pathways,
)


class Command(BaseCommand):
    help = "Validate the Tazkiyah 114 pathway mapping (content/tazkiyah114/pathways.json)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            default=str(DEFAULT_PATHWAYS_PATH),
            help="Path to pathways.json (defaults to the repo file).",
        )

    def handle(self, *args, **options):
        errors = validate_pathways(options["path"])
        if errors:
            self.stderr.write(self.style.ERROR(f"✗ Tazkiyah 114 pathway validation FAILED ({len(errors)} issue(s)):"))
            for e in errors:
                self.stderr.write(self.style.ERROR(f"  - {e}"))
            raise CommandError("Tazkiyah 114 pathway validation failed.")
        self.stdout.write(self.style.SUCCESS("✓ Tazkiyah 114 pathway validation passed: pathways non-empty, surahs in 1-114, caution notes present, all draft/pending, non-authoritative."))
