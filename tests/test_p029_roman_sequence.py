from pathlib import Path

import fitz
from typer.testing import CliRunner

from njit_auditor.cli import app
from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.rules.pdf_page_numbering_regime import check_pdf_page_numbering_regime
from njit_auditor.rules.pdf_roman_sequence import check_pdf_roman_sequence

runner = CliRunner()


def _make_pdf_with_page_numbers(
    path: Path,
    texts: list[str | None],
    x: float = 300,
    y: float = 770,
    add_chapter: bool = False,
    abstract_at: int | None = None,
    heading_at: int | None = None,
    heading_text: str = "TABLE OF CONTENTS",
) -> None:
    doc = fitz.open()
    for idx, txt in enumerate(texts):
        page = doc.new_page(width=612, height=792)
        if txt is not None:
            page.insert_text((x, y), txt, fontsize=12)
        if abstract_at is not None and idx == abstract_at:
            page.insert_text((250, 90), "ABSTRACT", fontsize=16, fontname="Times-Bold")
        if heading_at is not None and idx == heading_at:
            # place heading near top centered
            page.insert_textbox(
                fitz.Rect(0, 70, 612, 110),
                heading_text,
                fontsize=16,
                fontname="Times-Bold",
                align=1,
            )
    if add_chapter:
        page = doc.new_page(width=612, height=792)
        page.insert_text((100, 100), "CHAPTER 1 INTRODUCTION", fontsize=16)
    doc.save(path)
    doc.close()



