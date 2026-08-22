"""Focused Biographical Sketch birth-information check (P084, Q023).

Q023: Does the Biographical Sketch text exclude both place of birth and date of birth?

This detector is intentionally narrow:
- scans only the unique BIOGRAPHICAL SKETCH page
- stops before any Publications/Presentations subsection when present
- warns only on high-confidence birth-information patterns

It does not attempt broad biographical-content classification and does not
implement Q024 or Q030.
"""

from __future__ import annotations

import re

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument, PdfTextLine
from njit_auditor.rules.pdf_biosketch_degree_ordering import (
    _PAGE_NUM_RE,
    _find_biosketch_page_and_heading_y,
    _find_publications_boundary_y,
)

_MONTH_NAMES = frozenset(
    {
        "january",
        "february",
        "march",
        "april",
        "may",
        "june",
        "july",
        "august",
        "september",
        "october",
        "november",
        "december",
    }
)
_DATE_OF_BIRTH_RE = re.compile(r"\bdate\s+of\s+birth\b", re.IGNORECASE)
_PLACE_OF_BIRTH_RE = re.compile(r"\bplace\s+of\s+birth\b", re.IGNORECASE)
_BIRTHPLACE_RE = re.compile(
    r"(?:^|\b)birthplace(?:\b\s*(?::|-)\s*|\b\s+is\s+)",
    re.IGNORECASE,
)
_BORN_WITH_DATE_RE = re.compile(
    r"\b(?:was\s+)?born\s+(?:on\s+)?"
    r"(?:"
    r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+\d{1,2},\s+\d{4}"
    r"|"
    r"\d{1,2}/\d{1,2}/\d{2,4}"
    r"|"
    r"\d{1,2}-\d{1,2}-\d{2,4}"
    r")\b"
)
_BORN_IN_PLACE_RE = re.compile(
    r"\b(?:[Ww]as\s+)?born\s+in\s+"
    r"(?P<place>(?:[A-Z][A-Za-z'.-]*)(?:(?:\s+|,\s*)(?:[A-Z][A-Za-z'.-]*)){0,4})\b"
)
_DETERMINER_PLACE_TOKENS = frozenset({"The", "A", "An", "This", "That", "These", "Those"})


def _collapse_text(text: str) -> str:
    return " ".join(text.strip().split())


def _match_birth_pattern(line: PdfTextLine) -> set[str]:
    """Return high-confidence birth-information pattern labels for a line."""
    text = _collapse_text(line.text)
    if not text or _PAGE_NUM_RE.match(text):
        return set()

    lowered = text.lower()
    matches: set[str] = set()

    if _DATE_OF_BIRTH_RE.search(text):
        matches.add("date_of_birth_field")
    if _PLACE_OF_BIRTH_RE.search(text):
        matches.add("place_of_birth_field")
    if _BIRTHPLACE_RE.search(text):
        matches.add("birthplace_field")
    if _BORN_WITH_DATE_RE.search(text):
        matches.add("born_with_date")

    place_match = _BORN_IN_PLACE_RE.search(text)
    if place_match is not None:
        first_token = place_match.group("place").split()[0].rstrip(",")
        if first_token not in _DETERMINER_PLACE_TOKENS and first_token.lower() not in _MONTH_NAMES:
            matches.add("born_in_place")

    # Guard against generic non-personal phrasing such as "birth of the internet".
    if "birth of " in lowered and not matches:
        return set()

    return matches


def check_pdf_biosketch_birth_information(pdf_document: PdfDocument) -> list[AuditFinding]:
    """Emit P084 when the Biographical Sketch appears to include birth information."""
    result = _find_biosketch_page_and_heading_y(pdf_document)
    if result is None:
        return []

    page, heading_y = result
    pub_boundary_y = _find_publications_boundary_y(page, heading_y)

    matched_types: set[str] = set()
    matched_line_count = 0
    for block in page.text_blocks:
        for line in block.lines:
            if line.bbox.y0 <= heading_y + 2:
                continue
            if pub_boundary_y is not None and line.bbox.y0 >= pub_boundary_y:
                continue
            line_matches = _match_birth_pattern(line)
            if not line_matches:
                continue
            matched_line_count += 1
            matched_types.update(line_matches)

    if not matched_types:
        return []

    return [
        AuditFinding(
            rule_id="P084",
            severity=Severity.WARNING,
            page=page.page_number,
            message=(
                "Biographical Sketch appears to include place of birth or date of birth. "
                "NJIT guidelines require the Biographical Sketch to exclude both place "
                "of birth and date of birth."
            ),
            details={
                "page_number": str(page.page_number),
                "issue_type": "biosketch_birth_information_present",
                "matched_pattern_types": ",".join(sorted(matched_types)),
                "matched_line_count": str(matched_line_count),
                "confidence": "high",
                "triage_tier": "medium",
                "suggested_fix": (
                    "Remove place of birth and date of birth from the Biographical Sketch."
                ),
                "source_q_rule_id": "Q023",
            },
        )
    ]
