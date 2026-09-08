"""Conservative inter-entry spacing checks for TOC/List pages (P036).

Partial heuristic PDF coverage for Q057, Q067, and Q077.
"""

from __future__ import annotations

import re

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument, PdfTextLine, format_bbox_detail
from njit_auditor.rules.pdf_toc_alignment import _clean_text, detect_toc_like_pages
from njit_auditor.rules.pdf_toc_list_wrapped_spacing import (
    _collect_entry_region_lines,
    _estimate_line_height,
    _has_intervening_page_number_line,
    _is_wrap_continuation_pair,
    _looks_like_new_entry_start_given_previous,
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
    return _looks_like_new_entry_start_given_previous(previous, _clean_text(line.text))


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


def _classify_entry_level(text: str, page_type: str) -> str:
    """Classify the hierarchical level/kind of a TOC/List entry line."""
    cleaned = _clean_text(text)
    if page_type == "list_of_tables":
        return "table_entry"
    if page_type == "list_of_figures":
        return "figure_entry"

    normalized = cleaned.upper()
    if normalized.startswith("CHAPTER") or normalized.startswith("APPENDIX"):
        return "toc_level_1"
    if re.match(r"^[0-9]+\.[0-9]+\.[0-9]+", cleaned):
        return "toc_level_3"
    if re.match(r"^[0-9]+\.[0-9]+", cleaned):
        return "toc_level_2"
    if re.match(r"^[0-9]+\s", cleaned):
        return "toc_level_1"
    if re.match(r"^[IVXLCDM]+\s", cleaned):
        return "toc_level_1"

    words = [w for w in re.split(r"[.\s\d]+", normalized) if w]
    if words:
        first_word = words[0]
        if first_word in ("REFERENCES", "BIBLIOGRAPHY", "VITA", "GLOSSARY", "INDEX"):
            return "toc_level_1"

    return "unknown"


_TOC_LEVEL_DEPTH = {"toc_level_1": 1, "toc_level_2": 2, "toc_level_3": 3}


def _is_exempt_structural_transition(prev_level: str, next_level: str) -> bool:
    """Return True for a transition exempt from tight-spacing detection
    because it borders a structural row (a chapter/appendix/top-level
    heading), not an ordinary peer-to-peer entry gap.

    Two exempt shapes, both confirmed against real Ester-reviewed cases
    (see docs/evaluation/ESTER_FEEDBACK_MIGRATION.md, P036/Anthony p12 and
    the R036 email/sheet policy: "the relevant spacing transitions
    involve structural rows such as chapter or appendix headings, and the
    auditor should allow appropriate flexibility rather than treating
    them like ordinary peer entries"):

    1. *prev* is a heading (or any entry) immediately followed by its own
       first, more deeply nested child entry (``prev_depth < next_depth``)
       -- a parent-to-first-child transition.
    2. *next* is itself a top-level structural row (``toc_level_1`` --
       CHAPTER/APPENDIX/REFERENCES/etc., see ``_classify_entry_level``)
       and *prev* is at a strictly deeper level -- finishing a nested
       subsection and entering a new top-level section (e.g. "3.5
       Conclusion" -> "APPENDIX", the reviewed Anthony p12 case: a
       level-2 entry finishing right before an APPENDIX heading). A
       top-level-to-top-level peer pair (e.g. "Chapter 3" -> "Chapter 4")
       is deliberately NOT covered by this shape -- ``prev_level`` must
       differ from ``toc_level_1``, or two chapter headings back-to-back
       would wrongly become exempt as "ordinary peer entries", which is
       exactly what Ester's policy says should stay checked.

    A same-depth peer pair (e.g. "1.1" -> "1.2") or a pair that merely
    finishes a nested subsection and returns to an ordinary (non-level-1)
    peer (e.g. "1.2.3" -> "1.3") is deliberately NOT exempted by shape 2 --
    only entering a genuine top-level structural row is. Broadening this
    further without further reviewed evidence would risk silently
    suppressing genuine spacing defects across the corpus. Pairs
    involving an unclassifiable ("unknown") entry are never exempt.
    """
    if next_level == "toc_level_1" and prev_level != "toc_level_1":
        return True
    prev_depth = _TOC_LEVEL_DEPTH.get(prev_level)
    next_depth = _TOC_LEVEL_DEPTH.get(next_level)
    if prev_depth is None or next_depth is None:
        return False
    return prev_depth < next_depth


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

            prev_level = _classify_entry_level(previous_entry[0].text, context.page_type)
            next_level = _classify_entry_level(next_entry[0].text, context.page_type)
            if _is_exempt_structural_transition(prev_level, next_level):
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
