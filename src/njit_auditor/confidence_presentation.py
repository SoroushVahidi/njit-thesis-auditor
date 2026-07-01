"""Confidence normalization, filtering, sorting, and grouping for audit result pages."""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import urlencode

CONFIDENCE_BUCKETS: tuple[str, ...] = ("high", "medium", "low", "needs_review")

CONFIDENCE_SORT_RANK: dict[str, int] = {
    bucket: index for index, bucket in enumerate(CONFIDENCE_BUCKETS)
}

CONFIDENCE_SUMMARY_LABELS: dict[str, str] = {
    "high": "High confidence",
    "medium": "Medium confidence",
    "low": "Low confidence",
    "needs_review": "Needs review",
}

CONFIDENCE_FILTER_LABELS: dict[str, str] = {
    "": "All warnings",
    "high": "High confidence",
    "medium": "Medium confidence",
    "low": "Low confidence",
    "needs_review": "Needs review",
}

VALID_CONFIDENCE_FILTERS: frozenset[str] = frozenset(CONFIDENCE_BUCKETS)

VALID_SORT_MODES: frozenset[str] = frozenset(
    {
        "default",
        "confidence_desc",
        "confidence_asc",
        "page",
        "rule",
    }
)

_CONFIDENCE_ALIASES: dict[str, str] = {
    "high": "high",
    "medium": "medium",
    "med": "medium",
    "low": "low",
    "needs_review": "needs_review",
    "needs review": "needs_review",
    "unknown": "needs_review",
    "review needed": "needs_review",
    "review": "needs_review",
    "unclassified": "needs_review",
}


def normalize_confidence_bucket(value: str) -> str:
    """Map raw confidence text to a canonical bucket, defaulting to needs_review."""
    normalized = value.strip().lower().replace("-", " ").replace("_", " ")
    normalized = " ".join(normalized.split())
    if normalized in _CONFIDENCE_ALIASES:
        return _CONFIDENCE_ALIASES[normalized]
    compact = normalized.replace(" ", "_")
    if compact in _CONFIDENCE_ALIASES:
        return _CONFIDENCE_ALIASES[compact]
    if not normalized:
        return "needs_review"
    return "needs_review"


def parse_confidence_filter(raw: str | None) -> str:
    bucket = normalize_confidence_bucket(str(raw or ""))
    if bucket in VALID_CONFIDENCE_FILTERS and str(raw or "").strip():
        return bucket
    return ""


def parse_sort_mode(raw: str | None) -> str:
    mode = str(raw or "").strip().lower()
    if mode in VALID_SORT_MODES:
        return mode
    return "default"


def parse_group_by_confidence(raw: str | None) -> bool:
    return str(raw or "").strip().lower() == "confidence"


def finding_confidence_bucket(finding: Mapping[str, Any]) -> str:
    level = str(finding.get("confidence_level", "") or finding.get("confidence", "")).strip()
    if level.lower() == "mixed":
        return ""
    return normalize_confidence_bucket(level)


def grouped_problem_confidence_levels(problem: Mapping[str, Any]) -> list[str]:
    levels = [
        normalize_confidence_bucket(str(level))
        for level in problem.get("confidence_levels") or []
    ]
    deduped = [level for level in CONFIDENCE_BUCKETS if level in set(levels)]
    if deduped:
        return deduped
    primary = str(problem.get("confidence_level", "")).strip().lower()
    if primary == "mixed":
        nested = [
            finding_confidence_bucket(item)
            for item in problem.get("individual_findings") or []
        ]
        deduped = [level for level in CONFIDENCE_BUCKETS if level in set(nested)]
        if deduped:
            return deduped
        return []
    bucket = finding_confidence_bucket(problem)
    return [bucket] if bucket else ["needs_review"]


def grouped_problem_matches_filter(problem: Mapping[str, Any], confidence_filter: str) -> bool:
    if not confidence_filter:
        return True
    return confidence_filter in grouped_problem_confidence_levels(problem)


def finding_matches_filter(finding: Mapping[str, Any], confidence_filter: str) -> bool:
    if not confidence_filter:
        return True
    bucket = finding_confidence_bucket(finding)
    if bucket:
        return bucket == confidence_filter
    return confidence_filter == "needs_review"


