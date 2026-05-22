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
                            rule_id="P003",
                            severity=Severity.WARNING,
                            message=f"Label contains spaces: '{label}'",
                            details={
                                "file": str(source_file.path),
                                "line": str(i),
                                "suggested_fix": (
                                    "Use label keys without spaces, e.g. fig:result_plot."
                                ),
                            },
                        )
                    )
            for match in REF_RE.finditer(line):
                refs.append((str(source_file.path), i, match.group(1)))

    for label, locations in labels.items():
        if len(locations) > 1:
            for file_path, line_no in locations:
                    findings.append(
                        AuditFinding(
                            rule_id="P002",
                            severity=Severity.FAIL,
                            message=f"Duplicate label detected: '{label}'",
                            details={
                                "file": file_path,
                                "line": str(line_no),
                                "suggested_fix": (
                                    "Rename one duplicate label and update related refs."
                                ),
                            },
                        )
                    )

    known_labels = set(labels)
    for file_path, line_no, ref in refs:
        if ref not in known_labels:
            findings.append(
                AuditFinding(
                    rule_id="P004",
                    severity=Severity.WARNING,
                    message=f"Reference points to undefined label: '{ref}'",
                    details={
                        "file": file_path,
                        "line": str(line_no),
                        "suggested_fix": "Define the missing label or correct the ref key.",
                    },
                )
            )

    if not findings:
        return [
            AuditFinding(
                rule_id="P002",
                severity=Severity.PASS,
                message="No duplicate/invalid labels or dangling references detected.",
            )
        ]
    return findings
