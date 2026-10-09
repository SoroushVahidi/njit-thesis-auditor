"""P015 missing-indent: a new paragraph only follows a finished sentence.

Ester (R015 feedback) rejected missing-indent flags on lines that continue a
sentence, and suggested the rule "a new paragraph always comes after a
period". This covers prose that resumes after a displayed equation, whose
last line (the formula or its number) does not end a sentence.
"""

from __future__ import annotations

from test_p015_r015_ester_run_in_heading_20260831 import _CONT, _block, _doc, _line, _page

from njit_auditor.pdf_models import PdfTextLine
from njit_auditor.rules.pdf_indentation import check_pdf_indentation

_EQ = "F(x, t) = alpha g(x) + beta h(x, t) + gamma k(t)"


def _doc_with_equation(lead_in_end: str):
    """Indented paragraphs, then prose ending in *lead_in_end*, a displayed
    equation (a one-line block the paragraph grouper sets aside), and
    flush-left text after it."""
    y = 80.0
    lines: list[PdfTextLine] = []
    for index in range(4):  # indented paragraphs establish the page's indent style
        lines.append(
            _line(
                f"Indented synthetic paragraph opener establishing page style {index}.",
                x0=144.0,
                y0=y,
                y1=y + 12,
            )
        )
        y += 14.0
        for _ in range(3):
            lines.append(_line(_CONT, x0=108.0, y0=y, y1=y + 12))
            y += 14.0
        y += 14.0
    lines.append(
        _line("Indented paragraph introducing the model whose energy", x0=144.0, y0=y, y1=y + 12)
    )
    y += 14.0
    lines.append(
        _line(f"over the whole synthetic domain is written{lead_in_end}", x0=108.0, y0=y, y1=y + 12)
    )
    y += 28.0
    lines.append(_line(_EQ, x0=200.0, x1=470.0, y0=y, y1=y + 12))  # displayed equation
    y += 28.0
    for _ in range(4):  # flush-left text after the equation
        lines.append(
            _line(
                "Flush-left synthetic text that follows the displayed equation.",
                x0=108.0,
                y0=y,
                y1=y + 12,
            )
        )
        y += 14.0
    return _doc(_page(30, _block(*lines)))


def _missing_indent(doc) -> list:
    return [
        f
        for f in check_pdf_indentation(doc)
        if f.rule_id == "P015" and f.details.get("issue_type") == "missing_later_indent"
    ]


def test_prose_resuming_after_an_unfinished_equation_sentence_is_not_flagged() -> None:
    for lead_in_end in (" as", ":", ","):
        assert _missing_indent(_doc_with_equation(lead_in_end)) == [], lead_in_end


def test_flush_left_paragraph_after_a_finished_sentence_is_still_flagged() -> None:
    assert len(_missing_indent(_doc_with_equation("."))) == 1
