"""Conservative PDF heading-level style checks (P027).

Detects heading-like lines using numbered-section patterns (1.1, 1.1.1, etc.)
and infers expected capitalization/punctuation style from NJIT guidelines.

NJIT expectations (Titles Examples Level 1 to 5.docx):
  Level 1: ALL CAPS, bold, centered  — P014 covers named front-matter; P027 covers body chapters.
  Level 2: Title Case, bold          — supplementary to P020 (adds coverage for non-bold PDFs).
  Level 3: Sentence case, bold       — flagged when title-case-like (≥2 non-first caps words).
  Level 4: Sentence case, period     — flagged when title-case-like or missing terminal period.
  Level 5: Sentence case, period, italic — same checks; italic detection is unreliable.

Q-rule basis: Q051 (Level 3 sentence case).

Does NOT duplicate:
  - P014: named front-matter heading style (ABSTRACT, APPROVAL PAGE, etc.).
  - P020: bold-line title-case checking.
  - P024: TOC/List entry capitalization.
"""

from __future__ import annotations

import re

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import BBox, PdfDocument, PdfPage, PdfTextLine, format_bbox_detail
from njit_auditor.rules.pdf_headings import (
    BOLD_FONT_HINT_RE,
    EXPECTED_HEADINGS,
    normalize_heading_text,
)
from njit_auditor.rules.pdf_page_numbers import PAGE_NUM_RE
from njit_auditor.rules.pdf_title_capitalization import (
    check_apa_title_case_phrase,
    is_minor_word,
    looks_like_acronym,
)

# Numbered section patterns — most specific first.
_L5_RE = re.compile(r"^(\d+\.\d+\.\d+\.\d+\.\d+)\s+(.+)$")
_L4_RE = re.compile(r"^(\d+\.\d+\.\d+\.\d+)\s+(.+)$")
_L3_RE = re.compile(r"^(\d+\.\d+\.\d+)\s+(.+)$")
_L2_RE = re.compile(r"^(\d+\.\d+)\s+(.+)$")

# Level 1 body-chapter pattern: "CHAPTER N ..." or "APPENDIX A ...".
_CHAPTER_RE = re.compile(r"^(CHAPTER|APPENDIX)\s+[\dA-Z]+\s*(.*)$", re.IGNORECASE)

# Year-in-parens pattern — indicates a reference/citation, not a heading.
_CITATION_RE = re.compile(r"\(\d{4}\)")

# Pages to skip entirely.
_SKIP_HEADINGS: frozenset[str] = frozenset(EXPECTED_HEADINGS) | frozenset(
    ["REFERENCES", "BIBLIOGRAPHY", "WORKS CITED", "DEDICATION", "COPYRIGHT PAGE"]
)
_TOC_LIST_HEADINGS: frozenset[str] = frozenset(
    ["TABLE OF CONTENTS", "LIST OF TABLES", "LIST OF FIGURES"]
)

_TOP_ZONE_RATIO = 0.15
_MIN_HEADING_TEXT_LEN = 5
_MAX_HEADING_LINE_LEN = 150
_MAX_PREVIEW_LEN = 80
_MIN_ALPHA_RATIO = 0.50
# ≥2 non-first capitalized major words required to call text "title-case-like".
_TITLE_CASE_MAJOR_WORD_MIN = 2


def _in_margin_zone(line: PdfTextLine, page_height: float) -> bool:
    top = page_height * _TOP_ZONE_RATIO
    bottom = page_height * (1.0 - _TOP_ZONE_RATIO)
    return line.bbox.y0 < top or line.bbox.y0 > bottom


def _page_has_any_heading(page: PdfPage, headings: frozenset[str]) -> bool:
    for block in page.text_blocks:
        for line in block.lines:
            if normalize_heading_text(line.text).upper() in headings:
                return True
    return False


def _looks_like_title_case_violation(text: str) -> bool:
    """Return True if text has ≥2 non-first capitalized major words (title-case signal).

    Used to detect sentence-case violations: if a Level 3–5 heading looks like it
    was written in title case, this returns True. Conservative: requires ≥2 such words.
    """
    words = text.split()
    if len(words) < 3:
        return False
    major_caps = 0
    for word in words[1:]:
        clean = word.strip(".,;:!?\"'()-[]")
        if not clean or not clean[0].isupper():
            continue
        if is_minor_word(clean.lower()):
            continue
        if looks_like_acronym(clean):
            continue
        if len(clean) <= 1:
            continue
        major_caps += 1
    return major_caps >= _TITLE_CASE_MAJOR_WORD_MIN


