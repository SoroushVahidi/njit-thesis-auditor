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
# Rules with this many or more findings appear in high_volume_rules summary.
HIGH_VOLUME_THRESHOLD = 5
# Maximum page-range segments shown in compact page lists before truncation.
_MAX_COMPACT_RANGES = 8
P013_RULE_ID = "P013"
P013_PAGE_ISSUE_TYPE = "page_number_candidate"
P013_DOC_ISSUE_TYPE = "p013_document_overview"


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


def compact_page_list(pages: list[int], max_ranges: int = _MAX_COMPACT_RANGES) -> str:
    """Convert a list of page numbers to a compact range string.

    Examples:
        [1, 2, 3, 5, 7, 8] → "1-3, 5, 7-8"
        Long lists truncated: "1-3, 5, 7-8, ... (42 pages)"
    """
    if not pages:
        return ""
    sorted_pages = sorted(set(pages))
    ranges: list[tuple[int, int]] = []
    start = end = sorted_pages[0]
    for page in sorted_pages[1:]:
        if page == end + 1:
            end = page
        else:
            ranges.append((start, end))
            start = end = page
    ranges.append((start, end))

    parts: list[str] = []
    for s, e in ranges[:max_ranges]:
        parts.append(str(s) if s == e else f"{s}-{e}")

    result = ", ".join(parts)
    if len(ranges) > max_ranges:
        result += f", ... ({len(sorted_pages)} pages total)"
    return result


def build_p013_triage_summary(findings: list[AuditFinding]) -> dict[str, Any] | None:
    """Build a P013-specific rollup for high-volume page-number candidate triage.

    Raw findings are not modified. This summary separates document overview from
    per-page candidate warnings and adds position/style pattern page ranges.
    """
    p013_findings = [f for f in findings if f.rule_id == P013_RULE_ID]
    if not p013_findings:
        return None

    page_findings = [f for f in p013_findings if f.page is not None]
    doc_findings = [f for f in p013_findings if f.page is None]

    pages = sorted({f.page for f in page_findings if f.page is not None})
    position_type_counts: Counter[str] = Counter()
    number_style_counts: Counter[str] = Counter()
    confidence_counts: Counter[str] = Counter()
    issue_type_counts: Counter[str] = Counter()
    multi_candidate_pages: list[int] = []
    by_observed: dict[str, list[int]] = defaultdict(list)

    for finding in page_findings:
        details = finding.details or {}
        issue_type_counts[details.get("issue_type", P013_PAGE_ISSUE_TYPE)] += 1
        position_type = details.get("position_type", "")
        if position_type:
            position_type_counts[position_type] += 1
        number_style = details.get("number_style", "")
        if number_style:
            number_style_counts[number_style] += 1
        confidence = details.get("confidence", "")
        if confidence:
            confidence_counts[confidence] += 1
        try:
            candidate_count = int(details.get("candidate_count_on_page", "1"))
        except ValueError:
            candidate_count = 1
        if candidate_count > 1 and finding.page is not None:
            multi_candidate_pages.append(finding.page)
        observed = details.get("observed_summary", "")
        if observed and finding.page is not None:
            by_observed[observed].append(finding.page)

    for finding in doc_findings:
        details = finding.details or {}
        issue_type_counts[details.get("issue_type", P013_DOC_ISSUE_TYPE)] += 1

    pattern_page_ranges = {
        observed: compact_page_list(sorted(set(page_list)))
        for observed, page_list in sorted(
            by_observed.items(), key=lambda item: (-len(item[1]), item[0])
        )[:8]
    }

    return {
        "raw_finding_count": len(p013_findings),
        "page_level_finding_count": len(page_findings),
        "document_overview_finding_count": len(doc_findings),
        "affected_page_count": len(pages),
        "affected_pages_compact": compact_page_list(pages),
        "issue_type_counts": dict(sorted(issue_type_counts.items())),
        "position_type_counts": dict(sorted(position_type_counts.items())),
        "number_style_counts": dict(sorted(number_style_counts.items())),
        "confidence_counts": dict(sorted(confidence_counts.items())),
        "pages_with_multiple_candidates": len(multi_candidate_pages),
        "multiple_candidate_pages_compact": compact_page_list(multi_candidate_pages),
        "pattern_page_ranges": pattern_page_ranges,
        "triage_tier": "informational",
        "triage_note": (
            "P013 reports heuristic page-number candidates for manual NJIT verification. "
            "Page-level warnings are triage signals, not confirmed formatting defects."
        ),
    }


