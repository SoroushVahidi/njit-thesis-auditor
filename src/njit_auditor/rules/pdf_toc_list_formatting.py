"""Heuristic TOC/List entry capitalization checks (P024).

Scope: TABLE OF CONTENTS, LIST OF TABLES, and LIST OF FIGURES pages only.
Not applied to body pages, references pages, or other front-matter pages.

Source: NJIT Thesis and Dissertation Formatting Guidelines;
        Titles Examples Level 1-5.docx; Self-Self Assessment Sheet.pdf
  - TOC Level 1 chapter/front-matter entries: ALL CAPS (Q049)
  - TOC Level 2 entries: Title Case (Q050)
  - List of Tables titles: Title Case (Q065; public card R024D)
  - List of Figures titles: Title Case (Q074 slot; public card R024E)

Ester's 2026-10-05 feedback set both lists to title case and asked for
separate codes. That supersedes the earlier List of Figures sentence-case
reading of Q074. R024D and R024E stay distinct through their issue types.

Terminal punctuation is owned elsewhere: P053 (List of Tables), P054
(Table of Contents), and P040 (List of Figures).
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
    extract_toc_logical_entry_lines,
)

LINE_PREVIEW_MAX = 80
MIN_ENTRY_WORDS = 3

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

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'À-ɏ]*(?:-[A-Za-z][A-Za-z'À-ɏ]*)*")

_SCIENTIFIC_SEQUENCE_RE = re.compile(r"\b[A-Z]{4,}\b")
_GLUED_SCIENTIFIC_TOKEN_RE = re.compile(r"\b[a-z]{2,}[A-Z][A-Za-z]*")
_SCIENCE_NOMENCLATURE_RE = re.compile(
    r"(?:\b(?:peptide|protein|cytochrome|bradykinin|casein)\b|β|m/z)",
    re.IGNORECASE,
)
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


def _lot_title_case_is_unreliable(entry_text: str) -> bool:
    """True for LoT entries dominated by scientific nomenclature/extraction tokens.

    Protein/peptide sequences, m/z notation, Greek prefixes, and glued PDF text
    (forGATLFK/fromCytochrome) make ordinary title-case word heuristics unsafe.
    Require at least two independent signals so an ordinary title containing one
    scientific word still remains eligible for P024.
    """
    signal_count = 0
    if _SCIENTIFIC_SEQUENCE_RE.search(entry_text):
        signal_count += 1
    if _GLUED_SCIENTIFIC_TOKEN_RE.search(entry_text):
        signal_count += 1
    signal_count += min(2, len(_SCIENCE_NOMENCLATURE_RE.findall(entry_text)))
    return signal_count >= 2


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
            # The shared title tokenizer accepts straight apostrophes. PDF
            # text often uses a curly possessive apostrophe; normalize it
            # here so the trailing "s" is not treated as a separate word.
            issues = check_apa_title_case_phrase(entry_text.replace("\u2019", "'"))
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


_LIST_TITLE_CASE_SPECS: dict[str, tuple[str, str, str]] = {
    # page_type: (issue_type, list label, source Q-rule slot)
    "list_of_tables": ("list_of_tables_title_case", "List of Tables", "Q065"),
    "list_of_figures": ("list_of_figures_title_case", "List of Figures", "Q074"),
}


def _check_list_title_case_page(
    context: TocPageContext,
    entries: list[TocEntryLine],
) -> list[AuditFinding]:
    """Flag List of Tables / List of Figures entries that are not in title case.

    Both lists use the same title-case check; the issue type keeps them
    distinct (R024D for tables, R024E for figures).
    """
    issue_type, list_label, q_rule_id = _LIST_TITLE_CASE_SPECS[context.page_type]
    findings: list[AuditFinding] = []
    for entry_index, entry in enumerate(entries):
        raw = _clean_entry_text(entry)
        entry_text = _strip_list_prefix(raw)
        if not entry_text or len(entry_text) < 10:
            continue
        if len(tokenize_title_words(entry_text)) < MIN_ENTRY_WORDS:
            continue
        issues = []
        if not _lot_title_case_is_unreliable(entry_text):
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
                        f"{list_label} entry may have title-case issue: "
                        f"'{first['word']}' may need to be capitalized "
                        f"({first['reason']})."
                    ),
                    details={
                        "page_number": str(context.page.page_number),
                        "page_type": context.page_type,
                        "issue_type": issue_type,
                        "entry_index": str(entry_index),
                        "line_preview": entry.cleaned_text[:LINE_PREVIEW_MAX],
                        "bbox": format_bbox_detail(entry.line.bbox),
                        "expected_or_reason": first["reason"],
                        "confidence": first["confidence"],
                        "source_q_rule_id": q_rule_id,
                    },
                )
            )
    return findings


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def check_pdf_toc_list_formatting(pdf_document: PdfDocument) -> list[AuditFinding]:
    """Emit P024 warnings for TOC/LoT/LoF entry capitalization issues."""
    findings: list[AuditFinding] = []
    for context in detect_toc_like_pages(pdf_document):
        entries = extract_toc_logical_entry_lines(context)
        if context.page_type == "table_of_contents":
            findings.extend(_check_toc_page(context, entries))
        elif context.page_type in _LIST_TITLE_CASE_SPECS:
            findings.extend(_check_list_title_case_page(context, entries))
    return findings
