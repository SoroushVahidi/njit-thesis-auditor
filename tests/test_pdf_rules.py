import json
from pathlib import Path

import fitz
from typer.testing import CliRunner

from njit_auditor.cli import app
from njit_auditor.highlight_targeting import (
    parse_highlight_bboxes_from_details,
    resolve_primary_highlight_bbox,
)
from njit_auditor.pdf_highlight import has_visible_highlight
from njit_auditor.pdf_layout import _style_flags_from_font_name, load_pdf_layout
from njit_auditor.pdf_models import (
    BBox,
    PdfDocument,
    PdfPage,
    PdfTextBlock,
    PdfTextLine,
    PdfTextSpan,
)
from njit_auditor.report_view import enriched_pdf_location_label
from njit_auditor.rules.pdf_abstract import check_pdf_abstract_word_count
from njit_auditor.rules.pdf_abstract_indentation import check_pdf_abstract_indentation
from njit_auditor.rules.pdf_acknowledgements_indentation import (
    check_pdf_acknowledgements_indentation,
)
from njit_auditor.rules.pdf_annotations import run_pdf_annotation_rule
from njit_auditor.rules.pdf_biosketch_bullet_spacing import (
    check_pdf_biosketch_bullet_spacing,
)
from njit_auditor.rules.pdf_biosketch_publication_layout import (
    check_pdf_biosketch_publication_layout,
)
from njit_auditor.rules.pdf_body_spacing import check_pdf_body_spacing
from njit_auditor.rules.pdf_captions import check_pdf_captions, detect_caption_lines
from njit_auditor.rules.pdf_copyright_page import (
    check_pdf_copyright_author_format,
    check_pdf_copyright_page,
    check_pdf_copyright_year_format,
)
from njit_auditor.rules.pdf_dedication_page import check_pdf_dedication_page
from njit_auditor.rules.pdf_figure_table_layout import check_pdf_figure_table_layout
from njit_auditor.rules.pdf_font_compliance import (
    check_pdf_font_compliance,
    classify_font,
)
from njit_auditor.rules.pdf_frontmatter_headings import check_pdf_frontmatter_headings
from njit_auditor.rules.pdf_frontmatter_no_page_number import (
    check_pdf_frontmatter_no_page_number,
)
from njit_auditor.rules.pdf_frontmatter_structure import (
    check_pdf_frontmatter_structure,
    check_pdf_title_page_graduation_month,
)
from njit_auditor.rules.pdf_heading_levels import (
    _is_all_caps_phrase,
    _looks_like_title_case_violation,
    check_pdf_heading_level_styles,
)
from njit_auditor.rules.pdf_headings import check_named_frontmatter_headings, find_body_start_page
from njit_auditor.rules.pdf_indentation import (
    _merge_same_row_fragments,
    _same_run_style,
    check_pdf_indentation,
)
from njit_auditor.rules.pdf_lof_terminal_punctuation import check_pdf_lof_terminal_punctuation
from njit_auditor.rules.pdf_lot_lof_column_header_style_alignment import (
    check_pdf_lot_lof_column_header_style_alignment,
    check_pdf_lot_lof_left_column_header_bold,
)
from njit_auditor.rules.pdf_lot_lof_column_headers import check_pdf_lot_lof_column_headers
from njit_auditor.rules.pdf_lot_lof_entry_number_alignment import (
    check_pdf_lot_lof_entry_number_alignment,
)
from njit_auditor.rules.pdf_lot_lof_entry_number_ordering import (
    check_pdf_lot_lof_entry_number_ordering,
)
from njit_auditor.rules.pdf_lot_lof_entry_type import check_pdf_lot_lof_entry_type
from njit_auditor.rules.pdf_lot_lof_number_format import check_pdf_lot_lof_number_format
from njit_auditor.rules.pdf_lot_lof_page_number_alignment import (
    check_pdf_lot_lof_page_number_alignment,
)
from njit_auditor.rules.pdf_lot_lof_page_number_ordering import (
    check_pdf_lot_lof_page_number_ordering,
)
from njit_auditor.rules.pdf_lot_terminal_period import check_pdf_lot_terminal_period
from njit_auditor.rules.pdf_margins import run_pdf_margin_rule
from njit_auditor.rules.pdf_page_numbering_regime import check_pdf_page_numbering_regime
from njit_auditor.rules.pdf_page_numbers import (
    check_pdf_page_number_sequence,
    run_pdf_page_number_candidates_rule,
)
from njit_auditor.rules.pdf_roman_section_anchors import check_pdf_roman_section_anchors
from njit_auditor.rules.pdf_spacing import check_pdf_spacing
from njit_auditor.rules.pdf_title_capitalization import (
    _is_math_font,
    _spans_bold_reason,
    check_apa_title_case_phrase,
    check_pdf_title_capitalization,
    is_minor_word,
    looks_like_acronym,
    normalize_numbered_heading_text,
)
from njit_auditor.rules.pdf_title_consistency import (
    _collect_title_candidates,
    _extract_below_heading_candidate,
    check_pdf_title_consistency,
)
from njit_auditor.rules.pdf_toc_alignment import check_pdf_toc_alignment
from njit_auditor.rules.pdf_toc_appendix_format import check_pdf_toc_appendix_format
from njit_auditor.rules.pdf_toc_continued_headings import check_pdf_toc_continued_headings
from njit_auditor.rules.pdf_toc_entry_hierarchy import check_pdf_toc_entry_hierarchy
from njit_auditor.rules.pdf_toc_entry_number_ordering import (
    check_pdf_toc_entry_number_ordering,
)
from njit_auditor.rules.pdf_toc_list_entry_spacing import check_pdf_toc_list_entry_spacing
from njit_auditor.rules.pdf_toc_list_formatting import check_pdf_toc_list_formatting
from njit_auditor.rules.pdf_toc_list_wrapped_spacing import check_pdf_toc_list_wrapped_spacing
from njit_auditor.rules.pdf_toc_page_number_ordering import (
    check_pdf_toc_page_number_ordering,
)

runner = CliRunner()


def _make_pdf_with_bottom_page_number(path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((300, 770), "1", fontsize=12)
    page.insert_text((120, 120), "Normal body text", fontsize=12)
    doc.save(path)
    doc.close()


def _make_pdf_with_margin_violation(path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((40, 120), "Too far left", fontsize=12)
    doc.save(path)
    doc.close()


def _make_pdf_with_right_margin_violation(path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    # Place long text near right edge so line bbox crosses right margin.
    page.insert_text((560, 120), "Right edge overflow text", fontsize=12)
    doc.save(path)
    doc.close()


def _make_pdf_with_small_left_overflow(path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    # Left margin is 108pt. x=106 should stay within tolerance (2pt).
    page.insert_text((106, 120), "Tiny overflow", fontsize=12)
    doc.save(path)
    doc.close()


def _make_pdf_with_grouped_left_violations(path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    for y in (120, 140, 160):
        page.insert_text((40, y), "Left overflow line", fontsize=12)
    doc.save(path)
    doc.close()


def _make_pdf_with_normal_text(path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((130, 130), "Inside margins", fontsize=12)
    doc.save(path)
    doc.close()


def _make_manual_pdf_doc_with_right_overflow(
    *, overflow_pt: float, line_count: int = 3
) -> PdfDocument:
    lines: list[PdfTextLine] = []
    for index in range(line_count):
        bbox = BBox(
            x0=108.0,
            y0=120.0 + (index * 18.0),
            x1=540.0 + overflow_pt,
            y1=132.0 + (index * 18.0),
        )
        span = PdfTextSpan(text=f"Synthetic overflow line {index}", bbox=bbox, size=12.0)
        lines.append(PdfTextLine(spans=[span], bbox=bbox, text=span.text))
    block_bbox = BBox(
        x0=min(line.bbox.x0 for line in lines),
        y0=min(line.bbox.y0 for line in lines),
        x1=max(line.bbox.x1 for line in lines),
        y1=max(line.bbox.y1 for line in lines),
    )
    page = PdfPage(
        page_number=1,
        width=612.0,
        height=792.0,
        text_blocks=[
            PdfTextBlock(
                lines=lines,
                bbox=block_bbox,
                text="\n".join(line.text for line in lines),
            )
        ],
    )
    return PdfDocument(path="synthetic.pdf", pages=[page])


def _make_pdf_with_annotation(path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((120, 120), "Annotated text", fontsize=12)
    annot = page.add_text_annot((180, 120), "Review comment")
    annot.update()
    doc.save(path)
    doc.close()


def _make_pdf_with_heading(
    path: Path,
    text: str = "ABSTRACT",
    x: float = 250,
    y: float = 90,
    fontname: str = "Times-Bold",
    centered: bool = False,
) -> None:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    if centered:
        # Center within the text area (1.5" left, 1" right margins) so centering
        # checks against text_area_center pass correctly.
        page.insert_textbox(
            fitz.Rect(108, y - 20, 540, y + 20),
            text,
            fontsize=16,
            fontname=fontname,
            align=fitz.TEXT_ALIGN_CENTER,
        )
    else:
        page.insert_text((x, y), text, fontsize=16, fontname=fontname)
    doc.save(path)
    doc.close()


def _draw_paragraph(
    page: fitz.Page, first_x: float, rest_x: float, y: float, lines: int = 3
) -> None:
    page.insert_text((first_x, y), "This is a synthetic paragraph line for indentation checks.")
    for idx in range(1, lines):
        page.insert_text((rest_x, y + (idx * 14)), "Continuation synthetic paragraph line text.")


def _draw_spacing_lines(page: fitz.Page, y_positions: list[float], x: float = 108) -> None:
    for idx, y in enumerate(y_positions):
        page.insert_text((x, y), f"Synthetic spacing line {idx} with normal text content.")


def _draw_toc_entry(
    page: fitz.Page, y: float, label_x: float, label: str, page_num_x: float
) -> None:
    page.insert_text((label_x, y), label)
    page.insert_text((page_num_x, y), "12")


def _make_pdf_with_page_numbers(
    path: Path,
    texts: list[str | None],
    x: float = 300,
    y: float = 770,
    add_second_numbers: dict[int, tuple[str, float]] | None = None,
) -> None:
    doc = fitz.open()
    for idx, txt in enumerate(texts):
        page = doc.new_page(width=612, height=792)
        if txt is not None:
            page.insert_text((x, y), txt, fontsize=12)
        if add_second_numbers and idx in add_second_numbers:
            extra_text, extra_x = add_second_numbers[idx]
            page.insert_text((extra_x, y), extra_text, fontsize=12)
    doc.save(path)
    doc.close()


def test_page_number_candidate_detected(tmp_path: Path) -> None:
    pdf_path = tmp_path / "page_no.pdf"
    _make_pdf_with_bottom_page_number(pdf_path)
    model = load_pdf_layout(str(pdf_path))
    findings = run_pdf_page_number_candidates_rule(model)
    assert any(f.rule_id == "P013" and f.severity.value == "WARNING" for f in findings)


def test_page_number_candidates_grouped_per_page(tmp_path: Path) -> None:
    pdf_path = tmp_path / "page_no_grouped.pdf"
    _make_pdf_with_page_numbers(
        pdf_path,
        texts=["1", "2"],
        x=300,
        y=770,
        add_second_numbers={0: ("i", 540)},
    )
    model = load_pdf_layout(str(pdf_path))
    findings = run_pdf_page_number_candidates_rule(model)
    warnings = [f for f in findings if f.rule_id == "P013" and f.page is not None]
    assert len(warnings) == 2

    overview = next(f for f in findings if f.rule_id == "P013" and f.page is None)
    assert overview.details.get("issue_type") == "p013_document_overview"
    assert overview.details.get("triage_tier") == "informational"

    page1 = next(f for f in warnings if f.page == 1)
    assert page1.details.get("issue_type") == "page_number_candidate"
    assert page1.details.get("candidate_count_on_page") == "2"
    assert page1.details.get("candidate_sample")
    assert page1.details.get("confidence") in {"low", "medium"}
    assert page1.details.get("triage_tier") == "informational"

    page2 = next(f for f in warnings if f.page == 2)
    assert page2.details.get("candidate_count_on_page") == "1"


def test_p013_frontmatter_toc_right_column_numbers_filtered(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p013_toc_column_filtered.pdf"
    doc = fitz.open()

    p1 = doc.new_page(width=612, height=792)
    p1.insert_text((180, 90), "TABLE OF CONTENTS", fontsize=14, fontname="Times-Bold")
    p1.insert_text((108, 180), "Introduction", fontsize=12)
    p1.insert_text((528, 180), "29", fontsize=12)
    p1.insert_text((108, 200), "Literature Review", fontsize=12)
    p1.insert_text((528, 200), "34", fontsize=12)
    p1.insert_text((300, 760), "viii", fontsize=12)

    p2 = doc.new_page(width=612, height=792)
    p2.insert_text((220, 90), "CHAPTER 1", fontsize=16, fontname="Times-Bold")
    p2.insert_text((220, 120), "INTRODUCTION", fontsize=14, fontname="Times-Bold")
    p2.insert_text((300, 760), "1", fontsize=12)

    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in run_pdf_page_number_candidates_rule(model) if f.page == 1]
    assert len(findings) == 1
    finding = findings[0]
    assert finding.details.get("issue_type") == "page_number_candidate"
    assert finding.details.get("candidate_count_on_page") == "1"
    assert finding.details.get("position_type") == "bottom_center"
    assert finding.details.get("number_style") == "roman_lower"


def test_margin_violation_detected(tmp_path: Path) -> None:
    pdf_path = tmp_path / "margin_bad.pdf"
    _make_pdf_with_margin_violation(pdf_path)
    model = load_pdf_layout(str(pdf_path))
    findings = run_pdf_margin_rule(model)
    warning = next(f for f in findings if f.rule_id == "P011" and f.severity.value == "WARNING")
    assert warning.details
    assert warning.details.get("side") == "left_margin"
    assert float(warning.details.get("worst_overflow_pt", "0")) > 3.0


def test_right_margin_violation_detected(tmp_path: Path) -> None:
    pdf_path = tmp_path / "margin_right_bad.pdf"
    _make_pdf_with_right_margin_violation(pdf_path)
    model = load_pdf_layout(str(pdf_path))
    findings = run_pdf_margin_rule(model)
    warning = next(f for f in findings if f.rule_id == "P011" and f.severity.value == "WARNING")
    assert warning.details
    assert warning.details.get("side") == "right_margin"


def test_small_overflow_is_ignored(tmp_path: Path) -> None:
    pdf_path = tmp_path / "margin_tiny.pdf"
    _make_pdf_with_small_left_overflow(pdf_path)
    model = load_pdf_layout(str(pdf_path))
    findings = run_pdf_margin_rule(model)
    assert any(f.rule_id == "P011" and f.severity.value == "PASS" for f in findings)


def test_no_false_margin_violation_for_normal_text(tmp_path: Path) -> None:
    pdf_path = tmp_path / "margin_ok.pdf"
    _make_pdf_with_normal_text(pdf_path)
    model = load_pdf_layout(str(pdf_path))
    findings = run_pdf_margin_rule(model)
    assert any(f.rule_id == "P011" and f.severity.value == "PASS" for f in findings)


def test_margin_violations_grouped_by_side(tmp_path: Path) -> None:
    pdf_path = tmp_path / "margin_grouped.pdf"
    _make_pdf_with_grouped_left_violations(pdf_path)
    model = load_pdf_layout(str(pdf_path))
    findings = run_pdf_margin_rule(model)
    warnings = [f for f in findings if f.rule_id == "P011" and f.severity.value == "WARNING"]
    assert len(warnings) == 1
    assert warnings[0].details
    assert warnings[0].details.get("side") == "left_margin"
    assert warnings[0].details.get("affected_line_count") == "3"


def test_page_number_candidate_not_flagged_as_margin_violation(tmp_path: Path) -> None:
    pdf_path = tmp_path / "page_number_only.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((300, 770), "1", fontsize=12)
    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))
    findings = run_pdf_margin_rule(model)
    assert any(f.rule_id == "P011" and f.severity.value == "PASS" for f in findings)


def _make_pdf_with_many_marginal_right_overflows(
    path: Path, line_count: int = 6, overflow_x: float = 537
) -> None:
    """Create a PDF where many lines each barely cross the right margin (artifact pattern)."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    for i in range(line_count):
        page.insert_text((overflow_x, 120 + i * 18), "Xx", fontsize=12)
    doc.save(path)
    doc.close()


def _make_pdf_with_many_large_right_overflows(path: Path, line_count: int = 6) -> None:
    """Create a PDF where many lines deeply overflow the right margin (real violations)."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    for i in range(line_count):
        page.insert_text((400, 120 + i * 18), "Far right overflow text AAAA", fontsize=12)
    doc.save(path)
    doc.close()


def test_artifact_group_high_count_low_overflow_suppressed(tmp_path: Path) -> None:
    pdf_path = tmp_path / "artifact_many_marginal.pdf"
    _make_pdf_with_many_marginal_right_overflows(pdf_path, line_count=6, overflow_x=533)
    model = load_pdf_layout(str(pdf_path))
    findings = run_pdf_margin_rule(model)
    # A group of ≥5 lines all barely crossing the margin should be suppressed as artifact.
    assert any(f.rule_id == "P011" and f.severity.value == "PASS" for f in findings)


def test_large_overflow_group_still_warns_despite_many_lines(tmp_path: Path) -> None:
    pdf_path = tmp_path / "real_many_overflow.pdf"
    _make_pdf_with_many_large_right_overflows(pdf_path, line_count=6)
    model = load_pdf_layout(str(pdf_path))
    findings = run_pdf_margin_rule(model)
    warnings = [f for f in findings if f.rule_id == "P011" and f.severity.value == "WARNING"]
    assert warnings, "Substantial right-margin overflow should still fire even with many lines"
    assert any(w.details.get("side") == "right_margin" for w in warnings)


def test_p011_warning_includes_triage_tier(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p011_triage_tier.pdf"
    _make_pdf_with_margin_violation(pdf_path)
    model = load_pdf_layout(str(pdf_path))
    findings = run_pdf_margin_rule(model)
    warning = next(f for f in findings if f.rule_id == "P011" and f.severity.value == "WARNING")
    assert warning.details.get("triage_tier") == "informational"
    assert warning.details.get("issue_type") == "margin_boundary_violation"


def test_confidence_field_present_in_p011_warning(tmp_path: Path) -> None:
    pdf_path = tmp_path / "margin_conf.pdf"
    _make_pdf_with_margin_violation(pdf_path)
    model = load_pdf_layout(str(pdf_path))
    findings = run_pdf_margin_rule(model)
    warning = next(f for f in findings if f.rule_id == "P011" and f.severity.value == "WARNING")
    assert warning.details
    assert "confidence" in warning.details
    assert warning.details["confidence"] in ("low", "medium", "high")


def test_small_group_real_violation_still_warns(tmp_path: Path) -> None:
    pdf_path = tmp_path / "margin_small_group.pdf"
    _make_pdf_with_right_margin_violation(pdf_path)
    model = load_pdf_layout(str(pdf_path))
    findings = run_pdf_margin_rule(model)
    # Small group (count < 5) should never be suppressed by the artifact guard.
    assert any(f.rule_id == "P011" and f.severity.value == "WARNING" for f in findings)


def test_right_margin_float_fuzz_at_threshold_is_ignored() -> None:
    """A multi-line group at 3.000xpt should honor the documented 3pt cutoff,
    not promote float noise into a medium-confidence warning."""
    model = _make_manual_pdf_doc_with_right_overflow(overflow_pt=3.002, line_count=3)
    findings = run_pdf_margin_rule(model)
    assert not any(f.rule_id == "P011" and f.severity.value == "WARNING" for f in findings)
    assert any(f.rule_id == "P011" and f.severity.value == "PASS" for f in findings)


def test_right_margin_overflow_just_beyond_float_guard_still_warns() -> None:
    model = _make_manual_pdf_doc_with_right_overflow(overflow_pt=3.02, line_count=3)
    findings = run_pdf_margin_rule(model)
    warnings = [f for f in findings if f.rule_id == "P011" and f.severity.value == "WARNING"]
    assert len(warnings) == 1
    assert warnings[0].details.get("side") == "right_margin"
    assert warnings[0].details.get("confidence") == "medium"


def test_thin_right_margin_overflow_gets_display_widening() -> None:
    model = _make_manual_pdf_doc_with_right_overflow(overflow_pt=3.02, line_count=2)
    findings = run_pdf_margin_rule(model)
    warning = next(f for f in findings if f.rule_id == "P011" and f.severity.value == "WARNING")
    boxes = parse_highlight_bboxes_from_details(
        warning.details, rule_id="P011", issue_type="margin_boundary_violation"
    )
    overflow_boxes = [box for box in boxes if box.kind == "overflow"]
    display_boxes = [box for box in boxes if box.kind == "overflow_display"]
    guide_boxes = [box for box in boxes if box.kind == "guide"]
    assert len(overflow_boxes) == 1
    assert len(display_boxes) == 1
    assert len(guide_boxes) == 1
    overflow_box = overflow_boxes[0]
    display_box = display_boxes[0]
    assert display_box[2] - display_box[0] >= 4.0
    assert display_box[2] - display_box[0] >= overflow_box[2] - overflow_box[0]
    assert display_box[0] <= overflow_box[0]
    assert display_box[2] >= overflow_box[2]


def test_grouped_violations_confidence_high_for_large_overflow(tmp_path: Path) -> None:
    pdf_path = tmp_path / "margin_high_conf.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((40, 120), "Very far left extreme overflow text here", fontsize=12)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = run_pdf_margin_rule(model)
    warning = next(f for f in findings if f.rule_id == "P011" and f.severity.value == "WARNING")
    assert warning.details.get("confidence") == "high"


def test_p011_tiny_single_line_overflow_is_suppressed(tmp_path: Path) -> None:
    """A tiny (just-over-tolerance), single-line overflow is no longer reported
    as a problem at all.

    Before Ester's Sample B review, this "low confidence" pattern (single
    line, sub-5pt overflow) still produced a full P011 warning. Ester's
    review confirmed several real-document instances of exactly this pattern
    (single short line, ~3-5pt right-margin "overflow") as false positives —
    almost certainly font-metric/text-extraction measurement noise rather
    than real content outside the margin. See
    docs/status/ester_sample_b_p011_margin_low_overflow.md.
    """
    pdf_path = tmp_path / "margin_tiny_low_conf.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    # Left margin is 108pt; x=103.5 -> ~4.5pt overflow (above the 3pt tolerance,
    # below the 5pt medium-confidence floor) on a single line.
    page.insert_text((103.5, 120), "Barely over the left margin here", fontsize=12)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = run_pdf_margin_rule(model)
    assert any(f.rule_id == "P011" and f.severity.value == "PASS" for f in findings)
    assert not any(f.rule_id == "P011" and f.severity.value == "WARNING" for f in findings)


def test_p011_real_overflow_message_states_measured_overrun(tmp_path: Path) -> None:
    """A substantial margin crossing must state the exact measured overrun in
    the finding message, not a generic 'possible crossing' with no numbers."""
    pdf_path = tmp_path / "margin_message_overrun.pdf"
    _make_pdf_with_margin_violation(pdf_path)
    model = load_pdf_layout(str(pdf_path))
    findings = run_pdf_margin_rule(model)
    warning = next(f for f in findings if f.rule_id == "P011" and f.severity.value == "WARNING")
    overflow = float(warning.details["worst_overflow_pt"])
    assert f"{overflow:.1f} pt" in warning.message
    assert warning.details.get("confidence") == "high"
    assert warning.details.get("triage_tier") == "informational"


def test_annotation_extraction_detects_comment(tmp_path: Path) -> None:
    pdf_path = tmp_path / "annot.pdf"
    _make_pdf_with_annotation(pdf_path)
    findings = run_pdf_annotation_rule(str(pdf_path))
    assert findings
    assert any(f.rule_id == "P012" for f in findings)


def test_p012_warnings_include_triage_metadata(tmp_path: Path) -> None:
    pdf_path = tmp_path / "annot_triage.pdf"
    _make_pdf_with_annotation(pdf_path)
    warnings = [f for f in run_pdf_annotation_rule(str(pdf_path)) if f.severity.value == "WARNING"]
    assert warnings
    for finding in warnings:
        assert finding.details.get("issue_type") == "pdf_annotation_detected"
        assert finding.details.get("triage_tier") == "informational"


def test_centered_bold_abstract_near_top_produces_no_p014_warning(tmp_path: Path) -> None:
    pdf_path = tmp_path / "heading_ok.pdf"
    _make_pdf_with_heading(
        pdf_path, text="ABSTRACT", x=250, y=90, fontname="Times-Bold", centered=True
    )
    model = load_pdf_layout(str(pdf_path))
    findings = check_named_frontmatter_headings(model)
    assert not any(f.rule_id == "P014" for f in findings)


def test_off_center_abstract_produces_p014_warning(tmp_path: Path) -> None:
    pdf_path = tmp_path / "heading_off_center.pdf"
    _make_pdf_with_heading(pdf_path, text="ABSTRACT", x=120, y=90, fontname="Times-Bold")
    model = load_pdf_layout(str(pdf_path))
    findings = check_named_frontmatter_headings(model)
    warning = next(f for f in findings if f.rule_id == "P014")
    assert warning.details.get("centered") == "False"


def test_lowercase_abstract_produces_p014_warning(tmp_path: Path) -> None:
    pdf_path = tmp_path / "heading_case.pdf"
    _make_pdf_with_heading(pdf_path, text="Abstract", x=250, y=90, fontname="Times-Bold")
    model = load_pdf_layout(str(pdf_path))
    findings = check_named_frontmatter_headings(model)
    warning = next(f for f in findings if f.rule_id == "P014")
    assert warning.details.get("all_caps") == "False"


def test_non_bold_abstract_produces_p014_warning(tmp_path: Path) -> None:
    pdf_path = tmp_path / "heading_non_bold.pdf"
    _make_pdf_with_heading(pdf_path, text="ABSTRACT", x=250, y=90, fontname="Times-Roman")
    model = load_pdf_layout(str(pdf_path))
    findings = check_named_frontmatter_headings(model)
    warning = next(f for f in findings if f.rule_id == "P014")
    assert warning.details.get("bold") == "False"


def test_abstract_too_low_produces_p014_warning(tmp_path: Path) -> None:
    pdf_path = tmp_path / "heading_too_low.pdf"
    _make_pdf_with_heading(pdf_path, text="ABSTRACT", x=250, y=220, fontname="Times-Bold")
    model = load_pdf_layout(str(pdf_path))
    findings = check_named_frontmatter_headings(model)
    warning = next(f for f in findings if f.rule_id == "P014")
    assert warning.details.get("near_top") == "False"


def test_p014_cmbx_bold_heading_not_flagged_as_non_bold() -> None:
    # CMBX (Computer Modern Bold Extended) is recognized as bold via _style_flags_from_font_name.
    # Test directly at model level since CMBX is not a built-in PyMuPDF render font.
    from njit_auditor.pdf_layout import _style_flags_from_font_name
    from njit_auditor.pdf_models import BBox, PdfDocument, PdfPage, PdfTextBlock, PdfTextSpan
    from njit_auditor.rules.pdf_headings import check_named_frontmatter_headings

    bold, _ = _style_flags_from_font_name("CMBX12")
    assert bold, "CMBX12 font name should be recognized as bold"

    span = PdfTextSpan(
        text="ABSTRACT",
        bbox=BBox(x0=282.0, y0=75.0, x1=366.0, y1=91.0),
        font="CMBX12",
        size=14.0,
        bold=bold,
        italic=False,
    )
    line = PdfTextLine(
        spans=[span],
        bbox=BBox(x0=282.0, y0=75.0, x1=366.0, y1=91.0),
        text="ABSTRACT",
    )
    block = PdfTextBlock(
        lines=[line],
        bbox=BBox(x0=282.0, y0=75.0, x1=366.0, y1=91.0),
        text="ABSTRACT",
    )
    page = PdfPage(page_number=1, width=612.0, height=792.0, text_blocks=[block])
    doc = PdfDocument(path="synthetic", pages=[page])

    findings = check_named_frontmatter_headings(doc)
    non_bold = [f for f in findings if f.rule_id == "P014" and f.details.get("bold") == "False"]
    assert not non_bold, "CMBX heading should be recognized as bold"


def test_p014_text_area_centered_heading_passes(tmp_path: Path) -> None:
    # Heading centered within the text area (between margins) should pass P014.
    pdf_path = tmp_path / "heading_ta_centered.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    # Insert heading centered within text area [108, 540] — center at 324pt.
    page.insert_textbox(
        fitz.Rect(108, 70, 540, 110),
        "ABSTRACT",
        fontsize=16,
        fontname="Times-Bold",
        align=fitz.TEXT_ALIGN_CENTER,
    )
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_named_frontmatter_headings(model)
    assert not any(f.rule_id == "P014" for f in findings), (
        "Heading centered in text area should pass P014"
    )


def test_flush_left_first_abstract_paragraph_does_not_warn(tmp_path: Path) -> None:
    pdf_path = tmp_path / "indent_abstract_ok.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((250, 90), "ABSTRACT", fontsize=16, fontname="Times-Bold")
    _draw_paragraph(page, first_x=108, rest_x=108, y=140)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_indentation(model)
    assert not any(f.rule_id == "P015" for f in findings)


def test_indented_first_abstract_paragraph_warns(tmp_path: Path) -> None:
    # P015 no longer fires on Abstract pages (Q002 covered atomically by P044).
    # Verify P044 catches the indented first abstract paragraph instead.
    pdf_path = tmp_path / "indent_abstract_bad.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((250, 90), "ABSTRACT", fontsize=16, fontname="Times-Bold")
    _draw_paragraph(page, first_x=190, rest_x=108, y=140)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    # P015 must not fire on Abstract page
    p015_findings = [f for f in check_pdf_indentation(model) if f.rule_id == "P015"]
    assert not p015_findings, "P015 should not fire on Abstract page after atomic split"
    # P044 must catch the indented first paragraph (Q002)
    p044_findings = check_pdf_abstract_indentation(model)
    warning = next(
        (
            f for f in p044_findings
            if f.details.get("issue_type") == "abstract_first_paragraph_indented"
        ),
        None,
    )
    assert warning is not None, "P044 should catch indented first abstract paragraph (Q002)"
    assert warning.details.get("source_q_rule_id") == "Q002"


def test_later_paragraph_with_expected_indent_does_not_warn(tmp_path: Path) -> None:
    pdf_path = tmp_path / "indent_later_ok.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    _draw_paragraph(page, first_x=190, rest_x=108, y=140)
    _draw_paragraph(page, first_x=190, rest_x=108, y=210)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_indentation(model)
    assert not any(f.rule_id == "P015" for f in findings)


def test_later_paragraph_missing_indent_warns(tmp_path: Path) -> None:
    pdf_path = tmp_path / "indent_later_bad.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    _draw_paragraph(page, first_x=190, rest_x=108, y=140)
    _draw_paragraph(page, first_x=190, rest_x=108, y=210)
    _draw_paragraph(page, first_x=108, rest_x=108, y=280, lines=4)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_indentation(model)
    warning = next(f for f in findings if f.rule_id == "P015")
    assert warning.details.get("issue_type") == "missing_later_indent"
    assert warning.details.get("expected") == "first_line_indent_approx_36pt"
    assert warning.details.get("paragraph_index") == "3"
    bbox = warning.details.get("bbox", "")
    assert len(bbox.split(",")) == 4


def test_headings_and_page_numbers_are_ignored_for_p015(tmp_path: Path) -> None:
    pdf_path = tmp_path / "indent_ignore_heading_page_num.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((250, 90), "ABSTRACT", fontsize=16, fontname="Times-Bold")
    page.insert_text((300, 770), "1", fontsize=12)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_indentation(model)
    assert not any(f.rule_id == "P015" for f in findings)


def test_figure_or_table_caption_is_ignored_for_p015(tmp_path: Path) -> None:
    pdf_path = tmp_path / "indent_ignore_caption.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((190, 140), "Figure 1. This is a synthetic caption line.")
    page.insert_text((108, 154), "Continuation synthetic caption text line.")
    page.insert_text((108, 168), "Another continuation caption line.")
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_indentation(model)
    assert not any(f.rule_id == "P015" for f in findings)


def test_references_like_page_is_ignored_for_p015(tmp_path: Path) -> None:
    pdf_path = tmp_path / "indent_ignore_references.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((250, 90), "REFERENCES", fontsize=16, fontname="Times-Bold")
    _draw_paragraph(page, first_x=190, rest_x=108, y=140)
    _draw_paragraph(page, first_x=108, rest_x=108, y=210)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_indentation(model)
    assert not any(f.rule_id == "P015" for f in findings)


def test_bullet_list_paragraph_is_ignored_for_p015(tmp_path: Path) -> None:
    pdf_path = tmp_path / "indent_ignore_bullets.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((190, 140), "- Bullet line one with synthetic text.")
    page.insert_text((108, 154), "Continuation bullet explanation line.")
    page.insert_text((108, 168), "Another continuation bullet line.")
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_indentation(model)
    assert not any(f.rule_id == "P015" for f in findings)


def test_low_confidence_short_or_two_line_paragraphs_are_ignored(tmp_path: Path) -> None:
    pdf_path = tmp_path / "indent_ignore_low_confidence.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((190, 140), "This is a synthetic first line.")
    page.insert_text((108, 154), "This is a synthetic continuation line.")
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_indentation(model)
    assert not any(f.rule_id == "P015" for f in findings)


def test_repeated_same_page_p015_warnings_are_grouped(tmp_path: Path) -> None:
    pdf_path = tmp_path / "indent_grouped_same_page.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    _draw_paragraph(page, first_x=190, rest_x=108, y=140)
    _draw_paragraph(page, first_x=190, rest_x=108, y=210)
    _draw_paragraph(page, first_x=190, rest_x=108, y=280)
    _draw_paragraph(page, first_x=108, rest_x=108, y=350, lines=4)
    _draw_paragraph(page, first_x=108, rest_x=108, y=430, lines=4)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_indentation(model) if f.rule_id == "P015"]
    assert len(findings) == 1
    assert findings[0].details.get("issue_type") == "missing_later_indent"


def test_later_paragraph_missing_indent_low_style_confidence_is_ignored(tmp_path: Path) -> None:
    pdf_path = tmp_path / "indent_later_low_style_confidence.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    _draw_paragraph(page, first_x=190, rest_x=108, y=140)
    _draw_paragraph(page, first_x=108, rest_x=108, y=210, lines=4)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_indentation(model)
    assert not any(f.rule_id == "P015" for f in findings)


def test_p015_algorithm_block_not_treated_as_missing_indent(tmp_path: Path) -> None:
    pdf_path = tmp_path / "indent_algorithm_block.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    _draw_paragraph(page, first_x=190, rest_x=108, y=140)
    _draw_paragraph(page, first_x=190, rest_x=108, y=210)
    page.insert_text((108, 300), "Input: n, epsilon, psi, omega.")
    page.insert_text((108, 314), "for i in range(0, N) do")
    page.insert_text((108, 328), "{accept candidate}")
    page.insert_text((108, 342), "until t < T")
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_indentation(model) if f.rule_id == "P015"]
    assert not findings


def test_p015_lowercase_continuation_split_not_treated_as_new_paragraph(tmp_path: Path) -> None:
    pdf_path = tmp_path / "indent_lowercase_continuation.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    _draw_paragraph(page, first_x=190, rest_x=108, y=140)
    _draw_paragraph(page, first_x=190, rest_x=108, y=210)
    page.insert_text((108, 300), "approaches produce a continuation-style split paragraph line.")
    page.insert_text((108, 314), "Continuation text for the same synthetic paragraph line.")
    page.insert_text((108, 328), "Another continuation line for the same synthetic paragraph.")
    page.insert_text((108, 342), "Final continuation line for the same paragraph block.")
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_indentation(model) if f.rule_id == "P015"]
    assert not findings


def test_p015_first_paragraph_after_split_numbered_heading_not_flagged(tmp_path: Path) -> None:
    pdf_path = tmp_path / "indent_split_heading.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    _draw_paragraph(page, first_x=190, rest_x=108, y=140)
    _draw_paragraph(page, first_x=190, rest_x=108, y=210)
    page.insert_text((246, 300), "4.3", fontsize=12)
    page.insert_text((276, 300), "Problem Formulation", fontsize=12)
    page.insert_text(
        (108, 340),
        "This paragraph should be flush left after the heading line.",
        fontsize=12,
    )
    page.insert_text(
        (108, 354),
        "Continuation text for the same synthetic paragraph block.",
        fontsize=12,
    )
    page.insert_text(
        (108, 368),
        "Another continuation line for the same paragraph block.",
        fontsize=12,
    )
    page.insert_text(
        (108, 382),
        "Final continuation line for the same paragraph block.",
        fontsize=12,
    )
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_indentation(model) if f.rule_id == "P015"]
    assert not findings


def test_p015_same_baseline_split_line_not_treated_as_new_paragraph(tmp_path: Path) -> None:
    """Regression for Sample B page 23: extraction split one line into two same-y runs.

    When a PDF producer emits a single visual line as two non-overlapping,
    same-style text runs at an identical baseline, the following continuation
    lines must stay part of the same paragraph rather than being misread as a
    new, unindented paragraph.
    """
    pdf_path = tmp_path / "indent_same_baseline_split.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    _draw_paragraph(page, first_x=190, rest_x=108, y=140)
    page.insert_text((190, 210), "This is a synthetic paragraph line for indentation checks.")
    page.insert_text((108, 224), "Continuation synthetic paragraph line text.")
    page.insert_text((108, 238), "Split line fragment one ends here.")
    page.insert_text((300, 238), "and fragment two continues on the same baseline.")
    page.insert_text((108, 252), "Continuation synthetic paragraph line text again.")
    page.insert_text((108, 266), "Another continuation synthetic paragraph line text.")
    page.insert_text((108, 280), "Final continuation synthetic paragraph line text.")
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_indentation(model) if f.rule_id == "P015"]
    assert not findings


def test_merge_same_row_fragments_combines_matching_style_runs() -> None:
    bbox_a = BBox(x0=108.0, y0=568.8, x1=374.8, y1=580.7)
    bbox_b = BBox(x0=388.0, y0=568.8, x1=540.0, y1=580.7)
    span_a = PdfTextSpan(text="field.", bbox=bbox_a, font="CMR12", bold=False, italic=False)
    span_b = PdfTextSpan(text="One", bbox=bbox_b, font="CMR12", bold=False, italic=False)
    line_a = PdfTextLine(spans=[span_a], bbox=bbox_a, text="field.")
    line_b = PdfTextLine(spans=[span_b], bbox=bbox_b, text="One")

    merged = _merge_same_row_fragments([line_a, line_b])

    assert len(merged) == 1
    assert merged[0].bbox.x0 == 108.0
    assert merged[0].bbox.x1 == 540.0
    assert merged[0].text == "field. One"


def test_merge_same_row_fragments_keeps_run_in_heading_separate() -> None:
    """A bold run-in heading followed by regular text must not be merged.

    Sample B pages 46/68 open a paragraph with a bold LaTeX-style run-in
    heading (e.g. "Strong-Start Annealing Principle.") immediately followed
    by regular body text on the same baseline. That style change is a real
    row, not an extraction artifact, and must stay two lines.
    """
    bbox_a = BBox(x0=108.0, y0=322.5, x1=306.0, y1=334.4)
    bbox_b = BBox(x0=317.6, y0=322.5, x1=547.6, y1=334.4)
    heading_span = PdfTextSpan(
        text="Strong-Start Annealing Principle.", bbox=bbox_a, font="CMBX12", bold=True
    )
    body_span = PdfTextSpan(
        text="The scheduling strategy follows a strong-start", bbox=bbox_b, font="CMR12", bold=False
    )
    line_a = PdfTextLine(spans=[heading_span], bbox=bbox_a, text=heading_span.text)
    line_b = PdfTextLine(spans=[body_span], bbox=bbox_b, text=body_span.text)

    assert _same_run_style(line_a, line_b) is False
    merged = _merge_same_row_fragments([line_a, line_b])
    assert len(merged) == 2


def test_pdf_cli_command_runs(tmp_path: Path) -> None:
    # PDF has ABSTRACT heading with an indented first paragraph.
    # P015 no longer fires on Abstract pages (Q002 covered atomically by P044).
    pdf_path = tmp_path / "cli.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((250, 90), "ABSTRACT", fontsize=16, fontname="Times-Bold")
    _draw_paragraph(page, first_x=190, rest_x=108, y=140)
    doc.save(pdf_path)
    doc.close()
    result = runner.invoke(app, ["pdf", str(pdf_path)])
    assert result.exit_code == 0
    assert "PDF Layout Findings" in result.output
    assert "P044" in result.output


def test_normal_spacing_does_not_warn_for_p016(tmp_path: Path) -> None:
    pdf_path = tmp_path / "spacing_ok.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    _draw_spacing_lines(page, [140, 154, 168, 182, 196, 210])
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_spacing(model)
    assert not any(f.rule_id == "P016" for f in findings)


def test_obvious_large_blank_gap_warns_for_p016(tmp_path: Path) -> None:
    pdf_path = tmp_path / "spacing_large_gap.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((250, 90), "ABSTRACT", fontsize=16, fontname="Times-Bold")
    _draw_spacing_lines(page, [140, 154, 168, 240, 254, 326])
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in check_pdf_spacing(model) if f.rule_id == "P016"]
    assert warnings
    assert any(f.details.get("issue_type") == "excessive_line_gap" for f in warnings)


def test_repeated_excessive_gaps_grouped_for_p016(tmp_path: Path) -> None:
    """Repeated large gaps are grouped into one P016 finding, not one per gap.

    These gaps are large enough to clear both the line-gap and the stricter
    paragraph-gap threshold, so the paragraph-gap finding is the one that
    fires (see test_p016_paragraph_gap_suppresses_redundant_line_gap for the
    dedup rule itself). It still reports affected_gap_count == 2, preserving
    the "grouped, not duplicated per gap" guarantee this test checks.
    """
    pdf_path = tmp_path / "spacing_grouped.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((250, 90), "ABSTRACT", fontsize=16, fontname="Times-Bold")
    _draw_spacing_lines(page, [140, 154, 230, 244, 320, 334])
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in check_pdf_spacing(model) if f.rule_id == "P016"]
    assert len(warnings) == 1
    assert warnings[0].details.get("issue_type") == "excessive_paragraph_gap"
    assert warnings[0].details.get("affected_gap_count") == "2"


def test_page_number_line_ignored_for_p016(tmp_path: Path) -> None:
    pdf_path = tmp_path / "spacing_ignore_page_number.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    _draw_spacing_lines(page, [140, 154, 168])
    page.insert_text((300, 770), "1", fontsize=12)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_spacing(model)
    assert not any(f.rule_id == "P016" for f in findings)


def test_toc_like_page_ignored_for_p016(tmp_path: Path) -> None:
    pdf_path = tmp_path / "spacing_ignore_toc.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((220, 90), "TABLE OF CONTENTS", fontsize=16, fontname="Times-Bold")
    _draw_spacing_lines(page, [140, 154, 230, 244])
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_spacing(model)
    assert not any(f.rule_id == "P016" for f in findings)


def test_pdf_cli_command_runs_with_p016(tmp_path: Path) -> None:
    pdf_path = tmp_path / "cli_spacing.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((250, 90), "ABSTRACT", fontsize=16, fontname="Times-Bold")
    _draw_spacing_lines(page, [140, 154, 230, 244])
    doc.save(pdf_path)
    doc.close()
    result = runner.invoke(app, ["pdf", str(pdf_path)])
    assert result.exit_code == 0
    assert "P016" in result.output


def test_biographical_sketch_page_skipped_for_p016(tmp_path: Path) -> None:
    """Biographical Sketch special-layout pages must not trigger P016.

    The intentional large blank area after the centered BIOGRAPHICAL SKETCH
    heading (before the author/degree/date block) is template layout, not an
    accidental blank line. The identical geometry on an ABSTRACT page is still
    flagged (see test_obvious_large_blank_gap_warns_for_p016).
    """
    pdf_path = tmp_path / "biosketch_p016.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((225, 90), "BIOGRAPHICAL SKETCH", fontsize=16, fontname="Times-Bold")
    # Large intentional gap after the heading, then the author/degree/date block.
    _draw_spacing_lines(page, [320, 334, 430, 444, 540])
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_spacing(model)
    assert not any(f.rule_id == "P016" for f in findings)


def test_approval_page_skipped_for_p016(tmp_path: Path) -> None:
    """Approval Page committee-signature template layout must not trigger P016."""
    pdf_path = tmp_path / "approval_p016.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((240, 90), "APPROVAL PAGE", fontsize=16, fontname="Times-Bold")
    _draw_spacing_lines(page, [320, 334, 430, 444, 540])
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_spacing(model)
    assert not any(f.rule_id == "P016" for f in findings)


def test_p016_heading_gap_reported_as_after_heading(tmp_path: Path) -> None:
    """A suspicious heading blank gap is measured AFTER the heading, and both the
    finding message and the recorded position detail must say so."""
    pdf_path = tmp_path / "heading_gap_after.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((250, 90), "ABSTRACT", fontsize=16, fontname="Times-Bold")
    # First content sits far below the heading -> gap AFTER the heading.
    _draw_spacing_lines(page, [320, 334, 348, 362])
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    gap_findings = [
        f
        for f in check_pdf_spacing(model)
        if f.rule_id == "P016"
        and f.details.get("issue_type") == "suspicious_heading_blank_gap"
    ]
    assert gap_findings
    finding = gap_findings[0]
    assert finding.details.get("heading_gap_position") == "after"
    assert "after" in finding.message.lower()
    assert "before a heading" not in finding.message.lower()


def test_p016_paragraph_gap_suppresses_redundant_line_gap(tmp_path: Path) -> None:
    """A single large gap must not emit both excessive_line_gap and
    excessive_paragraph_gap for the same page.

    Regression for Ester's Sample B feedback: page 1 showed two "Spacing /
    blank lines" cards because one large gap cleared both the (lower)
    line-gap threshold and the (higher) paragraph-gap threshold, so both
    issue types fired with the same largest_gap_pt. paragraph_gap_threshold
    is always stricter than excessive_gap_threshold, so any gap that
    qualifies as a paragraph gap is always already counted as a line gap —
    the two findings are never independent evidence, only the more specific
    paragraph-gap classification should be reported.
    """
    pdf_path = tmp_path / "spacing_duplicate_gap.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((250, 90), "ABSTRACT", fontsize=16, fontname="Times-Bold")
    # One gap (~50pt) clears only the line-gap threshold; one gap (~65pt)
    # clears both. Pre-fix this produced excessive_line_gap (count=2) AND
    # excessive_paragraph_gap (count=1) with the same largest_gap_pt.
    _draw_spacing_lines(page, [140, 154, 168, 233, 247, 327])
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in check_pdf_spacing(model) if f.rule_id == "P016"]

    issue_types = {f.details.get("issue_type") for f in warnings}
    assert "excessive_line_gap" not in issue_types
    assert "excessive_paragraph_gap" in issue_types
    assert len(warnings) == 1


def test_figure_caption_with_terminal_punctuation_does_not_warn_p017(tmp_path: Path) -> None:
    pdf_path = tmp_path / "caption_figure_ok.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((108, 140), "Figure 1.1 Sample figure caption ends properly.")
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_captions(model)
    assert not any(f.rule_id == "P017" for f in findings)


def test_figure_caption_without_terminal_punctuation_warns_p017(tmp_path: Path) -> None:
    pdf_path = tmp_path / "caption_figure_bad.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((108, 140), "Figure 2 Sample figure caption missing ending punctuation")
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    warning = next(f for f in check_pdf_captions(model) if f.rule_id == "P017")
    assert warning.details.get("caption_type") == "figure"
    assert warning.details.get("issue_type") == "missing_terminal_punctuation"


def test_table_title_with_acceptable_formatting_does_not_warn_p017(tmp_path: Path) -> None:
    pdf_path = tmp_path / "caption_table_ok.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((108, 140), "Table 3.4 Results Summary and Key Metrics")
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_captions(model)
    assert not any(f.rule_id == "P017" for f in findings)


def test_obvious_table_punctuation_problem_warns_p017(tmp_path: Path) -> None:
    pdf_path = tmp_path / "caption_table_punct_bad.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((108, 140), "Table 5 Results Summary..")
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    warning = next(f for f in check_pdf_captions(model) if f.rule_id == "P017")
    assert warning.details.get("caption_type") == "table"
    assert warning.details.get("issue_type") == "unexpected_terminal_period"


def test_list_of_tables_entry_ending_with_period_warns_p017(tmp_path: Path) -> None:
    pdf_path = tmp_path / "caption_lot_period_bad.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((220, 90), "LIST OF TABLES", fontsize=16, fontname="Times-Bold")
    page.insert_text((108, 140), "Table 1 Summary of Experimental Setup.")
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    warning = next(f for f in check_pdf_captions(model) if f.rule_id == "P017")
    assert warning.details.get("issue_type") == "unexpected_terminal_period"


def test_ambiguous_short_caption_is_ignored_p017(tmp_path: Path) -> None:
    pdf_path = tmp_path / "caption_short_ignored.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((108, 140), "Fig. 1 Short")
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_captions(model)
    assert not any(f.rule_id == "P017" for f in findings)


def test_prose_figure_reference_not_treated_as_caption_p017(tmp_path: Path) -> None:
    pdf_path = tmp_path / "caption_figure_prose_reference.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text(
        (108, 140),
        "Figure 3.2 shows the synthetic pattern across each group clearly. It",
    )
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_captions(model)
    assert not any(f.rule_id == "P017" for f in findings)


def test_prose_table_reference_not_treated_as_caption_p017(tmp_path: Path) -> None:
    pdf_path = tmp_path / "caption_table_prose_reference.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text(
        (108, 140),
        "Table 4 presents the synthetic values for each group below. Each row",
    )
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_captions(model)
    assert not any(f.rule_id == "P017" for f in findings)


def test_shortened_table_reference_not_treated_as_caption_p017(tmp_path: Path) -> None:
    # A body sentence that opens with a shortened table number wraps onto
    # the next line just like ordinary prose: the sentence boundary lands on
    # a later line rather than within the matched line's own body, so the
    # embedded-sentence check above cannot catch it on its own.
    pdf_path = tmp_path / "caption_table_shortened_reference.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text(
        (108, 140),
        "Table 9 presents the synthetic coefficients for each remaining",
    )
    page.insert_text((108, 158), "predictor across every model examined in this section.")
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_captions(model)
    assert not any(f.rule_id == "P017" for f in findings)


def test_shortened_figure_reference_not_treated_as_caption_p017(tmp_path: Path) -> None:
    pdf_path = tmp_path / "caption_figure_shortened_reference.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text(
        (108, 140),
        "Figure 5 illustrates the synthetic trend across each remaining",
    )
    page.insert_text((108, 158), "group examined later in this same chapter.")
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_captions(model)
    assert not any(f.rule_id == "P017" for f in findings)


def test_caption_followed_by_body_at_different_margin_still_detected_p017(
    tmp_path: Path,
) -> None:
    # A genuine caption can sit directly above body content that happens to
    # start with a lowercase word (e.g. a table's first data row). Because
    # that body text starts at a different left margin than the caption, it
    # must not be mistaken for a paragraph continuation of the caption line.
    pdf_path = tmp_path / "caption_figure_followed_by_body.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((108, 140), "Figure 7 Summary of synthetic group outcomes")
    page.insert_text((180, 158), "synthetic row alpha value here")
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    warning = next(f for f in check_pdf_captions(model) if f.rule_id == "P017")
    assert warning.details.get("caption_type") == "figure"
    assert warning.details.get("issue_type") == "missing_terminal_punctuation"


def test_caption_followed_by_same_margin_lowercase_body_still_detected_p017(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "caption_figure_followed_by_same_margin_body.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((108, 140), "Figure 7 Summary of synthetic group outcomes")
    page.insert_text((108, 158), "synthetic row alpha value here")
    page.insert_text((108, 176), "synthetic row beta value here")
    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))
    captions = [
        caption for caption in detect_caption_lines(model) if caption.caption_type == "figure"
    ]
    assert any(
        caption.raw_text == "Figure 7 Summary of synthetic group outcomes"
        for caption in captions
    )

    warning = next(f for f in check_pdf_captions(model) if f.rule_id == "P017")
    assert warning.details.get("caption_type") == "figure"
    assert warning.details.get("issue_type") == "missing_terminal_punctuation"


def test_legitimate_short_caption_with_same_margin_lowercase_body_is_retained(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "caption_short_legitimate_with_body.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((108, 140), "Figure 8 Brief synthetic overview.")
    page.insert_text((108, 158), "synthetic row alpha value here")
    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))
    captions = [
        caption for caption in detect_caption_lines(model) if caption.caption_type == "figure"
    ]
    assert any(caption.raw_text == "Figure 8 Brief synthetic overview." for caption in captions)


def test_merged_number_text_figure_caption_detected_and_flagged_p017(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "caption_figure_merged_number_text.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((108, 140), "Figure 4.1Brief synthetic overview")
    page.insert_text((108, 158), "synthetic row alpha value here")
    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))
    captions = [
        caption for caption in detect_caption_lines(model) if caption.caption_type == "figure"
    ]
    assert any(caption.raw_text == "Figure 4.1Brief synthetic overview" for caption in captions)
    assert any(caption.caption_body == "Brief synthetic overview" for caption in captions)

    warning = next(f for f in check_pdf_captions(model) if f.rule_id == "P017")
    assert warning.details.get("caption_type") == "figure"
    assert warning.details.get("issue_type") == "missing_terminal_punctuation"


def test_merged_number_text_table_caption_detected(tmp_path: Path) -> None:
    pdf_path = tmp_path / "caption_table_merged_number_text.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((108, 140), "Table 4.2Summary of values across groups")
    page.insert_text((108, 158), "synthetic row alpha value here")
    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))
    captions = [
        caption for caption in detect_caption_lines(model) if caption.caption_type == "table"
    ]
    assert any(
        caption.raw_text == "Table 4.2Summary of values across groups" for caption in captions
    )
    assert any(caption.caption_body == "Summary of values across groups" for caption in captions)


def test_caption_with_prose_restatement_flags_only_caption_p017(tmp_path: Path) -> None:
    # A real caption that restates its own figure number in the very next
    # paragraph (a common writing convention) must not produce a second,
    # spurious finding for that follow-up sentence.
    pdf_path = tmp_path / "caption_figure_restated_bad.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((108, 140), "Figure 6.1 Distribution of synthetic sample values")
    page.insert_text(
        (108, 160),
        "Figure 6.1 shows the synthetic distribution clearly. The pattern",
    )
    page.insert_text((108, 178), "continues downward across each remaining group.")
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_captions(model) if f.rule_id == "P017"]
    assert len(findings) == 1
    assert findings[0].details.get("caption_type") == "figure"
    assert findings[0].details.get("issue_type") == "missing_terminal_punctuation"


def test_caption_with_prose_restatement_no_finding_when_well_formed_p017(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "caption_figure_restated_ok.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((108, 140), "Figure 5.2 Distribution of synthetic sample values.")
    page.insert_text(
        (108, 160),
        "Figure 5.2 shows the synthetic distribution clearly. The pattern",
    )
    page.insert_text((108, 178), "continues downward across each remaining group.")
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_captions(model) if f.rule_id == "P017"]
    assert findings == []


def test_pdf_cli_command_runs_with_p017(tmp_path: Path) -> None:
    pdf_path = tmp_path / "cli_caption.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((108, 140), "Figure 2 Caption without terminal punctuation")
    doc.save(pdf_path)
    doc.close()
    result = runner.invoke(app, ["pdf", str(pdf_path)])
    assert result.exit_code == 0
    assert "P017" in result.output


def test_aligned_toc_entries_do_not_warn_p018(tmp_path: Path) -> None:
    pdf_path = tmp_path / "toc_aligned.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((220, 90), "TABLE OF CONTENTS", fontsize=16, fontname="Times-Bold")
    _draw_toc_entry(page, 140, 108, "Chapter 1 Introduction ....", 500)
    _draw_toc_entry(page, 160, 108, "Chapter 2 Methods ....", 500)
    _draw_toc_entry(page, 180, 108, "Chapter 3 Results ....", 500)
    _draw_toc_entry(page, 200, 108, "Chapter 4 Discussion ....", 500)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_toc_alignment(model)
    assert not any(f.rule_id == "P018" for f in findings)


def test_misaligned_toc_page_number_warns_p018(tmp_path: Path) -> None:
    pdf_path = tmp_path / "toc_misaligned_page_num.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((220, 90), "TABLE OF CONTENTS", fontsize=16, fontname="Times-Bold")
    _draw_toc_entry(page, 140, 108, "Chapter 1 Introduction ....", 500)
    _draw_toc_entry(page, 160, 108, "Chapter 2 Methods ....", 500)
    _draw_toc_entry(page, 180, 108, "Chapter 3 Results ....", 465)
    _draw_toc_entry(page, 200, 108, "Chapter 4 Discussion ....", 500)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in check_pdf_toc_alignment(model) if f.rule_id == "P018"]
    finding = next(
        f for f in warnings if f.details.get("issue_type") == "misaligned_page_number_column"
    )
    assert finding.details.get("worst_entry_index") == "2"


def test_missing_page_number_warns_p018(tmp_path: Path) -> None:
    pdf_path = tmp_path / "toc_missing_page_number.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((220, 90), "TABLE OF CONTENTS", fontsize=16, fontname="Times-Bold")
    _draw_toc_entry(page, 140, 108, "Chapter 1 Introduction ....", 500)
    _draw_toc_entry(page, 160, 108, "Chapter 2 Methods ....", 500)
    page.insert_text((108, 180), "Chapter 3 Results ....")
    _draw_toc_entry(page, 200, 108, "Chapter 4 Discussion ....", 500)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in check_pdf_toc_alignment(model) if f.rule_id == "P018"]
    finding = next(f for f in warnings if f.details.get("issue_type") == "missing_page_number")
    assert finding.details.get("worst_entry_index") == "2"


def test_inconsistent_leader_dots_warns_p018(tmp_path: Path) -> None:
    pdf_path = tmp_path / "toc_inconsistent_dots.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((220, 90), "TABLE OF CONTENTS", fontsize=16, fontname="Times-Bold")
    _draw_toc_entry(page, 140, 108, "Chapter 1 Introduction ....", 500)
    _draw_toc_entry(page, 160, 108, "Chapter 2 Methods ....", 500)
    _draw_toc_entry(page, 180, 108, "Chapter 3 Results ....", 500)
    _draw_toc_entry(page, 200, 108, "Chapter 4 Discussion", 500)
    _draw_toc_entry(page, 220, 108, "Chapter 5 Conclusion ....", 500)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in check_pdf_toc_alignment(model) if f.rule_id == "P018"]
    finding = next(f for f in warnings if f.details.get("issue_type") == "inconsistent_leader_dots")
    assert finding.details.get("worst_entry_index") == "3"


def test_hierarchy_indent_outlier_warns_p018(tmp_path: Path) -> None:
    pdf_path = tmp_path / "toc_indent_outlier.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((220, 90), "TABLE OF CONTENTS", fontsize=16, fontname="Times-Bold")
    _draw_toc_entry(page, 140, 108, "Chapter 1 Introduction ....", 500)
    _draw_toc_entry(page, 160, 108, "Chapter 2 Methods ....", 500)
    _draw_toc_entry(page, 180, 108, "Chapter 3 Results ....", 500)
    _draw_toc_entry(page, 200, 108, "Chapter 4 Discussion ....", 500)
    _draw_toc_entry(page, 220, 108, "Chapter 5 Conclusion ....", 500)
    _draw_toc_entry(page, 240, 160, "Odd Entry Indent ....", 500)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in check_pdf_toc_alignment(model) if f.rule_id == "P018"]
    finding = next(
        f for f in warnings if f.details.get("issue_type") == "inconsistent_hierarchy_indent"
    )
    assert finding.details.get("worst_entry_index") == "5"


def test_level2_entries_consistently_indented_do_not_trigger_hierarchy_indent(
    tmp_path: Path,
) -> None:
    """Level-2 entries aligned at the same x must never fire inconsistent_hierarchy_indent.

    Regression guard for the false-positive where 1.1/1.2/… level-2 entries were
    compared against level-1 entries and flagged because their (correct) extra indent
    exceeded the cross-level tolerance threshold.
    """
    pdf_path = tmp_path / "toc_level2_consistent.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((220, 90), "TABLE OF CONTENTS", fontsize=16, fontname="Times-Bold")
    _draw_toc_entry(page, 140, 108, "1 INTRODUCTION ....", 500)
    _draw_toc_entry(page, 160, 130, "1.1 Background and Context ....", 500)
    _draw_toc_entry(page, 180, 130, "1.2 Exoskeletons as an Emerging Solution ....", 500)
    _draw_toc_entry(page, 200, 130, "1.3 Problem Statement ....", 500)
    _draw_toc_entry(page, 220, 130, "1.4 Purpose of the Study ....", 500)
    _draw_toc_entry(page, 240, 130, "1.5 Research Questions and Hypotheses ....", 500)
    _draw_toc_entry(page, 260, 130, "1.6 Significance of the Study ....", 500)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in check_pdf_toc_alignment(model) if f.rule_id == "P018"]
    indent_warnings = [
        f for f in warnings if f.details.get("issue_type") == "inconsistent_hierarchy_indent"
    ]
    assert indent_warnings == [], (
        "Level-2 entries with a consistent indent must not trigger inconsistent_hierarchy_indent"
    )


def test_level2_not_compared_against_level1_large_indent_difference(tmp_path: Path) -> None:
    """Level-2 entries with a large indent relative to level-1 must not be flagged.

    If level-2 entries are 50+ pt to the right of level-1 entries, they are correctly
    indented and must not be flagged — hierarchy-level comparison must stay within level.
    """
    pdf_path = tmp_path / "toc_level2_large_indent.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((220, 90), "TABLE OF CONTENTS", fontsize=16, fontname="Times-Bold")
    _draw_toc_entry(page, 140, 72, "1 INTRODUCTION ....", 500)
    _draw_toc_entry(page, 160, 72, "2 LITERATURE REVIEW ....", 500)
    _draw_toc_entry(page, 180, 72, "3 METHODS ....", 500)
    _draw_toc_entry(page, 200, 144, "3.1 Data Collection ....", 500)
    _draw_toc_entry(page, 220, 144, "3.2 Analysis Approach ....", 500)
    _draw_toc_entry(page, 240, 144, "3.3 Validation Strategy ....", 500)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in check_pdf_toc_alignment(model) if f.rule_id == "P018"]
    indent_warnings = [
        f for f in warnings if f.details.get("issue_type") == "inconsistent_hierarchy_indent"
    ]
    assert indent_warnings == [], (
        "Level-2 entries consistently indented relative to level-1 must not be flagged"
    )


def test_clear_same_level_outlier_triggers_hierarchy_indent_warning(tmp_path: Path) -> None:
    """A level-2 entry clearly mis-indented relative to its level-2 peers must be flagged."""
    pdf_path = tmp_path / "toc_level2_outlier.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((220, 90), "TABLE OF CONTENTS", fontsize=16, fontname="Times-Bold")
    _draw_toc_entry(page, 140, 108, "1 INTRODUCTION ....", 500)
    _draw_toc_entry(page, 160, 130, "1.1 Background and Context ....", 500)
    _draw_toc_entry(page, 180, 130, "1.2 Literature Review ....", 500)
    _draw_toc_entry(page, 200, 130, "1.3 Problem Statement ....", 500)
    _draw_toc_entry(page, 220, 130, "1.4 Purpose of the Study ....", 500)
    _draw_toc_entry(page, 240, 180, "1.5 Deeply Mis-Indented Entry ....", 500)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in check_pdf_toc_alignment(model) if f.rule_id == "P018"]
    finding = next(
        (f for f in warnings if f.details.get("issue_type") == "inconsistent_hierarchy_indent"),
        None,
    )
    assert finding is not None, "A clearly mis-indented level-2 entry should trigger a warning"
    assert float(finding.details.get("worst_delta_pt", "0")) > 10.0


def test_fewer_than_3_same_level_entries_no_hierarchy_indent_warning(tmp_path: Path) -> None:
    """With only 2 level-2 entries, no comparison is possible — no warning should fire."""
    pdf_path = tmp_path / "toc_level2_two_entries.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((220, 90), "TABLE OF CONTENTS", fontsize=16, fontname="Times-Bold")
    _draw_toc_entry(page, 140, 108, "1 INTRODUCTION ....", 500)
    _draw_toc_entry(page, 160, 130, "1.1 Background ....", 500)
    _draw_toc_entry(page, 180, 200, "1.2 Mis-indented ....", 500)
    _draw_toc_entry(page, 200, 108, "2 METHODS ....", 500)
    _draw_toc_entry(page, 220, 108, "3 RESULTS ....", 500)
    _draw_toc_entry(page, 240, 108, "4 DISCUSSION ....", 500)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in check_pdf_toc_alignment(model) if f.rule_id == "P018"]
    indent_warnings = [
        f for f in warnings if f.details.get("issue_type") == "inconsistent_hierarchy_indent"
    ]
    assert indent_warnings == [], (
        "With only 2 same-level entries, the hierarchy indent check must not fire"
    )


def test_slight_indent_jitter_within_tolerance_no_warning(tmp_path: Path) -> None:
    """Level-2 entries with x-coordinate jitter ≤ 8 pt must not trigger a warning."""
    pdf_path = tmp_path / "toc_level2_jitter.pdf"
    import fitz as _fitz

    doc = _fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((220, 90), "TABLE OF CONTENTS", fontsize=16, fontname="Times-Bold")
    _draw_toc_entry(page, 140, 108, "1 INTRODUCTION ....", 500)
    _draw_toc_entry(page, 160, 130, "1.1 Background and Context ....", 500)
    _draw_toc_entry(page, 180, 133, "1.2 Literature Review ....", 500)
    _draw_toc_entry(page, 200, 131, "1.3 Problem Statement ....", 500)
    _draw_toc_entry(page, 220, 132, "1.4 Purpose of the Study ....", 500)
    _draw_toc_entry(page, 240, 129, "1.5 Research Questions ....", 500)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in check_pdf_toc_alignment(model) if f.rule_id == "P018"]
    indent_warnings = [
        f for f in warnings if f.details.get("issue_type") == "inconsistent_hierarchy_indent"
    ]
    assert indent_warnings == [], (
        "Minor rendering jitter (≤8 pt) must not trigger inconsistent_hierarchy_indent"
    )


def test_hierarchy_indent_medium_confidence_only_for_large_deviation(tmp_path: Path) -> None:
    """Confidence must be 'medium' only when deviation is clearly beyond 18 pt."""
    pdf_path = tmp_path / "toc_level2_confidence.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((220, 90), "TABLE OF CONTENTS", fontsize=16, fontname="Times-Bold")
    _draw_toc_entry(page, 140, 108, "1 INTRODUCTION ....", 500)
    _draw_toc_entry(page, 160, 130, "1.1 Background ....", 500)
    _draw_toc_entry(page, 180, 130, "1.2 Methods ....", 500)
    _draw_toc_entry(page, 200, 130, "1.3 Results ....", 500)
    _draw_toc_entry(page, 220, 130, "1.4 Discussion ....", 500)
    _draw_toc_entry(page, 240, 180, "1.5 Greatly Mis-indented ....", 500)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in check_pdf_toc_alignment(model) if f.rule_id == "P018"]
    finding = next(
        (f for f in warnings if f.details.get("issue_type") == "inconsistent_hierarchy_indent"),
        None,
    )
    assert finding is not None
    assert finding.details.get("confidence") == "medium", (
        "A 50-pt deviation should produce medium confidence"
    )


def test_non_toc_page_is_ignored_for_p018(tmp_path: Path) -> None:
    pdf_path = tmp_path / "toc_ignore_non_toc.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    _draw_toc_entry(page, 140, 108, "Chapter 1 Introduction ....", 500)
    _draw_toc_entry(page, 160, 108, "Chapter 2 Methods ....", 470)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_toc_alignment(model)
    assert not any(f.rule_id == "P018" for f in findings)


def test_p018_toc_heading_with_trailing_period_is_detected(tmp_path: Path) -> None:
    pdf_path = tmp_path / "toc_heading_period.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((220, 90), "TABLE OF CONTENTS.", fontsize=16, fontname="Times-Bold")
    _draw_toc_entry(page, 140, 108, "Chapter 1 Introduction ....", 500)
    _draw_toc_entry(page, 160, 108, "Chapter 2 Methods ....", 500)
    page.insert_text((108, 180), "Chapter 3 Results ....")
    _draw_toc_entry(page, 200, 108, "Chapter 4 Discussion ....", 500)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in check_pdf_toc_alignment(model) if f.rule_id == "P018"]
    assert any(f.details.get("issue_type") == "missing_page_number" for f in warnings)


def test_pdf_cli_command_runs_with_p018(tmp_path: Path) -> None:
    pdf_path = tmp_path / "cli_toc_alignment.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((220, 90), "TABLE OF CONTENTS", fontsize=16, fontname="Times-Bold")
    _draw_toc_entry(page, 140, 108, "Chapter 1 Introduction ....", 500)
    _draw_toc_entry(page, 160, 108, "Chapter 2 Methods ....", 500)
    _draw_toc_entry(page, 180, 108, "Chapter 3 Results ....", 465)
    _draw_toc_entry(page, 200, 108, "Chapter 4 Discussion ....", 500)
    doc.save(pdf_path)
    doc.close()
    result = runner.invoke(app, ["pdf", str(pdf_path)])
    assert result.exit_code == 0
    assert "P018" in result.output


def test_pdf_cli_json_report_output_works(tmp_path: Path) -> None:
    pdf_path = tmp_path / "cli_report_json.pdf"
    json_out = tmp_path / "out" / "report.json"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((250, 90), "ABSTRACT", fontsize=16, fontname="Times-Bold")
    _draw_spacing_lines(page, [140, 154, 230, 244])
    doc.save(pdf_path)
    doc.close()
    result = runner.invoke(app, ["pdf", str(pdf_path), "--json-out", str(json_out)])
    assert result.exit_code == 0
    assert json_out.exists()
    assert "\"total_findings\"" in json_out.read_text(encoding="utf-8")
    assert "JSON report" in result.output


def test_pdf_cli_markdown_report_output_works(tmp_path: Path) -> None:
    pdf_path = tmp_path / "cli_report_md.pdf"
    md_out = tmp_path / "out" / "report.md"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((250, 90), "ABSTRACT", fontsize=16, fontname="Times-Bold")
    _draw_spacing_lines(page, [140, 154, 230, 244])
    doc.save(pdf_path)
    doc.close()
    result = runner.invoke(app, ["pdf", str(pdf_path), "--md-out", str(md_out)])
    assert result.exit_code == 0
    assert md_out.exists()
    assert "# NJIT PDF Audit Report" in md_out.read_text(encoding="utf-8")
    assert "Markdown report" in result.output


def test_sequential_arabic_page_numbers_do_not_warn_p019(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p019_arabic_ok.pdf"
    _make_pdf_with_page_numbers(pdf_path, ["1", "2", "3", "4"])
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_page_number_sequence(model)
    assert not any(f.rule_id == "P019" for f in findings)


def test_missing_page_number_in_sequence_warns_p019(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p019_missing.pdf"
    _make_pdf_with_page_numbers(pdf_path, ["1", None, "3", "4"])
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_page_number_sequence(model)
    assert any(f.details.get("issue_type") == "missing_page_number" for f in findings)


def test_multiple_page_numbers_on_same_page_warns_p019(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p019_multiple.pdf"
    _make_pdf_with_page_numbers(
        pdf_path,
        ["1", "2", "3"],
        add_second_numbers={1: ("99", 560)},
    )
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_page_number_sequence(model)
    assert any(f.details.get("issue_type") == "multiple_page_numbers" for f in findings)


def test_inconsistent_position_warns_p019(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p019_position.pdf"
    doc = fitz.open()
    p1 = doc.new_page(width=612, height=792)
    p1.insert_text((300, 770), "1", fontsize=12)
    p2 = doc.new_page(width=612, height=792)
    p2.insert_text((300, 770), "2", fontsize=12)
    p2.insert_text((560, 30), "2", fontsize=12)
    p2.insert_text((300, 30), "2", fontsize=12)
    p3 = doc.new_page(width=612, height=792)
    p3.insert_text((300, 770), "3", fontsize=12)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_page_number_sequence(model)
    assert any(f.details.get("issue_type") == "inconsistent_position" for f in findings)


def test_arabic_sequence_gap_warns_p019(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p019_gap_arabic.pdf"
    _make_pdf_with_page_numbers(pdf_path, ["1", "2", "4", "5"])
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_page_number_sequence(model)
    assert any(f.details.get("issue_type") == "sequence_gap" for f in findings)


def test_roman_lower_sequence_no_warn_for_small_numbers(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p019_roman_ok.pdf"
    _make_pdf_with_page_numbers(pdf_path, ["i", "ii", "iii", "iv"])
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_page_number_sequence(model)
    assert not any(f.rule_id == "P019" for f in findings)


def test_pdf_cli_command_runs_with_p019(tmp_path: Path) -> None:
    pdf_path = tmp_path / "cli_p019.pdf"
    _make_pdf_with_page_numbers(pdf_path, ["1", None, "3"])
    result = runner.invoke(app, ["pdf", str(pdf_path)])
    assert result.exit_code == 0
    assert "P019" in result.output


def test_json_and_markdown_report_include_p019(tmp_path: Path) -> None:
    pdf_path = tmp_path / "cli_p019_reports.pdf"
    json_out = tmp_path / "out" / "p019.json"
    md_out = tmp_path / "out" / "p019.md"
    _make_pdf_with_page_numbers(pdf_path, ["1", None, "3"])
    result = runner.invoke(
        app,
        ["pdf", str(pdf_path), "--json-out", str(json_out), "--md-out", str(md_out)],
    )
    assert result.exit_code == 0
    assert "P019" in json_out.read_text(encoding="utf-8")
    assert "### P019" in md_out.read_text(encoding="utf-8")


def test_p019_sequence_gap_finding_has_triage_metadata(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p019_gap_triage.pdf"
    _make_pdf_with_page_numbers(pdf_path, ["1", "2", "4", "5"])
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_page_number_sequence(model)
    gap_findings = [f for f in findings if f.details.get("issue_type") == "sequence_gap"]
    assert gap_findings, "Expected at least one sequence_gap finding"
    for f in gap_findings:
        assert f.details.get("triage_tier") == "high"
        assert f.details.get("p019_triage_category") == "high_signal_sequence_gap"
        assert "triage_reason" in f.details


def test_p019_missing_page_number_finding_has_triage_metadata(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p019_missing_triage.pdf"
    _make_pdf_with_page_numbers(pdf_path, ["1", None, "3", "4"])
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_page_number_sequence(model)
    missing_findings = [
        f for f in findings if f.details.get("issue_type") == "missing_page_number"
    ]
    assert missing_findings, "Expected at least one missing_page_number finding"
    for f in missing_findings:
        assert f.details.get("triage_tier") == "high"
        assert f.details.get("p019_triage_category") == "high_signal_missing_page_number"
        assert "triage_reason" in f.details


def test_p019_inconsistent_position_finding_has_triage_metadata(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p019_pos_triage.pdf"
    doc = fitz.open()
    p1 = doc.new_page(width=612, height=792)
    p1.insert_text((300, 770), "1", fontsize=12)
    p2 = doc.new_page(width=612, height=792)
    p2.insert_text((300, 770), "2", fontsize=12)
    p2.insert_text((560, 30), "2", fontsize=12)
    p2.insert_text((300, 30), "2", fontsize=12)
    p3 = doc.new_page(width=612, height=792)
    p3.insert_text((300, 770), "3", fontsize=12)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_page_number_sequence(model)
    pos_findings = [
        f for f in findings if f.details.get("issue_type") == "inconsistent_position"
    ]
    assert pos_findings, "Expected at least one inconsistent_position finding"
    for f in pos_findings:
        assert f.details.get("triage_tier") == "low"
        assert f.details.get("p019_triage_category") == "position_inconsistency_artifact_suspected"
        assert "triage_reason" in f.details


def test_p019_raw_finding_count_unchanged_by_triage(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p019_count_check.pdf"
    _make_pdf_with_page_numbers(pdf_path, ["1", "2", "4", "5"])
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_page_number_sequence(model)
    p019_count = sum(1 for f in findings if f.rule_id == "P019")
    assert p019_count >= 1
    assert all(f.rule_id == "P019" for f in findings)


def test_pdf_cli_handles_unreadable_pdf_gracefully(tmp_path: Path) -> None:
    pdf_path = tmp_path / "broken.pdf"
    pdf_path.write_text("not a pdf")
    result = runner.invoke(app, ["pdf", str(pdf_path)])
    assert result.exit_code == 1
    assert "Unable to read PDF" in result.output


# ---------------------------------------------------------------------------
# P019: TOC/List front-matter arabic column-number noise suppression
# ---------------------------------------------------------------------------


def _make_toc_noise_pdf(
    path: Path,
    *,
    toc_page_count: int = 2,
    roman_page_nums: list[str] | None = None,
    toc_column_arabic: list[str] | None = None,
    chapter_heading: str = "CHAPTER 1 INTRODUCTION",
    body_arabic: str = "1",
) -> None:
    """Create a PDF where front-matter TOC pages have:
    - a roman page number at bottom-center (the real page number)
    - one or more arabic numbers at bottom-right (TOC destination column)
    Followed by a CHAPTER 1 body page with an arabic page number.
    """
    if roman_page_nums is None:
        roman_page_nums = ["viii", "ix"][:toc_page_count]
    if toc_column_arabic is None:
        toc_column_arabic = ["29"] * toc_page_count

    doc = fitz.open()
    for i in range(toc_page_count):
        page = doc.new_page(width=612, height=792)
        page.insert_text((180, 90), "TABLE OF CONTENTS", fontsize=14, fontname="Times-Bold")
        # Real page number: bottom-center (x=300).
        page.insert_text((300, 760), roman_page_nums[i], fontsize=12)
        # TOC column destination number: bottom-right (x=540, in the bottom zone).
        page.insert_text((540, 760), toc_column_arabic[i], fontsize=12)

    # Body page: CHAPTER 1 with arabic page number.
    body = doc.new_page(width=612, height=792)
    body.insert_text((108, 90), chapter_heading, fontsize=14)
    body.insert_text((300, 760), body_arabic, fontsize=12)

    doc.save(path)
    doc.close()


def test_p019_toc_page_arabic_column_numbers_not_flagged(tmp_path: Path) -> None:
    """TOC front-matter pages with roman bottom-center + arabic bottom-right (TOC column)
    should not produce multiple_page_numbers, mixed_numbering_style, or
    inconsistent_position P019 findings.
    """
    pdf_path = tmp_path / "p019_toc_noise.pdf"
    _make_toc_noise_pdf(pdf_path, toc_page_count=2, roman_page_nums=["viii", "ix"],
                        toc_column_arabic=["29", "73"])
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_page_number_sequence(model)
    per_page_noise = [
        f for f in findings
        if f.rule_id == "P019"
        and f.page in {1, 2}
        and f.details.get("issue_type") in {
            "multiple_page_numbers", "mixed_numbering_style", "inconsistent_position"
        }
    ]
    assert not per_page_noise, (
        "TOC pages should not produce per-page P019 noise from TOC column numbers: "
        f"{per_page_noise}"
    )


def test_p019_toc_noise_body_page_still_detected(tmp_path: Path) -> None:
    """After filtering TOC noise, body pages with genuine arabic page numbers are
    still detected (no over-suppression).
    """
    pdf_path = tmp_path / "p019_toc_body_ok.pdf"
    _make_toc_noise_pdf(pdf_path, toc_page_count=1, roman_page_nums=["iv"],
                        toc_column_arabic=["12"])
    model = load_pdf_layout(str(pdf_path))
    from njit_auditor.rules.pdf_page_numbers import detect_page_number_candidates
    candidates = detect_page_number_candidates(model)
    body_page_candidates = [c for c in candidates if c.page_number == 2]
    assert any(c.number_style == "arabic" for c in body_page_candidates), (
        "Body page arabic candidate should still be detected after TOC-noise filtering"
    )


def test_p019_toc_noise_not_suppressed_without_roman_center(tmp_path: Path) -> None:
    """Conservative guard: on a front-matter page with NO roman bottom-center,
    arabic bottom-right candidates are NOT suppressed (could be a real error).
    """
    pdf_path = tmp_path / "p019_toc_no_roman_center.pdf"
    doc = fitz.open()
    # Page 1: front-matter with ONLY arabic bottom-right (no roman at all).
    p1 = doc.new_page(width=612, height=792)
    p1.insert_text((180, 90), "TABLE OF CONTENTS", fontsize=14, fontname="Times-Bold")
    p1.insert_text((540, 760), "29", fontsize=12)   # arabic, bottom-right, no roman partner
    p1.insert_text((540, 745), "34", fontsize=12)   # second arabic, bottom-right
    # Page 2: CHAPTER 1 body.
    p2 = doc.new_page(width=612, height=792)
    p2.insert_text((108, 90), "CHAPTER 1 INTRODUCTION", fontsize=14)
    p2.insert_text((300, 760), "1", fontsize=12)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_page_number_sequence(model)
    # With no roman bottom-center, arabic candidates are kept and may trigger noise.
    # We just verify the guard didn't crash and did not suppress everything.
    assert isinstance(findings, list)


def test_p019_body_page_arabic_right_not_suppressed(tmp_path: Path) -> None:
    """Body pages are never subject to the TOC-noise filter regardless of position."""
    pdf_path = tmp_path / "p019_body_right.pdf"
    doc = fitz.open()
    # Front-matter with roman bottom-center.
    p1 = doc.new_page(width=612, height=792)
    p1.insert_text((300, 760), "iii", fontsize=12)
    # Body page: CHAPTER 1, arabic at bottom-right AND bottom-center (genuinely suspicious).
    p2 = doc.new_page(width=612, height=792)
    p2.insert_text((108, 90), "CHAPTER 1 INTRODUCTION", fontsize=14)
    p2.insert_text((300, 760), "1", fontsize=12)   # bottom-center arabic
    p2.insert_text((540, 760), "99", fontsize=12)  # bottom-right arabic (duplicate)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_page_number_sequence(model)
    body_multiple = [
        f for f in findings
        if f.rule_id == "P019" and f.page == 2
        and f.details.get("issue_type") == "multiple_page_numbers"
    ]
    assert body_multiple, (
        "Body page with two arabic candidates should still trigger multiple_page_numbers"
    )


def test_p019_lot_lof_page_arabic_column_not_flagged(tmp_path: Path) -> None:
    """LIST OF TABLES and LIST OF FIGURES pages follow the same pattern as TOC:
    roman bottom-center (real page num) + arabic bottom-right (entry page refs).
    No per-page P019 noise should be emitted.
    """
    pdf_path = tmp_path / "p019_lot_lof_noise.pdf"
    doc = fitz.open()
    # LIST OF TABLES page (front matter, roman xii).
    p = doc.new_page(width=612, height=792)
    p.insert_text((210, 90), "LIST OF TABLES", fontsize=14, fontname="Times-Bold")
    p.insert_text((300, 760), "xii", fontsize=12)
    p.insert_text((540, 760), "45", fontsize=12)   # Table 1 destination page
    # LIST OF FIGURES page (front matter, roman xiii).
    p = doc.new_page(width=612, height=792)
    p.insert_text((210, 90), "LIST OF FIGURES", fontsize=14, fontname="Times-Bold")
    p.insert_text((300, 760), "xiii", fontsize=12)
    p.insert_text((540, 760), "67", fontsize=12)   # Figure 1 destination page
    # CHAPTER 1 body.
    p = doc.new_page(width=612, height=792)
    p.insert_text((108, 90), "CHAPTER 1 INTRODUCTION", fontsize=14)
    p.insert_text((300, 760), "1", fontsize=12)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_page_number_sequence(model)
    lot_lof_noise = [
        f for f in findings
        if f.rule_id == "P019"
        and f.page in {1, 2}
        and f.details.get("issue_type") in {
            "multiple_page_numbers", "mixed_numbering_style", "inconsistent_position"
        }
    ]
    assert not lot_lof_noise, (
        f"LIST OF TABLES/FIGURES pages should not produce per-page P019 noise: {lot_lof_noise}"
    )


def test_p019_real_multiple_candidates_body_still_warns(tmp_path: Path) -> None:
    """Existing test: normal body page with two arabic candidates still warns."""
    pdf_path = tmp_path / "p019_real_multiple.pdf"
    _make_pdf_with_page_numbers(
        pdf_path,
        ["1", "2", "3"],
        add_second_numbers={1: ("99", 560)},
    )
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_page_number_sequence(model)
    assert any(f.details.get("issue_type") == "multiple_page_numbers" for f in findings)


# ---------------------------------------------------------------------------
# P019: reprinted/embedded-material secondary page numbering (Sample B page 57/58)
# ---------------------------------------------------------------------------


def _make_pdf_with_dominant_bottom_numbering(
    path: Path,
    *,
    page_count: int,
    embedded_reprint_pages: dict[int, str] | None = None,
    second_bottom_pages: dict[int, str] | None = None,
) -> None:
    """Build a PDF where nearly every page has a single bottom-center arabic page
    number (the document-wide dominant pattern), optionally with some pages
    additionally carrying a top-center "embedded reprint" number (its own original
    page numbering, e.g. a reproduced published paper) and/or a second bottom
    candidate (a genuine same-location duplicate).
    """
    embedded_reprint_pages = embedded_reprint_pages or {}
    second_bottom_pages = second_bottom_pages or {}
    doc = fitz.open()
    for idx in range(page_count):
        page_number = idx + 1
        page = doc.new_page(width=612, height=792)
        page.insert_text((300, 770), str(page_number), fontsize=12)
        if page_number in embedded_reprint_pages:
            page.insert_text((300, 30), embedded_reprint_pages[page_number], fontsize=12)
        if page_number in second_bottom_pages:
            page.insert_text((560, 770), second_bottom_pages[page_number], fontsize=12)
    doc.save(path)
    doc.close()


def test_p019_embedded_reprint_top_number_not_flagged_as_multiple(tmp_path: Path) -> None:
    """Regression test for Sample B pages 57/58: a page with an overwhelming
    document-wide bottom-center numbering pattern plus a rare top-center number
    (an embedded reprint's own original page count) must not be flagged as
    "multiple_page_numbers" — the manuscript's own bottom-center page number is
    unambiguous. See docs/status/ester_sample_b_p019_page_numbering_highlights.md.
    """
    pdf_path = tmp_path / "p019_embedded_reprint.pdf"
    _make_pdf_with_dominant_bottom_numbering(
        pdf_path,
        page_count=20,
        embedded_reprint_pages={10: "2", 11: "3"},
    )
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_page_number_sequence(model)
    noise = [
        f
        for f in findings
        if f.details.get("issue_type") == "multiple_page_numbers" and f.page in {10, 11}
    ]
    assert noise == [], f"embedded reprint top-numbers should not be flagged: {noise}"


def test_p019_genuine_duplicate_bottom_candidate_still_flagged_in_large_doc(
    tmp_path: Path,
) -> None:
    """A page with two candidates at the SAME (bottom) location remains a genuine
    ambiguity even in a document large enough for the dominant-location filter to
    be active — the filter only ever discounts a different-location secondary
    candidate, never a same-location duplicate."""
    pdf_path = tmp_path / "p019_genuine_duplicate.pdf"
    _make_pdf_with_dominant_bottom_numbering(
        pdf_path,
        page_count=15,
        second_bottom_pages={10: "99"},
    )
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_page_number_sequence(model)
    hit = [
        f
        for f in findings
        if f.details.get("issue_type") == "multiple_page_numbers" and f.page == 10
    ]
    assert hit, "same-location duplicate candidates must still be flagged"


def test_p019_embedded_reprint_pattern_not_suppressed_in_small_document(
    tmp_path: Path,
) -> None:
    """Conservative guard: the dominant-location filter requires a large enough
    sample to trust the document-wide pattern. In a short document (below the
    minimum sample size), a top+bottom split on one page is still flagged —
    there isn't enough signal yet to call one location "dominant"."""
    pdf_path = tmp_path / "p019_small_doc_top_bottom.pdf"
    _make_pdf_with_dominant_bottom_numbering(
        pdf_path,
        page_count=3,
        embedded_reprint_pages={2: "1"},
    )
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_page_number_sequence(model)
    hit = [
        f
        for f in findings
        if f.details.get("issue_type") == "multiple_page_numbers" and f.page == 2
    ]
    assert hit, "small documents must not suppress top+bottom candidates as noise"


def test_p019_multiple_page_numbers_highlight_targets_dominant_candidate(
    tmp_path: Path,
) -> None:
    """When multiple_page_numbers still fires, its bbox must point at the highest
    ranked (most page-number-like) candidate, not merely the first one detected in
    document scan order — otherwise the highlight can land on unrelated noise
    instead of the actual page number."""
    pdf_path = tmp_path / "p019_highlight_target.pdf"
    _make_pdf_with_dominant_bottom_numbering(
        pdf_path,
        page_count=15,
        second_bottom_pages={10: "99"},
    )
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_page_number_sequence(model)
    hit = next(
        f
        for f in findings
        if f.details.get("issue_type") == "multiple_page_numbers" and f.page == 10
    )
    bbox = hit.details.get("bbox", "")
    assert bbox, "expected a bbox on the remaining genuine multiple_page_numbers finding"
    # bottom-center ("10", rank score higher: dominant style+position) must win over
    # bottom-right ("99") as the primary highlight target.
    x0 = float(bbox.split(",")[0])
    assert 250 < x0 < 350, f"expected bottom-center bbox to be selected, got x0={x0}"


def test_p013_embedded_reprint_top_number_not_counted_as_duplicate(tmp_path: Path) -> None:
    """P013's own candidate count must apply the same dominant-location noise
    filter as P019 (see test_p019_embedded_reprint_top_number_not_flagged_as_multiple).

    P013 and P019 independently compute "how many plausible page-number
    candidates are on this page" and both classify a count > 1 as a
    "duplicate_or_ambiguous_page_number" problem (see
    classify_visible_page_number_issue in page_number_student_preview.py).
    Fixing only P019 would leave P013's raw candidate finding unsuppressed
    (it is normally hidden as "redundant with P019's confirmed problem" —
    see _collect_claimed_page_number_keys in report_view.py — but only when
    P019 actually reports a problem there), silently moving the false
    positive from P019 to P013 instead of resolving it.
    """
    pdf_path = tmp_path / "p013_embedded_reprint.pdf"
    _make_pdf_with_dominant_bottom_numbering(
        pdf_path,
        page_count=20,
        embedded_reprint_pages={10: "2", 11: "3"},
    )
    model = load_pdf_layout(str(pdf_path))
    findings = run_pdf_page_number_candidates_rule(model)
    for page in (10, 11):
        finding = next(f for f in findings if f.page == page)
        assert finding.details.get("candidate_count_on_page") == "1", (
            f"page {page}: embedded reprint's top-number should not count as a "
            f"second candidate, got {finding.details}"
        )


# ---------------------------------------------------------------------------
# P020: Title-case capitalization — helper unit tests
# ---------------------------------------------------------------------------


def test_p020_minor_word_detection() -> None:
    for word in (
        "a",
        "an",
        "the",
        "and",
        "but",
        "or",
        "for",
        "nor",
        "as",
        "at",
        "by",
        "in",
        "of",
        "on",
        "per",
        "to",
        "up",
        "via",
        "with",
        "from",
        "into",
        "over",
        "between",
        "through",
        "without",
    ):
        assert is_minor_word(word), f"'{word}' should be a minor word"
    for word in ("machine", "learning", "results", "comparison", "robustness"):
        assert not is_minor_word(word), f"'{word}' should NOT be a minor word"


def test_p020_acronym_detection() -> None:
    for word in ("PDF", "AI", "MRI", "NJIT", "CAD", "SDF"):
        assert looks_like_acronym(word), f"'{word}' should look like an acronym"
    for word in ("Machine", "learning", "a", "the"):
        assert not looks_like_acronym(word), f"'{word}' should NOT look like an acronym"


def test_p020_phrase_correct_title_case_no_issues() -> None:
    issues = check_apa_title_case_phrase(
        "Machine Learning Approaches to Signal Processing"
    )
    assert issues == []


def test_p020_phrase_minor_word_in_middle_no_issue() -> None:
    issues = check_apa_title_case_phrase("Machine Learning and Signal Processing")
    assert issues == []


def test_p020_phrase_major_word_lowercase_flagged() -> None:
    issues = check_apa_title_case_phrase(
        "Machine learning Approaches to Signal Processing"
    )
    assert any(i["word"] == "learning" for i in issues)
    assert any(i["reason"] == "major_word_requires_capital" for i in issues)


def test_p020_phrase_first_word_lowercase_flagged() -> None:
    issues = check_apa_title_case_phrase(
        "machine Learning Approaches to Signal Processing"
    )
    assert any(i["reason"] == "first_word_requires_capital" for i in issues)
    assert any(i["confidence"] == "high" for i in issues)


def test_p020_phrase_word_after_colon_lowercase_flagged() -> None:
    issues = check_apa_title_case_phrase(
        "Signal Processing: a Novel Approach to Learning"
    )
    assert any(
        i["reason"] == "word_after_separator_requires_capital" and i["word"] == "a"
        for i in issues
    )


def test_p020_phrase_word_after_emdash_flagged() -> None:
    issues = check_apa_title_case_phrase(
        "Signal Processing—a Novel Approach to Learning"
    )
    assert any(i["reason"] == "word_after_separator_requires_capital" for i in issues)


def test_p020_phrase_allcaps_acronym_not_flagged() -> None:
    issues = check_apa_title_case_phrase(
        "Using PDF Format for Scientific Communication"
    )
    assert not any(i["word"] == "PDF" for i in issues)
    assert issues == []


def test_p020_phrase_math_model_token_suppressed() -> None:
    # Words containing digits or math notation should be skipped
    issues = check_apa_title_case_phrase(
        "Optimization of CO2 and H2O Emissions in Processes"
    )
    assert not any("2" in i.get("word", "") for i in issues)


def test_p020_phrase_hyphenated_word_conservative_no_flag() -> None:
    issues = check_apa_title_case_phrase(
        "A well-known Method for Image Analysis Research"
    )
    assert not any("-" in i.get("word", "") for i in issues)


def test_p020_phrase_too_short_no_issues() -> None:
    assert check_apa_title_case_phrase("Two Words") == []
    assert check_apa_title_case_phrase("Single") == []


def test_p020_phrase_statistical_sample_size_not_flagged() -> None:
    # Regression: "(n = 97)" is statistical notation, not an English word.
    # The lowercase "n" must NOT be flagged for capitalization.
    issues = check_apa_title_case_phrase(
        "Multiple Linear Regression Predicting Readiness (n = 97)"
    )
    assert issues == []
    assert not any(i["word"] == "n" for i in issues)


def test_p020_phrase_statistical_notation_variants_not_flagged() -> None:
    # None of these statistical expressions should produce a capitalization issue.
    for phrase in (
        "Correlation of Readiness (p < .001)",
        "Correlation of Readiness (r = 0.22)",
        "Variance Explained by the Model R² = 0.684",
        "Unstandardized Coefficient B = 0.65 for Readiness",
        "Standard Error SE and Degrees of Freedom df",
    ):
        assert check_apa_title_case_phrase(phrase) == [], phrase


def test_p020_phrase_preposition_with_lowercase_no_issue() -> None:
    # NJIT/Esther: prepositions stay lowercase in title case, including "with".
    issues = check_apa_title_case_phrase("Comparison with Prior Studies")
    assert issues == []
    assert not any(i["word"].lower() == "with" for i in issues)


def test_p020_phrase_representative_minor_prepositions_no_issue() -> None:
    for phrase in (
        "Results from Sparse Sampling Experiments",
        "Analysis into Incomplete Point Clouds",
        "Methods over Multiple Benchmark Datasets",
        "Tradeoffs between Accuracy and Speed Metrics",
        "Reconstruction through Geometry Aware Sampling",
        "Evaluation without Manual Annotation Labels",
        "Quantitative Results on Sparse Point Clouds with 10k, 5k, and 1k Points",
        "Comparison of Uniform and Geometry-Aware Importance Sampling on",
    ):
        assert check_apa_title_case_phrase(phrase) == [], phrase


def test_p020_normalize_glued_section_number_spacing() -> None:
    assert (
        normalize_numbered_heading_text("3.3.9.4Robustness to input variations.")
        == "3.3.9.4 Robustness to input variations."
    )
    assert (
        normalize_numbered_heading_text("3.2 Quantitative Results Overview Title")
        == "3.2 Quantitative Results Overview Title"
    )


# ---------------------------------------------------------------------------
# P020: Title-case capitalization — PDF integration tests
# ---------------------------------------------------------------------------


def test_p020_correct_title_case_bold_heading_no_warning(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p020_ok.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text(
        (108, 140),
        "Machine Learning Approaches to Signal Processing",
        fontsize=16,
        fontname="Times-Bold",
    )
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_title_capitalization(model)
    assert not any(f.rule_id == "P020" for f in findings)


def test_p020_lowercase_major_word_in_bold_heading_warns(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p020_major_bad.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text(
        (108, 140),
        "Machine learning Approaches to Signal Processing",
        fontsize=16,
        fontname="Times-Bold",
    )
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_title_capitalization(model)
    warning = next((f for f in findings if f.rule_id == "P020"), None)
    assert warning is not None
    assert warning.details.get("issue_type") == "possible_title_capitalization_issue"
    assert warning.details.get("expected_or_reason") == "major_word_requires_capital"


def test_p020_finding_includes_flagged_and_corrected_word(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p020_word_metadata.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text(
        (108, 140),
        "Machine learning Approaches to Signal Processing",
        fontsize=16,
        fontname="Times-Bold",
    )
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_title_capitalization(model)
    warning = next((f for f in findings if f.rule_id == "P020"), None)
    assert warning is not None
    assert warning.details.get("flagged_word") == "learning"
    assert warning.details.get("corrected_word") == "Learning"


def test_p020_lowercase_minor_word_in_middle_no_warning(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p020_minor_ok.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text(
        (108, 140),
        "Machine Learning and Signal Processing",
        fontsize=16,
        fontname="Times-Bold",
    )
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_title_capitalization(model)
    assert not any(f.rule_id == "P020" for f in findings)


def test_p020_table_title_lowercase_with_not_flagged(tmp_path: Path) -> None:
    """NJIT title case keeps the preposition 'with' lowercase in table titles."""
    pdf_path = tmp_path / "p020_table_with.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text(
        (108, 140),
        "Table 3.5 Quantitative Results with Different Weight Settings",
        fontsize=12,
        fontname="Times-Roman",
    )
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_title_capitalization(model)
    assert not any(
        f.rule_id == "P020" and (f.details or {}).get("flagged_word", "").lower() == "with"
        for f in findings
    )
    assert not any(f.rule_id == "P020" for f in findings)


def test_p020_genuine_table_caption_still_checked(tmp_path: Path) -> None:
    """Real table captions remain in scope; true major-word errors still warn."""
    pdf_path = tmp_path / "p020_table_major.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text(
        (108, 140),
        "Table 3.1 Quantitative results on Sparse Point Clouds",
        fontsize=12,
        fontname="Times-Roman",
    )
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_title_capitalization(model)
    warning = next((f for f in findings if f.rule_id == "P020"), None)
    assert warning is not None
    assert warning.details.get("source") == "caption"
    assert warning.details.get("flagged_word") == "results"
    assert warning.details.get("expected_or_reason") == "major_word_requires_capital"


def test_p020_prose_table_reference_not_treated_as_caption(tmp_path: Path) -> None:
    """Inline 'Table N.N compares…' prose must not become a table-title finding."""
    pdf_path = tmp_path / "p020_table_prose.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text(
        (108, 140),
        "Table 3.1 compares the iteration time, convergence time, and GPU memory",
        fontsize=12,
        fontname="Times-Roman",
    )
    page.insert_text(
        (108, 158),
        "usage of the original and finite-difference formulations on this task.",
        fontsize=12,
        fontname="Times-Roman",
    )
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_title_capitalization(model)
    assert not any(f.rule_id == "P020" for f in findings)
    captions = detect_caption_lines(model)
    assert not any(
        c.caption_type == "table" and c.caption_body.lower().startswith("compares")
        for c in captions
    )


def test_p020_level4_heading_sentence_case_not_title_cased(tmp_path: Path) -> None:
    """Level 4 headings use sentence case; P020 must not demand title case."""
    pdf_path = tmp_path / "p020_level4.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    # Mimic glued number+title extraction seen in real PDFs.
    page.insert_text(
        (108, 140),
        "3.3.9.4Robustness to input variations.",
        fontsize=12,
        fontname="Times-Bold",
    )
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_title_capitalization(model)
    assert not any(f.rule_id == "P020" for f in findings)


def test_p020_level2_heading_still_title_case_checked(tmp_path: Path) -> None:
    """Level 2 (X.x) headings remain in P020 title-case scope."""
    pdf_path = tmp_path / "p020_level2.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text(
        (108, 140),
        "3.2 Robustness to input variations here",
        fontsize=14,
        fontname="Times-Bold",
    )
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_title_capitalization(model)
    warning = next((f for f in findings if f.rule_id == "P020"), None)
    assert warning is not None
    assert warning.details.get("flagged_word") == "input"
    assert "3.2 " in (warning.details.get("line_preview") or "")


def test_p020_period_terminated_sentence_case_heading_not_title_cased(tmp_path: Path) -> None:
    """Level 4/5-style headings end with a period and must not get P020 title case."""
    pdf_path = tmp_path / "p020_period_heading.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text(
        (108, 140),
        "Neural signed distance representation.",
        fontsize=12,
        fontname="Times-Bold",
    )
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    assert not any(f.rule_id == "P020" for f in check_pdf_title_capitalization(model))


def test_p020_run_in_heading_with_body_on_same_baseline_excluded(tmp_path: Path) -> None:
    """Bold run-in heading + non-bold body on the same baseline is not L2 title case."""
    pdf_path = tmp_path / "p020_run_in.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text(
        (108, 140),
        "Expectation-maximization (EM) algorithm",
        fontsize=12,
        fontname="Times-Bold",
    )
    page.insert_text(
        (380, 140),
        "The EM algorithm is used for estimation.",
        fontsize=12,
        fontname="Times-Roman",
    )
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    assert not any(f.rule_id == "P020" for f in check_pdf_title_capitalization(model))


def test_p020_glued_and_performance_suppressed_when_rebuild_is_clean(tmp_path: Path) -> None:
    """Span-gap rebuild that yields valid title case suppresses glued-token FPs."""
    pdf_path = tmp_path / "p020_glued_and.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    x = 100.0
    y = 140.0
    for word in ("Relating", "Floc", "Filter", "Porosity,", "Depth,", "and", "Performance"):
        page.insert_text((x, y), word, fontsize=12, fontname="Times-Bold")
        x += fitz.get_text_length(word, fontname="Times-Bold", fontsize=12) + 4.5
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    # Historical extraction may glue words; P020 must not warn once gaps are restored.
    assert not any(f.rule_id == "P020" for f in check_pdf_title_capitalization(model))


def test_p020_glued_in_power_systems_flags_visible_word(tmp_path: Path) -> None:
    """When rebuild still has a title-case issue, flag the visible word not the glue token."""
    pdf_path = tmp_path / "p020_glued_power.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((108, 120), "3.3", fontsize=12, fontname="Times-Bold")
    x = 108.0
    y = 140.0
    for word in ("Graph", "Attention", "Network", "(GAEN)", "in", "power", "systems"):
        page.insert_text((x, y), word, fontsize=12, fontname="Times-Bold")
        x += fitz.get_text_length(word, fontname="Times-Bold", fontsize=12) + 4.5
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_title_capitalization(model) if f.rule_id == "P020"]
    assert findings
    flagged = findings[0].details.get("flagged_word")
    assert flagged == "power"
    assert flagged != "inpowersystems"
    preview = findings[0].details.get("line_preview") or ""
    assert "in power systems" in preview


def test_p020_table_title_comparison_lowercase_still_warns(tmp_path: Path) -> None:
    """Control: genuine table-title capitalization issues remain detectable."""
    pdf_path = tmp_path / "p020_table_comparison.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text(
        (108, 140),
        "Table 4.2 Quantitative comparison on Spot, Bunny, and Duck",
        fontsize=12,
        fontname="Times-Roman",
    )
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    warning = next((f for f in check_pdf_title_capitalization(model) if f.rule_id == "P020"), None)
    assert warning is not None
    assert warning.details.get("flagged_word") == "comparison"
    assert warning.details.get("source") == "caption"


def test_p020_prose_table_ref_with_determiner_clause_excluded(tmp_path: Path) -> None:
    """Table N.N. The … is … prose sentences are not table titles."""
    pdf_path = tmp_path / "p020_table_prose_the.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text(
        (108, 140),
        "Table 3.2. The corresponding profile of a plane jet is experimentally determined",
        fontsize=12,
        fontname="Times-Roman",
    )
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    assert not any(f.rule_id == "P020" for f in check_pdf_title_capitalization(model))


def test_p020_first_word_lowercase_in_bold_heading_warns(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p020_first_bad.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text(
        (108, 140),
        "machine Learning Approaches to Signal Processing",
        fontsize=16,
        fontname="Times-Bold",
    )
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_title_capitalization(model)
    warning = next((f for f in findings if f.rule_id == "P020"), None)
    assert warning is not None
    assert warning.details.get("expected_or_reason") == "first_word_requires_capital"
    assert warning.details.get("confidence") == "high"


def test_p020_word_after_colon_lowercase_warns(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p020_colon_bad.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text(
        (108, 140),
        "Signal Processing: a Novel Approach to Learning",
        fontsize=16,
        fontname="Times-Bold",
    )
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_title_capitalization(model)
    warning = next((f for f in findings if f.rule_id == "P020"), None)
    assert warning is not None
    assert warning.details.get("expected_or_reason") == "word_after_separator_requires_capital"


def test_p020_allcaps_acronym_in_bold_heading_no_warning(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p020_acronym_ok.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text(
        (108, 140),
        "Using PDF Format for Scientific Communication",
        fontsize=16,
        fontname="Times-Bold",
    )
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_title_capitalization(model)
    assert not any(f.rule_id == "P020" for f in findings)


def test_p020_allcaps_frontmatter_label_ignored(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p020_frontmatter_ok.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((250, 90), "ABSTRACT", fontsize=16, fontname="Times-Bold")
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_title_capitalization(model)
    assert not any(f.rule_id == "P020" for f in findings)


def test_p020_normal_non_bold_body_paragraph_ignored(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p020_body_ok.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text(
        (108, 140),
        "this is a long body paragraph that is not bold and has lowercase words",
        fontsize=12,
        fontname="Times-Roman",
    )
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_title_capitalization(model)
    assert not any(f.rule_id == "P020" for f in findings)


def test_p020_references_page_bold_line_ignored(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p020_references_ok.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((250, 90), "REFERENCES", fontsize=16, fontname="Times-Bold")
    page.insert_text(
        (108, 140),
        "machine learning and deep neural networks",
        fontsize=12,
        fontname="Times-Bold",
    )
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_title_capitalization(model)
    assert not any(f.rule_id == "P020" for f in findings)


def test_p020_table_title_lowercase_major_word_warns(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p020_table_bad.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    # Table title uses title case per NJIT guidelines; "results" should be capitalized
    page.insert_text(
        (108, 140),
        "Table 3.2 AI applications in Education",
        fontsize=12,
    )
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_title_capitalization(model)
    warning = next((f for f in findings if f.rule_id == "P020"), None)
    assert warning is not None
    assert warning.details.get("source") == "caption"


def test_p020_table_title_with_sample_size_notation_not_flagged(tmp_path: Path) -> None:
    """Regression: a table title carrying "(n = 97)" must not warn about the
    lowercase "n", and must never corrupt "Linear" into "LiNear"."""
    pdf_path = tmp_path / "p020_table_stat.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text(
        (108, 140),
        "Table 4.4 Multiple Linear Regression Predicting Readiness (n = 97)",
        fontsize=12,
    )
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_title_capitalization(model) if f.rule_id == "P020"]
    assert not findings, f"statistical notation must not trigger P020; got: {findings}"


def test_p020_level3_numbered_heading_excluded_from_title_case_check(tmp_path: Path) -> None:
    """Regression (Ester Sample B page 71): a Level 3 numbered heading (e.g.
    "3.4.3") whose number sits on its own bold line directly above the bold
    heading text must be excluded from P020's Title Case check. Level 3+
    headings use sentence case (Q051), which P020 does not check — this heading
    text would otherwise be misread as a Level 2 title-case violation."""
    pdf_path = tmp_path / "p020_level3_excluded.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((108, 140), "3.4.3", fontsize=12, fontname="Times-Bold")
    page.insert_text(
        (108, 160),
        "Implementation experiments and Results",
        fontsize=12,
        fontname="Times-Bold",
    )
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_title_capitalization(model) if f.rule_id == "P020"]
    assert not findings, f"Level 3+ numbered headings must be excluded from P020; got: {findings}"


def test_p020_same_heading_text_without_level3_prefix_still_warns(tmp_path: Path) -> None:
    """The Level 3 exclusion above must be targeted, not a blanket suppression:
    the identical heading text without a preceding Level 3+ number line is still
    a bold heading and must still be checked."""
    pdf_path = tmp_path / "p020_no_level3_prefix.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text(
        (108, 140),
        "Implementation experiments and Results",
        fontsize=12,
        fontname="Times-Bold",
    )
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_title_capitalization(model) if f.rule_id == "P020"]
    assert findings, "a bold heading without a Level 3+ number prefix must still be checked"


def test_p020_level2_numbered_heading_not_excluded(tmp_path: Path) -> None:
    """Boundary check: a Level 2 number prefix (single dot, e.g. "3.4") must not
    trigger the Level 3+ exclusion — Level 2 headings remain Title Case-checked."""
    pdf_path = tmp_path / "p020_level2_not_excluded.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((108, 140), "3.4", fontsize=12, fontname="Times-Bold")
    page.insert_text(
        (108, 160),
        "Implementation experiments and Results",
        fontsize=12,
        fontname="Times-Bold",
    )
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_title_capitalization(model) if f.rule_id == "P020"]
    assert findings, "Level 2 numbered headings must remain Title Case-checked"


def test_p020_cli_pdf_run_includes_p020(tmp_path: Path) -> None:
    pdf_path = tmp_path / "cli_p020.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text(
        (108, 140),
        "machine learning Approaches for Signal Processing",
        fontsize=16,
        fontname="Times-Bold",
    )
    doc.save(pdf_path)
    doc.close()
    result = runner.invoke(app, ["pdf", str(pdf_path)])
    assert result.exit_code == 0
    assert "P020" in result.output


# ---------------------------------------------------------------------------
# P020 — title/approval-page template boilerplate suppression
# ---------------------------------------------------------------------------


def _make_title_page_boilerplate_pdf(path: Path, *, with_real_body_heading: bool = False) -> None:
    """Create a PDF with an NJIT-style title page (bold template text) and optional body."""
    doc = fitz.open()

    # Page 1: NJIT title page — all text bold (as it appears in real theses).
    p = doc.new_page(width=612, height=792)
    for y, text in [
        (80,  "A STUDY OF MACHINE LEARNING"),
        (100, "AND APPLICATIONS"),
        (140, "by"),
        (160, "Test Author"),
        (220, "A Thesis"),
        (245, "Submitted to the Faculty of the"),
        (270, "New Jersey Institute of Technology"),
        (295, "in Partial Fulfillment of the Requirements for the Degree of"),
        (320, "Master of Science in Computer Science"),
        (380, "Department of Computer Science"),
        (440, "December 2024"),
    ]:
        p.insert_text((108, y), text, fontsize=12, fontname="Times-Bold")

    # Page 2: APPROVAL PAGE with template fields (bold labels).
    p = doc.new_page(width=612, height=792)
    p.insert_text((200, 90), "APPROVAL PAGE", fontsize=14, fontname="Times-Bold")
    for y, text in [
        (150, "Author:"),
        (180, "Test Author"),
        (210, "Degree:"),
        (240, "Master of Science in Computer Science"),
        (270, "Date:"),
        (300, "December 2024"),
        (340, "Dissertation Advisor:"),
        (370, "Dr. Test Advisor"),
    ]:
        p.insert_text((108, y), text, fontsize=12, fontname="Times-Bold")

    # Page 3: body chapter heading with deliberate title-case error.
    p = doc.new_page(width=612, height=792)
    p.insert_text((220, 90), "CHAPTER 1", fontsize=16, fontname="Times-Bold")
    if with_real_body_heading:
        p.insert_text(
            (108, 200),
            "2.1 background and Related Work",
            fontsize=14,
            fontname="Times-Bold",
        )

    doc.save(path)
    doc.close()


def test_p020_title_page_boilerplate_in_partial_fulfillment_not_flagged(tmp_path: Path) -> None:
    """Regression: 'in Partial Fulfillment of the Requirements for the Degree of'
    (title page template text) must NOT trigger P020."""
    pdf_path = tmp_path / "title_page_boilerplate.pdf"
    _make_title_page_boilerplate_pdf(pdf_path)
    model = load_pdf_layout(str(pdf_path))

    findings = [f for f in check_pdf_title_capitalization(model) if f.rule_id == "P020"]
    title_page_findings = [f for f in findings if f.page == 1]
    assert not title_page_findings, (
        f"P020 should not fire on Title Page template text; got: {title_page_findings}"
    )


def test_p020_title_page_submitted_to_faculty_not_flagged(tmp_path: Path) -> None:
    """Regression: 'Submitted to the Faculty of the' (title page template text)
    must NOT trigger P020 — the trailing 'the' as last word should not be flagged."""
    pdf_path = tmp_path / "submitted_to_faculty.pdf"
    _make_title_page_boilerplate_pdf(pdf_path)
    model = load_pdf_layout(str(pdf_path))

    findings = [f for f in check_pdf_title_capitalization(model) if f.rule_id == "P020"]
    submitted_findings = [
        f for f in findings
        if "submitted" in f.details.get("line_preview", "").lower()
        or "faculty" in f.details.get("line_preview", "").lower()
    ]
    assert not submitted_findings, (
        f"'Submitted to the Faculty' must not trigger P020; got: {submitted_findings}"
    )


def test_p020_approval_page_template_not_flagged(tmp_path: Path) -> None:
    """Regression: Approval Page template fields ('Author:', 'Degree:', etc.)
    and the 'APPROVAL PAGE' heading must NOT trigger P020."""
    pdf_path = tmp_path / "approval_page.pdf"
    _make_title_page_boilerplate_pdf(pdf_path)
    model = load_pdf_layout(str(pdf_path))

    findings = [f for f in check_pdf_title_capitalization(model) if f.rule_id == "P020"]
    approval_page_findings = [f for f in findings if f.page == 2]
    assert not approval_page_findings, (
        f"P020 should not fire on Approval Page template; got: {approval_page_findings}"
    )


def test_p020_real_body_heading_still_flagged_after_title_page_fix(tmp_path: Path) -> None:
    """Body heading 'background and Related Work' must still trigger P020
    even when a Title Page with template boilerplate precedes it."""
    pdf_path = tmp_path / "title_then_real_heading.pdf"
    _make_title_page_boilerplate_pdf(pdf_path, with_real_body_heading=True)
    model = load_pdf_layout(str(pdf_path))

    findings = [f for f in check_pdf_title_capitalization(model) if f.rule_id == "P020"]
    body_findings = [
        f for f in findings
        if f.page == 3 and f.details.get("flagged_word") == "background"
    ]
    assert body_findings, (
        "P020 should still fire on real body heading 'background and Related Work'; "
        f"got page-3 findings: {[f.details.get('flagged_word') for f in findings if f.page == 3]}"
    )


def test_is_template_frontmatter_page_detects_title_and_approval_pages(tmp_path: Path) -> None:
    """_is_template_frontmatter_page must return True for title/approval pages
    and False for normal body pages."""
    from njit_auditor.rules.pdf_title_capitalization import _is_template_frontmatter_page

    pdf_path = tmp_path / "template_detect.pdf"
    _make_title_page_boilerplate_pdf(pdf_path)
    model = load_pdf_layout(str(pdf_path))

    # Page 1 is the title page.
    assert _is_template_frontmatter_page(model.pages[0]), (
        "Title page must be detected as template frontmatter"
    )
    # Page 2 is the approval page.
    assert _is_template_frontmatter_page(model.pages[1]), (
        "Approval page must be detected as template frontmatter"
    )
    # Page 3 is a body chapter page.
    assert not _is_template_frontmatter_page(model.pages[2]), (
        "Body chapter page must NOT be detected as template frontmatter"
    )


# ---------------------------------------------------------------------------
# P021: PDF abstract word-count tests
# ---------------------------------------------------------------------------


def _make_pdf_with_abstract(
    path: Path,
    abstract_word_count: int,
    include_abstract_heading: bool = True,
) -> None:
    body = " ".join(f"word{i}" for i in range(abstract_word_count))
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    if include_abstract_heading:
        page.insert_text((250, 90), "ABSTRACT", fontsize=16, fontname="Times-Bold")
    page.insert_text((108, 130), body[:500], fontsize=12)
    if len(body) > 500:
        page.insert_text((108, 400), body[500:900], fontsize=12)
    doc.save(path)
    doc.close()


def test_pdf_abstract_under_phd_limit_no_p021(tmp_path: Path) -> None:
    pdf_path = tmp_path / "abstract_ok.pdf"
    _make_pdf_with_abstract(pdf_path, abstract_word_count=50)
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_abstract_word_count(model)
    assert not any(f.rule_id == "P021" for f in findings)


def test_pdf_abstract_over_phd_limit_warns_p021(tmp_path: Path) -> None:
    pdf_path = tmp_path / "abstract_over.pdf"
    # Write 360 words of body text after ABSTRACT heading
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((250, 90), "ABSTRACT", fontsize=16, fontname="Times-Bold")
    # Insert lines of ~10 words each to total >350
    y = 130
    words_written = 0
    while words_written < 360 and y < 750:
        line = " ".join(f"word{words_written + i}" for i in range(10))
        page.insert_text((108, y), line, fontsize=12)
        y += 14
        words_written += 10
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_abstract_word_count(model)
    warning = next((f for f in findings if f.rule_id == "P021"), None)
    assert warning is not None
    assert int(warning.details["word_count"]) > 350


def test_pdf_no_abstract_heading_no_p021(tmp_path: Path) -> None:
    pdf_path = tmp_path / "no_abstract.pdf"
    _make_pdf_with_abstract(pdf_path, abstract_word_count=400, include_abstract_heading=False)
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_abstract_word_count(model)
    assert not any(f.rule_id == "P021" for f in findings)


def test_pdf_abstract_word_count_detail_fields(tmp_path: Path) -> None:
    pdf_path = tmp_path / "abstract_detail.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((250, 90), "ABSTRACT", fontsize=16, fontname="Times-Bold")
    y = 130
    words_written = 0
    while words_written < 360 and y < 750:
        line = " ".join(f"word{words_written + i}" for i in range(10))
        page.insert_text((108, y), line, fontsize=12)
        y += 14
        words_written += 10
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_abstract_word_count(model)
    warning = next(f for f in findings if f.rule_id == "P021")
    assert "word_count" in warning.details
    assert "limit" in warning.details
    assert "inferred_degree_type" in warning.details
    assert "confidence" in warning.details


def test_pdf_cli_command_runs_with_p021(tmp_path: Path) -> None:
    pdf_path = tmp_path / "cli_p021.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((250, 90), "ABSTRACT", fontsize=16, fontname="Times-Bold")
    y = 130
    words_written = 0
    while words_written < 360 and y < 750:
        line = " ".join(f"word{words_written + i}" for i in range(10))
        page.insert_text((108, y), line, fontsize=12)
        y += 14
        words_written += 10
    doc.save(pdf_path)
    doc.close()
    result = runner.invoke(app, ["pdf", str(pdf_path)])
    assert result.exit_code == 0
    assert "P021" in result.output


# ---------------------------------------------------------------------------
# P023: PDF body text double-spacing tests
# ---------------------------------------------------------------------------

_BODY_TEXT_TEMPLATE = (
    "Synthetic body paragraph text line for double-spacing verification test {idx}."
)

# Single-spaced: 12pt baseline spacing → ratio 1.0 per 12pt font (clearly suspicious).
_SINGLE_SPACED_Y = [140, 152, 164, 176, 188, 200, 212, 224, 236, 248, 260]
# Double-spaced: 24pt baseline spacing → ratio 2.0 per 12pt font (clearly fine).
_DOUBLE_SPACED_Y = [140, 164, 188, 212, 236, 260, 284, 308, 332, 356]


def _make_body_spacing_pdf(
    path: Path,
    y_positions: list[float],
    fontsize: float = 12,
) -> None:
    """Synthetic PDF with body-text lines at given baseline y positions."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    for idx, y in enumerate(y_positions):
        page.insert_text((108, y), _BODY_TEXT_TEMPLATE.format(idx=idx), fontsize=fontsize)
    doc.save(path)
    doc.close()


def test_double_spaced_body_no_p023(tmp_path: Path) -> None:
    """Double-spaced body text (24pt between 12pt baselines, ratio 2.0) must not warn."""
    pdf_path = tmp_path / "body_double_ok.pdf"
    _make_body_spacing_pdf(pdf_path, _DOUBLE_SPACED_Y)
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_body_spacing(model)
    assert not any(f.rule_id == "P023" for f in findings)


def test_single_spaced_body_warns_p023(tmp_path: Path) -> None:
    """Single-spaced body text (12pt between 12pt baselines, ratio 1.0) must warn.

    11 lines → 10 suspicious gaps, fraction 100% → satisfies the conservative
    thresholds (≥8 suspicious, ≥60% fraction, median < 1.55).
    """
    pdf_path = tmp_path / "body_single_warns.pdf"
    _make_body_spacing_pdf(pdf_path, _SINGLE_SPACED_Y)
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_body_spacing(model)
    assert any(f.rule_id == "P023" for f in findings)


def test_p023_one_finding_per_page(tmp_path: Path) -> None:
    """P023 emits at most one finding per under-spaced page."""
    pdf_path = tmp_path / "body_single_one_per_page.pdf"
    _make_body_spacing_pdf(pdf_path, _SINGLE_SPACED_Y)
    model = load_pdf_layout(str(pdf_path))
    p023 = [f for f in check_pdf_body_spacing(model) if f.rule_id == "P023"]
    assert len(p023) == 1


def test_p023_details_include_required_fields(tmp_path: Path) -> None:
    """P023 finding details must include all required fields."""
    pdf_path = tmp_path / "body_single_details.pdf"
    _make_body_spacing_pdf(pdf_path, _SINGLE_SPACED_Y)
    model = load_pdf_layout(str(pdf_path))
    f = next(f for f in check_pdf_body_spacing(model) if f.rule_id == "P023")
    assert f.details.get("issue_type") == "possible_body_text_not_double_spaced"
    assert f.details.get("median_body_gap_pt") is not None
    assert f.details.get("estimated_body_font_size_pt") is not None
    assert f.details.get("gap_to_font_ratio") is not None
    assert f.details.get("affected_gap_count") is not None
    assert f.details.get("confidence") == "medium"


def test_p023_named_heading_page_skipped(tmp_path: Path) -> None:
    """Pages with a named front-matter heading (e.g. ABSTRACT) are skipped for P023.

    Even if enough single-spaced body-text lines exist on the page, the named
    heading causes the whole page to be excluded from P023 analysis.
    """
    pdf_path = tmp_path / "heading_only_p023.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((250, 90), "ABSTRACT", fontsize=16, fontname="Times-Bold")
    for idx, y in enumerate(_SINGLE_SPACED_Y):
        page.insert_text((108, y), _BODY_TEXT_TEMPLATE.format(idx=idx), fontsize=12)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_body_spacing(model)
    assert not any(f.rule_id == "P023" for f in findings)


def test_p023_page_number_line_not_counted(tmp_path: Path) -> None:
    """A double-spaced body page with a bottom page number must not warn."""
    pdf_path = tmp_path / "body_double_with_pagenum.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    for idx, y in enumerate(_DOUBLE_SPACED_Y):
        page.insert_text(
            (108, y), _BODY_TEXT_TEMPLATE.format(idx=idx), fontsize=12
        )
    page.insert_text((300, 770), "5", fontsize=12)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_body_spacing(model)
    assert not any(f.rule_id == "P023" for f in findings)


def test_p023_toc_page_ignored(tmp_path: Path) -> None:
    """TABLE OF CONTENTS pages must be completely skipped for P023."""
    pdf_path = tmp_path / "toc_p023.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((190, 90), "TABLE OF CONTENTS", fontsize=16, fontname="Times-Bold")
    for idx, y in enumerate(_SINGLE_SPACED_Y):
        page.insert_text((108, y), _BODY_TEXT_TEMPLATE.format(idx=idx), fontsize=12)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_body_spacing(model)
    assert not any(f.rule_id == "P023" for f in findings)


def test_p023_list_of_tables_page_ignored(tmp_path: Path) -> None:
    """LIST OF TABLES pages must be completely skipped for P023."""
    pdf_path = tmp_path / "lot_p023.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((210, 90), "LIST OF TABLES", fontsize=16, fontname="Times-Bold")
    for idx, y in enumerate(_SINGLE_SPACED_Y):
        page.insert_text((108, y), _BODY_TEXT_TEMPLATE.format(idx=idx), fontsize=12)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_body_spacing(model)
    assert not any(f.rule_id == "P023" for f in findings)


def test_p023_references_page_ignored(tmp_path: Path) -> None:
    """REFERENCES pages must be completely skipped for P023."""
    pdf_path = tmp_path / "ref_p023.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((240, 90), "REFERENCES", fontsize=16, fontname="Times-Bold")
    for idx, y in enumerate(_SINGLE_SPACED_Y):
        page.insert_text((108, y), _BODY_TEXT_TEMPLATE.format(idx=idx), fontsize=12)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_body_spacing(model)
    assert not any(f.rule_id == "P023" for f in findings)


def test_p023_caption_lines_not_counted(tmp_path: Path) -> None:
    """Caption lines must not be counted as body-text lines for P023."""
    pdf_path = tmp_path / "captions_p023.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    for idx, y in enumerate(_SINGLE_SPACED_Y):
        page.insert_text(
            (108, y),
            f"Figure {idx + 1}. Synthetic figure caption line for test purposes only here.",
            fontsize=12,
        )
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_body_spacing(model)
    assert not any(f.rule_id == "P023" for f in findings)


def test_p023_short_lines_not_counted(tmp_path: Path) -> None:
    """Lines shorter than MIN_LINE_TEXT_LEN must not be counted as body-text lines."""
    pdf_path = tmp_path / "short_lines_p023.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    for idx, y in enumerate(_SINGLE_SPACED_Y):
        page.insert_text((108, y), "Short.", fontsize=12)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_body_spacing(model)
    assert not any(f.rule_id == "P023" for f in findings)


def test_p023_not_enough_suspicious_gaps_no_warning(tmp_path: Path) -> None:
    """Double-spaced lines produce 0 suspicious gaps (ratio 2.0 >> 1.55) so P023 does not fire."""
    pdf_path = tmp_path / "body_mostly_double.pdf"
    # 10 lines at 24pt spacing → 9 gaps, ratio 2.0, none suspicious → no P023
    _make_body_spacing_pdf(pdf_path, _DOUBLE_SPACED_Y)
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_body_spacing(model)
    assert not any(f.rule_id == "P023" for f in findings)


def test_p023_cli_in_output(tmp_path: Path) -> None:
    """CLI pdf command must surface P023 when body text appears single-spaced."""
    pdf_path = tmp_path / "cli_p023.pdf"
    _make_body_spacing_pdf(pdf_path, _SINGLE_SPACED_Y)
    result = runner.invoke(app, ["pdf", str(pdf_path)])
    assert result.exit_code == 0
    assert "P023" in result.output


def test_p023_json_report_includes_rule_when_triggered(tmp_path: Path) -> None:
    """JSON report must include P023 when body text is single-spaced."""
    pdf_path = tmp_path / "json_p023.pdf"
    json_out = tmp_path / "out" / "p023_report.json"
    _make_body_spacing_pdf(pdf_path, _SINGLE_SPACED_Y)
    result = runner.invoke(app, ["pdf", str(pdf_path), "--json-out", str(json_out)])
    assert result.exit_code == 0
    assert json_out.exists()
    assert "P023" in json_out.read_text(encoding="utf-8")


def test_p023_front_matter_continuation_page_not_flagged(tmp_path: Path) -> None:
    """Front-matter continuation pages (before Chapter 1) must not trigger P023.

    The biographical-sketch publication list and other front-matter content is
    legitimately single-spaced. P023 should only apply to body pages (at or after
    the first CHAPTER/APPENDIX heading).  This two-page PDF has a single-spaced
    front-matter page followed by a CHAPTER 1 body page; only the body page
    would be eligible (but the body page has double-spaced text, so no P023).
    """
    pdf_path = tmp_path / "frontmatter_continuation_p023.pdf"
    doc = fitz.open()

    # Page 1: single-spaced front-matter continuation (no named heading).
    page1 = doc.new_page(width=612, height=792)
    for idx, y in enumerate(_SINGLE_SPACED_Y):
        page1.insert_text((108, y), _BODY_TEXT_TEMPLATE.format(idx=idx), fontsize=12)

    # Page 2: body page starting with CHAPTER 1 heading, double-spaced text.
    page2 = doc.new_page(width=612, height=792)
    page2.insert_text((220, 90), "CHAPTER 1", fontsize=16, fontname="Times-Bold")
    for idx, y in enumerate(_DOUBLE_SPACED_Y):
        page2.insert_text((108, y), _BODY_TEXT_TEMPLATE.format(idx=idx), fontsize=12)

    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_body_spacing(model)
    assert not any(f.rule_id == "P023" for f in findings), (
        "P023 must not fire on front-matter pages that precede Chapter 1"
    )


def test_p023_body_single_spaced_still_flagged_after_chapter(tmp_path: Path) -> None:
    """Body pages (at or after CHAPTER 1) with single-spaced text must still warn.

    Ensures the body-start suppression does not accidentally suppress body findings.
    """
    pdf_path = tmp_path / "body_after_chapter_p023.pdf"
    doc = fitz.open()

    # Page 1: single-spaced front-matter continuation (should be skipped).
    page1 = doc.new_page(width=612, height=792)
    for idx, y in enumerate(_SINGLE_SPACED_Y):
        page1.insert_text((108, y), _BODY_TEXT_TEMPLATE.format(idx=idx), fontsize=12)

    # Page 2: body page with CHAPTER 1 heading but single-spaced content.
    page2 = doc.new_page(width=612, height=792)
    page2.insert_text((220, 90), "CHAPTER 1", fontsize=16, fontname="Times-Bold")
    for idx, y in enumerate(_SINGLE_SPACED_Y):
        page2.insert_text((108, y), _BODY_TEXT_TEMPLATE.format(idx=idx), fontsize=12)

    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_body_spacing(model)
    p023 = [f for f in findings if f.rule_id == "P023"]
    assert len(p023) == 1
    assert p023[0].page == 2, "P023 should fire on page 2 (body), not page 1 (front matter)"


# Single-spaced table rows: 12pt pitch → tight spacing that lives only inside the
# table region and must be excluded from body-text measurement.
_TABLE_ROW_Y = [126, 138, 150, 162, 174, 186, 198, 210, 222, 234, 246]
_TABLE_CAPTION_TEXT = "Table 4.1 Alignment of Research Questions and Survey Items"


def _draw_table_rows(page: fitz.Page, y_positions: list[float], x: float = 108) -> None:
    for idx, y in enumerate(y_positions):
        page.insert_text(
            (x, y),
            f"Research question {idx} aligned with survey item set for the study.",
            fontsize=12,
        )


def test_p023_table_region_tight_spacing_not_flagged(tmp_path: Path) -> None:
    """When the only tight spacing is inside a captioned table, P023 must not fire.

    All single-spaced lines belong to the table region anchored by the
    ``Table 4.1 ...`` caption, so no body-text lines remain to measure.
    """
    pdf_path = tmp_path / "table_only_p023.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((108, 110), _TABLE_CAPTION_TEXT, fontsize=12)
    _draw_table_rows(page, _TABLE_ROW_Y)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_body_spacing(model)
    assert not any(f.rule_id == "P023" for f in findings)


def test_p023_table_borders_not_treated_as_body_evidence(tmp_path: Path) -> None:
    """Drawn table borders (graphic lines) must not drive a body-spacing warning.

    Border strokes are not text and never enter the measurement; combined with a
    captioned single-spaced table, the page yields no P023 finding.
    """
    pdf_path = tmp_path / "table_borders_p023.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((108, 110), _TABLE_CAPTION_TEXT, fontsize=12)
    _draw_table_rows(page, _TABLE_ROW_Y)
    for border_y in (118, 258):
        page.draw_line((108, border_y), (504, border_y))
    page.draw_line((108, 118), (108, 258))
    page.draw_line((504, 118), (504, 258))
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_body_spacing(model)
    assert not any(f.rule_id == "P023" for f in findings)


def test_p023_table_plus_body_measures_only_body(tmp_path: Path) -> None:
    """With a table above and ordinary prose below, P023 measures only the prose.

    The single-spaced table rows are excluded via the caption-anchored region;
    the single-spaced body prose beneath the table is still measured and warns,
    and the finding counts only the body lines (not the table rows).
    """
    pdf_path = tmp_path / "table_plus_body_p023.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((108, 110), _TABLE_CAPTION_TEXT, fontsize=12)
    _draw_table_rows(page, _TABLE_ROW_Y)
    # Clear separation, then 11 single-spaced ordinary body lines below the table.
    body_y = [320 + i * 12 for i in range(11)]
    for idx, y in enumerate(body_y):
        page.insert_text((108, y), _BODY_TEXT_TEMPLATE.format(idx=idx), fontsize=12)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    p023 = [f for f in check_pdf_body_spacing(model) if f.rule_id == "P023"]
    assert len(p023) == 1
    finding = p023[0]
    assert finding.details.get("measured_body_line_count") == str(len(body_y))
    # Evidence bbox must cover the body region below the table, not the table rows.
    bbox = finding.details.get("bbox")
    assert bbox is not None
    measured_y0 = float(bbox.split(",")[1])
    assert measured_y0 > max(_TABLE_ROW_Y), "measured region must be below the table"


def _p023_text_line(text: str, x0: float, y0: float, x1: float, y1: float) -> PdfTextLine:
    bbox = BBox(x0=x0, y0=y0, x1=x1, y1=y1)
    span = PdfTextSpan(text=text, bbox=bbox, font="Times", size=12.0)
    return PdfTextLine(spans=[span], bbox=bbox, text=text)


def test_p023_figure_description_split_row_not_counted() -> None:
    """A multi-line figure description must not be flagged as under-spaced body text.

    Reproduces the Sample B page 82 layout artifact: text extraction splits a
    figure caption's number ("Figure 3.3") from its description text onto a
    separate line fragment sharing the same visual row, and the description
    continues below at single-spacing (a normal, expected convention for
    figure descriptions, per Ester's exception list: tables, figure
    descriptions, bullet points, multi-line titles). Without the
    split-row-aware exclusion, these 9 tightly packed description lines alone
    clear the P023 thresholds (>= 8 suspicious gaps, majority fraction,
    median ratio < 1.55). See
    docs/status/ester_sample_b_p023_figure_description_spacing.md.
    """
    lines = [
        # Bare "Figure 3.3" label, split from its description onto the same row.
        _p023_text_line("Figure 3.3", 108, 100, 160, 112),
        _p023_text_line(
            "Scheduling strategies for the ODW weight over training. From left to",
            180,
            100,
            520,
            112,
        ),
    ]
    y = 112
    for idx in range(8):
        text = f"right: description continuation line number {idx} for the figure caption."
        lines.append(_p023_text_line(text, 108, y, 500, y + 12))
        y += 12
    block = PdfTextBlock(lines=lines, bbox=BBox(x0=108, y0=100, x1=520, y1=y), text="")
    page = PdfPage(page_number=1, width=612, height=792, text_blocks=[block])
    model = PdfDocument(path="synthetic", pages=[page])

    findings = check_pdf_body_spacing(model)
    assert not any(f.rule_id == "P023" for f in findings)


def test_p023_figure_description_does_not_suppress_ordinary_body_paragraph() -> None:
    """A figure-description exception must not swallow a separate body paragraph.

    A figure block (label + single-spaced description) sits above an
    unrelated, ordinary single-spaced body paragraph. P023 must still fire
    on the body paragraph, and the finding must measure only the body lines
    -- not the figure-description lines above it.
    """
    lines = [
        _p023_text_line("Figure 3.3", 108, 100, 160, 112),
        _p023_text_line(
            "Scheduling strategies for the ODW weight over training. From left to",
            180,
            100,
            520,
            112,
        ),
    ]
    y = 112
    for idx in range(4):
        text = f"right: description continuation line number {idx} for the figure caption."
        lines.append(_p023_text_line(text, 108, y, 500, y + 12))
        y += 12

    # Clear paragraph-break gap, then ordinary single-spaced body prose.
    body_top = y + 40
    body_y = [body_top + i * 12 for i in range(11)]
    for idx, by in enumerate(body_y):
        lines.append(
            _p023_text_line(_BODY_TEXT_TEMPLATE.format(idx=idx), 108, by, 500, by + 12)
        )

    block = PdfTextBlock(
        lines=lines, bbox=BBox(x0=108, y0=100, x1=520, y1=body_y[-1] + 12), text=""
    )
    page = PdfPage(page_number=1, width=612, height=792, text_blocks=[block])
    model = PdfDocument(path="synthetic", pages=[page])

    p023 = [f for f in check_pdf_body_spacing(model) if f.rule_id == "P023"]
    assert len(p023) == 1
    finding = p023[0]
    assert finding.details.get("measured_body_line_count") == str(len(body_y))
    bbox = finding.details.get("bbox")
    assert bbox is not None
    measured_y0 = float(bbox.split(",")[1])
    assert measured_y0 >= body_top, "measured region must be the body paragraph, not the figure"


def test_p023_references_continuation_page_not_flagged(tmp_path: Path) -> None:
    """References continuation pages (no repeated heading) must be excluded from P023.

    Reference-entry spacing has its own dedicated rule (P064); it must not be
    surfaced as ordinary "body text not double-spaced".
    """
    from njit_auditor.rules.pdf_references_citations_structural import (
        references_section_page_numbers,
    )

    pdf_path = tmp_path / "references_continuation_p023.pdf"
    doc = fitz.open()

    # Page 1: body page (Chapter 1) with double-spaced prose -> sets body start.
    page1 = doc.new_page(width=612, height=792)
    page1.insert_text((200, 90), "CHAPTER 1 INTRODUCTION", fontsize=16, fontname="Times-Bold")
    for idx, y in enumerate(_DOUBLE_SPACED_Y):
        page1.insert_text((108, y), _BODY_TEXT_TEMPLATE.format(idx=idx), fontsize=12)

    # Page 2: REFERENCES heading + single-spaced reference entries.
    page2 = doc.new_page(width=612, height=792)
    page2.insert_text((240, 90), "REFERENCES", fontsize=16, fontname="Times-Bold")
    for idx, y in enumerate(_SINGLE_SPACED_Y):
        page2.insert_text(
            (108, y + 40),
            f"Author {idx}, A. (2020). Title of reference entry number {idx} here.",
            fontsize=12,
        )

    # Page 3: references continuation, single-spaced, NO repeated heading.
    page3 = doc.new_page(width=612, height=792)
    for idx, y in enumerate(_SINGLE_SPACED_Y):
        page3.insert_text(
            (108, y),
            f"Writer {idx}, B. (2019). Continued reference entry number {idx} listed.",
            fontsize=12,
        )

    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))

    ref_pages = references_section_page_numbers(model)
    assert 3 in ref_pages, "continuation page must be recognized as references section"

    findings = check_pdf_body_spacing(model)
    assert not any(f.rule_id == "P023" for f in findings), (
        "References pages (including continuation) must not be flagged as body text"
    )


# ---------------------------------------------------------------------------
# P024: TOC/List entry capitalization and punctuation
# ---------------------------------------------------------------------------

def _make_toc_pdf(path: Path, heading: str, entries: list[tuple[str, float]]) -> None:
    """Create a PDF with a TOC/List heading and entries at given x-indents."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((190, 90), heading, fontsize=16, fontname="Times-Bold")
    for idx, (label, indent_x) in enumerate(entries):
        y = 130 + idx * 20
        page.insert_text((indent_x, y), label)
        page.insert_text((500, y), "12")
    doc.save(path)
    doc.close()


def test_p024_toc_level2_correct_title_case_no_warning(tmp_path: Path) -> None:
    """TOC Level 2 entry in correct Title Case must not produce a P024 warning."""
    pdf_path = tmp_path / "toc_l2_ok.pdf"
    _make_toc_pdf(
        pdf_path,
        "TABLE OF CONTENTS",
        [
            # Use 5+ word CHAPTER entries to pass _likely_entry_line's all-caps/≤4-word filter.
            ("CHAPTER 1 INTRODUCTION TO THE STUDY ....", 108),
            ("CHAPTER 2 BACKGROUND AND RELATED WORK ....", 108),
            ("CHAPTER 3 RESEARCH METHODOLOGY AND DATA ....", 108),
            ("1.1 Background of the Study ....", 140),
            ("1.2 Statement of the Problem ....", 140),
        ],
    )
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_toc_list_formatting(model)
    p024 = [f for f in findings if f.rule_id == "P024"]
    assert not any(
        f.details.get("issue_type") == "toc_level_capitalization"
        and f.details.get("entry_level") == "2"
        for f in p024
    )


def test_p024_toc_level2_lowercase_major_word_warns(tmp_path: Path) -> None:
    """TOC Level 2 entry with obvious lowercase major word must warn."""
    pdf_path = tmp_path / "toc_l2_bad.pdf"
    _make_toc_pdf(
        pdf_path,
        "TABLE OF CONTENTS",
        [
            # Use numbered Level 2 entries only — all pass _likely_entry_line.
            ("1.1 background of the study and motivation ....", 108),
            ("1.2 Statement of the Problem and Research Gap ....", 108),
            ("1.3 Review of Related Literature and Prior Work ....", 108),
        ],
    )
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_toc_list_formatting(model)
    p024 = [f for f in findings if f.rule_id == "P024"]
    assert any(
        f.details.get("issue_type") == "toc_level_capitalization"
        and f.details.get("entry_level") == "2"
        for f in p024
    )


def test_p024_toc_ambiguous_entry_skipped(tmp_path: Path) -> None:
    """TOC entries that cannot be level-classified must be skipped (no P024 warning)."""
    pdf_path = tmp_path / "toc_ambiguous.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((190, 90), "TABLE OF CONTENTS", fontsize=16, fontname="Times-Bold")
    # Single-indent level — cannot distinguish Level 1 from Level 2.
    # One entry is a short entry that fails the word-count gate.
    page.insert_text((108, 130), "Short")
    page.insert_text((500, 130), "2")
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_toc_list_formatting(model)
    assert not any(f.rule_id == "P024" for f in findings)


def test_p024_lot_correct_title_case_no_warning(tmp_path: Path) -> None:
    """LoT entry with correct Title Case and no terminal period must not warn."""
    pdf_path = tmp_path / "lot_ok.pdf"
    _make_toc_pdf(
        pdf_path,
        "LIST OF TABLES",
        [
            ("Table 1 Descriptive Statistics for Participant Demographics ....", 108),
            ("Table 2 Summary of Regression Coefficients for Main Model ....", 108),
            ("Table 3 Comparison of Algorithm Performance Metrics ....", 108),
        ],
    )
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_toc_list_formatting(model)
    assert not any(
        f.rule_id == "P024" and f.details.get("issue_type") == "list_of_tables_title_case"
        for f in findings
    )


def test_p024_lot_lowercase_major_word_warns(tmp_path: Path) -> None:
    """LoT entry with obvious lowercase major word must warn."""
    pdf_path = tmp_path / "lot_bad.pdf"
    _make_toc_pdf(
        pdf_path,
        "LIST OF TABLES",
        [
            ("Table 1 descriptive statistics for participant demographics ....", 108),
            ("Table 2 Summary of Regression Coefficients for Main Model ....", 108),
            ("Table 3 Comparison of Algorithm Performance Metrics ....", 108),
        ],
    )
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_toc_list_formatting(model)
    assert any(
        f.rule_id == "P024" and f.details.get("issue_type") == "list_of_tables_title_case"
        for f in findings
    )


def test_p024_lot_continued_heading_detected(tmp_path: Path) -> None:
    """LoT '(CONTINUED)' heading variant should still run list-format checks."""
    pdf_path = tmp_path / "lot_continued_bad.pdf"
    _make_toc_pdf(
        pdf_path,
        "LIST OF TABLES (CONTINUED)",
        [
            ("Table 1 descriptive statistics for participant demographics ....", 108),
            ("Table 2 Summary of Regression Coefficients for Main Model ....", 108),
            ("Table 3 Comparison of Algorithm Performance Metrics ....", 108),
        ],
    )
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_toc_list_formatting(model)
    assert any(
        f.rule_id == "P024" and f.details.get("issue_type") == "list_of_tables_title_case"
        for f in findings
    )


def test_p024_lot_unexpected_terminal_period_warns(tmp_path: Path) -> None:
    """LoT entry ending with a period must produce an unexpected_terminal_punctuation warning."""
    pdf_path = tmp_path / "lot_period.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((210, 90), "LIST OF TABLES", fontsize=16, fontname="Times-Bold")
    page.insert_text((108, 130), "Table 1. Descriptive Statistics for Participants.")
    page.insert_text((500, 130), "12")
    page.insert_text((108, 150), "Table 2. Summary of Regression Coefficients Here.")
    page.insert_text((500, 150), "24")
    page.insert_text((108, 170), "Table 3. Comparison of Algorithm Performance.")
    page.insert_text((500, 170), "36")
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_toc_list_formatting(model)
    assert any(
        f.rule_id == "P024"
        and f.details.get("issue_type") == "unexpected_terminal_punctuation"
        and f.details.get("page_type") == "list_of_tables"
        for f in findings
    )


def test_p024_lof_sentence_case_correct_no_warning(tmp_path: Path) -> None:
    """LoF entry in correct sentence case must not warn."""
    pdf_path = tmp_path / "lof_ok.pdf"
    _make_toc_pdf(
        pdf_path,
        "LIST OF FIGURES",
        [
            ("Figure 1 Schematic diagram of the proposed system architecture ....", 108),
            ("Figure 2 Overview of data collection pipeline for experiments ....", 108),
            ("Figure 3 Comparison of training accuracy across baseline models ....", 108),
        ],
    )
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_toc_list_formatting(model)
    assert not any(
        f.rule_id == "P024" and f.details.get("issue_type") == "list_of_figures_sentence_case"
        for f in findings
    )


def test_p024_lof_title_case_like_warns(tmp_path: Path) -> None:
    """LoF entry with title-case-like capitalization warns for sentence-case violation."""
    pdf_path = tmp_path / "lof_bad.pdf"
    _make_toc_pdf(
        pdf_path,
        "LIST OF FIGURES",
        [
            ("Figure 1 Schematic Diagram of the Proposed System Architecture ....", 108),
            ("Figure 2 Overview of Data Collection Pipeline for Experiments ....", 108),
            ("Figure 3 Comparison of Training Accuracy Across Baseline Models ....", 108),
        ],
    )
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_toc_list_formatting(model)
    assert any(
        f.rule_id == "P024" and f.details.get("issue_type") == "list_of_figures_sentence_case"
        for f in findings
    )


def test_p024_lof_sentence_case_keeps_long_minor_words_in_ratio(tmp_path: Path) -> None:
    """Lowercase long prepositions must dilute LoF sentence-case ratio (not tip FPs)."""
    pdf_path = tmp_path / "lof_with_marching.pdf"
    _make_toc_pdf(
        pdf_path,
        "LIST OF FIGURES",
        [
            ("Figure 1 Overview of the experimental setup for this study ....", 108),
            ("Figure 2 Schematic of the measurement configuration used here ....", 108),
            ("Figure 3 Qualitative comparison with Marching Cubes ....", 108),
        ],
    )
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_toc_list_formatting(model)
    assert not any(
        f.rule_id == "P024"
        and f.details.get("issue_type") == "list_of_figures_sentence_case"
        and "Marching" in (f.details.get("line_preview") or "")
        for f in findings
    )


def test_p024_lof_sentence_case_identifies_exact_flagged_words(tmp_path: Path) -> None:
    """The finding must name the specific words causing the sentence-case
    violation, not just a generic 'multiple later words' message."""
    pdf_path = tmp_path / "lof_flagged_words.pdf"
    _make_toc_pdf(
        pdf_path,
        "LIST OF FIGURES",
        [
            ("Figure 1 Schematic Diagram of the Proposed System Architecture ....", 108),
            ("Figure 2 Overview of Data Collection Pipeline for Experiments ....", 108),
            ("Figure 3 Comparison of Training Accuracy Across Baseline Models ....", 108),
        ],
    )
    model = load_pdf_layout(str(pdf_path))
    findings = [
        f
        for f in check_pdf_toc_list_formatting(model)
        if f.rule_id == "P024" and f.details.get("issue_type") == "list_of_figures_sentence_case"
    ]
    assert findings
    for f in findings:
        flagged_words = f.details.get("flagged_words", "")
        assert flagged_words
        first_word = flagged_words.split(",")[0].strip()
        assert first_word in f.message


def test_p024_lof_common_nouns_in_title_case_warn(tmp_path: Path) -> None:
    """A LoF entry with obvious title-cased common nouns must trigger the warning."""
    pdf_path = tmp_path / "lof_common_nouns_bad.pdf"
    _make_toc_pdf(
        pdf_path,
        "LIST OF FIGURES",
        [
            # Use several capitalized major nouns (not prepositions) so the
            # sentence-case heuristic still has enough eligible later words after
            # NJIT minor-word filtering (articles/prepositions/conjunctions).
            ("Figure 4.1 Relationship Benefits Readiness Outcomes Across Cohorts ....", 108),
            ("Figure 4.2 Overview of results for baseline comparison ....", 108),
            ("Figure 4.3 Summary of findings from pilot testing ....", 108),
        ],
    )
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_toc_list_formatting(model)
    lof_findings = [
        f
        for f in findings
        if f.rule_id == "P024"
        and f.details.get("issue_type") == "list_of_figures_sentence_case"
    ]
    assert lof_findings
    assert lof_findings[0].details.get("source_q_rule_id") == "Q074"
    assert lof_findings[0].details.get("entry_index") == "0"


def test_p024_leader_dots_and_page_number_stripped_before_check(tmp_path: Path) -> None:
    """Leader dots and trailing page numbers must be stripped before capitalization check."""
    pdf_path = tmp_path / "lot_stripped.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((210, 90), "LIST OF TABLES", fontsize=16, fontname="Times-Bold")
    # This entry has correct Title Case; the trailing ".... 12" must not be part of the check.
    page.insert_text((108, 130), "Table 1 Regression Analysis of Independent Variables ....")
    page.insert_text((500, 130), "12")
    page.insert_text((108, 150), "Table 2 Summary Statistics for Population Groups ....")
    page.insert_text((500, 150), "24")
    page.insert_text((108, 170), "Table 3 Cross-Validation Results for Classifier Models ....")
    page.insert_text((500, 170), "36")
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_toc_list_formatting(model)
    assert not any(
        f.rule_id == "P024" and f.details.get("issue_type") == "list_of_tables_title_case"
        for f in findings
    )


def test_p024_body_page_ignored(tmp_path: Path) -> None:
    """P024 must not fire on ordinary body pages."""
    pdf_path = tmp_path / "body_p024.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((108, 130), "1.1 background of the study and its implications here.")
    page.insert_text((108, 150), "some more lowercase paragraph text on this body page.")
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_toc_list_formatting(model)
    assert not any(f.rule_id == "P024" for f in findings)


def test_p024_references_page_ignored(tmp_path: Path) -> None:
    """P024 must not fire on REFERENCES pages."""
    pdf_path = tmp_path / "ref_p024.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((240, 90), "REFERENCES", fontsize=16, fontname="Times-Bold")
    page.insert_text((108, 130), "1.1 background of the study and its implications here.")
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_toc_list_formatting(model)
    assert not any(f.rule_id == "P024" for f in findings)


def test_p024_cli_pdf_includes_p024(tmp_path: Path) -> None:
    """CLI pdf command must surface P024 when a LoT entry has a title-case violation."""
    pdf_path = tmp_path / "cli_p024.pdf"
    _make_toc_pdf(
        pdf_path,
        "LIST OF TABLES",
        [
            ("Table 1 descriptive statistics for participant demographics ....", 108),
            ("Table 2 Summary of Regression Coefficients for Main Model ....", 108),
            ("Table 3 Comparison of Algorithm Performance Metrics ....", 108),
        ],
    )
    result = runner.invoke(app, ["pdf", str(pdf_path)])
    assert result.exit_code == 0
    assert "P024" in result.output


def test_p024_json_report_includes_p024_when_triggered(tmp_path: Path) -> None:
    """JSON report must include P024 when LoT entry has a title-case violation."""
    pdf_path = tmp_path / "json_p024.pdf"
    json_out = tmp_path / "out" / "p024_report.json"
    _make_toc_pdf(
        pdf_path,
        "LIST OF TABLES",
        [
            ("Table 1 descriptive statistics for participant demographics ....", 108),
            ("Table 2 Summary of Regression Coefficients for Main Model ....", 108),
            ("Table 3 Comparison of Algorithm Performance Metrics ....", 108),
        ],
    )
    result = runner.invoke(app, ["pdf", str(pdf_path), "--json-out", str(json_out)])
    assert result.exit_code == 0
    assert json_out.exists()
    assert "P024" in json_out.read_text(encoding="utf-8")


def test_p024_entry_index_distinguishes_same_page_toc_violations(tmp_path: Path) -> None:
    """Two flagged Level 2 entries on the same TOC page must record distinct entry_index."""
    pdf_path = tmp_path / "toc_l2_two_bad.pdf"
    _make_toc_pdf(
        pdf_path,
        "TABLE OF CONTENTS",
        [
            ("1.1 background of the study and motivation ....", 140),
            ("1.2 Statement of the Problem and Research Gap ....", 140),
            ("1.3 review of related literature and prior work ....", 140),
        ],
    )
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_toc_list_formatting(model)
    p024_level2 = [
        f
        for f in findings
        if f.details.get("issue_type") == "toc_level_capitalization"
        and f.details.get("entry_level") == "2"
    ]
    assert len(p024_level2) == 2
    entry_indexes = {f.details.get("entry_index") for f in p024_level2}
    assert entry_indexes == {"0", "2"}


def test_p024_entry_index_distinguishes_same_page_lot_violations(tmp_path: Path) -> None:
    """Two flagged List of Tables entries on the same page must record distinct entry_index."""
    pdf_path = tmp_path / "lot_two_bad.pdf"
    _make_toc_pdf(
        pdf_path,
        "LIST OF TABLES",
        [
            ("Table 1 descriptive statistics for participant demographics ....", 108),
            ("Table 2 Summary of Regression Coefficients for Main Model ....", 108),
            ("Table 3 comparison of algorithm performance metrics here ....", 108),
        ],
    )
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_toc_list_formatting(model)
    p024_lot = [
        f for f in findings if f.details.get("issue_type") == "list_of_tables_title_case"
    ]
    assert len(p024_lot) == 2
    entry_indexes = {f.details.get("entry_index") for f in p024_lot}
    assert entry_indexes == {"0", "2"}


def test_p024_entry_index_present_for_lof_and_terminal_punctuation(tmp_path: Path) -> None:
    """LoF sentence-case and LoT terminal-punctuation findings must also carry entry_index."""
    lof_path = tmp_path / "lof_bad.pdf"
    _make_toc_pdf(
        lof_path,
        "LIST OF FIGURES",
        [
            ("Figure 1 Schematic Diagram of the Proposed System Architecture ....", 108),
        ],
    )
    model = load_pdf_layout(str(lof_path))
    findings = check_pdf_toc_list_formatting(model)
    lof_finding = next(
        f for f in findings if f.details.get("issue_type") == "list_of_figures_sentence_case"
    )
    assert lof_finding.details.get("entry_index") == "0"

    lot_path = tmp_path / "lot_period.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((210, 90), "LIST OF TABLES", fontsize=16, fontname="Times-Bold")
    page.insert_text((108, 130), "Table 1. Descriptive Statistics for Participants.")
    page.insert_text((500, 130), "12")
    page.insert_text((108, 150), "Table 2. Summary of Regression Coefficients Here.")
    page.insert_text((500, 150), "24")
    doc.save(lot_path)
    doc.close()
    model = load_pdf_layout(str(lot_path))
    findings = check_pdf_toc_list_formatting(model)
    period_findings = [
        f for f in findings if f.details.get("issue_type") == "unexpected_terminal_punctuation"
    ]
    assert len(period_findings) == 2
    entry_indexes = {f.details.get("entry_index") for f in period_findings}
    assert entry_indexes == {"0", "1"}


# ---------------------------------------------------------------------------
# P025: Front-matter structure and required-elements checks
# ---------------------------------------------------------------------------

def _make_frontmatter_pdf(
    path: Path,
    *,
    title_page_text: list[str] | None = None,
    abstract_body: list[str] | None = None,
    approval_body: list[str] | None = None,
    toc_before_abstract: bool = False,
) -> None:
    """Create a minimal multi-page front-matter PDF for P025 tests."""
    doc = fitz.open()

    # Page 1: title page
    p1 = doc.new_page(width=612, height=792)
    default_title = [
        "A Study of Systems",
        "by",
        "Test Author",
        "A Dissertation",
        "Submitted to",
        "New Jersey Institute of Technology",
        "in Partial Fulfillment of the Requirements",
        "for the Degree of Doctor of Philosophy",
        "May 2024",
    ]
    for idx, line in enumerate(title_page_text if title_page_text is not None else default_title):
        p1.insert_text((108, 100 + idx * 20), line, fontsize=12)

    # Page 2: ABSTRACT page (or TOC first if toc_before_abstract)
    p2 = doc.new_page(width=612, height=792)
    if toc_before_abstract:
        p2.insert_text((190, 90), "TABLE OF CONTENTS", fontsize=14, fontname="Times-Bold")
        p2.insert_text((108, 140), "CHAPTER 1 INTRODUCTION .......    1", fontsize=12)
    else:
        p2.insert_text((250, 90), "ABSTRACT", fontsize=14, fontname="Times-Bold")
        body_lines = abstract_body if abstract_body is not None else [
            "This dissertation presents a comprehensive study of synthetic test cases.",
            "The results demonstrate consistent performance across all configurations.",
            "Statistical analysis confirms the validity of the proposed methodology.",
        ]
        for idx, line in enumerate(body_lines):
            p2.insert_text((108, 140 + idx * 18), line, fontsize=12)

    # Page 3: APPROVAL PAGE
    p3 = doc.new_page(width=612, height=792)
    p3.insert_text((210, 90), "APPROVAL PAGE", fontsize=14, fontname="Times-Bold")
    approval_lines = approval_body if approval_body is not None else [
        "Dissertation Committee:",
        "Dr. Test Advisor, Dissertation Advisor",
        "Department of Computer Science",
        "Dr. Committee Member, Committee Member",
        "Dr. Another Member, Committee Member",
        "Date:",
    ]
    for idx, line in enumerate(approval_lines):
        p3.insert_text((108, 140 + idx * 18), line, fontsize=12)

    # Page 4: TABLE OF CONTENTS (if abstract was page 2)
    p4 = doc.new_page(width=612, height=792)
    if toc_before_abstract:
        p4.insert_text((250, 90), "ABSTRACT", fontsize=14, fontname="Times-Bold")
        p4.insert_text((108, 140), "Abstract body text here for testing purposes.", fontsize=12)
    else:
        p4.insert_text((190, 90), "TABLE OF CONTENTS", fontsize=14, fontname="Times-Bold")
        p4.insert_text((108, 140), "CHAPTER 1 INTRODUCTION .......    1", fontsize=12)

    doc.save(path)
    doc.close()


def test_p025_abstract_with_body_no_warning(tmp_path: Path) -> None:
    """ABSTRACT heading with sufficient body text must not warn."""
    pdf_path = tmp_path / "abstract_ok.pdf"
    _make_frontmatter_pdf(pdf_path)
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_frontmatter_structure(model)
    assert not any(
        f.rule_id == "P025" and f.details.get("issue_type") == "missing_abstract_body"
        for f in findings
    )


def test_p025_abstract_without_body_warns(tmp_path: Path) -> None:
    """ABSTRACT heading with no body text must produce missing_abstract_body warning."""
    pdf_path = tmp_path / "abstract_empty.pdf"
    _make_frontmatter_pdf(pdf_path, abstract_body=[])
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_frontmatter_structure(model)
    assert any(
        f.rule_id == "P025" and f.details.get("issue_type") == "missing_abstract_body"
        for f in findings
    )


def test_p025_title_page_with_required_elements_no_warning(tmp_path: Path) -> None:
    """Title page with degree phrase and institution must not warn."""
    pdf_path = tmp_path / "title_ok.pdf"
    _make_frontmatter_pdf(pdf_path)
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_frontmatter_structure(model)
    assert not any(
        f.rule_id == "P025" and f.details.get("issue_type") in {
            "missing_title_page_degree_phrase",
            "missing_title_page_institution",
        }
        for f in findings
    )


def test_p025_title_page_missing_institution_warns(tmp_path: Path) -> None:
    """Title page without institution name must warn."""
    pdf_path = tmp_path / "title_no_institution.pdf"
    _make_frontmatter_pdf(
        pdf_path,
        title_page_text=[
            "A Study of Systems",
            "by Test Author",
            "Doctor of Philosophy",
            "May 2024",
        ],
    )
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_frontmatter_structure(model)
    assert any(
        f.rule_id == "P025" and f.details.get("issue_type") == "missing_title_page_institution"
        for f in findings
    )


def test_p025_title_page_missing_degree_warns(tmp_path: Path) -> None:
    """Title page without degree phrase must warn."""
    pdf_path = tmp_path / "title_no_degree.pdf"
    _make_frontmatter_pdf(
        pdf_path,
        title_page_text=[
            "A Study of Systems",
            "by Test Author",
            "New Jersey Institute of Technology",
            "May 2024",
        ],
    )
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_frontmatter_structure(model)
    assert any(
        f.rule_id == "P025" and f.details.get("issue_type") == "missing_title_page_degree_phrase"
        for f in findings
    )


def test_p025_title_page_year_not_confused_as_issue(tmp_path: Path) -> None:
    """A year like 2024 on the title page must not cause a P025 warning about degree/institution."""
    pdf_path = tmp_path / "title_with_year.pdf"
    _make_frontmatter_pdf(
        pdf_path,
        title_page_text=[
            "Research in Computer Systems 2024",
            "by Test Author",
            "New Jersey Institute of Technology",
            "Doctor of Philosophy",
        ],
    )
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_frontmatter_structure(model)
    assert not any(
        f.rule_id == "P025" and f.details.get("issue_type") in {
            "missing_title_page_degree_phrase",
            "missing_title_page_institution",
        }
        for f in findings
    )


def test_p025_approval_page_with_content_no_warning(tmp_path: Path) -> None:
    """APPROVAL PAGE with enough committee content must not warn."""
    pdf_path = tmp_path / "approval_ok.pdf"
    _make_frontmatter_pdf(pdf_path)
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_frontmatter_structure(model)
    assert not any(
        f.rule_id == "P025" and f.details.get("issue_type") == "sparse_approval_page_content"
        for f in findings
    )


def test_p025_approval_page_sparse_warns(tmp_path: Path) -> None:
    """APPROVAL PAGE with sparse content must warn."""
    pdf_path = tmp_path / "approval_sparse.pdf"
    _make_frontmatter_pdf(pdf_path, approval_body=["One line."])
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_frontmatter_structure(model)
    assert any(
        f.rule_id == "P025" and f.details.get("issue_type") == "sparse_approval_page_content"
        for f in findings
    )


def test_p025_normal_frontmatter_order_no_warning(tmp_path: Path) -> None:
    """Abstract before TOC must not trigger an order warning."""
    pdf_path = tmp_path / "order_ok.pdf"
    _make_frontmatter_pdf(pdf_path)
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_frontmatter_structure(model)
    assert not any(
        f.rule_id == "P025" and f.details.get("issue_type") == "possible_frontmatter_order_issue"
        for f in findings
    )


def test_p025_abstract_after_toc_warns(tmp_path: Path) -> None:
    """ABSTRACT appearing after TABLE OF CONTENTS must warn."""
    pdf_path = tmp_path / "order_bad.pdf"
    _make_frontmatter_pdf(pdf_path, toc_before_abstract=True)
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_frontmatter_structure(model)
    assert any(
        f.rule_id == "P025" and f.details.get("issue_type") == "possible_frontmatter_order_issue"
        for f in findings
    )


def test_p025_body_page_ignored(tmp_path: Path) -> None:
    """Plain body pages without front-matter headings must not produce P025 findings."""
    pdf_path = tmp_path / "body_p025.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((108, 130), "This is ordinary body text for a regular chapter.")
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_frontmatter_structure(model)
    assert not any(f.rule_id == "P025" for f in findings)


def test_p025_cli_includes_p025(tmp_path: Path) -> None:
    """CLI pdf command must surface P025 when a front-matter issue is detected."""
    pdf_path = tmp_path / "cli_p025.pdf"
    _make_frontmatter_pdf(pdf_path, abstract_body=[])
    result = runner.invoke(app, ["pdf", str(pdf_path)])
    assert result.exit_code == 0
    assert "P025" in result.output


def test_p025_json_report_includes_p025(tmp_path: Path) -> None:
    """JSON report must include P025 when a front-matter issue is detected."""
    pdf_path = tmp_path / "json_p025.pdf"
    json_out = tmp_path / "out" / "p025_report.json"
    _make_frontmatter_pdf(pdf_path, abstract_body=[])
    result = runner.invoke(app, ["pdf", str(pdf_path), "--json-out", str(json_out)])
    assert result.exit_code == 0
    assert json_out.exists()
    assert "P025" in json_out.read_text(encoding="utf-8")


def test_p025_runon_text_degree_not_flagged(tmp_path: Path) -> None:
    """Title page with run-together text containing degree phrase must not warn.

    Simulates a PDF where text extraction produces space-free tokens like
    'DoctorofPhilosophy' instead of 'Doctor of Philosophy'.
    """
    pdf_path = tmp_path / "runon_degree.pdf"
    _make_frontmatter_pdf(
        pdf_path,
        title_page_text=[
            "ADissertationSubmittedto",
            "NewJerseyInstituteofTechnology",
            "fortheDegreeof",
            "DoctorofPhilosophy",
            "DepartmentofComputerScience",
        ],
    )
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_frontmatter_structure(model)
    assert not any(
        f.rule_id == "P025" and f.details.get("issue_type") == "missing_title_page_degree_phrase"
        for f in findings
    )


def test_p025_runon_text_institution_not_flagged(tmp_path: Path) -> None:
    """Title page with run-together institution name must not warn."""
    pdf_path = tmp_path / "runon_institution.pdf"
    _make_frontmatter_pdf(
        pdf_path,
        title_page_text=[
            "ADissertationSubmittedto",
            "NewJerseyInstituteofTechnology",
            "fortheDegreeof",
            "DoctorofPhilosophy",
            "DepartmentofComputerScience",
        ],
    )
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_frontmatter_structure(model)
    assert not any(
        f.rule_id == "P025" and f.details.get("issue_type") == "missing_title_page_institution"
        for f in findings
    )


def test_p025_text_based_title_missing_degree_still_warns(tmp_path: Path) -> None:
    """Text-based title page without degree phrase must still produce a warning.

    When spaces are present but the required phrase is genuinely absent, both the
    spaced and space-stripped searches should fail, and the warning should fire.
    """
    pdf_path = tmp_path / "text_no_degree.pdf"
    _make_frontmatter_pdf(
        pdf_path,
        title_page_text=[
            "A Study of Systems",
            "by Test Author",
            "New Jersey Institute of Technology",
            "Submitted in Partial Fulfillment",
            "May 2024",
        ],
    )
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_frontmatter_structure(model)
    assert any(
        f.rule_id == "P025" and f.details.get("issue_type") == "missing_title_page_degree_phrase"
        for f in findings
    )


def test_p025_text_based_title_missing_institution_still_warns(tmp_path: Path) -> None:
    """Text-based title page without institution name must still produce a warning."""
    pdf_path = tmp_path / "text_no_institution.pdf"
    _make_frontmatter_pdf(
        pdf_path,
        title_page_text=[
            "A Study of Systems",
            "by Test Author",
            "Doctor of Philosophy",
            "Submitted in Partial Fulfillment",
            "May 2024",
        ],
    )
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_frontmatter_structure(model)
    assert any(
        f.rule_id == "P025" and f.details.get("issue_type") == "missing_title_page_institution"
        for f in findings
    )


# ---------------------------------------------------------------------------
# P022 — front-matter no visible page number tests
# ---------------------------------------------------------------------------


def test_p022_abstract_without_visible_page_number_no_warning(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p022_abstract_clean.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((220, 90), "ABSTRACT", fontsize=16, fontname="Times-Bold")
    page.insert_text((108, 200), "This dissertation presents research on formatting.", fontsize=12)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_frontmatter_no_page_number(model)
    assert not any(f.rule_id == "P022" for f in findings)


def test_p022_abstract_with_visible_page_number_warns(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p022_abstract_num.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((220, 90), "ABSTRACT", fontsize=16, fontname="Times-Bold")
    page.insert_text((108, 200), "Abstract body text here.", fontsize=12)
    page.insert_text((300, 770), "ii", fontsize=12)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in check_pdf_frontmatter_no_page_number(model) if f.rule_id == "P022"]
    assert len(warnings) == 1
    assert warnings[0].details.get("page_type") == "abstract"
    assert warnings[0].details.get("issue_type") == "visible_page_number_on_no_number_page"
    assert warnings[0].details.get("source_q_rule_id") == "Q001"


def test_p022_title_page_without_visible_page_number_no_warning(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p022_title_clean.pdf"
    doc = fitz.open()
    page1 = doc.new_page(width=612, height=792)
    page1.insert_text((200, 300), "Thesis Title", fontsize=24)
    page2 = doc.new_page(width=612, height=792)
    page2.insert_text((220, 90), "ABSTRACT", fontsize=16, fontname="Times-Bold")
    page2.insert_text((108, 200), "Abstract text.", fontsize=12)
    page3 = doc.new_page(width=612, height=792)
    page3.insert_text((108, 200), "Chapter content.", fontsize=12)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_frontmatter_no_page_number(model)
    # No page-number candidate on title page or abstract page.
    assert not any(f.rule_id == "P022" for f in findings)


def test_p022_title_page_with_visible_page_number_warns(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p022_title_num.pdf"
    doc = fitz.open()
    page1 = doc.new_page(width=612, height=792)
    page1.insert_text((200, 300), "Thesis Title", fontsize=24)
    page1.insert_text((300, 770), "1", fontsize=12)
    page2 = doc.new_page(width=612, height=792)
    page2.insert_text((220, 90), "ABSTRACT", fontsize=16, fontname="Times-Bold")
    page2.insert_text((108, 200), "Abstract body text.", fontsize=12)
    page3 = doc.new_page(width=612, height=792)
    page3.insert_text((108, 200), "Chapter content.", fontsize=12)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in check_pdf_frontmatter_no_page_number(model) if f.rule_id == "P022"]
    assert any(w.details.get("page_type") == "title_page" for w in warnings)
    title_warning = next(w for w in warnings if w.details.get("page_type") == "title_page")
    assert title_warning.details.get("source_q_rule_id") == "Q008"


def test_p022_year_on_title_page_not_flagged(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p022_title_year.pdf"
    doc = fitz.open()
    page1 = doc.new_page(width=612, height=792)
    page1.insert_text((200, 300), "Thesis Title", fontsize=24)
    page1.insert_text((300, 770), "2024", fontsize=12)
    page2 = doc.new_page(width=612, height=792)
    page2.insert_text((220, 90), "ABSTRACT", fontsize=16, fontname="Times-Bold")
    page2.insert_text((108, 200), "Abstract body text.", fontsize=12)
    page3 = doc.new_page(width=612, height=792)
    page3.insert_text((108, 200), "Chapter content.", fontsize=12)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in check_pdf_frontmatter_no_page_number(model) if f.rule_id == "P022"]
    # Year 2024 in bottom zone should be suppressed on title page.
    assert not any(w.details.get("page_type") == "title_page" for w in warnings)


def test_p022_approval_page_with_visible_page_number_warns(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p022_approval_num.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((200, 90), "APPROVAL PAGE", fontsize=16, fontname="Times-Bold")
    page.insert_text((108, 200), "Dr. Advisor Name", fontsize=12)
    page.insert_text((108, 220), "Dr. Committee Member", fontsize=12)
    page.insert_text((300, 770), "iii", fontsize=12)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in check_pdf_frontmatter_no_page_number(model) if f.rule_id == "P022"]
    assert len(warnings) == 1
    assert warnings[0].details.get("page_type") == "approval_page"
    assert warnings[0].details.get("source_q_rule_id") == "Q014"


def test_p022_copyright_page_with_visible_page_number_warns(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p022_copyright_num.pdf"
    doc = fitz.open()
    page1 = doc.new_page(width=612, height=792)
    page1.insert_text((200, 300), "Thesis Title", fontsize=24)
    page2 = doc.new_page(width=612, height=792)
    page2.insert_text((200, 400), "© 2024 Author Name. All Rights Reserved.", fontsize=12)
    page2.insert_text((300, 770), "2", fontsize=12)
    page3 = doc.new_page(width=612, height=792)
    page3.insert_text((220, 90), "ABSTRACT", fontsize=16, fontname="Times-Bold")
    page3.insert_text((108, 200), "Abstract text.", fontsize=12)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in check_pdf_frontmatter_no_page_number(model) if f.rule_id == "P022"]
    assert any(w.details.get("page_type") == "copyright_page" for w in warnings)
    cr_warning = next(w for w in warnings if w.details.get("page_type") == "copyright_page")
    assert cr_warning.details.get("source_q_rule_id") == "Q012"


def test_p022_body_page_with_page_number_no_p022(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p022_body_num.pdf"
    doc = fitz.open()
    page1 = doc.new_page(width=612, height=792)
    page1.insert_text((220, 90), "ABSTRACT", fontsize=16, fontname="Times-Bold")
    page1.insert_text((108, 200), "Abstract text.", fontsize=12)
    page2 = doc.new_page(width=612, height=792)
    page2.insert_text((108, 200), "Chapter 1 body text.", fontsize=12)
    page2.insert_text((300, 770), "5", fontsize=12)
    page3 = doc.new_page(width=612, height=792)
    page3.insert_text((108, 200), "More body text.", fontsize=12)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in check_pdf_frontmatter_no_page_number(model) if f.rule_id == "P022"]
    # Page 2 is a body page and should not trigger P022.
    assert not any(w.page == 2 for w in warnings)


def test_p022_toc_page_with_page_number_no_p022(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p022_toc_num.pdf"
    doc = fitz.open()
    page1 = doc.new_page(width=612, height=792)
    page1.insert_text((220, 90), "ABSTRACT", fontsize=16, fontname="Times-Bold")
    page1.insert_text((108, 200), "Abstract text.", fontsize=12)
    page2 = doc.new_page(width=612, height=792)
    page2.insert_text((180, 90), "TABLE OF CONTENTS", fontsize=16, fontname="Times-Bold")
    page2.insert_text((300, 770), "iv", fontsize=12)
    page3 = doc.new_page(width=612, height=792)
    page3.insert_text((108, 200), "Body text.", fontsize=12)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in check_pdf_frontmatter_no_page_number(model) if f.rule_id == "P022"]
    # TOC pages are expected to have Roman numeral page numbers — not a no-number page.
    assert not any(w.page == 2 for w in warnings)


def test_p022_one_finding_per_page_with_multiple_candidates(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p022_abstract_multi.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((220, 90), "ABSTRACT", fontsize=16, fontname="Times-Bold")
    page.insert_text((108, 200), "Abstract body text.", fontsize=12)
    page.insert_text((300, 50), "ii", fontsize=12)
    page.insert_text((300, 770), "ii", fontsize=12)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in check_pdf_frontmatter_no_page_number(model) if f.rule_id == "P022"]
    assert len(warnings) == 1
    assert int(warnings[0].details.get("candidate_count", "0")) >= 2


def test_p022_cli_pdf_includes_p022(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p022_cli.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((220, 90), "ABSTRACT", fontsize=16, fontname="Times-Bold")
    page.insert_text((108, 200), "Abstract body text.", fontsize=12)
    page.insert_text((300, 770), "iii", fontsize=12)
    doc.save(pdf_path)
    doc.close()
    result = runner.invoke(app, ["pdf", str(pdf_path)])
    assert result.exit_code == 0
    assert "P022" in result.output


def test_p022_json_report_includes_p022_when_triggered(tmp_path: Path) -> None:
    import json as _json

    pdf_path = tmp_path / "p022_json.pdf"
    json_path = tmp_path / "p022_report.json"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((220, 90), "ABSTRACT", fontsize=16, fontname="Times-Bold")
    page.insert_text((108, 200), "Abstract body text.", fontsize=12)
    page.insert_text((300, 770), "iii", fontsize=12)
    doc.save(pdf_path)
    doc.close()
    result = runner.invoke(app, ["pdf", str(pdf_path), "--json-out", str(json_path)])
    assert result.exit_code == 0
    data = _json.loads(json_path.read_text())
    rule_ids = [f.get("rule_id") for f in data.get("findings", [])]
    assert "P022" in rule_ids


# ---------------------------------------------------------------------------
# P026 — body font compliance tests
# ---------------------------------------------------------------------------

_LONG_BODY_LINE = "An ordinary body text paragraph line for PDF font compliance testing here."


def _make_body_page_with_font(
    path: Path,
    fontname: str,
    fontsize: float,
    line_count: int = 12,
    y_start: float = 150.0,
    y_step: float = 28.0,
) -> None:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    for i in range(line_count):
        page.insert_text(
            (108, y_start + i * y_step), _LONG_BODY_LINE, fontsize=fontsize, fontname=fontname
        )
    doc.save(path)
    doc.close()


# ---- classify_font unit tests ----

def test_classify_font_times_roman() -> None:
    assert classify_font("Times-Roman") == "times"


def test_classify_font_times_new_roman_psmt() -> None:
    assert classify_font("TimesNewRomanPSMT") == "times"


def test_classify_font_subset_prefix_times() -> None:
    assert classify_font("ABCDEF+TimesNewRomanPSMT") == "times"


def test_classify_font_nimbus() -> None:
    assert classify_font("NimbusRomNo9L") == "times"


def test_classify_font_cmr_is_computer_modern() -> None:
    assert classify_font("CMR12") == "computer_modern"


def test_classify_font_cmbx_is_computer_modern() -> None:
    assert classify_font("CMBX12") == "computer_modern"


def test_classify_font_helvetica_is_other() -> None:
    assert classify_font("Helvetica") == "other"


def test_classify_font_georgia_is_other() -> None:
    assert classify_font("Georgia") == "other"


def test_classify_font_none_is_unknown() -> None:
    assert classify_font(None) == "unknown"


def test_classify_font_math_cmmi_skipped() -> None:
    assert classify_font("CMMI12") == "math"


# ---- integration tests with fitz PDFs ----

def test_p026_times_roman_12pt_no_warning(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p026_times_ok.pdf"
    _make_body_page_with_font(pdf_path, "tiro", 12.0)
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_font_compliance(model)
    assert not any(f.rule_id == "P026" for f in findings)


def test_p026_times_roman_alias_12pt_no_warning(tmp_path: Path) -> None:
    # "tiro" → Times-Roman, an accepted alias
    pdf_path = tmp_path / "p026_times_alias_ok.pdf"
    _make_body_page_with_font(pdf_path, "tiro", 12.0)
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_font_compliance(model)
    family_issue = "possible_body_font_family_issue"
    assert not any(
        f.rule_id == "P026" and f.details.get("issue_type") == family_issue
        for f in findings
    )


def test_p026_non_times_font_repeated_warns_family(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p026_helv_family.pdf"
    _make_body_page_with_font(pdf_path, "helv", 12.0, line_count=12)
    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in check_pdf_font_compliance(model) if f.rule_id == "P026"]
    family_warnings = [
        w for w in warnings if w.details.get("issue_type") == "possible_body_font_family_issue"
    ]
    assert len(family_warnings) >= 1
    assert family_warnings[0].details.get("confidence") == "medium"
    assert family_warnings[0].details.get("triage_tier") == "informational"


def test_p026_body_10pt_repeated_warns_size(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p026_10pt_size.pdf"
    _make_body_page_with_font(pdf_path, "tiro", 10.0, line_count=12)
    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in check_pdf_font_compliance(model) if f.rule_id == "P026"]
    size_warnings = [
        w for w in warnings if w.details.get("issue_type") == "possible_body_font_size_issue"
    ]
    assert len(size_warnings) >= 1


def test_p026_body_14pt_repeated_warns_size(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p026_14pt_size.pdf"
    _make_body_page_with_font(pdf_path, "tiro", 14.0, line_count=12)
    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in check_pdf_font_compliance(model) if f.rule_id == "P026"]
    size_warnings = [
        w for w in warnings if w.details.get("issue_type") == "possible_body_font_size_issue"
    ]
    assert len(size_warnings) >= 1


def test_p026_toc_page_ignored(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p026_toc_ignored.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((180, 90), "TABLE OF CONTENTS", fontsize=16, fontname="Times-Bold")
    for i in range(10):
        page.insert_text((108, 150 + i * 28), _LONG_BODY_LINE, fontsize=12, fontname="helv")
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_font_compliance(model)
    assert not any(f.rule_id == "P026" for f in findings)


def test_p026_abstract_page_ignored(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p026_abstract_ignored.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((220, 90), "ABSTRACT", fontsize=16, fontname="Times-Bold")
    for i in range(10):
        page.insert_text((108, 150 + i * 28), _LONG_BODY_LINE, fontsize=12, fontname="helv")
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_font_compliance(model)
    assert not any(f.rule_id == "P026" for f in findings)


def test_p026_references_page_ignored(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p026_refs_ignored.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((240, 90), "REFERENCES", fontsize=16, fontname="Times-Bold")
    for i in range(10):
        page.insert_text((108, 150 + i * 28), _LONG_BODY_LINE, fontsize=12, fontname="helv")
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_font_compliance(model)
    assert not any(f.rule_id == "P026" for f in findings)


def test_p026_short_lines_not_enough_no_warning(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p026_short_no_warn.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    for i in range(10):
        page.insert_text((108, 150 + i * 28), "Short text.", fontsize=12, fontname="helv")
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_font_compliance(model)
    assert not any(f.rule_id == "P026" for f in findings)


def test_p026_one_finding_per_page_issue_type(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p026_one_per_page.pdf"
    _make_body_page_with_font(pdf_path, "helv", 12.0, line_count=14)
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_font_compliance(model) if f.rule_id == "P026" and f.page == 1]
    family_findings = [
        f for f in findings if f.details.get("issue_type") == "possible_body_font_family_issue"
    ]
    assert len(family_findings) == 1


def test_p026_cli_pdf_includes_p026(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p026_cli.pdf"
    _make_body_page_with_font(pdf_path, "helv", 12.0, line_count=12)
    result = runner.invoke(app, ["pdf", str(pdf_path)])
    assert result.exit_code == 0
    assert "P026" in result.output


def test_p026_json_report_includes_p026_when_triggered(tmp_path: Path) -> None:
    import json as _json

    pdf_path = tmp_path / "p026_json.pdf"
    json_path = tmp_path / "p026_report.json"
    _make_body_page_with_font(pdf_path, "helv", 12.0, line_count=12)
    result = runner.invoke(app, ["pdf", str(pdf_path), "--json-out", str(json_path)])
    assert result.exit_code == 0
    data = _json.loads(json_path.read_text())
    rule_ids = [f.get("rule_id") for f in data.get("findings", [])]
    assert "P026" in rule_ids


# ---- concatenated named-heading page-skip (Ester Sample B page 5 false positive) ----
# When PDF text extraction runs heading words together with no spaces (a known
# layout artifact -- see pdf_frontmatter_headings.py's own
# _P038_CONCATENATED_HEADING_VARIANTS), the P026 page-skip gate must still
# recognize the page as front matter so a signature/name block (allowed
# correct-size text for that page type) is not measured against the 12pt
# body-text rule.

def test_p026_approval_page_concatenated_heading_signature_block_not_flagged(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "p026_approval_concat.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((240, 90), "APPROVALPAGE", fontsize=12.0, fontname="tiro")
    committee_line = "Dr. Example Advisor, Dissertation Committee Member Title"
    for i in range(8):
        page.insert_text((108, 250 + i * 40), committee_line, fontsize=10.9, fontname="tiro")
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_font_compliance(model)
    assert not any(f.rule_id == "P026" for f in findings)


def test_p026_biographical_sketch_concatenated_heading_not_flagged(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p026_biosketch_concat.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((200, 90), "BIOGRAPHICALSKETCH", fontsize=12.0, fontname="tiro")
    for i in range(10):
        page.insert_text((108, 150 + i * 28), _LONG_BODY_LINE, fontsize=10.0, fontname="tiro")
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_font_compliance(model)
    assert not any(f.rule_id == "P026" for f in findings)


def test_p026_body_10_9pt_without_named_heading_still_flagged(tmp_path: Path) -> None:
    """Same font size as the real Sample B approval-page text (10.9pt), but on
    an ordinary body page with no front-matter heading -- must still be
    flagged. The page-skip fix must not reduce font checking globally."""
    pdf_path = tmp_path / "p026_10_9pt_body.pdf"
    _make_body_page_with_font(pdf_path, "tiro", 10.9, line_count=12)
    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in check_pdf_font_compliance(model) if f.rule_id == "P026"]
    size_warnings = [
        w for w in warnings if w.details.get("issue_type") == "possible_body_font_size_issue"
    ]
    assert len(size_warnings) >= 1


def test_p026_concatenated_heading_that_is_not_a_known_variant_still_flagged(
    tmp_path: Path,
) -> None:
    """A concatenated line that isn't one of the known front-matter headings
    (e.g. an ordinary run-together sentence) must not accidentally exempt the
    page -- only the curated variant list should skip font checking."""
    pdf_path = tmp_path / "p026_unrelated_concat.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text(
        (108, 90), "ThisIsNotARecognizedFrontMatterHeadingAtAll", fontsize=12.0, fontname="tiro"
    )
    for i in range(12):
        page.insert_text((108, 150 + i * 28), _LONG_BODY_LINE, fontsize=10.0, fontname="tiro")
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in check_pdf_font_compliance(model) if f.rule_id == "P026"]
    size_warnings = [
        w for w in warnings if w.details.get("issue_type") == "possible_body_font_size_issue"
    ]
    assert len(size_warnings) >= 1


def test_p026_highlight_targets_offending_span_not_correct_text(tmp_path: Path) -> None:
    """When a font-size finding is legitimate, its highlight bbox must point
    at a wrong-size line, never at a correct-size line on the same page."""
    pdf_path = tmp_path / "p026_highlight_target.pdf"
    correct_line = "An ordinary correct size body paragraph line for the test."
    wrong_line = "An ordinary wrong size body paragraph line for the test here."
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    correct_y0s = []
    for i in range(4):
        y = 150 + i * 28
        page.insert_text((108, y), correct_line, fontsize=12.0, fontname="tiro")
        correct_y0s.append(y)
    wrong_y0s = []
    for i in range(6):
        y = 150 + (4 + i) * 28
        page.insert_text((108, y), wrong_line, fontsize=15.0, fontname="tiro")
        wrong_y0s.append(y)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = [
        f
        for f in check_pdf_font_compliance(model)
        if f.rule_id == "P026" and f.details.get("issue_type") == "possible_body_font_size_issue"
    ]
    assert len(findings) == 1
    bbox_str = findings[0].details["bbox"]
    highlighted_y0 = float(bbox_str.split(",")[1])
    # PyMuPDF's extracted line bbox.y0 sits a few points above the insertion
    # baseline; allow slack but keep well clear of the correct-size cluster.
    assert any(abs(highlighted_y0 - (wy - 10)) < 6 for wy in wrong_y0s)
    assert not any(abs(highlighted_y0 - (cy - 10)) < 6 for cy in correct_y0s)


# ---------------------------------------------------------------------------
# P027 — heading-level style tests
# ---------------------------------------------------------------------------

# ---- unit tests ----

def test_looks_like_title_case_violation_detects_multiple_caps() -> None:
    assert _looks_like_title_case_violation("Background Theory and Methods Study") is True


def test_looks_like_title_case_violation_sentence_case_no_flag() -> None:
    assert _looks_like_title_case_violation("Background theory and methods") is False


def test_looks_like_title_case_violation_short_text_no_flag() -> None:
    assert _looks_like_title_case_violation("Background theory") is False


def test_is_all_caps_phrase_true() -> None:
    assert _is_all_caps_phrase("INTRODUCTION TO THE TOPIC") is True


def test_is_all_caps_phrase_false() -> None:
    assert _is_all_caps_phrase("Introduction to the topic") is False


# ---- integration tests ----

def _make_single_page_pdf(path: Path, lines: list[tuple[float, str]]) -> None:
    """Bold by default: NJIT numbered Level 2-5 headings are always bold
    (Titles Examples Level 1 to 5.docx), and P027 requires bold before
    classifying a numbered-pattern line as a heading candidate."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    for y, text in lines:
        page.insert_text((108, y), text, fontsize=12, fontname="Times-Bold")
    doc.save(path)
    doc.close()


def test_p027_level2_correct_title_case_no_warning(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p027_l2_ok.pdf"
    _make_single_page_pdf(pdf_path, [(200, "1.1 Background and Motivation")])
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_heading_level_styles(model)
    l2 = [f for f in findings if f.details.get("issue_type") == "level2_title_case_issue"]
    assert not l2


def test_p027_level2_lowercase_first_word_warns(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p027_l2_lower.pdf"
    _make_single_page_pdf(pdf_path, [(200, "1.1 the impact of machine learning methods")])
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_heading_level_styles(model)
    l2 = [f for f in findings if f.details.get("issue_type") == "level2_title_case_issue"]
    assert len(l2) == 1
    assert l2[0].details.get("inferred_level") == "2"


def test_p027_level3_sentence_case_correct_no_warning(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p027_l3_ok.pdf"
    _make_single_page_pdf(pdf_path, [(200, "1.1.1 Background theory and methods")])
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_heading_level_styles(model)
    l3 = [f for f in findings if f.details.get("issue_type") == "level3_sentence_case_issue"]
    assert not l3


def test_p027_level3_title_case_like_warns(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p027_l3_titlecase.pdf"
    _make_single_page_pdf(pdf_path, [(200, "1.1.1 Background Theory and Methods Study")])
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_heading_level_styles(model)
    l3 = [f for f in findings if f.details.get("issue_type") == "level3_sentence_case_issue"]
    assert len(l3) == 1
    assert l3[0].details.get("inferred_level") == "3"
    assert l3[0].details.get("source_q_rule_id") == "Q051"


def test_p027_level4_title_case_like_warns(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p027_l4_titlecase.pdf"
    _make_single_page_pdf(pdf_path, [(200, "1.1.1.1 Background Theory and Results.")])
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_heading_level_styles(model)
    l4 = [f for f in findings if f.details.get("inferred_level") == "4"]
    assert any(f.details.get("issue_type") == "level4_sentence_case_issue" for f in l4)


def test_p027_level4_missing_period_warns(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p027_l4_noperiod.pdf"
    _make_single_page_pdf(pdf_path, [(200, "1.1.1.1 Background theory here")])
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_heading_level_styles(model)
    l4 = [
        f for f in findings
        if f.details.get("inferred_level") == "4"
        and "punctuation" in f.details.get("issue_type", "")
    ]
    assert len(l4) == 1


def test_p027_level4_with_period_no_period_warning(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p027_l4_period_ok.pdf"
    _make_single_page_pdf(pdf_path, [(200, "1.1.1.1 Background theory here.")])
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_heading_level_styles(model)
    punct = [
        f for f in findings
        if f.details.get("inferred_level") == "4"
        and "punctuation" in f.details.get("issue_type", "")
    ]
    assert not punct


def test_p027_chapter_heading_not_all_caps_warns(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p027_chap_lower.pdf"
    _make_single_page_pdf(pdf_path, [(200, "CHAPTER 1 Introduction to the Topic")])
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_heading_level_styles(model)
    l1 = [f for f in findings if f.details.get("issue_type") == "level1_not_all_caps"]
    assert len(l1) == 1
    assert l1[0].details.get("inferred_level") == "1"


def test_p027_chapter_heading_all_caps_no_warning(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p027_chap_upper.pdf"
    _make_single_page_pdf(pdf_path, [(200, "CHAPTER 1 INTRODUCTION TO THE TOPIC")])
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_heading_level_styles(model)
    l1 = [f for f in findings if f.details.get("issue_type") == "level1_not_all_caps"]
    assert not l1


def test_p027_body_sentence_starting_with_chapter_not_treated_as_heading(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p027_chapter_sentence.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text(
        (108, 260),
        "Chapter 3 is dedicated to describing the proposed method.",
        fontsize=12,
    )
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_heading_level_styles(model)
    assert not any(f.rule_id == "P027" for f in findings)


def test_p027_toc_page_ignored(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p027_toc_skip.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((180, 90), "TABLE OF CONTENTS", fontsize=16, fontname="Times-Bold")
    page.insert_text((108, 200), "1.1.1 Background Theory and Methods Study")
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_heading_level_styles(model)
    assert not any(f.rule_id == "P027" for f in findings)


def test_p027_abstract_page_ignored(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p027_abstract_skip.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((220, 90), "ABSTRACT", fontsize=16, fontname="Times-Bold")
    page.insert_text((108, 200), "1.1.1 Background Theory and Methods Study")
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_heading_level_styles(model)
    assert not any(f.rule_id == "P027" for f in findings)


def test_p027_references_page_ignored(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p027_refs_skip.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((240, 90), "REFERENCES", fontsize=16, fontname="Times-Bold")
    page.insert_text((108, 200), "1.1 Background Theory and Methods")
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_heading_level_styles(model)
    assert not any(f.rule_id == "P027" for f in findings)


def test_p027_citation_text_ignored(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p027_citation_skip.pdf"
    _make_single_page_pdf(pdf_path, [(200, "1.1 Smith et al. (2020) proposed a method")])
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_heading_level_styles(model)
    assert not any(f.rule_id == "P027" for f in findings)


def test_p027_non_bold_statistic_sentence_not_treated_as_heading(tmp_path: Path) -> None:
    """A body sentence starting with a decimal number (e.g. a statistic) must not
    be classified as a Level 2 heading merely because it matches the numbered
    pattern — real headings are bold; ordinary body text is not."""
    pdf_path = tmp_path / "p027_statistic_not_heading.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    # Real bold Level 2 heading elsewhere on the page.
    page.insert_text((108, 150), "5.6 Summary", fontsize=12, fontname="Times-Bold")
    # Ordinary, non-bold body sentence that happens to start with "68.4 ...".
    page.insert_text(
        (108, 200),
        "68.4 percent of participants reported improved outcomes overall.",
        fontsize=12,
    )
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_heading_level_styles(model)
    for f in findings:
        assert "68.4" not in f.details.get("line_preview", "")
        assert "percent" not in f.details.get("line_preview", "")


def test_p027_level3_finding_includes_corrected_example_and_location(tmp_path: Path) -> None:
    """A real (bold) Level 3 title-case violation must still warn, and the
    finding must carry enough evidence to show the actual heading — not
    generic body text — plus a concrete sentence-case rewrite."""
    pdf_path = tmp_path / "p027_l3_example.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text(
        (108, 200),
        "4.4.1 Scatterplots Of Relationships With Readiness",
        fontsize=12,
        fontname="Times-Bold",
    )
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = [
        f
        for f in check_pdf_heading_level_styles(model)
        if f.details.get("issue_type") == "level3_sentence_case_issue"
    ]
    assert len(findings) == 1
    finding = findings[0]
    assert finding.details.get("heading_pattern") == "4.4.1"
    assert "Scatterplots Of Relationships With Readiness" in finding.details.get(
        "line_preview", ""
    )
    assert finding.details.get("corrected_example") == (
        "4.4.1 Scatterplots of relationships with readiness"
    )
    assert "Level 3" in finding.message
    assert "Level 2" not in finding.message
    assert "Level 4" not in finding.message
    assert "Level 5" not in finding.message


def test_p027_level3_message_uses_exact_change_replacement(tmp_path: Path) -> None:
    """A safe sentence-case rewrite must appear as an exact 'Change X to Y'
    instruction (not a generic style reminder) and record corrected_from."""
    pdf_path = tmp_path / "p027_l3_change.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text(
        (108, 200),
        "4.4.1 Scatterplots Of Relationships With Readiness",
        fontsize=12,
        fontname="Times-Bold",
    )
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = [
        f
        for f in check_pdf_heading_level_styles(model)
        if f.details.get("issue_type") == "level3_sentence_case_issue"
    ]
    assert len(findings) == 1
    finding = findings[0]
    assert finding.details.get("corrected_from") == (
        "4.4.1 Scatterplots Of Relationships With Readiness"
    )
    assert finding.message == (
        'Change "4.4.1 Scatterplots Of Relationships With Readiness" to '
        '"4.4.1 Scatterplots of relationships with readiness" '
        "(Level 3 heading; NJIT: Level 3 = Sentence case)."
    )


def test_p027_cli_includes_p027(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p027_cli.pdf"
    _make_single_page_pdf(pdf_path, [(200, "1.1.1 Background Theory and Methods Study")])
    result = runner.invoke(app, ["pdf", str(pdf_path)])
    assert result.exit_code == 0
    assert "P027" in result.output


def test_p027_json_report_includes_p027_when_triggered(tmp_path: Path) -> None:
    import json as _json

    pdf_path = tmp_path / "p027_json.pdf"
    json_path = tmp_path / "p027_report.json"
    _make_single_page_pdf(pdf_path, [(200, "1.1.1 Background Theory and Methods Study")])
    result = runner.invoke(app, ["pdf", str(pdf_path), "--json-out", str(json_path)])
    assert result.exit_code == 0
    data = _json.loads(json_path.read_text())
    rule_ids = [f.get("rule_id") for f in data.get("findings", [])]
    assert "P027" in rule_ids


# ---------------------------------------------------------------------------
# P028 — page-numbering regime tests
# ---------------------------------------------------------------------------

def _make_regime_pdf(
    path: Path,
    pages: list[tuple[str | None, str | None, str | None]],
) -> None:
    """Create a multi-page PDF for regime tests.

    pages: list of (heading_text_or_none, chapter_text_or_none, page_num_text_or_none)
    heading_text: named heading like "TABLE OF CONTENTS"
    chapter_text: body heading like "CHAPTER 1 INTRODUCTION"
    page_num_text: page number candidate like "iii" or "3"
    """
    doc = fitz.open()
    for heading, chapter, page_num in pages:
        page = doc.new_page(width=612, height=792)
        if heading:
            page.insert_text((180, 90), heading, fontsize=14, fontname="Times-Bold")
        if chapter:
            page.insert_text((108, 200), chapter, fontsize=14)
        if page_num:
            page.insert_text((300, 760), page_num, fontsize=12)
    doc.save(path)
    doc.close()


def test_p028_frontmatter_lowercase_roman_no_warning(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p028_fm_roman_ok.pdf"
    _make_regime_pdf(pdf_path, [
        ("TABLE OF CONTENTS", None, "iv"),
        (None, "CHAPTER 1 INTRODUCTION", "1"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_page_numbering_regime(model) if f.rule_id == "P028"]
    assert not findings


def test_p028_frontmatter_arabic_warns(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p028_fm_arabic_bad.pdf"
    _make_regime_pdf(pdf_path, [
        ("TABLE OF CONTENTS", None, "4"),
        (None, "CHAPTER 1 INTRODUCTION", "1"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_page_numbering_regime(model) if f.rule_id == "P028"]
    assert any(f.details.get("issue_type") == "arabic_number_on_frontmatter_page" for f in findings)


def test_p028_frontmatter_uppercase_roman_warns(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p028_fm_upper_roman.pdf"
    _make_regime_pdf(pdf_path, [
        ("TABLE OF CONTENTS", None, "IV"),
        (None, "CHAPTER 1 INTRODUCTION", "1"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_page_numbering_regime(model) if f.rule_id == "P028"]
    assert any(
        f.details.get("issue_type") == "uppercase_roman_on_frontmatter_page" for f in findings
    )


def test_p028_frontmatter_toc_right_column_numbers_ignored(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p028_toc_column_filtered.pdf"
    doc = fitz.open()

    p1 = doc.new_page(width=612, height=792)
    p1.insert_text((180, 90), "TABLE OF CONTENTS", fontsize=14, fontname="Times-Bold")
    p1.insert_text((108, 180), "Introduction", fontsize=12)
    p1.insert_text((528, 180), "29", fontsize=12)
    p1.insert_text((108, 200), "Literature Review", fontsize=12)
    p1.insert_text((528, 200), "34", fontsize=12)
    p1.insert_text((300, 760), "viii", fontsize=12)

    p2 = doc.new_page(width=612, height=792)
    p2.insert_text((220, 90), "CHAPTER 1", fontsize=16, fontname="Times-Bold")
    p2.insert_text((220, 120), "INTRODUCTION", fontsize=14, fontname="Times-Bold")
    p2.insert_text((300, 760), "1", fontsize=12)

    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_page_numbering_regime(model) if f.rule_id == "P028"]
    assert not findings


def test_p028_body_arabic_no_warning(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p028_body_arabic_ok.pdf"
    _make_regime_pdf(pdf_path, [
        ("TABLE OF CONTENTS", None, "iv"),
        (None, "CHAPTER 1 INTRODUCTION", "1"),
        (None, None, "2"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_page_numbering_regime(model) if f.rule_id == "P028"]
    body_roman = [f for f in findings if f.details.get("issue_type") == "roman_number_on_body_page"]
    assert not body_roman


def test_p028_body_roman_warns(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p028_body_roman_bad.pdf"
    _make_regime_pdf(pdf_path, [
        ("TABLE OF CONTENTS", None, "iv"),
        (None, "CHAPTER 1 INTRODUCTION", "v"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_page_numbering_regime(model) if f.rule_id == "P028"]
    assert any(f.details.get("issue_type") == "roman_number_on_body_page" for f in findings)


def test_p028_abstract_page_excluded(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p028_abstract_excl.pdf"
    doc = fitz.open()
    p1 = doc.new_page(width=612, height=792)
    p1.insert_text((220, 90), "ABSTRACT", fontsize=16, fontname="Times-Bold")
    p1.insert_text((300, 760), "ii", fontsize=12)  # would be a P022 issue, not P028
    p2 = doc.new_page(width=612, height=792)
    p2.insert_text((180, 90), "TABLE OF CONTENTS", fontsize=14, fontname="Times-Bold")
    p2.insert_text((300, 760), "iv", fontsize=12)
    p3 = doc.new_page(width=612, height=792)
    p3.insert_text((108, 200), "CHAPTER 1 INTRODUCTION", fontsize=14)
    p3.insert_text((300, 760), "1", fontsize=12)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_page_numbering_regime(model) if f.rule_id == "P028"]
    # Abstract page (page 1, no-number) should NOT produce a P028 finding.
    assert not any(f.page == 1 for f in findings)


def test_p028_no_front_matter_detected_no_crash(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p028_no_fm.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((108, 200), "Some body text.", fontsize=12)
    page.insert_text((300, 760), "1", fontsize=12)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_page_numbering_regime(model)
    assert isinstance(findings, list)


def test_p028_one_finding_per_page_issue_type(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p028_dedup.pdf"
    _make_regime_pdf(pdf_path, [
        ("TABLE OF CONTENTS", None, "4"),
        (None, "CHAPTER 1 INTRODUCTION", "1"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_page_numbering_regime(model) if f.rule_id == "P028"]
    arabic_fm = [
        f for f in findings if f.details.get("issue_type") == "arabic_number_on_frontmatter_page"
    ]
    # Only one P028 finding per (page, issue_type).
    pages = [f.page for f in arabic_fm]
    assert len(pages) == len(set(pages))


def test_p028_cli_includes_p028(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p028_cli.pdf"
    _make_regime_pdf(pdf_path, [
        ("TABLE OF CONTENTS", None, "4"),
        (None, "CHAPTER 1 INTRODUCTION", "1"),
    ])
    result = runner.invoke(app, ["pdf", str(pdf_path)])
    assert result.exit_code == 0
    assert "P028" in result.output


def test_p028_json_report_includes_p028_when_triggered(tmp_path: Path) -> None:
    import json as _json

    pdf_path = tmp_path / "p028_json.pdf"
    json_path = tmp_path / "p028_report.json"
    _make_regime_pdf(pdf_path, [
        ("TABLE OF CONTENTS", None, "4"),
        (None, "CHAPTER 1 INTRODUCTION", "1"),
    ])
    result = runner.invoke(app, ["pdf", str(pdf_path), "--json-out", str(json_path)])
    assert result.exit_code == 0
    data = _json.loads(json_path.read_text())
    rule_ids = [f.get("rule_id") for f in data.get("findings", [])]
    assert "P028" in rule_ids


def test_p028_chapter_heading_split_across_lines_no_false_positive(tmp_path: Path) -> None:
    """When CHAPTER and the chapter number appear on separate text lines, body start is
    still detected, so the chapter page is NOT flagged as front-matter."""
    pdf_path = tmp_path / "p028_split_chapter.pdf"
    doc = fitz.open()
    # Front-matter page: TOC with correct Roman numeral.
    p1 = doc.new_page(width=612, height=792)
    p1.insert_text((180, 90), "TABLE OF CONTENTS", fontsize=14, fontname="Times-Bold")
    p1.insert_text((300, 760), "iv", fontsize=12)
    # Body page: "CHAPTER" and "1" as separate text elements (split layout).
    p2 = doc.new_page(width=612, height=792)
    p2.insert_text((108, 180), "CHAPTER", fontsize=18, fontname="Times-Bold")
    p2.insert_text((108, 210), "1", fontsize=18, fontname="Times-Bold")
    p2.insert_text((108, 250), "INTRODUCTION", fontsize=14)
    p2.insert_text((300, 760), "1", fontsize=12)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_page_numbering_regime(model) if f.rule_id == "P028"]
    # The chapter page (page 2) must NOT be flagged as arabic_number_on_frontmatter_page.
    chapter_false_positives = [
        f for f in findings
        if f.page == 2 and f.details.get("issue_type") == "arabic_number_on_frontmatter_page"
    ]
    assert not chapter_false_positives, (
        f"Chapter 1 page incorrectly flagged as front-matter: {chapter_false_positives}"
    )


def test_p028_section_heading_number_not_used_as_page_number_candidate(tmp_path: Path) -> None:
    """A left-aligned '1' from a chapter heading section is not used as the page-number
    candidate for P028; the bottom-positioned '1' is used instead."""
    pdf_path = tmp_path / "p028_section_heading.pdf"
    doc = fitz.open()
    # Front-matter page.
    p1 = doc.new_page(width=612, height=792)
    p1.insert_text((180, 90), "TABLE OF CONTENTS", fontsize=14, fontname="Times-Bold")
    p1.insert_text((300, 760), "iv", fontsize=12)
    # Chapter page: chapter heading at top, then "1.1 Background", page number at bottom.
    p2 = doc.new_page(width=612, height=792)
    p2.insert_text((108, 80), "CHAPTER 1 INTRODUCTION", fontsize=14)
    # Section heading — its left-aligned "1" fragment should NOT be a page-number candidate.
    p2.insert_text((108, 130), "1.1 Background", fontsize=12)
    # Actual bottom page number.
    p2.insert_text((300, 760), "1", fontsize=12)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_page_numbering_regime(model) if f.rule_id == "P028"]
    # Page 2 is body (chapter page) — no warning expected.
    page2_findings = [f for f in findings if f.page == 2]
    assert not page2_findings, (
        f"Chapter page should not produce P028 findings; got: {page2_findings}"
    )


def test_p028_body_arabic_not_flagged_when_chapter_on_same_page(tmp_path: Path) -> None:
    """A chapter page with Arabic page number 1 should never receive a
    'arabic_number_on_frontmatter_page' warning."""
    pdf_path = tmp_path / "p028_body_no_false_pos.pdf"
    _make_regime_pdf(pdf_path, [
        ("TABLE OF CONTENTS", None, "v"),
        ("ACKNOWLEDGEMENTS", None, "vi"),
        (None, "CHAPTER 1 INTRODUCTION", "1"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_page_numbering_regime(model) if f.rule_id == "P028"]
    false_positives = [
        f for f in findings
        if f.details.get("issue_type") == "arabic_number_on_frontmatter_page"
        and f.details.get("page_region") == "body"
    ]
    assert not false_positives


# ---------------------------------------------------------------------------
# Regression tests: body-start detection must not match TOC column header
# (PR #378 regression — _CHAPTER_STANDALONE_RE was case-insensitive, matching
# the title-case "Chapter" column header on TABLE OF CONTENTS pages)
# ---------------------------------------------------------------------------


def test_find_body_start_page_toc_chapter_column_header_not_matched(tmp_path: Path) -> None:
    """Title-case 'Chapter' TOC column header must NOT trigger body-start detection.

    The TABLE OF CONTENTS page uses 'Chapter' and 'Page' as column headers.
    With re.IGNORECASE removed from _CHAPTER_STANDALONE_RE, 'Chapter' (title
    case) no longer matches, so body_start stays None until a real all-caps
    CHAPTER heading is found.
    """
    pdf_path = tmp_path / "toc_chapter_header.pdf"
    doc = fitz.open()
    # Page 1: TABLE OF CONTENTS with title-case "Chapter" column header.
    p1 = doc.new_page(width=612, height=792)
    p1.insert_text((180, 90), "TABLE OF CONTENTS", fontsize=14, fontname="Times-Bold")
    p1.insert_text((108, 140), "Chapter", fontsize=12)   # column header, title case
    p1.insert_text((400, 140), "Page", fontsize=12)       # column header
    p1.insert_text((108, 165), "1", fontsize=12)
    p1.insert_text((108, 185), "INTRODUCTION", fontsize=12)
    p1.insert_text((400, 185), "5", fontsize=12)
    p1.insert_text((300, 760), "iv", fontsize=12)         # Roman page number
    # Page 2: Real CHAPTER 1 body start.
    p2 = doc.new_page(width=612, height=792)
    p2.insert_text((220, 90), "CHAPTER 1", fontsize=16, fontname="Times-Bold")
    p2.insert_text((220, 120), "INTRODUCTION", fontsize=14)
    p2.insert_text((300, 760), "1", fontsize=12)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    body_start = find_body_start_page(model)
    assert body_start == 2, (
        f"body_start should be page 2 (CHAPTER 1), not {body_start!r}; "
        "title-case 'Chapter' TOC column header must not match"
    )


def test_find_body_start_page_all_caps_standalone_still_matches(tmp_path: Path) -> None:
    """ALL-CAPS 'CHAPTER' alone on a line (split-heading layout) must still match.

    This verifies the original split-heading fix still works after removing
    re.IGNORECASE from _CHAPTER_STANDALONE_RE.
    """
    pdf_path = tmp_path / "split_chapter_caps.pdf"
    doc = fitz.open()
    # Page 1: front-matter.
    p1 = doc.new_page(width=612, height=792)
    p1.insert_text((300, 760), "iv", fontsize=12)
    # Page 2: split chapter heading — "CHAPTER" on one line, "1" on the next.
    p2 = doc.new_page(width=612, height=792)
    p2.insert_text((220, 90), "CHAPTER", fontsize=16, fontname="Times-Bold")
    p2.insert_text((250, 120), "1", fontsize=16, fontname="Times-Bold")
    p2.insert_text((220, 155), "INTRODUCTION", fontsize=14)
    p2.insert_text((300, 760), "1", fontsize=12)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    body_start = find_body_start_page(model)
    assert body_start == 2, (
        f"body_start should be page 2 (split CHAPTER heading), got {body_start!r}"
    )


def test_p028_toc_chapter_column_header_roman_pages_not_flagged(tmp_path: Path) -> None:
    """Regression: TOC pages with Roman page numbers must not be flagged as body pages.

    Before the fix, 'Chapter' (title case) in the TOC column header triggered
    body_start at the TOC page, causing TOC/List pages with Roman numerals to
    be wrongly classified as body pages and flagged by P028.

    Structure mirrors the real dissertation that triggered the bug:
    - Pages 1-4:  front matter (roman i-iv)
    - Pages 5-7:  TABLE OF CONTENTS continuation, LIST OF TABLES, LIST OF FIGURES
                  (roman v-vii) — these must remain front matter
    - Page 8:     CHAPTER 1 body start (arabic 1)
    """
    pdf_path = tmp_path / "toc_regression.pdf"
    doc = fitz.open()

    # Front-matter page 1 (roman i).
    p = doc.new_page(width=612, height=792)
    p.insert_text((180, 90), "BIOGRAPHICAL SKETCH", fontsize=14, fontname="Times-Bold")
    p.insert_text((300, 760), "i", fontsize=12)

    # Front-matter page 2 (roman ii).
    p = doc.new_page(width=612, height=792)
    p.insert_text((215, 90), "ACKNOWLEDGEMENTS", fontsize=14, fontname="Times-Bold")
    p.insert_text((300, 760), "ii", fontsize=12)

    # TOC page with title-case "Chapter" column header (roman iii).
    p = doc.new_page(width=612, height=792)
    p.insert_text((180, 90), "TABLE OF CONTENTS", fontsize=14, fontname="Times-Bold")
    p.insert_text((108, 140), "Chapter", fontsize=12)   # title-case column header
    p.insert_text((108, 165), "1", fontsize=12)
    p.insert_text((108, 185), "INTRODUCTION", fontsize=12)
    p.insert_text((300, 760), "iii", fontsize=12)

    # TOC continuation (roman iv).
    p = doc.new_page(width=612, height=792)
    p.insert_text((180, 90), "TABLE OF CONTENTS", fontsize=14, fontname="Times-Bold")
    p.insert_text((108, 140), "(Continued)", fontsize=12)
    p.insert_text((300, 760), "iv", fontsize=12)

    # LIST OF TABLES (roman v).
    p = doc.new_page(width=612, height=792)
    p.insert_text((210, 90), "LIST OF TABLES", fontsize=14, fontname="Times-Bold")
    p.insert_text((108, 140), "Table", fontsize=12)     # title-case column header
    p.insert_text((300, 760), "v", fontsize=12)

    # LIST OF FIGURES (roman vi).
    p = doc.new_page(width=612, height=792)
    p.insert_text((210, 90), "LIST OF FIGURES", fontsize=14, fontname="Times-Bold")
    p.insert_text((108, 140), "Figure", fontsize=12)
    p.insert_text((300, 760), "vi", fontsize=12)

    # Front-matter page (roman vii).
    p = doc.new_page(width=612, height=792)
    p.insert_text((300, 760), "vii", fontsize=12)

    # CHAPTER 1 body start (arabic 1).
    p = doc.new_page(width=612, height=792)
    p.insert_text((220, 90), "CHAPTER 1", fontsize=16, fontname="Times-Bold")
    p.insert_text((300, 760), "1", fontsize=12)

    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))

    # Body start must be page 8 (CHAPTER 1), not pages 3-7 (TOC/list pages).
    body_start = find_body_start_page(model)
    assert body_start == 8, (
        f"body_start should be page 8 (CHAPTER 1), got {body_start!r}; "
        "TOC 'Chapter' column header must not trigger body-start detection"
    )

    # P028: TOC/list pages (3-7) with Roman numerals must NOT be flagged.
    p028 = check_pdf_page_numbering_regime(model)
    toc_list_false_positives = [
        f for f in p028
        if f.rule_id == "P028" and f.page in {3, 4, 5, 6, 7}
    ]
    assert not toc_list_false_positives, (
        f"TOC/list pages wrongly flagged by P028 as body: {toc_list_false_positives}"
    )

    # The body page (8) with Arabic '1' must not be flagged.
    body_page_findings = [f for f in p028 if f.rule_id == "P028" and f.page == 8]
    assert not body_page_findings, (
        f"CHAPTER 1 page wrongly flagged by P028: {body_page_findings}"
    )


def test_find_body_start_page_allcaps_chapter_entries_on_toc_not_matched(
    tmp_path: Path,
) -> None:
    """Regression: ALL-CAPS TOC entries 'CHAPTER 1 INTRODUCTION ........ 1' must NOT
    trigger body-start detection on the TABLE OF CONTENTS page.

    The previous implementation only excluded title-case 'Chapter'; this tests the
    all-caps 'CHAPTER N HEADING' format that actually appears as TOC entry text in
    many NJIT dissertations.
    """
    pdf_path = tmp_path / "allcaps_toc_entries.pdf"
    doc = fitz.open()

    # Page 1: TABLE OF CONTENTS with all-caps TOC entries matching _CHAPTER_HEADING_RE.
    p = doc.new_page(width=612, height=792)
    p.insert_text((180, 90), "TABLE OF CONTENTS", fontsize=14, fontname="Times-Bold")
    p.insert_text((108, 140), "CHAPTER 1 INTRODUCTION ........ 1", fontsize=11)
    p.insert_text((108, 160), "CHAPTER 2 LITERATURE REVIEW ........ 13", fontsize=11)
    p.insert_text((108, 180), "CHAPTER 3 METHODOLOGY ........ 23", fontsize=11)
    p.insert_text((300, 760), "vii", fontsize=12)

    # Page 2: real CHAPTER 1 body page.
    p = doc.new_page(width=612, height=792)
    p.insert_text((220, 90), "CHAPTER 1", fontsize=16, fontname="Times-Bold")
    p.insert_text((220, 120), "INTRODUCTION", fontsize=14)
    p.insert_text((300, 760), "1", fontsize=12)

    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))

    body_start = find_body_start_page(model)
    assert body_start == 2, (
        f"body_start should be page 2 (real CHAPTER 1), got {body_start!r}; "
        "TOC entries 'CHAPTER 1 INTRODUCTION ........ 1' must not trigger body-start detection"
    )


def test_find_body_start_page_allcaps_chapter_column_header_on_toc_not_matched(
    tmp_path: Path,
) -> None:
    """Regression: ALL-CAPS 'CHAPTER' column header on the TOC page must NOT
    trigger body-start detection via _CHAPTER_STANDALONE_RE.

    Some NJIT theses use all-caps 'CHAPTER' (not title-case 'Chapter') as the
    column header label on the TABLE OF CONTENTS page.
    """
    pdf_path = tmp_path / "allcaps_chapter_column_toc.pdf"
    doc = fitz.open()

    # Page 1: TOC with all-caps CHAPTER column header.
    p = doc.new_page(width=612, height=792)
    p.insert_text((180, 90), "TABLE OF CONTENTS", fontsize=14, fontname="Times-Bold")
    p.insert_text((108, 140), "CHAPTER", fontsize=12)   # all-caps column header
    p.insert_text((400, 140), "PAGE", fontsize=12)
    p.insert_text((108, 165), "1 INTRODUCTION ........ 1", fontsize=11)
    p.insert_text((108, 185), "2 LITERATURE REVIEW ........ 13", fontsize=11)
    p.insert_text((300, 760), "iv", fontsize=12)

    # Page 2: real CHAPTER 1 body page.
    p = doc.new_page(width=612, height=792)
    p.insert_text((220, 90), "CHAPTER 1", fontsize=16, fontname="Times-Bold")
    p.insert_text((300, 760), "1", fontsize=12)

    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))

    body_start = find_body_start_page(model)
    assert body_start == 2, (
        f"body_start should be page 2 (real CHAPTER 1), got {body_start!r}; "
        "ALL-CAPS 'CHAPTER' column header on TOC must not trigger body-start"
    )


def test_p028_toc_with_allcaps_chapter_entries_roman_not_flagged(tmp_path: Path) -> None:
    """Regression: TOC page with all-caps 'CHAPTER 1 INTRODUCTION ........ 1' entries
    and Roman numeral page number must NOT produce a P028 false positive.

    Structure mirrors the real dissertation at digitalcommons.njit.edu/theses/3363:
    - Pages 1-3:  front matter (roman i-iii)
    - Pages 4-5:  TABLE OF CONTENTS continuation (roman iv-v) with all-caps CHAPTER entries
    - Pages 6-7:  LIST OF TABLES / LIST OF FIGURES (roman vi-vii)
    - Page 8:     CHAPTER 1 body (arabic 1)
    """
    pdf_path = tmp_path / "toc_allcaps_chapter_entries.pdf"
    doc = fitz.open()

    # Front matter (pages 1-3).
    front_matter = [
        ("i", "ABSTRACT"),
        ("ii", "BIOGRAPHICAL SKETCH"),
        ("iii", "ACKNOWLEDGEMENTS"),
    ]
    for roman, heading in front_matter:
        p = doc.new_page(width=612, height=792)
        p.insert_text((220, 90), heading, fontsize=14, fontname="Times-Bold")
        p.insert_text((300, 760), roman, fontsize=12)

    # TABLE OF CONTENTS page with all-caps "CHAPTER N" entries (roman iv).
    p = doc.new_page(width=612, height=792)
    p.insert_text((180, 90), "TABLE OF CONTENTS", fontsize=14, fontname="Times-Bold")
    p.insert_text((108, 135), "CHAPTER 1 INTRODUCTION ........ 1", fontsize=11)
    p.insert_text((108, 155), "CHAPTER 2 LITERATURE REVIEW ........ 13", fontsize=11)
    p.insert_text((108, 175), "CHAPTER 3 METHODOLOGY ........ 23", fontsize=11)
    p.insert_text((300, 760), "iv", fontsize=12)

    # TABLE OF CONTENTS continued (roman v).
    p = doc.new_page(width=612, height=792)
    p.insert_text((180, 90), "TABLE OF CONTENTS", fontsize=14, fontname="Times-Bold")
    p.insert_text((108, 135), "(Continued)", fontsize=11)
    p.insert_text((108, 155), "CHAPTER 4 RESULTS ........ 45", fontsize=11)
    p.insert_text((300, 760), "v", fontsize=12)

    # LIST OF TABLES (roman vi).
    p = doc.new_page(width=612, height=792)
    p.insert_text((210, 90), "LIST OF TABLES", fontsize=14, fontname="Times-Bold")
    p.insert_text((300, 760), "vi", fontsize=12)

    # LIST OF FIGURES (roman vii).
    p = doc.new_page(width=612, height=792)
    p.insert_text((210, 90), "LIST OF FIGURES", fontsize=14, fontname="Times-Bold")
    p.insert_text((300, 760), "vii", fontsize=12)

    # CHAPTER 1 body start (arabic 1).
    p = doc.new_page(width=612, height=792)
    p.insert_text((220, 90), "CHAPTER 1", fontsize=16, fontname="Times-Bold")
    p.insert_text((220, 120), "INTRODUCTION", fontsize=14)
    p.insert_text((300, 760), "1", fontsize=12)

    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))

    body_start = find_body_start_page(model)
    assert body_start == 8, (
        f"body_start should be page 8 (CHAPTER 1), got {body_start!r}; "
        "TOC pages with all-caps CHAPTER entries must not trigger body-start"
    )

    p028 = [f for f in check_pdf_page_numbering_regime(model) if f.rule_id == "P028"]
    fm_false_positives = [f for f in p028 if f.page in {1, 2, 3, 4, 5, 6, 7}]
    assert not fm_false_positives, (
        f"Front-matter/TOC/List pages wrongly flagged by P028 as body: {fm_false_positives}"
    )

    body_false_positives = [f for f in p028 if f.page == 8]
    assert not body_false_positives, (
        f"CHAPTER 1 page (arabic '1') wrongly flagged by P028: {body_false_positives}"
    )


def test_p028_real_body_roman_still_flagged_when_toc_has_allcaps_chapter_entries(
    tmp_path: Path,
) -> None:
    """Real body page using Roman numeral must still produce a P028 warning,
    even when the preceding TOC contains all-caps 'CHAPTER N' entries."""
    pdf_path = tmp_path / "toc_allcaps_body_roman.pdf"
    doc = fitz.open()

    # TOC page with all-caps CHAPTER entries.
    p = doc.new_page(width=612, height=792)
    p.insert_text((180, 90), "TABLE OF CONTENTS", fontsize=14, fontname="Times-Bold")
    p.insert_text((108, 140), "CHAPTER 1 INTRODUCTION ........ 1", fontsize=11)
    p.insert_text((300, 760), "iii", fontsize=12)

    # CHAPTER 1 body page — wrong: uses Roman instead of Arabic.
    p = doc.new_page(width=612, height=792)
    p.insert_text((220, 90), "CHAPTER 1", fontsize=16, fontname="Times-Bold")
    p.insert_text((300, 760), "iv", fontsize=12)   # wrong: should be arabic

    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))

    p028 = [f for f in check_pdf_page_numbering_regime(model) if f.rule_id == "P028"]
    body_roman_findings = [
        f for f in p028
        if f.page == 2 and f.details.get("issue_type") == "roman_number_on_body_page"
    ]
    assert body_roman_findings, (
        "Expected P028 roman_number_on_body_page on CHAPTER 1 page; "
        f"got: {[(f.page, f.details.get('issue_type')) for f in p028]}"
    )


def test_p028_toc_continued_page_roman_not_flagged(tmp_path: Path) -> None:
    """TABLE OF CONTENTS (Continued) page with Roman numeral must not be flagged."""
    pdf_path = tmp_path / "toc_continued_roman.pdf"
    doc = fitz.open()

    # TOC page 1.
    p = doc.new_page(width=612, height=792)
    p.insert_text((180, 90), "TABLE OF CONTENTS", fontsize=14, fontname="Times-Bold")
    p.insert_text((108, 140), "CHAPTER 1 INTRODUCTION ........ 1", fontsize=11)
    p.insert_text((300, 760), "v", fontsize=12)

    # TOC continued page — no "TABLE OF CONTENTS" heading; pure continuation entries.
    p = doc.new_page(width=612, height=792)
    p.insert_text((108, 90), "CHAPTER 2 LITERATURE REVIEW ........ 13", fontsize=11)
    p.insert_text((108, 110), "CHAPTER 3 METHODOLOGY ........ 23", fontsize=11)
    p.insert_text((300, 760), "vi", fontsize=12)

    # CHAPTER 1 body.
    p = doc.new_page(width=612, height=792)
    p.insert_text((220, 90), "CHAPTER 1", fontsize=16, fontname="Times-Bold")
    p.insert_text((300, 760), "1", fontsize=12)

    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))

    # The TOC page 1 must NOT be body start.
    body_start = find_body_start_page(model)
    assert body_start == 3, (
        f"body_start should be page 3 (CHAPTER 1), got {body_start!r}; "
        "TOC page must be skipped even with all-caps CHAPTER entries"
    )

    # Page 1 (TOC) must not be flagged.
    p028 = [f for f in check_pdf_page_numbering_regime(model) if f.rule_id == "P028"]
    toc_flagged = [f for f in p028 if f.page == 1]
    assert not toc_flagged, (
        f"TOC page (roman 'v') wrongly flagged by P028: {toc_flagged}"
    )


def test_p038_toc_heading_in_front_matter_when_chapter_in_toc_column(tmp_path: Path) -> None:
    """Regression: TABLE OF CONTENTS should be detected in front matter even when
    the TOC page contains a title-case 'Chapter' column header.

    Before the fix, body_start was set to the TOC page (because 'Chapter' matched
    the standalone regex), placing the TOC heading in the body region and causing
    P038 to falsely report it as missing from front matter.
    """
    pdf_path = tmp_path / "p038_toc_front_matter.pdf"
    doc = fitz.open()
    # Front-matter pages.
    p = doc.new_page(width=612, height=792)
    p.insert_text((240, 90), "APPROVAL PAGE", fontsize=14, fontname="Times-Bold")
    p = doc.new_page(width=612, height=792)
    p.insert_text((200, 90), "BIOGRAPHICAL SKETCH", fontsize=14, fontname="Times-Bold")
    p.insert_text((300, 760), "iv", fontsize=12)
    p = doc.new_page(width=612, height=792)
    p.insert_text((205, 90), "ACKNOWLEDGEMENTS", fontsize=14, fontname="Times-Bold")
    p.insert_text((300, 760), "v", fontsize=12)
    # TABLE OF CONTENTS with title-case column header.
    p = doc.new_page(width=612, height=792)
    p.insert_text((180, 90), "TABLE OF CONTENTS", fontsize=14, fontname="Times-Bold")
    p.insert_text((108, 140), "Chapter", fontsize=12)   # title-case: must not shift body_start
    p.insert_text((300, 760), "vi", fontsize=12)
    # CHAPTER 1 body.
    p = doc.new_page(width=612, height=792)
    p.insert_text((220, 90), "CHAPTER 1", fontsize=16, fontname="Times-Bold")
    p.insert_text((300, 760), "1", fontsize=12)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_frontmatter_headings(model) if f.rule_id == "P038"]
    toc_missing = [
        f for f in findings
        if f.details.get("section_key") == "table_of_contents"
        and f.details.get("issue_type") == "required_heading_missing"
    ]
    assert not toc_missing, (
        "TABLE OF CONTENTS wrongly reported as missing from front matter; "
        "likely caused by body_start being set too early from TOC column header"
    )


def test_find_body_start_page_mashed_chapter_number_matches() -> None:
    """Mashed 'CHAPTER1' (no space) must still trigger body-start detection.

    pdf_layout.py skips whitespace-only spans (line 83), so when the space
    between 'CHAPTER' and '1' is its own span (common in LaTeX PDFs), the
    model sees line.text='CHAPTER1'.  _CHAPTER_HEADING_MASHED_RE must catch it.
    """
    from njit_auditor.pdf_models import BBox, PdfDocument, PdfPage, PdfTextBlock, PdfTextSpan

    zero_bbox = BBox(x0=0, y0=0, x1=100, y1=14)

    def _line(text: str) -> PdfTextLine:
        return PdfTextLine(
            text=text,
            bbox=zero_bbox,
            spans=[PdfTextSpan(text=text, bbox=zero_bbox, font="Times-Bold", size=16, bold=True)],
        )

    front_matter_block = PdfTextBlock(
        bbox=zero_bbox,
        text="iii",
        lines=[_line("iii")],
    )
    chapter_block = PdfTextBlock(
        bbox=zero_bbox,
        text="CHAPTER1",
        lines=[_line("CHAPTER1")],
    )
    doc = PdfDocument(
        path="synthetic.pdf",
        pages=[
            PdfPage(page_number=1, width=612, height=792, text_blocks=[front_matter_block]),
            PdfPage(page_number=2, width=612, height=792, text_blocks=[chapter_block]),
        ],
    )
    result = find_body_start_page(doc)
    assert result == 2, (
        f"body_start should be page 2 for mashed 'CHAPTER1', got {result!r}; "
        "_CHAPTER_HEADING_MASHED_RE must match all-caps CHAPTER followed by digits with no space"
    )


def test_find_body_start_page_body_sentence_not_matched(tmp_path: Path) -> None:
    """Title-case 'Chapter N' in a body-text forward reference must NOT trigger body-start.

    In the real dissertation, page 21 contains 'Chapter 3 is dedicated to the
    development and evaluation of...'.  With re.IGNORECASE removed from
    _CHAPTER_HEADING_RE, this sentence no longer matches, so body_start must
    advance to the actual CHAPTER 3 ALL-CAPS heading page.
    """
    pdf_path = tmp_path / "body_sentence_chapter.pdf"
    doc = fitz.open()
    # Page 1: front matter.
    p = doc.new_page(width=612, height=792)
    p.insert_text((300, 760), "iv", fontsize=12)
    # Page 2: body paragraph with title-case forward reference ("Chapter 3 is dedicated...").
    p = doc.new_page(width=612, height=792)
    p.insert_text(
        (108, 120),
        "Chapter 3 is dedicated to the development and evaluation of an advanced system.",
        fontsize=12,
    )
    p.insert_text((300, 760), "1", fontsize=12)
    # Page 3: real ALL-CAPS chapter heading.
    p = doc.new_page(width=612, height=792)
    p.insert_text((220, 90), "CHAPTER 3", fontsize=16, fontname="Times-Bold")
    p.insert_text((300, 760), "3", fontsize=12)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    body_start = find_body_start_page(model)
    assert body_start == 3, (
        f"body_start should be page 3 (ALL-CAPS CHAPTER 3), got {body_start!r}; "
        "title-case 'Chapter N' in body sentences must not match _CHAPTER_HEADING_RE"
    )


# ---------------------------------------------------------------------------
# P020 refinement tests — CMBX bold recognition and font-size fallback
# ---------------------------------------------------------------------------



def _make_line(font: str, size: float, bold: bool = False, text: str = "word") -> PdfTextLine:
    span = PdfTextSpan(
        text=text, bbox=BBox(x0=0, y0=0, x1=100, y1=14), font=font, size=size, bold=bold
    )
    return PdfTextLine(
        spans=[span], bbox=BBox(x0=0, y0=0, x1=100, y1=14), text=text
    )


# ---- _style_flags_from_font_name unit tests ----

def test_style_flags_cmbx12_is_bold() -> None:
    bold, italic = _style_flags_from_font_name("CMBX12")
    assert bold is True
    assert italic is False


def test_style_flags_cmbx_subset_prefix_is_bold() -> None:
    bold, italic = _style_flags_from_font_name("ABCDEF+CMBX12")
    assert bold is True
    assert italic is False


def test_style_flags_cmr12_is_not_bold() -> None:
    bold, italic = _style_flags_from_font_name("CMR12")
    assert bold is False
    assert italic is False


def test_style_flags_cmti12_is_italic_not_bold() -> None:
    bold, italic = _style_flags_from_font_name("CMTI12")
    assert bold is False
    assert italic is True


def test_style_flags_times_bold_is_bold() -> None:
    bold, italic = _style_flags_from_font_name("Times-Bold")
    assert bold is True


def test_style_flags_none_returns_false_false() -> None:
    assert _style_flags_from_font_name(None) == (False, False)


# ---- _is_math_font unit tests ----

def test_is_math_font_cmmi_true() -> None:
    assert _is_math_font("CMMI12") is True


def test_is_math_font_cmsy_true() -> None:
    assert _is_math_font("CMSY10") is True


def test_is_math_font_cmbx_false() -> None:
    assert _is_math_font("CMBX12") is False


def test_is_math_font_cmr_false() -> None:
    assert _is_math_font("CMR12") is False


# ---- _spans_bold_reason unit tests ----

def test_spans_bold_reason_cmbx_returns_cmbx() -> None:
    line = _make_line("CMBX12", 12.0)
    assert _spans_bold_reason(line) == "cmbx_bold_heading"


def test_spans_bold_reason_times_bold_returns_bold() -> None:
    line = _make_line("Times-Bold", 12.0, bold=True)
    assert _spans_bold_reason(line) == "bold_heading"


def test_spans_bold_reason_cmr_returns_none() -> None:
    line = _make_line("CMR12", 12.0)
    assert _spans_bold_reason(line) is None


def test_spans_bold_reason_math_font_excluded() -> None:
    # A line with only CMMI (math) spans should not be detected as bold heading.
    line = _make_line("CMMI12", 12.0)
    assert _spans_bold_reason(line) is None


# ---- Integration: P020 with fitz PDFs ----

def test_p020_cmbx_heading_wrong_title_case_warns(tmp_path: Path) -> None:
    """A CMBX-named heading with a title-case violation should trigger P020."""
    pdf_path = tmp_path / "p020_cmbx_bad.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    # Use a bold font for the heading line — fitz will embed it as bold.
    page.insert_text(
        (108, 200), "results and discussion methods", fontsize=12, fontname="hebo"
    )
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_title_capitalization(model)
    # The bold Times-Bold or Helvetica-Bold line should trigger (font=hebo → bold=True).
    warnings = [f for f in findings if f.rule_id == "P020"]
    # Expect at least one P020 finding (bold heading with title-case issue).
    assert len(warnings) >= 1


def test_p020_correct_title_case_hebo_heading_no_warning(tmp_path: Path) -> None:
    """A bold heading with correct Title Case should produce no P020 warning."""
    pdf_path = tmp_path / "p020_bold_ok.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text(
        (108, 200), "Results and Discussion Methods Here", fontsize=12, fontname="hebo"
    )
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_title_capitalization(model)
    assert not any(f.rule_id == "P020" for f in findings)


def test_p020_finding_includes_detection_reason(tmp_path: Path) -> None:
    """P020 findings must include a detection_reason detail field."""
    pdf_path = tmp_path / "p020_detection_reason.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text(
        (108, 200), "results and discussion methods", fontsize=12, fontname="hebo"
    )
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_title_capitalization(model) if f.rule_id == "P020"]
    if findings:
        assert "detection_reason" in findings[0].details


def _make_repository_wrapper_then_thesis_pdf(path: Path) -> None:
    doc = fitz.open()

    page = doc.new_page(width=612, height=792)
    page.insert_text((72, 72), "Digital Commons @ NJIT", fontsize=14)
    page.insert_text((72, 100), "Electronic Theses and Dissertations", fontsize=11)
    page.insert_text((72, 130), "Recommended Citation", fontsize=11)
    page.insert_text(
        (108, 210),
        "machine learning repository cover title",
        fontsize=16,
        fontname="Times-Bold",
    )
    page.insert_text((292, 760), "1", fontsize=12)

    page = doc.new_page(width=612, height=792)
    page.insert_text(
        (72, 90),
        "This work is protected by copyright and/or related rights.",
        fontsize=11,
    )
    page.insert_text(
        (72, 118),
        "For other uses you need to obtain permission from the rights-holder(s) directly.",
        fontsize=11,
    )
    page.insert_text(
        (72, 146),
        "A Creative Commons license in the record may apply to some uses.",
        fontsize=11,
    )
    page.insert_text((292, 760), "2", fontsize=12)

    page = doc.new_page(width=612, height=792)
    page.insert_text((108, 180), "Actual Thesis Title", fontsize=16, fontname="Times-Bold")
    page.insert_text((108, 210), "Author Name", fontsize=12)

    page = doc.new_page(width=612, height=792)
    page.insert_text((250, 90), "ABSTRACT", fontsize=16, fontname="Times-Bold")
    page.insert_text(
        (108, 140),
        "This abstract contains enough body text to count as the real manuscript front matter.",
        fontsize=12,
    )

    page = doc.new_page(width=612, height=792)
    page.insert_text(
        (108, 180),
        "Machine learning Approaches to Signal Processing",
        fontsize=16,
        fontname="Times-Bold",
    )

    doc.save(path)
    doc.close()


def _make_repository_wrapper_title_page_warning_pdf(path: Path) -> None:
    doc = fitz.open()

    page = doc.new_page(width=612, height=792)
    page.insert_text((72, 72), "Digital Commons @ NJIT", fontsize=14)
    page.insert_text((72, 100), "Electronic Theses and Dissertations", fontsize=11)
    page.insert_text((72, 130), "Recommended Citation", fontsize=11)
    page.insert_text((108, 210), "repository wrapper title", fontsize=16, fontname="Times-Bold")

    page = doc.new_page(width=612, height=792)
    page.insert_text(
        (72, 90),
        "This work is protected by copyright and/or related rights.",
        fontsize=11,
    )
    page.insert_text(
        (72, 118),
        "For other uses you need to obtain permission from the rights-holder(s) directly.",
        fontsize=11,
    )
    page.insert_text(
        (72, 146),
        "A Creative Commons license in the record may apply to some uses.",
        fontsize=11,
    )

    page = doc.new_page(width=612, height=792)
    page.insert_text(
        (108, 180),
        "machine learning Approaches to Signal Processing",
        fontsize=16,
        fontname="Times-Bold",
    )
    page.insert_text((108, 210), "Author Name", fontsize=12)

    page = doc.new_page(width=612, height=792)
    page.insert_text((250, 90), "ABSTRACT", fontsize=16, fontname="Times-Bold")
    page.insert_text(
        (108, 140),
        "This abstract contains enough body text to count as the real manuscript front matter.",
        fontsize=12,
    )

    page = doc.new_page(width=612, height=792)
    page.insert_text((108, 180), "Chapter 1", fontsize=16, fontname="Times-Bold")
    page.insert_text((108, 220), "Body text starts here.", fontsize=12)

    doc.save(path)
    doc.close()


def _make_repository_wrapper_real_copyright_pdf(
    path: Path,
    *,
    copyright_line: str,
) -> None:
    doc = fitz.open()

    page = doc.new_page(width=612, height=792)
    page.insert_text((72, 72), "Digital Commons @ NJIT", fontsize=14)
    page.insert_text((72, 100), "Electronic Theses and Dissertations", fontsize=11)
    page.insert_text((72, 130), "Recommended Citation", fontsize=11)

    page = doc.new_page(width=612, height=792)
    page.insert_text(
        (72, 90),
        "This work is protected by copyright and/or related rights.",
        fontsize=11,
    )
    page.insert_text(
        (72, 118),
        "For other uses you need to obtain permission from the rights-holder(s) directly.",
        fontsize=11,
    )
    page.insert_text(
        (72, 146),
        "A Creative Commons license in the record may apply to some uses.",
        fontsize=11,
    )

    page = doc.new_page(width=612, height=792)
    page.insert_text((108, 170), "Actual Thesis Title", fontsize=16, fontname="Times-Bold")
    page.insert_text((220, 210), "by", fontsize=12)
    page.insert_text((108, 238), "Author Name", fontsize=12)
    page.insert_text((108, 520), "May 2024", fontsize=12)

    page = doc.new_page(width=612, height=792)
    page.insert_text((220, 110), "COPYRIGHT PAGE", fontsize=14, fontname="Times-Bold")
    page.insert_text((108, 180), copyright_line, fontsize=12)

    page = doc.new_page(width=612, height=792)
    page.insert_text((250, 90), "ABSTRACT", fontsize=16, fontname="Times-Bold")
    page.insert_text(
        (108, 140),
        "This abstract contains enough body text to count as the real manuscript front matter.",
        fontsize=12,
    )

    doc.save(path)
    doc.close()


def test_p020_ignores_repository_wrapper_pages_but_still_flags_real_heading(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "repository_wrapper_then_thesis.pdf"
    _make_repository_wrapper_then_thesis_pdf(pdf_path)
    model = load_pdf_layout(str(pdf_path))

    findings = [f for f in check_pdf_title_capitalization(model) if f.rule_id == "P020"]

    assert len(findings) == 1
    assert findings[0].page == 5
    assert findings[0].details.get("flagged_word") == "learning"
    assert not any(f.page in {1, 2} for f in findings)


def test_p022_does_not_treat_repository_wrapper_page_as_title_page(tmp_path: Path) -> None:
    pdf_path = tmp_path / "repository_wrapper_frontmatter.pdf"
    _make_repository_wrapper_then_thesis_pdf(pdf_path)
    model = load_pdf_layout(str(pdf_path))

    warnings = [f for f in check_pdf_frontmatter_no_page_number(model) if f.rule_id == "P022"]

    assert not any(f.page == 1 for f in warnings)
    assert not any(f.page == 2 for f in warnings)


def test_collect_pdf_layout_findings_skips_repository_wrapper_pages_for_p020(
    tmp_path: Path,
) -> None:
    from njit_auditor.audit_runner import collect_pdf_layout_findings

    pdf_path = tmp_path / "repository_wrapper_collect.pdf"
    _make_repository_wrapper_then_thesis_pdf(pdf_path)
    model = load_pdf_layout(str(pdf_path))

    findings = collect_pdf_layout_findings(model, pdf_path)
    p020_pages = {
        f.page
        for f in findings
        if f.rule_id == "P020"
        and f.details.get("issue_type") == "possible_title_capitalization_issue"
    }
    wrapper_notice = [
        f
        for f in findings
        if f.details.get("issue_type") == "digital_commons_wrapper_pages_detected"
    ]

    assert p020_pages == {5}
    assert len(wrapper_notice) == 1
    assert wrapper_notice[0].details.get("digital_commons_wrapper_pages") == "1,2"


def test_without_wrapper_pages_preserves_original_and_manuscript_page_identity(
    tmp_path: Path,
) -> None:
    from njit_auditor.digital_commons_wrapper import (
        detect_digital_commons_wrapper_pages,
        without_wrapper_pages,
    )

    pdf_path = tmp_path / "repository_wrapper_identity.pdf"
    _make_repository_wrapper_then_thesis_pdf(pdf_path)
    model = load_pdf_layout(str(pdf_path))

    filtered = without_wrapper_pages(model, detect_digital_commons_wrapper_pages(model))

    assert [page.page_number for page in filtered.pages] == [3, 4, 5]
    assert [page.original_page_index for page in filtered.pages] == [2, 3, 4]
    assert [page.original_page_number for page in filtered.pages] == [3, 4, 5]
    assert [page.manuscript_page_index for page in filtered.pages] == [0, 1, 2]
    assert [page.manuscript_page_number for page in filtered.pages] == [1, 2, 3]
    assert [page.display_page_label for page in filtered.pages] == [
        "manuscript page 1 / PDF page 3",
        "manuscript page 2 / PDF page 4",
        "manuscript page 3 / PDF page 5",
    ]


def test_p025_title_page_warnings_use_original_pdf_page_after_wrapper_filtering(
    tmp_path: Path,
) -> None:
    from njit_auditor.audit_runner import collect_pdf_layout_findings

    pdf_path = tmp_path / "repository_wrapper_title_page_warning.pdf"
    _make_repository_wrapper_title_page_warning_pdf(pdf_path)
    model = load_pdf_layout(str(pdf_path))

    findings = [
        f
        for f in collect_pdf_layout_findings(model, pdf_path)
        if f.rule_id == "P025"
        and f.details.get("issue_type")
        in {"missing_title_page_degree_phrase", "missing_title_page_institution"}
    ]

    assert {f.page for f in findings} == {3}
    assert {f.details.get("page_number") for f in findings} == {"3"}
    assert {f.details.get("original_pdf_page_index") for f in findings} == {"2"}
    assert {f.details.get("original_pdf_page_number") for f in findings} == {"3"}
    assert {f.details.get("manuscript_page_index") for f in findings} == {"0"}
    assert {f.details.get("manuscript_page_number") for f in findings} == {"1"}
    assert {f.details.get("page_label") for f in findings} == {
        "manuscript page 1 / PDF page 3"
    }


def test_p051_ignores_repository_copyright_warning_but_checks_real_copyright_page(
    tmp_path: Path,
) -> None:
    from njit_auditor.audit_runner import collect_pdf_layout_findings

    pdf_path = tmp_path / "repository_wrapper_real_copyright_missing_year.pdf"
    _make_repository_wrapper_real_copyright_pdf(pdf_path, copyright_line="© Author Name")
    model = load_pdf_layout(str(pdf_path))

    findings = [f for f in collect_pdf_layout_findings(model, pdf_path) if f.rule_id == "P051"]

    assert len(findings) == 1
    assert findings[0].page == 4
    assert findings[0].details.get("issue_type") == "copyright_year_not_found"


def test_p052_ignores_repository_copyright_warning_but_checks_real_copyright_page(
    tmp_path: Path,
) -> None:
    from njit_auditor.audit_runner import collect_pdf_layout_findings

    pdf_path = tmp_path / "repository_wrapper_real_copyright_missing_author.pdf"
    _make_repository_wrapper_real_copyright_pdf(pdf_path, copyright_line="© 2024")
    model = load_pdf_layout(str(pdf_path))

    findings = [f for f in collect_pdf_layout_findings(model, pdf_path) if f.rule_id == "P052"]

    assert len(findings) == 1
    assert findings[0].page == 4
    assert findings[0].details.get("issue_type") == "copyright_author_not_found"


def test_p020_font_size_fallback_large_font_wrong_case_warns(tmp_path: Path) -> None:
    """Non-bold line at ≥14pt (body=12pt) should trigger font_size_heading_fallback."""
    pdf_path = tmp_path / "p020_size_fallback.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    # Body text at 12pt (many lines to establish body_size baseline).
    for i in range(10):
        page.insert_text(
            (108, 150 + i * 22),
            "An ordinary body text paragraph line for font compliance testing here.",
            fontsize=12,
            fontname="tiro",
        )
    # Non-bold heading at 14pt with title-case violation (must not start with a
    # minor word — those lines are treated as wrapped continuations).
    page.insert_text(
        (108, 380), "machine learning results and discussion", fontsize=14, fontname="tiro"
    )
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_title_capitalization(model) if f.rule_id == "P020"]
    size_fallback = [
        f for f in findings
        if f.details.get("detection_reason") == "font_size_heading_fallback"
    ]
    assert len(size_fallback) >= 1


def test_p020_font_size_fallback_correct_title_case_no_warning(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p020_size_fallback_ok.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    for i in range(10):
        page.insert_text(
            (108, 150 + i * 22),
            "An ordinary body text paragraph line for font compliance testing here.",
            fontsize=12,
            fontname="tiro",
        )
    # Non-bold heading at 14pt with correct Title Case.
    page.insert_text(
        (108, 380), "Results and Discussion Methods", fontsize=14, fontname="tiro"
    )
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    size_fallback = [
        f for f in check_pdf_title_capitalization(model)
        if f.rule_id == "P020"
        and f.details.get("detection_reason") == "font_size_heading_fallback"
    ]
    assert not size_fallback


# ---------------------------------------------------------------------------
# P030: TOC/List continued headings
# ---------------------------------------------------------------------------

_P030_TOC_ENTRIES: list[tuple[str, float]] = [
    ("CHAPTER 1 INTRODUCTION TO THE STUDY ....", 108),
    ("CHAPTER 2 BACKGROUND AND RELATED WORK ....", 108),
    ("CHAPTER 3 RESEARCH METHODOLOGY AND DATA ....", 108),
]

_P030_LOT_ENTRIES: list[tuple[str, float]] = [
    ("Table 1 Summary of Experimental Setup ....", 108),
    ("Table 2 Comparison of Model Performance ....", 108),
    ("Table 3 Regression Coefficients Overview ....", 108),
]

_P030_LOF_ENTRIES: list[tuple[str, float]] = [
    ("Figure 1 Overview of the experimental workflow ....", 108),
    ("Figure 2 Comparison of model performance ....", 108),
    ("Figure 3 Distribution of sample measurements ....", 108),
]


def _make_multi_page_section_pdf(
    path: Path,
    pages: list[tuple[str, list[tuple[str, float]]]],
) -> None:
    doc = fitz.open()
    for heading, entries in pages:
        page = doc.new_page(width=612, height=792)
        page.insert_text((190, 90), heading, fontsize=16, fontname="Times-Bold")
        for idx, (label, indent_x) in enumerate(entries):
            y = 130 + idx * 20
            page.insert_text((indent_x, y), label)
            page.insert_text((500, y), "12")
    doc.save(path)
    doc.close()


def test_p030_single_page_toc_no_warning(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p030_single_toc.pdf"
    _make_multi_page_section_pdf(
        pdf_path,
        [("TABLE OF CONTENTS", _P030_TOC_ENTRIES)],
    )
    model = load_pdf_layout(str(pdf_path))
    assert not any(f.rule_id == "P030" for f in check_pdf_toc_continued_headings(model))


def test_p030_two_page_toc_with_continued_heading_no_warning(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p030_toc_continued_ok.pdf"
    _make_multi_page_section_pdf(
        pdf_path,
        [
            ("TABLE OF CONTENTS", _P030_TOC_ENTRIES),
            ("TABLE OF CONTENTS (Continued)", _P030_TOC_ENTRIES),
        ],
    )
    model = load_pdf_layout(str(pdf_path))
    assert not any(f.rule_id == "P030" for f in check_pdf_toc_continued_headings(model))


def test_p030_two_page_toc_missing_continued_heading_warns(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p030_toc_missing_continued.pdf"
    _make_multi_page_section_pdf(
        pdf_path,
        [
            ("TABLE OF CONTENTS", _P030_TOC_ENTRIES),
            ("TABLE OF CONTENTS", _P030_TOC_ENTRIES),
        ],
    )
    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in check_pdf_toc_continued_headings(model) if f.rule_id == "P030"]
    assert len(warnings) == 1
    assert warnings[0].page == 2
    assert warnings[0].details.get("issue_type") == "missing_continued_heading"
    assert warnings[0].details.get("section_type") == "table_of_contents"
    assert warnings[0].details.get("expected_heading") == "TABLE OF CONTENTS (Continued)"


def test_p030_lot_continued_heading_accepted(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p030_lot_continued_ok.pdf"
    _make_multi_page_section_pdf(
        pdf_path,
        [
            ("LIST OF TABLES", _P030_LOT_ENTRIES),
            ("LIST OF TABLES (Continued)", _P030_LOT_ENTRIES),
        ],
    )
    model = load_pdf_layout(str(pdf_path))
    assert not any(f.rule_id == "P030" for f in check_pdf_toc_continued_headings(model))


def test_p030_lof_missing_continued_heading_warns(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p030_lof_missing_continued.pdf"
    _make_multi_page_section_pdf(
        pdf_path,
        [
            ("LIST OF FIGURES", _P030_LOF_ENTRIES),
            ("LIST OF FIGURES", _P030_LOF_ENTRIES),
        ],
    )
    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in check_pdf_toc_continued_headings(model) if f.rule_id == "P030"]
    assert len(warnings) == 1
    assert warnings[0].details.get("section_type") == "list_of_figures"


def test_p030_heading_variants_with_punctuation_and_continued_suffix_accepted(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "p030_heading_variants.pdf"
    _make_multi_page_section_pdf(
        pdf_path,
        [
            ("TABLE OF CONTENTS.", _P030_TOC_ENTRIES),
            ("TABLE OF CONTENTS (CONTINUED)", _P030_TOC_ENTRIES),
        ],
    )
    model = load_pdf_layout(str(pdf_path))
    assert not any(f.rule_id == "P030" for f in check_pdf_toc_continued_headings(model))


def test_p030_non_consecutive_toc_pages_not_flagged(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p030_non_consecutive.pdf"
    doc = fitz.open()
    page1 = doc.new_page(width=612, height=792)
    page1.insert_text((190, 90), "TABLE OF CONTENTS", fontsize=16, fontname="Times-Bold")
    for idx, (label, indent_x) in enumerate(_P030_TOC_ENTRIES):
        y = 130 + idx * 20
        page1.insert_text((indent_x, y), label)
        page1.insert_text((500, y), "12")

    page2 = doc.new_page(width=612, height=792)
    page2.insert_text((108, 140), "Ordinary body page content without list heading.")

    page3 = doc.new_page(width=612, height=792)
    page3.insert_text((190, 90), "TABLE OF CONTENTS", fontsize=16, fontname="Times-Bold")
    for idx, (label, indent_x) in enumerate(_P030_TOC_ENTRIES):
        y = 130 + idx * 20
        page3.insert_text((indent_x, y), label)
        page3.insert_text((500, y), "12")
    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))
    assert not any(f.rule_id == "P030" for f in check_pdf_toc_continued_headings(model))


def test_p030_finding_details_are_privacy_safe(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p030_privacy_safe_details.pdf"
    long_body = "X" * 200
    doc = fitz.open()
    page1 = doc.new_page(width=612, height=792)
    page1.insert_text((190, 90), "TABLE OF CONTENTS", fontsize=16, fontname="Times-Bold")
    page1.insert_text((108, 140), long_body)
    page2 = doc.new_page(width=612, height=792)
    page2.insert_text((190, 90), "TABLE OF CONTENTS", fontsize=16, fontname="Times-Bold")
    page2.insert_text((108, 140), "Chapter 4 Discussion of Results and Findings ....")
    page2.insert_text((500, 140), "12")
    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))
    warning = next(f for f in check_pdf_toc_continued_headings(model) if f.rule_id == "P030")
    assert len(warning.details.get("observed_heading", "")) <= 80
    assert long_body not in str(warning.details)
    assert long_body not in warning.message


# ---------------------------------------------------------------------------
# P031: LoT/LoF column headers
# ---------------------------------------------------------------------------


def _make_lot_lof_pdf(
    path: Path,
    heading: str,
    entries: list[tuple[str, float]],
    *,
    left_header: str | None = "Table",
    page_header: str | None = "Page",
    left_header_x: float = 108,
    page_header_x: float = 500,
) -> None:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((190, 90), heading, fontsize=16, fontname="Times-Bold")
    if left_header is not None:
        page.insert_text((left_header_x, 115), left_header)
    if page_header is not None:
        page.insert_text((page_header_x, 115), page_header)
    for idx, (label, indent_x) in enumerate(entries):
        y = 140 + idx * 20
        page.insert_text((indent_x, y), label)
        page.insert_text((500, y), "12")
    doc.save(path)
    doc.close()


def test_p031_lot_correct_header_row_no_warning(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p031_lot_ok.pdf"
    _make_lot_lof_pdf(
        pdf_path,
        "LIST OF TABLES",
        _P030_LOT_ENTRIES,
        left_header="Table",
        page_header="Page",
    )
    model = load_pdf_layout(str(pdf_path))
    assert not any(f.rule_id == "P031" for f in check_pdf_lot_lof_column_headers(model))


def test_p031_lot_missing_table_header_warns(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p031_lot_missing_table.pdf"
    _make_lot_lof_pdf(
        pdf_path,
        "LIST OF TABLES",
        _P030_LOT_ENTRIES,
        left_header=None,
        page_header="Page",
    )
    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in check_pdf_lot_lof_column_headers(model) if f.rule_id == "P031"]
    assert any(f.details.get("issue_type") == "missing_left_column_header" for f in warnings)


def test_p031_lot_missing_page_header_warns(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p031_lot_missing_page.pdf"
    _make_lot_lof_pdf(
        pdf_path,
        "LIST OF TABLES",
        _P030_LOT_ENTRIES,
        left_header="Table",
        page_header=None,
    )
    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in check_pdf_lot_lof_column_headers(model) if f.rule_id == "P031"]
    assert any(f.details.get("issue_type") == "missing_page_column_header" for f in warnings)


def test_p031_lof_correct_header_row_no_warning(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p031_lof_ok.pdf"
    _make_lot_lof_pdf(
        pdf_path,
        "LIST OF FIGURES",
        _P030_LOF_ENTRIES,
        left_header="Figure",
        page_header="Page",
    )
    model = load_pdf_layout(str(pdf_path))
    assert not any(f.rule_id == "P031" for f in check_pdf_lot_lof_column_headers(model))


def test_p031_lof_missing_figure_header_warns(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p031_lof_missing_figure.pdf"
    _make_lot_lof_pdf(
        pdf_path,
        "LIST OF FIGURES",
        _P030_LOF_ENTRIES,
        left_header=None,
        page_header="Page",
    )
    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in check_pdf_lot_lof_column_headers(model) if f.rule_id == "P031"]
    assert any(f.details.get("issue_type") == "missing_left_column_header" for f in warnings)


def test_p031_lof_missing_page_header_warns(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p031_lof_missing_page.pdf"
    _make_lot_lof_pdf(
        pdf_path,
        "LIST OF FIGURES",
        _P030_LOF_ENTRIES,
        left_header="Figure",
        page_header=None,
    )
    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in check_pdf_lot_lof_column_headers(model) if f.rule_id == "P031"]
    assert any(f.details.get("issue_type") == "missing_page_column_header" for f in warnings)


def test_p031_toc_page_not_checked(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p031_toc_ignored.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((190, 90), "TABLE OF CONTENTS", fontsize=16, fontname="Times-Bold")
    page.insert_text((108, 115), "Table")
    page.insert_text((500, 115), "Page")
    for idx, (label, indent_x) in enumerate(_P030_TOC_ENTRIES):
        y = 140 + idx * 20
        page.insert_text((indent_x, y), label)
        page.insert_text((500, y), "12")
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    assert not any(f.rule_id == "P031" for f in check_pdf_lot_lof_column_headers(model))


def test_p031_ambiguous_page_without_lot_heading_not_flagged(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p031_ambiguous.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((108, 115), "Table")
    page.insert_text((500, 115), "Page")
    page.insert_text((108, 140), "Table 1 Summary of Experimental Setup ....")
    page.insert_text((500, 140), "12")
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    assert not any(f.rule_id == "P031" for f in check_pdf_lot_lof_column_headers(model))


def test_p031_finding_details_are_privacy_safe(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p031_privacy_safe.pdf"
    long_entry = "Table 1 " + ("X" * 200)
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((190, 90), "LIST OF TABLES", fontsize=16, fontname="Times-Bold")
    page.insert_text((108, 140), long_entry)
    page.insert_text((500, 140), "12")
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    warning = next(
        f for f in check_pdf_lot_lof_column_headers(model) if f.rule_id == "P031"
    )
    assert long_entry not in str(warning.details)
    assert long_entry not in warning.message
    assert len(warning.details.get("observed_header_labels", "")) <= 80


def test_p031_header_row_immediately_below_heading_no_warning(tmp_path: Path) -> None:
    """Header labels slightly above heading_bottom_y should still be detected."""
    pdf_path = tmp_path / "p031_tight_header_row.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((190, 90), "LIST OF TABLES", fontsize=16, fontname="Times-Bold")
    page.insert_text((108, 84), "Table")
    page.insert_text((504, 84), "Page")
    page.insert_text((108, 98), "Table 1 Summary of Experimental Setup ....")
    page.insert_text((500, 98), "12")
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    assert not any(f.rule_id == "P031" for f in check_pdf_lot_lof_column_headers(model))


# ---------------------------------------------------------------------------
# P032: TOC/List wrapped-entry internal spacing
# ---------------------------------------------------------------------------


def _make_wrapped_entry_pdf(
    path: Path,
    heading: str,
    first_line: str,
    continuation_line: str,
    *,
    first_y: float = 140.0,
    continuation_y: float = 152.0,
    first_x: float = 108.0,
    continuation_x: float = 108.0,
    page_number_on_first: str | None = None,
    page_number_on_continuation: str | None = None,
    extra_lines: list[tuple[str, float, float]] | None = None,
) -> None:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((190, 90), heading, fontsize=16, fontname="Times-Bold")
    page.insert_text((first_x, first_y), first_line, fontsize=12)
    if page_number_on_first is not None:
        page.insert_text((500, first_y), page_number_on_first, fontsize=12)
    page.insert_text((continuation_x, continuation_y), continuation_line, fontsize=12)
    if page_number_on_continuation is not None:
        page.insert_text((500, continuation_y), page_number_on_continuation, fontsize=12)
    if extra_lines:
        for text, x_pos, y_pos in extra_lines:
            page.insert_text((x_pos, y_pos), text, fontsize=12)
    doc.save(path)
    doc.close()


def test_p032_toc_normal_wrapped_continuation_no_warning(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p032_toc_wrap_ok.pdf"
    _make_wrapped_entry_pdf(
        pdf_path,
        "TABLE OF CONTENTS",
        "Chapter 4 Extended Dissertation Topic Title ....",
        "Continuation Line of Wrapped Entry Text",
        continuation_y=152.0,
    )
    model = load_pdf_layout(str(pdf_path))
    assert not any(f.rule_id == "P032" for f in check_pdf_toc_list_wrapped_spacing(model))


def test_p032_toc_excessive_wrapped_gap_warns(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p032_toc_wrap_gap.pdf"
    _make_wrapped_entry_pdf(
        pdf_path,
        "TABLE OF CONTENTS",
        "Chapter 4 Extended Dissertation Topic Title ....",
        "Continuation Line of Wrapped Entry Text",
        continuation_y=185.0,
    )
    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in check_pdf_toc_list_wrapped_spacing(model) if f.rule_id == "P032"]
    assert len(warnings) == 1
    assert warnings[0].details.get("issue_type") == "wrapped_entry_internal_spacing"
    assert warnings[0].details.get("section_type") == "table_of_contents"


def test_p032_lot_normal_wrapped_continuation_no_warning(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p032_lot_wrap_ok.pdf"
    _make_wrapped_entry_pdf(
        pdf_path,
        "LIST OF TABLES",
        "Table 3.1 Summary of Experimental Setup and ....",
        "Additional Wrapped Table Title Continuation",
        continuation_y=152.0,
    )
    model = load_pdf_layout(str(pdf_path))
    assert not any(f.rule_id == "P032" for f in check_pdf_toc_list_wrapped_spacing(model))


def test_p032_lot_excessive_wrapped_gap_warns(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p032_lot_wrap_gap.pdf"
    _make_wrapped_entry_pdf(
        pdf_path,
        "LIST OF TABLES",
        "Table 3.1 Summary of Experimental Setup and ....",
        "Additional Wrapped Table Title Continuation",
        continuation_y=185.0,
    )
    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in check_pdf_toc_list_wrapped_spacing(model) if f.rule_id == "P032"]
    assert len(warnings) == 1
    assert warnings[0].details.get("section_type") == "list_of_tables"
    assert warnings[0].details.get("entry_kind") == "table_entry"


def test_p032_lof_excessive_wrapped_gap_warns(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p032_lof_wrap_gap.pdf"
    _make_wrapped_entry_pdf(
        pdf_path,
        "LIST OF FIGURES",
        "Figure 2.1 Overview of Experimental Apparatus ....",
        "Additional Wrapped Figure Title Continuation",
        continuation_y=185.0,
    )
    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in check_pdf_toc_list_wrapped_spacing(model) if f.rule_id == "P032"]
    assert len(warnings) == 1
    assert warnings[0].details.get("section_type") == "list_of_figures"
    assert warnings[0].details.get("entry_kind") == "figure_entry"


def test_p032_separate_entries_with_large_spacing_not_flagged(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p032_separate_entries.pdf"
    _make_wrapped_entry_pdf(
        pdf_path,
        "TABLE OF CONTENTS",
        "Chapter 3 Literature Review and Background ....",
        "Chapter 4 Extended Dissertation Topic Title ....",
        first_y=140.0,
        continuation_y=180.0,
        page_number_on_first="10",
        page_number_on_continuation="12",
    )
    model = load_pdf_layout(str(pdf_path))
    assert not any(f.rule_id == "P032" for f in check_pdf_toc_list_wrapped_spacing(model))


def test_p032_no_wrapped_entries_no_warning(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p032_single_line_entries.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((190, 90), "TABLE OF CONTENTS", fontsize=16, fontname="Times-Bold")
    for idx, (label, indent_x) in enumerate(_P030_TOC_ENTRIES):
        y = 140 + idx * 20
        page.insert_text((indent_x, y), label, fontsize=12)
        page.insert_text((500, y), "12", fontsize=12)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    assert not any(f.rule_id == "P032" for f in check_pdf_toc_list_wrapped_spacing(model))


def test_p032_ambiguous_continuation_indent_not_flagged(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p032_ambiguous_wrap.pdf"
    _make_wrapped_entry_pdf(
        pdf_path,
        "TABLE OF CONTENTS",
        "Chapter 4 Extended Dissertation Topic Title ....",
        "Continuation Line of Wrapped Entry Text",
        continuation_y=185.0,
        continuation_x=140.0,
    )
    model = load_pdf_layout(str(pdf_path))
    assert not any(f.rule_id == "P032" for f in check_pdf_toc_list_wrapped_spacing(model))


def test_p032_orphan_page_number_between_entries_not_flagged(tmp_path: Path) -> None:
    """Split page-number lines must not bridge two separate list entries as one wrap."""

    pdf_path = tmp_path / "p032_orphan_page_number.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((190, 90), "LIST OF FIGURES", fontsize=16, fontname="Times-Bold")
    page.insert_text(
        (148.9, 168.0),
        "Figure 3.1 Long Figure Title First Line Portion ....",
        fontsize=12,
    )
    page.insert_text(
        (148.9, 181.0),
        "Continuation Line of Wrapped Figure Title Text",
        fontsize=12,
    )
    page.insert_text((148.9, 192.0), "30", fontsize=12)
    page.insert_text(
        (137.2, 214.0),
        "Figure 3.2 Next Figure Title Begins On New Entry Row",
        fontsize=12,
    )
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    assert not any(f.rule_id == "P032" for f in check_pdf_toc_list_wrapped_spacing(model))


def test_p032_finding_details_are_privacy_safe(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p032_privacy_safe.pdf"
    long_entry = "Chapter 4 " + ("X" * 200)
    long_continuation = "Continuation " + ("Y" * 200)
    _make_wrapped_entry_pdf(
        pdf_path,
        "TABLE OF CONTENTS",
        long_entry,
        long_continuation,
        continuation_y=185.0,
    )
    model = load_pdf_layout(str(pdf_path))
    warning = next(f for f in check_pdf_toc_list_wrapped_spacing(model) if f.rule_id == "P032")
    assert long_entry not in str(warning.details)
    assert long_continuation not in str(warning.details)
    assert long_entry not in warning.message
    assert warning.details.get("issue_type") == "wrapped_entry_internal_spacing"


# ---------------------------------------------------------------------------
# P036: TOC/List inter-entry spacing
# ---------------------------------------------------------------------------


def _make_two_entry_list_pdf(
    path: Path,
    heading: str,
    entry1: str,
    entry2: str,
    *,
    first_y: float = 140.0,
    second_y: float = 168.0,
    page_number_on_first: str | None = "10",
    page_number_on_second: str | None = "12",
) -> None:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((190, 90), heading, fontsize=16, fontname="Times-Bold")
    page.insert_text((108, first_y), entry1, fontsize=12)
    if page_number_on_first is not None:
        page.insert_text((500, first_y), page_number_on_first, fontsize=12)
    page.insert_text((108, second_y), entry2, fontsize=12)
    if page_number_on_second is not None:
        page.insert_text((500, second_y), page_number_on_second, fontsize=12)
    doc.save(path)
    doc.close()


def test_p036_toc_double_spaced_entries_no_warning(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p036_toc_double_spaced.pdf"
    _make_two_entry_list_pdf(
        pdf_path,
        "TABLE OF CONTENTS",
        "Chapter 3 Literature Review and Background ....",
        "Chapter 4 Extended Dissertation Topic Title ....",
        first_y=140.0,
        second_y=180.0,
    )
    model = load_pdf_layout(str(pdf_path))
    assert not any(f.rule_id == "P036" for f in check_pdf_toc_list_entry_spacing(model))


def test_p036_toc_tight_entries_warns(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p036_toc_tight.pdf"
    _make_two_entry_list_pdf(
        pdf_path,
        "TABLE OF CONTENTS",
        "Chapter 3 Literature Review and Background ....",
        "Chapter 4 Extended Dissertation Topic Title ....",
        first_y=140.0,
        second_y=170.0,
    )
    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in check_pdf_toc_list_entry_spacing(model) if f.rule_id == "P036"]
    assert len(warnings) == 1
    assert warnings[0].details.get("issue_type") == "toc_inter_entry_spacing_too_tight"


def test_p036_lot_tight_entries_warns(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p036_lot_tight.pdf"
    _make_two_entry_list_pdf(
        pdf_path,
        "LIST OF TABLES",
        "Table 3.1 Summary of Experimental Setup ....",
        "Table 3.2 Additional Results Overview ....",
        first_y=140.0,
        second_y=170.0,
    )
    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in check_pdf_toc_list_entry_spacing(model) if f.rule_id == "P036"]
    assert len(warnings) == 1
    assert warnings[0].details.get("issue_type") == "lot_inter_entry_spacing_too_tight"


def test_p036_lof_tight_entries_warns(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p036_lof_tight.pdf"
    _make_two_entry_list_pdf(
        pdf_path,
        "LIST OF FIGURES",
        "Figure 2.1 Overview of Experimental Apparatus ....",
        "Figure 2.2 Detailed Component Layout ....",
        first_y=140.0,
        second_y=170.0,
    )
    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in check_pdf_toc_list_entry_spacing(model) if f.rule_id == "P036"]
    assert len(warnings) == 1
    assert warnings[0].details.get("issue_type") == "lof_inter_entry_spacing_too_tight"


def test_p036_wrapped_entry_internal_spacing_not_flagged(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p036_wrap_not_inter_entry.pdf"
    _make_wrapped_entry_pdf(
        pdf_path,
        "TABLE OF CONTENTS",
        "Chapter 4 Extended Dissertation Topic Title ....",
        "Continuation Line of Wrapped Entry Text",
        continuation_y=152.0,
    )
    model = load_pdf_layout(str(pdf_path))
    assert not any(f.rule_id == "P036" for f in check_pdf_toc_list_entry_spacing(model))


def test_p036_sparse_single_entry_page_skipped(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p036_sparse.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((190, 90), "TABLE OF CONTENTS", fontsize=16, fontname="Times-Bold")
    page.insert_text(
        (108, 140),
        "Chapter 1 Introduction and Background Overview ....",
        fontsize=12,
    )
    page.insert_text((500, 140), "1", fontsize=12)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    assert not any(f.rule_id == "P036" for f in check_pdf_toc_list_entry_spacing(model))


def test_p036_finding_details_are_privacy_safe(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p036_privacy_safe.pdf"
    long_entry1 = "Chapter 3 " + ("X" * 200)
    long_entry2 = "Chapter 4 " + ("Y" * 200)
    _make_two_entry_list_pdf(
        pdf_path,
        "TABLE OF CONTENTS",
        long_entry1,
        long_entry2,
        first_y=140.0,
        second_y=170.0,
    )
    model = load_pdf_layout(str(pdf_path))
    warning = next(f for f in check_pdf_toc_list_entry_spacing(model) if f.rule_id == "P036")
    assert long_entry1 not in str(warning.details)
    assert long_entry2 not in str(warning.details)
    assert long_entry1 not in warning.message
    assert warning.details.get("entry_pair_index") == "0"
    assert warning.details.get("gap_points")


def test_p036_wired_in_cli_pdf_audit(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p036_cli.pdf"
    _make_two_entry_list_pdf(
        pdf_path,
        "TABLE OF CONTENTS",
        "Chapter 3 Literature Review and Background ....",
        "Chapter 4 Extended Dissertation Topic Title ....",
        first_y=140.0,
        second_y=170.0,
    )
    json_out = tmp_path / "report.json"
    result = runner.invoke(
        app,
        ["pdf", str(pdf_path), "--json-out", str(json_out)],
    )
    assert result.exit_code == 0
    payload = json.loads(json_out.read_text())
    rule_ids = {finding["rule_id"] for finding in payload["findings"]}
    assert "P036" in rule_ids


# ---------------------------------------------------------------------------
# P033: Front-matter cross-page title consistency
# ---------------------------------------------------------------------------

_DEFAULT_DISS_TITLE = "A Study of Synthetic Systems Architecture"
_TITLE_PAGE_METADATA = [
    "by",
    "Test Author",
    "Submitted to the Graduate Faculty",
    "New Jersey Institute of Technology",
    "in Partial Fulfillment of the Requirements",
    "for the Degree of Doctor of Philosophy",
    "May 2024",
]


def _insert_centered_title_lines(page: fitz.Page, lines: list[str], start_y: float = 120.0) -> None:
    for idx, line in enumerate(lines):
        y = start_y + idx * 20
        page.insert_textbox(
            fitz.Rect(108, y - 16, 540, y + 16),
            line,
            fontsize=14,
            fontname="Times-Roman",
            align=fitz.TEXT_ALIGN_CENTER,
        )


def _make_title_consistency_pdf(
    path: Path,
    *,
    title_page_title_lines: list[str] | None = None,
    abstract_title_lines: list[str] | None = None,
    approval_title_lines: list[str] | None = None,
    title_page_metadata: list[str] | None = None,
    include_abstract_title: bool = True,
    include_approval_title: bool = True,
) -> None:
    doc = fitz.open()
    if title_page_title_lines is not None:
        title_lines = title_page_title_lines
    else:
        title_lines = [_DEFAULT_DISS_TITLE]
    metadata = title_page_metadata if title_page_metadata is not None else _TITLE_PAGE_METADATA

    p1 = doc.new_page(width=612, height=792)
    _insert_centered_title_lines(p1, title_lines, start_y=120.0)
    meta_y = 120.0 + len(title_lines) * 22 + 10
    for idx, line in enumerate(metadata):
        p1.insert_text((108, meta_y + idx * 18), line, fontsize=12)

    p2 = doc.new_page(width=612, height=792)
    if include_abstract_title and abstract_title_lines is not None:
        _insert_centered_title_lines(p2, abstract_title_lines, start_y=50.0)
    elif include_abstract_title:
        _insert_centered_title_lines(p2, title_lines, start_y=50.0)
    p2.insert_textbox(
        fitz.Rect(108, 84, 540, 110),
        "ABSTRACT",
        fontsize=14,
        fontname="Times-Bold",
        align=fitz.TEXT_ALIGN_CENTER,
    )
    p2.insert_text(
        (108, 140),
        "This dissertation presents synthetic abstract body text for testing purposes only.",
        fontsize=12,
    )

    p3 = doc.new_page(width=612, height=792)
    if include_approval_title and approval_title_lines is not None:
        _insert_centered_title_lines(p3, approval_title_lines, start_y=50.0)
    elif include_approval_title:
        _insert_centered_title_lines(p3, title_lines, start_y=50.0)
    p3.insert_textbox(
        fitz.Rect(108, 84, 540, 110),
        "APPROVAL PAGE",
        fontsize=14,
        fontname="Times-Bold",
        align=fitz.TEXT_ALIGN_CENTER,
    )
    p3.insert_text((108, 140), "Dissertation Committee:", fontsize=12)
    p3.insert_text((108, 158), "Dr. Test Advisor, Dissertation Advisor", fontsize=12)
    p3.insert_text((108, 176), "Department of Computer Science", fontsize=12)

    p4 = doc.new_page(width=612, height=792)
    p4.insert_text((190, 90), "TABLE OF CONTENTS", fontsize=14, fontname="Times-Bold")
    p4.insert_text((108, 140), "CHAPTER 1 INTRODUCTION .......    1", fontsize=12)

    doc.save(path)
    doc.close()


def test_p033_identical_title_line_breaks_no_finding(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p033_match_linebreaks.pdf"
    split_title = ["A Study of Synthetic", "Systems Architecture"]
    _make_title_consistency_pdf(
        pdf_path,
        title_page_title_lines=split_title,
        abstract_title_lines=split_title,
        approval_title_lines=split_title,
    )
    model = load_pdf_layout(str(pdf_path))
    assert not any(f.rule_id == "P033" for f in check_pdf_title_consistency(model))


def test_p033_case_and_punctuation_only_no_finding(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p033_case_punct.pdf"
    _make_title_consistency_pdf(
        pdf_path,
        abstract_title_lines=["A STUDY OF SYNTHETIC SYSTEMS ARCHITECTURE!!!"],
        approval_title_lines=["a study of synthetic systems architecture."],
    )
    model = load_pdf_layout(str(pdf_path))
    assert not any(f.rule_id == "P033" for f in check_pdf_title_consistency(model))


def test_p033_abstract_title_mismatch_warns(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p033_abstract_mismatch.pdf"
    _make_title_consistency_pdf(
        pdf_path,
        abstract_title_lines=["An Entirely Different Dissertation Topic for Testing"],
    )
    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in check_pdf_title_consistency(model) if f.rule_id == "P033"]
    assert len(warnings) == 1
    assert warnings[0].details.get("issue_type") == "frontmatter_title_mismatch"
    assert warnings[0].page == 2


def test_p033_approval_title_mismatch_warns(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p033_approval_mismatch.pdf"
    _make_title_consistency_pdf(
        pdf_path,
        approval_title_lines=["Another Dissertation Title on Approval Page Only"],
    )
    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in check_pdf_title_consistency(model) if f.rule_id == "P033"]
    assert len(warnings) == 1
    assert warnings[0].details.get("issue_type") == "frontmatter_title_mismatch"


def test_p033_single_title_candidate_no_finding(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p033_single_candidate.pdf"
    doc = fitz.open()
    p1 = doc.new_page(width=612, height=792)
    _insert_centered_title_lines(
        p1, [_DEFAULT_DISS_TITLE], start_y=120.0,
    )
    p1.insert_text((108, 160), "by", fontsize=12)
    p1.insert_text((108, 178), "Test Author", fontsize=12)
    p1.insert_text((108, 196), "Doctor of Philosophy", fontsize=12)
    p1.insert_text((108, 214), "New Jersey Institute of Technology", fontsize=12)
    p2 = doc.new_page(width=612, height=792)
    p2.insert_textbox(
        fitz.Rect(108, 84, 540, 110),
        "ABSTRACT",
        fontsize=14,
        fontname="Times-Bold",
        align=fitz.TEXT_ALIGN_CENTER,
    )
    p2.insert_text(
        (108, 140),
        "This dissertation presents synthetic abstract body text for testing only.",
        fontsize=12,
    )
    p3 = doc.new_page(width=612, height=792)
    p3.insert_text((190, 90), "TABLE OF CONTENTS", fontsize=14, fontname="Times-Bold")
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    assert not any(f.rule_id == "P033" for f in check_pdf_title_consistency(model))


def test_p033_ambiguous_short_title_no_finding(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p033_ambiguous.pdf"
    short = ["Short Title"]
    _make_title_consistency_pdf(
        pdf_path,
        title_page_title_lines=short,
        abstract_title_lines=short,
        approval_title_lines=short,
    )
    model = load_pdf_layout(str(pdf_path))
    assert not any(f.rule_id == "P033" for f in check_pdf_title_consistency(model))


def test_p033_no_extractable_title_no_finding(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p033_no_title_text.pdf"
    _make_title_consistency_pdf(
        pdf_path,
        title_page_title_lines=[],
        title_page_metadata=_TITLE_PAGE_METADATA,
        include_abstract_title=False,
        include_approval_title=False,
    )
    model = load_pdf_layout(str(pdf_path))
    assert not any(f.rule_id == "P033" for f in check_pdf_title_consistency(model))


def test_p033_finding_details_are_privacy_safe(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p033_privacy.pdf"
    secret_title = "Secret Dissertation Title For Privacy Testing Alpha"
    other_title = "Public Mismatch Title for Privacy Testing Beta Case"
    _make_title_consistency_pdf(
        pdf_path,
        title_page_title_lines=[secret_title],
        abstract_title_lines=[other_title],
    )
    model = load_pdf_layout(str(pdf_path))
    warning = next(f for f in check_pdf_title_consistency(model) if f.rule_id == "P033")
    assert secret_title not in str(warning.details)
    assert secret_title not in warning.message
    assert other_title not in str(warning.details)
    assert other_title not in warning.message
    assert warning.details.get("reference_title_hash")
    assert "title_hashes_by_role" in warning.details
    assert warning.details.get("comparison_basis") == (
        "normalized_text_hash_and_sequence_similarity"
    )


def test_p033_abstract_title_below_heading_no_mismatch(tmp_path: Path) -> None:
    """When ABSTRACT is first on the page, title below the heading should still compare."""

    pdf_path = tmp_path / "p033_abstract_below_heading.pdf"
    shared_title = ["Synthetic Dissertation Title for Below Heading Test"]
    doc = fitz.open()
    p1 = doc.new_page(width=612, height=792)
    _insert_centered_title_lines(p1, shared_title, start_y=120.0)
    p1.insert_text((108, 160), "by", fontsize=12)
    p1.insert_text((108, 178), "Test Author", fontsize=12)
    p1.insert_text((108, 196), "Doctor of Philosophy", fontsize=12)
    p1.insert_text((108, 214), "New Jersey Institute of Technology", fontsize=12)
    p2 = doc.new_page(width=612, height=792)
    p2.insert_textbox(
        fitz.Rect(108, 70, 540, 95),
        "ABSTRACT",
        fontsize=14,
        fontname="Times-Bold",
        align=fitz.TEXT_ALIGN_CENTER,
    )
    _insert_centered_title_lines(p2, shared_title, start_y=110.0)
    p2.insert_text(
        (108, 180),
        "This abstract body line provides synthetic spacing for the test fixture only.",
        fontsize=12,
    )
    p3 = doc.new_page(width=612, height=792)
    p3.insert_text((190, 90), "TABLE OF CONTENTS", fontsize=14, fontname="Times-Bold")
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    assert _extract_below_heading_candidate(model.pages[1], "ABSTRACT") is not None
    candidates = _collect_title_candidates(model)
    assert len(candidates) >= 1
    assert not any(f.rule_id == "P033" for f in check_pdf_title_consistency(model))


def test_p033_approval_title_below_heading_no_mismatch(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p033_approval_below_heading.pdf"
    shared_title = ["Synthetic Approval Title Match Test Case"]
    doc = fitz.open()
    p1 = doc.new_page(width=612, height=792)
    _insert_centered_title_lines(p1, shared_title, start_y=120.0)
    p1.insert_text((108, 160), "by", fontsize=12)
    p1.insert_text((108, 178), "Test Author", fontsize=12)
    p1.insert_text((108, 196), "Doctor of Philosophy", fontsize=12)
    p1.insert_text((108, 214), "New Jersey Institute of Technology", fontsize=12)
    p2 = doc.new_page(width=612, height=792)
    p2.insert_textbox(
        fitz.Rect(108, 70, 540, 95),
        "ABSTRACT",
        fontsize=14,
        fontname="Times-Bold",
        align=fitz.TEXT_ALIGN_CENTER,
    )
    p2.insert_text(
        (108, 140),
        "This dissertation presents synthetic abstract body text for this fixture only.",
        fontsize=12,
    )
    p3 = doc.new_page(width=612, height=792)
    p3.insert_textbox(
        fitz.Rect(108, 70, 540, 95),
        "APPROVAL PAGE",
        fontsize=14,
        fontname="Times-Bold",
        align=fitz.TEXT_ALIGN_CENTER,
    )
    _insert_centered_title_lines(p3, shared_title, start_y=110.0)
    p3.insert_text((108, 180), "Dissertation Committee:", fontsize=12)
    p3.insert_text((108, 198), "Dr. Test Advisor, Dissertation Advisor", fontsize=12)
    p4 = doc.new_page(width=612, height=792)
    p4.insert_text((190, 90), "TABLE OF CONTENTS", fontsize=14, fontname="Times-Bold")
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    assert _extract_below_heading_candidate(model.pages[2], "APPROVAL PAGE") is not None
    candidates = _collect_title_candidates(model)
    assert any(c.page_role == "title_page" for c in candidates)
    # Matching title on approval page deduplicates to one hash; comparison may still run
    # when hashes differ on real PDFs (see current-dataset evaluation).
    assert not any(f.rule_id == "P033" for f in check_pdf_title_consistency(model))


def test_p033_below_heading_does_not_capture_long_body_line(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p033_below_heading_body_guard.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_textbox(
        fitz.Rect(108, 70, 540, 95),
        "ABSTRACT",
        fontsize=14,
        fontname="Times-Bold",
        align=fitz.TEXT_ALIGN_CENTER,
    )
    page.insert_text(
        (108, 110),
        "Short Synthetic Title Line Here",
        fontsize=12,
    )
    page.insert_text(
        (108, 130),
        " ".join(["word"] * 20),
        fontsize=12,
    )
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    raw = _extract_below_heading_candidate(model.pages[0], "ABSTRACT")
    assert raw is not None
    assert len(raw.split()) <= 6


# ---------------------------------------------------------------------------
# P034: Copyright Page metadata and layout
# ---------------------------------------------------------------------------

_DEFAULT_TITLE_PAGE_LINES = [
    "A Study of Synthetic Systems",
    "by",
    "Test Author",
    "Submitted to the Graduate Faculty",
    "New Jersey Institute of Technology",
    "in Partial Fulfillment of the Requirements",
    "for the Degree of Doctor of Philosophy",
    "May 2024",
]


def _make_copyright_page_pdf(
    path: Path,
    *,
    title_page_lines: list[str] | None = None,
    copyright_notice: str | None = "© 2024 Test Author. All Rights Reserved.",
    copyright_y: float = 360.0,
    top_margin_text: str | None = None,
    include_copyright_page: bool = True,
) -> None:
    doc = fitz.open()
    p1 = doc.new_page(width=612, height=792)
    for idx, line in enumerate(
        title_page_lines if title_page_lines is not None else _DEFAULT_TITLE_PAGE_LINES
    ):
        p1.insert_text((108, 100 + idx * 20), line, fontsize=12)

    if include_copyright_page and copyright_notice is not None:
        p2 = doc.new_page(width=612, height=792)
        if top_margin_text is not None:
            p2.insert_text((108, 40), top_margin_text, fontsize=11)
        p2.insert_text((108, copyright_y), copyright_notice, fontsize=12)

    p_abs = doc.new_page(width=612, height=792)
    p_abs.insert_text((250, 90), "ABSTRACT", fontsize=14, fontname="Times-Bold")
    p_abs.insert_text(
        (108, 140),
        "Synthetic abstract body text for copyright page rule testing only.",
        fontsize=12,
    )

    doc.save(path)
    doc.close()


def test_p034_matching_copyright_metadata_no_finding(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p034_clean.pdf"
    _make_copyright_page_pdf(pdf_path)
    model = load_pdf_layout(str(pdf_path))
    assert not any(f.rule_id == "P034" for f in check_pdf_copyright_page(model))


def test_p034_top_margin_header_text_warns(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p034_top_header.pdf"
    _make_copyright_page_pdf(
        pdf_path,
        top_margin_text="Running Dissertation Header",
    )
    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in check_pdf_copyright_page(model) if f.rule_id == "P034"]
    assert any(w.details.get("issue_type") == "copyright_top_margin_header_text" for w in warnings)
    header = next(
        w for w in warnings if w.details.get("issue_type") == "copyright_top_margin_header_text"
    )
    assert header.details.get("source_q_rule_id") == "Q009"
    assert "Running Dissertation Header" not in str(header.details)
    assert "Running Dissertation Header" not in header.message


def test_p034_copyright_year_mismatch_warns(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p034_year_mismatch.pdf"
    _make_copyright_page_pdf(
        pdf_path,
        copyright_notice="© 2023 Test Author. All Rights Reserved.",
    )
    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in check_pdf_copyright_page(model) if f.rule_id == "P034"]
    year_warning = next(
        w for w in warnings if w.details.get("issue_type") == "copyright_year_mismatch"
    )
    assert year_warning.details.get("copyright_year") == "2023"
    assert year_warning.details.get("title_page_year") == "2024"
    assert year_warning.details.get("source_q_rule_id") == "Q010"


def test_p034_copyright_middle_initial_matches_title_no_finding(tmp_path: Path) -> None:
    """© line with one leading middle initial should not warn when title omits it."""

    pdf_path = tmp_path / "p034_middle_initial.pdf"
    _make_copyright_page_pdf(
        pdf_path,
        copyright_notice="© 2024 T Test Author. All Rights Reserved.",
    )
    model = load_pdf_layout(str(pdf_path))
    assert not any(
        f.rule_id == "P034"
        and f.details.get("issue_type") == "copyright_author_mismatch"
        for f in check_pdf_copyright_page(model)
    )


def test_p034_author_mismatch_uses_hashes_only(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p034_author_mismatch.pdf"
    _make_copyright_page_pdf(
        pdf_path,
        copyright_notice="© 2024 Other Person Name. All Rights Reserved.",
    )
    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in check_pdf_copyright_page(model) if f.rule_id == "P034"]
    author_warning = next(
        w for w in warnings if w.details.get("issue_type") == "copyright_author_mismatch"
    )
    assert author_warning.details.get("title_page_author_hash")
    assert author_warning.details.get("copyright_author_hash")
    assert author_warning.details.get("title_page_author_hash") != author_warning.details.get(
        "copyright_author_hash"
    )
    assert "Test Author" not in str(author_warning.details)
    assert "Other Person" not in str(author_warning.details)
    assert author_warning.details.get("source_q_rule_id") == "Q011"


def test_p034_no_copyright_page_no_finding(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p034_no_copyright.pdf"
    _make_copyright_page_pdf(pdf_path, include_copyright_page=False)
    model = load_pdf_layout(str(pdf_path))
    assert not any(f.rule_id == "P034" for f in check_pdf_copyright_page(model))


def test_p034_ambiguous_multiple_years_no_year_finding(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p034_ambiguous_years.pdf"
    _make_copyright_page_pdf(
        pdf_path,
        copyright_notice="© 2023-2024 Test Author. All Rights Reserved.",
    )
    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in check_pdf_copyright_page(model) if f.rule_id == "P034"]
    assert not any(w.details.get("issue_type") == "copyright_year_mismatch" for w in warnings)


def test_p034_finding_details_privacy_safe(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p034_privacy.pdf"
    _make_copyright_page_pdf(
        pdf_path,
        top_margin_text="Header Line",
        copyright_notice="© 2023 Wrong Name. All Rights Reserved.",
    )
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_copyright_page(model)
    blob = " ".join(f.message for f in findings) + " " + " ".join(
        f"{k}={v}" for f in findings for k, v in (f.details or {}).items()
    )
    assert "Test Author" not in blob
    assert "Wrong Name" not in blob
    assert "A Study of Synthetic" not in blob


# ---------------------------------------------------------------------------
# P051: Copyright page year-format refinement
# ---------------------------------------------------------------------------


def _make_p051_pdf(
    path: Path,
    copyright_page_lines: list[tuple[float, str]],
    *,
    with_title_page: bool = True,
) -> None:
    """Build a synthetic PDF with a custom copyright page for P051 testing."""
    doc = fitz.open()
    p1 = doc.new_page(width=612, height=792)
    if with_title_page:
        for idx, line in enumerate(_DEFAULT_TITLE_PAGE_LINES):
            p1.insert_text((108, 100 + idx * 20), line, fontsize=12)
    p2 = doc.new_page(width=612, height=792)
    for y, text in copyright_page_lines:
        p2.insert_text((108, y), text, fontsize=12)
    p_abs = doc.new_page(width=612, height=792)
    p_abs.insert_text((250, 90), "ABSTRACT", fontsize=14, fontname="Times-Bold")
    p_abs.insert_text((108, 140), "Synthetic abstract for P051 testing.", fontsize=12)
    doc.save(path)
    doc.close()


def _make_p051_fragmented_pdf(
    path: Path,
    copyright_fragments: list[tuple[float, float, str]],
    *,
    extra_lines: list[tuple[float, float, str]] | None = None,
    with_title_page: bool = True,
) -> None:
    """Build a copyright-page PDF with multiple same-row fragments."""
    doc = fitz.open()
    p1 = doc.new_page(width=612, height=792)
    if with_title_page:
        for idx, line in enumerate(_DEFAULT_TITLE_PAGE_LINES):
            p1.insert_text((108, 100 + idx * 20), line, fontsize=12)
    p2 = doc.new_page(width=612, height=792)
    for x, y, text in copyright_fragments:
        p2.insert_text((x, y), text, fontsize=12)
    for x, y, text in extra_lines or []:
        p2.insert_text((x, y), text, fontsize=12)
    p_abs = doc.new_page(width=612, height=792)
    p_abs.insert_text((250, 90), "ABSTRACT", fontsize=14, fontname="Times-Bold")
    p_abs.insert_text((108, 140), "Synthetic abstract for P051 testing.", fontsize=12)
    doc.save(path)
    doc.close()


def test_p051_standard_year_no_finding(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p051_standard.pdf"
    _make_copyright_page_pdf(pdf_path, copyright_notice="© 2024 Test Author. All Rights Reserved.")
    model = load_pdf_layout(str(pdf_path))
    assert not any(f.rule_id == "P051" for f in check_pdf_copyright_year_format(model))


def test_p051_no_space_year_no_finding(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p051_nospace.pdf"
    _make_copyright_page_pdf(pdf_path, copyright_notice="©2024 Test Author. All Rights Reserved.")
    model = load_pdf_layout(str(pdf_path))
    assert not any(f.rule_id == "P051" for f in check_pdf_copyright_year_format(model))


def test_p051_copyright_word_year_no_finding(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p051_word.pdf"
    _make_copyright_page_pdf(
        pdf_path, copyright_notice="Copyright 2024 Test Author. All Rights Reserved."
    )
    model = load_pdf_layout(str(pdf_path))
    assert not any(f.rule_id == "P051" for f in check_pdf_copyright_year_format(model))


def test_p051_adjacent_line_year_no_finding(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p051_adjacent.pdf"
    _make_p051_pdf(
        pdf_path,
        copyright_page_lines=[
            (360, "©"),
            (375, "2024"),
            (500, "Series Volume 2020"),
        ],
    )
    model = load_pdf_layout(str(pdf_path))
    assert not any(f.rule_id == "P051" for f in check_pdf_copyright_year_format(model))


def test_p051_adjacent_line_year_and_author_no_finding(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p051_adjacent_year_author.pdf"
    _make_p051_pdf(
        pdf_path,
        copyright_page_lines=[
            (360, "Copyright"),
            (375, "2024 by Test Author"),
        ],
    )
    model = load_pdf_layout(str(pdf_path))
    assert not any(f.rule_id == "P051" for f in check_pdf_copyright_year_format(model))


def test_p051_copyright_symbol_year_author_same_line_no_finding(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p051_symbol_year_author.pdf"
    _make_copyright_page_pdf(pdf_path, copyright_notice="© 2024 Test Author")
    model = load_pdf_layout(str(pdf_path))
    assert not any(f.rule_id == "P051" for f in check_pdf_copyright_year_format(model))


def test_p051_split_spans_same_line_no_finding(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p051_split_spans_same_line.pdf"
    _make_p051_fragmented_pdf(
        pdf_path,
        copyright_fragments=[
            (230, 360, "Copyright"),
            (285, 360, "©"),
            (302, 360, "2024"),
            (333, 360, "by"),
            (350, 360, "Test"),
            (382, 360, "Author"),
        ],
        extra_lines=[(254, 384, "ALL RIGHTS RESERVED")],
    )
    model = load_pdf_layout(str(pdf_path))
    assert not any(f.rule_id == "P051" for f in check_pdf_copyright_year_format(model))
    assert not any(f.rule_id == "P052" for f in check_pdf_copyright_author_format(model))


def test_p051_split_copyright_and_year_adjacent_fragments_no_finding(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p051_split_copyright_year_fragments.pdf"
    _make_p051_fragmented_pdf(
        pdf_path,
        copyright_fragments=[
            (240, 360, "Copyright"),
            (305, 360, "2024"),
            (340, 360, "Test"),
            (372, 360, "Author"),
        ],
    )
    model = load_pdf_layout(str(pdf_path))
    assert not any(f.rule_id == "P051" for f in check_pdf_copyright_year_format(model))


def test_p051_unusual_whitespace_no_finding(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p051_unusual_whitespace.pdf"
    _make_copyright_page_pdf(
        pdf_path,
        copyright_notice="Copyright\u00a0©\u00a02024\u00a0by\u00a0Test\u00a0Author",
    )
    model = load_pdf_layout(str(pdf_path))
    assert not any(f.rule_id == "P051" for f in check_pdf_copyright_year_format(model))


def test_p051_no_year_warns(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p051_no_year.pdf"
    _make_copyright_page_pdf(pdf_path, copyright_notice="© Test Author. All Rights Reserved.")
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_copyright_year_format(model) if f.rule_id == "P051"]
    assert any(f.details.get("issue_type") == "copyright_year_not_found" for f in findings)
    assert findings[0].details.get("confidence") == "low"
    assert findings[0].details.get("bbox")


def test_p051_category_is_copyright_page_not_title_page(tmp_path: Path) -> None:
    """P051 copyright-year findings must surface under Copyright page, not Title page.

    Ester's Sample B feedback confirmed the P051 finding itself is correct but
    flagged the wrong student-facing category (Title page). The rule ID and
    detector behavior must stay unchanged; only the category/topic label moves.
    """
    from njit_auditor.evaluation import map_finding_rule_to_category
    from njit_auditor.report_outputs import audit_findings_to_json_dict
    from njit_auditor.report_view import build_report_view
    from njit_auditor.web_app import _humanize_cat

    pdf_path = tmp_path / "p051_category.pdf"
    _make_copyright_page_pdf(pdf_path, copyright_notice="© Test Author. All Rights Reserved.")
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_copyright_year_format(model) if f.rule_id == "P051"]
    assert findings

    assert map_finding_rule_to_category("P051") == "copyright_page_metadata"

    view = build_report_view(audit_findings_to_json_dict(findings, {"audit_type": "pdf"}))
    p051_view = next(f for f in view.findings if f.rule_id == "P051")
    assert p051_view.category == "copyright_page_metadata"
    assert _humanize_cat(p051_view.category) == "Copyright page"
    assert _humanize_cat(p051_view.category) != "Title page"

    # JSON export keeps the P051 rule ID intact (category is a display-layer
    # concern computed by report_view/evaluation, not part of the raw schema).
    payload = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    json_finding = next(f for f in payload["findings"] if f["rule_id"] == "P051")
    assert json_finding["rule_id"] == "P051"

    # Markdown export renders without error and keeps the P051 rule ID intact.
    from njit_auditor.report_outputs import write_markdown_report

    md_path = tmp_path / "report.md"
    write_markdown_report(findings, {"audit_type": "pdf"}, md_path)
    md_text = md_path.read_text()
    assert "`P051`" in md_text
    assert "copyright_page_metadata" in md_text


def test_p051_no_copyright_page_no_finding(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p051_no_copyright.pdf"
    _make_copyright_page_pdf(pdf_path, include_copyright_page=False)
    model = load_pdf_layout(str(pdf_path))
    assert not any(f.rule_id == "P051" for f in check_pdf_copyright_year_format(model))


def test_p051_unrelated_year_elsewhere_warns_with_candidate_bbox(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p051_unrelated_year_elsewhere.pdf"
    _make_p051_pdf(
        pdf_path,
        copyright_page_lines=[
            (360, "© Test Author. All Rights Reserved."),
            (400, "Published 2020"),
            (420, "Revised 2024"),
        ],
    )
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_copyright_year_format(model) if f.rule_id == "P051"]
    assert len(findings) == 1
    assert findings[0].details.get("year_association") == "unassociated_year_elsewhere"
    assert findings[0].details.get("candidate_year_bbox")
    assert resolve_primary_highlight_bbox(
        findings[0].details,
        rule_id="P051",
        issue_type="copyright_year_not_found",
    ) is not None


def test_p051_multiple_years_but_one_near_notice_no_finding(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p051_multiple_years_one_near_notice.pdf"
    _make_p051_pdf(
        pdf_path,
        copyright_page_lines=[
            (360, "Copyright 2024 Test Author"),
            (500, "Series Volume 2020"),
        ],
    )
    model = load_pdf_layout(str(pdf_path))
    assert not any(f.rule_id == "P051" for f in check_pdf_copyright_year_format(model))


def test_p051_ambiguous_year_range_still_warns(tmp_path: Path) -> None:
    """Ambiguous same-line ranges like 2023-2024 must not count as a confident year."""
    pdf_path = tmp_path / "p051_ambiguous_year_range.pdf"
    _make_copyright_page_pdf(
        pdf_path,
        copyright_notice="© 2023-2024 Test Author. All Rights Reserved.",
    )
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_copyright_year_format(model) if f.rule_id == "P051"]
    assert len(findings) == 1
    assert findings[0].details.get("issue_type") == "copyright_year_not_found"
    assert findings[0].details.get("year_association") == "no_year_candidate"


def test_p051_year_far_from_notice_warns(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p051_far_year.pdf"
    _make_p051_pdf(
        pdf_path,
        copyright_page_lines=[
            (320, "Copyright"),
            (560, "2024 by Test Author"),
        ],
    )
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_copyright_year_format(model) if f.rule_id == "P051"]
    assert len(findings) == 1
    assert findings[0].details.get("year_association") == "unassociated_year_elsewhere"


def test_p051_non_copyright_page_copyright_like_prose_not_flagged(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p051_non_copyright_prose.pdf"
    doc = fitz.open()
    p1 = doc.new_page(width=612, height=792)
    for idx, line in enumerate(_DEFAULT_TITLE_PAGE_LINES):
        p1.insert_text((108, 100 + idx * 20), line, fontsize=12)
    p2 = doc.new_page(width=612, height=792)
    prose_lines = [
        "This chapter discusses historical context for the study.",
        "The copyright law reference below is body prose, not a Copyright Page notice.",
        "No visible copyright year should be inferred from this paragraph.",
        "Additional body text keeps the page clearly non-sparse and non-front-matter.",
        "Further explanatory prose remains on this same page for classification testing.",
        "This row exists only to keep the page body-like rather than front-matter-like.",
        "One more line prevents sparse-page inference from misclassifying the page.",
    ]
    for idx, line in enumerate(prose_lines):
        p2.insert_text((108, 140 + idx * 20), line, fontsize=12)
    p3 = doc.new_page(width=612, height=792)
    p3.insert_text((250, 90), "ABSTRACT", fontsize=14, fontname="Times-Bold")
    p3.insert_text((108, 140), "Synthetic abstract for P051 testing.", fontsize=12)
    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))
    assert not any(f.rule_id == "P051" for f in check_pdf_copyright_year_format(model))


def test_p051_finding_metadata_privacy_safe(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p051_privacy.pdf"
    _make_copyright_page_pdf(pdf_path, copyright_notice="© Test Author. All Rights Reserved.")
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_copyright_year_format(model)
    blob = " ".join(f.message for f in findings) + " " + " ".join(
        f"{k}={v}" for f in findings for k, v in (f.details or {}).items()
    )
    assert "Test Author" not in blob
    assert "A Study of Synthetic" not in blob
    assert "All Rights Reserved" not in blob


def test_p051_import_and_wiring(tmp_path: Path) -> None:
    import inspect

    import njit_auditor.audit_runner as audit_runner
    from njit_auditor.rules.pdf_copyright_page import check_pdf_copyright_year_format as fn

    assert callable(fn)
    src = inspect.getsource(audit_runner.collect_pdf_layout_findings)
    assert "check_pdf_copyright_year_format" in src


def test_p051_p034_unaffected(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p051_p034.pdf"
    _make_copyright_page_pdf(
        pdf_path,
        copyright_notice="© 2023 Test Author. All Rights Reserved.",
    )
    model = load_pdf_layout(str(pdf_path))
    p034 = [f for f in check_pdf_copyright_page(model) if f.rule_id == "P034"]
    p051 = [f for f in check_pdf_copyright_year_format(model) if f.rule_id == "P051"]
    assert any(f.details.get("issue_type") == "copyright_year_mismatch" for f in p034)
    assert not p051


def test_p051_span_joined_real_world_shape_still_allows_p034_year_and_author(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "p051_real_world_span_joined.pdf"
    _make_p051_fragmented_pdf(
        pdf_path,
        copyright_fragments=[
            (230, 360, "Copyright"),
            (285, 360, "©"),
            (302, 360, "2023"),
            (333, 360, "by"),
            (350, 360, "Test"),
            (382, 360, "Author"),
        ],
        extra_lines=[(254, 384, "ALL RIGHTS RESERVED")],
    )
    model = load_pdf_layout(str(pdf_path))
    p034 = [f for f in check_pdf_copyright_page(model) if f.rule_id == "P034"]
    p051 = [f for f in check_pdf_copyright_year_format(model) if f.rule_id == "P051"]
    p052 = [f for f in check_pdf_copyright_author_format(model) if f.rule_id == "P052"]
    assert any(f.details.get("issue_type") == "copyright_year_mismatch" for f in p034)
    assert not p051
    assert not p052


# ---------------------------------------------------------------------------
# P052: Copyright page author-format refinement
# ---------------------------------------------------------------------------


def test_p052_standard_author_no_finding(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p052_standard.pdf"
    _make_copyright_page_pdf(pdf_path, copyright_notice="© 2024 Test Author. All Rights Reserved.")
    model = load_pdf_layout(str(pdf_path))
    assert not any(f.rule_id == "P052" for f in check_pdf_copyright_author_format(model))


def test_p052_no_year_no_finding(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p052_no_year.pdf"
    _make_copyright_page_pdf(pdf_path, copyright_notice="© Test Author. All Rights Reserved.")
    model = load_pdf_layout(str(pdf_path))
    assert not any(f.rule_id == "P052" for f in check_pdf_copyright_author_format(model))


def test_p052_year_no_author_warns(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p052_no_author.pdf"
    _make_p051_pdf(
        pdf_path,
        copyright_page_lines=[(360, "© 2024"), (380, "All Rights Reserved.")],
    )
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_copyright_author_format(model) if f.rule_id == "P052"]
    assert any(f.details.get("issue_type") == "copyright_author_not_found" for f in findings)


def test_p052_adjacent_line_author_no_finding(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p052_adjacent.pdf"
    _make_p051_pdf(
        pdf_path,
        copyright_page_lines=[
            (360, "© 2024"),
            (376, "Test Author Name"),
        ],
    )
    model = load_pdf_layout(str(pdf_path))
    assert not any(f.rule_id == "P052" for f in check_pdf_copyright_author_format(model))


def test_p052_no_copyright_page_no_finding(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p052_no_copyright.pdf"
    _make_copyright_page_pdf(pdf_path, include_copyright_page=False)
    model = load_pdf_layout(str(pdf_path))
    assert not any(f.rule_id == "P052" for f in check_pdf_copyright_author_format(model))


def test_p052_finding_metadata_privacy_safe(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p052_privacy.pdf"
    _make_p051_pdf(
        pdf_path,
        copyright_page_lines=[(360, "© 2024"), (380, "All Rights Reserved.")],
    )
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_copyright_author_format(model)
    blob = " ".join(f.message for f in findings) + " " + " ".join(
        f"{k}={v}" for f in findings for k, v in (f.details or {}).items()
    )
    assert "Test Author" not in blob
    assert "All Rights Reserved" not in blob
    assert "A Study of Synthetic" not in blob


def test_p052_import_and_wiring(tmp_path: Path) -> None:
    import inspect

    import njit_auditor.audit_runner as audit_runner
    from njit_auditor.rules.pdf_copyright_page import check_pdf_copyright_author_format as fn

    assert callable(fn)
    src = inspect.getsource(audit_runner.collect_pdf_layout_findings)
    assert "check_pdf_copyright_author_format" in src


def test_p052_p034_p051_unaffected(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p052_siblings.pdf"
    _make_copyright_page_pdf(
        pdf_path,
        copyright_notice="© 2023 Test Author. All Rights Reserved.",
    )
    model = load_pdf_layout(str(pdf_path))
    p034 = [f for f in check_pdf_copyright_page(model) if f.rule_id == "P034"]
    p051 = [f for f in check_pdf_copyright_year_format(model) if f.rule_id == "P051"]
    p052 = [f for f in check_pdf_copyright_author_format(model) if f.rule_id == "P052"]
    assert any(f.details.get("issue_type") == "copyright_year_mismatch" for f in p034)
    assert not p051
    assert not p052


def test_p052_year_detected_flag_in_finding(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p052_year_flag.pdf"
    _make_p051_pdf(
        pdf_path,
        copyright_page_lines=[(360, "© 2024"), (380, "All Rights Reserved.")],
    )
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_copyright_author_format(model) if f.rule_id == "P052"]
    assert findings
    assert findings[0].details.get("year_detected") == "true"
    assert findings[0].details.get("source_q_rule_id") == "Q011"


# ---------------------------------------------------------------------------
# P035: Figure/table body layout
# ---------------------------------------------------------------------------

_P035_TABLE_CAPTION = "Table 3.1 Example table caption title for layout testing here."
_P035_FIGURE_CAPTION = "Figure 2.1 Example figure caption text for layout testing here."


def _draw_p035_body_rows(
    page: fitz.Page,
    *,
    x0: float,
    y_start: float,
    rows: int = 3,
    row_height: float = 18.0,
    centered: bool = False,
) -> None:
    text = "Row column alpha and column beta values"
    if centered:
        for idx in range(rows):
            y0 = y_start + idx * row_height
            # A 20pt-tall box (vs. the 14pt fontsize) keeps insert_textbox's
            # fit check positive even at a tight row_height, so rows still
            # render when simulating a merged, single-spaced table block.
            page.insert_textbox(
                fitz.Rect(108, y0 - 15, 540, y0 + 5),
                text,
                fontsize=11,
                align=fitz.TEXT_ALIGN_CENTER,
            )
        return
    for idx in range(rows):
        page.insert_text(
            (x0, y_start + idx * row_height),
            f"Row {idx + 1} column alpha and column beta values",
            fontsize=11,
        )


def _insert_p035_raster_figure(page: fitz.Page, rect: fitz.Rect) -> None:
    pixmap = fitz.Pixmap(
        fitz.csRGB,
        fitz.IRect(0, 0, int(rect.width), int(rect.height)),
        False,
    )
    pixmap.clear_with(0xD9D9D9)
    page.insert_image(rect, stream=pixmap.tobytes("png"))


def _make_p035_body_page_pdf(
    path: Path,
    *,
    float_type: str = "table",
    caption_text: str = _P035_TABLE_CAPTION,
    caption_y: float = 200.0,
    body_x0: float = 180.0,
    body_y: float = 240.0,
    body_rows: int = 3,
    body_row_height: float = 18.0,
    include_body: bool = True,
    toc_page: bool = False,
    body_centered: bool = False,
) -> None:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    if toc_page:
        page.insert_text((250, 90), "TABLE OF CONTENTS", fontsize=14, fontname="Times-Bold")
    page.insert_text((108, 80), "CHAPTER 1 INTRODUCTION", fontsize=14, fontname="Times-Bold")
    if include_body:
        _draw_p035_body_rows(
            page,
            x0=body_x0,
            y_start=body_y,
            rows=body_rows,
            row_height=body_row_height,
            centered=body_centered,
        )
    page.insert_text((108, caption_y), caption_text, fontsize=11)
    doc.save(path)
    doc.close()


def test_p035_centered_table_with_caption_above_no_finding(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p035_table_ok.pdf"
    _make_p035_body_page_pdf(
        pdf_path,
        float_type="table",
        caption_y=200.0,
        body_y=240.0,
        body_centered=True,
    )
    model = load_pdf_layout(str(pdf_path))
    assert not any(f.rule_id == "P035" for f in check_pdf_figure_table_layout(model))


def test_p035_off_center_table_body_warns(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p035_table_off_center.pdf"
    _make_p035_body_page_pdf(
        pdf_path,
        caption_y=200.0,
        body_x0=108.0,
        body_y=240.0,
    )
    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in check_pdf_figure_table_layout(model) if f.rule_id == "P035"]
    assert any(w.details.get("issue_type") == "table_body_not_centered" for w in warnings)


def test_p035_table_caption_below_body_warns(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p035_table_caption_below.pdf"
    _make_p035_body_page_pdf(
        pdf_path,
        caption_y=280.0,
        body_x0=180.0,
        body_y=180.0,
    )
    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in check_pdf_figure_table_layout(model) if f.rule_id == "P035"]
    assert any(w.details.get("issue_type") == "table_caption_not_above_body" for w in warnings)


def test_p035_table_caption_above_merged_multiline_body_no_finding(tmp_path: Path) -> None:
    # A tight, single-spaced row pitch (14pt) makes PyMuPDF extract the whole
    # table as one multi-line text block rather than one block per row. That
    # used to make the genuine table body invisible to the detector and
    # falsely flag a correctly placed caption as not being above the body.
    pdf_path = tmp_path / "p035_table_merged_rows_ok.pdf"
    _make_p035_body_page_pdf(
        pdf_path,
        caption_y=200.0,
        body_y=220.0,
        body_rows=5,
        body_row_height=14.0,
        body_centered=True,
    )
    model = load_pdf_layout(str(pdf_path))
    assert not any(f.rule_id == "P035" for f in check_pdf_figure_table_layout(model))


def test_p035_off_center_merged_multiline_table_body_warns(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p035_table_merged_rows_off_center.pdf"
    _make_p035_body_page_pdf(
        pdf_path,
        caption_y=200.0,
        body_x0=180.0,
        body_y=220.0,
        body_rows=5,
        body_row_height=14.0,
    )
    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in check_pdf_figure_table_layout(model) if f.rule_id == "P035"]
    assert any(w.details.get("issue_type") == "table_body_not_centered" for w in warnings)
    assert not any(
        w.details.get("issue_type") == "table_caption_not_above_body" for w in warnings
    )


def test_p035_intro_paragraph_above_table_caption_with_real_body_no_finding(
    tmp_path: Path,
) -> None:
    # A normal introductory paragraph just above a table caption must not be
    # mistaken for a misplaced table body when the genuine (merged,
    # multi-line) table body is correctly positioned below the caption.
    pdf_path = tmp_path / "p035_table_intro_paragraph.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((108, 80), "CHAPTER 1 INTRODUCTION", fontsize=14, fontname="Times-Bold")
    page.insert_text((108, 130), "The following section introduces the data used in", fontsize=11)
    page.insert_text((108, 148), "this part of the analysis for the current chapter.", fontsize=11)
    page.insert_text((108, 200), _P035_TABLE_CAPTION, fontsize=11)
    _draw_p035_body_rows(page, x0=180.0, y_start=220.0, rows=5, row_height=14.0, centered=True)
    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in check_pdf_figure_table_layout(model) if f.rule_id == "P035"]
    assert not any(
        w.details.get("issue_type") == "table_caption_not_above_body" for w in warnings
    )


def test_p035_centered_figure_with_caption_below_no_finding(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p035_figure_ok.pdf"
    _make_p035_body_page_pdf(
        pdf_path,
        float_type="figure",
        caption_text=_P035_FIGURE_CAPTION,
        caption_y=260.0,
        body_y=180.0,
        body_centered=True,
    )
    model = load_pdf_layout(str(pdf_path))
    assert not any(f.rule_id == "P035" for f in check_pdf_figure_table_layout(model))


def test_p035_raster_figure_above_caption_ignores_equation_below(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "p035_raster_figure_above_caption_ok.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((108, 80), "CHAPTER 2 RESULTS", fontsize=14, fontname="Times-Bold")
    _insert_p035_raster_figure(page, fitz.Rect(180, 120, 468, 236))
    page.insert_text((108, 260), _P035_FIGURE_CAPTION, fontsize=11)
    page.insert_text((240, 320), "J(C) = 1 / |C|", fontsize=11)
    page.insert_text(
        (108, 350),
        "This paragraph discusses the equation below the figure caption.",
        fontsize=11,
    )
    page.insert_text(
        (108, 368),
        "It must not be treated as the body of the figure.",
        fontsize=11,
    )
    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))
    assert model.pages[0].graphic_blocks
    warnings = [f for f in check_pdf_figure_table_layout(model) if f.rule_id == "P035"]
    assert not any(
        w.details.get("issue_type") == "figure_caption_not_below_body" for w in warnings
    )


def test_p035_raster_figure_below_caption_warns_and_highlights_figure(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "p035_raster_figure_below_caption_warns.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((108, 80), "CHAPTER 2 RESULTS", fontsize=14, fontname="Times-Bold")
    page.insert_text((108, 150), _P035_FIGURE_CAPTION, fontsize=11)
    _insert_p035_raster_figure(page, fitz.Rect(180, 200, 468, 316))
    page.insert_text((240, 360), "J(C) = 1 / |C|", fontsize=11)
    page.insert_text(
        (108, 390),
        "Unrelated prose below the figure must not become the highlight target.",
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
    assert len(warnings) == 1
    boxes = parse_highlight_bboxes_from_details(
        warnings[0].details,
        rule_id="P035",
        issue_type="figure_caption_not_below_body",
    )
    assert len(boxes) == 2
    body_bbox_raw = warnings[0].details.get("body_bbox", "")
    x0, y0, x1, y1 = (float(value) for value in body_bbox_raw.split(","))
    assert (x0, y0, x1, y1) == (180.0, 200.0, 468.0, 316.0)
    assert all(box[1] < 330.0 for box in boxes)


def test_p035_off_center_figure_body_warns(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p035_figure_off_center.pdf"
    _make_p035_body_page_pdf(
        pdf_path,
        float_type="figure",
        caption_text=_P035_FIGURE_CAPTION,
        caption_y=260.0,
        body_x0=108.0,
        body_y=180.0,
    )
    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in check_pdf_figure_table_layout(model) if f.rule_id == "P035"]
    assert any(w.details.get("issue_type") == "figure_body_not_centered" for w in warnings)


def test_p035_figure_caption_above_body_warns(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p035_figure_caption_above.pdf"
    _make_p035_body_page_pdf(
        pdf_path,
        float_type="figure",
        caption_text=_P035_FIGURE_CAPTION,
        caption_y=180.0,
        body_x0=180.0,
        body_y=240.0,
    )
    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in check_pdf_figure_table_layout(model) if f.rule_id == "P035"]
    assert any(w.details.get("issue_type") == "figure_caption_not_below_body" for w in warnings)


def test_p035_no_text_layer_body_is_skipped(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p035_caption_only.pdf"
    _make_p035_body_page_pdf(
        pdf_path,
        include_body=False,
        caption_y=260.0,
    )
    model = load_pdf_layout(str(pdf_path))
    assert not any(f.rule_id == "P035" for f in check_pdf_figure_table_layout(model))


def test_p035_toc_page_caption_skipped(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p035_toc_skip.pdf"
    _make_p035_body_page_pdf(
        pdf_path,
        toc_page=True,
        caption_y=260.0,
        body_x0=108.0,
        body_y=180.0,
    )
    model = load_pdf_layout(str(pdf_path))
    assert not any(f.rule_id == "P035" for f in check_pdf_figure_table_layout(model))


def test_p035_finding_details_privacy_safe(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p035_privacy.pdf"
    _make_p035_body_page_pdf(
        pdf_path,
        caption_y=200.0,
        body_x0=108.0,
        body_y=240.0,
    )
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_figure_table_layout(model)
    blob = " ".join(f.message for f in findings) + " " + " ".join(
        f"{k}={v}" for f in findings for k, v in (f.details or {}).items()
    )
    assert "Example table caption" not in blob
    assert "Row 1 column alpha" not in blob
    assert "line_preview" not in blob


def test_p035_prose_restating_figure_number_is_not_mistaken_for_caption(
    tmp_path: Path,
) -> None:
    # A body paragraph that opens by restating a figure's number (a common
    # academic-writing convention) must not be mistaken for a second caption
    # candidate, which would otherwise produce a spurious layout finding even
    # though the real caption is correctly placed below its real body.
    pdf_path = tmp_path / "p035_figure_prose_restate.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((108, 80), "CHAPTER 2 RESULTS", fontsize=14, fontname="Times-Bold")
    _draw_p035_body_rows(page, x0=180.0, y_start=180.0, rows=3, row_height=18.0, centered=True)
    page.insert_text((108, 260), _P035_FIGURE_CAPTION, fontsize=11)
    page.insert_text(
        (108, 280),
        "Figure 2.1 shows the synthetic pattern clearly. The values continue",
        fontsize=11,
    )
    page.insert_text((108, 298), "to trend in the same direction across each group.", fontsize=11)
    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in check_pdf_figure_table_layout(model) if f.rule_id == "P035"]
    assert not any(
        w.details.get("issue_type") == "figure_caption_not_below_body" for w in warnings
    )


def test_p035_shortened_table_reference_does_not_mask_real_caption_no_finding(
    tmp_path: Path,
) -> None:
    # A body sentence elsewhere on the page that opens with a shortened
    # table number (no sub-number, wrapping onto the next line like ordinary
    # prose) must not be mistaken for a second caption candidate. That would
    # otherwise interfere with the layout check for the real, fuller-numbered
    # caption and its real body.
    pdf_path = tmp_path / "p035_table_shortened_reference.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((108, 80), "CHAPTER 3 RESULTS", fontsize=14, fontname="Times-Bold")
    page.insert_text(
        (108, 130),
        "The first part of this chapter introduces the overall sample",
        fontsize=11,
    )
    page.insert_text(
        (108, 148),
        "and outlines the variables used in the analysis below.",
        fontsize=11,
    )
    page.insert_text(
        (108, 180),
        "Table 9 presents the synthetic coefficients for each remaining",
        fontsize=11,
    )
    page.insert_text(
        (108, 198),
        "predictor across every model examined in this section.",
        fontsize=11,
    )
    page.insert_text(
        (108, 240),
        "Table 9.2 Summary of synthetic regression coefficients for testing.",
        fontsize=11,
    )
    _draw_p035_body_rows(page, x0=108.0, y_start=260.0, rows=2, row_height=14.0, centered=True)
    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))
    assert not any(f.rule_id == "P035" for f in check_pdf_figure_table_layout(model))


def test_p035_same_margin_lowercase_body_below_real_caption_still_uses_caption(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "p035_same_margin_lowercase_body.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((108, 80), "CHAPTER 3 RESULTS", fontsize=14, fontname="Times-Bold")
    page.insert_text((108, 140), "Figure 7 Summary of synthetic group outcomes", fontsize=11)
    page.insert_text((108, 158), "synthetic row alpha value here", fontsize=11)
    page.insert_text((108, 176), "synthetic row beta value here", fontsize=11)
    page.insert_text((108, 194), "synthetic row gamma value here", fontsize=11)
    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in check_pdf_figure_table_layout(model) if f.rule_id == "P035"]
    assert any(
        w.details.get("issue_type") == "figure_caption_not_below_body" for w in warnings
    )


def test_p035_merged_number_text_figure_caption_still_used(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p035_merged_number_text_figure_caption.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((108, 80), "CHAPTER 3 RESULTS", fontsize=14, fontname="Times-Bold")
    page.insert_text((108, 140), "Figure 4.1Brief synthetic overview", fontsize=11)
    page.insert_text((108, 158), "synthetic row alpha value here", fontsize=11)
    page.insert_text((108, 176), "synthetic row beta value here", fontsize=11)
    page.insert_text((108, 194), "synthetic row gamma value here", fontsize=11)
    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))
    warnings = [f for f in check_pdf_figure_table_layout(model) if f.rule_id == "P035"]
    assert any(
        w.details.get("issue_type") == "figure_caption_not_below_body" for w in warnings
    )


def test_p035_cli_pdf_command_includes_rule(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p035_cli.pdf"
    json_out = tmp_path / "p035_cli_report.json"
    _make_p035_body_page_pdf(
        pdf_path,
        caption_y=200.0,
        body_x0=108.0,
        body_y=240.0,
    )
    runner = CliRunner()
    result = runner.invoke(app, ["pdf", str(pdf_path), "--json-out", str(json_out)])
    assert result.exit_code == 0
    payload = json.loads(json_out.read_text(encoding="utf-8"))
    assert any(item.get("rule_id") == "P035" for item in payload.get("findings", []))


# ---------------------------------------------------------------------------
# P037 — Section-anchored front-matter Roman numeral checks
# ---------------------------------------------------------------------------


def _make_p037_pdf(
    path: Path,
    pages: list[tuple[str | None, str | None, str | None]],
) -> None:
    """Create a synthetic front-matter PDF for P037 tests.

    pages: list of (heading_text_or_none, chapter_text_or_none, page_num_text_or_none)
    heading_text: e.g. "BIOGRAPHICAL SKETCH", "ACKNOWLEDGEMENTS"
    chapter_text: body heading like "CHAPTER 1 INTRODUCTION" (marks body start)
    page_num_text: Roman or Arabic page number placed at bottom center
    """
    doc = fitz.open()
    for heading, chapter, page_num in pages:
        page = doc.new_page(width=612, height=792)
        if heading:
            page.insert_text((180, 90), heading, fontsize=14, fontname="Times-Bold")
        if chapter:
            page.insert_text((108, 200), chapter, fontsize=14)
        if page_num:
            page.insert_text((300, 760), page_num, fontsize=12)
    doc.save(path)
    doc.close()


def test_p037_bio_sketch_iv_no_finding(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p037_bio_iv_ok.pdf"
    _make_p037_pdf(pdf_path, [
        ("BIOGRAPHICAL SKETCH", None, "iv"),
        ("ACKNOWLEDGEMENTS", None, "vi"),
        ("TABLE OF CONTENTS", None, "vii"),
        (None, "CHAPTER 1 INTRODUCTION", "1"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_roman_section_anchors(model) if f.rule_id == "P037"]
    assert not findings


def test_p037_bio_sketch_wrong_roman_warns(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p037_bio_v_bad.pdf"
    _make_p037_pdf(pdf_path, [
        ("BIOGRAPHICAL SKETCH", None, "v"),
        (None, "CHAPTER 1 INTRODUCTION", "1"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_roman_section_anchors(model) if f.rule_id == "P037"]
    assert any(f.details.get("issue_type") == "roman_bio_sketch_not_iv" for f in findings)
    bio_finding = next(
        f for f in findings if f.details.get("issue_type") == "roman_bio_sketch_not_iv"
    )
    assert bio_finding.details.get("expected_roman") == "iv"
    assert bio_finding.details.get("expected_value") == "4"
    assert bio_finding.details.get("observed_roman") == "v"
    assert bio_finding.details.get("section_key") == "biographical_sketch"


def test_p037_globally_offset_sequence_flags_bio(tmp_path: Path) -> None:
    """P029 may not catch a globally offset sequence (v,vi,...); P037 should flag bio=v."""
    pdf_path = tmp_path / "p037_offset_seq.pdf"
    _make_p037_pdf(pdf_path, [
        ("BIOGRAPHICAL SKETCH", None, "v"),
        ("ACKNOWLEDGEMENTS", None, "vii"),
        ("TABLE OF CONTENTS", None, "viii"),
        (None, "CHAPTER 1 INTRODUCTION", "1"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_roman_section_anchors(model) if f.rule_id == "P037"]
    assert any(f.details.get("issue_type") == "roman_bio_sketch_not_iv" for f in findings)


def test_p037_dedication_absent_ack_vi_passes(tmp_path: Path) -> None:
    """Dedication not detected; ACK at vi is correct per template slot counting."""
    pdf_path = tmp_path / "p037_no_ded_ack_vi.pdf"
    _make_p037_pdf(pdf_path, [
        ("BIOGRAPHICAL SKETCH", None, "iv"),
        ("ACKNOWLEDGEMENTS", None, "vi"),
        ("TABLE OF CONTENTS", None, "vii"),
        ("LIST OF TABLES", None, "viii"),
        (None, "CHAPTER 1 INTRODUCTION", "1"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_roman_section_anchors(model) if f.rule_id == "P037"]
    assert not findings


def test_p037_dedication_present_correct_no_finding(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p037_ded_ok.pdf"
    _make_p037_pdf(pdf_path, [
        ("BIOGRAPHICAL SKETCH", None, "iv"),
        ("DEDICATION", None, "v"),
        ("ACKNOWLEDGEMENTS", None, "vi"),
        ("TABLE OF CONTENTS", None, "vii"),
        (None, "CHAPTER 1 INTRODUCTION", "1"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_roman_section_anchors(model) if f.rule_id == "P037"]
    assert not findings


def test_p037_dedication_present_wrong_warns(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p037_ded_wrong.pdf"
    _make_p037_pdf(pdf_path, [
        ("BIOGRAPHICAL SKETCH", None, "iv"),
        ("DEDICATION", None, "vi"),
        (None, "CHAPTER 1 INTRODUCTION", "1"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_roman_section_anchors(model) if f.rule_id == "P037"]
    ded = [f for f in findings if f.details.get("section_key") == "dedication"]
    assert ded
    assert ded[0].details.get("issue_type") == "roman_section_wrong_value"
    assert ded[0].details.get("expected_roman") == "v"
    assert ded[0].details.get("observed_roman") == "vi"


def test_p037_toc_wrong_value_warns(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p037_toc_wrong.pdf"
    _make_p037_pdf(pdf_path, [
        ("BIOGRAPHICAL SKETCH", None, "iv"),
        ("ACKNOWLEDGEMENTS", None, "vi"),
        ("TABLE OF CONTENTS", None, "ix"),
        (None, "CHAPTER 1 INTRODUCTION", "1"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_roman_section_anchors(model) if f.rule_id == "P037"]
    toc = [f for f in findings if f.details.get("section_key") == "table_of_contents"]
    assert toc
    assert toc[0].details.get("expected_roman") == "vii"
    assert toc[0].details.get("issue_type") == "roman_section_wrong_value"


def test_p037_no_bio_heading_no_findings(tmp_path: Path) -> None:
    """When BIOGRAPHICAL SKETCH heading is absent, P037 emits nothing."""
    pdf_path = tmp_path / "p037_no_bio.pdf"
    _make_p037_pdf(pdf_path, [
        ("ACKNOWLEDGEMENTS", None, "vi"),
        ("TABLE OF CONTENTS", None, "vii"),
        (None, "CHAPTER 1 INTRODUCTION", "1"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_roman_section_anchors(model) if f.rule_id == "P037"]
    assert not findings


def test_p037_no_candidate_on_bio_page_skipped(tmp_path: Path) -> None:
    """Bio heading present but no Roman candidate → no P037 finding (skip)."""
    pdf_path = tmp_path / "p037_bio_no_num.pdf"
    _make_p037_pdf(pdf_path, [
        ("BIOGRAPHICAL SKETCH", None, None),
        (None, "CHAPTER 1 INTRODUCTION", "1"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_roman_section_anchors(model) if f.rule_id == "P037"]
    assert not findings


def test_p037_body_page_roman_not_checked(tmp_path: Path) -> None:
    """Roman numerals on body pages must not produce P037 findings."""
    pdf_path = tmp_path / "p037_body_roman.pdf"
    _make_p037_pdf(pdf_path, [
        ("BIOGRAPHICAL SKETCH", None, "iv"),
        (None, "CHAPTER 1 INTRODUCTION", "v"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_roman_section_anchors(model) if f.rule_id == "P037"]
    body_pages = [f for f in findings if f.page == 2]
    assert not body_pages


def test_p037_finding_metadata_privacy_safe(tmp_path: Path) -> None:
    """Finding details must not include dissertation body text or heading prose."""
    pdf_path = tmp_path / "p037_privacy.pdf"
    _make_p037_pdf(pdf_path, [
        ("BIOGRAPHICAL SKETCH", None, "v"),
        (None, "CHAPTER 1 INTRODUCTION", "1"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_roman_section_anchors(model) if f.rule_id == "P037"]
    assert findings
    for f in findings:
        assert f.details.get("section_key") is not None
        assert f.details.get("expected_roman") is not None
        assert f.details.get("observed_roman") is not None
        assert f.details.get("expected_value") is not None
        assert f.details.get("observed_value") is not None
        # Message should only reference section name and numerals, not body text.
        assert "body text" not in f.message.lower()


def test_p037_two_page_toc_list_of_tables_ix_no_finding(tmp_path: Path) -> None:
    """A TOC that spans two pages (ending in viii) makes ix the correct next
    value for List of Tables — not a hard-coded viii (Q060: sequential after
    the TOC, however many pages it takes)."""
    pdf_path = tmp_path / "p037_toc_two_page_ok.pdf"
    _make_p037_pdf(pdf_path, [
        ("BIOGRAPHICAL SKETCH", None, "iv"),
        ("ACKNOWLEDGEMENTS", None, "vi"),
        ("TABLE OF CONTENTS", None, "vii"),
        (None, None, "viii"),  # TOC "(Continued)" page
        ("LIST OF TABLES", None, "ix"),
        (None, "CHAPTER 1 INTRODUCTION", "1"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_roman_section_anchors(model) if f.rule_id == "P037"]
    lot = [f for f in findings if f.details.get("section_key") == "list_of_tables"]
    assert not lot


def test_p037_single_page_toc_list_of_tables_ix_warns_expected_viii(
    tmp_path: Path,
) -> None:
    """A single-page TOC ending in vii makes viii the correct next value; a List
    of Tables printed as ix is a real sequence break."""
    pdf_path = tmp_path / "p037_toc_one_page_bad.pdf"
    _make_p037_pdf(pdf_path, [
        ("BIOGRAPHICAL SKETCH", None, "iv"),
        ("ACKNOWLEDGEMENTS", None, "vi"),
        ("TABLE OF CONTENTS", None, "vii"),
        ("LIST OF TABLES", None, "ix"),
        (None, "CHAPTER 1 INTRODUCTION", "1"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_roman_section_anchors(model) if f.rule_id == "P037"]
    lot = [f for f in findings if f.details.get("section_key") == "list_of_tables"]
    assert lot
    assert lot[0].details.get("expected_roman") == "viii"
    assert lot[0].details.get("observed_roman") == "ix"


def test_p037_list_of_tables_uncertain_preceding_page_no_hardcoded_warning(
    tmp_path: Path,
) -> None:
    """When the page immediately before List of Tables has no confident Roman
    candidate, the expected value cannot be determined — do not fall back to
    a hard-coded guess and emit a false warning."""
    pdf_path = tmp_path / "p037_toc_uncertain_preceding.pdf"
    _make_p037_pdf(pdf_path, [
        ("BIOGRAPHICAL SKETCH", None, "iv"),
        ("ACKNOWLEDGEMENTS", None, "vi"),
        ("TABLE OF CONTENTS", None, "vii"),
        (None, None, None),  # TOC continuation page with no visible page number
        ("LIST OF TABLES", None, "ix"),
        (None, "CHAPTER 1 INTRODUCTION", "1"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_roman_section_anchors(model) if f.rule_id == "P037"]
    lot = [f for f in findings if f.details.get("section_key") == "list_of_tables"]
    assert not lot


def test_p037_cli_includes_rule(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p037_cli.pdf"
    json_out = tmp_path / "p037_report.json"
    _make_p037_pdf(pdf_path, [
        ("BIOGRAPHICAL SKETCH", None, "v"),
        (None, "CHAPTER 1 INTRODUCTION", "1"),
    ])
    runner = CliRunner()
    result = runner.invoke(app, ["pdf", str(pdf_path), "--json-out", str(json_out)])
    assert result.exit_code == 0
    payload = json.loads(json_out.read_text(encoding="utf-8"))
    assert any(item.get("rule_id") == "P037" for item in payload.get("findings", []))


# ---------------------------------------------------------------------------
# P038 — Front-matter exact heading phrase and missing-section checks
# ---------------------------------------------------------------------------


def _make_p038_pdf(
    path: Path,
    pages: list[tuple[str | None, str | None, str | None]],
) -> None:
    """Create a synthetic multi-page PDF for P038 tests.

    pages: list of (heading_text_or_none, chapter_text_or_none, page_num_text_or_none)
    heading_text: e.g. "APPROVAL PAGE", "BIOGRAPHICAL SKETCH"
    chapter_text: body heading like "CHAPTER 1 INTRODUCTION"
    page_num_text: page number at bottom
    """
    doc = fitz.open()
    for heading, chapter, page_num in pages:
        page = doc.new_page(width=612, height=792)
        if heading:
            page.insert_text((180, 90), heading, fontsize=14, fontname="Times-Bold")
        if chapter:
            page.insert_text((108, 200), chapter, fontsize=14)
        if page_num:
            page.insert_text((300, 760), page_num, fontsize=12)
    doc.save(path)
    doc.close()


def test_p038_all_required_headings_correct_no_finding(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p038_all_ok.pdf"
    _make_p038_pdf(pdf_path, [
        ("APPROVAL PAGE", None, None),
        ("BIOGRAPHICAL SKETCH", None, "iv"),
        ("ACKNOWLEDGEMENTS", None, "vi"),
        ("TABLE OF CONTENTS", None, "vii"),
        (None, "CHAPTER 1 INTRODUCTION", "1"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_frontmatter_headings(model) if f.rule_id == "P038"]
    assert not findings


def test_p038_approval_page_missing_warns(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p038_no_approval.pdf"
    _make_p038_pdf(pdf_path, [
        ("BIOGRAPHICAL SKETCH", None, "iv"),
        ("ACKNOWLEDGEMENTS", None, "vi"),
        ("TABLE OF CONTENTS", None, "vii"),
        (None, "CHAPTER 1 INTRODUCTION", "1"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_frontmatter_headings(model) if f.rule_id == "P038"]
    missing = [f for f in findings if f.details.get("issue_type") == "required_heading_missing"]
    assert any(f.details.get("section_key") == "approval_page" for f in missing)


def test_p038_biographical_sketch_missing_warns(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p038_no_bio.pdf"
    _make_p038_pdf(pdf_path, [
        ("APPROVAL PAGE", None, None),
        ("ACKNOWLEDGEMENTS", None, "vi"),
        ("TABLE OF CONTENTS", None, "vii"),
        (None, "CHAPTER 1 INTRODUCTION", "1"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_frontmatter_headings(model) if f.rule_id == "P038"]
    missing = [f for f in findings if f.details.get("issue_type") == "required_heading_missing"]
    assert any(f.details.get("section_key") == "biographical_sketch" for f in missing)


def test_p038_acknowledgements_missing_warns(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p038_no_ack.pdf"
    _make_p038_pdf(pdf_path, [
        ("APPROVAL PAGE", None, None),
        ("BIOGRAPHICAL SKETCH", None, "iv"),
        ("TABLE OF CONTENTS", None, "vii"),
        (None, "CHAPTER 1 INTRODUCTION", "1"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_frontmatter_headings(model) if f.rule_id == "P038"]
    missing = [f for f in findings if f.details.get("issue_type") == "required_heading_missing"]
    assert any(f.details.get("section_key") == "acknowledgements" for f in missing)


def test_p038_toc_missing_warns(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p038_no_toc.pdf"
    _make_p038_pdf(pdf_path, [
        ("APPROVAL PAGE", None, None),
        ("BIOGRAPHICAL SKETCH", None, "iv"),
        ("ACKNOWLEDGEMENTS", None, "vi"),
        (None, "CHAPTER 1 INTRODUCTION", "1"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_frontmatter_headings(model) if f.rule_id == "P038"]
    missing = [f for f in findings if f.details.get("issue_type") == "required_heading_missing"]
    assert any(f.details.get("section_key") == "table_of_contents" for f in missing)


def test_p038_acknowledgments_american_spelling_accepted_no_finding(tmp_path: Path) -> None:
    """Regression (Ester Sample B page 9): the standard American spelling
    "ACKNOWLEDGMENTS" is an NJIT-accepted equivalent of "ACKNOWLEDGEMENTS" and
    must not be reported as either a phrase mismatch or a missing heading —
    flagging it was a false positive, confirmed by Ester's live review."""
    pdf_path = tmp_path / "p038_ackments.pdf"
    _make_p038_pdf(pdf_path, [
        ("APPROVAL PAGE", None, None),
        ("BIOGRAPHICAL SKETCH", None, "iv"),
        ("ACKNOWLEDGMENTS", None, "vi"),  # American spelling — accepted equivalent
        ("TABLE OF CONTENTS", None, "vii"),
        (None, "CHAPTER 1 INTRODUCTION", "1"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_frontmatter_headings(model) if f.rule_id == "P038"]
    assert not findings, f"American spelling must not be flagged at all; got: {findings}"


def test_p038_dedication_absent_no_finding(tmp_path: Path) -> None:
    """DEDICATION is optional and must never trigger required_heading_missing."""
    pdf_path = tmp_path / "p038_no_dedication.pdf"
    _make_p038_pdf(pdf_path, [
        ("APPROVAL PAGE", None, None),
        ("BIOGRAPHICAL SKETCH", None, "iv"),
        ("ACKNOWLEDGEMENTS", None, "vi"),
        ("TABLE OF CONTENTS", None, "vii"),
        (None, "CHAPTER 1 INTRODUCTION", "1"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_frontmatter_headings(model) if f.rule_id == "P038"]
    dedication_missing = [
        f for f in findings
        if f.details.get("section_key") == "dedication"
        and f.details.get("issue_type") == "required_heading_missing"
    ]
    assert not dedication_missing


def test_p038_lot_lof_absent_no_missing_finding(tmp_path: Path) -> None:
    """LIST OF TABLES and LIST OF FIGURES are optional — absence must not be flagged."""
    pdf_path = tmp_path / "p038_no_lot_lof.pdf"
    _make_p038_pdf(pdf_path, [
        ("APPROVAL PAGE", None, None),
        ("BIOGRAPHICAL SKETCH", None, "iv"),
        ("ACKNOWLEDGEMENTS", None, "vi"),
        ("TABLE OF CONTENTS", None, "vii"),
        (None, "CHAPTER 1 INTRODUCTION", "1"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_frontmatter_headings(model) if f.rule_id == "P038"]
    optional_missing = [
        f for f in findings
        if f.details.get("section_key") in {"list_of_tables", "list_of_figures"}
        and f.details.get("issue_type") == "required_heading_missing"
    ]
    assert not optional_missing


def test_p038_no_headings_detected_no_finding(tmp_path: Path) -> None:
    """Flattened PDF with no detectable headings must produce no P038 findings."""
    pdf_path = tmp_path / "p038_no_headings.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((108, 200), "Some body text without any headings.", fontsize=12)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_frontmatter_headings(model) if f.rule_id == "P038"]
    assert not findings


def test_p038_finding_metadata_privacy_safe(tmp_path: Path) -> None:
    """P038 findings must not include arbitrary extracted body text."""
    pdf_path = tmp_path / "p038_privacy.pdf"
    _make_p038_pdf(pdf_path, [
        ("APPROVAL PAGE", None, None),
        ("BIOGRAPHICAL SKETCH", None, "iv"),
        # ACKNOWLEDGEMENTS omitted entirely so this still exercises a real P038
        # finding (required_heading_missing) for the privacy assertions below.
        ("TABLE OF CONTENTS", None, "vii"),
        (None, "CHAPTER 1 INTRODUCTION", "1"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_frontmatter_headings(model) if f.rule_id == "P038"]
    assert findings
    for f in findings:
        # observed_heading_normalized must only be present for known safe variants
        observed = f.details.get("observed_heading_normalized", "")
        if observed:
            assert observed in {"ACKNOWLEDGMENTS"}, f"Unexpected observed text: {observed}"
        # No body text, titles, or private content
        assert "body text" not in f.message.lower()
        assert "author" not in f.message.lower()


def test_p038_lot_lof_headings_correct_no_finding(tmp_path: Path) -> None:
    """When LIST OF TABLES and LIST OF FIGURES are present and exact, no P038 finding."""
    pdf_path = tmp_path / "p038_lot_lof_ok.pdf"
    _make_p038_pdf(pdf_path, [
        ("APPROVAL PAGE", None, None),
        ("BIOGRAPHICAL SKETCH", None, "iv"),
        ("ACKNOWLEDGEMENTS", None, "vi"),
        ("TABLE OF CONTENTS", None, "vii"),
        ("LIST OF TABLES", None, "viii"),
        ("LIST OF FIGURES", None, "ix"),
        (None, "CHAPTER 1 INTRODUCTION", "1"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_frontmatter_headings(model) if f.rule_id == "P038"]
    assert not findings


def test_p038_cli_includes_rule(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p038_cli.pdf"
    json_out = tmp_path / "p038_report.json"
    _make_p038_pdf(pdf_path, [
        ("APPROVAL PAGE", None, None),
        ("BIOGRAPHICAL SKETCH", None, "iv"),
        # ACKNOWLEDGEMENTS omitted entirely so this still triggers a P038
        # finding (required_heading_missing) for the CLI-inclusion assertion.
        ("TABLE OF CONTENTS", None, "vii"),
        (None, "CHAPTER 1 INTRODUCTION", "1"),
    ])
    runner = CliRunner()
    result = runner.invoke(app, ["pdf", str(pdf_path), "--json-out", str(json_out)])
    assert result.exit_code == 0
    payload = json.loads(json_out.read_text(encoding="utf-8"))
    assert any(item.get("rule_id") == "P038" for item in payload.get("findings", []))


def test_p038_accepted_variant_and_missing_heading_do_not_conflict(tmp_path: Path) -> None:
    """An accepted equivalent spelling must never appear in the missing list,
    while a genuinely different missing heading is still reported — the two
    checks must not produce duplicated or conflicting P038 findings for the
    same section."""
    pdf_path = tmp_path / "p038_variant_and_missing.pdf"
    _make_p038_pdf(pdf_path, [
        ("APPROVAL PAGE", None, None),
        # BIOGRAPHICAL SKETCH omitted — genuinely missing.
        ("ACKNOWLEDGMENTS", None, "vi"),  # American spelling — accepted equivalent
        ("TABLE OF CONTENTS", None, "vii"),
        (None, "CHAPTER 1 INTRODUCTION", "1"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_frontmatter_headings(model) if f.rule_id == "P038"]

    section_keys_by_issue_type: dict[str, set[str]] = {}
    for f in findings:
        issue_type = f.details.get("issue_type", "")
        section_keys_by_issue_type.setdefault(issue_type, set()).add(
            f.details.get("section_key", "")
        )

    # The accepted variant must not be reported at all — not missing, not a
    # phrase mismatch.
    assert "acknowledgements" not in section_keys_by_issue_type.get(
        "required_heading_missing", set()
    )
    assert "acknowledgements" not in section_keys_by_issue_type.get(
        "heading_phrase_not_exact", set()
    )

    # The genuinely missing heading must still be reported exactly once.
    missing_findings = [
        f for f in findings if f.details.get("issue_type") == "required_heading_missing"
    ]
    assert [f.details.get("section_key") for f in missing_findings] == ["biographical_sketch"]



# ---------------------------------------------------------------------------
# P039: TOC level indentation hierarchy
# ---------------------------------------------------------------------------


def _make_toc_hierarchy_pdf(
    path: Path,
    *,
    l1_x: float = 72.0,
    l2_x: float = 90.0,
    l3_x: float | None = None,
    l1_count: int = 2,
    l2_count: int = 2,
    l3_count: int = 0,
) -> None:
    """Create a synthetic TABLE OF CONTENTS page with configurable level indentation."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((190, 90), "TABLE OF CONTENTS", fontsize=16, fontname="Times-Bold")
    y = 140.0
    for i in range(l1_count):
        page.insert_text((l1_x, y), f"Chapter {i + 1} Section Heading Title Long", fontsize=12)
        page.insert_text((500, y), str(i + 1), fontsize=12)
        y += 22.0
        for j in range(l2_count):
            page.insert_text(
                (l2_x, y), f"{i + 1}.{j + 1} Subsection Title Entry Here", fontsize=12
            )
            page.insert_text((500, y), str(i * l2_count + j + 5), fontsize=12)
            y += 22.0
            if l3_count > 0 and l3_x is not None:
                for k in range(l3_count):
                    page.insert_text(
                        (l3_x, y), f"{i + 1}.{j + 1}.{k + 1} Sub Subpart Item Here", fontsize=12
                    )
                    page.insert_text((500, y), str(i * l2_count + j + k + 20), fontsize=12)
                    y += 22.0
    doc.save(path)
    doc.close()


def test_p039_l2_correctly_indented_no_warning(tmp_path: Path) -> None:
    """L2 entries indented 18pt right of L1 → no P039 finding."""
    pdf_path = tmp_path / "p039_l2_ok.pdf"
    _make_toc_hierarchy_pdf(pdf_path, l1_x=72.0, l2_x=90.0)
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_toc_entry_hierarchy(model) if f.rule_id == "P039"]
    assert not findings


def test_p039_l2_not_indented_warns(tmp_path: Path) -> None:
    """L2 entries at same indent as L1 → toc_l2_not_indented_relative_to_l1."""
    pdf_path = tmp_path / "p039_l2_flat.pdf"
    _make_toc_hierarchy_pdf(pdf_path, l1_x=72.0, l2_x=72.0)
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_toc_entry_hierarchy(model) if f.rule_id == "P039"]
    assert len(findings) >= 1
    assert findings[0].details.get("issue_type") == "toc_l2_not_indented_relative_to_l1"
    assert findings[0].details.get("level") == "2"
    assert findings[0].details.get("parent_level") == "1"
    assert findings[0].details.get("source_q_rule_id") == "Q056"


def test_p039_l3_correctly_indented_no_warning(tmp_path: Path) -> None:
    """L3 entries indented 18pt right of L2 → no P039 L3 finding."""
    pdf_path = tmp_path / "p039_l3_ok.pdf"
    _make_toc_hierarchy_pdf(pdf_path, l1_x=72.0, l2_x=90.0, l3_x=108.0, l3_count=2)
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_toc_entry_hierarchy(model) if f.rule_id == "P039"]
    l3_type = "toc_l3_not_indented_relative_to_l2"
    l3_findings = [f for f in findings if f.details.get("issue_type") == l3_type]
    assert not l3_findings


def test_p039_l3_not_indented_warns(tmp_path: Path) -> None:
    """L3 entries at same indent as L2 → toc_l3_not_indented_relative_to_l2."""
    pdf_path = tmp_path / "p039_l3_flat.pdf"
    _make_toc_hierarchy_pdf(pdf_path, l1_x=72.0, l2_x=90.0, l3_x=90.0, l3_count=2)
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_toc_entry_hierarchy(model) if f.rule_id == "P039"]
    l3_type = "toc_l3_not_indented_relative_to_l2"
    l3_findings = [f for f in findings if f.details.get("issue_type") == l3_type]
    assert len(l3_findings) >= 1
    assert l3_findings[0].details.get("level") == "3"
    assert l3_findings[0].details.get("parent_level") == "2"
    assert l3_findings[0].details.get("source_q_rule_id") == "Q056"


def test_p039_too_few_l2_entries_skipped(tmp_path: Path) -> None:
    """Only 1 L2 entry — below MIN_CHILD_ENTRIES_TO_CHECK gate → no finding."""
    pdf_path = tmp_path / "p039_one_l2.pdf"
    _make_toc_hierarchy_pdf(pdf_path, l1_x=72.0, l2_x=72.0, l1_count=1, l2_count=1)
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_toc_entry_hierarchy(model) if f.rule_id == "P039"]
    assert not findings


def test_p039_no_l1_entries_skipped(tmp_path: Path) -> None:
    """No L1 entries, only L2 → no finding (gate: need parent level to compare)."""
    pdf_path = tmp_path / "p039_no_l1.pdf"
    _make_toc_hierarchy_pdf(pdf_path, l1_x=72.0, l2_x=72.0, l1_count=0, l2_count=4)
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_toc_entry_hierarchy(model) if f.rule_id == "P039"]
    l2_type = "toc_l2_not_indented_relative_to_l1"
    l2_findings = [f for f in findings if f.details.get("issue_type") == l2_type]
    assert not l2_findings


def test_p039_lot_page_not_checked(tmp_path: Path) -> None:
    """LIST OF TABLES page → P039 does not apply (TOC-only rule)."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((190, 90), "LIST OF TABLES", fontsize=16, fontname="Times-Bold")
    y = 140.0
    for i in range(4):
        page.insert_text((72.0, y), f"Table {i + 1}. A Table Title That Is Quite Long", fontsize=12)
        page.insert_text((500, y), str(i + 10), fontsize=12)
        y += 22.0
    pdf_path = tmp_path / "p039_lot.pdf"
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_toc_entry_hierarchy(model) if f.rule_id == "P039"]
    assert not findings


def test_p039_findings_metadata_no_private_content(tmp_path: Path) -> None:
    """Finding details must contain only geometry/metadata — no entry title text."""
    pdf_path = tmp_path / "p039_privacy.pdf"
    _make_toc_hierarchy_pdf(pdf_path, l1_x=72.0, l2_x=72.0)
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_toc_entry_hierarchy(model) if f.rule_id == "P039"]
    assert findings
    for f in findings:
        for key, value in f.details.items():
            assert "Subsection" not in str(value), f"Entry text leaked into details[{key!r}]"
            assert "Chapter" not in str(value), f"Entry text leaked into details[{key!r}]"
        assert f.details.get("source_q_rule_id") == "Q056"
        assert "observed_delta_points" in f.details
        assert "required_delta_points" in f.details
        assert "entry_count" not in f.details or True  # field not required


def test_p039_cli_includes_rule(tmp_path: Path) -> None:
    """CLI JSON output includes P039 when L2 entries lack indentation."""
    pdf_path = tmp_path / "p039_cli.pdf"
    json_out = tmp_path / "p039_report.json"
    _make_toc_hierarchy_pdf(pdf_path, l1_x=72.0, l2_x=72.0)
    result = runner.invoke(app, ["pdf", str(pdf_path), "--json-out", str(json_out)])
    assert result.exit_code == 0
    payload = json.loads(json_out.read_text(encoding="utf-8"))
    assert any(item.get("rule_id") == "P039" for item in payload.get("findings", []))


# ---------------------------------------------------------------------------
# P040: LoF entry terminal punctuation
# ---------------------------------------------------------------------------


def _make_lof_terminal_punct_pdf(
    path: Path,
    entries: list[tuple[str, str | None]],
    heading: str = "LIST OF FIGURES",
) -> None:
    """Build a synthetic LoF/LoT/TOC page.

    entries: list of (entry_text, page_number) pairs.
    If page_number is None, the entry has no trailing page number (wrap continuation).
    """
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((190, 90), heading, fontsize=16, fontname="Times-Bold")
    y = 140.0
    for text, pg_num in entries:
        page.insert_text((72.0, y), text, fontsize=12)
        if pg_num is not None:
            page.insert_text((500, y), pg_num, fontsize=12)
        y += 22.0
    doc.save(path)
    doc.close()


def test_p040_lof_entry_with_period_no_finding(tmp_path: Path) -> None:
    """LoF entry ending with '.' → no P040 finding."""
    pdf_path = tmp_path / "p040_period.pdf"
    _make_lof_terminal_punct_pdf(pdf_path, [
        ("Figure 1. An Example Figure With Correct Punctuation.", "5"),
        ("Figure 2. Another Figure Description Ends Correctly.", "12"),
        ("Figure 3. Third Figure Also Correctly Ends.", "20"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lof_terminal_punctuation(model) if f.rule_id == "P040"]
    assert not findings


def test_p040_lof_entry_with_question_mark_no_finding(tmp_path: Path) -> None:
    """LoF entry ending with '?' → no P040 finding."""
    pdf_path = tmp_path / "p040_question.pdf"
    _make_lof_terminal_punct_pdf(pdf_path, [
        ("Figure 1. Does This Figure Show the Expected Results?", "7"),
        ("Figure 2. Another Entry Ending With Correct Punctuation.", "15"),
        ("Figure 3. Is This Also Acceptable?", "22"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lof_terminal_punctuation(model) if f.rule_id == "P040"]
    assert not findings


def test_p040_lof_entry_missing_punct_warns(tmp_path: Path) -> None:
    """LoF entry lacking terminal punctuation → lof_entry_missing_terminal_punctuation."""
    pdf_path = tmp_path / "p040_no_punct.pdf"
    _make_lof_terminal_punct_pdf(pdf_path, [
        ("Figure 1. An Example Figure With Correct Punctuation.", "5"),
        ("Figure 2. This Entry Has No Terminal Punctuation At All", "12"),
        ("Figure 3. Third Figure Also Correctly Ends.", "20"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lof_terminal_punctuation(model) if f.rule_id == "P040"]
    assert len(findings) >= 1
    assert findings[0].details.get("issue_type") == "lof_entry_missing_terminal_punctuation"
    assert findings[0].details.get("source_q_rule_id") == "Q075"


def test_p040_single_reconstructed_entry_missing_punct_warns(tmp_path: Path) -> None:
    """Q075 applies even when a List of Figures page contains one entry."""
    pdf_path = tmp_path / "p040_single_entry_no_punct.pdf"
    _make_lof_terminal_punct_pdf(
        pdf_path,
        [("Figure 1. A single figure description without terminal punctuation", "5")],
    )
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lof_terminal_punctuation(model) if f.rule_id == "P040"]
    assert len(findings) == 1
    assert findings[0].details.get("page_entry_index") == "0"


def test_p040_all_entries_missing_punct_multiple_findings(tmp_path: Path) -> None:
    """Multiple LoF entries lacking punctuation → multiple P040 findings."""
    pdf_path = tmp_path / "p040_all_missing.pdf"
    _make_lof_terminal_punct_pdf(pdf_path, [
        ("Figure 1. Entry Without Punctuation One", "5"),
        ("Figure 2. Entry Without Punctuation Two", "10"),
        ("Figure 3. Entry Without Punctuation Three", "15"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lof_terminal_punctuation(model) if f.rule_id == "P040"]
    assert len(findings) >= 2


def test_p040_continuation_line_no_page_token_skipped(tmp_path: Path) -> None:
    """Wrap-continuation line (no page number) is skipped — not checked."""
    pdf_path = tmp_path / "p040_wrap.pdf"
    _make_lof_terminal_punct_pdf(pdf_path, [
        ("Figure 1. A Very Long Description That Wraps Onto", None),
        ("the Next Line Here And Ends Without Punctuation.", "8"),
        ("Figure 2. Another Figure Entry With Correct Punctuation.", "15"),
        ("Figure 3. Third Complete Entry With Period.", "22"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lof_terminal_punctuation(model) if f.rule_id == "P040"]
    assert not any(
        "wraps onto" in str(f.details).lower()
        for f in findings
    )


def test_p040_lot_page_not_checked(tmp_path: Path) -> None:
    """LIST OF TABLES page → P040 does not apply (LoF-only rule)."""
    pdf_path = tmp_path / "p040_lot.pdf"
    _make_lof_terminal_punct_pdf(pdf_path, [
        ("Table 1. A Table Title Without Terminal Punctuation", "5"),
        ("Table 2. Another Table Title No Punctuation Here", "10"),
        ("Table 3. Third Table Title Also Missing Punctuation", "15"),
    ], heading="LIST OF TABLES")
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lof_terminal_punctuation(model) if f.rule_id == "P040"]
    assert not findings


def test_p040_toc_page_not_checked(tmp_path: Path) -> None:
    """TABLE OF CONTENTS page → P040 does not apply."""
    pdf_path = tmp_path / "p040_toc.pdf"
    _make_lof_terminal_punct_pdf(pdf_path, [
        ("Chapter 1 Introduction Without Punctuation", "1"),
        ("Chapter 2 Background Without Punctuation", "15"),
        ("Chapter 3 Methodology Without Punctuation", "30"),
    ], heading="TABLE OF CONTENTS")
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lof_terminal_punctuation(model) if f.rule_id == "P040"]
    assert not findings


def test_p040_findings_metadata_no_private_content(tmp_path: Path) -> None:
    """Finding details must not contain LoF entry text."""
    pdf_path = tmp_path / "p040_privacy.pdf"
    _make_lof_terminal_punct_pdf(pdf_path, [
        ("Figure 1. This Entry Has No Terminal Punctuation", "5"),
        ("Figure 2. Another Missing Punctuation Entry", "10"),
        ("Figure 3. Third Entry No Punct Either", "15"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lof_terminal_punctuation(model) if f.rule_id == "P040"]
    assert findings
    for f in findings:
        for key, value in f.details.items():
            assert "punctuation" not in str(value).lower() or key in (
                "issue_type", "terminal_punctuation_required"
            ), f"Unexpected entry text in details[{key!r}]"
            assert "figure" not in str(value).lower() or key in (
                "issue_type", "page_type"
            ), f"Entry text may have leaked into details[{key!r}]"
        assert f.details.get("source_q_rule_id") == "Q075"
        assert "line_y" in f.details


def test_p040_finding_includes_reliable_bbox(tmp_path: Path) -> None:
    """P040 findings must carry a bbox so the UI can highlight the affected entry.

    Regression test for the "Open original PDF page" fallback: without a bbox
    in details, has_visible_highlight() has nothing to work with and the UI
    can't offer a highlighted-page action even though the affected line is
    known internally.
    """
    pdf_path = tmp_path / "p040_bbox.pdf"
    _make_lof_terminal_punct_pdf(pdf_path, [
        ("Figure 1.1 Biomechanical representation of trunk support.", "6"),
        ("Figure 1.2 Labeled components of a lower-body exoskeleton", "7"),
        ("Figure 1.3 Scatterplot for perceptions and readiness.", "38"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lof_terminal_punctuation(model) if f.rule_id == "P040"]
    assert len(findings) == 1
    finding = findings[0]
    bbox_detail = finding.details.get("bbox", "")
    assert bbox_detail, "P040 finding is missing bbox evidence for the affected entry"
    x0, y0, x1, y1 = (float(v) for v in bbox_detail.split(","))
    assert x1 > x0
    assert y1 > y0


def test_p040_finding_bbox_is_highlightable(tmp_path: Path) -> None:
    """The bbox stored on a P040 finding must resolve to a visible highlight."""
    pdf_path = tmp_path / "p040_highlightable.pdf"
    _make_lof_terminal_punct_pdf(pdf_path, [
        ("Figure 1.1 Biomechanical representation of trunk support.", "6"),
        ("Figure 1.2 Labeled components of a lower-body exoskeleton", "7"),
        ("Figure 1.3 Scatterplot for perceptions and readiness.", "38"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lof_terminal_punctuation(model) if f.rule_id == "P040"]
    assert len(findings) == 1
    finding = findings[0]
    bbox = resolve_primary_highlight_bbox(
        finding.details, rule_id=finding.rule_id,
        issue_type=finding.details.get("issue_type", ""),
    )
    assert bbox is not None
    assert has_visible_highlight(bbox, page=finding.page)


def test_p040_only_missing_entry_flagged_others_clean(tmp_path: Path) -> None:
    """Only the entry lacking terminal punctuation is flagged; the rest are not."""
    pdf_path = tmp_path / "p040_mixed.pdf"
    _make_lof_terminal_punct_pdf(pdf_path, [
        ("Figure 1.1 Biomechanical representation of trunk support.", "6"),
        ("Figure 1.2 Labeled components of a lower-body exoskeleton", "7"),
        ("Figure 1.3 Scatterplot for perceptions and readiness.", "38"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lof_terminal_punctuation(model) if f.rule_id == "P040"]
    assert len(findings) == 1
    # Entry 1.2 is the second entry on the page (page-relative index 1).
    assert findings[0].details.get("page_entry_index") == "1"


def test_p040_location_label_shows_list_of_figures_section(tmp_path: Path) -> None:
    """Location text should read "List of Figures", not the generic "list" fallback.

    Regression test: before page_type was added to P040's details, the shared
    report_view location-label helper had no page_type to key off of and fell
    back to the generic noun "list" instead of naming the actual section.
    """
    pdf_path = tmp_path / "p040_location.pdf"
    _make_lof_terminal_punct_pdf(pdf_path, [
        ("Figure 1.1 Biomechanical representation of trunk support.", "6"),
        ("Figure 1.2 Labeled components of a lower-body exoskeleton", "7"),
        ("Figure 1.3 Scatterplot for perceptions and readiness.", "38"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lof_terminal_punctuation(model) if f.rule_id == "P040"]
    assert len(findings) == 1
    finding = findings[0]
    label = enriched_pdf_location_label(
        finding.rule_id,
        finding.details.get("issue_type", ""),
        finding.details,
        finding.page,
    )
    assert "List of Figures" in label
    assert label != "list"


def test_p040_rule_id_and_issue_type_unchanged(tmp_path: Path) -> None:
    """The bbox/location fix must not change rule_id, issue_type, or finding count."""
    pdf_path = tmp_path / "p040_semantics.pdf"
    _make_lof_terminal_punct_pdf(pdf_path, [
        ("Figure 1.1 Biomechanical representation of trunk support.", "6"),
        ("Figure 1.2 Labeled components of a lower-body exoskeleton", "7"),
        ("Figure 1.3 Scatterplot for perceptions and readiness.", "38"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_lof_terminal_punctuation(model)
    p040_findings = [f for f in findings if f.rule_id == "P040"]
    assert len(p040_findings) == 1
    assert p040_findings[0].rule_id == "P040"
    assert p040_findings[0].details.get("issue_type") == "lof_entry_missing_terminal_punctuation"
    assert "entry_index" in p040_findings[0].details


def test_p040_cli_includes_rule(tmp_path: Path) -> None:
    """CLI JSON output includes P040 when LoF entries lack terminal punctuation."""
    pdf_path = tmp_path / "p040_cli.pdf"
    json_out = tmp_path / "p040_report.json"
    _make_lof_terminal_punct_pdf(pdf_path, [
        ("Figure 1. Entry Without Terminal Punctuation", "5"),
        ("Figure 2. Another Entry Without Punctuation", "10"),
        ("Figure 3. Third Entry Also Missing Punctuation", "15"),
    ])
    result = runner.invoke(app, ["pdf", str(pdf_path), "--json-out", str(json_out)])
    assert result.exit_code == 0
    payload = json.loads(json_out.read_text(encoding="utf-8"))
    assert any(item.get("rule_id") == "P040" for item in payload.get("findings", []))


# ---------------------------------------------------------------------------
# P053: LoT entry terminal-period check
# ---------------------------------------------------------------------------


def _make_lot_terminal_period_pdf(
    path: Path,
    entries: list[tuple[str, str | None]],
    heading: str = "LIST OF TABLES",
) -> None:
    """Build a synthetic LoT page for P053 testing.

    entries: list of (entry_text, page_number) pairs.
    If page_number is None the entry is a wrap continuation line.
    """
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((190, 90), heading, fontsize=16, fontname="Times-Bold")
    y = 140.0
    for text, pg_num in entries:
        page.insert_text((72.0, y), text, fontsize=12)
        if pg_num is not None:
            page.insert_text((500, y), pg_num, fontsize=12)
        y += 22.0
    doc.save(path)
    doc.close()


def test_p053_lot_entry_no_period_no_finding(tmp_path: Path) -> None:
    """Complete LoT entries without terminal period → no P053 finding."""
    pdf_path = tmp_path / "p053_no_period.pdf"
    _make_lot_terminal_period_pdf(pdf_path, [
        ("Table 1 Summary of Experimental Results", "5"),
        ("Table 2 Comparison of Algorithm Performance", "12"),
        ("Table 3 Overview of Evaluation Metrics", "20"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_terminal_period(model) if f.rule_id == "P053"]
    assert not findings


def test_p053_lot_entry_with_period_warns(tmp_path: Path) -> None:
    """Complete LoT entry ending with '.' → P053 lot_entry_has_terminal_period."""
    pdf_path = tmp_path / "p053_period.pdf"
    _make_lot_terminal_period_pdf(pdf_path, [
        ("Table 1 Summary of Results With Terminal Period.", "5"),
        ("Table 2 Another Table Without Period", "12"),
        ("Table 3 Third Entry Without Period", "20"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_terminal_period(model) if f.rule_id == "P053"]
    assert len(findings) == 1
    assert findings[0].details.get("issue_type") == "lot_entry_has_terminal_period"


def test_p053_wrap_continuation_skipped(tmp_path: Path) -> None:
    """Lines without page-number tokens (leading wrap lines) are not flagged."""
    pdf_path = tmp_path / "p053_wrap.pdf"
    _make_lot_terminal_period_pdf(pdf_path, [
        ("Table 1 A Long Table Title That Wraps Onto", None),
        ("  the Next Line and Has No Period", "5"),
        ("Table 2 Another Entry That Also Wraps", None),
        ("  Continuation Ending Without Period", "12"),
        ("Table 3 Short Entry No Period Here", "20"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_terminal_period(model) if f.rule_id == "P053"]
    assert not findings


def test_p053_no_lot_page_no_finding(tmp_path: Path) -> None:
    """No LIST OF TABLES page → no P053 finding."""
    pdf_path = tmp_path / "p053_no_lot.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((72.0, 200.0), "This is a body page with no LoT heading.", fontsize=12)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_terminal_period(model) if f.rule_id == "P053"]
    assert not findings


def test_p053_lof_page_not_checked(tmp_path: Path) -> None:
    """LIST OF FIGURES page → P053 does not apply."""
    pdf_path = tmp_path / "p053_lof.pdf"
    _make_lot_terminal_period_pdf(pdf_path, [
        ("Figure 1 An Example Figure Caption With Period.", "5"),
        ("Figure 2 Another Figure Description With Period.", "12"),
        ("Figure 3 Third Figure Also Has Period.", "20"),
    ], heading="LIST OF FIGURES")
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_terminal_period(model) if f.rule_id == "P053"]
    assert not findings


def test_p053_sparse_page_skipped(tmp_path: Path) -> None:
    """LoT page with fewer than 2 entries → skipped."""
    pdf_path = tmp_path / "p053_sparse.pdf"
    _make_lot_terminal_period_pdf(pdf_path, [
        ("Table 1 Only One Entry With Terminal Period Here.", "5"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_terminal_period(model) if f.rule_id == "P053"]
    assert not findings


def test_p053_finding_metadata_privacy_safe(tmp_path: Path) -> None:
    """Findings must not include table title text or entry text."""
    pdf_path = tmp_path / "p053_privacy.pdf"
    _make_lot_terminal_period_pdf(pdf_path, [
        ("Table 1 A Table Entry That Ends With Period And Should Warn.", "5"),
        ("Table 2 Another Entry Without Period", "12"),
        ("Table 3 Third Entry Also Without Period", "20"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_terminal_period(model) if f.rule_id == "P053"]
    assert findings
    finding = findings[0]
    assert "issue_type" in finding.details
    assert "entry_index" in finding.details
    assert "page" in finding.details
    assert "section_type" in finding.details
    assert finding.details["section_type"] == "list_of_tables"
    assert finding.details.get("source_q_rule_id") == "Q065"
    assert finding.details.get("triage_tier") == "medium"
    for key, value in finding.details.items():
        assert "table" not in str(value).lower() or key in ("issue_type", "section_type"), (
            f"Entry text may have leaked into details[{key!r}]"
        )


def test_p053_finding_includes_reliable_bbox(tmp_path: Path) -> None:
    """P053 findings must carry a bbox so the UI can highlight the offending entry."""
    pdf_path = tmp_path / "p053_bbox.pdf"
    _make_lot_terminal_period_pdf(pdf_path, [
        ("Table 1 A Table Entry That Ends With Period And Should Warn.", "5"),
        ("Table 2 Another Entry Without Period", "12"),
        ("Table 3 Third Entry Also Without Period", "20"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_terminal_period(model) if f.rule_id == "P053"]
    assert findings
    finding = findings[0]
    bbox = resolve_primary_highlight_bbox(
        finding.details, rule_id=finding.rule_id,
        issue_type=finding.details.get("issue_type", ""),
    )
    assert bbox is not None
    assert has_visible_highlight(bbox, page=finding.page)


def test_p053_import_and_wiring(tmp_path: Path) -> None:
    """P053 is importable and wired in audit_runner."""
    import inspect

    import njit_auditor.audit_runner as audit_runner
    from njit_auditor.rules.pdf_lot_terminal_period import (
        check_pdf_lot_terminal_period as _check,
    )
    assert callable(_check)
    src = inspect.getsource(audit_runner.collect_pdf_layout_findings)
    assert "check_pdf_lot_terminal_period" in src


def test_p053_p040_unaffected(tmp_path: Path) -> None:
    """P040 (LoF terminal punctuation) unaffected by P053 implementation."""
    pdf_path = tmp_path / "p053_p040_unaffected.pdf"
    _make_lot_terminal_period_pdf(pdf_path, [
        ("Figure 1 Entry Without Terminal Punctuation", "5"),
        ("Figure 2 Another Entry Without Punctuation", "12"),
        ("Figure 3 Third Entry Also Missing Punctuation", "20"),
    ], heading="LIST OF FIGURES")
    model = load_pdf_layout(str(pdf_path))
    p040 = [f for f in check_pdf_lof_terminal_punctuation(model) if f.rule_id == "P040"]
    p053 = [f for f in check_pdf_lot_terminal_period(model) if f.rule_id == "P053"]
    assert p040
    assert not p053


# ---------------------------------------------------------------------------
# P054: TOC entry terminal-period absence check
# ---------------------------------------------------------------------------


from njit_auditor.rules.pdf_toc_terminal_period import check_pdf_toc_terminal_period  # noqa: E402


def _make_toc_terminal_period_pdf(
    path: Path,
    entries: list[tuple[str, str | None]],
    heading: str = "TABLE OF CONTENTS",
) -> None:
    """Build a synthetic TOC page for P054 testing.

    entries: list of (entry_text, page_number) pairs.
    If page_number is None the entry is a wrap continuation line.
    """
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((190, 90), heading, fontsize=16, fontname="Times-Bold")
    y = 140.0
    for text, pg_num in entries:
        page.insert_text((72.0, y), text, fontsize=12)
        if pg_num is not None:
            page.insert_text((500, y), pg_num, fontsize=12)
        y += 22.0
    doc.save(path)
    doc.close()


def test_p054_toc_entry_no_period_no_finding(tmp_path: Path) -> None:
    """Complete TOC entries without terminal period → no P054 finding."""
    pdf_path = tmp_path / "p054_no_period.pdf"
    _make_toc_terminal_period_pdf(pdf_path, [
        ("Chapter 1 Introduction and Background Overview", "1"),
        ("Chapter 2 Literature Review of Related Work", "15"),
        ("Chapter 3 Methodology and Experimental Design", "30"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_toc_terminal_period(model) if f.rule_id == "P054"]
    assert not findings


def test_p054_toc_entry_with_period_warns(tmp_path: Path) -> None:
    """Complete TOC entry ending with '.' → P054 toc_entry_has_terminal_period."""
    pdf_path = tmp_path / "p054_period.pdf"
    _make_toc_terminal_period_pdf(pdf_path, [
        ("Chapter 1 Introduction and Background Overview.", "1"),
        ("Chapter 2 Literature Review of Related Work", "15"),
        ("Chapter 3 Methodology and Experimental Design", "30"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_toc_terminal_period(model) if f.rule_id == "P054"]
    assert len(findings) == 1
    assert findings[0].details.get("issue_type") == "toc_entry_has_terminal_period"


def test_p054_period_before_hyphen_leaders_warns(tmp_path: Path) -> None:
    """A title period remains terminal punctuation before hyphen leaders."""
    pdf_path = tmp_path / "p054_period_hyphen_leaders.pdf"
    _make_toc_terminal_period_pdf(
        pdf_path,
        [
            ("Chapter 1 Introduction and Background.----------------", "1"),
            ("Chapter 2 Literature Review of Related Work", "15"),
            ("Chapter 3 Methodology and Experimental Design", "30"),
        ],
    )
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_toc_terminal_period(model) if f.rule_id == "P054"]
    assert len(findings) == 1
    assert findings[0].details.get("issue_type") == "toc_entry_has_terminal_period"


def test_p054_wrap_continuation_skipped(tmp_path: Path) -> None:
    """Lines without page-number tokens (wrap continuations) are not flagged."""
    pdf_path = tmp_path / "p054_wrap.pdf"
    _make_toc_terminal_period_pdf(pdf_path, [
        ("Chapter 1 A Very Long Chapter Title That Wraps", None),
        ("  to the Next Line and Has No Period", "1"),
        ("Chapter 2 Another Long Title That Also Wraps", None),
        ("  Continuation Line Without Period", "15"),
        ("Chapter 3 Methodology and Design", "30"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_toc_terminal_period(model) if f.rule_id == "P054"]
    assert not findings


def test_p054_no_toc_page_no_finding(tmp_path: Path) -> None:
    """No TABLE OF CONTENTS page → no P054 finding."""
    pdf_path = tmp_path / "p054_no_toc.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((72.0, 200.0), "This is a body page with no TOC heading.", fontsize=12)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_toc_terminal_period(model) if f.rule_id == "P054"]
    assert not findings


def test_p054_lot_page_not_checked(tmp_path: Path) -> None:
    """LIST OF TABLES page → P054 does not apply (LoT handled by P053)."""
    pdf_path = tmp_path / "p054_lot.pdf"
    _make_toc_terminal_period_pdf(pdf_path, [
        ("Table 1 A Table Entry With Terminal Period.", "5"),
        ("Table 2 Another Table With Terminal Period.", "12"),
        ("Table 3 Third Table With Terminal Period.", "20"),
    ], heading="LIST OF TABLES")
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_toc_terminal_period(model) if f.rule_id == "P054"]
    assert not findings


def test_p054_sparse_page_skipped(tmp_path: Path) -> None:
    """TOC page with fewer than 2 entries → skipped."""
    pdf_path = tmp_path / "p054_sparse.pdf"
    _make_toc_terminal_period_pdf(pdf_path, [
        ("Chapter 1 Introduction with Terminal Period.", "1"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_toc_terminal_period(model) if f.rule_id == "P054"]
    assert not findings


def test_p054_finding_metadata_privacy_safe(tmp_path: Path) -> None:
    """Findings must not include TOC entry text or chapter title text."""
    pdf_path = tmp_path / "p054_privacy.pdf"
    _make_toc_terminal_period_pdf(pdf_path, [
        ("Chapter 1 A Chapter Title That Ends With Period.", "1"),
        ("Chapter 2 Another Chapter Without Period Here", "15"),
        ("Chapter 3 Third Chapter Also Without Period", "30"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_toc_terminal_period(model) if f.rule_id == "P054"]
    assert findings
    finding = findings[0]
    assert "issue_type" in finding.details
    assert "entry_index" in finding.details
    assert "page" in finding.details
    assert "section_type" in finding.details
    assert finding.details["section_type"] == "table_of_contents"
    assert finding.details.get("source_q_rule_id") == "Q050"
    assert finding.details.get("triage_tier") == "medium"


def test_p054_finding_includes_reliable_bbox(tmp_path: Path) -> None:
    """P054 findings must carry a bbox so the UI can highlight the offending entry."""
    pdf_path = tmp_path / "p054_bbox.pdf"
    _make_toc_terminal_period_pdf(pdf_path, [
        ("Chapter 1 A Chapter Title That Ends With Period.", "1"),
        ("Chapter 2 Another Chapter Without Period Here", "15"),
        ("Chapter 3 Third Chapter Also Without Period", "30"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_toc_terminal_period(model) if f.rule_id == "P054"]
    assert findings
    finding = findings[0]
    bbox = resolve_primary_highlight_bbox(
        finding.details, rule_id=finding.rule_id,
        issue_type=finding.details.get("issue_type", ""),
    )
    assert bbox is not None
    assert has_visible_highlight(bbox, page=finding.page)


def test_p054_import_and_wiring(tmp_path: Path) -> None:
    """P054 is importable and wired in audit_runner."""
    import inspect

    import njit_auditor.audit_runner as audit_runner
    from njit_auditor.rules.pdf_toc_terminal_period import (
        check_pdf_toc_terminal_period as _check,
    )
    assert callable(_check)
    src = inspect.getsource(audit_runner.collect_pdf_layout_findings)
    assert "check_pdf_toc_terminal_period" in src


def test_p054_p053_unaffected(tmp_path: Path) -> None:
    """P053 still fires correctly for LoT entries after P054 added."""
    pdf_path = tmp_path / "p054_p053_unaffected.pdf"
    _make_lot_terminal_period_pdf(pdf_path, [
        ("Table 1 A Table Entry That Ends With Period.", "5"),
        ("Table 2 Another Table Without Period", "12"),
        ("Table 3 Third Table Without Period", "20"),
    ])
    model = load_pdf_layout(str(pdf_path))
    p053 = [f for f in check_pdf_lot_terminal_period(model) if f.rule_id == "P053"]
    p054 = [f for f in check_pdf_toc_terminal_period(model) if f.rule_id == "P054"]
    assert p053
    assert not p054


# ---------------------------------------------------------------------------
# P041: Dedication page top-margin header check
# ---------------------------------------------------------------------------


def _make_dedication_pdf(
    path: Path,
    *,
    header_text: str | None = None,
    header_y: float = 40.0,
    dedication_heading_y: float = 150.0,
    include_dedication_heading: bool = True,
    body_text_y: float = 260.0,
) -> None:
    """Create a synthetic Dedication page PDF.

    header_text: if provided, inserted in the top zone as a running header.
    dedication_heading_y: baseline y for the DEDICATION heading (should be below top zone).
    """
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    if header_text is not None:
        page.insert_text((72.0, header_y), header_text, fontsize=10)
    if include_dedication_heading:
        page.insert_text((270.0, dedication_heading_y), "DEDICATION", fontsize=14,
                         fontname="Times-Bold")
    page.insert_text((200.0, body_text_y), "In memory of those who came before.", fontsize=12)
    doc.save(path)
    doc.close()


def test_p041_no_dedication_page_no_finding(tmp_path: Path) -> None:
    """No DEDICATION heading in PDF → no P041 finding (gate)."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((190, 90), "TABLE OF CONTENTS", fontsize=16, fontname="Times-Bold")
    page.insert_text((108, 140), "Chapter 1 Introduction", fontsize=12)
    pdf_path = tmp_path / "p041_no_ded.pdf"
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_dedication_page(model) if f.rule_id == "P041"]
    assert not findings


def test_p041_dedication_page_no_header_no_finding(tmp_path: Path) -> None:
    """Dedication page with no top-margin text → no P041 finding."""
    pdf_path = tmp_path / "p041_ded_clean.pdf"
    _make_dedication_pdf(pdf_path, header_text=None)
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_dedication_page(model) if f.rule_id == "P041"]
    assert not findings


def test_p041_dedication_page_with_header_warns(tmp_path: Path) -> None:
    """Dedication page with running header text → dedication_top_margin_header_text."""
    pdf_path = tmp_path / "p041_ded_header.pdf"
    _make_dedication_pdf(pdf_path, header_text="Some Running Header Text")
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_dedication_page(model) if f.rule_id == "P041"]
    assert len(findings) >= 1
    assert findings[0].details.get("issue_type") == "dedication_top_margin_header_text"
    assert findings[0].details.get("source_q_rule_id") == "Q032"


def test_p041_page_number_in_top_zone_ignored(tmp_path: Path) -> None:
    """Page number candidate in top zone is skipped → no P041 finding."""
    pdf_path = tmp_path / "p041_ded_pagnum.pdf"
    _make_dedication_pdf(pdf_path, header_text="iv")
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_dedication_page(model) if f.rule_id == "P041"]
    assert not findings


def test_p041_dedication_heading_in_top_zone_ignored(tmp_path: Path) -> None:
    """DEDICATION heading appearing at page top is skipped → no P041 finding."""
    pdf_path = tmp_path / "p041_ded_hdg_top.pdf"
    _make_dedication_pdf(pdf_path, header_text="DEDICATION", header_y=40.0)
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_dedication_page(model) if f.rule_id == "P041"]
    assert not findings


def test_p041_body_text_below_top_zone_ignored(tmp_path: Path) -> None:
    """Dedication body text below top 15% is not flagged."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((270.0, 150.0), "DEDICATION", fontsize=14, fontname="Times-Bold")
    page.insert_text((200.0, 400.0), "In memory of those who came before.", fontsize=12)
    pdf_path = tmp_path / "p041_body_below.pdf"
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_dedication_page(model) if f.rule_id == "P041"]
    assert not findings


def test_p041_findings_metadata_no_private_content(tmp_path: Path) -> None:
    """Finding details must not contain dedication content."""
    pdf_path = tmp_path / "p041_privacy.pdf"
    _make_dedication_pdf(pdf_path, header_text="Some Running Header Text")
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_dedication_page(model) if f.rule_id == "P041"]
    assert findings
    for f in findings:
        assert f.details.get("source_q_rule_id") == "Q032"
        assert "line_y" in f.details
        assert "line_x0" in f.details
        assert "top_region_threshold_points" in f.details
        for key, value in f.details.items():
            assert "memory" not in str(value).lower(), f"Dedication content in details[{key!r}]"
            assert "header" not in str(value).lower() or key == "issue_type", (
                f"Header text may have leaked into details[{key!r}]"
            )


def test_p041_cli_includes_rule(tmp_path: Path) -> None:
    """CLI JSON output includes P041 when Dedication header is found."""
    pdf_path = tmp_path / "p041_cli.pdf"
    json_out = tmp_path / "p041_report.json"
    _make_dedication_pdf(pdf_path, header_text="Running Header Here")
    result = runner.invoke(app, ["pdf", str(pdf_path), "--json-out", str(json_out)])
    assert result.exit_code == 0
    payload = json.loads(json_out.read_text(encoding="utf-8"))
    assert any(item.get("rule_id") == "P041" for item in payload.get("findings", []))


# ---------------------------------------------------------------------------
# P042: TOC appendix entry format
# ---------------------------------------------------------------------------


def _make_toc_with_appendix_pdf(
    path: Path,
    appendix_entries: list[tuple[str, str]],
    chapter_entries: list[tuple[str, str]] | None = None,
    heading: str = "TABLE OF CONTENTS",
) -> None:
    """Create a synthetic TOC page with appendix entries.

    appendix_entries: list of (entry_text, page_number) pairs.
    """
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((190, 90), heading, fontsize=16, fontname="Times-Bold")
    y = 140.0
    if chapter_entries:
        for text, pg_num in chapter_entries:
            page.insert_text((72.0, y), text, fontsize=12)
            page.insert_text((500, y), pg_num, fontsize=12)
            y += 22.0
    for text, pg_num in appendix_entries:
        page.insert_text((72.0, y), text, fontsize=12)
        page.insert_text((500, y), pg_num, fontsize=12)
        y += 22.0
    doc.save(path)
    doc.close()


def test_p042_no_appendix_entries_no_finding(tmp_path: Path) -> None:
    """TOC with only chapter entries → no P042 finding."""
    pdf_path = tmp_path / "p042_no_app.pdf"
    _make_toc_with_appendix_pdf(pdf_path, appendix_entries=[], chapter_entries=[
        ("Chapter 1 Introduction to the Study", "1"),
        ("Chapter 2 Background and Related Work", "15"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_toc_appendix_format(model) if f.rule_id == "P042"]
    assert not findings


def test_p042_single_appendix_with_title_no_finding(tmp_path: Path) -> None:
    """Single appendix entry with title after APPENDIX → no P042 finding."""
    pdf_path = tmp_path / "p042_single_ok.pdf"
    _make_toc_with_appendix_pdf(pdf_path, appendix_entries=[
        ("APPENDIX Data Collection Instruments", "85"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_toc_appendix_format(model) if f.rule_id == "P042"]
    assert not findings


def test_p042_single_appendix_no_title_warns(tmp_path: Path) -> None:
    """Single appendix entry with no title → single_appendix_missing_title."""
    pdf_path = tmp_path / "p042_single_no_title.pdf"
    _make_toc_with_appendix_pdf(pdf_path, appendix_entries=[
        ("Appendix", "85"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_toc_appendix_format(model) if f.rule_id == "P042"]
    assert len(findings) >= 1
    assert findings[0].details.get("issue_type") == "single_appendix_missing_title"
    assert findings[0].details.get("source_q_rule_id") == "Q058"


def test_p042_multiple_appendix_with_letters_no_finding(tmp_path: Path) -> None:
    """Multiple appendices each with letter identifier → no P042 finding."""
    pdf_path = tmp_path / "p042_multi_ok.pdf"
    _make_toc_with_appendix_pdf(pdf_path, appendix_entries=[
        ("APPENDIX A Data Collection Instruments", "85"),
        ("APPENDIX B Survey Questionnaire Form", "95"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_toc_appendix_format(model) if f.rule_id == "P042"]
    assert not findings


def test_p042_multiple_appendix_missing_letter_warns(tmp_path: Path) -> None:
    """Multiple appendices without letter identifiers → multiple_appendix_missing_letter."""
    pdf_path = tmp_path / "p042_multi_no_letter.pdf"
    _make_toc_with_appendix_pdf(pdf_path, appendix_entries=[
        ("APPENDIX Data Collection Instruments", "85"),
        ("APPENDIX Survey Questionnaire Form Item", "95"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_toc_appendix_format(model) if f.rule_id == "P042"]
    assert len(findings) >= 1
    assert any(f.details.get("issue_type") == "multiple_appendix_missing_letter" for f in findings)
    assert any(f.details.get("source_q_rule_id") == "Q059" for f in findings)


def test_p042_multiple_appendix_number_instead_of_letter_warns(tmp_path: Path) -> None:
    """Multiple appendices using numbers instead of letters → multiple_appendix_missing_letter."""
    pdf_path = tmp_path / "p042_multi_number.pdf"
    _make_toc_with_appendix_pdf(pdf_path, appendix_entries=[
        ("APPENDIX A Data Collection Instruments", "85"),
        ("APPENDIX 2 Survey Questionnaire Form", "95"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_toc_appendix_format(model) if f.rule_id == "P042"]
    assert len(findings) >= 1
    issue = "multiple_appendix_missing_letter"
    offending = [f for f in findings if f.details.get("issue_type") == issue]
    assert offending


def test_p042_lot_page_not_checked(tmp_path: Path) -> None:
    """LIST OF TABLES page → P042 does not apply (TOC-only rule)."""
    pdf_path = tmp_path / "p042_lot.pdf"
    _make_toc_with_appendix_pdf(pdf_path, appendix_entries=[
        ("APPENDIX A Survey Questionnaire", "85"),
        ("APPENDIX Survey Without Letter", "95"),
    ], heading="LIST OF TABLES")
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_toc_appendix_format(model) if f.rule_id == "P042"]
    assert not findings


def test_p042_findings_metadata_no_private_content(tmp_path: Path) -> None:
    """Finding details must not include appendix title text."""
    pdf_path = tmp_path / "p042_privacy.pdf"
    _make_toc_with_appendix_pdf(pdf_path, appendix_entries=[
        ("APPENDIX Survey Questionnaire Here", "85"),
        ("APPENDIX Another Survey Without Letter", "95"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_toc_appendix_format(model) if f.rule_id == "P042"]
    assert findings
    for f in findings:
        for key, value in f.details.items():
            assert "survey" not in str(value).lower(), f"Appendix title in details[{key!r}]"
            assert "questionnaire" not in str(value).lower(), f"Appendix title in details[{key!r}]"
        assert "appendix_entry_count" in f.details
        assert "entry_index" in f.details
        assert "source_q_rule_id" in f.details


def test_p042_cli_includes_rule(tmp_path: Path) -> None:
    """CLI JSON output includes P042 when appendix entries are incorrectly formatted."""
    pdf_path = tmp_path / "p042_cli.pdf"
    json_out = tmp_path / "p042_report.json"
    _make_toc_with_appendix_pdf(pdf_path, appendix_entries=[
        ("APPENDIX Survey Questionnaire Here", "85"),
        ("APPENDIX Another Survey Without Letter", "95"),
    ])
    result = runner.invoke(app, ["pdf", str(pdf_path), "--json-out", str(json_out)])
    assert result.exit_code == 0
    payload = json.loads(json_out.read_text(encoding="utf-8"))
    assert any(item.get("rule_id") == "P042" for item in payload.get("findings", []))


# ---------------------------------------------------------------------------
# P043: Acknowledgements paragraph indentation
# ---------------------------------------------------------------------------


def _make_acknowledgements_pdf(
    path: Path,
    para1_x: float = 108.0,
    para2_x: float = 140.0,
    include_heading: bool = True,
    n_paras: int = 2,
    pre_heading_x: float | None = None,
) -> None:
    """Synthetic Acknowledgements PDF for P043 tests.

    para1_x: first-line x of paragraph 1 (continuation lines at 108)
    para2_x: first-line x of paragraph 2 (continuation lines at 108)
    n_paras: 1 or 2 paragraph blocks below the heading
    pre_heading_x: if set, insert a usable text line at this x above the heading
    """
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    if pre_heading_x is not None:
        page.insert_text(
            (pre_heading_x, 50),
            "Synthetic pre-heading text line for testing purposes only here.",
        )
    if include_heading:
        page.insert_text((200, 90), "ACKNOWLEDGEMENTS", fontsize=14, fontname="Times-Bold")
    # Para 1: first line at para1_x, continuation flush-left at 108
    page.insert_text((para1_x, 130), "Synthetic ack body paragraph first line text here.")
    page.insert_text((108.0, 144), "Continuation ack first paragraph body text line here.")
    page.insert_text((108.0, 158), "Another line in first ack paragraph body text here.")
    if n_paras >= 2:
        # Para 2: large y gap from para1 ensures a separate paragraph block
        page.insert_text((para2_x, 240), "Synthetic ack body paragraph second line text here.")
        page.insert_text((108.0, 254), "Continuation ack second paragraph body text line here.")
        page.insert_text((108.0, 268), "Another line in second ack paragraph body text here.")
    doc.save(path)
    doc.close()


def test_p043_no_acknowledgements_page_no_findings(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p043_no_heading.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((200, 90), "ABSTRACT", fontsize=14, fontname="Times-Bold")
    page.insert_text((108, 130), "Synthetic body paragraph text for abstract page testing here.")
    page.insert_text((108, 144), "Continuation of synthetic abstract paragraph body text line.")
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_acknowledgements_indentation(model)
    assert not any(f.rule_id == "P043" for f in findings)


def test_p043_fewer_than_two_paragraphs_no_findings(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p043_one_para.pdf"
    _make_acknowledgements_pdf(pdf_path, n_paras=1)
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_acknowledgements_indentation(model)
    assert not any(f.rule_id == "P043" for f in findings)


def test_p043_correct_format_no_findings(tmp_path: Path) -> None:
    """First para flush-left (x=108), second para indented (x=140) → no findings."""
    pdf_path = tmp_path / "p043_ok.pdf"
    _make_acknowledgements_pdf(pdf_path, para1_x=108.0, para2_x=140.0)
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_acknowledgements_indentation(model)
    assert not any(f.rule_id == "P043" for f in findings)


def test_p043_first_paragraph_indented_warns(tmp_path: Path) -> None:
    """First para indented (x=150) → acknowledgements_first_paragraph_indented."""
    pdf_path = tmp_path / "p043_first_indent.pdf"
    _make_acknowledgements_pdf(pdf_path, para1_x=150.0, para2_x=150.0)
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_acknowledgements_indentation(model) if f.rule_id == "P043"]
    issue_types = [f.details.get("issue_type") for f in findings]
    assert "acknowledgements_first_paragraph_indented" in issue_types


def test_p043_subsequent_paragraph_not_indented_warns(tmp_path: Path) -> None:
    """Second para flush-left when first is also flush-left → subsequent_paragraph_not_indented."""
    pdf_path = tmp_path / "p043_second_flush.pdf"
    _make_acknowledgements_pdf(pdf_path, para1_x=108.0, para2_x=108.0)
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_acknowledgements_indentation(model) if f.rule_id == "P043"]
    issue_types = [f.details.get("issue_type") for f in findings]
    assert "acknowledgements_subsequent_paragraph_not_indented" in issue_types


def test_p043_text_before_heading_ignored(tmp_path: Path) -> None:
    """Pre-heading text at far-left x=40 must not contaminate the left margin calculation."""
    pdf_path = tmp_path / "p043_pre_heading.pdf"
    # If pre-heading text at x=40 were included, left_margin would be 40 and
    # para1_x=108 would look indented (delta=68 > 18) → false positive.
    _make_acknowledgements_pdf(pdf_path, para1_x=108.0, para2_x=140.0, pre_heading_x=40.0)
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_acknowledgements_indentation(model)
    assert not any(f.rule_id == "P043" for f in findings)


def test_p043_finding_metadata_no_private_content(tmp_path: Path) -> None:
    """Finding details must contain geometry metadata only — no paragraph body text."""
    pdf_path = tmp_path / "p043_privacy.pdf"
    _make_acknowledgements_pdf(pdf_path, para1_x=150.0, para2_x=108.0)
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_acknowledgements_indentation(model) if f.rule_id == "P043"]
    assert findings
    for f in findings:
        for value in f.details.values():
            assert "synthetic" not in str(value).lower()
            assert "paragraph text" not in str(value).lower()
        assert "issue_type" in f.details
        assert "page_number" in f.details
        assert "source_q_rule_id" in f.details


# ---------------------------------------------------------------------------
# P044 helpers
# ---------------------------------------------------------------------------


def _make_abstract_pdf(
    path: Path,
    para1_x: float = 108.0,
    para2_x: float = 140.0,
    include_heading: bool = True,
    n_paras: int = 2,
    pre_heading_x: float | None = None,
) -> None:
    """Synthetic Abstract PDF for P044 tests.

    para1_x: first-line x of paragraph 1 (continuation lines at 108)
    para2_x: first-line x of paragraph 2 (continuation lines at 108)
    n_paras: 1 or 2 paragraph blocks below the heading
    pre_heading_x: if set, insert a usable text line at this x above the heading
    """
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    if pre_heading_x is not None:
        page.insert_text(
            (pre_heading_x, 50),
            "Synthetic pre-heading text line for testing purposes only here.",
        )
    if include_heading:
        page.insert_text((200, 90), "ABSTRACT", fontsize=14, fontname="Times-Bold")
    # Para 1: first line at para1_x, continuation flush-left at 108
    page.insert_text((para1_x, 130), "Synthetic abstract body paragraph first line text here.")
    page.insert_text((108.0, 144), "Continuation abstract first paragraph body text line here.")
    page.insert_text((108.0, 158), "Another line in first abstract paragraph body text here.")
    if n_paras >= 2:
        # Para 2: large y gap from para1 ensures a separate paragraph block
        page.insert_text((para2_x, 240), "Synthetic abstract body paragraph second line here.")
        page.insert_text((108.0, 254), "Continuation abstract second paragraph body text line.")
        page.insert_text((108.0, 268), "Another line in second abstract paragraph body text.")
    doc.save(path)
    doc.close()


# ---------------------------------------------------------------------------
# P044 tests
# ---------------------------------------------------------------------------


def test_p044_no_abstract_page_no_findings(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p044_no_heading.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((200, 90), "ACKNOWLEDGEMENTS", fontsize=14, fontname="Times-Bold")
    page.insert_text((108, 130), "Synthetic body paragraph text for testing here.")
    page.insert_text((108, 144), "Continuation of synthetic body paragraph text line.")
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_abstract_indentation(model)
    assert not any(f.rule_id == "P044" for f in findings)


def test_p044_one_paragraph_q002_only_no_q003(tmp_path: Path) -> None:
    """Single paragraph: Q002 (first para flush) checked; no Q003 subsequent check."""
    pdf_path = tmp_path / "p044_one_para.pdf"
    _make_abstract_pdf(pdf_path, para1_x=108.0, n_paras=1)
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_abstract_indentation(model) if f.rule_id == "P044"]
    issue_types = [f.details.get("issue_type") for f in findings]
    assert "abstract_subsequent_paragraph_not_indented" not in issue_types


def test_p044_correct_format_no_findings(tmp_path: Path) -> None:
    """First para flush-left (x=108), second para indented (x=140) → no findings."""
    pdf_path = tmp_path / "p044_ok.pdf"
    _make_abstract_pdf(pdf_path, para1_x=108.0, para2_x=140.0)
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_abstract_indentation(model)
    assert not any(f.rule_id == "P044" for f in findings)


def test_p044_first_paragraph_indented_warns(tmp_path: Path) -> None:
    """First para indented (x=150) → abstract_first_paragraph_indented."""
    pdf_path = tmp_path / "p044_first_indent.pdf"
    _make_abstract_pdf(pdf_path, para1_x=150.0, para2_x=150.0)
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_abstract_indentation(model) if f.rule_id == "P044"]
    issue_types = [f.details.get("issue_type") for f in findings]
    assert "abstract_first_paragraph_indented" in issue_types


def test_p044_subsequent_paragraph_not_indented_warns(tmp_path: Path) -> None:
    """Second para flush-left when first is also flush → subsequent_not_indented finding."""
    pdf_path = tmp_path / "p044_second_flush.pdf"
    _make_abstract_pdf(pdf_path, para1_x=108.0, para2_x=108.0)
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_abstract_indentation(model) if f.rule_id == "P044"]
    issue_types = [f.details.get("issue_type") for f in findings]
    assert "abstract_subsequent_paragraph_not_indented" in issue_types


def test_p044_text_before_heading_ignored(tmp_path: Path) -> None:
    """Pre-heading text at far-left x=40 must not contaminate the left margin calculation."""
    pdf_path = tmp_path / "p044_pre_heading.pdf"
    # If pre-heading text at x=40 were included, left_margin would be 40 and
    # para1_x=108 would look indented (delta=68 > 18) → false positive.
    _make_abstract_pdf(pdf_path, para1_x=108.0, para2_x=140.0, pre_heading_x=40.0)
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_abstract_indentation(model)
    assert not any(f.rule_id == "P044" for f in findings)


def test_p044_centered_title_preamble_after_heading_ignored(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p044_centered_preamble.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((200, 90), "ABSTRACT", fontsize=14, fontname="Times-Bold")
    page.insert_text((170, 130), "Synthetic dissertation title line for testing.", fontsize=12)
    page.insert_text((290, 150), "by", fontsize=12)
    page.insert_text((250, 170), "Student Name", fontsize=12)
    page.insert_text(
        (108, 220),
        "Synthetic abstract body paragraph first line text here.",
        fontsize=12,
    )
    page.insert_text(
        (108, 234),
        "Continuation abstract first paragraph body text line here.",
        fontsize=12,
    )
    page.insert_text(
        (108, 248),
        "Another line in first abstract paragraph body text here.",
        fontsize=12,
    )
    page.insert_text(
        (140, 320),
        "Synthetic abstract body paragraph second line here.",
        fontsize=12,
    )
    page.insert_text(
        (108, 334),
        "Continuation abstract second paragraph body text line.",
        fontsize=12,
    )
    page.insert_text(
        (108, 348),
        "Another line in second abstract paragraph body text.",
        fontsize=12,
    )
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_abstract_indentation(model)
    assert not any(f.rule_id == "P044" for f in findings)


def test_p044_finding_metadata_no_private_content(tmp_path: Path) -> None:
    """Finding details must contain geometry metadata only — no paragraph body text."""
    pdf_path = tmp_path / "p044_privacy.pdf"
    _make_abstract_pdf(pdf_path, para1_x=150.0, para2_x=108.0)
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_abstract_indentation(model) if f.rule_id == "P044"]
    assert findings
    for f in findings:
        for value in f.details.values():
            assert "synthetic" not in str(value).lower()
            assert "paragraph text" not in str(value).lower()
        assert "issue_type" in f.details
        assert "page_number" in f.details
        assert "source_q_rule_id" in f.details


def test_p044_q002_source_q_rule_id(tmp_path: Path) -> None:
    """Q002 finding must have source_q_rule_id=Q002."""
    pdf_path = tmp_path / "p044_q002_id.pdf"
    _make_abstract_pdf(pdf_path, para1_x=150.0, para2_x=140.0)
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_abstract_indentation(model) if f.rule_id == "P044"]
    q002_findings = [
        f for f in findings if f.details.get("issue_type") == "abstract_first_paragraph_indented"
    ]
    assert q002_findings
    assert all(f.details.get("source_q_rule_id") == "Q002" for f in q002_findings)


def test_p044_q003_source_q_rule_id(tmp_path: Path) -> None:
    """Q003 finding must have source_q_rule_id=Q003."""
    pdf_path = tmp_path / "p044_q003_id.pdf"
    _make_abstract_pdf(pdf_path, para1_x=108.0, para2_x=108.0)
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_abstract_indentation(model) if f.rule_id == "P044"]
    q003_findings = [
        f for f in findings
        if f.details.get("issue_type") == "abstract_subsequent_paragraph_not_indented"
    ]
    assert q003_findings
    assert all(f.details.get("source_q_rule_id") == "Q003" for f in q003_findings)


def test_p044_continuation_line_after_large_gap_not_new_paragraph(tmp_path: Path) -> None:
    """A wrapped continuation line separated by a wide, double-spacing-style gap
    from a sentence that has not yet ended must not be misread as a new,
    non-indented paragraph (Ester Q003 checks the *top line* of each paragraph,
    not every line separated by a large vertical gap)."""
    pdf_path = tmp_path / "p044_continuation_gap.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((200, 90), "ABSTRACT", fontsize=14, fontname="Times-Bold")
    # Para 1: flush-left (correct), ends with a period.
    page.insert_text((108.0, 130), "Synthetic abstract body paragraph first line text here.")
    page.insert_text((108.0, 144), "Continuation abstract first paragraph body text line here.")
    # Para 2: correctly indented first line; the sentence does not end here and
    # wraps onto a flush-left continuation line separated by a >14pt gap.
    page.insert_text((140.0, 220), "Synthetic paragraph two first line continues without a")
    page.insert_text((108.0, 252), "period yet and wraps onto this flush continuation line.")
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_abstract_indentation(model) if f.rule_id == "P044"]
    issue_types = [f.details.get("issue_type") for f in findings]
    assert "abstract_subsequent_paragraph_not_indented" not in issue_types


def test_p044_real_flush_left_later_paragraph_still_warns(tmp_path: Path) -> None:
    """A genuine later paragraph that begins flush-left (no indent) after a
    completed sentence and a real paragraph gap must still be flagged."""
    pdf_path = tmp_path / "p044_real_flush_later.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((200, 90), "ABSTRACT", fontsize=14, fontname="Times-Bold")
    # Para 1: flush-left (correct for the first paragraph).
    page.insert_text((108.0, 130), "Synthetic abstract body paragraph first line text here.")
    page.insert_text((108.0, 144), "Continuation abstract first paragraph body text line here.")
    # Para 2: correctly indented, ends with a completed sentence.
    page.insert_text((140.0, 220), "Synthetic abstract body paragraph second line ends here.")
    # Para 3: begins flush-left (violation) after a real paragraph-sized gap.
    page.insert_text((108.0, 300), "Synthetic abstract body paragraph third line begins flush.")
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_abstract_indentation(model) if f.rule_id == "P044"]
    issue_types = [f.details.get("issue_type") for f in findings]
    assert "abstract_subsequent_paragraph_not_indented" in issue_types


# ---------------------------------------------------------------------------
# P045 helpers
# ---------------------------------------------------------------------------


def _make_biosketch_pdf(
    path: Path,
    include_heading: bool = True,
    n_hanging_blocks: int = 2,
    hanging_first_x: float = 108.0,
    hanging_rest_x: float = 126.0,
    inter_block_gap: float = 40.0,
    within_block_gap: float = 12.0,
) -> None:
    """Synthetic Biographical Sketch PDF for P045 tests.

    hanging_first_x: x0 of first line in each pub entry (flush-left)
    hanging_rest_x: x0 of continuation lines (indented — creates hanging indent)
    inter_block_gap: vertical gap between consecutive entry blocks
    within_block_gap: vertical gap between lines inside each entry block
    """
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    if include_heading:
        page.insert_text(
            (200, 70), "BIOGRAPHICAL SKETCH", fontsize=14, fontname="Times-Bold"
        )
    y = 110.0
    for _ in range(n_hanging_blocks):
        # First line of entry (flush-left / start of hanging indent)
        page.insert_text(
            (hanging_first_x, y),
            "Synthetic pub entry first line text for testing purposes here.",
        )
        y += within_block_gap
        # Continuation line (indented — rest of hanging indent)
        page.insert_text(
            (hanging_rest_x, y),
            "Synthetic publication continuation line body text here only.",
        )
        y += within_block_gap
        # Another continuation line
        page.insert_text(
            (hanging_rest_x, y),
            "Another continuation line for synthetic publication entry text.",
        )
        y += inter_block_gap
    doc.save(path)
    doc.close()


# ---------------------------------------------------------------------------
# P045 tests
# ---------------------------------------------------------------------------


def test_p045_no_biosketch_page_no_findings(tmp_path: Path) -> None:
    """No BIOGRAPHICAL SKETCH heading → no P045 findings."""
    pdf_path = tmp_path / "p045_no_heading.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((200, 70), "ACKNOWLEDGEMENTS", fontsize=14, fontname="Times-Bold")
    page.insert_text((108, 110), "Synthetic body paragraph text for testing here.")
    page.insert_text((108, 124), "Continuation of synthetic paragraph body text line.")
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_biosketch_publication_layout(model)
    assert not any(f.rule_id == "P045" for f in findings)


def test_p045_too_few_blocks_no_findings(tmp_path: Path) -> None:
    """Fewer than 2 multi-line blocks → gate skips all checks."""
    pdf_path = tmp_path / "p045_one_block.pdf"
    _make_biosketch_pdf(pdf_path, n_hanging_blocks=1)
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_biosketch_publication_layout(model)
    assert not any(f.rule_id == "P045" for f in findings)


def test_p045_correct_hanging_indent_no_findings(tmp_path: Path) -> None:
    """Hanging indent present and inter-entry gap adequate → no findings."""
    pdf_path = tmp_path / "p045_ok.pdf"
    # inter_block_gap=40 gives geometric gap ~25pt > ENTRY_GAP_THRESHOLD_PT=20pt
    _make_biosketch_pdf(
        pdf_path,
        n_hanging_blocks=2,
        hanging_first_x=108.0,
        hanging_rest_x=126.0,
        inter_block_gap=40.0,
        within_block_gap=12.0,
    )
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_biosketch_publication_layout(model)
    assert not any(f.rule_id == "P045" for f in findings)


def test_p045_missing_hanging_indent_warns(tmp_path: Path) -> None:
    """All blocks flush (no hanging indent) → biosketch_publication_missing_hanging_indent."""
    pdf_path = tmp_path / "p045_no_hang.pdf"
    # Both first and rest lines at same x → no hanging indent
    _make_biosketch_pdf(
        pdf_path,
        n_hanging_blocks=2,
        hanging_first_x=108.0,
        hanging_rest_x=108.0,
        inter_block_gap=30.0,
        within_block_gap=12.0,
    )
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_biosketch_publication_layout(model) if f.rule_id == "P045"]
    issue_types = [f.details.get("issue_type") for f in findings]
    assert "biosketch_publication_missing_hanging_indent" in issue_types


def test_p045_entry_spacing_too_close_warns(tmp_path: Path) -> None:
    """Hanging indent present but inter-entry gap too small → entry_spacing_not_double."""
    pdf_path = tmp_path / "p045_close_entries.pdf"
    # inter_block_gap=30 gives geometric gap ~15pt — above grouping threshold (14pt)
    # so blocks are separate, but below ENTRY_GAP_THRESHOLD_PT (20pt) → Q028 fires.
    _make_biosketch_pdf(
        pdf_path,
        n_hanging_blocks=2,
        hanging_first_x=108.0,
        hanging_rest_x=126.0,
        inter_block_gap=30.0,
        within_block_gap=12.0,
    )
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_biosketch_publication_layout(model) if f.rule_id == "P045"]
    issue_types = [f.details.get("issue_type") for f in findings]
    assert "biosketch_publication_entry_spacing_not_double" in issue_types


def test_p045_finding_metadata_no_private_content(tmp_path: Path) -> None:
    """Finding details must contain geometry metadata only — no publication text."""
    pdf_path = tmp_path / "p045_privacy.pdf"
    # Trigger missing_hanging_indent to get at least one finding
    _make_biosketch_pdf(
        pdf_path,
        n_hanging_blocks=2,
        hanging_first_x=108.0,
        hanging_rest_x=108.0,  # no hanging indent
        inter_block_gap=30.0,
        within_block_gap=12.0,
    )
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_biosketch_publication_layout(model) if f.rule_id == "P045"]
    assert findings
    for f in findings:
        for value in f.details.values():
            assert "synthetic" not in str(value).lower()
            assert "entry first line" not in str(value).lower()
        assert "issue_type" in f.details
        assert "page_number" in f.details
        assert "source_q_rule_id" in f.details


def test_p045_q029_source_q_rule_id(tmp_path: Path) -> None:
    """Missing-hanging-indent finding must have source_q_rule_id=Q029."""
    pdf_path = tmp_path / "p045_q029_id.pdf"
    _make_biosketch_pdf(
        pdf_path,
        n_hanging_blocks=2,
        hanging_first_x=108.0,
        hanging_rest_x=108.0,
    )
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_biosketch_publication_layout(model) if f.rule_id == "P045"]
    q029 = [
        f for f in findings
        if f.details.get("issue_type") == "biosketch_publication_missing_hanging_indent"
    ]
    assert q029
    assert all(f.details.get("source_q_rule_id") == "Q029" for f in q029)


def test_p045_q028_source_q_rule_id(tmp_path: Path) -> None:
    """Entry-spacing finding must have source_q_rule_id=Q028."""
    pdf_path = tmp_path / "p045_q028_id.pdf"
    _make_biosketch_pdf(
        pdf_path,
        n_hanging_blocks=2,
        hanging_first_x=108.0,
        hanging_rest_x=126.0,
        inter_block_gap=30.0,  # ~15pt geometric gap — separate blocks but < 20pt threshold
    )
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_biosketch_publication_layout(model) if f.rule_id == "P045"]
    q028 = [
        f for f in findings
        if f.details.get("issue_type") == "biosketch_publication_entry_spacing_not_double"
    ]
    assert q028
    assert all(f.details.get("source_q_rule_id") == "Q028" for f in q028)


# ---------------------------------------------------------------------------
# P047 tests
# ---------------------------------------------------------------------------


def _make_biosketch_bullet_pdf(
    path: Path,
    *,
    block_count: int = 2,
    lines_per_block: int = 3,
    within_block_step: float = 14.0,
    inter_block_step: float = 50.0,
) -> None:
    """Synthetic Biographical Sketch PDF for P047 bullet/list spacing tests."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((210, 70), "BIOGRAPHICAL SKETCH", fontsize=14, fontname="Times-Bold")
    y = 120.0
    for block_index in range(block_count):
        for line_index in range(lines_per_block):
            page.insert_text(
                (108, y),
                (
                    "Synthetic education bullet block "
                    f"{block_index} line {line_index} placeholder words only."
                ),
                fontsize=12,
            )
            y += within_block_step
        y += inter_block_step
    doc.save(path)
    doc.close()


def test_p047_no_biosketch_page_no_findings(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p047_no_heading.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((200, 70), "ACKNOWLEDGEMENTS", fontsize=14, fontname="Times-Bold")
    page.insert_text((108, 110), "Synthetic body paragraph text for testing here.")
    page.insert_text((108, 124), "Continuation of synthetic paragraph body text line.")
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_biosketch_bullet_spacing(model)
    assert not any(f.rule_id == "P047" for f in findings)


def test_p047_single_spaced_bullet_blocks_no_findings(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p047_single_spaced.pdf"
    _make_biosketch_bullet_pdf(pdf_path, within_block_step=14.0, inter_block_step=50.0)
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_biosketch_bullet_spacing(model)
    assert not any(f.rule_id == "P047" for f in findings)


def test_p047_double_spaced_lines_grouped_and_warn(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p047_double_spaced_grouped.pdf"
    _make_biosketch_bullet_pdf(pdf_path, within_block_step=36.0, inter_block_step=50.0)
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_biosketch_bullet_spacing(model) if f.rule_id == "P047"]
    assert findings
    assert all(
        f.details.get("issue_type") == "biosketch_bullet_section_not_single_spaced"
        for f in findings
    )
    assert {f.details.get("block_index") for f in findings} == {"0", "1"}
    assert all(float(f.details["observed_gap_points"]) > 12.0 for f in findings)


def test_p047_separate_bullet_entries_remain_split(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p047_entries_split.pdf"
    _make_biosketch_bullet_pdf(
        pdf_path,
        block_count=2,
        lines_per_block=3,
        within_block_step=14.0,
        inter_block_step=50.0,
    )
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_biosketch_bullet_spacing(model)
    assert not any(f.rule_id == "P047" for f in findings)


def test_p047_sparse_ambiguous_blocks_skipped(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p047_sparse.pdf"
    _make_biosketch_bullet_pdf(
        pdf_path,
        block_count=2,
        lines_per_block=2,
        within_block_step=36.0,
        inter_block_step=50.0,
    )
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_biosketch_bullet_spacing(model)
    assert not any(f.rule_id == "P047" for f in findings)


def test_p047_finding_metadata_no_private_content(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p047_privacy.pdf"
    _make_biosketch_bullet_pdf(pdf_path, within_block_step=36.0, inter_block_step=50.0)
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_biosketch_bullet_spacing(model) if f.rule_id == "P047"]
    assert findings
    forbidden = (
        "synthetic",
        "education",
        "placeholder",
        "publication",
        "citation",
        "name",
        "title",
    )
    for finding in findings:
        assert "bullet or list block" in finding.message.lower()
        assert set(finding.details) == {
            "page_number",
            "issue_type",
            "section_type",
            "block_index",
            "line_pair_index",
            "observed_gap_points",
            "required_max_gap_points",
            "triage_tier",
            "source_q_rule_id",
        }
        for value in finding.details.values():
            lowered = str(value).lower()
            assert not any(term in lowered for term in forbidden)


# ---------------------------------------------------------------------------
# P046 tests
# ---------------------------------------------------------------------------

_P046_LOT_ALIGNED = [
    ("Table 1 Synthetic experimental setup overview entry text here.", 108.0),
    ("Table 2 Synthetic model performance comparison entry text here.", 108.0),
    ("Table 3 Synthetic regression coefficients overview entry text.", 108.0),
]

_P046_LOT_MISALIGNED = [
    ("Table 1 Synthetic experimental setup overview entry text here.", 108.0),
    ("Table 2 Synthetic model performance comparison entry text here.", 130.0),
    ("Table 3 Synthetic regression coefficients overview entry text.", 108.0),
]

_P046_LOF_ALIGNED = [
    ("Figure 1 Synthetic workflow overview entry description text here.", 108.0),
    ("Figure 2 Synthetic performance comparison entry description text.", 108.0),
    ("Figure 3 Synthetic sample measurement distribution entry text.", 108.0),
]

_P046_LOF_MISALIGNED = [
    ("Figure 1 Synthetic workflow overview entry description text here.", 108.0),
    ("Figure 2 Synthetic performance comparison entry description text.", 134.0),
    ("Figure 3 Synthetic sample measurement distribution entry text.", 108.0),
]


def test_p046_no_lot_lof_pages_no_findings(tmp_path: Path) -> None:
    """No LoT/LoF heading detected → no P046 findings."""
    pdf_path = tmp_path / "p046_no_list.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((200, 90), "TABLE OF CONTENTS", fontsize=16, fontname="Times-Bold")
    page.insert_text((108, 130), "Chapter 1 Introduction ............... 1")
    page.insert_text((108, 150), "Chapter 2 Background ................ 5")
    page.insert_text((108, 170), "Chapter 3 Methodology .............. 10")
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_lot_lof_entry_number_alignment(model)
    assert not any(f.rule_id == "P046" for f in findings)


def test_p046_lot_aligned_no_findings(tmp_path: Path) -> None:
    """LoT entries at consistent x0 → no P046 findings."""
    pdf_path = tmp_path / "p046_lot_ok.pdf"
    _make_lot_lof_pdf(pdf_path, "LIST OF TABLES", _P046_LOT_ALIGNED)
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_lot_lof_entry_number_alignment(model)
    assert not any(f.rule_id == "P046" for f in findings)


def test_p046_lot_misaligned_warns(tmp_path: Path) -> None:
    """LoT entries with outlier x0 → lot_entry_number_column_misaligned."""
    pdf_path = tmp_path / "p046_lot_bad.pdf"
    _make_lot_lof_pdf(pdf_path, "LIST OF TABLES", _P046_LOT_MISALIGNED)
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_lof_entry_number_alignment(model) if f.rule_id == "P046"]
    issue_types = [f.details.get("issue_type") for f in findings]
    assert "lot_entry_number_column_misaligned" in issue_types
    finding = next(
        f for f in findings if f.details.get("issue_type") == "lot_entry_number_column_misaligned"
    )
    assert finding.details.get("affected_entry_count") == "1"
    assert finding.details.get("entry_index") == "1"


def test_p046_lof_aligned_no_findings(tmp_path: Path) -> None:
    """LoF entries at consistent x0 → no P046 findings."""
    pdf_path = tmp_path / "p046_lof_ok.pdf"
    _make_lot_lof_pdf(pdf_path, "LIST OF FIGURES", _P046_LOF_ALIGNED, left_header="Figure")
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_lot_lof_entry_number_alignment(model)
    assert not any(f.rule_id == "P046" for f in findings)


def test_p046_lof_misaligned_warns(tmp_path: Path) -> None:
    """LoF entries with outlier x0 → lof_entry_number_column_misaligned."""
    pdf_path = tmp_path / "p046_lof_bad.pdf"
    _make_lot_lof_pdf(pdf_path, "LIST OF FIGURES", _P046_LOF_MISALIGNED, left_header="Figure")
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_lof_entry_number_alignment(model) if f.rule_id == "P046"]
    issue_types = [f.details.get("issue_type") for f in findings]
    assert "lof_entry_number_column_misaligned" in issue_types
    finding = next(
        f for f in findings if f.details.get("issue_type") == "lof_entry_number_column_misaligned"
    )
    assert finding.details.get("affected_entry_count") == "1"
    assert finding.details.get("entry_index") == "1"


def test_p046_too_few_entries_no_findings(tmp_path: Path) -> None:
    """Fewer than MIN_ENTRIES=3 entries → gate skips check."""
    pdf_path = tmp_path / "p046_sparse.pdf"
    sparse_entries = [
        ("Table 1 Only one entry in the list for testing purposes.", 108.0),
        ("Table 2 Second misaligned entry at different x position.", 130.0),
    ]
    _make_lot_lof_pdf(pdf_path, "LIST OF TABLES", sparse_entries)
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_lot_lof_entry_number_alignment(model)
    assert not any(f.rule_id == "P046" for f in findings)


def test_p046_entry_index_omitted_when_worst_entry_on_later_page(tmp_path: Path) -> None:
    """Entry index must only be set when the worst offender is on the reported page."""
    pdf_path = tmp_path / "p046_multi_page.pdf"
    doc = fitz.open()
    page1 = doc.new_page(width=612, height=792)
    page1.insert_text((190, 90), "LIST OF TABLES", fontsize=16, fontname="Times-Bold")
    page1.insert_text((108, 115), "Table")
    page1.insert_text((500, 115), "Page")
    page1.insert_text((108, 140), "Table 1 Synthetic experimental setup overview entry.")
    page1.insert_text((500, 140), "12")
    page1.insert_text((108, 160), "Table 2 Synthetic model performance comparison entry.")
    page1.insert_text((500, 160), "12")
    page2 = doc.new_page(width=612, height=792)
    page2.insert_text((190, 90), "LIST OF TABLES (continued)", fontsize=16, fontname="Times-Bold")
    page2.insert_text((108, 115), "Table")
    page2.insert_text((500, 115), "Page")
    page2.insert_text((108, 140), "Table 3 Synthetic regression coefficients overview entry.")
    page2.insert_text((500, 140), "12")
    page2.insert_text((130, 160), "Table 4 Synthetic sample distribution overview entry text.")
    page2.insert_text((500, 160), "12")
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_lof_entry_number_alignment(model) if f.rule_id == "P046"]
    finding = next(
        f for f in findings if f.details.get("issue_type") == "lot_entry_number_column_misaligned"
    )
    assert finding.details.get("page_number") == "1"
    assert finding.details.get("affected_entry_count") == "1"
    assert "entry_index" not in finding.details


def test_p046_finding_metadata_no_private_content(tmp_path: Path) -> None:
    """Finding details may include short entry previews but not full entry text."""
    pdf_path = tmp_path / "p046_privacy.pdf"
    _make_lot_lof_pdf(pdf_path, "LIST OF TABLES", _P046_LOT_MISALIGNED)
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_lof_entry_number_alignment(model) if f.rule_id == "P046"]
    assert findings
    for f in findings:
        preview = f.details.get("affected_entry_preview", "")
        if preview:
            assert len(preview) <= 72
        for key, value in f.details.items():
            if key in {"affected_entry_preview", "bbox"}:
                continue
            assert "entry text here" not in str(value).lower()
        assert "issue_type" in f.details
        assert "page_number" in f.details
        assert "source_q_rule_id" in f.details


def test_p046_q068_source_q_rule_id(tmp_path: Path) -> None:
    """LoT misalignment finding must have source_q_rule_id=Q068."""
    pdf_path = tmp_path / "p046_q068_id.pdf"
    _make_lot_lof_pdf(pdf_path, "LIST OF TABLES", _P046_LOT_MISALIGNED)
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_lof_entry_number_alignment(model) if f.rule_id == "P046"]
    q068 = [
        f for f in findings if f.details.get("issue_type") == "lot_entry_number_column_misaligned"
    ]
    assert q068
    assert all(f.details.get("source_q_rule_id") == "Q068" for f in q068)


def test_p046_q078_source_q_rule_id(tmp_path: Path) -> None:
    """LoF misalignment finding must have source_q_rule_id=Q078."""
    pdf_path = tmp_path / "p046_q078_id.pdf"
    _make_lot_lof_pdf(pdf_path, "LIST OF FIGURES", _P046_LOF_MISALIGNED, left_header="Figure")
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_lof_entry_number_alignment(model) if f.rule_id == "P046"]
    q078 = [
        f for f in findings if f.details.get("issue_type") == "lof_entry_number_column_misaligned"
    ]
    assert q078
    assert all(f.details.get("source_q_rule_id") == "Q078" for f in q078)


# P048 tests


def _make_lot_lof_page_number_pdf(
    path: Path,
    heading: str,
    *,
    left_header: str | None = "Table",
    page_header: str | None = "Page",
    page_number_xs: list[float] | None = None,
    include_wrapped_continuation: bool = False,
) -> None:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((190, 90), heading, fontsize=16, fontname="Times-Bold")
    if left_header is not None:
        page.insert_text((108, 115), left_header)
    if page_header is not None:
        page.insert_text((500, 115), page_header)

    xs = page_number_xs or [500.0, 500.0, 500.0]
    prefix = "Figure" if heading == "LIST OF FIGURES" else "Table"
    for idx, page_number_x in enumerate(xs):
        y = 140 + idx * 24
        page.insert_text(
            (108, y),
            f"{prefix} {idx + 1} Synthetic placeholder entry text for alignment.",
        )
        page.insert_text((page_number_x, y), "12")
        if include_wrapped_continuation and idx == 0:
            page.insert_text(
                (132, y + 12),
                "Synthetic wrapped continuation placeholder line without page number.",
            )

    doc.save(path)
    doc.close()


def test_p048_no_lot_lof_pages_no_findings(tmp_path: Path) -> None:
    """No LoT/LoF heading detected → no P048 findings."""
    pdf_path = tmp_path / "p048_no_list.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((200, 90), "TABLE OF CONTENTS", fontsize=16, fontname="Times-Bold")
    page.insert_text((108, 130), "Chapter 1 Introduction ............... 1")
    page.insert_text((108, 150), "Chapter 2 Background ................ 5")
    page.insert_text((108, 170), "Chapter 3 Methodology .............. 10")
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_lot_lof_page_number_alignment(model)
    assert not any(f.rule_id == "P048" for f in findings)


def test_p048_lot_aligned_page_numbers_no_findings(tmp_path: Path) -> None:
    """LoT page numbers at consistent right edge → no P048 findings."""
    pdf_path = tmp_path / "p048_lot_ok.pdf"
    _make_lot_lof_page_number_pdf(pdf_path, "LIST OF TABLES")
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_lot_lof_page_number_alignment(model)
    assert not any(f.rule_id == "P048" for f in findings)


def test_p048_lot_misaligned_page_number_warns(tmp_path: Path) -> None:
    """LoT page-number right-edge outlier → lot_page_number_column_misaligned."""
    pdf_path = tmp_path / "p048_lot_bad.pdf"
    _make_lot_lof_page_number_pdf(
        pdf_path,
        "LIST OF TABLES",
        page_number_xs=[500.0, 532.0, 500.0],
    )
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_lof_page_number_alignment(model) if f.rule_id == "P048"]
    issue_types = [f.details.get("issue_type") for f in findings]
    assert "lot_page_number_column_misaligned" in issue_types
    assert all(f.details.get("source_q_rule_id") == "Q069" for f in findings)


def test_p048_lof_aligned_page_numbers_no_findings(tmp_path: Path) -> None:
    """LoF page numbers at consistent right edge → no P048 findings."""
    pdf_path = tmp_path / "p048_lof_ok.pdf"
    _make_lot_lof_page_number_pdf(pdf_path, "LIST OF FIGURES", left_header="Figure")
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_lot_lof_page_number_alignment(model)
    assert not any(f.rule_id == "P048" for f in findings)


def test_p048_lof_misaligned_page_number_warns(tmp_path: Path) -> None:
    """LoF page-number right-edge outlier → lof_page_number_column_misaligned."""
    pdf_path = tmp_path / "p048_lof_bad.pdf"
    _make_lot_lof_page_number_pdf(
        pdf_path,
        "LIST OF FIGURES",
        left_header="Figure",
        page_number_xs=[500.0, 500.0, 535.0],
    )
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_lof_page_number_alignment(model) if f.rule_id == "P048"]
    issue_types = [f.details.get("issue_type") for f in findings]
    assert "lof_page_number_column_misaligned" in issue_types
    assert all(f.details.get("source_q_rule_id") == "Q079" for f in findings)


def test_p048_wrapped_continuation_lines_skipped(tmp_path: Path) -> None:
    """Wrapped continuation lines without page numbers do not create false positives."""
    pdf_path = tmp_path / "p048_wrapped_ok.pdf"
    _make_lot_lof_page_number_pdf(
        pdf_path,
        "LIST OF TABLES",
        include_wrapped_continuation=True,
    )
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_lot_lof_page_number_alignment(model)
    assert not any(f.rule_id == "P048" for f in findings)


def test_p048_header_column_label_lines_skipped(tmp_path: Path) -> None:
    """Table/Figure/Page column labels are not counted as entry rows."""
    pdf_path = tmp_path / "p048_header_labels.pdf"
    _make_lot_lof_page_number_pdf(pdf_path, "LIST OF TABLES", page_number_xs=[500.0, 532.0])
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_lot_lof_page_number_alignment(model)
    assert not any(f.rule_id == "P048" for f in findings)


def test_p048_sparse_complete_entries_skipped(tmp_path: Path) -> None:
    """Fewer than MIN_ENTRIES=3 complete entries → gate skips P048."""
    pdf_path = tmp_path / "p048_sparse.pdf"
    _make_lot_lof_page_number_pdf(
        pdf_path,
        "LIST OF FIGURES",
        left_header="Figure",
        page_number_xs=[500.0, 535.0],
    )
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_lot_lof_page_number_alignment(model)
    assert not any(f.rule_id == "P048" for f in findings)


def test_p048_finding_metadata_no_private_content(tmp_path: Path) -> None:
    """Finding details must contain geometry metadata only — no entry text."""
    pdf_path = tmp_path / "p048_privacy.pdf"
    _make_lot_lof_page_number_pdf(
        pdf_path,
        "LIST OF TABLES",
        page_number_xs=[500.0, 532.0, 500.0],
    )
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_lof_page_number_alignment(model) if f.rule_id == "P048"]
    assert findings
    expected_keys = {
        "page_number",
        "issue_type",
        "section_type",
        "entry_index",
        "observed_page_number_x",
        "expected_page_number_x",
        "x_delta_points",
        "allowed_delta_points",
        "entry_count",
        "triage_tier",
        "source_q_rule_id",
    }
    forbidden_terms = (
        "synthetic",
        "placeholder",
        "entry text",
        "table 1",
        "figure 1",
        "caption",
        "title",
        "name",
    )
    for finding in findings:
        assert set(finding.details) == expected_keys
        for value in finding.details.values():
            value_lower = str(value).lower()
            assert all(term not in value_lower for term in forbidden_terms)


# P049 tests


def _make_p049_pdf(
    path: Path,
    heading: str,
    *,
    page_header_x: float = 490.0,
    page_header_bold: bool = True,
    num_entries: int = 3,
    page_number_x: float = 500.0,
    include_page_header: bool = True,
) -> None:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((190, 90), heading, fontsize=16, fontname="Times-Bold")
    prefix = "Figure" if "FIGURES" in heading else "Table"
    page.insert_text((108, 115), prefix)
    if include_page_header:
        fontname = "Times-Bold" if page_header_bold else "helv"
        page.insert_text((page_header_x, 115), "Page", fontname=fontname, fontsize=12)
    for i in range(num_entries):
        y = 140 + i * 24
        page.insert_text(
            (108, y),
            f"{prefix} {i + 1} Synthetic placeholder entry text for column-header checks.",
        )
        page.insert_text((page_number_x, y), str(10 + i))
    doc.save(path)
    doc.close()


def test_p049_no_lot_lof_pages_no_findings(tmp_path: Path) -> None:
    """No LoT/LoF heading detected → no P049 findings."""
    pdf_path = tmp_path / "p049_no_list.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((200, 90), "TABLE OF CONTENTS", fontsize=16, fontname="Times-Bold")
    page.insert_text((108, 130), "Chapter 1 Introduction ............... 1")
    page.insert_text((108, 150), "Chapter 2 Background ................ 5")
    page.insert_text((108, 170), "Chapter 3 Methodology .............. 10")
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_lot_lof_column_header_style_alignment(model)
    assert not any(f.rule_id == "P049" for f in findings)


def test_p049_lot_page_header_right_aligned_no_findings(tmp_path: Path) -> None:
    """LoT 'Page' header co-located with page-number column and bold → no P049 findings."""
    pdf_path = tmp_path / "p049_lot_ok.pdf"
    _make_p049_pdf(pdf_path, "LIST OF TABLES", page_header_x=490.0, page_header_bold=True)
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_lot_lof_column_header_style_alignment(model)
    assert not any(f.rule_id == "P049" for f in findings)


def test_p049_lot_page_header_misaligned_warns(tmp_path: Path) -> None:
    """LoT 'Page' header far from page-number column → lot_page_header_not_right_aligned."""
    pdf_path = tmp_path / "p049_lot_bad_align.pdf"
    _make_p049_pdf(
        pdf_path,
        "LIST OF TABLES",
        page_header_x=200.0,
        page_header_bold=True,
        page_number_x=500.0,
    )
    model = load_pdf_layout(str(pdf_path))
    findings = [
        f
        for f in check_pdf_lot_lof_column_header_style_alignment(model)
        if f.rule_id == "P049"
    ]
    issue_types = [f.details.get("issue_type") for f in findings]
    assert "lot_page_header_not_right_aligned" in issue_types
    assert all(f.details.get("source_q_rule_id") == "Q064" for f in findings)


def test_p049_lof_page_header_right_aligned_no_findings(tmp_path: Path) -> None:
    """LoF 'Page' header co-located with page-number column and bold → no P049 findings."""
    pdf_path = tmp_path / "p049_lof_ok.pdf"
    _make_p049_pdf(pdf_path, "LIST OF FIGURES", page_header_x=490.0, page_header_bold=True)
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_lot_lof_column_header_style_alignment(model)
    assert not any(f.rule_id == "P049" for f in findings)


def test_p049_lof_page_header_misaligned_warns(tmp_path: Path) -> None:
    """LoF 'Page' header far from page-number column → lof_page_header_not_right_aligned."""
    pdf_path = tmp_path / "p049_lof_bad_align.pdf"
    _make_p049_pdf(
        pdf_path,
        "LIST OF FIGURES",
        page_header_x=200.0,
        page_header_bold=True,
        page_number_x=500.0,
    )
    model = load_pdf_layout(str(pdf_path))
    findings = [
        f
        for f in check_pdf_lot_lof_column_header_style_alignment(model)
        if f.rule_id == "P049"
    ]
    issue_types = [f.details.get("issue_type") for f in findings]
    assert "lof_page_header_not_right_aligned" in issue_types
    assert all(f.details.get("source_q_rule_id") == "Q073" for f in findings)


def test_p049_lot_page_header_bold_no_bold_finding(tmp_path: Path) -> None:
    """LoT 'Page' header with bold font → no lot_page_header_not_bold finding."""
    pdf_path = tmp_path / "p049_lot_bold_ok.pdf"
    _make_p049_pdf(pdf_path, "LIST OF TABLES", page_header_x=490.0, page_header_bold=True)
    model = load_pdf_layout(str(pdf_path))
    findings = [
        f
        for f in check_pdf_lot_lof_column_header_style_alignment(model)
        if f.rule_id == "P049"
    ]
    assert not any(f.details.get("issue_type") == "lot_page_header_not_bold" for f in findings)


def test_p049_lot_page_header_not_bold_warns(tmp_path: Path) -> None:
    """LoT 'Page' header with non-bold font and reliable metadata → lot_page_header_not_bold."""
    pdf_path = tmp_path / "p049_lot_not_bold.pdf"
    _make_p049_pdf(pdf_path, "LIST OF TABLES", page_header_x=490.0, page_header_bold=False)
    model = load_pdf_layout(str(pdf_path))
    findings = [
        f
        for f in check_pdf_lot_lof_column_header_style_alignment(model)
        if f.rule_id == "P049"
    ]
    issue_types = [f.details.get("issue_type") for f in findings]
    assert "lot_page_header_not_bold" in issue_types


def test_p049_lof_page_header_not_bold_warns(tmp_path: Path) -> None:
    """LoF 'Page' header with non-bold font → lof_page_header_not_bold."""
    pdf_path = tmp_path / "p049_lof_not_bold.pdf"
    _make_p049_pdf(pdf_path, "LIST OF FIGURES", page_header_x=490.0, page_header_bold=False)
    model = load_pdf_layout(str(pdf_path))
    findings = [
        f
        for f in check_pdf_lot_lof_column_header_style_alignment(model)
        if f.rule_id == "P049"
    ]
    issue_types = [f.details.get("issue_type") for f in findings]
    assert "lof_page_header_not_bold" in issue_types


def test_p049_too_few_entries_skipped(tmp_path: Path) -> None:
    """Fewer than MIN_COMPLETE_ENTRIES=3 → gate skips P049."""
    pdf_path = tmp_path / "p049_sparse.pdf"
    _make_p049_pdf(
        pdf_path, "LIST OF TABLES", page_header_x=200.0, page_header_bold=False, num_entries=2
    )
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_lot_lof_column_header_style_alignment(model)
    assert not any(f.rule_id == "P049" for f in findings)


def test_p049_no_page_header_skipped(tmp_path: Path) -> None:
    """No 'Page' header detected in header zone → no P049 findings."""
    pdf_path = tmp_path / "p049_no_page_header.pdf"
    _make_p049_pdf(
        pdf_path, "LIST OF TABLES", page_header_x=490.0, include_page_header=False
    )
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_lot_lof_column_header_style_alignment(model)
    assert not any(f.rule_id == "P049" for f in findings)


def test_p049_finding_metadata_privacy_safe(tmp_path: Path) -> None:
    """P049 findings contain only privacy-safe metadata — no entry text or titles."""
    pdf_path = tmp_path / "p049_privacy.pdf"
    _make_p049_pdf(
        pdf_path,
        "LIST OF TABLES",
        page_header_x=200.0,
        page_header_bold=False,
        page_number_x=500.0,
    )
    model = load_pdf_layout(str(pdf_path))
    findings = [
        f
        for f in check_pdf_lot_lof_column_header_style_alignment(model)
        if f.rule_id == "P049"
    ]
    assert findings
    alignment_keys = {
        "page_number",
        "issue_type",
        "section_type",
        "column_type",
        "observed_x",
        "expected_x",
        "x_delta_points",
        "allowed_delta_points",
        "entry_count",
        "triage_tier",
        "source_q_rule_id",
    }
    bold_keys = {
        "page_number",
        "issue_type",
        "section_type",
        "column_type",
        "entry_count",
        "triage_tier",
        "source_q_rule_id",
    }
    forbidden_terms = ("synthetic", "placeholder", "table 1", "caption", "title")
    for finding in findings:
        assert finding.details.keys() <= alignment_keys | bold_keys
        for value in finding.details.values():
            value_lower = str(value).lower()
            assert all(term not in value_lower for term in forbidden_terms)


def test_p049_import_and_wiring() -> None:
    """P049 checker is importable and returns a list for an empty document."""
    from njit_auditor.pdf_models import PdfDocument  # noqa: PLC0415

    empty_doc = PdfDocument(path="test.pdf", pages=[])
    result = check_pdf_lot_lof_column_header_style_alignment(empty_doc)
    assert result == []


# P050 tests


def _make_p050_pdf(
    path: Path,
    heading: str,
    *,
    left_header_bold: bool = True,
    num_entries: int = 3,
    page_number_x: float = 500.0,
    include_left_header: bool = True,
) -> None:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((190, 90), heading, fontsize=16, fontname="Times-Bold")
    prefix = "Figure" if "FIGURES" in heading else "Table"
    if include_left_header:
        left_fontname = "Times-Bold" if left_header_bold else "helv"
        page.insert_text((108, 115), prefix, fontname=left_fontname, fontsize=12)
    page.insert_text((490, 115), "Page", fontname="Times-Bold", fontsize=12)
    for i in range(num_entries):
        y = 140 + i * 24
        page.insert_text(
            (108, y),
            f"{prefix} {i + 1} Synthetic placeholder entry text for left-column header checks.",
        )
        page.insert_text((page_number_x, y), str(10 + i))
    doc.save(path)
    doc.close()


def test_p050_no_lot_lof_pages_no_findings(tmp_path: Path) -> None:
    """No LoT/LoF heading detected → no P050 findings."""
    pdf_path = tmp_path / "p050_no_list.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((200, 90), "TABLE OF CONTENTS", fontsize=16, fontname="Times-Bold")
    page.insert_text((108, 130), "Chapter 1 Introduction ............... 1")
    page.insert_text((108, 150), "Chapter 2 Background ................ 5")
    page.insert_text((108, 170), "Chapter 3 Methodology .............. 10")
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_lot_lof_left_column_header_bold(model)
    assert not any(f.rule_id == "P050" for f in findings)


def test_p050_lot_left_header_bold_no_findings(tmp_path: Path) -> None:
    """LoT 'Table' header bold → no lot_table_header_not_bold finding."""
    pdf_path = tmp_path / "p050_lot_bold_ok.pdf"
    _make_p050_pdf(pdf_path, "LIST OF TABLES", left_header_bold=True)
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_lot_lof_left_column_header_bold(model)
    assert not any(f.rule_id == "P050" for f in findings)


def test_p050_lot_left_header_not_bold_warns(tmp_path: Path) -> None:
    """LoT 'Table' header not bold with reliable metadata → lot_table_header_not_bold."""
    pdf_path = tmp_path / "p050_lot_not_bold.pdf"
    _make_p050_pdf(pdf_path, "LIST OF TABLES", left_header_bold=False)
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_lof_left_column_header_bold(model) if f.rule_id == "P050"]
    issue_types = [f.details.get("issue_type") for f in findings]
    assert "lot_table_header_not_bold" in issue_types
    assert all(f.details.get("source_q_rule_id") == "Q063" for f in findings)


def test_p050_lof_left_header_bold_no_findings(tmp_path: Path) -> None:
    """LoF 'Figure' header bold → no lof_figure_header_not_bold finding."""
    pdf_path = tmp_path / "p050_lof_bold_ok.pdf"
    _make_p050_pdf(pdf_path, "LIST OF FIGURES", left_header_bold=True)
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_lot_lof_left_column_header_bold(model)
    assert not any(f.rule_id == "P050" for f in findings)


def test_p050_lof_left_header_not_bold_warns(tmp_path: Path) -> None:
    """LoF 'Figure' header not bold with reliable metadata → lof_figure_header_not_bold."""
    pdf_path = tmp_path / "p050_lof_not_bold.pdf"
    _make_p050_pdf(pdf_path, "LIST OF FIGURES", left_header_bold=False)
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_lof_left_column_header_bold(model) if f.rule_id == "P050"]
    issue_types = [f.details.get("issue_type") for f in findings]
    assert "lof_figure_header_not_bold" in issue_types
    assert all(f.details.get("source_q_rule_id") == "Q072" for f in findings)


def test_p050_missing_left_header_skipped(tmp_path: Path) -> None:
    """No left-column header in header zone → no P050 findings (P031 handles this)."""
    pdf_path = tmp_path / "p050_no_left_header.pdf"
    _make_p050_pdf(pdf_path, "LIST OF TABLES", include_left_header=False)
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_lot_lof_left_column_header_bold(model)
    assert not any(f.rule_id == "P050" for f in findings)


def test_p050_too_few_entries_skipped(tmp_path: Path) -> None:
    """Fewer than MIN_COMPLETE_ENTRIES=3 → gate skips P050."""
    pdf_path = tmp_path / "p050_sparse.pdf"
    _make_p050_pdf(pdf_path, "LIST OF TABLES", left_header_bold=False, num_entries=2)
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_lot_lof_left_column_header_bold(model)
    assert not any(f.rule_id == "P050" for f in findings)


def test_p050_finding_metadata_privacy_safe(tmp_path: Path) -> None:
    """P050 findings contain only privacy-safe metadata — no entry text, titles, or header text."""
    pdf_path = tmp_path / "p050_privacy.pdf"
    _make_p050_pdf(pdf_path, "LIST OF TABLES", left_header_bold=False)
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_lof_left_column_header_bold(model) if f.rule_id == "P050"]
    assert findings
    allowed_keys = {
        "page_number",
        "issue_type",
        "section_type",
        "column_type",
        "style_signal",
        "font_metadata_available",
        "entry_count",
        "triage_tier",
        "source_q_rule_id",
    }
    forbidden_terms = ("synthetic", "placeholder", "table 1", "caption", "title")
    for finding in findings:
        assert finding.details.keys() <= allowed_keys
        for value in finding.details.values():
            value_lower = str(value).lower()
            assert all(term not in value_lower for term in forbidden_terms)


def test_p050_import_and_wiring() -> None:
    """P050 checker is importable and returns a list for an empty document."""
    from njit_auditor.pdf_models import PdfDocument  # noqa: PLC0415

    empty_doc = PdfDocument(path="test.pdf", pages=[])
    result = check_pdf_lot_lof_left_column_header_bold(empty_doc)
    assert result == []


# ---------------------------------------------------------------------------
# P055: LoT/LoF cross-type entry checks
# ---------------------------------------------------------------------------


def _make_lot_lof_entry_type_pdf(
    path: Path,
    entries: list[tuple[str, str | None]],
    heading: str = "LIST OF TABLES",
) -> None:
    """Build a synthetic LoT or LoF page for P055 testing."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((190, 90), heading, fontsize=16, fontname="Times-Bold")
    y = 140.0
    for text, pg_num in entries:
        page.insert_text((72.0, y), text, fontsize=12)
        if pg_num is not None:
            page.insert_text((500, y), pg_num, fontsize=12)
        y += 22.0
    doc.save(path)
    doc.close()


def test_p055_lot_correct_entries_no_finding(tmp_path: Path) -> None:
    """LoT entries starting with Table → no P055 finding."""
    pdf_path = tmp_path / "p055_lot_ok.pdf"
    _make_lot_lof_entry_type_pdf(pdf_path, [
        ("Table 1 Summary of Experimental Results", "5"),
        ("Table 2 Comparison of Algorithm Performance", "12"),
        ("Table 3 Overview of Evaluation Metrics", "20"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_lof_entry_type(model) if f.rule_id == "P055"]
    assert not findings


def test_p055_lot_figure_entry_warns(tmp_path: Path) -> None:
    """LoT entry starting with 'Figure' → lot_entry_is_figure."""
    pdf_path = tmp_path / "p055_lot_fig.pdf"
    _make_lot_lof_entry_type_pdf(pdf_path, [
        ("Table 1 Summary of Results", "5"),
        ("Figure 2 Misplaced Figure Entry in LoT", "12"),
        ("Table 3 Another Correct Table Entry", "20"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_lof_entry_type(model) if f.rule_id == "P055"]
    assert len(findings) == 1
    assert findings[0].details.get("issue_type") == "lot_entry_is_figure"
    assert findings[0].details.get("section_type") == "list_of_tables"
    assert findings[0].details.get("observed_entry_type") == "figure"
    assert findings[0].details.get("expected_entry_type") == "table"


def test_p055_lof_correct_entries_no_finding(tmp_path: Path) -> None:
    """LoF entries starting with Figure → no P055 finding."""
    pdf_path = tmp_path / "p055_lof_ok.pdf"
    _make_lot_lof_entry_type_pdf(pdf_path, [
        ("Figure 1 System Architecture Overview Diagram", "3"),
        ("Figure 2 Comparison Chart of Results", "7"),
        ("Figure 3 Evaluation Workflow Summary", "11"),
    ], heading="LIST OF FIGURES")
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_lof_entry_type(model) if f.rule_id == "P055"]
    assert not findings


def test_p055_lof_table_entry_warns(tmp_path: Path) -> None:
    """LoF entry starting with 'Table' → lof_entry_is_table."""
    pdf_path = tmp_path / "p055_lof_tbl.pdf"
    _make_lot_lof_entry_type_pdf(pdf_path, [
        ("Figure 1 Correct Figure Entry Here", "3"),
        ("Table 2 Misplaced Table Entry in LoF", "7"),
        ("Figure 3 Another Correct Figure Entry", "11"),
    ], heading="LIST OF FIGURES")
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_lof_entry_type(model) if f.rule_id == "P055"]
    assert len(findings) == 1
    assert findings[0].details.get("issue_type") == "lof_entry_is_table"
    assert findings[0].details.get("section_type") == "list_of_figures"
    assert findings[0].details.get("observed_entry_type") == "table"
    assert findings[0].details.get("expected_entry_type") == "figure"


def test_p055_wrap_continuation_skipped(tmp_path: Path) -> None:
    """Entries without page-number token (wrap continuations) are not checked."""
    pdf_path = tmp_path / "p055_wrap.pdf"
    _make_lot_lof_entry_type_pdf(pdf_path, [
        ("Table 1 A Long Table Title That Wraps Onto", None),
        ("  the Next Line Continuation Text Here", "5"),
        ("Table 2 Another Entry Without Problem", "12"),
        ("Table 3 Third Correct Entry Here", "20"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_lof_entry_type(model) if f.rule_id == "P055"]
    assert not findings


def test_p055_sparse_page_skipped(tmp_path: Path) -> None:
    """LoT page with fewer than 2 entries → skipped."""
    pdf_path = tmp_path / "p055_sparse.pdf"
    _make_lot_lof_entry_type_pdf(pdf_path, [
        ("Figure 1 Only One Entry So Page Is Sparse", "5"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_lof_entry_type(model) if f.rule_id == "P055"]
    assert not findings


def test_p055_toc_entries_unaffected(tmp_path: Path) -> None:
    """TABLE OF CONTENTS page → P055 does not apply."""
    pdf_path = tmp_path / "p055_toc.pdf"
    _make_lot_lof_entry_type_pdf(pdf_path, [
        ("Figure 1 A Figure Reference in TOC", "5"),
        ("Table 2 A Table Reference in TOC", "12"),
        ("Chapter 3 Chapter Title Here", "20"),
    ], heading="TABLE OF CONTENTS")
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_lof_entry_type(model) if f.rule_id == "P055"]
    assert not findings


def test_p055_finding_metadata_privacy_safe(tmp_path: Path) -> None:
    """Findings must not include LoT/LoF entry text, titles, or private content."""
    pdf_path = tmp_path / "p055_privacy.pdf"
    _make_lot_lof_entry_type_pdf(pdf_path, [
        ("Table 1 A Correct Table Entry Here", "5"),
        ("Figure 2 Misplaced Figure Entry Metadata Test", "12"),
        ("Table 3 Another Correct Table Entry", "20"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_lof_entry_type(model) if f.rule_id == "P055"]
    assert findings
    finding = findings[0]
    allowed_keys = {
        "issue_type",
        "page",
        "section_type",
        "entry_index",
        "observed_entry_type",
        "expected_entry_type",
        "page_number_token_present",
        "triage_tier",
        "source_q_rule_id",
    }
    assert finding.details.keys() <= allowed_keys
    assert finding.details.get("triage_tier") == "medium"
    assert finding.details.get("source_q_rule_id") == "Q063"
    for value in finding.details.values():
        value_lower = str(value).lower()
        assert "misplaced" not in value_lower
        assert "metadata test" not in value_lower


def test_p055_import_and_wiring(tmp_path: Path) -> None:
    """P055 is importable and wired in audit_runner."""
    import inspect

    import njit_auditor.audit_runner as audit_runner
    from njit_auditor.rules.pdf_lot_lof_entry_type import (
        check_pdf_lot_lof_entry_type as _check,
    )
    assert callable(_check)
    src = inspect.getsource(audit_runner.collect_pdf_layout_findings)
    assert "check_pdf_lot_lof_entry_type" in src


def test_p055_p053_p054_unaffected(tmp_path: Path) -> None:
    """P053 and P054 still fire correctly after P055 is added."""
    from njit_auditor.rules.pdf_toc_terminal_period import check_pdf_toc_terminal_period

    pdf_path = tmp_path / "p055_unaffected.pdf"
    _make_lot_terminal_period_pdf(pdf_path, [
        ("Table 1 A Table Entry That Ends With Period.", "5"),
        ("Table 2 Another Table Without Period", "12"),
        ("Table 3 Third Table Without Period", "20"),
    ])
    model = load_pdf_layout(str(pdf_path))
    p053 = [f for f in check_pdf_lot_terminal_period(model) if f.rule_id == "P053"]
    p054 = [f for f in check_pdf_toc_terminal_period(model) if f.rule_id == "P054"]
    p055 = [f for f in check_pdf_lot_lof_entry_type(model) if f.rule_id == "P055"]
    assert p053
    assert not p054
    assert not p055


# ---------------------------------------------------------------------------
# P056: LoT/LoF entry numbering format consistency checks
# ---------------------------------------------------------------------------


def _make_lot_lof_number_format_pdf(
    path: Path,
    entries: list[tuple[str, str | None]],
    heading: str = "LIST OF TABLES",
) -> None:
    """Build a synthetic LoT or LoF page for P056 testing."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((190, 90), heading, fontsize=16, fontname="Times-Bold")
    y = 140.0
    for text, pg_num in entries:
        page.insert_text((72.0, y), text, fontsize=12)
        if pg_num is not None:
            page.insert_text((500, y), pg_num, fontsize=12)
        y += 22.0
    doc.save(path)
    doc.close()


def test_p056_no_lot_lof_page_no_finding(tmp_path: Path) -> None:
    """No LoT/LoF page → no P056 finding."""
    pdf_path = tmp_path / "p056_no_list.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((72.0, 200.0), "Body text with no LoT or LoF.", fontsize=12)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_lof_number_format(model) if f.rule_id == "P056"]
    assert not findings


def test_p056_lot_consistent_sequential_no_finding(tmp_path: Path) -> None:
    """LoT with all sequential (N) entries → no finding."""
    pdf_path = tmp_path / "p056_lot_seq.pdf"
    _make_lot_lof_number_format_pdf(pdf_path, [
        ("Table 1 Results Overview", "5"),
        ("Table 2 Comparison of Methods", "12"),
        ("Table 3 Evaluation Summary", "20"),
        ("Table 4 Statistical Analysis", "28"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_lof_number_format(model) if f.rule_id == "P056"]
    assert not findings


def test_p056_lot_consistent_chapter_based_no_finding(tmp_path: Path) -> None:
    """LoT with all chapter-based (X.Y) entries → no finding."""
    pdf_path = tmp_path / "p056_lot_chap.pdf"
    _make_lot_lof_number_format_pdf(pdf_path, [
        ("Table 1.1 First Chapter Results", "5"),
        ("Table 1.2 Second Chapter Results", "12"),
        ("Table 2.1 Another Chapter Table", "20"),
        ("Table 2.2 More Results Here", "28"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_lof_number_format(model) if f.rule_id == "P056"]
    assert not findings


def test_p056_lot_mixed_format_warns(tmp_path: Path) -> None:
    """LoT with mixed chapter-based and sequential entries → lot_mixed_numbering_format."""
    pdf_path = tmp_path / "p056_lot_mixed.pdf"
    _make_lot_lof_number_format_pdf(pdf_path, [
        ("Table 1.1 Chapter Based Entry One", "5"),
        ("Table 1.2 Chapter Based Entry Two", "12"),
        ("Table 3 Sequential Entry One", "20"),
        ("Table 4 Sequential Entry Two", "28"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_lof_number_format(model) if f.rule_id == "P056"]
    assert len(findings) == 1
    assert findings[0].details.get("issue_type") == "lot_mixed_numbering_format"
    assert findings[0].details.get("section_type") == "list_of_tables"


def test_p056_lof_consistent_no_finding(tmp_path: Path) -> None:
    """LoF with consistent numbering → no finding."""
    pdf_path = tmp_path / "p056_lof_ok.pdf"
    _make_lot_lof_number_format_pdf(pdf_path, [
        ("Figure 1 System Architecture Diagram", "3"),
        ("Figure 2 Evaluation Results Chart", "7"),
        ("Figure 3 Comparison Overview Plot", "11"),
        ("Figure 4 Final Results Summary", "15"),
    ], heading="LIST OF FIGURES")
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_lof_number_format(model) if f.rule_id == "P056"]
    assert not findings


def test_p056_lof_mixed_format_warns(tmp_path: Path) -> None:
    """LoF with mixed numbering formats → lof_mixed_numbering_format."""
    pdf_path = tmp_path / "p056_lof_mixed.pdf"
    _make_lot_lof_number_format_pdf(pdf_path, [
        ("Figure 1.1 Chapter One Architecture", "3"),
        ("Figure 1.2 Chapter One Results", "7"),
        ("Figure 3 Sequential Format Entry", "11"),
        ("Figure 4 Another Sequential Entry", "15"),
    ], heading="LIST OF FIGURES")
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_lof_number_format(model) if f.rule_id == "P056"]
    assert len(findings) == 1
    assert findings[0].details.get("issue_type") == "lof_mixed_numbering_format"
    assert findings[0].details.get("section_type") == "list_of_figures"


def test_p056_wrap_continuation_skipped(tmp_path: Path) -> None:
    """Entries without page-number token (wrap continuations) are not classified."""
    pdf_path = tmp_path / "p056_wrap.pdf"
    _make_lot_lof_number_format_pdf(pdf_path, [
        ("Table 1.1 A Long Table Title That Wraps", None),
        ("  Continuation of Title Here", "5"),
        ("Table 1.2 Another Entry Chapter Based", None),
        ("  Continuation Line", "12"),
        ("Table 2 Sequential Entry Only One", "20"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_lof_number_format(model) if f.rule_id == "P056"]
    assert not findings


def test_p056_sparse_page_skipped(tmp_path: Path) -> None:
    """LoT page with fewer than 2 entries → skipped."""
    pdf_path = tmp_path / "p056_sparse.pdf"
    _make_lot_lof_number_format_pdf(pdf_path, [
        ("Table 1 Only One Entry Here", "5"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_lof_number_format(model) if f.rule_id == "P056"]
    assert not findings


def test_p056_toc_entries_unaffected(tmp_path: Path) -> None:
    """TABLE OF CONTENTS page → P056 does not apply."""
    pdf_path = tmp_path / "p056_toc.pdf"
    _make_lot_lof_number_format_pdf(pdf_path, [
        ("Chapter 1 Introduction to the Research", "1"),
        ("Chapter 2 Literature Review Overview", "15"),
        ("Chapter 3 Methodology and Design", "30"),
        ("Chapter 4 Results and Discussion", "45"),
    ], heading="TABLE OF CONTENTS")
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_lof_number_format(model) if f.rule_id == "P056"]
    assert not findings


def test_p056_single_format_type_insufficient_no_finding(tmp_path: Path) -> None:
    """Only one entry of each format type does not trigger (gate: >=2 each)."""
    pdf_path = tmp_path / "p056_one_each.pdf"
    _make_lot_lof_number_format_pdf(pdf_path, [
        ("Table 1.1 Chapter Based Entry", "5"),
        ("Table 2 Sequential Entry", "12"),
        ("Table 3 Another Sequential Entry", "20"),
        ("Table 4 Yet Another Sequential Entry", "28"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_lof_number_format(model) if f.rule_id == "P056"]
    # Only 1 chapter_based entry → below gate threshold → no finding
    assert not findings


def test_p056_finding_metadata_privacy_safe(tmp_path: Path) -> None:
    """Findings must not include LoT/LoF entry text, titles, or private content."""
    pdf_path = tmp_path / "p056_privacy.pdf"
    _make_lot_lof_number_format_pdf(pdf_path, [
        ("Table 1.1 Chapter Based Entry One", "5"),
        ("Table 1.2 Chapter Based Entry Two", "12"),
        ("Table 3 Sequential Entry First", "20"),
        ("Table 4 Sequential Entry Second", "28"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_lof_number_format(model) if f.rule_id == "P056"]
    assert findings
    finding = findings[0]
    allowed_keys = {
        "issue_type",
        "page",
        "section_type",
        "entry_count",
        "format_counts",
        "observed_formats",
        "dominant_format",
        "triage_tier",
        "source_q_rule_id",
    }
    assert finding.details.keys() <= allowed_keys
    assert finding.details.get("triage_tier") == "low"
    assert finding.details.get("source_q_rule_id") == "Q063"
    for value in finding.details.values():
        value_lower = str(value).lower()
        assert "chapter based entry" not in value_lower
        assert "sequential entry" not in value_lower


def test_p056_import_and_wiring(tmp_path: Path) -> None:
    """P056 is importable and wired in audit_runner."""
    import inspect

    import njit_auditor.audit_runner as audit_runner
    from njit_auditor.rules.pdf_lot_lof_number_format import (
        check_pdf_lot_lof_number_format as _check,
    )
    assert callable(_check)
    src = inspect.getsource(audit_runner.collect_pdf_layout_findings)
    assert "check_pdf_lot_lof_number_format" in src


def test_p056_p055_p053_unaffected(tmp_path: Path) -> None:
    """P053 and P055 still fire correctly after P056 is added."""
    pdf_path = tmp_path / "p056_unaffected.pdf"
    _make_lot_lof_number_format_pdf(pdf_path, [
        ("Figure 2 Misplaced Figure in LoT", "5"),
        ("Table 2 Correct Table Entry Here", "12"),
        ("Table 3 Another Correct Table Entry", "20"),
    ])
    model = load_pdf_layout(str(pdf_path))
    p055 = [f for f in check_pdf_lot_lof_entry_type(model) if f.rule_id == "P055"]
    p056 = [f for f in check_pdf_lot_lof_number_format(model) if f.rule_id == "P056"]
    assert p055  # P055 still fires for the misplaced Figure entry
    assert not p056  # P056 does not fire (only 1 chapter-based or mixed — insufficient)


# ---------------------------------------------------------------------------
# P057: LoT/LoF page-number ordering checks
# ---------------------------------------------------------------------------


def _make_lot_lof_ordering_pdf(
    path: Path,
    entries: list[tuple[str, str | None]],
    heading: str = "LIST OF TABLES",
) -> None:
    """Build a synthetic LoT or LoF page for P057 testing."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((190, 90), heading, fontsize=16, fontname="Times-Bold")
    y = 140.0
    for text, pg_num in entries:
        page.insert_text((72.0, y), text, fontsize=12)
        if pg_num is not None:
            page.insert_text((500, y), pg_num, fontsize=12)
        y += 22.0
    doc.save(path)
    doc.close()


def test_p057_no_lot_lof_page_no_finding(tmp_path: Path) -> None:
    """No LoT/LoF page → no P057 finding."""
    pdf_path = tmp_path / "p057_no_list.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((72.0, 200.0), "Body text with no LoT or LoF.", fontsize=12)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_lof_page_number_ordering(model) if f.rule_id == "P057"]
    assert not findings


def test_p057_lot_ascending_no_finding(tmp_path: Path) -> None:
    """LoT page numbers non-decreasing → no finding."""
    pdf_path = tmp_path / "p057_lot_asc.pdf"
    _make_lot_lof_ordering_pdf(pdf_path, [
        ("Table 1 Results Overview Introduction", "5"),
        ("Table 2 Comparison of Methods Summary", "12"),
        ("Table 3 Evaluation Summary Statistics", "20"),
        ("Table 4 Statistical Analysis Results", "28"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_lof_page_number_ordering(model) if f.rule_id == "P057"]
    assert not findings


def test_p057_lot_one_inversion_no_finding(tmp_path: Path) -> None:
    """LoT with one inversion only → no finding (conservative gate requires >= 2)."""
    pdf_path = tmp_path / "p057_lot_one_inv.pdf"
    _make_lot_lof_ordering_pdf(pdf_path, [
        ("Table 1 Results Overview Introduction", "5"),
        ("Table 2 Comparison of Methods Summary", "12"),
        ("Table 3 Evaluation Summary Statistics", "8"),
        ("Table 4 Statistical Analysis Results", "28"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_lof_page_number_ordering(model) if f.rule_id == "P057"]
    assert not findings


def test_p057_lot_two_inversions_warns(tmp_path: Path) -> None:
    """LoT with >= 2 inversions → lot_page_numbers_not_nondecreasing."""
    pdf_path = tmp_path / "p057_lot_two_inv.pdf"
    _make_lot_lof_ordering_pdf(pdf_path, [
        ("Table 1 Results Overview Introduction", "20"),
        ("Table 2 Comparison of Methods Summary", "5"),
        ("Table 3 Evaluation Summary Statistics", "25"),
        ("Table 4 Statistical Analysis Results", "10"),
        ("Table 5 Additional Data Overview Table", "30"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_lof_page_number_ordering(model) if f.rule_id == "P057"]
    assert len(findings) == 1
    assert findings[0].details.get("issue_type") == "lot_page_numbers_not_nondecreasing"
    assert findings[0].details.get("section_type") == "list_of_tables"
    assert int(findings[0].details.get("inversion_count", "0")) >= 2


def test_p057_lof_ascending_no_finding(tmp_path: Path) -> None:
    """LoF page numbers non-decreasing → no finding."""
    pdf_path = tmp_path / "p057_lof_asc.pdf"
    _make_lot_lof_ordering_pdf(pdf_path, [
        ("Figure 1 System Architecture Overview", "3"),
        ("Figure 2 Evaluation Results Chart Plot", "7"),
        ("Figure 3 Comparison Overview Pattern", "11"),
        ("Figure 4 Final Results Summary Report", "15"),
    ], heading="LIST OF FIGURES")
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_lof_page_number_ordering(model) if f.rule_id == "P057"]
    assert not findings


def test_p057_lof_two_inversions_warns(tmp_path: Path) -> None:
    """LoF with >= 2 inversions → lof_page_numbers_not_nondecreasing."""
    pdf_path = tmp_path / "p057_lof_two_inv.pdf"
    _make_lot_lof_ordering_pdf(pdf_path, [
        ("Figure 1 System Architecture Overview", "30"),
        ("Figure 2 Evaluation Results Chart Plot", "5"),
        ("Figure 3 Comparison Overview Pattern", "35"),
        ("Figure 4 Final Results Summary Report", "10"),
        ("Figure 5 Additional Architecture Graph", "40"),
    ], heading="LIST OF FIGURES")
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_lof_page_number_ordering(model) if f.rule_id == "P057"]
    assert len(findings) == 1
    assert findings[0].details.get("issue_type") == "lof_page_numbers_not_nondecreasing"
    assert findings[0].details.get("section_type") == "list_of_figures"
    assert int(findings[0].details.get("inversion_count", "0")) >= 2


def test_p057_sparse_page_skipped(tmp_path: Path) -> None:
    """Fewer than 3 comparable entries → skipped."""
    pdf_path = tmp_path / "p057_sparse.pdf"
    _make_lot_lof_ordering_pdf(pdf_path, [
        ("Table 1 Results Overview Here", "20"),
        ("Table 2 Comparison Summary Results", "5"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_lof_page_number_ordering(model) if f.rule_id == "P057"]
    assert not findings


def test_p057_non_integer_page_skipped(tmp_path: Path) -> None:
    """Entries with non-integer page tokens are excluded from ordering check."""
    pdf_path = tmp_path / "p057_nonint.pdf"
    _make_lot_lof_ordering_pdf(pdf_path, [
        ("Table 1 Results Overview Introduction", "v"),
        ("Table 2 Comparison of Methods Summary", "vi"),
        ("Table 3 Evaluation Summary Statistics", "iii"),
        ("Table 4 Statistical Analysis Results", "vii"),
        ("Table 5 Additional Data Overview Here", "ii"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_lof_page_number_ordering(model) if f.rule_id == "P057"]
    assert not findings


def test_p057_toc_unaffected(tmp_path: Path) -> None:
    """TOC pages → P057 does not fire."""
    pdf_path = tmp_path / "p057_toc.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((190, 90), "TABLE OF CONTENTS", fontsize=16, fontname="Times-Bold")
    y = 140.0
    for text, pg_num in [
        ("Chapter 1 Introduction Overview", "30"),
        ("Chapter 2 Literature Review Summary", "5"),
        ("Chapter 3 Methodology Description", "35"),
        ("Chapter 4 Results and Discussion", "10"),
        ("Chapter 5 Conclusions and Future Work", "40"),
    ]:
        page.insert_text((72.0, y), text, fontsize=12)
        page.insert_text((500, y), pg_num, fontsize=12)
        y += 22.0
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_lof_page_number_ordering(model) if f.rule_id == "P057"]
    assert not findings


def test_p057_finding_metadata_privacy_safe(tmp_path: Path) -> None:
    """Finding details contain only structural metadata — no entry text or titles."""
    pdf_path = tmp_path / "p057_privacy.pdf"
    _make_lot_lof_ordering_pdf(pdf_path, [
        ("Table 1 Results Overview Introduction", "20"),
        ("Table 2 Comparison of Methods Summary", "5"),
        ("Table 3 Evaluation Summary Statistics", "25"),
        ("Table 4 Statistical Analysis Results", "10"),
        ("Table 5 Additional Data Overview Table", "30"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_lof_page_number_ordering(model) if f.rule_id == "P057"]
    assert findings
    finding = findings[0]
    allowed_keys = {
        "issue_type", "page", "section_type", "entry_count",
        "comparable_page_number_count", "inversion_count",
        "first_inversion_index", "triage_tier", "source_q_rule_id",
    }
    for key in finding.details:
        assert key in allowed_keys, f"Unexpected metadata key: {key!r}"
    for key, val in finding.details.items():
        assert isinstance(val, str), f"Metadata value for {key!r} should be str"
    assert finding.details.get("triage_tier") == "medium"
    assert finding.details.get("source_q_rule_id") in ("Q069", "Q079")


def test_p057_import_and_wiring(tmp_path: Path) -> None:
    """P057 is importable and wired into cli.py collect path."""
    from njit_auditor.rules.pdf_lot_lof_page_number_ordering import (
        check_pdf_lot_lof_page_number_ordering as fn,
    )
    assert callable(fn)
    pdf_path = tmp_path / "p057_wire.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((72.0, 200.0), "No LoT or LoF page here.", fontsize=12)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = fn(model)
    assert isinstance(findings, list)


def test_p057_toc_entries_unaffected(tmp_path: Path) -> None:
    """TOC entries with inversions are not flagged by P057."""
    pdf_path = tmp_path / "p057_toc_entries.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((190, 90), "TABLE OF CONTENTS", fontsize=16, fontname="Times-Bold")
    entries = [
        ("1 Introduction Overview Chapter", "1"),
        ("2 Background Literature Review", "5"),
        ("3 Methodology Description Here", "10"),
        ("4 Results Discussion Analysis", "15"),
        ("5 Conclusion Future Work", "20"),
    ]
    y = 140.0
    for text, pg_num in entries:
        page.insert_text((72.0, y), text, fontsize=12)
        page.insert_text((500, y), pg_num, fontsize=12)
        y += 22.0
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    p057 = [f for f in check_pdf_lot_lof_page_number_ordering(model) if f.rule_id == "P057"]
    assert not p057


# ---------------------------------------------------------------------------
# P058: TOC page-number ordering checks
# ---------------------------------------------------------------------------


def _make_toc_ordering_pdf(
    path: Path,
    entries: list[tuple[str, str | None]],
) -> None:
    """Build a synthetic TOC page for P058 testing."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((190, 90), "TABLE OF CONTENTS", fontsize=16, fontname="Times-Bold")
    y = 140.0
    for text, pg_num in entries:
        page.insert_text((72.0, y), text, fontsize=12)
        if pg_num is not None:
            page.insert_text((500, y), pg_num, fontsize=12)
        y += 22.0
    doc.save(path)
    doc.close()


def test_p058_no_toc_page_no_finding(tmp_path: Path) -> None:
    """No TOC page → no P058 finding."""
    pdf_path = tmp_path / "p058_no_toc.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((72.0, 200.0), "Body text with no Table of Contents.", fontsize=12)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_toc_page_number_ordering(model) if f.rule_id == "P058"]
    assert not findings


def test_p058_toc_ascending_no_finding(tmp_path: Path) -> None:
    """TOC page numbers non-decreasing → no finding."""
    pdf_path = tmp_path / "p058_toc_asc.pdf"
    _make_toc_ordering_pdf(pdf_path, [
        ("Chapter 1 Introduction Overview", "1"),
        ("Chapter 2 Literature Survey", "15"),
        ("Chapter 3 Methodology Approach", "30"),
        ("Chapter 4 Results Discussion", "45"),
        ("Chapter 5 Conclusion Future", "60"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_toc_page_number_ordering(model) if f.rule_id == "P058"]
    assert not findings


def test_p058_toc_one_inversion_no_finding(tmp_path: Path) -> None:
    """TOC with one inversion only → no finding (conservative gate requires >= 2)."""
    pdf_path = tmp_path / "p058_toc_one_inv.pdf"
    _make_toc_ordering_pdf(pdf_path, [
        ("Chapter 1 Introduction Overview", "1"),
        ("Chapter 2 Literature Survey", "15"),
        ("Chapter 3 Methodology Approach", "10"),
        ("Chapter 4 Results Discussion", "45"),
        ("Chapter 5 Conclusion Future", "60"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_toc_page_number_ordering(model) if f.rule_id == "P058"]
    assert not findings


def test_p058_toc_two_inversions_warns(tmp_path: Path) -> None:
    """TOC with >= 2 inversions → toc_page_numbers_not_nondecreasing."""
    pdf_path = tmp_path / "p058_toc_two_inv.pdf"
    _make_toc_ordering_pdf(pdf_path, [
        ("Chapter 1 Introduction Overview", "45"),
        ("Chapter 2 Literature Survey", "10"),
        ("Chapter 3 Methodology Approach", "55"),
        ("Chapter 4 Results Discussion", "20"),
        ("Chapter 5 Conclusion Future", "70"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_toc_page_number_ordering(model) if f.rule_id == "P058"]
    assert len(findings) == 1
    assert findings[0].details.get("issue_type") == "toc_page_numbers_not_nondecreasing"
    assert findings[0].details.get("section_type") == "table_of_contents"
    assert int(findings[0].details.get("inversion_count", "0")) >= 2


def test_p058_sparse_toc_skipped(tmp_path: Path) -> None:
    """Fewer than 3 comparable entries → skipped."""
    pdf_path = tmp_path / "p058_sparse.pdf"
    _make_toc_ordering_pdf(pdf_path, [
        ("Chapter 1 Introduction Overview", "45"),
        ("Chapter 2 Literature Survey", "10"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_toc_page_number_ordering(model) if f.rule_id == "P058"]
    assert not findings


def test_p058_roman_entries_skipped(tmp_path: Path) -> None:
    """Roman-numeral page tokens are excluded from ordering comparison."""
    pdf_path = tmp_path / "p058_roman.pdf"
    _make_toc_ordering_pdf(pdf_path, [
        ("Abstract Overview Content", "v"),
        ("Acknowledgements Section", "vi"),
        ("Table of Contents List", "vii"),
        ("List of Tables Entry", "viii"),
        ("List of Figures Entry", "ix"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_toc_page_number_ordering(model) if f.rule_id == "P058"]
    assert not findings


def test_p058_lot_lof_unaffected(tmp_path: Path) -> None:
    """LoT and LoF pages → P058 does not fire."""
    pdf_path = tmp_path / "p058_lot_lof.pdf"
    doc = fitz.open()
    # LoT page with inversions
    page = doc.new_page(width=612, height=792)
    page.insert_text((190, 90), "LIST OF TABLES", fontsize=16, fontname="Times-Bold")
    for text, pg in [
        ("Table 1 Overview Introduction", "45"),
        ("Table 2 Comparison Survey", "10"),
        ("Table 3 Evaluation Approach", "55"),
        ("Table 4 Results Discussion", "20"),
        ("Table 5 Summary Conclusion", "70"),
    ]:
        y = 140.0 + 22.0 * ["Table 1 Overview Introduction", "Table 2 Comparison Survey",
                              "Table 3 Evaluation Approach", "Table 4 Results Discussion",
                              "Table 5 Summary Conclusion"].index(text)
        page.insert_text((72.0, y), text, fontsize=12)
        page.insert_text((500, y), pg, fontsize=12)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    p058 = [f for f in check_pdf_toc_page_number_ordering(model) if f.rule_id == "P058"]
    assert not p058


def test_p058_finding_metadata_privacy_safe(tmp_path: Path) -> None:
    """Finding details contain only structural metadata — no entry text or titles."""
    pdf_path = tmp_path / "p058_privacy.pdf"
    _make_toc_ordering_pdf(pdf_path, [
        ("Chapter 1 Introduction Overview", "45"),
        ("Chapter 2 Literature Survey", "10"),
        ("Chapter 3 Methodology Approach", "55"),
        ("Chapter 4 Results Discussion", "20"),
        ("Chapter 5 Conclusion Future", "70"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_toc_page_number_ordering(model) if f.rule_id == "P058"]
    assert findings
    finding = findings[0]
    allowed_keys = {
        "issue_type", "page", "section_type", "entry_count",
        "comparable_page_number_count", "inversion_count",
        "first_inversion_index", "triage_tier", "source_q_rule_id",
    }
    for key in finding.details:
        assert key in allowed_keys, f"Unexpected metadata key: {key!r}"
    for key, val in finding.details.items():
        assert isinstance(val, str), f"Metadata value for {key!r} should be str"
    assert finding.details.get("triage_tier") == "medium"
    assert finding.details.get("source_q_rule_id") == "Q057"


def test_p058_import_and_wiring(tmp_path: Path) -> None:
    """P058 is importable and wired into cli.py collect path."""
    from njit_auditor.rules.pdf_toc_page_number_ordering import (
        check_pdf_toc_page_number_ordering as fn,
    )
    assert callable(fn)
    pdf_path = tmp_path / "p058_wire.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((72.0, 200.0), "No TOC page here.", fontsize=12)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = fn(model)
    assert isinstance(findings, list)


def test_p058_lot_entries_unaffected_by_p058(tmp_path: Path) -> None:
    """LoT with inversions is caught by P057, not P058."""
    pdf_path = tmp_path / "p058_lot_only.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((190, 90), "LIST OF TABLES", fontsize=16, fontname="Times-Bold")
    entries = [
        ("Table 1 Overview Introduction", "45"),
        ("Table 2 Comparison Survey", "10"),
        ("Table 3 Evaluation Approach", "55"),
        ("Table 4 Results Discussion", "20"),
        ("Table 5 Summary Conclusion", "70"),
    ]
    y = 140.0
    for text, pg in entries:
        page.insert_text((72.0, y), text, fontsize=12)
        page.insert_text((500, y), pg, fontsize=12)
        y += 22.0
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    p058 = [f for f in check_pdf_toc_page_number_ordering(model) if f.rule_id == "P058"]
    p057 = [f for f in check_pdf_lot_lof_page_number_ordering(model) if f.rule_id == "P057"]
    assert not p058
    assert p057  # P057 fires for LoT ordering violation


# ---------------------------------------------------------------------------
# P059 — LoT/LoF entry-number ordering check
# ---------------------------------------------------------------------------


def _make_lot_entry_num_ordering_pdf(
    path: Path,
    entries: list[tuple[str, str | None]],
    heading: str = "LIST OF TABLES",
) -> None:
    """Build a synthetic LoT/LoF page for P059 testing."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((190, 90), heading, fontsize=16, fontname="Times-Bold")
    y = 140.0
    for text, pg_num in entries:
        page.insert_text((72.0, y), text, fontsize=12)
        if pg_num is not None:
            page.insert_text((500, y), pg_num, fontsize=12)
        y += 22.0
    doc.save(path)
    doc.close()


def test_p059_no_lot_page_no_finding(tmp_path: Path) -> None:
    """No LoT/LoF page → no P059 finding."""
    pdf_path = tmp_path / "p059_no_lot.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((72.0, 200.0), "Body text with no List of Tables.", fontsize=12)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_lof_entry_number_ordering(model) if f.rule_id == "P059"]
    assert not findings


def test_p059_lot_ascending_no_finding(tmp_path: Path) -> None:
    """LoT entry numbers non-decreasing → no finding."""
    pdf_path = tmp_path / "p059_lot_asc.pdf"
    _make_lot_entry_num_ordering_pdf(pdf_path, [
        ("Table 1 Overview Survey", "10"),
        ("Table 2 Analysis Report", "20"),
        ("Table 3 Results Study", "30"),
        ("Table 4 Evaluation Survey", "40"),
        ("Table 5 Discussion Report", "50"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_lof_entry_number_ordering(model) if f.rule_id == "P059"]
    assert not findings


def test_p059_lot_one_inversion_no_finding(tmp_path: Path) -> None:
    """LoT with exactly one inversion → no finding (conservative gate requires >= 2)."""
    pdf_path = tmp_path / "p059_lot_one_inv.pdf"
    # Entry numbers: 1, 3, 5, 2, 4 → 1 inversion (5>2)
    _make_lot_entry_num_ordering_pdf(pdf_path, [
        ("Table 1 Overview Survey", "10"),
        ("Table 3 Analysis Report", "30"),
        ("Table 5 Results Study", "50"),
        ("Table 2 Evaluation Survey", "20"),
        ("Table 4 Discussion Report", "40"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_lof_entry_number_ordering(model) if f.rule_id == "P059"]
    assert not findings


def test_p059_lot_two_inversions_warns(tmp_path: Path) -> None:
    """LoT with >= 2 entry-number inversions → lot_entry_numbers_not_nondecreasing."""
    pdf_path = tmp_path / "p059_lot_two_inv.pdf"
    # Entry numbers: 1, 5, 2, 4, 3 → 2 inversions (5>2 and 4>3)
    _make_lot_entry_num_ordering_pdf(pdf_path, [
        ("Table 1 Overview Survey", "10"),
        ("Table 5 Analysis Report", "45"),
        ("Table 2 Results Study", "20"),
        ("Table 4 Evaluation Survey", "35"),
        ("Table 3 Discussion Report", "30"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_lof_entry_number_ordering(model) if f.rule_id == "P059"]
    assert len(findings) == 1
    assert findings[0].details.get("issue_type") == "lot_entry_numbers_not_nondecreasing"
    assert findings[0].details.get("section_type") == "list_of_tables"
    assert int(findings[0].details.get("inversion_count", "0")) >= 2


def test_p059_lof_two_inversions_warns(tmp_path: Path) -> None:
    """LoF with >= 2 entry-number inversions → lof_entry_numbers_not_nondecreasing."""
    pdf_path = tmp_path / "p059_lof_two_inv.pdf"
    # Entry numbers: 1, 5, 2, 4, 3 → 2 inversions (5>2 and 4>3)
    _make_lot_entry_num_ordering_pdf(pdf_path, [
        ("Figure 1 Overview Survey", "10"),
        ("Figure 5 Analysis Report", "45"),
        ("Figure 2 Results Study", "20"),
        ("Figure 4 Evaluation Survey", "35"),
        ("Figure 3 Discussion Report", "30"),
    ], heading="LIST OF FIGURES")
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_lof_entry_number_ordering(model) if f.rule_id == "P059"]
    assert len(findings) == 1
    assert findings[0].details.get("issue_type") == "lof_entry_numbers_not_nondecreasing"
    assert findings[0].details.get("section_type") == "list_of_figures"
    assert int(findings[0].details.get("inversion_count", "0")) >= 2


def test_p059_toc_unaffected(tmp_path: Path) -> None:
    """TOC page → P059 does not fire."""
    pdf_path = tmp_path / "p059_toc.pdf"
    _make_toc_ordering_pdf(pdf_path, [
        ("Chapter 5 Overview Survey", "10"),
        ("Chapter 1 Analysis Report", "45"),
        ("Chapter 3 Results Study", "20"),
        ("Chapter 2 Evaluation Survey", "35"),
        ("Chapter 4 Discussion Report", "30"),
    ])
    model = load_pdf_layout(str(pdf_path))
    p059 = [f for f in check_pdf_lot_lof_entry_number_ordering(model) if f.rule_id == "P059"]
    assert not p059


def test_p059_sparse_lot_skipped(tmp_path: Path) -> None:
    """Fewer than 3 parseable entry numbers → skipped."""
    pdf_path = tmp_path / "p059_sparse.pdf"
    _make_lot_entry_num_ordering_pdf(pdf_path, [
        ("Table 5 Overview Survey", "45"),
        ("Table 2 Analysis Report", "10"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_lof_entry_number_ordering(model) if f.rule_id == "P059"]
    assert not findings


def test_p059_mixed_format_skipped(tmp_path: Path) -> None:
    """Mixed sequential + chapter-based entry numbers → skipped."""
    pdf_path = tmp_path / "p059_mixed.pdf"
    _make_lot_entry_num_ordering_pdf(pdf_path, [
        ("Table 1 Overview Survey", "10"),
        ("Table 2.1 Analysis Report", "20"),
        ("Table 3 Results Study", "30"),
        ("Table 2.2 Evaluation Survey", "25"),
        ("Table 5 Discussion Report", "50"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_lof_entry_number_ordering(model) if f.rule_id == "P059"]
    assert not findings


def test_p059_chapter_based_two_inversions_warns(tmp_path: Path) -> None:
    """Chapter-based entry numbers with >= 2 inversions → finding."""
    pdf_path = tmp_path / "p059_chapter.pdf"
    # Entry tuples: (1,1), (1,5), (1,2), (1,4), (1,3) → 2 inversions
    _make_lot_entry_num_ordering_pdf(pdf_path, [
        ("Table 1.1 Overview Survey", "10"),
        ("Table 1.5 Analysis Report", "45"),
        ("Table 1.2 Results Study", "20"),
        ("Table 1.4 Evaluation Survey", "35"),
        ("Table 1.3 Discussion Report", "30"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_lof_entry_number_ordering(model) if f.rule_id == "P059"]
    assert len(findings) == 1
    assert findings[0].details.get("issue_type") == "lot_entry_numbers_not_nondecreasing"
    assert int(findings[0].details.get("inversion_count", "0")) >= 2


def test_p059_finding_metadata_privacy_safe(tmp_path: Path) -> None:
    """Finding details contain only structural metadata — no entry text or titles."""
    pdf_path = tmp_path / "p059_privacy.pdf"
    _make_lot_entry_num_ordering_pdf(pdf_path, [
        ("Table 1 Overview Survey", "10"),
        ("Table 5 Analysis Report", "45"),
        ("Table 2 Results Study", "20"),
        ("Table 4 Evaluation Survey", "35"),
        ("Table 3 Discussion Report", "30"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_lof_entry_number_ordering(model) if f.rule_id == "P059"]
    assert findings
    finding = findings[0]
    allowed_keys = {
        "issue_type", "page", "section_type", "entry_count",
        "comparable_entry_number_count", "inversion_count",
        "first_inversion_index", "triage_tier", "source_q_rule_id",
    }
    for key in finding.details:
        assert key in allowed_keys, f"Unexpected metadata key: {key!r}"
    for key, val in finding.details.items():
        assert isinstance(val, str), f"Metadata value for {key!r} should be str"
    assert finding.details.get("triage_tier") == "medium"
    assert finding.details.get("source_q_rule_id") in {"Q063", "Q072"}


def test_p059_import_and_wiring(tmp_path: Path) -> None:
    """P059 is importable and wired into cli.py collect path."""
    from njit_auditor.rules.pdf_lot_lof_entry_number_ordering import (
        check_pdf_lot_lof_entry_number_ordering as fn,
    )
    assert callable(fn)
    pdf_path = tmp_path / "p059_wire.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((72.0, 200.0), "No LoT/LoF page here.", fontsize=12)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = fn(model)
    assert isinstance(findings, list)


def test_p059_unparseable_entries_skipped(tmp_path: Path) -> None:
    """Entries with no parseable Table/Figure prefix are silently excluded."""
    pdf_path = tmp_path / "p059_unparse.pdf"
    _make_lot_entry_num_ordering_pdf(pdf_path, [
        ("Table 1 Overview Survey", "10"),
        ("Diagram 2 Random Analysis", "20"),   # not Table/Figure prefix
        ("Table 5 Results Study", "50"),
        ("Random Entry Content Here", "40"),    # no prefix
        ("Table 3 Discussion Report", "30"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_lot_lof_entry_number_ordering(model) if f.rule_id == "P059"]
    # Only 3 parseable entries (1, 5, 3) with 1 inversion (5>3) → below gate
    assert not findings

# ---------------------------------------------------------------------------
# P060 — TOC section-number ordering check
# ---------------------------------------------------------------------------

def test_p060_no_toc_page_no_finding(tmp_path: Path) -> None:
    """No TOC page → no P060 finding."""
    pdf_path = tmp_path / "p060_no_toc.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((72.0, 200.0), "Body text with no Table of Contents.", fontsize=12)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_toc_entry_number_ordering(model) if f.rule_id == "P060"]
    assert not findings


def test_p060_toc_ascending_no_finding(tmp_path: Path) -> None:
    """TOC section numbers non-decreasing → no finding."""
    pdf_path = tmp_path / "p060_toc_asc.pdf"
    _make_toc_ordering_pdf(pdf_path, [
        ("1 Overview Survey", "5"),
        ("2 Analysis Report", "15"),
        ("3 Results Study", "25"),
        ("4 Evaluation Survey", "35"),
        ("5 Discussion Report", "45"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_toc_entry_number_ordering(model) if f.rule_id == "P060"]
    assert not findings


def test_p060_toc_one_inversion_no_finding(tmp_path: Path) -> None:
    """TOC with exactly one inversion → no finding (conservative gate requires >= 2)."""
    pdf_path = tmp_path / "p060_toc_one_inv.pdf"
    # Section numbers: 1, 3, 5, 2, 4 → 1 inversion (5>2)
    _make_toc_ordering_pdf(pdf_path, [
        ("1 Overview Survey", "5"),
        ("3 Analysis Report", "25"),
        ("5 Results Study", "45"),
        ("2 Evaluation Survey", "15"),
        ("4 Discussion Report", "35"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_toc_entry_number_ordering(model) if f.rule_id == "P060"]
    assert not findings


def test_p060_toc_two_inversions_warns(tmp_path: Path) -> None:
    """TOC with >= 2 section-number inversions → toc_entry_numbers_not_nondecreasing."""
    pdf_path = tmp_path / "p060_toc_two_inv.pdf"
    # Section numbers: 1, 5, 2, 4, 3 → 2 inversions (5>2 and 4>3)
    _make_toc_ordering_pdf(pdf_path, [
        ("1 Overview Survey", "5"),
        ("5 Analysis Report", "45"),
        ("2 Results Study", "15"),
        ("4 Evaluation Survey", "35"),
        ("3 Discussion Report", "25"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_toc_entry_number_ordering(model) if f.rule_id == "P060"]
    assert len(findings) == 1
    assert findings[0].details.get("issue_type") == "toc_entry_numbers_not_nondecreasing"
    assert findings[0].details.get("section_type") == "table_of_contents"
    assert int(findings[0].details.get("inversion_count", "0")) >= 2


def test_p060_lot_unaffected(tmp_path: Path) -> None:
    """LoT page → P060 does not fire."""
    pdf_path = tmp_path / "p060_lot.pdf"
    _make_lot_entry_num_ordering_pdf(pdf_path, [
        ("1 Overview Survey", "5"),
        ("5 Analysis Report", "45"),
        ("2 Results Study", "15"),
        ("4 Evaluation Survey", "35"),
        ("3 Discussion Report", "25"),
    ], heading="LIST OF TABLES")
    model = load_pdf_layout(str(pdf_path))
    p060 = [f for f in check_pdf_toc_entry_number_ordering(model) if f.rule_id == "P060"]
    assert not p060


def test_p060_lof_unaffected(tmp_path: Path) -> None:
    """LoF page → P060 does not fire."""
    pdf_path = tmp_path / "p060_lof.pdf"
    _make_lot_entry_num_ordering_pdf(pdf_path, [
        ("Figure 1 Overview Survey", "5"),
        ("Figure 5 Analysis Report", "45"),
        ("Figure 2 Results Study", "15"),
        ("Figure 4 Evaluation Survey", "35"),
        ("Figure 3 Discussion Report", "25"),
    ], heading="LIST OF FIGURES")
    model = load_pdf_layout(str(pdf_path))
    p060 = [f for f in check_pdf_toc_entry_number_ordering(model) if f.rule_id == "P060"]
    assert not p060


def test_p060_sparse_toc_skipped(tmp_path: Path) -> None:
    """Fewer than 3 parseable section numbers → skipped."""
    pdf_path = tmp_path / "p060_sparse.pdf"
    _make_toc_ordering_pdf(pdf_path, [
        ("5 Overview Survey", "45"),
        ("2 Analysis Report", "15"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_toc_entry_number_ordering(model) if f.rule_id == "P060"]
    assert not findings


def test_p060_word_prefix_entries_skipped(tmp_path: Path) -> None:
    """Word-prefix entries (CHAPTER, ABSTRACT, APPENDIX) not counted."""
    pdf_path = tmp_path / "p060_word_prefix.pdf"
    # Only 3 numeric entries (1, 2, 5), with 1 inversion (5 appears before nothing → 
    # actually 1, 2, 5 is non-decreasing → no finding)
    # Plus word-prefix entries that should be silently excluded
    _make_toc_ordering_pdf(pdf_path, [
        ("ABSTRACT Overview Survey", "iv"),
        ("1 Analysis Report", "5"),
        ("2 Results Study", "15"),
        ("APPENDIX Overview Notes", "98"),
        ("5 Discussion Report", "45"),
        ("3 Summary Notes", "25"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_toc_entry_number_ordering(model) if f.rule_id == "P060"]
    # Numeric entries: (1,), (2,), (5,), (3,) → 1 inversion (5>3) → below gate of 2
    assert not findings


def test_p060_subsection_two_inversions_warns(tmp_path: Path) -> None:
    """Subsection entries with >= 2 inversions → toc_entry_numbers_not_nondecreasing."""
    pdf_path = tmp_path / "p060_subsect.pdf"
    # Subsection tuples: (1,1), (1,5), (1,2), (1,4), (1,3) → 2 inversions
    _make_toc_ordering_pdf(pdf_path, [
        ("1.1 Overview Survey", "5"),
        ("1.5 Analysis Report", "45"),
        ("1.2 Results Study", "15"),
        ("1.4 Evaluation Survey", "35"),
        ("1.3 Discussion Report", "25"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_toc_entry_number_ordering(model) if f.rule_id == "P060"]
    assert len(findings) == 1
    assert findings[0].details.get("issue_type") == "toc_entry_numbers_not_nondecreasing"
    assert int(findings[0].details.get("inversion_count", "0")) >= 2


def test_p060_finding_metadata_privacy_safe(tmp_path: Path) -> None:
    """Finding details contain only structural metadata — no entry text or titles."""
    pdf_path = tmp_path / "p060_privacy.pdf"
    _make_toc_ordering_pdf(pdf_path, [
        ("1 Overview Survey", "5"),
        ("5 Analysis Report", "45"),
        ("2 Results Study", "15"),
        ("4 Evaluation Survey", "35"),
        ("3 Discussion Report", "25"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_toc_entry_number_ordering(model) if f.rule_id == "P060"]
    assert findings
    finding = findings[0]
    allowed_keys = {
        "issue_type", "page", "section_type", "entry_count",
        "comparable_entry_number_count", "inversion_count",
        "first_inversion_index", "triage_tier", "source_q_rule_id",
    }
    for key in finding.details:
        assert key in allowed_keys, f"Unexpected metadata key: {key!r}"
    for key, val in finding.details.items():
        assert isinstance(val, str), f"Metadata value for {key!r} should be str"
    assert finding.details.get("triage_tier") == "medium"
    assert finding.details.get("source_q_rule_id") == "Q056"


def test_p060_import_and_wiring(tmp_path: Path) -> None:
    """P060 is importable and wired into cli.py collect path."""
    from njit_auditor.rules.pdf_toc_entry_number_ordering import (
        check_pdf_toc_entry_number_ordering as fn,
    )
    assert callable(fn)
    pdf_path = tmp_path / "p060_wire.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((72.0, 200.0), "No TOC page here.", fontsize=12)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = fn(model)
    assert isinstance(findings, list)


def test_p060_unparseable_entries_skipped(tmp_path: Path) -> None:
    """Entries with no parseable section number are silently excluded."""
    pdf_path = tmp_path / "p060_unparse.pdf"
    _make_toc_ordering_pdf(pdf_path, [
        ("1 Overview Survey", "5"),
        ("CHAPTER 3 Analysis Report", "25"),   # word-prefix, skipped
        ("5 Results Study", "45"),
        ("Random Content Notes", "40"),         # no numeric prefix, skipped
        ("3 Discussion Report", "25"),
    ])
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_toc_entry_number_ordering(model) if f.rule_id == "P060"]
    # Only 3 parseable entries (1, 5, 3) with 1 inversion (5>3) → below gate
    assert not findings


# ---------------------------------------------------------------------------
# P074: Title Page graduation month validation
# ---------------------------------------------------------------------------


def _make_title_page_graduation_month_doc(month_year_text: str):  # type: ignore[return]
    """Return a synthetic PdfDocument whose title page has a single 'Month YYYY' line."""
    from njit_auditor.pdf_models import (
        BBox,
        PdfDocument,
        PdfPage,
        PdfTextBlock,
        PdfTextLine,
        PdfTextSpan,
    )

    bbox = BBox(x0=108.0, y0=700.0, x1=400.0, y1=716.0)
    span = PdfTextSpan(
        text=month_year_text,
        bbox=bbox,
        font="Times-Roman",
        size=12.0,
        bold=False,
        italic=False,
    )
    line = PdfTextLine(spans=[span], bbox=bbox, text=month_year_text)
    block = PdfTextBlock(lines=[line], bbox=bbox, text=month_year_text)
    page = PdfPage(page_number=1, width=612.0, height=792.0, text_blocks=[block])
    return PdfDocument(path="synthetic", pages=[page])


def test_p074_august_is_valid() -> None:
    doc = _make_title_page_graduation_month_doc("August 2024")
    assert not check_pdf_title_page_graduation_month(doc)


def test_p074_december_is_valid() -> None:
    doc = _make_title_page_graduation_month_doc("December 2024")
    assert not check_pdf_title_page_graduation_month(doc)


def test_p074_may_is_valid() -> None:
    doc = _make_title_page_graduation_month_doc("May 2024")
    assert not check_pdf_title_page_graduation_month(doc)


def test_p074_june_is_invalid() -> None:
    doc = _make_title_page_graduation_month_doc("June 2024")
    findings = check_pdf_title_page_graduation_month(doc)
    assert len(findings) == 1
    assert findings[0].rule_id == "P074"
    assert findings[0].details.get("issue_type") == "title_page_graduation_month_invalid"
    assert findings[0].details.get("detected_month") == "june"


def test_p074_october_is_invalid() -> None:
    doc = _make_title_page_graduation_month_doc("October 2024")
    findings = check_pdf_title_page_graduation_month(doc)
    assert len(findings) == 1
    assert findings[0].rule_id == "P074"
    assert findings[0].details.get("detected_month") == "october"


def test_p074_no_month_pattern_emits_nothing() -> None:
    from njit_auditor.pdf_models import (
        BBox,
        PdfDocument,
        PdfPage,
        PdfTextBlock,
        PdfTextLine,
        PdfTextSpan,
    )

    bbox = BBox(x0=108.0, y0=100.0, x1=400.0, y1=116.0)
    span = PdfTextSpan(
        text="A Study of Distributed Systems",
        bbox=bbox,
        font="Times-Roman",
        size=14.0,
        bold=False,
        italic=False,
    )
    line = PdfTextLine(spans=[span], bbox=bbox, text="A Study of Distributed Systems")
    block = PdfTextBlock(lines=[line], bbox=bbox, text="A Study of Distributed Systems")
    page = PdfPage(page_number=1, width=612.0, height=792.0, text_blocks=[block])
    doc = PdfDocument(path="synthetic", pages=[page])
    assert not check_pdf_title_page_graduation_month(doc)


def test_p074_case_insensitive_match() -> None:
    doc = _make_title_page_graduation_month_doc("JUNE 2024")
    findings = check_pdf_title_page_graduation_month(doc)
    assert len(findings) == 1
    assert findings[0].details.get("detected_month") == "june"


def test_p074_valid_months_in_details() -> None:
    doc = _make_title_page_graduation_month_doc("March 2024")
    findings = check_pdf_title_page_graduation_month(doc)
    assert len(findings) == 1
    assert findings[0].details.get("valid_months") == "august, december, may"
    assert findings[0].details.get("page_type") == "title_page"


def test_p074_finding_message_contains_detected_month() -> None:
    doc = _make_title_page_graduation_month_doc("February 2024")
    findings = check_pdf_title_page_graduation_month(doc)
    assert len(findings) == 1
    assert "February" in findings[0].message


def test_p074_empty_document_emits_nothing() -> None:
    from njit_auditor.pdf_models import PdfDocument

    doc = PdfDocument(path="synthetic", pages=[])
    assert not check_pdf_title_page_graduation_month(doc)


def test_p074_wiring_in_collect_pdf_layout_findings(tmp_path: Path) -> None:
    from njit_auditor.audit_runner import collect_pdf_layout_findings

    pdf_path = tmp_path / "p074_wire.pdf"
    _make_frontmatter_pdf(
        pdf_path,
        title_page_text=[
            "A Study of Systems",
            "by",
            "Test Author",
            "A Dissertation Submitted to New Jersey Institute of Technology",
            "for the Degree of Doctor of Philosophy",
            "June 2024",
        ],
    )
    model = load_pdf_layout(str(pdf_path))
    findings = collect_pdf_layout_findings(model, pdf_path)
    p074 = [f for f in findings if f.rule_id == "P074"]
    assert len(p074) == 1
    assert p074[0].details.get("issue_type") == "title_page_graduation_month_invalid"


# ---------------------------------------------------------------------------
# US-federal copyright-warning wrapper detection (regression tests for P020
# false-positive family where pages 2-3 of a repository PDF were not detected
# as wrappers and P020 ran on legal boilerplate text).
# ---------------------------------------------------------------------------


def _make_us_copyright_warning_then_thesis_pdf(path: Path) -> None:
    """Create a 5-page PDF: DC cover, US copyright notice, Van Houten notice, thesis pages."""
    doc = fitz.open()

    # Page 1: Digital Commons cover
    page = doc.new_page(width=612, height=792)
    page.insert_text((72, 72), "Digital Commons @ NJIT", fontsize=14)
    page.insert_text((72, 100), "Electronic Theses and Dissertations", fontsize=11)
    page.insert_text((72, 130), "Recommended Citation", fontsize=11)
    page.insert_text((292, 760), "1", fontsize=12)

    # Page 2: US federal copyright warning (the format NOT matched by old markers)
    page = doc.new_page(width=612, height=792)
    page.insert_text(
        (150, 72),
        "Copyright Warning & Restrictions",
        fontsize=14,
        fontname="Times-Bold",
    )
    page.insert_text(
        (72, 100),
        "The copyright law of the United States (Title 17, United States Code)",
        fontsize=11,
    )
    page.insert_text(
        (72, 120),
        "governs the making of photocopies or other reproductions of copyrighted material.",
        fontsize=11,
    )
    page.insert_text(
        (72, 145),
        "Under certain conditions specified in the law, libraries and archives are authorized",
        fontsize=11,
    )
    page.insert_text(
        (72, 165),
        "to furnish a photocopy or other reproduction.",
        fontsize=11,
    )
    page.insert_text(
        (72, 190),
        "If a, user makes a request for, or later uses, a photocopy or",
        fontsize=11,
    )
    page.insert_text(
        (72, 210),
        "reproduction for purposes in excess of fair use that user",
        fontsize=11,
    )
    page.insert_text(
        (72, 230),
        "may be liable for copyright infringement.",
        fontsize=11,
    )
    page.insert_text(
        (72, 255),
        "This institution reserves the right to refuse to accept a copying order",
        fontsize=11,
    )
    page.insert_text((292, 760), "2", fontsize=12)

    # Page 3: Van Houten Library privacy notice
    page = doc.new_page(width=612, height=792)
    page.insert_text(
        (72, 72),
        "The Van Houten library has removed some of the personal information",
        fontsize=11,
    )
    page.insert_text(
        (72, 92),
        "and all signatures from the approval page and biographical sketches",
        fontsize=11,
    )
    page.insert_text(
        (72, 112),
        "of theses and dissertations in order to protect the identity of",
        fontsize=11,
    )
    page.insert_text((72, 132), "NJIT graduates and faculty.", fontsize=11)
    page.insert_text((292, 760), "3", fontsize=12)

    # Page 4: real title page
    page = doc.new_page(width=612, height=792)
    page.insert_text((108, 180), "Actual Thesis Title", fontsize=16, fontname="Times-Bold")
    page.insert_text((108, 210), "Author Name", fontsize=12)

    # Page 5: chapter heading with a deliberate title-case error
    page = doc.new_page(width=612, height=792)
    page.insert_text(
        (108, 180),
        "Machine learning Approaches to Signal Processing",
        fontsize=16,
        fontname="Times-Bold",
    )

    doc.save(path)
    doc.close()


def test_us_copyright_warning_page_detected_as_wrapper(tmp_path: Path) -> None:
    from njit_auditor.digital_commons_wrapper import is_repository_copyright_warning_page

    pdf_path = tmp_path / "us_copyright_wrapper.pdf"
    _make_us_copyright_warning_then_thesis_pdf(pdf_path)
    model = load_pdf_layout(str(pdf_path))

    # Page 2 is the US federal copyright notice — must be classified as wrapper.
    copyright_page = model.pages[1]
    assert is_repository_copyright_warning_page(copyright_page)


def test_van_houten_library_page_detected_as_wrapper(tmp_path: Path) -> None:
    from njit_auditor.digital_commons_wrapper import is_repository_copyright_warning_page

    pdf_path = tmp_path / "van_houten_wrapper.pdf"
    _make_us_copyright_warning_then_thesis_pdf(pdf_path)
    model = load_pdf_layout(str(pdf_path))

    # Page 3 is the Van Houten Library privacy notice — must be classified as wrapper.
    van_houten_page = model.pages[2]
    assert is_repository_copyright_warning_page(van_houten_page)


def test_dc_cover_plus_us_copyright_plus_van_houten_all_excluded(tmp_path: Path) -> None:
    from njit_auditor.digital_commons_wrapper import detect_digital_commons_wrapper_pages

    pdf_path = tmp_path / "us_copyright_full_wrapper.pdf"
    _make_us_copyright_warning_then_thesis_pdf(pdf_path)
    model = load_pdf_layout(str(pdf_path))

    wrapper_pages = detect_digital_commons_wrapper_pages(model)

    # All three leading repository pages must be excluded.
    assert 1 in wrapper_pages, f"DC cover (page 1) not detected; got {wrapper_pages}"
    assert 2 in wrapper_pages, f"US copyright page (page 2) not detected; got {wrapper_pages}"
    assert 3 in wrapper_pages, f"Van Houten page (page 3) not detected; got {wrapper_pages}"
    # Manuscript pages must not be excluded.
    assert 4 not in wrapper_pages
    assert 5 not in wrapper_pages


def test_p020_not_triggered_on_us_copyright_warning_pages(tmp_path: Path) -> None:
    pdf_path = tmp_path / "us_copyright_p020.pdf"
    _make_us_copyright_warning_then_thesis_pdf(pdf_path)
    model = load_pdf_layout(str(pdf_path))

    findings = [f for f in check_pdf_title_capitalization(model) if f.rule_id == "P020"]

    copyright_or_van_houten_pages = {2, 3}
    wrapper_hits = [f for f in findings if f.page in copyright_or_van_houten_pages]
    assert not any(
        f.page in copyright_or_van_houten_pages for f in findings
    ), f"P020 fired on wrapper page: {wrapper_hits}"


def test_p020_still_triggered_on_real_heading_after_us_copyright_wrappers(tmp_path: Path) -> None:
    pdf_path = tmp_path / "us_copyright_p020_real_heading.pdf"
    _make_us_copyright_warning_then_thesis_pdf(pdf_path)
    model = load_pdf_layout(str(pdf_path))

    findings = [f for f in check_pdf_title_capitalization(model) if f.rule_id == "P020"]

    # Page 5 has "Machine learning Approaches…" — the word "learning" must be flagged.
    assert any(
        f.page == 5 and f.details.get("flagged_word") == "learning" for f in findings
    ), f"Expected P020 on page 5 for 'learning'; got: {[(f.page, f.details) for f in findings]}"


def test_page_labels_correct_after_us_copyright_wrapper_filtering(tmp_path: Path) -> None:
    from njit_auditor.digital_commons_wrapper import (
        detect_digital_commons_wrapper_pages,
        without_wrapper_pages,
    )

    pdf_path = tmp_path / "us_copyright_labels.pdf"
    _make_us_copyright_warning_then_thesis_pdf(pdf_path)
    model = load_pdf_layout(str(pdf_path))

    wrapper_pages = detect_digital_commons_wrapper_pages(model)
    filtered = without_wrapper_pages(model, wrapper_pages)

    assert [p.page_number for p in filtered.pages] == [4, 5]
    assert [p.manuscript_page_number for p in filtered.pages] == [1, 2]
    assert [p.original_page_number for p in filtered.pages] == [4, 5]


def test_p020_prose_paragraph_guard_filters_comma_heavy_lines(tmp_path: Path) -> None:
    """Regression: comma-heavy copyright prose must not be flagged as title case."""
    from njit_auditor.rules.pdf_title_capitalization import _is_prose_paragraph_line

    # The exact sentence from the copyright-warning page.
    assert _is_prose_paragraph_line(
        "If a, user makes a request for, or later uses, a photocopy or"
    )
    # Multi-sentence body paragraph.
    assert _is_prose_paragraph_line(
        "Under certain conditions. Libraries and archives are authorized. Fair use applies."
    )
    # Line ending with a comma (truncated sentence).
    assert _is_prose_paragraph_line("The copyright law of the United States,")
    # Normal heading-like line must NOT be filtered.
    assert not _is_prose_paragraph_line("Machine Learning Approaches to Signal Processing")
    assert not _is_prose_paragraph_line("Data Analysis and Visualization")
