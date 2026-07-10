"""Baseline tests for current highlight-targeting behavior.

These tests document TODAY's behavior of `highlight_targeting.py` and the
detectors that feed it -- they intentionally do not assert desired future
behavior. A future highlight-quality PR (see
docs/status/highlight_quality_improvement_plan.md) may deliberately change
some of these expectations; when it does, update the affected test here and
explain why in the same PR, rather than silently letting it drift.

No private PDFs, screenshots, or generated highlighted PDFs are used or
committed here -- every fixture is a small synthetic PDF built inline.
"""

from __future__ import annotations

from pathlib import Path

import fitz

from njit_auditor.highlight_targeting import (
    parse_highlight_bboxes_from_details,
    resolve_primary_highlight_bbox,
    word_bbox_in_line,
)
from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.pdf_models import BBox, PdfTextLine, PdfTextSpan
from njit_auditor.rules.pdf_figure_table_layout import check_pdf_figure_table_layout
from njit_auditor.rules.pdf_margins import run_pdf_margin_rule

# ---------------------------------------------------------------------------
# 1. Explicit single bbox: returned as-is, never inflated.
# ---------------------------------------------------------------------------


def test_single_explicit_bbox_is_returned_without_inflation() -> None:
    """Baseline: with exactly one bbox in details, resolve_primary_highlight_bbox
    returns it unchanged. The highlight layer never expands a single box into a
    larger region on its own -- region size is entirely determined by what a
    detector puts in `details`."""
    resolved = resolve_primary_highlight_bbox(
        {"bbox": "100.0,200.0,300.0,212.0"},
        rule_id="P011",
        issue_type="margin_boundary_violation",
    )
    assert resolved == (100.0, 200.0, 300.0, 212.0)


# ---------------------------------------------------------------------------
# 2. Multiple bboxes: unioned into their bounding rectangle.
# ---------------------------------------------------------------------------


def test_multiple_recognized_bboxes_are_unioned() -> None:
    """Baseline: when more than one *recognized* bbox-like key is present
    (here `bbox` and `caption_bbox` -- both already recognized generically by
    `_EXTRA_BBOX_KEYS`, independent of rule_id), resolve_primary_highlight_bbox
    unions them into their bounding rectangle rather than picking just one.
    This union mechanism is rule-agnostic; only which *keys* a detector
    populates is rule-specific."""
    resolved = resolve_primary_highlight_bbox(
        {
            "bbox": "100.0,200.0,300.0,212.0",
            "caption_bbox": "100.0,150.0,250.0,162.0",
        },
        rule_id="P999",  # deliberately not a rule with special-cased handling
        issue_type="some_other_issue",
    )
    assert resolved == (100.0, 150.0, 300.0, 212.0)


# ---------------------------------------------------------------------------
# 3. P035 full-region precedent: body_bbox is a genuine multi-line union.
# ---------------------------------------------------------------------------


def test_p035_body_bbox_unions_every_body_line_not_just_one(tmp_path: Path) -> None:
    """Precedent for future full-region highlights (see
    docs/status/highlight_quality_improvement_plan.md): P035's `body_bbox` is a
    real union spanning every text block in the figure/table body cluster, not
    just the first or the worst one. A future PR extending this pattern to
    P011/P046/P048 should produce the same *kind* of union -- this test pins
    that the precedent itself keeps working."""
    pdf_path = tmp_path / "p035_body_union.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((108, 80), "CHAPTER 2 RESULTS", fontsize=14, fontname="Times-Bold")
    # Three tightly-spaced body lines (matching the spacing already proven to
    # cluster correctly in test_p035_placement_finding_includes_body_and_caption_highlight_boxes),
    # all part of the same figure body.
    page.insert_text(
        (180, 180),
        "Row alpha value and row beta value for synthetic figure body",
        fontsize=11,
    )
    page.insert_text(
        (180, 198),
        "Row gamma value and row delta value for synthetic figure body",
        fontsize=11,
    )
    page.insert_text(
        (180, 216),
        "Row epsilon value and row zeta value for synthetic figure body",
        fontsize=11,
    )
    page.insert_text(
        (108, 140),
        "Figure 1.1 Biomechanical representation of trunk support.",
        fontsize=11,
    )
    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))
    warnings = [
        f
        for f in check_pdf_figure_table_layout(model)
        if f.details.get("issue_type") == "figure_caption_not_below_body"
    ]
    assert warnings
    body_bbox_raw = warnings[0].details.get("body_bbox", "")
    assert body_bbox_raw, "expected a body_bbox to be present on this P035 finding"
    x0, y0, x1, y1 = (float(v) for v in body_bbox_raw.split(","))
    # A single 11pt text line is roughly 12-14pt tall. The three body lines here
    # span 36pt of insertion points (180 to 216) plus a line's own height, so a
    # genuine union is well beyond one line's height -- proving this is a real
    # multi-line union, not just the first body line's own box.
    assert (y1 - y0) > 30.0


# ---------------------------------------------------------------------------
# 4. Missing table/row/column metadata: not invented from unrelated keys.
# ---------------------------------------------------------------------------


