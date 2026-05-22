"""Metadata checks for LaTeX source projects."""

from __future__ import annotations

import re

from njit_auditor.latex_loader import LoadedTexProject
from njit_auditor.models import AuditFinding, Severity

VALID_MONTHS = {"may", "august", "december"}
MONTH_RE = re.compile(
    r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\b",
    re.IGNORECASE,
)
GRAD_CONTEXT_RE = re.compile(
    r"(graduation|degree|submitted|thesis|dissertation|title)",
    re.IGNORECASE,
)


def run_latex_graduation_month_check(project: LoadedTexProject) -> list[AuditFinding]:
    """Check likely front-matter sources for NJIT graduation month constraints."""

    findings: list[AuditFinding] = []
    month_hits: list[tuple[str, int, str]] = []
    front_files = project.files[:5]
    for source_file in front_files:
        for i, line in enumerate(source_file.lines, start=1):
            if not GRAD_CONTEXT_RE.search(line):
                continue
            for match in MONTH_RE.finditer(line):
                month_hits.append((str(source_file.path), i, match.group(1).lower()))

    if not month_hits:
        return [
            AuditFinding(
                rule_id="latex_graduation_month",
                severity=Severity.WARNING,
                message="No graduation month found in likely front-matter TeX sources.",
            )
        ]

    for file_path, line_no, month in month_hits:
        if month not in VALID_MONTHS:
            findings.append(
                AuditFinding(
                    rule_id="latex_graduation_month",
                    severity=Severity.WARNING,
                    message=f"Non-NJIT graduation month '{month.title()}' found in context.",
                    details={"file": file_path, "line": str(line_no)},
                )
            )

    if findings:
        return findings

    return [
        AuditFinding(
            rule_id="latex_graduation_month",
            severity=Severity.PASS,
            message="Graduation month mentions appear valid (May/August/December).",
        )
    ]
