from pathlib import Path

import pytest
from reportlab.pdfgen.canvas import Canvas

from njit_auditor.audit_runner import run_pdf_audit_full
from njit_auditor.pdf_models import (
    BBox,
    PdfDocument,
    PdfPage,
    PdfTextBlock,
    PdfTextLine,
    PdfTextSpan,
)
from njit_auditor.rules.pdf_lot_lof_entry_type import check_pdf_lot_lof_entry_type


def make_mock_list_doc(lines, page_type="list_of_tables"):
    page = PdfPage(
        page_number=1,
        original_page_index=0,
        original_page_number=1,
        manuscript_page_index=0,
        manuscript_page_number=1,
        width=612.0,
        height=792.0,
        is_visually_landscape=False,
        text_blocks=[],
        graphic_blocks=[],
    )

    header_text = (
        "LIST OF TABLES" if page_type == "list_of_tables" else "LIST OF FIGURES"
    )
    cap_bbox = BBox(x0=108.0, y0=100.0, x1=540.0, y1=115.0)
    span = PdfTextSpan(text=header_text, bbox=cap_bbox)
    line = PdfTextLine(spans=[span], bbox=cap_bbox, text=header_text)
    block = PdfTextBlock(lines=[line], bbox=cap_bbox, text=header_text)
    page.text_blocks.append(block)

    for idx, (text, page_num) in enumerate(lines):
        y0 = 150.0 + idx * 30.0
        y1 = y0 + 12.0
        full_text = f"{text} ..................................... {page_num}"
        bbox = BBox(x0=108.0, y0=y0, x1=540.0, y1=y1)

        span_text = PdfTextSpan(text=text, bbox=BBox(x0=108.0, y0=y0, x1=450.0, y1=y1))
        span_dots = PdfTextSpan(
            text=".....................................",
            bbox=BBox(x0=450.0, y0=y0, x1=500.0, y1=y1),
        )
        span_num = PdfTextSpan(
            text=str(page_num), bbox=BBox(x0=510.0, y0=y0, x1=540.0, y1=y1)
        )

        line = PdfTextLine(
            spans=[span_text, span_dots, span_num], bbox=bbox, text=full_text
        )
        block = PdfTextBlock(lines=[line], bbox=bbox, text=full_text)
        page.text_blocks.append(block)

    doc = PdfDocument(path="mock.pdf", pages=[page])
    return doc


def test_r055_valid_table_prefix():
    """Test valid Table 1.1 entry should not generate finding"""
    doc = make_mock_list_doc(
        [
            ("Table 1.1 Experimental Results", 12),
            ("Table 1.2 Quantitative Analysis", 15),
        ],
        "list_of_tables",
    )
    findings = check_pdf_lot_lof_entry_type(doc)
    assert not any(
        "lot_entry_is_figure" in f.details.get("issue_type", "") for f in findings
    )
    assert not any(
        "lof_entry_is_table" in f.details.get("issue_type", "") for f in findings
    )
    assert not any(
        "lot_entry_missing_table_prefix" in f.details.get("issue_type", "")
        for f in findings
    )


def test_r055_numeric_only_lot_entry_without_column_heading():
    """Keep the advisory when the table column heading is missing."""
    doc = make_mock_list_doc(
        [
            ("1.1 Experimental Results", 12),
            ("1.2 Quantitative Analysis", 15),
        ],
        "list_of_tables",
    )
    findings = check_pdf_lot_lof_entry_type(doc)
    assert any(
        "lot_entry_missing_table_prefix" in f.details.get("issue_type", "")
        for f in findings
    )


def test_r055_cross_type_lot():
    """Test Figure 1.1 in List of Tables should generate wrong-type violation"""
    doc = make_mock_list_doc(
        [
            ("Figure 1.1 Experimental Results", 12),
            ("Table 1.2 Quantitative Analysis", 15),
        ],
        "list_of_tables",
    )
    findings = check_pdf_lot_lof_entry_type(doc)
    assert any(
        "lot_entry_is_figure" in f.details.get("issue_type", "") for f in findings
    )


def test_r055_cross_type_lof():
    """Test Table 1.1 in List of Figures should generate wrong-type violation"""
    doc = make_mock_list_doc(
        [
            ("Table 1.1 Experimental Results", 12),
            ("Figure 1.2 Quantitative Analysis", 15),
        ],
        "list_of_figures",
    )
    findings = check_pdf_lot_lof_entry_type(doc)
    assert any(
        "lof_entry_is_table" in f.details.get("issue_type", "") for f in findings
    )


