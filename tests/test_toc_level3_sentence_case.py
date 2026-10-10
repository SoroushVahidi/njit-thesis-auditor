"""Synthetic boundaries for the established Q051 TOC sentence-case rule."""

from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from njit_auditor.finding_explanations import build_detailed_explanation
from njit_auditor.highlight_targeting import parse_highlight_bboxes_from_details
from njit_auditor.issue_type_explanations import explain_issue_type
from njit_auditor.pdf_highlight import build_highlighted_single_page_pdf
from njit_auditor.pdf_models import (
    BBox,
    PdfDocument,
    PdfPage,
    PdfTextBlock,
    PdfTextLine,
    PdfTextSpan,
)
from njit_auditor.polished_comments import build_polished_comment
from njit_auditor.rules.pdf_toc_list_formatting import check_pdf_toc_list_formatting
from njit_auditor.web_app import _public_rule_reference_id


def _document(
    target: str,
    *,
    heading: str = "TABLE OF CONTENTS",
    split_blocks: bool = False,
    wrapped: str = "",
    page_edge: float = 548,
    body_sentences: tuple[str, ...] = (),
) -> PdfDocument:
    rows = [
        ("CHAPTER 1 INTRODUCTION .... 1", 100, 140, 548),
        ("1.1 Background and Motivation .... 3", 120, 164, 548),
        ("1.1.1 A compliant section title .... 4", 145, 188, 548),
        (target, 145, 212, page_edge),
        ("1.1.3 Another compliant section title .... 6", 145, 260, 548),
    ]
    if wrapped:
        rows.insert(4, (wrapped, 160, 228, 548))
    lines = [PdfTextLine(text=heading, bbox=BBox(x0=200, y0=80, x1=400, y1=94))]
    lines += [
        PdfTextLine(text=text, bbox=BBox(x0=x0, y0=y, x1=x1, y1=y + 12))
        for text, x0, y, x1 in rows
    ]
    if split_blocks:
        blocks = [
            PdfTextBlock(lines=[line], bbox=line.bbox, text=line.text)
            for line in lines
        ]
    else:
        blocks = [PdfTextBlock(
            lines=lines,
            bbox=BBox(x0=100, y0=80, x1=548, y1=280),
            text="\n".join(line.text for line in lines),
        )]
    pages = [PdfPage(page_number=1, width=612, height=792, text_blocks=blocks)]
    if body_sentences:
        body_lines = []
        for index, sentence in enumerate(body_sentences):
            bbox = BBox(x0=100, y0=100 + 20 * index, x1=510, y1=112 + 20 * index)
            body_lines.append(PdfTextLine(
                text=sentence, bbox=bbox,
                spans=[PdfTextSpan(text=sentence, bbox=bbox, font="Times-Roman", size=12)],
            ))
        pages.append(PdfPage(
            page_number=2, width=612, height=792,
            text_blocks=[PdfTextBlock(
                lines=body_lines,
                bbox=BBox(x0=100, y0=100, x1=510, y1=112 + 20 * len(body_lines)),
                text="\n".join(body_sentences),
            )],
        ))
    return PdfDocument(path="synthetic.pdf", pages=pages)


def _level3_findings(document: PdfDocument):
    return [
        finding for finding in check_pdf_toc_list_formatting(document)
        if finding.details.get("entry_level") == "3"
    ]


def test_compliant_level1_level2_and_level3_entries() -> None:
    assert check_pdf_toc_list_formatting(_document(
        "1.1.2 Comparative analysis and experimental results .... 5"
    )) == []


@pytest.mark.parametrize("split_blocks", [False, True])
def test_clear_level3_title_case_is_q051_and_routes_to_r018c(
    split_blocks: bool,
) -> None:
    findings = _level3_findings(_document(
        "1.1.2 Comparative Analysis and Experimental Results .... 5",
        split_blocks=split_blocks,
    ))
    assert len(findings) == 1
    finding = findings[0]
    assert finding.rule_id == "P024"
    assert finding.details["issue_type"] == "toc_level_capitalization"
    assert finding.details["source_q_rule_id"] == "Q051"
    assert finding.details["entry_level"] == "3"
    assert _public_rule_reference_id(
        finding.rule_id,
        issue_type=finding.details["issue_type"],
        source_q_rule_id=finding.details["source_q_rule_id"],
        details=finding.details,
    ) == "P018C"
    assert "sentence case" in finding.details["suggested_fix"]
    comment = build_polished_comment(
        rule_id=finding.rule_id, issue_type=finding.details["issue_type"],
        page=finding.page, details=finding.details,
    )
    assert "Level 3" in comment and "sentence case" in comment
    assert "Level 2" not in comment
    assert "Level 3 uses sentence case" in explain_issue_type(
        finding.rule_id, finding.details["issue_type"], finding.details
    )
    assert "Level 3 = sentence case" in build_detailed_explanation(
        rule_id=finding.rule_id, issue_type=finding.details["issue_type"],
        details=finding.details, page=finding.page, has_highlight=True,
    )


