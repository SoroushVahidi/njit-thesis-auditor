"""Conservative body-page appendix heading label checks (P063).

Heuristic PDF coverage for Q058/Q059 (body-page extension):
  - Q058: If the document has only one appendix, its body heading must be
    "APPENDIX" followed by a title (no letter suffix).
  - Q059: If the document has multiple appendices, each body heading must be
    "APPENDIX <letter>" (e.g. APPENDIX A, APPENDIX B, ...).

Guideline source (Self-Assessment Sheet, page 4):
  "If there is one appendix it is called APPENDIX; if there are multiple
  appendices, they are named APPENDIX A, B, C + the appendix title.
  Appendices titles are in all caps both in the text and in the TOC."

Companion to P042 (TOC-side appendix format check, Q058/Q059). P042 checks
the Table of Contents entries; P063 checks the body-page headings.

Conservative gates:
  - Requires at least one body-page APPENDIX-like heading to fire at all.
  - Skips documents where no body/chapter region is detected (image-only or
    front-matter-only PDFs).
  - A heading qualifies only if it:
      * Starts with APPENDIX (case-insensitive) at the start of the line
      * Appears after the body start page (past front-matter)
  - Single-appendix case: the heading must be exactly "APPENDIX" with no
    trailing letter (A–Z), OR must be "APPENDIX" optionally followed by a
    title that is NOT a single letter.  A bare letter suffix triggers a
    warning: single-appendix docs should NOT use "APPENDIX A".
  - Multi-appendix case: each heading must use "APPENDIX <letter>" format.
    Missing letter suffix triggers a warning.
  - Letter sequence is checked for continuity from A: gaps or repeats are
    flagged (e.g. APPENDIX A, APPENDIX C skipping B).
  - Issue types:
      * "single_appendix_uses_letter_label" — one appendix found but heading
        uses APPENDIX A/B/... format (not required per Q058)
      * "multiple_appendix_missing_letter" — multiple appendices found but
        at least one heading lacks a letter identifier (required per Q059)
      * "appendix_letter_sequence_gap" — letter identifiers are non-
        consecutive (e.g., A, C with no B)
      * "appendix_letter_sequence_repeat" — same letter used on more than one
        appendix heading

Privacy: findings contain only structural metadata — heading count, letter
labels (A, B, C...) as structural identifiers, page number. No body text,
section titles, dissertation content, or author names are included.

Does NOT duplicate:
  - P042: TOC appendix entry format (Q058/Q059 TOC side).
  - P038: required front-matter heading presence.
  - P014: front-matter named heading layout/style.
"""

from __future__ import annotations

import re

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import BBox, PdfDocument, format_bbox_detail

# Matches a line starting with APPENDIX (case-insensitive), possibly followed by
# a letter identifier and/or title text.
_APPENDIX_LINE_RE = re.compile(r"^APPENDIX\b", re.IGNORECASE)

# Matches APPENDIX immediately followed by a single uppercase letter and
# word boundary (e.g. "APPENDIX A" or "APPENDIX A Title Text").
_APPENDIX_WITH_LETTER_RE = re.compile(r"^APPENDIX\s+([A-Z])\b", re.IGNORECASE)

# Body chapter/appendix heading pattern — marks start of body region.
# Re-uses the same pattern as pdf_page_numbering_regime._CHAPTER_RE.
_CHAPTER_APPENDIX_RE = re.compile(r"^(CHAPTER|APPENDIX)\s+[\dA-Z]+", re.IGNORECASE)

# Minimum number of words that the heading line must have beyond "APPENDIX [letter]"
# to be considered a meaningful appendix heading (not a wrapped sub-heading or label).
_MIN_LINE_LEN = 3  # characters

_RULE_ID = "P063"
_SOURCE_Q_RULE_IDS = ("Q058", "Q059")


def _find_body_start_page(pdf_doc: PdfDocument) -> int | None:
    """Return the first page number where a CHAPTER or APPENDIX body heading is found."""
    for page in pdf_doc.pages:
        for block in page.text_blocks:
            for line in block.lines:
                clean = " ".join(line.text.strip().split())
                if _CHAPTER_APPENDIX_RE.match(clean):
                    return page.page_number
    return None


def _collect_appendix_headings(
    pdf_doc: PdfDocument, body_start: int
) -> list[tuple[int, str, BBox]]:
    """Return (page_number, normalized_heading_text, bbox) for body-page APPENDIX headings.

    Only lines starting with APPENDIX (case-insensitive), on pages at or after
    body_start, with length >= _MIN_LINE_LEN, are collected.
    Duplicate headings on the same page are skipped (multi-line wrapped headings).
    """
    seen_pages: set[int] = set()
    results: list[tuple[int, str, BBox]] = []
    for page in pdf_doc.pages:
        if page.page_number < body_start:
            continue
        if page.page_number in seen_pages:
            continue
        for block in page.text_blocks:
            for line in block.lines:
                clean = " ".join(line.text.strip().split())
                if len(clean) < _MIN_LINE_LEN:
                    continue
                if _APPENDIX_LINE_RE.match(clean):
                    if page.page_number not in seen_pages:
                        seen_pages.add(page.page_number)
                        results.append((page.page_number, clean.upper(), line.bbox))
                    break  # Only first matching line per page
    return results


