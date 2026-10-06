"""Ester's 2026-10-05 adjudications (R011, R018, R024, R040, R045).

Synthetic shapes only; no dissertation text. Each test names the reviewed
pattern it guards, not the private document.
"""

from __future__ import annotations

from njit_auditor.pdf_models import (
    BBox,
    PdfDocument,
    PdfPage,
    PdfTextBlock,
    PdfTextLine,
    PdfTextSpan,
)
from njit_auditor.rules.pdf_toc_alignment import check_pdf_toc_alignment


def _doc(heading: str, rows: list[tuple[str, float, float, float]]) -> PdfDocument:
    lines = [PdfTextLine(text=heading, bbox=BBox(x0=220, y0=80, x1=390, y1=94))]
    lines.extend(
        PdfTextLine(text=text, bbox=BBox(x0=x0, y0=y, x1=x1, y1=y + 12))
        for text, x0, x1, y in rows
    )
    block = PdfTextBlock(
        lines=lines,
        bbox=BBox(x0=100, y0=80, x1=560, y1=max(line.bbox.y1 for line in lines)),
        text="\n".join(line.text for line in lines),
    )
    page = PdfPage(page_number=1, width=612, height=792, text_blocks=[block])
    return PdfDocument(path="synthetic.pdf", pages=[page])


# ---------------------------------------------------------------------------
# R018: a full-width List of Figures entry with no leader dots still warns.
# ---------------------------------------------------------------------------


def _lof_leader_rows(full_width_title: str) -> list[tuple[str, float, float, float]]:
    return [
        ("Figure 3.1 First synthetic result. . . . . . . . . . . . . 40", 108, 540, 140),
        (full_width_title, 108, 540, 164),
        ("Figure 3.3 Third synthetic result. . . . . . . . . . . . . 42", 108, 540, 188),
        ("Figure 3.4 Fourth synthetic result. . . . . . . . . . . . 43", 108, 540, 212),
        ("Figure 3.5 Fifth synthetic result. . . . . . . . . . . . . 44", 108, 540, 236),
    ]


def test_r018_full_width_lof_entry_without_leaders_still_warns() -> None:
    """Ester (2026-10-05): a List of Figures entry whose title runs right up to
    the page-number column with no leader dots, among dotted neighbors, is a
    true R018D violation. Lack of room for leaders is not an exemption."""
    doc = _doc(
        "LIST OF FIGURES",
        _lof_leader_rows(
            "Figure 3.2 A synthetic title long enough to reach the page column 41"
        ),
    )
    findings = [
        f
        for f in check_pdf_toc_alignment(doc)
        if f.rule_id == "P018" and f.details.get("issue_type") == "inconsistent_leader_dots"
    ]
    assert len(findings) == 1
    assert findings[0].details["page_type"] == "list_of_figures"
    assert findings[0].details["worst_entry_index"] == "1"


def test_r018_dotted_full_width_entry_does_not_warn() -> None:
    doc = _doc(
        "LIST OF FIGURES",
        _lof_leader_rows("Figure 3.2 A synthetic title long enough. . . . . . . . 41"),
    )
    assert not any(
        f.details.get("issue_type") == "inconsistent_leader_dots"
        for f in check_pdf_toc_alignment(doc)
        if f.rule_id == "P018"
    )


def test_r018_leader_finding_maps_to_list_leader_card() -> None:
    import njit_auditor.web_app as wa

    card_id = wa._public_rule_reference_id(
        "P018", issue_type="inconsistent_leader_dots", source_q_rule_id="Q052"
    )
    assert card_id == "P018D"
    cards = {r["id"]: r for r in wa._build_rule_catalog()["student_rules"]}
    title = cards["P018D"]["title"]
    assert "List of Tables" in title and "List of Figures" in title
    assert "Table of Contents" not in title


# ---------------------------------------------------------------------------
# R024: List of Tables -> R024D, List of Figures -> R024E.
# ---------------------------------------------------------------------------


def _lot_rows(first_title: str) -> list[tuple[str, float, float, float]]:
    return [
        (first_title, 108, 540, 140),
        ("Table 2.2 Synthetic Results for the Second Experiment . . . . . . . . 21", 108, 540, 164),
        ("Table 2.3 Synthetic Results for the Third Experiment . . . . . . . . 22", 108, 540, 188),
    ]


