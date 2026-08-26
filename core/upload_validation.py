"""
core/upload_validation.py — reusable validation for user-uploaded evidence.

EcoIQ accepts files from people it does not fully trust — an audit
respondent's PDF, a company's sustainability report, a league evidence
attachment — and then *parses* them with pypdf and renders alongside them
with WeasyPrint. The upload path is therefore both a storage problem and a
parser-feeding problem.

The rule this module is built on: **the filename is a hint, never evidence.**
Every accepted type is confirmed by inspecting the leading bytes, and a file
whose extension and content disagree is refused even when both are
individually allowed — that mismatch is the signature of a disguised upload,
not of an honest mistake.

Where these run: Django model-field validators execute on `full_clean()`,
which ModelForms, the admin, and DRF serializers all call. A bare
`Model.save()` does not run them, so **existing stored files are untouched**
and no historical evidence is retroactively invalidated. New uploads through
any normal form path are covered.

Not a virus scanner. It refuses classes of file that have no business being
evidence; it does not claim the ones it accepts are safe to execute — and
nothing here should be executed.
"""
from __future__ import annotations

import os
import zipfile

from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible
from django.utils.text import get_valid_filename

DEFAULT_MAX_BYTES = 20 * 1024 * 1024  # 20 MB

# extension -> (human label, leading-byte signatures, family)
# A signature of () means "no reliable magic bytes", handled as text.
_TYPES = {
    '.pdf':  ('PDF document',      (b'%PDF-',), 'document'),
    '.png':  ('PNG image',         (b'\x89PNG\r\n\x1a\n',), 'image'),
    '.jpg':  ('JPEG image',        (b'\xff\xd8\xff',), 'image'),
    '.jpeg': ('JPEG image',        (b'\xff\xd8\xff',), 'image'),
    '.gif':  ('GIF image',         (b'GIF87a', b'GIF89a'), 'image'),
    '.webp': ('WebP image',        (b'RIFF',), 'image'),
    '.xlsx': ('Excel workbook',    (b'PK\x03\x04',), 'zip'),
    '.docx': ('Word document',     (b'PK\x03\x04',), 'zip'),
    '.csv':  ('CSV file',          (), 'text'),
    '.txt':  ('Text file',         (), 'text'),
}

DOCUMENT_EXTENSIONS = frozenset({'.pdf', '.csv', '.txt', '.xlsx', '.docx'})
IMAGE_EXTENSIONS = frozenset({'.png', '.jpg', '.jpeg', '.gif', '.webp'})
EVIDENCE_EXTENSIONS = DOCUMENT_EXTENSIONS | IMAGE_EXTENSIONS

# Leading bytes that must never appear in an upload, whatever it is called.
_EXECUTABLE_SIGNATURES = (
    (b'\x7fELF', 'a Linux executable'),
    (b'MZ', 'a Windows executable'),
    (b'\xca\xfe\xba\xbe', 'a Mach-O/Java binary'),
    (b'\xcf\xfa\xed\xfe', 'a macOS executable'),
    (b'\xfe\xed\xfa\xce', 'a macOS executable'),
    (b'#!', 'a script with a shebang'),
    (b'\x1f\x8b', 'a gzip archive'),
    (b'Rar!', 'a RAR archive'),
    (b'7z\xbc\xaf', 'a 7-Zip archive'),
)

# Markers that make a nominally-textual file active content.
_ACTIVE_CONTENT_MARKERS = (
    (b'<?php', 'PHP code'),
    (b'<script', 'a script tag'),
    (b'javascript:', 'a javascript: URL'),
    (b'<!ENTITY', 'an XML entity declaration (XXE risk)'),
    (b'<svg', 'inline SVG'),
)

# Archive limits. A 20 MB xlsx that expands to gigabytes is a zip bomb.
_MAX_ARCHIVE_MEMBERS = 2000
_MAX_ARCHIVE_EXPANSION_RATIO = 120
_MAX_ARCHIVE_UNCOMPRESSED_BYTES = 400 * 1024 * 1024

# Pillow's own bomb guard is ~89 Mpx; evidence images have no reason to be
# anywhere near it.
_MAX_IMAGE_PIXELS = 40_000_000


class UnsafeUpload(ValidationError):
    """Raised for every refusal so callers can catch one type."""


def sanitize_upload_filename(name):
    """Return a storage-safe base filename.

    Strips any directory component (both separators, so a Windows-style
    `..\\..\\evil.pdf` cannot survive a POSIX-only check), removes NUL bytes,
    and runs Django's own `get_valid_filename`. Refuses rather than silently
    rewrites when nothing usable is left.
    """
    if not name:
        raise UnsafeUpload('The file has no name.')

    cleaned = str(name).replace('\x00', '')
    # Take the last component under either separator convention.
    cleaned = cleaned.replace('\\', '/').rsplit('/', 1)[-1]
    cleaned = os.path.basename(cleaned).strip()

    if cleaned in ('', '.', '..'):
        raise UnsafeUpload('The file name is not valid.')

    cleaned = get_valid_filename(cleaned)
    if not cleaned or cleaned.lstrip('.') == '':
        raise UnsafeUpload('The file name is not valid.')
    return cleaned


