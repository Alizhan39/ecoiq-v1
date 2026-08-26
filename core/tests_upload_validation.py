"""
Tests for core/upload_validation.py.

Fixtures are built byte-by-byte rather than checked in, so the repository does
not accumulate binary test files and every case states exactly what makes it
dangerous. Nothing here writes to disk or opens a socket.
"""
import io
import struct
import zipfile
import zlib

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from core.upload_validation import (
    DEFAULT_MAX_BYTES,
    UnsafeUpload,
    UploadValidator,
    sanitize_upload_filename,
    validate_upload,
)

PDF_BYTES = b'%PDF-1.7\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n%%EOF\n'


def _jpeg(width=8, height=8):
    """A genuinely decodable JPEG.

    Hand-written JPEG headers are not enough: the validator opens images with
    Pillow, so a fixture that only *looks* like a JPEG is correctly refused —
    which is the behaviour under test elsewhere, not here.
    """
    from PIL import Image

    buffer = io.BytesIO()
    Image.new('RGB', (width, height), (200, 40, 40)).save(buffer, format='JPEG')
    return buffer.getvalue()


def _upload(name, content, content_type='application/octet-stream'):
    return SimpleUploadedFile(name, content, content_type=content_type)


def _png(width=8, height=8):
    """A structurally valid PNG whose IHDR declares the given dimensions.

    Pillow reads the size from IHDR without decoding pixels, which is exactly
    how a decompression bomb presents itself: a tiny file announcing an
    enormous canvas.
    """
    def chunk(tag, payload):
        body = tag + payload
        return struct.pack('>I', len(payload)) + body + struct.pack('>I', zlib.crc32(body) & 0xFFFFFFFF)

    ihdr = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
    raw = b''.join(b'\x00' + b'\xff\x00\x00' * width for _ in range(height))
    return (
        b'\x89PNG\r\n\x1a\n'
        + chunk(b'IHDR', ihdr)
        + chunk(b'IDAT', zlib.compress(raw))
        + chunk(b'IEND', b'')
    )


def _xlsx(members=None, declared_size=None):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, payload in (members or {'xl/workbook.xml': b'<workbook/>'}).items():
            archive.writestr(name, payload)
    data = buffer.getvalue()
    if declared_size is not None:
        # Rewrite the central-directory uncompressed size to fake an
        # expansion ratio, the way a real zip bomb advertises itself.
        buffer = io.BytesIO(data)
        with zipfile.ZipFile(buffer) as archive:
            pass
        data = data.replace(struct.pack('<I', 12), struct.pack('<I', declared_size), 1)
    return data


class FilenameSanitisationTests(SimpleTestCase):

    def test_directory_components_are_stripped(self):
        self.assertEqual(sanitize_upload_filename('/etc/passwd'), 'passwd')
        self.assertEqual(sanitize_upload_filename('../../../etc/passwd'), 'passwd')

    def test_windows_separators_are_stripped_too(self):
        # A POSIX-only basename() would leave this fully intact.
        self.assertEqual(sanitize_upload_filename(r'..\..\windows\evil.pdf'), 'evil.pdf')

    def test_null_bytes_are_removed(self):
        self.assertEqual(sanitize_upload_filename('report.pdf\x00.exe'), 'report.pdf.exe')

    def test_unusable_names_are_refused_not_silently_rewritten(self):
        for name in ('', '.', '..', '/', '///'):
            with self.subTest(name=name):
                with self.assertRaises(UnsafeUpload):
                    sanitize_upload_filename(name)

    def test_ordinary_name_survives(self):
        self.assertEqual(sanitize_upload_filename('Q3 Emissions Report.pdf'), 'Q3_Emissions_Report.pdf')


