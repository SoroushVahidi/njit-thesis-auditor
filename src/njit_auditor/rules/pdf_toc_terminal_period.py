"""Conservative TOC entry terminal-period absence check (P054).

Partial heuristic PDF coverage for Q049/Q050/Q051:
  - Q049: TOC L1 entries (chapter headings) are all-caps with no terminal period.
  - Q050: TOC L2 entries use title case with no terminal period.
  - Q051: TOC L3 entries use sentence case with no terminal period.

Table of Contents pages only. LoT and LoF are excluded (handled by P053 and P040).
Does not duplicate P024 (TOC case/punctuation), P039 (hierarchy), P042 (appendix format),
P053 (LoT no terminal period), or P040 (LoF must have terminal punctuation).

P040 checks that LoF entries DO have terminal punctuation.
P053 checks that LoT entries do NOT have a terminal period.
P054 checks that TOC entries do NOT have a terminal period (symmetric to P053 for TOC pages).
"""

from __future__ import annotations

import re

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument, format_bbox_detail
from njit_auditor.rules.pdf_toc_alignment import (
    TocEntryLine,
    TocPageContext,
    detect_toc_like_pages,
    extract_toc_entry_lines,
)

MIN_ENTRY_TEXT_LEN = 10

_LEADER_STRIP_RE = re.compile(r"\s*(?:(?:\.\s*){2,}|[-–—_]{2,})$")
_DOT_LEADER_CHARS = ".…·"
_SEPARATED_DOT_LEADER_RE = re.compile(r"\s+[.…·][.…·\s]*$")
_ATTACHED_DOT_LEADER_RE = re.compile(r"[.…·]+$")
_TERMINAL_PERIOD_RE = re.compile(r"\.\s*$")


def _dot_leader_weight(text: str) -> int:
    """Return visible dot weight for a candidate dot-leader fragment."""

    return sum(3 if char == "…" else 1 for char in text if char in _DOT_LEADER_CHARS)


def _strip_trailing_leaders(text: str) -> str:
    """Strip visual leaders while preserving isolated title punctuation."""

    stripped = text.rstrip()
    while True:
        legacy_stripped = _LEADER_STRIP_RE.sub("", stripped).strip()
        if legacy_stripped != stripped:
            stripped = legacy_stripped
            continue

        separated = _SEPARATED_DOT_LEADER_RE.search(stripped)
        if separated is not None and _dot_leader_weight(separated.group()) >= 2:
            stripped = stripped[: separated.start()].rstrip()
            continue

        attached = _ATTACHED_DOT_LEADER_RE.search(stripped)
        if attached is not None and _dot_leader_weight(attached.group()) >= 2:
            stripped = stripped[: attached.start()].rstrip()
            continue

        break

    return stripped.strip()


def _extract_toc_entry_text(entry: TocEntryLine) -> str | None:
    """Return entry text stripped of page number, leaders, and level prefix."""
    text = entry.cleaned_text
    if entry.page_number_token:
        stripped = text.rstrip()
        if stripped.endswith(entry.page_number_token):
            stripped = stripped[: -len(entry.page_number_token)].rstrip()
        text = stripped
    text = _strip_trailing_leaders(text)
    return text if len(text) >= MIN_ENTRY_TEXT_LEN else None


def _check_toc_terminal_period_page(
    context: TocPageContext,
    entries: list[TocEntryLine],
    page_entry_offset: int,
) -> list[AuditFinding]:
    findings: list[AuditFinding] = []
    for idx, entry in enumerate(entries):
        if entry.page_number_token is None:
            continue
        entry_text = _extract_toc_entry_text(entry)
        if entry_text is None:
            continue
        if not _TERMINAL_PERIOD_RE.search(entry_text):
            continue
        details = {
            "issue_type": "toc_entry_has_terminal_period",
            "page": str(context.page.page_number),
            "section_type": "table_of_contents",
            "entry_index": str(page_entry_offset + idx),
            "terminal_punctuation": ".",
            "page_number_token_present": "true",
            "bbox": format_bbox_detail(entry.line.bbox),
            "triage_tier": "medium",
            "source_q_rule_id": "Q050",
        }
        findings.append(
            AuditFinding(
                rule_id="P054",
                severity=Severity.WARNING,
                page=context.page.page_number,
                message=(
                    "Table of Contents entry ends with a terminal period. "
                    "NJIT guidelines require that TOC entries "
                    "at all levels do not end with a terminal period."
                ),
                details=details,
            )
        )
    return findings


def check_pdf_toc_terminal_period(pdf_document: PdfDocument) -> list[AuditFinding]:
    """Emit P054 warnings for TOC entries with a terminal period."""
    findings: list[AuditFinding] = []
    entry_offset = 0
    for context in detect_toc_like_pages(pdf_document):
        if context.page_type != "table_of_contents":
            continue
        entries = extract_toc_entry_lines(context)
        if len(entries) < 2:
            continue
        page_findings = _check_toc_terminal_period_page(context, entries, entry_offset)
        findings.extend(page_findings)
        entry_offset += len(entries)
    return findings
