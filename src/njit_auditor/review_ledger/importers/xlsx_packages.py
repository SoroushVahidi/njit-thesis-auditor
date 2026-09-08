"""Generic importer for Ester review-package ``.xlsx`` files.

Reads the standard 4-column shape produced by
``scripts/ester_batch/build_rule_package.py``
(``DOCUMENT | possible-violation text | Correct? (Y/N) | Notes``). A row
whose ``Correct?`` column is blank carries no verdict and is reported as
such, never fabricated into an adjudication -- most packages currently in
this repository are entirely blank (sent for review, not yet returned;
verified directly, not assumed -- see the migration report this importer
produces for exact counts).

This importer is intentionally read-only with respect to interpretation:
it does not decide what a filled-in "Y"/"N" *means* beyond the literal
mapping documented on ``VERDICT_Y`` / ``VERDICT_N`` below; rule-specific
nuance (e.g. Ester's free-text policy notes) still belongs in
``known_cases.py`` or the authority-matrix importer, transcribed by a
human, not inferred here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import openpyxl

from njit_auditor.review_ledger.importers.evidence_text import parse_evidence_block

VERDICT_Y = "TRUE_VIOLATION"
VERDICT_N = "FALSE_POSITIVE"


@dataclass
class XlsxPackageRow:
    ester_id: str
    document: str
    no_finding: bool
    physical_page: int | None
    location: str | None
    message: str | None
    confidence: str | None
    verdict_letter: str | None  # raw "Y"/"N"/other, or None if blank
    notes: str | None


@dataclass
class XlsxImportSummary:
    packages_scanned: int = 0
    rows_read: int = 0
    rows_with_verdict: int = 0
    rows_blank: int = 0
    rows_unparseable: int = 0
    verdict_rows: list[XlsxPackageRow] = field(default_factory=list)


def read_xlsx_package(path: Path) -> list[XlsxPackageRow]:
    """Read one ``Rxxx_Ester_Auditor_Feedback.xlsx`` into typed rows.

    Does not raise on an unexpected header shape -- returns an empty list
    instead, since a package this importer cannot confidently parse must
    never be silently skipped as "no verdicts" (that would be
    indistinguishable from a genuinely blank package in the summary); the
    caller should treat an empty return specially if that distinction
    matters.
    """
    ester_id = path.name.split("_", 1)[0]
    workbook = openpyxl.load_workbook(path, read_only=True)
    try:
        worksheet = workbook.active
        rows: list[XlsxPackageRow] = []
        for row in worksheet.iter_rows(min_row=2, values_only=True):
            if row[0] is None:
                continue
            document = str(row[0]).strip()
            evidence_text = str(row[1] or "")
            block = parse_evidence_block(evidence_text)
            verdict_raw = row[2]
            notes_raw = row[3] if len(row) > 3 else None
            verdict_letter = (
                str(verdict_raw).strip().upper() if verdict_raw not in (None, "") else None
            )
            rows.append(
                XlsxPackageRow(
                    ester_id=ester_id,
                    document=document,
                    no_finding=block.no_finding,
                    physical_page=block.physical_page,
                    location=block.location,
                    message=block.message,
                    confidence=block.confidence,
                    verdict_letter=verdict_letter,
                    notes=str(notes_raw).strip() if notes_raw not in (None, "") else None,
                )
            )
        return rows
    finally:
        workbook.close()


def scan_xlsx_packages(packages_dir: Path) -> XlsxImportSummary:
    """Scan every ``*_Ester_Auditor_Feedback.xlsx`` under ``packages_dir``.

    Never writes to the ledger itself -- returns a summary the caller
    (``run_migration.py``) decides what to do with. Kept separate from
    ledger writes so this can run safely as a pure read-only inventory
    step (Phase 2's "produce a source inventory" is this function's
    result).
    """
    summary = XlsxImportSummary()
    for path in sorted(packages_dir.glob("*_Ester_Auditor_Feedback.xlsx")):
        summary.packages_scanned += 1
        rows = read_xlsx_package(path)
        for row in rows:
            summary.rows_read += 1
            if row.no_finding:
                continue
            if row.verdict_letter in ("Y", "N"):
                summary.rows_with_verdict += 1
                summary.verdict_rows.append(row)
            elif row.verdict_letter is None:
                summary.rows_blank += 1
            else:
                summary.rows_unparseable += 1
    return summary
