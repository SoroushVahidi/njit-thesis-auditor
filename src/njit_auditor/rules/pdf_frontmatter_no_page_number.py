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

from njit_auditor.digital_commons_wrapper import (
    detect_digital_commons_wrapper_pages,
    without_wrapper_pages,
)
from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument, PdfPage, format_bbox_detail
from njit_auditor.rules.pdf_headings import (
    find_body_start_page,
    find_named_frontmatter_headings,
)

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
            candidates.append(
                {"text": clean, "location": location, "bbox": format_bbox_detail(line.bbox)}
            )
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


def frontmatter_no_number_roles(pdf_doc: PdfDocument) -> dict[int, tuple[str, str]]:
    """Identify unnumbered sections, including a bounded Abstract continuation.

    The Abstract is outside the Roman count. Title/copyright/approval pages
    have hidden folios; the first displayed section is checked by P037's Bio
    Sketch anchor. Never use a stray Abstract folio to establish that sequence.
    A submission statement distinguishes a later title page from Abstract prose.
    """
    working_doc = without_wrapper_pages(pdf_doc, detect_digital_commons_wrapper_pages(pdf_doc))
    headings = find_named_frontmatter_headings(working_doc)
    named = {h.page_number: h.heading for h in headings}
    # Exact compact headings handle extraction without inter-word spaces and
    # optional sections that the style detector does not inventory.
    for page in working_doc.pages:
        for block in page.text_blocks:
            for line in block.lines:
                compact = re.sub(r"\s+", "", line.text).upper()
                if line.bbox.y0 < page.height * _TOP_ZONE_RATIO and compact in {
                    "BIOGRAPHICALSKETCH", "DEDICATION", "ACKNOWLEDGMENTS",
                    "ACKNOWLEDGEMENTS", "LISTOFSYMBOLS",
                }:
                    named.setdefault(page.page_number, compact)
    body_start = find_body_start_page(working_doc)
    roles: dict[int, tuple[str, str]] = {
        pn: ("abstract", "Q001") if name == "ABSTRACT" else ("approval_page", "Q014")
        for pn, name in named.items()
        if name in {"ABSTRACT", "APPROVAL PAGE"} and (body_start is None or pn < body_start)
    }
    boundaries = set(named)
    if body_start is not None:
        boundaries.add(body_start)
    first_numbered = min(
        (pn for pn, name in named.items() if name not in {"ABSTRACT", "APPROVAL PAGE"}),
        default=body_start or (working_doc.pages[-1].page_number + 1 if working_doc.pages else 1),
    )
    for page in working_doc.pages:
        pn = page.page_number
        if pn >= first_numbered:
            break
        if named.get(pn) == "ABSTRACT":
            roles[pn] = ("abstract", "Q001")
        elif named.get(pn) == "APPROVAL PAGE":
            roles[pn] = ("approval_page", "Q014")
        else:
            text = " ".join(line.text for block in page.text_blocks for line in block.lines)
            compact = re.sub(r"\s+", "", text).casefold()
            if ("submitted" in compact and "partialfulfillment" in compact
                    and ("newjerseyinstituteoftechnology" in compact or "njit" in compact)):
                roles[pn] = ("title_page", "Q008")
                boundaries.add(pn)
            elif _COPYRIGHT_RE.search(text):
                roles[pn] = ("copyright_page", "Q012")
                boundaries.add(pn)
    # Retain the legacy first-page fallback only for an unnamed opening page.
    if working_doc.pages and len(working_doc.pages) >= _MIN_DOC_PAGES_FOR_TITLE_CHECK and named:
        first = working_doc.pages[0].page_number
        if first not in named and first not in roles:
            roles[first] = ("title_page", "Q008")
            boundaries.add(first)
    for heading in headings:
        if heading.heading != "ABSTRACT" or heading.page_number >= first_numbered:
            continue
        end = min((pn for pn in boundaries if pn > heading.page_number), default=None)
        # Without a following boundary, only the named page is established.
        if end is not None:
            for page in working_doc.pages:
                if heading.page_number < page.page_number < end:
                    roles[page.page_number] = ("abstract", "Q001")
    return roles


def check_pdf_frontmatter_no_page_number(pdf_doc: PdfDocument) -> list[AuditFinding]:
    """Emit P022 warnings when visible page-number candidates appear on no-number pages."""
    working_doc = without_wrapper_pages(pdf_doc, detect_digital_commons_wrapper_pages(pdf_doc))
    no_number_targets = [
        (pn, role, q_rule, role == "title_page")
        for pn, (role, q_rule) in sorted(frontmatter_no_number_roles(pdf_doc).items())
    ]

    if not no_number_targets:
        return []

    pages_by_number = {p.page_number: p for p in working_doc.pages}
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
                    "pdf_page": str(page_num),
                    "page_type": page_type,
                    "issue_type": "visible_page_number_on_no_number_page",
                    "candidate_text": first["text"],
                    "document_page_label": first["text"],
                    "document_page_label_confidence": "medium",
                    "candidate_position": first["location"],
                    "observed_location": first["location"],
                    "candidate_count": str(len(candidates)),
                    "source_q_rule_id": q_rule_id,
                    "confidence": "medium",
                    "bbox": first["bbox"],
                    "document_page_label_bbox": first["bbox"],
                    "suggested_fix": (
                        f"Remove the visible page number from the {label} page."
                    ),
                },
            )
        )

    return findings
