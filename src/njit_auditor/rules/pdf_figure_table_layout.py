"""Conservative PDF figure/table body layout checks (centering and caption placement).

Centering and caption placement are visual questions, so they are measured in
the page's reading frame (:class:`~njit_auditor.pdf_models.PdfReadingFrame`,
see ``docs/architecture/pdf_rotation_frames_adr.md``). Every size, the
portrait/landscape tolerance, and every box come from that frame:

* on a page whose text reads upright only after ``/Rotate`` (a pdflscape
  landscape page: portrait MediaBox, ``/Rotate 90`` or ``270``) boxes are first
  mapped to the displayed page, which makes it measure exactly like the same
  layout encoded as an intrinsic landscape page;
* on an unrotated page, or one whose ``/Rotate`` only turns already upright
  text in the viewer, the reading frame is the unrotated box space, so a
  viewer-only ``/Rotate`` gives the same verdict as ``/Rotate 0``.

The displayed page size (``PdfPage.width``/``height``/``is_visually_landscape``)
is never used. Reported boxes are mapped back to the unrotated space the rest
of the pipeline uses.

Scope: synthetic pixel-equivalent differential tests verify intrinsic
landscape = pdflscape, and viewer-only ``/Rotate`` = ``/Rotate 0``. This does
not certify arbitrary object rotation or ambiguous reading frames, and no
real thesis page available to the project uses ``/Rotate`` today.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import (
    BBox,
    PdfDocument,
    PdfGraphicBlock,
    PdfPage,
    PdfReadingFrame,
    PdfTextBlock,
    PdfTextLine,
    format_bbox_detail,
)
from njit_auditor.rules.pdf_captions import (
    CAPTION_START_RE,
    CaptionLine,
    detect_caption_lines,
    normalize_caption_candidate_text,
    normalize_caption_text,
)
from njit_auditor.rules.pdf_margins import (
    BOTTOM_MARGIN_PT,
    LEFT_MARGIN_PT,
    RIGHT_MARGIN_PT,
    TOP_MARGIN_PT,
)
from njit_auditor.rules.pdf_page_numbers import PAGE_NUM_RE

CENTER_TOLERANCE_PT = 18.0  # Portrait tolerance - strict for genuine centering

# Landscape pages: use text area center but allow larger deviation due to rotation
# Ester confirmed landscape page-number positioning follows normal convention
# So centering inference should use effective content area center

LANDSCAPE_CENTER_TOLERANCE_PT = 50.0  # Larger tolerance for landscape pages
CAPTION_BODY_GAP_PT = 8.0
MAX_BODY_SEARCH_GAP_PT = 120.0
MIN_BODY_LINES = 2
MIN_BODY_WIDTH_PT = 72.0
MIN_BODY_ALPHA_CHARS = 12
MIN_GRAPHIC_BODY_HEIGHT_PT = 24.0
MAX_GRAPHIC_PAGE_FRACTION = 0.90

FLOAT_NUMBER_RE = re.compile(
    r"^\s*(?:figure|fig\.|table)\s+(?P<number>[0-9ivxlcdm]+(?:[.\-][0-9ivxlcdm]+)*)",
    re.IGNORECASE,
)


CHAPTER_HEADING_RE = re.compile(r"^CHAPTER\s+", re.IGNORECASE)
MAX_CLUSTER_LINE_GAP_PT = 24.0
TABLE_RULE_EDGE_TOLERANCE_PT = 3.0
TABLE_RULE_TOP_GAP_PT = 30.0
TABLE_RULE_MIN_OVERLAP_FRACTION = 0.70


BBoxMapper = Callable[[BBox], BBox]


def _keep_bbox(bbox: BBox) -> BBox:
    return bbox


def _reading_frame_page(page: PdfPage) -> tuple[PdfPage, PdfReadingFrame]:
    """Return *page*'s content in its reading frame, plus that frame.

    Only the returned page's boxes are used; every size and the policy
    orientation come from the frame. The returned page is a copy when boxes
    move; *page* itself is never modified.
    """
    frame = PdfReadingFrame.for_page(page)
    if frame.reading_rotation == 0:
        return page, frame
    to_frame = frame.to_reading

    framed = page.model_copy(
        update={
            "text_blocks": [
                block.model_copy(
                    update={
                        "bbox": to_frame(block.bbox),
                        "lines": [
                            line.model_copy(
                                update={
                                    "bbox": to_frame(line.bbox),
                                    "spans": [
                                        span.model_copy(update={"bbox": to_frame(span.bbox)})
                                        for span in line.spans
                                    ],
                                }
                            )
                            for line in block.lines
                        ],
                    }
                )
                for block in page.text_blocks
            ],
            "graphic_blocks": [
                graphic.model_copy(update={"bbox": to_frame(graphic.bbox)})
                for graphic in page.graphic_blocks
            ],
            "horizontal_rules": [to_frame(rule) for rule in page.horizontal_rules],
        }
    )
    return framed, frame


def _collect_page_lines(page: PdfPage) -> list[PdfTextLine]:
    lines: list[PdfTextLine] = []
    for block in page.text_blocks:
        lines.extend(block.lines)
    return lines


def _text_area_bounds(frame: PdfReadingFrame) -> tuple[float, float]:
    return LEFT_MARGIN_PT, frame.reading_width - RIGHT_MARGIN_PT


def _text_area_center(frame: PdfReadingFrame) -> float:
    x0, x1 = _text_area_bounds(frame)
    return (x0 + x1) / 2.0


def _bbox_center_x(bbox: BBox) -> float:
    return (bbox.x0 + bbox.x1) / 2.0


def _is_caption_line_text(text: str) -> bool:
    clean = normalize_caption_candidate_text(text)
    if not clean or PAGE_NUM_RE.match(clean):
        return False
    match = CAPTION_START_RE.match(clean)
    if not match:
        return False
    body = normalize_caption_text(match.group("body"))
    return len(body) >= 14


def _block_is_chapter_heading(block: PdfTextBlock) -> bool:
    return bool(CHAPTER_HEADING_RE.match(block.text.strip()))


BodyRegion = PdfTextBlock | PdfGraphicBlock


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


def _has_any_text_body_signal(blocks: list[PdfTextBlock]) -> bool:
    return any(_cluster_has_body_signal(cluster) for cluster in _cluster_body_blocks(blocks))


def _union_bbox(blocks: Sequence[BodyRegion]) -> BBox:
    return BBox(
        x0=min(block.bbox.x0 for block in blocks),
        y0=min(block.bbox.y0 for block in blocks),
        x1=max(block.bbox.x1 for block in blocks),
        y1=max(block.bbox.y1 for block in blocks),
    )


def _graphic_has_body_signal(frame: PdfReadingFrame, graphic: PdfGraphicBlock) -> bool:
    bbox = graphic.bbox
    width, height = frame.reading_size
    if bbox.width < MIN_BODY_WIDTH_PT or bbox.height < MIN_GRAPHIC_BODY_HEIGHT_PT:
        return False
    if bbox.width > width * MAX_GRAPHIC_PAGE_FRACTION:
        return False
    if bbox.height > height * MAX_GRAPHIC_PAGE_FRACTION:
        return False
    if bbox.y0 < TOP_MARGIN_PT - 12.0:
        return False
    if bbox.y1 > height - BOTTOM_MARGIN_PT + 12.0:
        return False
    return True


def _cluster_graphic_blocks(
    graphics: list[PdfGraphicBlock],
) -> list[list[PdfGraphicBlock]]:
    if not graphics:
        return []
    ordered = sorted(graphics, key=lambda graphic: graphic.bbox.y0)
    clusters: list[list[PdfGraphicBlock]] = [[ordered[0]]]
    for graphic in ordered[1:]:
        previous = clusters[-1][-1]
        gap = graphic.bbox.y0 - previous.bbox.y1
        if gap <= MAX_CLUSTER_LINE_GAP_PT:
            clusters[-1].append(graphic)
        else:
            clusters.append([graphic])
    return clusters


def _select_graphic_cluster(
    frame: PdfReadingFrame, graphics: list[PdfGraphicBlock]
) -> list[PdfGraphicBlock] | None:
    qualifying = [
        cluster
        for cluster in _cluster_graphic_blocks(graphics)
        if any(_graphic_has_body_signal(frame, graphic) for graphic in cluster)
    ]
    if not qualifying:
        return None
    if len(qualifying) > 1:
        return None
    return qualifying[0]


def _has_any_graphic_body_signal(
    frame: PdfReadingFrame, graphics: list[PdfGraphicBlock]
) -> bool:
    return any(
        any(_graphic_has_body_signal(frame, graphic) for graphic in cluster)
        for cluster in _cluster_graphic_blocks(graphics)
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


def _block_in_margin_zone(frame: PdfReadingFrame, block: PdfTextBlock) -> bool:
    return (
        block.bbox.y0 < TOP_MARGIN_PT - 4.0
        or block.bbox.y1 > frame.reading_height - BOTTOM_MARGIN_PT + 4.0
    )


def _extract_float_number(raw_text: str) -> str:
    match = FLOAT_NUMBER_RE.match(normalize_caption_text(raw_text))
    return match.group("number") if match else ""


def _find_caption_line_bbox(page: PdfPage, caption: CaptionLine) -> BBox | None:
    target_number = _extract_float_number(caption.raw_text)
    for line in _collect_page_lines(page):
        raw_clean = normalize_caption_text(line.text)
        if raw_clean == caption.raw_text:
            return line.bbox
        clean = normalize_caption_candidate_text(raw_clean)
        match = CAPTION_START_RE.match(clean)
        if match and _extract_float_number(clean) == target_number:
            return line.bbox
    return None


def _candidate_body_blocks(
    page: PdfPage,
    frame: PdfReadingFrame,
    caption_bbox: BBox,
    *,
    allow_multiline: bool = False,
) -> tuple[list[PdfTextBlock], list[PdfTextBlock]]:
    above: list[PdfTextBlock] = []
    below: list[PdfTextBlock] = []
    for block in page.text_blocks:
        if any(_is_caption_line_text(line.text) for line in block.lines):
            continue
        if _block_is_chapter_heading(block):
            continue
        if _block_in_margin_zone(frame, block):
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


def _candidate_graphic_blocks(
    page: PdfPage, frame: PdfReadingFrame, caption_bbox: BBox
) -> tuple[list[PdfGraphicBlock], list[PdfGraphicBlock]]:
    above: list[PdfGraphicBlock] = []
    below: list[PdfGraphicBlock] = []
    for graphic in page.graphic_blocks:
        if not _graphic_has_body_signal(frame, graphic):
            continue
        gap_above = caption_bbox.y0 - graphic.bbox.y1
        gap_below = graphic.bbox.y0 - caption_bbox.y1
        if -CAPTION_BODY_GAP_PT <= gap_above <= MAX_BODY_SEARCH_GAP_PT:
            above.append(graphic)
        if -CAPTION_BODY_GAP_PT <= gap_below <= MAX_BODY_SEARCH_GAP_PT:
            below.append(graphic)
    return above, below


def _centering_issue(frame: PdfReadingFrame, body_bbox: BBox) -> tuple[bool, float, float]:
    center_delta = abs(_bbox_center_x(body_bbox) - _text_area_center(frame))
    tolerance = LANDSCAPE_CENTER_TOLERANCE_PT if frame.is_landscape else CENTER_TOLERANCE_PT
    return center_delta > tolerance, center_delta, tolerance


def _complete_ruled_table_body_bbox(
    page: PdfPage, text_bbox: BBox, caption_bbox: BBox, next_caption_y: float
) -> BBox:
    """Use a table's repeated outer rules when they bound its text body.

    A text cluster can omit the final row or the table borders. At least two
    matching, full-width horizontal rules must surround that cluster before
    their geometry can replace the text-only proxy. Unruled or ambiguous
    tables keep the existing text-bbox behavior.
    """
    candidates = []
    for rule in page.horizontal_rules:
        if not (caption_bbox.y1 + 1.0 <= rule.y0 < next_caption_y):
            continue
        overlap = min(rule.x1, text_bbox.x1) - max(rule.x0, text_bbox.x0)
        if overlap < TABLE_RULE_MIN_OVERLAP_FRACTION * max(rule.width, text_bbox.width):
            continue
        candidates.append(rule)

    groups: list[list[BBox]] = []
    for rule in sorted(candidates, key=lambda item: (item.x0, item.x1, item.y0)):
        matching = next(
            (
                group for group in groups
                if abs(group[0].x0 - rule.x0) <= TABLE_RULE_EDGE_TOLERANCE_PT
                and abs(group[0].x1 - rule.x1) <= TABLE_RULE_EDGE_TOLERANCE_PT
            ),
            None,
        )
        if matching is None:
            groups.append([rule])
        else:
            matching.append(rule)

    qualifying = []
    for group in groups:
        if len(group) < 2:
            continue
        first = min(group, key=lambda rule: rule.y0)
        last = max(group, key=lambda rule: rule.y1)
        if not (0 <= text_bbox.y0 - first.y1 <= TABLE_RULE_TOP_GAP_PT):
            continue
        if last.y1 < text_bbox.y1 - 8.0:
            continue
        qualifying.append((abs(text_bbox.y0 - first.y1), -len(group), group))

    if not qualifying:
        return text_bbox
    _, _, chosen = min(qualifying, key=lambda item: (item[0], item[1]))
    return BBox(
        x0=min(text_bbox.x0, *(rule.x0 for rule in chosen)),
        y0=min(text_bbox.y0, *(rule.y0 for rule in chosen)),
        x1=max(text_bbox.x1, *(rule.x1 for rule in chosen)),
        y1=max(text_bbox.y1, *(rule.y1 for rule in chosen)),
    )


def _cluster_looks_like_body_paragraph(
    cluster: list[PdfTextBlock],
) -> bool:
    """Return True when a below-caption cluster looks like ordinary body prose."""
    lines = [
        line.text.strip()
        for block in cluster
        for line in block.lines
        if line.text.strip()
    ]
    if not lines:
        return False
    first_line = lines[0]
    if re.match(
        r"^(The|This|In|When|As|Results|Additional|However|These|While|Because)\b",
        first_line,
        flags=re.IGNORECASE,
    ):
        return True
    avg_len = sum(len(line) for line in lines) / len(lines)
    union = _union_bbox(cluster)
    if union.x0 <= LEFT_MARGIN_PT + 18.0 and len(lines) >= 2 and avg_len >= 40.0:
        return True
    return False


def _append_finding(
    findings: list[AuditFinding],
    *,
    issue_type: str,
    float_type: str,
    page_number: int,
    float_number: str,
    center_delta: float | None = None,
    allowed_center_delta: float | None = None,
    bbox: BBox | None = None,
    body_bbox: BBox | None = None,
    caption_bbox: BBox | None = None,
    to_source: BBoxMapper = _keep_bbox,
) -> None:
    allowed_delta = (
        allowed_center_delta
        if allowed_center_delta is not None
        else CENTER_TOLERANCE_PT
    )
    details: dict[str, str] = {
        "issue_type": issue_type,
        "float_type": float_type,
        "caption_page": str(page_number),
        "body_page": str(page_number),
        "float_number": float_number,
        "triage_tier": "review",
        "allowed_center_delta_points": str(int(allowed_delta)),
    }
    if center_delta is not None:
        details["center_delta_points"] = f"{center_delta:.1f}"
    if bbox is not None:
        details["bbox"] = format_bbox_detail(to_source(bbox))
    if body_bbox is not None:
        details["body_bbox"] = format_bbox_detail(to_source(body_bbox))
    if caption_bbox is not None:
        details["caption_bbox"] = format_bbox_detail(to_source(caption_bbox))

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
    frames = {page.page_number: _reading_frame_page(page) for page in pdf_document.pages}

    captions = detect_caption_lines(pdf_document)
    for caption in captions:
        if caption.context != "body":
            continue

        frame = frames.get(caption.page_number)
        if frame is None:
            continue
        page, reading_frame = frame
        to_source = reading_frame.from_reading

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
            _, below = _candidate_body_blocks(
                page, reading_frame, caption_bbox, allow_multiline=True
            )
            above, _ = _candidate_body_blocks(page, reading_frame, caption_bbox)
            primary = _select_body_cluster(below)
            wrong_side = _select_body_cluster(above)
            if primary is None and wrong_side is None:
                continue
            if primary is None and wrong_side is not None:
                if _has_any_text_body_signal(below):
                    continue
                _append_finding(
                    findings,
                    to_source=to_source,
                    issue_type="table_caption_not_above_body",
                    float_type="table",
                    page_number=caption.page_number,
                    float_number=float_number,
                    bbox=caption_bbox,
                    body_bbox=_union_bbox(wrong_side),
                    caption_bbox=caption_bbox,
                )
                continue
            if primary is None:
                continue
            text_bbox = _union_bbox(primary)
            later_captions = [
                other_bbox.y0
                for other in captions
                if other is not caption and other.page_number == caption.page_number
                if (other_bbox := _find_caption_line_bbox(page, other)) is not None
                and other_bbox.y0 > caption_bbox.y1
            ]
            body_bbox = _complete_ruled_table_body_bbox(
                page, text_bbox, caption_bbox,
                min(later_captions, default=reading_frame.reading_height),
            )
            not_centered, center_delta, tolerance = _centering_issue(reading_frame, body_bbox)
            if not_centered:
                _append_finding(
                    findings,
                    to_source=to_source,
                    issue_type="table_body_not_centered",
                    float_type="table",
                    page_number=caption.page_number,
                    float_number=float_number,
                    center_delta=center_delta,
                    allowed_center_delta=tolerance,
                    bbox=body_bbox,
                )
            continue

        above, below = _candidate_body_blocks(page, reading_frame, caption_bbox)
        graphic_above, graphic_below = _candidate_graphic_blocks(
            page, reading_frame, caption_bbox
        )
        primary_graphic = _select_graphic_cluster(reading_frame, graphic_above)
        primary = _select_body_cluster(above)
        wrong_side_graphic = _select_graphic_cluster(reading_frame, graphic_below)
        wrong_side = _select_body_cluster(below)
        if primary_graphic is not None:
            body_bbox = _union_bbox(primary_graphic)
            not_centered, center_delta, tolerance = _centering_issue(reading_frame, body_bbox)
            if not_centered:
                _append_finding(
                    findings,
                    to_source=to_source,
                    issue_type="figure_body_not_centered",
                    float_type="figure",
                    page_number=caption.page_number,
                    float_number=float_number,
                    center_delta=center_delta,
                    allowed_center_delta=tolerance,
                    bbox=body_bbox,
                    body_bbox=body_bbox,
                    caption_bbox=caption_bbox,
                )
            continue
        if primary is None and wrong_side is None:
            if wrong_side_graphic is None:
                continue
        if primary is None and wrong_side_graphic is not None:
            if _has_any_text_body_signal(above) or _has_any_graphic_body_signal(
                reading_frame, graphic_above
            ):
                continue
            _append_finding(
                findings,
                to_source=to_source,
                issue_type="figure_caption_not_below_body",
                float_type="figure",
                page_number=caption.page_number,
                float_number=float_number,
                bbox=caption_bbox,
                body_bbox=_union_bbox(wrong_side_graphic),
                caption_bbox=caption_bbox,
            )
            continue
        if primary is None and wrong_side is None:
            continue
        if primary is None and wrong_side is not None:
            if _has_any_text_body_signal(above) or _has_any_graphic_body_signal(
                reading_frame, graphic_above
            ):
                continue
            if _cluster_looks_like_body_paragraph(wrong_side):
                continue
            _append_finding(
                findings,
                to_source=to_source,
                issue_type="figure_caption_not_below_body",
                float_type="figure",
                page_number=caption.page_number,
                float_number=float_number,
                bbox=caption_bbox,
                body_bbox=_union_bbox(wrong_side),
                caption_bbox=caption_bbox,
            )
            continue
        if primary is None:
            continue
        # ``primary`` here is a text-block fallback, not a confirmed graphic
        # body (that case already returned above via ``primary_graphic``).
        # Text fragments above a figure caption -- axis labels, callouts,
        # legend text extracted as their own blocks -- do not reliably
        # represent the figure's true visual extent, so their union bbox is
        # not a valid centering measurement. Centering is only meaningful
        # against the actual image geometry; skip it on this fallback path.

    return findings
