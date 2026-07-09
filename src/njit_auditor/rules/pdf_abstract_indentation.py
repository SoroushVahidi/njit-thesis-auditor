"""Conservative Abstract page paragraph indentation checks (P044).

Partial heuristic PDF coverage for Q002 and Q003:
  - Q002: Does the first Abstract paragraph begin flush with the left margin?
  - Q003: Does every Abstract paragraph after the first begin with a visible indent?

Abstract page only. Does not duplicate P015 (general paragraph indentation).
Does not duplicate P043 (Acknowledgements page indentation).
Does not check Abstract word count (P021) or abstract heading style (P038).
"""

from __future__ import annotations

import re

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import (
    PdfDocument,
    PdfPage,
    PdfTextLine,
    format_bbox_detail,
)
from njit_auditor.rules.pdf_frontmatter_heading_gate import find_gate_heading_page_and_y

INDENT_THRESHOLD_PT = 18.0
MAX_PARA_GAP_PT = 14.0
MIN_TEXT_LEN = 20
MIN_PARA_BLOCKS = 2
LEFT_MARGIN_CLUSTER_TOLERANCE_PT = 8.0
_HEADING_LABEL = "ABSTRACT"
_PAGE_NUM_RE = re.compile(r"^\s*[\[(]?(?:\d+|[ivxlcdm]+)[\])]?[.]?\s*$", re.IGNORECASE)
# A line ending in sentence-terminal punctuation (optionally followed by a closing
# quote/paren) signals that the *next* line is free to start a new paragraph.
# Without that, a large vertical gap is more likely double-spacing/rendering
# jitter than a real paragraph break, and the next line is a wrapped
# continuation of the current sentence — see _group_paragraphs.
_SENTENCE_END_RE = re.compile(r"[.?!][\"'”’)\]]?\s*$")


def _is_usable_line(line: PdfTextLine) -> bool:
    cleaned = " ".join(line.text.strip().split())
    if len(cleaned) < MIN_TEXT_LEN:
        return False
    if _PAGE_NUM_RE.match(cleaned):
        return False
    alpha_count = sum(ch.isalpha() for ch in cleaned)
    return alpha_count >= 10 and alpha_count / max(len(cleaned), 1) >= 0.45


def _find_abstract_page_and_heading_y(
    pdf_document: PdfDocument,
) -> tuple[PdfPage, float] | None:
    """Return (page, heading_bottom_y) for the ABSTRACT page, or None."""
    return find_gate_heading_page_and_y(
        pdf_document, _HEADING_LABEL, require_unique=False
    )


def _lines_below_heading(
    page: PdfPage, heading_bottom_y: float
) -> list[PdfTextLine]:
    lines = []
    for block in page.text_blocks:
        for line in block.lines:
            if line.bbox.y0 <= heading_bottom_y + 2:
                continue
            if _is_usable_line(line):
                lines.append(line)
    sorted_lines = sorted(lines, key=lambda line: (line.bbox.y0, line.bbox.x0))
    if not sorted_lines:
        return []

    # Dissertation titles and bylines often sit between the ABSTRACT heading and
    # the real paragraph body. They are usually centered and should not become
    # paragraph 1 for P044. Find the first line that joins the shared left-margin
    # cluster, then keep any immediately-preceding wrapped line from that same
    # paragraph if needed.
    left_margin_x = min(line.bbox.x0 for line in sorted_lines)
    body_start_idx = next(
        (
            index
            for index, line in enumerate(sorted_lines)
            if line.bbox.x0 <= left_margin_x + LEFT_MARGIN_CLUSTER_TOLERANCE_PT
        ),
        0,
    )
    while body_start_idx > 0:
        gap = sorted_lines[body_start_idx].bbox.y0 - sorted_lines[body_start_idx - 1].bbox.y1
        if gap > MAX_PARA_GAP_PT:
            break
        body_start_idx -= 1
    return sorted_lines[body_start_idx:]


def _ends_sentence(line: PdfTextLine) -> bool:
    return bool(_SENTENCE_END_RE.search(line.text.strip()))


