"""Regression coverage for the 2026-08 Esther/R011 false-positive batch.

Esther reviewed the lowest-confidence surviving P011 finding from each of
seven real dissertations and classified all seven as false positives. The
seven findings split into three distinct, independently confirmed root
causes -- see docs/status/p011_r011_batch_2026_08_false_positive_fix.md for
the full diagnosis:

1. Bottom-margin single-trailing-line slack (4 cases: prose and equation
   lines, both Word and LaTeX sources): a fully justified line that lands
   last on an otherwise full page routinely has its own descent/leading dip
   a few extra points past the nominal 1-inch line.
2. Right-margin trailing-whitespace-in-bbox measurement artifact (2 cases,
   both Word and LaTeX sources): a justified line's extracted bbox includes
   the advance width of a trailing space character, which carries no visible
   ink.
3. Reference-list unbreakable-citation overflow (1 case): a bibliography
   entry containing a long title/DOI that cannot wrap without altering the
   citation.

Each fixture here is synthetic (no real dissertation content), built from the
exact geometry that reproduces each root cause, with a paired positive
control proving the corresponding genuine violation still gets flagged.
"""

from __future__ import annotations

from pathlib import Path

import fitz

from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.rules.pdf_margins import (
    BOTTOM_MARGIN_OVERFLOW_TOLERANCE_PT,
    BOTTOM_MARGIN_PT,
    OVERFLOW_TOLERANCE_PT,
    REFERENCES_MARGIN_EXTRA_TOLERANCE_PT,
    RIGHT_MARGIN_PT,
    run_pdf_margin_rule,
)

PAGE_WIDTH = 612.0
PAGE_HEIGHT = 792.0
ALLOWED_X1 = PAGE_WIDTH - RIGHT_MARGIN_PT
ALLOWED_Y1 = PAGE_HEIGHT - BOTTOM_MARGIN_PT


def _warnings(pdf_path: Path, side: str) -> list:
    model = load_pdf_layout(str(pdf_path))
    return [
        f
        for f in run_pdf_margin_rule(model)
        if f.severity.value == "WARNING" and f.details.get("side") == side
    ]


# ---------------------------------------------------------------------------
# Root cause 1: bottom-margin single-trailing-line slack.
# ---------------------------------------------------------------------------


def test_bottom_margin_overflow_just_under_tolerance_suppressed(tmp_path: Path) -> None:
    """~8.3pt single-line bottom overflow (below the new 9.0pt tolerance,
    matching Esther's confirmed 3.9-8.2pt false positives) must not warn."""
    doc = fitz.open()
    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    page.insert_text((150, 725.0), "Footer line crossing bottom margin boundary", fontsize=11)
    pdf_path = tmp_path / "bottom_just_under.pdf"
    doc.save(pdf_path)
    doc.close()

    assert _warnings(pdf_path, "bottom_margin") == []


def test_bottom_margin_overflow_just_over_tolerance_still_flagged(tmp_path: Path) -> None:
    """~9.3pt single-line bottom overflow (just above the new tolerance) must
    still warn -- the tolerance has a ceiling, it is not a blanket exemption."""
    doc = fitz.open()
    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    page.insert_text((150, 726.0), "Footer line crossing bottom margin boundary", fontsize=11)
    pdf_path = tmp_path / "bottom_just_over.pdf"
    doc.save(pdf_path)
    doc.close()

    warnings = _warnings(pdf_path, "bottom_margin")
    assert len(warnings) == 1
    assert float(warnings[0].details["worst_overflow_pt"]) > BOTTOM_MARGIN_OVERFLOW_TOLERANCE_PT
    assert warnings[0].details["confidence"] == "medium"


def test_bottom_margin_large_overflow_still_high_confidence(tmp_path: Path) -> None:
    """A genuinely large bottom-margin bleed (~13pt, well past one trailing
    line's worth of slack) is a positive control: it must remain a
    high-confidence violation, proving the new tolerance does not mask real
    overflow."""
    doc = fitz.open()
    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    page.insert_text((150, 730.0), "Footer line crossing bottom margin boundary", fontsize=11)
    pdf_path = tmp_path / "bottom_large.pdf"
    doc.save(pdf_path)
    doc.close()

    warnings = _warnings(pdf_path, "bottom_margin")
    assert len(warnings) == 1
    assert float(warnings[0].details["worst_overflow_pt"]) >= 12.0
    assert warnings[0].details["confidence"] == "high"


# ---------------------------------------------------------------------------
# Root cause 2: right-margin trailing-whitespace-in-bbox artifact.
# ---------------------------------------------------------------------------


