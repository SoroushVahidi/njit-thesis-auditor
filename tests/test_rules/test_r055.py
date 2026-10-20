import pytest

from njit_auditor.highlight_targeting import parse_highlight_bboxes_from_details
from njit_auditor.pdf_highlight import is_drawable_bbox
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


def test_r055_numeric_only_lot_entry():
    """Test numeric-only LoT entry should generate missing Table prefix finding"""
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
    """Test numeric-only LoF entry should generate missing Figure prefix finding"""
    doc = make_mock_list_doc(
        [
            ("1.1 System Architecture", 12),
            ("1.2 Experimental Setup", 15),
        ],
        "list_of_figures",
    )
    findings = check_pdf_lot_lof_entry_type(doc)
    assert any(
        "lof_entry_missing_figure_prefix" in f.details.get("issue_type", "")
        for f in findings
    )


@pytest.mark.parametrize(
    ("page_type", "entry_text", "issue_type"),
    [
        ("list_of_tables", "Figure 1.1 Synthetic result", "lot_entry_is_figure"),
        ("list_of_tables", "1.1 Synthetic result", "lot_entry_missing_table_prefix"),
        ("list_of_figures", "Table 1.1 Synthetic result", "lof_entry_is_table"),
        ("list_of_figures", "1.1 Synthetic result", "lof_entry_missing_figure_prefix"),
    ],
)
def test_r055_finding_highlights_offending_entry(
    page_type: str, entry_text: str, issue_type: str
) -> None:
    doc = make_mock_list_doc(
        [(entry_text, 12), ("Figure 1.2 Valid entry", 13)], page_type
    )
    finding = next(
        f for f in check_pdf_lot_lof_entry_type(doc)
        if f.details["issue_type"] == issue_type
    )
    boxes = parse_highlight_bboxes_from_details(finding.details)
    assert len(boxes) == 1
    assert is_drawable_bbox(boxes[0])
    assert boxes[0] == (108.0, 150.0, 540.0, 162.0)


def test_r055_missing_prefix_suggested_fix_names_the_prefix():
    """Ester (2026-09-04): entries need the literal Table/Figure prefix.

    A numeric-only entry is not a misplaced entry, so its suggested fix must
    ask for the prefix rather than reuse the cross-type "move" remediation.
    """
    from njit_auditor.polished_comments import resolve_suggested_fix_for_display

    for section, issue_type, word in (
        ("list_of_tables", "lot_entry_missing_table_prefix", "Table"),
        ("list_of_figures", "lof_entry_missing_figure_prefix", "Figure"),
    ):
        doc = make_mock_list_doc(
            [("1.1 System Architecture", 12), ("1.2 Experimental Setup", 15)],
            section,
        )
        finding = next(
            f
            for f in check_pdf_lot_lof_entry_type(doc)
            if f.details.get("issue_type") == issue_type
        )
        fix = resolve_suggested_fix_for_display(
            "P055", issue_type, existing=finding.details.get("suggested_fix", "")
        )
        assert f"with the word '{word}' before its number" in fix
        assert "misplaced" not in fix.lower()

    cross_type_fix = resolve_suggested_fix_for_display("P055", "lot_entry_is_figure")
    assert "misplaced entry" in cross_type_fix


def test_r055_public_card_describes_prefix_requirement():
    from njit_auditor.web_app import _build_rule_catalog

    card = next(r for r in _build_rule_catalog()["student_rules"] if r["id"] == "P055")
    for text in (card["title"], card["how_to_correct"]):
        assert "'Table'" in text and "'Figure'" in text
    assert "only a number" in card["what_it_checks"]
    assert "misplaced entry" in card["what_it_checks"]
