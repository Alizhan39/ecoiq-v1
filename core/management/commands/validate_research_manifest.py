"""
Management command: validate_research_manifest

Validates a research ingestion manifest against
docs/research-ingest-manifest.schema.json and, more importantly, against the
cross-field provenance rules JSON Schema cannot express:

  * review_state above 'unreviewed' requires a named human reviewer
  * an AI-written summary can never be 'approved'
  * confidence is null or a real number in [0,1] — never a plausible default
  * document_sha256 is a real 64-hex digest
  * retrieved_date is present and is not in the future

No new dependency: `jsonschema` is not installed in this project and adding a
library to validate one file would not be proportionate, so the structural
checks are written out here. The schema file remains the published contract
(and is checked for drift against this command by core/tests_engineering_os.py).

Usage:
    python manage.py validate_research_manifest path/to/manifest.json
    python manage.py validate_research_manifest a.json b.json

Exits 1 if any manifest fails. Paired skill:
.claude/skills/ecoiq-research-ingest/SKILL.md
"""
import datetime as _datetime
import json
import re
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

SOURCE_ID_RE = re.compile(r'^[a-z0-9][a-z0-9._-]{2,63}$')
SHA256_RE = re.compile(r'^[0-9a-f]{64}$')
REVIEW_STATES = ('unreviewed', 'reviewed', 'approved')
SUMMARY_AUTHORS = ('human', 'ai')
JURISDICTIONS = ('GB', 'KZ', 'SA', 'TR')

REQUIRED_SOURCE_FIELDS = (
    'source_id', 'title', 'origin', 'retrieved_date',
    'document_sha256', 'confidence', 'review_state', 'citations',
)

# A `reviewer` names a person who takes responsibility, so an obvious model or
# service name there is a real error. Matched as whole words, case-insensitive.
# Deliberately excludes bare "ai": Ai is a common given name, and a validator
# that rejects a real reviewer's name would be worse than the rule it enforces.
NON_HUMAN_REVIEWER_TOKENS = (
    'claude', 'gpt', 'llama', 'gemini', 'mistral', 'bot',
    'model', 'ecoiq', 'assistant', 'automated', 'system',
)


class Command(BaseCommand):
    help = 'Validate one or more EcoIQ research ingestion manifests.'

    def add_arguments(self, parser):
        parser.add_argument('paths', nargs='+', help='Manifest JSON file(s).')

    def handle(self, *args, **options):
        failed = 0
        for raw_path in options['paths']:
            path = Path(raw_path)
            if not path.exists():
                raise CommandError(f'No such file: {path}')
            try:
                document = json.loads(path.read_text(encoding='utf-8'))
            except json.JSONDecodeError as exc:
                self.stdout.write(self.style.ERROR(f'{path}: invalid JSON — {exc}'))
                failed += 1
                continue

            errors = validate_manifest(document)
            if errors:
                failed += 1
                self.stdout.write(self.style.ERROR(f'{path}: {len(errors)} problem(s)'))
                for error in errors:
                    self.stdout.write(f'  · {error}')
            else:
                count = len(document.get('sources', []))
                self.stdout.write(self.style.SUCCESS(f'{path}: OK ({count} source(s))'))

        if failed:
            raise SystemExit(1)


def validate_manifest(document):
    """Return a list of human-readable error strings. Empty means valid.

    Importable so tests can assert on individual rules without shelling out.
    """
    errors = []

    if not isinstance(document, dict):
        return ['manifest root must be a JSON object']

    if document.get('manifest_version') != 1:
        errors.append('manifest_version must be exactly 1')

    errors += _check_date(document.get('created_date'), 'created_date', required=True)

    sources = document.get('sources')
    if not isinstance(sources, list) or not sources:
        errors.append('sources must be a non-empty array')
        return errors

    seen_ids = set()
    for index, source in enumerate(sources):
        label = f'sources[{index}]'
        if not isinstance(source, dict):
            errors.append(f'{label}: must be an object')
            continue
        errors += _validate_source(source, label, seen_ids)

    return errors