def test_r024_lowercase_code_identifier_in_lot_title_still_warns() -> None:
    """Ester (2026-10-05): a lowercase field-convention identifier in a List of
    Tables title does not satisfy title case. The auditor flags it; the student
    may choose to ignore it. It must not be silently suppressed."""
    from njit_auditor.rules.pdf_toc_list_formatting import check_pdf_toc_list_formatting

    doc = _doc(
        "LIST OF TABLES",
        _lot_rows("Table 2.1 Baseline: Search over max_depth for Synthetic Models . . . . 20"),
    )
    findings = [f for f in check_pdf_toc_list_formatting(doc) if f.rule_id == "P024"]
    assert [f.details["issue_type"] for f in findings] == ["list_of_tables_title_case"]
    assert findings[0].details["source_q_rule_id"] == "Q065"
    assert findings[0].details["entry_index"] == "0"


def test_r024_correct_title_case_lot_entry_does_not_warn() -> None:
    from njit_auditor.rules.pdf_toc_list_formatting import check_pdf_toc_list_formatting

    doc = _doc(
        "LIST OF TABLES",
        _lot_rows("Table 2.1 Baseline Search over Depth for Synthetic Models . . . . 20"),
    )
    assert not [f for f in check_pdf_toc_list_formatting(doc) if f.rule_id == "P024"]


def test_r024_lot_and_lof_findings_map_to_distinct_visible_cards() -> None:
    import njit_auditor.web_app as wa
    from njit_auditor.report_outputs import public_display_rule_id

    lot = wa._public_rule_reference_id(
        "P024", issue_type="list_of_tables_title_case", source_q_rule_id="Q065"
    )
    lof = wa._public_rule_reference_id(
        "P024", issue_type="list_of_figures_title_case", source_q_rule_id="Q074"
    )
    assert (lot, lof) == ("P024D", "P024E")
    # Without the Q-rule detail (older stored reports) the mapping still holds.
    assert wa._public_rule_reference_id("P024", issue_type="list_of_tables_title_case") == "P024D"
    assert (
        wa._public_rule_reference_id("P024", issue_type="list_of_figures_title_case")
        == "P024E"
    )
    assert public_display_rule_id(lot) == "R024D"
    assert public_display_rule_id(lof) == "R024E"

    cards = {r["id"]: r for r in wa._build_rule_catalog()["student_rules"]}
    assert "P024" not in cards  # the ambiguous parent stays hidden
    assert "List of Tables" in cards["P024D"]["title"]
    assert "title case" in cards["P024D"]["title"]
    assert "List of Figures" in cards["P024E"]["title"]
    assert "title case" in cards["P024E"]["title"]
    assert "sentence case" not in cards["P024E"]["title"]
    assert cards["P024D"]["title"] != cards["P024E"]["title"]
    assert wa._public_rule_reference_href(
        "P024", issue_type="list_of_tables_title_case"
    ).endswith("#P024D")
    assert wa._public_rule_reference_href(
        "P024", issue_type="list_of_figures_title_case"
    ).endswith("#P024E")


# ---------------------------------------------------------------------------
# R040: a gap then spaced leader dots is not terminal punctuation.
# ---------------------------------------------------------------------------


def _lof_punct_rows(first: str) -> list[tuple[str, float, float, float]]:
    return [
        (first, 108, 540, 140),
        ("Figure 2.2 Second synthetic title. . . . . . . . . . . . 22", 108, 540, 164),
        ("Figure 2.3 Third synthetic title. . . . . . . . . . . . . 23", 108, 540, 188),
    ]


def _r040_issues(first: str) -> list[str]:
    from njit_auditor.rules.pdf_lof_terminal_punctuation import (
        check_pdf_lof_terminal_punctuation,
    )

    doc = _doc("LIST OF FIGURES", _lof_punct_rows(first))
    return [
        f.details["page_entry_index"]
        for f in check_pdf_lof_terminal_punctuation(doc)
        if f.rule_id == "P040"
    ]


def test_r040_gap_then_spaced_leaders_is_missing_punctuation() -> None:
    """Ester (2026-10-05) confirmed this List of Figures shape lacks terminal
    punctuation: the first spaced leader dot after a gap is not a period."""
    from njit_auditor.rules.pdf_lof_terminal_punctuation import _strip_trailing_lof_dot_leaders

    assert (
        _strip_trailing_lof_dot_leaders("Synthetic equation title (2.6) . . . . . . . .")
        == "Synthetic equation title (2.6)"
    )
    assert _r040_issues("Figure 2.1 Synthetic equation title (2.6) . . . . . . . . 21") == [
        "0"
    ]


