"""Synthetic regression cases for the November TOC rule clarifications."""

from __future__ import annotations

import json
from pathlib import Path

import fitz
import pytest

from njit_auditor.pdf_highlight import build_highlighted_pdf
from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.pdf_models import BBox, PdfPage, PdfTextLine, PdfTextSpan
from njit_auditor.report_outputs import audit_findings_to_json_dict
from njit_auditor.report_view import build_report_view
from njit_auditor.rules.pdf_toc_alignment import (
    TocEntryLine,
    TocPageContext,
    detect_toc_like_pages,
    extract_toc_entry_lines,
    is_isolated_terminal_grid_leader_dot,
)
from njit_auditor.rules.pdf_toc_terminal_period import (
    _check_toc_terminal_period_page,
    check_pdf_toc_terminal_period,
)
from njit_auditor.rules.pdf_toc_title_structure import check_pdf_toc_title_structure
from njit_auditor.web_app import _highlight_boxes_by_page


def _span(text: str, x0: float, x1: float) -> PdfTextSpan:
    return PdfTextSpan(
        text=text,
        font="Times-Roman",
        size=12.0,
        bold=False,
        italic=False,
        bbox=BBox(x0=x0, y0=140, x1=x1, y1=153),
    )


def _entry(title: str, dot_x: float, *, with_spans: bool = True) -> TocEntryLine:
    spans = (
        [_span(title, 72, 310), _span(".", dot_x, dot_x + 4), _span("1", 500, 508)]
        if with_spans
        else []
    )
    line = PdfTextLine(
        text=f"{title} . 1",
        bbox=BBox(x0=72, y0=140, x1=508, y1=153),
        spans=spans,
    )
    return TocEntryLine(
        line=line,
        cleaned_text=line.text,
        page_number_token="1",
        page_number_right_x=508,
        indent_x=72,
        has_leader_dots=False,
    )


@pytest.mark.parametrize(
    ("title", "dot_x", "with_spans", "expected"),
    [
        ("Chapter 1 Synthetic Topic", 400, True, 0),
        ("Chapter 1 Synthetic Topic", 314, True, 0),
        ("Chapter 1 Synthetic Topic", 400, False, 0),
        ("Chapter 1 Synthetic Topic.", 400, True, 1),
        ("Chapter 1 Synthetic Topic.", 309, True, 0),
        ("Chapter 1 Synthetic Topic.", 400, False, 0),
    ],
)
def test_p054_single_dot_geometry_and_ambiguous_extraction(
    title: str, dot_x: float, with_spans: bool, expected: int
) -> None:
    page = PdfPage(page_number=3, width=612, height=792, text_blocks=[])
    context = TocPageContext(page, "table_of_contents", 100)
    entry = _entry(title, dot_x, with_spans=with_spans)
    assert len(_check_toc_terminal_period_page(context, [entry], 0)) == expected


def test_p054_attached_title_period_still_warns() -> None:
    line = PdfTextLine(
        text="Chapter 1 Synthetic Topic. 1",
        bbox=BBox(x0=72, y0=140, x1=508, y1=153),
        spans=[_span("Chapter 1 Synthetic Topic.", 72, 310), _span("1", 500, 508)],
    )
    entry = TocEntryLine(
        line=line,
        cleaned_text=line.text,
        page_number_token="1",
        page_number_right_x=508,
        indent_x=72,
        has_leader_dots=False,
    )
    page = PdfPage(page_number=3, width=612, height=792, text_blocks=[])
    context = TocPageContext(page, "table_of_contents", 100)
    assert len(_check_toc_terminal_period_page(context, [entry], 0)) == 1


def test_p054_geometry_distinguishes_leader_when_extraction_loses_space() -> None:
    page = PdfPage(page_number=3, width=612, height=792)
    context = TocPageContext(page, "table_of_contents", 100)
    entry = _entry("Chapter 1 Synthetic Topic.", 400)
    entry.cleaned_text = "Chapter 1 Synthetic Topic.. 1"
    finding, = _check_toc_terminal_period_page(context, [entry], 0)
    assert finding.details["bbox"] == "72.0,140.0,310.0,153.0"