def _validate_source(source, label, seen_ids):
    errors = []

    for field in REQUIRED_SOURCE_FIELDS:
        if field not in source:
            errors.append(f'{label}: missing required field "{field}"')

    source_id = source.get('source_id')
    if isinstance(source_id, str):
        if not SOURCE_ID_RE.match(source_id):
            errors.append(
                f'{label}: source_id "{source_id}" must be 3-64 chars of '
                'lowercase letters, digits, dot, underscore or hyphen'
            )
        elif source_id in seen_ids:
            errors.append(f'{label}: duplicate source_id "{source_id}"')
        else:
            seen_ids.add(source_id)

    for field in ('title', 'origin'):
        value = source.get(field)
        if field in source and (not isinstance(value, str) or not value.strip()):
            errors.append(f'{label}: {field} must be a non-empty string')

    digest = source.get('document_sha256')
    if 'document_sha256' in source and (
        not isinstance(digest, str) or not SHA256_RE.match(digest)
    ):
        errors.append(f'{label}: document_sha256 must be 64 lowercase hex characters')

    errors += _check_date(source.get('retrieved_date'), f'{label}.retrieved_date', required=True)
    for optional in ('publication_date', 'review_date', 'expiry_date'):
        if source.get(optional) is not None:
            errors += _check_date(source.get(optional), f'{label}.{optional}', required=False)

    # Confidence: honest or absent. A default chosen to look plausible is the
    # failure mode this exists to prevent.
    confidence = source.get('confidence', 'MISSING')
    if confidence != 'MISSING' and confidence is not None:
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            errors.append(f'{label}: confidence must be null or a number in [0,1]')
        elif not 0 <= confidence <= 1:
            errors.append(f'{label}: confidence {confidence} is outside [0,1]')

    jurisdiction = source.get('jurisdiction')
    if jurisdiction is not None and jurisdiction not in JURISDICTIONS:
        errors.append(
            f'{label}: jurisdiction must be one of {JURISDICTIONS} or null — '
            'never a region like "EU/UK"'
        )

    citations = source.get('citations')
    if 'citations' in source:
        if not isinstance(citations, list) or not citations:
            errors.append(f'{label}: citations must be a non-empty array')
        else:
            for c_index, citation in enumerate(citations):
                c_label = f'{label}.citations[{c_index}]'
                if not isinstance(citation, dict):
                    errors.append(f'{c_label}: must be an object')
                    continue
                locator = citation.get('locator')
                if not isinstance(locator, str) or not locator.strip():
                    errors.append(f'{c_label}: locator must be a non-empty string')
                quote = citation.get('quote')
                if quote is not None and (not isinstance(quote, str) or len(quote) > 1000):
                    errors.append(f'{c_label}: quote must be a string of at most 1000 characters')

    errors += _validate_review_state(source, label)
    return errors


def _validate_review_state(source, label):
    """The rules the schema cannot express — these are the point of the file."""
    errors = []

    review_state = source.get('review_state')
    if 'review_state' in source and review_state not in REVIEW_STATES:
        errors.append(f'{label}: review_state must be one of {REVIEW_STATES}')
        return errors

    reviewer = source.get('reviewer')
    has_reviewer = isinstance(reviewer, str) and bool(reviewer.strip())

    if review_state in ('reviewed', 'approved') and not has_reviewer:
        errors.append(
            f'{label}: review_state "{review_state}" requires a named human reviewer — '
            'promotion out of "unreviewed" is a human act'
        )

    if has_reviewer:
        lowered = reviewer.lower()
        for token in NON_HUMAN_REVIEWER_TOKENS:
            if re.search(rf'\b{re.escape(token)}\b', lowered):
                errors.append(
                    f'{label}: reviewer "{reviewer}" looks like a model or system, '
                    'not a person — a reviewer takes responsibility'
                )
                break

    summary = source.get('summary')
    summary_author = source.get('summary_author')
    if isinstance(summary, str) and summary.strip():
        if summary_author not in SUMMARY_AUTHORS:
            errors.append(
                f'{label}: summary is present so summary_author must be '
                f'one of {SUMMARY_AUTHORS}'
            )
        elif summary_author == 'ai' and review_state == 'approved' and not has_reviewer:
            errors.append(
                f'{label}: an AI-written summary cannot be "approved" without a '
                'named human reviewer'
            )
    elif summary_author is not None:
        errors.append(f'{label}: summary_author is set but summary is empty')

    return errors


def _check_date(value, label, *, required):
    if value is None or value == '':
        return [f'{label} is required'] if required else []
    if not isinstance(value, str):
        return [f'{label} must be an ISO date string (YYYY-MM-DD)']
    try:
        parsed = _datetime.date.fromisoformat(value)
    except ValueError:
        return [f'{label} "{value}" is not a valid ISO date (YYYY-MM-DD)']
    if parsed > _datetime.date.today():
        return [f'{label} "{value}" is in the future']
    return []
