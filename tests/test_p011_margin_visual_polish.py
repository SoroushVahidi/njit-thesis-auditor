"""Regression tests for P011 margin-warning visual evidence and clarity polish.

Covers: precise (non-union) highlight boxes for separated affected lines,
margin-boundary guide-line geometry, preserved single-line precision, and
clearer mixed-side (top+right, etc.) evidence -- all without changing what
counts as a P011 violation, thresholds, rule IDs, issue types, confidence
labels, or sorting behavior.
"""

from __future__ import annotations

from pathlib import Path

import fitz

from njit_auditor.highlight_targeting import parse_highlight_bboxes_from_details
from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.polished_comments import build_polished_comment
from njit_auditor.report_outputs import audit_findings_to_json_dict
from njit_auditor.report_view import build_report_view
from njit_auditor.rules.pdf_margins import (
    LEFT_MARGIN_PT,
    OVERFLOW_TOLERANCE_PT,
    RIGHT_MARGIN_PT,
    TOP_MARGIN_PT,
    run_pdf_margin_rule,
)
from njit_auditor.web_app import _highlight_boxes_by_page

PAGE_WIDTH = 612.0
PAGE_HEIGHT = 792.0
ALLOWED_X1 = PAGE_WIDTH - RIGHT_MARGIN_PT  # 540.0
ALLOWED_X0 = LEFT_MARGIN_PT  # 108.0
ALLOWED_Y0 = TOP_MARGIN_PT  # 72.0


def _p011_warnings(pdf_path: Path) -> list:
    model = load_pdf_layout(str(pdf_path))
    return [f for f in run_pdf_margin_rule(model) if f.severity.value == "WARNING"]


def _text_at_x1(text: str, target_x1: float, y: float, fontsize: float = 11) -> tuple[float, str]:
    """Return (x0, text) so inserting *text* at fontsize ends at target_x1."""
    width = fitz.get_text_length(text, fontsize=fontsize)
    return target_x1 - width, text


def test_small_right_margin_overflow_still_flags(tmp_path: Path) -> None:
    """A right-margin overflow just past the tolerance must still be flagged --
    small overflows are never suppressed."""
    target_overflow = OVERFLOW_TOLERANCE_PT + 2.0  # comfortably over tolerance, still "small"
    text = "Slightly over the margin boundary line"
    x0, _ = _text_at_x1(text, ALLOWED_X1 + target_overflow, 120)
    doc = fitz.open()
    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    page.insert_text((x0, 120), text, fontsize=11)
    pdf_path = tmp_path / "small_right_overflow.pdf"
    doc.save(pdf_path)
    doc.close()

    warnings = _p011_warnings(pdf_path)
    right = [f for f in warnings if f.details.get("side") == "right_margin"]
    assert len(right) == 1, "small overflow must still produce a P011 warning, not be suppressed"
    overflow = float(right[0].details["worst_overflow_pt"])
    assert overflow > OVERFLOW_TOLERANCE_PT
    assert overflow < 10.0, "expected a genuinely small overflow for this test"


def test_single_line_large_right_margin_overflow_stays_precise(tmp_path: Path) -> None:
    """Approval-Page 'Date'-style case: one short line far over the right
    margin must remain a single, precise, tight highlight -- current good
    behavior must not regress.

    x=535 (not 520) so the measured overflow is comfortably in "high
    confidence" territory (~18pt) -- genuinely "far over", matching this
    test's own docstring, and distinct from the sub-5pt single-line noise
    now suppressed by the low-confidence filter (see
    docs/status/ester_sample_b_p011_margin_low_overflow.md).
    """
    doc = fitz.open()
    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    page.insert_text((535, 400), "Date", fontsize=11)
    pdf_path = tmp_path / "single_line_date.pdf"
    doc.save(pdf_path)
    doc.close()

    warnings = _p011_warnings(pdf_path)
    right = [f for f in warnings if f.details.get("side") == "right_margin"]
    assert len(right) == 1
    details = right[0].details
    assert details.get("affected_line_count") == "1"
    assert details.get("affected_line_texts") == "Date"

    boxes = parse_highlight_bboxes_from_details(
        details, rule_id="P011", issue_type="margin_boundary_violation"
    )
    # One tight text box, its overflow-only segment, plus one boundary guide.
    assert len(boxes) == 3
    text_box = boxes[0]
    assert text_box[3] - text_box[1] < 20.0, "single-line box must stay one line tall"
    assert text_box.kind == "line"
    overflow_box = boxes[1]
    assert overflow_box.kind == "overflow"
    assert overflow_box[0] >= ALLOWED_X1, "overflow segment must start at/after the boundary"
    assert overflow_box[2] == text_box[2], "overflow segment must share the line's right edge"
    guide_box = boxes[2]
    assert guide_box.kind == "guide"
    assert guide_box[2] - guide_box[0] < 5.0, "boundary guide must be a thin line"
    assert guide_box[0] < ALLOWED_X1 < guide_box[2], "right guide must straddle the boundary"


