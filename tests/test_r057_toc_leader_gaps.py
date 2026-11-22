"""Synthetic PDF regressions for Ester's R057 TOC leader feedback."""

from pathlib import Path

import pymupdf
import pytest

from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.rules.pdf_toc_alignment import (
    check_pdf_toc_alignment,
    detect_toc_like_pages,
    extract_toc_entry_lines,
)
from njit_auditor.rules.pdf_toc_leader_consistency import check_pdf_toc_leader_consistency
from njit_auditor.rules.pdf_toc_terminal_period import check_pdf_toc_terminal_period


def _toc_pdf(
    path: Path, case: str, *, size: float, pitch_em: float, wrapped: bool,
) -> None:
    font = "Times-Roman"

    def write(text: str, x: float, y: float) -> None:
        page.insert_text((x, y), text, fontname=font, fontsize=size)

    def width(text: str) -> float:
        return pymupdf.get_text_length(text, fontname=font, fontsize=size)

    # Terminal dots end well before the folio in many production TOC grids.
    # Use a different pitch on each test page to exercise measured capacity.
    pitch = pitch_em * size
    title = "CALIBRATION, WITH 2.5 V AND AN EXTENDED MATHEMATICAL MODEL"
    if not wrapped:
        title = f"2 {title}"
    if case == "period":
        title += "."
    folio_left = (126 if wrapped else 108) + width(title) + 1.40 * size
    last_dot = folio_left - 1.50 * size
    with pymupdf.open() as pdf:
        pdf.new_page(width=612, height=792)
        page = pdf.new_page(width=612, height=792)
        page.insert_text((225, 90), "TABLE OF CONTENTS", fontname="Times-Bold", fontsize=12)
        for index, peer in enumerate((
            "1 INTRODUCTION", "3 CONTINUOUS SIGNALS", "4 CONCLUSIONS",
        )):
            y = 135 + 24 * index
            write(peer, 108, y)
            first_run_x = 108 + width(peer) + 0.50 * size
            write("....", first_run_x, y)
            x = last_dot + ((index - 1) * 0.45 * size if case == "ambiguous" else 0)
            while x > first_run_x + 1.25 * size:
                write(".", x, y)
                x -= pitch
            write(str(10 + 20 * index), folio_left, y)

        baseline = 222
        title_right = last_dot + 0.18 * size
        if case in {"one", "bad_dot"}:
            title_right = last_dot - 0.24 * size
        elif case in {"wide", "wide_one", "multi"}:
            title = "MODEL 2.5: VALIDATION" if wrapped else "2 MODEL 2.5: VALIDATION"
            title_right = (126 if wrapped else 108) + width(title)
        if wrapped:
            # The first visual row reaches much farther right than a short
            # continuation. Its x1 must never determine the final-line gap.
            write("2 AN EXTENDED STUDY OF INDEPENDENT MEASUREMENTS IN THE LAB", 108, baseline)
            baseline += 14
        write(title, title_right - width(title), baseline)
        if case in {"one", "wide_one"}:
            write(".", last_dot, baseline)
        if case == "bad_dot":
            write(".", last_dot + 0.40 * size, baseline)
        if case == "multi":
            x = last_dot
            while x > title_right + 0.25 * size:
                write(".", x, baseline)
                x -= pitch
        if case != "missing":
            write("35", folio_left + (25 if case == "misaligned" else 0), baseline)
        pdf.save(path)


@pytest.mark.parametrize(
    ("case", "wrapped", "missing_leader", "punctuation"),
    [
        ("zero", False, False, False),
        ("one", False, False, False),
        ("multi", False, False, False),
        ("wide", False, True, False),
        ("wide_one", False, True, False),
        ("bad_dot", False, True, False),
        ("period", False, False, True),
        ("ambiguous", False, True, False),
        ("zero", True, False, False),
        ("one", True, False, False),
        ("wide", True, True, False),
        ("missing", False, False, False),
        ("misaligned", False, True, False),
    ],
)
def test_toc_short_leader_geometry(
    tmp_path: Path, case: str, wrapped: bool, missing_leader: bool, punctuation: bool,
) -> None:
    path = tmp_path / "toc.pdf"
    _toc_pdf(path, case, size=11, pitch_em=0.60, wrapped=wrapped)
    layout = load_pdf_layout(str(path))
    (context,) = detect_toc_like_pages(layout)
    entries = extract_toc_entry_lines(context)
    if case != "missing":
        (target,) = [entry for entry in entries if entry.page_number_token == "35"]
        assert target.is_wrapped is wrapped
        assert target.page_number_line is not None
        assert len(target.page_number_line.spans) > 1
    findings = check_pdf_toc_leader_consistency(layout)
    assert bool(findings) is missing_leader
    if missing_leader:
        (finding,) = findings
        assert finding.page == 2
        assert finding.details["issue_type"] == "toc_missing_leader_style"
        assert finding.details["entry_index"] == str(entries.index(target))
        assert finding.details["entries_without_leader"] == "1"
        assert finding.details["bbox"]
    periods = check_pdf_toc_terminal_period(layout)
    assert bool(periods) is punctuation
    page_number_issues = {
        finding.details["issue_type"] for finding in check_pdf_toc_alignment(layout)
        if "page_number" in finding.details["issue_type"]
    }
    if case == "missing":
        assert "missing_page_number" in page_number_issues
    elif case == "misaligned":
        assert "misaligned_page_number_column" in page_number_issues
    else:
        assert not page_number_issues


@pytest.mark.parametrize(("size", "pitch_em"), [(9.5, 0.43), (13, 0.78)])
@pytest.mark.parametrize("case", ["zero", "one", "wide_one"])
def test_short_gap_uses_local_font_and_dot_pitch(
    tmp_path: Path, size: float, pitch_em: float, case: str,
) -> None:
    path = tmp_path / "scaled.pdf"
    _toc_pdf(path, case, size=size, pitch_em=pitch_em, wrapped=False)
    findings = check_pdf_toc_leader_consistency(load_pdf_layout(str(path)))
    assert bool(findings) is (case == "wide_one")
