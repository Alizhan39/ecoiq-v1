from pypdf import PdfReader
import io


def extract_text(file_field) -> str:
    """Return plain text from an uploaded PDF or text file. Truncated to 40 000 chars."""
    name = file_field.name.lower()
    file_field.seek(0)
    raw = file_field.read()

    if name.endswith('.pdf'):
        reader = PdfReader(io.BytesIO(raw))
        pages = [page.extract_text() or '' for page in reader.pages]
        text = '\n'.join(pages)
    else:
        text = raw.decode('utf-8', errors='replace')

    return text[:40_000]
