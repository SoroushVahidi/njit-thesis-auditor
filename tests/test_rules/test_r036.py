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
            ("1.1 Synthetic Topic A ......... 12", 150.0, 162.0),
            ("1.2 Synthetic Topic B ......... 15", 182.0, 194.0),
        ]
    )
    findings = check_pdf_toc_list_entry_spacing(doc)
    assert not any(
        "spacing_too_tight" in f.details.get("issue_type", "") for f in findings
    )


def test_r036_toc_insufficient_spacing():
    """TOC entries with tight spacing no longer produce a student-facing
    finding under the production page-relative policy. The fixed 1.6 ratio
    is retired as the decisive reporting rule (24 Ester-confirmed false
    positives at ratios 1.00-1.56 contradicted it); positive detection is
    unvalidated on real ground truth, so tight candidates abstain rather
    than report. See
    docs/status/r036_production_page_relative_suppression_design_20260916.md.
    This 2-entry page also has a single eligible gap, so it is a
    sparse-page abstention either way."""
    doc = make_mock_toc_doc(
        [
            ("1.1 Synthetic Topic A ......... 12", 150.0, 162.0),
            ("1.2 Synthetic Topic B ......... 15", 172.0, 184.0),
        ]
    )
    findings = check_pdf_toc_list_entry_spacing(doc)
    assert findings == []


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
            ("Figure 1.1 Synthetic apparatus diagram ......... 12", 150.0, 162.0),
            ("Figure 1.2 Synthetic reaction diagram ......... 15", 182.0, 194.0),
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
            ("1.1 Synthetic Topic A ......... 12", 172.0, 184.0),
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


def test_r036_appendix_to_appendix_peer_transition_not_reported():
    """A top-level-to-top-level peer transition (APPENDIX A -> APPENDIX B)
    is an ordinary peer pair. Under the production page-relative policy it
    is no longer reported on a fixed ratio; the tight candidate abstains
    (no student-facing finding). The structural-exemption distinction
    (deeper-level finishing into a top-level row is exempt) is preserved in
    the reconstruction, but reporting requires a validated true positive,
    which does not yet exist."""
    doc = make_mock_toc_doc(
        [
            ("APPENDIX A", 150.0, 162.0),
            ("APPENDIX B", 172.0, 184.0),
        ]
    )
    findings = check_pdf_toc_list_entry_spacing(doc)
    assert findings == []


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


def test_r036_arbitrary_all_caps_not_reported():
    """Arbitrary all-caps text which is not structural is still *checked*
    (not treated as a structural row), but under the production page-
    relative policy it is not reported on a fixed ratio; the tight
    candidate abstains (no student-facing finding)."""
    doc = make_mock_toc_doc(
        [
            ("ORDINARY CAPS TEXT LINE ......... 12", 150.0, 162.0),
            ("ANOTHER UPPERCASE LINE ......... 15", 172.0, 184.0),
        ]
    )
    findings = check_pdf_toc_list_entry_spacing(doc)
    assert findings == []


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


def test_r036_genuine_tight_gap_after_wrapped_entry_not_reported():
    """A wrapped entry's own internal gap is exempt, and the gap to the
    next distinct entry is *measured* correctly from the wrapped entry's
    true last line. Under the production page-relative policy it is not
    reported on a fixed ratio; the candidate abstains (no student-facing
    finding) because positive detection is unvalidated on real ground
    truth. The grouping still reconstructs the two entries (verified via
    the record count), so this also guards that the fix does not merge the
    wrapped entry with the next one."""
    doc = make_mock_toc_doc(
        [
            ("2.3 A Very Long Section Title That Continues", 150.0, 162.0),
            ("Onto The Next Physical Line Segment ......... 45", 163.0, 175.0),
            ("2.4 Another Distinct Section Title ......... 60", 176.0, 188.0),
        ]
    )
    findings = check_pdf_toc_list_entry_spacing(doc)
    assert findings == []


# ---------------------------------------------------------------------------
# Ester's 2026-09-14 policy clarification regression suite
#
# "The TOC must be double spaced except for titles that run longer than one
# line in which case these titles must be single spaced." The single/double
# pitch values below (13.8pt / 27.6pt at 12pt font) are the exact
# baseline-to-baseline measurements taken from the real Praneeth PDF -- see
# docs/status/r036_toc_wrapped_title_spacing_policy_20260914.md for the full
# forensic derivation.
# ---------------------------------------------------------------------------