def _extract_letter(heading: str) -> str | None:
    """Return the letter suffix from an APPENDIX heading, or None if absent."""
    m = _APPENDIX_WITH_LETTER_RE.match(heading)
    if m:
        return m.group(1).upper()
    return None


def check_pdf_appendix_body_headings(pdf_doc: PdfDocument) -> list[AuditFinding]:
    """Emit P063 warnings for body-page appendix headings with incorrect label format.

    Conservative gates:
    - No findings if no body region is detected (image-only / front-matter-only PDFs).
    - No findings if no APPENDIX headings are found in the body region.
    - Single appendix: warn if heading uses a letter suffix (APPENDIX A) per Q058.
    - Multiple appendices: warn if any heading lacks a letter suffix per Q059.
    - Warn if letter identifiers are non-consecutive or repeated.
    """
    if not pdf_doc.pages:
        return []

    body_start = _find_body_start_page(pdf_doc)
    if body_start is None:
        # No body heading detected → likely front-matter only or image PDF; skip.
        return []

    headings = _collect_appendix_headings(pdf_doc, body_start)
    if not headings:
        return []

    findings: list[AuditFinding] = []
    n = len(headings)

    if n == 1:
        page_num, heading, bbox = headings[0]
        letter = _extract_letter(heading)
        if letter is not None:
            # Single appendix uses a letter suffix — not required per Q058.
            findings.append(
                AuditFinding(
                    rule_id=_RULE_ID,
                    severity=Severity.WARNING,
                    page=page_num,
                    message=(
                        f"Single appendix body heading on page {page_num} uses a letter "
                        f"identifier ('{letter}'). NJIT guidelines (Q058) require a single "
                        f"appendix to be labeled APPENDIX without a letter suffix."
                    ),
                    details={
                        "issue_type": "single_appendix_uses_letter_label",
                        "page": str(page_num),
                        "appendix_count": "1",
                        "letter_found": letter,
                        "triage_tier": "medium",
                        "source_q_rule_id": "Q058",
                        "bbox": format_bbox_detail(bbox),
                    },
                )
            )
    else:
        # Multiple appendices: each must use APPENDIX <letter> format.
        letters: list[str | None] = []
        for page_num, heading, bbox in headings:
            letter = _extract_letter(heading)
            letters.append(letter)
            if letter is None:
                findings.append(
                    AuditFinding(
                        rule_id=_RULE_ID,
                        severity=Severity.WARNING,
                        page=page_num,
                        message=(
                            f"Multiple-appendix body heading on page {page_num} does not "
                            f"include a letter identifier. NJIT guidelines (Q059) require "
                            f"multiple appendices to be labeled APPENDIX A, APPENDIX B, etc."
                        ),
                        details={
                            "issue_type": "multiple_appendix_missing_letter",
                            "page": str(page_num),
                            "appendix_count": str(n),
                            "triage_tier": "medium",
                            "source_q_rule_id": "Q059",
                            "bbox": format_bbox_detail(bbox),
                        },
                    )
                )

        # Check letter sequence only when all headings have letters.
        resolved = [ltr for ltr in letters if ltr is not None]
        if len(resolved) == n:
            # Check for repeated letters.
            seen_letters: set[str] = set()
            for idx, (page_num, _, bbox) in enumerate(headings):
                letter = resolved[idx]
                if letter in seen_letters:
                    findings.append(
                        AuditFinding(
                            rule_id=_RULE_ID,
                            severity=Severity.WARNING,
                            page=page_num,
                            message=(
                                f"Appendix body heading on page {page_num} repeats the "
                                f"letter identifier '{letter}'. Each appendix must use a "
                                f"unique letter (A, B, C ...) per NJIT guidelines (Q059)."
                            ),
                            details={
                                "issue_type": "appendix_letter_sequence_repeat",
                                "page": str(page_num),
                                "appendix_count": str(n),
                                "letter_repeated": letter,
                                "triage_tier": "medium",
                                "source_q_rule_id": "Q059",
                                "bbox": format_bbox_detail(bbox),
                            },
                        )
                    )
                seen_letters.add(letter)

            # Check for non-consecutive sequence (gaps).
            # Expected: A, B, C, D, ... in order.
            if not findings:  # Only check gaps when no repeat found.
                expected_letters = [chr(ord("A") + i) for i in range(n)]
                for idx, (page_num, _, bbox) in enumerate(headings):
                    actual = resolved[idx]
                    expected = expected_letters[idx]
                    if actual != expected:
                        findings.append(
                            AuditFinding(
                                rule_id=_RULE_ID,
                                severity=Severity.WARNING,
                                page=page_num,
                                message=(
                                    f"Appendix body heading letter sequence is non-consecutive "
                                    f"on page {page_num}: expected '{expected}' at position "
                                    f"{idx + 1} but found '{actual}'. NJIT guidelines (Q059) "
                                    f"require consecutive letter labels (A, B, C ...)."
                                ),
                                details={
                                    "issue_type": "appendix_letter_sequence_gap",
                                    "page": str(page_num),
                                    "appendix_count": str(n),
                                    "expected_letter": expected,
                                    "found_letter": actual,
                                    "sequence_position": str(idx + 1),
                                    "triage_tier": "medium",
                                    "source_q_rule_id": "Q059",
                                    "bbox": format_bbox_detail(bbox),
                                },
                            )
                        )
                        break  # Report only the first gap.

    return findings
