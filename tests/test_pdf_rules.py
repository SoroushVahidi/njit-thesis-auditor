from pathlib import Path

import fitz
from typer.testing import CliRunner

from njit_auditor.cli import app
from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.rules.pdf_annotations import run_pdf_annotation_rule
from njit_auditor.rules.pdf_headings import check_named_frontmatter_headings
from njit_auditor.rules.pdf_margins import run_pdf_margin_rule
from njit_auditor.rules.pdf_page_numbers import run_pdf_page_number_candidates_rule

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


def test_pdf_cli_command_runs(tmp_path: Path) -> None:
    pdf_path = tmp_path / "cli.pdf"
    _make_pdf_with_heading(pdf_path, text="Abstract", x=120, y=220, fontname="Times-Roman")
    result = runner.invoke(app, ["pdf", str(pdf_path)])
    assert result.exit_code == 0
    assert "PDF Layout Findings" in result.output
    assert "P014" in result.output


def test_pdf_cli_handles_unreadable_pdf_gracefully(tmp_path: Path) -> None:
    pdf_path = tmp_path / "broken.pdf"
    pdf_path.write_text("not a pdf")
    result = runner.invoke(app, ["pdf", str(pdf_path)])
    assert result.exit_code == 1
    assert "Unable to read PDF" in result.output
