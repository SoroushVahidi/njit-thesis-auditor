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

# Numbered body section heading: "2.4 Perceived Barriers", "3.6.1 Sub-section Title"
# Requires at least one level separator (dot+digit) so bare "1 Introduction" is excluded.
_BODY_SECTION_HEADING_RE = re.compile(r"^\d+(?:\.\d+)+\s+\S")
# Chapter/appendix heading in the body region: "CHAPTER 1 INTRODUCTION"
_BODY_CHAPTER_HEADING_RE = re.compile(r"^(?:CHAPTER|APPENDIX)\s+[\dA-Z]")

# Equation-continuation lines after displayed math often start flush-left with these words.
_EQUATION_CONTINUATION_START_RE = re.compile(
    r"^(?:where|with|such that|for|and|or|while|in which)\b",
    re.IGNORECASE,
)
# Symbol-heavy displayed-equation markers in the PDF text layer.
_DISPLAY_EQUATION_MARKER_RE = re.compile(
    r"(?:[=→↦⟶≥≤±∑∫√]|:\s*R\b|\bR[\^³²]|\bf[\wθ({])",
    re.IGNORECASE,
)
_MAX_EQUATION_TO_CONTINUATION_GAP_PT = 36.0
_MAX_FIRST_LINE_WRAP_GAP_PT = 6.0
_SHORT_FIRST_LINE_CHARS = 24


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


def _is_section_heading_line(line: PdfTextLine) -> bool:
    """Return True for lines that act as section headings, resetting indent expectations.

    Covers named front-matter headings, chapter/appendix headings, and numbered
    body section headings like "2.4 Perceived Barriers".  Prose sentences that
    happen to start with a section reference are excluded by the 100-char cap and
    the no-trailing-punctuation guard.
    """
    if _is_named_heading_line(line):
        return True
    clean = " ".join(line.text.strip().split())
    if not clean or len(clean) > 100:
        return False
    if clean.endswith((".", ",", ";")):
        return False
    return bool(
        _BODY_SECTION_HEADING_RE.match(clean) or _BODY_CHAPTER_HEADING_RE.match(clean)
    )


def _is_math_font(font_name: str) -> bool:
    base = font_name.lower().split("+")[-1]
    return base.startswith(
        ("cmmi", "cmsy", "cmex", "msam", "msbm", "wasy", "symbol", "zapf")
    )


def _line_clean_text(line: PdfTextLine) -> str:
    return " ".join(line.text.strip().split())


def _starts_equation_continuation(paragraph: list[PdfTextLine]) -> bool:
    return bool(_EQUATION_CONTINUATION_START_RE.match(_line_clean_text(paragraph[0])))


