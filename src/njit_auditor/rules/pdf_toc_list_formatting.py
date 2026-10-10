"""Heuristic TOC/List entry capitalization checks (P024).

Scope: TABLE OF CONTENTS, LIST OF TABLES, and LIST OF FIGURES pages only.
Not applied to body pages, references pages, or other front-matter pages.

Source: NJIT Thesis and Dissertation Formatting Guidelines;
        Titles Examples Level 1-5.docx; Self-Self Assessment Sheet.pdf
  - TOC Level 1 chapter/front-matter entries: ALL CAPS (Q049)
  - TOC Level 2 entries: Title Case (Q050)
  - TOC Level 3 entries: Sentence case (Q051)
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
from njit_auditor.rules.pdf_heading_levels import (
    _document_proper_nouns,
    _looks_like_title_case_violation,
)
from njit_auditor.rules.pdf_title_capitalization import (
    MINOR_WORDS,
    check_apa_title_case_phrase,
    looks_like_acronym,
    normalize_title_text,
    tokenize_title_words,
)
from njit_auditor.rules.pdf_toc_alignment import (
    INDENT_CLUSTER_TOLERANCE_PT,
    LOGICAL_WRAP_MIN_INDENT_PT,
    LOGICAL_WRAP_Y_GAP_PT,
    TocEntryLine,
    TocPageContext,
    detect_toc_like_pages,
    extract_toc_logical_entry_lines,
)

LINE_PREVIEW_MAX = 80
MIN_ENTRY_WORDS = 3

# TOC level-classification patterns.
_CHAPTER_RE = re.compile(r"^(?:chapter|appendix)\b", re.IGNORECASE)
_NUMBERED_SECTION_RE = re.compile(r"^([0-9]+(?:\.[0-9]+)*)\s+(.+)$")

# List-entry prefix: "Table 1." / "Figure 2." etc.
_LIST_PREFIX_RE = re.compile(
    r"^(?:table|fig(?:ure)?\.?)\s+[0-9]+(?:[.\-][0-9]+)?\s*[.):]?\s*",
    re.IGNORECASE,
)

# Leader dots: 2+ dots with optional whitespace between them (not a single terminal period).
_LEADER_STRIP_RE = re.compile(r"\s*(?:\.\s*){2,}$")

_TERMINAL_PERIOD_RE = re.compile(r"\.\s*$")

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
    """Classify TOC entry level, preserving the exact numbered depth."""
    text = entry.cleaned_text
    numbered = _NUMBERED_SECTION_RE.match(text)
    if numbered:
        return numbered.group(1).count(".") + 1
    # A malformed numeric prefix cannot safely inherit its level from indent.
    if text and text[0].isdigit():
        return None
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
    words = tokenize_title_words(text)
    lowercase_major = [
        w
        for w in words
        if len(w) > 3
        and w.lower() not in MINOR_WORDS
        and not looks_like_acronym(w)
        and w[0].islower()
    ]
    return len(lowercase_major) >= 2


def _toc_sentence_case_issue(
    title: str, proper_nouns: frozenset[str], lowercase_prose: frozenset[str]
) -> bool:
    """Require a strong title-case pattern or a two-word prose-confirmed one.

    The body heading check supplies the conservative multi-capital heuristic.
    A two-word title has only one noninitial word, so accept that case only
    when the same word occurs lowercase in the document's prose.
    """
    words = title.split()
    # The first word of a subtitle may be capitalized in sentence case.
    for index in range(1, len(words)):
        if words[index - 1].endswith(":") and words[index].istitle():
            words[index] = words[index][0].lower() + words[index][1:]
    if _looks_like_title_case_violation(" ".join(words), proper_nouns):
        return True
    if len(words) != 2:
        return False
    # Sentence case may capitalize the first word after a subtitle colon.
    if words[0].endswith(":"):
        return False
    # A named modifier can make a two-word technical term legitimate.
    if words[0].strip(".,;:!?\"'()-[]").lower() in proper_nouns:
        return False
    second = words[1].strip(".,;:!?\"'()-[]")
    return (
        len(second) > 3
        and second.istitle()
        and second.lower() not in proper_nouns
        and second.lower() in lowercase_prose
        and not looks_like_acronym(second)
    )


def _lowercase_prose_words(pdf_document: PdfDocument) -> frozenset[str]:
    """Collect lowercase words from non-bold, non-TOC prose lines."""
    toc_pages = {c.page.page_number for c in detect_toc_like_pages(pdf_document)}
    words: set[str] = set()
    for page in pdf_document.pages:
        if page.page_number in toc_pages:
            continue
        for block in page.text_blocks:
            for line in block.lines:
                if any(span.bold for span in line.spans):
                    continue
                words.update(w.lower() for w in re.findall(r"\b[a-z]{4,}\b", line.text))
    return frozenset(words)


# ---------------------------------------------------------------------------
# Page-level checks
# ---------------------------------------------------------------------------


def _check_toc_page(
    context: TocPageContext,
    entries: list[TocEntryLine],
    proper_nouns: frozenset[str] = frozenset(),
    lowercase_prose: frozenset[str] = frozenset(),
) -> list[AuditFinding]:
    findings: list[AuditFinding] = []
    if len(entries) < 3:
        return findings
    indent_clusters = _build_indent_clusters(entries)
    for entry_index, entry in enumerate(entries):
        entry_text = _clean_entry_text(entry)
        if not entry_text or len(entry_text) < 8:
            continue
        level = _classify_toc_level(entry, indent_clusters)
        if level is None:
            continue
        if level != 3 and len(tokenize_title_words(entry_text)) < MIN_ENTRY_WORDS:
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
        elif level == 3:
            numbered = _NUMBERED_SECTION_RE.match(entry_text)
            if not numbered or not entry.page_number_token:
                continue
            title = numbered.group(2).strip()
            if _toc_sentence_case_issue(title, proper_nouns, lowercase_prose):
                findings.append(
                    AuditFinding(
                        rule_id="P024",
                        severity=Severity.WARNING,
                        page=context.page.page_number,
                        message=(
                            "TOC Level 3 title appears to use title case. "
                            "Use sentence case, retaining proper names, acronyms, "
                            "and technical notation."
                        ),
                        details={
                            "page_number": str(context.page.page_number),
                            "page_type": "table_of_contents",
                            "issue_type": "toc_level_capitalization",
                            "entry_level": "3",
                            "entry_index": str(entry_index),
                            "line_preview": entry.cleaned_text[:LINE_PREVIEW_MAX],
                            "bbox": format_bbox_detail(entry.line.bbox),
                            "expected_or_reason": "Level 3 TOC titles use sentence case",
                            "suggested_fix": (
                                "Use sentence case for this level-3 TOC title; retain proper "
                                "names, acronyms and technical terms."
                            ),
                            "confidence": "medium",
                            "source_q_rule_id": "Q051",
                        },
                    )
                )
    return findings


_LIST_TITLE_CASE_SPECS: dict[str, tuple[str, str, str]] = {
    # page_type: (issue_type, list label, source Q-rule slot)
    "list_of_tables": ("list_of_tables_title_case", "List of Tables", "Q065"),
    "list_of_figures": ("list_of_figures_title_case", "List of Figures", "Q074"),
}

# A list entry begins with its number ("3.2", "3.2Title" when the extractor
# glues the spans) or a "Table"/"Figure" label.
_LIST_ENTRY_NUMBER_RE = re.compile(
    r"^\s*(?:(?:table|fig(?:ure)?\.?)\s*)?\d+(?:[.\-]\d+)*", re.IGNORECASE
)


def _group_wrapped_list_entries(
    entries: list[TocEntryLine],
) -> list[tuple[int, TocEntryLine, list[TocEntryLine]]]:
    """Group list rows into semantic entries: (head index, head, continuations).

    A row is a wrapped line of the entry above it when it has no entry
    number, is indented past the page's entry-start column, sits directly
    below the previous row, and that previous row has not already closed its
    entry with a numeric page number. The shared logical-entry repair only
    rejoins wraps that end on a recognizable page number, so long
    multi-panel captions and captions whose first row picked up a bogus page
    token arrive here as separate rows. Grouping them stops one title from
    being checked, and reported, once per physical line.
    """
    numbered_x = [e.indent_x for e in entries if _LIST_ENTRY_NUMBER_RE.match(e.cleaned_text)]
    if not numbered_x:
        return [(index, entry, []) for index, entry in enumerate(entries)]
    entry_start_x = min(numbered_x)

    groups: list[tuple[int, TocEntryLine, list[TocEntryLine]]] = []
    previous: TocEntryLine | None = None
    for index, entry in enumerate(entries):
        # Logical entries carry the union bbox of their rows, so compare
        # bottoms: for one-row entries this is the usual top-to-top step.
        is_continuation = (
            previous is not None
            and bool(groups)
            and not (previous.page_number_token or "").isdigit()
            and not _LIST_ENTRY_NUMBER_RE.match(entry.cleaned_text)
            and entry.indent_x >= entry_start_x + LOGICAL_WRAP_MIN_INDENT_PT
            and 0 < entry.line.bbox.y1 - previous.line.bbox.y1 <= LOGICAL_WRAP_Y_GAP_PT
        )
        if is_continuation:
            groups[-1][2].append(entry)
        else:
            groups.append((index, entry, []))
        previous = entry
    return groups


def _explanatory_issue(issues: list[dict[str, str]]) -> dict[str, str]:
    """Pick the issue whose word best explains the finding to a student.

    Prefer an ordinary lowercase word over a panel label ("a)"), a formula
    fragment, or a mixed-case unit ("pH"). Only the quoted word changes;
    the finding itself is decided by whether any issue exists.
    """
    for issue in issues:
        word = issue["word"]
        if len(word) >= 3 and word.isalpha() and word.islower():
            return issue
    return issues[0]


def _check_list_title_case_page(
    context: TocPageContext,
    entries: list[TocEntryLine],
) -> list[AuditFinding]:
    """Flag List of Tables / List of Figures entries that are not in title case.

    Both lists use the same title-case check; the issue type keeps them
    distinct (R024D for tables, R024E for figures). Wrapped rows are joined
    to their entry first, so each entry is checked and reported once.
    """
    issue_type, list_label, q_rule_id = _LIST_TITLE_CASE_SPECS[context.page_type]
    findings: list[AuditFinding] = []
    for entry_index, entry, continuations in _group_wrapped_list_entries(entries):
        head_text = _strip_list_prefix(_clean_entry_text(entry))
        raw = " ".join(_clean_entry_text(row) for row in (entry, *continuations))
        entry_text = _strip_list_prefix(normalize_title_text(raw))
        if not entry_text or len(entry_text) < 10:
            continue
        if len(tokenize_title_words(entry_text)) < MIN_ENTRY_WORDS:
            continue
        issues = []
        # Judge scientific-nomenclature reliability on the entry's first
        # row, as before grouping: long wrapped panel descriptions add enough
        # nomenclature signals to hide a title that is plainly not title case.
        if not _lot_title_case_is_unreliable(head_text):
            issues = check_apa_title_case_phrase(entry_text, skip_hyphenated_fragments=True)
        if issues:
            first = _explanatory_issue(issues)
            details = {
                "page_number": str(context.page.page_number),
                "page_type": context.page_type,
                "issue_type": issue_type,
                "entry_index": str(entry_index),
                "line_preview": entry.cleaned_text[:LINE_PREVIEW_MAX],
                "bbox": format_bbox_detail(entry.line.bbox),
                "expected_or_reason": first["reason"],
                "confidence": first["confidence"],
                "source_q_rule_id": q_rule_id,
            }
            if continuations:
                details["wrapped_line_count"] = str(1 + len(continuations))
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
                    details=details,
                )
            )
    return findings


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def check_pdf_toc_list_formatting(pdf_document: PdfDocument) -> list[AuditFinding]:
    """Emit P024 warnings for TOC/LoT/LoF entry capitalization issues."""
    findings: list[AuditFinding] = []
    proper_nouns = _document_proper_nouns(pdf_document)
    lowercase_prose = _lowercase_prose_words(pdf_document)
    for context in detect_toc_like_pages(pdf_document):
        entries = extract_toc_logical_entry_lines(context)
        if context.page_type == "table_of_contents":
            findings.extend(_check_toc_page(context, entries, proper_nouns, lowercase_prose))
        elif context.page_type in _LIST_TITLE_CASE_SPECS:
            findings.extend(_check_list_title_case_page(context, entries))
    return findings
