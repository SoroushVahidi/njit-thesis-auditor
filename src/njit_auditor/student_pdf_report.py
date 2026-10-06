"""Compose a complete annotated thesis and its student-facing problem report.

The caller supplies the already-normalized, numbered web findings and boxes
obtained through the existing highlight-targeting path. This module only lays
out a PDF; it never interprets detector details or changes finding policy.
"""

from __future__ import annotations

import io
import os
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Any

import fitz
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from njit_auditor.issue_type_explanations import (
    has_curated_issue_type_title,
    humanize_issue_type,
    issue_type_title,
)
from njit_auditor.pdf_highlight import HighlightBox, build_highlighted_pdf, clip_box_to_page
from njit_auditor.report_outputs import public_display_rule_id
from njit_auditor.report_text import _detruncate_fix_text
from njit_auditor.report_view import SORT_MODE_PAGE, sort_findings


@dataclass(frozen=True)
class CombinedReportResult:
    total_visible_findings: int
    highlighted_findings: int
    unhighlighted_page_findings: int
    document_level_findings: int
    highlight_boxes_drawn: int
    pages_with_highlights: int
    thesis_pages: int
    report_pages: int
    markers_drawn: int


def ordered_student_findings(findings: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """Keep canonical problem numbers, sorting stably by physical PDF page."""
    return sort_findings(findings, SORT_MODE_PAGE)


def _field(finding: Mapping[str, Any], key: str) -> str:
    return str(finding.get(key) or "").strip()


def _public_rule(finding: Mapping[str, Any]) -> str:
    return public_display_rule_id(
        _field(finding, "public_rule_reference_id") or _field(finding, "rule_id")
    )


def _title(finding: Mapping[str, Any]) -> str:
    rule_id = _field(finding, "rule_id")
    issue_type = _field(finding, "issue_type")
    if has_curated_issue_type_title(rule_id, issue_type):
        return issue_type_title(rule_id, issue_type)
    return (
        humanize_issue_type(issue_type)
        or _field(finding, "issue_type_label")
        or "Formatting problem"
    )


def _fix(finding: Mapping[str, Any]) -> str:
    return _detruncate_fix_text(_field(finding, "rule_id"), _field(finding, "suggested_fix"))


def render_student_report_text(
    findings: Sequence[Mapping[str, Any]],
    *,
    file_name: str,
    manuscript_page_labels: Mapping[int, str] | None = None,
) -> str:
    """Text download using the same web problem identities and wording as the PDF."""
    labels = manuscript_page_labels or {}
    ordered = ordered_student_findings(findings)
    lines = [
        "NJIT THESIS/DISSERTATION FORMATTING AUDIT",
        "Formatting Problems",
        f"File: {file_name}",
        "",
    ]
    if not ordered:
        lines.append("No formatting problems were detected by the implemented checks.")
    current_page: int | None = None
    doc_heading = False
    for finding in ordered:
        page = finding.get("page")
        if page is None and not doc_heading:
            lines.extend(["", "DOCUMENT-LEVEL FINDINGS", ""])
            doc_heading = True
        elif page is not None and page != current_page:
            current_page = int(page)
            lines.extend(["", f"PDF PAGE {current_page}"])
            if labels.get(current_page):
                lines.append(f"Manuscript page: {labels[current_page]}")
            lines.append("")
        lines.append(
            f"Problem #{finding['problem_number']} — {_public_rule(finding)} — {_title(finding)}"
        )
        if _field(finding, "location_label"):
            lines.append(f"Location: {_field(finding, 'location_label')}")
        lines.append(f"What was detected: {_field(finding, 'polished_comment')}")
        if _fix(finding):
            lines.append(f"How to fix: {_fix(finding)}")
        if _field(finding, "confidence_label"):
            lines.append(f"Confidence: {_field(finding, 'confidence_label')}")
        if _field(finding, "detailed_explanation"):
            lines.append(f"More detail: {_field(finding, 'detailed_explanation')}")
        if page is not None and not finding.get(
            "_combined_has_highlight", finding.get("has_highlight", False)
        ):
            lines.append("Exact visual highlight unavailable.")
            if _field(finding, "no_highlight_reason"):
                lines.append(_field(finding, "no_highlight_reason"))
        lines.append(f"Public rule reference: {_public_rule(finding)}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    # ReportLab's built-in font handles ASCII reliably. A system DejaVu font
    # supports manuscript titles, names, and comments containing Unicode.
    font_name = "Helvetica"
    for candidate in (
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/local/share/fonts/DejaVuSans.ttf"),
    ):
        if candidate.exists():
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont

            if "StudentDejaVu" not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont("StudentDejaVu", str(candidate)))
            font_name = "StudentDejaVu"
            break
    return {
        "title": ParagraphStyle(
            "StudentTitle",
            parent=base["Title"],
            fontName=font_name,
            fontSize=17,
            leading=23,
            textColor=colors.HexColor("#12365a"),
            spaceAfter=12,
        ),
        "subtitle": ParagraphStyle(
            "StudentSubtitle",
            parent=base["Heading2"],
            fontName=font_name,
            fontSize=12,
            leading=17,
            textColor=colors.HexColor("#12365a"),
            spaceBefore=16,
            spaceAfter=7,
        ),
        "problem": ParagraphStyle(
            "StudentProblem",
            parent=base["Heading3"],
            fontName=font_name,
            fontSize=10.5,
            leading=15,
            textColor=colors.HexColor("#12365a"),
            spaceBefore=12,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "StudentBody",
            parent=base["BodyText"],
            fontName=font_name,
            fontSize=9,
            leading=14,
            spaceAfter=6,
            splitLongWords=True,
        ),
        "small": ParagraphStyle(
            "StudentSmall",
            parent=base["BodyText"],
            fontName=font_name,
            fontSize=8,
            leading=12,
            textColor=colors.HexColor("#4b5563"),
            spaceAfter=6,
            splitLongWords=True,
        ),
    }


def _p(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(text).replace("\n", "<br/>"), style)


def _report_page_footer(canvas: Any, document: Any) -> None:
    canvas.setStrokeColor(colors.HexColor("#d1d9e2"))
    canvas.line(54, 38, 558, 38)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#4b5563"))
    canvas.drawRightString(558, 25, f"Formatting Problems  |  Report page {document.page}")


def _report_pdf(
    findings: Sequence[Mapping[str, Any]],
    *,
    file_name: str,
    labels: Mapping[int, str],
) -> bytes:
    styles = _styles()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=(612, 792),
        leftMargin=54,
        rightMargin=54,
        topMargin=50,
        bottomMargin=50,
        title="NJIT Formatting Problems",
        author="NJIT Thesis Auditor",
    )
    story: list[Any] = [
        _p("NJIT Thesis/Dissertation Formatting Audit", styles["title"]),
        _p("Formatting Problems", styles["subtitle"]),
        _p(f"File: {file_name}", styles["body"]),
        _p(
            "The preceding pages contain your thesis with detected formatting problems "
            "highlighted where an exact location was available. The problems below are "
            "listed in document order. Problem numbers correspond to numbered highlights "
            "when shown.",
            styles["body"],
        ),
    ]
    pages = {int(f["page"]) for f in findings if f.get("page") is not None}
    rules = {_public_rule(f) for f in findings}
    story.append(
        _p(
            f"{len(findings)} problems  |  {len(pages)} pages affected  |  "
            f"{len(rules)} rules flagged",
            styles["body"],
        )
    )
    if not findings:
        story.append(
            _p(
                "No formatting problems were detected by the implemented checks. "
                "This automated check does not establish full compliance with NJIT requirements.",
                styles["body"],
            )
        )
    current_page: int | None = None
    doc_heading = False
    for finding in findings:
        page = finding.get("page")
        if page is None and not doc_heading:
            story.append(_p("DOCUMENT-LEVEL FINDINGS", styles["subtitle"]))
            doc_heading = True
        elif page is not None and page != current_page:
            current_page = int(page)
            story.append(_p(f"PDF PAGE {current_page}", styles["subtitle"]))
            if labels.get(current_page):
                story.append(_p(f"Manuscript page: {labels[current_page]}", styles["small"]))
        heading = (
            f"Problem #{finding['problem_number']} — {_public_rule(finding)} — {_title(finding)}"
        )
        block: list[Any] = [_p(heading, styles["problem"])]
        if _field(finding, "location_label"):
            block.append(_p(f"Location: {_field(finding, 'location_label')}", styles["small"]))
        block.append(
            _p(f"What was detected: {_field(finding, 'polished_comment')}", styles["body"])
        )
        if _fix(finding):
            block.append(_p(f"How to fix: {_fix(finding)}", styles["body"]))
        if _field(finding, "confidence_label"):
            block.append(_p(f"Confidence: {_field(finding, 'confidence_label')}", styles["small"]))
        if _field(finding, "detailed_explanation"):
            block.append(
                _p(f"More detail: {_field(finding, 'detailed_explanation')}", styles["small"])
            )
        if page is not None and not finding.get("_combined_has_highlight", False):
            block.append(_p("Exact visual highlight unavailable.", styles["small"]))
            if _field(finding, "no_highlight_reason"):
                block.append(_p(_field(finding, "no_highlight_reason"), styles["small"]))
        block.append(Spacer(1, 5))
        # The heading stays with the first text line; long explanations can
        # flow naturally onto subsequent report pages.
        story.extend(block)
    story.append(
        _p(
            "Automated checks can miss issues or flag acceptable formatting. "
            "Confirm findings against the current NJIT guidelines before submission.",
            styles["small"],
        )
    )
    doc.build(story, onFirstPage=_report_page_footer, onLaterPages=_report_page_footer)
    return buffer.getvalue()