@pytest.fixture
def mixed_dot_toc(tmp_path: Path) -> Path:
    """Separate text operators reproduce both historical one-dot cases."""
    path = tmp_path / "mixed_dot_toc.pdf"
    with fitz.open() as doc:
        doc.new_page()
        page = doc.new_page(width=612, height=792)
        page.insert_text((225, 96), "TABLE OF CONTENTS", fontname="Times-Bold", fontsize=12)
        rows = [
            ("1 EXPERIMENTAL METHODS.", (282,), 11, 12),
            ("2 MEASUREMENT PROCEDURE.", (312,), 22, 12),
            ("3 ORDINARY TERMINAL PERIOD.", (), 33, 12),
            ("4 ISOLATED LEADER ONLY", (312,), 44, 12),
            ("5 NO TERMINAL PUNCTUATION", (), 55, 12),
            ("6 LEADER GRID CONTROL", (270, 284, 298, 312), 66, 12),
            ("7 LEADER GRID CONTROL", (270, 284, 298, 312), 77, 12),
            ("8 LEADER GRID CONTROL", (270, 284, 298, 312), 88, 12),
            ("9 INPUT FROM DR. RIVERS", (270, 284, 298, 312), 99, 12),
            ("10 A MULTI-DOT LEADER. . . . . .", (), 110, 14),
            ("11 A WRAPPED CHAPTER TITLE THAT", (), None, 10),
            ("continues on its final line.", (274, 288, 302, 316), 121, 10),
            ("12 CONTIGUOUS LEADER ONLY.....", (), 132, 12),
        ]
        for i, (title, leaders, folio, size) in enumerate(rows):
            y = 135 + 24 * i - (6 if i == 11 else 0)
            x = 126 if i == 11 else 108
            page.insert_text((x, y), title, fontname="Times-Roman", fontsize=size)
            for dot_x in leaders:
                page.insert_text((dot_x, y), ".", fontname="Times-Roman", fontsize=size)
            if folio is not None:
                # Keep the folio in a distinct text operator and aligned at x=540.
                page.insert_text((540 - len(str(folio)) * 6, y), str(folio),
                                 fontname="Times-Roman", fontsize=12)
        doc.save(path)
    return path


@pytest.mark.parametrize(("folio", "grid_match"), [("11", False), ("22", True)])
def test_p054_historical_mixed_dot_rows(
    mixed_dot_toc: Path, folio: str, grid_match: bool
) -> None:
    layout = load_pdf_layout(str(mixed_dot_toc))
    context, = detect_toc_like_pages(layout)
    entries = extract_toc_entry_lines(context)
    index, entry = next((i, e) for i, e in enumerate(entries) if e.page_number_token == folio)
    assert is_isolated_terminal_grid_leader_dot(entry, entries) is grid_match
    findings = [
        f for f in check_pdf_toc_terminal_period(layout) if f.details["entry_index"] == str(index)
    ]
    assert len(findings) == 1
    finding = findings[0]
    assert finding.page == 2
    assert finding.details["issue_type"] == "toc_entry_has_terminal_period"
    assert finding.details["terminal_punctuation"] == "."


def test_p054_mixed_leader_controls_and_highlights(mixed_dot_toc: Path, tmp_path: Path) -> None:
    layout = load_pdf_layout(str(mixed_dot_toc))
    context, = detect_toc_like_pages(layout)
    entries = extract_toc_entry_lines(context)
    findings = check_pdf_toc_terminal_period(layout)
    by_folio = {entries[int(f.details["entry_index"])].page_number_token: f for f in findings}
    assert set(by_folio) == {"11", "22", "33", "110", "121"}
    wrapped = next(e for e in entries if e.page_number_token == "121")
    assert wrapped.is_wrapped
    assert wrapped.cleaned_text.endswith("line. . . . .")

    with fitz.open(mixed_dot_toc) as original:
        glyphs = [
            char for block in original[1].get_text("rawdict")["blocks"]
            for line in block.get("lines", []) for span in line["spans"] for char in span["chars"]
        ]
    for folio, y in (("11", 135), ("22", 159), ("110", 351), ("121", 393)):
        bbox = tuple(float(v) for v in by_folio[folio].details["bbox"].split(","))
        period, first_leader, *_ = sorted(
            char["bbox"] for char in glyphs if char["c"] == "." and char["origin"][1] == y
        )
        assert bbox[0] <= period[0] + 0.1
        assert bbox[2] == pytest.approx(period[2], abs=0.1)
        assert bbox[2] + 1 < first_leader[0]

    mixed_findings = [finding for folio, finding in by_folio.items() if folio != "33"]
    export = audit_findings_to_json_dict(mixed_findings, {"audit_type": "pdf"})
    view = build_report_view(export, pdf_page_sizes=[(612, 792)] * 2)
    assert len(view.findings) == 4
    assert all(card.page == 2 and card.has_highlight and "period" in card.polished_comment
               for card in view.findings)
    highlighted = tmp_path / "highlighted.pdf"
    boxes = _highlight_boxes_by_page(export["findings"])
    result = build_highlighted_pdf(mixed_dot_toc, highlighted, boxes)
    assert result.drawn_count == 4
    with fitz.open(highlighted) as rendered:
        assert not list(rendered[0].annots())
        marks = sorted((mark.rect for mark in rendered[1].annots()), key=lambda rect: rect.y0)
    for mark, folio in zip(marks, ("11", "22", "110", "121"), strict=True):
        bbox = tuple(float(v) for v in by_folio[folio].details["bbox"].split(","))
        assert tuple(mark) == pytest.approx(
            (bbox[0] - 1, bbox[1] - 1, bbox[2] + 1, bbox[3] + 1), abs=0.11
        )


