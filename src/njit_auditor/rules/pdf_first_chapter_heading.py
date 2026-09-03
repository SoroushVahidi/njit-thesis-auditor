"""Check that the first body page starts with the required CHAPTER 1 heading."""

from __future__ import annotations

import re

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument, format_bbox_detail
from njit_auditor.rules.pdf_page_numbering_regime import _classify_pages

_HEADING_SCAN_BOTTOM_PT = 220.0
_CHAPTER_ONE_RE = re.compile(r"^CHAPTER\s*1(?:\D|$)", re.IGNORECASE)


def _starts_with_chapter_one(text: str) -> bool:
    compact = " ".join(text.strip().split())
    return bool(_CHAPTER_ONE_RE.match(compact))


def check_pdf_first_chapter_heading(pdf_doc: PdfDocument) -> list[AuditFinding]:
    """Emit one finding when the first classified body page lacks CHAPTER 1.

    The body-page classification is shared with P028. A later chapter heading
    cannot satisfy this check because only the first body page is inspected.
    """

    regions, _ = _classify_pages(pdf_doc)
    body_pages = [page_number for page_number, region in regions.items() if region == "body"]
    if not body_pages:
        return []

    first_body_page_number = min(body_pages)
    page = next(
        (
            candidate
            for candidate in pdf_doc.pages
            if candidate.page_number == first_body_page_number
        ),
        None,
    )
    if page is None:
        return []

    first_text_line = None
    for block in page.text_blocks:
        for line in block.lines:
            text = " ".join(line.text.strip().split())
            if not text or line.bbox.y0 > _HEADING_SCAN_BOTTOM_PT:
                continue
            first_text_line = line
            if _starts_with_chapter_one(text):
                return []
            break
        if first_text_line is not None:
            break

    details = {
        "page_number": str(first_body_page_number),
        "issue_type": "missing_first_chapter_one_heading",
        "expected_heading": "CHAPTER 1",
        "observed_heading": (
            "" if first_text_line is None else " ".join(first_text_line.text.split())
        ),
        "confidence": "high",
        "triage_tier": "high",
    }
    if first_text_line is not None:
        details["bbox"] = format_bbox_detail(first_text_line.bbox)
    return [
        AuditFinding(
            rule_id="P085",
            severity=Severity.WARNING,
            page=first_body_page_number,
            message="The first body page does not begin with the required CHAPTER 1 heading.",
            details=details,
        )
    ]
