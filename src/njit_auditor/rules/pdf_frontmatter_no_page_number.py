"""Heuristic check for visible page numbers on no-number front-matter pages (P022).

NJIT guidelines require no visible page number on:
  - Abstract page       (Q001)
  - Title page          (Q008)
  - Approval page       (Q014)
  - Copyright page      (Q012, if reliably detected)

Reuses P013-style zone and candidate detection logic but targets specific named pages only.
Does NOT duplicate P013 (global candidate detection) or P019 (sequence/style checks).

Sources:
  - Thesis and Dissertation Formatting Guidelines (WIP).docx
  - Front Matter Pages Lorem Ipsum.pdf
"""

from __future__ import annotations

import re

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument, PdfPage
from njit_auditor.rules.pdf_headings import find_named_frontmatter_headings

# P013-compatible candidate pattern: isolated numeric or Roman numeral token.
_PAGE_NUM_RE = re.compile(r"^\s*[\[(]?(?:\d+|[ivxlcdm]+)[\])]?[.]?\s*$", re.IGNORECASE)
# Four-digit years 1900–2099 are suppressed on the title page to avoid false positives.
_YEAR_RE = re.compile(r"^(19|20)\d{2}$")
# Copyright page signal: word "copyright", © symbol, or "(c)".
_COPYRIGHT_RE = re.compile(r"\bcopyright\b|©|\(c\)", re.IGNORECASE)

_TOP_ZONE_RATIO = 0.15
_COPYRIGHT_SCAN_PAGES = 4
_MIN_DOC_PAGES_FOR_TITLE_CHECK = 3


def _in_top_or_bottom_zone(y0: float, y1: float, page_height: float) -> bool:
    top_limit = page_height * _TOP_ZONE_RATIO
    bottom_limit = page_height * (1.0 - _TOP_ZONE_RATIO)
    return y1 <= top_limit or y0 >= bottom_limit


def _candidates_on_page(page: PdfPage, suppress_years: bool = False) -> list[dict[str, str]]:
    """Return page-number-like candidates in the top/bottom margin zone of a single page."""
    candidates: list[dict[str, str]] = []
    for block in page.text_blocks:
        if not _in_top_or_bottom_zone(block.bbox.y0, block.bbox.y1, page.height):
            continue
        for line in block.lines:
            clean = " ".join(line.text.strip().split())
            if not clean or not _PAGE_NUM_RE.match(clean):
                continue
            normalized = clean.strip().strip("[]()").rstrip(".")
            if suppress_years and _YEAR_RE.match(normalized):
                continue
            location = "top" if line.bbox.y1 <= page.height * _TOP_ZONE_RATIO else "bottom"
            candidates.append({"text": clean, "location": location})
    return candidates


def _find_copyright_page_number(pdf_doc: PdfDocument) -> int | None:
    """Return 1-based page number of a copyright page if clearly detected in early pages."""
    for page in pdf_doc.pages[:_COPYRIGHT_SCAN_PAGES]:
        full_text = " ".join(
            line.text for block in page.text_blocks for line in block.lines
        )
        if _COPYRIGHT_RE.search(full_text):
            return page.page_number
    return None


def check_pdf_frontmatter_no_page_number(pdf_doc: PdfDocument) -> list[AuditFinding]:
    """Emit P022 warnings when visible page-number candidates appear on no-number pages."""

    if not pdf_doc.pages:
        return []

    headings = find_named_frontmatter_headings(pdf_doc)
    heading_pages: dict[str, int] = {}
    for match in headings:
        if match.heading not in heading_pages:
            heading_pages[match.heading] = match.page_number

    # Build the list of (page_number, page_type, q_rule_id, suppress_years).
    no_number_targets: list[tuple[int, str, str, bool]] = []

    if "ABSTRACT" in heading_pages:
        no_number_targets.append((heading_pages["ABSTRACT"], "abstract", "Q001", False))

    if "APPROVAL PAGE" in heading_pages:
        no_number_targets.append((heading_pages["APPROVAL PAGE"], "approval_page", "Q014", False))

    # Title page heuristic: page 1 when the document has front-matter headings.
    if len(pdf_doc.pages) >= _MIN_DOC_PAGES_FOR_TITLE_CHECK and heading_pages:
        page1_num = pdf_doc.pages[0].page_number
        already_claimed = {pn for pn, _, _, _ in no_number_targets}
        if page1_num not in already_claimed:
            no_number_targets.append((page1_num, "title_page", "Q008", True))

    # Copyright page: conservative — only when clearly identified in early pages.
    copyright_pnum = _find_copyright_page_number(pdf_doc)
    if copyright_pnum is not None:
        already_claimed = {pn for pn, _, _, _ in no_number_targets}
        if copyright_pnum not in already_claimed:
            no_number_targets.append((copyright_pnum, "copyright_page", "Q012", False))

    if not no_number_targets:
        return []

    pages_by_number = {p.page_number: p for p in pdf_doc.pages}
    findings: list[AuditFinding] = []
    seen: set[int] = set()

    for page_num, page_type, q_rule_id, suppress_years in no_number_targets:
        if page_num in seen:
            continue
        page = pages_by_number.get(page_num)
        if page is None:
            continue
        candidates = _candidates_on_page(page, suppress_years=suppress_years)
        if not candidates:
            continue
        seen.add(page_num)
        first = candidates[0]
        label = page_type.replace("_", " ")
        findings.append(
            AuditFinding(
                rule_id="P022",
                severity=Severity.WARNING,
                page=page_num,
                message=(
                    f"Possible visible page number '{first['text']}' detected on "
                    f"{label} page (NJIT requires no visible page number here)."
                ),
                details={
                    "page_number": str(page_num),
                    "page_type": page_type,
                    "issue_type": "visible_page_number_on_no_number_page",
                    "candidate_text": first["text"],
                    "candidate_position": first["location"],
                    "observed_location": first["location"],
                    "candidate_count": str(len(candidates)),
                    "source_q_rule_id": q_rule_id,
                    "confidence": "medium",
                    "suggested_fix": (
                        f"Remove the visible page number from the {label} page."
                    ),
                },
            )
        )

    return findings
