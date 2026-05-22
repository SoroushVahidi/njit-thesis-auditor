"""Helpers for category-level comparison of comments and audit findings."""

from __future__ import annotations

from collections import Counter
from typing import Any

from njit_auditor.comment_analysis import categorize_comment_text
from njit_auditor.models import AuditFinding


def map_finding_rule_to_category(rule_id: str) -> str:
    """Map finding rule ids to coarse comparison categories."""

    mapping = {
        "P011": "margin_or_overflow",
        "P012": "annotations",
        "P013": "page_numbering",
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
        counts[map_finding_rule_to_category(finding.rule_id)] += 1
    return dict(sorted(counts.items()))
