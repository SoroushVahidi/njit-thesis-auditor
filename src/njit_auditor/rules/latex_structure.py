"""Project structure checks for LaTeX source projects."""

from __future__ import annotations

import re

from njit_auditor.latex_loader import LoadedTexProject
from njit_auditor.models import AuditFinding, Severity

STRUCTURE_RULES: list[tuple[str, re.Pattern[str], str]] = [
    ("abstract", re.compile(r"\\begin\{abstract\}", re.IGNORECASE), "abstract"),
    ("table_of_contents", re.compile(r"\\tableofcontents\b"), r"\tableofcontents"),
    ("list_of_tables", re.compile(r"\\listoftables\b"), r"\listoftables"),
    ("list_of_figures", re.compile(r"\\listoffigures\b"), r"\listoffigures"),
    ("chapter", re.compile(r"\\chapter\b"), r"\chapter"),
    (
        "bibliography",
        re.compile(
            r"\\bibliography\b|\\printbibliography\b|\\begin\{thebibliography\}",
            re.IGNORECASE,
        ),
        "bibliography command/environment",
    ),
]


def run_latex_structure_checks(project: LoadedTexProject) -> list[AuditFinding]:
    """Check for required structural elements in source text."""

    findings: list[AuditFinding] = []
    text = project.combined_text
    lower_file_names = [f.path.name.lower() for f in project.files]

    for rule_id, pattern, hint in STRUCTURE_RULES:
        present = bool(pattern.search(text))
        if rule_id == "abstract" and not present:
            present = any("abstract" in name for name in lower_file_names)
        if not present:
            findings.append(
                AuditFinding(
                    rule_id=f"latex_structure_{rule_id}",
                    severity=Severity.WARNING,
                    message=f"Required structure appears missing: {hint}.",
                )
            )

    if not findings:
        return [
            AuditFinding(
                rule_id="latex_structure",
                severity=Severity.PASS,
                message="Required structure commands/environments detected.",
            )
        ]
    return findings