def test_r036_wrapped_entry_then_correct_double_spacing_no_warning():
    """Case C: a wrapped (2-line) entry followed by a properly double-spaced
    next entry must not be flagged. Mirrors the real Praneeth page-11
    "1.1 Synthetic Topic A..." / "Continuation..." / "1.2 Synthetic Topic B..."
    sequence exactly (13.8pt single pitch within the
    wrapped entry, 27.6pt = 2x pitch to the next entry)."""
    doc = make_mock_toc_doc(
        [
            ("1.1 Synthetic Topic A With Long Wrapped Text", 169.09, 182.37),
            ("Continuation ......... 12", 182.89, 196.17),
            ("1.2 Synthetic Topic B With Long Text ......... 15", 210.49, 223.77),
        ]
    )
    findings = check_pdf_toc_list_entry_spacing(doc)
    assert not any(
        "toc_inter_entry_spacing_too_tight" in f.details.get("issue_type", "")
        for f in findings
    )


def test_r036_wrapped_entry_then_insufficient_spacing_not_reported():
    """Case C, insufficient variant: the same wrapped entry, but the next
    entry starts only single-spaced (no visible double spacing) after it.
    Under the production page-relative policy this is not reported on a
    fixed ratio; the candidate abstains (no student-facing finding) because
    positive detection is unvalidated on real ground truth."""
    doc = make_mock_toc_doc(
        [
            ("1.1 Synthetic Topic A With Long Wrapped Text", 169.09, 182.37),
            ("Continuation ......... 12", 182.89, 196.17),
            ("1.2 Synthetic Topic B With Long Text ......... 15", 196.69, 209.97),
        ]
    )
    findings = check_pdf_toc_list_entry_spacing(doc)
    assert findings == []


def test_r036_deeper_level_entries_double_spaced_no_warning():
    """Deeper-level (level-3) peer entries with genuine double spacing must
    not be flagged."""
    doc = make_mock_toc_doc(
        [
            ("1.1.1 First Subsection Detail ......... 12", 150.0, 162.0),
            ("1.1.2 Second Subsection Detail ......... 14", 182.0, 194.0),
        ]
    )
    findings = check_pdf_toc_list_entry_spacing(doc)
    assert not any(
        "toc_inter_entry_spacing_too_tight" in f.details.get("issue_type", "")
        for f in findings
    )


def test_r036_deeper_level_entries_insufficient_spacing_not_reported():
    """Deeper-level (level-3) peer entries with insufficient spacing are
    still *checked* (the level-3 depth itself is not an exemption), but
    under the production page-relative policy they are not reported on a
    fixed ratio; the candidate abstains (no student-facing finding)."""
    doc = make_mock_toc_doc(
        [
            ("1.1.1 First Subsection Detail ......... 12", 150.0, 162.0),
            ("1.1.2 Second Subsection Detail ......... 14", 168.0, 180.0),
        ]
    )
    findings = check_pdf_toc_list_entry_spacing(doc)
    assert findings == []


def test_r036_level_change_without_structural_heading_still_checked_not_reported():
    """A level-3-to-level-2 transition with no structural (CHAPTER/APPENDIX/
    REFERENCES/etc.) heading involved -- e.g. "1.2.3" finishing back to an
    ordinary "1.3" peer -- is NOT covered by the structural-boundary
    exemption (only entering a genuine top-level row is) and is still
    *checked*, but under the production page-relative policy it is not
    reported on a fixed ratio; the candidate abstains (no student-facing
    finding)."""
    doc = make_mock_toc_doc(
        [
            ("1.2.3 Study Limitations Detail ......... 49", 150.0, 162.0),
            ("1.3 Next Ordinary Section ......... 50", 168.0, 180.0),
        ]
    )
    findings = check_pdf_toc_list_entry_spacing(doc)
    assert findings == []


