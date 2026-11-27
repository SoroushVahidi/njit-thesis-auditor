"""Conservative TOC cross-page section-number ordering check (P062).

Heuristic PDF coverage for Q056/Q057 (cross-page extension):
  - Q056: level-2/3 entries indented to show hierarchy implies sequential
    section numbering across all TOC pages
  - Q057: double spacing between consecutive section-title entries implies
    all entries are ordered across the full TOC section

Emits a WARNING when the TABLE OF CONTENTS spans multiple consecutive pages
and the combined section-number sequence across those pages is not in
non-decreasing order.

Companion to P060 (within-page TOC ordering) and P061 (cross-page LoT/LoF).
Conservative gates:
  - At least 2 consecutive TABLE OF CONTENTS pages with comparable entries
  - At least 3 total comparable entries across all pages of the section
  - At least 2 inversions in the combined sequence before flagging
  - Word-prefix entries (CHAPTER, APPENDIX, ABSTRACT, etc.) skipped
  - Entries without page_number_token (wrapped continuation lines) skipped
  - LoT and LoF pages excluded; TABLE OF CONTENTS only

Findings contain only structural metadata — no entry text, chapter/section
titles, or dissertation content.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument, PdfPage, format_bbox_detail, text_space_size
from njit_auditor.rules.pdf_page_numbers import (
    detect_page_number_candidates,
    is_plausible_page_number_candidate,
)
from njit_auditor.rules.pdf_toc_alignment import (
    TocEntryLine,
    TocPageContext,
    detect_toc_like_pages,
    extract_toc_entry_lines,
)
from njit_auditor.rules.pdf_toc_entry_number_ordering import (
    MIN_COMPARABLE_ENTRIES,
    MIN_ENTRY_TEXT_LEN,
    MIN_INVERSIONS_TO_FLAG,
    _parse_section_num,
)
from njit_auditor.toc_order_evidence import describe_p062_pair

_SOURCE_Q_RULE_ID = "Q056"
_FOLIO = re.compile(r"(?:[0-9]{1,4}|[ivxlcdm]{1,12})", re.IGNORECASE)


@dataclass(frozen=True)
class _ComparableEntry:
    number: tuple[int, ...]
    page: PdfPage
    entry: TocEntryLine
    index: int


def _source_number_span_box(row: _ComparableEntry) -> str:
    """Use a measured entry-start span only when it has a unique source line."""
    span = next((span for span in row.entry.line.spans if span.text.strip()), None)
    if span is None or _parse_section_num(span.text) != row.number:
        return ""
    origins = [
        line for block in row.page.text_blocks for line in block.lines if span in line.spans
    ]
    if len(origins) != 1:
        return ""
    origin = origins[0]
    if origin.wmode not in (None, 0) or (
        origin.line_dir is not None
        and (abs(origin.line_dir[0] - 1) > 0.01 or abs(origin.line_dir[1]) > 0.01)
    ):
        return ""
    box = span.bbox
    width, height = text_space_size(row.page)
    if not (0 <= box.x0 < box.x1 <= width and 0 <= box.y0 < box.y1 <= height):
        return ""
    return format_bbox_detail(box)


def _pair_details(before: _ComparableEntry, after: _ComparableEntry) -> dict[str, str]:
    pages = {row.page.page_number: row.page for row in (before, after)}
    printed: dict[int, list[str]] = {}
    pair_document = PdfDocument(path="", pages=list(pages.values()))
    for candidate in detect_page_number_candidates(pair_document):
        if candidate.position_type == "bottom_center" and is_plausible_page_number_candidate(
            candidate
        ) and _FOLIO.fullmatch(candidate.text):
            printed.setdefault(candidate.page_number, []).append(candidate.text)

    details: dict[str, str] = {}
    primary_boxes: list[str] = []
    for role, row in (("preceding", before), ("following", after)):
        page = row.page.page_number
        prefix = f"{role}_entry"
        details[f"{prefix}_number"] = row.entry.cleaned_text.strip().split(maxsplit=1)[0]
        details[f"{prefix}_page"] = str(page)
        details[f"{prefix}_index"] = str(row.index)
        footer = printed.get(page, [])
        if len(footer) == 1:
            details[f"{prefix}_toc_folio"] = footer[0]
        destination = row.entry.page_number_token
        if destination and _FOLIO.fullmatch(destination):
            details[f"{prefix}_destination_folio"] = destination
        if box := _source_number_span_box(row):
            details[f"{prefix}_bbox"] = box
            if page == after.page.page_number:
                primary_boxes.append(box)
    if primary_boxes:
        details["highlight_bboxes"] = " | ".join(primary_boxes)
    return details


def _collect_comparable_entries(
    contexts: list[TocPageContext],
) -> list[_ComparableEntry]:
    """Collect all parseable section numbers from a run of TOC pages in order."""
    comparable: list[_ComparableEntry] = []
    for context in contexts:
        for index, entry in enumerate(extract_toc_entry_lines(context)):
            if entry.page_number_token is None:
                continue
            if len(entry.cleaned_text.strip()) < MIN_ENTRY_TEXT_LEN:
                continue
            num = _parse_section_num(entry.cleaned_text)
            if num is None:
                continue
            comparable.append(_ComparableEntry(num, context.page, entry, index))
    return comparable


def _group_consecutive_toc_runs(
    contexts: list[TocPageContext],
) -> list[list[TocPageContext]]:
    """Group consecutive TABLE OF CONTENTS pages into runs."""
    toc_pages = sorted(
        (ctx for ctx in contexts if ctx.page_type == "table_of_contents"),
        key=lambda ctx: ctx.page.page_number,
    )
    runs: list[list[TocPageContext]] = []
    current: list[TocPageContext] = []
    for ctx in toc_pages:
        page_number = ctx.page.page_number
        if not current or page_number == current[-1].page.page_number + 1:
            current.append(ctx)
        else:
            if current:
                runs.append(current)
            current = [ctx]
    if current:
        runs.append(current)
    return runs


def _check_cross_page_toc_run(
    run: list[TocPageContext],
) -> list[AuditFinding]:
    """Check ordering across a multi-page TOC run; return findings."""
    if len(run) < 2:
        return []

    comparable = _collect_comparable_entries(run)

    if len(comparable) < MIN_COMPARABLE_ENTRIES:
        return []

    inversion_indices = [
        i for i in range(len(comparable) - 1) if comparable[i].number > comparable[i + 1].number
    ]
    if len(inversion_indices) < MIN_INVERSIONS_TO_FLAG:
        return []

    representative = next(
        (i for i in inversion_indices
         if comparable[i].page.page_number != comparable[i + 1].page.page_number),
        inversion_indices[0],
    )
    preceding, following = comparable[representative:representative + 2]
    page = following.page.page_number
    evidence = _pair_details(preceding, following)
    return [
        AuditFinding(
            rule_id="P062",
            severity=Severity.WARNING,
            page=page,
            message=(
                f"{describe_p062_pair(evidence)} The Table of Contents has "
                f"{len(inversion_indices)} decreases among {len(comparable)} comparable "
                f"section entries across {len(run)} consecutive pages."
            ),
            details={
                # The static registry reads detector issue IDs without importing them.
                "issue_type": "toc_cross_page_entry_numbers_not_nondecreasing",
                "page": str(page),
                "section_type": "table_of_contents",
                "page_count": str(len(run)),
                "entry_count": str(len(comparable)),
                "comparable_entry_number_count": str(len(comparable)),
                "inversion_count": str(len(inversion_indices)),
                "first_inversion_index": str(inversion_indices[0]),
                "representative_inversion_index": str(representative),
                "suggested_fix": (
                    f"Check sections {evidence['preceding_entry_number']} and "
                    f"{evidence['following_entry_number']} against manuscript headings. "
                    "Fix the numbering or order, then regenerate the TOC."
                ),
                "triage_tier": "medium",
                "source_q_rule_id": _SOURCE_Q_RULE_ID,
                **evidence,
            },
        )
    ]


def check_pdf_toc_cross_page_entry_ordering(
    pdf_document: PdfDocument,
) -> list[AuditFinding]:
    """Emit P062 warnings for cross-page TOC section-number ordering violations."""
    findings: list[AuditFinding] = []
    contexts = detect_toc_like_pages(pdf_document)
    for run in _group_consecutive_toc_runs(contexts):
        findings.extend(_check_cross_page_toc_run(run))
    return findings
