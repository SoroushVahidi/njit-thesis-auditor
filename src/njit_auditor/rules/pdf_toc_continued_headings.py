"""Conservative continued-heading checks for multi-page TOC/List sections (P030).

Partial heuristic coverage for Q048, Q062, and Q071 on compiled PDFs only.
"""

from __future__ import annotations

import re
from collections import defaultdict

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument, PdfPage, PdfTextLine
from njit_auditor.rules.pdf_headings import normalize_heading_text
from njit_auditor.rules.pdf_toc_alignment import (
    TocPageContext,
    classify_toc_heading_line,
    detect_toc_like_pages,
    extract_toc_entry_lines,
)

HEADING_PREVIEW_MAX_LEN = 80
MIN_CONTINUATION_ENTRIES = 1

# A "(Continued)"/"Continued" marker printed on its own physical line,
# separate from the main heading line -- a real reviewed PDF (P030,
# Anthony p11 and Praneeth p12) was found to place "TABLE OF CONTENTS"
# and "(Continued)" in two different PyMuPDF text blocks even though they
# are the same logical heading (see
# docs/evaluation/ESTER_FEEDBACK_MIGRATION.md). classify_toc_heading_line
# only recognizes "(Continued)" as a same-line suffix (e.g. "TABLE OF
# CONTENTS (Continued)"), so a standalone marker line needs this separate
# check.
_BARE_CONTINUED_RE = re.compile(r"^\(?\s*continued\s*\)?[.:]?$", re.IGNORECASE)

EXPECTED_CONTINUED_HEADINGS = {
    "table_of_contents": "TABLE OF CONTENTS (Continued)",
    "list_of_tables": "LIST OF TABLES (Continued)",
    "list_of_figures": "LIST OF FIGURES (Continued)",
}


def _group_consecutive_pages(contexts: list[TocPageContext]) -> list[list[TocPageContext]]:
    if not contexts:
        return []

    sorted_contexts = sorted(contexts, key=lambda ctx: ctx.page.page_number)
    groups: list[list[TocPageContext]] = [[sorted_contexts[0]]]
    for context in sorted_contexts[1:]:
        previous = groups[-1][-1]
        if (
            context.page_type == previous.page_type
            and context.page.page_number == previous.page.page_number + 1
        ):
            groups[-1].append(context)
            continue
        groups.append([context])
    return groups


def _flatten_lines(page: PdfPage) -> list[PdfTextLine]:
    """Physical lines in reading order across every text block. Block
    boundaries are a PyMuPDF layout artifact, not a reliable signal of
    logical grouping -- the real regression this guards against split one
    logical heading ("TABLE OF CONTENTS" + "(Continued)") across two
    separate blocks with nothing between them but a normal line gap."""
    return [line for block in page.text_blocks for line in block.lines]


def _is_bare_continued_marker(line: PdfTextLine) -> bool:
    cleaned = " ".join(line.text.strip().split())
    return bool(_BARE_CONTINUED_RE.match(cleaned))


def _continued_heading_status(page: PdfPage, page_type: str) -> tuple[bool, str]:
    """Return whether *any* occurrence of the ``page_type`` heading on this
    page carries a continuation marker, and a preview of what was found.

    Does not stop at the first matching heading line found: the prior
    behavior returned as soon as it saw a bare "TABLE OF CONTENTS" line,
    even when a separate "(Continued)" line immediately followed it (a
    real reviewed false positive, not a hypothetical -- see module
    docstring). Checks the same-line suffix first (the common case), then
    falls back to a bare continuation marker on the very next physical
    line, before concluding this occurrence lacks "(Continued)" and
    moving on to check for another occurrence elsewhere on the page.
    """
    lines = _flatten_lines(page)
    fallback_preview = ""
    for index, line in enumerate(lines):
        normalized = normalize_heading_text(line.text)
        classified = classify_toc_heading_line(normalized)
        if classified is None:
            continue
        found_type, is_continued = classified
        if found_type != page_type:
            continue
        preview = normalize_heading_text(line.text)[:HEADING_PREVIEW_MAX_LEN]
        if not fallback_preview:
            fallback_preview = preview
        if is_continued:
            return True, preview
        if index + 1 < len(lines) and _is_bare_continued_marker(lines[index + 1]):
            next_text = " ".join(lines[index + 1].text.strip().split())
            return True, f"{preview} {next_text}"[:HEADING_PREVIEW_MAX_LEN]
    return False, fallback_preview


def check_pdf_toc_continued_headings(pdf_document: PdfDocument) -> list[AuditFinding]:
    """Emit P030 warnings when a continuation TOC/List page lacks a continued heading."""

    findings: list[AuditFinding] = []
    contexts = detect_toc_like_pages(pdf_document)
    by_type: dict[str, list[TocPageContext]] = defaultdict(list)
    for context in contexts:
        by_type[context.page_type].append(context)

    for page_type, type_contexts in by_type.items():
        for group in _group_consecutive_pages(type_contexts):
            if len(group) < 2:
                continue

            section_start_page = group[0].page.page_number
            for context in group[1:]:
                entries = extract_toc_entry_lines(context)
                if len(entries) < MIN_CONTINUATION_ENTRIES:
                    continue

                is_continued, observed_heading = _continued_heading_status(
                    context.page,
                    page_type,
                )
                if is_continued:
                    continue

                findings.append(
                    AuditFinding(
                        rule_id="P030",
                        severity=Severity.WARNING,
                        page=context.page.page_number,
                        message=(
                            "Multi-page TOC/List continuation page appears to be "
                            "missing a continued heading."
                        ),
                        details={
                            "page_number": str(context.page.page_number),
                            "section_type": page_type,
                            "issue_type": "missing_continued_heading",
                            "expected_heading": EXPECTED_CONTINUED_HEADINGS[page_type],
                            "observed_heading": observed_heading,
                            "section_start_page": str(section_start_page),
                            "continuation_index": str(
                                context.page.page_number - section_start_page + 1
                            ),
                            "confidence": "high",
                            "source_q_rule_ids": "Q048,Q062,Q071",
                        },
                    )
                )

    return findings
