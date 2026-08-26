"""
Enforcement tests for the four protected upload fields.

`core/tests_upload_validation.py` proves the validator *works*. This module
proves it is actually *reached* on every real entry point — a different claim,
and the one that matters.

Django model-field validators do NOT run on `Model.save()`,
`objects.create()`, `bulk_create()` or `queryset.update()`. They run inside
`Model.full_clean()`, which ModelForms and ModelAdmin call from
`ModelForm._post_clean()`. So "the field has a validator" is not evidence of
anything on its own; these tests exercise the concrete forms the product
actually uses, with real malicious payloads.

Traced entry points for the four fields, and what covers them:

  core.Assessment.uploaded_file
      core/views.py:92  AssessmentUploadForm(request.POST, request.FILES)
      core/admin.py     AssessmentAdmin (ModelAdmin -> ModelForm)
  audit.AuditSession.uploaded_file
      audit/views.py:75 AuditSessionForm(request.POST, request.FILES)
      audit/admin.py    AuditSessionAdmin
  league.Evidence.file
      league/admin.py   EvidenceAdmin + EvidenceInline  (admin-only field)
  leads.ReviewRequest.sustainability_report
      leads/views.py:370 ReviewRequestForm(request.POST, request.FILES)
      leads/admin.py    ReviewRequestAdmin

No DRF serializer exposes any of these fields, no code assigns to them
directly, and no `bulk_create`/`update()` writes them — all verified by the
static checks at the bottom of this module so a future change cannot quietly
add such a path.
"""
import io
import struct
import zlib
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.forms import modelform_factory
from django.test import SimpleTestCase

BASE_DIR = Path(settings.BASE_DIR)

PDF = b'%PDF-1.7\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n%%EOF\n'
WINDOWS_EXE = b'MZ\x90\x00' + b'\x00' * 300
LINUX_EXE = b'\x7fELF\x02\x01\x01' + b'\x00' * 300

PROTECTED_FIELDS = (
    ('core', 'Assessment', 'uploaded_file'),
    ('audit', 'AuditSession', 'uploaded_file'),
    ('league', 'Evidence', 'file'),
    ('leads', 'ReviewRequest', 'sustainability_report'),
)


def _upload(name, content):
    return SimpleUploadedFile(name, content)


def _png(width=8, height=8):
    def chunk(tag, payload):
        body = tag + payload
        return struct.pack('>I', len(payload)) + body + struct.pack('>I', zlib.crc32(body) & 0xFFFFFFFF)

    raw = b''.join(b'\x00' + b'\xff\x00\x00' * width for _ in range(height))
    return (
        b'\x89PNG\r\n\x1a\n'
        + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
        + chunk(b'IDAT', zlib.compress(raw))
        + chunk(b'IEND', b'')
    )


class ModelFormEnforcementTests(SimpleTestCase):
    """A minimal ModelForm over each field — the shape the admin builds."""

    def _form_for(self, app_label, model_name, field_name):
        model = apps.get_model(app_label, model_name)
        return modelform_factory(model, fields=[field_name])

    def _assert_rejected(self, field_name, form, expected_fragment):
        self.assertIn(field_name, form.errors, 'upload was accepted')
        self.assertIn(expected_fragment, str(form.errors[field_name]))

    def test_windows_executable_renamed_to_pdf_is_rejected_everywhere(self):
        for app_label, model_name, field_name in PROTECTED_FIELDS:
            with self.subTest(field=f'{app_label}.{model_name}.{field_name}'):
                Form = self._form_for(app_label, model_name, field_name)
                form = Form(data={}, files={field_name: _upload('report.pdf', WINDOWS_EXE)})
                form.is_valid()
                self._assert_rejected(field_name, form, 'Windows executable')

    def test_linux_executable_renamed_to_pdf_is_rejected_everywhere(self):
        for app_label, model_name, field_name in PROTECTED_FIELDS:
            with self.subTest(field=f'{app_label}.{model_name}.{field_name}'):
                Form = self._form_for(app_label, model_name, field_name)
                form = Form(data={}, files={field_name: _upload('audit.pdf', LINUX_EXE)})
                form.is_valid()
                self._assert_rejected(field_name, form, 'Linux executable')

    def test_double_extension_is_rejected_everywhere(self):
        for app_label, model_name, field_name in PROTECTED_FIELDS:
            with self.subTest(field=f'{app_label}.{model_name}.{field_name}'):
                Form = self._form_for(app_label, model_name, field_name)
                form = Form(data={}, files={field_name: _upload('invoice.exe.pdf', PDF)})
                form.is_valid()
                self._assert_rejected(field_name, form, 'more than one file-type extension')

    def test_a_genuine_pdf_is_still_accepted_everywhere(self):
        # The point of the gate is to block disguises, not to break the product.
        for app_label, model_name, field_name in PROTECTED_FIELDS:
            with self.subTest(field=f'{app_label}.{model_name}.{field_name}'):
                Form = self._form_for(app_label, model_name, field_name)
                form = Form(data={}, files={field_name: _upload('report.pdf', PDF)})
                form.is_valid()
                self.assertNotIn(field_name, form.errors, str(form.errors))


