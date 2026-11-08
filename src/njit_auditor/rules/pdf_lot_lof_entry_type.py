"""Conservative List of Tables / List of Figures cross-type entry checks (P055).

Heuristic PDF coverage for Q063/Q072:
  - Q063: LIST OF TABLES column header is "Table" — entries should be table entries.
  - Q072: LIST OF FIGURES column header is "Figure" — entries should be figure entries.

Emits an advisory when:
  - A List of Tables entry starts with "Figure" (lot_entry_is_figure) or
    is numeric-only (lot_entry_missing_table_prefix).
  - A List of Figures entry starts with "Table" (lof_entry_is_table) or
    is numeric-only (lof_entry_missing_figure_prefix).

TOC pages are excluded. Findings contain only structural metadata — no title text.
"""

from __future__ import annotations

import hashlib
import re

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import BBox, PdfDocument, format_bbox_detail
from njit_auditor.rules.pdf_toc_alignment import (
    RIGHT_COLUMN_MIN_X_OFFSET_PT,
    RIGHT_EDGE_TOLERANCE_PT,
    TocEntryLine,
    TocPageContext,
    detect_toc_like_pages,
    extract_toc_logical_entry_lines,
)

MIN_ENTRY_TEXT_LEN = 10

_FIGURE_PREFIX_RE = re.compile(
    r"^figure\s+([a-z][.\-]\d+(?:[.\-]\d+)*|[0-9ivxlcdm]+(?:[.\-][0-9ivxlcdm]+)*)",
    re.IGNORECASE,
)
_TABLE_PREFIX_RE = re.compile(
    r"^table\s+([a-z][.\-]\d+(?:[.\-]\d+)*|[0-9ivxlcdm]+(?:[.\-][0-9ivxlcdm]+)*)",
    re.IGNORECASE,
)
_NUMERIC_PREFIX_RE = re.compile(
    r"^(?:[a-z][.\-]\d+(?:[.\-]\d+)*(?=\s|[.):]|(?-i:[A-Z])|$)|"
    r"\d+(?:[.\-]\d+)*(?=\s|[.):]|(?-i:[A-Z])|$)|"
    r"[ivxlcdm]+(?:[.\-][0-9ivxlcdm]+)*(?=\s|[.):]|$))",
    re.IGNORECASE,
)


def _prefix_geometry(entry: TocEntryLine) -> tuple[str, BBox | None]:
    """Locate only the entry label/type prefix, without retaining title text."""
    match = next(
        (m for pattern in (_TABLE_PREFIX_RE, _FIGURE_PREFIX_RE, _NUMERIC_PREFIX_RE)
         if (m := pattern.match(entry.cleaned_text.strip())) is not None), None
    )
    if match is None:
        return "", None
    prefix = "".join(match.group().split())
    remaining = prefix.casefold()
    boxes: list[BBox] = []
    for span in entry.line.spans:
        positions = [i for i, char in enumerate(span.text) if not char.isspace()]
        if not positions:
            continue
        text = "".join(span.text[i] for i in positions).casefold()
        count = min(len(text), len(remaining))
        if text[:count] != remaining[:count]:
            return prefix, None
        if span.char_x_bounds is not None and len(span.char_x_bounds) == len(span.text):
            bounds = [span.char_x_bounds[i] for i in positions[:count]]
            boxes.append(BBox(x0=min(x[0] for x in bounds), y0=span.bbox.y0,
                              x1=max(x[1] for x in bounds), y1=span.bbox.y1))
        elif count == len(text):
            boxes.append(span.bbox)
        else:
            return prefix, None
        remaining = remaining[count:]
        if not remaining:
            return prefix, BBox(
                x0=min(b.x0 for b in boxes), y0=min(b.y0 for b in boxes),
                x1=max(b.x1 for b in boxes), y1=max(b.y1 for b in boxes),
            )
    return prefix, None


def _entry_evidence(context: TocPageContext, entry: TocEntryLine) -> dict[str, str]:
    prefix, prefix_box = _prefix_geometry(entry)
    # Geometry anchors survive changes to parser/report ordinals. No document
    # path, title or reviewer annotation participates in this identifier.
    anchor = prefix_box or entry.line.bbox
    key = f"{context.page.page_number}|{context.page_type}|{prefix}|{format_bbox_detail(anchor)}"
    details = {
        "entry_id": "list-entry-" + hashlib.sha256(key.encode()).hexdigest()[:20],
        "source_row_id": f"{context.page.page_number}:{anchor.y0:.1f}:{anchor.x0:.1f}",
        "bbox": format_bbox_detail(anchor),
        "prefix_geometry": "exact" if prefix_box is not None else "entry_span_fallback",
        "confidence": "medium",
        "confidence_reason": "prefix_or_folio_geometry_requires_review",
    }
    token = entry.page_number_token or ""
    number_line = entry.page_number_line
    if prefix_box is not None and token.isdecimal() and number_line is not None:
        spans = [s for s in number_line.spans if s.text.strip() == token]
        if len(spans) == 1:
            number = spans[0].bbox
            split_number = any(
                s is not spans[0] and s.text.strip().isdecimal()
                and 0 <= number.x0 - s.bbox.x1 <= RIGHT_EDGE_TOLERANCE_PT
                and min(number.y1, s.bbox.y1) > max(number.y0, s.bbox.y0)
                for s in number_line.spans
            )
            if (
                not split_number
                and number.y0 >= prefix_box.y0
                and number.x0 - prefix_box.x0 >= RIGHT_COLUMN_MIN_X_OFFSET_PT
                and entry.page_number_right_x is not None
                and abs(number.x1 - entry.page_number_right_x) <= RIGHT_EDGE_TOLERANCE_PT
            ):
                details.update(
                    confidence="high",
                    confidence_reason="exact_prefix_and_separate_numeric_folio",
                    page_number_bbox=format_bbox_detail(number),
                )
    return details