def test_p029_no_warning_for_correct_roman_sequence(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p029_ok.pdf"
    _make_pdf_with_page_numbers(pdf_path, ["i", "ii", "iii"], add_chapter=True, heading_at=0)
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_roman_sequence(model)
    assert not any(f.rule_id == "P029" for f in findings)


def test_p029_gap_detected_for_missing_middle_number(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p029_gap.pdf"
    _make_pdf_with_page_numbers(pdf_path, ["i", None, "iii"], add_chapter=True, heading_at=0)
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_roman_sequence(model)
    assert any(
        f.rule_id == "P029" and f.details.get("issue_type") == "roman_sequence_gap"
        for f in findings
    )


def test_p029_repeat_detected(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p029_repeat.pdf"
    _make_pdf_with_page_numbers(pdf_path, ["i", "ii", "ii"], add_chapter=True, heading_at=0)
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_roman_sequence(model)
    assert any(
        f.rule_id == "P029" and f.details.get("issue_type") == "roman_sequence_repeat"
        for f in findings
    )


def test_p029_decrease_detected(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p029_decrease.pdf"
    _make_pdf_with_page_numbers(pdf_path, ["iii", "ii"], add_chapter=True, heading_at=0)
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_roman_sequence(model)
    assert any(
        f.rule_id == "P029" and f.details.get("issue_type") == "roman_sequence_decrease"
        for f in findings
    )


def test_p029_too_few_candidates_no_warning(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p029_few.pdf"
    _make_pdf_with_page_numbers(pdf_path, ["i", "ii"], add_chapter=True, heading_at=0)
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_roman_sequence(model)
    assert not any(f.rule_id == "P029" for f in findings)


def test_p029_ignores_arabic_frontmatter(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p029_arabic.pdf"
    _make_pdf_with_page_numbers(pdf_path, ["1", "2", "3"], add_chapter=True, heading_at=0)
    model = load_pdf_layout(str(pdf_path))
    regime_findings = check_pdf_page_numbering_regime(model)
    p029_findings = check_pdf_roman_sequence(model)
    assert any(f.rule_id == "P028" for f in regime_findings)
    assert not any(f.rule_id == "P029" for f in p029_findings)


def test_p029_ignores_body_roman_numerals(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p029_body_roman.pdf"
    # First page is chapter -> body start, subsequent pages are body
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((100, 100), "CHAPTER 1 INTRODUCTION", fontsize=16)
    page = doc.new_page(width=612, height=792)
    page.insert_text((300, 770), "i", fontsize=12)
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    p029_findings = check_pdf_roman_sequence(model)
    assert not any(f.rule_id == "P029" for f in p029_findings)


def test_p029_allows_skip_over_no_number_pages(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p029_skip_nonumber.pdf"
    _make_pdf_with_page_numbers(
        pdf_path,
        ["i", None, "ii"],
        add_chapter=True,
        abstract_at=1,
        heading_at=0,
    )
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_roman_sequence(model)
    # should not flag gap because the skipped page is a recognized no-number page
    assert not any(f.rule_id == "P029" for f in findings)


def test_p029_implausible_high_value_roman_suppressed(tmp_path: Path) -> None:
    # "m" (=1000) is a valid Roman numeral but implausibly large for a front-matter page number.
    # It should be excluded from the P029 sequence so it cannot produce false positives.
    pdf_path = tmp_path / "p029_high_value.pdf"
    # Sequence: i, ii, m (=1000 — TOC/noise artifact), iii
    _make_pdf_with_page_numbers(
        pdf_path, ["i", "ii", "m", "iii"], add_chapter=True, heading_at=0
    )
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_roman_sequence(model)
    # "m" should be excluded by the max-plausible-value guard; i→ii→iii sequence is valid.
    assert not any(f.rule_id == "P029" for f in findings), (
        "Implausibly large Roman numeral 'M' (1000) should not produce P029 findings"
    )


def test_p029_cm_value_roman_suppressed(tmp_path: Path) -> None:
    # "cm" (=900) — another implausibly large Roman numeral, suppressed by the guard.
    pdf_path = tmp_path / "p029_cm.pdf"
    _make_pdf_with_page_numbers(
        pdf_path, ["i", "ii", "cm", "iii"], add_chapter=True, heading_at=0
    )
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_roman_sequence(model)
    assert not any(f.rule_id == "P029" for f in findings), (
        "'cm' (900) should be excluded from P029 sequence checks"
    )


def test_p029_real_gap_after_high_value_artifact_still_warns(tmp_path: Path) -> None:
    # Even with an artifact present, a real gap in the remaining sequence should warn.
    pdf_path = tmp_path / "p029_gap_with_artifact.pdf"
    # Sequence: i, m (artifact), i, iii — i then iii is a gap that should still warn.
    _make_pdf_with_page_numbers(
        pdf_path, ["i", "m", "i", "iii"], add_chapter=True, heading_at=0
    )
    model = load_pdf_layout(str(pdf_path))
    findings = check_pdf_roman_sequence(model)
    # After removing "m", remaining sequence is i, i, iii → repeat then gap → at least one warning
    assert any(f.rule_id == "P029" for f in findings), (
        "Real sequence issues after artifact removal should still produce P029 warnings"
    )


def test_p029_cli_and_reports_include_findings(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p029_cli.pdf"
    json_out = tmp_path / "data" / "evaluation" / "generated" / "p029_roman_sequence" / "out.json"
    md_out = tmp_path / "data" / "evaluation" / "generated" / "p029_roman_sequence" / "out.md"
    json_out.parent.mkdir(parents=True, exist_ok=True)
    _make_pdf_with_page_numbers(pdf_path, ["i", None, "iii"], add_chapter=True, heading_at=0)
    result = runner.invoke(
        app,
        ["pdf", str(pdf_path), "--json-out", str(json_out), "--md-out", str(md_out)],
    )
    assert result.exit_code == 0
    assert "P029" in result.output
    assert json_out.exists()
    assert md_out.exists()
    content = json_out.read_text(encoding="utf-8")
    assert "P029" in content
    md_text = md_out.read_text(encoding="utf-8")
    # Markdown is student-facing and shows the Rxxx display id (see
    # public_display_rule_id); the JSON export above keeps the internal P029.
    assert "### R029" in md_text