def test_non_adjacent_right_margin_lines_not_one_giant_highlight(tmp_path: Path) -> None:
    """Two separated right-margin violations with clean lines between them
    must not be highlighted as one region spanning the clean lines."""
    doc = fitz.open()
    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    y = 100.0
    over_text = "This line runs well past the required right margin boundary xxxxxx"
    x0, _ = _text_at_x1(over_text, ALLOWED_X1 + 40, y)
    page.insert_text((x0, y), over_text, fontsize=11)
    y += 20
    page.insert_text((150, y), "A normal clean line well inside the margins.", fontsize=11)
    y += 20
    page.insert_text((150, y), "Another normal clean line inside the margins.", fontsize=11)
    y += 20
    x0, _ = _text_at_x1(over_text, ALLOWED_X1 + 40, y)
    page.insert_text((x0, y), over_text, fontsize=11)
    pdf_path = tmp_path / "nonadjacent_right.pdf"
    doc.save(pdf_path)
    doc.close()

    warnings = _p011_warnings(pdf_path)
    right = [f for f in warnings if f.details.get("side") == "right_margin"]
    assert len(right) == 1
    details = right[0].details
    assert details.get("affected_line_count") == "2"

    boxes = parse_highlight_bboxes_from_details(
        details, rule_id="P011", issue_type="margin_boundary_violation"
    )
    # Two separate tight line boxes, two matching overflow segments, plus one
    # boundary guide -- never a single union spanning both clean lines in between.
    assert len(boxes) == 5
    line_boxes = boxes[:2]
    for box in line_boxes:
        assert box[3] - box[1] < 20.0, "each affected-line box must stay one line tall"
        assert box.kind == "line"
    # The two line boxes must not overlap the clean lines' vertical band.
    first_y1 = line_boxes[0][3]
    second_y0 = line_boxes[1][1]
    assert second_y0 - first_y1 > 15.0, "boxes must be separated, not merged across the gap"
    overflow_boxes = boxes[2:4]
    for box in overflow_boxes:
        assert box.kind == "overflow"


def test_adjacent_right_margin_lines_merge_without_extra_content(tmp_path: Path) -> None:
    """Two consecutive (adjacent) right-margin violations may be grouped into
    one tight box, but must not include any unaffected content."""
    doc = fitz.open()
    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    over_text = "This line runs well past the required right margin boundary xxxxxx"
    y = 100.0
    x0, _ = _text_at_x1(over_text, ALLOWED_X1 + 40, y)
    page.insert_text((x0, y), over_text, fontsize=11)
    y += 20
    x0, _ = _text_at_x1(over_text, ALLOWED_X1 + 40, y)
    page.insert_text((x0, y), over_text, fontsize=11)
    pdf_path = tmp_path / "adjacent_right.pdf"
    doc.save(pdf_path)
    doc.close()

    warnings = _p011_warnings(pdf_path)
    right = [f for f in warnings if f.details.get("side") == "right_margin"]
    assert len(right) == 1
    details = right[0].details
    assert details.get("affected_line_count") == "2"

    boxes = parse_highlight_bboxes_from_details(
        details, rule_id="P011", issue_type="margin_boundary_violation"
    )
    # One merged tight box (both lines, no gap), its overflow segment, plus
    # the boundary guide.
    assert len(boxes) == 3
    merged_box = boxes[0]
    assert merged_box[3] - merged_box[1] < 40.0, "merged box must span only these two lines"
    guide_box = boxes[2]
    assert guide_box[2] - guide_box[0] < 5.0


def test_left_margin_reference_entries_not_one_giant_highlight(tmp_path: Path) -> None:
    """Two separated hanging-reference first lines crossing the left margin
    must be highlighted separately, not as one block covering the references
    between them, and the guide must be left-margin-specific."""
    doc = fitz.open()
    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    y = 100.0
    page.insert_text((80, y), "Overflowing reference entry number one, over margin", fontsize=11)
    y += 20
    page.insert_text((150, y), "    continuation of reference one, inside margins", fontsize=11)
    y += 20
    page.insert_text((150, y), "A normal reference entry inside the margins.", fontsize=11)
    y += 20
    page.insert_text((80, y), "Overflowing reference entry number two, over margin", fontsize=11)
    pdf_path = tmp_path / "left_margin_refs.pdf"
    doc.save(pdf_path)
    doc.close()

    warnings = _p011_warnings(pdf_path)
    left = [f for f in warnings if f.details.get("side") == "left_margin"]
    assert len(left) == 1
    details = left[0].details
    assert details.get("affected_line_count") == "2"

    boxes = parse_highlight_bboxes_from_details(
        details, rule_id="P011", issue_type="margin_boundary_violation"
    )
    assert len(boxes) == 5
    line_boxes = boxes[:2]
    first_y1 = line_boxes[0][3]
    second_y0 = line_boxes[1][1]
    assert second_y0 - first_y1 > 15.0, "separated reference lines must not be merged"
    guide_box = boxes[4]
    assert guide_box[2] - guide_box[0] < 5.0
    assert guide_box[0] < ALLOWED_X0 < guide_box[2], "left guide must straddle the left boundary"


