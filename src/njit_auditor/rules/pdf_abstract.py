"""Heuristic abstract word-count check for compiled PDF files (P021).

Locates the Abstract page by the named 'ABSTRACT' heading, extracts visible
body text from that page, and checks the word count against NJIT limits.

Limitations:
- Abstract text spanning multiple pages is undercounted (only first page checked).
- Degree type (PhD/MS) cannot be reliably inferred from the PDF text layer alone;
  a conservative threshold of 350 words (PhD limit) is used.
- Word counting uses whitespace splitting and is heuristic.
"""

from __future__ import annotations

import re

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument, PdfPage, PdfTextLine
from njit_auditor.rules.latex_abstract import PHD_WORD_LIMIT, count_abstract_words
from njit_auditor.rules.pdf_headings import normalize_heading_text

_ABSTRACT_HEADING = "ABSTRACT"

# Degree inference patterns from PDF title-page text
_PDF_PHD_RE = re.compile(
    r"\b(ph\.?d|doctor\w*|doctoral|dissertation)\b", re.IGNORECASE
)
_PDF_MS_RE = re.compile(
    r"\b(master\w*|m\.?s\.?|m\.?eng\.?)\b", re.IGNORECASE
)

# Named front-matter headings that signal the end of the abstract section
_NEXT_SECTION_HEADINGS = frozenset(
    [
        "APPROVAL PAGE",
        "BIOGRAPHICAL SKETCH",
        "ACKNOWLEDGEMENTS",
        "ACKNOWLEDGMENTS",
        "TABLE OF CONTENTS",
        "DEDICATION",
        "COPYRIGHT PAGE",
    ]
)

MAX_PREVIEW_LEN = 80


def _normalized_heading(line: PdfTextLine) -> str:
    return normalize_heading_text(line.text).upper()


def _page_has_abstract_heading(page: PdfPage) -> bool:
    for block in page.text_blocks:
        for line in block.lines:
            if _normalized_heading(line) == _ABSTRACT_HEADING:
                return True
    return False


def _infer_degree_from_pdf(pdf_document: PdfDocument) -> str:
    """Scan early PDF pages for PhD/MS degree indicators."""
    phd_hits = 0
    ms_hits = 0
    for page in pdf_document.pages[:5]:
        for block in page.text_blocks:
            text = block.text
            phd_hits += len(_PDF_PHD_RE.findall(text))
            ms_hits += len(_PDF_MS_RE.findall(text))
    if phd_hits > 0 and phd_hits >= ms_hits:
        return "phd"
    if ms_hits > 0 and ms_hits > phd_hits:
        return "ms"
    return "unknown"


def _extract_abstract_body_text(page: PdfPage) -> str:
    """
    Extract text from the abstract page, skipping the ABSTRACT heading line itself.

    Conservative: only reads the single abstract page. Multi-page abstracts
    will be undercounted.
    """
    lines: list[str] = []
    heading_seen = False
    for block in page.text_blocks:
        for line in block.lines:
            norm = _normalized_heading(line)
            if norm == _ABSTRACT_HEADING:
                heading_seen = True
                continue
            if not heading_seen:
                continue
            # Stop if we hit another major named heading on the same page
            if norm in _NEXT_SECTION_HEADINGS:
                break
            text = line.text.strip()
            if text:
                lines.append(text)
    return " ".join(lines)


# Mirrors FORBIDDEN_WORD_RE and FIRST_PERSON_RE from latex_abstract.py (Q004/Q005 TeX checks).
_PDF_FORBIDDEN_WORD_RE = re.compile(r"\b(paper|papers|article|articles)\b", re.IGNORECASE)
_PDF_FIRST_PERSON_I_RE = re.compile(r"(?<![A-Za-z'’])I(?![A-Za-z'’])")
_PDF_FIRST_PERSON_OTHER_RE = re.compile(
    r"\b(me|my|mine|we|us|our|ours)\b", re.IGNORECASE
)


