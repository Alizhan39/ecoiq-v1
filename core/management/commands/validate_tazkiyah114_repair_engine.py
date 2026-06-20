"""
Validate the Tazkiyah 114 Repair Engine architecture
(content/tazkiyah114/repair_engine.json).

Lightweight guardrail for the product navigation / reflection architecture that
defines the repair journey (struggle → heart wound → false belief → Qur'anic
theme → surah pathway → reflection → dua → action → 7-day consistency). Pure
validation — reads JSON only; no models, routes, or views. Exits non-zero on
failure.

Run:
    python manage.py validate_tazkiyah114_repair_engine

Validation logic lives in ``validate_repair_engine()`` (in the seeds command
module) so tests can reuse it (see core/tests_tazkiyah_repair_engine.py).
"""
from django.core.management.base import BaseCommand, CommandError

from core.management.commands.validate_tazkiyah114_seeds import (
    DEFAULT_REPAIR_ENGINE_PATH,
    validate_repair_engine,
)


class Command(BaseCommand):
    help = "Validate the Tazkiyah 114 Repair Engine architecture (content/tazkiyah114/repair_engine.json)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            default=str(DEFAULT_REPAIR_ENGINE_PATH),
            help="Path to repair_engine.json (defaults to the repo file).",
        )

    def handle(self, *args, **options):
        errors = validate_repair_engine(options["path"])
        if errors:
            self.stderr.write(self.style.ERROR(f"✗ Tazkiyah 114 repair-engine validation FAILED ({len(errors)} issue(s)):"))
            for e in errors:
                self.stderr.write(self.style.ERROR(f"  - {e}"))
            raise CommandError("Tazkiyah 114 repair-engine validation failed.")
        self.stdout.write(self.style.SUCCESS("✓ Tazkiyah 114 repair-engine validation passed: heart wounds linked to valid struggles/pathways, caution notes present, all draft/pending, cycles present, non-authoritative."))
