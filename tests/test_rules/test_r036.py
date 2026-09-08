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


def test_r036_appendix_boundary_exempt_when_finishing_subsection():
    """A section's last entry ending tightly into the next chapter/appendix
    heading is exempt, not a genuine spacing defect -- corrected per an
    Ester-reviewed real case (P036/Anthony p12, "3.5 Conclusion" ->
    "APPENDIX", explicit FALSE_POSITIVE: "the relevant spacing transitions
    involve structural rows such as chapter or appendix headings, and the
    auditor should allow appropriate flexibility rather than treating them
    like ordinary peer entries" -- see
    docs/evaluation/ESTER_FEEDBACK_MIGRATION.md). This test previously
    asserted the opposite (a design assumption made before this reviewed
    evidence was available); see
    test_r036_appendix_to_appendix_still_flagged_when_tight below for the
    boundary this exemption does NOT cover (top-level peer transitions)."""
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


def test_r036_appendix_to_appendix_still_flagged_when_tight():
    """Unlike a subsection finishing into an appendix (exempt, see above),
    a top-level-to-top-level peer transition -- e.g. one appendix directly
    followed by the next -- is an ordinary peer pair and must still be
    flagged when tight. Only a transition where *prev* is at a strictly
    deeper level than the new top-level row is exempt."""
    doc = make_mock_toc_doc(
        [
            ("APPENDIX A", 150.0, 162.0),
            ("APPENDIX B", 172.0, 184.0),
        ]
    )
    findings = check_pdf_toc_list_entry_spacing(doc)
    assert any(
        "toc_inter_entry_spacing_too_tight" in f.details.get("issue_type", "")
        for f in findings
    )


def test_r036_appendix_heading_to_first_child_accepted():
    """An appendix heading immediately followed by its own first entry is
    exempt, same as a chapter heading followed by its first subsection."""
    doc = make_mock_toc_doc(
        [
            ("APPENDIX", 150.0, 162.0),
            ("1.1 Supplementary Data ......... 130", 172.0, 184.0),
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


def test_r036_wrapped_entry_title_not_split_into_two_entries():
    """A single entry whose title wraps onto a second physical line (first
    line has no dot leaders yet, second line finishes with dot leaders and
    a page number) must not be scored as two tightly-spaced entries, even
    though the second physical line's dot-leader shape looks like a new
    entry start in isolation."""
    doc = make_mock_toc_doc(
        [
            ("2.3 A Very Long Section Title That Continues", 150.0, 162.0),
            ("Onto The Next Physical Line Segment ......... 45", 163.0, 175.0),
        ]
    )
    findings = check_pdf_toc_list_entry_spacing(doc)
    assert not any(
        "toc_inter_entry_spacing_too_tight" in f.details.get("issue_type", "")
        for f in findings
    )


def test_r036_genuine_tight_gap_after_wrapped_entry_still_flagged():
    """A wrapped entry's own internal gap must be exempt, but a genuinely
    tight gap between that (now-complete) entry and the NEXT distinct entry
    must still be reported."""
    doc = make_mock_toc_doc(
        [
            ("2.3 A Very Long Section Title That Continues", 150.0, 162.0),
            ("Onto The Next Physical Line Segment ......... 45", 163.0, 175.0),
            ("2.4 Another Distinct Section Title ......... 60", 176.0, 188.0),
        ]
    )
    findings = check_pdf_toc_list_entry_spacing(doc)
    tight = [
        f
        for f in findings
        if "toc_inter_entry_spacing_too_tight" in f.details.get("issue_type", "")
    ]
    assert len(tight) == 1
    assert tight[0].details.get("previous_entry_preview", "").startswith(
        "Onto The Next Physical Line"
    )
