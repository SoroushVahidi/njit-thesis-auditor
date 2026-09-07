"""Heuristic TOC/List entry capitalization and punctuation checks (P024).

Scope: TABLE OF CONTENTS, LIST OF TABLES, and LIST OF FIGURES pages only.
Not applied to body pages, references pages, or other front-matter pages.

Source: NJIT Thesis and Dissertation Formatting Guidelines;
        Titles Examples Level 1-5.docx; Self-Self Assessment Sheet.pdf
  - TOC Level 1 chapter/front-matter entries: ALL CAPS (Q049)
  - TOC Level 2 entries: Title Case (Q050)
  - List of Tables titles: Title Case, no terminal period (Q065 area)
  - List of Figures descriptions: Sentence case (conservative)
"""

from __future__ import annotations

import re

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument, format_bbox_detail
from njit_auditor.rules.pdf_title_capitalization import (
    MINOR_WORDS,
    check_apa_title_case_phrase,
    looks_like_acronym,
    normalize_title_text,
    tokenize_title_words,
)
from njit_auditor.rules.pdf_toc_alignment import (
    INDENT_CLUSTER_TOLERANCE_PT,
    TocEntryLine,
    TocPageContext,
    detect_toc_like_pages,
    extract_toc_entry_lines,
)

LINE_PREVIEW_MAX = 80
MIN_ENTRY_WORDS = 3
_MAX_FLAGGED_WORDS = 3

# TOC level-classification patterns.
_CHAPTER_RE = re.compile(r"^(?:chapter|appendix)\b", re.IGNORECASE)
_LEVEL2_NUM_RE = re.compile(r"^[0-9]+\.[0-9]+(?:\s|$)")
_LEVEL3_NUM_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+")

# List-entry prefix: "Table 1." / "Figure 2." etc.
_LIST_PREFIX_RE = re.compile(
    r"^(?:table|fig(?:ure)?\.?)\s+[0-9]+(?:[.\-][0-9]+)?\s*[.):]?\s*",
    re.IGNORECASE,
)

# Leader dots: 2+ dots with optional whitespace between them (not a single terminal period).
_LEADER_STRIP_RE = re.compile(r"\s*(?:\.\s*){2,}$")

_TERMINAL_PERIOD_RE = re.compile(r"\.\s*$")

# Words containing digits or special math notation: skip in case checks.
_SKIP_WORD_RE = re.compile(r"[0-9Α-ω+*/=<>^\\{}[\]()°]")

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'À-ɏ]*(?:-[A-Za-z][A-Za-z'À-ɏ]*)*")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _clean_entry_text(entry: TocEntryLine) -> str:
    """Return entry text with page number token and leader dots stripped."""
    text = entry.cleaned_text
    if entry.page_number_token:
        stripped = text.rstrip()
        if stripped.endswith(entry.page_number_token):
            stripped = stripped[: -len(entry.page_number_token)].rstrip()
        text = stripped
    text = _LEADER_STRIP_RE.sub("", text).strip()
    return normalize_title_text(text)


def _strip_list_prefix(text: str) -> str:
    """Strip 'Table N.' or 'Figure N.' prefix from LoT/LoF entry text."""
    match = _LIST_PREFIX_RE.match(text)
    return text[match.end() :].strip() if match else text


def _build_indent_clusters(entries: list[TocEntryLine]) -> list[float]:
    """Build sorted indentation clusters from entry x-positions."""
    indents = sorted({e.indent_x for e in entries})
    clusters: list[float] = []
    for indent in indents:
        for idx, center in enumerate(clusters):
            if abs(indent - center) <= INDENT_CLUSTER_TOLERANCE_PT:
                clusters[idx] = (clusters[idx] + indent) / 2.0
                break
        else:
            clusters.append(indent)
    return sorted(clusters)


def _classify_toc_level(entry: TocEntryLine, indent_clusters: list[float]) -> int | None:
    """Classify TOC entry level (1, 2, 3+) or None if ambiguous."""
    text = entry.cleaned_text
    if _LEVEL3_NUM_RE.match(text):
        return 3
    if _LEVEL2_NUM_RE.match(text):
        return 2
    if _CHAPTER_RE.match(text):
        return 1
    # Indentation-based fallback.
    if len(indent_clusters) >= 2:
        if abs(entry.indent_x - indent_clusters[0]) <= INDENT_CLUSTER_TOLERANCE_PT:
            return 1
        if abs(entry.indent_x - indent_clusters[1]) <= INDENT_CLUSTER_TOLERANCE_PT:
            return 2
    elif indent_clusters:
        if abs(entry.indent_x - indent_clusters[0]) <= INDENT_CLUSTER_TOLERANCE_PT:
            return 1
    return None


