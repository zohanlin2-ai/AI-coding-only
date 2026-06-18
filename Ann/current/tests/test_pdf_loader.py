"""
Tests for doc_qa.pdf_loader — text/PDF dispatch and graceful failures.

pypdf is mocked via sys.modules so these tests run whether or not the optional
dependency is installed.
"""
import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from doc_qa.pdf_loader import DocLoadError, extract_text


def _install_fake_pypdf(monkeypatch, pages_text, raise_on_read=False):
    fake = types.ModuleType("pypdf")

    class _Page:
        def __init__(self, text):
            self._text = text

        def extract_text(self):
            return self._text

    class _Reader:
        def __init__(self, _path):
            if raise_on_read:
                raise ValueError("corrupt pdf")
            self.pages = [_Page(t) for t in pages_text]

    fake.PdfReader = _Reader
    monkeypatch.setitem(sys.modules, "pypdf", fake)


# --- text dispatch ---------------------------------------------------------

def test_extract_plain_text_file(tmp_path):
    f = tmp_path / "note.md"
    f.write_text("# Title\n\nbody text", encoding="utf-8")
    assert extract_text(f) == "# Title\n\nbody text"


def test_extract_text_latin1_fallback(tmp_path):
    f = tmp_path / "weird.txt"
    f.write_bytes(b"caf\xe9")  # invalid utf-8, valid latin-1
    assert "caf" in extract_text(f)


# --- pdf dispatch ----------------------------------------------------------

def test_extract_pdf_joins_pages(tmp_path, monkeypatch):
    _install_fake_pypdf(monkeypatch, ["Page one.", "Page two."])
    f = tmp_path / "doc.pdf"
    f.write_bytes(b"%PDF-1.4 fake")
    assert extract_text(f) == "Page one.\n\nPage two."


def test_extract_pdf_skips_empty_pages(tmp_path, monkeypatch):
    _install_fake_pypdf(monkeypatch, ["Real content", "", "   "])
    f = tmp_path / "doc.pdf"
    f.write_bytes(b"%PDF")
    assert extract_text(f) == "Real content"


# --- pdf failure modes -----------------------------------------------------

def test_missing_pypdf_raises_with_hint(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "pypdf", None)  # forces ImportError
    f = tmp_path / "doc.pdf"
    f.write_bytes(b"%PDF")
    with pytest.raises(DocLoadError) as exc:
        extract_text(f)
    assert "pip install pypdf" in str(exc.value)


def test_corrupt_pdf_raises(tmp_path, monkeypatch):
    _install_fake_pypdf(monkeypatch, [], raise_on_read=True)
    f = tmp_path / "doc.pdf"
    f.write_bytes(b"%PDF")
    with pytest.raises(DocLoadError):
        extract_text(f)


def test_image_only_pdf_raises(tmp_path, monkeypatch):
    _install_fake_pypdf(monkeypatch, ["", ""])  # no extractable text
    f = tmp_path / "scan.pdf"
    f.write_bytes(b"%PDF")
    with pytest.raises(DocLoadError) as exc:
        extract_text(f)
    assert "scanned" in str(exc.value).lower() or "no extractable text" in str(exc.value).lower()