def test_p054_wrapped_period_with_partial_glyph_metrics(mixed_dot_toc: Path) -> None:
    layout = load_pdf_layout(str(mixed_dot_toc))
    context, = detect_toc_like_pages(layout)
    entries = extract_toc_entry_lines(context)
    index, entry = next(
        (index, entry) for index, entry in enumerate(entries) if entry.page_number_token == "121"
    )
    assert entry.is_wrapped
    assert entry.page_number_line is not None
    title_span = next(s for s in entry.page_number_line.spans if s.text.endswith("line."))
    assert title_span.char_x_bounds is not None
    title_span.char_x_bounds = None

    finding, = [
        finding for finding in _check_toc_terminal_period_page(context, entries, 0)
        if finding.details["entry_index"] == str(index)
    ]
    bbox = tuple(float(v) for v in finding.details["bbox"].split(","))
    assert bbox[0] == pytest.approx(title_span.bbox.x0, abs=0.05)
    assert bbox[2] == pytest.approx(title_span.bbox.x1, abs=0.05)
    assert bbox[2] < float(finding.details["highlight_right_limit"])


def _toc_pdf(tmp_path: Path, lines: list[str]):
    path = tmp_path / "synthetic_toc.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((210, 85), "TABLE OF CONTENTS", fontsize=12)
    for index, line in enumerate(lines):
        page.insert_text((108, 140 + index * 25), line, fontsize=10)
    doc.save(path)
    doc.close()
    return load_pdf_layout(str(path))


def test_p087_question_matches_exact_generic_repeat_scope(tmp_path: Path) -> None:
    rules = json.loads(
        (Path(__file__).resolve().parents[1] / "data/processed/rules/project_added_rules.json")
        .read_text(encoding="utf-8")
    )
    question = next(rule["question"] for rule in rules if rule["id"] == "P087")
    assert "same generic section title" in question
    assert "distinct numbered sections" in question
    assert "across chapters" not in question

    doc = _toc_pdf(
        tmp_path,
        [
            "1.1 Introduction .... 1",
            "2.1 Introduction .... 10",
            "2.2 Introduction to Optics .... 11",
        ],
    )
    findings = check_pdf_toc_title_structure(doc)
    repeats = [f for f in findings if f.details["issue_type"] == "toc_generic_title_repeated"]
    assert len(repeats) == 1
    assert repeats[0].details["normalized_title"] == "introduction"
    assert repeats[0].details["confidence"] == "medium"
    assert "Check whether" in repeats[0].message
    view = build_report_view(audit_findings_to_json_dict(repeats, {"audit_type": "pdf"}))
    assert "chapter or section context" in view.findings[0].polished_comment


def test_p087_unique_generic_titles_do_not_warn(tmp_path: Path) -> None:
    doc = _toc_pdf(
        tmp_path,
        [
            "1.1 Introduction .... 1",
            "2.1 Methods .... 10",
            "2.2 Introduction to Optics .... 11",
        ],
    )
    assert not [
        f
        for f in check_pdf_toc_title_structure(doc)
        if f.details["issue_type"] == "toc_generic_title_repeated"
    ]