def _obvious_not_all_caps(text: str) -> bool:
    """Return True if text has >=2 lowercase-starting major words (implies not ALL CAPS)."""
    words = _WORD_RE.findall(text)
    lowercase_major = [
        w for w in words
        if len(w) > 3
        and w.lower() not in MINOR_WORDS
        and not looks_like_acronym(w)
        and w[0].islower()
    ]
    return len(lowercase_major) >= 2


def _sentence_case_violation_words(text: str) -> list[str]:
    """Return the specific later words that are unexpectedly capitalized.

    Conservative: flags only when >=60% of eligible later words are
    capitalized (title-case-like). Used for List of Figures entries, which
    NJIT expects in sentence case.

    Lowercase NJIT minor words (including longer prepositions such as
    ``with``) stay in the denominator so they dilute the title-case ratio.
    Short minors are already dropped by the ``len(w) > 3`` gate; excluding
    long minors here would falsely tip borderline sentence-case figure
    titles that contain a few proper nouns (e.g. ``… with Marching Cubes``).
    """
    words: list[str] = []
    depth = 0
    last_end = 0
    for match in _WORD_RE.finditer(text):
        between = text[last_end : match.start()]
        for char in between:
            if char == "(":
                depth += 1
            elif char == ")":
                depth = max(0, depth - 1)
        if depth == 0:
            words.append(match.group())
        last_end = match.end()
    if len(words) < 4:
        return []
    later = [
        w for w in words[1:]
        if len(w) > 3
        and not looks_like_acronym(w)
        and not _SKIP_WORD_RE.search(w)
    ]
    if len(later) < 3:
        return []
    capitalized = [w for w in later if w[0].isupper()]
    if (len(capitalized) / len(later)) >= 0.6:
        return capitalized
    return []


def _sentence_case_violation(text: str) -> bool:
    """Conservative: True if later content words are >60% capitalized (title-case-like).

    Used for List of Figures entries where sentence case is expected.
    """
    return bool(_sentence_case_violation_words(text))


# ---------------------------------------------------------------------------
# Page-level checks
# ---------------------------------------------------------------------------


def _check_toc_page(
    context: TocPageContext,
    entries: list[TocEntryLine],
) -> list[AuditFinding]:
    findings: list[AuditFinding] = []
    if len(entries) < 3:
        return findings
    indent_clusters = _build_indent_clusters(entries)
    for entry_index, entry in enumerate(entries):
        entry_text = _clean_entry_text(entry)
        if not entry_text or len(entry_text) < 8:
            continue
        if len(tokenize_title_words(entry_text)) < MIN_ENTRY_WORDS:
            continue
        level = _classify_toc_level(entry, indent_clusters)
        if level is None:
            continue
        if level == 1:
            if _obvious_not_all_caps(entry_text):
                findings.append(
                    AuditFinding(
                        rule_id="P024",
                        severity=Severity.WARNING,
                        page=context.page.page_number,
                        message=(
                            "TOC Level 1 entry may not be in ALL CAPS as expected by "
                            "NJIT guidelines."
                        ),
                        details={
                            "page_number": str(context.page.page_number),
                            "page_type": "table_of_contents",
                            "issue_type": "toc_level_capitalization",
                            "entry_level": "1",
                            "entry_index": str(entry_index),
                            "line_preview": entry.cleaned_text[:LINE_PREVIEW_MAX],
                            "bbox": format_bbox_detail(entry.line.bbox),
                            "expected_or_reason": "Level 1 TOC entries expected ALL CAPS",
                            "confidence": "medium",
                            "source_q_rule_id": "Q049",
                        },
                    )
                )
        elif level == 2:
            issues = check_apa_title_case_phrase(entry_text)
            if issues:
                first = issues[0]
                findings.append(
                    AuditFinding(
                        rule_id="P024",
                        severity=Severity.WARNING,
                        page=context.page.page_number,
                        message=(
                            f"TOC Level 2 entry may have title-case issue: "
                            f"'{first['word']}' may need to be capitalized "
                            f"({first['reason']})."
                        ),
                        details={
                            "page_number": str(context.page.page_number),
                            "page_type": "table_of_contents",
                            "issue_type": "toc_level_capitalization",
                            "entry_level": "2",
                            "entry_index": str(entry_index),
                            "line_preview": entry.cleaned_text[:LINE_PREVIEW_MAX],
                            "bbox": format_bbox_detail(entry.line.bbox),
                            "expected_or_reason": first["reason"],
                            "confidence": first["confidence"],
                            "source_q_rule_id": "Q050",
                        },
                    )
                )
        # Level 3+: do not enforce (no clear guideline for sentence-case TOC entries).
    return findings


