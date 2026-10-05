"""Regressions for Ester's 2026-10-05 R024 and R045 answers.

R024: List of Tables and List of Figures titles both use title case, and the
two checks carry different codes (R024D for tables, R024E for figures). This
supersedes the earlier List of Figures sentence-case reading of Q074.

R045: single spacing within a publication entry is mandatory and a hanging
indent is optional. Numbering is deliberately not checked yet: Ester's note
("publications and presentations are not numbered") was written about a page
whose entries are visibly labeled [1], [2], so whether entries must or must
not be numbered still needs her clarification.

All text is synthetic.
"""

from __future__ import annotations

import fitz
import pytest

from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.pdf_models import BBox, PdfDocument, PdfPage, PdfTextBlock, PdfTextLine
from njit_auditor.rules.pdf_biosketch_publication_layout import (
    check_pdf_biosketch_publication_layout,
)
from njit_auditor.rules.pdf_toc_list_formatting import check_pdf_toc_list_formatting

# ---------------------------------------------------------------------------
# R024: List of Tables and List of Figures both use title case.
# ---------------------------------------------------------------------------


def _list_doc(heading: str, titles: list[str], prefix: str) -> PdfDocument:
    lines = [PdfTextLine(text=heading, bbox=BBox(x0=220, y0=80, x1=390, y1=94))]
    for index, title in enumerate(titles):
        y = 140.0 + 24.0 * index
        lines.append(
            PdfTextLine(
                text=f"{prefix} {index + 1}.1 {title} .... {index + 2}",
                bbox=BBox(x0=108, y0=y, x1=540, y1=y + 12),
            )
        )
    block = PdfTextBlock(
        lines=lines,
        bbox=BBox(x0=100, y0=80, x1=560, y1=max(line.bbox.y1 for line in lines)),
        text="\n".join(line.text for line in lines),
    )
    page = PdfPage(page_number=16, width=612, height=792, text_blocks=[block])
    return PdfDocument(path="synthetic.pdf", pages=[page])


_TITLE_CASE = [
    "Performance of the Baseline Model on Benchmark Data",
    "Summary of Results Across All Experimental Settings",
    "Overview of the Proposed Evaluation Pipeline",
]
# One lowercase field-convention identifier, like the Muyeed p16 pattern Ester
# called a true violation that the student may choose to ignore.
_LOWERCASE_IDENTIFIER = [
    "Performance of the bert Model on Benchmark Data",
    *_TITLE_CASE[1:],
]
_SENTENCE_CASE = [
    "Performance of the baseline model on benchmark data",
    *_TITLE_CASE[1:],
]


def _p024(doc: PdfDocument) -> list:
    return [f for f in check_pdf_toc_list_formatting(doc) if f.rule_id == "P024"]


def test_lot_title_case_entries_are_clean() -> None:
    assert _p024(_list_doc("LIST OF TABLES", _TITLE_CASE, "Table")) == []


@pytest.mark.parametrize("titles", [_LOWERCASE_IDENTIFIER, _SENTENCE_CASE])
def test_lot_non_title_case_entry_warns(titles: list[str]) -> None:
    findings = _p024(_list_doc("LIST OF TABLES", titles, "Table"))
    assert [f.details["issue_type"] for f in findings] == ["list_of_tables_title_case"]
    assert findings[0].details["entry_index"] == "0"
    assert findings[0].severity.value.lower() == "warning"


def test_lof_title_case_entries_are_clean() -> None:
    assert _p024(_list_doc("LIST OF FIGURES", _TITLE_CASE, "Figure")) == []


@pytest.mark.parametrize("titles", [_LOWERCASE_IDENTIFIER, _SENTENCE_CASE])
def test_lof_non_title_case_entry_warns(titles: list[str]) -> None:
    findings = _p024(_list_doc("LIST OF FIGURES", titles, "Figure"))
    assert [f.details["issue_type"] for f in findings] == ["list_of_figures_title_case"]
    assert findings[0].details["entry_index"] == "0"
    assert findings[0].message.startswith("List of Figures entry")


def test_lot_and_lof_findings_carry_distinct_codes() -> None:
    import njit_auditor.web_app as wa
    from njit_auditor.report_outputs import public_display_rule_id

    lot = _p024(_list_doc("LIST OF TABLES", _SENTENCE_CASE, "Table"))[0]
    lof = _p024(_list_doc("LIST OF FIGURES", _SENTENCE_CASE, "Figure"))[0]
    assert lot.details["page_type"] == "list_of_tables"
    assert lof.details["page_type"] == "list_of_figures"
    assert lot.details["source_q_rule_id"] != lof.details["source_q_rule_id"]

    codes = {
        public_display_rule_id(
            wa._public_rule_reference_id(
                "P024",
                issue_type=f.details["issue_type"],
                source_q_rule_id=f.details["source_q_rule_id"],
            )
        )
        for f in (lot, lof)
    }
    assert codes == {"R024D", "R024E"}


