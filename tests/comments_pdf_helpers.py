"""Content parity checks for synthetic comments PDFs, independent of layout."""

from __future__ import annotations

import io
import re

import fitz
from pypdf import PdfReader


def assert_comments_pdf_parity(payload: bytes, canonical: str) -> None:
    assert payload.startswith(b"%PDF-")
    with fitz.open(stream=payload, filetype="pdf") as document:
        assert document.page_count > 0
        assert not document.embfile_count()
        assert all(not page.get_images() and not page.get_links() for page in document)
        assert all(not list(page.annots() or []) for page in document)
        texts = ["\n".join(page.get_text() for page in document)]
    # A second PDF reader checks the ToUnicode maps rather than only visual glyphs.
    texts.append("\n".join(page.extract_text() for page in PdfReader(io.BytesIO(payload)).pages))
    for text in texts:
        text = re.sub(r"NJIT Comments Report\s*Report page \d+", "", text)
        text = text.replace("Comments Report", "", 1)
        assert "".join(text.split()) == "".join(canonical.split())
