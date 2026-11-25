"""Synthetic checks for explicitly blank lines above page-opening headings."""

from pathlib import Path

import pymupdf
import pytest

from njit_auditor.audit_runner import run_pdf_audit_full
from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.report_outputs import audit_findings_to_json_dict, write_markdown_report
from njit_auditor.report_view import build_report_view
from njit_auditor.rules.pdf_section_page_top_spacing import check_pdf_section_page_top_spacing

ISSUE = "blank_line_before_opening_level_three_heading"
PITCH = 26
BODY_BASELINE = 83
PROSE = "The synthetic example measures an ordinary paragraph in the selected section"
HEADING = "1.2.2 Further observations from the synthetic trial"


def _text(
    page: pymupdf.Page, y: float, text: str, *, x: float = 108, font: str = "tiro",
) -> None:
    page.insert_text((x, y), text, fontname=font, fontsize=12)


def _pdf(path: Path, case: str = "positive") -> None:
    with pymupdf.open() as pdf:
        chapter = pdf.new_page(width=612, height=792)
        chapter_text = "ABSTRACT" if case == "front-matter" else "CHAPTER 1 INTRODUCTION"
        _text(chapter, BODY_BASELINE, chapter_text, x=207, font="tibo")
        _text(chapter, 170, "1.2 Background and methods", font="tibo")
        prev = pdf.new_page(width=612, height=792)
        previous_heading = (
            "1.4.1 Unrelated section"
            if case == "ghost-predecessor" else "1.2.1 Earlier observations"
        )
        _text(prev, 220, previous_heading, font="tibo")
        tail = 530 if case == "short-predecessor" else 706
        _text(prev, tail - PITCH, PROSE)
        ending = "which finishes the earlier section."
        if case == "unfinished-predecessor":
            ending = "with the following measurements"
        if case == "abbreviation":
            ending = "with an incomplete reference to fig."
        if case == "prior-caption":
            ending = "Figure 1.2 Previous sample results."
        _text(prev, tail, ending)
        _text(prev, 752, "2", x=320, font="tibo")
        if case == "interposed-blank-page":
            pdf.new_page(width=612, height=792)
        page = pdf.new_page(width=612, height=792)
        _text(page, 752, "3", x=320, font="tibo")
        if case not in {"normal-top", "page-break-without-marker"}:
            _text(page, BODY_BASELINE + (5 if case == "wrong-marker-baseline" else 0),
                  " ", x=146 if case == "wrong-marker-column" else 108)
        heading_y = BODY_BASELINE + 8
        if case != "normal-top":
            heading_y += PITCH
        title = HEADING
        if case == "different-parent":
            title = HEADING.replace("1.2.2", "1.3.2")
        elif case == "level-two":
            title = HEADING.replace("1.2.2", "1.3")
        elif case == "chapter":
            title = "CHAPTER 2 RESULTS"
        if case == "leading-caption":
            _text(page, 94, "Figure 1.3 First sample", font="tibo")
        if case == "leading-figure":
            image = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 22, 12), False)
            image.clear_with(130)
            page.insert_image(pymupdf.Rect(220, 92, 380, 108), pixmap=image)
        if case == "table":
            page.draw_rect(pymupdf.Rect(105, 113, 543, 210))
        if case == "ink-in-gap":
            page.draw_line((200, 89), (230, 89))
        _text(page, heading_y, title, font="tiro" if case == "plain-label" else "tibo")
        for row in range(3):
            y = heading_y + (row + 1) * PITCH
            _text(page, y + (4 if case == "irregular-pitch" and row == 2 else 0), PROSE)
        if case == "ambiguous-row":
            _text(page, heading_y, "Secondary title", x=463, font="tibo")
        if case == "missing-body":
            page.add_redact_annot(pymupdf.Rect(0, heading_y + 10, 612, 730), fill=False)
            page.apply_redactions()
        if case != "no-outline":
            point = pymupdf.Point(108, heading_y - (90 if case == "wrong-destination" else 16))
            entry = [3, title, len(pdf), {"kind": pymupdf.LINK_GOTO, "page": len(pdf)-1,
                                          "to": point}]
            if case == "wrong-bookmark-title":
                entry[1] = HEADING + " elsewhere"
            outline = [[1, "CHAPTER 1 INTRODUCTION", 1],
                       [2, "1.2 Background and methods", 1],
                       [3, "1.2.1 Earlier observations", 2, {
                           "kind": pymupdf.LINK_GOTO, "page": 1, "to": pymupdf.Point(108, 208),
                       }],
                       entry]
            if case == "duplicate-bookmark":
                outline.append(entry.copy())
            pdf.set_toc(outline)
        pdf.save(path)


