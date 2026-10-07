"""Atomic, operator-only import of the normalised provider export contract."""
from django.db import transaction

from .models import KnowledgePassage
from .providers import PROVIDERS

FIELDS = ('external_id', 'source_url', 'kind', 'work', 'edition', 'source_version',
          'language', 'attribution', 'passage', 'surah', 'ayah_start', 'ayah_end',
          'name_key', 'enumeration', 'rights', 'rights_evidence')
REQUIRED = FIELDS[:9]


def import_export(provider, data):
    if provider not in PROVIDERS or not isinstance(data, dict):
        raise ValueError('Unknown provider or invalid export.')
    if type(data.get('schema_version')) is not int or data['schema_version'] != 1 or data.get('provider') != provider:
        raise ValueError('Export schema or provider does not match.')
    rows = data.get('passages')
    if not isinstance(rows, list) or not 1 <= len(rows) <= 1000:
        raise ValueError('Export must contain 1–1000 passages.')
    records, seen = [], set()
    for row in rows:
        if not isinstance(row, dict) or set(row) - set(FIELDS):
            raise ValueError('Unknown passage fields; review and vectors cannot be imported.')
        if any(not isinstance(row.get(key), str) or not row[key].strip() for key in REQUIRED):
            raise ValueError('Export is missing required attribution/content fields.')
        if any(not isinstance(row[key], str) for key in FIELDS if key in row
               and key not in ('surah', 'ayah_start', 'ayah_end')):
            raise ValueError('Source metadata and content must be strings.')
        if row['external_id'] in seen:
            raise ValueError('Duplicate external ID in export.')
        seen.add(row['external_id'])
        for key in ('surah', 'ayah_start', 'ayah_end'):
            if row.get(key) is not None and type(row[key]) is not int:
                raise ValueError('Quran reference numbers must be integers.')
        candidate = KnowledgePassage(provider=provider, **row)
        candidate.full_clean(exclude=('digest',), validate_unique=False, validate_constraints=False)
        records.append(row)
    created = updated = unchanged = 0
    with transaction.atomic():
        for row in records:
            record = KnowledgePassage.objects.select_for_update().filter(
                provider=provider, external_id=row['external_id']).first()
            if record is None:
                KnowledgePassage.objects.create(provider=provider, **row)
                created += 1
                continue
            candidate = KnowledgePassage(provider=provider, **row)
            if candidate.source_digest() == record.digest:
                unchanged += 1
                continue
            for key in FIELDS:
                setattr(record, key, getattr(candidate, key))
            record.save()
            updated += 1
    return {'created': created, 'updated': updated, 'unchanged': unchanged}