def _is_all_caps_phrase(text: str) -> bool:
    """Return True when ≥80% of alphabetic chars in text are uppercase."""
    alpha = [c for c in text if c.isalpha()]
    if not alpha:
        return False
    return sum(1 for c in alpha if c.isupper()) / len(alpha) >= 0.80


def _is_bold_line(line: PdfTextLine) -> bool:
    """Return True when the line's text is (mostly) bold.

    Per Titles Examples Level 1 to 5.docx, numbered Level 2-5 headings are all
    bold and stand on their own line — a body sentence that merely starts with
    a decimal-looking number (e.g. a statistic like "68.4 percent...") is
    neither. Requiring bold before treating a numbered-pattern match as a real
    heading candidate is what keeps such sentences from being misclassified.
    """
    if not line.spans:
        return False
    return any(
        span.bold or bool(span.font and BOLD_FONT_HINT_RE.search(span.font))
        for span in line.spans
    )


def _sentence_case_example(number_prefix: str, heading_text: str) -> str:
    """Return a conservative sentence-case rewrite of heading_text, or "" if unsafe.

    Only lowercases simple Title-Case words (single leading capital, rest
    lowercase); acronyms, hyphenated/mixed-case tokens, and numbers are left
    untouched. Returns "" if nothing would change, so callers can skip
    offering a misleading "example" when the safe rewrite is a no-op.
    """
    words = heading_text.split()
    if not words:
        return ""
    rewritten = [words[0]]
    changed = False
    for word in words[1:]:
        core = word.strip(".,;:!?\"'()-[]")
        if core and core[0].isupper() and core[1:].islower() and not looks_like_acronym(core):
            lowered = word[0].lower() + word[1:]
            rewritten.append(lowered)
            changed = True
        else:
            rewritten.append(word)
    if not changed:
        return ""
    return f"{number_prefix} {' '.join(rewritten)}"


def _is_qualified_heading(text: str) -> bool:
    """Return True when heading text looks like a real heading title (not noise/equations).

    Does NOT check first-character case — lowercase-first may be a formatting error that
    level-specific checks should flag.
    """
    if len(text) < _MIN_HEADING_TEXT_LEN or len(text) > _MAX_HEADING_LINE_LEN:
        return False
    alpha = sum(1 for c in text if c.isalpha())
    if alpha / max(len(text), 1) < _MIN_ALPHA_RATIO:
        return False
    if _CITATION_RE.search(text):
        return False
    return True


def _finding(
    page_number: int,
    issue_type: str,
    inferred_level: str,
    heading_pattern: str,
    message: str,
    expected_or_reason: str,
    line_preview: str,
    confidence: str,
    source_q_rule_id: str = "",
    bbox: BBox | None = None,
) -> AuditFinding:
    details: dict[str, str] = {
        "page_number": str(page_number),
        "issue_type": issue_type,
        "inferred_level": inferred_level,
        "heading_pattern": heading_pattern,
        "expected_or_reason": expected_or_reason,
        "line_preview": line_preview[:_MAX_PREVIEW_LEN],
        "confidence": confidence,
    }
    if source_q_rule_id:
        details["source_q_rule_id"] = source_q_rule_id
    if bbox is not None:
        details["bbox"] = format_bbox_detail(bbox)
    return AuditFinding(
        rule_id="P027",
        severity=Severity.WARNING,
        page=page_number,
        message=message,
        details=details,
    )


