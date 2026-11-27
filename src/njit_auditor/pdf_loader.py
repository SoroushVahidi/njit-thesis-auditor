"""PDF loading helpers using PyMuPDF."""

from __future__ import annotations

from pathlib import Path

import pymupdf as fitz

from njit_auditor.models import DocumentInfo, PageInfo


def load_document_info(pdf_path: str) -> DocumentInfo:
    """Load basic PDF geometry information for later checks."""
    path = Path(pdf_path)
    with fitz.open(path) as doc:
        pages = [
            PageInfo(page_index=idx, width=float(page.rect.width), height=float(page.rect.height))
            for idx, page in enumerate(doc)
        ]
        return DocumentInfo(path=str(path), page_count=len(doc), pages=pages)


def read_page_text(pdf_path: str, page_index: int) -> str:
    """Read plain text from a single page."""
    with fitz.open(pdf_path) as doc:
        if page_index < 0 or page_index >= len(doc):
            return ""
        return doc[page_index].get_text("text")