def build_grouped_summary(findings: list[AuditFinding]) -> dict[str, Any]:
    """Build a grouped summary structure for triage use in JSON/Markdown reports.

    Returns a dict with two keys:
    - ``high_volume_rules``: list of rule summaries for rules with ≥5 findings.
    - ``by_rule_issue_type``: nested breakdown by rule_id → issue_type.

    Raw findings are not modified. This summary is additive.
    """
    # Group findings by rule_id → issue_type.
    by_rule_issue: dict[str, dict[str, list[AuditFinding]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for finding in findings:
        issue_type = (finding.details or {}).get("issue_type", "")
        by_rule_issue[finding.rule_id][issue_type].append(finding)

    # Build by_rule_issue_type (full cross-tabulation).
    by_rule_issue_type: dict[str, dict[str, dict[str, Any]]] = {}
    for rule_id in sorted(by_rule_issue):
        by_rule_issue_type[rule_id] = {}
        for issue_type, rule_findings in sorted(by_rule_issue[rule_id].items()):
            pages = sorted({f.page for f in rule_findings if f.page is not None})
            obs_counts: Counter[str] = Counter()
            conf_counts: Counter[str] = Counter()
            for f in rule_findings:
                obs = (f.details or {}).get("observed_summary", "")
                if obs:
                    obs_counts[obs] += 1
                conf = (f.details or {}).get("confidence", "")
                if conf:
                    conf_counts[conf] += 1
            entry: dict[str, Any] = {
                "count": len(rule_findings),
                "affected_page_count": len(pages),
                "affected_pages_compact": compact_page_list(pages),
            }
            if obs_counts:
                entry["observed_summary_sample"] = ", ".join(
                    v for v, _ in obs_counts.most_common(3)
                )
            if conf_counts:
                entry["confidence_counts"] = dict(conf_counts)
            by_rule_issue_type[rule_id][issue_type] = entry

    # Build high_volume_rules list (rules with ≥ HIGH_VOLUME_THRESHOLD findings).
    high_volume: list[dict[str, Any]] = []
    for rule_id in sorted(by_rule_issue):
        all_rule_findings = [
            f for issue_fs in by_rule_issue[rule_id].values() for f in issue_fs
        ]
        total = len(all_rule_findings)
        if total < HIGH_VOLUME_THRESHOLD:
            continue
        category = map_finding_rule_to_category(rule_id)
        issue_type_counts = {
            it: len(fs) for it, fs in sorted(by_rule_issue[rule_id].items())
        }
        pages = sorted({f.page for f in all_rule_findings if f.page is not None})
        obs_counts = Counter(
            (f.details or {}).get("observed_summary", "")
            for f in all_rule_findings
            if (f.details or {}).get("observed_summary")
        )
        entry = {
            "rule_id": rule_id,
            "count": total,
            "category": category,
            "issue_type_counts": issue_type_counts,
            "affected_page_count": len(pages),
            "affected_pages_compact": compact_page_list(pages),
        }
        if obs_counts:
            entry["observed_summary_sample"] = ", ".join(
                v for v, _ in obs_counts.most_common(3)
            )
        high_volume.append(entry)

    result: dict[str, Any] = {
        "high_volume_rules": high_volume,
        "by_rule_issue_type": by_rule_issue_type,
    }
    p013_triage = build_p013_triage_summary(findings)
    if p013_triage is not None:
        result["p013_triage"] = p013_triage
    return result


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
        "grouped_summary": build_grouped_summary(findings),
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


def _format_grouped_summary_section(grouped: dict[str, Any]) -> list[str]:
    """Render the grouped summary as Markdown lines."""
    high_volume = grouped.get("high_volume_rules", [])
    if not high_volume:
        return []

    lines: list[str] = []
    lines.append("## Repeated Findings Summary")
    lines.append("")
    lines.append(
        f"Rules with {HIGH_VOLUME_THRESHOLD}+ findings grouped for triage. "
        "Raw findings are listed below. All findings are heuristic warnings "
        "requiring manual review."
    )
    lines.append("")
    lines.append("| Rule | Count | Category | Pages | Top Issue Types |")
    lines.append("|------|------:|---------|------:|-----------------|")
    for entry in high_volume:
        rule_id = entry["rule_id"]
        count = entry["count"]
        category = entry["category"]
        page_count = entry["affected_page_count"]
        page_str = f"{page_count}" if page_count else "—"
        issue_parts = [
            f"{it}×{n}" for it, n in sorted(entry["issue_type_counts"].items()) if it
        ]
        if not issue_parts:
            issue_parts = [f"{n} findings" for n in entry["issue_type_counts"].values()]
        issue_str = "; ".join(issue_parts[:2])
        obs = entry.get("observed_summary_sample", "")
        if obs:
            issue_str += f" ({obs[:40]})" if len(obs) > 40 else f" ({obs})"
        lines.append(f"| `{rule_id}` | {count} | {category} | {page_str} | {issue_str} |")
    lines.append("")
    return lines


def _format_p013_triage_section(grouped: dict[str, Any]) -> list[str]:
    """Render P013-specific triage rollup for Markdown reports."""
    triage = grouped.get("p013_triage")
    if not triage:
        return []

    lines: list[str] = []
    lines.append("## P013 Page-Number Candidate Triage")
    lines.append("")
    lines.append(triage.get("triage_note", ""))
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    lines.append(f"| Raw P013 findings | {triage['raw_finding_count']} |")
    lines.append(f"| Page-level warnings | {triage['page_level_finding_count']} |")
    lines.append(f"| Document overview | {triage['document_overview_finding_count']} |")
    lines.append(f"| Affected pages | {triage['affected_page_count']} |")
    lines.append(f"| Pages with multiple candidates | {triage['pages_with_multiple_candidates']} |")
    lines.append("")

    issue_counts = triage.get("issue_type_counts", {})
    if issue_counts:
        lines.append("### Issue type counts")
        lines.append("")
        for issue_type, count in sorted(issue_counts.items()):
            label = issue_type or "(unspecified)"
            lines.append(f"- `{label}`: {count}")
        lines.append("")

    position_counts = triage.get("position_type_counts", {})
    style_counts = triage.get("number_style_counts", {})
    if position_counts or style_counts:
        lines.append("### Position and style distribution (page-level)")
        lines.append("")
        for position, count in sorted(position_counts.items()):
            lines.append(f"- position `{position}`: {count}")
        for style, count in sorted(style_counts.items()):
            lines.append(f"- style `{style}`: {count}")
        lines.append("")

    pattern_ranges = triage.get("pattern_page_ranges", {})
    if pattern_ranges:
        lines.append("### Position/style pattern page ranges")
        lines.append("")
        for observed, page_range in pattern_ranges.items():
            lines.append(f"- `{observed}`: pages {page_range}")
        lines.append("")

    multi_compact = triage.get("multiple_candidate_pages_compact", "")
    if multi_compact:
        lines.append(f"Pages with multiple candidates: {multi_compact}")
        lines.append("")

    affected_compact = triage.get("affected_pages_compact", "")
    if affected_compact:
        lines.append(f"All affected pages (compact): {affected_compact}")
        lines.append("")

    lines.append(
        "Raw per-page P013 findings are listed under **Findings by Rule → P013** below."
    )
    lines.append("")
    return lines


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

    # Grouped summary section (new).
    lines.append("")
    grouped_section = _format_grouped_summary_section(payload["grouped_summary"])
    lines.extend(grouped_section)

    p013_section = _format_p013_triage_section(payload["grouped_summary"])
    lines.extend(p013_section)

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
