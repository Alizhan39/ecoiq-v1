"""
Validate the Tazkiyah 114 surah seed dataset.

A lightweight guardrail so future changes cannot accidentally break the
114-surah seed structure (content/tazkiyah114/surah_seeds.json). Pure
validation — reads the JSON only; touches no models, routes, or views.

Run:
    python manage.py validate_tazkiyah114_seeds

Exits non-zero if any check fails (suitable for CI). The validation logic
lives in ``validate_seeds()`` so tests can reuse it (see
core/tests_tazkiyah_seeds.py).
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

# Repo root → content/tazkiyah114/surah_seeds.json
# (this file: core/management/commands/validate_tazkiyah114_seeds.py)
DEFAULT_SEED_PATH = (
    Path(__file__).resolve().parents[3] / "content" / "tazkiyah114" / "surah_seeds.json"
)

EXPECTED_FIELDS = [
    "surah_number",
    "surah_name_arabic",
    "surah_name_transliteration",
    "surah_name_translation",
    "revelation_type",
    "short_theme",
    "life_pathways",
    "repair_areas",
    "content_status",
    "source_status",
    "translation_status",
    "tafsir_status",
    "scholar_review_status",
    "wellbeing_review_required",
    "sensitivity_level",
    "reviewed_by",
    "last_reviewed_at",
    "notes",
]

REQUIRED_STATUS = {
    "content_status": "draft_reflection",
    "translation_status": "translation_pending",
    "scholar_review_status": "scholar_review_pending",
}

SAFETY_PHRASE = "reflection inspired by qur'anic themes"


def validate_seeds(path=DEFAULT_SEED_PATH):
    """Return a list of error strings. Empty list means the dataset is valid."""
    errors = []
    path = Path(path)

    # 1. JSON parses cleanly.
    if not path.exists():
        return [f"Seed file not found: {path}"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"JSON does not parse: {exc}"]

    surahs = data.get("surahs")
    if not isinstance(surahs, list):
        return ["Top-level 'surahs' array is missing or not a list."]

    # 2. Exactly 114 records.
    if len(surahs) != 114:
        errors.append(f"Expected 114 surah records, found {len(surahs)}.")

    numbers = [s.get("surah_number") for s in surahs]

    # 3. Contiguous 1-114.
    if sorted(n for n in numbers if isinstance(n, int)) != list(range(1, 115)):
        errors.append("Surah numbers are not contiguous 1-114.")

    # 4. Unique.
    if len(set(numbers)) != len(numbers):
        errors.append("Surah numbers are not unique (duplicates found).")

    # 5-9. Per-record checks.
    for i, s in enumerate(surahs):
        sid = s.get("surah_number", f"index {i}")
        # 5. Identical expected 18-field schema/order.
        if list(s.keys()) != EXPECTED_FIELDS:
            errors.append(f"Surah {sid}: field set/order does not match the expected 18-field schema.")
        # 6. Required draft/pending statuses.
        for field, expected in REQUIRED_STATUS.items():
            if s.get(field) != expected:
                errors.append(f"Surah {sid}: {field} must be '{expected}', got {s.get(field)!r}.")
        # 9. Required safety notes (humble framing, non-empty).
        notes = s.get("notes")
        if not isinstance(notes, str) or not notes.strip():
            errors.append(f"Surah {sid}: missing safety 'notes'.")
        elif SAFETY_PHRASE not in notes.lower():
            errors.append(f"Surah {sid}: notes must include the humble framing '{SAFETY_PHRASE}'.")

    # 7. _meta.authoritative is false.
    meta = data.get("_meta", {})
    if meta.get("authoritative") is not False:
        errors.append("_meta.authoritative must be false.")

    # 8. _meta.scope mentions all 114 surahs.
    scope = str(meta.get("scope", "")).lower()
    if "all 114 surahs" not in scope:
        errors.append("_meta.scope must indicate coverage of all 114 surahs.")

    return errors


class Command(BaseCommand):
    help = "Validate the Tazkiyah 114 surah seed dataset (content/tazkiyah114/surah_seeds.json)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            default=str(DEFAULT_SEED_PATH),
            help="Path to surah_seeds.json (defaults to the repo seed file).",
        )

    def handle(self, *args, **options):
        path = options["path"]
        errors = validate_seeds(path)
        if errors:
            self.stderr.write(self.style.ERROR(f"✗ Tazkiyah 114 seed validation FAILED ({len(errors)} issue(s)):"))
            for e in errors:
                self.stderr.write(self.style.ERROR(f"  - {e}"))
            # Non-zero exit for CI.
            raise CommandError("Tazkiyah 114 seed validation failed.")
        self.stdout.write(self.style.SUCCESS("✓ Tazkiyah 114 seed validation passed: 114 surahs, schema intact, all draft/pending, non-authoritative."))