def _extensions_of(filename):
    """All dotted suffixes, lowercased, e.g. report.pdf.exe -> ['.pdf', '.exe']."""
    base = filename.lstrip('.')
    return ['.' + part.lower() for part in base.split('.')[1:] if part]


def _read_head(uploaded, size=4096):
    """Read the first bytes without consuming the file for later handlers."""
    position = uploaded.tell() if hasattr(uploaded, 'tell') else 0
    try:
        uploaded.seek(0)
        head = uploaded.read(size)
    finally:
        uploaded.seek(position if isinstance(position, int) else 0)
    return head or b''


def _matches_signature(head, extension):
    _label, signatures, _family = _TYPES[extension]
    if not signatures:
        return True  # text types are validated by decoding instead
    if extension == '.webp':
        # RIFF....WEBP — the container tag sits at offset 8.
        return head.startswith(b'RIFF') and head[8:12] == b'WEBP'
    return any(head.startswith(signature) for signature in signatures)


def _detect_family(head):
    """Best-effort identification of what the bytes actually are."""
    for extension, (label, signatures, _family) in _TYPES.items():
        if signatures and any(head.startswith(signature) for signature in signatures):
            return label
    return 'an unrecognised format'


@deconstructible
class UploadValidator:
    """Django field validator. Deconstructible so it migrates cleanly."""

    def __init__(self, allowed_extensions=None, max_bytes=DEFAULT_MAX_BYTES):
        self.allowed_extensions = frozenset(
            allowed_extensions if allowed_extensions is not None else EVIDENCE_EXTENSIONS
        )
        self.max_bytes = max_bytes

    def __call__(self, value):
        validate_upload(
            value,
            allowed_extensions=self.allowed_extensions,
            max_bytes=self.max_bytes,
        )

    def __eq__(self, other):
        return (
            isinstance(other, UploadValidator)
            and self.allowed_extensions == other.allowed_extensions
            and self.max_bytes == other.max_bytes
        )

    def __hash__(self):
        return hash((self.allowed_extensions, self.max_bytes))


def validate_upload(value, *, allowed_extensions=None, max_bytes=DEFAULT_MAX_BYTES):
    """Validate one uploaded file. Raises UnsafeUpload with a specific reason."""
    allowed = frozenset(allowed_extensions or EVIDENCE_EXTENSIONS)

    uploaded = getattr(value, 'file', value)
    raw_name = getattr(value, 'name', None) or getattr(uploaded, 'name', None)
    filename = sanitize_upload_filename(raw_name)

    _check_size(value, uploaded, max_bytes)
    extension = _check_extensions(filename, allowed)

    head = _read_head(uploaded)
    if not head:
        raise UnsafeUpload('The file is empty.')

    _check_executable(head)
    _check_declared_type_matches_content(head, extension)

    family = _TYPES[extension][2]
    if family == 'text':
        _check_text(head, extension)
    elif family == 'zip':
        _check_archive(uploaded, extension)
    elif family == 'image':
        _check_image(uploaded)

    return filename


def _check_size(value, uploaded, max_bytes):
    size = getattr(value, 'size', None)
    if size is None:
        size = getattr(uploaded, 'size', None)
    if size is None:
        try:
            current = uploaded.tell()
            uploaded.seek(0, os.SEEK_END)
            size = uploaded.tell()
            uploaded.seek(current)
        except (AttributeError, OSError):
            return
    if size == 0:
        raise UnsafeUpload('The file is empty.')
    if size > max_bytes:
        raise UnsafeUpload(
            f'The file is {size / 1_048_576:.1f} MB. '
            f'The maximum is {max_bytes / 1_048_576:.0f} MB.'
        )


def _check_extensions(filename, allowed):
    extensions = _extensions_of(filename)
    if not extensions:
        raise UnsafeUpload(
            'The file has no extension. Allowed types: '
            + ', '.join(sorted(allowed))
        )

    final = extensions[-1]
    if final not in allowed:
        raise UnsafeUpload(
            f'Files of type "{final}" are not accepted. Allowed types: '
            + ', '.join(sorted(allowed))
        )

    # Double extensions: report.pdf.exe ends in .exe (already refused above),
    # but invoice.exe.pdf ends in .pdf and would otherwise pass. Any earlier
    # component that is a *known* type, or an obviously executable one, means
    # the name is trying to look like two things at once.
    dangerous_inner = {
        '.exe', '.sh', '.bat', '.cmd', '.com', '.scr', '.js', '.jar',
        '.php', '.py', '.rb', '.pl', '.ps1', '.dll', '.so', '.app', '.svg',
        '.html', '.htm', '.xml', '.zip',
    }
    for part in extensions[:-1]:
        if part in dangerous_inner or part in _TYPES:
            raise UnsafeUpload(
                f'The file name contains more than one file-type extension '
                f'("{part}" then "{final}"). Rename it to a single extension.'
            )
    return final


