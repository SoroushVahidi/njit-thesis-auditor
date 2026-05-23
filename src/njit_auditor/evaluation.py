"""Helpers for category-level comparison of comments and audit findings."""

from __future__ import annotations

from collections import Counter
from typing import Any

from njit_auditor.comment_analysis import categorize_comment_text
from njit_auditor.models import AuditFinding


def map_finding_rule_to_category(rule_id: str, details: dict[str, str] | None = None) -> str:
    """Map finding rule ids to coarse comparison categories."""

    if rule_id == "P017":
        issue_type = (details or {}).get("issue_type", "")
        caption_type = (details or {}).get("caption_type", "")
        if issue_type in {"missing_terminal_punctuation", "unexpected_terminal_period"}:
            return "punctuation"
        if caption_type == "figure":
            return "figure_format"
        return "table_format"

    mapping = {
        "P011": "margin_or_overflow",
        "P012": "annotations",
        "P013": "page_numbering",
        "P014": "heading_title",
        "P015": "indentation",
        "P016": "spacing_blank_lines",
        "P018": "list_of_tables_figures_toc",
        "Q004": "abstract_language",
        "Q005": "abstract_language",
        "Q006": "title_page_metadata",
    }
    return mapping.get(rule_id, "other")


def summarize_comment_categories(annotations: list[dict[str, Any]]) -> dict[str, int]:
    """Count deterministic categories from extracted annotation comments."""

    counts: Counter[str] = Counter()
    for annotation in annotations:
        content = str(annotation.get("content", "") or "")
        for category in categorize_comment_text(content):
            counts[category] += 1
    return dict(sorted(counts.items()))


def summarize_audit_findings(findings: list[AuditFinding]) -> dict[str, int]:
    """Count category frequencies from audit findings."""

    counts: Counter[str] = Counter()
    for finding in findings:
        counts[map_finding_rule_to_category(finding.rule_id, finding.details)] += 1
    return dict(sorted(counts.items()))