def test_right_margin_trailing_space_only_overflow_suppressed(tmp_path: Path) -> None:
    """A justified line whose measured right edge crosses the margin by
    ~3.05pt purely because of one trailing space glyph (matching Esther's
    confirmed ~3.0pt Word and LaTeX false positives) must not warn."""
    text_with_space = "Line ending near the margin boundary "
    width = fitz.get_text_length(text_with_space, fontsize=12)
    x0 = ALLOWED_X1 + 3.05 - width
    doc = fitz.open()
    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    page.insert_text((x0, 300), text_with_space, fontsize=12)
    pdf_path = tmp_path / "right_trailing_space.pdf"
    doc.save(pdf_path)
    doc.close()

    assert _warnings(pdf_path, "right_margin") == []


def test_right_margin_real_ink_overflow_without_trailing_space_still_flagged(
    tmp_path: Path,
) -> None:
    """A line with the same magnitude of overflow (~10pt) but no trailing
    whitespace -- real ink actually crosses the margin -- must still warn.
    Proves the fix targets the measurement artifact, not right-margin
    detection generally."""
    text = "Line with no trailing whitespace here"
    width = fitz.get_text_length(text, fontsize=12)
    x0 = ALLOWED_X1 + 10 - width
    doc = fitz.open()
    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    page.insert_text((x0, 300), text, fontsize=12)
    pdf_path = tmp_path / "right_real_overflow.pdf"
    doc.save(pdf_path)
    doc.close()

    warnings = _warnings(pdf_path, "right_margin")
    assert len(warnings) == 1
    assert float(warnings[0].details["worst_overflow_pt"]) == 10.0


def test_right_margin_trailing_space_with_large_overflow_still_flagged(tmp_path: Path) -> None:
    """A line with a trailing space AND a large genuine overflow (~23pt raw)
    must still warn -- the ~3pt trim only removes the whitespace artifact, it
    does not zero out real overflow. Positive control matching the observed
    behavior on real evaluation PDFs (Praneeth pp.17-18, 58), where trimming
    correctly reduced -- but did not eliminate -- large right-margin
    overflows."""
    text_with_space = "Line that overflows the right margin by a lot "
    width = fitz.get_text_length(text_with_space, fontsize=12)
    x0 = ALLOWED_X1 + 23 - width
    doc = fitz.open()
    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    page.insert_text((x0, 300), text_with_space, fontsize=12)
    pdf_path = tmp_path / "right_trailing_space_large.pdf"
    doc.save(pdf_path)
    doc.close()

    warnings = _warnings(pdf_path, "right_margin")
    assert len(warnings) == 1
    # ~23pt raw, minus one space-glyph width (0.25 * 12pt = 3pt) trimmed.
    assert abs(float(warnings[0].details["worst_overflow_pt"]) - 20.0) < 0.5
    assert warnings[0].details["confidence"] == "high"


# ---------------------------------------------------------------------------
# Root cause 3: reference-list unbreakable-citation overflow.
# ---------------------------------------------------------------------------


def test_references_entry_bounded_right_overflow_suppressed(tmp_path: Path) -> None:
    """A references-list entry overflowing the right margin by ~7pt (matching
    Esther's confirmed ~6.9pt false positive) must not warn."""
    text = "Author, A. An Unbreakable Long Citation Title That Cannot Wrap."
    width = fitz.get_text_length(text, fontsize=12)
    x0 = ALLOWED_X1 + 7.0 - width
    doc = fitz.open()
    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    page.insert_text((108, 100), "References", fontsize=14)
    page.insert_text((x0, 300), text, fontsize=12)
    pdf_path = tmp_path / "references_small_overflow.pdf"
    doc.save(pdf_path)
    doc.close()

    assert _warnings(pdf_path, "right_margin") == []


def test_references_entry_beyond_bound_still_flagged(tmp_path: Path) -> None:
    """A references-list entry overflowing the right margin by ~15pt -- well
    past the bounded extra tolerance -- must still warn. Proves the reference
    exception is bounded, not a blanket exemption for the whole content kind."""
    text = "Author, A. An Unbreakable Long Citation Title That Cannot Wrap."
    width = fitz.get_text_length(text, fontsize=12)
    x0 = ALLOWED_X1 + 15.0 - width
    doc = fitz.open()
    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    page.insert_text((108, 100), "References", fontsize=14)
    page.insert_text((x0, 300), text, fontsize=12)
    pdf_path = tmp_path / "references_large_overflow.pdf"
    doc.save(pdf_path)
    doc.close()

    warnings = _warnings(pdf_path, "right_margin")
    assert len(warnings) == 1
    assert float(warnings[0].details["worst_overflow_pt"]) == 15.0
    assert warnings[0].details["margin_content_kind"] == "references_hanging_indent"
    bound = OVERFLOW_TOLERANCE_PT + REFERENCES_MARGIN_EXTRA_TOLERANCE_PT
    assert float(warnings[0].details["worst_overflow_pt"]) > bound
