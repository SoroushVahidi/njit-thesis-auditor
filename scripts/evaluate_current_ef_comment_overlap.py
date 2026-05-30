"""Summarize overlap between current audit findings and extractable EF comments."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from njit_auditor.evaluation import (
    build_comment_page_category_sets,
    build_finding_page_category_sets,
    map_finding_rule_to_category,
    summarize_category_page_overlap,
    summarize_page_overlap,
)
from njit_auditor.models import AuditFinding, Severity

DEFAULT_CATEGORIES = [
    "indentation",
    "spacing_blank_lines",
    "capitalization_case",
    "heading_title",
    "table_format",
    "figure_format",
    "page_numbering",
    "margin_or_overflow",
    "references_citations",
    "list_of_tables_figures_toc",
    "font_format",
    "abstract_length",
    "committee_approval_page",
    "unclear_or_other",
]


@dataclass(frozen=True)
class ComparisonInput:
    label: str
    audit_json: Path
    comments_json: Path


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_findings(audit_path: Path) -> tuple[list[AuditFinding], dict[str, Any]]:
    payload = _load_json(audit_path)
    findings_raw = payload.get("findings", [])
    findings: list[AuditFinding] = []
    for item in findings_raw:
        findings.append(
            AuditFinding(
                rule_id=str(item.get("rule_id", "")),
                severity=Severity(str(item.get("severity", "WARNING"))),
                message=str(item.get("message", "")),
                page=item.get("page"),
                details=dict(item.get("details", {}) or {}),
            )
        )
    return findings, payload.get("metadata", {})


def _load_annotations(comment_path: Path) -> list[dict[str, Any]]:
    payload = _load_json(comment_path)
    if isinstance(payload, list):
        return payload
    return list(payload.get("annotations", []))


def _count_finding_categories(findings: list[AuditFinding]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for finding in findings:
        category = map_finding_rule_to_category(finding.rule_id, finding.details)
        counts[category] = counts.get(category, 0) + 1
    return dict(sorted(counts.items()))


def _count_comment_categories(annotations: list[dict[str, Any]]) -> dict[str, int]:
    from njit_auditor.evaluation import summarize_comment_categories

    return summarize_comment_categories(annotations)


def summarize_file(item: ComparisonInput) -> dict[str, Any]:
    findings, metadata = _load_findings(item.audit_json)
    annotations = _load_annotations(item.comments_json)

    comment_page_categories = build_comment_page_category_sets(annotations)
    finding_page_categories = build_finding_page_category_sets(findings)

    page_overlap = summarize_page_overlap(
        set(comment_page_categories.keys()),
        set(finding_page_categories.keys()),
    )
    category_overlap = summarize_category_page_overlap(
        comment_page_categories,
        finding_page_categories,
        categories=DEFAULT_CATEGORIES,
    )

    return {
        "label": item.label,
        "source_pdf": metadata.get("input_file_name", ""),
        "ef_comment_count": len(annotations),
        "tool_finding_count": len(findings),
        "ef_comment_category_counts": _count_comment_categories(annotations),
        "tool_finding_category_counts": _count_finding_categories(findings),
        "page_overlap": page_overlap,
        "category_overlap_by_page": category_overlap,
    }


def _format_counts_table(title: str, counts: dict[str, int]) -> list[str]:
    lines = [f"### {title}", "", "| Category | Count |", "|---|---:|"]
    for key, value in sorted(counts.items()):
        lines.append(f"| `{key}` | {value} |")
    lines.append("")
    return lines


def _format_page_overlap_table(summary: dict[str, Any]) -> list[str]:
    overlap = summary["page_overlap"]
    lines = [
        "| Metric | Value |",
        "|---|---:|",
        f"| EF comments total | {summary['ef_comment_count']} |",
        f"| Tool findings total | {summary['tool_finding_count']} |",
        f"| Pages with EF comments | {overlap['pages_with_ef_comments']} |",
        f"| Pages with tool findings | {overlap['pages_with_tool_findings']} |",
        f"| Pages with both | {overlap['pages_with_both']} |",
        f"| EF-only pages | {len(overlap['ef_only_pages'])} |",
        f"| Tool-only pages | {len(overlap['tool_only_pages'])} |",
    ]
    return lines


def _format_category_overlap_table(summary: dict[str, Any]) -> list[str]:
    lines = [
        "| Category | EF count | Tool count | EF pages | Tool pages | Both pages |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    ef_counts = summary["ef_comment_category_counts"]
    tool_counts = summary["tool_finding_category_counts"]
    category_overlap = summary["category_overlap_by_page"]
    categories = sorted(set(DEFAULT_CATEGORIES) | set(ef_counts) | set(tool_counts))
    for category in categories:
        overlap = category_overlap.get(category, {})
        lines.append(
            "| `{}` | {} | {} | {} | {} | {} |".format(
                category,
                ef_counts.get(category, 0),
                tool_counts.get(category, 0),
                overlap.get("ef_page_count", 0),
                overlap.get("tool_page_count", 0),
                overlap.get("both_page_count", 0),
            )
        )
    return lines


def write_markdown(payload: dict[str, Any], output_path: Path) -> None:
    lines: list[str] = []
    lines.append("# Current EF Comment-vs-Tool Overlap Summary")
    lines.append("")
    lines.append(
        "High-level page/category overlap between current P001-P029 tool findings "
        "and extractable EF comments."
    )
    lines.append("")
    for file_summary in payload["files"]:
        lines.append(f"## {file_summary['label']}")
        lines.append("")
        lines.append(f"- Source PDF: `{file_summary['source_pdf']}`")
        lines.append("")
        lines.extend(_format_page_overlap_table(file_summary))
        lines.append("")
        lines.extend(_format_category_overlap_table(file_summary))
        lines.append("")
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    out_dir = Path("data/evaluation/generated/current_ef_comment_comparison")
    inputs = [
        ComparisonInput(
            label="Cibaku Elson 1st review",
            audit_json=out_dir / "cibaku_elson_first_review_audit.json",
            comments_json=out_dir / "cibaku_elson_first_review_comments.json",
        ),
        ComparisonInput(
            label="Yin Haotian 2nd review",
            audit_json=out_dir / "yin_haotian_second_review_audit.json",
            comments_json=out_dir / "yin_haotian_second_review_comments.json",
        ),
    ]

    summary = {
        "files": [summarize_file(item) for item in inputs],
        "categories": DEFAULT_CATEGORIES,
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    summary_json = out_dir / "current_ef_comment_overlap_summary.json"
    summary_md = out_dir / "current_ef_comment_overlap_summary.md"
    summary_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_markdown(summary, summary_md)
    print(str(summary_json))
    print(str(summary_md))


if __name__ == "__main__":
    main()
