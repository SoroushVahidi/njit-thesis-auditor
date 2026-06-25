"""Tests for skipping export/log timestamp lines in TOC/list entry parsing."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from njit_auditor.audit_runner import run_pdf_audit_full
from njit_auditor.pdf_models import BBox, PdfPage, PdfTextBlock, PdfTextLine, PdfTextSpan
from njit_auditor.report_outputs import audit_findings_to_json_dict
from njit_auditor.report_view import build_report_view
from njit_auditor.rules.pdf_toc_alignment import TocPageContext, extract_toc_entry_lines
from njit_auditor.toc_list_student_preview import is_toc_export_metadata_line

_PAGE_W = 612.0
_PAGE_H = 792.0
_MARGIN_L = 108.0


def _make_line(
    text: str,
    y: float,
    *,
    x0: float = _MARGIN_L,
    x1: float = 420.0,
) -> PdfTextLine:
    bbox = BBox(x0=x0, y0=y, x1=x1, y1=y + 14.0)
    span = PdfTextSpan(text=text, bbox=bbox, font="Helvetica", size=12.0)
    return PdfTextLine(spans=[span], bbox=bbox, text=text)


def _make_page(page_number: int, lines: list[PdfTextLine]) -> PdfPage:
    block = PdfTextBlock(
        lines=lines,
        bbox=BBox(
            x0=min(line.bbox.x0 for line in lines),
            y0=min(line.bbox.y0 for line in lines),
            x1=max(line.bbox.x1 for line in lines),
            y1=max(line.bbox.y1 for line in lines),
        ),
        text=" ".join(line.text for line in lines),
    )
    return PdfPage(
        page_number=page_number,
        width=_PAGE_W,
        height=_PAGE_H,
        text_blocks=[block],
    )


def _toc_context(page: PdfPage, heading_y: float = 90.0) -> TocPageContext:
    return TocPageContext(page=page, page_type="table_of_contents", heading_bottom_y=heading_y)


@pytest.mark.parametrize(
    "text",
    [
        "2026-04-30 12:45:08",
        "2026-04-30 12:45:34",
        "2026-01-01 00:00",
        "2026-06-24",
    ],
)
def test_is_toc_export_metadata_line_matches_obvious_timestamps(text: str) -> None:
    assert is_toc_export_metadata_line(text)


@pytest.mark.parametrize(
    "text",
    [
        "2026 Budget Analysis",
        "1.2 2026 Budget Analysis .... 12",
        "CHAPTER 1 INTRODUCTION .... 5",
        "Appendix A — 2026 survey data .... 88",
    ],
)
def test_is_toc_export_metadata_line_keeps_real_titles(text: str) -> None:
    assert not is_toc_export_metadata_line(text)


def test_extract_toc_entry_lines_skips_timestamp_metadata() -> None:
    page = _make_page(
        12,
        [
            _make_line("TABLE OF CONTENTS", 80.0, x1=300.0),
            _make_line("2026-04-30 12:45:08", 120.0, x1=300.0),
            _make_line("1 LOREM SECTION ALPHA .... 12", 140.0, x1=520.0),
            _make_line("2 LOREM SECTION BETA .... 24", 160.0, x1=520.0),
            _make_line("3 LOREM SECTION GAMMA .... 36", 180.0, x1=520.0),
        ],
    )
    entries = extract_toc_entry_lines(_toc_context(page))
    cleaned = [entry.cleaned_text for entry in entries]
    assert "2026-04-30 12:45:08" not in cleaned
    assert len(entries) == 3


def test_extract_toc_entry_lines_keeps_year_in_real_title() -> None:
    page = _make_page(
        1,
        [
            _make_line("TABLE OF CONTENTS", 80.0, x1=300.0),
            _make_line("2026 Budget Analysis .... 12", 120.0, x1=520.0),
            _make_line("1 LOREM SECTION BETA .... 24", 140.0, x1=520.0),
            _make_line("2 LOREM SECTION GAMMA .... 36", 160.0, x1=520.0),
        ],
    )
    entries = extract_toc_entry_lines(_toc_context(page))
    assert any("2026 Budget Analysis" in entry.cleaned_text for entry in entries)


@pytest.mark.skipif(
    not Path("data/raw/ester/Yin_H_4th_Review_with_EF_comments_compressed.pdf").exists(),
    reason="Ester sample D PDF not available locally",
)
def test_ester_sample_d_has_no_timestamp_toc_p018_cards() -> None:
    from njit_auditor.web_samples import get_builtin_sample

    sample = get_builtin_sample("ester_sample_d")
    view = build_report_view(
        audit_findings_to_json_dict(
            run_pdf_audit_full(sample.abs_path),
            {"audit_type": "pdf"},
        )
    )
    timestamp_cards = [
        card
        for card in view.findings
        if card.rule_id == "P018"
        and re.search(r"\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}", card.location_label or "")
    ]
    assert timestamp_cards == []
