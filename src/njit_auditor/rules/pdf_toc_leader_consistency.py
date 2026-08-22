"""Focused TOC leader-style consistency check (P075, Q052).

Q052: Is each entry connected to a page number by a consistent leader style?
Every TOC entry must connect to a right-aligned page number using one
consistent leader style (dots or hyphens) throughout the Table of Contents.

Complements the broader P018 diagnostic. Silent when all entries
consistently use dots, all use hyphens, or fewer than 3 paged entries exist.
Fires for: mixed dot+hyphen leaders (toc_mixed_leader_styles) or some entries
missing a leader while others have one (toc_missing_leader_style).

Implementation note: the shared PAGE_NUMBER_TOKEN_RE uses _clean_text which
collapses whitespace, so hyphen-leader and no-leader entries have no
page_number_token. P075 falls back to entry.line.text (the uncollapsed raw
extraction) for those cases so whitespace and hyphens are visible.
"""

from __future__ import annotations

import re

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument
from njit_auditor.rules.pdf_toc_alignment import (
    TocEntryLine,
    detect_toc_like_pages,
    extract_toc_entry_lines,
)

MIN_ENTRIES_FOR_LEADER_CHECK = 3

# Detect 4+ consecutive hyphens followed by optional whitespace and a page number.
_HYPHEN_PAGED_RE = re.compile(
    r"-{4,}\s*(?:[0-9]+|[ivxlcdm]+)\s*$",
    re.IGNORECASE,
)

# Detect a page number preceded by 2+ whitespace chars (uses raw, uncollapsed text).
_SPACE_PAGED_RE = re.compile(
    r"\s{2,}(?:[0-9]+|[ivxlcdm]+)\s*$",
    re.IGNORECASE,
)


def _count_phrase(label: str, count: int) -> str:
    noun = "entry" if count == 1 else "entries"
    return f"{label}: {count} {noun}"


def _classify_entry(entry: TocEntryLine) -> str | None:
    """Return leader style or None when no page number is detectable.

    'dot'    — entry uses dot leaders (... patterns)
    'hyphen' — entry uses hyphen leaders (---- patterns)
    'none'   — entry has a page number but no leader
    None     — no page number detected; skip this entry
    """
    # Dot leaders are set by the shared extractor.
    if entry.has_leader_dots and entry.page_number_token is not None:
        return "dot"
    # Fallback: use the raw (uncollapsed) line text for hyphen and space detection.
    raw = entry.line.text
    if _HYPHEN_PAGED_RE.search(raw):
        return "hyphen"
    # Shared extractor found a page number (via dots or double-spaces in raw text).
    if entry.page_number_token is not None:
        return "none"
    if _SPACE_PAGED_RE.search(raw):
        return "none"
    return None


def check_pdf_toc_leader_consistency(pdf_document: PdfDocument) -> list[AuditFinding]:
    """Emit P075 warnings when TOC leader styles are inconsistent (Q052)."""
    paged: list[tuple[str, int]] = []  # (leader_style, page_number)

    for context in detect_toc_like_pages(pdf_document):
        if context.page_type != "table_of_contents":
            continue
        for entry in extract_toc_entry_lines(context):
            style = _classify_entry(entry)
            if style is not None:
                paged.append((style, context.page.page_number))

    if len(paged) < MIN_ENTRIES_FOR_LEADER_CHECK:
        return []

    dot_count = sum(1 for s, _ in paged if s == "dot")
    hyphen_count = sum(1 for s, _ in paged if s == "hyphen")
    none_count = sum(1 for s, _ in paged if s == "none")
    total = len(paged)
    first_page = paged[0][1]

    if dot_count > 0 and hyphen_count > 0:
        style_summary = "; ".join(
            [
                _count_phrase("dot leaders", dot_count),
                _count_phrase("hyphen leaders", hyphen_count),
            ]
        )
        return [
            AuditFinding(
                rule_id="P075",
                severity=Severity.WARNING,
                page=first_page,
                message=(
                    f"Table of Contents entries are not connected to page numbers by one "
                    f"consistent leader style: {style_summary} "
                    f"(out of {total} paged entries). "
                    "NJIT guidelines require one consistent leader style throughout the TOC."
                ),
                details={
                    "page_number": str(first_page),
                    "issue_type": "toc_mixed_leader_styles",
                    "dot_leader_count": str(dot_count),
                    "hyphen_leader_count": str(hyphen_count),
                    "total_paged_entries": str(total),
                    "confidence": "medium",
                    "triage_tier": "medium",
                    "suggested_fix": (
                        "Right-align page numbers and use one consistent leader style "
                        "(dots or hyphens)."
                    ),
                    "source_q_rule_id": "Q052",
                },
            )
        ]

    if (dot_count > 0 or hyphen_count > 0) and none_count > 0:
        dominant = "dot" if dot_count >= hyphen_count else "hyphen"
        dominant_count = dot_count if dominant == "dot" else hyphen_count
        style_summary = "; ".join(
            [
                _count_phrase(f"{dominant} leaders", dominant_count),
                _count_phrase("no leader", none_count),
            ]
        )
        return [
            AuditFinding(
                rule_id="P075",
                severity=Severity.WARNING,
                page=first_page,
                message=(
                    f"Table of Contents entries are not all connected to page numbers by a "
                    f"consistent leader style: {style_summary} "
                    f"(out of {total} paged entries). "
                    "NJIT guidelines require every TOC entry to connect to its page "
                    "number with a consistent leader style."
                ),
                details={
                    "page_number": str(first_page),
                    "issue_type": "toc_missing_leader_style",
                    "dominant_style": dominant,
                    "entries_with_leader": str(dominant_count),
                    "entries_without_leader": str(none_count),
                    "total_paged_entries": str(total),
                    "confidence": "medium",
                    "triage_tier": "medium",
                    "suggested_fix": (
                        "Right-align page numbers and use one consistent leader style "
                        "(dots or hyphens)."
                    ),
                    "source_q_rule_id": "Q052",
                },
            )
        ]

    return []
