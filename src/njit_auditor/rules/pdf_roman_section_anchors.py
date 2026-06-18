"""Conservative front-matter section-anchored Roman numeral checks (P037)."""

from __future__ import annotations

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument
from njit_auditor.rules.pdf_headings import normalize_heading_text
from njit_auditor.rules.pdf_page_numbering_regime import (
    _classify_pages,
    _find_no_number_pages,
)
from njit_auditor.rules.pdf_page_numbers import (
    PageNumberCandidate,
    detect_page_number_candidates,
)
from njit_auditor.rules.pdf_roman_sequence import _MAX_PLAUSIBLE_FRONTMATTER_ROMAN

# NJIT template expected Roman numeral values by section heading.
# Biographical Sketch is always iv (4); subsequent sections occupy fixed slots.
# DEDICATION is optional: if the heading is absent, the slot (v) is still counted
# because a dedication page may exist without a detectable heading.
_SECTION_EXPECTED: dict[str, int] = {
    "BIOGRAPHICAL SKETCH": 4,
    "DEDICATION": 5,
    "ACKNOWLEDGEMENTS": 6,
    "TABLE OF CONTENTS": 7,
    "LIST OF TABLES": 8,
}

_SECTION_KEYS: dict[str, str] = {
    "BIOGRAPHICAL SKETCH": "biographical_sketch",
    "DEDICATION": "dedication",
    "ACKNOWLEDGEMENTS": "acknowledgements",
    "TABLE OF CONTENTS": "table_of_contents",
    "LIST OF TABLES": "list_of_tables",
}


def _int_to_roman_lower(value: int) -> str:
    """Convert a positive integer to a lowercase Roman numeral string."""
    vals = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
    syms = ["m", "cm", "d", "cd", "c", "xc", "l", "xl", "x", "ix", "v", "iv", "i"]
    result: list[str] = []
    for v, s in zip(vals, syms):
        while value >= v:
            result.append(s)
            value -= v
    return "".join(result)


def _find_heading_first_page(
    heading_upper: str,
    front_matter_pages: set[int],
    pdf_doc: PdfDocument,
) -> int | None:
    """Return the lowest front-matter page number where heading text appears."""
    found: list[int] = []
    for page in pdf_doc.pages:
        if page.page_number not in front_matter_pages:
            continue
        for block in page.text_blocks:
            for line in block.lines:
                if normalize_heading_text(line.text).upper() == heading_upper:
                    found.append(page.page_number)
    return min(found) if found else None


def _best_roman_candidate(
    page_number: int,
    candidates: list[PageNumberCandidate],
    no_number_pages: set[int],
) -> PageNumberCandidate | None:
    """Return the best roman_lower candidate on a page, or None if absent/excluded."""
    if page_number in no_number_pages:
        return None
    page_cands = [
        c
        for c in candidates
        if c.page_number == page_number
        and c.number_style == "roman_lower"
        and c.value is not None
        and c.value <= _MAX_PLAUSIBLE_FRONTMATTER_ROMAN
    ]
    if not page_cands:
        return None
    # Prefer bottom-zone candidates; fall back to first match.
    bottom = [c for c in page_cands if c.location == "bottom"]
    return (bottom or page_cands)[0]


def check_pdf_roman_section_anchors(pdf_doc: PdfDocument) -> list[AuditFinding]:
    """Emit P037 warnings when front-matter section pages carry wrong Roman numerals.

    Conservative: emits nothing unless BIOGRAPHICAL SKETCH heading is detected.
    Checks five sections against NJIT template-fixed expected values.
    Does not duplicate P029 relative sequence checks or P028 regime checks.
    """
    if not pdf_doc.pages:
        return []

    regions, has_front = _classify_pages(pdf_doc)
    if not has_front:
        return []

    front_matter_pages = {pn for pn, r in regions.items() if r == "front_matter"}
    no_number_pages = _find_no_number_pages(pdf_doc)
    candidates = detect_page_number_candidates(pdf_doc)

    # Gate: no findings without a detectable BIOGRAPHICAL SKETCH heading.
    bio_page = _find_heading_first_page("BIOGRAPHICAL SKETCH", front_matter_pages, pdf_doc)
    if bio_page is None:
        return []

    findings: list[AuditFinding] = []

    for heading, expected_value in _SECTION_EXPECTED.items():
        section_page = (
            bio_page
            if heading == "BIOGRAPHICAL SKETCH"
            else _find_heading_first_page(heading, front_matter_pages, pdf_doc)
        )
        if section_page is None:
            continue  # Section absent; P025 covers missing structure.

        cand = _best_roman_candidate(section_page, candidates, no_number_pages)
        if cand is None:
            continue  # No confident candidate; skip conservatively.

        if cand.value == expected_value:
            continue  # Correct.

        section_key = _SECTION_KEYS[heading]
        expected_roman = _int_to_roman_lower(expected_value)
        issue_type = (
            "roman_bio_sketch_not_iv"
            if heading == "BIOGRAPHICAL SKETCH"
            else "roman_section_wrong_value"
        )

        findings.append(
            AuditFinding(
                rule_id="P037",
                severity=Severity.WARNING,
                page=section_page,
                message=(
                    f"Section '{heading}' on page {section_page} has Roman numeral "
                    f"'{cand.text}' (value={cand.value}); "
                    f"NJIT template expects {expected_roman} ({expected_value})."
                ),
                details={
                    "issue_type": issue_type,
                    "section_key": section_key,
                    "page_number": str(section_page),
                    "expected_roman": expected_roman,
                    "expected_value": str(expected_value),
                    "observed_roman": cand.text,
                    "observed_value": str(cand.value),
                    "observed_sequence": cand.text,
                    "expected_sequence": expected_roman,
                    "triage_tier": "check",
                    "confidence": "medium",
                },
            )
        )

    return findings