def _check_line(page: PdfPage, line: PdfTextLine) -> list[AuditFinding]:
    if _in_margin_zone(line, page.height):
        return []
    clean = " ".join(line.text.strip().split())
    if not clean or PAGE_NUM_RE.match(clean):
        return []
    if normalize_heading_text(clean).upper() in _SKIP_HEADINGS:
        return []
    if len(clean) > _MAX_HEADING_LINE_LEN:
        return []

    preview = clean[:_MAX_PREVIEW_LEN]
    results: list[AuditFinding] = []

    # Try numbered patterns, most-specific first.
    for level, pattern in [(5, _L5_RE), (4, _L4_RE), (3, _L3_RE), (2, _L2_RE)]:
        m = pattern.match(clean)
        if not m:
            continue
        number_prefix, heading_text = m.group(1), m.group(2).strip()
        if not _is_qualified_heading(heading_text):
            break  # matched pattern but text is not heading-like; skip
        if not _is_bold_line(line):
            # A body sentence that merely starts with a decimal-looking number
            # (e.g. "68.4 percent of participants...") matches the numbered
            # pattern but is not a heading — NJIT numbered headings are bold.
            break

        if level == 2:
            issues = check_apa_title_case_phrase(heading_text)
            high_conf = [i for i in issues if i.get("confidence") == "high"]
            if high_conf:
                first = high_conf[0]
                results.append(_finding(
                    page.page_number,
                    issue_type="level2_title_case_issue",
                    inferred_level="2",
                    heading_pattern=number_prefix,
                    message=(
                        f"Level 2 heading on page {page.page_number} may violate "
                        f"title-case style (NJIT: Level 2 = Title Case)."
                    ),
                    expected_or_reason=(
                        f"Title Case; {first.get('reason', '?')} "
                        f"on '{first.get('word', '?')}'"
                    ),
                    line_preview=preview,
                    confidence="medium",
                    bbox=line.bbox,
                ))

        else:  # level 3, 4, 5
            q_rule = "Q051" if level == 3 else ""
            if _looks_like_title_case_violation(heading_text):
                example = _sentence_case_example(number_prefix, heading_text)
                original = f"{number_prefix} {heading_text}"
                if example:
                    # Prefer an exact, safe token-level replacement over a
                    # generic style reminder when one can be computed.
                    message = (
                        f'Change "{original}" to "{example}" '
                        f"(Level {level} heading; NJIT: Level {level} = Sentence case)."
                    )
                else:
                    message = (
                        f"Change this Level {level} heading to sentence case "
                        f"(NJIT: Level {level} = Sentence Case)."
                    )
                finding = _finding(
                    page.page_number,
                    issue_type=f"level{level}_sentence_case_issue",
                    inferred_level=str(level),
                    heading_pattern=number_prefix,
                    message=message,
                    expected_or_reason="Sentence case (only first word capitalized)",
                    line_preview=preview,
                    confidence="medium",
                    source_q_rule_id=q_rule,
                    bbox=line.bbox,
                )
                if example:
                    finding.details["corrected_example"] = example
                    finding.details["corrected_from"] = original
                results.append(finding)
            # Level 4/5: heading text should end with a period.
            if level in (4, 5) and not heading_text.rstrip().endswith("."):
                results.append(_finding(
                    page.page_number,
                    issue_type=f"level{level}_sentence_case_or_punctuation_issue",
                    inferred_level=str(level),
                    heading_pattern=number_prefix,
                    message=(
                        f"Level {level} heading on page {page.page_number} may be "
                        f"missing a required terminal period "
                        f"(NJIT: Level {level} heading ends with a period)."
                    ),
                    expected_or_reason="Heading text should end with a period '.'",
                    line_preview=preview,
                    confidence="low",
                    source_q_rule_id=q_rule,
                    bbox=line.bbox,
                ))
        break  # apply only the most specific matched level

    else:
        # No numbered pattern matched — check for Level 1 body-chapter headings.
        m1 = _CHAPTER_RE.match(clean)
        if m1:
            title_part = m1.group(2).strip()
            if title_part and len(title_part) >= 3 and not _is_all_caps_phrase(title_part):
                results.append(_finding(
                    page.page_number,
                    issue_type="level1_not_all_caps",
                    inferred_level="1",
                    heading_pattern="CHAPTER/APPENDIX",
                    message=(
                        f"Chapter/Appendix heading on page {page.page_number} title "
                        f"may not be ALL CAPS (NJIT: Level 1 = ALL CAPS)."
                    ),
                    expected_or_reason="ALL CAPS heading title after CHAPTER/APPENDIX N",
                    line_preview=preview,
                    confidence="medium",
                    bbox=line.bbox,
                ))

    return results


def check_pdf_heading_level_styles(pdf_doc: PdfDocument) -> list[AuditFinding]:
    """Emit P027 warnings for numbered headings that violate expected level-specific style.

    Conservative: only numbered section headings (1.1, 1.1.1, etc.) are classified.
    Pages with named front-matter headings, TOC/List headings, or references are skipped.
    """
    findings: list[AuditFinding] = []
    for page in pdf_doc.pages:
        if _page_has_any_heading(page, _SKIP_HEADINGS):
            continue
        if _page_has_any_heading(page, _TOC_LIST_HEADINGS):
            continue
        for block in page.text_blocks:
            for line in block.lines:
                findings.extend(_check_line(page, line))
    return findings