def test_no_list_of_figures_sentence_case_expectation_remains() -> None:
    import njit_auditor.web_app as wa
    from njit_auditor.polished_comments import build_polished_comment
    from njit_auditor.rules import pdf_captions

    cards = {r["id"]: r for r in wa._build_rule_catalog()["student_rules"]}
    lof_card = " ".join(
        (cards["P024E"]["title"], cards["P024E"]["how_to_correct"])
    ).lower()
    assert "title case" in lof_card
    assert "sentence case" not in lof_card
    assert ("P024", "list_of_figures_sentence_case") not in wa._PUBLIC_RULE_ISSUE_REFERENCE
    assert ("list_of_figures", "possible_sentence_case_issue") not in (
        pdf_captions._P017_Q_RULE_MAP
    )
    comment = build_polished_comment(
        rule_id="P024",
        issue_type="list_of_figures_title_case",
        page=11,
        details={"expected_or_reason": "major_word_requires_capital"},
    )
    assert "List of Figures" in comment
    assert "sentence case" not in comment.lower()


def test_p017_no_longer_checks_lof_capitalization() -> None:
    """A title-case List of Figures entry would have tripped P017's old
    sentence-case check; LoF capitalization now belongs to R024E only."""
    from njit_auditor.rules.pdf_captions import check_pdf_captions

    lines = [PdfTextLine(text="LIST OF FIGURES", bbox=BBox(x0=220, y0=80, x1=390, y1=94))]
    for index, title in enumerate(_TITLE_CASE):
        y = 140.0 + 24.0 * index
        lines.append(
            PdfTextLine(
                text=f"Figure {index + 1}.1 {title}.",
                bbox=BBox(x0=108, y0=y, x1=480, y1=y + 12),
            )
        )
    block = PdfTextBlock(
        lines=lines,
        bbox=BBox(x0=100, y0=80, x1=560, y1=200),
        text="\n".join(line.text for line in lines),
    )
    doc = PdfDocument(
        path="synthetic.pdf",
        pages=[PdfPage(page_number=11, width=612, height=792, text_blocks=[block])],
    )
    issue_types = [
        f.details.get("issue_type") for f in check_pdf_captions(doc) if f.rule_id == "P017"
    ]
    assert issue_types == []


# ---------------------------------------------------------------------------
# R045: single spacing mandatory, hanging indent optional, numbering deferred.
# ---------------------------------------------------------------------------


def _publications_pdf(
    path,
    *,
    numbered: bool,
    hanging: bool,
    line_step: float,
    entry_step: float,
    entries: int = 3,
    lines_per_entry: int = 3,
) -> None:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((200, 70), "BIOGRAPHICAL SKETCH", fontsize=14, fontname="Times-Bold")
    page.insert_text((108, 110), "Presentations and Publications:", fontname="Times-Bold")
    y = 136.0
    for index in range(entries):
        for line in range(lines_per_entry):
            text = f"Synthetic publication entry {index + 1} wrapped line {line + 1} text."
            if numbered and line == 0:
                page.insert_text((108, y), f"[{index + 1}]", fontsize=12)
            if numbered:
                x = 132.0
            elif hanging and line > 0:
                x = 144.0
            else:
                x = 108.0
            page.insert_text((x, y), text, fontsize=12)
            y += line_step
        y += entry_step - line_step
    page.insert_text((300, 760), "iv", fontsize=12)
    doc.save(path)
    doc.close()


def _p045(path) -> list[dict[str, str]]:
    return [
        f.details
        for f in check_pdf_biosketch_publication_layout(load_pdf_layout(str(path)))
        if f.rule_id == "P045"
    ]


def test_r045_unnumbered_hanging_entries_single_spaced_are_clean(tmp_path) -> None:
    """The corpus-common style: unnumbered, hanging indent, single-spaced."""
    path = tmp_path / "unnumbered_hanging.pdf"
    _publications_pdf(path, numbered=False, hanging=True, line_step=14.0, entry_step=28.0)
    assert _p045(path) == []