def test_unrecognized_region_keys_are_not_used_for_highlighting() -> None:
    """Baseline limitation: highlight_targeting has no concept of `table_bbox`,
    `row_bbox`, or `column_bbox` today (see docs/status/highlight_quality_improvement_plan.md,
    Metadata gaps). If a finding's details happened to carry these keys, they
    would be silently ignored -- only the keys highlight_targeting actually
    recognizes (`bbox`/`rect`/`body_bbox`/`caption_bbox`/`token_bbox`/`word_bbox`)
    affect the resolved highlight. This documents that no accidental or future
    unrelated field could be mistaken for a full-region box without an explicit
    code change to recognize it."""
    resolved = resolve_primary_highlight_bbox(
        {
            "bbox": "100.0,200.0,150.0,212.0",
            "table_bbox": "50.0,50.0,500.0,700.0",
            "row_bbox": "50.0,200.0,500.0,212.0",
            "column_bbox": "400.0,50.0,500.0,700.0",
        },
        rule_id="P011",
        issue_type="margin_boundary_violation",
    )
    assert resolved == (100.0, 200.0, 150.0, 212.0)


# ---------------------------------------------------------------------------
# 5. Word-level shrink behavior: pinned for a second _TOKEN_HIGHLIGHT_RULES
#    member beyond the P020 case already covered in
#    test_web_audit_warning_fixes_batch2.py, to broaden the baseline.
# ---------------------------------------------------------------------------


def test_p027_level3_sentence_case_shrinks_to_flagged_word() -> None:
    """Baseline: word-level rules (here P027's Level 3 sentence-case check, one
    of several entries in `_TOKEN_HIGHLIGHT_RULES`) narrow a full-line bbox down
    to just the flagged word. `word_bbox_in_line` computes the exact span-based
    box (this is what a detector uses to populate `token_bbox` in `details`
    before a finding ever reaches `resolve_primary_highlight_bbox`), and once
    that `token_bbox` is present, resolve_primary_highlight_bbox prefers it over
    the full line bbox -- the same mechanism already pinned for P020 in
    test_web_audit_warning_fixes_batch2.py. Word-level precision must be
    preserved by any future table/list/figure region-size improvement -- this
    pins a second rule beyond P020 so that guarantee is broader than a single
    example."""
    before, after = "This is a heading about ", " results"
    word = "Perceptions"
    line = PdfTextLine(
        text=f"{before}{word}{after}",
        bbox=BBox(x0=72.0, y0=100.0, x1=360.0, y1=112.0),
        spans=[
            PdfTextSpan(text=before, bbox=BBox(x0=72.0, y0=100.0, x1=220.0, y1=112.0)),
            PdfTextSpan(text=word, bbox=BBox(x0=220.0, y0=100.0, x1=270.0, y1=112.0)),
            PdfTextSpan(text=after, bbox=BBox(x0=270.0, y0=100.0, x1=360.0, y1=112.0)),
        ],
    )
    token_bbox = word_bbox_in_line(line, word)
    assert token_bbox is not None
    assert token_bbox.width < line.bbox.width
    assert (token_bbox.x0, token_bbox.y0, token_bbox.x1, token_bbox.y1) == (
        220.0,
        100.0,
        270.0,
        112.0,
    )

    resolved = resolve_primary_highlight_bbox(
        {
            "bbox": "72.0,100.0,360.0,112.0",
            "token_bbox": (
                f"{token_bbox.x0},{token_bbox.y0},{token_bbox.x1},{token_bbox.y1}"
            ),
            "flagged_word": word,
            "line_preview": line.text,
        },
        rule_id="P027",
        issue_type="level3_sentence_case_issue",
    )
    assert resolved == (220.0, 100.0, 270.0, 112.0)


def test_word_bbox_never_matches_inside_a_larger_word() -> None:
    """Regression: a single-letter flagged token ("n") must resolve to a
    standalone token, never the "n" buried inside "Linear". Here the only
    standalone "n" lives in the "(n = 97)" span, so that span is returned."""
    line = PdfTextLine(
        text="Linear Regression (n = 97)",
        bbox=BBox(x0=72.0, y0=100.0, x1=300.0, y1=112.0),
        spans=[
            PdfTextSpan(
                text="Linear Regression (",
                bbox=BBox(x0=72.0, y0=100.0, x1=200.0, y1=112.0),
            ),
            PdfTextSpan(text="n", bbox=BBox(x0=200.0, y0=100.0, x1=208.0, y1=112.0)),
            PdfTextSpan(text=" = 97)", bbox=BBox(x0=208.0, y0=100.0, x1=300.0, y1=112.0)),
        ],
    )
    token_bbox = word_bbox_in_line(line, "n")
    assert token_bbox is not None
    # The returned box must be the standalone "n", not the "n" inside "Linear".
    assert token_bbox.x0 >= 200.0


# ---------------------------------------------------------------------------
# 6. P011 highlight coverage: the union of every violating line's box, not
#    just the single worst offender -- fixed from the prior baseline by
#    docs/status/highlight_quality_improvement_plan.md's first targeted
#    improvement. `worst_overflow_pt`/`affected_line_count`/`side`/`confidence`
#    still describe the single worst offender exactly as before; only which
#    region gets drawn changed.
# ---------------------------------------------------------------------------