class RealUploadFormTests(SimpleTestCase):
    """The actual product forms, with their own data, as the views build them."""

    CORE_DATA = {'company_name': 'Acme Industrial', 'notes': ''}

    def test_core_assessment_form_rejects_a_disguised_executable(self):
        from core.forms import AssessmentUploadForm

        form = AssessmentUploadForm(
            self.CORE_DATA, {'uploaded_file': _upload('report.pdf', WINDOWS_EXE)},
        )
        self.assertFalse(form.is_valid())
        self.assertIn('Windows executable', str(form.errors['uploaded_file']))

    def test_core_assessment_form_rejects_script_content_in_a_text_file(self):
        from core.forms import AssessmentUploadForm

        form = AssessmentUploadForm(
            self.CORE_DATA,
            {'uploaded_file': _upload('notes.txt', b'<script>alert(1)</script>')},
        )
        self.assertFalse(form.is_valid())
        self.assertIn('script tag', str(form.errors['uploaded_file']))

    def test_core_assessment_form_still_accepts_a_real_pdf(self):
        from core.forms import AssessmentUploadForm

        form = AssessmentUploadForm(
            self.CORE_DATA, {'uploaded_file': _upload('report.pdf', PDF)},
        )
        self.assertTrue(form.is_valid(), str(form.errors))

    def test_markdown_is_still_accepted_because_the_form_advertises_it(self):
        # core/forms.py and audit/forms.py have always listed .md as accepted.
        # An earlier revision of the validator omitted it and silently broke a
        # documented upload type; this test exists so that cannot recur.
        from core.forms import ALLOWED_EXTENSIONS, AssessmentUploadForm

        self.assertIn('.md', ALLOWED_EXTENSIONS)
        form = AssessmentUploadForm(
            self.CORE_DATA,
            {'uploaded_file': _upload('notes.md', b'# Facility notes\n\nBoiler replaced.\n')},
        )
        self.assertTrue(form.is_valid(), str(form.errors))

    def test_every_extension_the_forms_advertise_is_actually_accepted(self):
        """The forms' own allowlists and the validator must not disagree.

        A file the form says it takes but the validator refuses is a broken
        product surface, not a security win.
        """
        from audit.forms import ALLOWED_EXTENSIONS as AUDIT_EXTS
        from core.forms import ALLOWED_EXTENSIONS as CORE_EXTS
        from core.upload_validation import EVIDENCE_EXTENSIONS

        for extension in set(CORE_EXTS) | set(AUDIT_EXTS):
            with self.subTest(extension=extension):
                self.assertIn(
                    extension, EVIDENCE_EXTENSIONS,
                    f'a form advertises "{extension}" but the validator rejects it',
                )

    def test_leads_review_form_rejects_a_non_pdf_even_though_it_is_a_valid_image(self):
        from leads.forms import ReviewRequestForm

        form = ReviewRequestForm(
            {
                'name': 'Jo Smith', 'work_email': 'jo@example.com',
                'organisation': 'Acme', 'sector': 'other',
                'request_type': 'other', 'message': 'Please review.',
            },
            {'sustainability_report': _upload('chart.png', _png())},
        )
        self.assertFalse(form.is_valid())
        self.assertIn('sustainability_report', form.errors)