def test_r040_wrapped_title_gap_then_spaced_leaders_warns() -> None:
    """The reviewed pattern is a wrapped entry whose final line is a citation
    in parentheses, a gap, and LaTeX-style spaced leaders."""
    from njit_auditor.rules.pdf_lof_terminal_punctuation import (
        check_pdf_lof_terminal_punctuation,
    )

    doc = _doc(
        "LIST OF FIGURES",
        [
            ("Figure 2.7 Synthetic model problem stated in Relation (2.4),", 108, 540, 140),
            ("Relation (2.5), and Relation (2.6) . . . . . . . . . 30", 129, 540, 154.3),
            ("Figure 2.8 Second synthetic title. . . . . . . . . . . . 31", 108, 540, 180),
            ("Figure 2.9 Third synthetic title. . . . . . . . . . . . 31", 108, 540, 204),
        ],
    )
    findings = [f for f in check_pdf_lof_terminal_punctuation(doc) if f.rule_id == "P040"]
    assert len(findings) == 1


def test_r040_attached_period_before_leaders_is_punctuation() -> None:
    from njit_auditor.rules.pdf_lof_terminal_punctuation import _strip_trailing_lof_dot_leaders

    assert _strip_trailing_lof_dot_leaders("Synthetic title (2.6). . . . . .") == (
        "Synthetic title (2.6)."
    )
    assert _strip_trailing_lof_dot_leaders("Synthetic title.……………") == "Synthetic title."
    assert _r040_issues("Figure 2.1 Synthetic equation title (2.6). . . . . . . . 21") == []


def test_r040_lone_period_before_unicode_leaders_still_counts() -> None:
    """The 2026-09-19 leader-placement shape (title, gap, period, Unicode
    leaders) keeps its period; its gap is owned by R018S, not R040."""
    from njit_auditor.rules.pdf_lof_terminal_punctuation import _strip_trailing_lof_dot_leaders

    assert _strip_trailing_lof_dot_leaders("Synthetic title .……………") == "Synthetic title."
    assert _strip_trailing_lof_dot_leaders("Synthetic title ·······") == "Synthetic title"


# ---------------------------------------------------------------------------
# R045: hanging indent optional; single spacing within entries mandatory;
# numbering prohibited (Ester 2026-10-06), so numbered shapes also report it.
# ---------------------------------------------------------------------------


def _biosketch_pdf(
    path,
    *,
    entries: int = 2,
    lines_per_entry: int = 3,
    line_step: float,
    entry_step: float,
    label_style: str = "separate",
) -> None:
    """Numbered publication entries whose text is flush-aligned under the
    first line's text (no hanging indent), like the reviewed Patrick page."""
    import fitz

    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((200, 70), "BIOGRAPHICAL SKETCH", fontsize=14, fontname="Times-Bold")
    page.insert_text((108, 96), "Undergraduate and Graduate Education:", fontname="Times-Bold")
    page.insert_text((140, 116), "Synthetic degree line for the education list.", fontsize=12)
    page.insert_text((108, 150), "Presentations and Publications:", fontname="Times-Bold")
    y = 176.0
    for index in range(entries):
        for line in range(lines_per_entry):
            text = f"Synthetic publication entry {index + 1} wrapped line {line + 1} text."
            if line == 0 and label_style == "separate":
                page.insert_text((114, y), f"[{index + 1}]", fontsize=12)
            if line == 0 and label_style == "inline":
                text = f"[{index + 1}] {text}"
                page.insert_text((114, y), text, fontsize=12)
            else:
                page.insert_text((138, y), text, fontsize=12)
            y += line_step
        y += entry_step - line_step
    page.insert_text((300, 760), "iv", fontsize=12)
    doc.save(path)
    doc.close()


def _r045(path) -> list[dict[str, str]]:
    from njit_auditor.pdf_layout import load_pdf_layout
    from njit_auditor.rules.pdf_biosketch_publication_layout import (
        check_pdf_biosketch_publication_layout,
    )

    return [
        f.details
        for f in check_pdf_biosketch_publication_layout(load_pdf_layout(str(path)))
        if f.rule_id == "P045"
    ]


def test_r045_patrick_style_double_spaced_numbered_entries_warn_for_spacing(tmp_path) -> None:
    """Ester (2026-10-05): numbered entries with no hanging indent, double-spaced
    within each entry. Single spacing is mandatory (warn); the missing hanging
    indent is acceptable (never warn). Labels extracted as separate lines.
    Since 2026-10-06 the numbering itself is also reported."""
    path = tmp_path / "patrick_style.pdf"
    _biosketch_pdf(path, line_step=24.0, entry_step=29.0)
    findings = _r045(path)
    assert [d["issue_type"] for d in findings] == [
        "biosketch_publication_entry_numbered",
        "biosketch_publication_wrapped_line_spacing_not_single",
    ]
    assert findings[1]["entry_segmentation"] == "entry_labels"
    assert findings[1]["source_q_rule_id"] == "Q028"