def _check_executable(head):
    for signature, description in _EXECUTABLE_SIGNATURES:
        if head.startswith(signature):
            raise UnsafeUpload(f'The file appears to be {description}, which is not accepted.')


def _check_declared_type_matches_content(head, extension):
    if not _matches_signature(head, extension):
        label = _TYPES[extension][0]
        raise UnsafeUpload(
            f'The file is named "{extension}" but its contents are '
            f'{_detect_family(head)}, not {label}. '
            'The extension and the actual file type must match.'
        )


def _check_text(head, extension):
    """CSV/TXT have no magic bytes, so prove they are really text."""
    if b'\x00' in head:
        raise UnsafeUpload(
            f'A "{extension}" file must be plain text, but this one contains binary data.'
        )
    try:
        head.decode('utf-8')
    except UnicodeDecodeError:
        try:
            head.decode('latin-1')
        except UnicodeDecodeError:
            raise UnsafeUpload(f'A "{extension}" file must be readable text.')

    lowered = head.lower()
    for marker, description in _ACTIVE_CONTENT_MARKERS:
        # Both sides lowercased: the markers are written in their conventional
        # casing (`<!ENTITY`), and comparing them against lowered content
        # without this would silently never match.
        if marker.lower() in lowered:
            raise UnsafeUpload(
                f'The file contains {description}. Evidence files must not '
                'contain active or scriptable content.'
            )


def _check_archive(uploaded, extension):
    """xlsx/docx are ZIP containers: check for traversal and zip bombs."""
    position = uploaded.tell() if hasattr(uploaded, 'tell') else 0
    try:
        uploaded.seek(0)
        try:
            with zipfile.ZipFile(uploaded) as archive:
                infos = archive.infolist()

                if len(infos) > _MAX_ARCHIVE_MEMBERS:
                    raise UnsafeUpload(
                        f'The file contains {len(infos)} entries, more than the '
                        f'{_MAX_ARCHIVE_MEMBERS} allowed.'
                    )

                compressed = uncompressed = 0
                for info in infos:
                    name = info.filename.replace('\\', '/')
                    if name.startswith('/') or '../' in name or name == '..':
                        raise UnsafeUpload(
                            f'The file contains an entry with an unsafe path '
                            f'("{info.filename}").'
                        )
                    compressed += info.compress_size
                    uncompressed += info.file_size

                if uncompressed > _MAX_ARCHIVE_UNCOMPRESSED_BYTES:
                    raise UnsafeUpload(
                        'The file expands to more than '
                        f'{_MAX_ARCHIVE_UNCOMPRESSED_BYTES // 1_048_576} MB and was refused.'
                    )
                if compressed > 0 and uncompressed / compressed > _MAX_ARCHIVE_EXPANSION_RATIO:
                    raise UnsafeUpload(
                        'The file expands far more than its size suggests and was '
                        'refused as a possible compression bomb.'
                    )
        except zipfile.BadZipFile:
            raise UnsafeUpload(
                f'The file is named "{extension}" but is not a readable archive.'
            )
    finally:
        uploaded.seek(position if isinstance(position, int) else 0)


def _check_image(uploaded):
    """Reject malformed images and decompression bombs before anything renders."""
    try:
        from PIL import Image, UnidentifiedImageError
    except ImportError:  # pragma: no cover - Pillow ships with matplotlib here
        return

    position = uploaded.tell() if hasattr(uploaded, 'tell') else 0
    try:
        uploaded.seek(0)
        try:
            with Image.open(uploaded) as image:
                width, height = image.size
                if width * height > _MAX_IMAGE_PIXELS:
                    raise UnsafeUpload(
                        f'The image is {width}×{height} pixels, which exceeds the '
                        f'{_MAX_IMAGE_PIXELS // 1_000_000} megapixel limit.'
                    )
                image.verify()
        except UnsafeUpload:
            raise
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
            raise UnsafeUpload('The file is not a readable image.')
    finally:
        uploaded.seek(position if isinstance(position, int) else 0)


# Ready-made validators for the evidence upload fields.
validate_evidence_upload = UploadValidator()
validate_document_upload = UploadValidator(allowed_extensions=DOCUMENT_EXTENSIONS)
