"""Heuristic paragraph indentation checks for layout-aware PDF text lines."""

from __future__ import annotations

import re
from statistics import median

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument, PdfPage, PdfTextLine, format_bbox_detail
from njit_auditor.rules.pdf_headings import EXPECTED_HEADINGS, normalize_heading_text
from njit_auditor.rules.pdf_page_numbers import PAGE_NUM_RE

EXPECTED_NORMAL_INDENT_PT = 36.0
INDENT_TOLERANCE_PT = 8.0
STRONG_INDENT_THRESHOLD_PT = 18.0
MIN_TEXT_LEN = 20
MAX_PARAGRAPH_GAP_PT = 14.0
X_GROUP_TOLERANCE_PT = 24.0
FIRST_LINE_INDENT_GROUP_TOLERANCE_PT = 96.0
MAX_LINE_X_SPREAD_PT = 110.0
MAX_FINDINGS_PER_PAGE_ISSUE = 1
NEGATIVE_INDENT_IGNORE_PT = -8.0
MIN_LINES_FOR_MISSING_LATER_INDENT = 4
MIN_LIKELY_INDENTED_PARAGRAPHS_FOR_PAGE_STYLE = 2
MIN_INDENT_STYLE_CONFIDENCE_RATIO = 0.6

TOC_LIKE_HEADINGS = {
    "TABLE OF CONTENTS",
    "LIST OF TABLES",
    "LIST OF FIGURES",
}
REFERENCES_LIKE_HEADINGS = {
    "REFERENCES",
    "BIBLIOGRAPHY",
    "WORKS CITED",
}

CAPTION_PREFIX_RE = re.compile(r"^(figure|table)\s+[\divxlcdm]+[.:)]?\s+", re.IGNORECASE)
BULLET_PREFIX_RE = re.compile(r"^\s*(?:[-*•]|\d+[.)]|[a-zA-Z][.)])\s+")


def first_text_x(line: PdfTextLine) -> float:
    """Return the first text x position for a line."""

    return line.bbox.x0


def _is_page_number_line(line: PdfTextLine) -> bool:
    clean = " ".join(line.text.strip().split())
    return bool(clean and PAGE_NUM_RE.match(clean))


def _is_named_heading_line(line: PdfTextLine) -> bool:
    normalized = normalize_heading_text(line.text)
    return normalized.upper() in EXPECTED_HEADINGS


def _is_usable_paragraph_line(line: PdfTextLine) -> bool:
    if _is_named_heading_line(line) or _is_page_number_line(line):
        return False
    clean = " ".join(line.text.strip().split())
    if len(clean) < MIN_TEXT_LEN:
        return False
    if BULLET_PREFIX_RE.match(clean):
        return False
    if CAPTION_PREFIX_RE.match(clean):
        return False
    alpha_count = sum(ch.isalpha() for ch in clean)
    if alpha_count < 10:
        return False
    if alpha_count / max(len(clean), 1) < 0.45:
        return False
    return True


def _has_page_heading_in(page: PdfPage, headings: set[str]) -> bool:
    for block in page.text_blocks:
        for line in block.lines:
            normalized = normalize_heading_text(line.text).upper()
            if normalized in headings:
                return True
    return False


def group_lines_into_paragraphs(page: PdfPage) -> list[list[PdfTextLine]]:
    """Group nearby lines into paragraph candidates on a page."""

    if _has_page_heading_in(page, TOC_LIKE_HEADINGS):
        return []

    lines: list[PdfTextLine] = []
    for block in page.text_blocks:
        for line in block.lines:
            if _is_usable_paragraph_line(line):
                lines.append(line)

    if not lines:
        return []

    lines.sort(key=lambda line: (line.bbox.y0, line.bbox.x0))

    paragraphs: list[list[PdfTextLine]] = []
    current: list[PdfTextLine] = []
    prev_line: PdfTextLine | None = None

    for line in lines:
        if prev_line is None:
            current = [line]
            prev_line = line
            continue

        vertical_gap = line.bbox.y0 - prev_line.bbox.y1
        x_delta = abs(first_text_x(line) - first_text_x(prev_line))

        allowed_x_delta = (
            FIRST_LINE_INDENT_GROUP_TOLERANCE_PT if len(current) == 1 else X_GROUP_TOLERANCE_PT
        )
        if vertical_gap <= MAX_PARAGRAPH_GAP_PT and x_delta <= allowed_x_delta:
            current.append(line)
        else:
            if current:
                paragraphs.append(current)
            current = [line]

        prev_line = line

    if current:
        paragraphs.append(current)

    return [paragraph for paragraph in paragraphs if len(paragraph) >= 2]


def _paragraph_indent_pt(paragraph: list[PdfTextLine]) -> float:
    first_x = first_text_x(paragraph[0])
    rest_x = [first_text_x(line) for line in paragraph[1:]]
    median_rest_x = median(rest_x)
    return first_x - median_rest_x


def _find_abstract_page_numbers(pdf_document: PdfDocument) -> set[int]:
    pages: set[int] = set()
    for page in pdf_document.pages:
        for block in page.text_blocks:
            for line in block.lines:
                normalized = normalize_heading_text(line.text).upper()
                if normalized == "ABSTRACT":
                    pages.add(page.page_number)
                    break
    return pages


