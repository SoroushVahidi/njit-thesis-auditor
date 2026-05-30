"""Conservative front-matter Roman numeral sequence checks (P029)."""

from __future__ import annotations

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument
from njit_auditor.rules.pdf_page_numbering_regime import (
    _classify_pages,
    _find_no_number_pages,
)
from njit_auditor.rules.pdf_page_numbers import (
    detect_page_number_candidates,
)

# Front-matter Roman numeral pages never legitimately exceed this value.
# Candidates above this threshold (e.g. "m"=1000, "cm"=900) are TOC entries
# or other noise, not page numbers, and are excluded from sequence checks.
_MAX_PLAUSIBLE_FRONTMATTER_ROMAN = 50


def check_pdf_roman_sequence(pdf_doc: PdfDocument) -> list[AuditFinding]:
    """Emit P029 warnings for front-matter lowercase Roman numeral ordering.

    Conservative heuristics:
    - Only considers candidates classified as roman_lower and within front_matter region.
    - Requires at least 2 roman candidates before emitting sequence checks.
    - Flags repeats, decreases, and obvious gaps between consecutive visible candidates.
    - Skips pages explicitly classified as no-number (title/abstract/approval/copyright).
    - Returns one finding per (page, issue_type).
    """
    if not pdf_doc.pages:
        return []

    regions, has_front = _classify_pages(pdf_doc)
    if not has_front:
        return []

    no_number_pages = _find_no_number_pages(pdf_doc)
    candidates = detect_page_number_candidates(pdf_doc)

    fm_candidates = [
        c
        for c in candidates
        if regions.get(c.page_number) == "front_matter"
        and c.number_style == "roman_lower"
        and c.value is not None
        and c.page_number not in no_number_pages
        and c.value <= _MAX_PLAUSIBLE_FRONTMATTER_ROMAN
    ]

    # Require at least two visible roman candidates to check for continuity.
    if len(fm_candidates) < 2:
        return []

    fm_candidates_sorted = sorted(fm_candidates, key=lambda c: c.page_number)

    findings: list[AuditFinding] = []
    seen: set = set()

    prev = fm_candidates_sorted[0]
    for cand in fm_candidates_sorted[1:]:
        page_step = cand.page_number - prev.page_number
        if page_step <= 0:
            prev = cand
            continue
        # Expect visible roman numerals to increase by one across consecutive
        # visible numbered front-matter pages. This flags non-consecutive visible
        # numerals (i, iii) as a gap. Skipped no-number pages are handled by
        # excluding those pages from candidate lists; if an intermediate page is
        # a recognized no-number page, a following visible numeral that equals
        # previous+1 will still pass.
        expected = (prev.value or 0) + 1
        issue_type = None
        confidence = "medium"

        if cand.value is not None and prev.value is not None and cand.value == prev.value:
            issue_type = "roman_sequence_repeat"
            message = (
                f"Repeated Roman numeral '{cand.text}' on page {cand.page_number} "
                f"(previous page {prev.page_number} = {prev.text})."
            )
        elif cand.value is not None and prev.value is not None and cand.value < prev.value:
            issue_type = "roman_sequence_decrease"
            message = (
                f"Roman numeral decreased to '{cand.text}' on page {cand.page_number} "
                f"(previous {prev.page_number} = {prev.text})."
            )
        elif cand.value is not None and cand.value != expected:
            issue_type = "roman_sequence_gap"
            message = (
                f"Roman numeral on page {cand.page_number} is '{cand.text}' (value={cand.value}), "
                f"expected {expected} based on previous visible numeral {prev.text} "
                f"on page {prev.page_number}."
            )
            # Be conservative: lower confidence for large page gaps
            if page_step > 2:
                confidence = "low"

        if issue_type is not None:
            key = (cand.page_number, issue_type)
            if key in seen:
                prev = cand
                continue
            seen.add(key)
            details = {
                "page_number": str(cand.page_number),
                "issue_type": issue_type,
                "candidate_text": cand.text,
                "candidate_value": str(cand.value),
                "previous_value": str(prev.value),
                "expected_value": str(expected),
                "page_region": "front_matter",
                "confidence": confidence,
            }
            findings.append(
                AuditFinding(
                    rule_id="P029",
                    severity=Severity.WARNING,
                    page=cand.page_number,
                    message=message,
                    details=details,
                )
            )
        prev = cand

    return findings
