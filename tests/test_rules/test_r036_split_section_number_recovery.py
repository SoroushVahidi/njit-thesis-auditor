"""Regression tests for the split-leading-section-number recovery fix
(``_reassemble_split_row_fragments`` in pdf_toc_list_wrapped_spacing.py).

Background: on some real TOC pages (LaTeX tocloft-style layout), PyMuPDF's
text extraction splits one visual row -- number, title, page number -- into
separate line objects sharing one baseline. A lone number fragment was
previously discarded as noise, breaking both entry-boundary detection and
the structural parent-to-first-child spacing exemption. See
docs/status/r036_split_section_number_recovery_20260914.md for the full
forensic derivation (Muyeed "7"/"CONTROLLING NEURAL NETWORK
GENERALIZATION...", Patrick "2.2"/"Scattering by Two Elastic Disks...",
Youra "1.1"/"Solar Wind...").
"""

from njit_auditor.pdf_models import (
    BBox,
    PdfDocument,
    PdfPage,
    PdfTextBlock,
    PdfTextLine,
    PdfTextSpan,
)
from njit_auditor.rules.pdf_toc_list_entry_spacing import check_pdf_toc_list_entry_spacing
from njit_auditor.rules.pdf_toc_list_wrapped_spacing import _reassemble_split_row_fragments


def _line(
    text: str,
    x0: float,
    y0: float,
    x1: float | None = None,
    y1: float | None = None,
) -> PdfTextLine:
    bbox = BBox(
        x0=x0,
        y0=y0,
        x1=x1 if x1 is not None else x0 + len(text) * 6.0,
        y1=y1 if y1 is not None else y0 + 12.0,
    )
    span = PdfTextSpan(text=text, bbox=bbox)
    return PdfTextLine(spans=[span], bbox=bbox, text=text)


def _merged_texts(lines: list[PdfTextLine]) -> list[str]:
    return [line.text for line in _reassemble_split_row_fragments(lines)]


# ---------------------------------------------------------------------------
# 1-6: each of the real detached-number shapes reattaches correctly.
# ---------------------------------------------------------------------------


def test_detached_bare_chapter_number_7_reattaches():
    lines = [
        _line("7", x0=108.36, y0=622.77, x1=114.22),
        _line("CONTROLLINGNEURALNETWORKGENERALIZATION.......", x0=124.75, y0=622.77),
    ]
    result = _merged_texts(lines)
    assert result == ["7 CONTROLLINGNEURALNETWORKGENERALIZATION......."]


def test_detached_level2_number_7_1_reattaches():
    lines = [
        _line("7.1", x0=124.75, y0=646.38, x1=139.72),
        _line("Introduction................................", x0=151.68, y0=646.38),
    ]
    result = _merged_texts(lines)
    assert result == ["7.1 Introduction................................"]


def test_detached_number_2_2_reattaches():
    lines = [
        _line("2.2", x0=124.39, y0=487.30, x1=139.36),
        _line("ScatteringbyTwoElasticDisksofFluidWave.............", x0=151.32, y0=487.30),
    ]
    result = _merged_texts(lines)
    assert result == ["2.2 ScatteringbyTwoElasticDisksofFluidWave............."]


def test_detached_number_2_2_1_reattaches():
    lines = [
        _line("2.2.1", x0=151.31, y0=510.91, x1=175.39),
        _line("Fourierseriessolution.......................", x0=186.45, y0=510.91),
    ]
    result = _merged_texts(lines)
    assert result == ["2.2.1 Fourierseriessolution......................."]


def test_detached_number_1_1_reattaches():
    lines = [
        _line("1.1", x0=125.10, y0=163.02, x1=140.06),
        _line(
            "SolarWind-Magnetosphere-IonosphereCouplingastheFramework",
            x0=152.59,
            y0=163.02,
        ),
    ]
    result = _merged_texts(lines)
    assert result == ["1.1 SolarWind-Magnetosphere-IonosphereCouplingastheFramework"]


def test_detached_number_1_1_1_reattaches():
    lines = [
        _line("1.1.1", x0=152.59, y0=200.99, x1=176.67),
        _line("Solar-windforcingofgeospace..................", x0=188.46, y0=200.99),
    ]
    result = _merged_texts(lines)
    assert result == ["1.1.1 Solar-windforcingofgeospace.................."]


# ---------------------------------------------------------------------------
# 9-11: negative cases -- must NOT merge.
# ---------------------------------------------------------------------------


def test_page_number_fragment_not_attached_as_prefix():
    """A pure page-number column (far right, large x0) must never be
    treated as a hierarchy-number prefix or merged onto anything -- only
    the leading number (small x0, immediately left of the title) merges."""
    lines = [
        _line("7", x0=108.36, y0=622.77, x1=114.22),
        _line("CONTROLLINGNEURALNETWORKGENERALIZATION.......", x0=124.75, y0=622.77, x1=511.47),
        _line("120", x0=522.81, y0=622.77, x1=540.38),
    ]
    result = _merged_texts(lines)
    assert result == [
        "7 CONTROLLINGNEURALNETWORKGENERALIZATION.......",
        "120",
    ]


def test_dot_leader_fragment_not_mistaken_for_hierarchy_prefix():
    """A pure dot-leader run must never itself be treated as a hierarchy
    number (it has no digits), and must merge onto the title as a
    trailing suffix, not a leading prefix."""
    lines = [
        _line("1 INTRODUCTION", x0=125.10, y0=139.40, x1=200.0),
        _line("...............................", x0=231.33, y0=139.69),
    ]
    result = _merged_texts(lines)
    assert result == ["1 INTRODUCTION ..............................."]


