"""Conservative inter-entry spacing checks for TOC/List pages (P036).

Partial heuristic PDF coverage for Q057, Q067, and Q077.
"""

from __future__ import annotations

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument, PdfTextLine, format_bbox_detail
from njit_auditor.rules.pdf_toc_alignment import _clean_text, detect_toc_like_pages
from njit_auditor.rules.pdf_toc_list_wrapped_spacing import (
    _collect_entry_region_lines,
    _estimate_line_height,
    _has_intervening_page_number_line,
    _is_wrap_continuation_pair,
    _looks_like_new_entry_start,
)
from njit_auditor.toc_list_student_preview import (
    gap_bbox_between_boxes,
    sanitize_toc_list_entry_preview,
)

MIN_INTER_ENTRY_GAP_RATIO = 1.4
FALLBACK_LINE_HEIGHT_PT = 12.0

ISSUE_TYPE_BY_SECTION = {
    "table_of_contents": "toc_inter_entry_spacing_too_tight",
    "list_of_tables": "lot_inter_entry_spacing_too_tight",
    "list_of_figures": "lof_inter_entry_spacing_too_tight",
}

SOURCE_Q_RULE_IDS_BY_SECTION = {
    "table_of_contents": "Q057",
    "list_of_tables": "Q067",
    "list_of_figures": "Q077",
}


def _is_entry_boundary(
    previous: PdfTextLine,
    line: PdfTextLine,
    page_type: str,
) -> bool:
    """Return True when *line* begins a new logical TOC/List entry.

    ``_is_wrap_continuation_pair`` is tuned for P032's conservative "only
    check a gap when we are SURE these two lines are the same wrapped
    entry" purpose -- a False return there is a safe default to skip
    checking, not proof the two lines belong to different entries. Treating
    that negation directly as an entry boundary over-splits any entry whose
    wrapped continuation uses a hanging indent (continuation lines indented
    under the entry text rather than under its leading number), which is
    common in this corpus and shifts x0 by more than
    ``INDENT_CLUSTER_TOLERANCE_PT``. That over-split then makes each
    entry's own internal single-line-height wrap gap look like an
    unusually tight gap BETWEEN two entries. Require positive evidence of a
    new entry start instead (numbered "N.N"/Chapter/Appendix line, or a
    dot-leader entry line) so only genuinely separate entries are split.
    """
    if _is_wrap_continuation_pair(previous, line, page_type):
        return False
    return _looks_like_new_entry_start(_clean_text(line.text))


def _group_lines_into_entries(
    lines: list[PdfTextLine],
    page_type: str,
) -> list[list[PdfTextLine]]:
    if not lines:
        return []

    entries: list[list[PdfTextLine]] = [[lines[0]]]
    for line in lines[1:]:
        previous = entries[-1][-1]
        if _is_entry_boundary(previous, line, page_type):
            entries.append([line])
            continue
        entries[-1].append(line)
    return entries


def _triage_tier(gap_ratio: float) -> str:
    if gap_ratio < 1.1:
        return "high"
    if gap_ratio < MIN_INTER_ENTRY_GAP_RATIO:
        return "medium"
    return "low"


def check_pdf_toc_list_entry_spacing(pdf_document: PdfDocument) -> list[AuditFinding]:
    """Emit P036 warnings when consecutive TOC/List entries appear too tightly spaced."""

    findings: list[AuditFinding] = []

    for context in detect_toc_like_pages(pdf_document):
        lines = _collect_entry_region_lines(context)
        entries = _group_lines_into_entries(lines, context.page_type)
        if len(entries) < 2:
            continue

        issue_type = ISSUE_TYPE_BY_SECTION.get(context.page_type)
        if issue_type is None:
            continue

        for pair_index, (previous_entry, next_entry) in enumerate(zip(entries, entries[1:])):
            last_line = previous_entry[-1]
            first_line = next_entry[0]
            if _has_intervening_page_number_line(context, last_line, first_line):
                continue

            gap_pt = first_line.bbox.y0 - last_line.bbox.y1
            if gap_pt <= 0:
                continue

            line_height = _estimate_line_height(last_line, first_line)
            if line_height <= 0:
                line_height = FALLBACK_LINE_HEIGHT_PT

            gap_ratio = gap_pt / line_height
            if gap_ratio >= MIN_INTER_ENTRY_GAP_RATIO:
                continue

            required_gap_pt = line_height * MIN_INTER_ENTRY_GAP_RATIO
            triage_tier = _triage_tier(gap_ratio)

            previous_preview = sanitize_toc_list_entry_preview(last_line.text)
            next_preview = sanitize_toc_list_entry_preview(first_line.text)
            gap_bbox = gap_bbox_between_boxes(last_line.bbox, first_line.bbox)
            details: dict[str, str] = {
                "page_number": str(context.page.page_number),
                "section_type": context.page_type,
                "issue_type": issue_type,
                "entry_pair_index": str(pair_index),
                "gap_points": f"{gap_pt:.1f}",
                "required_gap_points": f"{required_gap_pt:.1f}",
                "local_line_height_points": f"{line_height:.1f}",
                "gap_ratio": f"{gap_ratio:.2f}",
                "triage_tier": triage_tier,
                "source_q_rule_ids": SOURCE_Q_RULE_IDS_BY_SECTION[context.page_type],
            }
            if previous_preview:
                details["previous_entry_preview"] = previous_preview
            if next_preview:
                details["next_entry_preview"] = next_preview
            if gap_bbox is not None:
                details["bbox"] = format_bbox_detail(gap_bbox)

            findings.append(
                AuditFinding(
                    rule_id="P036",
                    severity=Severity.WARNING,
                    page=context.page.page_number,
                    message=(
                        "Consecutive TOC/List entries appear to have insufficient "
                        "inter-entry vertical spacing."
                    ),
                    details=details,
                )
            )

    return findings
