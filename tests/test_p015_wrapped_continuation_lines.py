"""Regression tests for P015 wrapped-continuation-line false positives.

A reviewed sample flagged a line beginning "Eikonal regularization [8], which
enforces..." as a missing-first-line-indent paragraph start, but it was really a
wrapped continuation of the previous line ("One widely used strategy is"). The
line grouper can split one physical paragraph into two groups when the
inter-line gap runs slightly over MAX_PARAGRAPH_GAP_PT (e.g. on double-spaced
pages), so P015 must double-check that a candidate paragraph start isn't
actually mid-sentence before warning.
"""

from __future__ import annotations

from pathlib import Path

import fitz

from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.pdf_models import BBox, PdfPage, PdfTextBlock, PdfTextLine
from njit_auditor.rules.pdf_indentation import (
    _paragraph_is_continuation_of_previous,
    _paragraph_start_confidence,
    check_pdf_indentation,
    group_lines_into_paragraphs,
)


def _line(text: str, y0: float, y1: float, x0: float = 108.0) -> PdfTextLine:
    return PdfTextLine(text=text, bbox=BBox(x0=x0, y0=y0, x1=x0 + 300.0, y1=y1), spans=[])


def _make_split_paragraph_pdf(
    path: Path, *, prev_line: str, continuation_lines: list[str]
) -> None:
    """Two indented body paragraphs, then a third paragraph whose tail lines get
    split off by a borderline-large gap -- the exact shape of the reviewed bug."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((144, 120), "This is a synthetic paragraph line for indentation checks.")
    page.insert_text((108, 134), "Continuation synthetic paragraph line text.")
    page.insert_text((108, 148), "Continuation synthetic paragraph line text.")
    page.insert_text((144, 190), "This is a synthetic paragraph line for indentation checks.")
    page.insert_text((108, 204), "Continuation synthetic paragraph line text.")
    page.insert_text((108, 218), "Continuation synthetic paragraph line text.")
    page.insert_text((144, 260), "This is a synthetic paragraph line describing prior work.")
    page.insert_text((108, 274), prev_line)
    for i, text in enumerate(continuation_lines):
        page.insert_text((108, 324 + i * 14), text)
    doc.save(path)
    doc.close()


def test_eikonal_regularization_continuation_is_suppressed(tmp_path: Path) -> None:
    """The reviewed false positive: 'One widely used strategy is' + wrapped tail."""
    pdf_path = tmp_path / "eikonal.pdf"
    _make_split_paragraph_pdf(
        pdf_path,
        prev_line="One widely used strategy is",
        continuation_lines=[
            "Eikonal regularization [8], which enforces the unit gradient constraint and",
            "improves surface quality across the reconstruction domain significantly for",
            "the class of neural signed distance field reconstructions studied here in",
            "this dissertation chapter under a variety of controlled settings and cases.",
        ],
    )
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_indentation(model) if f.rule_id == "P015"]
    assert not findings


def test_previous_line_ending_with_comma_suppresses_p015(tmp_path: Path) -> None:
    pdf_path = tmp_path / "comma.pdf"
    _make_split_paragraph_pdf(
        pdf_path,
        prev_line="specifically the following methods, which are described below,",
        continuation_lines=[
            "which include several well-known regularization techniques used broadly",
            "across the literature for related reconstruction tasks in this general",
            "problem area under a variety of settings, scenarios, and configurations.",
            "each producing comparable results across the benchmark suite evaluated.",
        ],
    )
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_indentation(model) if f.rule_id == "P015"]
    assert not findings


def test_previous_line_ending_with_of_suppresses_p015(tmp_path: Path) -> None:
    pdf_path = tmp_path / "ends_of.pdf"
    _make_split_paragraph_pdf(
        pdf_path,
        prev_line="This is a synthetic paragraph line describing the study of",
        continuation_lines=[
            "surface reconstruction quality across many different settings and cases",
            "studied extensively throughout this dissertation chapter and its results,",
            "which are summarized in the following section for further discussion here.",
            "additional detail is provided in the appendix for interested readers too.",
        ],
    )
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_indentation(model) if f.rule_id == "P015"]
    assert not findings


def test_previous_line_ending_with_and_suppresses_p015(tmp_path: Path) -> None:
    pdf_path = tmp_path / "ends_and.pdf"
    _make_split_paragraph_pdf(
        pdf_path,
        prev_line="This is a synthetic paragraph line describing prior work and",
        continuation_lines=[
            "how it relates to the reconstruction quality metrics used throughout this",
            "dissertation chapter to evaluate the proposed method against baselines,",
            "which are described in detail in the following experimental section here.",
            "further analysis is provided later in this chapter for completeness too.",
        ],
    )
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_indentation(model) if f.rule_id == "P015"]
    assert not findings


def test_true_new_paragraph_after_complete_sentence_still_warns(tmp_path: Path) -> None:
    """A genuine new paragraph (prior sentence complete, real paragraph gap) must
    still be flagged when it is missing its first-line indent."""
    pdf_path = tmp_path / "true_new_paragraph.pdf"
    _make_split_paragraph_pdf(
        pdf_path,
        prev_line="This line ends a complete sentence describing prior work fully.",
        continuation_lines=[
            "This paragraph begins an entirely new topic after a real paragraph break.",
            "It continues describing the new topic across several more lines of text.",
            "The discussion proceeds further with additional supporting detail here.",
            "Finally the paragraph concludes with a closing summary statement here.",
        ],
    )
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_indentation(model) if f.rule_id == "P015"]
    assert findings
    assert findings[0].details.get("issue_type") == "missing_later_indent"
    assert findings[0].details.get("confidence") == "high"


def test_normal_wrapped_paragraph_stays_one_group() -> None:
    """Lines with normal (non-borderline) spacing and no punctuation ambiguity should
    already group into a single paragraph, never reaching the continuation check."""
    lines = [
        _line("One widely used strategy is", 274, 289),
        _line("Eikonal regularization, which enforces the unit gradient constraint.", 288, 303),
    ]
    block = PdfTextBlock(
        bbox=BBox(x0=108, y0=274, x1=450, y1=303),
        lines=lines,
        text=" ".join(ln.text for ln in lines),
    )
    page = PdfPage(page_number=1, width=612.0, height=792.0, text_blocks=[block])
    paragraphs = group_lines_into_paragraphs(page)
    assert len(paragraphs) == 1
    assert len(paragraphs[0]) == 2


def test_continuation_word_list_covers_reviewed_cue() -> None:
    prev_paragraph = [_line("One widely used strategy is", 274, 289)]
    current_paragraph = [
        _line("Eikonal regularization [8], which enforces the constraint and", 340, 355),
        _line("x", 354, 369),
        _line("x", 368, 383),
        _line("x", 382, 397),
    ]
    ordered_lines = prev_paragraph + current_paragraph
    assert _paragraph_is_continuation_of_previous(
        ordered_lines, [prev_paragraph, current_paragraph], 1
    )


def test_high_confidence_not_used_for_ambiguous_paragraph_start() -> None:
    """Previous line ends its sentence, but the gap is only borderline-large --
    not clearly a genuine paragraph break -- so confidence must not be High."""
    prev_paragraph = [_line("This line ends a complete sentence right here.", 260, 275)]
    current_paragraph = [
        _line("Flush continuation line right after a small gap here.", 291, 306),
        _line("x", 305, 320),
        _line("x", 319, 334),
        _line("x", 333, 348),
    ]
    ordered_lines = prev_paragraph + current_paragraph
    paragraphs = [prev_paragraph, current_paragraph]
    assert not _paragraph_is_continuation_of_previous(ordered_lines, paragraphs, 1)
    assert _paragraph_start_confidence(ordered_lines, paragraphs, 1) == "medium"


def test_high_confidence_used_for_clear_paragraph_start() -> None:
    """Previous line ends its sentence and the gap is a genuine paragraph-sized
    gap -- confidence should be High."""
    prev_paragraph = [_line("This line ends a complete sentence right here.", 260, 275)]
    current_paragraph = [
        _line("New paragraph starting after a big gap right here today.", 320, 335),
        _line("x", 334, 349),
        _line("x", 348, 363),
        _line("x", 362, 377),
    ]
    ordered_lines = prev_paragraph + current_paragraph
    paragraphs = [prev_paragraph, current_paragraph]
    assert _paragraph_start_confidence(ordered_lines, paragraphs, 1) == "high"


def test_orphaned_trailing_line_at_different_x_still_suppresses_p015(tmp_path: Path) -> None:
    """Reproduces the exact real-world EF-archive PDF quirk: a short trailing line
    ("One widely used strategy is") sits at the same y as the previous line but far
    to the right (the tail of a wrapped sentence), so the paragraph grouper drops it
    as an orphaned single-line group instead of attaching it to either neighbor.
    P015 must still recognize it as the true previous line and suppress the warning
    on the following wrapped continuation."""
    pdf_path = tmp_path / "orphaned_trailing_line.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((144, 120), "This is a synthetic paragraph line for indentation checks.")
    page.insert_text((108, 134), "Continuation synthetic paragraph line text.")
    page.insert_text((108, 148), "Continuation synthetic paragraph line text.")
    page.insert_text((144, 190), "This is a synthetic paragraph line for indentation checks.")
    page.insert_text((108, 204), "Continuation synthetic paragraph line text.")
    page.insert_text((108, 218), "Continuation synthetic paragraph line text.")
    page.insert_text((144, 260), "This is a synthetic paragraph line describing prior work.")
    page.insert_text((108, 274), "function behaves as a valid signed distance field.")
    page.insert_text((388, 274), "One widely used strategy is")
    page.insert_text((108, 298), "Eikonal regularization [9], which enforces the unit gradient")
    page.insert_text((108, 312), "constraint and improves reconstruction stability across the")
    page.insert_text((108, 326), "full range of settings and configurations studied in this work.")
    page.insert_text((108, 340), "Further analysis appears later in this dissertation chapter.")
    doc.save(pdf_path)
    doc.close()
    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_indentation(model) if f.rule_id == "P015"]
    assert not findings
