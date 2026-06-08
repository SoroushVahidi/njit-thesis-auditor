"""Conservative Biographical Sketch publication paragraph layout checks (P045).

Partial heuristic PDF coverage for Q028 and Q029:
  - Q029: do publication entries use hanging indent (first line flush, continuations indented)?
  - Q028: are publication entries separated by a blank line (adequate inter-entry gap)?

Q026 (within-entry single spacing) is deferred to v2 — reliable detection requires a grouping
approach that distinguishes intra-entry gaps from inter-entry gaps, which is not feasible with
the single vertical-gap threshold used in v1.

Biographical Sketch page only. Does not read or quote publication text, author names,
citation content, or biographical prose. Does not duplicate P015 (general indentation),
P043 (Acknowledgements), or P044 (Abstract).
"""

from __future__ import annotations

import re
from statistics import median as _median

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument, PdfPage, PdfTextLine
from njit_auditor.rules.pdf_frontmatter_heading_gate import find_gate_heading_page_and_y

HANGING_THRESHOLD_PT = 12.0
MAX_PARA_GAP_PT = 14.0
ENTRY_GAP_THRESHOLD_PT = 20.0
MIN_TEXT_LEN = 20
MIN_PARA_BLOCKS = 2
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
    """Return True if block exhibits hanging-indent pattern (continuations more indented)."""
    if len(block) < 2:
        return False
    first_x0 = block[0].bbox.x0
    rest_x0s = [line.bbox.x0 for line in block[1:]]
    rest_median = _median(rest_x0s)
    return (rest_median - first_x0) >= HANGING_THRESHOLD_PT


def check_pdf_biosketch_publication_layout(
    pdf_document: PdfDocument,
) -> list[AuditFinding]:
    """Emit P045 warnings for Bio Sketch publication layout violations."""
    result = _find_biosketch_page_and_heading_y(pdf_document)
    if result is None:
        return []

    page, heading_bottom_y = result
    lines = _lines_below_heading(page, heading_bottom_y)
    all_blocks = _group_paragraphs(lines)

    multi_line_blocks = [b for b in all_blocks if len(b) >= 2]
    if len(multi_line_blocks) < MIN_PARA_BLOCKS:
        return []

    hanging_blocks = [b for b in multi_line_blocks if _has_hanging_indent(b)]
    findings: list[AuditFinding] = []

    # Q029: no hanging indent detected across any multi-line block
    if not hanging_blocks:
        findings.append(
            AuditFinding(
                rule_id="P045",
                severity=Severity.WARNING,
                page=page.page_number,
                message=(
                    "Biographical Sketch page has no publication entries with hanging indent. "
                    "NJIT guidelines (Q029) require publication/presentation entries to use "
                    "hanging indentation."
                ),
                details={
                    "page_number": str(page.page_number),
                    "issue_type": "biosketch_publication_missing_hanging_indent",
                    "multi_line_block_count": str(len(multi_line_blocks)),
                    "hanging_indent_threshold_points": f"{HANGING_THRESHOLD_PT:.1f}",
                    "triage_tier": "medium",
                    "source_q_rule_id": "Q029",
                },
            )
        )
        return findings

    # Q028: inter-entry spacing between consecutive hanging-indent blocks
    for idx in range(len(hanging_blocks) - 1):
        block_a = hanging_blocks[idx]
        block_b = hanging_blocks[idx + 1]
        gap = block_b[0].bbox.y0 - block_a[-1].bbox.y1
        if gap < ENTRY_GAP_THRESHOLD_PT:
            findings.append(
                AuditFinding(
                    rule_id="P045",
                    severity=Severity.WARNING,
                    page=page.page_number,
                    message=(
                        "Consecutive publication entries on the Biographical Sketch page "
                        "appear to lack the required blank line between them (Q028)."
                    ),
                    details={
                        "page_number": str(page.page_number),
                        "issue_type": "biosketch_publication_entry_spacing_not_double",
                        "entry_index": str(idx),
                        "observed_gap_points": f"{gap:.1f}",
                        "required_gap_points": f"{ENTRY_GAP_THRESHOLD_PT:.1f}",
                        "triage_tier": "medium",
                        "source_q_rule_id": "Q028",
                    },
                )
            )
            break  # One finding per page for this issue type.

    return findings
