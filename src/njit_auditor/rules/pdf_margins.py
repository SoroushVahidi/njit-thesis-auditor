"""Heuristic margin checks for layout-aware PDF text lines."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import BBox, PdfDocument, PdfTextLine
from njit_auditor.rules.pdf_page_numbers import PAGE_NUM_RE, _is_top_or_bottom_zone

INCH_TO_PT = 72.0
LEFT_MARGIN_PT = 1.5 * INCH_TO_PT
RIGHT_MARGIN_PT = 1.0 * INCH_TO_PT
TOP_MARGIN_PT = 1.0 * INCH_TO_PT
BOTTOM_MARGIN_PT = 1.0 * INCH_TO_PT
MIN_ARTIFACT_SIZE_PT = 2.0
OVERFLOW_TOLERANCE_PT = 3.0

# Artifact guard: a page/side group with this many lines all below this overflow
# is likely caused by a compressed-PDF coordinate shift rather than a real margin violation.
ARTIFACT_GUARD_MIN_COUNT = 5
ARTIFACT_GUARD_MAX_OVERFLOW_PT = 8.0


class MarginSide(str, Enum):
    LEFT = "left_margin"
    RIGHT = "right_margin"
    TOP = "top_margin"
    BOTTOM = "bottom_margin"


@dataclass
class LineViolation:
    side: MarginSide
    overflow_pt: float
    line: PdfTextLine


def _likely_page_number_text(text: str, y0: float, y1: float, page_height: float) -> bool:
    return _is_top_or_bottom_zone(y0, y1, page_height) and bool(PAGE_NUM_RE.match(text.strip()))


def _line_violation(
    line: PdfTextLine,
    page_height: float,
    allowed_x0: float,
    allowed_y0: float,
    allowed_x1: float,
    allowed_y1: float,
) -> LineViolation | None:
    text = line.text.strip()
    if not text:
        return None
    bbox: BBox = line.bbox
    if bbox.width < MIN_ARTIFACT_SIZE_PT or bbox.height < MIN_ARTIFACT_SIZE_PT:
        return None
    if _likely_page_number_text(text, bbox.y0, bbox.y1, page_height):
        return None

    overflow_by_side: dict[MarginSide, float] = {}
    if bbox.x0 < allowed_x0:
        overflow_by_side[MarginSide.LEFT] = allowed_x0 - bbox.x0
    if bbox.x1 > allowed_x1:
        overflow_by_side[MarginSide.RIGHT] = bbox.x1 - allowed_x1
    if bbox.y0 < allowed_y0:
        overflow_by_side[MarginSide.TOP] = allowed_y0 - bbox.y0
    if bbox.y1 > allowed_y1:
        overflow_by_side[MarginSide.BOTTOM] = bbox.y1 - allowed_y1

    if not overflow_by_side:
        return None
    side, overflow = max(overflow_by_side.items(), key=lambda item: item[1])
    if overflow <= OVERFLOW_TOLERANCE_PT:
        return None
    return LineViolation(side=side, overflow_pt=overflow, line=line)


def _group_confidence(worst_overflow_pt: float, count: int) -> str:
    large_count_ok = (
        count >= ARTIFACT_GUARD_MIN_COUNT and worst_overflow_pt >= ARTIFACT_GUARD_MAX_OVERFLOW_PT
    )
    if worst_overflow_pt >= 12.0 or large_count_ok:
        return "high"
    if worst_overflow_pt >= 5.0 or count >= 2:
        return "medium"
    return "low"


def run_pdf_margin_rule(pdf_doc: PdfDocument) -> list[AuditFinding]:
    """Detect possible text lines outside expected margin rectangle."""

    findings: list[AuditFinding] = []
    for page in pdf_doc.pages:
        allowed_x0 = LEFT_MARGIN_PT
        allowed_y0 = TOP_MARGIN_PT
        allowed_x1 = page.width - RIGHT_MARGIN_PT
        allowed_y1 = page.height - BOTTOM_MARGIN_PT

        grouped: dict[MarginSide, list[LineViolation]] = {}
        for block in page.text_blocks:
            for line in block.lines:
                violation = _line_violation(
                    line, page.height, allowed_x0, allowed_y0, allowed_x1, allowed_y1
                )
                if not violation:
                    continue
                grouped.setdefault(violation.side, []).append(violation)

        for side, violations in grouped.items():
            worst = max(v.overflow_pt for v in violations)
            count = len(violations)
            # Suppress groups where many lines all barely cross the margin: this pattern
            # indicates a compressed-PDF coordinate shift, not a real margin violation.
            if count >= ARTIFACT_GUARD_MIN_COUNT and worst < ARTIFACT_GUARD_MAX_OVERFLOW_PT:
                continue
            confidence = _group_confidence(worst, count)
            findings.append(
                AuditFinding(
                    rule_id="P011",
                    severity=Severity.WARNING,
                    page=page.page_number,
                    message=f"Possible text crossing {side.value}.",
                    details={
                        "side": side.value,
                        "issue_type": "margin_boundary_violation",
                        "worst_overflow_pt": f"{worst:.1f}",
                        "affected_line_count": str(count),
                        "confidence": confidence,
                        "triage_tier": "informational",
                        "suggested_fix": (
                            "Review margin settings and move content inside required layout bounds."
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
