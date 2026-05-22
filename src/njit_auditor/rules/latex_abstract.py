"""Abstract-oriented checks for LaTeX source projects."""

from __future__ import annotations

import re

from njit_auditor.latex_loader import LoadedTexProject, TeXSourceFile
from njit_auditor.models import AuditFinding, Severity

FORBIDDEN_WORD_RE = re.compile(r"\b(paper|papers|article|articles)\b", re.IGNORECASE)
FIRST_PERSON_RE = re.compile(r"\b(i|me|my|mine|we|us|our|ours)\b", re.IGNORECASE)
ABSTRACT_BLOCK_RE = re.compile(
    r"\\begin\{abstract\}(.*?)\\end\{abstract\}",
    re.IGNORECASE | re.DOTALL,
)


def _iter_abstract_sources(project: LoadedTexProject) -> list[tuple[TeXSourceFile, str]]:
    sources: list[tuple[TeXSourceFile, str]] = []
    for source_file in project.files:
        blocks = [m.group(1) for m in ABSTRACT_BLOCK_RE.finditer(source_file.text)]
        if blocks:
            sources.append((source_file, "\n".join(blocks)))
            continue
        if "abstract" in source_file.path.name.lower():
            sources.append((source_file, source_file.text))
    return sources


def run_latex_abstract_checks(project: LoadedTexProject) -> list[AuditFinding]:
    """Run forbidden-term and first-person checks on abstract content."""

    findings: list[AuditFinding] = []
    abstract_sources = _iter_abstract_sources(project)
    if not abstract_sources:
        return [
            AuditFinding(
                rule_id="P008",
                severity=Severity.WARNING,
                message="No abstract block/file detected in TeX sources.",
                details={"suggested_fix": "Add a \\begin{abstract}...\\end{abstract} section."},
            )
        ]

    for source_file, text in abstract_sources:
        for match in FORBIDDEN_WORD_RE.finditer(text):
            findings.append(
                AuditFinding(
                    rule_id="Q004",
                    severity=Severity.FAIL,
                    message=(
                        f"Abstract uses forbidden term '{match.group(1)}' "
                        "(paper/article variants are not allowed)."
                    ),
                    details={
                        "file": str(source_file.path),
                        "line": str(text[: match.start()].count("\n") + 1),
                        "suggested_fix": "Replace with dissertation/study/work/research wording.",
                    },
                )
            )
        for match in FIRST_PERSON_RE.finditer(text):
            findings.append(
                AuditFinding(
                    rule_id="Q005",
                    severity=Severity.FAIL,
                    message=f"First-person pronoun '{match.group(1)}' detected in abstract.",
                    details={
                        "file": str(source_file.path),
                        "line": str(text[: match.start()].count("\n") + 1),
                        "suggested_fix": "Rewrite sentence in neutral third-person style.",
                    },
                )
            )

    if not findings:
        return [
            AuditFinding(
                rule_id="Q004",
                severity=Severity.PASS,
                message="Abstract forbidden-term and first-person checks passed.",
            )
        ]
    return findings