@pytest.fixture(params=["measured", "fragmented"])
def peer_grid_toc(tmp_path: Path, request: pytest.FixtureRequest) -> tuple[Path, bool]:
    path = tmp_path / "peer_grid_toc.pdf"
    font = "Times-Roman"
    measured = request.param == "measured"
    grid = (272, 286, 300, 314, 328, 342)
    with fitz.open() as doc:
        doc.new_page()
        page = doc.new_page(width=612, height=792)
        page.insert_text((225, 80), "TABLE OF CONTENTS", fontname="Times-Bold", fontsize=12)

        def row(
            y: float, title: str, dots: tuple[float, ...] = (), folio: int | None = None,
            *, title_right: float | None = None,
        ) -> None:
            width = fitz.get_text_length(title, fontname=font, fontsize=12)
            x = 100 if title_right is None else title_right - width
            page.insert_text((x, y), title, fontname=font, fontsize=12)
            for x in dots:
                page.insert_text((x, y), ".", fontname=font, fontsize=12)
            if folio is not None:
                page.insert_text((528, y), str(folio), fontname=font, fontsize=12)

        # Punctuation in the title's own PDF text run, including exact alignment.
        row(115, "1 AUTHORED NEAR GRID PERIOD.", grid[1:4], 12, title_right=274.2)
        row(145, "2 AUTHORED ON GRID PERIOD.", grid[1:4], 13, title_right=275)
        row(175, "3 AUTHORED SHORT LEADER.", (286,), 18, title_right=275)
        row(205, "4 WRAPPED TITLE START")
        row(219, "continued title terminal period.", grid[1:4], 19, title_right=275)
        # The leader operators below are separate from the unpunctuated title.
        row(249, "5 ALL LEADER CELLS PRESENT", grid[:4], 11, title_right=272.02)
        row(279, "6 ONE EMPTY LEADER CELL", (272, 300, 314), 14, title_right=272.02)
        row(309, "7 SEVERAL EMPTY LEADER CELLS", (272, 314, 342), 16, title_right=272.02)
        row(339, "8 TWO LEADER DOTS", (300, 314), 17, title_right=300.02)
        row(369, "9 ONE SEPARATED LEADER DOT", (342,), 21)
        # A standalone dot at the boundary can be a fragmented period or an
        # adjacent leader. Its grid position and extraction cannot tell.
        row(399, "10 AMBIGUOUS BOUNDARY", (272, 286), 22, title_right=272)
        # The title's period is in a separate PDF operator but lies off-grid.
        row(429, "11 FRAGMENTED OFF GRID TITLE", (268, 286), 23, title_right=268)
        for i, shift in enumerate((-0.08, 0.0, 0.08) if measured else (0.0, 0.0, 0.0)):
            # Different leader counts and occupied cells on the same grid.
            positions = grid if i != 1 else (272, 286, 300, 314, 342)
            row(459 + i * 30, f"{12 + i} GRID CONTROL", tuple(x + shift for x in positions), 24 + i)
        if measured:
            # A compact run activates glyph bounds. The fragmented variant
            # uses only the first and last coordinates of extracted spans.
            row(549, "15 COMPACT LEADERS.....", folio=27)
            page.add_freetext_annot((80, 620, 250, 660), "Synthetic reviewer note.")
        doc.save(path)
    return path, measured


def test_p054_peer_grid_uses_source_ownership_and_occupied_columns(
    peer_grid_toc: tuple[Path, bool],
) -> None:
    path, measured = peer_grid_toc
    layout = load_pdf_layout(str(path))
    context, = detect_toc_like_pages(layout)
    entries = extract_toc_entry_lines(context)
    by_folio = {entry.page_number_token: entry for entry in entries}
    assert by_folio["19"].is_wrapped
    for folio in ("11", "13"):
        line = by_folio[folio].page_number_line
        assert line is not None
        # The same extracted title span ends in a dot in both cases.
        assert line.spans[0].text.endswith(".")
        assert (line.spans[0].char_x_bounds is not None) is measured
    with fitz.open(path) as pdf:
        page = pdf[1]
        by_baseline = {
            baseline: ["".join(chr(c[0]) for c in run["chars"]) for run in page.get_texttrace()
                       if run["chars"][0][2][1] == baseline]
            for baseline in (115, 145, 249, 279)
        }
        assert by_baseline[115][0].endswith(".")
        assert by_baseline[145][0].endswith(".")
        assert by_baseline[249][0].endswith("PRESENT")
        assert by_baseline[279][1:4] == [".", ".", "."]
    findings = check_pdf_toc_terminal_period(layout)
    assert {entries[int(f.details["entry_index"])].page_number_token for f in findings} == {
        "12", "13", "18", "19", "23"
    }
    assert all(f.page == 2 and f.details["issue_type"] == "toc_entry_has_terminal_period"
               for f in findings)