def test_r055_valid_figure_prefix():
    """Test valid Figure 1.1 entry should not generate finding"""
    doc = make_mock_list_doc(
        [
            ("Figure 1.1 System Architecture", 12),
            ("Figure 1.2 Experimental Setup", 15),
        ],
        "list_of_figures",
    )
    findings = check_pdf_lot_lof_entry_type(doc)
    assert not any(
        "lof_entry_missing_figure_prefix" in f.details.get("issue_type", "")
        for f in findings
    )


def test_r055_numeric_only_lof_entry():
    """Ester 2026-11-17: numeric-only LoF entries are valid"""
    doc = make_mock_list_doc(
        [
            ("1.1 System Architecture", 12),
            ("1.2 Experimental Setup", 15),
        ],
        "list_of_figures",
    )
    findings = check_pdf_lot_lof_entry_type(doc)
    assert findings == []


def _draw_list(
    canvas: Canvas,
    heading: str,
    label: str,
    entries: list[tuple[str, str | None]],
    *,
    label_x: int = 108,
    label_y: int = 670,
    page_label: str = "Page",
    continuation_subtitle: bool = False,
) -> None:
    canvas.setFont("Times-Bold", 12)
    canvas.drawCentredString(324, 710, heading)
    if continuation_subtitle:
        canvas.drawCentredString(324, 690, "(Continued)")
    if label:
        canvas.drawString(label_x, label_y, label)
    if page_label:
        canvas.drawRightString(540, 670, page_label)
    canvas.setFont("Times-Roman", 12)
    for index, (entry, folio) in enumerate(entries):
        y = 638 - 24 * index
        canvas.drawString(108, y, entry)
        canvas.drawString(405, y, "...................")
        if folio:
            canvas.drawRightString(540, y, folio)
    canvas.showPage()


@pytest.mark.parametrize("label", ["Table", "TABLE", "Tables"])
@pytest.mark.parametrize("single_entry", [True, False])
def test_p055_accepts_numeric_lot_entries_under_column_heading(
    tmp_path: Path, label: str, single_entry: bool
) -> None:
    path = tmp_path / "lot.pdf"
    canvas = Canvas(str(path), pagesize=(612, 792))
    rows = [("2.1 Experimental Results", "35")]
    if not single_entry:
        rows.extend([("2.2 Synthetic Inputs", "39"), ("A.1 Appendix Data", "72")])
    _draw_list(canvas, "LIST OF TABLES", label, rows)
    canvas.save()

    findings = run_pdf_audit_full(path)
    assert not [f for f in findings if f.rule_id in {"P031", "P055"}]


@pytest.mark.parametrize(
    ("label", "label_x", "label_y", "heading_issue"),
    [
        ("", 108, 670, "missing_left_column_header"),
        ("Tab.", 108, 670, "missing_left_column_header"),
        ("Figure", 108, 670, "missing_left_column_header"),
        ("Table 2", 108, 670, "missing_left_column_header"),
        ("Table", 440, 670, "left_column_header_misaligned"),
        ("Table", 108, 622, "missing_left_column_header"),
    ],
)
def test_p055_requires_reliable_table_column_heading(
    tmp_path: Path, label: str, label_x: int, label_y: int, heading_issue: str
) -> None:
    path = tmp_path / "ambiguous_lot.pdf"
    canvas = Canvas(str(path), pagesize=(612, 792))
    _draw_list(
        canvas, "LIST OF TABLES", label, [("2.1 Experimental Results", "35")],
        label_x=label_x, label_y=label_y,
    )
    canvas.save()

    findings = run_pdf_audit_full(path)
    issues = {f.details.get("issue_type") for f in findings}
    assert heading_issue in issues
    (prefix,) = [f for f in findings if f.rule_id == "P055"]
    assert prefix.page == 1
    assert prefix.details["issue_type"] == "lot_entry_missing_table_prefix"
    assert prefix.details["bbox"]
    assert prefix.details["entry_id"].startswith("list-entry-")


