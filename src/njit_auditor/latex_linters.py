"""Optional local LaTeX linter integrations."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from njit_auditor.models import AuditFinding, Severity

CHKTeX_LINE_RE = re.compile(
    r"^(?P<file>.*?):(?P<line>\d+):(?P<col>\d+):(?P<kind>Warning|Error)\s+\d+:(?P<msg>.*)$"
)
LACHECK_LINE_RE = re.compile(r"^(?P<file>.*?),\s*line\s*(?P<line>\d+):\s*(?P<msg>.*)$")


def is_tool_available(tool_name: str) -> bool:
    """Return whether a local executable is available on PATH."""

    return shutil.which(tool_name) is not None


def _skipped_linter_finding(tool_name: str, rule_id: str) -> AuditFinding:
    return AuditFinding(
        rule_id=rule_id,
        severity=Severity.WARNING,
        message=f"Optional linter '{tool_name}' not found; skipped.",
        details={
            "tool": tool_name,
            "suggested_fix": (
                f"Install {tool_name} locally and rerun with --linters for additional checks."
            ),
        },
    )


def _parse_chktex_line(line: str) -> AuditFinding | None:
    match = CHKTeX_LINE_RE.match(line.strip())
    if not match:
        return None
    return AuditFinding(
        rule_id="P009",
        severity=Severity.WARNING,
        message=match.group("msg").strip(),
        details={
            "tool": "chktex",
            "file": match.group("file"),
            "line": match.group("line"),
            "suggested_fix": (
                "Review the LaTeX linter warning and adjust the source if appropriate."
            ),
        },
    )


def _parse_lacheck_line(line: str) -> AuditFinding | None:
    match = LACHECK_LINE_RE.match(line.strip())
    if not match:
        return None
    return AuditFinding(
        rule_id="P010",
        severity=Severity.WARNING,
        message=match.group("msg").strip(),
        details={
            "tool": "lacheck",
            "file": match.group("file"),
            "line": match.group("line"),
            "suggested_fix": (
                "Review the LaTeX linter warning and adjust the source if appropriate."
            ),
        },
    )


def run_chktex(main_tex_path: Path) -> list[AuditFinding]:
    """Run chktex if available and parse warning output."""

    if not is_tool_available("chktex"):
        return [_skipped_linter_finding("chktex", "P009")]

    try:
        result = subprocess.run(
            ["chktex", "-q", "-f%f:%l:%c:%k %n:%m\n", str(main_tex_path)],
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception as exc:
        return [
            AuditFinding(
                rule_id="P009",
                severity=Severity.WARNING,
                message=f"Optional linter 'chktex' failed to run: {exc}",
                details={
                    "tool": "chktex",
                    "suggested_fix": "Check local chktex installation and command availability.",
                },
            )
        ]

    findings: list[AuditFinding] = []
    for line in (result.stdout or "").splitlines():
        finding = _parse_chktex_line(line)
        if finding:
            findings.append(finding)

    if findings:
        return findings

    if result.returncode not in {0, 1, 2}:
        return [
            AuditFinding(
                rule_id="P009",
                severity=Severity.WARNING,
                message=f"chktex exited with code {result.returncode} and no parseable warnings.",
                details={
                    "tool": "chktex",
                    "suggested_fix": "Inspect local chktex output for details.",
                },
            )
        ]
    return []


def run_lacheck(main_tex_path: Path) -> list[AuditFinding]:
    """Run lacheck if available and parse warning output."""

    if not is_tool_available("lacheck"):
        return [_skipped_linter_finding("lacheck", "P010")]

    try:
        result = subprocess.run(
            ["lacheck", str(main_tex_path)],
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception as exc:
        return [
            AuditFinding(
                rule_id="P010",
                severity=Severity.WARNING,
                message=f"Optional linter 'lacheck' failed to run: {exc}",
                details={
                    "tool": "lacheck",
                    "suggested_fix": "Check local lacheck installation and command availability.",
                },
            )
        ]

    findings: list[AuditFinding] = []
    combined = "\n".join([result.stdout or "", result.stderr or ""])
    for line in combined.splitlines():
        finding = _parse_lacheck_line(line)
        if finding:
            findings.append(finding)

    if findings:
        return findings

    if result.returncode not in {0, 1}:
        return [
            AuditFinding(
                rule_id="P010",
                severity=Severity.WARNING,
                message=f"lacheck exited with code {result.returncode} and no parseable warnings.",
                details={
                    "tool": "lacheck",
                    "suggested_fix": "Inspect local lacheck output for details.",
                },
            )
        ]
    return []


def run_optional_latex_linters(main_tex_path: Path) -> list[AuditFinding]:
    """Run optional local linters and aggregate findings."""

    findings: list[AuditFinding] = []
    findings.extend(run_chktex(main_tex_path))
    findings.extend(run_lacheck(main_tex_path))
    return findings