def test_p054_abstains_at_grid_collision_when_source_runs_are_unavailable(
    peer_grid_toc: tuple[Path, bool],
) -> None:
    path, _ = peer_grid_toc
    missing_path = str(path.with_suffix(".missing"))
    layout = load_pdf_layout(str(path)).model_copy(update={"path": missing_path})
    context, = detect_toc_like_pages(layout)
    entries = extract_toc_entry_lines(context)
    findings = check_pdf_toc_terminal_period(layout)
    # Independent off-grid attachment still has enough evidence. An exact
    # collision cannot be resolved using identical-looking layout spans alone.
    assert {entries[int(f.details["entry_index"])].page_number_token for f in findings} == {
        "12", "23"
    }


@pytest.mark.parametrize(
    ("title_has_period", "peer_offsets", "leader_x", "leader_offset_y", "expected"),
    [
        pytest.param(False, (0, 0, 0, -0.72, 0.72), (318, 333, 348, 363), 0, False,
                     id="coherent-quorum-with-outliers"),
        pytest.param(False, (0, 0, 0), (318, 332.7, 348, 363), 0, False,
                     id="displaced-first-follower"),
        pytest.param(True, (0, 0, 0), (333, 348, 363), 0.48, True,
                     id="authored-period-with-offset-leader-baseline"),
        pytest.param(False, (0, 0), (318, 333, 348, 363), 0, False,
                     id="two-peers-leave-ownership-ambiguous"),
        pytest.param(True, (0, 0), (333, 348, 363), 0, True,
                     id="authored-period-with-only-two-peers"),
    ],
)
def test_p054_peer_evidence_does_not_override_authored_punctuation(
    tmp_path: Path, title_has_period: bool, peer_offsets: tuple[float, ...],
    leader_x: tuple[float, ...], leader_offset_y: float, expected: bool,
) -> None:
    path = tmp_path / "peer_evidence_toc.pdf"
    font = "Times-Roman"
    title = "1 DECISION RECORDS AND MEASURES" + ("." if title_has_period else "")
    title_right = 321 if title_has_period else 318.03
    with fitz.open() as pdf:
        pdf.new_page()
        page = pdf.new_page(width=612, height=792)
        page.insert_text((225, 90), "TABLE OF CONTENTS", fontsize=12)
        width = fitz.get_text_length(title, fontname=font, fontsize=12)
        page.insert_text((title_right - width, 137), title, fontname=font, fontsize=12)
        for x in leader_x:
            page.insert_text((x, 137 + leader_offset_y), ".", fontname=font, fontsize=12)
        page.insert_text((528, 137), "41", fontname=font, fontsize=12)
        for index, offset in enumerate(peer_offsets):
            y = 174 + 27 * index
            page.insert_text((104, y), f"{21 + index} PEER CONTROL", fontname=font, fontsize=12)
            for x in (318, 333, 348, 363):
                page.insert_text((x + offset, y), ".", fontname=font, fontsize=12)
            page.insert_text((528, y), str(80 + index), fontname=font, fontsize=12)
        page.insert_text((108, 340), "29 COMPACT CONTROL.....", fontname=font, fontsize=12)
        page.insert_text((528, 340), "96", fontname=font, fontsize=12)
        pdf.save(path)

    # Text operators, independent of layout spans, establish which marks
    # belong to the title and the actual baseline of the first leader.
    with fitz.open(path) as pdf:
        page = pdf[1]
        runs = [(run["chars"][0][2][1], "".join(chr(c[0]) for c in run["chars"]))
                for run in page.get_texttrace() if run["chars"]]
        assert (137, title) in runs
        assert sum(text == "." and y == pytest.approx(137 + leader_offset_y, abs=0.001)
                   for y, text in runs) == len(leader_x)
    layout = load_pdf_layout(str(path))
    context, = detect_toc_like_pages(layout)
    entries = extract_toc_entry_lines(context)
    index, = [i for i, entry in enumerate(entries) if entry.page_number_token == "41"]
    findings = check_pdf_toc_terminal_period(layout)
    assert [f.details["entry_index"] for f in findings] == ([str(index)] if expected else [])
    assert all(f.page == 2 and f.rule_id == "P054"
               and f.details["issue_type"] == "toc_entry_has_terminal_period" for f in findings)