def _paragraph_is_low_confidence(paragraph: list[PdfTextLine]) -> bool:
    if len(paragraph) < 3:
        return True
    x_values = [first_text_x(line) for line in paragraph]
    return (max(x_values) - min(x_values)) > MAX_LINE_X_SPREAD_PT


def _is_likely_expected_indent(indent_pt: float) -> bool:
    return abs(indent_pt - EXPECTED_NORMAL_INDENT_PT) <= INDENT_TOLERANCE_PT


def check_pdf_indentation(pdf_document: PdfDocument) -> list[AuditFinding]:
    """Emit P015 warnings for strong likely indentation issues."""

    findings: list[AuditFinding] = []
    abstract_pages = _find_abstract_page_numbers(pdf_document)

    for page in pdf_document.pages:
        if _has_page_heading_in(page, REFERENCES_LIKE_HEADINGS):
            continue
        paragraphs = group_lines_into_paragraphs(page)
        if not paragraphs:
            continue

        paragraph_data: list[tuple[int, list[PdfTextLine], float]] = []
        for idx, paragraph in enumerate(paragraphs):
            if _paragraph_is_low_confidence(paragraph):
                continue
            paragraph_data.append((idx, paragraph, _paragraph_indent_pt(paragraph)))
        if not paragraph_data:
            continue

        likely_indented_count = 0
        likely_not_indented_count = 0
        for idx, paragraph, indent_pt in paragraph_data:
            if indent_pt >= STRONG_INDENT_THRESHOLD_PT:
                likely_indented_count += 1
            elif (
                NEGATIVE_INDENT_IGNORE_PT <= indent_pt < STRONG_INDENT_THRESHOLD_PT
                and len(paragraph) >= MIN_LINES_FOR_MISSING_LATER_INDENT
            ):
                likely_not_indented_count += 1

        comparable_count = likely_indented_count + likely_not_indented_count
        page_has_high_confidence_indent_style = (
            likely_indented_count >= MIN_LIKELY_INDENTED_PARAGRAPHS_FOR_PAGE_STYLE
            and comparable_count > 0
            and (likely_indented_count / comparable_count) >= MIN_INDENT_STYLE_CONFIDENCE_RATIO
        )

        seen_indented_paragraph = False
        page_issue_findings: dict[str, AuditFinding] = {}
        for idx, paragraph, indent_pt in paragraph_data:

            # Strong case: opening abstract/front-matter paragraph should be flush-left.
            if page.page_number in abstract_pages and idx == 0:
                if indent_pt > STRONG_INDENT_THRESHOLD_PT:
                    page_issue_findings["unexpected_opening_indent"] = AuditFinding(
                        rule_id="P015",
                        severity=Severity.WARNING,
                        page=page.page_number,
                        message=(
                            "Opening paragraph appears unexpectedly indented where "
                            "flush-left is likely expected."
                        ),
                        details={
                            "page_number": str(page.page_number),
                            "issue_type": "unexpected_opening_indent",
                            "indent_pt": f"{indent_pt:.1f}",
                            "expected": "flush_left",
                            "paragraph_line_count": str(len(paragraph)),
                            "paragraph_index": str(idx + 1),
                            "bbox": format_bbox_detail(paragraph[0].bbox),
                            "confidence": "high",
                            "suggested_fix": (
                                "Remove first-line indent for opening front-matter paragraph."
                            ),
                        },
                    )
                continue

            if indent_pt >= STRONG_INDENT_THRESHOLD_PT:
                seen_indented_paragraph = True

            # Strong case: later paragraph likely expected to have first-line indent.
            if idx >= 1:
                likely_indented = _is_likely_expected_indent(indent_pt)
                if likely_indented or not seen_indented_paragraph:
                    continue
                if not page_has_high_confidence_indent_style:
                    continue
                if len(paragraph) < MIN_LINES_FOR_MISSING_LATER_INDENT:
                    continue
                if NEGATIVE_INDENT_IGNORE_PT <= indent_pt < STRONG_INDENT_THRESHOLD_PT:
                    existing = page_issue_findings.get("missing_later_indent")
                    current = AuditFinding(
                        rule_id="P015",
                        severity=Severity.WARNING,
                        page=page.page_number,
                        message=(
                            "Later paragraph appears to be missing expected first-line "
                            "indentation."
                        ),
                        details={
                            "page_number": str(page.page_number),
                            "issue_type": "missing_later_indent",
                            "indent_pt": f"{indent_pt:.1f}",
                            "expected": "first_line_indent_approx_36pt",
                            "paragraph_line_count": str(len(paragraph)),
                            "paragraph_index": str(idx + 1),
                            "bbox": format_bbox_detail(paragraph[0].bbox),
                            "confidence": "high",
                            "suggested_fix": (
                                "Apply consistent first-line indentation "
                                "for non-opening paragraphs."
                            ),
                        },
                    )
                    if existing is None:
                        page_issue_findings["missing_later_indent"] = current
                    else:
                        existing_indent = float(existing.details.get("indent_pt", "999"))
                        if indent_pt < existing_indent:
                            page_issue_findings["missing_later_indent"] = current

        for issue_type in ("unexpected_opening_indent", "missing_later_indent"):
            if issue_type in page_issue_findings and MAX_FINDINGS_PER_PAGE_ISSUE >= 1:
                findings.append(page_issue_findings[issue_type])

    return findings
