"""Conservative front-matter Roman numeral sequence checks (P029)."""

from __future__ import annotations

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument, format_bbox_detail
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


def _int_to_roman_lower(value: int) -> str:
    vals = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
    syms = ["m", "cm", "d", "cd", "c", "xc", "l", "xl", "x", "ix", "v", "iv", "i"]
    result: list[str] = []
    for amount, symbol in zip(vals, syms):
        while value >= amount:
            result.append(symbol)
            value -= amount
    return "".join(result)


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
        # Unreadable/missing folios still occupy physical numbered pages. Do not
        # invent a gap merely because an intermediate numeral was not extracted.
        # Explicit no-number pages remain exempt, as in the historical policy.
        numbered_step = sum(
            p not in no_number_pages for p in range(prev.page_number + 1, cand.page_number + 1)
        )
        expected = (prev.value or 0) + numbered_step
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
                "pdf_page": str(cand.page_number),
                "issue_type": issue_type,
                "candidate_text": cand.text,
                "candidate_value": str(cand.value),
                "previous_value": str(prev.value),
                "expected_value": str(expected),
                "observed_sequence": cand.text,
                "expected_sequence": _int_to_roman_lower(expected),
                "document_page_label": cand.text,
                "document_page_label_style": cand.number_style,
                "document_page_label_confidence": "medium",
                "page_region": "front_matter",
                "confidence": confidence,
            }
            if cand.bbox is not None:
                details["bbox"] = format_bbox_detail(cand.bbox)
                details["document_page_label_bbox"] = format_bbox_detail(cand.bbox)
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
