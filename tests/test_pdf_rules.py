from pathlib import Path

import fitz
from typer.testing import CliRunner

from njit_auditor.cli import app
from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.rules.pdf_abstract import check_pdf_abstract_word_count
from njit_auditor.rules.pdf_annotations import run_pdf_annotation_rule
from njit_auditor.rules.pdf_body_spacing import check_pdf_body_spacing
from njit_auditor.rules.pdf_captions import check_pdf_captions
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
from njit_auditor.rules.pdf_margins import run_pdf_margin_rule
from njit_auditor.rules.pdf_page_numbering_regime import check_pdf_page_numbering_regime
from njit_auditor.rules.pdf_page_numbers import (
    check_pdf_page_number_sequence,
    run_pdf_page_number_candidates_rule,
)
from njit_auditor.rules.pdf_spacing import check_pdf_spacing
from njit_auditor.rules.pdf_title_capitalization import (
    check_apa_title_case_phrase,
    check_pdf_title_capitalization,
    is_minor_word,
    looks_like_acronym,
)
from njit_auditor.rules.pdf_toc_alignment import check_pdf_toc_alignment
from njit_auditor.rules.pdf_toc_list_formatting import check_pdf_toc_list_formatting

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
        page.insert_textbox(
            fitz.Rect(0, y - 20, 612, y + 20),
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
