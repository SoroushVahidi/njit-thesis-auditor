"""R011 bottom-only allowances on landscape sheets (synthetic PDFs only).

BOTTOM_MARGIN_OVERFLOW_TOLERANCE_PT, the final-line box exception and the
references final-line allowance come from Ester's verdicts on the last line of
a portrait page's text flow dipping into its ordinary 1-inch bottom margin.
They follow the text-space bottom (where horizontal text flow ends), but never
relax the 1.5-inch binding margin: a sheet turned counter-clockwise puts the
binding edge at the bottom, and it must be as strict as a binding edge at the
top. They are not remapped onto the portrait-bottom edge either.
"""

from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.rules.pdf_margins import _margin_frame, run_pdf_margin_rule

TEXT = "Synthetic landscape table row with several ordinary words"
FONT_SIZE = 11.0
# Allowed text rectangle per sheet (x0, y0, x1, y1), from the 1.5 in binding edge.
FRAMES = {
    "portrait": (108.0, 72.0, 540.0, 720.0),
    "cw": (72.0, 108.0, 720.0, 540.0),  # binding at the top
    "ccw": (72.0, 72.0, 720.0, 504.0),  # binding at the bottom
    "undetermined": (72.0, 72.0, 720.0, 540.0),
}


def _glyph_box(tmp_path: Path) -> tuple[float, float, float, float]:
    """(above-baseline, below-baseline, left offset, width) of TEXT's line box."""
    doc = fitz.open()
    doc.new_page(width=792, height=612).insert_text((200, 300), TEXT, fontsize=FONT_SIZE)
    path = tmp_path / "probe.pdf"
    doc.save(path)
    doc.close()
    (line,) = [
        line for block in load_pdf_layout(str(path)).pages[0].text_blocks for line in block.lines
    ]
    return 300 - line.bbox.y0, line.bbox.y1 - 300, line.bbox.x0 - 200, line.bbox.width


def _sheet(tmp_path: Path, sheet: str, edge: str, intrusion: float) -> list[str]:
    """One line crossing `edge` (text-space) by `intrusion` pt; WARNING sides."""
    up, down, left, width = _glyph_box(tmp_path)
    portrait = sheet == "portrait"
    doc = fitz.open()
    page = doc.new_page(width=612 if portrait else 792, height=792 if portrait else 612)
    if sheet == "cw":
        page.insert_text((50, 306), "81", fontsize=12, rotate=270)
    elif sheet == "ccw":
        page.insert_text((742, 306), "81", fontsize=12, rotate=90)
    x0, y0, x1, y1 = FRAMES[sheet]
    if edge == "top":
        origin = (200.0, y0 - intrusion + up)
    elif edge == "bottom":
        origin = (200.0, y1 + intrusion - down)
    elif edge == "left":
        origin = (x0 - intrusion - left, 300.0)
    else:
        origin = (x1 + intrusion - left - width, 300.0)
    page.insert_text(origin, TEXT, fontsize=FONT_SIZE)
    path = tmp_path / f"{sheet}_{edge}_{intrusion}.pdf"
    doc.save(path)
    doc.close()
    model = load_pdf_layout(str(path))
    expected_edge = {"portrait": "left", "cw": "top", "ccw": "bottom"}.get(sheet, "undetermined")
    assert _margin_frame(model.pages[0]).binding_edge == expected_edge
    return [
        finding.details["side"]
        for finding in run_pdf_margin_rule(model)
        if finding.severity.value == "WARNING"
    ]


@pytest.mark.parametrize("edge", ["top", "left", "right"])
def test_portrait_ordinary_edges_keep_the_ordinary_tolerance(tmp_path: Path, edge: str) -> None:
    assert _sheet(tmp_path, "portrait", edge, 4.0) == []
    assert _sheet(tmp_path, "portrait", edge, 6.0) == [f"{edge}_margin"]


def test_portrait_bottom_keeps_the_last_line_allowance(tmp_path: Path) -> None:
    assert _sheet(tmp_path, "portrait", "bottom", 9.2) == []
    assert _sheet(tmp_path, "portrait", "bottom", 13.0) == ["bottom_margin"]


