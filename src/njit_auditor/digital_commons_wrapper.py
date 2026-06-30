"""Detect repository-generated wrapper pages inserted before the thesis manuscript."""

from __future__ import annotations

import re
from collections.abc import Collection, Sequence
from dataclasses import dataclass

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
_COPYRIGHT_WARNING_MARKERS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "copyright_related_rights",
        re.compile(r"copyright\s+and/or\s+related\s+rights", re.IGNORECASE),
    ),
    ("rights_holder", re.compile(r"rights-holder", re.IGNORECASE)),
    (
        "permission_required",
        re.compile(r"obtain\s+permission\s+from\s+the\s+rights-holder", re.IGNORECASE),
    ),
    (
        "creative_commons_record",
        re.compile(r"creative\s+commons\s+license\s+in\s+the\s+record", re.IGNORECASE),
    ),
)
_MIN_COPYRIGHT_WARNING_HITS = 2

# Strong single-marker patterns for US federal copyright-law notice pages and
# Van Houten Library privacy/redaction notices.  Any one of these on a page is
# sufficient to classify it as a non-manuscript repository wrapper page because
# each pattern is highly specific to institutional boilerplate.
_REPOSITORY_LEGALESE_MARKERS: tuple[tuple[str, re.Pattern[str]], ...] = (
    # --- US federal copyright law warning (Van Houten Library / Digital Commons) ---
    (
        "copyright_warning_heading",
        re.compile(r"copyright\s+warning\s*(?:&|and)\s*restrictions", re.IGNORECASE),
    ),
    (
        "us_copyright_law_intro",
        re.compile(r"copyright\s+law\s+of\s+the\s+united\s+states", re.IGNORECASE),
    ),
    (
        "governs_photocopies",
        re.compile(r"governs\s+the\s+making\s+of\s+photocopies", re.IGNORECASE),
    ),
    (
        "libraries_archives_authorized",
        re.compile(r"libraries\s+and\s+archives\s+are\s+authorized", re.IGNORECASE),
    ),
    (
        "liable_copyright_infringement",
        re.compile(r"liable\s+for\s+copyright\s+infringement", re.IGNORECASE),
    ),
    (
        "copying_order_refused",
        re.compile(
            r"right\s+to\s+refuse\s+to\s+accept\s+a\s+copying\s+order", re.IGNORECASE
        ),
    ),
    # --- Van Houten Library privacy/redaction notice ---
    (
        "van_houten_library",
        re.compile(r"van\s+houten\s+library", re.IGNORECASE),
    ),
    (
        "removed_personal_signatures",
        re.compile(
            r"removed\s+(?:some\s+of\s+the\s+)?personal\s+information\s+and\s+all\s+signatures",
            re.IGNORECASE,
        ),
    ),
    (
        "protect_identity_graduates",
        re.compile(
            r"protect\s+the\s+identity\s+of\s+(?:njit\s+)?graduates", re.IGNORECASE
        ),
    ),
)
_MIN_LEGALESE_HITS = 1
_MAX_LEADING_WRAPPER_SCAN_PAGES = 4
_LAYOUT_WARNING_RULES = frozenset({"P011", "P012", "P013"})


@dataclass(frozen=True)
class PdfPageIdentity:
    """Stable page identity spanning original-PDF and wrapper-filtered views."""

    original_page_index: int
    original_page_number: int
    manuscript_page_index: int
    manuscript_page_number: int
    display_page_label: str


def _page_text_blob(page: PdfPage) -> str:
    return " ".join(block.text for block in page.text_blocks if block.text.strip())


def digital_commons_wrapper_marker_hits(page: PdfPage) -> list[str]:
    """Return matched marker ids for a page, if any."""
    blob = _page_text_blob(page)
    if not blob.strip():
        return []
    return [marker_id for marker_id, pattern in _DIGITAL_COMMONS_MARKERS if pattern.search(blob)]


def repository_copyright_warning_marker_hits(page: PdfPage) -> list[str]:
    """Return matched copyright-warning marker ids for a page, if any."""
    blob = _page_text_blob(page)
    if not blob.strip():
        return []
    hits = [
        marker_id
        for marker_id, pattern in _COPYRIGHT_WARNING_MARKERS
        if pattern.search(blob)
    ]
    hits += [
        marker_id
        for marker_id, pattern in _REPOSITORY_LEGALESE_MARKERS
        if pattern.search(blob)
    ]
    return hits


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