def test_r045_inline_labels_double_spaced_entries_warn_for_spacing(tmp_path) -> None:
    path = tmp_path / "inline_labels.pdf"
    _biosketch_pdf(path, line_step=24.0, entry_step=29.0, label_style="inline")
    assert [d["issue_type"] for d in _r045(path)] == [
        "biosketch_publication_entry_numbered",
        "biosketch_publication_wrapped_line_spacing_not_single",
    ]


def test_r045_single_spaced_numbered_entries_without_hanging_indent_report_only_numbering(
    tmp_path,
) -> None:
    path = tmp_path / "single_spaced.pdf"
    _biosketch_pdf(path, line_step=14.0, entry_step=28.0)
    assert [d["issue_type"] for d in _r045(path)] == ["biosketch_publication_entry_numbered"]


def test_r045_blank_line_check_runs_without_hanging_indent(tmp_path) -> None:
    """Single-spaced numbered entries with no blank line between them still warn
    for Q028 spacing, independent of any hanging indent."""
    path = tmp_path / "no_blank_line.pdf"
    _biosketch_pdf(path, entries=3, line_step=14.0, entry_step=14.0)
    findings = _r045(path)
    assert [d["issue_type"] for d in findings] == [
        "biosketch_publication_entry_numbered",
        "biosketch_publication_entry_spacing_not_double",
    ]
    assert findings[1]["entry_segmentation"] == "entry_labels"


def test_r045_education_section_is_not_checked(tmp_path) -> None:
    """Only the Publications/Presentations section is inspected."""
    import fitz

    path = tmp_path / "education_only.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((200, 70), "BIOGRAPHICAL SKETCH", fontsize=14, fontname="Times-Bold")
    page.insert_text((108, 96), "Undergraduate and Graduate Education:", fontname="Times-Bold")
    for index, y in enumerate((120.0, 134.0, 160.0, 174.0)):
        x = 123.0 if index % 2 == 0 else 138.0
        page.insert_text((x, y), "Synthetic degree and institution line for testing.")
    doc.save(path)
    doc.close()
    assert _r045(path) == []


def test_r045_public_wording_no_longer_requires_hanging_indent() -> None:
    import njit_auditor.web_app as wa
    from njit_auditor.polished_comments import build_polished_comment

    card = {r["id"]: r for r in wa._build_rule_catalog()["student_rules"]}["P045"]
    text = " ".join((card["title"], card["what_it_checks"], card["how_to_correct"])).lower()
    assert "single-spaced" in text or "single-space" in text
    assert "hanging indent is optional" in text
    assert "use the required layout: hanging indent" not in text

    comment = build_polished_comment(
        rule_id="P045",
        issue_type="biosketch_publication_wrapped_line_spacing_not_single",
        page=5,
        details={"observed_line_pitch_points": "23.9", "font_size_points": "12.0"},
    )
    assert "single-spaced" in comment
    assert "23.9pt apart for 12.0pt text" in comment
    assert "hanging" not in comment.lower()


# ---------------------------------------------------------------------------
# R011: final reference/DOI line on a references page (Ester: not a violation).
# ---------------------------------------------------------------------------


def _span_line(text: str, box: tuple[float, float, float, float], size: float = 12.0):
    bbox = BBox(x0=box[0], y0=box[1], x1=box[2], y1=box[3])
    return PdfTextLine(text=text, bbox=bbox, spans=[PdfTextSpan(text=text, bbox=bbox, size=size)])


def _margin_page(*lines: PdfTextLine) -> PdfDocument:
    block = PdfTextBlock(
        lines=list(lines),
        bbox=BBox(x0=100, y0=70, x1=560, y1=760),
        text=" ".join(line.text for line in lines),
    )
    page = PdfPage(page_number=28, width=612, height=792, text_blocks=[block])
    return PdfDocument(path="synthetic.pdf", pages=[page])


_REFERENCE_BODY = (
    _span_line("[4] A. Author and B. Author, Synthetic reference title, vol. 1, 2001.",
               (108, 645.7, 535, 661.8)),
    _span_line("[5] C. Author, Another synthetic reference title, Synthetic Press,",
               (108, 672.9, 535, 689.0)),
    _span_line("[6] D. Author and E. Author, A third synthetic reference entry title",
               (108, 699.5, 535.4, 715.6)),
    _span_line("in a synthetic journal name, vol. 3, no. 4, pp. 5-6, 1991, doi:",
               (133.2, 713.3, 526.0, 729.4)),
)
_FINAL_DOI_LINE = _span_line("10.0000/synthetic.0001.", (133.2, 727.1, 255.2, 743.2))
_PAGE_NUMBER = _span_line("9", (318.0, 740.7, 333.0, 757.3))


