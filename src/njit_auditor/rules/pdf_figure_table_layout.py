"""Conservative PDF figure/table body layout checks (centering and caption placement)."""

from __future__ import annotations

import re

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import BBox, PdfDocument, PdfPage, PdfTextBlock, PdfTextLine
from njit_auditor.rules.pdf_captions import (
    CAPTION_START_RE,
    CaptionLine,
    detect_caption_lines,
    normalize_caption_text,
)
from njit_auditor.rules.pdf_margins import (
    BOTTOM_MARGIN_PT,
    LEFT_MARGIN_PT,
    RIGHT_MARGIN_PT,
    TOP_MARGIN_PT,
)
from njit_auditor.rules.pdf_page_numbers import PAGE_NUM_RE

CENTER_TOLERANCE_PT = 15.0
CAPTION_BODY_GAP_PT = 8.0
MAX_BODY_SEARCH_GAP_PT = 120.0
MIN_BODY_LINES = 2
MIN_BODY_WIDTH_PT = 72.0
MIN_BODY_ALPHA_CHARS = 12

FLOAT_NUMBER_RE = re.compile(
    r"^\s*(?:figure|fig\.|table)\s+(?P<number>[0-9ivxlcdm]+(?:[.\-][0-9ivxlcdm]+)*)",
    re.IGNORECASE,
)


CHAPTER_HEADING_RE = re.compile(r"^CHAPTER\s+", re.IGNORECASE)
MAX_CLUSTER_LINE_GAP_PT = 24.0


def _collect_page_lines(page: PdfPage) -> list[PdfTextLine]:
    lines: list[PdfTextLine] = []
    for block in page.text_blocks:
        lines.extend(block.lines)
    return lines


def _text_area_bounds(page: PdfPage) -> tuple[float, float]:
    return LEFT_MARGIN_PT, page.width - RIGHT_MARGIN_PT


def _text_area_center(page: PdfPage) -> float:
    x0, x1 = _text_area_bounds(page)
    return (x0 + x1) / 2.0


def _bbox_center_x(bbox: BBox) -> float:
    return (bbox.x0 + bbox.x1) / 2.0


def _is_caption_line_text(text: str) -> bool:
    clean = normalize_caption_text(text)
    if not clean or PAGE_NUM_RE.match(clean):
        return False
    match = CAPTION_START_RE.match(clean)
    if not match:
        return False
    body = normalize_caption_text(match.group("body"))
    return len(body) >= 14


def _block_is_chapter_heading(block: PdfTextBlock) -> bool:
    return bool(CHAPTER_HEADING_RE.match(block.text.strip()))


def _cluster_body_blocks(blocks: list[PdfTextBlock]) -> list[list[PdfTextBlock]]:
    if not blocks:
        return []
    ordered = sorted(blocks, key=lambda block: block.bbox.y0)
    clusters: list[list[PdfTextBlock]] = [[ordered[0]]]
    for block in ordered[1:]:
        previous = clusters[-1][-1]
        gap = block.bbox.y0 - previous.bbox.y1
        if gap <= MAX_CLUSTER_LINE_GAP_PT:
            clusters[-1].append(block)
        else:
            clusters.append([block])
    return clusters


def _select_body_cluster(blocks: list[PdfTextBlock]) -> list[PdfTextBlock] | None:
    qualifying = [
        cluster
        for cluster in _cluster_body_blocks(blocks)
        if _cluster_has_body_signal(cluster)
    ]
    if not qualifying:
        return None
    if len(qualifying) > 1:
        return None
    return qualifying[0]


def _union_bbox(blocks: list[PdfTextBlock]) -> BBox:
    return BBox(
        x0=min(block.bbox.x0 for block in blocks),
        y0=min(block.bbox.y0 for block in blocks),
        x1=max(block.bbox.x1 for block in blocks),
        y1=max(block.bbox.y1 for block in blocks),
    )


def _cluster_has_body_signal(cluster: list[PdfTextBlock]) -> bool:
    line_count = sum(
        1 for block in cluster for line in block.lines if line.text.strip()
    )
    if line_count < MIN_BODY_LINES:
        return False
    union = _union_bbox(cluster)
    if union.width < MIN_BODY_WIDTH_PT:
        return False
    alpha_chars = sum(1 for block in cluster for ch in block.text if ch.isalpha())
    return alpha_chars >= MIN_BODY_ALPHA_CHARS


def _block_in_margin_zone(page: PdfPage, block: PdfTextBlock) -> bool:
    return (
        block.bbox.y0 < TOP_MARGIN_PT - 4.0
        or block.bbox.y1 > page.height - BOTTOM_MARGIN_PT + 4.0
    )


def _extract_float_number(raw_text: str) -> str:
    match = FLOAT_NUMBER_RE.match(normalize_caption_text(raw_text))
    return match.group("number") if match else ""


def _find_caption_line_bbox(page: PdfPage, caption: CaptionLine) -> BBox | None:
    target_number = _extract_float_number(caption.raw_text)
    for line in _collect_page_lines(page):
        clean = normalize_caption_text(line.text)
        if clean == caption.raw_text:
            return line.bbox
        match = CAPTION_START_RE.match(clean)
        if match and _extract_float_number(clean) == target_number:
            return line.bbox
    return None


