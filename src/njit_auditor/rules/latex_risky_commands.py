"""Detect risky manual formatting commands in LaTeX sources."""

from __future__ import annotations

import re

from njit_auditor.latex_loader import LoadedTexProject
from njit_auditor.models import AuditFinding, Severity

RISKY_COMMANDS = [
    "vspace",
    "hspace",
    "newpage",
    "clearpage",
    "pagebreak",
    "thispagestyle",
    "pagestyle",
    "pagenumbering",
    "setlength",
    "addtolength",
    "geometry",
    "textwidth",
    "oddsidemargin",
    "evensidemargin",
    "topmargin",
]
RISKY_RE = re.compile(r"\\(" + "|".join(RISKY_COMMANDS) + r")\b")


def run_latex_risky_command_checks(project: LoadedTexProject) -> list[AuditFinding]:
    """Warn about commands that can override formatting requirements."""

    findings: list[AuditFinding] = []
    for source_file in project.files:
        for i, line in enumerate(source_file.lines, start=1):
            for match in RISKY_RE.finditer(line):
                command = match.group(1)
                findings.append(
                    AuditFinding(
                        rule_id="latex_risky_command",
                        severity=Severity.WARNING,
                        message=(
                            f"Risky formatting override '\\{command}' detected; "
                            "manual formatting can break NJIT requirements."
                        ),
                        details={"file": str(source_file.path), "line": str(i), "command": command},
                    )
                )

    if not findings:
        return [
            AuditFinding(
                rule_id="latex_risky_command",
                severity=Severity.PASS,
                message="No risky manual formatting commands detected.",
            )
        ]
    return findings