def _marker_rect(
    page: fitz.Page, box: tuple[float, float, float, float], number: int, occupied: list[fitz.Rect]
) -> fitz.Rect | None:
    label = f"#{number}"
    width = max(17.0, fitz.get_text_length(label, fontsize=8) + 7)
    x0, y0, x1, y1 = box
    positions = ((x0 - width - 3, y0), (x1 + 3, y0), (x0, y0 - 16), (x0, y1 + 3))
    for x, y in positions:
        rect = fitz.Rect(x, y, x + width, y + 13)
        if rect in page.rect and all(not rect.intersects(other) for other in occupied):
            return rect
    return None


def build_combined_student_pdf_report(
    source_pdf: Path,
    output_pdf: Path,
    findings: Sequence[Mapping[str, Any]],
    *,
    boxes_by_problem: Mapping[int, Sequence[HighlightBox | tuple[float, float, float, float]]],
    file_name: str,
    manuscript_page_labels: Mapping[int, str] | None = None,
) -> CombinedReportResult:
    """Atomically write the original thesis, visual marks, and appended report."""
    ordered = ordered_student_findings(findings)
    numbers = [int(f["problem_number"]) for f in ordered]
    if numbers != list(range(1, len(ordered) + 1)):
        raise ValueError("student findings must have canonical, page-ordered problem numbers")
    labels = manuscript_page_labels or {}
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output_pdf.parent, prefix="student-pdf-") as temp_name:
        temp_dir = Path(temp_name)
        annotated_path = temp_dir / "annotated.pdf"
        with fitz.open(source_pdf) as source:
            thesis_pages = source.page_count
            page_sizes = [(p.rect.width, p.rect.height) for p in source]
        selected: dict[int, list[HighlightBox]] = {}
        primary: dict[int, tuple[int, tuple[float, float, float, float]]] = {}
        drawn_findings: set[int] = set()
        for finding in ordered:
            page_raw = finding.get("page")
            if page_raw is None:
                continue
            page = int(page_raw)
            if not 1 <= page <= thesis_pages:
                continue
            number = int(finding["problem_number"])
            for box in boxes_by_problem.get(number, ()):
                clipped = clip_box_to_page(box, *page_sizes[page - 1])
                if clipped is None:
                    continue
                selected.setdefault(page, []).append(
                    box if isinstance(box, HighlightBox) else HighlightBox.from_tuple(box)
                )
                drawn_findings.add(number)
                if number not in primary and getattr(box, "kind", "default") not in {
                    "guide",
                    "overflow_display",
                }:
                    primary[number] = (page, clipped)
        highlight_result = build_highlighted_pdf(
            source_pdf, annotated_path, selected, max_boxes_per_page=None
        )
        thesis_path = annotated_path if highlight_result.has_highlight else source_pdf
        display_findings = [
            dict(f, _combined_has_highlight=int(f["problem_number"]) in drawn_findings)
            for f in ordered
        ]
        report_bytes = _report_pdf(display_findings, file_name=file_name, labels=labels)
        markers_drawn = 0
        with (
            fitz.open(thesis_path) as thesis,
            fitz.open(stream=report_bytes, filetype="pdf") as report,
        ):
            report_page_count = report.page_count
            # Draw one visible problem badge per finding with a reliable
            # primary box. P011's existing line-index markers remain intact.
            occupied_by_page: dict[int, list[fitz.Rect]] = {}
            for number, (page_number, box) in primary.items():
                page = thesis[page_number - 1]
                occupied = occupied_by_page.setdefault(page_number, [])
                marker = _marker_rect(page, box, number, occupied)
                if marker is None:
                    continue
                shape = page.new_shape()
                shape.draw_rect(marker)
                shape.finish(color=(0.15, 0.20, 0.45), fill=(1, 1, 1), width=0.7)
                shape.commit(overlay=True)
                page.insert_text(
                    (marker.x0 + 3, marker.y1 - 3),
                    f"#{number}",
                    fontsize=8,
                    color=(0.15, 0.20, 0.45),
                )
                occupied.append(marker)
                markers_drawn += 1
            with fitz.open() as combined:
                combined.insert_pdf(thesis, annots=True)
                combined.insert_pdf(report)
                combined.set_toc([[1, "Thesis", 1], [1, "Formatting Problems", thesis_pages + 1]])
                temp_output = temp_dir / "combined.pdf"
                combined.save(temp_output, garbage=4, deflate=True)
        os.replace(temp_output, output_pdf)
        return CombinedReportResult(
            total_visible_findings=len(ordered),
            highlighted_findings=len(drawn_findings),
            unhighlighted_page_findings=sum(
                1
                for f in ordered
                if f.get("page") is not None and int(f["problem_number"]) not in drawn_findings
            ),
            document_level_findings=sum(1 for f in ordered if f.get("page") is None),
            highlight_boxes_drawn=highlight_result.drawn_count,
            pages_with_highlights=len(highlight_result.pages_highlighted),
            thesis_pages=thesis_pages,
            report_pages=report_page_count,
            markers_drawn=markers_drawn,
        )