def test_r045_unnumbered_hanging_entries_double_spaced_warn(tmp_path) -> None:
    path = tmp_path / "unnumbered_double.pdf"
    _publications_pdf(path, numbered=False, hanging=True, line_step=24.0, entry_step=40.0)
    findings = _p045(path)
    assert [d["issue_type"] for d in findings] == [
        "biosketch_publication_wrapped_line_spacing_not_single"
    ]
    assert findings[0]["entry_segmentation"] == "hanging_indent"


def test_r045_numbered_entries_without_hanging_indent_are_clean(tmp_path) -> None:
    """Missing hanging indent alone is never a violation."""
    path = tmp_path / "numbered_flush.pdf"
    _publications_pdf(path, numbered=True, hanging=False, line_step=14.0, entry_step=28.0)
    assert _p045(path) == []


def test_r045_numbered_double_spaced_entries_warn_for_spacing_only(tmp_path) -> None:
    path = tmp_path / "numbered_double.pdf"
    _publications_pdf(path, numbered=True, hanging=False, line_step=24.0, entry_step=40.0)
    assert [d["issue_type"] for d in _p045(path)] == [
        "biosketch_publication_wrapped_line_spacing_not_single"
    ]


@pytest.mark.parametrize("numbered", [True, False])
def test_r045_wrapped_continuation_lines_are_not_new_entries(tmp_path, numbered) -> None:
    """Four-line single-spaced entries: if a continuation line were taken as a
    new entry, the blank-line check between entries would fire."""
    path = tmp_path / f"wrapped_{numbered}.pdf"
    _publications_pdf(
        path,
        numbered=numbered,
        hanging=not numbered,
        line_step=14.0,
        entry_step=28.0,
        lines_per_entry=4,
    )
    assert _p045(path) == []


@pytest.mark.parametrize("numbered", [True, False])
def test_r045_numbering_is_not_enforced_while_pending_clarification(
    tmp_path, numbered
) -> None:
    path = tmp_path / f"numbering_{numbered}.pdf"
    _publications_pdf(
        path, numbered=numbered, hanging=not numbered, line_step=14.0, entry_step=28.0
    )
    assert not any("number" in d["issue_type"] for d in _p045(path))


# ---------------------------------------------------------------------------
# R024E calibration: one finding per wrapped List of Figures entry.
# ---------------------------------------------------------------------------

_TITLE_X0 = 108.0
_WRAP_X0 = 135.0
_ROW_STEP = 14.0


def _lof_rows_doc(
    rows: list[tuple[str, float, float]], heading: str = "LIST OF FIGURES"
) -> PdfDocument:
    """Rows are (text, x0, y). Every row ends near the page-number column."""
    lines = [PdfTextLine(text=heading, bbox=BBox(x0=220, y0=80, x1=390, y1=94))]
    lines.extend(
        PdfTextLine(text=text, bbox=BBox(x0=x0, y0=y, x1=540, y1=y + 11))
        for text, x0, y in rows
    )
    block = PdfTextBlock(
        lines=lines,
        bbox=BBox(x0=100, y0=80, x1=560, y1=max(line.bbox.y1 for line in lines)),
        text="\n".join(line.text for line in lines),
    )
    page = PdfPage(page_number=17, width=612, height=792, text_blocks=[block])
    return PdfDocument(path="synthetic.pdf", pages=[page])


def _wrapped_entry(
    number: str, head: str, continuations: list[str], page: str, y: float
) -> tuple[list[tuple[str, float, float]], float]:
    """A wrapped entry whose first row ends on a non-page token (as the
    corpus multi-panel captions do), so the shared repair leaves the
    continuation rows as separate rows."""
    rows = [(f"{number} {head} LC", _TITLE_X0, y)]
    for index, text in enumerate(continuations):
        y += _ROW_STEP
        suffix = f" . . . . . {page}" if index == len(continuations) - 1 else ""
        rows.append((f"{text}{suffix}", _WRAP_X0, y))
    return rows, y + 2 * _ROW_STEP


_CLOSING_ENTRY = ("9.9 Summary of Results Across All Settings . . . 99", _TITLE_X0)


def _lof_findings(rows: list[tuple[str, float, float]]) -> list:
    return [
        f
        for f in check_pdf_toc_list_formatting(_lof_rows_doc(rows))
        if f.details["issue_type"] == "list_of_figures_title_case"
    ]


def _with_closing(rows: list[tuple[str, float, float]], y: float) -> list:
    return [*rows, (_CLOSING_ENTRY[0], _CLOSING_ENTRY[1], y)]


def test_r024e_single_line_title_case_entry_is_clean() -> None:
    rows = [("1.1 Overview of the Proposed Signal Pipeline . . . . 3", _TITLE_X0, 140.0)]
    assert _lof_findings(_with_closing(rows, 168.0)) == []