def _check_lot_entry_type_page(
    context: TocPageContext,
    entries: list[TocEntryLine],
    page_entry_offset: int,
) -> list[AuditFinding]:
    findings: list[AuditFinding] = []
    for idx, entry in enumerate(entries):
        if entry.page_number_token is None:
            continue
        text = entry.cleaned_text.strip()
        if len(text) < MIN_ENTRY_TEXT_LEN:
            continue

        if _FIGURE_PREFIX_RE.match(text):
            findings.append(
                AuditFinding(
                    rule_id="P055",
                    severity=Severity.WARNING,
                    page=context.page.page_number,
                    message=(
                        "List of Tables entry starts with 'Figure'. "
                        "NJIT guidelines require that the List of Tables "
                        "contain only table entries."
                    ),
                    details={
                        "issue_type": "lot_entry_is_figure",
                        "page": str(context.page.page_number),
                        "section_type": "list_of_tables",
                        "entry_index": str(page_entry_offset + idx),
                        "observed_entry_type": "figure",
                        "expected_entry_type": "table",
                        "page_number_token_present": "true",
                        "triage_tier": "medium",
                        "source_q_rule_id": "Q063",
                    },
                )
            )
        elif _NUMERIC_PREFIX_RE.match(text):
            findings.append(
                AuditFinding(
                    rule_id="P055",
                    severity=Severity.WARNING,
                    page=context.page.page_number,
                    message=(
                        "List of Tables entry is missing the required 'Table' prefix. "
                        "NJIT guidelines require that each entry in the List of Tables "
                        "begin with the word 'Table'."
                    ),
                    details={
                        "issue_type": "lot_entry_missing_table_prefix",
                        "page": str(context.page.page_number),
                        "section_type": "list_of_tables",
                        "entry_index": str(page_entry_offset + idx),
                        "observed_entry_type": "numeric_only",
                        "expected_entry_type": "table",
                        "page_number_token_present": "true",
                        "triage_tier": "medium",
                        "source_q_rule_id": "Q063",
                    },
                )
            )
    return findings


def _check_lof_entry_type_page(
    context: TocPageContext,
    entries: list[TocEntryLine],
    page_entry_offset: int,
) -> list[AuditFinding]:
    findings: list[AuditFinding] = []
    for idx, entry in enumerate(entries):
        if entry.page_number_token is None:
            continue
        text = entry.cleaned_text.strip()
        if len(text) < MIN_ENTRY_TEXT_LEN:
            continue

        if _TABLE_PREFIX_RE.match(text):
            findings.append(
                AuditFinding(
                    rule_id="P055",
                    severity=Severity.WARNING,
                    page=context.page.page_number,
                    message=(
                        "List of Figures entry starts with 'Table'. "
                        "NJIT guidelines require that the List of Figures "
                        "contain only figure entries."
                    ),
                    details={
                        "issue_type": "lof_entry_is_table",
                        "page": str(context.page.page_number),
                        "section_type": "list_of_figures",
                        "entry_index": str(page_entry_offset + idx),
                        "observed_entry_type": "table",
                        "expected_entry_type": "figure",
                        "page_number_token_present": "true",
                        "triage_tier": "medium",
                        "source_q_rule_id": "Q072",
                    },
                )
            )
        elif _NUMERIC_PREFIX_RE.match(text):
            findings.append(
                AuditFinding(
                    rule_id="P055",
                    severity=Severity.WARNING,
                    page=context.page.page_number,
                    message=(
                        "List of Figures entry is missing the required 'Figure' prefix. "
                        "NJIT guidelines require that each entry in the List of Figures "
                        "begin with the word 'Figure'."
                    ),
                    details={
                        "issue_type": "lof_entry_missing_figure_prefix",
                        "page": str(context.page.page_number),
                        "section_type": "list_of_figures",
                        "entry_index": str(page_entry_offset + idx),
                        "observed_entry_type": "numeric_only",
                        "expected_entry_type": "figure",
                        "page_number_token_present": "true",
                        "triage_tier": "medium",
                        "source_q_rule_id": "Q072",
                    },
                )
            )
    return findings


def check_pdf_lot_lof_entry_type(pdf_document: PdfDocument) -> list[AuditFinding]:
    """Emit P055 warnings for cross-type or missing prefix LoT/LoF entries."""
    findings: list[AuditFinding] = []
    entry_offset = 0
    for context in detect_toc_like_pages(pdf_document):
        if context.page_type == "list_of_tables":
            entries = extract_toc_logical_entry_lines(context, require_right_edge=True)
            page_findings = _check_lot_entry_type_page(context, entries, entry_offset)
        elif context.page_type == "list_of_figures":
            entries = extract_toc_logical_entry_lines(context, require_right_edge=True)
            page_findings = _check_lof_entry_type_page(context, entries, entry_offset)
        else:
            continue
        for finding in page_findings:
            entry = entries[int(finding.details["entry_index"]) - entry_offset]
            finding.details.update(_entry_evidence(context, entry))
        findings.extend(page_findings)
        entry_offset += len(entries)
    return findings
