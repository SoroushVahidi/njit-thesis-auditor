from pathlib import Path

import fitz
from typer.testing import CliRunner

from njit_auditor.cli import app
from njit_auditor.pdf_layout import _style_flags_from_font_name, load_pdf_layout
from njit_auditor.pdf_models import BBox, PdfTextLine, PdfTextSpan
from njit_auditor.rules.pdf_abstract import check_pdf_abstract_word_count
from njit_auditor.rules.pdf_annotations import run_pdf_annotation_rule
from njit_auditor.rules.pdf_body_spacing import check_pdf_body_spacing
from njit_auditor.rules.pdf_captions import check_pdf_captions
from njit_auditor.rules.pdf_copyright_page import check_pdf_copyright_page
from njit_auditor.rules.pdf_font_compliance import (
    check_pdf_font_compliance,
    classify_font,
)
from njit_auditor.rules.pdf_frontmatter_no_page_number import (
    check_pdf_frontmatter_no_page_number,
)
from njit_auditor.rules.pdf_frontmatter_structure import check_pdf_frontmatter_structure
from njit_auditor.rules.pdf_heading_levels import (
    _is_all_caps_phrase,
    _looks_like_title_case_violation,
    check_pdf_heading_level_styles,
)
from njit_auditor.rules.pdf_headings import check_named_frontmatter_headings
from njit_auditor.rules.pdf_indentation import check_pdf_indentation
from njit_auditor.rules.pdf_lot_lof_column_headers import check_pdf_lot_lof_column_headers
from njit_auditor.rules.pdf_margins import run_pdf_margin_rule
from njit_auditor.rules.pdf_page_numbering_regime import check_pdf_page_numbering_regime
from njit_auditor.rules.pdf_page_numbers import (
    check_pdf_page_number_sequence,
    run_pdf_page_number_candidates_rule,
)
from njit_auditor.rules.pdf_spacing import check_pdf_spacing
from njit_auditor.rules.pdf_title_capitalization import (
    _is_math_font,
    _spans_bold_reason,
    check_apa_title_case_phrase,
    check_pdf_title_capitalization,
    is_minor_word,
    looks_like_acronym,
)
from njit_auditor.rules.pdf_title_consistency import (
    _collect_title_candidates,
    _extract_below_heading_candidate,
    check_pdf_title_consistency,
)
from njit_auditor.rules.pdf_toc_alignment import check_pdf_toc_alignment
from njit_auditor.rules.pdf_toc_continued_headings import check_pdf_toc_continued_headings
from njit_auditor.rules.pdf_toc_list_formatting import check_pdf_toc_list_formatting
from njit_auditor.rules.pdf_toc_list_wrapped_spacing import check_pdf_toc_list_wrapped_spacing

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

    page1 = next(f for f in warnings if f.page == 1)
    assert page1.details.get("issue_type") == "page_number_candidate"
    assert page1.details.get("candidate_count_on_page") == "2"
    assert page1.details.get("candidate_sample")
    assert page1.details.get("confidence") in {"low", "medium"}

    page2 = next(f for f in warnings if f.page == 2)
    assert page2.details.get("candidate_count_on_page") == "1"


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


def test_annotation_extraction_detects_comment(tmp_path: Path) -> None:
    pdf_path = tmp_path / "annot.pdf"
    _make_pdf_with_annotation(pdf_path)
    findings = run_pdf_annotation_rule(str(pdf_path))
    assert findings
    assert any(f.rule_id == "P012" for f in findings)


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
    pdf_path = tmp_path / "indent_abstract_bad.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((250, 90), "ABSTRACT", fontsize=16, fontname="Times-Bold")
    _draw_paragraph(page, first_x=190, rest_x=108, y=140)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_indentation(model)
    warning = next(f for f in findings if f.rule_id == "P015")
    assert warning.details.get("issue_type") == "unexpected_opening_indent"
    assert warning.details.get("expected") == "flush_left"


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


def test_pdf_cli_command_runs(tmp_path: Path) -> None:
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
    assert "P015" in result.output


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
    pdf_path = tmp_path / "spacing_grouped.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((250, 90), "ABSTRACT", fontsize=16, fontname="Times-Bold")
    _draw_spacing_lines(page, [140, 154, 230, 244, 320, 334])
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    warnings = [
        f
        for f in check_pdf_spacing(model)
        if f.rule_id == "P016" and f.details.get("issue_type") == "excessive_line_gap"
    ]
    assert len(warnings) == 1
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
    assert any(f.details.get("issue_type") == "misaligned_page_number_column" for f in warnings)


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
    assert any(f.details.get("issue_type") == "missing_page_number" for f in warnings)


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
    assert any(f.details.get("issue_type") == "inconsistent_leader_dots" for f in warnings)


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
    assert any(f.details.get("issue_type") == "inconsistent_hierarchy_indent" for f in warnings)


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
        add_second_numbers={1: ("99", 520)},
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


def test_pdf_cli_handles_unreadable_pdf_gracefully(tmp_path: Path) -> None:
    pdf_path = tmp_path / "broken.pdf"
    pdf_path.write_text("not a pdf")
    result = runner.invoke(app, ["pdf", str(pdf_path)])
    assert result.exit_code == 1
    assert "Unable to read PDF" in result.output


# ---------------------------------------------------------------------------
# P020: Title-case capitalization — helper unit tests
# ---------------------------------------------------------------------------


def test_p020_minor_word_detection() -> None:
    for word in ("a", "an", "the", "and", "but", "or", "for", "nor", "as",
                 "at", "by", "in", "of", "on", "per", "to", "up", "via"):
        assert is_minor_word(word), f"'{word}' should be a minor word"
    for word in ("machine", "learning", "with", "from", "into", "over"):
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
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    for y, text in lines:
        page.insert_text((108, y), text, fontsize=12)
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
    # Non-bold heading at 14pt with title-case violation.
    page.insert_text(
        (108, 380), "the results and discussion methods", fontsize=14, fontname="tiro"
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