def _check_lot_page(
    context: TocPageContext,
    entries: list[TocEntryLine],
) -> list[AuditFinding]:
    findings: list[AuditFinding] = []
    for entry_index, entry in enumerate(entries):
        raw = _clean_entry_text(entry)
        entry_text = _strip_list_prefix(raw)
        if not entry_text or len(entry_text) < 10:
            continue
        if len(tokenize_title_words(entry_text)) < MIN_ENTRY_WORDS:
            continue
        issues = check_apa_title_case_phrase(
            entry_text, skip_hyphenated_fragments=True
        )
        if issues:
            first = issues[0]
            findings.append(
                AuditFinding(
                    rule_id="P024",
                    severity=Severity.WARNING,
                    page=context.page.page_number,
                    message=(
                        f"List of Tables entry may have title-case issue: "
                        f"'{first['word']}' may need to be capitalized "
                        f"({first['reason']})."
                    ),
                    details={
                        "page_number": str(context.page.page_number),
                        "page_type": "list_of_tables",
                        "issue_type": "list_of_tables_title_case",
                        "entry_index": str(entry_index),
                        "line_preview": entry.cleaned_text[:LINE_PREVIEW_MAX],
                        "bbox": format_bbox_detail(entry.line.bbox),
                        "expected_or_reason": first["reason"],
                        "confidence": first["confidence"],
                        "source_q_rule_id": "Q065",
                    },
                )
            )
        if _TERMINAL_PERIOD_RE.search(entry_text):
            findings.append(
                AuditFinding(
                    rule_id="P024",
                    severity=Severity.WARNING,
                    page=context.page.page_number,
                    message="List of Tables entry appears to end with an unexpected period.",
                    details={
                        "page_number": str(context.page.page_number),
                        "page_type": "list_of_tables",
                        "issue_type": "unexpected_terminal_punctuation",
                        "entry_index": str(entry_index),
                        "line_preview": entry.cleaned_text[:LINE_PREVIEW_MAX],
                        "bbox": format_bbox_detail(entry.line.bbox),
                        "expected_or_reason": "Table titles in LoT should not end with a period",
                        "confidence": "high",
                        "source_q_rule_id": "Q065",
                    },
                )
            )
    return findings


def _check_lof_page(
    context: TocPageContext,
    entries: list[TocEntryLine],
) -> list[AuditFinding]:
    findings: list[AuditFinding] = []
    for entry_index, entry in enumerate(entries):
        raw = _clean_entry_text(entry)
        entry_text = _strip_list_prefix(raw)
        if not entry_text or len(entry_text) < 10:
            continue
        if len(tokenize_title_words(entry_text)) < 4:
            continue
        flagged_words = _sentence_case_violation_words(entry_text)
        if flagged_words:
            words_clause = ", ".join(f"'{w}'" for w in flagged_words[:_MAX_FLAGGED_WORDS])
            findings.append(
                AuditFinding(
                    rule_id="P024",
                    severity=Severity.WARNING,
                    page=context.page.page_number,
                    message=(
                        "List of Figures entry may not follow sentence-case style: "
                        f"{words_clause} appear capitalized where sentence case is expected."
                    ),
                    details={
                        "page_number": str(context.page.page_number),
                        "page_type": "list_of_figures",
                        "issue_type": "list_of_figures_sentence_case",
                        "entry_index": str(entry_index),
                        "line_preview": entry.cleaned_text[:LINE_PREVIEW_MAX],
                        "bbox": format_bbox_detail(entry.line.bbox),
                        "expected_or_reason": (
                            "Figure descriptions in LoF expected in sentence case"
                        ),
                        "flagged_words": ", ".join(flagged_words[:_MAX_FLAGGED_WORDS]),
                        "confidence": "medium",
                        "source_q_rule_id": "Q074",
                    },
                )
            )
    return findings


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def check_pdf_toc_list_formatting(pdf_document: PdfDocument) -> list[AuditFinding]:
    """Emit P024 warnings for TOC/LoT/LoF entry capitalization and punctuation issues."""
    findings: list[AuditFinding] = []
    for context in detect_toc_like_pages(pdf_document):
        entries = extract_toc_entry_lines(context)
        if context.page_type == "table_of_contents":
            findings.extend(_check_toc_page(context, entries))
        elif context.page_type == "list_of_tables":
            findings.extend(_check_lot_page(context, entries))
        elif context.page_type == "list_of_figures":
            findings.extend(_check_lof_page(context, entries))
    return findings
