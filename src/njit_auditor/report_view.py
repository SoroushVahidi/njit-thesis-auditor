"""GUI-ready report view DTOs built from existing audit JSON payloads."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from typing import Any

from njit_auditor.evaluation import map_finding_rule_to_category
from njit_auditor.pdf_highlight import is_drawable_bbox
from njit_auditor.polished_comments import build_polished_comment, sanitize_suggested_fix_for_web
from njit_auditor.report_outputs import _source_location_basename, format_source_location

_TRIAGE_KEYS: tuple[tuple[str, str, str], ...] = (
    ("p011_margin_triage", "P011", "Margin / overflow summary"),
    ("p013_triage", "P013", "Page-number candidates summary"),
    ("p026_font_triage", "P026", "Body font summary"),
)


@dataclass(frozen=True)
class SummaryCard:
    label: str
    value: str


@dataclass(frozen=True)
class RuleSummaryView:
    rule_id: str
    count: int
    category: str


@dataclass(frozen=True)
class FindingView:
    rule_id: str
    category: str
    page: int | None
    severity: str
    issue_type: str
    polished_comment: str
    suggested_fix: str = ""
    triage_tier: str = ""
    confidence: str = ""
    source_file: str = ""
    source_line: str = ""
    location_label: str = ""
    bbox: tuple[float, float, float, float] | None = None


@dataclass(frozen=True)
class TriagePanelView:
    rule_id: str
    title: str
    triage_note: str
    triage_tier: str
    raw_finding_count: int
    affected_pages_compact: str
    highlights: list[tuple[str, str]] = field(default_factory=list)


@dataclass(frozen=True)
class GroupedProblemView:
    rule_id: str
    category: str
    severity: str
    issue_type: str
    polished_comment: str
    suggested_fix: str
    occurrence_count: int
    affected_label: str
    affected_compact: str
    triage_tier: str = ""
    confidence: str = ""
    is_grouped: bool = False
    page_tokens: list[str] = field(default_factory=list)
    location_tokens: list[str] = field(default_factory=list)
    individual_findings: list[FindingView] = field(default_factory=list)


@dataclass(frozen=True)
class ReportView:
    total_findings: int
    counts_by_severity: dict[str, int]
    counts_by_category: dict[str, int]
    counts_by_rule: dict[str, int]
    pages: list[int]
    summary_cards: list[SummaryCard]
    rule_summaries: list[RuleSummaryView]
    triage_panels: list[TriagePanelView]
    grouped_problems: list[GroupedProblemView]
    findings: list[FindingView]


def _build_triage_highlights(rule_id: str, triage: Mapping[str, Any]) -> list[tuple[str, str]]:
    highlights: list[tuple[str, str]] = []
    pages = str(triage.get("affected_pages_compact", "")).strip()
    if pages:
        highlights.append(("Affected pages", pages))

    if rule_id == "P011":
        side_counts = triage.get("side_counts", {})
        if isinstance(side_counts, dict) and side_counts:
            top = ", ".join(
                f"{k.replace('_', ' ')}: {v}" for k, v in sorted(side_counts.items())[:4]
            )
            highlights.append(("Margin sides", top))
        dominant = str(triage.get("dominant_margin_side", "")).strip()
        if dominant:
            highlights.append(("Dominant side", dominant.replace("_", " ")))
    elif rule_id == "P013":
        position_counts = triage.get("position_type_counts", {})
        if isinstance(position_counts, dict) and position_counts:
            top = ", ".join(
                f"{k.replace('_', ' ')}: {v}" for k, v in sorted(position_counts.items())[:4]
            )
            highlights.append(("Position types", top))
        multi = str(triage.get("multiple_candidate_pages_compact", "")).strip()
        if multi:
            highlights.append(("Multi-candidate pages", multi))
    elif rule_id == "P026":
        issue_counts = triage.get("issue_type_counts", {})
        if isinstance(issue_counts, dict) and issue_counts:
            top = ", ".join(
                f"{k.replace('_', ' ')}: {v}" for k, v in sorted(issue_counts.items())[:4]
            )
            highlights.append(("Issue types", top))

    return highlights


def _build_triage_panels(grouped: Mapping[str, Any]) -> list[TriagePanelView]:
    panels: list[TriagePanelView] = []
    for key, rule_id, title in _TRIAGE_KEYS:
        triage = grouped.get(key)
        if not isinstance(triage, Mapping):
            continue
        panels.append(
            TriagePanelView(
                rule_id=rule_id,
                title=title,
                triage_note=str(triage.get("triage_note", "")).strip(),
                triage_tier=str(triage.get("triage_tier", "")).strip(),
                raw_finding_count=int(triage.get("raw_finding_count", 0) or 0),
                affected_pages_compact=str(triage.get("affected_pages_compact", "")).strip(),
                highlights=_build_triage_highlights(rule_id, triage),
            )
        )
    return panels


_BBOX_DETAIL_KEYS: tuple[str, ...] = ("bbox", "rect")


def _parse_bbox_from_details(
    details: Mapping[str, str],
) -> tuple[float, float, float, float] | None:
    """Extract a drawable (x0, y0, x1, y1) box from finding details when present."""
    for key in _BBOX_DETAIL_KEYS:
        raw = str(details.get(key, "")).strip()
        if not raw:
            continue
        parts = [part.strip() for part in raw.split(",")]
        if len(parts) != 4:
            continue
        try:
            x0, y0, x1, y1 = (float(part) for part in parts)
        except ValueError:
            continue
        box = (x0, y0, x1, y1)
        return box if is_drawable_bbox(box) else None

    if all(str(details.get(key, "")).strip() for key in ("x0", "y0", "x1", "y1")):
        try:
            box = (
                float(details["x0"]),
                float(details["y0"]),
                float(details["x1"]),
                float(details["y1"]),
            )
        except ValueError:
            return None
        return box if is_drawable_bbox(box) else None
    return None


def _finding_view_from_item(
    item: Mapping[str, Any],
    *,
    is_source_audit: bool,
) -> tuple[FindingView, tuple[str, str] | None]:
    rule_id = str(item.get("rule_id", ""))
    details_raw = item.get("details", {})
    details = (
        {str(k): str(v) for k, v in details_raw.items()}
        if isinstance(details_raw, Mapping)
        else {}
    )
    page_raw = item.get("page")
    page = int(page_raw) if page_raw is not None else None
    source_file = str(item.get("source_file", "")) or _source_location_basename(details)
    source_line = str(item.get("source_line", "")) or details.get("line", "")
    location_key = (source_file, source_line) if (source_file or source_line) else None
    location_label = (
        format_source_location(details)
        if is_source_audit
        else (str(page) if page is not None else "")
    )
    issue_type = str(details.get("issue_type", ""))
    severity = str(item.get("severity", "WARNING"))
    category = map_finding_rule_to_category(rule_id, details)
    polished = build_polished_comment(
        rule_id=rule_id,
        issue_type=issue_type,
        severity=severity,
        page=page,
        details=details,
        category=category,
    )
    return (
        FindingView(
            rule_id=rule_id,
            category=category,
            page=page,
            severity=severity,
            issue_type=issue_type,
            polished_comment=polished,
            suggested_fix=sanitize_suggested_fix_for_web(
                rule_id, str(details.get("suggested_fix", ""))
            ),
            triage_tier=str(details.get("triage_tier", "")),
            confidence=str(details.get("confidence", "")),
            source_file=source_file,
            source_line=source_line,
            location_label=location_label,
            bbox=_parse_bbox_from_details(details),
        ),
        location_key,
    )


def build_report_view(report: Mapping[str, Any]) -> ReportView:
    """Convert an audit JSON payload into a GUI-friendly report view."""
    metadata = report.get("metadata", {})
    if not isinstance(metadata, Mapping):
        metadata = {}

    counts_by_severity = dict(metadata.get("counts_by_severity", {}) or {})
    counts_by_category = dict(metadata.get("counts_by_category", {}) or {})
    counts_by_rule = dict(metadata.get("counts_by_rule_id", {}) or {})
    total = int(metadata.get("total_findings", 0) or 0)

    grouped = report.get("grouped_summary", {})
    if not isinstance(grouped, Mapping):
        grouped = {}

    rule_summaries: list[RuleSummaryView] = []
    high_volume = grouped.get("high_volume_rules", [])
    if isinstance(high_volume, list):
        for entry in high_volume:
            if not isinstance(entry, Mapping):
                continue
            rule_summaries.append(
                RuleSummaryView(
                    rule_id=str(entry.get("rule_id", "")),
                    count=int(entry.get("count", 0) or 0),
                    category=str(entry.get("category", "")),
                )
            )

    if not rule_summaries and counts_by_rule:
        for rule_id, count in sorted(counts_by_rule.items()):
            rule_summaries.append(
                RuleSummaryView(
                    rule_id=rule_id,
                    count=int(count),
                    category=map_finding_rule_to_category(rule_id),
                )
            )

    audit_type = str(metadata.get("audit_type", "pdf"))
    is_source_audit = audit_type == "tex"

    finding_views: list[FindingView] = []
    pages: set[int] = set()
    source_locations: set[tuple[str, str]] = set()
    raw_findings = report.get("findings", [])
    if isinstance(raw_findings, list):
        for item in raw_findings:
            if not isinstance(item, Mapping):
                continue
            finding_view, location_key = _finding_view_from_item(
                item, is_source_audit=is_source_audit
            )
            page = finding_view.page
            if page is not None:
                pages.add(page)
            if location_key is not None:
                source_locations.add(location_key)
            finding_views.append(finding_view)

    grouped_problem_views: list[GroupedProblemView] = []
    raw_grouped = report.get("grouped_findings", [])
    if isinstance(raw_grouped, list):
        for entry in raw_grouped:
            if not isinstance(entry, Mapping):
                continue
            raw_indexes = entry.get("individual_indexes", [])
            if not isinstance(raw_indexes, list):
                raw_indexes = []
            indices = [
                idx for idx in raw_indexes if isinstance(idx, int) and 0 <= idx < len(finding_views)
            ]
            individual_views = [finding_views[idx] for idx in indices]
            if not individual_views:
                continue
            first = individual_views[0]
            grouped_problem_views.append(
                GroupedProblemView(
                    rule_id=str(entry.get("rule_id", first.rule_id)),
                    category=str(entry.get("category", first.category)),
                    severity=str(entry.get("severity", first.severity)),
                    issue_type=str(entry.get("issue_type", first.issue_type)),
                    polished_comment=str(
                        entry.get("problem", first.polished_comment)
                    ),
                    suggested_fix=sanitize_suggested_fix_for_web(
                        str(entry.get("rule_id", first.rule_id)),
                        str(entry.get("suggested_fix", first.suggested_fix)),
                    ),
                    occurrence_count=int(entry.get("occurrence_count", len(individual_views)) or 0),
                    affected_label=str(entry.get("affected_label", "Occurrences")),
                    affected_compact=str(entry.get("affected_compact", "")).strip(),
                    triage_tier=str(entry.get("triage_tier", first.triage_tier)),
                    confidence=str(entry.get("confidence", first.confidence)),
                    is_grouped=int(entry.get("occurrence_count", len(individual_views)) or 0) > 1,
                    page_tokens=[str(value) for value in entry.get("pages", [])],
                    location_tokens=[str(value) for value in entry.get("locations", [])],
                    individual_findings=individual_views,
                )
            )

    if not grouped_problem_views:
        grouped_problem_views = [
            GroupedProblemView(
                rule_id=finding.rule_id,
                category=finding.category,
                severity=finding.severity,
                issue_type=finding.issue_type,
                polished_comment=finding.polished_comment,
                suggested_fix=finding.suggested_fix,
                occurrence_count=1,
                affected_label="Locations" if is_source_audit else "Pages",
                affected_compact=(
                    finding.location_label
                    or (str(finding.page) if finding.page is not None else "")
                ),
                triage_tier=finding.triage_tier,
                confidence=finding.confidence,
                is_grouped=False,
                page_tokens=[str(finding.page)] if finding.page is not None else [],
                location_tokens=[finding.location_label] if finding.location_label else [],
                individual_findings=[finding],
            )
            for finding in finding_views
        ]

    location_count = int(metadata.get("source_location_count", 0) or 0)
    if is_source_audit and not location_count:
        location_count = len(source_locations)

    summary_cards = [
        SummaryCard(label="Total findings", value=str(total)),
        SummaryCard(label="Warnings", value=str(counts_by_severity.get("WARNING", 0))),
        SummaryCard(label="Errors", value=str(counts_by_severity.get("FAIL", 0))),
        SummaryCard(label="Categories", value=str(len(counts_by_category))),
        SummaryCard(label="Rules flagged", value=str(len(counts_by_rule))),
    ]
    if is_source_audit:
        summary_cards.append(
            SummaryCard(label="Source locations", value=str(location_count))
        )
    else:
        summary_cards.append(
            SummaryCard(label="Pages affected", value=str(len(pages)))
        )

    return ReportView(
        total_findings=total,
        counts_by_severity=counts_by_severity,
        counts_by_category=counts_by_category,
        counts_by_rule=counts_by_rule,
        pages=sorted(pages),
        summary_cards=summary_cards,
        rule_summaries=sorted(rule_summaries, key=lambda r: (-r.count, r.rule_id)),
        triage_panels=_build_triage_panels(grouped),
        grouped_problems=grouped_problem_views,
        findings=finding_views,
    )


def report_view_to_dict(view: ReportView) -> dict[str, Any]:
    """Serialize a ReportView for templates and in-memory job state."""
    return asdict(view)