def count_confidence_summary(findings: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counts = {bucket: 0 for bucket in CONFIDENCE_BUCKETS}
    for finding in findings:
        bucket = finding_confidence_bucket(finding)
        counts[bucket if bucket else "needs_review"] += 1
    return counts


def _finding_page_sort_key(finding: Mapping[str, Any]) -> tuple[Any, ...]:
    page = finding.get("page")
    page_num = page if isinstance(page, int) else 10**9
    return (
        page_num,
        str(finding.get("rule_id", "")),
        str(finding.get("issue_type", "")),
        str(finding.get("location_label", "")),
        str(finding.get("polished_comment", "")),
    )


def _finding_rule_sort_key(finding: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        str(finding.get("rule_id", "")),
        _finding_page_sort_key(finding),
    )


def _finding_confidence_sort_key(
    finding: Mapping[str, Any], *, descending: bool
) -> tuple[Any, ...]:
    bucket = finding_confidence_bucket(finding) or "needs_review"
    rank = CONFIDENCE_SORT_RANK[bucket]
    if descending:
        return (rank, *_finding_page_sort_key(finding))
    return (-rank, *_finding_page_sort_key(finding))


def _grouped_problem_confidence_sort_key(
    problem: Mapping[str, Any], *, descending: bool
) -> tuple[Any, ...]:
    levels = grouped_problem_confidence_levels(problem)
    ranks = [
        CONFIDENCE_SORT_RANK[level] for level in levels
    ] or [CONFIDENCE_SORT_RANK["needs_review"]]
    rank = min(ranks) if descending else max(ranks)
    first_page = problem.get("page_tokens") or []
    page_num = int(first_page[0]) if first_page else 10**9
    return (
        rank if descending else -rank,
        page_num,
        str(problem.get("rule_id", "")),
        str(problem.get("issue_type", "")),
    )


def sort_findings(
    findings: Sequence[Mapping[str, Any]],
    sort_mode: str,
) -> list[dict[str, Any]]:
    items = [dict(item) for item in findings]
    if sort_mode == "default":
        return items
    if sort_mode == "confidence_desc":
        return sorted(items, key=lambda item: _finding_confidence_sort_key(item, descending=True))
    if sort_mode == "confidence_asc":
        return sorted(items, key=lambda item: _finding_confidence_sort_key(item, descending=False))
    if sort_mode == "page":
        return sorted(items, key=_finding_page_sort_key)
    if sort_mode == "rule":
        return sorted(items, key=_finding_rule_sort_key)
    return items


def sort_grouped_problems(
    grouped_problems: Sequence[Mapping[str, Any]],
    sort_mode: str,
) -> list[dict[str, Any]]:
    items = [dict(item) for item in grouped_problems]
    if sort_mode == "default":
        return items
    if sort_mode in {"confidence_desc", "confidence_asc"}:
        descending = sort_mode == "confidence_desc"
        return sorted(
            items,
            key=lambda item: _grouped_problem_confidence_sort_key(item, descending=descending),
        )
    if sort_mode == "page":
        return sorted(
            items,
            key=lambda item: (
                int(item.get("page_tokens", ["999999"])[0])
                if item.get("page_tokens")
                else 10**9,
                str(item.get("rule_id", "")),
                str(item.get("issue_type", "")),
            ),
        )
    if sort_mode == "rule":
        return sorted(
            items,
            key=lambda item: (
                str(item.get("rule_id", "")),
                int(item.get("page_tokens", ["999999"])[0])
                if item.get("page_tokens")
                else 10**9,
                str(item.get("issue_type", "")),
            ),
        )
    return items


def filter_findings(
    findings: Sequence[Mapping[str, Any]],
    confidence_filter: str,
) -> list[dict[str, Any]]:
    if not confidence_filter:
        return [dict(item) for item in findings]
    return [
        dict(item)
        for item in findings
        if finding_matches_filter(item, confidence_filter)
    ]


def filter_grouped_problems(
    grouped_problems: Sequence[Mapping[str, Any]],
    confidence_filter: str,
) -> list[dict[str, Any]]:
    if not confidence_filter:
        return [dict(item) for item in grouped_problems]
    filtered: list[dict[str, Any]] = []
    for problem in grouped_problems:
        if not grouped_problem_matches_filter(problem, confidence_filter):
            continue
        copy_problem = dict(problem)
        nested = [
            dict(item)
            for item in problem.get("individual_findings") or []
            if finding_matches_filter(item, confidence_filter)
        ]
        copy_problem["individual_findings"] = nested
        filtered.append(copy_problem)
    return filtered


def build_confidence_sections(
    *,
    findings: Sequence[Mapping[str, Any]],
    grouped_problems: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    for bucket in CONFIDENCE_BUCKETS:
        section_findings = [
            dict(item)
            for item in findings
            if finding_confidence_bucket(item) == bucket
            or (not finding_confidence_bucket(item) and bucket == "needs_review")
        ]
        section_grouped = [
            dict(item)
            for item in grouped_problems
            if bucket in grouped_problem_confidence_levels(item)
        ]
        if not section_findings and not section_grouped:
            continue
        sections.append(
            {
                "bucket": bucket,
                "label": CONFIDENCE_SUMMARY_LABELS[bucket],
                "count": len(section_findings),
                "grouped_count": len(section_grouped),
                "findings": section_findings,
                "grouped_problems": section_grouped,
            }
        )
    return sections


def apply_results_presentation(
    *,
    findings: Sequence[Mapping[str, Any]],
    grouped_problems: Sequence[Mapping[str, Any]],
    confidence_filter: str = "",
    sort_mode: str = "default",
    group_by_confidence: bool = False,
) -> dict[str, Any]:
    """Filter/sort findings and grouped problems for audit result pages."""
    summary_source = list(findings)
    confidence_summary = count_confidence_summary(summary_source)

    filtered_findings = filter_findings(findings, confidence_filter)
    filtered_grouped = filter_grouped_problems(grouped_problems, confidence_filter)

    if sort_mode != "default":
        filtered_findings = sort_findings(filtered_findings, sort_mode)
        filtered_grouped = sort_grouped_problems(filtered_grouped, sort_mode)

    confidence_sections: list[dict[str, Any]] = []
    if group_by_confidence:
        confidence_sections = build_confidence_sections(
            findings=filtered_findings,
            grouped_problems=filtered_grouped,
        )

    return {
        "findings": filtered_findings,
        "grouped_problems": filtered_grouped,
        "confidence_summary": confidence_summary,
        "confidence_sections": confidence_sections,
        "confidence_filter": confidence_filter,
        "sort_mode": sort_mode,
        "group_by_confidence": group_by_confidence,
    }


def build_results_query_url(
    base_path: str,
    *,
    confidence: str = "",
    sort: str = "default",
    group: str = "",
) -> str:
    params: dict[str, str] = {}
    if confidence:
        params["confidence"] = confidence
    if sort and sort != "default":
        params["sort"] = sort
    if group:
        params["group"] = group
    if not params:
        return base_path
    return f"{base_path}?{urlencode(params)}"


def confidence_presentation_template_context(
    base_path: str,
    presentation: Mapping[str, Any],
) -> dict[str, Any]:
    """Template helpers for confidence summary, filters, and sort links."""
    confidence_filter = str(presentation.get("confidence_filter", ""))
    sort_mode = str(presentation.get("sort_mode", "default"))
    group_by_confidence = bool(presentation.get("group_by_confidence"))

    def query_url(
        *,
        confidence: str | None = None,
        sort: str | None = None,
        group: str | None = None,
    ) -> str:
        resolved_group = ""
        if group is not None:
            resolved_group = group
        elif group_by_confidence:
            resolved_group = "confidence"
        return build_results_query_url(
            base_path,
            confidence=confidence if confidence is not None else confidence_filter,
            sort=sort if sort is not None else sort_mode,
            group=resolved_group,
        )

    filter_links = [
        {
            "bucket": "",
            "label": CONFIDENCE_FILTER_LABELS[""],
            "href": query_url(confidence="", group="" if group_by_confidence else None),
            "active": not confidence_filter,
        }
    ]
    for bucket in CONFIDENCE_BUCKETS:
        filter_links.append(
            {
                "bucket": bucket,
                "label": CONFIDENCE_FILTER_LABELS[bucket],
                "href": query_url(confidence=bucket),
                "active": confidence_filter == bucket,
            }
        )

    sort_links = [
        {
            "mode": "default",
            "label": "Document order",
            "href": query_url(sort="default"),
            "active": sort_mode == "default",
        },
        {
            "mode": "confidence_desc",
            "label": "Highest confidence first",
            "href": query_url(sort="confidence_desc"),
            "active": sort_mode == "confidence_desc",
        },
        {
            "mode": "confidence_asc",
            "label": "Lowest confidence first",
            "href": query_url(sort="confidence_asc"),
            "active": sort_mode == "confidence_asc",
        },
        {
            "mode": "page",
            "label": "Page order",
            "href": query_url(sort="page"),
            "active": sort_mode == "page",
        },
        {
            "mode": "rule",
            "label": "Rule number",
            "href": query_url(sort="rule"),
            "active": sort_mode == "rule",
        },
    ]

    return {
        "confidence_summary": dict(presentation.get("confidence_summary") or {}),
        "confidence_filter": confidence_filter,
        "sort_mode": sort_mode,
        "group_by_confidence": group_by_confidence,
        "confidence_sections": list(presentation.get("confidence_sections") or []),
        "confidence_filter_links": filter_links,
        "confidence_sort_links": sort_links,
        "confidence_group_view_href": query_url(group="confidence"),
        "confidence_default_view_href": query_url(group=""),
        "results_query_url": query_url,
    }


def apply_report_view_presentation(
    report_view: Mapping[str, Any],
    presentation: Mapping[str, Any],
) -> dict[str, Any]:
    updated = copy.deepcopy(dict(report_view))
    updated["grouped_problems"] = list(presentation.get("grouped_problems") or [])
    return updated
