"""P063 missing alphabetic prefixes in structurally owned appendix subsections."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_layout import join_content_span_texts
from njit_auditor.pdf_models import BBox, PdfDocument, PdfTextLine, format_bbox_detail
from njit_auditor.pdf_table_continuations import measure_ruled_table_boxes
from njit_auditor.rules.pdf_heading_levels import (
    _SKIP_HEADINGS,
    _is_qualified_heading,
    _split_number_headings,
    _union_bbox,
)
from njit_auditor.rules.pdf_headings import (
    _CHAPTER_HEADING_MASHED_RE,
    _CHAPTER_HEADING_RE,
    _CHAPTER_STANDALONE_RE,
    _is_bold_line,
    normalize_heading_text,
)
from njit_auditor.rules.pdf_margins import BOTTOM_MARGIN_PT, TOP_MARGIN_PT
from njit_auditor.rules.pdf_references_citations_structural import (
    _page_heading as _references_page_heading,
)
from njit_auditor.rules.pdf_title_capitalization import check_apa_title_case_phrase
from njit_auditor.rules.pdf_toc_alignment import (
    HEADING_SUFFIX_RE,
    LETTERED_SECTION_PREFIX_RE,
    LOGICAL_WRAP_MAX_ROWS,
    LOGICAL_WRAP_MIN_INDENT_PT,
    LOGICAL_WRAP_Y_GAP_PT,
    RIGHT_EDGE_TOLERANCE_PT,
    SECTION_NUMBER_PREFIX_RE,
    TOP_LEVEL_TOC_WORD_PREFIX_RE,
    TocEntryLine,
    TocPageContext,
    _assemble_same_baseline_toc_rows,
    _line_reaches_page_number_column,
    _make_entry_from_line,
    collect_toc_visual_rows,
    detect_toc_like_pages,
    group_toc_page_runs,
)

_IDENTIFIER = r"\.[0-9]+(?:\.[0-9]+)*"
_NUMBER_ONLY_RE = re.compile(_IDENTIFIER + r"$")
_SUBSECTION_START_RE = re.compile(rf"^{_IDENTIFIER}(?=\s|$)")
_SUBSECTION_RE = re.compile(rf"^({_IDENTIFIER})\s+(.+)$")
_TOC_APPENDIX_RE = re.compile(
    r"^APPENDIX\b(?:\s+([A-Z])(?=$|[\s:\-–—]))?", re.IGNORECASE,
)
_NUMBERED_APPENDIX_TAIL_RE = re.compile(r"^(?:[A-Z]?\.)?[0-9]", re.IGNORECASE)
_OTHER_ROOT_RE = re.compile(r"^(?:WORKS CITED|GLOSSARY|INDEX)\b", re.IGNORECASE)
_NON_TITLE_RE = re.compile(r"[=≈≃≤≥∑∫<>]|[.!?;]$")
_TRAILING_LEADERS_RE = re.compile(r"(?:(?:[.·]\s*){2,}|…+)$")
_SECTION_START_RE = re.compile(r"^(?:[A-Z]\.)?[0-9]+(?:\.[0-9]+)*\s", re.IGNORECASE)
_OTHER_BODY_BOUNDARIES = frozenset({
    "GLOSSARY", "INDEX", "LIST OF SYMBOLS", "LIST OF ABBREVIATIONS",
})
_TABLE_VALUE_RE = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)\s*%?")
_TABLE_COLUMN_ALIGNMENT_PT = 2.0


def _looks_like_title(title: str) -> bool:
    return (
        _is_qualified_heading(title) and title[0].isupper()
        and _NON_TITLE_RE.search(title) is None
    )


def _identifier_bbox(line: PdfTextLine, identifier: str) -> BBox | None:
    """Use measured glyphs or a span containing only the identifier."""
    if line.line_dir is not None and line.line_dir[0] < 0.99:
        return None
    remaining = identifier
    bbox = None
    for span in line.spans:
        text = span.text.lstrip()
        if not text:
            continue
        count = min(len(remaining), len(text))
        if text[:count] != remaining[:count]:
            return None
        if span.char_x_bounds is not None and len(span.char_x_bounds) == len(span.text):
            offset = len(span.text) - len(text)
            bounds = span.char_x_bounds[offset : offset + count]
            token_box = BBox(x0=min(x0 for x0, _ in bounds), y0=span.bbox.y0,
                             x1=max(x1 for _, x1 in bounds), y1=span.bbox.y1)
        elif span.text == remaining[:count]:
            token_box = span.bbox
        else:
            return None
        if token_box.width <= 0 or token_box.height <= 0:
            return None
        bbox = token_box if bbox is None else _union_bbox(bbox, token_box)
        remaining = remaining[count:]
        if not remaining:
            return bbox
    return None


def _finding(
    page: int, line: PdfTextLine, identifier: str, letter: str, *, toc: bool = False,
) -> AuditFinding:
    expected = f"{letter}{identifier}"
    location = "table of contents" if toc else "body"
    details = {
        "issue_type": "appendix_subsection_missing_letter_prefix",
        "page": str(page),
        "appendix_location": location,
        "actual_identifier": identifier,
        "expected_letter": letter,
        "expected_identifier": expected,
        "triage_tier": "medium",
        "suggested_fix": (
            f"Add the appendix letter {letter} before '{identifier}' so it reads '{expected}'."
        ),
    }
    bbox = _identifier_bbox(line, identifier)
    if bbox is not None:
        details["bbox"] = format_bbox_detail(bbox)
    return AuditFinding(
        rule_id="P063", severity=Severity.WARNING, page=page, details=details,
        message=(
            f"The appendix subsection identifier '{identifier}' in the {location} on page "
            f"{page} is missing its appendix letter. Use '{expected}'."
        ),
    )


def _body_section_boundary(line: PdfTextLine, owner: str) -> bool:
    text = normalize_heading_text(line.text)
    upper = text.upper()
    if upper in _SKIP_HEADINGS or upper in _OTHER_BODY_BOUNDARIES:
        return True
    if not _is_bold_line(line):
        return False
    if upper.startswith("CHAPTER") and (
        _CHAPTER_HEADING_RE.match(upper) or _CHAPTER_STANDALONE_RE.fullmatch(upper)
        or _CHAPTER_HEADING_MASHED_RE.match(upper)
    ):
        return True
    # A conflicting appendix-like heading that N02 could not establish as an
    # anchor makes the previous interval unsafe to extend past this line.
    base = HEADING_SUFFIX_RE.sub("", text)
    appendix = _TOC_APPENDIX_RE.match(base)
    return bool(
        appendix and base.isupper() and appendix[1] != owner
        and (appendix[1] is not None or base == text)
    )


def _starts_in_table(box: BBox, tables: tuple[BBox, ...]) -> bool:
    mid_y = (box.y0 + box.y1) / 2
    return any(table.x0 <= box.x0 < table.x1 and table.y0 <= mid_y <= table.y1 for table in tables)


def _has_borderless_table_peers(
    line: PdfTextLine, identifier: str, lines: list[PdfTextLine], ruled: tuple[BBox, ...],
) -> bool:
    """Look for nearby rows with the same separated value and label columns."""
    spans = [span for span in line.spans if span.text.strip()]
    if len(spans) < 2 or spans[0].text.strip() != identifier:
        return False
    left, right = spans[:2]
    if right.bbox.x0 - left.bbox.x1 < (left.size or left.bbox.height):
        return False
    mid_y = (left.bbox.y0 + left.bbox.y1) / 2
    row_height = max(left.bbox.height, right.bbox.height)
    nearby = [
        peer for peer in lines
        if abs((peer.bbox.y0 + peer.bbox.y1) / 2 - mid_y) <= 3 * row_height
        and not _starts_in_table(peer.bbox, ruled)
    ]
    peers: list[tuple[float, str | None]] = []
    for row in _assemble_same_baseline_toc_rows(nearby):
        y = (row.bbox.y0 + row.bbox.y1) / 2
        if abs(y - mid_y) <= _TABLE_COLUMN_ALIGNMENT_PT:
            continue
        first = next((span for span in row.spans
                      if abs(span.bbox.x0 - left.bbox.x0) <= _TABLE_COLUMN_ALIGNMENT_PT), None)
        second = next((span for span in row.spans
                       if abs(span.bbox.x0 - right.bbox.x0) <= _TABLE_COLUMN_ALIGNMENT_PT), None)
        if first is None or second is None or not any(c.isalpha() for c in second.text):
            continue
        value = first.text.strip()
        if _TABLE_VALUE_RE.fullmatch(value):
            peers.append((y, value))
        elif y < mid_y and value.replace(" ", "").isalpha():
            peers.append((y, None))

    # A column header and another value, in the same local row rhythm, also
    # support the first and last value rows of a borderless table.
    for (y1, value1), (y2, value2) in zip(peers, peers[1:]):
        if value1 is None and value2 is not None:
            gaps = sorted((y1, y2, mid_y))
            if abs((gaps[1] - gaps[0]) - (gaps[2] - gaps[1])) <= row_height * 0.25:
                return True
    # With no identifiable header, require value rows on both sides and
    # distinguish decimal measurements from a run of split .1/.2 headings.
    decimals = [y for y, value in peers if value and not value.startswith(".") and "." in value]
    return any(y < mid_y for y in decimals) and any(y > mid_y for y in decimals)


def _body_findings(
    document: PdfDocument, starts: list[tuple[int, str | None, BBox]], list_pages: set[int],
) -> list[AuditFinding]:
    starts_by_page: dict[int, list[tuple[str | None, BBox]]] = {}
    for page_number, letter, box in starts:
        starts_by_page.setdefault(page_number, []).append((letter, box))
    findings: list[AuditFinding] = []
    owner = None
    for page in document.pages:
        if page.page_number < starts[0][0] or page.page_number in list_pages:
            continue
        if _references_page_heading(page) is not None:
            owner = None
            continue
        lines = sorted(
            (line for block in page.text_blocks for line in block.lines),
            key=lambda line: (line.bbox.y0, line.bbox.x0),
        )
        page_starts = iter(starts_by_page.get(page.page_number, ()))
        next_start = next(page_starts, None)
        anchor_bottom = 0.0
        ruled = None
        joined = _split_number_headings(
            page, number_pattern=_NUMBER_ONLY_RE, require_unique_title=True,
        ) if any(_NUMBER_ONLY_RE.fullmatch(line.text.strip()) for line in lines) else {}
        for line in lines:
            while next_start is not None and next_start[1].y0 <= line.bbox.y0:
                owner, box = next_start
                anchor_bottom = box.y1
                next_start = next(page_starts, None)
            if line.bbox.y0 < anchor_bottom:
                continue
            if owner is None:
                continue
            if _body_section_boundary(line, owner):
                owner = None
                continue
            candidate = joined.get(id(line), line)
            if (
                candidate.bbox.y0 < max(anchor_bottom, TOP_MARGIN_PT)
                or candidate.bbox.y1 > page.height - BOTTOM_MARGIN_PT
                or (next_start is not None and candidate.bbox.y1 > next_start[1].y0)
            ):
                continue
            text = normalize_heading_text(
                join_content_span_texts(candidate.spans) if candidate is line else candidate.text
            )
            match = _SUBSECTION_RE.fullmatch(text)
            if match is None:
                continue
            identifier, title = match.groups()
            if not _looks_like_title(title) or not _is_bold_line(candidate):
                continue
            title_spans = (span for span in candidate.spans if any(c.isalpha() for c in span.text))
            # A bold inline number is not enough. Second-level headings should also
            # look like titles; this disambiguates bold prose starting with a decimal.
            if not all(span.bold for span in title_spans):
                continue
            if identifier.count(".") == 1 and check_apa_title_case_phrase(title):
                continue
            if ruled is None:
                ruled = measure_ruled_table_boxes(document.path, page)
            if _starts_in_table(candidate.bbox, ruled) or _has_borderless_table_peers(
                candidate, identifier, lines, ruled,
            ):
                continue
            findings.append(_finding(page.page_number, candidate, identifier, owner))
    return findings


@dataclass(frozen=True)
class _TocOwner:
    letter: str
    indent_x: float
    folio: int
    column_x: float


def _toc_folio(entry: TocEntryLine) -> tuple[int, float] | None:
    token, right_x = entry.page_number_token, entry.page_number_right_x
    if (
        token and token.isascii() and token.isdecimal() and right_x is not None
        and _line_reaches_page_number_column(entry.line)
    ):
        return int(token), right_x
    return None


def _toc_title(entry: TocEntryLine) -> str:
    text = entry.cleaned_text
    token = entry.page_number_token
    if token:
        text = text.removesuffix(token).rstrip()
    return _TRAILING_LEADERS_RE.sub("", text).rstrip()


def _toc_appendix(entry: TocEntryLine) -> tuple[str | None, tuple[int, float]] | None:
    folio = _toc_folio(entry)
    if folio is None:
        return None
    text = _toc_title(entry)
    match = _TOC_APPENDIX_RE.match(text)
    if match is None or _NUMBERED_APPENDIX_TAIL_RE.match(text[match.end():].lstrip()):
        return None
    return (match[1].upper() if match[1] else None), folio


def _toc_logical_subsection(
    rows: list[TocEntryLine], index: int, owner: _TocOwner,
) -> tuple[str, int] | None:
    """Return the row text and final index if its hanging lines supply an aligned folio."""
    first = rows[index]
    parts = []
    previous = first
    for offset, row in enumerate(rows[index : index + LOGICAL_WRAP_MAX_ROWS]):
        text = _toc_title(row)
        if offset and (
            row.line.bbox.y0 - previous.line.bbox.y0 > LOGICAL_WRAP_Y_GAP_PT
            or row.indent_x < first.indent_x + LOGICAL_WRAP_MIN_INDENT_PT
            or TOP_LEVEL_TOC_WORD_PREFIX_RE.match(text)
            or _OTHER_ROOT_RE.match(text)
            or _SECTION_START_RE.match(text)
        ):
            break
        parts.append(text)
        folio = _toc_folio(row)
        if folio is not None:
            number, x = folio
            if number >= owner.folio and abs(x - owner.column_x) <= RIGHT_EDGE_TOLERANCE_PT:
                return " ".join(parts), index + offset
            break
        previous = row
    return None


def _toc_findings(
    contexts: list[TocPageContext], starts: list[tuple[int, str | None, BBox]],
) -> list[AuditFinding]:
    body_letters = {letter for _, letter, _ in starts if letter is not None}
    findings: list[AuditFinding] = []
    for run in group_toc_page_runs(contexts):
        pages = {
            context.page.page_number: [
                _make_entry_from_line(row, row.text, require_right_edge=True)
                for row in collect_toc_visual_rows(context)
            ]
            for context in run.contexts
        }
        counts = Counter(
            parent[0] for rows in pages.values() for row in rows
            if (parent := _toc_appendix(row)) is not None
        )
        owner = None
        for page, rows in pages.items():
            consumed_through = -1
            for index, row in enumerate(rows):
                if index <= consumed_through:
                    continue
                text = row.cleaned_text
                if TOP_LEVEL_TOC_WORD_PREFIX_RE.match(text) or _OTHER_ROOT_RE.match(text):
                    owner = None
                    parent = _toc_appendix(row)
                    if parent is not None:
                        label, (folio, column) = parent
                        letter = label or "A"
                        if (
                            letter in body_letters and counts[label] == 1
                            and (label is not None or (len(starts) == 1 and len(counts) == 1))
                        ):
                            owner = _TocOwner(letter, row.indent_x, folio, column)
                    continue
                if owner is None:
                    continue
                valid = LETTERED_SECTION_PREFIX_RE.match(text.upper())
                if (valid and valid[1][0] != owner.letter) or SECTION_NUMBER_PREFIX_RE.match(text):
                    owner = None
                    continue
                malformed = _SUBSECTION_START_RE.match(_toc_title(row))
                if not valid and (
                    not malformed or row.indent_x < owner.indent_x + LOGICAL_WRAP_MIN_INDENT_PT
                ):
                    continue
                logical = _toc_logical_subsection(rows, index, owner)
                if logical is None:
                    continue
                title, consumed_through = logical
                # A prefixless-looking line deeper than an open numbered row
                # may finish its title. Its aligned folio closes that entry.
                match = _SUBSECTION_RE.fullmatch(title) if malformed else None
                if match is not None and _looks_like_title(match[2]):
                    findings.append(_finding(page, row.line, match[1], owner.letter, toc=True))
    return findings


def check_appendix_subsections(
    document: PdfDocument, headings: list[tuple[int, str | None, BBox]],
) -> list[AuditFinding]:
    """Check body headings and independently evidenced TOC rows against N02 ownership."""
    if not headings:
        return []
    counts = Counter(letter for _, letter, _ in headings if letter is not None)
    starts = [
        (page, (letter or "A") if len(headings) == 1 else (
            letter if letter is not None and counts[letter] == 1 else None
        ), box)
        for page, letter, box in headings
    ]
    contexts = detect_toc_like_pages(document)
    body = _body_findings(document, starts, {context.page.page_number for context in contexts})
    toc = [context for context in contexts if context.page_type == "table_of_contents"]
    return body + _toc_findings(toc, starts)
