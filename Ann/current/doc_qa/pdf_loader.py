"""
Document text extraction for the RAG module.

Dispatches by file type: PDFs are extracted with pypdf (an optional dependency,
imported lazily), everything else is read as text with encoding fallbacks.
"""
from __future__ import annotations

from pathlib import Path


class DocLoadError(Exception):
    """Raised when a document cannot be loaded (missing dependency or bad file)."""


def extract_text(path) -> str:
    """Return the text content of *path*. PDFs are handled via pypdf."""
    path = Path(path)
    if path.suffix.lower() == ".pdf":
        return _extract_pdf(path)
    return _read_text_file(path)


def _extract_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise DocLoadError(
            "PDF support requires pypdf. Install it with: pip install pypdf"
        ) from e
    try:
        reader = PdfReader(str(path))
        pages = [(page.extract_text() or "") for page in reader.pages]
    except Exception as e:  # corrupt / encrypted / unreadable PDF
        raise DocLoadError(f"Failed to read PDF {path.name}: {e}") from e
    text = "\n\n".join(p for p in pages if p.strip()).strip()
    if not text:
        raise DocLoadError(
            f"No extractable text in {path.name} (it may be a scanned/image-only PDF)."
        )
    return text


def _read_text_file(path: Path) -> str:
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="latin-1", errors="replace")
