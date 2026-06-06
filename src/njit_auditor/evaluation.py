"""Helpers for category-level comparison of comments and audit findings."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from njit_auditor.comment_analysis import categorize_comment_text
from njit_auditor.models import AuditFinding


def map_finding_rule_to_category(rule_id: str, details: dict[str, str] | None = None) -> str:
    """Map finding rule ids to coarse comparison categories."""

    if rule_id == "P027":
        issue_type = (details or {}).get("issue_type", "")
        if "case" in issue_type or "capitalization" in issue_type:
            return "capitalization_case"
        return "heading_title"

    if rule_id == "P025":
        issue_type = (details or {}).get("issue_type", "")
        if issue_type == "missing_abstract_body":
            return "abstract_length"
        if "title_page" in issue_type:
            return "title_page_metadata"
        return "frontmatter_structure"

    if rule_id == "P024":
        issue_type = (details or {}).get("issue_type", "")
        if issue_type == "unexpected_terminal_punctuation":
            return "punctuation"
        return "list_of_tables_figures_toc"

    if rule_id == "P017":
        issue_type = (details or {}).get("issue_type", "")
        caption_type = (details or {}).get("caption_type", "")
        if issue_type in {"missing_terminal_punctuation", "unexpected_terminal_period"}:
            return "punctuation"
        if caption_type == "figure":
            return "figure_format"
        return "table_format"

    if rule_id == "P035":
        float_type = (details or {}).get("float_type", "")
        if float_type == "figure":
            return "figure_format"
        return "table_format"

    mapping = {
        "P011": "margin_or_overflow",
        "P012": "annotations",
        "P013": "page_numbering",
        "P019": "page_numbering",
        "P022": "page_numbering",
        "P028": "page_numbering",
        "P029": "page_numbering",
        "P037": "page_numbering",
        "P026": "font_format",
        "P014": "heading_title",
        "P038": "heading_title",
        "P015": "indentation",
        "P043": "indentation",
        "P044": "indentation",
        "P045": "indentation",
        "P047": "indentation",
        "P016": "spacing_blank_lines",
        "P023": "spacing_blank_lines",
        "P018": "list_of_tables_figures_toc",
        "P030": "list_of_tables_figures_toc",
        "P031": "list_of_tables_figures_toc",
        "P032": "list_of_tables_figures_toc",
        "P036": "list_of_tables_figures_toc",
        "P039": "list_of_tables_figures_toc",
        "P042": "list_of_tables_figures_toc",
        "P040": "list_of_tables_figures_toc",
        "P046": "list_of_tables_figures_toc",
        "P048": "list_of_tables_figures_toc",
        "P049": "list_of_tables_figures_toc",
        "P050": "list_of_tables_figures_toc",
        "P053": "list_of_tables_figures_toc",
        "P054": "list_of_tables_figures_toc",
        "P055": "list_of_tables_figures_toc",
        "P056": "list_of_tables_figures_toc",
        "P057": "list_of_tables_figures_toc",
        "P058": "list_of_tables_figures_toc",
        "P059": "list_of_tables_figures_toc",
        "P060": "list_of_tables_figures_toc",
        "P033": "title_page_metadata",
        "P034": "title_page_metadata",
        "P051": "title_page_metadata",
        "P052": "title_page_metadata",
        "P041": "title_page_metadata",
        "P020": "capitalization_case",
        "P021": "abstract_length",
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


def normalize_page_number(page: Any) -> int | None:
    """Normalize page values from comments/findings into positive int page numbers."""

    if page is None:
        return None

    if isinstance(page, int):
        return page if page > 0 else None

    if isinstance(page, float):
        if page.is_integer() and page > 0:
            return int(page)
        return None

    if isinstance(page, str):
        stripped = page.strip()
        if not stripped:
            return None
        if stripped.isdigit():
            value = int(stripped)
            return value if value > 0 else None
        return None

    return None


def build_comment_page_category_sets(
    annotations: list[dict[str, Any]],
) -> dict[int, set[str]]:
    """Build page -> category set mapping from extracted comments."""

    by_page: dict[int, set[str]] = defaultdict(set)
    for annotation in annotations:
        page = normalize_page_number(annotation.get("page_number"))
        if page is None:
            continue
        content = str(annotation.get("content", "") or "")
        for category in categorize_comment_text(content):
            by_page[page].add(category)
    return dict(sorted((page, cats) for page, cats in by_page.items()))


def build_finding_page_category_sets(findings: list[AuditFinding]) -> dict[int, set[str]]:
    """Build page -> category set mapping from audit findings."""

    by_page: dict[int, set[str]] = defaultdict(set)
    for finding in findings:
        page = normalize_page_number(finding.page)
        if page is None:
            continue
        by_page[page].add(map_finding_rule_to_category(finding.rule_id, finding.details))
    return dict(sorted((page, cats) for page, cats in by_page.items()))


def summarize_page_overlap(comment_pages: set[int], finding_pages: set[int]) -> dict[str, Any]:
    """Summarize overlap between EF-comment pages and tool-finding pages."""

    both = comment_pages & finding_pages
    comment_only = comment_pages - finding_pages
    finding_only = finding_pages - comment_pages
    return {
        "pages_with_ef_comments": len(comment_pages),
        "pages_with_tool_findings": len(finding_pages),
        "pages_with_both": len(both),
        "ef_only_pages": sorted(comment_only),
        "tool_only_pages": sorted(finding_only),
    }


def summarize_category_page_overlap(
    comment_page_categories: dict[int, set[str]],
    finding_page_categories: dict[int, set[str]],
    categories: list[str] | None = None,
) -> dict[str, dict[str, Any]]:
    """Summarize category overlap by page for comments and tool findings."""

    if categories is None:
        categories = sorted(
            {
                category
                for page_categories in [comment_page_categories, finding_page_categories]
                for category_set in page_categories.values()
                for category in category_set
            }
        )

    summary: dict[str, dict[str, Any]] = {}
    for category in categories:
        comment_pages = set()
        for page, category_set in comment_page_categories.items():
            if category in category_set:
                comment_pages.add(page)
        finding_pages = set()
        for page, category_set in finding_page_categories.items():
            if category in category_set:
                finding_pages.add(page)
        both = comment_pages & finding_pages
        summary[category] = {
            "ef_pages": sorted(comment_pages),
            "tool_pages": sorted(finding_pages),
            "both_pages": sorted(both),
            "ef_only_pages": sorted(comment_pages - finding_pages),
            "tool_only_pages": sorted(finding_pages - comment_pages),
            "ef_page_count": len(comment_pages),
            "tool_page_count": len(finding_pages),
            "both_page_count": len(both),
        }
    return summary