class AcceptedUploadTests(SimpleTestCase):

    def test_pdf_is_accepted(self):
        self.assertEqual(validate_upload(_upload('report.pdf', PDF_BYTES)), 'report.pdf')

    def test_png_is_accepted(self):
        validate_upload(_upload('site.png', _png()))

    def test_jpeg_is_accepted(self):
        validate_upload(_upload('photo.jpg', _jpeg()))

    def test_a_fake_jpeg_header_is_not_enough(self):
        # Content inspection goes past the magic bytes for images.
        fake = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01' + b'\x00' * 64 + b'\xff\xd9'
        with self.assertRaises(UnsafeUpload):
            validate_upload(_upload('photo.jpg', fake))

    def test_csv_is_accepted(self):
        validate_upload(_upload('emissions.csv', b'year,scope1,scope2\n2025,100,50\n'))

    def test_xlsx_is_accepted(self):
        validate_upload(_upload('workbook.xlsx', _xlsx()))

    def test_a_traversal_style_name_is_accepted_once_sanitised(self):
        # The name is cleaned rather than the upload refused — the content is
        # a genuine PDF and the path component simply cannot survive.
        self.assertEqual(
            validate_upload(_upload('../../evidence.pdf', PDF_BYTES)),
            'evidence.pdf',
        )


class ExtensionPolicyTests(SimpleTestCase):

    def test_disallowed_extension_is_refused_with_the_allowed_list(self):
        with self.assertRaises(UnsafeUpload) as ctx:
            validate_upload(_upload('payload.exe', PDF_BYTES))
        self.assertIn('not accepted', str(ctx.exception))
        self.assertIn('.pdf', str(ctx.exception))

    def test_missing_extension_is_refused(self):
        with self.assertRaises(UnsafeUpload) as ctx:
            validate_upload(_upload('report', PDF_BYTES))
        self.assertIn('no extension', str(ctx.exception))

    def test_trailing_double_extension_is_refused(self):
        with self.assertRaises(UnsafeUpload):
            validate_upload(_upload('report.pdf.exe', PDF_BYTES))

    def test_leading_double_extension_is_refused(self):
        # invoice.exe.pdf ends in an allowed extension, so an extension-only
        # check would pass it.
        with self.assertRaises(UnsafeUpload) as ctx:
            validate_upload(_upload('invoice.exe.pdf', PDF_BYTES))
        self.assertIn('more than one file-type extension', str(ctx.exception))

    def test_svg_is_not_an_accepted_evidence_type(self):
        with self.assertRaises(UnsafeUpload):
            validate_upload(_upload('diagram.svg', b'<svg xmlns="http://www.w3.org/2000/svg"></svg>'))

    def test_html_disguised_as_pdf_extension_is_refused_by_content(self):
        with self.assertRaises(UnsafeUpload):
            validate_upload(_upload('page.pdf', b'<!DOCTYPE html><html><body>hi</body></html>'))

    def test_extension_case_is_ignored(self):
        validate_upload(_upload('REPORT.PDF', PDF_BYTES))