@pytest.mark.parametrize("target", [
    "1.1.2 Comparative analysis and experimental results .... 5",
    "1.1.2 Problem Formulation .... 5",  # short title: abstain
    "1.1.2 Study of i.e. and e.g. examples in NASA data .... 5",
    "1.1.2 Effects of the ﬂuorescence signal in MRI data .... 5",
    "1.1.2 Bayesian inference with Markov models and DNA .... 5",
    "1.1.2 A study of problem Solving in MATLAB .... 5",  # one ordinary cap
    "1.1.2.1 Comparative Analysis and Experimental Results .... 5",
    "1.1.2.1.1 Comparative Analysis and Experimental Results .... 5",
    "1.1.2 Comparative Analysis and Experimental Results",  # no page number
])
def test_compliant_or_ambiguous_entries_abstain(target: str) -> None:
    assert _level3_findings(_document(target)) == []


def test_page_number_alignment_and_leaders_are_not_title_words() -> None:
    target = "1.1.2 Comparative Analysis and Experimental Results . . . 5"
    assert len(_level3_findings(_document(target))) == 1
    assert _level3_findings(_document(target, page_edge=505)) == []


def test_two_word_title_requires_repeated_lowercase_body_evidence() -> None:
    title = "1.1.2 Problem Formulation .... 5"
    ordinary = (
        "The formulation is explained here.",
        "This formulation has a measurable result.",
        "A similar formulation appears later.",
    )
    findings = _level3_findings(_document(title, body_sentences=ordinary))
    assert len(findings) == 1
    assert findings[0].details["source_q_rule_id"] == "Q051"
    assert _level3_findings(_document(title, body_sentences=ordinary[:2])) == []
    named = ordinary + (
        "The Formulation method is cited here.",
        "Another Formulation method is discussed.",
    )
    assert _level3_findings(_document(title, body_sentences=named)) == []
    assert _level3_findings(_document(
        "1.1.2 Methodology: Constraints .... 5",
        body_sentences=(
            "The constraints apply here.",
            "Those constraints remain active.",
            "Other constraints are documented.",
        ),
    )) == []


def test_wrapped_level3_highlight_spans_both_lines() -> None:
    findings = _level3_findings(_document(
        "1.1.2 Comparative Analysis and",
        wrapped="Experimental Results . . . 5",
    ))
    assert len(findings) == 1
    bbox = parse_highlight_bboxes_from_details(findings[0].details)
    assert len(bbox) == 1
    assert bbox[0][1] <= 212 and bbox[0][3] >= 240


@pytest.mark.parametrize("heading", ["LIST OF TABLES", "LIST OF FIGURES"])
def test_lists_are_not_toc_level3(heading: str) -> None:
    assert _level3_findings(_document(
        "1.1.2 Comparative Analysis and Experimental Results .... 5",
        heading=heading,
    )) == []


def test_highlighted_pdf_contains_visible_target(tmp_path: Path) -> None:
    target = "1.1.2 Comparative Analysis and Experimental Results .... 5"
    finding = _level3_findings(_document(target))[0]
    source = tmp_path / "synthetic.pdf"
    rendered = fitz.open()
    page = rendered.new_page(width=612, height=792)
    page.insert_text((145, 224), target)
    rendered.save(source)
    rendered.close()
    output = tmp_path / "highlighted.pdf"
    result = build_highlighted_single_page_pdf(
        source, output, source_page_number=finding.page,
        boxes=parse_highlight_bboxes_from_details(finding.details),
    )
    assert result.has_highlight
    with fitz.open(output) as highlighted:
        assert len(highlighted) == 1
        assert target in highlighted[0].get_text()
