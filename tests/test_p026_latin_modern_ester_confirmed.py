"""R026/P026: Latin Modern is part of the accepted Computer Modern allowance.

Ester's 2026-09-23 answer ("YES") to "Should Latin Modern be treated as part
of the accepted Computer Modern-family allowance?" confirms the behavior the
detector already had. These tests pin it with the embedded font-name variants
LaTeX/Overleaf PDFs actually carry, so a future alias refactor cannot silently
drop it. No other font family is broadened here.
"""

from __future__ import annotations

import pytest

from njit_auditor.pdf_models import (
    BBox,
    PdfDocument,
    PdfPage,
    PdfTextBlock,
    PdfTextLine,
    PdfTextSpan,
)
from njit_auditor.rules.pdf_font_compliance import (
    check_pdf_font_compliance,
    classify_font,
    is_accepted_body_font_family,
)

LATIN_MODERN_VARIANTS = [
    "LMRoman10-Regular",
    "LMRoman12-Regular",
    "LMRoman12-Bold",
    "LMRoman10-Italic",
    "LMRomanSlant10-Regular",
    "LMRomanCaps10-Regular",
    "LMRomanDemi10-Regular",
    "ABCDEF+LMRoman12-Regular",
    "XYZABC+LMRomanSlant12-Regular",
    "Latin Modern Roman",
    "LatinModernRoman-Regular",
]

_LINE = "An ordinary body text paragraph line for PDF font compliance testing here."


def _body_doc(font: str) -> PdfDocument:
    lines: list[PdfTextLine] = []
    y = 150.0
    for _ in range(12):
        bbox = BBox(x0=108.0, y0=y, x1=500.0, y1=y + 14.0)
        span = PdfTextSpan(text=_LINE, bbox=bbox, font=font, size=12.0)
        lines.append(PdfTextLine(spans=[span], bbox=bbox, text=_LINE))
        y += 28.0
    block = PdfTextBlock(lines=lines, bbox=BBox(x0=108.0, y0=150.0, x1=500.0, y1=y), text=_LINE)
    page = PdfPage(page_number=1, width=612.0, height=792.0, text_blocks=[block])
    return PdfDocument(path="synthetic", pages=[page])


@pytest.mark.parametrize("font_name", LATIN_MODERN_VARIANTS)
def test_latin_modern_variants_classify_as_computer_modern_family(font_name: str) -> None:
    assert classify_font(font_name) == "computer_modern"
    assert is_accepted_body_font_family(classify_font(font_name))


@pytest.mark.parametrize("font_name", ["LMRoman12-Regular", "ABCDEF+LMRoman12-Regular"])
def test_latin_modern_body_text_produces_no_font_family_finding(font_name: str) -> None:
    findings = [
        f
        for f in check_pdf_font_compliance(_body_doc(font_name))
        if f.details.get("issue_type") == "possible_body_font_family_issue"
    ]
    assert findings == []


def test_unaccepted_family_is_still_flagged_alongside_latin_modern_policy() -> None:
    findings = [
        f
        for f in check_pdf_font_compliance(_body_doc("Calibri"))
        if f.details.get("issue_type") == "possible_body_font_family_issue"
    ]
    assert len(findings) == 1