def test_r036_references_after_appendix_grouped_separately_not_reported():
    """Regression for a real grouping bug fixed alongside the 2026-09-14
    policy update (Anthony page 12): a short, complete, all-caps structural
    row like "REFERENCES ... 117" immediately following another complete
    structural row like "APPENDIX ... 80" was previously swallowed into the
    preceding entry. APPENDIX and REFERENCES must be recognized as two
    separate entries (verified via the record count); under the production
    page-relative policy the tight gap between them is not reported on a
    fixed ratio and the candidate abstains (no student-facing finding)."""
    doc = make_mock_toc_doc(
        [
            ("APPENDIX ......... 80", 150.0, 162.0),
            ("REFERENCES ......... 117", 168.0, 180.0),
        ]
    )
    findings = check_pdf_toc_list_entry_spacing(doc)
    assert findings == []


def test_r036_unnumbered_allcaps_chapter_title_grouped_correctly_not_reported():
    """Regression for a real grouping bug fixed alongside the 2026-09-14
    policy update (Anthony page 11): an unnumbered, no-"CHAPTER"-prefix,
    ALL-CAPS chapter title that wraps across two physical lines was
    previously swallowed into the PRECEDING, already-complete entry
    a complete numbered entry wrongly absorbing a following unnumbered
    all-caps wrapped chapter title). The fix must recognize the all-caps title as
    a new entry (a real entry split, not a lucky side effect of both
    readings producing the same absent finding); under the production
    page-relative policy the tight gap between them is not reported on a
    fixed ratio and the candidate abstains (no student-facing finding)."""
    doc = make_mock_toc_doc(
        [
            ("2.5 Conclusion ......... 50", 150.0, 162.0),
            ("SYNTHETIC ALL CAPS CHAPTER TITLE THAT WRAPS AS A", 165.0, 178.28),
            (
                "SECOND SYNTHETIC ALL CAPS TITLE LINE ......... 52",
                178.80,
                192.08,
            ),
        ]
    )
    findings = check_pdf_toc_list_entry_spacing(doc)
    assert findings == []


def test_r036_praneeth_page11_real_geometry_all_examples_clean():
    """The 12 actual Praneeth page-11 examples Ester reviewed on 2026-09-14
    ("All of these are False positives"), reproduced with the exact real
    baseline-to-baseline coordinates and text extracted from the real PDF
    (see docs/status/r036_toc_wrapped_title_spacing_policy_20260914.md).
    Every one of these pairs is a genuinely double-spaced (or exempt
    parent-to-first-child) TOC transition; none may be reported.

    R036 findings on the 12 Ester-reviewed cases = 0.
    """
    doc = make_mock_toc_doc(
        [
            ("1    INTRODUCTION…....……………………………………", 141.49, 154.77),
            ("1.1 Synthetic Topic A With Long Wrapped Text", 169.09, 182.37),
            ("Continuation ……………………. ……………………..", 182.89, 196.17),
            ("1.2 Synthetic Topic B With Long Text…………………...", 210.49, 223.77),
            ("1.2.1 Synthetic Subtopic B1 …………………...", 238.12, 251.40),
            ("1.2.2 Synthetic Subtopic B2………", 265.72, 279.00),
            ("1.2.3 Synthetic Subtopic B3…….", 293.32, 306.60),
            ("1.3 Synthetic Topic C……………………. ………….", 320.92, 334.20),
            ("1.3.1 Synthetic Subtopic C1………………...", 348.52, 361.80),
            ("1.3.2 Synthetic Subtopic C2……", 376.12, 389.40),
            ("1.3.3 Synthetic Wrapped Subtopic C3", 403.74, 417.02),
            ("continuation text………………………. ……………….", 417.54, 430.82),
            ("1.3.4 Synthetic Wrapped Subtopic C4", 445.14, 458.42),
            ("continuation text …….……....", 458.94, 472.22),
            ("1.3.5 Synthetic Wrapped Subtopic C5", 486.54, 499.82),
            ("continuation text ….…….", 500.34, 513.62),
            ("1.4 Synthetic Topic D……………………", 527.94, 541.22),
            ("1.4.1 Synthetic Subtopic D1.…....", 555.54, 568.82),
            ("1.4.2 Synthetic Subtopic D2.…....................", 583.17, 596.45),
            ("1.4.3 Synthetic Subtopic D3..", 610.77, 624.05),
            ("1.4.4 Synthetic Subtopic D4 ………", 638.37, 651.65),
        ]
    )
    findings = check_pdf_toc_list_entry_spacing(doc)
    tight = [
        f
        for f in findings
        if "toc_inter_entry_spacing_too_tight" in f.details.get("issue_type", "")
    ]
    assert tight == []