@pytest.mark.parametrize("intrusion", [4.0, 6.0, 8.0, 9.2, 10.0])
def test_mirrored_binding_edges_get_the_same_verdict(tmp_path: Path, intrusion: float) -> None:
    top_binding = _sheet(tmp_path, "cw", "top", intrusion)
    bottom_binding = _sheet(tmp_path, "ccw", "bottom", intrusion)
    assert bool(top_binding) == bool(bottom_binding)


def test_bottom_binding_edge_violation_is_reported(tmp_path: Path) -> None:
    # Inside the portrait-bottom allowance, but on the binding margin.
    assert _sheet(tmp_path, "ccw", "bottom", 8.0) == ["bottom_margin"]
    assert _sheet(tmp_path, "cw", "top", 8.0) == ["top_margin"]


def test_ordinary_text_space_bottom_keeps_the_last_line_allowance(tmp_path: Path) -> None:
    # Turned clockwise, the text-space bottom is the ordinary portrait-right edge.
    assert _sheet(tmp_path, "cw", "bottom", 8.0) == []
    assert _sheet(tmp_path, "cw", "bottom", 13.0) == ["bottom_margin"]


@pytest.mark.parametrize(("sheet", "edge"), [("cw", "left"), ("ccw", "right")])
def test_portrait_bottom_edge_is_not_given_the_bottom_allowance(
    tmp_path: Path, sheet: str, edge: str
) -> None:
    assert _sheet(tmp_path, sheet, edge, 6.0) == [f"{edge}_margin"]


@pytest.mark.parametrize(("sheet", "edge"), [("cw", "right"), ("ccw", "top"), ("ccw", "left")])
def test_ordinary_one_inch_landscape_edge_violation_is_reported(
    tmp_path: Path, sheet: str, edge: str
) -> None:
    assert _sheet(tmp_path, sheet, edge, 6.0) == [f"{edge}_margin"]


@pytest.mark.parametrize("sheet", ["cw", "ccw"])
def test_portrait_page_number_is_not_a_violation(tmp_path: Path, sheet: str) -> None:
    assert _sheet(tmp_path, sheet, "top", 0.0) == []


def test_undetermined_binding_edge_stays_lenient_at_the_bottom(tmp_path: Path) -> None:
    # Either long edge could be the binding edge, so only what violates both
    # readings is reported: the bottom keeps the ordinary-edge allowance.
    assert _sheet(tmp_path, "undetermined", "bottom", 8.0) == []
    assert _sheet(tmp_path, "undetermined", "bottom", 13.0) == ["bottom_margin"]


def _references_final_line_sheet(tmp_path: Path, sheet: str) -> list[str]:
    """A references sheet whose last entry line dips 8pt past the text-space
    bottom boundary, directly above a horizontal page number."""
    up, down, _, _ = _glyph_box(tmp_path)
    doc = fitz.open()
    page = doc.new_page(width=792, height=612)
    if sheet == "cw":
        page.insert_text((50, 306), "81", fontsize=12, rotate=270)
    else:
        page.insert_text((742, 306), "81", fontsize=12, rotate=90)
    y1 = FRAMES[sheet][3]
    page.insert_text((360, 130), "REFERENCES", fontsize=FONT_SIZE)
    last = y1 + 8.0 - down
    for step in range(6, 0, -1):
        page.insert_text((120, last - 13.0 * step), f"[{7 - step}] {TEXT}", fontsize=FONT_SIZE)
    page.insert_text((120, last), "https://doi.org/10.0000/synthetic.reference", fontsize=FONT_SIZE)
    page.insert_text((392, 600), "82", fontsize=FONT_SIZE)
    path = tmp_path / f"refs_{sheet}.pdf"
    doc.save(path)
    doc.close()
    return [
        finding.details["side"]
        for finding in run_pdf_margin_rule(load_pdf_layout(str(path)))
        if finding.severity.value == "WARNING"
    ]


def test_references_final_line_allowance_never_relaxes_the_binding_edge(tmp_path: Path) -> None:
    assert _references_final_line_sheet(tmp_path, "cw") == []
    assert _references_final_line_sheet(tmp_path, "ccw") == ["bottom_margin"]
