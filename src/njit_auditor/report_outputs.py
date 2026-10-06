"""Structured JSON/Markdown output helpers for audit findings."""

from __future__ import annotations

import json
import re
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from njit_auditor.evaluation import map_finding_rule_to_category
from njit_auditor.issue_type_explanations import humanize_issue_type
from njit_auditor.models import AuditFinding, Severity
from njit_auditor.page_number_student_preview import classify_visible_page_number_issue

MAX_DETAIL_TEXT_LEN = 120
# Rules with this many or more findings appear in high_volume_rules summary.
HIGH_VOLUME_THRESHOLD = 5
# Maximum page-range segments shown in compact page lists before truncation.
_MAX_COMPACT_RANGES = 8
P013_RULE_ID = "P013"
P013_PAGE_ISSUE_TYPE = "page_number_candidate"
P013_DOC_ISSUE_TYPE = "p013_document_overview"
P026_RULE_ID = "P026"
P026_FAMILY_ISSUE_TYPE = "possible_body_font_family_issue"
P026_SIZE_ISSUE_TYPE = "possible_body_font_size_issue"
P011_RULE_ID = "P011"
P011_ISSUE_TYPE = "margin_boundary_violation"
P012_RULE_ID = "P012"
P012_ISSUE_TYPE = "pdf_annotation_detected"
P019_RULE_ID = "P019"
P036_RULE_ID = "P036"
P038_RULE_ID = "P038"
P044_RULE_ID = "P044"
_REPEATED_PROBLEM_CONTEXT_KEYS: tuple[str, ...] = (
    "side",
    "annotation_type",
    "position_type",
    "number_style",
    "section_type",
    "p019_triage_category",
    "source_q_rule_id",
    "source_q_rule",
    "expected_heading",
    "expected_phrase",
    "expected_value",
    "actual_value",
    "expected_label",
    "actual_label",
    "command",
    "environment",
    "issue_subtype",
    "candidate_count_on_page",
    "paragraph_index",
    "source_file",
)
_RULE_SPECIFIC_GROUPING_KEYS: dict[str, tuple[str, ...]] = {
    "P013": ("observed_summary",),
    "P026": ("observed_summary",),
}
_ROMAN_LABEL_RE = re.compile(r"^[ivxlcdm]+$", re.IGNORECASE)


def _truncate(value: str, max_len: int = MAX_DETAIL_TEXT_LEN) -> str:
    if len(value) <= max_len:
        return value
    return f"{value[: max_len - 3]}..."


# Detail keys that hold several already-short, "|"-joined preview snippets
# (each individually capped by its own detector -- e.g. P011's
# affected_line_texts truncates each line to 60 chars before joining) get a
# dedicated item-boundary-safe truncation instead of the generic single-value
# cap below: (max_total_chars, max_item_count). This is deliberately *not* a
# blanket exemption from size limits -- it still bounds both the total
# exported size and the item count, so a malformed/adversarial PDF producing
# an unusually large details dict cannot inflate the report payload. It only
# changes *where* truncation is allowed to cut: never through the middle of
# an already-short preview snippet, only by dropping whole trailing items.
_MULTI_ITEM_DETAIL_LIMITS: dict[str, tuple[int, int]] = {
    "affected_line_texts": (340, 6),
    # bbox-family keys hold " | "-joined "x0,y0,x1,y1" coordinate groups
    # (e.g. P011's per-group highlight_bboxes) that can exceed the generic
    # 120-char cap on pages with 5+ separated violation groups. Each box is
    # ~20-30 chars, so (1200, 40) comfortably covers realistic pages while
    # still bounding total exported size against a malformed/adversarial PDF.
    "highlight_bboxes": (1200, 40),
    "margin_boundary_bboxes": (1200, 40),
    "overflow_display_bboxes": (1200, 40),
    "overflow_segment_bboxes": (1200, 40),
}
_MULTI_ITEM_SEPARATOR = " | "
_INTERNAL_STUDENT_EXPORT_DETAIL_KEYS: frozenset[str] = frozenset(
    {
        "source_q_rule_id",
        "source_q_rule_ids",
        "source_q_rule",
        "source_q_rule_basis",
    }
)


def _truncate_pipe_joined(value: str, *, max_len: int, max_items: int) -> str:
    """Truncate a ``" | "``-joined multi-item string at item boundaries only.

    Never cuts a surviving item's text short -- an item is either included
    whole or dropped entirely, so downstream numbered-list formatting never
    displays a truncated fragment as if it were a complete snippet.
    """
    items = value.split(_MULTI_ITEM_SEPARATOR)[:max_items]
    kept: list[str] = []
    total = 0
    for item in items:
        added = len(item) if not kept else len(_MULTI_ITEM_SEPARATOR) + len(item)
        if total + added > max_len:
            break
        kept.append(item)
        total += added
    # Always keep at least the first item, even if it alone exceeds max_len,
    # so a single long snippet degrades to one (safely char-truncated) item
    # rather than disappearing entirely.
    if not kept and items:
        kept = [_truncate(items[0], max_len)]
    return _MULTI_ITEM_SEPARATOR.join(kept)


def _sanitize_details(details: dict[str, str]) -> dict[str, str]:
    sanitized: dict[str, str] = {}
    for key, value in details.items():
        if key in _INTERNAL_STUDENT_EXPORT_DETAIL_KEYS:
            continue
        text = str(value)
        limits = _MULTI_ITEM_DETAIL_LIMITS.get(key)
        if limits is not None:
            max_len, max_items = limits
            sanitized[key] = _truncate_pipe_joined(text, max_len=max_len, max_items=max_items)
        else:
            sanitized[key] = _truncate(text)
    return sanitized


def _student_export_role(rule_id: str, details: dict[str, str]) -> tuple[bool, str]:
    """Return whether an exported finding is a student-visible problem and its role.

    P013 page-number candidates are detector evidence, not violations by
    themselves. Keep them in the raw export for compatibility, but label their
    role explicitly so JSON consumers do not treat routine candidates as warning
    cards.
    """
    issue_type = details.get("issue_type", "").strip()
    if rule_id == P013_RULE_ID:
        visible_issue_type, is_visible = classify_visible_page_number_issue(
            rule_id, issue_type, details
        )
        if not is_visible:
            if issue_type == P013_DOC_ISSUE_TYPE:
                return False, "internal_summary"
            return False, "inventory"
        if visible_issue_type:
            return True, "problem"
    return True, "problem"


def _severity_counts(findings: list[AuditFinding]) -> dict[str, int]:
    counts = Counter(finding.severity.value for finding in findings)
    return {
        Severity.PASS.value: counts.get(Severity.PASS.value, 0),
        Severity.WARNING.value: counts.get(Severity.WARNING.value, 0),
        Severity.FAIL.value: counts.get(Severity.FAIL.value, 0),
    }


def _rule_counts(findings: list[AuditFinding]) -> dict[str, int]:
    counts = Counter(finding.rule_id for finding in findings)
    return dict(sorted(counts.items()))


