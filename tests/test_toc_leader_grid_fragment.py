"""Regression coverage for single-cell TOC leader extraction."""

from njit_auditor.pdf_models import BBox, PdfPage, PdfTextLine, PdfTextSpan
from njit_auditor.rules.pdf_toc_alignment import (
    TocEntryLine,
    entry_has_visible_dot_leader,
    is_isolated_terminal_grid_leader_dot,
)
from njit_auditor.rules.pdf_toc_leader_consistency import _classify_entry
from njit_auditor.rules.pdf_toc_terminal_period import _extract_toc_entry_text


def _span(
    text: str,
    x0: float,
    x1: float,
    *,
    char_x_bounds: list[tuple[float, float]] | None = None,
) -> PdfTextSpan:
    return PdfTextSpan(
        text=text,
        bbox=BBox(x0=x0, y0=100.0, x1=x1, y1=112.0),
        size=12.0,
        char_x_bounds=char_x_bounds,
    )


def _entry(
    title: str,
    leader: PdfTextSpan | list[PdfTextSpan],
    page_number: str = "123",
) -> TocEntryLine:
    leaders = [leader] if isinstance(leader, PdfTextSpan) else leader
    spans = [
        _span(title, 108.0, 200.0),
        *leaders,
        _span(page_number, 220.0, 238.0),
    ]
    line = PdfTextLine(
        text=f"{title}{''.join(span.text for span in leaders)}{page_number}",
        bbox=BBox(x0=108.0, y0=100.0, x1=238.0, y1=112.0),
        spans=spans,
    )
    return TocEntryLine(
        line=line,
        cleaned_text=line.text,
        page_number_token=page_number,
        page_number_right_x=238.0,
        indent_x=108.0,
        has_leader_dots=False,
    )


def test_single_terminal_grid_dot_with_leading_space_is_a_leader() -> None:
    target = _entry(
        "Evaluating Conditions",
        _span(
            " .",
            200.0,
            206.0,
            char_x_bounds=[(200.0, 203.0), (203.0, 206.0)],
        ),
    )
    peers = [
        _entry(
            f"Peer {index}",
            [
                _span(".", 180.0, 183.0),
                _span(".", 190.0, 193.0),
                _span(".", 203.0, 206.0),
            ],
        )
        for index in range(3)
    ]

    assert is_isolated_terminal_grid_leader_dot(target, [target, *peers])
    page = PdfPage(page_number=12, width=612.0, height=792.0)
    assert entry_has_visible_dot_leader(target, page, [target, *peers])
    assert _classify_entry(target, page, [target, *peers]) == "dot"
    assert _extract_toc_entry_text(target) == "Evaluating Conditions ."


def test_attached_title_period_is_not_removed_as_a_leader() -> None:
    target = _entry("Evaluating Conditions.", _span("...", 200.0, 220.0))
    target.has_leader_dots = True
    page = PdfPage(page_number=12, width=612.0, height=792.0)

    assert not is_isolated_terminal_grid_leader_dot(target, [target])
    assert _classify_entry(target, page, [target]) == "dot"
