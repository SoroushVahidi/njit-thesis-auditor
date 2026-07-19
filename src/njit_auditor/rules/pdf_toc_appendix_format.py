"""Conservative TOC appendix entry format checks (P042).

Partial heuristic PDF coverage for Q058 and Q059:
  - Q058: If only one appendix is listed, does it begin with APPENDIX plus title?
  - Q059: If multiple appendices are listed, are they identified by letters?

TABLE OF CONTENTS pages only. LoT and LoF are excluded.
Does not duplicate P024 (capitalization), P018 (alignment), P032 (wrap spacing),
P036 (inter-entry spacing), or P039 (indentation hierarchy).
"""

from __future__ import annotations

import re

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_models import PdfDocument
from njit_auditor.rules.pdf_toc_alignment import (
    TocEntryLine,
    TocPageContext,
    detect_toc_like_pages,
    extract_toc_entry_lines,
)

_APPENDIX_RE = re.compile(r"^appendix\b", re.IGNORECASE)
_APPENDIX_WITH_LETTER_RE = re.compile(r"^appendix\s+[A-Z]\b", re.IGNORECASE)
_APPENDIX_STRIP_PREFIX_RE = re.compile(r"^appendix\s*[:\-]?\s*", re.IGNORECASE)


def _is_appendix_entry(entry: TocEntryLine) -> bool:
    return bool(_APPENDIX_RE.match(entry.cleaned_text))


def _has_title_after_appendix(entry: TocEntryLine) -> bool:
    """Return True if there is non-empty title text after the APPENDIX prefix."""
    remainder = _APPENDIX_STRIP_PREFIX_RE.sub("", entry.cleaned_text).strip()
    return bool(remainder and not remainder.startswith(entry.page_number_token or ""))


def _check_toc_appendix_format_page(
    context: TocPageContext,
    entries: list[TocEntryLine],
) -> list[AuditFinding]:
    findings: list[AuditFinding] = []

    appendix_entries = [e for e in entries if _is_appendix_entry(e)]
    if not appendix_entries:
        return findings

    appendix_count = len(appendix_entries)

    if appendix_count == 1:
        entry = appendix_entries[0]
        if not _has_title_after_appendix(entry):
            findings.append(
                AuditFinding(
                    rule_id="P042",
                    severity=Severity.WARNING,
                    page=context.page.page_number,
                    message=(
                        "Single TOC appendix entry appears to lack a title after "
                        "APPENDIX, as required by NJIT guidelines."
                    ),
                    details={
                        "page_number": str(context.page.page_number),
                        "issue_type": "single_appendix_missing_title",
                        "appendix_entry_count": "1",
                        "entry_index": "0",
                        "expected_pattern": "APPENDIX <title>",
                        "triage_tier": "medium",
                        "source_q_rule_id": "Q058",
                    },
                )
            )
    else:
        for idx, entry in enumerate(appendix_entries):
            if not _APPENDIX_WITH_LETTER_RE.match(entry.cleaned_text):
                findings.append(
                    AuditFinding(
                        rule_id="P042",
                        severity=Severity.WARNING,
                        page=context.page.page_number,
                        message=(
                            "TOC appendix entry does not use a letter identifier "
                            "(e.g. APPENDIX A), which is required when multiple "
                            "appendices are listed."
                        ),
                        details={
                            "page_number": str(context.page.page_number),
                            "issue_type": "multiple_appendix_missing_letter",
                            "appendix_entry_count": str(appendix_count),
                            "entry_index": str(idx),
                            "expected_pattern": "APPENDIX <A-Z>",
                            "triage_tier": "medium",
                            "source_q_rule_id": "Q059",
                        },
                    )
                )

    return findings


def check_pdf_toc_appendix_format(pdf_document: PdfDocument) -> list[AuditFinding]:
    """Emit P042 warnings for TOC appendix entries with incorrect format."""
    findings: list[AuditFinding] = []
    for context in detect_toc_like_pages(pdf_document):
        if context.page_type != "table_of_contents":
            continue
        entries = extract_toc_entry_lines(context)
        if not entries:
            continue
        findings.extend(_check_toc_appendix_format_page(context, entries))
    return findings