def _bottom_warnings(doc: PdfDocument) -> list:
    from njit_auditor.rules.pdf_margins import run_pdf_margin_rule

    return [
        f
        for f in run_pdf_margin_rule(doc)
        if f.severity.value == "WARNING" and f.details.get("side") == "bottom_margin"
    ]


def test_r011_references_page_final_doi_line_is_not_flagged() -> None:
    """Ester (2026-10-05): the final reference/DOI line about 7pt below the
    margin (box ending about 23pt below) above the page number is not a
    bottom-margin violation."""
    doc = _margin_page(*_REFERENCE_BODY, _FINAL_DOI_LINE, _PAGE_NUMBER)
    assert _bottom_warnings(doc) == []


def test_r011_references_heading_page_final_line_is_not_flagged() -> None:
    heading = _span_line("REFERENCES", (270, 80, 342, 96))
    body = [
        _span_line(line.text.split("] ", 1)[-1], (133.2, line.bbox.y0, 520, line.bbox.y1))
        for line in _REFERENCE_BODY
    ]
    doc = _margin_page(heading, *body, _FINAL_DOI_LINE, _PAGE_NUMBER)
    assert _bottom_warnings(doc) == []


def test_r011_same_geometry_on_prose_page_still_warns() -> None:
    prose = [
        _span_line("Ordinary synthetic paragraph text that fills one body line here.",
                   (108, y0, 535, y0 + 16.1))
        for y0 in (658.1, 685.7, 713.3)
    ]
    final = _span_line("closing words of the paragraph.", (108, 727.1, 255.2, 743.2))
    assert _bottom_warnings(_margin_page(*prose, final, _PAGE_NUMBER))


def test_r011_same_geometry_on_contents_page_still_warns() -> None:
    heading = _span_line("TABLE OF CONTENTS (Continued)", (210, 82, 400, 98))
    doc = _margin_page(heading, *_REFERENCE_BODY, _FINAL_DOI_LINE, _PAGE_NUMBER)
    assert _bottom_warnings(doc)


def test_r011_deeper_references_bleed_still_warns() -> None:
    lower_top = _span_line("10.0000/synthetic.0001.", (133.2, 729.6, 255.2, 743.6))
    assert _bottom_warnings(_margin_page(*_REFERENCE_BODY, lower_top, _PAGE_NUMBER))
    taller = _span_line("10.0000/synthetic.0001.", (133.2, 727.1, 255.2, 745.0))
    assert _bottom_warnings(_margin_page(*_REFERENCE_BODY, taller, _PAGE_NUMBER))


def test_r011_references_line_running_into_page_number_still_warns() -> None:
    footer_number = _span_line("9", (318.0, 733.0, 333.0, 749.0))
    assert _bottom_warnings(_margin_page(*_REFERENCE_BODY, _FINAL_DOI_LINE, footer_number))
    # No page number below the line: the shape cannot be confirmed.
    assert _bottom_warnings(_margin_page(*_REFERENCE_BODY, _FINAL_DOI_LINE))


def test_r011_references_line_that_is_not_the_last_text_still_warns() -> None:
    trailing = _span_line("Synthetic footer note text.", (133.2, 738.0, 300.0, 750.0))
    doc = _margin_page(*_REFERENCE_BODY, _FINAL_DOI_LINE, trailing, _PAGE_NUMBER)
    assert _bottom_warnings(doc)


def test_r011_detached_line_below_references_block_still_warns() -> None:
    """A line not continuing the single-spaced block (large step) still warns."""
    body = _REFERENCE_BODY[:3]
    doc = _margin_page(*body, _FINAL_DOI_LINE, _PAGE_NUMBER)
    assert _bottom_warnings(doc)


def test_r011_references_right_margin_18pt_still_warns() -> None:
    """Ester's confirmed Patrick reference entry, about 18pt past the right margin."""
    from njit_auditor.rules.pdf_margins import run_pdf_margin_rule

    entry = _span_line("[7] A. Author, An unbreakable synthetic reference title.",
                       (137.9, 304.7, 558.0, 316.7))
    doc = _margin_page(*_REFERENCE_BODY[:2], entry, _PAGE_NUMBER)
    assert any(
        f.severity.value == "WARNING" and f.details.get("side") == "right_margin"
        for f in run_pdf_margin_rule(doc)
    )