@pytest.mark.parametrize("label_y", [670, 620])
def test_p055_table_column_ownership_on_split_continuation_heading(
    tmp_path: Path, label_y: int,
) -> None:
    path = tmp_path / "continued-list.pdf"
    canvas = Canvas(str(path), pagesize=(612, 792))
    _draw_list(canvas, "LIST OF TABLES", "Table", [("2.1 Initial Results", "35")])
    _draw_list(
        canvas, "LIST OF TABLES", "Table",
        [("2.2 Continued Results", "36"), ("Figure 2.3 Wrong List", "37")],
        label_y=label_y, continuation_subtitle=True,
    )
    canvas.save()

    findings = [f for f in run_pdf_audit_full(path) if f.rule_id == "P055"]
    issues = {(f.page, f.details["issue_type"]) for f in findings}
    expected = {(2, "lot_entry_is_figure")}
    if label_y == 620:
        expected.add((2, "lot_entry_missing_table_prefix"))
    assert issues == expected
    assert all(f.details.get("bbox") for f in findings)


def test_p055_lot_exemption_leaves_other_checks_active(tmp_path: Path) -> None:
    path = tmp_path / "mixed_lists.pdf"
    canvas = Canvas(str(path), pagesize=(612, 792))
    _draw_list(canvas, "LIST OF TABLES", "Table", [
        ("2.1 Experimental Results", "35"),
        ("2.2 Missing Page Reference", None),
        ("Unnumbered Title.", "37"),
        ("Table 3.4 Synthetic Data", "38"),
        ("Table 3.3 Synthetic Inputs", "39"),
        ("Table 3.2 Synthetic Output", "40"),
        ("Figure 2.3 Wrong List", "41"),
    ])
    _draw_list(canvas, "LIST OF TABLES (Continued)", "Table", [
        ("2.4 A Wrapped Synthetic", None),
        ("    Title with a Page Number", "42"),
        ("2.5 Another Result", "43"),
    ], page_label="")
    _draw_list(canvas, "LIST OF TABLES (Continued)", "", [
        ("2.6 Numeric Entry Without a Column Heading", "44"),
    ])
    _draw_list(canvas, "LIST OF FIGURES", "Figure", [
        ("1.1 Synthetic figure.", "45"),
        ("Table 1.2 Wrong list.", "46"),
    ])
    _draw_list(canvas, "TABLE OF CONTENTS", "Table", [("2.1 Section", "47")])
    canvas.setFont("Times-Roman", 12)
    canvas.drawString(108, 510, "See Table 2.1 and Figure 1.1 for the results.")
    canvas.drawString(108, 486, "See Fig. 1.1 for the control.")
    canvas.drawString(108, 400, "Table 2.1 Synthetic Table Title.")
    canvas.save()

    findings = run_pdf_audit_full(path)
    rule_issues = {(f.page, f.rule_id, f.details.get("issue_type")) for f in findings}
    assert {row for row in rule_issues if row[1] == "P055"} == {
        (1, "P055", "lot_entry_is_figure"),
        (3, "P055", "lot_entry_missing_table_prefix"),
        (4, "P055", "lof_entry_is_table"),
        (6, "P055", "body_figure_reference_abbreviated"),
    }
    assert (1, "P018", "missing_page_number") in rule_issues
    assert (1, "P053", "lot_entry_has_terminal_period") in rule_issues
    assert (1, "P059", "lot_entry_numbers_not_nondecreasing") in rule_issues
    assert (2, "P031", "missing_page_column_header") in rule_issues
    assert (3, "P031", "missing_left_column_header") in rule_issues
    assert (6, "P017", "unexpected_terminal_period") in rule_issues


def test_r055_missing_prefix_suggested_fix_points_to_column_heading():
    """The retained advisory directs students to the column heading."""
    from njit_auditor.polished_comments import resolve_suggested_fix_for_display

    doc = make_mock_list_doc([("1.1 Experimental Setup", 12)])
    (finding,) = check_pdf_lot_lof_entry_type(doc)
    fix = resolve_suggested_fix_for_display(
        finding.rule_id, finding.details["issue_type"],
        existing=finding.details.get("suggested_fix", ""),
    )
    assert "'Table' column heading above the entry numbers" in fix
    assert "before its number" not in fix
    assert "misplaced" not in fix.lower()

    cross_type_fix = resolve_suggested_fix_for_display("P055", "lot_entry_is_figure")
    assert "misplaced entry" in cross_type_fix


def test_r055_public_card_describes_heading_and_body_requirements():
    from njit_auditor.web_app import _build_rule_catalog

    card = next(r for r in _build_rule_catalog()["student_rules"] if r["id"] == "P055")
    assert "body references" in card["title"]
    assert "do not need that prefix" in card["how_to_correct"]
    assert "'Table' column heading may begin with their number" in card["how_to_correct"]
    assert "only a number" in card["what_it_checks"]
    assert "misplaced entries" in card["what_it_checks"]