def _category_counts(findings: list[AuditFinding]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for finding in findings:
        counts[map_finding_rule_to_category(finding.rule_id, finding.details)] += 1
    return dict(sorted(counts.items()))


# Student-facing display labels for the coarse comparison categories returned by
# map_finding_rule_to_category(). Shared by the web app's category chips/labels
# and by the plain-text student report's "Section" field.
CATEGORY_DISPLAY_LABELS: dict[str, str] = {
    "abstract_language": "Abstract language",
    "abstract_length": "Abstract length",
    "abstract_structure": "Abstract structure",
    "annotations": "Annotations / comments",
    "capitalization_case": "Capitalization",
    "committee_approval_page": "Approval page",
    "copyright_page_metadata": "Copyright page",
    "figure_format": "Figure formatting",
    "figure_table_format": "Figures / tables",
    "font_format": "Font formatting",
    "formatting_override": "Formatting overrides",
    "frontmatter_structure": "Front matter / appendix structure",
    "heading_title": "Headings / titles",
    "indentation": "Indentation",
    "labels_references": "Labels / cross-references",
    "latex_linter": "LaTeX linting",
    "list_of_tables_figures_toc": "TOC / lists",
    "margin_or_overflow": "Margins / overflow",
    "page_numbering": "Page numbering",
    "punctuation": "Punctuation",
    "references_citations": "References / citations",
    "spacing_blank_lines": "Spacing / blank lines",
    "table_format": "Table formatting",
    "title_page_metadata": "Title page",
}


def category_display_label(category: str) -> str:
    """Return a student-friendly display label for a raw category key."""
    return CATEGORY_DISPLAY_LABELS.get(str(category), str(category).replace("_", " ").capitalize())


# ---------------------------------------------------------------------------
# Public/student-facing rule text sanitization (shared by the /rules page and
# the plain-text student report's de-truncated remediation text).
# ---------------------------------------------------------------------------

_HEURISTIC_WORDING = [
    # Order matters: collapse the "heuristic check" bigram first so it
    # doesn't end up as the doubled-up "check check".
    (re.compile(r"\bHeuristic check\b"), "Automated check"),
    (re.compile(r"\bheuristic check\b"), "automated check"),
    (re.compile(r"\bHeuristically\b"), "Automatically"),
    (re.compile(r"\bheuristically\b"), "automatically"),
    (re.compile(r"\bHeuristics\b"), "Checks"),
    (re.compile(r"\bheuristics\b"), "checks"),
    (re.compile(r"\bHeuristic\b"), "Check"),
    (re.compile(r"\bheuristic\b"), "check"),
]

# A handful of canonical rule_definition/remediation strings reference
# LaTeX-specific authoring/implementation detail (e.g. LaTeX-only remediation
# commands, "implemented for both LaTeX source and compiled PDF"). This
# website only ever runs the PDF path, so those mentions are confusing here.
# Override just the public display text for those entries — the canonical
# rule data on disk (used by the CLI's source audit) is left untouched.
_RULE_TEXT_OVERRIDES: dict[str, dict[str, str]] = {
    "P011": {
        "question": (
            "Is all text (including tables and figures) contained entirely within "
            "the required page margins?"
        ),
        "remediation": (
            "Set left margin to 1.5 inches and top, bottom, and right margin to "
            "1 inch."
        ),
    },
    "P021": {
        "rule_definition": (
            "PhD abstract maximum: 400 words. MS/Master abstract maximum: 200 "
            "words. Degree type is inferred from the document text. Word count "
            "uses conservative tokenization (letter-containing tokens only)."
        ),
    },
    "P023": {
        "question": (
            "Is body text double-spaced, except for tables, figure descriptions, "
            "bullet points, and multi-line titles?"
        ),
        "remediation": (
            "Apply double spacing to body text. Keep tables, figure descriptions, "
            "bullet points, and multi-line titles single-spaced."
        ),
    },
    "P026": {
        "rule_definition": (
            "NJIT guidelines require body text to use an accepted font family and 12pt size. "
            "Word documents should use Times New Roman or Arial. Documents prepared with "
            "common thesis templates often use Computer Modern or Latin Modern, which are "
            "also accepted. "
            "This check looks at ordinary body-text spans on each page for "
            "(A) font size outside 11.0-13.0pt and (B) font family outside accepted "
            "families (Times New Roman, Arial, Computer Modern, Latin Modern, and "
            "common near-equivalent serifs)."
        ),
        "remediation": (
            "Word users: set body text to Times New Roman or Arial at 12pt. "
            "For documents prepared with common thesis templates, Computer Modern or "
            "Latin Modern are accepted."
        ),
    },
    "P028": {
        "rule_definition": (
            "NJIT requires front-matter pages that show page numbers to use "
            "lowercase Roman numerals (i, ii, iii, ...) and main-body pages "
            "to use Arabic numerals (1, 2, 3, ...). This rule detects the "
            "front-matter and body regions from named headings and "
            "chapter/body heading detection, then checks that detected "
            "page-number candidates match the expected style for their "
            "region. Pages that should show no page number at all "
            "(Abstract, Approval Page, Title page) are excluded and are "
            "covered by a separate check."
        ),
        "remediation": (
            "Use lowercase Roman numerals for numbered front-matter pages, "
            "and use Arabic numerals for body pages."
        ),
    },
    "P029": {
        "question": (
            "Do visible lowercase Roman numerals in the front matter appear "
            "in a continuous increasing sequence?"
        ),
        "remediation": (
            "Correct the front-matter Roman numeral page numbers so they "
            "increase continuously in order."
        ),
    },
    "P043": {
        "question": (
            "Does the Acknowledgements page follow the correct paragraph "
            "indentation style: first paragraph flush-left and subsequent "
            "paragraphs indented?"
        ),
        "rule_definition": (
            "Detects the Acknowledgements page and extracts its body "
            "paragraphs. Checks that the first paragraph's first line is "
            "flush-left with the page's left margin, and that each "
            "subsequent paragraph's first line is indented relative to "
            "that margin. Skips pages where the Acknowledgements heading "
            "is not detected or fewer than 2 paragraphs are found. "
            "Complements the general indentation check, which may miss "
            "short Acknowledgements pages due to conservative thresholds. "
            "Findings contain only geometry metadata -- no paragraph text."
        ),
        "remediation": (
            "Remove any first-line indent from the first Acknowledgements "
            "paragraph, and apply a first-line indent to each subsequent "
            "Acknowledgements paragraph."
        ),
    },
    "P044": {
        "question": (
            "Does the Abstract page follow the correct paragraph "
            "indentation style: first paragraph flush-left and subsequent "
            "paragraphs indented?"
        ),
        "rule_definition": (
            "Detects the Abstract page and extracts its body paragraphs. "
            "Checks that the first paragraph's first line is flush-left "
            "with the page's left margin, and that each subsequent "
            "paragraph's first line is indented relative to that margin. "
            "Skips pages where the Abstract page is not detected; skips "
            "the subsequent-paragraph check if fewer than 2 paragraphs are "
            "found. Complements the general indentation check, which "
            "partially covers the abstract opening but not subsequent "
            "paragraphs. Findings contain only geometry metadata -- no "
            "paragraph text."
        ),
        "remediation": (
            "Remove any first-line indent from the first Abstract "
            "paragraph, and apply a first-line indent to each subsequent "
            "Abstract paragraph."
        ),
    },
    "P013": {
        "question": (
            "Are all visible page numbers located exactly in the designated "
            "bottom-center position?"
        ),
        "rule_definition": (
            "Detect text that looks like a page number and record its position "
            "and style so it can be checked manually. This is a verification "
            "signal, not a confirmed formatting defect by itself — see the "
            "page-number sequence/style and page-numbering-regime rules for "
            "findings that flag a specific page-numbering problem. "
            "NJIT requires page numbers at the bottom center of the page, "
            "0.5 inches from the bottom edge."
        ),
        "remediation": (
            "Set page numbers at the bottom center of the page, 0.5 inches "
            "from the bottom edge."
        ),
    },
    "P030": {
        "question": (
            "Do continuation pages of a multi-page Table of Contents, List of "
            "Tables, or List of Figures include the correct continued heading?"
        ),
        "remediation": (
            "Add the correct continued heading on each continuation page, such "
            "as \"TABLE OF CONTENTS (Continued),\" \"LIST OF TABLES "
            "(Continued),\" or \"LIST OF FIGURES (Continued).\""
        ),
    },
    "P050": {
        "question": (
            "Is the left-column header, \"Table\" or \"Figure,\" formatted in "
            "bold in the List of Tables or List of Figures?"
        ),
        "rule_definition": (
            "Conservative check: detects List of Tables/List of Figures "
            "pages with at least 3 entries whose page-number position is "
            "confidently detected. Locates the left-column header label "
            "('Table' for the List of Tables, 'Figure' for the List of "
            "Figures) in the expected header zone. If the header text is "
            "reliably detected as not bold, flags a bold-style issue. "
            "Skips pages without a detected left header, sparse pages, "
            "image-only pages, and pages where font metadata is "
            "unavailable or ambiguous. Findings contain style metadata "
            "only -- no entry text, captions, titles, header text, or "
            "private content."
        ),
        "remediation": (
            "Format the \"Table\" or \"Figure\" column header in bold."
        ),
    },
    "P031": {
        "question": (
            "Do List of Tables and List of Figures pages show the required "
            "\"Table\" or \"Figure\" and \"Page\" column headers?"
        ),
        "remediation": (
            "Add the required column headers directly below the list heading: "
            "\"Table\" or \"Figure\" on the left and \"Page\" on the right."
        ),
    },
    "P032": {
        "question": (
            "Are wrapped Table of Contents, List of Tables, and List of Figures "
            "entries single-spaced within the same entry?"
        ),
        "remediation": (
            "Single-space wrapped TOC, List of Tables, and List of Figures "
            "entries so continuation lines stay within the same entry without "
            "extra blank space."
        ),
    },
    "P036": {
        "question": (
            "Is there visible double spacing or a blank line between consecutive "
            "TOC, List of Tables, or List of Figures entries?"
        ),
        "remediation": (
            "Add visible double spacing or a blank line between consecutive "
            "entries in the TOC, List of Tables, or List of Figures."
        ),
    },
    "P039": {
        "question": (
            "Are level-2 and level-3 Table of Contents entries indented to "
            "show hierarchy?"
        ),
        "remediation": (
            "Indent level-2 TOC entries to the right of level-1 entries, and "
            "indent level-3 entries further to the right of level-2 entries."
        ),
    },
    "P040": {
        "question": (
            "Does every figure description in the List of Figures end with "
            "terminal punctuation?"
        ),
        "remediation": (
            "Add terminal punctuation, such as a period, question mark, or "
            "exclamation point, to every figure description in the List of "
            "Figures."
        ),
    },
    "P046": {
        "question": (
            "Are all table numbers in the List of Tables and all figure numbers "
            "in the List of Figures aligned vertically in one left column?"
        ),
        "remediation": (
            "Align all table numbers in the List of Tables and all figure "
            "numbers in the List of Figures into one consistent left column."
        ),
    },
    "P048": {
        "question": (
            "Are all page numbers in the List of Tables and List of Figures "
            "aligned vertically in one right column?"
        ),
        "remediation": (
            "Align all page numbers in the List of Tables and List of Figures "
            "into one consistent right column."
        ),
    },
    "P049": {
        "question": (
            "Is the \"Page\" column header in the List of Tables or List of "
            "Figures bold and right-aligned over the page-number column?"
        ),
        "rule_definition": (
            "Conservative check: detects List of Tables/List of Figures "
            "pages with at least 3 entries whose page-number position is "
            "confidently detected. Derives the expected right-column "
            "position from the median position of those entries. Locates "
            "the 'Page' header label in the expected header zone. If the "
            "header's right edge deviates from the expected position by "
            "more than about 25pt, flags a right-alignment issue. If the "
            "header text is reliably detected as not bold, flags a "
            "bold-style issue. Skips pages without a detected 'Page' "
            "header. Findings contain geometry and style metadata only -- "
            "no entry text, captions, titles, or private content."
        ),
        "remediation": (
            "Format the \"Page\" column header in bold and align it over the "
            "page-number column on the right."
        ),
    },
    "P041": {
        "question": (
            "Is there no header text in the top margin area of the Dedication page?"
        ),
        "remediation": (
            "Remove any running header or header text from the top margin area "
            "of the Dedication page."
        ),
    },
    "P042": {
        "question": (
            "Are appendix entries in the Table of Contents formatted correctly "
            "for a single appendix or multiple appendices?"
        ),
        "remediation": (
            "For one appendix, begin the TOC entry with \"APPENDIX\" followed "
            "by the title. For multiple appendices, label each TOC entry with a "
            "letter, such as \"APPENDIX A,\" \"APPENDIX B,\" and so on."
        ),
    },
    "P053": {
        "question": (
            "Are all List of Tables entries free of a final period?"
        ),
        "rule_definition": (
            "Conservative automated check. NJIT guidelines require that "
            "List of Tables entry titles use title case with no terminal "
            "period. This rule emits a warning when a complete List of "
            "Tables entry ends with a period after stripping leaders and "
            "the 'Table X' prefix. Mirrors the separate check that List of "
            "Figures entries DO have terminal punctuation. Findings "
            "contain only structural metadata -- no entry text, no table "
            "titles."
        ),
        "remediation": (
            "Remove the final period from each List of Tables entry. Table "
            "titles should use title case without terminal punctuation."
        ),
    },
    "P054": {
        "question": (
            "Are all Table of Contents entries free of a final period?"
        ),
        "rule_definition": (
            "Conservative automated check. NJIT guidelines require TOC "
            "entries at all levels to be in specific case styles (all-caps "
            "for level 1, title case for level 2, sentence case for level "
            "3) without terminal punctuation. This rule emits a warning "
            "when a complete TOC entry ends with a period after stripping "
            "leaders and any level prefix. Mirrors the separate check that "
            "List of Tables entries must not have a terminal period. "
            "Findings contain only structural metadata -- no heading text."
        ),
        "remediation": (
            "Remove the final period from each Table of Contents entry."
        ),
    },
    # Ester (2026-09-04): List of Tables / List of Figures entries should
    # always show the word "Table" or "Figure" before the X.x number. The
    # detector enforces that prefix as well as the original cross-type check.
    "P055": {
        "question": (
            "Does each List of Tables entry begin with the word 'Table', and "
            "each List of Figures entry with the word 'Figure', before its "
            "number?"
        ),
        "rule_definition": (
            "Conservative automated check. Each complete List of Tables "
            "entry should begin with 'Table' and each complete List of "
            "Figures entry with 'Figure', followed by its number. This rule "
            "emits an advisory when an entry starts with only a number, or "
            "when a List of Tables entry starts with 'Figure' or a List of "
            "Figures entry starts with 'Table' (a misplaced entry). "
            "Findings contain only structural metadata -- no title text."
        ),
        "remediation": (
            "Begin each List of Tables entry with the word 'Table' and each "
            "List of Figures entry with the word 'Figure' before its number "
            "(for example, Table 1.1 or Figure 1.1). Move any misplaced entry "
            "to the correct list."
        ),
    },
    "P074": {
        "question": (
            "Does the Title Page display a graduation month that is exactly "
            "August, December, or May?"
        ),
        "remediation": (
            "Change the graduation month on the Title Page to August, December, "
            "or May."
        ),
    },
    "P078": {
        "question": (
            "Is the Abstract text free of the words \"paper\" or \"article\" "
            "and free of first-person pronouns?"
        ),
        "rule_definition": (
            "Locates the Abstract page and extracts its body text. Matches "
            "words like \"paper\"/\"papers\"/\"article\"/\"articles\" and "
            "first-person pronouns like capital standalone \"I\" plus "
            "\"me\"/\"my\"/\"mine\"/\"we\"/\"us\"/\"our\"/\"ours\" against "
            "the body text. Emits one warning per unique matched word "
            "(deduplicated, with only non-I pronouns matched "
            "case-insensitively). Does not scan headings, Table of Contents, "
            "body chapters, references, or acknowledgements. If no Abstract "
            "page is found, returns no findings."
        ),
        "remediation": (
            "Replace \"paper\" or \"article\" with \"dissertation,\" \"study,\" "
            "\"work,\" or \"research.\" Rewrite sentences to remove "
            "first-person pronouns such as \"I,\" \"me,\" \"my,\" \"we,\" or "
            "\"our.\""
        ),
    },
    "P045": {
        "question": (
            "Are publication and presentation entries in the Biographical Sketch "
            "single-spaced within each entry, with a blank line between entries?"
        ),
        "rule_definition": (
            "Finds the Publications and Presentations section of the Biographical "
            "Sketch page and separates its entries using entry labels such as [1] "
            "or, when there are none, the entries' indentation. Flags an entry "
            "whose wrapped lines are spaced more widely than single spacing, and "
            "consecutive entries with no blank line between them. A hanging indent "
            "is optional and is not required. Skips the section when its entries "
            "cannot be told apart. Findings are geometry-only -- no publication "
            "text, citation content, or names."
        ),
        "remediation": (
            "Single-space the wrapped lines within each publication or presentation "
            "entry, and add a blank line between separate entries. A hanging indent "
            "is optional."
        ),
    },
    "P047": {
        "question": (
            "Are bullet items in the Biographical Sketch education section "
            "single-spaced within each bullet?"
        ),
        "remediation": (
            "Single-space each bullet item in the Biographical Sketch education "
            "section, with no extra blank lines inside the same bullet item."
        ),
    },
    "P066": {
        "question": (
            "Are postgraduate degrees in the Biographical Sketch listed from "
            "most recent to oldest?"
        ),
        "remediation": (
            "Reorder postgraduate degree entries in the Biographical Sketch from "
            "most recent to oldest."
        ),
    },
    "P067": {
        "question": (
            "Are publication and presentation entries in the Biographical Sketch "
            "listed from most recent to oldest?"
        ),
        "remediation": (
            "Reorder publication and presentation entries in the Biographical "
            "Sketch from most recent to oldest."
        ),
    },
    # Signature/date block counting no longer reports (Ester, R068 follow-up
    # 2026-09-21: committee-block layout depends on committee size); only the
    # advisor-role label check emits findings.
    "P068": {
        "rule_definition": (
            "Conservative structural check: finds the Approval Page and the "
            "committee role labels below its heading, and warns when at "
            "least two committee role labels are found but none identifies "
            "the advisor. Signature and date lines are not counted toward a "
            "warning, because committee-block layout depends on committee "
            "size and on how each template renders signature lines. Findings "
            "contain counts and booleans only."
        ),
        "question": (
            "Does the Approval Page include committee role labels and "
            "signature/date structural blocks for committee entries?"
        ),
        "remediation": (
            "Add the required advisor or committee role label and the "
            "signature/date structural block for each committee entry on the "
            "Approval Page."
        ),
    },
    "P014": {
        "rule_definition": (
            "Detect named front-matter headings and warn when any fail the "
            "required format: centered, bold, all caps, near top of page."
        ),
        "remediation": (
            "Format each front-matter heading in all-caps, bold, centered, "
            "at the top of its page."
        ),
    },
    "P017": {
        "rule_definition": (
            "Automatically detect punctuation and case-style issues in "
            "figure/table caption-like PDF lines. Figure captions (body): "
            "check terminal punctuation and sentence case. List of Figures "
            "entries: check terminal punctuation only; their capitalization "
            "(title case) is checked under R024E. Table titles (body) and "
            "List of Tables entries: check title case and unexpected "
            "terminal period."
        ),
    },
    "P022": {
        "rule_definition": (
            "NJIT requires no visible page number on the Abstract page, "
            "Title page, Approval page, and Copyright page. This rule "
            "detects page-number-like candidates (numeric or Roman "
            "numeral tokens) in the top/bottom margin zone on these "
            "specific named pages and emits one warning per affected page. "
            "Years (1900-2099) in the title-page zone are suppressed to "
            "avoid false positives. Copyright page detection is "
            "conservative: only flagged when clear copyright signals are "
            "found in the first four pages."
        ),
    },
    "P034": {
        "rule_definition": (
            "Conservative check on a confidently identified Copyright "
            "Page: flags visible non-page-number text in the top margin; "
            "compares copyright year to Title Page graduation year and "
            "author name to Title Page author after 'by' only when both "
            "sides are confidently extracted. Skips ambiguous, image-only, "
            "or undetected copyright pages. Does not quote author names or "
            "title text in findings."
        ),
    },
    "P037": {
        "rule_definition": (
            "Conservative check anchored on the detected BIOGRAPHICAL "
            "SKETCH page: requires visible Roman numeral iv (4) on that "
            "page. Dedication, Acknowledgements, and Table of Contents are "
            "checked against fixed NJIT template slots when present. List "
            "of Tables is checked against the next Roman numeral after the "
            "page immediately before List of Tables, because a multi-page "
            "Table of Contents shifts the expected value away from any "
            "fixed slot. Emits nothing when BIOGRAPHICAL SKETCH heading is "
            "not detected. Skips pages with no confident lowercase-Roman-"
            "numeral candidate. Does not duplicate the separate Roman-"
            "numeral regime or sequence checks."
        ),
    },
    "P038": {
        "rule_definition": (
            "Conservative check: (1) flags a missing required heading when "
            "APPROVAL PAGE, BIOGRAPHICAL SKETCH, ACKNOWLEDGEMENTS, or "
            "TABLE OF CONTENTS is not detected in the front-matter region; "
            "(2) flags a non-exact heading phrase when a known curated "
            "spelling variant (e.g. ACKNOWLEDGMENTS) is found instead of "
            "the canonical NJIT phrase. Gated: no findings if no headings "
            "at all are detected (flattened/image-only PDFs). Optional "
            "sections (DEDICATION, LIST OF TABLES, LIST OF FIGURES) are "
            "not flagged as missing. Does not duplicate the separate "
            "heading style check (bold/centered/near-top/all-caps) or the "
            "separate structure check."
        ),
    },
    "P051": {
        "rule_definition": (
            "Conservative check extension of the Copyright Page check. "
            "Uses the same page-detection gate. Attempts year extraction "
            "using the existing method, plus an additional method that "
            "looks for a copyright marker on one line and a standalone "
            "year on the next line. If neither method extracts a year and "
            "no year token exists anywhere on the page, emits a "
            "low-confidence advisory. Skips pages where a year token is "
            "present but not confidently extractable (conservative "
            "false-negative preference). Findings contain only structural "
            "metadata -- no copyright text, author names, or private "
            "content."
        ),
    },
    "P052": {
        "rule_definition": (
            "Conservative check extension of the Copyright Page checks. "
            "Uses the same page-detection gate. Requires that a copyright "
            "year was already found. Attempts author extraction using the "
            "existing method, plus an additional method that looks for a "
            "year on one line and an author-like string on the next line. "
            "If neither method extracts an author and a year was found, "
            "emits a low-confidence advisory. Skips pages where no year "
            "was found. Findings contain only structural metadata -- no "
            "author names, no copyright text, no private content."
        ),
    },
    "P056": {
        "rule_definition": (
            "Conservative automated check. NJIT formatting guidelines "
            "imply that List of Tables and List of Figures entries should "
            "follow a consistent naming convention. This rule emits an "
            "advisory when a complete List of Tables or List of Figures "
            "section contains a mix of chapter-based numbering (e.g., "
            "Table 1.2) and plain sequential numbering (e.g., Table 1). "
            "Findings contain only structural metadata -- no title text."
        ),
    },
    "P063": {
        "rule_definition": (
            "Body-page appendix headings must follow NJIT labeling rules: "
            "if there is one appendix, its heading must be APPENDIX "
            "(without a letter); if there are multiple appendices, each "
            "heading must be APPENDIX A, APPENDIX B, APPENDIX C, etc. with "
            "consecutive letter identifiers. Applies to body pages only; "
            "the Table of Contents side is handled by a separate check."
        ),
    },
}


# A few canonical remediation strings end with a short internal note
# addressed to other rule authors/reviewers rather than to a student (e.g.
# P017's remediation ends with "Ester: figure descriptions -> sentence case
# + terminal period; table titles -> title case + no period."). The
# preceding sentence(s) already state the same guidance in full prose, so
# dropping everything from the internal-name label onward loses no
# actionable content.
_INTERNAL_AUTHORING_NOTE_RE = re.compile(r"\s*\b(?:Ester|Esther|EF)\s*:\s*.*$")


def _strip_internal_authoring_note(text: str) -> str:
    """Remove a trailing internal-reviewer shorthand note, if present.

    Falls back to the original text if stripping would leave nothing, so a
    remediation field is never emptied out.
    """
    stripped = _INTERNAL_AUTHORING_NOTE_RE.sub("", text).strip()
    return stripped if stripped else text


_PXXX_RULE_ID_RE = re.compile(r"^P(\d{3})([A-Z]?)$")


def public_display_rule_id(rule_id: str) -> str:
    """Map an internal ``Pxxx``/``PxxxA`` catalog id to its ``Rxxx``/``RxxxA``
    id shown to students.

    The detector catalog, tests, and rule registry use ``Pxxx`` internally
    (stable identifiers, unrelated to Ester's own Q-rule numbering). Broad
    parent rules such as P018 are further split into lettered atomic
    sub-rules (``P018A``, ``P018B``, ... -- see the catalog entries in
    ``web_app.py``) for the public rule-reference page; a finding can carry
    one of these directly as its ``rule_id``/reference id. Ester asked that
    students only ever see the ``Rxxx`` form. Rather than rename ~113 source
    files' ``rule_id="P019"`` literals -- a large, high-risk change to
    identifiers tests and tooling key off of -- every student-visible
    surface should call this at its final render/serialize step. The
    optional trailing letter is preserved, not dropped: ``P018D`` becomes
    ``R018D``, not ``R018`` -- collapsing it would point students at the
    wrong atomic sub-rule. Anything that is not a plain ``Pddd``/``PdddX``
    id (already-external ids, unexpected values) passes through unchanged.
    """
    match = _PXXX_RULE_ID_RE.match(str(rule_id).strip())
    return f"R{match.group(1)}{match.group(2)}" if match else rule_id


_PXXX_TOKEN_RE = re.compile(r"\bP(\d{3})([A-Z]?)\b")


def convert_pxxx_tokens_to_public_display(text: str) -> str:
    """Replace every standalone ``Pxxx``/``PxxxA`` token in rendered,
    human-readable student-facing text with its ``Rxxx``/``RxxxA`` display
    form.

    This is the Markdown/plain-text-report counterpart of the Jinja
    ``display_rule_id`` filter used by the web templates: rather than hunt
    down every one of the many rule_id interpolations spread across this
    module's ~15 Markdown-section formatter functions (headings, counts
    tables, per-rule triage sections, cross-references, etc. -- a large,
    easy-to-under-cover surface), this converts the *final rendered text* in
    one pass, reusing public_display_rule_id as the single source of truth
    for the id mapping itself. It must only ever be applied to text that is
    about to be shown to a student (e.g. the assembled Markdown report just
    before it is written to disk) -- never to JSON payloads or any other
    structure internal tooling/tests parse by key, since those must keep
    their real Pxxx values (see write_json_report, audit_findings_to_json_dict).
    The \\b...\\b word-boundary anchors mean a longer digit run such as
    "P0191" is left untouched -- only an exact "Pddd" or "PdddX" (single
    trailing uppercase letter, matching the atomic-sub-rule catalog ids)
    token converts.
    """
    return _PXXX_TOKEN_RE.sub(lambda m: public_display_rule_id(m.group(0)), text)


def _websafe_rule_text(rule_id: str, field: str, text: str) -> str:
    """Rewrite internal authoring language for public/student-facing display.

    Shared by the public Rules Reference page (``web_app.py``'s
    ``_build_rule_catalog``) and the plain-text student report's
    de-truncated "How to fix it" text (``report_text.py``) so any canonical
    rule-JSON field reaching a student -- via either surface -- goes through
    the same overrides, heuristic-wording cleanup, and internal-note
    stripping, without touching the canonical rule data on disk.
    """
    result = _RULE_TEXT_OVERRIDES.get(rule_id, {}).get(field, text)
    result = _strip_internal_authoring_note(result)
    for pattern, replacement in _HEURISTIC_WORDING:
        result = pattern.sub(replacement, result)
    return result


def derive_source_issue_type(rule_id: str, details: dict[str, str] | None = None) -> str:
    """Map a source/TeX finding to a stable issue_type for export and comments."""
    safe = details or {}
    explicit = safe.get("issue_type", "").strip()
    if explicit:
        return explicit
    if rule_id == "P001":
        return "risky_command"
    if rule_id == "P002":
        return "duplicate_label"
    if rule_id == "P003":
        return "invalid_label"
    if rule_id == "P004":
        return "dangling_reference"
    if rule_id == "P005":
        return "missing_caption"
    if rule_id == "P006":
        return "missing_label"
    if rule_id == "P007":
        return "caption_punctuation"
    if rule_id == "P008":
        return "abstract_structure"
    if rule_id == "P009":
        return "chktex_warning"
    if rule_id == "P010":
        return "lacheck_warning"
    return "source_check"


def _source_location_basename(details: dict[str, str]) -> str:
    file_path = details.get("file", "").strip()
    if not file_path:
        return ""
    return Path(file_path).name


def _prepare_findings_for_export(
    findings: list[AuditFinding], audit_type: str
) -> list[AuditFinding]:
    """Return findings with export-friendly details (issue_type for source audits)."""
    if audit_type != "tex":
        return findings
    prepared: list[AuditFinding] = []
    for finding in findings:
        details = dict(finding.details)
        if not details.get("issue_type"):
            details["issue_type"] = derive_source_issue_type(finding.rule_id, details)
        prepared.append(
            AuditFinding(
                rule_id=finding.rule_id,
                severity=finding.severity,
                message=finding.message,
                page=finding.page,
                details=details,
            )
        )
    return prepared


def _findings_sorted_for_export(findings: list[AuditFinding]) -> list[AuditFinding]:
    """Return findings ordered by PDF page, earliest first, page-less findings last.

    The audit pipeline emits findings grouped by detector/rule (each rule sweeps
    the whole document before the next one runs), not by page, so without this
    sort a downloaded report's finding order -- and its problem numbers -- jump
    around the document non-sequentially. TeX-source findings carry no ``page``
    (they use file/line instead), so every one shares sort key ``(True, 0)`` and
    this is a no-op for source audits; their own file/line ordering is applied
    separately where needed (see the "Findings by Rule" sort_key below).

    The sort is stable, which matters beyond determinism: several presentation
    helpers downstream (``_problem_number_map``, ``build_grouped_findings``, and
    the P011/P012/P020/P026/page-number "first occurrence wins" dedup states)
    pick their representative finding via per-page state keyed on traversal
    order, not raw list position. Because every one of those dedup keys already
    includes the page, a stable sort preserves which finding wins each dedup
    slot -- it only reorders the page groups themselves, so finding counts and
    representative-finding choices are unchanged; only display order changes.
    """
    return sorted(
        findings,
        key=lambda finding: (finding.page is None, finding.page or 0),
    )


def build_source_report(
    findings: list[AuditFinding],
    *,
    input_file_path: str,
    input_file_name: str,
    input_kind: str = "tex",
    main_tex_path: str = "",
    loaded_tex_file_count: int | None = None,
    job_id: str = "",
) -> dict[str, Any]:
    """Build a JSON-compatible source-audit report for TeX/ZIP uploads."""
    metadata: dict[str, str] = {
        "input_file_path": input_file_path,
        "input_file_name": input_file_name,
        "audit_type": "tex",
        "input_kind": input_kind,
        "main_tex_path": main_tex_path,
        "loaded_tex_file_count": (
            str(loaded_tex_file_count) if loaded_tex_file_count is not None else ""
        ),
        "job_id": job_id,
    }
    return audit_findings_to_json_dict(findings, metadata)


def build_audit_report(
    findings: list[AuditFinding],
    metadata: dict[str, str],
) -> dict[str, Any]:
    """Build a JSON-compatible report for PDF or source audits."""
    audit_type = metadata.get("audit_type", "pdf")
    prepared = _prepare_findings_for_export(findings, audit_type)
    return audit_findings_to_json_dict(prepared, metadata)


def compact_page_list(pages: list[int], max_ranges: int = _MAX_COMPACT_RANGES) -> str:
    """Convert a list of page numbers to a compact range string.

    Examples:
        [1, 2, 3, 5, 7, 8] → "1-3, 5, 7-8"
        Long lists truncated: "1-3, 5, 7-8, ... (42 pages)"
    """
    if not pages:
        return ""
    sorted_pages = sorted(set(pages))
    ranges: list[tuple[int, int]] = []
    start = end = sorted_pages[0]
    for page in sorted_pages[1:]:
        if page == end + 1:
            end = page
        else:
            ranges.append((start, end))
            start = end = page
    ranges.append((start, end))

    parts: list[str] = []
    for s, e in ranges[:max_ranges]:
        parts.append(str(s) if s == e else f"{s}-{e}")

    result = ", ".join(parts)
    if len(ranges) > max_ranges:
        result += f", ... ({len(sorted_pages)} pages total)"
    return result


def _compact_numeric_ranges(numbers: list[int]) -> list[str]:
    """Return sorted, deduplicated numeric values as compact en-dash ranges."""
    if not numbers:
        return []
    ordered = sorted(set(numbers))
    ranges: list[str] = []
    start = end = ordered[0]
    for number in ordered[1:]:
        if number == end + 1:
            end = number
            continue
        ranges.append(str(start) if start == end else f"{start}–{end}")
        start = end = number
    ranges.append(str(start) if start == end else f"{start}–{end}")
    return ranges


def _compact_numeric_range_text(numbers: list[int]) -> str:
    return ", ".join(_compact_numeric_ranges(numbers))


def _roman_to_int(label: str) -> int | None:
    if not label or not _ROMAN_LABEL_RE.fullmatch(label):
        return None
    values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total = 0
    previous = 0
    for char in reversed(label.upper()):
        value = values[char]
        if value < previous:
            total -= value
        else:
            total += value
            previous = value
    return total if total > 0 else None


def _int_to_roman(value: int, *, uppercase: bool = False) -> str:
    numerals = (
        (1000, "M"),
        (900, "CM"),
        (500, "D"),
        (400, "CD"),
        (100, "C"),
        (90, "XC"),
        (50, "L"),
        (40, "XL"),
        (10, "X"),
        (9, "IX"),
        (5, "V"),
        (4, "IV"),
        (1, "I"),
    )
    remaining = value
    parts: list[str] = []
    for amount, symbol in numerals:
        while remaining >= amount:
            parts.append(symbol)
            remaining -= amount
    roman = "".join(parts)
    return roman if uppercase else roman.lower()


def _compact_roman_ranges(labels: list[str]) -> list[str]:
    if not labels:
        return []
    normalized: list[tuple[int, str]] = []
    for label in labels:
        value = _roman_to_int(label)
        if value is None:
            return []
        normalized.append((value, label))
    uppercase = all(label.isupper() for _, label in normalized)
    ordered_values = sorted({value for value, _ in normalized})
    ranges: list[str] = []
    start = end = ordered_values[0]
    for value in ordered_values[1:]:
        if value == end + 1:
            end = value
            continue
        start_label = _int_to_roman(start, uppercase=uppercase)
        end_label = _int_to_roman(end, uppercase=uppercase)
        ranges.append(start_label if start == end else f"{start_label}–{end_label}")
        start = end = value
    start_label = _int_to_roman(start, uppercase=uppercase)
    end_label = _int_to_roman(end, uppercase=uppercase)
    ranges.append(start_label if start == end else f"{start_label}–{end_label}")
    return ranges


def _compact_location_ranges(
    locations: list[tuple[str, str]],
) -> tuple[list[str], str]:
    if not locations:
        return [], ""
    by_file: dict[str, dict[str, list[str]]] = defaultdict(lambda: {"lines": []})
    standalone_files: list[str] = []
    for file_name, line in locations:
        clean_file = file_name.strip()
        clean_line = line.strip()
        if not clean_file:
            continue
        if not clean_line:
            standalone_files.append(clean_file)
            continue
        by_file[clean_file]["lines"].append(clean_line)

    tokens: list[str] = []
    for file_name in sorted(set(standalone_files)):
        tokens.append(file_name)

    for file_name in sorted(by_file):
        numeric_lines: list[int] = []
        non_numeric_lines: list[str] = []
        for line in by_file[file_name]["lines"]:
            if line.isdigit():
                numeric_lines.append(int(line))
            else:
                non_numeric_lines.append(line)
        for compact in _compact_numeric_ranges(numeric_lines):
            tokens.append(f"{file_name}:{compact}")
        for line in sorted(set(non_numeric_lines)):
            tokens.append(f"{file_name}:{line}")

    return tokens, ", ".join(tokens)


def _page_label_from_details(details: dict[str, str]) -> str:
    for key in ("page_label", "page_number_label"):
        value = details.get(key, "").strip()
        if value:
            return value
    return ""


def _normalize_grouping_text(
    text: str,
    *,
    audit_type: str,
    page: int | None,
    details: dict[str, str],
) -> str:
    """Normalize display text for grouping without relying on page-specific values."""
    normalized = " ".join(text.split())
    if not normalized:
        return ""

    if audit_type == "tex":
        location = format_source_location(details)
        if location and location != "source":
            normalized = normalized.replace(location, "<location>")
    elif page is not None:
        normalized = normalized.replace(f"page {page}", "page <page>")
        normalized = normalized.replace(f"p.{page}", "p.<page>")

    page_label = _page_label_from_details(details)
    if page_label:
        normalized = normalized.replace(page_label, "<page_label>")

    start = details.get("run_start_page", "").strip()
    end = details.get("run_end_page", "").strip()
    if start and end:
        range_label = start if start == end else f"{start}–{end}"
        normalized = normalized.replace(range_label, "<page_range>")

    return normalized


def _grouping_context_signature(
    rule_id: str,
    details: dict[str, str],
) -> tuple[tuple[str, str], ...]:
    keys = set(_REPEATED_PROBLEM_CONTEXT_KEYS)
    keys.update(_RULE_SPECIFIC_GROUPING_KEYS.get(rule_id, ()))
    signature: list[tuple[str, str]] = []
    for key in sorted(keys):
        value = details.get(key, "").strip()
        if value:
            signature.append((key, value))
    return tuple(signature)


def build_grouped_findings(
    findings: list[AuditFinding],
    audit_type: str,
) -> list[dict[str, Any]]:
    """Build a deterministic grouped-problem structure for repeated findings.

    The raw ``findings`` list is preserved unchanged elsewhere. This structure is
    additive and intended for compact web/Markdown display.
    """
    from njit_auditor.polished_comments import (
        build_polished_comment,
        finalize_student_facing_comment_and_fix,
        resolve_suggested_fix_for_display,
    )

    grouped: dict[
        tuple[Any, ...],
        dict[str, Any],
    ] = {}

    for index, finding in enumerate(findings):
        details = {str(k): str(v) for k, v in (finding.details or {}).items()}
        rule_id = finding.rule_id
        issue_type = details.get("issue_type", "")
        severity = finding.severity.value
        page = finding.page
        category = map_finding_rule_to_category(rule_id, details)
        polished_comment = build_polished_comment(
            rule_id=rule_id,
            issue_type=issue_type,
            severity=severity,
            page=page,
            details=details,
            category=category,
        )
        suggested_fix = resolve_suggested_fix_for_display(
            rule_id,
            issue_type,
            existing=details.get("suggested_fix", "").strip(),
        )
        polished_comment, suggested_fix = finalize_student_facing_comment_and_fix(
            rule_id,
            issue_type,
            polished_comment,
            suggested_fix,
        )
        confidence = details.get("confidence", "").strip()
        triage_tier = details.get("triage_tier", "").strip()
        normalized_problem = _normalize_grouping_text(
            polished_comment,
            audit_type=audit_type,
            page=page,
            details=details,
        )
        normalized_fix = _normalize_grouping_text(
            suggested_fix,
            audit_type=audit_type,
            page=page,
            details=details,
        )
        # Confidence is deliberately excluded from the grouping key: the same
        # problem type should stay on one card even when individual occurrences
        # were detected with different confidence levels (see _CONFIDENCE_ORDER
        # in report_view.py, which aggregates per-occurrence confidence for
        # display rather than relying on a single value here).
        key = (
            rule_id,
            issue_type,
            severity,
            category,
            normalized_problem,
            normalized_fix,
            triage_tier,
            _grouping_context_signature(rule_id, details),
        )
        file_name = _source_location_basename(details)
        source_line = details.get("line", "").strip()
        page_label = _page_label_from_details(details)

        if key not in grouped:
            grouped[key] = {
                "rule_id": rule_id,
                "issue_type": issue_type,
                "severity": severity,
                "category": category,
                "problem": polished_comment,
                "suggested_fix": suggested_fix,
                "triage_tier": triage_tier,
                "occurrence_count": 0,
                "pages": [],
                "page_ranges": [],
                "page_labels": [],
                "page_labels_compact": "",
                "locations": [],
                "locations_compact": "",
                "individual_indexes": [],
                "_confidence_values": [],
            }

        entry = grouped[key]
        entry["occurrence_count"] += 1
        entry["individual_indexes"].append(index)
        if confidence:
            entry["_confidence_values"].append(confidence)
        if page is not None:
            entry["pages"].append(int(page))
        if page_label:
            entry["page_labels"].append(page_label)
        if file_name or source_line:
            entry["locations"].append(format_source_location(details))
            entry.setdefault("_raw_locations", []).append((file_name, source_line))

    ordered_groups = sorted(
        grouped.values(),
        key=lambda entry: (entry["individual_indexes"][0], entry["rule_id"], entry["issue_type"]),
    )
    for entry in ordered_groups:
        raw_confidences = set(entry.pop("_confidence_values", []))
        confidence_levels = [
            level for level in ("high", "medium", "low") if level in raw_confidences
        ]
        entry["confidence_levels"] = confidence_levels
        if len(confidence_levels) == 1:
            entry["confidence"] = confidence_levels[0]
        elif confidence_levels:
            entry["confidence"] = "mixed"
        else:
            entry["confidence"] = ""

        page_values = sorted(set(int(page) for page in entry["pages"]))
        page_ranges = _compact_numeric_ranges(page_values)
        page_labels = sorted(set(str(label) for label in entry["page_labels"]))
        roman_ranges = _compact_roman_ranges(page_labels)
        raw_locations = entry.pop("_raw_locations", [])
        location_ranges, locations_compact = _compact_location_ranges(raw_locations)
        location_tokens = sorted(set(str(location) for location in entry["locations"]))

        entry["pages"] = page_values
        entry["page_ranges"] = page_ranges
        entry["pages_compact"] = ", ".join(page_ranges)
        entry["page_labels"] = page_labels
        entry["page_label_ranges"] = roman_ranges
        entry["page_labels_compact"] = (
            ", ".join(roman_ranges) if roman_ranges else ", ".join(page_labels)
        )
        entry["locations"] = location_tokens
        entry["location_ranges"] = location_ranges
        entry["locations_compact"] = locations_compact
        if entry["page_labels_compact"]:
            entry["affected_label"] = "Pages"
            entry["affected_compact"] = entry["page_labels_compact"]
        elif entry["pages_compact"]:
            entry["affected_label"] = "Pages"
            entry["affected_compact"] = entry["pages_compact"]
        elif entry["locations_compact"]:
            entry["affected_label"] = "Locations"
            entry["affected_compact"] = entry["locations_compact"]
        else:
            entry["affected_label"] = "Occurrences"
            entry["affected_compact"] = ""

    return ordered_groups


_P036_HIGH_VOLUME_SECTION_LABELS: dict[str, str] = {
    "toc_inter_entry_spacing_too_tight": "Table of Contents",
    "lot_inter_entry_spacing_too_tight": "List of Tables",
    "lof_inter_entry_spacing_too_tight": "List of Figures",
}
_P019_DOCUMENT_PATTERN_ISSUE_TYPES: frozenset[str] = frozenset(
    {
        # Raw rule-internal issue_type values (used when grouping/Markdown read
        # straight from AuditFinding.details, before any display remapping).
        "sequence_gap",
        "missing_page_number",
        "multiple_page_numbers",
        "inconsistent_position",
        "mixed_numbering_style",
        # Student-facing "visible issue type" values that report_view.py maps
        # raw P019 issue types onto for HTML display (see
        # _classify_visible_page_number_issue); a grouped HTML card's
        # issue_type is already this remapped value, not the raw one above.
        "duplicate_or_ambiguous_page_number",
        "wrong_page_number_location",
        "wrong_page_numbering_style",
        "wrong_page_number_sequence",
    }
)


def _high_volume_pattern_note(
    rule_id: str,
    issue_type: str,
    occurrence_count: int,
    affected_label: str,
    affected_compact: str,
) -> str:
    """Explain, for a grouped card, why it has many occurrences.

    Presentation only: never changes detection, grouping, counts, or
    thresholds. Returns "" when the group has one occurrence or the
    rule/issue type has no high-volume framing defined here.
    """
    if occurrence_count <= 1:
        return ""
    where = f" across {affected_label.lower()} {affected_compact}" if affected_compact else ""

    if rule_id == "P036" and issue_type in _P036_HIGH_VOLUME_SECTION_LABELS:
        section = _P036_HIGH_VOLUME_SECTION_LABELS[issue_type]
        return (
            f"This spacing pattern appears {occurrence_count} times, all in the "
            f"{section}. It is the same formatting issue repeated rather than "
            f"{occurrence_count} unrelated problems. Review one entry below, fix "
            "the spacing, then apply the same correction to the remaining "
            'entries under "Show individual occurrences".'
        )

    if rule_id == "P020" and issue_type == "possible_title_capitalization_issue":
        return (
            f"This title-case pattern appears {occurrence_count} times{where}. "
            "Each occurrence flags a different word that should follow Title "
            'Case; open "Show individual occurrences" below for the exact word '
            "and expected capitalization in each case. This card only groups "
            "findings that share the same capitalization reason and confidence "
            "level -- a separate P020 card covering a different reason (for "
            "example, a missing first-word capital vs. a missing major-word "
            "capital) is not a duplicate."
        )

    if rule_id == "P026" and issue_type in (P026_FAMILY_ISSUE_TYPE, P026_SIZE_ISSUE_TYPE):
        return (
            f"This issue appears {occurrence_count} times because the auditor found the "
            f"same body-text font pattern{where}. Student-facing problem cards may "
            "summarize repeated patterns document-wide; review the affected pages listed "
            "in each summary and set Times New Roman 12pt consistently before re-export."
        )

    if rule_id == "P012" and issue_type == "pdf_annotation_detected":
        return (
            f"This issue appears {occurrence_count} times because the uploaded PDF "
            f"contains embedded annotations or comments{where}. Student-facing cards "
            "may summarize high-volume annotation warnings document-wide. Remove or "
            "flatten reviewer markup, then upload a clean PDF before submission."
        )

    if rule_id == "P011" and issue_type == P011_ISSUE_TYPE:
        return (
            f"This margin issue appears {occurrence_count} times{where}. When multiple "
            "margin sides fail on the same page, the student-facing report may show one "
            "combined page-level card listing every affected side. Review page margins "
            "and text frames on the listed pages."
        )

    if rule_id == "P019" and issue_type in _P019_DOCUMENT_PATTERN_ISSUE_TYPES:
        return (
            f"This page-numbering issue appears {occurrence_count} times{where}. "
            "Repeats like this are usually one document-level numbering pattern "
            f"rather than {occurrence_count} separate problems. Review the "
            "page-numbering scheme used across the document, then apply one "
            "consistent fix."
        )

    return ""


def _share_pct(count: int, total: int) -> float:
    """Return a compact percentage for report summaries."""
    if total <= 0:
        return 0.0
    return round((count / total) * 100.0, 1)


def _bucket_summary(pages: list[int]) -> dict[str, Any]:
    """Build a compact count/range summary for a page bucket."""
    deduped = sorted(set(pages))
    return {
        "count": len(deduped),
        "pages_compact": compact_page_list(deduped),
    }


def build_p013_triage_summary(findings: list[AuditFinding]) -> dict[str, Any] | None:
    """Build a P013-specific rollup for high-volume page-number candidate triage.

    Raw findings are not modified. This summary separates document overview from
    per-page candidate warnings and adds position/style pattern page ranges.
    """
    p013_findings = [f for f in findings if f.rule_id == P013_RULE_ID]
    if not p013_findings:
        return None

    page_findings = [f for f in p013_findings if f.page is not None]
    doc_findings = [f for f in p013_findings if f.page is None]

    pages = sorted({f.page for f in page_findings if f.page is not None})
    position_type_counts: Counter[str] = Counter()
    number_style_counts: Counter[str] = Counter()
    confidence_counts: Counter[str] = Counter()
    issue_type_counts: Counter[str] = Counter()
    multi_candidate_pages: list[int] = []
    by_observed: dict[str, list[int]] = defaultdict(list)
    page_rows: list[tuple[int, int, str, str]] = []

    for finding in page_findings:
        details = finding.details or {}
        issue_type_counts[details.get("issue_type", P013_PAGE_ISSUE_TYPE)] += 1
        position_type = details.get("position_type", "")
        if position_type:
            position_type_counts[position_type] += 1
        number_style = details.get("number_style", "")
        if number_style:
            number_style_counts[number_style] += 1
        confidence = details.get("confidence", "")
        if confidence:
            confidence_counts[confidence] += 1
        try:
            candidate_count = int(details.get("candidate_count_on_page", "1"))
        except ValueError:
            candidate_count = 1
        if candidate_count > 1 and finding.page is not None:
            multi_candidate_pages.append(finding.page)
        observed = details.get("observed_summary", "")
        if observed and finding.page is not None:
            by_observed[observed].append(finding.page)
        if finding.page is not None:
            page_rows.append((finding.page, candidate_count, confidence, observed))

    for finding in doc_findings:
        details = finding.details or {}
        issue_type_counts[details.get("issue_type", P013_DOC_ISSUE_TYPE)] += 1

    pattern_page_ranges = {
        observed: compact_page_list(sorted(set(page_list)))
        for observed, page_list in sorted(
            by_observed.items(), key=lambda item: (-len(item[1]), item[0])
        )[:8]
    }

    dominant_pattern = ""
    dominant_pattern_pages: list[int] = []
    if by_observed:
        dominant_pattern, dominant_pattern_pages = max(
            (
                (observed, sorted(set(page_list)))
                for observed, page_list in by_observed.items()
            ),
            key=lambda item: (len(item[1]), item[0]),
        )

    routine_pages: list[int] = []
    other_pages: list[int] = []
    for page, candidate_count, confidence, observed in page_rows:
        if candidate_count > 1:
            continue
        if observed and observed == dominant_pattern and confidence == "medium":
            routine_pages.append(page)
        else:
            other_pages.append(page)

    affected_page_count = len(pages)
    dominant_pattern_share = _share_pct(len(dominant_pattern_pages), affected_page_count)
    routine_share = _share_pct(len(set(routine_pages)), affected_page_count)
    if routine_share >= 80.0:
        document_pattern_label = "document_wide_routine_pattern"
    elif dominant_pattern_share >= 60.0:
        document_pattern_label = "mostly_routine_pattern_with_outliers"
    else:
        document_pattern_label = "mixed_candidate_patterns"

    calibration_buckets = {
        "routine_single_candidate_dominant_pattern": _bucket_summary(routine_pages),
        "multi_candidate_pages": _bucket_summary(multi_candidate_pages),
        "other_pattern_or_low_confidence": _bucket_summary(other_pages),
    }

    return {
        "raw_finding_count": len(p013_findings),
        "page_level_finding_count": len(page_findings),
        "document_overview_finding_count": len(doc_findings),
        "affected_page_count": len(pages),
        "affected_pages_compact": compact_page_list(pages),
        "issue_type_counts": dict(sorted(issue_type_counts.items())),
        "position_type_counts": dict(sorted(position_type_counts.items())),
        "number_style_counts": dict(sorted(number_style_counts.items())),
        "confidence_counts": dict(sorted(confidence_counts.items())),
        "pages_with_multiple_candidates": len(multi_candidate_pages),
        "multiple_candidate_pages_compact": compact_page_list(multi_candidate_pages),
        "pattern_page_ranges": pattern_page_ranges,
        "document_pattern_label": document_pattern_label,
        "dominant_pattern": dominant_pattern,
        "dominant_pattern_page_count": len(dominant_pattern_pages),
        "dominant_pattern_pages_compact": compact_page_list(dominant_pattern_pages),
        "dominant_pattern_share_pct": dominant_pattern_share,
        "calibration_buckets": calibration_buckets,
        "calibration_note": (
            "Calibration buckets organize routine dominant-pattern pages separately from "
            "multi-candidate and non-dominant pages for manual triage only. P013 "
            "detector entries are retained as inventory evidence and are not "
            "student-visible problems unless a specific page-number defect is reported."
        ),
        "triage_tier": "informational",
        "triage_note": (
            "Most P013 entries are routine page-number candidates that help verify "
            "page-number location and style. They are informational and are not "
            "counted as formatting problems unless another finding reports a "
            "specific defect on that page."
        ),
    }


def _p026_pattern_key(issue_type: str, observed_summary: str) -> str:
    """Build a privacy-safe grouping key for P026 pattern page ranges."""
    observed = observed_summary.strip() or "(unspecified)"
    if len(observed) > 60:
        observed = f"{observed[:57]}..."
    return f"{issue_type}/{observed}"


def build_p026_font_triage_summary(findings: list[AuditFinding]) -> dict[str, Any] | None:
    """Build a P026-specific rollup for high-volume body-font compliance triage.

    Raw findings are not modified. Groups consecutive pages by issue type and
    observed font label/size summary for compact pattern page ranges.
    """
    p026_findings = [f for f in findings if f.rule_id == P026_RULE_ID]
    if not p026_findings:
        return None

    pages = sorted({f.page for f in p026_findings if f.page is not None})
    issue_type_counts: Counter[str] = Counter()
    confidence_counts: Counter[str] = Counter()
    font_label_counts: Counter[str] = Counter()
    size_label_counts: Counter[str] = Counter()
    by_pattern: dict[str, list[int]] = defaultdict(list)
    pages_by_issue: dict[str, set[int]] = defaultdict(set)
    page_rows: dict[int, list[tuple[str, str, str]]] = defaultdict(list)

    for finding in p026_findings:
        details = finding.details or {}
        issue_type = details.get("issue_type", "")
        issue_type_counts[issue_type] += 1
        confidence = details.get("confidence", "")
        if confidence:
            confidence_counts[confidence] += 1
        observed = details.get("observed_summary", "").strip()
        if issue_type == P026_FAMILY_ISSUE_TYPE and observed:
            font_label_counts[observed] += 1
        elif issue_type == P026_SIZE_ISSUE_TYPE and observed:
            size_label_counts[observed] += 1
        if finding.page is not None:
            pages_by_issue[issue_type].add(finding.page)
            pattern_key = _p026_pattern_key(issue_type, observed)
            by_pattern[pattern_key].append(finding.page)
            page_rows[finding.page].append((issue_type, observed, confidence))

    family_pages = pages_by_issue.get(P026_FAMILY_ISSUE_TYPE, set())
    size_pages = pages_by_issue.get(P026_SIZE_ISSUE_TYPE, set())
    both_pages = sorted(family_pages & size_pages)

    pattern_page_ranges = {
        pattern: compact_page_list(sorted(set(page_list)))
        for pattern, page_list in sorted(
            by_pattern.items(), key=lambda item: (-len(item[1]), item[0])
        )[:8]
    }

    dominant_pattern = ""
    dominant_pattern_pages: list[int] = []
    if by_pattern:
        dominant_pattern, dominant_pattern_pages = max(
            (
                (pattern, sorted(set(page_list)))
                for pattern, page_list in by_pattern.items()
            ),
            key=lambda item: (len(item[1]), item[0]),
        )

    routine_pages: list[int] = []
    size_only_pages: list[int] = []
    non_dominant_pages: list[int] = []
    for page, entries in sorted(page_rows.items()):
        issue_types = {issue_type for issue_type, _, _ in entries if issue_type}
        has_size_issue = P026_SIZE_ISSUE_TYPE in issue_types
        page_patterns = {
            _p026_pattern_key(issue_type, observed)
            for issue_type, observed, _ in entries
        }
        confidences = {confidence for _, _, confidence in entries if confidence}
        if len(issue_types) > 1:
            continue
        if has_size_issue:
            size_only_pages.append(page)
            continue
        if (
            dominant_pattern
            and page_patterns == {dominant_pattern}
            and confidences <= {"medium"}
        ):
            routine_pages.append(page)
        else:
            non_dominant_pages.append(page)

    affected_page_count = len(pages)
    dominant_pattern_share = _share_pct(len(dominant_pattern_pages), affected_page_count)
    routine_share = _share_pct(len(set(routine_pages)), affected_page_count)
    if routine_share >= 75.0 and not both_pages and not size_only_pages:
        document_pattern_label = "document_wide_single_font_pattern"
    elif dominant_pattern_share >= 50.0:
        document_pattern_label = "dominant_font_pattern_with_outliers"
    else:
        document_pattern_label = "mixed_font_patterns"

    calibration_buckets = {
        "routine_single_issue_dominant_pattern": _bucket_summary(routine_pages),
        "pages_with_both_issue_types": _bucket_summary(both_pages),
        "size_issue_only_pages": _bucket_summary(size_only_pages),
        "non_dominant_family_only_pages": _bucket_summary(non_dominant_pages),
    }

    return {
        "raw_finding_count": len(p026_findings),
        "affected_page_count": len(pages),
        "affected_pages_compact": compact_page_list(pages),
        "issue_type_counts": dict(sorted(issue_type_counts.items())),
        "font_label_counts": dict(
            font_label_counts.most_common(8),
        ),
        "size_observed_label_counts": dict(
            size_label_counts.most_common(8),
        ),
        "confidence_counts": dict(sorted(confidence_counts.items())),
        "pages_with_both_issue_types": len(both_pages),
        "both_issue_types_pages_compact": compact_page_list(both_pages),
        "pattern_page_ranges": pattern_page_ranges,
        "document_pattern_label": document_pattern_label,
        "dominant_pattern": dominant_pattern,
        "dominant_pattern_page_count": len(dominant_pattern_pages),
        "dominant_pattern_pages_compact": compact_page_list(dominant_pattern_pages),
        "dominant_pattern_share_pct": dominant_pattern_share,
        "calibration_buckets": calibration_buckets,
        "calibration_note": (
            "Calibration buckets separate routine dominant-pattern pages from size-driven, "
            "mixed-issue, and non-dominant pages for manual triage only. Raw P026 warnings "
            "are not suppressed or re-scored."
        ),
        "triage_tier": "informational",
        "triage_note": (
            "P026 reports automated body-font size/family compliance warnings for manual "
            "NJIT verification. Page-level warnings are triage signals, not confirmed "
            "formatting defects."
        ),
    }


def _parse_overflow_pt(details: dict[str, str]) -> float | None:
    raw = details.get("worst_overflow_pt", "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def build_p012_annotation_triage_summary(
    findings: list[AuditFinding],
) -> dict[str, Any] | None:
    """Build a P012-specific rollup for embedded PDF annotation/comment triage.

    Raw findings are not modified. Summaries use annotation types and page numbers
    only — never annotation text content.
    """
    p012_findings = [f for f in findings if f.rule_id == P012_RULE_ID]
    if not p012_findings:
        return None

    pages = sorted({f.page for f in p012_findings if f.page is not None})
    annotation_type_counts: Counter[str] = Counter()
    annotations_by_page: Counter[int] = Counter()
    by_type_pages: dict[str, list[int]] = defaultdict(list)

    for finding in p012_findings:
        details = finding.details or {}
        annotation_type = details.get("annotation_type", "") or "(unknown)"
        annotation_type_counts[annotation_type] += 1
        if finding.page is not None:
            annotations_by_page[finding.page] += 1
            by_type_pages[annotation_type].append(finding.page)

    multi_annotation_pages = sorted(
        page for page, count in annotations_by_page.items() if count > 1
    )
    type_page_ranges = {
        annotation_type: compact_page_list(sorted(set(page_list)))
        for annotation_type, page_list in sorted(
            by_type_pages.items(), key=lambda item: (-len(item[1]), item[0])
        )[:8]
    }

    dominant_type = ""
    if annotation_type_counts:
        dominant_type = annotation_type_counts.most_common(1)[0][0]

    return {
        "raw_finding_count": len(p012_findings),
        "affected_page_count": len(pages),
        "affected_pages_compact": compact_page_list(pages),
        "annotation_type_counts": dict(sorted(annotation_type_counts.items())),
        "annotations_per_page_max": (
            max(annotations_by_page.values()) if annotations_by_page else 0
        ),
        "pages_with_multiple_annotations": len(multi_annotation_pages),
        "multiple_annotations_pages_compact": compact_page_list(
            multi_annotation_pages
        ),
        "type_page_ranges": type_page_ranges,
        "dominant_annotation_type": dominant_type,
        "triage_tier": "informational",
        "triage_note": (
            "P012 reports annotations, comments, and markup that were already present "
            "in the uploaded PDF -- not highlights added by this auditor. This is an "
            "informational triage category; resolve or remove comments rather than "
            "treating each warning as a formatting defect."
        ),
        "recommended_action": (
            "Review affected pages, resolve feedback, and remove or flatten annotations "
            "before submitting the final PDF."
        ),
    }


def build_p011_margin_triage_summary(findings: list[AuditFinding]) -> dict[str, Any] | None:
    """Build a P011-specific rollup for margin/overflow triage.

    Raw findings are not modified. Groups pages by margin side for compact ranges
    and summarizes overflow distance by side.
    """
    p011_findings = [
        f
        for f in findings
        if f.rule_id == P011_RULE_ID and f.severity == Severity.WARNING
    ]
    if not p011_findings:
        return None

    pages = sorted({f.page for f in p011_findings if f.page is not None})
    side_counts: Counter[str] = Counter()
    confidence_counts: Counter[str] = Counter()
    by_side: dict[str, list[int]] = defaultdict(list)
    overflow_by_side: dict[str, list[float]] = defaultdict(list)
    pages_by_side: dict[str, set[int]] = defaultdict(set)
    total_affected_lines = 0

    for finding in p011_findings:
        details = finding.details or {}
        side = details.get("side", "") or "(unspecified)"
        side_counts[side] += 1
        confidence = details.get("confidence", "")
        if confidence:
            confidence_counts[confidence] += 1
        try:
            total_affected_lines += int(details.get("affected_line_count", "0"))
        except ValueError:
            pass
        overflow = _parse_overflow_pt(details)
        if overflow is not None:
            overflow_by_side[side].append(overflow)
        if finding.page is not None:
            by_side[side].append(finding.page)
            pages_by_side[side].add(finding.page)

    page_side_count: Counter[int] = Counter()
    for page in pages:
        page_side_count[page] = sum(1 for s in pages_by_side.values() if page in s)
    multi_side_pages = sorted(page for page, n in page_side_count.items() if n > 1)

    pattern_page_ranges = {
        side: compact_page_list(sorted(set(page_list)))
        for side, page_list in sorted(
            by_side.items(), key=lambda item: (-len(item[1]), item[0])
        )[:8]
    }

    max_overflow_by_side = {
        side: round(max(values), 1)
        for side, values in sorted(overflow_by_side.items())
        if values
    }
    median_overflow_by_side = {
        side: round(statistics.median(values), 1)
        for side, values in sorted(overflow_by_side.items())
        if values
    }

    dominant_side = side_counts.most_common(1)[0][0] if side_counts else ""

    return {
        "raw_finding_count": len(p011_findings),
        "affected_page_count": len(pages),
        "affected_pages_compact": compact_page_list(pages),
        "side_counts": dict(sorted(side_counts.items())),
        "confidence_counts": dict(sorted(confidence_counts.items())),
        "total_affected_line_count": total_affected_lines,
        "max_overflow_by_side_pt": max_overflow_by_side,
        "median_overflow_by_side_pt": median_overflow_by_side,
        "pages_with_multiple_sides": len(multi_side_pages),
        "multiple_sides_pages_compact": compact_page_list(multi_side_pages),
        "pattern_page_ranges": pattern_page_ranges,
        "dominant_margin_side": dominant_side,
        "triage_tier": "informational",
        "triage_note": (
            "P011 reports automated margin-boundary crossings for manual NJIT verification. "
            "Page-level warnings are triage signals, not confirmed layout defects. "
            "Many small same-side overflows on compressed PDFs may reflect coordinate shifts "
            "rather than true margin violations."
        ),
    }


def build_p019_page_numbering_triage_summary(
    findings: list[AuditFinding],
) -> dict[str, Any] | None:
    """Build a P019-specific rollup for page-numbering sequence/style triage.

    Raw findings are not modified. Groups by issue_type, triage_tier, and
    p019_triage_category. Never includes candidate text or page content.
    """
    p019_findings = [f for f in findings if f.rule_id == P019_RULE_ID]
    if not p019_findings:
        return None

    issue_type_counts: Counter[str] = Counter()
    triage_tier_counts: Counter[str] = Counter()
    category_counts: Counter[str] = Counter()
    affected_pages: list[int] = []

    for finding in p019_findings:
        details = finding.details or {}
        issue_type = details.get("issue_type", "")
        if issue_type:
            issue_type_counts[issue_type] += 1
        tier = details.get("triage_tier", "")
        if tier:
            triage_tier_counts[tier] += 1
        category = details.get("p019_triage_category", "")
        if category:
            category_counts[category] += 1
        if finding.page is not None:
            affected_pages.append(finding.page)

    return {
        "total_findings": len(p019_findings),
        "by_issue_type": dict(sorted(issue_type_counts.items())),
        "by_triage_tier": dict(sorted(triage_tier_counts.items())),
        "by_category": dict(sorted(category_counts.items())),
        "high_priority_count": triage_tier_counts.get("high", 0),
        "medium_priority_count": triage_tier_counts.get("medium", 0),
        "low_priority_count": triage_tier_counts.get("low", 0),
        "affected_pages_compact": compact_page_list(sorted(set(affected_pages))),
        "review_guidance": (
            "High-priority: review first — especially sequence gaps and missing page numbers. "
            "Medium-priority: manual review; may include boundary or multiple-candidate cases. "
            "Low-priority: likely artifact-heavy; spot check only."
        ),
    }


def _normalize_p036_section_type(details: dict[str, str]) -> str:
    section_type = details.get("section_type", "").strip()
    if section_type:
        return section_type

    issue_type = details.get("issue_type", "").strip().lower()
    if issue_type.startswith("toc_"):
        return "toc"
    if issue_type.startswith("lot_"):
        return "lot"
    if issue_type.startswith("lof_"):
        return "lof"
    return "unknown"


def _parse_p036_gap_ratio(details: dict[str, str]) -> float | None:
    raw = details.get("gap_ratio", "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _bucket_p036_gap_ratio(gap_ratio: float) -> str:
    if gap_ratio < 0.25:
        return "very_tight"
    if gap_ratio < 0.50:
        return "tight"
    if gap_ratio < 0.75:
        return "moderately_tight"
    if gap_ratio < 1.0:
        return "slightly_tight"
    return "unexpected_non_tight"


def build_p036_toc_list_spacing_triage_summary(
    findings: list[AuditFinding],
) -> dict[str, Any] | None:
    """Build a P036-specific rollup for TOC/LoT/LoF inter-entry spacing triage."""
    p036_findings = [f for f in findings if f.rule_id == P036_RULE_ID]
    if not p036_findings:
        return None

    pages = sorted({f.page for f in p036_findings if f.page is not None})
    issue_type_counts: Counter[str] = Counter()
    section_type_counts: Counter[str] = Counter()
    triage_tier_counts: Counter[str] = Counter()
    spacing_gap_bucket_counts: Counter[str] = Counter()
    section_pages: dict[str, list[int]] = defaultdict(list)
    gap_ratios: list[float] = []

    for finding in p036_findings:
        details = finding.details or {}
        issue_type = details.get("issue_type", "")
        if issue_type:
            issue_type_counts[issue_type] += 1

        section_type = _normalize_p036_section_type(details)
        section_type_counts[section_type] += 1
        if finding.page is not None:
            section_pages[section_type].append(finding.page)

        triage_tier = details.get("triage_tier", "").strip()
        if triage_tier:
            triage_tier_counts[triage_tier] += 1

        gap_ratio = _parse_p036_gap_ratio(details)
        if gap_ratio is not None:
            gap_ratios.append(gap_ratio)
            spacing_gap_bucket_counts[_bucket_p036_gap_ratio(gap_ratio)] += 1

    section_page_ranges = {
        section_type: compact_page_list(sorted(set(page_list)))
        for section_type, page_list in sorted(section_pages.items())
    }

    return {
        "raw_finding_count": len(p036_findings),
        "affected_page_count": len(pages),
        "affected_pages_compact": compact_page_list(pages),
        "issue_type_counts": dict(sorted(issue_type_counts.items())),
        "section_type_counts": dict(sorted(section_type_counts.items())),
        "section_page_ranges": section_page_ranges,
        "triage_tier_counts": dict(sorted(triage_tier_counts.items())),
        "spacing_gap_bucket_counts": dict(sorted(spacing_gap_bucket_counts.items())),
        "min_gap_ratio": min(gap_ratios) if gap_ratios else None,
        "max_gap_ratio": max(gap_ratios) if gap_ratios else None,
        "triage_note": (
            "P036 reports automated TOC/LoT/LoF inter-entry spacing warnings for "
            "manual NJIT verification."
        ),
        "recommended_action": (
            "Review affected TOC/List pages first; repeated same-section findings may "
            "indicate a systematic list-spacing issue; spot-check compressed PDFs for "
            "coordinate artifacts."
        ),
    }


def build_p038_frontmatter_heading_triage_summary(
    findings: list[AuditFinding],
) -> dict[str, Any] | None:
    """Build a P038-specific rollup for front-matter heading presence/phrase triage."""
    p038_findings = [f for f in findings if f.rule_id == P038_RULE_ID]
    if not p038_findings:
        return None

    pages = sorted({f.page for f in p038_findings if f.page is not None})
    issue_type_counts: Counter[str] = Counter()
    expected_heading_counts: Counter[str] = Counter()
    missing_heading_counts: Counter[str] = Counter()
    inexact_phrase_counts: Counter[str] = Counter()
    triage_tier_counts: Counter[str] = Counter()
    confidence_counts: Counter[str] = Counter()

    for finding in p038_findings:
        details = finding.details or {}
        issue_type = details.get("issue_type", "")
        if issue_type:
            issue_type_counts[issue_type] += 1

        expected_heading = details.get("expected_heading", "")
        if expected_heading:
            expected_heading_counts[expected_heading] += 1
            if issue_type == "required_heading_missing":
                missing_heading_counts[expected_heading] += 1
            elif issue_type == "heading_phrase_not_exact":
                inexact_phrase_counts[expected_heading] += 1

        triage_tier = details.get("triage_tier", "").strip()
        if triage_tier:
            triage_tier_counts[triage_tier] += 1

        confidence = details.get("confidence", "").strip()
        if confidence:
            confidence_counts[confidence] += 1

    return {
        "raw_finding_count": len(p038_findings),
        "affected_page_count": len(pages),
        "affected_pages_compact": compact_page_list(pages),
        "issue_type_counts": dict(sorted(issue_type_counts.items())),
        "expected_heading_counts": dict(sorted(expected_heading_counts.items())),
        "missing_heading_counts": dict(sorted(missing_heading_counts.items())),
        "inexact_phrase_counts": dict(sorted(inexact_phrase_counts.items())),
        "triage_tier_counts": dict(sorted(triage_tier_counts.items())),
        "confidence_counts": dict(sorted(confidence_counts.items())),
        "triage_note": (
            "P038 identifies required front-matter headings that are missing or use "
            "non-exact phrases. These are advisory warnings for manual NJIT verification."
        ),
        "recommended_action": (
            "Confirm that all required front-matter headings are present and use the "
            "exact NJIT canonical phrase (APPROVAL PAGE, BIOGRAPHICAL SKETCH, "
            "ACKNOWLEDGEMENTS, TABLE OF CONTENTS)."
        ),
    }


def build_p044_abstract_indentation_triage_summary(
    findings: list[AuditFinding],
) -> dict[str, Any] | None:
    """Build a P044-specific rollup for Abstract paragraph indentation triage."""
    p044_findings = [f for f in findings if f.rule_id == P044_RULE_ID]
    if not p044_findings:
        return None

    pages = sorted({f.page for f in p044_findings if f.page is not None})
    issue_type_counts: Counter[str] = Counter()
    triage_tier_counts: Counter[str] = Counter()
    paragraph_index_counts: Counter[str] = Counter()

    for finding in p044_findings:
        details = finding.details or {}
        issue_type = details.get("issue_type", "")
        if issue_type:
            issue_type_counts[issue_type] += 1

        triage_tier = details.get("triage_tier", "").strip()
        if triage_tier:
            triage_tier_counts[triage_tier] += 1

        para_idx_raw = details.get("paragraph_index", "")
        try:
            para_idx = str(int(para_idx_raw))
        except (ValueError, TypeError):
            para_idx = para_idx_raw or "(unknown)"
        if para_idx:
            paragraph_index_counts[para_idx] += 1

    return {
        "raw_finding_count": len(p044_findings),
        "affected_page_count": len(pages),
        "affected_pages_compact": compact_page_list(pages),
        "issue_type_counts": dict(sorted(issue_type_counts.items())),
        "triage_tier_counts": dict(sorted(triage_tier_counts.items())),
        "paragraph_index_counts": dict(sorted(paragraph_index_counts.items())),
        "triage_note": (
            "P044 reports automated Abstract paragraph indentation warnings "
            "for manual NJIT verification."
        ),
        "recommended_action": (
            "Check whether the first Abstract paragraph is unindented and each "
            "subsequent Abstract paragraph is indented according to NJIT guidance; "
            "use raw P044 findings for per-page details."
        ),
    }


def build_grouped_summary(findings: list[AuditFinding]) -> dict[str, Any]:
    """Build a grouped summary structure for triage use in JSON/Markdown reports.

    Returns a dict with two keys:
    - ``high_volume_rules``: list of rule summaries for rules with ≥5 findings.
    - ``by_rule_issue_type``: nested breakdown by rule_id → issue_type.

    Raw findings are not modified. This summary is additive.
    """
    # Group findings by rule_id → issue_type.
    by_rule_issue: dict[str, dict[str, list[AuditFinding]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for finding in findings:
        issue_type = (finding.details or {}).get("issue_type", "")
        by_rule_issue[finding.rule_id][issue_type].append(finding)

    # Build by_rule_issue_type (full cross-tabulation).
    by_rule_issue_type: dict[str, dict[str, dict[str, Any]]] = {}
    for rule_id in sorted(by_rule_issue):
        by_rule_issue_type[rule_id] = {}
        for issue_type, rule_findings in sorted(by_rule_issue[rule_id].items()):
            pages = sorted({f.page for f in rule_findings if f.page is not None})
            obs_counts: Counter[str] = Counter()
            conf_counts: Counter[str] = Counter()
            for f in rule_findings:
                obs = (f.details or {}).get("observed_summary", "")
                if obs:
                    obs_counts[obs] += 1
                conf = (f.details or {}).get("confidence", "")
                if conf:
                    conf_counts[conf] += 1
            entry: dict[str, Any] = {
                "count": len(rule_findings),
                "affected_page_count": len(pages),
                "affected_pages_compact": compact_page_list(pages),
            }
            if obs_counts:
                entry["observed_summary_sample"] = ", ".join(
                    v for v, _ in obs_counts.most_common(3)
                )
            if conf_counts:
                entry["confidence_counts"] = dict(conf_counts)
            by_rule_issue_type[rule_id][issue_type] = entry

    # Build high_volume_rules list (rules with ≥ HIGH_VOLUME_THRESHOLD findings).
    high_volume: list[dict[str, Any]] = []
    for rule_id in sorted(by_rule_issue):
        all_rule_findings = [
            f for issue_fs in by_rule_issue[rule_id].values() for f in issue_fs
        ]
        total = len(all_rule_findings)
        if total < HIGH_VOLUME_THRESHOLD:
            continue
        category = map_finding_rule_to_category(rule_id)
        issue_type_counts = {
            it: len(fs) for it, fs in sorted(by_rule_issue[rule_id].items())
        }
        pages = sorted({f.page for f in all_rule_findings if f.page is not None})
        obs_counts = Counter(
            (f.details or {}).get("observed_summary", "")
            for f in all_rule_findings
            if (f.details or {}).get("observed_summary")
        )
        entry = {
            "rule_id": rule_id,
            "count": total,
            "category": category,
            "issue_type_counts": issue_type_counts,
            "affected_page_count": len(pages),
            "affected_pages_compact": compact_page_list(pages),
        }
        if obs_counts:
            entry["observed_summary_sample"] = ", ".join(
                v for v, _ in obs_counts.most_common(3)
            )
        high_volume.append(entry)

    result: dict[str, Any] = {
        "high_volume_rules": high_volume,
        "by_rule_issue_type": by_rule_issue_type,
    }
    p013_triage = build_p013_triage_summary(findings)
    if p013_triage is not None:
        result["p013_triage"] = p013_triage
    p026_triage = build_p026_font_triage_summary(findings)
    if p026_triage is not None:
        result["p026_font_triage"] = p026_triage
    p011_triage = build_p011_margin_triage_summary(findings)
    if p011_triage is not None:
        result["p011_margin_triage"] = p011_triage
    p012_triage = build_p012_annotation_triage_summary(findings)
    if p012_triage is not None:
        result["p012_annotation_triage"] = p012_triage
    p019_triage = build_p019_page_numbering_triage_summary(findings)
    if p019_triage is not None:
        result["p019_page_numbering_triage"] = p019_triage
    p036_triage = build_p036_toc_list_spacing_triage_summary(findings)
    if p036_triage is not None:
        result["p036_toc_list_spacing_triage"] = p036_triage
    p038_triage = build_p038_frontmatter_heading_triage_summary(findings)
    if p038_triage is not None:
        result["p038_frontmatter_heading_triage"] = p038_triage
    p044_triage = build_p044_abstract_indentation_triage_summary(findings)
    if p044_triage is not None:
        result["p044_abstract_indentation_triage"] = p044_triage
    return result


def audit_findings_to_json_dict(
    findings: list[AuditFinding], metadata: dict[str, str]
) -> dict[str, Any]:
    """Convert findings + metadata into a structured serializable payload."""
    audit_type = metadata.get("audit_type", "pdf")
    prepared = _findings_sorted_for_export(_prepare_findings_for_export(findings, audit_type))

    serialized_findings: list[dict[str, Any]] = []
    for finding in prepared:
        details = _sanitize_details(finding.details)
        _, student_facing_role = _student_export_role(finding.rule_id, details)
        entry: dict[str, Any] = {
            "rule_id": finding.rule_id,
            "public_rule_id": public_display_rule_id(finding.rule_id),
            "severity": finding.severity.value,
            "message": finding.message,
            "page": finding.page,
            "details": details,
            "student_visible_problem": False,
            "student_facing_role": student_facing_role,
        }
        if finding.page is not None:
            entry["pdf_page"] = finding.page
        document_page_label = details.get("document_page_label", "").strip()
        if document_page_label:
            entry["document_page_label"] = document_page_label
        if audit_type == "tex":
            entry["source_file"] = _source_location_basename(details)
            entry["source_line"] = details.get("line", "")
        serialized_findings.append(entry)

    problem_number_map = _problem_number_map(serialized_findings)
    for index, entry in enumerate(serialized_findings):
        problem_number = problem_number_map.get(index)
        entry["problem_number"] = problem_number
        entry["problem_anchor"] = f"problem-{problem_number}" if problem_number else ""
        entry["student_visible_problem"] = problem_number is not None
        details = entry.get("details", {})
        if (
            entry.get("rule_id") == P013_RULE_ID
            and not entry["student_visible_problem"]
            and isinstance(details, dict)
            and details.get("issue_type") == P013_PAGE_ISSUE_TYPE
        ):
            entry["student_facing_role"] = "inventory"

    inventory_finding_count = sum(
        1
        for entry in serialized_findings
        if entry.get("student_facing_role") == "inventory"
    )

    meta_block: dict[str, Any] = {
        **metadata,
        "total_findings": len(prepared),
        "visible_problem_count": len(problem_number_map),
        "inventory_finding_count": inventory_finding_count,
        "counts_by_severity": _severity_counts(prepared),
        "counts_by_rule_id": _rule_counts(prepared),
        "counts_by_public_rule_id": {
            public_display_rule_id(rule_id): count
            for rule_id, count in _rule_counts(prepared).items()
        },
        "counts_by_category": _category_counts(prepared),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "note": "Findings are heuristic signals and require human review.",
    }
    if audit_type == "tex":
        locations = {
            (details.get("file", ""), details.get("line", ""))
            for details in (f.details for f in prepared)
            if details.get("file") or details.get("line")
        }
        meta_block["source_location_count"] = len(locations)

    return {
        "metadata": meta_block,
        "grouped_summary": build_grouped_summary(prepared),
        "grouped_findings": build_grouped_findings(prepared, audit_type),
        "findings": serialized_findings,
    }


# Detail keys that may contain private source content (label names, ref keys,
# body text, author/title info).  These are removed from web-exported JSON
# findings for source (TeX) audits.  Numeric/structural keys are preserved.
_UNSAFE_SOURCE_DETAIL_KEYS: frozenset[str] = frozenset(
    {
        "label",
        "ref",
        "caption",
        "caption_text",
        "title",
        "title_text",
        "author",
        "author_name",
        "body",
        "text",
        "line_text",
        "body_text",
        "extracted_text",
        "entry_text",
        "heading_text",
        "observed_summary",
        "annotation_text",
        "comment_text",
    }
)

# Source rule IDs whose message fields may embed private label/ref/caption names.
_SOURCE_RULE_IDS_FOR_SANITIZE: frozenset[str] = frozenset(
    {"P001", "P002", "P003", "P004", "P005", "P006", "P007", "P008", "P009", "P010"}
)


def _privacy_safe_source_message(rule_id: str, issue_type: str, details: dict[str, str]) -> str:
    """Return a generic privacy-safe message for a source-audit finding.

    This replaces the raw ``message`` field (which may contain label/ref/caption
    names) with a short structural description suitable for web export.
    """
    location = format_source_location(details)
    public_rule_id = public_display_rule_id(rule_id)
    rule_label = f"{public_rule_id} ({issue_type})" if issue_type else public_rule_id
    return f"{rule_label} issue detected at {location}. See polished comment for details."


def sanitize_report_for_web_export(report: dict[str, Any]) -> dict[str, Any]:
    """Return a privacy-reduced copy of an audit report for web JSON/Markdown export.

    Applied only to source (TeX) audits.  PDF audit reports are returned unchanged.

    Sanitization rules:
    - ``findings[].message`` for source rules (P001–P010) is replaced with a
      generic structural message that does not embed label names, ref keys,
      caption text, or other private content.
    - Unsafe detail keys (``label``, ``ref``, ``caption``, ``title``, ``author``,
      ``body``, ``text``, and related source-snippet keys) are removed from each
      finding's ``details`` dict.
    - Safe structural keys (``file``, ``line``, ``issue_type``, ``command``,
      ``confidence``, ``triage_tier``, ``suggested_fix``, numeric counts, etc.)
      are preserved.
    - Finding counts, rule IDs, severity, category, ``source_file``, and
      ``source_line`` are never altered.
    - PDF report structure (``grouped_summary``, ``metadata``) is not modified.
    """
    import copy

    audit_type = str(report.get("metadata", {}).get("audit_type", "pdf"))
    if audit_type != "tex":
        return report

    result = copy.deepcopy(report)
    sanitized_findings: list[dict[str, Any]] = []
    for finding in result.get("findings", []):
        rule_id = str(finding.get("rule_id", ""))
        details_raw = finding.get("details", {})
        if isinstance(details_raw, dict):
            # Remove unsafe keys; keep safe structural / numeric keys.
            clean_details = {
                k: v
                for k, v in details_raw.items()
                if k not in _UNSAFE_SOURCE_DETAIL_KEYS
            }
        else:
            clean_details = {}
        finding["details"] = clean_details

        # Replace raw message for source rules to avoid leaking label/ref names.
        if rule_id in _SOURCE_RULE_IDS_FOR_SANITIZE:
            issue_type = str(clean_details.get("issue_type", ""))
            finding["message"] = _privacy_safe_source_message(
                rule_id, issue_type, {str(k): str(v) for k, v in clean_details.items()}
            )
        sanitized_findings.append(finding)
    result["findings"] = sanitized_findings
    return result


def write_json_report(
    findings: list[AuditFinding], metadata: dict[str, str], output_path: Path
) -> None:
    """Write structured JSON report to disk."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = audit_findings_to_json_dict(findings, metadata)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _format_summary_table(payload: dict[str, Any]) -> str:
    meta = payload["metadata"]
    sev = meta["counts_by_severity"]
    lines = [
        "| Metric | Value |",
        "|---|---:|",
        f"| Total findings | {meta['total_findings']} |",
        f"| PASS | {sev.get('PASS', 0)} |",
        f"| WARNING | {sev.get('WARNING', 0)} |",
        f"| FAIL | {sev.get('FAIL', 0)} |",
    ]
    return "\n".join(lines)


def _format_grouped_summary_section(grouped: dict[str, Any]) -> list[str]:
    """Render the grouped summary as Markdown lines."""
    high_volume = grouped.get("high_volume_rules", [])
    if not high_volume:
        return []

    lines: list[str] = []
    lines.append("## Repeated Findings Summary")
    lines.append("")
    lines.append(
        f"Rules with {HIGH_VOLUME_THRESHOLD}+ findings grouped for triage. "
        "Raw findings are listed below. All findings are heuristic warnings "
        "requiring manual review."
    )
    lines.append("")
    lines.append("| Rule | Count | Category | Pages | Top Issue Types |")
    lines.append("|------|------:|---------|------:|-----------------|")
    for entry in high_volume:
        rule_id = entry["rule_id"]
        count = entry["count"]
        category = entry["category"]
        page_count = entry["affected_page_count"]
        page_str = f"{page_count}" if page_count else "—"
        issue_parts = [
            f"{it}×{n}" for it, n in sorted(entry["issue_type_counts"].items()) if it
        ]
        if not issue_parts:
            issue_parts = [f"{n} findings" for n in entry["issue_type_counts"].values()]
        issue_str = "; ".join(issue_parts[:2])
        obs = entry.get("observed_summary_sample", "")
        if obs:
            issue_str += f" ({obs[:40]})" if len(obs) > 40 else f" ({obs})"
        lines.append(f"| `{rule_id}` | {count} | {category} | {page_str} | {issue_str} |")
    lines.append("")
    return lines


_MARKDOWN_GROUPED_SUMMARIES_HEADING = "Advanced grouped summaries"


def _format_grouped_findings_section(
    grouped_findings: list[dict[str, Any]],
) -> list[str]:
    """Render grouped repeated-problem display for Markdown reports."""
    repeated_groups = [
        entry
        for entry in grouped_findings
        if int(entry.get("occurrence_count", 0) or 0) > 1
    ]
    if not repeated_groups:
        return []

    lines: list[str] = []
    lines.append(f"## {_MARKDOWN_GROUPED_SUMMARIES_HEADING}")
    lines.append("")
    lines.append(
        "Repeated findings with the same rule, issue type, severity, user-facing problem, "
        "suggested fix, and meaningful triage/context metadata are grouped here for review. "
        "The raw findings remain unchanged in the per-rule findings section below."
    )
    lines.append("")

    for entry in repeated_groups:
        rule_id = str(entry.get("rule_id", ""))
        severity = str(entry.get("severity", ""))
        issue_type = str(entry.get("issue_type", ""))
        occurrence_count = int(entry.get("occurrence_count", 0) or 0)
        affected_label = str(entry.get("affected_label", "Occurrences"))
        affected_compact = str(entry.get("affected_compact", "")).strip()
        problem = str(entry.get("problem", "")).strip()
        suggested_fix = str(entry.get("suggested_fix", "")).strip()

        heading = f"### {rule_id} — {occurrence_count} occurrence"
        if occurrence_count != 1:
            heading += "s"
        lines.append(heading)
        lines.append("")
        lines.append(f"- Severity: `{severity}`")
        if issue_type:
            lines.append(f"- Issue type: {humanize_issue_type(issue_type)}")
        if affected_compact:
            lines.append(f"- {affected_label}: {affected_compact}")
        if problem:
            lines.append(f"- Problem: {problem}")
        if suggested_fix:
            lines.append(f"- Suggested fix: {suggested_fix}")
        pattern_note = _high_volume_pattern_note(
            rule_id, issue_type, occurrence_count, affected_label, affected_compact
        )
        if pattern_note:
            lines.append(f"- Why this repeats: {pattern_note}")
        lines.append("")

    return lines


def _format_p013_triage_section(grouped: dict[str, Any]) -> list[str]:
    """Render P013-specific triage rollup for Markdown reports."""
    triage = grouped.get("p013_triage")
    if not triage:
        return []

    lines: list[str] = []
    lines.append("## P013 Page-Number Candidate Inventory")
    lines.append("")
    lines.append(triage.get("triage_note", ""))
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    lines.append(f"| Raw P013 detector entries | {triage['raw_finding_count']} |")
    lines.append(f"| Page-level inventory entries | {triage['page_level_finding_count']} |")
    lines.append(f"| Document overview | {triage['document_overview_finding_count']} |")
    lines.append(f"| Affected pages | {triage['affected_page_count']} |")
    lines.append(f"| Pages with multiple candidates | {triage['pages_with_multiple_candidates']} |")
    lines.append("")

    issue_counts = triage.get("issue_type_counts", {})
    if issue_counts:
        lines.append("### Issue type counts")
        lines.append("")
        for issue_type, count in sorted(issue_counts.items()):
            label = issue_type or "(unspecified)"
            lines.append(f"- `{label}`: {count}")
        lines.append("")

    position_counts = triage.get("position_type_counts", {})
    style_counts = triage.get("number_style_counts", {})
    if position_counts or style_counts:
        lines.append("### Position and style distribution (page-level)")
        lines.append("")
        for position, count in sorted(position_counts.items()):
            lines.append(f"- position `{position}`: {count}")
        for style, count in sorted(style_counts.items()):
            lines.append(f"- style `{style}`: {count}")
        lines.append("")

    pattern_ranges = triage.get("pattern_page_ranges", {})
    if pattern_ranges:
        lines.append("### Position/style pattern page ranges")
        lines.append("")
        for observed, page_range in pattern_ranges.items():
            lines.append(f"- `{observed}`: pages {page_range}")
        lines.append("")

    dominant_pattern = triage.get("dominant_pattern", "")
    if dominant_pattern:
        lines.append("### Calibration summary")
        lines.append("")
        lines.append(
            f"Document pattern label: `{triage.get('document_pattern_label', '')}`"
        )
        lines.append(
            f"Dominant pattern `{dominant_pattern}` covers "
            f"{triage.get('dominant_pattern_page_count', 0)} page(s) "
            f"({triage.get('dominant_pattern_share_pct', 0.0)}%)."
        )
        lines.append("")

    calibration_buckets = triage.get("calibration_buckets", {})
    if calibration_buckets:
        lines.append("### Calibration buckets")
        lines.append("")
        lines.append(
            triage.get(
                "calibration_note",
                "Calibration buckets are triage-only summaries; raw findings remain below.",
            )
        )
        lines.append("")
        for bucket_name, bucket in calibration_buckets.items():
            lines.append(
                f"- `{bucket_name}`: {bucket.get('count', 0)} page(s)"
                + (
                    f" — pages {bucket.get('pages_compact', '')}"
                    if bucket.get("pages_compact")
                    else ""
                )
            )
        lines.append("")

    multi_compact = triage.get("multiple_candidate_pages_compact", "")
    if multi_compact:
        lines.append(f"Pages with multiple candidates: {multi_compact}")
        lines.append("")

    affected_compact = triage.get("affected_pages_compact", "")
    if affected_compact:
        lines.append(f"All affected pages (compact): {affected_compact}")
        lines.append("")

    lines.append(
        "Routine per-page P013 candidates are inventory evidence. They are not "
        "listed as problems unless another finding reports a specific page-number defect."
    )
    lines.append("")
    return lines


def _format_p026_triage_section(grouped: dict[str, Any]) -> list[str]:
    """Render P026-specific triage rollup for Markdown reports."""
    triage = grouped.get("p026_font_triage")
    if not triage:
        return []

    lines: list[str] = []
    lines.append("## P026 Body Font Compliance Triage")
    lines.append("")
    lines.append(triage.get("triage_note", ""))
    lines.append("")
    lines.append(
        "Student-facing problem cards may summarize repeated font patterns "
        "document-wide using human-readable font wording. This triage section lists "
        "pattern counts and page ranges only."
    )
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    lines.append(f"| Raw P026 findings | {triage['raw_finding_count']} |")
    lines.append(f"| Affected pages | {triage['affected_page_count']} |")
    both_count = triage.get("pages_with_both_issue_types", 0)
    if both_count:
        lines.append(f"| Pages with family and size issues | {both_count} |")
    lines.append("")

    issue_counts = triage.get("issue_type_counts", {})
    if issue_counts:
        lines.append("### Issue type counts")
        lines.append("")
        for issue_type, count in sorted(issue_counts.items()):
            label = issue_type or "(unspecified)"
            lines.append(f"- `{label}`: {count}")
        lines.append("")

    font_labels = triage.get("font_label_counts", {})
    if font_labels:
        from njit_auditor.p026_student_preview import student_facing_observed_font_phrase

        lines.append("### Dominant non-compliant font labels (family issues)")
        lines.append("")
        for label, count in font_labels.items():
            readable = student_facing_observed_font_phrase(label)
            lines.append(f"- {readable}: {count} page(s)")
        lines.append("")

    size_labels = triage.get("size_observed_label_counts", {})
    if size_labels:
        lines.append("### Observed size labels (size issues)")
        lines.append("")
        for label, count in size_labels.items():
            lines.append(f"- `{label}`: {count} page(s)")
        lines.append("")

    pattern_ranges = triage.get("pattern_page_ranges", {})
    if pattern_ranges:
        from njit_auditor.p026_student_preview import student_facing_observed_font_phrase

        lines.append("### Issue/font pattern page ranges")
        lines.append("")
        for pattern, page_range in pattern_ranges.items():
            issue_type, _, observed = pattern.partition("/")
            readable = student_facing_observed_font_phrase(observed) if observed else observed
            label = f"{issue_type} — {readable}" if readable else pattern
            lines.append(f"- {label}: pages {page_range}")
        lines.append("")

    dominant_pattern = triage.get("dominant_pattern", "")
    if dominant_pattern:
        lines.append("### Calibration summary")
        lines.append("")
        lines.append(
            f"Document pattern label: `{triage.get('document_pattern_label', '')}`"
        )
        lines.append(
            f"Dominant pattern `{dominant_pattern}` covers "
            f"{triage.get('dominant_pattern_page_count', 0)} page(s) "
            f"({triage.get('dominant_pattern_share_pct', 0.0)}%)."
        )
        lines.append("")

    calibration_buckets = triage.get("calibration_buckets", {})
    if calibration_buckets:
        lines.append("### Calibration buckets")
        lines.append("")
        lines.append(
            triage.get(
                "calibration_note",
                "Calibration buckets are triage-only summaries; raw findings remain below.",
            )
        )
        lines.append("")
        for bucket_name, bucket in calibration_buckets.items():
            lines.append(
                f"- `{bucket_name}`: {bucket.get('count', 0)} page(s)"
                + (
                    f" — pages {bucket.get('pages_compact', '')}"
                    if bucket.get("pages_compact")
                    else ""
                )
            )
        lines.append("")

    affected_compact = triage.get("affected_pages_compact", "")
    if affected_compact:
        lines.append(f"All affected pages (compact): {affected_compact}")
        lines.append("")

    lines.append(
        "Raw per-page P026 findings are listed under **Findings by Rule → P026** below."
    )
    lines.append("")
    return lines


def _format_p012_triage_section(grouped: dict[str, Any]) -> list[str]:
    """Render P012-specific triage rollup for Markdown reports."""
    triage = grouped.get("p012_annotation_triage")
    if not triage:
        return []

    lines: list[str] = []
    lines.append("## P012 Annotation/Comment Triage")
    lines.append("")
    lines.append(triage.get("triage_note", ""))
    lines.append("")
    lines.append(
        "Student-facing problem cards may summarize high-volume annotation warnings "
        "as one document-wide card with affected-page ranges. This triage section "
        "never repeats annotation text or reviewer comments."
    )
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    lines.append(f"| Raw P012 findings | {triage['raw_finding_count']} |")
    lines.append(f"| Affected pages | {triage['affected_page_count']} |")
    max_per_page = triage.get("annotations_per_page_max", 0)
    if max_per_page:
        lines.append(f"| Max annotations on one page | {max_per_page} |")
    multi_count = triage.get("pages_with_multiple_annotations", 0)
    if multi_count:
        lines.append(f"| Pages with multiple annotations | {multi_count} |")
    dominant = triage.get("dominant_annotation_type", "")
    if dominant:
        lines.append(f"| Dominant annotation type | `{dominant}` |")
    lines.append("")

    type_counts = triage.get("annotation_type_counts", {})
    if type_counts:
        lines.append("### Annotation type counts")
        lines.append("")
        for annotation_type, count in sorted(type_counts.items()):
            lines.append(f"- `{annotation_type}`: {count}")
        lines.append("")

    type_ranges = triage.get("type_page_ranges", {})
    if type_ranges:
        lines.append("### Annotation type page ranges")
        lines.append("")
        for annotation_type, page_range in type_ranges.items():
            lines.append(f"- `{annotation_type}`: pages {page_range}")
        lines.append("")

    multi_compact = triage.get("multiple_annotations_pages_compact", "")
    if multi_compact:
        lines.append(f"Pages with multiple annotations: {multi_compact}")
        lines.append("")

    affected_compact = triage.get("affected_pages_compact", "")
    if affected_compact:
        lines.append(f"All affected pages (compact): {affected_compact}")
        lines.append("")

    recommended = triage.get("recommended_action", "")
    if recommended:
        lines.append(f"**Recommended action:** {recommended}")
        lines.append("")

    lines.append(
        "Raw per-annotation P012 findings are listed under **Findings by Rule → P012** "
        "below. Annotation text is not repeated in this triage section."
    )
    lines.append("")
    return lines


def _format_p011_triage_section(grouped: dict[str, Any]) -> list[str]:
    """Render P011-specific triage rollup for Markdown reports."""
    triage = grouped.get("p011_margin_triage")
    if not triage:
        return []

    lines: list[str] = []
    lines.append("## P011 Margin/Overflow Triage")
    lines.append("")
    lines.append(triage.get("triage_note", ""))
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    lines.append(f"| Raw P011 warnings | {triage['raw_finding_count']} |")
    lines.append(f"| Affected pages | {triage['affected_page_count']} |")
    lines.append(f"| Total affected lines (sum) | {triage.get('total_affected_line_count', 0)} |")
    multi = triage.get("pages_with_multiple_sides", 0)
    if multi:
        lines.append(f"| Pages with multiple margin sides | {multi} |")
    dominant = triage.get("dominant_margin_side", "")
    if dominant:
        lines.append(f"| Dominant margin side | `{dominant}` |")
    lines.append("")

    side_counts = triage.get("side_counts", {})
    if side_counts:
        lines.append("### Margin side counts")
        lines.append("")
        for side, count in sorted(side_counts.items()):
            lines.append(f"- `{side}`: {count}")
        lines.append("")

    confidence_counts = triage.get("confidence_counts", {})
    if confidence_counts:
        lines.append("### Confidence distribution")
        lines.append("")
        for level, count in sorted(confidence_counts.items()):
            lines.append(f"- `{level}`: {count}")
        lines.append("")

    max_overflow = triage.get("max_overflow_by_side_pt", {})
    median_overflow = triage.get("median_overflow_by_side_pt", {})
    if max_overflow or median_overflow:
        lines.append("### Overflow distance by side (pt)")
        lines.append("")
        for side in sorted(set(max_overflow) | set(median_overflow)):
            max_pt = max_overflow.get(side)
            med_pt = median_overflow.get(side)
            parts = []
            if max_pt is not None:
                parts.append(f"max {max_pt}")
            if med_pt is not None:
                parts.append(f"median {med_pt}")
            lines.append(f"- `{side}`: {', '.join(parts)}")
        lines.append("")

    pattern_ranges = triage.get("pattern_page_ranges", {})
    if pattern_ranges:
        lines.append("### Margin-side page ranges")
        lines.append("")
        for side, page_range in pattern_ranges.items():
            lines.append(f"- `{side}`: pages {page_range}")
        lines.append("")

    affected_compact = triage.get("affected_pages_compact", "")
    if affected_compact:
        lines.append(f"All affected pages (compact): {affected_compact}")
        lines.append("")

    lines.append(
        "Raw per-page P011 findings are listed under **Findings by Rule → P011** below."
    )
    lines.append("")
    return lines


def _format_p019_triage_section(grouped: dict[str, Any]) -> list[str]:
    """Render P019-specific triage rollup for Markdown reports."""
    triage = grouped.get("p019_page_numbering_triage")
    if not triage:
        return []

    lines: list[str] = []
    lines.append("## P019 Page-Numbering Triage Summary")
    lines.append("")
    lines.append(
        "P019 reports heuristic page-numbering sequence and style issues for manual NJIT "
        "verification. Raw findings are preserved; this section summarizes the most common "
        "page-numbering patterns to review."
    )
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    lines.append(f"| Total P019 findings | {triage['total_findings']} |")
    lines.append(f"| Check first | {triage['high_priority_count']} |")
    lines.append(f"| Review carefully | {triage['medium_priority_count']} |")
    lines.append(f"| Spot check | {triage['low_priority_count']} |")
    lines.append("")

    issue_counts = triage.get("by_issue_type", {})
    if issue_counts:
        lines.append("### Issue type counts")
        lines.append("")
        for issue_type, count in sorted(issue_counts.items()):
            lines.append(f"- `{issue_type}`: {count}")
        lines.append("")

    guidance = triage.get("review_guidance", "")
    if guidance:
        lines.append("### Reviewer guidance")
        lines.append("")
        lines.append(
            "- Check first: sequence gaps and missing page numbers usually need the "
            "closest manual review."
        )
        lines.append(
            "- Review carefully: boundary and multiple-candidate cases may need manual judgment."
        )
        lines.append(
            "- Spot check: artifact-heavy cases may only need a quick confirmation."
        )
        lines.append("")

    affected_compact = triage.get("affected_pages_compact", "")
    if affected_compact:
        lines.append(f"Affected pages (compact): {affected_compact}")
        lines.append("")

    lines.append(
        "Raw per-page P019 findings are listed under **Findings by Rule → P019** below."
    )
    lines.append("")
    return lines


def _format_p036_triage_section(grouped: dict[str, Any]) -> list[str]:
    """Render P036-specific triage rollup for Markdown reports."""
    triage = grouped.get("p036_toc_list_spacing_triage")
    if not triage:
        return []

    def _fmt_ratio(value: Any) -> str:
        if isinstance(value, (int, float)):
            return f"{float(value):.2f}"
        return "—"

    lines: list[str] = []
    lines.append("## P036 TOC/List Spacing Triage")
    lines.append("")
    lines.append(triage.get("triage_note", ""))
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    lines.append(f"| Raw P036 findings | {triage['raw_finding_count']} |")
    lines.append(f"| Affected pages | {triage['affected_page_count']} |")
    lines.append(f"| Min gap ratio | {_fmt_ratio(triage.get('min_gap_ratio'))} |")
    lines.append(f"| Max gap ratio | {_fmt_ratio(triage.get('max_gap_ratio'))} |")
    lines.append("")

    issue_counts = triage.get("issue_type_counts", {})
    if issue_counts:
        lines.append("### Issue type counts")
        lines.append("")
        for issue_type, count in sorted(issue_counts.items()):
            lines.append(f"- `{issue_type}`: {count}")
        lines.append("")

    section_counts = triage.get("section_type_counts", {})
    if section_counts:
        lines.append("### Section type counts")
        lines.append("")
        for section_type, count in sorted(section_counts.items()):
            lines.append(f"- `{section_type}`: {count}")
        lines.append("")

    bucket_counts = triage.get("spacing_gap_bucket_counts", {})
    if bucket_counts:
        lines.append("### Spacing gap bucket counts")
        lines.append("")
        for bucket, count in sorted(bucket_counts.items()):
            lines.append(f"- `{bucket}`: {count}")
        lines.append("")

    page_ranges = triage.get("section_page_ranges", {})
    if page_ranges:
        lines.append("### Section page ranges")
        lines.append("")
        for section_type, page_range in sorted(page_ranges.items()):
            lines.append(f"- `{section_type}`: pages {page_range}")
        lines.append("")

    affected_compact = triage.get("affected_pages_compact", "")
    if affected_compact:
        lines.append(f"All affected pages (compact): {affected_compact}")
        lines.append("")

    recommended_action = triage.get("recommended_action", "")
    if recommended_action:
        lines.append(f"**Recommended action:** {recommended_action}")
        lines.append("")

    lines.append(
        "Raw per-page P036 findings are listed under **Findings by Rule → P036** below."
    )
    lines.append("")
    return lines


def _format_p038_triage_section(grouped: dict[str, Any]) -> list[str]:
    """Render P038-specific triage rollup for Markdown reports."""
    triage = grouped.get("p038_frontmatter_heading_triage")
    if not triage:
        return []

    lines: list[str] = []
    lines.append("## P038 Front-Matter Heading Triage")
    lines.append("")
    lines.append(triage.get("triage_note", ""))
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    lines.append(f"| Raw P038 findings | {triage['raw_finding_count']} |")
    lines.append(f"| Affected pages | {triage['affected_page_count']} |")
    lines.append("")

    issue_counts = triage.get("issue_type_counts", {})
    if issue_counts:
        lines.append("### Issue type counts")
        lines.append("")
        for issue_type, count in sorted(issue_counts.items()):
            lines.append(f"- `{issue_type}`: {count}")
        lines.append("")

    missing_counts = triage.get("missing_heading_counts", {})
    if missing_counts:
        lines.append("### Missing heading counts")
        lines.append("")
        for heading, count in sorted(missing_counts.items()):
            lines.append(f"- `{heading}`: {count}")
        lines.append("")

    inexact_counts = triage.get("inexact_phrase_counts", {})
    if inexact_counts:
        lines.append("### Non-exact phrase counts")
        lines.append("")
        for heading, count in sorted(inexact_counts.items()):
            lines.append(f"- `{heading}`: {count}")
        lines.append("")

    confidence_counts = triage.get("confidence_counts", {})
    if confidence_counts:
        lines.append("### Confidence counts")
        lines.append("")
        for conf, count in sorted(confidence_counts.items()):
            lines.append(f"- `{conf}`: {count}")
        lines.append("")

    affected_compact = triage.get("affected_pages_compact", "")
    if affected_compact:
        lines.append(f"All affected pages (compact): {affected_compact}")
        lines.append("")

    recommended_action = triage.get("recommended_action", "")
    if recommended_action:
        lines.append(f"**Recommended action:** {recommended_action}")
        lines.append("")

    lines.append(
        "Raw per-page P038 findings are listed under **Findings by Rule → P038** below."
    )
    lines.append("")
    return lines


def _format_p044_triage_section(grouped: dict[str, Any]) -> list[str]:
    """Render P044-specific triage rollup for Markdown reports."""
    triage = grouped.get("p044_abstract_indentation_triage")
    if not triage:
        return []

    lines: list[str] = []
    lines.append("## P044 Abstract Indentation Triage")
    lines.append("")
    lines.append(triage.get("triage_note", ""))
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    lines.append(f"| Raw P044 findings | {triage['raw_finding_count']} |")
    lines.append(f"| Affected pages | {triage['affected_page_count']} |")
    lines.append("")

    issue_counts = triage.get("issue_type_counts", {})
    if issue_counts:
        lines.append("### Issue type counts")
        lines.append("")
        for issue_type, count in sorted(issue_counts.items()):
            lines.append(f"- `{issue_type}`: {count}")
        lines.append("")

    para_counts = triage.get("paragraph_index_counts", {})
    if para_counts:
        lines.append("### Paragraph index counts")
        lines.append("")
        for para_idx, count in sorted(para_counts.items()):
            lines.append(f"- paragraph {para_idx}: {count}")
        lines.append("")

    affected_compact = triage.get("affected_pages_compact", "")
    if affected_compact:
        lines.append(f"All affected pages (compact): {affected_compact}")
        lines.append("")

    recommended_action = triage.get("recommended_action", "")
    if recommended_action:
        lines.append(f"**Recommended action:** {recommended_action}")
        lines.append("")

    lines.append(
        "Raw per-page P044 findings are listed under **Findings by Rule → P044** below."
    )
    lines.append("")
    return lines


def _group_findings_by_rule(findings: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for finding in findings:
        grouped[str(finding["rule_id"])].append(finding)
    return dict(sorted(grouped.items()))


def _p012_document_stats_for_markdown(
    p012_count_by_page: dict[int, int] | None,
) -> Any:
    """Return document-level P012 stats when presentation summary mode applies."""
    if not p012_count_by_page:
        return None
    from njit_auditor.p012_student_preview import (
        build_p012_presentation_stats,
        should_use_p012_document_summary,
    )

    stats = build_p012_presentation_stats(p012_count_by_page)
    if should_use_p012_document_summary(
        stats.affected_page_count,
        stats.raw_finding_count,
    ):
        return stats
    return None


def _p026_document_stats_for_markdown(
    details: dict[str, str],
    p026_pattern_stats: dict[tuple[str, str, str], Any] | None,
) -> Any:
    if not p026_pattern_stats:
        return None
    from njit_auditor.p026_student_preview import (
        p026_pattern_key,
        should_use_p026_document_summary,
    )

    issue_type = details.get("issue_type", "").strip()
    key = p026_pattern_key(issue_type, details)
    stats = p026_pattern_stats.get(key)
    if stats is None:
        return None
    if should_use_p026_document_summary(
        stats.affected_page_count,
        stats.raw_finding_count,
    ):
        return stats
    return None


def _serialized_finding_is_visible_problem(
    finding: dict[str, Any],
    *,
    p020_display_seen: set[tuple] | None = None,
    consume_p020_display_slot: Any = None,
    page_number_display_seen: set[tuple] | None = None,
    consume_page_number_display_slot: Any = None,
    classify_visible_page_number_issue: Any = None,
    grouped_display_seen: set[tuple] | None = None,
    consume_grouped_finding_display_slot: Any = None,
    p012_display_state: Any = None,
    p026_display_state: Any = None,
    p011_display_state: Any = None,
    finding_index: int | None = None,
    claimed_page_number_keys: frozenset[tuple[str, int]] = frozenset(),
) -> bool:
    rule_id = str(finding.get("rule_id", "")).strip()
    details_raw = finding.get("details", {})
    details = (
        {str(k): str(v) for k, v in details_raw.items()}
        if isinstance(details_raw, dict)
        else {}
    )
    issue_type = details.get("issue_type", "").strip()
    category = map_finding_rule_to_category(rule_id, details)

    if rule_id == "P018" and issue_type == "missing_page_number":
        from njit_auditor.toc_list_student_preview import (
            is_toc_structural_column_label,
            sanitize_toc_list_entry_preview,
        )

        preview = sanitize_toc_list_entry_preview(details.get("affected_entry_preview", ""))
        if preview and is_toc_structural_column_label(preview):
            return False

    if (
        rule_id == "P020"
        and issue_type == "possible_title_capitalization_issue"
        and p020_display_seen is not None
        and consume_p020_display_slot is not None
    ):
        page_raw = finding.get("page")
        page = int(page_raw) if page_raw is not None else None
        return consume_p020_display_slot(details, p020_display_seen, page=page)

    if (
        grouped_display_seen is not None
        and consume_grouped_finding_display_slot is not None
        and rule_id in {"P024", "P036", "P044", "P046"}
    ):
        page_raw = finding.get("page")
        page = int(page_raw) if page_raw is not None else None
        return consume_grouped_finding_display_slot(
            rule_id,
            issue_type,
            details,
            grouped_display_seen,
            page=page,
        )

    if (
        p012_display_state is not None
        and finding_index is not None
        and rule_id == P012_RULE_ID
        and issue_type == P012_ISSUE_TYPE
    ):
        from njit_auditor.p012_student_preview import consume_p012_finding_visibility

        page_raw = finding.get("page")
        page = int(page_raw) if page_raw is not None else None
        return consume_p012_finding_visibility(
            page=page,
            finding_index=finding_index,
            state=p012_display_state,
        )

    if (
        p026_display_state is not None
        and finding_index is not None
        and rule_id == P026_RULE_ID
        and issue_type in (P026_FAMILY_ISSUE_TYPE, P026_SIZE_ISSUE_TYPE)
    ):
        from njit_auditor.p026_student_preview import (
            consume_p026_finding_visibility,
            p026_pattern_key,
        )

        page_raw = finding.get("page")
        page = int(page_raw) if page_raw is not None else None
        return consume_p026_finding_visibility(
            pattern_key=p026_pattern_key(issue_type, details),
            page=page,
            finding_index=finding_index,
            state=p026_display_state,
        )

    if (
        p011_display_state is not None
        and finding_index is not None
        and rule_id == P011_RULE_ID
        and issue_type == P011_ISSUE_TYPE
    ):
        from njit_auditor.p011_student_preview import consume_p011_finding_visibility

        page_raw = finding.get("page")
        page = int(page_raw) if page_raw is not None else None
        return consume_p011_finding_visibility(
            page=page,
            side=details.get("side", ""),
            finding_index=finding_index,
            state=p011_display_state,
        )

    if category != "page_numbering":
        return True
    if (
        page_number_display_seen is not None
        and consume_page_number_display_slot is not None
        and classify_visible_page_number_issue is not None
    ):
        page_raw = finding.get("page")
        page = int(page_raw) if page_raw is not None else None
        visible_issue_type, is_visible = classify_visible_page_number_issue(
            rule_id, issue_type, details
        )
        if not is_visible:
            return False
        if (
            rule_id == P013_RULE_ID
            and visible_issue_type is not None
            and page is not None
            and (visible_issue_type, page) in claimed_page_number_keys
        ):
            return False
        if visible_issue_type is not None:
            return consume_page_number_display_slot(
                rule_id,
                visible_issue_type,
                details,
                page_number_display_seen,
                page=page,
            )
    if rule_id == "P013":
        if issue_type == P013_DOC_ISSUE_TYPE:
            return False
        if issue_type != P013_PAGE_ISSUE_TYPE:
            return True
        try:
            candidate_count = int(details.get("candidate_count_on_page", "1") or "1")
        except ValueError:
            candidate_count = 1
        if candidate_count > 1:
            return True
        if details.get("position_type", "").strip() in {"top_center", "top_right", "other"}:
            return True
        return False
    return True


def _problem_number_map(
    serialized_findings: list[dict[str, Any]],
) -> dict[int, int]:
    from njit_auditor.high_volume_student_preview import consume_grouped_finding_display_slot
    from njit_auditor.p011_student_preview import (
        collect_p011_margin_pages_from_serialized,
        init_p011_display_state,
    )
    from njit_auditor.p012_student_preview import (
        count_p012_annotations_by_page,
        find_p012_summary_anchor_index_from_serialized,
        init_p012_display_state,
    )
    from njit_auditor.p026_student_preview import (
        collect_p026_pattern_pages_from_serialized,
        init_p026_display_state,
    )
    from njit_auditor.page_number_student_preview import (
        classify_visible_page_number_issue,
        consume_page_number_display_slot,
    )
    from njit_auditor.title_case_student_preview import consume_p020_display_slot

    mapping: dict[int, int] = {}
    next_problem_number = 1
    p020_display_seen: set[tuple] = set()
    page_number_display_seen: set[tuple] = set()
    grouped_display_seen: set[tuple] = set()
    p012_count_by_page = count_p012_annotations_by_page(serialized_findings)
    p012_display_state = init_p012_display_state(
        p012_count_by_page,
        find_p012_summary_anchor_index_from_serialized(
            serialized_findings,
            p012_count_by_page,
        ),
    )
    p026_display_state = init_p026_display_state(
        collect_p026_pattern_pages_from_serialized(serialized_findings),
    )
    p011_display_state = init_p011_display_state(
        collect_p011_margin_pages_from_serialized(serialized_findings),
    )
    claimed_page_number_keys: set[tuple[str, int]] = set()
    for finding in serialized_findings:
        rule_id = str(finding.get("rule_id", "")).strip()
        if rule_id == P013_RULE_ID:
            continue
        details_raw = finding.get("details", {})
        details = (
            {str(k): str(v) for k, v in details_raw.items()}
            if isinstance(details_raw, dict)
            else {}
        )
        if map_finding_rule_to_category(rule_id, details) != "page_numbering":
            continue
        issue_type = details.get("issue_type", "").strip()
        visible_issue_type, is_visible = classify_visible_page_number_issue(
            rule_id, issue_type, details
        )
        page_raw = finding.get("page")
        if not is_visible or visible_issue_type is None or page_raw is None:
            continue
        try:
            page = int(page_raw)
        except (TypeError, ValueError):
            continue
        claimed_page_number_keys.add((visible_issue_type, page))
    for index, finding in enumerate(serialized_findings):
        if not _serialized_finding_is_visible_problem(
            finding,
            p020_display_seen=p020_display_seen,
            consume_p020_display_slot=consume_p020_display_slot,
            page_number_display_seen=page_number_display_seen,
            consume_page_number_display_slot=consume_page_number_display_slot,
            classify_visible_page_number_issue=classify_visible_page_number_issue,
            grouped_display_seen=grouped_display_seen,
            consume_grouped_finding_display_slot=consume_grouped_finding_display_slot,
            p012_display_state=p012_display_state,
            p026_display_state=p026_display_state,
            p011_display_state=p011_display_state,
            finding_index=index,
            claimed_page_number_keys=frozenset(claimed_page_number_keys),
        ):
            continue
        mapping[index] = next_problem_number
        next_problem_number += 1
    return mapping


def format_source_location(details: dict[str, str]) -> str:
    """Return a privacy-safe file:line label for source findings."""
    file_name = _source_location_basename(details)
    line = details.get("line", "").strip()
    if file_name and line:
        return f"{file_name}:{line}"
    if file_name:
        return file_name
    return "source"


def _safe_source_location(details: dict[str, str]) -> str:
    return format_source_location(details)


_P036_SPACING_ISSUE_TYPES: frozenset[str] = frozenset(
    {
        "toc_inter_entry_spacing_too_tight",
        "lot_inter_entry_spacing_too_tight",
        "lof_inter_entry_spacing_too_tight",
    }
)
_P036_SECTION_LABELS: dict[str, str] = {
    "table_of_contents": "Table of Contents",
    "list_of_tables": "List of Tables",
    "list_of_figures": "List of Figures",
}


def _p036_entry_pair_label(details: dict[str, str]) -> str:
    raw = details.get("entry_pair_index", "").strip()
    try:
        index = int(raw)
    except ValueError:
        return "two consecutive entries"
    return f"entries {index + 1}-{index + 2}"


_P020_TITLE_CASE_SUBJECT_AND_RULE: dict[str, tuple[str, str]] = {
    "caption": (
        "table title",
        "NJIT requires table titles to use Title Case (every word capitalized "
        "except prepositions, conjunctions, and articles) and table titles "
        "must not end with a period",
    ),
}
_P020_TITLE_CASE_DEFAULT_SUBJECT_AND_RULE = (
    "Level 2 heading",
    "NJIT requires Level 2 headings (e.g. 1.1, 1.2) to use Title Case",
)


def individual_finding_comment_and_fix(
    rule_id: str,
    issue_type: str,
    *,
    severity: str,
    page: int | None,
    details: dict[str, str],
    p012_count_by_page: dict[int, int] | None = None,
    p026_pattern_stats: dict[tuple[str, str, str], Any] | None = None,
    p011_page_stats: dict[int, Any] | None = None,
) -> tuple[str, str]:
    """Return (comment, suggested_fix) text for one individual finding.

    Shared by the Markdown "## Problems" / "## Findings by Rule" sections and
    the plain-text student report so both stay in sync. Comment and fix are
    always returned as separate strings -- never merge a "Suggested fix: ..."
    clause into the comment here, since callers append their own suggested-fix
    line/field and a merged clause would show up twice (see
    test_warning_actionability_quickwins.py::test_p020_comment_and_fix_are_not_duplicated_on_card
    for the regression this guards against).

    build_grouped_findings() intentionally keys grouping on the generic,
    pair-independent build_polished_comment() text so repeated same-page
    P036/P020 occurrences still collapse into one grouped card (see
    test_p036_grouping_key_is_stable_across_entry_pairs). The per-occurrence
    callers here, however, always list every occurrence individually by its
    own problem number, so each one needs to be distinguishable on its own
    rather than reusing that pair-independent text verbatim.
    """
    from njit_auditor.polished_comments import (
        REVIEW_PREFIX,
        build_polished_comment,
        finalize_student_facing_comment_and_fix,
        resolve_suggested_fix_for_display,
    )

    comment = ""
    fix = ""

    if rule_id == P012_RULE_ID and issue_type == P012_ISSUE_TYPE:
        from njit_auditor.p012_student_preview import (
            p012_document_rolled_up_comment,
            p012_document_suggested_fix,
            p012_rolled_up_comment,
        )

        doc_stats = _p012_document_stats_for_markdown(p012_count_by_page)
        if doc_stats is not None:
            comment = p012_document_rolled_up_comment(doc_stats)
            fix = p012_document_suggested_fix()
        else:
            annotation_count = 1
            if p012_count_by_page is not None and page is not None:
                annotation_count = p012_count_by_page.get(page, 1)
            comment = p012_rolled_up_comment(page=page, annotation_count=annotation_count)
            fix = resolve_suggested_fix_for_display(
                rule_id, issue_type, existing=str(details.get("suggested_fix", ""))
            )
    elif rule_id == P026_RULE_ID and issue_type in (P026_FAMILY_ISSUE_TYPE, P026_SIZE_ISSUE_TYPE):
        from njit_auditor.p026_student_preview import (
            p026_document_rolled_up_comment,
            p026_document_suggested_fix,
        )

        doc_stats = _p026_document_stats_for_markdown(details, p026_pattern_stats)
        if doc_stats is not None:
            comment = p026_document_rolled_up_comment(doc_stats)
            fix = p026_document_suggested_fix(doc_stats)
        else:
            comment = build_polished_comment(
                rule_id=rule_id, issue_type=issue_type, severity=severity, page=page,
                details=details,
            )
            fix = resolve_suggested_fix_for_display(
                rule_id, issue_type, existing=str(details.get("suggested_fix", ""))
            )
    elif rule_id == P011_RULE_ID and issue_type == P011_ISSUE_TYPE:
        from njit_auditor.p011_student_preview import (
            p011_combined_rolled_up_comment,
            p011_combined_suggested_fix,
        )

        page_stats = p011_page_stats.get(page) if p011_page_stats is not None and page else None
        if page_stats is not None and page_stats.raw_finding_count > 1:
            comment = p011_combined_rolled_up_comment(page_stats)
            fix = p011_combined_suggested_fix(page_stats)
        else:
            comment = build_polished_comment(
                rule_id=rule_id, issue_type=issue_type, severity=severity, page=page,
                details=details,
            )
            fix = resolve_suggested_fix_for_display(
                rule_id, issue_type, existing=str(details.get("suggested_fix", ""))
            )
    elif rule_id == "P036" and issue_type in _P036_SPACING_ISSUE_TYPES:
        from njit_auditor.toc_list_student_preview import (
            p036_short_likely_problem,
            p036_short_suggested_fix,
        )

        comment = p036_short_likely_problem(
            details.get("previous_entry_preview", ""),
            details.get("next_entry_preview", ""),
        )
        fix = p036_short_suggested_fix()
    elif (
        rule_id == "P020"
        and issue_type == "possible_title_capitalization_issue"
        and details.get("flagged_word", "").strip()
        and details.get("corrected_word", "").strip()
    ):
        from njit_auditor.title_case_student_preview import (
            p020_short_likely_problem,
            p020_short_suggested_fix,
        )

        flagged_word = details.get("flagged_word", "").strip()
        corrected_word = details.get("corrected_word", "").strip()
        source = details.get("source", "")
        comment = (
            f"{REVIEW_PREFIX} "
            f"{p020_short_likely_problem(flagged_word, corrected_word, source=source)}"
        )
        fix = p020_short_suggested_fix(
            flagged_word, corrected_word, details.get("line_preview", ""), source=source
        )
    else:
        comment = build_polished_comment(
            rule_id=rule_id, issue_type=issue_type, severity=severity, page=page,
            details=details,
        )
        fix = resolve_suggested_fix_for_display(
            rule_id, issue_type, existing=str(details.get("suggested_fix", ""))
        )

    return finalize_student_facing_comment_and_fix(rule_id, issue_type, comment, fix)


def _format_p013_informational_candidates_block(
    findings: list[dict[str, Any]],
) -> list[str]:
    """Summarize routine P013 page-number candidates instead of listing each one.

    Mirrors the web UI's "Detected page-number candidates" inventory section:
    these entries are informational signals the auditor uses to verify
    page-number location and style, not confirmed formatting problems.
    """
    count = len(findings)
    pages = sorted({int(f["page"]) for f in findings if f.get("page") is not None})
    position_counts: Counter[str] = Counter()
    style_counts: Counter[str] = Counter()
    for finding in findings:
        details = finding.get("details", {})
        if not isinstance(details, dict):
            continue
        position_type = str(details.get("position_type", "")).strip()
        if position_type:
            position_counts[position_type] += 1
        number_style = str(details.get("number_style", "")).strip()
        if number_style:
            style_counts[number_style] += 1

    lines = [
        f"**{count} additional detected page-number candidate"
        f"{'s' if count != 1 else ''} (informational — not counted as problems).**",
        "",
        "These are detected page-number candidates used by the auditor and are "
        "not counted as formatting problems unless another finding reports a "
        "specific defect.",
        "",
    ]
    if pages:
        lines.append(f"- Pages: {compact_page_list(pages)}")
    if position_counts:
        position_summary = ", ".join(
            f"{key.replace('_', ' ')}: {value}"
            for key, value in sorted(position_counts.items())
        )
        lines.append(f"- Position: {position_summary}")
    if style_counts:
        style_summary = ", ".join(
            f"{key.replace('_', ' ')}: {value}"
            for key, value in sorted(style_counts.items())
        )
        lines.append(f"- Number style: {style_summary}")
    lines.append(
        "- See **P013 Page-Number Candidate Inventory** earlier in this report "
        "for a fuller breakdown."
    )
    lines.append("")
    return lines


def _finding_markdown_line(
    finding: dict[str, Any],
    *,
    audit_type: str = "pdf",
    p012_count_by_page: dict[int, int] | None = None,
    p026_pattern_stats: dict[tuple[str, str, str], Any] | None = None,
    p011_page_stats: dict[int, Any] | None = None,
) -> str:
    details = finding.get("details", {})
    if not isinstance(details, dict):
        details = {}
    safe_details = {str(k): str(v) for k, v in details.items()}
    issue_type = safe_details.get("issue_type", "")
    page_raw = finding.get("page")
    page = int(page_raw) if page_raw is not None else None

    if audit_type == "tex":
        loc_text = _safe_source_location(safe_details)
    elif (
        str(finding.get("rule_id", "")) == P011_RULE_ID
        and issue_type == P011_ISSUE_TYPE
    ):
        loc_text = _problem_location_text(
            finding,
            audit_type=audit_type,
            p011_page_stats=p011_page_stats,
        )
    elif (
        str(finding.get("rule_id", "")) == P026_RULE_ID
        and issue_type in (P026_FAMILY_ISSUE_TYPE, P026_SIZE_ISSUE_TYPE)
    ):
        loc_text = _problem_location_text(
            finding,
            audit_type=audit_type,
            p026_pattern_stats=p026_pattern_stats,
        )
    elif (
        str(finding.get("rule_id", "")) == P012_RULE_ID
        and issue_type == P012_ISSUE_TYPE
    ):
        loc_text = _problem_location_text(
            finding,
            audit_type=audit_type,
            p012_count_by_page=p012_count_by_page,
        )
    elif (
        map_finding_rule_to_category(str(finding.get("rule_id", "")), safe_details)
        == "page_numbering"
    ):
        from njit_auditor.page_number_student_preview import (
            classify_visible_page_number_issue,
            page_number_location_label,
        )

        visible_issue_type, is_visible = classify_visible_page_number_issue(
            str(finding.get("rule_id", "")),
            issue_type,
            safe_details,
        )
        loc_text = (
            page_number_location_label(
                str(finding.get("rule_id", "")),
                visible_issue_type,
                safe_details,
                page,
            )
            if is_visible
            else (f"PDF page {page}" if page is not None else "Document-wide overview")
        )
    else:
        from njit_auditor.report_view import enriched_pdf_location_label

        loc_text = enriched_pdf_location_label(
            str(finding.get("rule_id", "")),
            issue_type,
            safe_details,
            page,
        ) or (f"p.{page}" if page is not None else "p.-")

    rule_id = str(finding.get("rule_id", ""))
    polished, suggested_fix = individual_finding_comment_and_fix(
        rule_id,
        issue_type,
        severity=str(finding.get("severity", "WARNING")),
        page=page,
        details=safe_details,
        p012_count_by_page=p012_count_by_page,
        p026_pattern_stats=p026_pattern_stats,
        p011_page_stats=p011_page_stats,
    )
    problem_number = finding.get("problem_number")
    problem_prefix = ""
    if isinstance(problem_number, int) and problem_number > 0:
        problem_prefix = f"Problem {problem_number} · "
    line = f"- **{problem_prefix}{loc_text}** [{finding['severity']}] {polished}"
    if suggested_fix:
        line += f" | Suggested fix: {suggested_fix}"
    return line


def _problem_heading_text(
    finding: dict[str, Any],
    *,
    audit_type: str,
    p012_count_by_page: dict[int, int] | None = None,
    p026_pattern_stats: dict[tuple[str, str, str], Any] | None = None,
    p011_page_stats: dict[int, Any] | None = None,
) -> str:
    details = finding.get("details", {})
    if not isinstance(details, dict):
        details = {}
    safe_details = {str(k): str(v) for k, v in details.items()}
    page_raw = finding.get("page")
    page = int(page_raw) if page_raw is not None else None
    polished, _fix = individual_finding_comment_and_fix(
        str(finding.get("rule_id", "")),
        safe_details.get("issue_type", ""),
        severity=str(finding.get("severity", "WARNING")),
        page=page,
        details=safe_details,
        p012_count_by_page=p012_count_by_page,
        p026_pattern_stats=p026_pattern_stats,
        p011_page_stats=p011_page_stats,
    )
    return _truncate(polished, 96)


def _problem_location_text(
    finding: dict[str, Any],
    *,
    audit_type: str,
    p012_count_by_page: dict[int, int] | None = None,
    p026_pattern_stats: dict[tuple[str, str, str], Any] | None = None,
    p011_page_stats: dict[int, Any] | None = None,
) -> str:
    details = finding.get("details", {})
    if not isinstance(details, dict):
        details = {}
    safe_details = {str(k): str(v) for k, v in details.items()}
    page_raw = finding.get("page")
    page = int(page_raw) if page_raw is not None else None
    if audit_type == "tex":
        return _safe_source_location(safe_details)
    from njit_auditor.report_view import enriched_pdf_location_label

    rule_id = str(finding.get("rule_id", ""))
    issue_type = safe_details.get("issue_type", "")
    if rule_id == P012_RULE_ID and issue_type == P012_ISSUE_TYPE:
        from njit_auditor.p012_student_preview import (
            p012_document_location_label,
            p012_location_label,
        )

        doc_stats = _p012_document_stats_for_markdown(p012_count_by_page)
        if doc_stats is not None:
            return p012_document_location_label(doc_stats)
        annotation_count = 1
        if p012_count_by_page is not None and page is not None:
            annotation_count = p012_count_by_page.get(page, 1)
        return p012_location_label(page, annotation_count)
    if rule_id == P011_RULE_ID and issue_type == P011_ISSUE_TYPE:
        from njit_auditor.high_volume_student_preview import margin_location_label
        from njit_auditor.p011_student_preview import p011_page_location_label

        page_stats = p011_page_stats.get(page) if p011_page_stats is not None and page else None
        if page_stats is not None and page_stats.raw_finding_count > 1 and page is not None:
            return p011_page_location_label(page, page_stats.sides)
        return margin_location_label(safe_details, page)
    if rule_id == P026_RULE_ID and issue_type in (P026_FAMILY_ISSUE_TYPE, P026_SIZE_ISSUE_TYPE):
        from njit_auditor.p026_student_preview import (
            p026_document_location_label,
            p026_page_location_label,
        )

        doc_stats = _p026_document_stats_for_markdown(safe_details, p026_pattern_stats)
        if doc_stats is not None:
            return p026_document_location_label(doc_stats)
        return p026_page_location_label(
            page=page,
            issue_type=issue_type,
            observed_summary=safe_details.get("observed_summary", ""),
            expected=safe_details.get("expected", ""),
        )
    if map_finding_rule_to_category(rule_id, safe_details) == "page_numbering":
        from njit_auditor.page_number_student_preview import (
            classify_visible_page_number_issue,
            page_number_location_label,
        )

        visible_issue_type, is_visible = classify_visible_page_number_issue(
            rule_id,
            issue_type,
            safe_details,
        )
        if is_visible:
            label = page_number_location_label(
                rule_id,
                visible_issue_type,
                safe_details,
                page,
            )
            if label:
                return label
        return f"PDF page {page}" if page is not None else "Document-wide overview"
    label = enriched_pdf_location_label(rule_id, issue_type, safe_details, page)
    if label:
        return label
    return f"Page {page}" if page is not None else "Document-wide overview"


def write_markdown_report(
    findings: list[AuditFinding], metadata: dict[str, str], output_path: Path
) -> None:
    """Write student/office-friendly markdown audit report."""
    from njit_auditor.polished_comments import GLOBAL_AUTOMATED_REVIEW_NOTE

    output_path.parent.mkdir(parents=True, exist_ok=True)
    audit_type = metadata.get("audit_type", "pdf")
    prepared = _prepare_findings_for_export(findings, audit_type)
    payload = audit_findings_to_json_dict(prepared, metadata)
    meta = payload["metadata"]
    serialized_findings = payload["findings"]
    grouped_by_rule = _group_findings_by_rule(serialized_findings)

    lines: list[str] = []
    title = (
        "# NJIT Source Audit Report"
        if audit_type == "tex"
        else "# NJIT PDF Audit Report"
    )
    lines.append(title)
    lines.append("")
    if audit_type != "tex":
        lines.append(f"> {GLOBAL_AUTOMATED_REVIEW_NOTE}")
        lines.append("")
    lines.append(f"- Input file: `{meta.get('input_file_name', '-')}`")
    lines.append(f"- Input path: `{meta.get('input_file_path', '-')}`")
    lines.append(f"- Audit type: `{meta.get('audit_type', 'pdf')}`")
    if audit_type == "tex":
        lines.append(f"- Input kind: `{meta.get('input_kind', 'tex')}`")
        if meta.get("main_tex_path"):
            lines.append(f"- Main TeX file: `{meta.get('main_tex_path', '-')}`")
        if meta.get("loaded_tex_file_count"):
            lines.append(f"- Loaded TeX files: `{meta.get('loaded_tex_file_count', '-')}`")
    lines.append(f"- Generated at: `{meta.get('generated_at', '-')}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(_format_summary_table(payload))
    lines.append("")
    lines.append("### Counts by Rule")
    lines.append("")
    for rule_id, count in meta["counts_by_rule_id"].items():
        lines.append(f"- `{rule_id}`: {count}")
    lines.append("")
    lines.append("### Counts by Category")
    lines.append("")
    for category, count in meta["counts_by_category"].items():
        lines.append(f"- `{category}`: {count}")

    grouped_findings_section = _format_grouped_findings_section(
        payload.get("grouped_findings", [])
    )
    lines.extend(grouped_findings_section)

    # Grouped summary and PDF-only triage sections.
    lines.append("")
    grouped_section = _format_grouped_summary_section(payload["grouped_summary"])
    lines.extend(grouped_section)

    if audit_type != "tex":
        p011_section = _format_p011_triage_section(payload["grouped_summary"])
        lines.extend(p011_section)

        p012_section = _format_p012_triage_section(payload["grouped_summary"])
        lines.extend(p012_section)

        p013_section = _format_p013_triage_section(payload["grouped_summary"])
        lines.extend(p013_section)

        p019_section = _format_p019_triage_section(payload["grouped_summary"])
        lines.extend(p019_section)

        p026_section = _format_p026_triage_section(payload["grouped_summary"])
        lines.extend(p026_section)

        p036_section = _format_p036_triage_section(payload["grouped_summary"])
        lines.extend(p036_section)

        p038_section = _format_p038_triage_section(payload["grouped_summary"])
        lines.extend(p038_section)

        p044_section = _format_p044_triage_section(payload["grouped_summary"])
        lines.extend(p044_section)

    visible_problem_findings = [
        finding
        for finding in serialized_findings
        if isinstance(finding.get("problem_number"), int) and finding["problem_number"] > 0
    ]
    from njit_auditor.p011_student_preview import (
        collect_p011_margin_pages_from_serialized,
        init_p011_display_state,
    )
    from njit_auditor.p012_student_preview import count_p012_annotations_by_page
    from njit_auditor.p026_student_preview import (
        collect_p026_pattern_pages_from_serialized,
        init_p026_display_state,
    )

    p012_count_by_page = count_p012_annotations_by_page(serialized_findings)
    p026_pattern_stats = init_p026_display_state(
        collect_p026_pattern_pages_from_serialized(serialized_findings),
    ).pattern_stats
    p011_page_stats = init_p011_display_state(
        collect_p011_margin_pages_from_serialized(serialized_findings),
    ).page_stats
    if visible_problem_findings:
        lines.append("## Problems")
        lines.append("")
        for finding in visible_problem_findings:
            problem_number = int(finding["problem_number"])
            heading_text = _problem_heading_text(
                finding,
                audit_type=audit_type,
                p012_count_by_page=p012_count_by_page,
                p026_pattern_stats=p026_pattern_stats,
                p011_page_stats=p011_page_stats,
            )
            lines.append(
                f"### Problem {problem_number} — {heading_text}"
            )
            lines.append("")
            lines.append(f"- Rule: `{finding['rule_id']}`")
            lines.append(f"- Severity: `{finding['severity']}`")
            location_text = _problem_location_text(
                finding,
                audit_type=audit_type,
                p012_count_by_page=p012_count_by_page,
                p026_pattern_stats=p026_pattern_stats,
                p011_page_stats=p011_page_stats,
            )
            lines.append(f"- Location: `{location_text}`")
            lines.append(
                _finding_markdown_line(
                    finding,
                    audit_type=audit_type,
                    p012_count_by_page=p012_count_by_page,
                    p026_pattern_stats=p026_pattern_stats,
                    p011_page_stats=p011_page_stats,
                )
            )
            lines.append("")

    lines.append("## Findings by Rule")
    lines.append("")
    for rule_id, rule_findings in grouped_by_rule.items():
        if audit_type == "tex":
            sort_key = lambda item: (  # noqa: E731
                item.get("source_file", ""),
                int(item.get("source_line") or 0),
                item.get("rule_id", ""),
            )
        else:
            sort_key = lambda item: (  # noqa: E731
                item["page"] is None,
                item["page"] or 0,
                item["message"],
            )
        sorted_findings = sorted(rule_findings, key=sort_key)
        visible_findings = []
        informational_findings = []
        for finding in sorted_findings:
            finding_problem_number = finding.get("problem_number")
            if isinstance(finding_problem_number, int) and finding_problem_number > 0:
                visible_findings.append(finding)
            else:
                informational_findings.append(finding)

        if rule_id == "P013" and not visible_findings:
            continue

        lines.append(f"### {rule_id}")
        lines.append("")
        for finding in visible_findings:
            lines.append(_finding_markdown_line(finding, audit_type=audit_type))
        if informational_findings:
            if visible_findings:
                lines.append("")
            if rule_id == "P013":
                # Page-level candidates are routine and summarized together (the
                # web inventory shows them the same way); the document-overview
                # entry is a one-off summary note, not a per-page candidate, so
                # it still gets its own line rather than being folded into the
                # "N additional candidates" tally.
                page_level_informational = [
                    finding
                    for finding in informational_findings
                    if str((finding.get("details") or {}).get("issue_type", ""))
                    == P013_PAGE_ISSUE_TYPE
                ]
                other_informational = [
                    finding
                    for finding in informational_findings
                    if str((finding.get("details") or {}).get("issue_type", ""))
                    != P013_PAGE_ISSUE_TYPE
                ]
                for finding in other_informational:
                    lines.append(_finding_markdown_line(finding, audit_type=audit_type))
                if page_level_informational:
                    if other_informational:
                        lines.append("")
                    lines.extend(
                        _format_p013_informational_candidates_block(page_level_informational)
                    )
            else:
                for finding in informational_findings:
                    lines.append(_finding_markdown_line(finding, audit_type=audit_type))
        lines.append("")

    lines.append("## Notes")
    lines.append("")
    lines.append("- Privacy: report output avoids dissertation body text and source line quotes.")
    lines.append("- Limitation: findings are heuristic and require human review.")

    output_path.write_text(
        convert_pxxx_tokens_to_public_display("\n".join(lines) + "\n"), encoding="utf-8"
    )
