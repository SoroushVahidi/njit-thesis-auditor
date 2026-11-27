"""Conservative continued-heading checks for multi-page TOC/List sections (P030).

Partial heuristic coverage for Q048, Q062, and Q071 on compiled PDFs only.
List of Symbols continuation is supported by the separate F04 reviewer case.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from statistics import median

from njit_auditor.digital_commons_wrapper import page_identity
from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import BBox, PdfDocument, PdfPage, PdfTextLine, format_bbox_detail
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

_COLLAPSED_HEADINGS = {
    "TABLEOFCONTENTS": "table_of_contents",
    "LISTOFTABLES": "list_of_tables",
    "LISTOFFIGURES": "list_of_figures",
}

_SYMBOLS_HEADING = re.compile(r"LISTOFSYMBOLS(?P<continued>\(CONTINUED\)|CONTINUED)?[.:]?")
_FOLIO = re.compile(r"[ivxlcdm]+|[0-9]+", re.IGNORECASE)
_SYMBOLS_COLUMN_TOLERANCE_PT = 5.0
_MIN_SYMBOL_ROWS = 3


def _classify_heading(line_text: str) -> tuple[str, bool] | None:
    classified = classify_toc_heading_line(normalize_heading_text(line_text))
    if classified is not None:
        return classified
    # Some PDF producers omit every inter-word space in the heading text layer,
    # even though the rendered heading is plainly spaced. Match only an entire
    # known heading so body text cannot become a continuation heading.
    compact = re.sub(r"\s+", "", line_text).upper()
    for heading, page_type in _COLLAPSED_HEADINGS.items():
        if compact == heading:
            return page_type, False
        if compact in (f"{heading}(CONTINUED)", f"{heading}CONTINUED"):
            return page_type, True
    return None


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
        classified = _classify_heading(line.text)
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


@dataclass(frozen=True)
class _SymbolsRows:
    symbol_x: float
    definition_x: float
    definition_height: float
    first_row: BBox
    last_row_bottom: float


def _symbols_lines(page: PdfPage) -> list[PdfTextLine]:
    if page.text_extraction_unavailable or page.page_rotation or page.is_visually_landscape:
        return []
    lines = [
        line
        for line in _flatten_lines(page)
        if line.text.strip()
        and not (line.bbox.y0 >= 0.92 * page.height and _FOLIO.fullmatch(line.text.strip()))
    ]
    if any(
        not (0 <= line.bbox.x0 < line.bbox.x1 <= page.width
             and 0 <= line.bbox.y0 < line.bbox.y1 <= page.height)
        for line in lines
    ):
        return []
    return sorted(lines, key=lambda line: (line.bbox.y0, line.bbox.x0))


def _looks_like_symbol(line: PdfTextLine, width: float) -> bool:
    text = line.text.strip()
    return (
        line.bbox.width <= 0.15 * width
        and len("".join(text.split())) <= 10
        and len(text.split()) <= 3
        and not re.search(r"[^\W\d_]{5}", text)
        and not text.isdecimal()
    )


def _matches_column(line: PdfTextLine, x: float) -> bool:
    return abs(line.bbox.x0 - x) <= _SYMBOLS_COLUMN_TOLERANCE_PT


def _symbol_definition_pairs(
    lines: list[PdfTextLine], width: float, expected: _SymbolsRows | None,
) -> list[tuple[PdfTextLine, PdfTextLine]]:
    symbols = [line for line in lines if _looks_like_symbol(line, width)]
    definitions = [line for line in lines if sum(char.isalpha() for char in line.text) >= 4]
    if expected is not None:
        symbols = [line for line in symbols if _matches_column(line, expected.symbol_x)]
        definitions = [line for line in definitions if _matches_column(line, expected.definition_x)]
    pairs = []
    owners: dict[int, int] = defaultdict(int)
    for symbol in symbols:
        left = symbol.bbox
        matches = [
            line for line in definitions
            if line.bbox.x0 - left.x1 >= 0.07 * width
            and min(left.y1, line.bbox.y1) - max(left.y0, line.bbox.y0)
            >= 0.6 * min(left.height, line.bbox.height)
        ]
        if len(matches) == 1:
            definition = matches[0]
            pairs.append((symbol, definition))
            owners[id(definition)] += 1
    return [(symbol, definition) for symbol, definition in pairs if owners[id(definition)] == 1]


def _symbols_rows(
    lines: list[PdfTextLine], width: float, expected: _SymbolsRows | None = None,
) -> _SymbolsRows | None:
    pairs = _symbol_definition_pairs(lines, width, expected)
    if len(pairs) < _MIN_SYMBOL_ROWS:
        return None
    if expected is None:
        # Only learn left and right column positions on a page headed List of Symbols.
        # Reject layouts without one clearly dominant pairing of columns.
        symbol_x = median(symbol.bbox.x0 for symbol, _ in pairs)
        definition_x = median(definition.bbox.x0 for _, definition in pairs)
    else:
        symbol_x, definition_x = expected.symbol_x, expected.definition_x
    aligned = [
        (symbol, definition)
        for symbol, definition in pairs
        if _matches_column(symbol, symbol_x) and _matches_column(definition, definition_x)
    ]
    if len(aligned) < _MIN_SYMBOL_ROWS or len(aligned) * 2 <= len(pairs):
        return None
    definition_height = median(definition.bbox.height for _, definition in aligned)
    if expected is not None:
        if not 0.8 <= definition_height / expected.definition_height <= 1.2:
            return None
        # Keep the anchored type size across the section so small changes on
        # several pages cannot accumulate into a different layout.
        definition_height = expected.definition_height
    symbol, definition = aligned[0]
    return _SymbolsRows(
        symbol_x,
        definition_x,
        definition_height,
        BBox(
            x0=symbol.bbox.x0,
            y0=min(symbol.bbox.y0, definition.bbox.y0),
            x1=definition.bbox.x1,
            y1=max(symbol.bbox.y1, definition.bbox.y1),
        ),
        max(max(left.bbox.y1, right.bbox.y1) for left, right in aligned),
    )


def _headerless_symbols_body(
    lines: list[PdfTextLine], page: PdfPage, previous: _SymbolsRows,
) -> _SymbolsRows | None:
    # Require an apparently full preceding page and a current page that
    # starts directly with the same two-column pattern. A new heading,
    # prose, or competing columns end ownership even if some rows match.
    if previous.last_row_bottom < 0.8 * page.height:
        return None
    if lines and _is_bare_continued_marker(lines[0]):
        lines = lines[1:]
    rows = _symbols_rows(lines, page.width, previous)
    if (
        rows is None
        or lines[0].bbox.y0 < rows.first_row.y0
        or rows.first_row.y0 > 0.25 * page.height
    ):
        return None
    if not all(
        _matches_column(line, rows.definition_x)
        or (_matches_column(line, rows.symbol_x) and _looks_like_symbol(line, page.width))
        for line in lines
    ):
        return None
    return rows


def _adjacent_symbols_pages(previous: PdfPage, page: PdfPage) -> bool:
    prior, current = page_identity(previous), page_identity(page)
    return (
        page.page_number == previous.page_number + 1
        and current.original_page_number == prior.original_page_number + 1
        and current.manuscript_page_number == prior.manuscript_page_number + 1
        and abs(page.width - previous.width) <= 1
        and abs(page.height - previous.height) <= 1
    )


def _check_symbols_continued_headings(
    pages: list[PdfPage], other_list_pages: set[int],
) -> list[AuditFinding]:
    findings: list[AuditFinding] = []
    previous: tuple[PdfPage, int, _SymbolsRows] | None = None
    for page in sorted(pages, key=lambda current: current.page_number):
        lines = _symbols_lines(page) if page.page_number not in other_list_pages else []
        if not lines:
            previous = None
            continue
        if previous is not None and not _adjacent_symbols_pages(previous[0], page):
            previous = None
        first = lines[0]
        heading = (
            _SYMBOLS_HEADING.fullmatch("".join(first.text.upper().split()))
            if first.bbox.y0 <= 0.2 * page.height
            else None
        )
        continued = False
        if heading is not None:
            body = lines[1:]
            continued = bool(heading.group("continued"))
            if body and _is_bare_continued_marker(body[0]):
                marker = body[0].bbox
                if (
                    -2 <= marker.y0 - first.bbox.y1 <= 1.5 * first.bbox.height
                    and marker.x0 < first.bbox.x1
                    and first.bbox.x0 < marker.x1
                ):
                    continued = True
                    body = body[1:]
            rows = _symbols_rows(body, page.width, previous[2] if previous else None)
            if rows is None and previous is not None:
                # An explicit heading can start a new list with different columns.
                previous = None
                rows = _symbols_rows(body, page.width)
        else:
            rows = _headerless_symbols_body(lines, page, previous[2]) if previous else None

        if rows is None:
            previous = None
            continue
        if previous is None:
            if heading is not None and not continued:
                previous = page, page.page_number, rows
            continue

        section_start = previous[1]
        previous = page, section_start, rows
        if not continued:
            target = first.bbox if heading is not None else rows.first_row
            findings.append(AuditFinding(
                rule_id="P030",
                severity=Severity.WARNING,
                page=page.page_number,
                message="This List of Symbols continuation page is missing its continued heading.",
                details={
                    "page_number": str(page.page_number),
                    "section_type": "list_of_symbols",
                    "issue_type": "missing_symbols_continued_heading",
                    "expected_heading": "LIST OF SYMBOLS (Continued)",
                    "observed_heading": "LIST OF SYMBOLS" if heading is not None else "",
                    "section_start_page": str(section_start),
                    "continuation_index": str(page.page_number - section_start + 1),
                    "bbox": format_bbox_detail(target),
                    "confidence": "high",
                    "source_feedback_id": "F04",
                },
            ))
    return findings


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

    findings.extend(_check_symbols_continued_headings(
        pdf_document.pages, {context.page.page_number for context in contexts},
    ))
    return findings
