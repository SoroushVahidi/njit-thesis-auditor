"""Conservative List of Tables entry terminal-period checks (P053).

Partial heuristic PDF coverage for Q065:
  - Q065: Do List of Tables entry titles use title case with no terminal period?

List of Tables pages only. TOC and LoF are excluded.
Does not duplicate P024 (LoT title-case, no-period checks), P018 (alignment),
P031 (column headers), P032 (wrap spacing), P036 (inter-entry spacing), or
P040 (LoF terminal punctuation — the symmetric opposite requirement).

P040 checks that LoF entries DO have terminal punctuation.
P053 checks that LoT entries do NOT have a terminal period.
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
    is_isolated_terminal_grid_leader_dot,
)

MIN_ENTRY_TEXT_LEN = 10

_LEADER_STRIP_RE = re.compile(r"\s*(?:\.\s*){2,}$")
_DOT_LEADER_CHARS = ".…·"
_SEPARATED_DOT_LEADER_RE = re.compile(r"\s+[.…·][.…·\s]*$")
_ATTACHED_DOT_LEADER_RE = re.compile(r"[.…·]+$")
_LOT_PREFIX_RE = re.compile(
    r"^(?:table\.?)\s+[0-9]+(?:[.\-][0-9]+)?\s*[.):]?\s*",
    re.IGNORECASE,
)
_TERMINAL_PERIOD_RE = re.compile(r"\.\s*$")


def _dot_leader_weight(text: str) -> int:
    """Return visible dot weight for a candidate dot-leader fragment."""

    return sum(3 if char == "…" else 1 for char in text if char in _DOT_LEADER_CHARS)


def _strip_trailing_dot_leaders(text: str) -> str:
    """Strip visual dot leaders while preserving isolated title punctuation.

    List entries often extract leaders as Unicode ellipsis characters, ASCII
    periods, or a mixture of both.  A separated leader run (whitespace before
    the run) starts after the semantic title, so a real title-ending period
    before that whitespace is preserved.  An attached run of multiple dot-like
    characters is treated as leader formatting, not title punctuation.
    """

    stripped = text.rstrip()
    legacy_stripped = _LEADER_STRIP_RE.sub("", stripped).strip()
    if legacy_stripped != stripped:
        return legacy_stripped

    separated = _SEPARATED_DOT_LEADER_RE.search(stripped)
    if separated is not None and _dot_leader_weight(separated.group()) >= 2:
        return stripped[: separated.start()].rstrip()

    attached = _ATTACHED_DOT_LEADER_RE.search(stripped)
    if attached is not None and _dot_leader_weight(attached.group()) >= 2:
        return stripped[: attached.start()].rstrip()

    return stripped.strip()


def _extract_lot_entry_text(entry: TocEntryLine) -> str | None:
    """Return table title text stripped of page number, leaders, and prefix."""
    text = entry.cleaned_text
    if entry.page_number_token:
        stripped = text.rstrip()
        if stripped.endswith(entry.page_number_token):
            stripped = stripped[: -len(entry.page_number_token)].rstrip()
        text = stripped
    text = _strip_trailing_dot_leaders(text)
    match = _LOT_PREFIX_RE.match(text)
    if match:
        text = text[match.end() :].strip()
    return text if len(text) >= MIN_ENTRY_TEXT_LEN else None


def _check_lot_terminal_period_page(
    context: TocPageContext,
    entries: list[TocEntryLine],
    page_entry_offset: int,
) -> list[AuditFinding]:
    findings: list[AuditFinding] = []
    for idx, entry in enumerate(entries):
        if entry.page_number_token is None:
            continue
        entry_text = _extract_lot_entry_text(entry)
        if entry_text is None:
            continue
        if not _TERMINAL_PERIOD_RE.search(entry_text):
            continue
        if is_isolated_terminal_grid_leader_dot(entry, entries):
            continue
        details = {
            "issue_type": "lot_entry_has_terminal_period",
            "page": str(context.page.page_number),
            "section_type": "list_of_tables",
            "entry_index": str(page_entry_offset + idx),
            "terminal_punctuation": ".",
            "page_number_token_present": "true",
            "bbox": format_bbox_detail(entry.line.bbox),
            "triage_tier": "medium",
            "source_q_rule_id": "Q065",
        }
        findings.append(
            AuditFinding(
                rule_id="P053",
                severity=Severity.WARNING,
                page=context.page.page_number,
                message=(
                    "List of Tables entry ends with a terminal period. "
                    "NJIT guidelines require that table titles use "
                    "title case with no terminal period."
                ),
                details=details,
            )
        )
    return findings


def check_pdf_lot_terminal_period(pdf_document: PdfDocument) -> list[AuditFinding]:
    """Emit P053 warnings for LoT entries with a terminal period."""
    findings: list[AuditFinding] = []
    entry_offset = 0
    for context in detect_toc_like_pages(pdf_document):
        if context.page_type != "list_of_tables":
            continue
        entries = extract_toc_entry_lines(context)
        if len(entries) < 2:
            continue
        page_findings = _check_lot_terminal_period_page(context, entries, entry_offset)
        findings.extend(page_findings)
        entry_offset += len(entries)
    return findings
