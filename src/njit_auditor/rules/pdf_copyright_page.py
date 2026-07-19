"""Conservative Copyright Page metadata and layout checks (P034, P051, P052).

Partial PDF heuristic coverage for Q009–Q011:
  - Q009: no header text in the Copyright page top margin
  - Q010: copyright year matches title-page graduation year (P034);
          copyright year not found at all (P051)
  - Q011: copyright author name matches title-page author name (P034);
          copyright author not found at all (P052)

Does not quote author names, title text, or body text in findings.
Does not duplicate Q012 (no page number on copyright page) — see P022.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import (
    BBox,
    PdfDocument,
    PdfPage,
    PdfTextLine,
    format_bbox_detail,
)
from njit_auditor.rules.pdf_headings import (
    find_named_frontmatter_headings,
    normalize_heading_text,
)

_COPYRIGHT_HEADING = "COPYRIGHT PAGE"
_COPYRIGHT_RE = re.compile(r"\bcopyright\b|©|\(c\)", re.IGNORECASE)
_COPYRIGHT_SCAN_PAGES = 6
_TOP_ZONE_RATIO = 0.15
_MIN_DOC_PAGES = 3
_PAGE_NUM_RE = re.compile(r"^\s*[\[(]?(?:\d+|[ivxlcdm]+)[\])]?[.]?\s*$", re.IGNORECASE)
_MONTH_YEAR_RE = re.compile(
    r"^(?:january|february|march|april|may|june|july|august|september|"
    r"october|november|december)\s+((?:19|20)\d{2})$",
    re.IGNORECASE,
)
_YEAR_TOKEN_RE = re.compile(r"(?<!\d)((?:19|20)\d{2})(?!\d)")
_COPYRIGHT_YEAR_LINE_RE = re.compile(
    r"(?:©|\(c\)|copyright)\s*(?:©\s*)?((?:19|20)\d{2})",
    re.IGNORECASE,
)
_ADJACENT_YEAR_ROW_RE = re.compile(
    r"^(?:©\s*)?((?:19|20)\d{2})(?:\s+(?:by\s+)?[A-Za-z].*)?$",
    re.IGNORECASE,
)
_AUTHOR_NOISE_RE = re.compile(
    r"^(submitted|a dissertation|a thesis|in partial fulfillment|"
    r"new jersey institute|njit|doctor of|master of|ph\.?d|committee|date:|"
    r"all rights reserved|rights reserved)\b",
    re.IGNORECASE,
)
_MIN_AUTHOR_NORMALIZED_LEN = 4
_MIN_AUTHOR_WORDS = 2
_NAME_SUFFIX_TOKENS = frozenset({"jr", "sr", "ii", "iii", "iv"})
_MAX_MIDDLE_INITIAL_TOKEN_LEN = 2
_ROW_Y_TOLERANCE_PT = 3.0
_MIN_SPAN_SPACE_GAP_PT = 1.0
_MAX_ADJACENT_ROW_GAP_PT = 36.0
_MAX_ADJACENT_ROW_CENTER_DELTA_PT = 72.0
_MAX_INFERRED_COPYRIGHT_ROWS = 6


@dataclass(frozen=True)
class _VisualRow:
    text: str
    bbox: BBox
    lines: tuple[PdfTextLine, ...]


@dataclass(frozen=True)
class _CopyrightYearContext:
    year: int | None
    notice_bbox: BBox | None
    associated_year_bbox: BBox | None
    candidate_year_bbox: BBox | None
    association: str
    marker_detected: bool


def _stable_author_hash(normalized: str) -> str:
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def _normalize_author(text: str) -> str:
    lowered = text.lower().replace("\u00a0", " ")
    lowered = re.sub(r"[^\w\s]", "", lowered)
    return " ".join(lowered.split())


def _normalize_notice_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).replace("\u00a0", " ")
    return " ".join(normalized.split())


def _sorted_lines(page: PdfPage) -> list[PdfTextLine]:
    lines = [line for block in page.text_blocks for line in block.lines]
    return sorted(lines, key=lambda line: (line.bbox.y0, line.bbox.x0))


def _union_bboxes(boxes: list[BBox]) -> BBox | None:
    if not boxes:
        return None
    return BBox(
        x0=min(box.x0 for box in boxes),
        y0=min(box.y0 for box in boxes),
        x1=max(box.x1 for box in boxes),
        y1=max(box.y1 for box in boxes),
    )


def _visual_space_gap_threshold(line: PdfTextLine) -> float:
    sizes = [span.size for span in line.spans if span.size]
    if not sizes:
        return _MIN_SPAN_SPACE_GAP_PT
    return max(_MIN_SPAN_SPACE_GAP_PT, min(sizes) * 0.12)


def _rebuild_line_text(line: PdfTextLine) -> str:
    pieces: list[str] = []
    prev_end_x: float | None = None
    gap_threshold = _visual_space_gap_threshold(line)

    for span in sorted(line.spans, key=lambda item: item.bbox.x0):
        raw = unicodedata.normalize("NFKC", span.text).replace("\u00a0", " ")
        if not raw.strip():
            continue
        clean = raw.strip()
        if pieces:
            needs_space = raw[:1].isspace() or pieces[-1][-1].isspace()
            if not needs_space and prev_end_x is not None:
                needs_space = (span.bbox.x0 - prev_end_x) >= gap_threshold
            if needs_space:
                pieces.append(" ")
        pieces.append(clean)
        prev_end_x = span.bbox.x1

    return _normalize_notice_text("".join(pieces))


def _visual_rows(page: PdfPage) -> list[_VisualRow]:
    rows: list[list[PdfTextLine]] = []
    for line in _sorted_lines(page):
        line_center_y = (line.bbox.y0 + line.bbox.y1) / 2.0
        if rows:
            previous = rows[-1]
            previous_center_y = sum(
                (item.bbox.y0 + item.bbox.y1) / 2.0 for item in previous
            ) / len(previous)
            previous_height = sum(item.bbox.height for item in previous) / len(previous)
            tolerance = max(
                _ROW_Y_TOLERANCE_PT,
                min(previous_height, line.bbox.height) * 0.35,
            )
            if abs(line_center_y - previous_center_y) <= tolerance:
                previous.append(line)
                continue
        rows.append([line])

    result: list[_VisualRow] = []
    for row_lines in rows:
        ordered = sorted(row_lines, key=lambda item: item.bbox.x0)
        row_text = " ".join(
            rebuilt for line in ordered if (rebuilt := _rebuild_line_text(line))
        ).strip()
        row_bbox = _union_bboxes([line.bbox for line in ordered])
        if not row_text or row_bbox is None:
            continue
        result.append(
            _VisualRow(
                text=_normalize_notice_text(row_text),
                bbox=row_bbox,
                lines=tuple(ordered),
            )
        )
    return result


def _page_has_meaningful_text(page: PdfPage) -> bool:
    for line in _sorted_lines(page):
        if re.search(r"[A-Za-z]{2,}", line.text):
            return True
    return False


def _find_copyright_page(pdf_document: PdfDocument) -> PdfPage | None:
    """Return the Copyright Page when confidently identified, else None."""

    if len(pdf_document.pages) < _MIN_DOC_PAGES:
        return None

    headings = find_named_frontmatter_headings(pdf_document)
    if not headings:
        return None

    pages_by_number = {page.page_number: page for page in pdf_document.pages}

    for match in headings:
        if match.heading == _COPYRIGHT_HEADING:
            page = pages_by_number.get(match.page_number)
            if page is not None and _page_has_meaningful_text(page):
                return page

    for page in pdf_document.pages[:_COPYRIGHT_SCAN_PAGES]:
        rows = _visual_rows(page)
        if not rows or len(rows) > _MAX_INFERRED_COPYRIGHT_ROWS:
            continue
        full_text = " ".join(row.text for row in rows)
        if _COPYRIGHT_RE.search(full_text):
            if _page_has_meaningful_text(page):
                return page
    return None


def _in_top_zone(line: PdfTextLine, page_height: float) -> bool:
    return line.bbox.y1 <= page_height * _TOP_ZONE_RATIO


def _classify_top_margin_text(cleaned: str) -> str:
    upper = cleaned.upper()
    if upper == _COPYRIGHT_HEADING:
        return "copyright_heading"
    if _PAGE_NUM_RE.match(cleaned):
        return "page_number_candidate"
    if _COPYRIGHT_RE.search(cleaned) and len(cleaned) < 40:
        return "copyright_notice_fragment"
    if len(cleaned.split()) <= 3 and cleaned.istitle():
        return "short_running_header"
    return "other_header_text"


def _check_top_margin_header(copyright_page: PdfPage) -> AuditFinding | None:
    """Flag non-page-number text clearly in the top margin (Q009)."""

    flagged: list[tuple[str, float]] = []
    for line in _sorted_lines(copyright_page):
        if not _in_top_zone(line, copyright_page.height):
            continue
        cleaned = normalize_heading_text(line.text)
        if not cleaned or len(cleaned) < 3:
            continue
        kind = _classify_top_margin_text(cleaned)
        if kind in {"page_number_candidate", "copyright_heading", "copyright_notice_fragment"}:
            continue
        if not re.search(r"[A-Za-z]", cleaned):
            continue
        flagged.append((kind, line.bbox.y0))

    if not flagged:
        return None

    kind, y0 = flagged[0]
    return AuditFinding(
        rule_id="P034",
        severity=Severity.WARNING,
        page=copyright_page.page_number,
        message=(
            "Possible header or running text detected in the top margin of the "
            "Copyright Page (NJIT expects no header text in this area)."
        ),
        details={
            "issue_type": "copyright_top_margin_header_text",
            "page": str(copyright_page.page_number),
            "observed_text_kind": kind,
            "approx_y0_pt": f"{y0:.1f}",
            "flagged_line_count": str(len(flagged)),
            "source_q_rule_id": "Q009",
            "confidence": "medium",
        },
    )


def _extract_title_page_year(title_page: PdfPage) -> int | None:
    years: list[int] = []
    for line in _sorted_lines(title_page):
        cleaned = _rebuild_line_text(line) or normalize_heading_text(line.text)
        month_year = _MONTH_YEAR_RE.match(cleaned)
        if month_year:
            return int(month_year.group(1))
        if _AUTHOR_NOISE_RE.match(cleaned):
            continue
        for match in _YEAR_TOKEN_RE.finditer(cleaned):
            years.append(int(match.group()))
    unique = sorted(set(years))
    if len(unique) == 1:
        return unique[0]
    return None


def _extract_copyright_year(copyright_page: PdfPage) -> int | None:
    return _locate_copyright_year(copyright_page).year


def _author_confidence(normalized: str) -> str:
    words = normalized.split()
    if len(normalized) < _MIN_AUTHOR_NORMALIZED_LEN:
        return "low"
    if len(words) >= _MIN_AUTHOR_WORDS:
        return "high"
    if len(words) == 1 and len(words[0]) >= _MIN_AUTHOR_NORMALIZED_LEN:
        return "high"
    return "low"


def _is_author_noise(cleaned: str) -> bool:
    if not cleaned:
        return True
    if _AUTHOR_NOISE_RE.match(cleaned):
        return True
    if _MONTH_YEAR_RE.match(cleaned):
        return True
    if _COPYRIGHT_RE.search(cleaned):
        return True
    return False


def _extract_title_page_author(title_page: PdfPage) -> tuple[str, str] | None:
    lines = [
        _rebuild_line_text(line) or normalize_heading_text(line.text)
        for line in _sorted_lines(title_page)
    ]
    for index, cleaned in enumerate(lines):
        if cleaned.lower() != "by":
            continue
        if index + 1 >= len(lines):
            return None
        candidate = lines[index + 1]
        if _is_author_noise(candidate):
            return None
        normalized = _normalize_author(candidate)
        if _author_confidence(normalized) != "high":
            return None
        return normalized, _stable_author_hash(normalized)
    return None


def _authors_match_with_middle_initial_tolerance(
    title_norm: str,
    copyright_norm: str,
) -> bool:
    """Treat copyright notice with one extra short initial/suffix token as a match.

    Common layout: Title Page ``by`` line has given + family name; © line adds a
    leading middle initial (e.g. two characters after normalization).
    """

    if title_norm == copyright_norm:
        return True
    title_words = title_norm.split()
    copyright_words = copyright_norm.split()
    if len(title_words) < _MIN_AUTHOR_WORDS or len(copyright_words) < _MIN_AUTHOR_WORDS:
        return False
    if len(copyright_words) != len(title_words) + 1:
        return False

    extra: str | None = None
    if copyright_words[1:] == title_words:
        extra = copyright_words[0]
    elif copyright_words[:-1] == title_words:
        extra = copyright_words[-1]
    if extra is None:
        return False
    if len(extra) <= _MAX_MIDDLE_INITIAL_TOKEN_LEN:
        return True
    return extra in _NAME_SUFFIX_TOKENS


def _extract_copyright_year_adjacent_lines(copyright_page: PdfPage) -> int | None:
    """Return copyright year when marker and year appear on adjacent lines.

    Handles the pattern where line N has a copyright marker but no year token
    and line N+1 has exactly one year token with no other significant text.
    """
    context = _locate_copyright_year(copyright_page)
    if context.association == "adjacent_row":
        return context.year
    return None


def _extract_copyright_author_adjacent_lines(
    copyright_page: PdfPage,
) -> tuple[str, str] | None:
    """Return (normalized, hash) when copyright year and author appear on adjacent lines.

    Handles the pattern where line N has the copyright year (© YYYY or Copyright YYYY)
    but no recognizable author string, and line N+1 has a plausible author-like string
    (2+ words, no copyright marker, no year token, no noise patterns).
    """
    rows = _visual_rows(copyright_page)
    for i, row in enumerate(rows[:-1]):
        cleaned = row.text.strip()
        if not cleaned:
            continue
        if not _COPYRIGHT_RE.search(cleaned):
            continue
        next_text = rows[i + 1].text.strip()
        if not next_text:
            continue
        if _COPYRIGHT_RE.search(next_text):
            continue  # next line is another copyright marker line
        if _YEAR_TOKEN_RE.search(cleaned):
            existing_match = re.search(
                r"(?:©|\(c\)|copyright)\s*(?:©\s*)?(?:19|20)\d{2}\s*(?:by\s+)?(.+)$",
                cleaned,
                re.IGNORECASE,
            )
            if existing_match and existing_match.group(1).strip():
                continue  # same-line author already handled
        elif _is_plausible_adjacent_year_row(next_text):
            if author := _extract_author_from_year_row(next_text):
                return author
            continue
        elif _YEAR_TOKEN_RE.search(next_text):
            continue  # unrelated year on next line — too ambiguous
        if _AUTHOR_NOISE_RE.match(next_text):
            continue
        normalized = _normalize_author(next_text)
        if _author_confidence(normalized) != "high":
            continue
        return normalized, _stable_author_hash(normalized)
    return None


def _extract_copyright_author(copyright_page: PdfPage) -> tuple[str, str] | None:
    for row in _visual_rows(copyright_page):
        raw = row.text.strip()
        if not _COPYRIGHT_RE.search(raw):
            continue
        if author := _extract_author_from_year_row(raw):
            return author
    return None


def _row_years(row: _VisualRow) -> list[int]:
    return [int(match.group(1)) for match in _YEAR_TOKEN_RE.finditer(row.text)]


def _is_plausible_adjacent_year_row(text: str) -> bool:
    return _ADJACENT_YEAR_ROW_RE.match(text) is not None


def _extract_author_from_year_row(text: str) -> tuple[str, str] | None:
    match = re.search(
        r"(?:©|\(c\)|copyright)?\s*(?:©\s*)?(?:19|20)\d{2}\s*(?:by\s+)?(.+)$",
        text,
        re.IGNORECASE,
    )
    if not match:
        return None
    remainder = match.group(1)
    remainder = re.split(
        r"\.\s*All Rights Reserved|\s+All Rights Reserved",
        remainder,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    remainder = remainder.strip(" .,;")
    if not remainder:
        return None
    normalized = _normalize_author(remainder)
    if _author_confidence(normalized) != "high":
        return None
    return normalized, _stable_author_hash(normalized)


def _rows_are_visually_adjacent(notice_row: _VisualRow, candidate_row: _VisualRow) -> bool:
    vertical_gap = max(
        candidate_row.bbox.y0 - notice_row.bbox.y1,
        notice_row.bbox.y0 - candidate_row.bbox.y1,
        0.0,
    )
    if vertical_gap > _MAX_ADJACENT_ROW_GAP_PT:
        return False
    notice_center_x = (notice_row.bbox.x0 + notice_row.bbox.x1) / 2.0
    candidate_center_x = (candidate_row.bbox.x0 + candidate_row.bbox.x1) / 2.0
    return abs(notice_center_x - candidate_center_x) <= _MAX_ADJACENT_ROW_CENTER_DELTA_PT


def _locate_copyright_year(copyright_page: PdfPage) -> _CopyrightYearContext:
    rows = _visual_rows(copyright_page)
    notice_rows = [(index, row) for index, row in enumerate(rows) if _COPYRIGHT_RE.search(row.text)]
    marker_detected = bool(notice_rows)

    for notice_index, notice_row in notice_rows:
        same_row_match = _COPYRIGHT_YEAR_LINE_RE.search(notice_row.text)
        same_row_years = sorted(set(_row_years(notice_row)))
        if same_row_match is not None and len(same_row_years) == 1:
            return _CopyrightYearContext(
                year=same_row_years[0],
                notice_bbox=notice_row.bbox,
                associated_year_bbox=notice_row.bbox,
                candidate_year_bbox=notice_row.bbox,
                association="same_row",
                marker_detected=True,
            )

        for offset in (-1, 1):
            candidate_index = notice_index + offset
            if not (0 <= candidate_index < len(rows)):
                continue
            candidate_row = rows[candidate_index]
            if _COPYRIGHT_RE.search(candidate_row.text):
                continue
            if not _rows_are_visually_adjacent(notice_row, candidate_row):
                continue
            years = _row_years(candidate_row)
            if len(years) != 1 or not _is_plausible_adjacent_year_row(candidate_row.text):
                continue
            return _CopyrightYearContext(
                year=years[0],
                notice_bbox=notice_row.bbox,
                associated_year_bbox=candidate_row.bbox,
                candidate_year_bbox=candidate_row.bbox,
                association="adjacent_row",
                marker_detected=True,
            )

    first_notice_bbox = notice_rows[0][1].bbox if notice_rows else None
    candidate_year_rows = [
        row for row in rows if _row_years(row) and not _COPYRIGHT_RE.search(row.text)
    ]
    if notice_rows and candidate_year_rows:
        notice_row = notice_rows[0][1]
        candidate_row = min(
            candidate_year_rows,
            key=lambda row: abs(
                ((row.bbox.y0 + row.bbox.y1) / 2.0)
                - ((notice_row.bbox.y0 + notice_row.bbox.y1) / 2.0)
            ),
        )
        return _CopyrightYearContext(
            year=None,
            notice_bbox=first_notice_bbox,
            associated_year_bbox=None,
            candidate_year_bbox=candidate_row.bbox,
            association="unassociated_year_elsewhere",
            marker_detected=True,
        )

    return _CopyrightYearContext(
        year=None,
        notice_bbox=first_notice_bbox,
        associated_year_bbox=None,
        candidate_year_bbox=None,
        association="no_year_candidate" if marker_detected else "no_copyright_notice",
        marker_detected=marker_detected,
    )


def _check_year_consistency(
    copyright_page: PdfPage,
    title_page: PdfPage,
) -> AuditFinding | None:
    copyright_year = _extract_copyright_year(copyright_page)
    title_year = _extract_title_page_year(title_page)
    if copyright_year is None or title_year is None:
        return None
    if copyright_year == title_year:
        return None
    return AuditFinding(
        rule_id="P034",
        severity=Severity.WARNING,
        page=copyright_page.page_number,
        message=(
            "Copyright year on the Copyright Page may not match the graduation year "
            "on the Title Page."
        ),
        details={
            "issue_type": "copyright_year_mismatch",
            "copyright_year": str(copyright_year),
            "title_page_year": str(title_year),
            "source_q_rule_id": "Q010",
            "confidence": "high",
        },
    )


def _check_author_consistency(
    copyright_page: PdfPage,
    title_page: PdfPage,
) -> AuditFinding | None:
    title_author = _extract_title_page_author(title_page)
    copyright_author = _extract_copyright_author(copyright_page)
    if title_author is None or copyright_author is None:
        return None
    title_norm, title_hash = title_author
    copyright_norm, copyright_hash = copyright_author
    if title_hash == copyright_hash:
        return None
    if _authors_match_with_middle_initial_tolerance(title_norm, copyright_norm):
        return None
    return AuditFinding(
        rule_id="P034",
        severity=Severity.WARNING,
        page=copyright_page.page_number,
        message=(
            "Author name on the Copyright Page may not match the author name on the "
            "Title Page."
        ),
        details={
            "issue_type": "copyright_author_mismatch",
            "title_page_author_hash": title_hash,
            "copyright_author_hash": copyright_hash,
            "comparison_basis": "normalized_author_name_hash",
            "source_q_rule_id": "Q011",
            "confidence": "high",
        },
    )


def check_pdf_copyright_year_format(pdf_document: PdfDocument) -> list[AuditFinding]:
    """Emit P051 advisory when copyright page is detected but no copyright year is found."""
    copyright_page = _find_copyright_page(pdf_document)
    if copyright_page is None:
        return []
    context = _locate_copyright_year(copyright_page)
    if context.year is not None:
        return []
    details = {
        "issue_type": "copyright_year_not_found",
        "page": str(copyright_page.page_number),
        "copyright_marker_detected": str(context.marker_detected).lower(),
        "triage_tier": "low",
        "confidence": "low",
        "source_q_rule_id": "Q010",
        "year_association": context.association,
    }
    if context.notice_bbox is not None:
        details["bbox"] = format_bbox_detail(context.notice_bbox)
    if context.candidate_year_bbox is not None:
        details["candidate_year_bbox"] = format_bbox_detail(context.candidate_year_bbox)
    return [
        AuditFinding(
            rule_id="P051",
            severity=Severity.WARNING,
            page=copyright_page.page_number,
            message=(
                "Copyright Page detected, but the auditor could not confidently "
                "associate a four-digit year with the copyright notice. Verify that "
                "the year appears directly next to the notice and matches the Title "
                "Page year."
            ),
            details=details,
        )
    ]


def check_pdf_copyright_author_format(pdf_document: PdfDocument) -> list[AuditFinding]:
    """Emit P052 advisory when copyright page and year found but no author is extractable."""
    copyright_page = _find_copyright_page(pdf_document)
    if copyright_page is None:
        return []
    # Only fire when year IS found (confirming it is a real copyright page with year content)
    if _extract_copyright_year(copyright_page) is None:
        if _extract_copyright_year_adjacent_lines(copyright_page) is None:
            return []  # year not found — P051 handles that; not our concern
    # If P034 can already extract the author, no advisory needed
    if _extract_copyright_author(copyright_page) is not None:
        return []
    if _extract_copyright_author_adjacent_lines(copyright_page) is not None:
        return []
    # Copyright page with year but no author string extractable
    page_text = " ".join(row.text for row in _visual_rows(copyright_page))
    return [
        AuditFinding(
            rule_id="P052",
            severity=Severity.WARNING,
            page=copyright_page.page_number,
            message=(
                "Copyright Page detected with a copyright year but no author or "
                "copyright-owner name could be confidently identified. Verify that "
                "the copyright owner name is present and clearly formatted."
            ),
            details={
                "issue_type": "copyright_author_not_found",
                "page": str(copyright_page.page_number),
                "copyright_marker_detected": str(
                    bool(_COPYRIGHT_RE.search(page_text))
                ).lower(),
                "year_detected": "true",
                "triage_tier": "low",
                "source_q_rule_id": "Q011",
            },
        )
    ]


def check_pdf_copyright_page(pdf_document: PdfDocument) -> list[AuditFinding]:
    """Emit P034 warnings for Copyright Page layout and metadata consistency."""

    copyright_page = _find_copyright_page(pdf_document)
    if copyright_page is None:
        return []

    if not pdf_document.pages:
        return []

    title_page = pdf_document.pages[0]
    findings: list[AuditFinding] = []

    header_finding = _check_top_margin_header(copyright_page)
    if header_finding is not None:
        findings.append(header_finding)

    year_finding = _check_year_consistency(copyright_page, title_page)
    if year_finding is not None:
        findings.append(year_finding)

    author_finding = _check_author_consistency(copyright_page, title_page)
    if author_finding is not None:
        findings.append(author_finding)

    return findings
