from pathlib import Path

import fitz
from typer.testing import CliRunner

from njit_auditor.cli import app
from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.rules.pdf_annotations import run_pdf_annotation_rule
from njit_auditor.rules.pdf_headings import check_named_frontmatter_headings
from njit_auditor.rules.pdf_indentation import check_pdf_indentation
from njit_auditor.rules.pdf_margins import run_pdf_margin_rule
from njit_auditor.rules.pdf_page_numbers import run_pdf_page_number_candidates_rule
from njit_auditor.rules.pdf_spacing import check_pdf_spacing

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


def test_pdf_cli_handles_unreadable_pdf_gracefully(tmp_path: Path) -> None:
    pdf_path = tmp_path / "broken.pdf"
    pdf_path.write_text("not a pdf")
    result = runner.invoke(app, ["pdf", str(pdf_path)])
    assert result.exit_code == 1
    assert "Unable to read PDF" in result.output