def test_page_start_with_an_explicit_extra_line(tmp_path: Path) -> None:
    pdf = tmp_path / "positive.pdf"
    _pdf(pdf)
    failures: list[str] = []
    result = run_pdf_audit_full(pdf, check_failures=failures)
    assert not failures
    warning, = [finding for finding in result if finding.details.get("issue_type") == ISSUE]
    assert (warning.rule_id, warning.page, warning.severity) == ("P023", 3, Severity.WARNING)
    assert warning.details["blank_baseline_pt"] == "83.0"
    assert warning.details["heading_baseline_pt"] == "117.0"
    assert warning.details["body_pitch_pt"] == "26.0"
    assert warning.details["bbox"].startswith("108.0,")


@pytest.mark.parametrize("case", [
    "normal-top", "page-break-without-marker", "leading-caption", "leading-figure",
    "table", "ink-in-gap", "chapter", "level-two", "different-parent", "no-outline",
    "wrong-destination", "wrong-bookmark-title", "ambiguous-row", "irregular-pitch",
    "short-predecessor", "unfinished-predecessor", "front-matter", "plain-label",
    "wrong-marker-baseline", "wrong-marker-column", "interposed-blank-page",
    "prior-caption", "missing-body", "duplicate-bookmark", "abbreviation", "ghost-predecessor",
])
def test_valid_or_ambiguous_page_starts_abstain(tmp_path: Path, case: str) -> None:
    pdf = tmp_path / "negative.pdf"
    _pdf(pdf, case)
    assert check_pdf_section_page_top_spacing(load_pdf_layout(str(pdf))) == []


@pytest.mark.parametrize("case", ["missing-origin", "unknown-direction", "rotated", "unavailable"])
def test_unsupported_geometry_abstains(tmp_path: Path, case: str) -> None:
    pdf = tmp_path / "unsupported.pdf"
    _pdf(pdf)
    layout = load_pdf_layout(str(pdf))
    page = layout.pages[-1]
    heading = min((line for block in page.text_blocks for line in block.lines),
                  key=lambda line: line.bbox.y0)
    if case == "missing-origin":
        heading.spans[0].baseline_y = None
    elif case == "unknown-direction":
        heading.line_dir = None
    elif case == "rotated":
        page.page_rotation = 180
    else:
        page.text_extraction_unavailable = True
    assert check_pdf_section_page_top_spacing(layout) == []


def test_reports_keep_existing_ids_and_renumber_by_page(tmp_path: Path) -> None:
    before = AuditFinding(rule_id="P023", severity=Severity.WARNING, page=1, message="First")
    after = AuditFinding(rule_id="P016", severity=Severity.WARNING, page=4, message="Later")
    opening = AuditFinding(rule_id="P023", severity=Severity.WARNING, page=3, message="New",
                           details={"issue_type": ISSUE})
    meta = {"audit_type": "pdf"}
    report = audit_findings_to_json_dict([before, after, opening], meta)
    assert [row["page"] for row in report["findings"]] == [1, 4, 3]
    cards = build_report_view(report).findings
    assert [(card.finding_id, card.page, card.problem_number) for card in cards] == [
        ("f0", 1, 1), ("f2", 3, 2), ("f1", 4, 3),
    ]
    destination = tmp_path / "report.md"
    write_markdown_report([before, after, opening], meta, destination)
    text = destination.read_text()
    assert text.index("### Problem 1") < text.index("### Problem 2") < text.index("### Problem 3")
    assert "prescribed 8 pt" in text