def _candidate_body_blocks(
    page: PdfPage, caption_bbox: BBox, *, allow_multiline: bool = False
) -> tuple[list[PdfTextBlock], list[PdfTextBlock]]:
    above: list[PdfTextBlock] = []
    below: list[PdfTextBlock] = []
    for block in page.text_blocks:
        if any(_is_caption_line_text(line.text) for line in block.lines):
            continue
        if _block_is_chapter_heading(block):
            continue
        if _block_in_margin_zone(page, block):
            continue
        if not block.text.strip():
            continue
        if not allow_multiline and len(block.lines) != 1:
            continue
        gap_above = caption_bbox.y0 - block.bbox.y1
        gap_below = block.bbox.y0 - caption_bbox.y1
        if -CAPTION_BODY_GAP_PT <= gap_above <= MAX_BODY_SEARCH_GAP_PT:
            above.append(block)
        if -CAPTION_BODY_GAP_PT <= gap_below <= MAX_BODY_SEARCH_GAP_PT:
            below.append(block)
    return above, below


def _centering_issue(page: PdfPage, body_bbox: BBox) -> tuple[bool, float]:
    center_delta = abs(_bbox_center_x(body_bbox) - _text_area_center(page))
    return center_delta > CENTER_TOLERANCE_PT, center_delta


def _append_finding(
    findings: list[AuditFinding],
    *,
    issue_type: str,
    float_type: str,
    page_number: int,
    float_number: str,
    center_delta: float | None = None,
) -> None:
    details: dict[str, str] = {
        "issue_type": issue_type,
        "float_type": float_type,
        "caption_page": str(page_number),
        "body_page": str(page_number),
        "float_number": float_number,
        "triage_tier": "review",
        "allowed_center_delta_points": str(int(CENTER_TOLERANCE_PT)),
    }
    if center_delta is not None:
        details["center_delta_points"] = f"{center_delta:.1f}"

    if issue_type == "table_body_not_centered":
        message = "Inferred table body block may not be centered within the text area."
    elif issue_type == "figure_body_not_centered":
        message = "Inferred figure body block may not be centered within the text area."
    elif issue_type == "table_caption_not_above_body":
        message = "Table caption may not appear above the inferred table body block."
    else:
        message = "Figure caption may not appear below the inferred figure body block."

    findings.append(
        AuditFinding(
            rule_id="P035",
            severity=Severity.WARNING,
            page=page_number,
            message=message,
            details=details,
        )
    )


def check_pdf_figure_table_layout(pdf_document: PdfDocument) -> list[AuditFinding]:
    """Emit conservative P035 warnings for figure/table body layout on body pages."""

    findings: list[AuditFinding] = []
    pages_by_number = {page.page_number: page for page in pdf_document.pages}

    for caption in detect_caption_lines(pdf_document):
        if caption.context != "body":
            continue

        page = pages_by_number.get(caption.page_number)
        if page is None:
            continue

        caption_bbox = _find_caption_line_bbox(page, caption)
        if caption_bbox is None:
            continue

        float_number = _extract_float_number(caption.raw_text)

        if caption.caption_type == "table":
            # Real table rows are commonly extracted as one multi-line text
            # block (tight, single-spaced row pitch), unlike loose caption-
            # adjacent text. Only the expected (below-caption) side allows
            # multi-line blocks so an ordinary paragraph above the caption
            # still can't masquerade as a misplaced table body.
            _, below = _candidate_body_blocks(page, caption_bbox, allow_multiline=True)
            above, _ = _candidate_body_blocks(page, caption_bbox)
            primary = _select_body_cluster(below)
            wrong_side = _select_body_cluster(above)
            if primary is None and wrong_side is None:
                continue
            if primary is None and wrong_side is not None:
                _append_finding(
                    findings,
                    issue_type="table_caption_not_above_body",
                    float_type="table",
                    page_number=caption.page_number,
                    float_number=float_number,
                )
                continue
            if primary is None:
                continue
            body_bbox = _union_bbox(primary)
            not_centered, center_delta = _centering_issue(page, body_bbox)
            if not_centered:
                _append_finding(
                    findings,
                    issue_type="table_body_not_centered",
                    float_type="table",
                    page_number=caption.page_number,
                    float_number=float_number,
                    center_delta=center_delta,
                )
            continue

        above, below = _candidate_body_blocks(page, caption_bbox)
        primary = _select_body_cluster(above)
        wrong_side = _select_body_cluster(below)
        if primary is None and wrong_side is None:
            continue
        if primary is None and wrong_side is not None:
            _append_finding(
                findings,
                issue_type="figure_caption_not_below_body",
                float_type="figure",
                page_number=caption.page_number,
                float_number=float_number,
            )
            continue
        if primary is None:
            continue
        body_bbox = _union_bbox(primary)
        not_centered, center_delta = _centering_issue(page, body_bbox)
        if not_centered:
            _append_finding(
                findings,
                issue_type="figure_body_not_centered",
                float_type="figure",
                page_number=caption.page_number,
                float_number=float_number,
                center_delta=center_delta,
            )

    return findings