def test_top_margin_boundary_guide_is_horizontal(tmp_path: Path) -> None:
    """A top-margin warning must still appear, with a horizontal boundary
    guide and a tight highlight for the affected content."""
    doc = fitz.open()
    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    page.insert_text(
        (150, 40), "This text sits above the required top margin boundary", fontsize=11
    )
    pdf_path = tmp_path / "top_margin.pdf"
    doc.save(pdf_path)
    doc.close()

    warnings = _p011_warnings(pdf_path)
    top = [f for f in warnings if f.details.get("side") == "top_margin"]
    assert len(top) == 1
    details = top[0].details
    assert details.get("affected_line_count") == "1"

    boxes = parse_highlight_bboxes_from_details(
        details, rule_id="P011", issue_type="margin_boundary_violation"
    )
    assert len(boxes) == 3
    text_box, overflow_box, guide_box = boxes
    assert overflow_box[3] <= ALLOWED_Y0, "top overflow segment must sit above the boundary"
    assert guide_box[3] - guide_box[1] < 5.0, "top guide must be a thin horizontal line"
    assert guide_box[2] - guide_box[0] > 20.0, "top guide must span the affected width"
    assert guide_box[1] < ALLOWED_Y0 < guide_box[3], "top guide must straddle the top boundary"


def test_mixed_top_and_right_margin_page_gives_separated_evidence(tmp_path: Path) -> None:
    """A page with both a top-margin and a right-margin violation must
    (a) still flag both underlying violations, (b) roll up to one problem
    card without losing either side's evidence in vague wording, and
    (c) draw separate highlight/guide boxes for each side, never one
    highlight spanning the whole page."""
    doc = fitz.open()
    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    over_text = "This line runs well past the required right margin boundary xxxxxx"
    x0, _ = _text_at_x1(over_text, ALLOWED_X1 + 40, 100)
    page.insert_text((x0, 100), over_text, fontsize=11)
    page.insert_text(
        (150, 40), "This text sits above the required top margin boundary", fontsize=11
    )
    pdf_path = tmp_path / "mixed_top_right.pdf"
    doc.save(pdf_path)
    doc.close()

    raw_findings = _p011_warnings(pdf_path)
    assert {f.details.get("side") for f in raw_findings} == {"right_margin", "top_margin"}

    payload = audit_findings_to_json_dict(raw_findings, {"audit_type": "pdf"})
    view = build_report_view(payload, pdf_page_sizes=[(PAGE_WIDTH, PAGE_HEIGHT)])
    cards = [f for f in view.findings if f.rule_id == "P011"]
    assert len(cards) == 1, "mixed-side page still rolls up to one problem card"
    card = cards[0]
    assert card.has_highlight is True
    assert card.action_label == "Open highlighted PDF page"
    # The comment must break out per-side evidence, not just a vague count.
    comment = card.polished_comment
    assert "right margin (~" in comment
    assert "top margin (~" in comment
    assert "pt over" in comment
    lowered = comment.lower()
    assert "strict" not in lowered
    assert "even by a small amount" not in lowered
    assert "appears to cross the required" not in lowered

    # The actual highlighted-PDF drawing path must show separate boxes for
    # each side -- never one region spanning the whole page between them.
    boxes_by_page = _highlight_boxes_by_page(payload["findings"])
    boxes = boxes_by_page[1]
    assert len(boxes) == 6, "expected 3 boxes (line + overflow + guide) per side, 6 total"
    # No single box should span from the top-margin region to the right-margin
    # region: every box's own height must stay small relative to the full gap.
    for box in boxes:
        assert box[3] - box[1] < 40.0, "no box should span both affected regions"


def test_single_side_comment_stays_neutral_without_downgrading() -> None:
    """A single-side P011 comment must stay neutral and must never suggest
    the warning is optional or ignorable."""
    comment = build_polished_comment(
        rule_id="P011",
        issue_type="margin_boundary_violation",
        page=4,
        details={"side": "right_margin", "worst_overflow_pt": "3.0", "affected_line_count": "2"},
    )
    lowered = comment.lower()
    assert "strict" not in lowered
    assert "even by a small amount" not in lowered
    assert "appears to cross the required right margin boundary" in lowered
    for phrase in ("optional", "can be ignored", "may be ignored", "not required"):
        assert phrase not in lowered