def check_pdf_abstract_keywords(pdf_document: PdfDocument) -> list[AuditFinding]:
    """Emit P078 warnings for Q004 forbidden terms and Q005 first-person pronouns
    found in the Abstract page body text only.

    Scoped to the single Abstract page via existing helpers; does not scan body,
    references, TOC, or other sections.
    """
    abstract_page: PdfPage | None = None
    for page in pdf_document.pages:
        if _page_has_abstract_heading(page):
            abstract_page = page
            break
    if abstract_page is None:
        return []

    body_text = _extract_abstract_body_text(abstract_page)
    if not body_text:
        return []

    findings: list[AuditFinding] = []

    for term in sorted(
        {m.group(1).lower() for m in _PDF_FORBIDDEN_WORD_RE.finditer(body_text)}
    ):
        findings.append(
            AuditFinding(
                rule_id="P078",
                severity=Severity.WARNING,
                page=abstract_page.page_number,
                message=(
                    f"Abstract uses forbidden term '{term}' "
                    "under NJIT abstract wording guidance."
                ),
                details={
                    "issue_type": "abstract_pdf_forbidden_term",
                    "term": term,
                    "source_q_rule_ids": "Q004",
                    "triage_tier": "check",
                    "confidence": "medium",
                },
            )
        )

    first_person_pronouns = {
        m.group(0).lower() for m in _PDF_FIRST_PERSON_I_RE.finditer(body_text)
    }
    first_person_pronouns.update(
        m.group(1).lower() for m in _PDF_FIRST_PERSON_OTHER_RE.finditer(body_text)
    )
    for pronoun in sorted(first_person_pronouns):
        findings.append(
            AuditFinding(
                rule_id="P078",
                severity=Severity.WARNING,
                page=abstract_page.page_number,
                message=(
                    f"Abstract uses first-person pronoun '{pronoun}' "
                    "under NJIT abstract wording guidance."
                ),
                details={
                    "issue_type": "abstract_pdf_first_person_pronoun",
                    "pronoun": pronoun,
                    "source_q_rule_ids": "Q005",
                    "triage_tier": "check",
                    "confidence": "medium",
                },
            )
        )

    return findings


def check_pdf_abstract_word_count(pdf_document: PdfDocument) -> list[AuditFinding]:
    """Emit a conservative P021 warning if the abstract text on the Abstract page
    appears to exceed word-count limits.

    Uses a 350-word threshold (PhD limit) by default; only downgrades to MS (150)
    when the PDF text layer clearly indicates an MS-level degree.
    Does not emit a warning when count is within the inferred limit.
    """
    abstract_page: PdfPage | None = None
    for page in pdf_document.pages:
        if _page_has_abstract_heading(page):
            abstract_page = page
            break

    if abstract_page is None:
        return []

    body_text = _extract_abstract_body_text(abstract_page)
    if not body_text:
        return []

    word_count = count_abstract_words(body_text)
    if word_count == 0:
        return []

    degree = _infer_degree_from_pdf(pdf_document)

    from njit_auditor.rules.latex_abstract import MS_WORD_LIMIT  # avoid circular at module level

    if degree == "ms":
        limit = MS_WORD_LIMIT
        degree_label = "MS"
        confidence = "medium"
    else:
        limit = PHD_WORD_LIMIT
        degree_label = "PhD" if degree == "phd" else "inferred PhD (degree type uncertain)"
        confidence = "low" if degree == "unknown" else "medium"

    if word_count <= limit:
        return []

    return [
        AuditFinding(
            rule_id="P021",
            severity=Severity.WARNING,
            page=abstract_page.page_number,
            message=(
                f"Abstract word count on Abstract page ({word_count} words) appears to exceed "
                f"the {degree_label} limit of {limit} words. "
                f"Note: multi-page abstracts may be undercounted."
            ),
            details={
                "page_number": str(abstract_page.page_number),
                "word_count": str(word_count),
                "limit": str(limit),
                "inferred_degree_type": degree,
                "confidence": confidence,
                "caveat": "single-page extraction only; multi-page abstract undercounted",
            },
        )
    ]
