"""Privacy-safe geometry cases for wrapped numbered body headings."""

from __future__ import annotations

from pathlib import Path

import pymupdf
import pytest

from njit_auditor.pdf_models import (
    BBox,
    PdfDocument,
    PdfGraphicBlock,
    PdfPage,
    PdfTextBlock,
    PdfTextLine,
    PdfTextSpan,
)
from njit_auditor.polished_comments import resolve_suggested_fix_for_display
from njit_auditor.report_outputs import audit_findings_to_json_dict
from njit_auditor.rules.pdf_body_heading_spacing import check_pdf_body_heading_spacing


def _line(
    text: str, x0: float, x1: float, y0: float, *, size: float = 12,
    font: str = "TestBold", bold: bool = True,
) -> PdfTextLine:
    bbox = BBox(x0=x0, y0=y0, x1=x1, y1=y0 + size)
    return PdfTextLine(
        text=text, bbox=bbox,
        spans=[PdfTextSpan(text=text, bbox=bbox, size=size, font=font, bold=bold)],
    )


def _block(*lines: PdfTextLine) -> PdfTextBlock:
    return PdfTextBlock(
        lines=list(lines), text="\n".join(line.text for line in lines),
        bbox=BBox(
            x0=min(line.bbox.x0 for line in lines),
            y0=min(line.bbox.y0 for line in lines),
            x1=max(line.bbox.x1 for line in lines),
            y1=max(line.bbox.y1 for line in lines),
        ),
    )


def _document(
    *, pitch: float = 24, continuation: str = "final words", split_blocks: bool = True,
    first_right: float = 540, second_x: float = 149, second_font: str = "TestBold",
    second_size: float = 12, second_bold: bool = True, second_y: float | None = None,
    second_right: float = 255, section: str = "body", heading_number: str = "2.3.5",
    body_pitch: float = 24, body_font: str = "TestRegular", body_size: float = 12,
    heading_size: float = 12,
) -> PdfDocument:
    chapter = _line("CHAPTER 1 INTRODUCTION", 190, 420, 70)
    number = _line(heading_number, 108, 137, 110, size=heading_size)
    title = _line(
        "Synthetic heading extends across the page edge", 149, first_right, 110,
        size=heading_size,
    )
    next_line = _line(
        continuation, second_x, second_right,
        110 + pitch if second_y is None else second_y,
        size=second_size, font=second_font, bold=second_bold,
    )
    prose = [
        _line(
            f"Synthetic prose line {i} has enough words for pitch calibration.",
            108, 540, 200 + i * body_pitch,
            size=body_size, font=body_font, bold=False,
        )
        for i in range(7)
    ]
    heading_blocks = (
        [_block(number, title, next_line)] if not split_blocks
        else [_block(number, title), _block(next_line)]
    )
    blocks = [_block(chapter), *heading_blocks, _block(*prose)]
    if section != "body":
        marker = {
            "toc": "TABLE OF CONTENTS", "lot": "LIST OF TABLES",
            "lof": "LIST OF FIGURES", "references": "REFERENCES",
        }[section]
        blocks.insert(0, _block(_line(marker, 200, 410, 45)))
    page = PdfPage(page_number=1, width=612, height=792, text_blocks=blocks)
    return PdfDocument(path="synthetic.pdf", pages=[page])


def test_double_spaced_wrap_highlight_and_remediation() -> None:
    findings = check_pdf_body_heading_spacing(_document())
    assert len(findings) == 1
    finding = findings[0]
    assert finding.rule_id == "P023"
    assert finding.details["issue_type"] == "multiline_body_heading_not_single_spaced"
    assert finding.details["bbox"] == "149.0,110.0,540.0,146.0"
    fix = resolve_suggested_fix_for_display("P023", finding.details["issue_type"])
    assert "Single-space the wrapped lines within this heading" in fix
    assert "heading and the body paragraph" in fix
    exported = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    assert exported["findings"][0]["student_visible_problem"] is True


@pytest.mark.parametrize("split_blocks", [False, True])
def test_correct_single_spaced_wrap_in_either_block_arrangement(split_blocks: bool) -> None:
    assert check_pdf_body_heading_spacing(_document(pitch=14, split_blocks=split_blocks)) == []


