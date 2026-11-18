"""Heuristic TOC/List entry capitalization checks (P024).

Scope: TABLE OF CONTENTS, LIST OF TABLES, and LIST OF FIGURES pages only.
Not applied to body pages, references pages, or other front-matter pages.

Source: NJIT Thesis and Dissertation Formatting Guidelines;
        Titles Examples Level 1-5.docx; Self-Self Assessment Sheet.pdf
  - TOC Level 1 chapter/front-matter entries: ALL CAPS (Q049)
  - TOC Level 2 entries: Title Case (Q050)
  - TOC Level 3 entries: Sentence case (Q051; clear Title Case only)
  - List of Tables titles: Title Case (Q065; public card R024D)
  - List of Figures descriptions: Sentence case (Q074; public card R024E)

Ester's 2026-11-09 instruction restores sentence case for figure descriptions.
The existing list_of_figures_title_case subtype is retained as a compatibility
key for R024E; it now reports clear excess capitals, never lowercase major words.

Terminal punctuation is owned elsewhere: P053 (List of Tables), P054
(Table of Contents), and P040 (List of Figures).
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from statistics import median

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_layout import join_content_span_texts
from njit_auditor.pdf_models import PdfDocument, format_bbox_detail
from njit_auditor.rules.pdf_heading_levels import (
    _BODY_WORD_RE,
    _document_proper_nouns,
    _is_bold_line,
    _keeps_capital,
    _looks_like_title_case_violation,
)
from njit_auditor.rules.pdf_title_capitalization import (
    MINOR_WORDS,
    check_apa_title_case_phrase,
    is_minor_word,
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
from njit_auditor.rules.pdf_toc_entry_number_ordering import ambiguous_collapsed_subsections

LINE_PREVIEW_MAX = 80
MIN_ENTRY_WORDS = 3

# TOC level-classification patterns. An appendix letter occupies the chapter
# component: B.1 is level 2; B.1.7 is level 3. Explicit depth beats indentation.
_CHAPTER_RE = re.compile(r"^(?:chapter|appendix)\b", re.IGNORECASE)
_LEVEL2_NUM_RE = re.compile(r"^(?:[0-9]+|[A-Z])\.[0-9]+(?:\s|$)")
_LEVEL3_TITLE_RE = re.compile(r"^(?:[0-9]+|[A-Z])\.[0-9]+\.[0-9]+\s+(?P<title>.+)$")
_DEEPER_NUM_RE = re.compile(r"^(?:[0-9]+|[A-Z])(?:\.[0-9]+){3,}")
_SIMPLE_CAPITAL_WORD_RE = re.compile(r"^[A-Z][a-z]{2,}$")

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
    """Classify TOC entry level (1, 2, 3) or None if ambiguous."""
    text = entry.cleaned_text
    if _DEEPER_NUM_RE.match(text):
        return None
    if _LEVEL3_TITLE_RE.match(text):
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


def _prose_case_counts(
    pdf_document: PdfDocument, excluded_pages: set[int]
) -> dict[str, tuple[int, int]]:
    """Count lowercase and uppercase mid-sentence words in regular prose.

    This supports only two-word titles, which have just one noninitial word.
    A common lowercase prose word can establish its ordinary usage; a word
    repeatedly capitalized in prose stays ambiguous and is never changed.
    """
    lowercase: Counter[str] = Counter()
    uppercase: Counter[str] = Counter()
    for page in pdf_document.pages:
        if page.page_number in excluded_pages:
            continue
        for block in page.text_blocks:
            for line in block.lines:
                if _is_bold_line(line):
                    continue
                text = " ".join(join_content_span_texts(line.spans).split())
                for match in _BODY_WORD_RE.finditer(text):
                    before = text[: match.start()].rstrip()
                    if not before or before.endswith((".", "?", "!", ":")):
                        continue
                    word = match.group(1)
                    if word[0].islower():
                        lowercase[word.lower()] += 1
                    else:
                        uppercase[word.lower()] += 1
    return {
        word: (count, uppercase[word])
        for word, count in lowercase.items()
    }


def _level3_title_case_words(
    title: str,
    proper_nouns: frozenset[str],
    prose_case_counts: dict[str, tuple[int, int]],
) -> list[str]:
    """Return only clear ordinary-word capitals in a title-case-like L3 title.

    P027 supplies the established two-capital sentence-case signal and document
    proper-name evidence. For an exact two-word title, repeated lowercase
    body-prose usage supplies the missing independent signal. The token filter
    abstains on notation, acronyms, dotted abbreviations, hyphenated terms,
    and extraction debris.
    """
    words = title.split()
    capitalized: list[str] = []
    for index, word in enumerate(words[1:], start=1):
        if _keeps_capital(words, index, proper_nouns):
            continue
        core = word.strip(".,;:!?\"'()[]")
        core = unicodedata.normalize("NFKC", core)
        if (
            _SIMPLE_CAPITAL_WORD_RE.fullmatch(core)
            and not is_minor_word(core)
            and not looks_like_acronym(core)
        ):
            capitalized.append(core)
    if len(capitalized) >= 2 and _looks_like_title_case_violation(title, proper_nouns):
        return capitalized
    if (
        len(words) == 2
        and len(capitalized) == 1
        and not words[0].endswith((":", ";", ".", "?", "!"))
    ):
        lowercase_count, uppercase_count = prose_case_counts.get(capitalized[0].lower(), (0, 0))
        if lowercase_count >= 3 and uppercase_count <= 1:
            return capitalized
    return []


def _obvious_not_all_caps(text: str) -> bool:
    """Return True if text has >=2 lowercase-starting major words (implies not ALL CAPS)."""
    words = tokenize_title_words(text)
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
    proper_nouns: frozenset[str],
    prose_case_counts: dict[str, tuple[int, int]],
) -> list[AuditFinding]:
    findings: list[AuditFinding] = []
    if len(entries) < 3:
        return findings
    ambiguous = ambiguous_collapsed_subsections(entries)
    indent_clusters = _build_indent_clusters(entries)
    page_number_edges = [
        entry.page_number_right_x for entry in entries
        if entry.page_number_token and entry.page_number_right_x is not None
    ]
    page_number_edge = median(page_number_edges) if len(page_number_edges) >= 3 else None
    for entry_index, entry in enumerate(entries):
        if entry_index in ambiguous:
            continue  # P060 owns the structural review before case advice.
        entry_text = _clean_entry_text(entry)
        if not entry_text or len(entry_text) < 8:
            continue
        level = _classify_toc_level(entry, indent_clusters)
        if level is None:
            continue
        min_words = 2 if level == 3 else MIN_ENTRY_WORDS
        if len(tokenize_title_words(entry_text)) < min_words:
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
                            "suggested_fix": "Use ALL CAPS for this Level 1 TOC entry.",
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
                            "suggested_fix": "Use Title Case for this Level 2 TOC entry.",
                        },
                    )
                )
        elif level == 3:
            match = _LEVEL3_TITLE_RE.match(entry_text)
            if (
                match is None
                or not entry.page_number_token
                or entry.page_number_right_x is None
                or page_number_edge is None
                or abs(entry.page_number_right_x - page_number_edge) > 12.0
            ):
                continue
            capitalized = _level3_title_case_words(
                match.group("title"), proper_nouns, prose_case_counts
            )
            if not capitalized:
                continue
            findings.append(AuditFinding(
                rule_id="P024",
                severity=Severity.WARNING,
                page=context.page.page_number,
                message=(
                    "A level-3 Table of Contents entry appears to use Title Case "
                    "where NJIT requires sentence case."
                ),
                details={
                    "page_number": str(context.page.page_number),
                    "page_type": "table_of_contents",
                    "issue_type": "toc_level_capitalization",
                    "entry_level": "3",
                    "entry_index": str(entry_index),
                    "line_preview": entry.cleaned_text[:LINE_PREVIEW_MAX],
                    "bbox": format_bbox_detail(entry.line.bbox),
                    "expected_or_reason": "Level 3 TOC entries expected sentence case",
                    "capitalized_major_word_count": str(len(capitalized)),
                    "confidence": "medium",
                    "source_q_rule_id": "Q051",
                    "suggested_fix": (
                        "Use sentence case: capitalize the first word and proper "
                        "names; keep acronyms and technical notation."
                    ),
                },
            ))
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


def _figure_title_case_words(
    sentence: str, proper_nouns: frozenset[str], prose_case_counts: dict[str, tuple[int, int]],
) -> list[str]:
    # Long descriptions can contain named techniques and acronym expansions.
    # Only a clear Title Case sentence supports a case correction without
    # guessing whether isolated internal capitals are names or technical terms.
    words = tokenize_title_words(sentence)
    if any(word[0].islower() and not is_minor_word(word) and not looks_like_acronym(word)
           for word in words[1:]):
        return []
    return _level3_title_case_words(sentence, proper_nouns, prose_case_counts)


def _check_list_case_page(
    context: TocPageContext,
    entries: list[TocEntryLine],
    proper_nouns: frozenset[str],
    prose_case_counts: dict[str, tuple[int, int]],
) -> list[AuditFinding]:
    """Check table titles and figure descriptions with their respective case policy."""
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
            issues = check_apa_title_case_phrase(
                entry_text, skip_hyphenated_fragments=True
            )
        is_figure = context.page_type == "list_of_figures"
        if is_figure:
            # Remove a numeric-only label too: it is not the first word of the
            # description. Numeric-only LoF labels are valid (Ester 2026-11-17).
            description = _LIST_ENTRY_NUMBER_RE.sub("", entry_text).lstrip(" .):-")
            capitalized = [
                word for sentence in re.split(
                    r"(?<=[.!?])\s+|(?:\([a-z]\)|\b[a-z]\))\s*", description
                )
                for word in _figure_title_case_words(sentence, proper_nouns, prose_case_counts)
            ]
            issues = ([{"word": capitalized[0], "reason": "figure_description_sentence_case",
                        "confidence": "medium"}] if capitalized else [])
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
            details["suggested_fix"] = (
                "Use sentence case for this figure description; "
                "preserve proper names, acronyms and notation."
                if is_figure else "Use Title Case for this table title."
            )
            if continuations:
                details["wrapped_line_count"] = str(1 + len(continuations))
            findings.append(
                AuditFinding(
                    rule_id="P024",
                    severity=Severity.WARNING,
                    page=context.page.page_number,
                    message=(
                        "List of Figures description appears to use Title Case; use sentence case."
                        if is_figure else
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
    proper_nouns: frozenset[str] | None = None
    prose_case_counts: dict[str, tuple[int, int]] | None = None
    contexts = detect_toc_like_pages(pdf_document)
    excluded_pages = {context.page.page_number for context in contexts}
    for context in contexts:
        entries = extract_toc_logical_entry_lines(context)
        if context.page_type == "table_of_contents":
            if proper_nouns is None:
                proper_nouns = _document_proper_nouns(pdf_document)
                prose_case_counts = _prose_case_counts(pdf_document, excluded_pages)
            findings.extend(_check_toc_page(
                context, entries, proper_nouns, prose_case_counts or {}
            ))
        elif context.page_type in _LIST_TITLE_CASE_SPECS:
            if proper_nouns is None:
                proper_nouns = _document_proper_nouns(pdf_document)
                prose_case_counts = _prose_case_counts(pdf_document, excluded_pages)
            findings.extend(_check_list_case_page(
                context, entries, proper_nouns, prose_case_counts or {}
            ))
    return findings
