from njit_auditor.pdf_models import (
    BBox,
    PdfDocument,
    PdfPage,
    PdfTextBlock,
    PdfTextLine,
    PdfTextSpan,
)
from njit_auditor.rules.pdf_toc_list_entry_spacing import check_pdf_toc_list_entry_spacing


def make_mock_toc_doc(lines_with_y, page_type="table_of_contents"):
    # Create page model matching standard parameters
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

    # Header block matching the page_type
    header_text = "TABLE OF CONTENTS"
    if page_type == "list_of_tables":
        header_text = "LIST OF TABLES"
    elif page_type == "list_of_figures":
        header_text = "LIST OF FIGURES"

    cap_bbox = BBox(x0=108.0, y0=100.0, x1=540.0, y1=115.0)
    span = PdfTextSpan(text=header_text, bbox=cap_bbox)
    line = PdfTextLine(spans=[span], bbox=cap_bbox, text=header_text)
    block = PdfTextBlock(lines=[line], bbox=cap_bbox, text=header_text)
    page.text_blocks.append(block)

    # Populate the entry lines
    for text, y0, y1 in lines_with_y:
        bbox = BBox(x0=108.0, y0=y0, x1=540.0, y1=y1)
        span = PdfTextSpan(text=text, bbox=bbox)
        line = PdfTextLine(spans=[span], bbox=bbox, text=text)
        block = PdfTextBlock(lines=[line], bbox=bbox, text=text)
        page.text_blocks.append(block)

    doc = PdfDocument(path="mock.pdf", pages=[page])
    return doc


def test_r036_toc_acceptable_spacing():
    """TOC entries with sufficient spacing (ratio >= 1.4) must pass"""
    doc = make_mock_toc_doc(
        [
            ("1.1 Biological Importance ......... 12", 150.0, 162.0),
            ("1.2 Protein Quantification ......... 15", 182.0, 194.0),
        ]
    )
    findings = check_pdf_toc_list_entry_spacing(doc)
    assert not any(
        "spacing_too_tight" in f.details.get("issue_type", "") for f in findings
    )


def test_r036_toc_insufficient_spacing():
    """TOC entries with tight spacing (ratio < 1.4) must trigger finding"""
    doc = make_mock_toc_doc(
        [
            ("1.1 Biological Importance ......... 12", 150.0, 162.0),
            ("1.2 Protein Quantification ......... 15", 172.0, 184.0),
        ]
    )
    findings = check_pdf_toc_list_entry_spacing(doc)
    assert any(
        "toc_inter_entry_spacing_too_tight" in f.details.get("issue_type", "")
        for f in findings
    )


def test_r036_lot_acceptable_spacing():
    """LoT entries with sufficient spacing must pass"""
    doc = make_mock_toc_doc(
        [
            ("Table 1.1 Experimental Results ......... 12", 150.0, 162.0),
            ("Table 1.2 Quantitative Analysis ......... 15", 182.0, 194.0),
        ],
        page_type="list_of_tables",
    )
    findings = check_pdf_toc_list_entry_spacing(doc)
    assert not any(
        "spacing_too_tight" in f.details.get("issue_type", "") for f in findings
    )


def test_r036_lof_acceptable_spacing():
    """LoF entries with sufficient spacing must pass"""
    doc = make_mock_toc_doc(
        [
            ("Figure 1.1 Mass Spectrometry System ......... 12", 150.0, 162.0),
            ("Figure 1.2 Reaction Microdroplets ......... 15", 182.0, 194.0),
        ],
        page_type="list_of_figures",
    )
    findings = check_pdf_toc_list_entry_spacing(doc)
    assert not any(
        "spacing_too_tight" in f.details.get("issue_type", "") for f in findings
    )


def test_r036_chapter_boundary_accepted():
    """TOC chapter structural rows should be ignored from spacing checks"""
    doc = make_mock_toc_doc(
        [
            ("1     INTRODUCTION", 150.0, 162.0),
            ("1.1 Biological Importance ......... 12", 172.0, 184.0),
        ]
    )
    findings = check_pdf_toc_list_entry_spacing(doc)
    assert not any(
        "toc_inter_entry_spacing_too_tight" in f.details.get("issue_type", "")
        for f in findings
    )


def test_r036_appendix_boundary_accepted():
    """TOC appendix structural rows should be ignored from spacing checks"""
    doc = make_mock_toc_doc(
        [
            ("3.5 Conclusion ......... 77", 150.0, 162.0),
            ("APPENDIX", 172.0, 184.0),
        ]
    )
    findings = check_pdf_toc_list_entry_spacing(doc)
    assert not any(
        "toc_inter_entry_spacing_too_tight" in f.details.get("issue_type", "")
        for f in findings
    )


def test_r036_arbitrary_all_caps_not_exempted():
    """Arbitrary all-caps text which is not structural must trigger if tight"""
    doc = make_mock_toc_doc(
        [
            ("ORDINARY CAPS TEXT LINE ......... 12", 150.0, 162.0),
            ("ANOTHER UPPERCASE LINE ......... 15", 172.0, 184.0),
        ]
    )
    findings = check_pdf_toc_list_entry_spacing(doc)
    assert any(
        "toc_inter_entry_spacing_too_tight" in f.details.get("issue_type", "")
        for f in findings
    )