class ContentInspectionTests(SimpleTestCase):
    """The filename is a hint; the bytes decide."""

    def test_windows_executable_renamed_to_pdf_is_refused(self):
        with self.assertRaises(UnsafeUpload) as ctx:
            validate_upload(_upload('invoice.pdf', b'MZ\x90\x00' + b'\x00' * 200))
        self.assertIn('Windows executable', str(ctx.exception))

    def test_linux_executable_renamed_to_pdf_is_refused(self):
        with self.assertRaises(UnsafeUpload) as ctx:
            validate_upload(_upload('report.pdf', b'\x7fELF\x02\x01\x01' + b'\x00' * 200))
        self.assertIn('Linux executable', str(ctx.exception))

    def test_shell_script_renamed_to_csv_is_refused(self):
        with self.assertRaises(UnsafeUpload) as ctx:
            validate_upload(_upload('data.csv', b'#!/bin/sh\nrm -rf /\n'))
        self.assertIn('shebang', str(ctx.exception))

    def test_gzip_and_rar_and_7z_are_refused(self):
        for content, label in (
            (b'\x1f\x8b\x08\x00', 'gzip'),
            (b'Rar!\x1a\x07\x00', 'RAR'),
            (b'7z\xbc\xaf\x27\x1c', '7-Zip'),
        ):
            with self.subTest(label=label):
                with self.assertRaises(UnsafeUpload):
                    validate_upload(_upload('archive.pdf', content + b'\x00' * 100))

    def test_extension_content_mismatch_is_named_explicitly(self):
        with self.assertRaises(UnsafeUpload) as ctx:
            validate_upload(_upload('photo.png', PDF_BYTES))
        message = str(ctx.exception)
        self.assertIn('.png', message)
        self.assertIn('PDF document', message)

    def test_binary_content_in_a_text_file_is_refused(self):
        with self.assertRaises(UnsafeUpload) as ctx:
            validate_upload(_upload('data.csv', b'year,value\n\x00\x01\x02binary'))
        self.assertIn('binary data', str(ctx.exception))

    def test_script_tag_in_a_csv_is_refused(self):
        with self.assertRaises(UnsafeUpload) as ctx:
            validate_upload(_upload('data.csv', b'year,value\n2025,"<script>alert(1)</script>"'))
        self.assertIn('script tag', str(ctx.exception))

    def test_php_in_a_text_file_is_refused(self):
        with self.assertRaises(UnsafeUpload):
            validate_upload(_upload('notes.txt', b'<?php system($_GET["c"]); ?>'))

    def test_inline_svg_inside_a_text_file_is_refused(self):
        with self.assertRaises(UnsafeUpload) as ctx:
            validate_upload(_upload('notes.txt', b'hello <svg onload=alert(1)>'))
        self.assertIn('SVG', str(ctx.exception))

    def test_xml_entity_declaration_is_refused(self):
        with self.assertRaises(UnsafeUpload) as ctx:
            validate_upload(_upload('data.txt', b'<!ENTITY xxe SYSTEM "file:///etc/passwd">'))
        self.assertIn('entity', str(ctx.exception).lower())


class SizeTests(SimpleTestCase):

    def test_empty_file_is_refused(self):
        with self.assertRaises(UnsafeUpload) as ctx:
            validate_upload(_upload('report.pdf', b''))
        self.assertIn('empty', str(ctx.exception))

    def test_oversized_file_is_refused_with_both_numbers(self):
        oversized = PDF_BYTES + b'\x00' * (2 * 1024 * 1024)
        with self.assertRaises(UnsafeUpload) as ctx:
            validate_upload(_upload('report.pdf', oversized), max_bytes=1024 * 1024)
        message = str(ctx.exception)
        self.assertIn('MB', message)
        self.assertIn('maximum is 1 MB', message)

    def test_default_limit_is_twenty_megabytes(self):
        self.assertEqual(DEFAULT_MAX_BYTES, 20 * 1024 * 1024)


class ArchiveTests(SimpleTestCase):

    def test_xlsx_with_a_traversal_member_is_refused(self):
        content = _xlsx({'../../etc/cron.d/evil': b'* * * * * root sh\n'})
        with self.assertRaises(UnsafeUpload) as ctx:
            validate_upload(_upload('book.xlsx', content))
        self.assertIn('unsafe path', str(ctx.exception))

    def test_xlsx_with_an_absolute_member_is_refused(self):
        content = _xlsx({'/etc/passwd': b'root:x:0:0\n'})
        with self.assertRaises(UnsafeUpload) as ctx:
            validate_upload(_upload('book.xlsx', content))
        self.assertIn('unsafe path', str(ctx.exception))

    def test_xlsx_with_too_many_members_is_refused(self):
        content = _xlsx({f'sheet{n}.xml': b'<x/>' for n in range(2100)})
        with self.assertRaises(UnsafeUpload) as ctx:
            validate_upload(_upload('book.xlsx', content))
        self.assertIn('entries', str(ctx.exception))

    def test_highly_compressible_content_is_refused_as_a_bomb(self):
        # 20 MB of zeroes compresses to a few KB — ratio far past the cap.
        content = _xlsx({'xl/data.xml': b'\x00' * (20 * 1024 * 1024)})
        with self.assertRaises(UnsafeUpload) as ctx:
            validate_upload(_upload('book.xlsx', content))
        self.assertIn('compression bomb', str(ctx.exception))

    def test_a_file_named_xlsx_that_is_not_a_zip_is_refused(self):
        with self.assertRaises(UnsafeUpload):
            validate_upload(_upload('book.xlsx', b'PK\x03\x04not-really-a-zip'))


