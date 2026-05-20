"""Title/front-matter checks for graduation month."""

from __future__ import annotations

import re

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.pdf_loader import read_page_text

VALID_MONTHS = {"may", "august", "december"}
MONTH_RE = re.compile(
    r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\b",
    re.IGNORECASE,
)


GRAD_CONTEXT_RE = re.compile(
    r"(submitted|degree|graduation|thesis|dissertation|new jersey institute of technology)",
    re.IGNORECASE,
)


def _extract_month_hits(text: str) -> list[str]:
    """Extract all month mentions from text."""
    return [m.group(1).lower() for m in MONTH_RE.finditer(text)]


def run_title_page_month_check(pdf_path: str, max_pages_to_scan: int = 5) -> list[AuditFinding]:
    """Check early pages for graduation month validity."""
    findings: list[AuditFinding] = []
    found_months: list[tuple[int, str]] = []

    for page_index in range(max_pages_to_scan):
        text = read_page_text(pdf_path, page_index)
        if not text.strip():
            continue

        if not GRAD_CONTEXT_RE.search(text):
            continue

        for month in _extract_month_hits(text):
            found_months.append((page_index + 1, month))

    if not found_months:
        return [
            AuditFinding(
                rule_id="title_page_graduation_month",
                severity=Severity.WARNING,
                message="No graduation month found in first pages; verify title page manually.",
            )
        ]

    invalid_hits = [(page, month) for page, month in found_months if month not in VALID_MONTHS]
    if invalid_hits:
        for page, month in invalid_hits:
            findings.append(
                AuditFinding(
                    rule_id="title_page_graduation_month",
                    severity=Severity.WARNING,
                    page=page,
                    message=(
                        f"Found non-NJIT graduation month '{month.title()}' "
                        "in likely title-page context."
                    ),
                )
            )
        return findings

    findings.append(
        AuditFinding(
            rule_id="title_page_graduation_month",
            severity=Severity.PASS,
            message="Graduation month mentions appear valid (May/August/December).",
            details={"months": ", ".join(sorted({m for _, m in found_months}))},
        )
    )
    return findings