def is_repository_copyright_warning_page(page: PdfPage) -> bool:
    """Return True for a repository-inserted copyright-warning page before the thesis."""
    blob = _page_text_blob(page)
    if not blob.strip():
        return False
    original_hits = [m for m, p in _COPYRIGHT_WARNING_MARKERS if p.search(blob)]
    if len(original_hits) >= _MIN_COPYRIGHT_WARNING_HITS:
        return True
    legalese_hits = [m for m, p in _REPOSITORY_LEGALESE_MARKERS if p.search(blob)]
    return len(legalese_hits) >= _MIN_LEGALESE_HITS


def is_repository_wrapper_page(page: PdfPage) -> bool:
    """Return True when a page looks like a repository wrapper, not manuscript content."""
    return is_digital_commons_wrapper_page(page) or is_repository_copyright_warning_page(page)


def detect_digital_commons_wrapper_pages(pdf_document: PdfDocument) -> set[int]:
    """Return a leading run of repository wrapper pages before the manuscript."""
    wrapper_pages: list[int] = []
    for idx, page in enumerate(pdf_document.pages):
        if is_repository_wrapper_page(page):
            wrapper_pages.append(page.page_number)
            continue
        if wrapper_pages:
            break
        if idx + 1 >= _MAX_LEADING_WRAPPER_SCAN_PAGES:
            break
    return set(wrapper_pages)


def without_wrapper_pages(
    pdf_document: PdfDocument,
    wrapper_pages: Collection[int],
) -> PdfDocument:
    """Return a view of the document with repository wrapper pages removed."""
    skipped = {int(page) for page in wrapper_pages}
    if not skipped:
        return pdf_document
    filtered_pages: list[PdfPage] = []
    manuscript_index = 0
    for page in pdf_document.pages:
        if page.page_number in skipped:
            continue
        original_page_number = (
            page.original_page_number
            if page.original_page_number is not None
            else page.page_number
        )
        original_page_index = (
            page.original_page_index
            if page.original_page_index is not None
            else max(original_page_number - 1, 0)
        )
        manuscript_page_number = manuscript_index + 1
        display_page_label = (
            f"manuscript page {manuscript_page_number} / PDF page {original_page_number}"
            if original_page_number != manuscript_page_number
            else str(original_page_number)
        )
        filtered_pages.append(
            page.model_copy(
                update={
                    "original_page_index": original_page_index,
                    "original_page_number": original_page_number,
                    "manuscript_page_index": manuscript_index,
                    "manuscript_page_number": manuscript_page_number,
                    "display_page_label": display_page_label,
                }
            )
        )
        manuscript_index += 1
    return PdfDocument(
        path=pdf_document.path,
        pages=filtered_pages,
    )


def page_identity(page: PdfPage) -> PdfPageIdentity:
    """Return the resolved original/manuscript identity for a PDF page."""
    original_page_number = (
        page.original_page_number
        if page.original_page_number is not None
        else page.page_number
    )
    original_page_index = (
        page.original_page_index
        if page.original_page_index is not None
        else max(original_page_number - 1, 0)
    )
    manuscript_page_number = (
        page.manuscript_page_number
        if page.manuscript_page_number is not None
        else original_page_number
    )
    manuscript_page_index = (
        page.manuscript_page_index
        if page.manuscript_page_index is not None
        else max(manuscript_page_number - 1, 0)
    )
    display_page_label = page.display_page_label.strip() or str(original_page_number)
    return PdfPageIdentity(
        original_page_index=original_page_index,
        original_page_number=original_page_number,
        manuscript_page_index=manuscript_page_index,
        manuscript_page_number=manuscript_page_number,
        display_page_label=display_page_label,
    )


def page_identity_details(page: PdfPage) -> dict[str, str]:
    """Return finding-detail fields describing a page's original/manuscript identity."""
    identity = page_identity(page)
    details = {
        "original_pdf_page_index": str(identity.original_page_index),
        "original_pdf_page_number": str(identity.original_page_number),
        "manuscript_page_index": str(identity.manuscript_page_index),
        "manuscript_page_number": str(identity.manuscript_page_number),
    }
    if identity.display_page_label != str(identity.original_page_number):
        details["page_label"] = identity.display_page_label
    return details


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
