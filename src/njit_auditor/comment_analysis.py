"""Deterministic category tagging for reviewer comment text."""

from __future__ import annotations

import re

CATEGORY_PATTERNS: list[tuple[str, list[re.Pattern[str]]]] = [
    (
        "margin_or_overflow",
        [
            re.compile(r"\bmargin(s)?\b", re.IGNORECASE),
            re.compile(r"\boverflow\b", re.IGNORECASE),
            re.compile(r"\boutside\b.*\bmargin", re.IGNORECASE),
        ],
    ),
    (
        "indentation",
        [
            re.compile(r"\bindent(ation)?\b", re.IGNORECASE),
            re.compile(r"\bdelete indent\b", re.IGNORECASE),
        ],
    ),
    (
        "spacing_blank_lines",
        [
            re.compile(r"\bblank line(s)?\b", re.IGNORECASE),
            re.compile(r"\bdouble space(d)?\b", re.IGNORECASE),
            re.compile(r"\bextra space(s)?\b", re.IGNORECASE),
            re.compile(r"\bspacing\b", re.IGNORECASE),
        ],
    ),
    (
        "capitalization_case",
        [
            re.compile(r"\bsentence case\b", re.IGNORECASE),
            re.compile(r"\bcapitali[sz]ation\b", re.IGNORECASE),
            re.compile(r"\blowercase\b|\buppercase\b", re.IGNORECASE),
        ],
    ),
    (
        "punctuation",
        [
            re.compile(r"\bperiod\b", re.IGNORECASE),
            re.compile(r"\bpunctuation\b", re.IGNORECASE),
            re.compile(r"\bcomma\b|\bsemicolon\b|\bcolon\b", re.IGNORECASE),
        ],
    ),
    (
        "page_numbering",
        [
            re.compile(r"\bpage number(ing)?\b", re.IGNORECASE),
            re.compile(r"\broman numeral(s)?\b", re.IGNORECASE),
            re.compile(r"\bfolio\b", re.IGNORECASE),
        ],
    ),
    (
        "heading_title",
        [
            re.compile(r"\bheading\b", re.IGNORECASE),
            re.compile(r"\btitle\b", re.IGNORECASE),
            re.compile(r"\bchapter\b", re.IGNORECASE),
        ],
    ),
    (
        "table_format",
        [
            re.compile(r"\btable\b", re.IGNORECASE),
            re.compile(r"\btable title\b", re.IGNORECASE),
        ],
    ),
    (
        "figure_format",
        [
            re.compile(r"\bfigure\b", re.IGNORECASE),
            re.compile(r"\bcaption\b", re.IGNORECASE),
        ],
    ),
    (
        "references_citations",
        [
            re.compile(r"\breference(s)?\b", re.IGNORECASE),
            re.compile(r"\bcitation(s)?\b", re.IGNORECASE),
            re.compile(r"\bbibliograph(y|ies)\b", re.IGNORECASE),
        ],
    ),
    ("acknowledgements", [re.compile(r"\backnowledg(e)?ments?\b", re.IGNORECASE)]),
    (
        "committee_approval_page",
        [
            re.compile(r"\bcommittee\b", re.IGNORECASE),
            re.compile(r"\bapproval page\b", re.IGNORECASE),
            re.compile(r"\bsignature\b", re.IGNORECASE),
        ],
    ),
    ("biographical_sketch", [re.compile(r"\bbiographical sketch\b", re.IGNORECASE)]),
    (
        "list_of_tables_figures_toc",
        [
            re.compile(r"\blist of tables\b", re.IGNORECASE),
            re.compile(r"\blist of figures\b", re.IGNORECASE),
            re.compile(r"\btable of contents\b|\bTOC\b", re.IGNORECASE),
        ],
    ),
]


def categorize_comment_text(text: str) -> list[str]:
    """Assign one or more deterministic categories to a comment string."""

    if not text.strip():
        return ["unclear_or_other"]

    categories: list[str] = []
    for category, patterns in CATEGORY_PATTERNS:
        if any(pattern.search(text) for pattern in patterns):
            categories.append(category)
    return categories or ["unclear_or_other"]