def test_r024e_single_line_sentence_case_entry_flags_once() -> None:
    rows = [("1.1 Overview of the proposed signal pipeline . . . . 3", _TITLE_X0, 140.0)]
    findings = _lof_findings(_with_closing(rows, 168.0))
    assert [f.details["entry_index"] for f in findings] == ["0"]


def test_r024e_two_line_wrapped_entry_flags_once() -> None:
    rows, y = _wrapped_entry(
        "3.1", "Overview of the proposed method for signal", ["processing in noisy channels"],
        "12", 140.0,
    )
    findings = _lof_findings(_with_closing(rows, y))
    assert len(findings) == 1
    assert findings[0].details["entry_index"] == "0"
    assert findings[0].details["wrapped_line_count"] == "2"


def test_r024e_long_wrapped_entry_flags_once_and_continuations_are_silent() -> None:
    continuations = [f"continuation panel line {i} showing the region" for i in range(10)]
    continuations.append("the final panel region")
    rows, y = _wrapped_entry(
        "3.3", "Scheme showing the sample fraction", continuations, "75", 140.0
    )
    findings = _lof_findings(_with_closing(rows, y))
    assert [f.details["entry_index"] for f in findings] == ["0"]
    assert findings[0].details["wrapped_line_count"] == "12"
    assert "first_word_requires_capital" not in {f.details["expected_or_reason"] for f in findings}


def test_r024e_wrapped_entry_with_math_has_no_fragment_finding() -> None:
    rows, y = _wrapped_entry(
        "4.1",
        "Numerical validation that the shape derivative captures the",
        [
            "O(|e|) behavior when k1 = 1, k2 = 2 and the perturbation",
            "of the disk with w = 5 - 10i",
        ],
        "48",
        140.0,
    )
    findings = _lof_findings(_with_closing(rows, y))
    assert [f.details["entry_index"] for f in findings] == ["0"]


def test_r024e_wrapped_panel_label_entry_is_one_entry_and_quotes_a_real_word() -> None:
    rows, y = _wrapped_entry(
        "3.2",
        "a) Mass spectrum of the control sample; b) Mass",
        ["spectrum of the treated sample"],
        "70",
        140.0,
    )
    findings = _lof_findings(_with_closing(rows, y))
    assert len(findings) == 1
    assert "'a'" not in findings[0].message
    assert "'spectrum'" in findings[0].message


def test_r024e_consecutive_wrapped_entries_stay_distinct() -> None:
    first, y = _wrapped_entry(
        "2.1", "Overview of the proposed method for signal", ["processing in noisy channels"],
        "20", 140.0,
    )
    second, y = _wrapped_entry(
        "2.2", "Comparison of the baseline and proposed", ["filters on benchmark data"], "21", y
    )
    findings = _lof_findings(_with_closing([*first, *second], y))
    assert [f.details["entry_index"] for f in findings] == ["0", "2"]
    assert all(f.details["wrapped_line_count"] == "2" for f in findings)


def test_r024e_unnumbered_row_after_a_closed_entry_is_not_absorbed() -> None:
    """A row below an entry that already ended on its page number starts a
    new entry, even if extraction dropped its figure number."""
    rows = [
        ("3.14 Visualization of Two Sub-Cases for the Proof . . . 62", _TITLE_X0, 140.0),
        ("Plot illustrating the effect of the added term", 137.0, 154.0),
    ]
    findings = _lof_findings(_with_closing(rows, 182.0))
    assert [f.details["entry_index"] for f in findings] == ["1"]
    assert "wrapped_line_count" not in findings[0].details


def test_r024e_wrapped_title_case_entry_is_clean() -> None:
    rows, y = _wrapped_entry(
        "3.1", "Overview of the Proposed Method for Signal", ["Processing in Noisy Channels"],
        "12", 140.0,
    )
    assert _lof_findings(_with_closing(rows, y)) == []


def test_r024d_wrapped_table_entry_also_reports_once_with_distinct_code() -> None:
    rows, y = _wrapped_entry(
        "3.1", "Overview of the proposed method for signal", ["processing in noisy channels"],
        "12", 140.0,
    )
    rows = [(text.replace("3.1 ", "Table 3.1 "), x0, ry) for text, x0, ry in rows]
    findings = [
        f
        for f in check_pdf_toc_list_formatting(
            _lof_rows_doc(_with_closing(rows, y), heading="LIST OF TABLES")
        )
        if f.rule_id == "P024"
    ]
    assert [f.details["issue_type"] for f in findings] == ["list_of_tables_title_case"]
