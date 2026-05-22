"""Label/reference consistency checks for LaTeX sources."""

from __future__ import annotations

import re
from collections import defaultdict

from njit_auditor.latex_loader import LoadedTexProject
from njit_auditor.models import AuditFinding, Severity

LABEL_RE = re.compile(r"\\label\{([^}]+)\}")
REF_RE = re.compile(r"\\(?:ref|eqref)\{([^}]+)\}")


def run_latex_label_checks(project: LoadedTexProject) -> list[AuditFinding]:
    """Detect duplicate/invalid labels and dangling refs."""

    findings: list[AuditFinding] = []
    labels: dict[str, list[tuple[str, int]]] = defaultdict(list)
    refs: list[tuple[str, int, str]] = []

    for source_file in project.files:
        for i, line in enumerate(source_file.lines, start=1):
            for match in LABEL_RE.finditer(line):
                label = match.group(1)
                labels[label].append((str(source_file.path), i))
                if " " in label:
                    findings.append(
                        AuditFinding(
                            rule_id="latex_label_space",
                            severity=Severity.WARNING,
                            message=f"Label contains spaces: '{label}'",
                            details={"file": str(source_file.path), "line": str(i)},
                        )
                    )
            for match in REF_RE.finditer(line):
                refs.append((str(source_file.path), i, match.group(1)))

    for label, locations in labels.items():
        if len(locations) > 1:
            for file_path, line_no in locations:
                findings.append(
                    AuditFinding(
                        rule_id="latex_duplicate_label",
                        severity=Severity.FAIL,
                        message=f"Duplicate label detected: '{label}'",
                        details={"file": file_path, "line": str(line_no)},
                    )
                )

    known_labels = set(labels)
    for file_path, line_no, ref in refs:
        if ref not in known_labels:
            findings.append(
                AuditFinding(
                    rule_id="latex_missing_label_reference",
                    severity=Severity.WARNING,
                    message=f"Reference points to undefined label: '{ref}'",
                    details={"file": file_path, "line": str(line_no)},
                )
            )

    if not findings:
        return [
            AuditFinding(
                rule_id="latex_labels",
                severity=Severity.PASS,
                message="No duplicate/invalid labels or dangling references detected.",
            )
        ]
    return findings
