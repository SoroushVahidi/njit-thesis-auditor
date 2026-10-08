"""Numbered headings whose number and title are extracted as separate lines.

Sample-style PDFs can emit "3.4.3" and the heading title as two text lines on
one baseline (sometimes in separate blocks), and omit the whitespace spans
between the title's words. P027 must still see one level-3 heading, check it
once, and read its words with spaces restored.
"""

from __future__ import annotations

from njit_auditor.pdf_models import (
    BBox,
    PdfDocument,
    PdfPage,
    PdfTextBlock,
    PdfTextLine,
    PdfTextSpan,
)
from njit_auditor.rules.pdf_heading_levels import check_pdf_heading_level_styles

_Y0, _Y1 = 300.0, 312.0


def _words_line(words: list[str], x0: float, *, bold: bool = True, y0: float = _Y0) -> PdfTextLine:
    spans, x = [], x0
    for word in words:
        width = 6.0 * len(word)
        spans.append(
            PdfTextSpan(
                text=word,
                bbox=BBox(x0=x, y0=y0, x1=x + width, y1=y0 + 12),
                size=12.0,
                bold=bold,
                font="Times-Bold" if bold else "Times-Roman",
            )
        )
        x += width + 4.0  # visible gap, but no whitespace span (as extracted)
    return PdfTextLine(
        spans=spans, bbox=BBox(x0=x0, y0=y0, x1=x - 4.0, y1=y0 + 12), text="".join(words)
    )


def _doc(*lines: PdfTextLine, same_block: bool = False) -> PdfDocument:
    if same_block:
        blocks = [PdfTextBlock(lines=list(lines), bbox=lines[0].bbox, text="")]
    else:
        blocks = [PdfTextBlock(lines=[line], bbox=line.bbox, text=line.text) for line in lines]
    body = _words_line(
        ["Body", "text", "follows", "the", "heading", "here."], 108.0, bold=False, y0=340.0
    )
    blocks.append(PdfTextBlock(lines=[body], bbox=body.bbox, text=body.text))
    return PdfDocument(
        path="synthetic.pdf",
        pages=[PdfPage(page_number=5, width=612, height=792, text_blocks=blocks)],
    )


def _number(y0: float = _Y0, bold: bool = True) -> PdfTextLine:
    return _words_line(["3.4.3"], 108.0, bold=bold, y0=y0)


def _issue_types(doc: PdfDocument) -> list[str]:
    return [f.details["issue_type"] for f in check_pdf_heading_level_styles(doc)]


def test_split_title_case_level3_heading_is_flagged_once() -> None:
    title = _words_line(["Implementation,", "Experiments,", "and", "Results"], 149.0)
    for same_block in (False, True):
        assert _issue_types(_doc(_number(), title, same_block=same_block)) == [
            "level3_sentence_case_issue"
        ]


def test_rejoined_heading_reads_words_with_spaces() -> None:
    title = _words_line(["Implementation,", "Experiments,", "and", "Results"], 149.0)
    (finding,) = check_pdf_heading_level_styles(_doc(_number(), title))
    assert "3.4.3 Implementation, Experiments, and Results" in finding.message


def test_split_sentence_case_heading_is_not_flagged() -> None:
    title = _words_line(["Implementation", "and", "results"], 149.0)
    assert _issue_types(_doc(_number(), title)) == []


def test_number_and_title_on_different_baselines_are_not_joined() -> None:
    title = _words_line(["Implementation,", "Experiments,", "and", "Results"], 149.0, y0=_Y0 + 24)
    assert _issue_types(_doc(_number(), title)) == []


def test_non_bold_parts_are_not_joined() -> None:
    title = _words_line(["Implementation,", "Experiments,", "and", "Results"], 149.0, bold=False)
    assert _issue_types(_doc(_number(), title)) == []
    title_bold = _words_line(["Implementation,", "Experiments,", "and", "Results"], 149.0)
    assert _issue_types(_doc(_number(bold=False), title_bold)) == []


# ---------------------------------------------------------------------------
# Sentence case keeps proper names and labelled references capitalized
# (Ester: level 3 "sentence case, capitalizing only the first word and proper
# names"). Rejoined split headings exposed P027 to headings such as
# "... Markov Chains on Markov Spaces" or "Proof of Theorem 5.2, Part (i)".
# ---------------------------------------------------------------------------

from njit_auditor.rules.pdf_heading_levels import (  # noqa: E402
    _looks_like_title_case_violation,
    _sentence_case_example,
)


def test_labelled_references_keep_their_capital() -> None:
    assert not _looks_like_title_case_violation("Proof of Theorem 5.2, Part (i) and the bound")
    assert _sentence_case_example("4.2.1", "Proof of Theorem 5.2, Part (i) and the Bound") == (
        "4.2.1 Proof of Theorem 5.2, Part (i) and the bound"
    )


def test_document_proper_nouns_are_not_lowercased() -> None:
    proper = frozenset({"markov"})
    assert not _looks_like_title_case_violation("Ergodic Markov chains on Markov spaces", proper)
    assert _looks_like_title_case_violation("Ergodic Markov Chains on Markov Spaces", proper)
    assert _sentence_case_example("3.1.2", "Ergodic Markov Chains on Markov Spaces", proper) == (
        "3.1.2 Ergodic Markov chains on Markov spaces"
    )


def test_body_text_capitalization_identifies_proper_names() -> None:
    body = [
        _words_line(
            ["The", "chain", "is", "a", "Markov", "process", "here."], 108.0, bold=False, y0=400.0
        ),
        _words_line(
            ["We", "use", "a", "Markov", "kernel", "and", "the", "results", "below."],
            108.0,
            bold=False,
            y0=424.0,
        ),
        _words_line(
            ["Results", "and", "methods", "follow", "from", "our", "results."],
            108.0,
            bold=False,
            y0=448.0,
        ),
    ]
    heading_number = _number()
    heading_title = _words_line(["Markov", "Chains", "and", "Markov", "Results"], 149.0)
    doc = _doc(heading_number, heading_title, *body)
    # "Markov" is always capitalized mid-sentence (proper name); "Chains" and
    # "Results" are not, so the heading still has two title-cased major words.
    assert _issue_types(doc) == ["level3_sentence_case_issue"]
    (finding,) = check_pdf_heading_level_styles(doc)
    assert "Markov chains and Markov results" in finding.message
