"""Synthetic coverage for P011 bottom-margin detection (previously untested in isolation)."""

from __future__ import annotations

from pathlib import Path

import fitz

from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.rules.pdf_margins import (
    BOTTOM_MARGIN_PT,
    OVERFLOW_TOLERANCE_PT,
    run_pdf_margin_rule,
)

PAGE_WIDTH = 612.0
PAGE_HEIGHT = 792.0
ALLOWED_Y1 = PAGE_HEIGHT - BOTTOM_MARGIN_PT


def _bottom_warnings(pdf_path: Path) -> list:
    model = load_pdf_layout(str(pdf_path))
    return [
        f
        for f in run_pdf_margin_rule(model)
        if f.severity.value == "WARNING" and f.details.get("side") == "bottom_margin"
    ]


def test_bottom_margin_violation_detected(tmp_path: Path) -> None:
    """A line clearly below the bottom margin must produce a bottom_margin warning."""
    # y_base=726 yields ~8.3pt measured overflow (above medium-confidence floor).
    y_base = 726.0
    doc = fitz.open()
    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    page.insert_text((150, y_base), "Footer line crossing bottom margin boundary", fontsize=11)
    pdf_path = tmp_path / "bottom_overflow.pdf"
    doc.save(pdf_path)
    doc.close()

    warnings = _bottom_warnings(pdf_path)
    assert len(warnings) == 1
    assert float(warnings[0].details["worst_overflow_pt"]) > OVERFLOW_TOLERANCE_PT


def test_bottom_margin_small_overflow_suppressed_when_low_confidence(tmp_path: Path) -> None:
    """Single-line sub-5pt bottom overflow is low confidence and must not warn."""
    # insert_text baseline is above the glyph bbox; y_base=721 yields ~4.3pt overflow.
    y_base = 721.0
    doc = fitz.open()
    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    page.insert_text((150, y_base), "Tiny footer nudge", fontsize=11)
    pdf_path = tmp_path / "bottom_tiny.pdf"
    doc.save(pdf_path)
    doc.close()

    warnings = _bottom_warnings(pdf_path)
    assert warnings == []