def test_legitimate_unnumbered_heading_left_unchanged():
    """A genuinely unnumbered structural heading with no plausible number
    fragment anywhere nearby must pass through unchanged."""
    lines = [_line("REFERENCES ......................................", x0=108.0, y0=300.0)]
    result = _merged_texts(lines)
    assert result == ["REFERENCES ......................................"]


def test_two_adjacent_number_shaped_fragments_not_concatenated():
    """Two number-shaped fragments on the same row with no distinct title
    fragment between them (e.g. a stray numeral before a page number)
    must never be concatenated into one bogus hierarchy number."""
    lines = [
        _line("7", x0=108.0, y0=100.0, x1=114.0),
        _line("120", x0=522.0, y0=100.0, x1=540.0),
    ]
    result = sorted(_merged_texts(lines))
    assert result == ["120", "7"]


def test_number_too_far_from_title_not_merged():
    """A number-shaped fragment far to the left of the title (beyond
    MAX_NUMBER_TO_TITLE_GAP_PT) must not be merged -- only a genuinely
    adjacent tab-stop column counts."""
    lines = [
        _line("7", x0=50.0, y0=100.0, x1=56.0),
        _line("Some Title Text.......................", x0=200.0, y0=100.0),
    ]
    result = _merged_texts(lines)
    assert result == ["7", "Some Title Text......................."]


def test_two_distinct_title_fragments_on_same_row_left_untouched():
    """A row with more than one primary (non-number, non-dot-leader)
    fragment has no unambiguous title to merge onto -- must be left
    completely alone rather than guessing."""
    lines = [
        _line("Alpha Title", x0=108.0, y0=100.0, x1=180.0),
        _line("Beta Title", x0=200.0, y0=100.0, x1=280.0),
    ]
    result = _merged_texts(lines)
    assert sorted(result) == ["Alpha Title", "Beta Title"]


# ---------------------------------------------------------------------------
# 7-8: integration -- recovered numbering feeds the real detector correctly.
# ---------------------------------------------------------------------------


def _make_mock_toc_doc_with_columns(rows, page_type="table_of_contents"):
    """Like test_r036.make_mock_toc_doc, but each row is a list of
    (text, x0, y0, y1) tuples -- allowing a row to be split across
    multiple same-baseline fragments, to simulate a detached number
    column."""
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
    header_text = "TABLE OF CONTENTS"
    cap_bbox = BBox(x0=108.0, y0=100.0, x1=540.0, y1=115.0)
    header_span = PdfTextSpan(text=header_text, bbox=cap_bbox)
    header_line = PdfTextLine(spans=[header_span], bbox=cap_bbox, text=header_text)
    page.text_blocks.append(PdfTextBlock(lines=[header_line], bbox=cap_bbox, text=header_text))

    for row in rows:
        for text, x0, y0, y1 in row:
            bbox = BBox(x0=x0, y0=y0, x1=x0 + len(text) * 6.0, y1=y1)
            span = PdfTextSpan(text=text, bbox=bbox)
            line = PdfTextLine(spans=[span], bbox=bbox, text=text)
            page.text_blocks.append(PdfTextBlock(lines=[line], bbox=bbox, text=text))

    return PdfDocument(path="mock.pdf", pages=[page])


def test_recovered_parent_to_first_child_is_exempt():
    """A chapter heading whose leading number was detached, immediately
    followed by its own first (also detached-numbered) child subsection,
    must be recognized as a parent-to-first-child transition and exempt
    from the spacing check -- even though genuinely tight."""
    doc = _make_mock_toc_doc_with_columns(
        [
            [("6.9 Conclusion ......... 50", 151.68, 150.0, 162.0)],
            [
                ("7", 108.36, 172.0, 184.0),
                ("CONTROLLING NEURAL NETWORK GENERALIZATION ....... 51", 124.75, 172.0, 184.0),
            ],
            [
                ("7.1", 124.75, 176.0, 188.0),
                ("Introduction ....... 51", 151.68, 176.0, 188.0),
            ],
        ]
    )
    findings = check_pdf_toc_list_entry_spacing(doc)
    assert not any(
        "toc_inter_entry_spacing_too_tight" in f.details.get("issue_type", "") for f in findings
    )


def test_recovered_same_level_peers_recognized_not_reported():
    """Two same-level peer entries whose leading numbers were both detached
    must still be recognized as ordinary peers (not exempt). Under the
    production page-relative policy the tight gap between them is not
    reported on a retired fixed ratio; the candidate abstains (no
    student-facing finding). The record count (2 eligible gaps: the
    recovered peer gap plus the one to the implicit next boundary) and the
    entry previews confirm the split-section-number recovery is intact."""
    from njit_auditor.rules.r036_production_page_relative_spacing import (
        classify_r036_spacing_candidates,
    )

    doc = _make_mock_toc_doc_with_columns(
        [
            [
                ("2.2", 124.39, 150.0, 162.0),
                ("Scattering by Two Disks of Fluid Wave ......... 25", 151.32, 150.0, 162.0),
            ],
            [
                ("2.3", 124.39, 166.0, 178.0),
                ("Numerical validation of the boundary ......... 26", 151.32, 166.0, 178.0),
            ],
        ]
    )
    findings = check_pdf_toc_list_entry_spacing(doc)
    assert findings == []
    records = classify_r036_spacing_candidates(doc)
    assert any(r["entry_pair_index"] == 0 for r in records)
    prev_texts = {r["previous_entry"] for r in records}
    assert any(t.startswith("2.2") for t in prev_texts)
    next_texts = {r["next_entry"] for r in records}
    assert any(t.startswith("2.3") for t in next_texts)
