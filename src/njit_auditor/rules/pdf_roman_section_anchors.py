"""Conservative front-matter section-anchored Roman numeral checks (P037)."""

from __future__ import annotations

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument, format_bbox_detail
from njit_auditor.rules.pdf_headings import normalize_heading_text
from njit_auditor.rules.pdf_page_numbering_regime import (
    _classify_pages,
    _find_no_number_pages,
)
from njit_auditor.rules.pdf_page_numbers import (
    PageNumberCandidate,
    detect_page_number_candidates,
    is_plausible_page_number_candidate,
)
from njit_auditor.rules.pdf_roman_sequence import _MAX_PLAUSIBLE_FRONTMATTER_ROMAN

# NJIT template: Biographical Sketch should begin on Roman numeral iv when numbered.
_BIO_SKETCH_EXPECTED = 4

_SECTION_KEYS: dict[str, str] = {
    "BIOGRAPHICAL SKETCH": "biographical_sketch",
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
        and is_plausible_page_number_candidate(c)
        and c.number_style == "roman_lower"
        and c.value is not None
        and c.value <= _MAX_PLAUSIBLE_FRONTMATTER_ROMAN
    ]
    if not page_cands:
        return None
    bottom = [c for c in page_cands if c.location == "bottom"]
    return (bottom or page_cands)[0]


def check_pdf_roman_section_anchors(pdf_doc: PdfDocument) -> list[AuditFinding]:
    """Emit P037 warnings for the Biographical Sketch Roman anchor only.

    Front-matter sequence continuity is handled by P029. Other section headings
    may legitimately fall on later Roman numerals when optional front-matter pages
    or multi-page lists shift the actual numbering.
    """
    if not pdf_doc.pages:
        return []

    regions, has_front = _classify_pages(pdf_doc)
    if not has_front:
        return []

    front_matter_pages = {pn for pn, r in regions.items() if r == "front_matter"}
    no_number_pages = _find_no_number_pages(pdf_doc)
    candidates = detect_page_number_candidates(pdf_doc)

    bio_page = _find_heading_first_page("BIOGRAPHICAL SKETCH", front_matter_pages, pdf_doc)
    if bio_page is None:
        return []

    cand = _best_roman_candidate(bio_page, candidates, no_number_pages)
    if cand is None or cand.value == _BIO_SKETCH_EXPECTED:
        return []

    expected_roman = _int_to_roman_lower(_BIO_SKETCH_EXPECTED)
    details = {
        "issue_type": "roman_bio_sketch_not_iv",
        "section_key": _SECTION_KEYS["BIOGRAPHICAL SKETCH"],
        "page_number": str(bio_page),
        "expected_roman": expected_roman,
        "expected_value": str(_BIO_SKETCH_EXPECTED),
        "observed_roman": cand.text,
        "observed_value": str(cand.value),
        "observed_sequence": cand.text,
        "expected_sequence": expected_roman,
        "triage_tier": "check",
        "confidence": "medium",
    }
    if cand.bbox is not None:
        details["bbox"] = format_bbox_detail(cand.bbox)

    return [
        AuditFinding(
            rule_id="P037",
            severity=Severity.WARNING,
            page=bio_page,
            message=(
                f"Section 'BIOGRAPHICAL SKETCH' on page {bio_page} has Roman numeral "
                f"'{cand.text}' (value={cand.value}); "
                f"NJIT template expects {expected_roman} ({_BIO_SKETCH_EXPECTED})."
            ),
            details=details,
        )
    ]
