"""Structured JSON/Markdown output helpers for audit findings."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from njit_auditor.evaluation import map_finding_rule_to_category
from njit_auditor.models import AuditFinding, Severity

MAX_DETAIL_TEXT_LEN = 120


def _truncate(value: str, max_len: int = MAX_DETAIL_TEXT_LEN) -> str:
    if len(value) <= max_len:
        return value
    return f"{value[: max_len - 3]}..."


def _sanitize_details(details: dict[str, str]) -> dict[str, str]:
    sanitized: dict[str, str] = {}
    for key, value in details.items():
        sanitized[key] = _truncate(str(value))
    return sanitized


def _severity_counts(findings: list[AuditFinding]) -> dict[str, int]:
    counts = Counter(finding.severity.value for finding in findings)
    return {
        Severity.PASS.value: counts.get(Severity.PASS.value, 0),
        Severity.WARNING.value: counts.get(Severity.WARNING.value, 0),
        Severity.FAIL.value: counts.get(Severity.FAIL.value, 0),
    }


def _rule_counts(findings: list[AuditFinding]) -> dict[str, int]:
    counts = Counter(finding.rule_id for finding in findings)
    return dict(sorted(counts.items()))


def _category_counts(findings: list[AuditFinding]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for finding in findings:
        counts[map_finding_rule_to_category(finding.rule_id, finding.details)] += 1
    return dict(sorted(counts.items()))


def audit_findings_to_json_dict(
    findings: list[AuditFinding], metadata: dict[str, str]
) -> dict[str, Any]:
    """Convert findings + metadata into a structured serializable payload."""

    serialized_findings: list[dict[str, Any]] = []
    for finding in findings:
        serialized_findings.append(
            {
                "rule_id": finding.rule_id,
                "severity": finding.severity.value,
                "message": finding.message,
                "page": finding.page,
                "details": _sanitize_details(finding.details),
            }
        )

    return {
        "metadata": {
            **metadata,
            "total_findings": len(findings),
            "counts_by_severity": _severity_counts(findings),
            "counts_by_rule_id": _rule_counts(findings),
            "counts_by_category": _category_counts(findings),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "note": "Findings are heuristic signals and require human review.",
        },
        "findings": serialized_findings,
    }


def write_json_report(
    findings: list[AuditFinding], metadata: dict[str, str], output_path: Path
) -> None:
    """Write structured JSON report to disk."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = audit_findings_to_json_dict(findings, metadata)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _format_summary_table(payload: dict[str, Any]) -> str:
    meta = payload["metadata"]
    sev = meta["counts_by_severity"]
    lines = [
        "| Metric | Value |",
        "|---|---:|",
        f"| Total findings | {meta['total_findings']} |",
        f"| PASS | {sev.get('PASS', 0)} |",
        f"| WARNING | {sev.get('WARNING', 0)} |",
        f"| FAIL | {sev.get('FAIL', 0)} |",
    ]
    return "\n".join(lines)


def _group_findings_by_rule(findings: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for finding in findings:
        grouped[str(finding["rule_id"])].append(finding)
    return dict(sorted(grouped.items()))


def _finding_markdown_line(finding: dict[str, Any]) -> str:
    page = finding.get("page")
    page_text = f"p.{page}" if page is not None else "p.-"
    details = finding.get("details", {})
    details_text = ""
    if details:
        detail_parts = [f"{k}={v}" for k, v in details.items() if k != "suggested_fix"]
        if detail_parts:
            details_text = f" ({'; '.join(detail_parts)})"
    line = f"- **{page_text}** [{finding['severity']}] {finding['message']}{details_text}"
    suggested_fix = details.get("suggested_fix")
    if suggested_fix:
        line += f" | Suggested fix: {suggested_fix}"
    return line


def write_markdown_report(
    findings: list[AuditFinding], metadata: dict[str, str], output_path: Path
) -> None:
    """Write student/office-friendly markdown audit report."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = audit_findings_to_json_dict(findings, metadata)
    meta = payload["metadata"]
    serialized_findings = payload["findings"]
    grouped_by_rule = _group_findings_by_rule(serialized_findings)

    lines: list[str] = []
    lines.append("# NJIT PDF Audit Report")
    lines.append("")
    lines.append(f"- Input file: `{meta.get('input_file_name', '-')}`")
    lines.append(f"- Input path: `{meta.get('input_file_path', '-')}`")
    lines.append(f"- Audit type: `{meta.get('audit_type', 'pdf')}`")
    lines.append(f"- Generated at: `{meta.get('generated_at', '-')}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(_format_summary_table(payload))
    lines.append("")
    lines.append("### Counts by Rule")
    lines.append("")
    for rule_id, count in meta["counts_by_rule_id"].items():
        lines.append(f"- `{rule_id}`: {count}")
    lines.append("")
    lines.append("### Counts by Category")
    lines.append("")
    for category, count in meta["counts_by_category"].items():
        lines.append(f"- `{category}`: {count}")

    lines.append("")
    lines.append("## Findings by Rule")
    lines.append("")
    for rule_id, rule_findings in grouped_by_rule.items():
        lines.append(f"### {rule_id}")
        lines.append("")
        sorted_findings = sorted(
            rule_findings,
            key=lambda item: (item["page"] is None, item["page"] or 0, item["message"]),
        )
        for finding in sorted_findings:
            lines.append(_finding_markdown_line(finding))
        lines.append("")

    lines.append("## Notes")
    lines.append("")
    lines.append("- Privacy: report output avoids long dissertation text excerpts.")
    lines.append("- Limitation: findings are heuristic and require human review.")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