def test_double_spaced_wrap_in_same_block() -> None:
    assert len(check_pdf_body_heading_spacing(_document(split_blocks=False))) == 1


def test_single_line_heading_and_following_double_spaced_body() -> None:
    doc = _document(continuation="Synthetic body text follows the heading.", second_bold=False)
    assert check_pdf_body_heading_spacing(doc) == []


def test_distinct_consecutive_numbered_headings() -> None:
    doc = _document(continuation="2.3.6 Another separate heading")
    assert check_pdf_body_heading_spacing(doc) == []


def test_heading_followed_by_subtitle_abstains() -> None:
    assert check_pdf_body_heading_spacing(_document(first_right=355)) == []


@pytest.mark.parametrize("change", [
    {"second_font": "OtherBold"}, {"second_size": 14}, {"second_x": 108},
    {"second_y": 142}, {"body_pitch": 18},
])
def test_mixed_style_or_ambiguous_geometry_abstains(change: dict[str, object]) -> None:
    assert check_pdf_body_heading_spacing(_document(**change)) == []  # type: ignore[arg-type]


@pytest.mark.parametrize("section", ["toc", "lot", "lof", "references"])
def test_non_body_section_abstains(section: str) -> None:
    assert check_pdf_body_heading_spacing(_document(section=section)) == []


def test_caption_after_heading_abstains() -> None:
    doc = _document(continuation="Figure 2.4 Synthetic caption")
    assert check_pdf_body_heading_spacing(doc) == []


def test_mixed_body_font_still_uses_page_pitch() -> None:
    assert len(check_pdf_body_heading_spacing(_document(body_font="OtherRegular"))) == 1


def test_larger_heading_font_uses_font_normalized_page_pitch() -> None:
    doc = _document(heading_size=14, second_size=14, pitch=28)
    assert len(check_pdf_body_heading_spacing(doc)) == 1


def test_run_in_level_four_abstains() -> None:
    assert check_pdf_body_heading_spacing(_document(heading_number="2.3.5.1")) == []


def test_single_line_heading() -> None:
    doc = _document()
    doc.pages[0].text_blocks = [
        block for block in doc.pages[0].text_blocks
        if all(line.text != "final words" for line in block.lines)
    ]
    assert check_pdf_body_heading_spacing(doc) == []


_F05_ISSUE = "blank_line_above_level_three_heading"


def _baseline_line(text: str, left: float, right: float, baseline: float, *,
                   font: str = "TestRegular", bold: bool = False) -> PdfTextLine:
    line = _line(text, left, right, baseline - 10, font=font, bold=bold)
    line.baseline_y = baseline
    return line


def _before_heading_document(
    tmp_path: Path, *, gap: float = 64.9, pitch: float = 27.6, number: str = "2.4.6",
    glued: bool = False, wrap: bool = False, completed: bool = True,
    mixed: bool = False, bold: bool = True, float_in_gap: bool = False,
    shifted_preceding: bool = False, page_start: bool = False,
    caption: bool = False, vector_in_gap: bool = False,
) -> PdfDocument:
    path = tmp_path / "heading_spacing_source.pdf"
    with pymupdf.open() as source:
        source_page = source.new_page(width=612, height=792)
        if vector_in_gap:
            source_page.draw_line((110, 275), (490, 275), width=1)
        if page_start:
            source.new_page(width=612, height=792)
        source.save(path)
    chapter = _line("CHAPTER 2 METHODOLOGY", 190, 430, 71)
    prose = [
        _baseline_line(f"Synthetic paragraph line {i} of this controlled example",
                       110 if not shifted_preceding else 190, 510, 165 + i * pitch)
        for i in range(3)
    ]
    paragraph_end = "The previous synthetic paragraph ends here" + ("." if completed else "")
    end = 165 + 3 * pitch
    prose.append(_baseline_line(paragraph_end, prose[0].bbox.x0, 344, end))
    if mixed:
        prose[-1].spans.append(PdfTextSpan(
            text="z", bbox=BBox(x0=344, y0=end-8, x1=348, y1=end),
            font="TestMath", size=8, italic=True,
        ))
    first = end + gap if not page_start else 153
    heading = _baseline_line(f"{number} Synthetic heading for spacing", 110, 359, first,
                             font="TestBold", bold=bold)
    if glued:
        left = _baseline_line(number, 110, 136, first, font="TestBold", bold=bold)
        right = _baseline_line("Synthetic heading for spacing", 142, 359, first,
                               font="TestBold", bold=bold)
        heading.spans = [*left.spans, *right.spans]
        heading.text = number + right.text
    title = [heading]
    last = first
    if wrap:
        last += 14
        title.append(_baseline_line("Wrapped end of the title", 110, 245, last,
                                    font="TestBold", bold=True))
    following = [
        _baseline_line(f"Ordinary synthetic body text following the heading row {i}",
                       110, 509, last + (i + 1)*pitch)
        for i in range(3)
    ]
    page = PdfPage(page_number=1, width=612, height=792,
                   text_blocks=[_block(chapter), _block(*prose)])
    if caption:
        page.text_blocks.insert(1, _block(_baseline_line(
            "Figure 2.6 Synthetic caption starts here", 110, 395, 165 - pitch,
        )))
    elif glued:
        page.text_blocks.insert(1, _block(_baseline_line(
            "2.4Prior section heading", 110, 395, 165 - pitch, font="TestBold", bold=True,
        )))
    if page_start:
        second = PdfPage(page_number=2, width=612, height=792,
                         text_blocks=[_block(*title), _block(*following)])
        return PdfDocument(path=str(path), pages=[page, second])
    page.text_blocks.extend((_block(*title), _block(*following)))
    if float_in_gap:
        page.graphic_blocks = [PdfGraphicBlock(
            bbox=BBox(x0=130, y0=end + 8, x1=330, y1=first - 14),
        )]
    return PdfDocument(path=str(path), pages=[page])


