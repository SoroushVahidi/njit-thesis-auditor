"""P082 — experimental opt-in landscape page-number orientation advisory."""

from __future__ import annotations

import math
from dataclasses import dataclass

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import BBox, PdfDocument, PdfPage, PdfTextLine
from njit_auditor.rules.pdf_page_numbers import (
    TOP_BOTTOM_ZONE_RATIO,
    _candidate_confidence,
    _classify_position_type,
    detect_page_number_candidates,
)

P082_RULE_ID = "P082"
SUPPORTED_WMODES = {0}
CARDINAL_DIRS: dict[tuple[float, float], int] = {
    (1.0, 0.0): 0,
    (0.0, -1.0): 90,
    (-1.0, 0.0): 180,
    (0.0, 1.0): 270,
}
CARDINAL_TOLERANCE = 0.15
SIDE_EDGE_X_RATIO = 0.12
BOTTOM_ZONE_RATIO = TOP_BOTTOM_ZONE_RATIO
CENTER_TOLERANCE_PT = 24.0
VERTICAL_MIDDLE_Y_MIN_RATIO = 0.2
VERTICAL_MIDDLE_Y_MAX_RATIO = 0.8
BBOX_MATCH_TOLERANCE_PT = 4.0

ISSUE_ORIENTATION = "landscape_page_number_orientation_advisory"
ISSUE_POSITION = "landscape_page_number_position_advisory"


@dataclass(frozen=True)
class _AcceptedCandidate:
    page_number: int
    position_type: str
    bbox: BBox
    line: PdfTextLine


def quantize_dir(line_dir: tuple[float, float] | None) -> int | None:
    """Map a near-cardinal PyMuPDF direction vector to degrees, else None."""
    if line_dir is None:
        return None
    dx, dy = line_dir
    magnitude = math.hypot(dx, dy)
    if magnitude <= 0:
        return None
    ux, uy = dx / magnitude, dy / magnitude
    for (card_x, card_y), angle in CARDINAL_DIRS.items():
        if math.hypot(ux - card_x, uy - card_y) <= CARDINAL_TOLERANCE:
            return angle
    return None


def visual_angle(line_angle: int, page_rotation: int) -> int:
    return (line_angle + page_rotation) % 360


def is_visually_landscape_page(page: PdfPage) -> bool:
    return page.is_visually_landscape


def _normalize_bbox(bbox: BBox) -> str:
    return (
        f"{bbox.x0:.1f},{bbox.y0:.1f},{bbox.x1:.1f},{bbox.y1:.1f}"
    )


def _find_candidate_line(
    page: PdfPage, candidate_text: str, position_type: str
) -> PdfTextLine | None:
    matches: list[PdfTextLine] = []
    for block in page.text_blocks:
        for line in block.lines:
            clean = " ".join(line.text.strip().split())
            if clean != candidate_text:
                continue
            line_position = _classify_position_type(
                line.bbox.x0, line.bbox.x1, line.bbox.y1, page.width, page.height
            )
            if line_position == position_type:
                matches.append(line)
    if len(matches) == 1:
        return matches[0]
    if not matches:
        return None
    return matches[0]


def _accepted_candidates_by_page(pdf_doc: PdfDocument) -> dict[int, _AcceptedCandidate]:
    candidates = detect_page_number_candidates(pdf_doc)
    by_page: dict[int, list] = {}
    for candidate in candidates:
        if _candidate_confidence(candidate) != "medium":
            continue
        by_page.setdefault(candidate.page_number, []).append(candidate)

    accepted: dict[int, _AcceptedCandidate] = {}
    for page_number, page_candidates in by_page.items():
        if len(page_candidates) != 1:
            continue
        candidate = page_candidates[0]
        page = pdf_doc.pages[page_number - 1]
        line = _find_candidate_line(page, candidate.text, candidate.position_type)
        if line is None:
            continue
        accepted[page_number] = _AcceptedCandidate(
            page_number=page_number,
            position_type=candidate.position_type,
            bbox=line.bbox,
            line=line,
        )
    return accepted


