"""Synthetic source and geometry controls for P016 page-top blank lines."""

from pathlib import Path

import pymupdf
import pytest

from njit_auditor.audit_runner import run_pdf_audit_full
from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.report_outputs import audit_findings_to_json_dict, write_markdown_report
from njit_auditor.report_view import build_report_view
from njit_auditor.rules.pdf_body_page_top_spacing import check_pdf_body_page_top_spacing

ISSUE = "blank_line_above_continuing_body_text"
PROSE = (
    "Subsequent measurements confirm the model and provide independent observations",
    "for the comparison, which uses synthetic data under repeatable conditions",
    "and provides a shorter final line for this paragraph.",
)
BODY_BASELINE = 85
BODY_PITCH = 26


def _line(page: pymupdf.Page, y: float, text: str, *, x: float = 108, font: str = "tiro") -> None:
    page.insert_text((x, y), text, fontname=font, fontsize=12)


def _document(path: Path, case: str) -> None:
    with pymupdf.open() as pdf:
        opening = pdf.new_page(width=612, height=792)
        heading = "ABSTRACT" if case == "front-matter" else "CHAPTER 1 INTRODUCTION"
        _line(opening, 85, heading, x=225, font="tibo")
        if case != "chapter-predecessor":
            previous = pdf.new_page(width=612, height=792)
            _line(previous, BODY_BASELINE + (5 if case == "baseline-drift" else 0), PROSE[0])
            _line(previous, BODY_BASELINE + BODY_PITCH, PROSE[1])
            if case == "after-figure":
                image = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 34, 52), False)
                image.clear_with(120)
                previous.insert_image(pymupdf.Rect(140, 160, 480, 680), pixmap=image)
                _line(previous, 707, "Figure 1.1 The preceding figure stays with its caption.")
            elif case not in {"short-previous", "footer-on-short-previous"}:
                _line(previous, 707 - BODY_PITCH, PROSE[1])
                _line(previous, 707, "the preceding page was filled with ordinary running prose")
            if case == "footer-on-short-previous":
                _line(previous, 709, "Department footer", x=262)
            _line(previous, 752, "2", x=320, font="tibo")
        page = pdf.new_page(width=612, height=792)
        # Write the folio first so extraction order can differ from reading order.
        _line(page, 752, "3", x=320, font="tibo")
        if case not in {"no-source-marker", "normal-top"}:
            _line(page, BODY_BASELINE + (5 if case == "misplaced-marker" else 0), " ",
                  x=200 if case == "wrong-gutter" else 108,
                  font="helv" if case == "wrong-font" else "tiro")
        start = BODY_BASELINE + (0 if case == "normal-top" else BODY_PITCH)
        if case == "less-than-one-line":
            start -= 5
        if case in {"new-heading", "caption", "references"}:
            label = {
                "new-heading": "1.2 The following section",
                "caption": "Figure 1.2 This is a synthetic caption",
                "references": "REFERENCES",
            }[case]
            _line(page, start, label, font="tibo")
            start += BODY_PITCH
        if case == "ink-in-gap":
            page.draw_line((150, 89), (480, 92), width=1)
        if case == "boxed-text":
            page.draw_rect(pymupdf.Rect(104, 104, 545, 176))
        if case == "intentional-blank-page":
            pdf.save(path)
            return
        for index, text in enumerate(PROSE):
            pitch = 32 if case == "irregular-pitch" and index == 2 else BODY_PITCH
            _line(page, start + index * pitch, text, x=130 if case == "different-column" else 108)
        if case == "table":
            _line(page, start + BODY_PITCH, "Secondary column", x=460)
        pdf.save(path)


@pytest.mark.parametrize("case", ["prose", "after-figure"])
def test_reports_only_a_confirmed_blank_line(tmp_path: Path, case: str) -> None:
    path = tmp_path / "body.pdf"
    _document(path, case)
    failures: list[str] = []
    results = run_pdf_audit_full(path, check_failures=failures)
    assert failures == []
    finding, = [item for item in results if item.details.get("issue_type") == ISSUE]
    assert (finding.rule_id, finding.page) == ("P016", 3)
    assert finding.details["blank_baseline_pt"] == "85.0"
    assert finding.details["first_text_baseline_pt"] == "111.0"
    assert finding.details["body_line_pitch_pt"] == "26.0"
    assert finding.details["bbox"].startswith("108.0,")
    assert results[-1] == finding


@pytest.mark.parametrize("case", [
    "normal-top", "no-source-marker", "misplaced-marker", "wrong-gutter", "wrong-font",
    "less-than-one-line", "new-heading", "caption", "references", "short-previous",
    "front-matter", "chapter-predecessor", "ink-in-gap", "intentional-blank-page",
    "irregular-pitch", "different-column", "table", "baseline-drift",
    "footer-on-short-previous", "boxed-text",
])
def test_unproven_openings_abstain(tmp_path: Path, case: str) -> None:
    path = tmp_path / "control.pdf"
    _document(path, case)
    assert check_pdf_body_page_top_spacing(load_pdf_layout(str(path))) == []


@pytest.mark.parametrize("unsupported", [
    "origin", "direction", "source", "physical-gap", "rotation", "extraction", "nonfinite",
])
def test_missing_or_inconsistent_geometry_abstains(tmp_path: Path, unsupported: str) -> None:
    path = tmp_path / "body.pdf"
    _document(path, "prose")
    document = load_pdf_layout(str(path))
    page = document.pages[-1]
    lines = (line for block in page.text_blocks for line in block.lines)
    line = min(lines, key=lambda row: row.bbox.y0)
    if unsupported == "origin":
        line.baseline_y = None
    elif unsupported == "direction":
        line.line_dir = (0, 1)
    elif unsupported == "source":
        document.path = str(tmp_path / "missing.pdf")
    elif unsupported == "physical-gap":
        page.original_page_index = 7
    elif unsupported == "rotation":
        page.page_rotation = 90
    elif unsupported == "extraction":
        page.text_extraction_unavailable = True
    elif unsupported == "nonfinite":
        line.bbox.y0 = float("nan")
    assert check_pdf_body_page_top_spacing(document) == []


def test_existing_finding_ids_survive_earlier_page_top_warning(tmp_path: Path) -> None:
    before = AuditFinding(rule_id="P016", page=2, severity=Severity.WARNING, message="Older gap")
    after = before.model_copy(update={"page": 4})
    new = before.model_copy(update={"page": 3, "details": {"issue_type": ISSUE}})
    metadata = {"audit_type": "pdf"}
    baseline = audit_findings_to_json_dict([before, after], metadata)
    candidate = audit_findings_to_json_dict([before, after, new], metadata)
    assert [row["page"] for row in candidate["findings"]] == [2, 4, 3]
    baseline_ids = {
        finding.page: finding.finding_id for finding in build_report_view(baseline).findings
    }
    view = build_report_view(candidate)
    cards = [
        (finding.page, finding.finding_id, finding.problem_number) for finding in view.findings
    ]
    assert cards == [(2, baseline_ids[2], 1), (3, "f2", 2), (4, baseline_ids[4], 3)]
    report = tmp_path / "report.md"
    write_markdown_report([before, after, new], metadata, report)
    text = report.read_text()
    assert text.index("### Problem 1") < text.index("### Problem 2") < text.index("### Problem 3")
