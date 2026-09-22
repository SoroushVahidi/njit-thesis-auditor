"""Unnumbered bold heading-shaped body phrase check (P086).

Ester's R015 follow-up review (2026-08-31) separately observed that a bold
run-in phrase Youra's document used as a de facto section title carries no
section number, and stated that bold should be reserved for numbered
title/heading levels 1-4 -- see
``docs/status/p015_r015_esther_feedback_run_in_heading_20260831.md``
("Separate Bold-Heading Observation"). That document's own rule-ownership
audit already ruled out P020 (style of *recognized* headings only), P026
(font family/size, no concept of "reserved for headings"), and P027
(numbered-heading level/style -- cannot own an unnumbered phrase by
definition). No existing rule owns this, and it is deliberately kept out of
R015 (which stays a paragraph-indentation rule).

Scope, deliberately conservative (see the design-gate discussion in
``docs/status/p086_unnumbered_bold_heading_design_20260922.md``): only the
exact structural shape Ester actually adjudicated -- a bold run-in heading
lead sharing a physical row with regular-styled continuation text, the same
shape ``pdf_indentation.py`` already detects (and excludes from indentation
comparison) for R015. This is reused verbatim, not reinvented, so this rule
inherits R015's existing, already-validated precision for telling a genuine
run-in heading lead apart from coincidental same-row bold text. A flagged
candidate must also pass the same "looks like a real heading title, not
noise" filter P027 already uses (``_is_qualified_heading``), and must not
already carry a section number (P027's own numbered patterns) or be a
named/TOC/List/references heading (already excluded by
``group_lines_into_paragraphs`` itself). Anything else -- inline emphasis,
labels, table/figure captions and column headers, math notation -- is not
this structural shape and is left alone; this rule does not scan for "any
bold span," only for a same-row bold-lead-plus-continuation heading shape
lacking a number.
"""

from __future__ import annotations

import re

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument, PdfTextLine, format_bbox_detail
from njit_auditor.rules.pdf_heading_levels import (
    _CHAPTER_RE,
    _SKIP_HEADINGS,
    _TOC_LIST_HEADINGS,
    _is_qualified_heading,
    _page_has_any_heading,
)
from njit_auditor.rules.pdf_headings import normalize_heading_text
from njit_auditor.rules.pdf_indentation import (
    _SECTION_NUMBER_ONLY_RE,
    _find_excluded_page_numbers,
    _paragraph_starts_with_run_in_heading,
    group_lines_into_paragraphs,
)

MAX_PREVIEW_LEN = 80

# A leading section-number-like prefix, tolerant of two known PDF text-
# extraction artifacts observed on the real corpus (see design doc): a
# trailing period glued to the last digit group before the space ("3.2.4.4.
# Title"), and the number glued directly onto the first word with *no*
# space at all ("1.4.1.3Atypical..."). Deliberately broader than
# pdf_heading_levels.py's own strict per-level patterns (which require
# `\s+` right after the digits and are calibrated for that rule's own
# positive-detection purpose): here the pattern is only ever used to
# *exclude* a candidate, so over-matching (e.g. a body sentence that
# happens to start with a decimal number like "68.4 percent...") is the
# safe direction to err in -- it can only suppress a flag, never invent one.
_LEADING_NUMBER_RE = re.compile(r"^\d+(?:\.\d+){1,4}\.?(?:\s+|(?=[A-Za-z]))")

# A leading bullet/list marker, tolerant of the same no-space extraction
# artifact (pdf_indentation.py's own BULLET_PREFIX_RE requires `\s+` after
# the marker and so misses "•RobustCovariance..." on the real corpus).
_LEADING_BULLET_RE = re.compile(r"^[-*•]")

_SAME_ROW_Y_TOLERANCE_PT = 1.0


def _already_numbered_or_named(candidate_text: str) -> bool:
    clean = " ".join(candidate_text.strip().split())
    if _LEADING_NUMBER_RE.match(clean):
        return True
    if _LEADING_BULLET_RE.match(clean):
        return True
    if _CHAPTER_RE.match(clean):
        return True
    if normalize_heading_text(clean).upper() in _SKIP_HEADINGS | _TOC_LIST_HEADINGS:
        return True
    return False


def _has_same_row_bare_number_to_left(
    candidate: PdfTextLine, all_lines: list[PdfTextLine]
) -> bool:
    """True when a bare section number (e.g. "2.1.3.2") sits on the same
    physical row, to the left of *candidate* -- the PDF extracted the
    heading's own number as a separate fragment from its title (the same
    split this rule's own numbered-prefix check cannot see, since it only
    looks at the candidate's own text). Observed on the real corpus: a
    numbered heading whose number and bold title extract as two distinct
    same-row lines. Without this check, such a heading would be
    misclassified as unnumbered.
    """
    for line in all_lines:
        if line is candidate:
            continue
        if abs(line.bbox.y0 - candidate.bbox.y0) > _SAME_ROW_Y_TOLERANCE_PT:
            continue
        if line.bbox.x0 >= candidate.bbox.x0:
            continue
        if _SECTION_NUMBER_ONLY_RE.match(" ".join(line.text.strip().split())):
            return True
    return False


def check_pdf_unnumbered_bold_heading(pdf_document: PdfDocument) -> list[AuditFinding]:
    """Emit P086 warnings for a bold run-in heading-shaped phrase with no
    section number and no recognized heading name.

    Conservative and structural only: reuses R015's own run-in-heading-lead
    detection (bold lead sharing a physical row with regular continuation
    text) and P027's own numbered-heading/qualified-heading-text checks.
    Does not fire on any bold span that is not this exact shape, and
    abstains (emits nothing) for anything the shared paragraph grouping
    already treats as a caption, named heading, bullet, or TOC/List page.
    """
    findings: list[AuditFinding] = []
    excluded_pages = _find_excluded_page_numbers(pdf_document)

    for page in pdf_document.pages:
        if page.page_number in excluded_pages:
            continue
        if _page_has_any_heading(page, _SKIP_HEADINGS):
            continue
        if _page_has_any_heading(page, _TOC_LIST_HEADINGS):
            continue

        paragraphs = group_lines_into_paragraphs(page)
        if not paragraphs:
            continue
        page_lines = [line for block in page.text_blocks for line in block.lines]

        for paragraph in paragraphs:
            if len(paragraph) < 2:
                continue
            if not _paragraph_starts_with_run_in_heading(paragraph):
                continue

            candidate_line = paragraph[0]
            candidate_text = " ".join(candidate_line.text.strip().split())
            if not _is_qualified_heading(candidate_text):
                continue
            if _already_numbered_or_named(candidate_text):
                continue
            if _has_same_row_bare_number_to_left(candidate_line, page_lines):
                continue

            preview = candidate_text[:MAX_PREVIEW_LEN]
            findings.append(
                AuditFinding(
                    rule_id="P086",
                    severity=Severity.WARNING,
                    page=page.page_number,
                    message=(
                        f"Bold phrase on page {page.page_number} reads like a heading "
                        "but has no section number. Bold is reserved for numbered "
                        "heading levels 1-4; either add the section number or "
                        "remove the bold styling."
                    ),
                    details={
                        "issue_type": "bold_heading_without_section_number",
                        "page": str(page.page_number),
                        "line_preview": preview,
                        "confidence": "medium",
                        "bbox": format_bbox_detail(candidate_line.bbox),
                    },
                )
            )

    return findings
