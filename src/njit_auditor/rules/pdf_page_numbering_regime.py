"""Conservative PDF page-numbering regime check (P028).

NJIT requires:
  - Front-matter pages that display page numbers use lowercase Roman numerals.
  - Main-body pages use Arabic numerals.

Region detection:
  - Front-matter: pages before the first detected CHAPTER/APPENDIX heading.
  - Body: pages at and after the first detected CHAPTER/APPENDIX heading.
  - No-number pages (ABSTRACT, APPROVAL PAGE, title page) are excluded —
    P022 handles visible page numbers on those pages.

Q-rule basis: Q022, Q031, Q035, Q046, Q060.

Does NOT duplicate:
  - P013: global page-number candidate detection.
  - P019: sequence/style consistency across detected candidates.
  - P022: visible page numbers on no-number front-matter pages.
"""

from __future__ import annotations

import re

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument
from njit_auditor.rules.pdf_headings import find_named_frontmatter_headings
from njit_auditor.rules.pdf_page_numbers import detect_page_number_candidates

# Body chapter / appendix heading pattern — marks start of body region.
_CHAPTER_RE = re.compile(r"^(CHAPTER|APPENDIX)\s+[\dA-Z]+", re.IGNORECASE)

# Named headings that define no-number pages (P022 territory — skip in P028).
_NO_NUMBER_HEADINGS: frozenset[str] = frozenset(["ABSTRACT", "APPROVAL PAGE"])

# Require at least this many classified pages to run regime checks.
_MIN_CLASSIFIED_PAGES = 2


def _find_body_start_page(pdf_doc: PdfDocument) -> int | None:
    """Return the page number of the first body chapter/appendix heading, or None."""
    for page in pdf_doc.pages:
        for block in page.text_blocks:
            for line in block.lines:
                clean = " ".join(line.text.strip().split())
                if _CHAPTER_RE.match(clean):
                    return page.page_number
    return None


def _find_no_number_pages(pdf_doc: PdfDocument) -> set[int]:
    """Return page numbers explicitly identified as no-number pages (skip in P028).

    Only ABSTRACT and APPROVAL PAGE headings define no-number pages here.
    The title page (page 1) is not excluded because it typically has no page-number
    candidate; P022 handles any stray candidates on it.
    """
    no_num: set[int] = set()
    for match in find_named_frontmatter_headings(pdf_doc):
        if match.heading in _NO_NUMBER_HEADINGS:
            no_num.add(match.page_number)
    return no_num


def _classify_pages(
    pdf_doc: PdfDocument,
) -> tuple[dict[int, str], bool]:
    """Return (page → region) map and whether any front-matter was detected.

    Regions: "front_matter", "body", "ambiguous".
    """
    # Named front-matter heading pages.
    fm_heading_pages: dict[int, str] = {}
    for match in find_named_frontmatter_headings(pdf_doc):
        if match.page_number not in fm_heading_pages:
            fm_heading_pages[match.page_number] = match.heading
    has_front_matter = bool(fm_heading_pages)

    body_start = _find_body_start_page(pdf_doc)

    regions: dict[int, str] = {}
    for page in pdf_doc.pages:
        pn = page.page_number
        if body_start is not None:
            if pn < body_start:
                regions[pn] = "front_matter"
            else:
                regions[pn] = "body"
        elif pn in fm_heading_pages:
            regions[pn] = "front_matter"
        else:
            regions[pn] = "ambiguous"

    return regions, has_front_matter


def check_pdf_page_numbering_regime(pdf_doc: PdfDocument) -> list[AuditFinding]:
    """Emit P028 warnings when page-number style does not match expected region regime.

    Front-matter numbered pages → lowercase Roman numeral expected.
    Body pages → Arabic numeral expected.
    One finding per (page_number, issue_type).
    """
    if not pdf_doc.pages:
        return []

    regions, has_front_matter = _classify_pages(pdf_doc)

    # If nothing is classifiable, skip.
    classified = {pn for pn, r in regions.items() if r != "ambiguous"}
    if len(classified) < _MIN_CLASSIFIED_PAGES:
        return []

    no_number_pages = _find_no_number_pages(pdf_doc)
    candidates = detect_page_number_candidates(pdf_doc)

    # Deduplicate: one finding per (page, issue_type).
    seen: set[tuple[int, str]] = set()
    findings: list[AuditFinding] = []

    for candidate in candidates:
        pn = candidate.page_number
        if pn in no_number_pages:
            continue  # P022 handles no-number pages
        region = regions.get(pn, "ambiguous")
        if region == "ambiguous":
            continue

        issue_type: str | None = None
        expected: str | None = None
        q_rule: str = ""

        if region == "front_matter":
            if candidate.number_style == "arabic":
                issue_type = "arabic_number_on_frontmatter_page"
                expected = "lowercase Roman numeral (i, ii, iii, …)"
                q_rule = "Q022"
            elif candidate.number_style == "roman_upper":
                issue_type = "uppercase_roman_on_frontmatter_page"
                expected = "lowercase Roman numeral (not uppercase)"
                q_rule = "Q022"
            # roman_lower is correct — no warning

        elif region == "body":
            if candidate.number_style in ("roman_lower", "roman_upper"):
                issue_type = "roman_number_on_body_page"
                expected = "Arabic numeral (1, 2, 3, …)"
                q_rule = ""

        if issue_type is None:
            continue
        key = (pn, issue_type)
        if key in seen:
            continue
        seen.add(key)

        findings.append(
            AuditFinding(
                rule_id="P028",
                severity=Severity.WARNING,
                page=pn,
                message=(
                    f"Page {pn} ({region}) has a page-number candidate "
                    f"'{candidate.text}' ({candidate.number_style}) that does not "
                    f"match the expected regime for that region."
                ),
                details={
                    "page_number": str(pn),
                    "issue_type": issue_type,
                    "candidate_text": candidate.text,
                    "candidate_style": candidate.number_style,
                    "page_region": region,
                    "expected_or_reason": expected or "",
                    "source_q_rule_id": q_rule,
                    "confidence": "medium",
                    "suggested_fix": (
                        f"Use {expected} for {region.replace('_', ' ')} pages."
                        if expected
                        else ""
                    ),
                },
            )
        )

    return findings