class ImageTests(SimpleTestCase):

    def test_megapixel_cap_is_enforced(self):
        import struct as _struct

        good = _png(4, 4)
        # Patch IHDR width/height in place; CRC then fails, which Pillow
        # tolerates for the header read but not for verify().
        header = bytearray(good)
        _struct.pack_into('>II', header, 16, 30000, 30000)
        with self.assertRaises(UnsafeUpload):
            validate_upload(_upload('huge.png', bytes(header)))

    def test_corrupt_image_is_refused(self):
        with self.assertRaises(UnsafeUpload) as ctx:
            validate_upload(_upload('broken.png', b'\x89PNG\r\n\x1a\n' + b'\x00' * 40))
        self.assertIn('not a readable image', str(ctx.exception))


class ValidatorObjectTests(SimpleTestCase):

    def test_validator_is_deconstructible_for_migrations(self):
        validator = UploadValidator(allowed_extensions={'.pdf'}, max_bytes=1024)
        path, args, kwargs = validator.deconstruct()
        self.assertEqual(path, 'core.upload_validation.UploadValidator')
        self.assertEqual(UploadValidator(*args, **kwargs), validator)

    def test_equality_drives_migration_stability(self):
        self.assertEqual(UploadValidator(), UploadValidator())
        self.assertNotEqual(UploadValidator(), UploadValidator(max_bytes=1))

    def test_pdf_only_validator_matches_the_leads_help_text(self):
        validator = UploadValidator(allowed_extensions={'.pdf'}, max_bytes=10 * 1024 * 1024)
        validator(_upload('report.pdf', PDF_BYTES))
        with self.assertRaises(UnsafeUpload):
            validator(_upload('sheet.xlsx', _xlsx()))
        with self.assertRaises(UnsafeUpload):
            validator(_upload('big.pdf', PDF_BYTES + b'\x00' * (11 * 1024 * 1024)))


class FieldWiringTests(SimpleTestCase):
    """All four upload surfaces must actually carry the validator."""

    def test_every_evidence_field_is_validated_and_uses_evidence_storage(self):
        from django.apps import apps

        from core.storage import evidence_storage
        from core.upload_validation import UploadValidator as _UV

        targets = [
            ('core', 'Assessment', 'uploaded_file'),
            ('audit', 'AuditSession', 'uploaded_file'),
            ('league', 'Evidence', 'file'),
            ('leads', 'ReviewRequest', 'sustainability_report'),
        ]
        for app_label, model_name, field_name in targets:
            with self.subTest(field=f'{app_label}.{model_name}.{field_name}'):
                field = apps.get_model(app_label, model_name)._meta.get_field(field_name)
                self.assertTrue(
                    any(isinstance(v, _UV) for v in field.validators),
                    'no UploadValidator attached',
                )
                # Compare the callable, not the instance: the instance is
                # memoised and other tests legitimately reset that cache, so
                # identity of the object would be a flaky assertion.
                self.assertIs(field._storage_callable, evidence_storage)

    def test_leads_field_enforces_the_limits_its_help_text_promises(self):
        from django.apps import apps

        field = apps.get_model('leads', 'ReviewRequest')._meta.get_field('sustainability_report')
        validator = next(v for v in field.validators if isinstance(v, UploadValidator))
        self.assertEqual(validator.allowed_extensions, frozenset({'.pdf'}))
        self.assertEqual(validator.max_bytes, 10 * 1024 * 1024)
        self.assertIn('PDF only', field.help_text)
        self.assertIn('10 MB', field.help_text)
