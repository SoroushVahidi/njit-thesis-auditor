"""R018/P018: wrapped TOC titles must not continue left of the title text.

Ester's 2026-09-23 clarification: "When a title runs for more than one line,
the second line should align with the text of the first line, not the
number." The November 18 clarification accepts valid rightward indentation
of second and third lines. These tests render synthetic TOC pages (invented titles, no
dissertation text) so the real ``load_pdf_layout`` glyph-geometry path is
exercised end to end.
"""

from pathlib import Path

import fitz
import pytest

from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.pdf_models import (
    BBox,
    PdfDocument,
    PdfPage,
    PdfTextBlock,
    PdfTextLine,
    PdfTextSpan,
)
from njit_auditor.rules.pdf_toc_alignment import check_pdf_toc_alignment
from njit_auditor.toc_entry_geometry import title_text_start_x

FONT = "tiro"
SIZE = 12.0
LEADER = "." * 40
ISSUE = "wrapped_title_continuation_misaligned"


def _text_width(text: str) -> float:
    return fitz.get_text_length(text, fontname=FONT, fontsize=SIZE)


def _render(tmp_path: Path, heading: str, rows: list[tuple[float, float, str]]) -> Path:
    pdf_path = tmp_path / "toc.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((250, 90), heading, fontname=FONT, fontsize=SIZE)
    for x, y, text in rows:
        page.insert_text((x, y), text, fontname=FONT, fontsize=SIZE)
    doc.save(pdf_path)
    doc.close()
    return pdf_path


def _findings(pdf_path: Path, issue_type: str = ISSUE) -> list:
    model = load_pdf_layout(str(pdf_path))
    return [
        f
        for f in check_pdf_toc_alignment(model)
        if f.rule_id == "P018" and f.details.get("issue_type") == issue_type
    ]


NUMBER_X = 144.0
LABEL = "1.3.3 "
TITLE_X = NUMBER_X + _text_width(LABEL)


def _wrapped_toc_rows(continuation_x: float) -> list[tuple[float, float, str]]:
    """One wrapped level-3 entry surrounded by single-line peers."""

    return [
        (108.0, 140.0, f"1 INTRODUCTION {LEADER} 1"),
        (126.0, 168.0, f"1.1 Background {LEADER} 2"),
        (NUMBER_X, 196.0, f"{LABEL}Sampling design for the long survey of"),
        (continuation_x, 210.0, f"coastal sites {LEADER} 5"),
        (NUMBER_X, 238.0, f"1.3.4 Summary {LEADER} 7"),
    ]


def test_continuation_aligned_with_title_text_is_not_flagged(tmp_path: Path) -> None:
    pdf = _render(tmp_path, "TABLE OF CONTENTS", _wrapped_toc_rows(TITLE_X))
    assert _findings(pdf) == []


def test_continuation_aligned_with_section_number_is_flagged(tmp_path: Path) -> None:
    pdf = _render(tmp_path, "TABLE OF CONTENTS", _wrapped_toc_rows(NUMBER_X))
    findings = _findings(pdf)
    assert len(findings) == 1
    details = findings[0].details
    assert details["continuation_alignment"] == "section_number"
    assert details["measurement"] == "glyph"
    assert details["affected_entry_count"] == "1"
    assert abs(float(details["worst_delta_pt"]) - (TITLE_X - NUMBER_X)) < 0.6


def test_continuation_left_of_section_number_is_flagged(tmp_path: Path) -> None:
    """The reviewer-identified shape: wrapped line flush with a shallower level."""

    pdf = _render(tmp_path, "TABLE OF CONTENTS", _wrapped_toc_rows(126.0))
    findings = _findings(pdf)
    assert len(findings) == 1
    assert findings[0].details["continuation_alignment"] == "left_of_section_number"


def test_small_coordinate_jitter_is_not_flagged(tmp_path: Path) -> None:
    for jitter in (-1.5, 1.5):
        case = tmp_path / f"jitter_{jitter}"
        case.mkdir()
        pdf = _render(case, "TABLE OF CONTENTS", _wrapped_toc_rows(TITLE_X + jitter))
        assert _findings(pdf) == [], jitter


def test_continuation_indented_past_title_text_is_accepted(tmp_path: Path) -> None:
    """The later reviewer clarification accepts continuation-line indentation."""
    pdf = _render(tmp_path, "TABLE OF CONTENTS", _wrapped_toc_rows(TITLE_X + 12.0))
    assert _findings(pdf) == []