def test_p011_grouped_violation_highlights_union_of_all_affected_lines(
    tmp_path: Path,
) -> None:
    """Current behavior: when several lines on a page violate the same margin
    (as a multi-row table extending into the margin would), P011 groups them
    into one finding, and the highlight bbox is the union of every violating
    line's box -- not only the single worst offender's -- so a multi-row
    table-like overflow is highlighted as one coherent region instead of one
    arbitrary row. This follows the P035 `body_bbox` precedent (test 3 above)."""
    pdf_path = tmp_path / "margin_three_different_overflows.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    # Three lines overflow the left margin (allowed x0 = 108pt) by different
    # amounts, so there is one unambiguous worst offender (the one starting
    # furthest left, at x=20) among lines that are otherwise all "violations".
    page.insert_text((60, 120), "Left overflow line one", fontsize=12)
    page.insert_text((20, 140), "Left overflow line two worst", fontsize=12)
    page.insert_text((80, 160), "Left overflow line three", fontsize=12)
    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))
    findings = run_pdf_margin_rule(model)
    warnings = [f for f in findings if f.rule_id == "P011" and f.severity.value == "WARNING"]
    assert len(warnings) == 1
    details = warnings[0].details
    # Diagnostic/wording metadata for the worst offender is unchanged.
    assert details.get("affected_line_count") == "3"
    assert details.get("side") == "left_margin"
    assert float(details.get("worst_overflow_pt", "0")) > 0.0

    boxes = parse_highlight_bboxes_from_details(
        details, rule_id="P011", issue_type="margin_boundary_violation"
    )
    # Three boxes reach the highlight layer: the affected-line region (a single
    # tight group, since these three lines are adjacent with nothing between
    # them), its overflow-only segment, and the margin-boundary guide line --
    # but no more than three, since the three violating lines are not split
    # into three separate line boxes.
    assert len(boxes) == 3
    x0, y0, x1, y1 = boxes[0]
    # A single 12pt line is roughly 14pt tall. These three lines span 40pt of
    # insertion points (120 to 160) plus a line's own height, so a genuine
    # union is well beyond one line's height -- proving this covers all three
    # lines, not just the worst offender's.
    assert y1 - y0 > 30.0, "expected a union spanning all three lines, not one line's height"
    # The third box is the thin left-margin boundary guide (allowed x0 = 108pt).
    gx0, gy0, gx1, gy1 = boxes[2]
    assert gx1 - gx0 < 5.0, "boundary guide must be a thin line, not a wide region"
    assert gx0 < 108.0 < gx1, "left-margin guide must straddle the required boundary at x=108"


def test_p011_single_violation_still_highlights_a_single_line_bbox(
    tmp_path: Path,
) -> None:
    """The union logic must not inflate a single-line finding: when only one
    line violates the margin, the highlight bbox is exactly that one line's
    box, the same as before this change."""
    pdf_path = tmp_path / "margin_single_violation.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((60, 120), "Only one overflowing line here", fontsize=12)
    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))
    findings = run_pdf_margin_rule(model)
    warnings = [f for f in findings if f.rule_id == "P011" and f.severity.value == "WARNING"]
    assert len(warnings) == 1
    details = warnings[0].details
    assert details.get("affected_line_count") == "1"

    boxes = parse_highlight_bboxes_from_details(
        details, rule_id="P011", issue_type="margin_boundary_violation"
    )
    # The single line's tight box, its overflow-only segment, plus the
    # margin-boundary guide line.
    assert len(boxes) == 3
    x0, y0, x1, y1 = boxes[0]
    assert y1 - y0 < 20.0, "a single-line finding must still highlight one line's height"
    gx0, gy0, gx1, gy1 = boxes[2]
    assert gx1 - gx0 < 5.0, "boundary guide must be a thin line, not a wide region"


def test_p011_highlight_union_does_not_invent_table_row_or_column_bbox(
    tmp_path: Path,
) -> None:
    """The P011 highlight-coverage fix only unions the *line* boxes it already
    detects internally; it does not introduce or infer a `table_bbox`,
    `row_bbox`, or `column_bbox` concept, matching the metadata-gap findings
    in docs/status/highlight_quality_improvement_plan.md. A true full-table
    bounding box (e.g. including unaffected columns/cells in the same table
    that don't individually violate the margin) is explicitly out of scope
    for this change."""
    pdf_path = tmp_path / "margin_grouped_no_table_bbox.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((60, 120), "Left overflow line one", fontsize=12)
    page.insert_text((20, 140), "Left overflow line two worst", fontsize=12)
    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))
    findings = run_pdf_margin_rule(model)
    warnings = [f for f in findings if f.rule_id == "P011" and f.severity.value == "WARNING"]
    assert len(warnings) == 1
    details = warnings[0].details
    assert "table_bbox" not in details
    assert "row_bbox" not in details
    assert "column_bbox" not in details
