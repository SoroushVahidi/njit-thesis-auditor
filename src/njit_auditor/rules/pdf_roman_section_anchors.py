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
)
from njit_auditor.rules.pdf_roman_sequence import _MAX_PLAUSIBLE_FRONTMATTER_ROMAN

# NJIT template's documented default Roman numeral sequence, by section
# heading, assuming every section takes exactly one physical page. Only the
# "BIOGRAPHICAL SKETCH" value (4/iv) is used as a check target directly --
# it is the one true anchor, since nothing numbered precedes it. The later
# values document the template's intended *default* ordering and give
# check_pdf_roman_section_anchors() its heading iteration order, but the
# actual expected value checked for each of them is computed dynamically by
# _chained_expected_value() from whatever numeral is actually on the
# preceding page, since any of these sections may span more than one page.
# DEDICATION is optional: if the heading is absent, it is skipped entirely
# (a dedication page may exist without a detectable heading; its numeral is
# simply absorbed into whatever the next detected section reads back).
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

# Alternate spellings this codebase already recognizes for the same section
# elsewhere (e.g. pdf_frontmatter_structure.py's and pdf_title_consistency.py's
# own _NAMED_HEADINGS sets both list "ACKNOWLEDGEMENTS" and "ACKNOWLEDGMENTS").
# Several Ester dissertations use the American spelling.
_HEADING_SPELLING_VARIANTS: dict[str, tuple[str, ...]] = {
    "ACKNOWLEDGEMENTS": ("ACKNOWLEDGEMENTS", "ACKNOWLEDGMENTS"),
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


def _acceptable_heading_forms(heading_upper: str) -> frozenset[str]:
    """Return the space-stripped forms that count as a match for *heading_upper*.

    Space-stripping absorbs the common PDF-extraction artifact where adjacent
    words lose their separating space in the text layer (e.g. observed on
    several Ester dissertations' Biographical Sketch heading, extracted as
    "BIOGRAPHICALSKETCH") -- the same class of artifact this codebase already
    works around elsewhere (pdf_headings.py's mashed CHAPTER/APPENDIX regex,
    pdf_frontmatter_structure.py's space-stripped degree/institution fallback).
    """
    variants = _HEADING_SPELLING_VARIANTS.get(heading_upper, (heading_upper,))
    return frozenset(variant.replace(" ", "") for variant in variants)


def _find_heading_first_page(
    heading_upper: str,
    front_matter_pages: set[int],
    pdf_doc: PdfDocument,
) -> int | None:
    """Return the lowest front-matter page number where heading text appears."""
    acceptable = _acceptable_heading_forms(heading_upper)
    found: list[int] = []
    for page in pdf_doc.pages:
        if page.page_number not in front_matter_pages:
            continue
        for block in page.text_blocks:
            for line in block.lines:
                normalized = normalize_heading_text(line.text).upper().replace(" ", "")
                if normalized in acceptable:
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


def _chained_expected_value(
    section_page: int,
    earliest_allowed_page: int,
    candidates: list[PageNumberCandidate],
    no_number_pages: set[int],
) -> int | None:
    """Return a section's expected Roman value from the numeral on the page
    immediately before it, or None if not confidently known.

    Every NJIT front-matter section after Biographical Sketch (Dedication,
    Acknowledgements, Table of Contents, List of Tables) is checked against
    the numeral that should immediately follow whatever the PREVIOUS section
    actually ended on -- not a fixed template slot -- because any of those
    sections may legitimately span more than one physical page (this rule
    already treated that as expected for List of Tables after a multi-page
    "(Continued)" Table of Contents run; the identical situation is just as
    real for a multi-page Acknowledgements or Biographical Sketch section,
    observed directly in this corpus). Hard-coding each section's slot as a
    fixed offset from Biographical Sketch assumes every earlier section took
    exactly one page, which is not guaranteed and not itself an NJIT
    requirement -- this rule's job is an unbroken Roman sequence, not a page
    count. *earliest_allowed_page* guards against reading a numeral from
    before the true anchor (Biographical Sketch) in some degenerate case.
    If the preceding page carries no confident numeral, the sequence cannot
    be verified here, so return None rather than assert a guessed value.
    """
    preceding_page = section_page - 1
    if preceding_page < earliest_allowed_page:
        return None
    preceding_cand = _best_roman_candidate(preceding_page, candidates, no_number_pages)
    if preceding_cand is None or preceding_cand.value is None:
        return None
    return preceding_cand.value + 1


def check_pdf_roman_section_anchors(pdf_doc: PdfDocument) -> list[AuditFinding]:
    """Emit P037 warnings when front-matter section pages carry wrong Roman numerals.

    Conservative: emits nothing unless BIOGRAPHICAL SKETCH heading is detected.
    Biographical Sketch is anchored at the NJIT template's fixed "iv" (Q022) --
    it is always the first numbered front-matter section, so nothing before it
    can shift its value. Every later section (Dedication, Acknowledgements,
    Table of Contents, List of Tables) is instead checked against the Roman
    numeral that should immediately follow the actual numeral printed on the
    page before it (Q060's "continues the sequence" logic, generalized from
    List of Tables to every chained section): any of those sections may span
    more than one physical page, which shifts every later section's slot away
    from the template's fixed single-page assumption.
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

    for heading in _SECTION_EXPECTED:
        section_page = (
            bio_page
            if heading == "BIOGRAPHICAL SKETCH"
            else _find_heading_first_page(heading, front_matter_pages, pdf_doc)
        )
        if section_page is None:
            continue  # Section absent; P025 covers missing structure.

        expected_value: int | None
        if heading == "BIOGRAPHICAL SKETCH":
            expected_value = _SECTION_EXPECTED[heading]
        else:
            expected_value = _chained_expected_value(
                section_page, bio_page, candidates, no_number_pages
            )
            if expected_value is None:
                continue  # Preceding sequence not confidently known; do not guess.

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

        details = {
            "issue_type": issue_type,
            "section_key": section_key,
            "page_number": str(section_page),
            "pdf_page": str(section_page),
            "expected_roman": expected_roman,
            "expected_value": str(expected_value),
            "observed_roman": cand.text,
            "observed_value": str(cand.value),
            "observed_sequence": cand.text,
            "expected_sequence": expected_roman,
            "document_page_label": cand.text,
            "document_page_label_style": cand.number_style,
            "document_page_label_confidence": "medium",
            "triage_tier": "check",
            "confidence": "medium",
        }
        if cand.bbox is not None:
            details["bbox"] = format_bbox_detail(cand.bbox)
            details["document_page_label_bbox"] = format_bbox_detail(cand.bbox)

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
                details=details,
            )
        )

    return findings