def _group_paragraphs(
    lines: list[PdfTextLine], left_margin: float
) -> list[list[PdfTextLine]]:
    """Group lines into paragraphs using indent, gap, and sentence-continuation evidence.

    A line starts a new paragraph when either:
      - it is visibly indented past the shared left margin (Q003's own signal
        that a new, correctly-indented paragraph has begun), or
      - it follows a large vertical gap *and* the previous line ends a
        sentence (a real paragraph break, not just a wide inter-line gap from
        double spacing).
    A flush-left line that merely continues the previous line's sentence
    (no terminal punctuation yet) is always treated as a continuation of the
    current paragraph, regardless of the raw vertical gap — this is what
    keeps a wrapped continuation line from being misread as a new,
    non-indented paragraph.
    """
    if not lines:
        return []
    groups: list[list[PdfTextLine]] = [[lines[0]]]
    for line in lines[1:]:
        prev_line = groups[-1][-1]
        gap = line.bbox.y0 - prev_line.bbox.y1
        indented = (line.bbox.x0 - left_margin) > INDENT_THRESHOLD_PT
        starts_new_paragraph = indented or (
            gap > MAX_PARA_GAP_PT and _ends_sentence(prev_line)
        )
        if starts_new_paragraph:
            groups.append([line])
        else:
            groups[-1].append(line)
    return groups


def check_pdf_abstract_indentation(
    pdf_document: PdfDocument,
) -> list[AuditFinding]:
    """Emit P044 warnings for Abstract paragraph indentation violations."""
    result = _find_abstract_page_and_heading_y(pdf_document)
    if result is None:
        return []

    page, heading_bottom_y = result
    lines = _lines_below_heading(page, heading_bottom_y)
    if not lines:
        return []

    left_margin = min(line.bbox.x0 for line in lines)
    paragraphs = _group_paragraphs(lines, left_margin)

    if not paragraphs:
        return []

    findings: list[AuditFinding] = []

    first_x0 = paragraphs[0][0].bbox.x0
    delta_first = first_x0 - left_margin
    if delta_first > INDENT_THRESHOLD_PT:
        findings.append(
            AuditFinding(
                rule_id="P044",
                severity=Severity.WARNING,
                page=page.page_number,
                message=(
                    "First Abstract paragraph appears to be indented rather "
                    "than flush-left, as required by NJIT guidelines (Q002)."
                ),
                details={
                    "page_number": str(page.page_number),
                    "issue_type": "abstract_first_paragraph_indented",
                    "paragraph_index": "0",
                    "observed_x0": f"{first_x0:.1f}",
                    "expected_left_margin": f"{left_margin:.1f}",
                    "indent_delta_points": f"{delta_first:.1f}",
                    "required_indent_points": "0.0",
                    "triage_tier": "medium",
                    "source_q_rule_id": "Q002",
                    "bbox": format_bbox_detail(paragraphs[0][0].bbox),
                },
            )
        )

    if len(paragraphs) < MIN_PARA_BLOCKS:
        return findings

    for idx, para in enumerate(paragraphs[1:], 1):
        para_x0 = para[0].bbox.x0
        delta = para_x0 - left_margin
        if delta < INDENT_THRESHOLD_PT:
            findings.append(
                AuditFinding(
                    rule_id="P044",
                    severity=Severity.WARNING,
                    page=page.page_number,
                    message=(
                        "Abstract paragraph after the first appears not to be "
                        "indented, as required by NJIT guidelines (Q003)."
                    ),
                    details={
                        "page_number": str(page.page_number),
                        "issue_type": "abstract_subsequent_paragraph_not_indented",
                        "paragraph_index": str(idx),
                        "observed_x0": f"{para_x0:.1f}",
                        "expected_left_margin": f"{left_margin:.1f}",
                        "indent_delta_points": f"{delta:.1f}",
                        "required_indent_points": f"{INDENT_THRESHOLD_PT:.1f}",
                        "triage_tier": "medium",
                        "source_q_rule_id": "Q003",
                        "bbox": format_bbox_detail(para[0].bbox),
                    },
                )
            )

    return findings
