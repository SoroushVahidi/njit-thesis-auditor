"""Utility functions for PDF structural heading detection.

These helpers extract and normalize chapter/appendix headings and provide
contextual information for audit rules. They are shared across multiple
rules to avoid duplication and circular dependencies.
"""

from __future__ import annotations

import re

# Chapter/appendix heading patterns (ALL CAPS as required by NJIT)
CHAPTER_HEADING_RE = re.compile(r"^CHAPTER (\d+|[IVXLCDM]+)(\.|\s|\b)")
APPENDIX_HEADING_RE = re.compile(r"^APPENDIX(\s+[A-Z](\.|\s|\b)|\s*$)")
CHAPTER_STANDALONE_RE = re.compile(r"^(CHAPTER|APPENDIX)\s*$")

# TOC leader pattern (four or more dots)
TOC_LEADER_RE = re.compile(r"\.{4,}")

# Expected named front-matter headings
EXPECTED_HEADINGS = (
    "ABSTRACT",
    "APPROVAL PAGE",
    "BIOGRAPHICAL SKETCH",
    "ACKNOWLEDGEMENTS",
    "TABLE OF CONTENTS",
    "LIST OF TABLES",
    "LIST OF FIGURES",
)

# Compact versions for comparison (space-normalized)
COMPACT_EXPECTED_HEADINGS: dict[str, str] = {
    h.replace(" ", ""): h for h in EXPECTED_HEADINGS
}

# Font-weight detection hint
BOLD_FONT_HINT_RE = re.compile(r"(bold|black|heavy|semibold)", re.IGNORECASE)


def is_chapter_heading(text: str) -> bool:
    """Return True if text matches a chapter/appendix heading pattern."""
    t = text.strip()
    return bool(CHAPTER_HEADING_RE.match(t) or APPENDIX_HEADING_RE.match(t))


def is_appendix_heading(text: str) -> bool:
    """Return True if text matches an appendix heading pattern."""
    t = text.strip()
    return bool(CHAPTER_HEADING_RE.match(t) or APPENDIX_HEADING_RE.match(t))


def is_structural_heading(text: str) -> bool:
    """Return True if text looks like any structural heading (chapter/appendix)."""
    t = text.strip()
    return bool(CHAPTER_HEADING_RE.match(t) or APPENDIX_HEADING_RE.match(t))


def normalize_chapter_number(text: str) -> str:
    """Extract and normalize chapter/appendix number from heading text.

    Handles "CHAPTER 1 INTRODUCTION" -> "1",
    "APPENDIX A" -> "A", and mashed forms "CHAPTER1" -> "1".
    """
    m = re.search(
        r"(CHAPTER|APPENDIX)[\s\.]*(\d+[\d\s]*|[A-Za-z]+|[\dA-Z]+)\"?",
        text,
        re.IGNORECASE,
    )
    if m:
        num = m.group(2) or ""
        return re.sub(r"[^\dA-Za-z]", "", num).strip()
    return ""


def extract_structural_context(text: str) -> tuple[str, str]:
    """Extract structural context from a heading line.

    Returns tuple of (prefix, number) e.g., ("CHAPTER", "1") or ("", "").
    """
    t = text.strip()
    m_ch = CHAPTER_HEADING_RE.match(t)
    if m_ch:
        num = normalize_chapter_number(t)
        return ("CHAPTER", num)
    m_ap = APPENDIX_HEADING_RE.match(t)
    if m_ap:
        num = normalize_chapter_number(t)
        return ("APPENDIX", num)
    return ("", "")


def normalize_heading_text(text: str) -> str:
    """Normalize heading text for deterministic matching.

    Removes extra whitespace and non-breaking spaces.
    """
    return " ".join(text.replace("\u00a0", " ").strip().split())
