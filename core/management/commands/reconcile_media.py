"""
Reconcile database file references against objects in the configured storage.

WHY THIS EXISTS RATHER THAN A MIGRATION SCRIPT
----------------------------------------------
Production currently has 0 uploaded files and 0 database references, measured
before this command was written. Writing a migrate-everything-to-R2 script for
zero files would be code nobody could test and nobody needed.

What IS needed is the ability to answer "what is actually there?" — before a
cutover, after one, and at any point where a row might reference a file that no
longer exists. That question has four honest answers and this reports all four:

    referenced_and_present     the row points at an object that exists
    referenced_but_missing     the row points at nothing — the failure mode the
                               ephemeral filesystem produced silently
    present_but_unreferenced   an object no row points at
    copied                     moved to the destination by --migrate

`--migrate` copies from the source storage to the CONFIGURED default storage.
It is storage-agnostic on purpose: local->local is testable without R2 or a
network, and the same code path runs local->R2 at cutover.

SAFETY
------
  - The source object is NEVER deleted. Copy, verify, then stop.
  - A database reference is never rewritten. Keys are preserved exactly, so a
    verified copy needs no row update at all.
  - Already-present destination objects are skipped, which makes re-running the
    whole command a no-op. Idempotent by construction, not by a flag.
  - Sizes are compared after every copy. A short write is a failure, not a
    success with fewer bytes.
  - No file CONTENT is ever printed. Only keys, sizes and counts.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from django.apps import apps
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand

#: (app_label, ModelName, field_name) for every upload field in the estate.
#: Enumerated rather than discovered so a new FileField has to be added here
#: deliberately — a field nobody reconciles is a field nobody notices losing.
UPLOAD_FIELDS = [
    ('core', 'Assessment', 'uploaded_file'),
    ('leads', 'ReviewRequest', 'sustainability_report'),
    ('league', 'Evidence', 'file'),
    ('audit', 'AuditSession', 'uploaded_file'),
    ('audit', 'AIAnalysisJob', 'pdf_file'),
    ('companies', 'CompanyGuidanceVideo', 'thumbnail'),
]


@dataclass
class Report:
    referenced_and_present: int = 0
    referenced_but_missing: list = field(default_factory=list)
    present_but_unreferenced: list = field(default_factory=list)
    copied: int = 0
    failed: list = field(default_factory=list)
    skipped_already_present: int = 0


def _referenced_keys():
    """Every non-empty file reference in the database, as storage keys."""
    keys = set()
    for app_label, model_name, field_name in UPLOAD_FIELDS:
        try:
            model = apps.get_model(app_label, model_name)
        except LookupError:
            continue
        qs = model.objects.exclude(**{field_name: ''}).exclude(**{f'{field_name}__isnull': True})
        for value in qs.values_list(field_name, flat=True):
            if value:
                keys.add(str(value))
    return keys


class Command(BaseCommand):
    help = 'Reconcile database file references against stored objects.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--migrate', action='store_true',
            help='Copy referenced objects from --source-root into the configured '
                 'default storage. Never deletes the source.')
        parser.add_argument(
            '--source-root', default=None,
            help='Filesystem directory holding the current objects. Defaults to MEDIA_ROOT.')

    def handle(self, *args, **options):
        from django.conf import settings
        from django.core.files.storage import FileSystemStorage

        source_root = options['source_root'] or str(settings.MEDIA_ROOT)
        source = FileSystemStorage(location=source_root)
        report = Report()

        referenced = _referenced_keys()
        self.stdout.write(f'database references: {len(referenced)}')

        for key in sorted(referenced):
            in_destination = default_storage.exists(key)
            in_source = source.exists(key)

            if in_destination:
                report.referenced_and_present += 1
                if options['migrate'] and in_source:
                    report.skipped_already_present += 1
                continue

            if not in_source:
                # The row claims a file that exists nowhere. Reported, never
                # "fixed" — deciding what a dangling evidence reference means is
                # a product decision, not a cleanup script's.
                report.referenced_but_missing.append(key)
                continue

            if not options['migrate']:
                report.referenced_but_missing.append(key)
                continue

            try:
                with source.open(key, 'rb') as fh:
                    default_storage.save(key, fh)
                copied_size = default_storage.size(key)
                original_size = source.size(key)
                if copied_size != original_size:
                    report.failed.append((key, f'size mismatch {original_size}->{copied_size}'))
                else:
                    report.copied += 1
            except Exception as exc:  # noqa: BLE001 - reported, never raised
                report.failed.append((key, type(exc).__name__))

        # Objects present in the source that nothing references.
        try:
            for key in self._walk(source, ''):
                if key not in referenced:
                    report.present_but_unreferenced.append(key)
        except (FileNotFoundError, NotImplementedError):
            pass

        self._render(report)

    def _walk(self, storage, prefix):
        dirs, files = storage.listdir(prefix)
        for name in files:
            yield f'{prefix}{name}'
        for name in dirs:
            yield from self._walk(storage, f'{prefix}{name}/')

    def _render(self, report):
        w = self.stdout.write
        w('')
        w(f'referenced_and_present    : {report.referenced_and_present}')
        w(f'referenced_but_missing    : {len(report.referenced_but_missing)}')
        w(f'present_but_unreferenced  : {len(report.present_but_unreferenced)}')
        w(f'copied                    : {report.copied}')
        w(f'skipped_already_present   : {report.skipped_already_present}')
        w(f'failed                    : {len(report.failed)}')
        for key in report.referenced_but_missing[:20]:
            w(f'  MISSING     {key}')
        for key in report.present_but_unreferenced[:20]:
            w(f'  UNREFERENCED {key}')
        for key, reason in report.failed[:20]:
            w(f'  FAILED      {key} ({reason})')
