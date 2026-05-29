"""Heuristic front-matter structure and required-elements checks (P025).

Scope: early/front-matter pages only.
Checks:
  A. Abstract body text presence (ABSTRACT heading present but no body text)
  B. Title page required elements (degree phrase, institution name) in early pages
  C. Approval page non-sparse content (APPROVAL PAGE heading with minimal body)
  D. Basic front-matter order (Abstract appears before TABLE OF CONTENTS)

Does NOT duplicate:
  - P014: named heading style (bold/centered/all-caps/near-top)
  - P021: abstract word count
  - P013/P019: page number candidate detection

Sources:
  - Thesis and Dissertation Formatting Guidelines (WIP).docx
  - Front Matter Pages Lorem Ipsum.pdf
  - PhD Title Pages.pdf
"""

from __future__ import annotations

import re

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument, PdfPage
from njit_auditor.rules.pdf_headings import (
    find_named_frontmatter_headings,
    normalize_heading_text,
)

# Named heading set for boundary detection.
_NAMED_HEADINGS: frozenset[str] = frozenset(
    [
        "ABSTRACT",
        "APPROVAL PAGE",
        "BIOGRAPHICAL SKETCH",
        "ACKNOWLEDGEMENTS",
        "ACKNOWLEDGMENTS",
        "TABLE OF CONTENTS",
        "LIST OF TABLES",
        "LIST OF FIGURES",
        "DEDICATION",
        "COPYRIGHT PAGE",
    ]
)

_ABSTRACT_HEADING = "ABSTRACT"
_APPROVAL_HEADING = "APPROVAL PAGE"
_TOC_HEADING = "TABLE OF CONTENTS"

_DEGREE_RE = re.compile(
    r"\b(doctor\s+of\s+philosophy|master\s+of\s+science|master\s+of\s+arts|"
    r"master\s+of\s+engineering|ph\.?\s*d\.?|m\.?\s*s\.?|m\.?\s*eng\.?)\b",
    re.IGNORECASE,
)
_INSTITUTION_RE = re.compile(
    r"\b(new\s+jersey\s+institute\s+of\s+technology|njit)\b",
    re.IGNORECASE,
)

TITLE_PAGE_SCAN_PAGES = 4
MIN_ABSTRACT_BODY_WORDS = 5
MIN_APPROVAL_BODY_LINES = 3  # substantial lines (≥2 words each)
MIN_DOC_PAGES_FOR_TITLE_CHECK = 3


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _normalized_heading(page: PdfPage, line_text: str) -> str:
    return normalize_heading_text(line_text).upper()


def _page_named_heading(page: PdfPage) -> str | None:
    """Return the first recognized named heading on this page, or None."""
    for block in page.text_blocks:
        for line in block.lines:
            norm = normalize_heading_text(line.text).upper()
            if norm in _NAMED_HEADINGS:
                return norm
    return None


def _lines_below_heading(page: PdfPage, heading: str) -> list[str]:
    """Return stripped non-empty lines appearing below `heading` on this page."""
    heading_seen = False
    result: list[str] = []
    for block in page.text_blocks:
        for line in block.lines:
            norm = normalize_heading_text(line.text).upper()
            if norm == heading:
                heading_seen = True
                continue
            if not heading_seen:
                continue
            if norm in _NAMED_HEADINGS:
                return result
            text = line.text.strip()
            if text:
                result.append(text)
    return result


def _page_all_text(page: PdfPage) -> str:
    """Return all text on a page joined by spaces."""
    parts = [line.text.strip() for block in page.text_blocks for line in block.lines]
    return " ".join(p for p in parts if p)


def _doc_has_frontmatter(pdf_document: PdfDocument) -> bool:
    """Return True if the document has at least one named front-matter heading."""
    return bool(find_named_frontmatter_headings(pdf_document))


# ---------------------------------------------------------------------------
# Check A: Abstract body text presence
# ---------------------------------------------------------------------------


def _check_abstract_body_presence(pdf_document: PdfDocument) -> list[AuditFinding]:
    findings: list[AuditFinding] = []
    for page in pdf_document.pages:
        if _page_named_heading(page) != _ABSTRACT_HEADING:
            continue
        body_lines = _lines_below_heading(page, _ABSTRACT_HEADING)
        body_text = " ".join(body_lines)
        word_count = len(body_text.split())
        if word_count < MIN_ABSTRACT_BODY_WORDS:
            findings.append(
                AuditFinding(
                    rule_id="P025",
                    severity=Severity.WARNING,
                    page=page.page_number,
                    message=(
                        "ABSTRACT heading is present but no body text was detected below it."
                    ),
                    details={
                        "page_number": str(page.page_number),
                        "page_type": "abstract",
                        "issue_type": "missing_abstract_body",
                        "body_word_count": str(word_count),
                        "expected_or_reason": (
                            "Abstract page should have body text below the ABSTRACT heading"
                        ),
                        "confidence": "high",
                    },
                )
            )
    return findings


# ---------------------------------------------------------------------------
# Check B: Title page required elements
# ---------------------------------------------------------------------------