def _is_displayed_equation_line(line: PdfTextLine) -> bool:
    """Return True when a line looks like displayed math rather than body prose."""
    if _is_named_heading_line(line) or _is_page_number_line(line):
        return False
    clean = _line_clean_text(line)
    if not clean:
        return False
    if _is_usable_paragraph_line(line):
        return False

    if line.spans:
        math_spans = sum(1 for span in line.spans if span.font and _is_math_font(span.font))
        if math_spans and math_spans >= max(1, len(line.spans) // 2):
            return True

    alpha_count = sum(ch.isalpha() for ch in clean)
    if _DISPLAY_EQUATION_MARKER_RE.search(clean) and alpha_count < 20:
        return True
    if re.search(r"[θαβγδλμσφω]", clean):
        return True
    symbol_count = sum(not ch.isalnum() and not ch.isspace() for ch in clean)
    return len(clean) <= 40 and symbol_count >= 2 and alpha_count <= 12


def _paragraph_follows_displayed_equation(
    page: PdfPage,
    paragraph: list[PdfTextLine],
) -> bool:
    """Return True when a displayed-equation line sits just above the paragraph."""
    start_y = paragraph[0].bbox.y0
    for block in page.text_blocks:
        for line in block.lines:
            if line is paragraph[0]:
                continue
            gap = start_y - line.bbox.y1
            if gap < -2.0 or gap > _MAX_EQUATION_TO_CONTINUATION_GAP_PT:
                continue
            if _is_section_heading_line(line):
                return False
            if _is_displayed_equation_line(line):
                return True
    return False


def _paragraph_is_equation_continuation_exempt(
    page: PdfPage,
    paragraph: list[PdfTextLine],
) -> bool:
    return _starts_equation_continuation(paragraph) and _paragraph_follows_displayed_equation(
        page, paragraph
    )


def _paragraph_highlight_bbox(paragraph: list[PdfTextLine]) -> tuple[float, float, float, float]:
    """Return a drawable bbox for the first logical line of a paragraph."""
    first = paragraph[0]
    boxes = [first.bbox]
    if len(paragraph) > 1:
        second = paragraph[1]
        first_text = _line_clean_text(first)
        second_text = _line_clean_text(second)
        wrapped_continuation = (
            len(first_text) <= _SHORT_FIRST_LINE_CHARS
            and second_text
            and second_text[0].islower()
            and (second.bbox.y0 - first.bbox.y1) <= _MAX_FIRST_LINE_WRAP_GAP_PT
        )
        if wrapped_continuation:
            boxes.append(second.bbox)
    x0 = min(box.x0 for box in boxes)
    y0 = min(box.y0 for box in boxes)
    x1 = max(box.x1 for box in boxes)
    y1 = max(box.y1 for box in boxes)
    return (x0, y0, x1, y1)


def _find_heading_exempt_paragraph_indices(
    page: PdfPage, paragraphs: list[list[PdfTextLine]]
) -> frozenset[int]:
    """Return indices of paragraphs that are opening paragraphs after a section heading.

    Two cases are detected:
    * A heading line falls in the vertical gap between paragraph[idx-1] and paragraph[idx].
    * paragraph[idx][0] is itself a heading (heading grouped with opening body line
      due to tight vertical spacing in the source PDF).

    These opening paragraphs are flush-left by NJIT convention and must not be
    flagged for missing first-line indentation.
    """
    exempt: set[int] = set()

    heading_spans: list[tuple[float, float]] = []
    for block in page.text_blocks:
        for line in block.lines:
            if _is_section_heading_line(line):
                heading_spans.append((line.bbox.y0, line.bbox.y1))

    for idx, paragraph in enumerate(paragraphs):
        if _is_section_heading_line(paragraph[0]):
            exempt.add(idx)
            continue
        if idx == 0 or not heading_spans:
            continue
        prev_end_y = paragraphs[idx - 1][-1].bbox.y1
        this_start_y = paragraph[0].bbox.y0
        for hy0, hy1 in heading_spans:
            if hy0 >= prev_end_y - 4.0 and hy1 <= this_start_y + 4.0:
                exempt.add(idx)
                break

    return frozenset(exempt)


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


# Headings whose pages are handled atomically by dedicated detectors.
# ABSTRACT → P044 covers Q002 and Q003.
# ACKNOWLEDGEMENTS → P043 covers Q044 and Q045.
_P015_EXCLUDED_HEADINGS: frozenset[str] = frozenset({"ABSTRACT", "ACKNOWLEDGEMENTS"})


def _find_excluded_page_numbers(pdf_document: PdfDocument) -> set[int]:
    """Return page numbers covered by P043/P044 that P015 should skip."""
    pages: set[int] = set()
    for page in pdf_document.pages:
        for block in page.text_blocks:
            for line in block.lines:
                normalized = normalize_heading_text(line.text).upper()
                if normalized in _P015_EXCLUDED_HEADINGS:
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
    """Emit P015 indentation warnings for body-text paragraph layout.

    Skips Abstract pages (Q002/Q003 handled atomically by P044) and Acknowledgements
    pages (Q044/Q045 handled atomically by P043).  P015A flags a first paragraph after
    a section heading that is indented; P015B flags later body paragraphs missing
    first-line indent when the page style supports indentation.
    """
    findings: list[AuditFinding] = []
    excluded_pages = _find_excluded_page_numbers(pdf_document)

    for page in pdf_document.pages:
        if page.page_number in excluded_pages:
            continue
        if _has_page_heading_in(page, REFERENCES_LIKE_HEADINGS):
            continue
        paragraphs = group_lines_into_paragraphs(page)
        if not paragraphs:
            continue

        heading_exempt = _find_heading_exempt_paragraph_indices(page, paragraphs)

        paragraph_data: list[tuple[int, list[PdfTextLine], float]] = []
        for idx, paragraph in enumerate(paragraphs):
            if _paragraph_is_low_confidence(paragraph):
                continue
            paragraph_data.append((idx, paragraph, _paragraph_indent_pt(paragraph)))
        if not paragraph_data:
            continue

        # Opening paragraphs after headings are flush-left by convention; exclude them
        # from the style-confidence stats so they don't dilute the indented-paragraph ratio.
        likely_indented_count = 0
        likely_not_indented_count = 0
        for idx, paragraph, indent_pt in paragraph_data:
            if idx in heading_exempt:
                continue
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
            if idx in heading_exempt and indent_pt >= STRONG_INDENT_THRESHOLD_PT:
                current = AuditFinding(
                    rule_id="P015",
                    severity=Severity.WARNING,
                    page=page.page_number,
                    message=(
                        "First paragraph after a heading appears indented but should "
                        "be flush-left."
                    ),
                    details={
                        "page_number": str(page.page_number),
                        "issue_type": "unexpected_opening_indent",
                        "indent_pt": f"{indent_pt:.1f}",
                        "expected": "flush_left_opening_paragraph",
                        "paragraph_line_count": str(len(paragraph)),
                        "paragraph_index": str(idx + 1),
                        "bbox": format_bbox_detail(_paragraph_highlight_bbox(paragraph)),
                        "confidence": "high",
                        "suggested_fix": (
                            "Remove the first-line indent from the first paragraph "
                            "after the heading."
                        ),
                    },
                )
                page_issue_findings["unexpected_opening_indent"] = current

            if indent_pt >= STRONG_INDENT_THRESHOLD_PT:
                seen_indented_paragraph = True

            # Detect body-text paragraphs after the first that are missing first-line indent.
            if idx >= 1:
                if idx in heading_exempt:
                    continue  # first paragraph after a section heading — flush-left expected
                likely_indented = _is_likely_expected_indent(indent_pt)
                if likely_indented or not seen_indented_paragraph:
                    continue
                if not page_has_high_confidence_indent_style:
                    continue
                if len(paragraph) < MIN_LINES_FOR_MISSING_LATER_INDENT:
                    continue
                if _paragraph_is_equation_continuation_exempt(page, paragraph):
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
                            "bbox": format_bbox_detail(_paragraph_highlight_bbox(paragraph)),
                            "confidence": "high",
                            "suggested_fix": (
                                "Apply a first-line indent to each body paragraph after "
                                "the first paragraph in the section."
                            ),
                        },
                    )
                    if existing is None:
                        page_issue_findings["missing_later_indent"] = current
                    else:
                        existing_indent = float(existing.details.get("indent_pt", "999"))
                        if indent_pt < existing_indent:
                            page_issue_findings["missing_later_indent"] = current

        if page_issue_findings and MAX_FINDINGS_PER_PAGE_ISSUE >= 1:
            findings.extend(page_issue_findings.values())

    return findings
