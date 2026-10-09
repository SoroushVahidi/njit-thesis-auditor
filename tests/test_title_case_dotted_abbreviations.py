"""Dotted abbreviations must not become title-case capitalization targets.

Privacy-safe synthetic phrases only — no dissertation prose.
"""

from __future__ import annotations

from njit_auditor.pdf_models import BBox, PdfDocument, PdfPage, PdfTextBlock, PdfTextLine
from njit_auditor.rules.pdf_title_capitalization import check_apa_title_case_phrase
from njit_auditor.rules.pdf_toc_list_formatting import check_pdf_toc_list_formatting


def _flagged(text: str) -> set[str]:
    return {issue["word"] for issue in check_apa_title_case_phrase(text)}


def test_ie_abbreviation_components_are_not_flagged() -> None:
    text = "Widest Differences in Cross-Run ARI within Same Toolkit, i.e., Baseline"
    flagged = _flagged(text)
    assert "i" not in flagged
    assert "e" not in flagged
    assert flagged == set()


def test_eg_and_et_al_abbreviations_are_not_flagged() -> None:
    assert "e" not in _flagged("Results for Several Methods, e.g., Baseline Models Today")
    assert "g" not in _flagged("Results for Several Methods, e.g., Baseline Models Today")
    assert "al" not in _flagged("Comparison with Prior Authors et al. on Benchmark Data")
    assert "et" not in _flagged("Comparison with Prior Authors et al. on Benchmark Data")


def test_genuine_lowercase_major_near_abbreviation_still_flagged() -> None:
    text = "Widest differences in Cross-Run ARI within Same Toolkit, i.e., Baseline"
    flagged = _flagged(text)
    assert "differences" in flagged
    assert "i" not in flagged
    assert "e" not in flagged


def test_legitimate_minor_words_and_correct_title_case_remain_clean() -> None:
    assert _flagged("Performance of the Baseline Model on Benchmark Data") == set()
    assert "with" not in _flagged("Comparison with Prior Studies and Methods")


def test_mixed_punctuation_around_abbreviation_preserves_other_checks() -> None:
    text = "Toolkit Results (i.e., Open Baseline): major findings Overview"
    issues = check_apa_title_case_phrase(text)
    flagged = {i["word"] for i in issues}
    assert "i" not in flagged
    assert "e" not in flagged
    assert "major" in flagged
    assert "findings" in flagged


def test_lot_entry_with_ie_does_not_emit_r024_for_i() -> None:
    lines = [
        PdfTextLine(text="LIST OF TABLES", bbox=BBox(x0=220, y0=80, x1=390, y1=94)),
        PdfTextLine(
            text=(
                "Table 1.1 Widest Differences in Cross-Run ARI "
                "(within Same Toolkit, i.e., Baseline) .... 12"
            ),
            bbox=BBox(x0=108, y0=140, x1=540, y1=152),
        ),
        PdfTextLine(
            text="Table 1.2 Summary of Results Across All Experimental Settings .... 13",
            bbox=BBox(x0=108, y0=164, x1=540, y1=176),
        ),
        PdfTextLine(
            text="Table 1.3 Overview of the Proposed Evaluation Pipeline .... 14",
            bbox=BBox(x0=108, y0=188, x1=540, y1=200),
        ),
    ]
    block = PdfTextBlock(
        lines=lines,
        bbox=BBox(x0=100, y0=80, x1=560, y1=200),
        text="\n".join(line.text for line in lines),
    )
    doc = PdfDocument(
        path="synthetic.pdf",
        pages=[PdfPage(page_number=16, width=612, height=792, text_blocks=[block])],
    )
    findings = [
        f
        for f in check_pdf_toc_list_formatting(doc)
        if f.rule_id == "P024" and f.details.get("issue_type") == "list_of_tables_title_case"
    ]
    assert not any("'i'" in f.message for f in findings)
    assert findings == []