def test_multiple_continuation_lines_are_each_checked(tmp_path: Path) -> None:
    aligned = [
        (NUMBER_X, 196.0, f"{LABEL}Sampling design for the long survey of"),
        (TITLE_X, 210.0, "coastal and estuarine monitoring sites across"),
        (TITLE_X, 224.0, f"three seasons {LEADER} 5"),
    ]
    second_misaligned = [
        (NUMBER_X, 196.0, f"{LABEL}Sampling design for the long survey of"),
        (TITLE_X, 210.0, "coastal and estuarine monitoring sites across"),
        (NUMBER_X, 224.0, f"three seasons {LEADER} 5"),
    ]
    peers = [
        (108.0, 140.0, f"1 INTRODUCTION {LEADER} 1"),
        (126.0, 168.0, f"1.1 Background {LEADER} 2"),
        (NUMBER_X, 252.0, f"1.3.4 Summary {LEADER} 7"),
    ]
    ok_dir = tmp_path / "ok"
    ok_dir.mkdir()
    assert _findings(_render(ok_dir, "TABLE OF CONTENTS", peers + aligned)) == []
    bad_dir = tmp_path / "bad"
    bad_dir.mkdir()
    findings = _findings(_render(bad_dir, "TABLE OF CONTENTS", peers + second_misaligned))
    assert len(findings) == 1
    assert findings[0].details["affected_entry_count"] == "1"


def test_second_and_third_line_indents_are_accepted_but_left_shift_is_not(
    tmp_path: Path,
) -> None:
    peers = [
        (108.0, 140.0, f"1 INTRODUCTION {LEADER} 1"),
        (NUMBER_X, 252.0, f"1.3.4 Summary {LEADER} 7"),
    ]
    first = (NUMBER_X, 168.0, f"{LABEL}Sampling design for the long survey of")
    second = (TITLE_X + 8.0, 182.0, "coastal and estuarine sites across")
    valid_dir = tmp_path / "valid"
    valid_dir.mkdir()
    valid = _render(
        valid_dir, "TABLE OF CONTENTS",
        [*peers, first, second, (TITLE_X + 15.0, 196.0, f"three seasons {LEADER} 5")],
    )
    assert _findings(valid) == []

    invalid_dir = tmp_path / "invalid"
    invalid_dir.mkdir()
    invalid = _render(
        invalid_dir, "TABLE OF CONTENTS",
        [*peers, first, second, (NUMBER_X, 196.0, f"three seasons {LEADER} 5")],
    )
    assert len(_findings(invalid)) == 1


def test_non_wrapped_entries_are_unaffected(tmp_path: Path) -> None:
    rows = [
        (108.0, 140.0, f"1 INTRODUCTION {LEADER} 1"),
        (126.0, 168.0, f"1.1 Background {LEADER} 2"),
        (NUMBER_X, 196.0, f"1.1.1 Scope {LEADER} 3"),
        (NUMBER_X, 224.0, f"1.1.2 Methods {LEADER} 4"),
    ]
    assert _findings(_render(tmp_path, "TABLE OF CONTENTS", rows)) == []


def test_unnumbered_wrapped_entry_does_not_use_numbered_logic(tmp_path: Path) -> None:
    rows = [
        (108.0, 140.0, f"1 INTRODUCTION {LEADER} 1"),
        (108.0, 168.0, "APPENDIX A SUPPLEMENTARY MEASUREMENTS FROM THE"),
        (108.0, 182.0, f"FIELD CAMPAIGN {LEADER} 90"),
        (108.0, 210.0, f"REFERENCES {LEADER} 95"),
    ]
    assert _findings(_render(tmp_path, "TABLE OF CONTENTS", rows)) == []


def test_wrapped_alignment_check_stays_in_table_of_contents(tmp_path: Path) -> None:
    """R018's wrapped-title rule was stated for the TOC; List pages keep their
    own entry-number rules and are not silently brought into scope."""

    rows = [
        (108.0, 140.0, f"1.1 Map of the survey area {LEADER} 3"),
        (108.0, 168.0, "1.2 Sampling design for the long survey of"),
        (108.0, 182.0, f"coastal sites {LEADER} 5"),
        (108.0, 210.0, f"1.3 Summary chart {LEADER} 7"),
    ]
    assert _findings(_render(tmp_path, "LIST OF FIGURES", rows)) == []


def test_title_start_estimate_without_glyph_geometry_is_a_lower_bound() -> None:
    """Spans without per-character geometry fall back to a lower-bound
    estimate, which can only understate the title start (hide, not invent,
    a misalignment)."""

    text = f"{LABEL}Sampling design"
    width = _text_width(text)
    span = PdfTextSpan(
        text=text,
        bbox=BBox(x0=NUMBER_X, y0=100.0, x1=NUMBER_X + width, y1=112.0),
        size=SIZE,
    )
    line = PdfTextLine(spans=[span], bbox=span.bbox, text=text)
    estimate, exact = title_text_start_x(line, len(LABEL.strip()))
    assert exact is False
    assert estimate is not None
    assert NUMBER_X < estimate <= TITLE_X