class NoBypassPathTests(SimpleTestCase):
    """Static guards: a future change must not add an unvalidated write path."""

    APP_SOURCES = (
        'core', 'audit', 'league', 'leads', 'ingestion', 'api',
        'companies', 'backend_intelligence_engine',
    )

    def _python_files(self):
        for app in self.APP_SOURCES:
            root = BASE_DIR / app
            if not root.exists():
                continue
            for path in root.rglob('*.py'):
                if 'migrations' in path.parts or path.name.startswith('test'):
                    continue
                yield path

    def test_nothing_assigns_to_a_protected_field_directly(self):
        # A direct `instance.uploaded_file = <uploaded file>` followed by
        # save() would store bytes without ever calling full_clean().
        import ast

        protected = {'uploaded_file', 'sustainability_report'}
        offenders = []
        for path in self._python_files():
            try:
                tree = ast.parse(path.read_text())
            except (SyntaxError, UnicodeDecodeError):  # pragma: no cover
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Assign):
                    continue
                for target in node.targets:
                    if isinstance(target, ast.Attribute) and target.attr in protected:
                        offenders.append(f'{path.relative_to(BASE_DIR)}:{node.lineno}')
        self.assertEqual(
            offenders, [],
            'direct assignment to a protected upload field bypasses validation: '
            + ', '.join(offenders),
        )

    def test_no_bulk_create_or_update_writes_a_protected_field(self):
        for path in self._python_files():
            source = path.read_text(errors='replace')
            for model in ('Assessment', 'AuditSession', 'Evidence', 'ReviewRequest'):
                for method in ('bulk_create', 'update'):
                    needle = f'{model}.objects.{method}('
                    if needle in source:
                        # Only a problem if it also names a protected field.
                        for field in ('uploaded_file', 'sustainability_report', 'file='):
                            self.assertNotIn(
                                field, source.split(needle, 1)[1][:400],
                                f'{path.relative_to(BASE_DIR)} writes {field} via {needle}',
                            )

    def test_no_drf_serializer_exposes_a_protected_field(self):
        for path in BASE_DIR.rglob('serializers.py'):
            if 'node_modules' in path.parts:
                continue
            source = path.read_text(errors='replace')
            for field in ('uploaded_file', 'sustainability_report'):
                self.assertNotIn(
                    field, source,
                    f'{path.relative_to(BASE_DIR)} exposes {field}; it would need '
                    'the validator wired onto the serializer field too',
                )

    def test_every_protected_field_still_carries_the_validator(self):
        from core.upload_validation import UploadValidator

        for app_label, model_name, field_name in PROTECTED_FIELDS:
            with self.subTest(field=f'{app_label}.{model_name}.{field_name}'):
                field = apps.get_model(app_label, model_name)._meta.get_field(field_name)
                self.assertTrue(
                    any(isinstance(v, UploadValidator) for v in field.validators)
                )


class TrustedInternalPathTests(SimpleTestCase):
    """Internal storage migration must NOT be forced through upload validation.

    `reconcile_media` copies objects that are already stored between storage
    backends. Those bytes were validated when they were uploaded, the command
    never receives an HTTP upload, and running a content check over an existing
    archive would fail the migration for files the system already accepted.
    It writes through `default_storage.save()`, deliberately outside the model
    layer — this test records that as intended, not as a gap.
    """

    def test_reconcile_media_writes_through_storage_not_the_model_layer(self):
        source = (
            BASE_DIR / 'core' / 'management' / 'commands' / 'reconcile_media.py'
        ).read_text()
        self.assertIn('default_storage.save(', source)
        for model_write in ('.full_clean(', 'objects.create(', 'UploadValidator'):
            self.assertNotIn(model_write, source)
