"""Heuristic paragraph indentation checks for layout-aware PDF text lines."""

from __future__ import annotations

from statistics import median

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument, PdfPage, PdfTextLine
from njit_auditor.rules.pdf_headings import EXPECTED_HEADINGS, normalize_heading_text
from njit_auditor.rules.pdf_page_numbers import PAGE_NUM_RE

EXPECTED_NORMAL_INDENT_PT = 36.0
INDENT_TOLERANCE_PT = 8.0
STRONG_INDENT_THRESHOLD_PT = 18.0
MIN_TEXT_LEN = 20
MAX_PARAGRAPH_GAP_PT = 14.0
X_GROUP_TOLERANCE_PT = 24.0
FIRST_LINE_INDENT_GROUP_TOLERANCE_PT = 96.0

TOC_LIKE_HEADINGS = {
    "TABLE OF CONTENTS",
    "LIST OF TABLES",
    "LIST OF FIGURES",
}


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
    return True


def _is_toc_or_list_page(page: PdfPage) -> bool:
    for block in page.text_blocks:
        for line in block.lines:
            normalized = normalize_heading_text(line.text).upper()
            if normalized in TOC_LIKE_HEADINGS:
                return True
    return False


def group_lines_into_paragraphs(page: PdfPage) -> list[list[PdfTextLine]]:
    """Group nearby lines into paragraph candidates on a page."""

    if _is_toc_or_list_page(page):
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


def check_pdf_indentation(pdf_document: PdfDocument) -> list[AuditFinding]:
    """Emit P015 warnings for strong likely indentation issues."""

    findings: list[AuditFinding] = []
    abstract_pages = _find_abstract_page_numbers(pdf_document)

    for page in pdf_document.pages:
        paragraphs = group_lines_into_paragraphs(page)
        if not paragraphs:
            continue

        seen_indented_paragraph = False
        for idx, paragraph in enumerate(paragraphs):
            indent_pt = _paragraph_indent_pt(paragraph)

            # Strong case: opening abstract/front-matter paragraph should be flush-left.
            if page.page_number in abstract_pages and idx == 0:
                if indent_pt > STRONG_INDENT_THRESHOLD_PT:
                    findings.append(
                        AuditFinding(
                            rule_id="P015",
                            severity=Severity.WARNING,
                            page=page.page_number,
                            message=(
                                "Opening paragraph appears unexpectedly indented where "
                                "flush-left is likely expected."
                            ),
                            details={
                                "page_number": str(page.page_number),
                                "indent_pt": f"{indent_pt:.1f}",
                                "expected": "flush_left",
                                "paragraph_line_count": str(len(paragraph)),
                                "suggested_fix": (
                                    "Remove first-line indent for opening front-matter paragraph."
                                ),
                            },
                        )
                    )
                continue

            if indent_pt >= STRONG_INDENT_THRESHOLD_PT:
                seen_indented_paragraph = True

            # Strong case: later paragraph likely expected to have first-line indent.
            if idx >= 1:
                likely_indented = (
                    abs(indent_pt - EXPECTED_NORMAL_INDENT_PT) <= INDENT_TOLERANCE_PT
                )
                if likely_indented or not seen_indented_paragraph:
                    continue
                if indent_pt < STRONG_INDENT_THRESHOLD_PT:
                    findings.append(
                        AuditFinding(
                            rule_id="P015",
                            severity=Severity.WARNING,
                            page=page.page_number,
                            message=(
                                "Later paragraph appears to be missing expected first-line "
                                "indentation."
                            ),
                            details={
                                "page_number": str(page.page_number),
                                "indent_pt": f"{indent_pt:.1f}",
                                "expected": "first_line_indent_approx_36pt",
                                "paragraph_line_count": str(len(paragraph)),
                                "suggested_fix": (
                                    "Apply consistent first-line indentation "
                                    "for non-opening paragraphs."
                                ),
                            },
                        )
                    )

    return findings