@pytest.mark.parametrize("wrap", [False, True])
def test_f05_detects_full_blank_pitch_before_a_real_level_three_heading(
    tmp_path: Path, wrap: bool,
) -> None:
    doc = _before_heading_document(tmp_path, glued=True, wrap=wrap, mixed=True)
    (finding,) = check_pdf_body_heading_spacing(doc)
    assert finding.rule_id == "P023" and finding.page == 1
    assert finding.details["issue_type"] == _F05_ISSUE
    assert finding.details["heading_number"] == "2.4.6"
    assert finding.details["body_pitch_pt"] == "27.6"
    assert finding.details["preceding_baseline_gap_pt"] == "64.9"
    assert finding.details["source_feedback_id"] == "F05"
    x0, y0, x1, y1 = [float(part) for part in finding.details["bbox"].split(",")]
    assert (x0, y0, x1, y1) == (110, 302.7, 359, 328.7 if wrap else 314.7)
    assert "Remove the blank line above this level-three heading" in (
        resolve_suggested_fix_for_display("P023", _F05_ISSUE)
    )
    assert audit_findings_to_json_dict([finding], {"audit_type": "pdf"})["findings"][0][
        "student_visible_problem"
    ]


@pytest.mark.parametrize("change", [
    {"gap": 27.6}, {"gap": 47.4}, {"gap": 27.6, "wrap": True},
    {"pitch": 16}, {"number": "2.4"}, {"number": "2.4.6.1"},
    {"completed": False}, {"bold": False}, {"float_in_gap": True},
    {"shifted_preceding": True}, {"page_start": True},
    {"caption": True}, {"vector_in_gap": True},
])
def test_f05_abstains_without_a_same_page_blank_line_above_a_level_three_heading(
    tmp_path: Path, change: dict[str, object],
) -> None:
    doc = _before_heading_document(tmp_path, **change)  # type: ignore[arg-type]
    assert not [f for f in check_pdf_body_heading_spacing(doc)
                if f.details["issue_type"] == _F05_ISSUE]


def test_f05_uses_baselines_when_font_boxes_have_different_ascenders(tmp_path: Path) -> None:
    doc = _before_heading_document(tmp_path, gap=27.6)
    heading = doc.pages[0].text_blocks[2].lines[0]
    heading.bbox.y0 += 3
    assert check_pdf_body_heading_spacing(doc) == []


def test_f05_accepts_a_full_empty_baseline_at_the_boundary(tmp_path: Path) -> None:
    (finding,) = check_pdf_body_heading_spacing(_before_heading_document(tmp_path, gap=55.2))
    assert finding.details["preceding_baseline_gap_pt"] == "55.2"
