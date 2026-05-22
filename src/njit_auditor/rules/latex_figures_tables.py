"""Figure/table environment checks for LaTeX sources."""

from __future__ import annotations

import re

from njit_auditor.latex_loader import LoadedTexProject
from njit_auditor.models import AuditFinding, Severity

BEGIN_RE = re.compile(r"\\begin\{(figure|table)\}")
END_RE_TEMPLATE = r"\\end\{%s\}"
CAPTION_RE = re.compile(r"\\caption\{([^}]*)\}")
LABEL_RE = re.compile(r"\\label\{([^}]*)\}")


def run_latex_figure_table_checks(project: LoadedTexProject) -> list[AuditFinding]:
    """Check figure/table environments for caption/label completeness."""

    findings: list[AuditFinding] = []
    for source_file in project.files:
        i = 0
        while i < len(source_file.lines):
            line = source_file.lines[i]
            begin = BEGIN_RE.search(line)
            if not begin:
                i += 1
                continue

            env = begin.group(1)
            start_line = i + 1
            env_lines = [line]
            i += 1
            end_re = re.compile(END_RE_TEMPLATE % env)
            while i < len(source_file.lines):
                env_lines.append(source_file.lines[i])
                if end_re.search(source_file.lines[i]):
                    break
                i += 1
            env_text = "\n".join(env_lines)

            caption_match = CAPTION_RE.search(env_text)
            label_match = LABEL_RE.search(env_text)
            if not caption_match:
                findings.append(
                    AuditFinding(
                        rule_id="P005",
                        severity=Severity.WARNING,
                        message=f"{env.title()} environment has no \\caption{{...}}.",
                        details={
                            "file": str(source_file.path),
                            "line": str(start_line),
                            "suggested_fix": f"Add a descriptive \\caption{{...}} to this {env}.",
                        },
                    )
                )
            else:
                caption_text = caption_match.group(1).strip()
                if caption_text and caption_text[-1] not in ".!?":
                    findings.append(
                        AuditFinding(
                            rule_id="P007",
                            severity=Severity.WARNING,
                            message=f"{env.title()} caption may be missing ending punctuation.",
                            details={
                                "file": str(source_file.path),
                                "line": str(start_line),
                                "suggested_fix": "End caption text with ., !, or ?.",
                            },
                        )
                    )

            if not label_match:
                findings.append(
                    AuditFinding(
                        rule_id="P006",
                        severity=Severity.WARNING,
                        message=f"{env.title()} environment has no \\label{{...}}.",
                        details={
                            "file": str(source_file.path),
                            "line": str(start_line),
                            "suggested_fix": f"Add a unique \\label{{...}} in this {env}.",
                        },
                    )
                )
            i += 1

    if not findings:
        return [
            AuditFinding(
                rule_id="P005",
                severity=Severity.PASS,
                message="Figure/table caption and label checks passed.",
            )
        ]
    return findings