@pytest.mark.parametrize(
    ("label", "number_x"),
    [("3 ", 108.0), ("1.2 ", 126.0), ("2.3.4.1 ", 162.0), ("10.12 ", 126.0)],
)
def test_section_number_width_does_not_change_the_title_reference(
    tmp_path: Path, label: str, number_x: float
) -> None:
    """Short, deep, and multi-digit labels all measure against their own
    title-text start, never the number."""

    title_x = number_x + _text_width(label)
    peers = [
        (108.0, 140.0, f"1 INTRODUCTION {LEADER} 1"),
        (number_x, 224.0, f"{label}Closing Notes {LEADER} 9"),
    ]
    first = (number_x, 168.0, f"{label}Sampling design for the long survey of")
    ok_dir = tmp_path / "ok"
    ok_dir.mkdir()
    ok_rows = [*peers, first, (title_x, 182.0, f"coastal sites {LEADER} 5")]
    assert _findings(_render(ok_dir, "TABLE OF CONTENTS", ok_rows)) == []
    bad_dir = tmp_path / "bad"
    bad_dir.mkdir()
    bad_rows = [*peers, first, (number_x, 182.0, f"coastal sites {LEADER} 5")]
    findings = _findings(_render(bad_dir, "TABLE OF CONTENTS", bad_rows))
    assert len(findings) == 1
    assert findings[0].details["continuation_alignment"] == "section_number"


def _unmeasured_row(x: float, y: float, text: str) -> PdfTextLine:
    width = _text_width(text)
    span = PdfTextSpan(text=text, bbox=BBox(x0=x, y0=y, x1=x + width, y1=y + 12.0), size=SIZE)
    return PdfTextLine(spans=[span], bbox=span.bbox, text=text)


def _unmeasured_toc(continuation_x: float) -> PdfDocument:
    """Rows without per-character geometry, forcing the estimated fallback."""

    heading = _unmeasured_row(250.0, 80.0, "TABLE OF CONTENTS")
    rows = [
        heading,
        _unmeasured_row(108.0, 130.0, f"1 INTRODUCTION {LEADER} 1"),
        _unmeasured_row(NUMBER_X, 158.0, f"{LABEL}Sampling design for the long survey of"),
        _unmeasured_row(continuation_x, 172.0, f"coastal sites {LEADER} 5"),
        _unmeasured_row(NUMBER_X, 200.0, f"1.3.4 Summary {LEADER} 7"),
    ]
    block = PdfTextBlock(lines=rows, bbox=BBox(x0=0.0, y0=60.0, x1=612.0, y1=780.0), text="")
    page = PdfPage(page_number=1, width=612.0, height=792.0, text_blocks=[block])
    return PdfDocument(path="<test>", pages=[page])


def _findings_for(doc: PdfDocument) -> list:
    return [
        f
        for f in check_pdf_toc_alignment(doc)
        if f.details.get("issue_type") == ISSUE
    ]


def test_estimated_geometry_flags_left_shift_with_low_confidence() -> None:
    findings = _findings_for(_unmeasured_toc(NUMBER_X))
    assert len(findings) == 1
    assert findings[0].details["measurement"] == "estimated_lower_bound"
    assert findings[0].details["confidence"] == "low"


def test_estimated_geometry_never_flags_a_rightward_shift() -> None:
    """The estimate understates the title start, so it cannot prove a
    continuation sits too far right; stay silent rather than guess."""

    assert _findings_for(_unmeasured_toc(TITLE_X)) == []
    assert _findings_for(_unmeasured_toc(TITLE_X + 12.0)) == []


def test_njit_model_front_matter_toc_has_no_wrapped_alignment_finding() -> None:
    """NJIT's own model TOC (public guideline PDF) hangs wrapped titles exactly
    under the title text; it must stay clean."""

    guidelines = Path(__file__).resolve().parents[2] / "data" / "raw" / "guidelines"
    guide = guidelines / "Front Matter Pages Lorem Ipsum.pdf"
    model = load_pdf_layout(str(guide))
    new_types = {
        "wrapped_title_continuation_misaligned",
        "title_to_leader_gap_too_wide",
        "leader_dots_before_final_title_line",
    }
    assert [
        f for f in check_pdf_toc_alignment(model) if f.details.get("issue_type") in new_types
    ] == []


def test_every_misaligned_wrapped_entry_is_highlighted(tmp_path: Path) -> None:
    """Ester boxed three misaligned wrapped entries; highlight each one, not only the worst."""
    rows = [
        (108.0, 140.0, f"1 INTRODUCTION {LEADER} 1"),
        (126.0, 168.0, f"1.1 Background {LEADER} 2"),
        (NUMBER_X, 196.0, f"{LABEL}Sampling design for the long survey of"),
        (NUMBER_X, 210.0, f"coastal sites {LEADER} 5"),
        (NUMBER_X, 238.0, "1.3.4 Measurement protocol for the repeated survey of"),
        (NUMBER_X - 20.0, 252.0, f"inland sites {LEADER} 7"),
        (NUMBER_X, 280.0, f"1.3.5 Summary {LEADER} 9"),
    ]
    (finding,) = _findings(_render(tmp_path, "TABLE OF CONTENTS", rows))
    from njit_auditor.highlight_targeting import parse_highlight_bboxes_from_details

    boxes = parse_highlight_bboxes_from_details(finding.details)
    assert finding.details["affected_entry_count"] == "2"
    assert len(boxes) == 2
    assert boxes[0][1] < 200 < boxes[1][1]  # one box per entry, in page order
