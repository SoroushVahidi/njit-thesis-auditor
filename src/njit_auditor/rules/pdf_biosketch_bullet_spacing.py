"""Conservative Biographical Sketch bullet section single-spacing checks (P047).

Partial heuristic PDF coverage for Q026:
  - Q026: are the bullet items in the education section single-spaced within each bullet?

Biographical Sketch page only. Identifies likely bullet/list blocks (multi-line blocks
that do NOT have hanging-indent) and checks that internal line spacing is not excessively
large (not double-spaced). Does not read or quote bullet text, education content,
institution names, or biographical prose.

Does not duplicate P045 (hanging-indent publication blocks), P043 (Acknowledgements),
or P015 (general indentation).
"""

from __future__ import annotations

import re

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument, PdfPage, PdfTextLine
from njit_auditor.rules.pdf_frontmatter_heading_gate import find_gate_heading_page_and_y

HANGING_THRESHOLD_PT = 12.0
# Paragraph grouping is intentionally wider than P043/P044/P045 so related
# wrapped or double-spaced bullet lines remain in one candidate block.
MAX_PARA_GAP_PT = 20.0
# Bullet-entry spacing is intentionally tighter so distinct bullet/list entries
# are still split by the lower-level single-spacing check.
BULLET_MAX_GAP_PT = 12.0
MIN_TEXT_LEN = 20
MIN_BULLET_BLOCKS = 2
MIN_LINES_PER_BLOCK = 3
_HEADING_LABEL = "BIOGRAPHICAL SKETCH"
_PAGE_NUM_RE = re.compile(r"^\s*[\[(]?(?:\d+|[ivxlcdm]+)[\])]?[.]?\s*$", re.IGNORECASE)


def _is_usable_line(line: PdfTextLine) -> bool:
    cleaned = " ".join(line.text.strip().split())
    if len(cleaned) < MIN_TEXT_LEN:
        return False
    if _PAGE_NUM_RE.match(cleaned):
        return False
    alpha_count = sum(ch.isalpha() for ch in cleaned)
    return alpha_count >= 10 and alpha_count / max(len(cleaned), 1) >= 0.45


def _find_biosketch_page_and_heading_y(
    pdf_document: PdfDocument,
) -> tuple[PdfPage, float] | None:
    """Return (page, heading_bottom_y) for the BIOGRAPHICAL SKETCH page, or None."""
    return find_gate_heading_page_and_y(pdf_document, _HEADING_LABEL)


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


def _has_hanging_indent(block: list[PdfTextLine]) -> bool:
    """Return True if block has hanging-indent pattern (continuations more indented)."""
    if len(block) < 2:
        return False
    from statistics import median as _median
    first_x0 = block[0].bbox.x0
    rest_x0s = [line.bbox.x0 for line in block[1:]]
    rest_median = _median(rest_x0s)
    return (rest_median - first_x0) >= HANGING_THRESHOLD_PT


def check_pdf_biosketch_bullet_spacing(
    pdf_document: PdfDocument,
) -> list[AuditFinding]:
    """Emit P047 warnings for Bio Sketch bullet blocks with excessive internal line spacing."""
    result = _find_biosketch_page_and_heading_y(pdf_document)
    if result is None:
        return []

    page, heading_bottom_y = result
    lines = _lines_below_heading(page, heading_bottom_y)
    all_blocks = _group_paragraphs(lines)

    # Identify bullet/list-like blocks: multi-line, NOT hanging-indent
    bullet_blocks = [
        b for b in all_blocks
        if len(b) >= 2 and not _has_hanging_indent(b)
    ]

    if len(bullet_blocks) < MIN_BULLET_BLOCKS:
        return []

    findings: list[AuditFinding] = []

    for idx, block in enumerate(bullet_blocks):
        if len(block) < MIN_LINES_PER_BLOCK:
            continue
        for i in range(1, len(block) - 1):
            gap = block[i + 1].bbox.y0 - block[i].bbox.y1
            if gap > BULLET_MAX_GAP_PT:
                findings.append(
                    AuditFinding(
                        rule_id="P047",
                        severity=Severity.WARNING,
                        page=page.page_number,
                        message=(
                            "A bullet or list block on the Biographical Sketch page has an "
                            "unexpectedly large line gap, suggesting double-spacing within a "
                            "bullet item."
                        ),
                        details={
                            "page_number": str(page.page_number),
                            "issue_type": "biosketch_bullet_section_not_single_spaced",
                            "section_type": "biographical_sketch",
                            "block_index": str(idx),
                            "line_pair_index": str(i),
                            "observed_gap_points": f"{gap:.1f}",
                            "required_max_gap_points": f"{BULLET_MAX_GAP_PT:.1f}",
                            "triage_tier": "low",
                            "source_q_rule_id": "Q026",
                        },
                    )
                )
                break  # One finding per block.

    return findings
