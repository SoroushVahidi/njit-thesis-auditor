"""Detect NJIT Digital Commons repository wrapper pages in thesis PDFs."""

from __future__ import annotations

import re
from collections.abc import Sequence

from njit_auditor.pdf_models import PdfDocument, PdfPage

_DIGITAL_COMMONS_MARKERS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("digital_commons_heading", re.compile(r"digital\s+commons\s*@\s*njit", re.IGNORECASE)),
    ("electronic_theses", re.compile(r"electronic\s+theses\s+and\s+dissertations", re.IGNORECASE)),
    ("recommended_citation", re.compile(r"recommended\s+citation", re.IGNORECASE)),
    (
        "open_access_notice",
        re.compile(
            r"this\s+thesis\s+is\s+brought\s+to\s+you\s+for\s+free\s+and\s+open\s+access",
            re.IGNORECASE,
        ),
    ),
    ("digitalcommons_url", re.compile(r"digitalcommons\.njit\.edu", re.IGNORECASE)),
)
_MIN_MARKER_HITS = 2
_LAYOUT_WARNING_RULES = frozenset({"P011", "P012", "P013"})


def _page_text_blob(page: PdfPage) -> str:
    return " ".join(block.text for block in page.text_blocks if block.text.strip())


def digital_commons_wrapper_marker_hits(page: PdfPage) -> list[str]:
    """Return matched marker ids for a page, if any."""
    blob = _page_text_blob(page)
    if not blob.strip():
        return []
    return [marker_id for marker_id, pattern in _DIGITAL_COMMONS_MARKERS if pattern.search(blob)]


def is_digital_commons_wrapper_page(page: PdfPage) -> bool:
    """Return True when a page looks like a repository-generated Digital Commons wrapper."""
    hits = digital_commons_wrapper_marker_hits(page)
    if len(hits) >= _MIN_MARKER_HITS:
        return True
    if "digitalcommons_url" in hits and (
        "digital_commons_heading" in hits or "recommended_citation" in hits
    ):
        return True
    return False


def detect_digital_commons_wrapper_pages(pdf_document: PdfDocument) -> set[int]:
    """Return 1-based page numbers that look like Digital Commons wrapper pages."""
    return {
        page.page_number
        for page in pdf_document.pages
        if is_digital_commons_wrapper_page(page)
    }


def digital_commons_wrapper_metadata(wrapper_pages: Sequence[int]) -> dict[str, str]:
    """Serialize wrapper-page metadata for audit JSON exports."""
    pages = sorted({int(page) for page in wrapper_pages})
    if not pages:
        return {}
    page_list = ", ".join(str(page) for page in pages[:8])
    if len(pages) > 8:
        page_list = f"{page_list}, and {len(pages) - 8} more"
    return {
        "digital_commons_wrapper_pages": ",".join(str(page) for page in pages),
        "digital_commons_wrapper_page_count": str(len(pages)),
        "digital_commons_wrapper_pages_compact": page_list,
    }


def is_layout_warning_suppressed_on_wrapper_page(
    rule_id: str,
    page: int | None,
    wrapper_pages: set[int],
) -> bool:
    """Return True when a layout warning should not be shown as a normal thesis defect."""
    return (
        rule_id in _LAYOUT_WARNING_RULES
        and page is not None
        and page in wrapper_pages
    )