def _location_bucket(line: PdfTextLine, page: PdfPage) -> str | None:
    line_center_x = (line.bbox.x0 + line.bbox.x1) / 2.0
    line_center_y = (line.bbox.y0 + line.bbox.y1) / 2.0
    in_bottom = line.bbox.y0 >= page.height * (1.0 - BOTTOM_ZONE_RATIO)
    near_center = abs(line_center_x - page.width / 2.0) <= CENTER_TOLERANCE_PT
    if in_bottom and near_center:
        return "bottom_center"
    near_left = line_center_x <= page.width * SIDE_EDGE_X_RATIO
    near_right = line_center_x >= page.width * (1.0 - SIDE_EDGE_X_RATIO)
    in_vertical_middle = (
        page.height * VERTICAL_MIDDLE_Y_MIN_RATIO
        <= line_center_y
        <= page.height * VERTICAL_MIDDLE_Y_MAX_RATIO
    )
    if (near_left or near_right) and in_vertical_middle:
        return "side_edge"
    if in_bottom:
        return "bottom_other"
    if line.bbox.y1 <= page.height * TOP_BOTTOM_ZONE_RATIO:
        return "top_margin"
    return "other"


def _orientation_advisory_reason(visual: int) -> str | None:
    if visual in {90, 270}:
        return "vertical_text_on_landscape_page"
    return None


def _position_advisory_reason(bucket: str, position_type: str) -> str | None:
    if bucket == "side_edge":
        return "page_number_on_long_edge"
    if position_type in {"top_center", "top_right"} and bucket == "top_margin":
        return "page_number_in_top_margin_on_landscape"
    if position_type == "other" and bucket not in {"bottom_center", "bottom_other"}:
        return "unexpected_margin_bucket"
    return None


def check_pdf_landscape_page_number_orientation(
    pdf_doc: PdfDocument,
    *,
    enabled: bool = False,
) -> list[AuditFinding]:
    """Emit P082 advisories only when explicitly enabled."""

    if not enabled:
        return []

    findings: list[AuditFinding] = []
    accepted_by_page = _accepted_candidates_by_page(pdf_doc)

    for page in pdf_doc.pages:
        if not is_visually_landscape_page(page):
            continue
        if not page.text_blocks:
            continue

        accepted = accepted_by_page.get(page.page_number)
        if accepted is None:
            continue

        line = accepted.line
        if line.line_dir is None:
            continue
        if line.wmode not in SUPPORTED_WMODES:
            continue

        line_angle = quantize_dir(line.line_dir)
        if line_angle is None:
            continue

        visual = visual_angle(line_angle, page.page_rotation)
        bucket = _location_bucket(line, page)
        if bucket is None:
            continue

        orientation_reason = _orientation_advisory_reason(visual)
        position_reason = _position_advisory_reason(bucket, accepted.position_type)

        if orientation_reason:
            findings.append(
                _make_advisory(
                    page=page,
                    accepted=accepted,
                    issue_type=ISSUE_ORIENTATION,
                    line_angle=line_angle,
                    visual_angle=visual,
                    location_bucket=bucket,
                    advisory_reason=orientation_reason,
                )
            )

        if position_reason and position_reason != orientation_reason:
            findings.append(
                _make_advisory(
                    page=page,
                    accepted=accepted,
                    issue_type=ISSUE_POSITION,
                    line_angle=line_angle,
                    visual_angle=visual,
                    location_bucket=bucket,
                    advisory_reason=position_reason,
                )
            )

    return findings


def _make_advisory(
    *,
    page: PdfPage,
    accepted: _AcceptedCandidate,
    issue_type: str,
    line_angle: int,
    visual_angle: int,
    location_bucket: str,
    advisory_reason: str,
) -> AuditFinding:
    line = accepted.line
    dir_x, dir_y = line.line_dir or (0.0, 0.0)
    return AuditFinding(
        rule_id=P082_RULE_ID,
        severity=Severity.WARNING,
        page=page.page_number,
        message=(
            "Experimental landscape page-number orientation advisory for manual review."
        ),
        details={
            "page_number": str(page.page_number),
            "issue_type": issue_type,
            "page_width_pt": f"{page.width:.1f}",
            "page_height_pt": f"{page.height:.1f}",
            "page_rotation": str(page.page_rotation),
            "candidate_bbox": _normalize_bbox(accepted.bbox),
            "line_dir": f"{dir_x:.3f},{dir_y:.3f}",
            "line_angle_deg": str(line_angle),
            "visual_angle_deg": str(visual_angle),
            "wmode": str(line.wmode if line.wmode is not None else ""),
            "location_bucket": location_bucket,
            "position_type": accepted.position_type,
            "confidence": "medium",
            "triage_tier": "manual_review",
            "advisory_reason": advisory_reason,
            "experimental_rule": "true",
        },
    )