def _check_title_page_elements(pdf_document: PdfDocument) -> list[AuditFinding]:
    if len(pdf_document.pages) < MIN_DOC_PAGES_FOR_TITLE_CHECK:
        return []
    if not _doc_has_frontmatter(pdf_document):
        return []

    scan_pages = pdf_document.pages[:TITLE_PAGE_SCAN_PAGES]
    combined_text = " ".join(_page_all_text(p) for p in scan_pages)

    findings: list[AuditFinding] = []

    if not _DEGREE_RE.search(combined_text):
        findings.append(
            AuditFinding(
                rule_id="P025",
                severity=Severity.WARNING,
                page=1,
                message=(
                    "No degree phrase detected in the first pages of the document. "
                    "Expected e.g. 'Doctor of Philosophy' or 'Master of Science' on title page."
                ),
                details={
                    "page_number": "1",
                    "page_type": "title_page",
                    "issue_type": "missing_title_page_degree_phrase",
                    "scan_pages": str(TITLE_PAGE_SCAN_PAGES),
                    "expected_or_reason": (
                        "Title page should state the degree (Doctor of Philosophy / "
                        "Master of Science / etc.)"
                    ),
                    "confidence": "medium",
                },
            )
        )

    if not _INSTITUTION_RE.search(combined_text):
        findings.append(
            AuditFinding(
                rule_id="P025",
                severity=Severity.WARNING,
                page=1,
                message=(
                    "Institution name not detected in the first pages of the document. "
                    "Expected 'New Jersey Institute of Technology' or 'NJIT' on title page."
                ),
                details={
                    "page_number": "1",
                    "page_type": "title_page",
                    "issue_type": "missing_title_page_institution",
                    "scan_pages": str(TITLE_PAGE_SCAN_PAGES),
                    "expected_or_reason": (
                        "Title page must include the institution name "
                        "(New Jersey Institute of Technology)"
                    ),
                    "confidence": "medium",
                },
            )
        )

    return findings


# ---------------------------------------------------------------------------
# Check C: Approval page sparse content
# ---------------------------------------------------------------------------


def _check_approval_page_content(pdf_document: PdfDocument) -> list[AuditFinding]:
    findings: list[AuditFinding] = []
    for page in pdf_document.pages:
        if _page_named_heading(page) != _APPROVAL_HEADING:
            continue
        body_lines = _lines_below_heading(page, _APPROVAL_HEADING)
        substantial = [line for line in body_lines if len(line.split()) >= 2]
        if len(substantial) < MIN_APPROVAL_BODY_LINES:
            findings.append(
                AuditFinding(
                    rule_id="P025",
                    severity=Severity.WARNING,
                    page=page.page_number,
                    message=(
                        "APPROVAL PAGE heading is present but body content appears sparse "
                        f"({len(substantial)} substantial lines found; "
                        f"expected at least {MIN_APPROVAL_BODY_LINES})."
                    ),
                    details={
                        "page_number": str(page.page_number),
                        "page_type": "approval_page",
                        "issue_type": "sparse_approval_page_content",
                        "substantial_line_count": str(len(substantial)),
                        "expected_or_reason": (
                            "Approval page should contain committee member names, "
                            "titles, and signature lines"
                        ),
                        "confidence": "medium",
                    },
                )
            )
    return findings


# ---------------------------------------------------------------------------
# Check D: Front-matter order (Abstract before TABLE OF CONTENTS)
# ---------------------------------------------------------------------------


def _check_frontmatter_order(pdf_document: PdfDocument) -> list[AuditFinding]:
    heading_pages: dict[str, int] = {
        m.heading: m.page_number for m in find_named_frontmatter_headings(pdf_document)
    }
    abstract_pg = heading_pages.get(_ABSTRACT_HEADING)
    toc_pg = heading_pages.get(_TOC_HEADING)

    if abstract_pg is None or toc_pg is None:
        return []

    if abstract_pg > toc_pg:
        return [
            AuditFinding(
                rule_id="P025",
                severity=Severity.WARNING,
                page=abstract_pg,
                message=(
                    f"ABSTRACT heading appears on page {abstract_pg}, which is after "
                    f"TABLE OF CONTENTS on page {toc_pg}. "
                    "NJIT guidelines require Abstract to precede Table of Contents."
                ),
                details={
                    "page_number": str(abstract_pg),
                    "page_type": "abstract",
                    "issue_type": "possible_frontmatter_order_issue",
                    "abstract_page": str(abstract_pg),
                    "toc_page": str(toc_pg),
                    "expected_or_reason": "Abstract should appear before Table of Contents",
                    "confidence": "high",
                },
            )
        ]

    return []


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def check_pdf_frontmatter_structure(pdf_document: PdfDocument) -> list[AuditFinding]:
    """Emit P025 warnings for front-matter structure and required-element issues."""
    findings: list[AuditFinding] = []
    findings.extend(_check_abstract_body_presence(pdf_document))
    findings.extend(_check_title_page_elements(pdf_document))
    findings.extend(_check_approval_page_content(pdf_document))
    findings.extend(_check_frontmatter_order(pdf_document))
    return findings
