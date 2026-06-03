"""Conservative Acknowledgements page paragraph indentation checks (P043).

Partial heuristic PDF coverage for Q044 and Q045:
  - Q044: Does the first Acknowledgements paragraph begin flush with the left margin?
  - Q045: Does every Acknowledgements paragraph after the first begin with a visible indent?

Acknowledgements page only. Does not duplicate P015 (general paragraph indentation).
Does not check Acknowledgements content, heading style, or page numbering.
"""

from __future__ import annotations

import re

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument, PdfPage, PdfTextLine
from njit_auditor.rules.pdf_headings import find_named_frontmatter_headings, normalize_heading_text

INDENT_THRESHOLD_PT = 18.0
MAX_PARA_GAP_PT = 14.0
MIN_TEXT_LEN = 20
MIN_PARA_BLOCKS = 2
_HEADING_LABEL = "ACKNOWLEDGEMENTS"
_PAGE_NUM_RE = re.compile(r"^\s*[\[(]?(?:\d+|[ivxlcdm]+)[\])]?[.]?\s*$", re.IGNORECASE)


def _is_usable_line(line: PdfTextLine) -> bool:
    cleaned = " ".join(line.text.strip().split())
    if len(cleaned) < MIN_TEXT_LEN:
        return False
    if _PAGE_NUM_RE.match(cleaned):
        return False
    alpha_count = sum(ch.isalpha() for ch in cleaned)
    return alpha_count >= 10 and alpha_count / max(len(cleaned), 1) >= 0.45


def _find_ack_page_and_heading_y(
    pdf_document: PdfDocument,
) -> tuple[PdfPage, float] | None:
    """Return (page, heading_bottom_y) for the ACKNOWLEDGEMENTS page, or None."""
    for match in find_named_frontmatter_headings(pdf_document):
        if match.heading != _HEADING_LABEL:
            continue
        for page in pdf_document.pages:
            if page.page_number != match.page_number:
                continue
            for block in page.text_blocks:
                for line in block.lines:
                    if normalize_heading_text(line.text).upper() == _HEADING_LABEL:
                        return page, line.bbox.y1
    return None


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
    return sorted(lines, key=lambda line: (line.bbox.y0, line.bbox.x0))


def _group_paragraphs(lines: list[PdfTextLine]) -> list[list[PdfTextLine]]:
    if not lines:
        return []
    groups: list[list[PdfTextLine]] = [[lines[0]]]
    for line in lines[1:]:
        gap = line.bbox.y0 - groups[-1][-1].bbox.y1
        if gap <= MAX_PARA_GAP_PT:
            groups[-1].append(line)
        else:
            groups.append([line])
    return groups


def check_pdf_acknowledgements_indentation(
    pdf_document: PdfDocument,
) -> list[AuditFinding]:
    """Emit P043 warnings for Acknowledgements paragraph indentation violations."""
    result = _find_ack_page_and_heading_y(pdf_document)
    if result is None:
        return []

    page, heading_bottom_y = result
    lines = _lines_below_heading(page, heading_bottom_y)
    paragraphs = _group_paragraphs(lines)

    if len(paragraphs) < MIN_PARA_BLOCKS:
        return []

    left_margin = min(line.bbox.x0 for para in paragraphs for line in para)
    findings: list[AuditFinding] = []

    first_x0 = paragraphs[0][0].bbox.x0
    delta_first = first_x0 - left_margin
    if delta_first > INDENT_THRESHOLD_PT:
        findings.append(
            AuditFinding(
                rule_id="P043",
                severity=Severity.WARNING,
                page=page.page_number,
                message=(
                    "First Acknowledgements paragraph appears to be indented rather "
                    "than flush-left, as required by NJIT guidelines (Q044)."
                ),
                details={
                    "page_number": str(page.page_number),
                    "issue_type": "acknowledgements_first_paragraph_indented",
                    "paragraph_index": "0",
                    "observed_x0": f"{first_x0:.1f}",
                    "expected_left_margin": f"{left_margin:.1f}",
                    "indent_delta_points": f"{delta_first:.1f}",
                    "required_indent_points": "0.0",
                    "triage_tier": "medium",
                    "source_q_rule_id": "Q044",
                },
            )
        )

    for idx, para in enumerate(paragraphs[1:], 1):
        para_x0 = para[0].bbox.x0
        delta = para_x0 - left_margin
        if delta < INDENT_THRESHOLD_PT:
            findings.append(
                AuditFinding(
                    rule_id="P043",
                    severity=Severity.WARNING,
                    page=page.page_number,
                    message=(
                        "Acknowledgements paragraph after the first appears not to be "
                        "indented, as required by NJIT guidelines (Q045)."
                    ),
                    details={
                        "page_number": str(page.page_number),
                        "issue_type": "acknowledgements_subsequent_paragraph_not_indented",
                        "paragraph_index": str(idx),
                        "observed_x0": f"{para_x0:.1f}",
                        "expected_left_margin": f"{left_margin:.1f}",
                        "indent_delta_points": f"{delta:.1f}",
                        "required_indent_points": f"{INDENT_THRESHOLD_PT:.1f}",
                        "triage_tier": "medium",
                        "source_q_rule_id": "Q045",
                    },
                )
            )

    return findings
