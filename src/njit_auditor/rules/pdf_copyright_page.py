"""Conservative Copyright Page metadata and layout checks (P034).

Partial PDF heuristic coverage for Q009–Q011:
  - Q009: no header text in the Copyright page top margin
  - Q010: copyright year matches title-page graduation year
  - Q011: copyright author name matches title-page author name

Does not quote author names, title text, or body text in findings.
Does not duplicate Q012 (no page number on copyright page) — see P022.
"""

from __future__ import annotations

import hashlib
import re

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument, PdfPage, PdfTextLine
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
_YEAR_TOKEN_RE = re.compile(r"\b(19|20)\d{2}\b")
_COPYRIGHT_YEAR_LINE_RE = re.compile(
    r"(?:©|\(c\)|copyright)\s*(?:©\s*)?(19|20)\d{2}",
    re.IGNORECASE,
)
_AUTHOR_NOISE_RE = re.compile(
    r"^(submitted|a dissertation|a thesis|in partial fulfillment|"
    r"new jersey institute|njit|doctor of|master of|ph\.?d|committee|date:)\b",
    re.IGNORECASE,
)
_MIN_AUTHOR_NORMALIZED_LEN = 4
_MIN_AUTHOR_WORDS = 2


def _stable_author_hash(normalized: str) -> str:
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def _normalize_author(text: str) -> str:
    lowered = text.lower().replace("\u00a0", " ")
    lowered = re.sub(r"[^\w\s]", "", lowered)
    return " ".join(lowered.split())


def _sorted_lines(page: PdfPage) -> list[PdfTextLine]:
    lines = [line for block in page.text_blocks for line in block.lines]
    return sorted(lines, key=lambda line: (line.bbox.y0, line.bbox.x0))


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
        full_text = " ".join(line.text for line in _sorted_lines(page))
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
        cleaned = normalize_heading_text(line.text)
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
    line_years: list[int] = []
    all_years: list[int] = []
    for line in _sorted_lines(copyright_page):
        cleaned = line.text.strip()
        if not cleaned:
            continue
        years_in_line = [int(m.group()) for m in _YEAR_TOKEN_RE.finditer(cleaned)]
        all_years.extend(years_in_line)
        if _COPYRIGHT_YEAR_LINE_RE.search(cleaned):
            if len(years_in_line) == 1:
                line_years.append(years_in_line[0])
            elif len(years_in_line) > 1:
                return None
    if len(line_years) == 1:
        return line_years[0]
    unique = sorted(set(all_years))
    if len(unique) == 1:
        return unique[0]
    return None


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
    lines = [normalize_heading_text(line.text) for line in _sorted_lines(title_page)]
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


def _extract_copyright_author(copyright_page: PdfPage) -> tuple[str, str] | None:
    for line in _sorted_lines(copyright_page):
        raw = line.text.strip()
        if not _COPYRIGHT_RE.search(raw):
            continue
        match = re.search(
            r"(?:©|\(c\)|copyright)\s*(?:©\s*)?(?:19|20)\d{2}\s+(.+)$",
            raw,
            re.IGNORECASE,
        )
        if not match:
            continue
        remainder = match.group(1)
        remainder = re.split(
            r"\.\s*All Rights Reserved|\s+All Rights Reserved",
            remainder,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]
        remainder = remainder.strip(" .,;")
        if not remainder:
            continue
        normalized = _normalize_author(remainder)
        if _author_confidence(normalized) != "high":
            continue
        return normalized, _stable_author_hash(normalized)
    return None


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
