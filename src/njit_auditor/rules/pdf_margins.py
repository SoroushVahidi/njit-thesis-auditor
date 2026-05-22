"""Heuristic margin checks for layout-aware PDF blocks."""

from __future__ import annotations

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument
from njit_auditor.rules.pdf_page_numbers import PAGE_NUM_RE, _is_top_or_bottom_zone

INCH_TO_PT = 72.0
LEFT_MARGIN_PT = 1.5 * INCH_TO_PT
RIGHT_MARGIN_PT = 1.0 * INCH_TO_PT
TOP_MARGIN_PT = 1.0 * INCH_TO_PT
BOTTOM_MARGIN_PT = 1.0 * INCH_TO_PT


def _likely_page_number_text(text: str, y0: float, y1: float, page_height: float) -> bool:
    return _is_top_or_bottom_zone(y0, y1, page_height) and bool(PAGE_NUM_RE.match(text.strip()))


def run_pdf_margin_rule(pdf_doc: PdfDocument) -> list[AuditFinding]:
    """Detect possible text blocks outside expected margin rectangle."""

    findings: list[AuditFinding] = []
    for page in pdf_doc.pages:
        allowed_x0 = LEFT_MARGIN_PT
        allowed_y0 = TOP_MARGIN_PT
        allowed_x1 = page.width - RIGHT_MARGIN_PT
        allowed_y1 = page.height - BOTTOM_MARGIN_PT

        for block in page.text_blocks:
            if _likely_page_number_text(block.text, block.bbox.y0, block.bbox.y1, page.height):
                continue
            outside = (
                block.bbox.x0 < allowed_x0
                or block.bbox.y0 < allowed_y0
                or block.bbox.x1 > allowed_x1
                or block.bbox.y1 > allowed_y1
            )
            if not outside:
                continue
            findings.append(
                AuditFinding(
                    rule_id="P011",
                    severity=Severity.WARNING,
                    page=page.page_number,
                    message="Possible text outside assumed NJIT margin rectangle.",
                    details={
                        "bbox": (
                            f"{block.bbox.x0:.1f},{block.bbox.y0:.1f},"
                            f"{block.bbox.x1:.1f},{block.bbox.y1:.1f}"
                        ),
                        "suggested_fix": (
                            "Review margins and move text inside required layout bounds if needed."
                        ),
                    },
                )
            )

    if findings:
        return findings
    return [
        AuditFinding(
            rule_id="P011",
            severity=Severity.PASS,
            message="No obvious margin-boundary text violations detected.",
        )
    ]
