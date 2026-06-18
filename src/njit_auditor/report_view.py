"""GUI-ready report view DTOs built from existing audit JSON payloads."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field, replace
from typing import Any

from njit_auditor.evaluation import map_finding_rule_to_category
from njit_auditor.finding_explanations import (
    build_detailed_explanation,
    get_action_kind,
    get_action_label,
    get_no_highlight_reason,
)
from njit_auditor.issue_type_explanations import explain_issue_type, humanize_issue_type
from njit_auditor.pdf_highlight import has_visible_highlight, is_drawable_bbox
from njit_auditor.polished_comments import build_polished_comment, sanitize_suggested_fix_for_web
from njit_auditor.report_outputs import (
    _source_location_basename,
    format_source_location,
)

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
    # Actionability fields (presentation layer only — never change detection semantics)
    action_kind: str = ""       # "highlight" | "explanation"
    action_label: str = ""      # button label
    has_highlight: bool = False  # True when bbox is valid and drawable
    no_highlight_reason: str = ""  # why no highlight is available
    detailed_explanation: str = ""  # extended student-facing explanation
    # Issue-type display fields
    issue_type_label: str = ""        # readable label, e.g. "PDF annotation detected"
    issue_type_explanation: str = ""  # student-facing explanation of what the issue means


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
    # Actionability fields for the group card
    detailed_explanation: str = ""  # group-level explanation
    has_any_highlight: bool = False  # whether any individual finding has a highlight
    # Issue-type display fields
    issue_type_label: str = ""        # readable label for the grouped issue type
    issue_type_explanation: str = ""  # student-facing explanation of what the issue means


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
    inventory_findings: list[FindingView] = field(default_factory=list)


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
    pdf_page_sizes: Sequence[tuple[float, float]] | None = None,
) -> tuple[FindingView, tuple[str, str] | None, dict[str, str]]:
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
    bbox = _parse_bbox_from_details(details)
    page_count = len(pdf_page_sizes) if pdf_page_sizes else None
    page_size = (
        pdf_page_sizes[page - 1]
        if pdf_page_sizes and page is not None and 1 <= page <= len(pdf_page_sizes)
        else None
    )
    has_highlight = has_visible_highlight(
        bbox, page=page, page_count=page_count, page_size=page_size
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
            bbox=bbox,
            action_kind=get_action_kind(has_highlight=has_highlight, page=page),
            action_label=get_action_label(has_highlight=has_highlight, page=page),
            has_highlight=has_highlight,
            no_highlight_reason=get_no_highlight_reason(has_highlight=has_highlight, page=page),
            detailed_explanation=build_detailed_explanation(
                rule_id=rule_id,
                issue_type=issue_type,
                details=details,
                page=page,
            ),
            issue_type_label=humanize_issue_type(issue_type),
            issue_type_explanation=explain_issue_type(rule_id, issue_type),
        ),
        location_key,
        details,
    )


def _page_number_position_label(position_type: str) -> str:
    labels = {
        "bottom_center": "bottom center",
        "bottom_right": "bottom right",
        "top_center": "top center",
        "top_right": "top right",
        "other": "an unexpected location",
    }
    return labels.get(position_type, "an unexpected location")


def _compact_page_ranges(values: Sequence[int]) -> str:
    if not values:
        return ""
    ordered = sorted(set(values))
    ranges: list[str] = []
    start = end = ordered[0]
    for value in ordered[1:]:
        if value == end + 1:
            end = value
            continue
        ranges.append(str(start) if start == end else f"{start}–{end}")
        start = end = value
    ranges.append(str(start) if start == end else f"{start}–{end}")
    return ", ".join(ranges)
def _page_number_detail_text(issue_type: str, *, page: int | None) -> str:
    text = explain_issue_type("", issue_type)
    if page is not None:
        return f"{text} This finding is on page {page}."
    return text


def _page_number_comment_and_fix(
    rule_id: str,
    visible_issue_type: str,
    *,
    page: int | None,
    details: Mapping[str, str],
) -> tuple[str, str]:
    page_label = str(page) if page is not None else "this document"
    if visible_issue_type == "missing_page_number":
        return (
            "Review needed: Problem: "
            f"The auditor did not find a clear page number on page {page_label}. "
            "NJIT requires page numbers on this type of page unless numbering is "
            "intentionally suppressed for that page type. "
            "Add the required page number unless this page type should suppress numbering.",
            "Add the required page number unless this page type should suppress numbering.",
        )

    if visible_issue_type == "wrong_page_number_location":
        observed_location = (
            details.get("observed_location", "").strip()
            or details.get("candidate_position_label", "").strip()
            or _page_number_position_label(details.get("position_type", "").strip())
        )
        return (
            "Review needed: Problem: "
            f"The page number on page {page_label} appears at {observed_location}, "
            "but NJIT expects the page number in the required bottom position. "
            "Move the page number to the required bottom position.",
            "Move the page number to the required bottom position.",
        )

    if visible_issue_type == "wrong_page_numbering_style":
        observed_style = (
            details.get("observed_style", "").strip()
            or details.get("candidate_style_label", "").strip()
            or details.get("observed_styles", "").strip()
            or "the observed numbering style"
        )
        expected_style = details.get("expected_style", "").strip() or (
            "the numbering style required for this section"
        )
        return (
            "Review needed: Problem: "
            f"The page number on page {page_label} appears to use {observed_style}, "
            f"but this section is expected to use {expected_style}. "
            "Update the page-numbering style for this section.",
            "Update the page-numbering style for this section.",
        )

    if visible_issue_type == "wrong_page_number_sequence":
        observed = details.get("observed_sequence", "").strip() or details.get(
            "observed_value", ""
        ).strip() or details.get("candidate_text", "").strip() or "the detected value"
        expected = details.get("expected_sequence", "").strip() or details.get(
            "expected_value", ""
        ).strip() or details.get("expected_roman", "").strip() or "the expected sequence value"
        return (
            "Review needed: Problem: "
            f"The detected page number on page {page_label} does not appear to follow the "
            f"expected numbering sequence. Observed: {observed}. Expected: {expected}. "
            "Renumber the affected pages so the sequence is correct.",
            "Renumber the affected pages so the sequence is correct.",
        )

    if visible_issue_type == "duplicate_or_ambiguous_page_number":
        return (
            "Review needed: Problem: "
            f"Multiple page-number-like tokens were detected on page {page_label}. "
            "This may indicate duplicate page numbering or footer/header text being "
            "mistaken for a page number. Verify which token is the actual page number "
            "and remove or correct duplicates.",
            "Verify which token is the actual page number and remove or correct duplicates.",
        )

    if visible_issue_type == "page_number_should_be_suppressed":
        return (
            "Review needed: Problem: "
            f"A page number appears on page {page_label}, but this page type may require "
            "the page number to be suppressed or hidden. Remove the page number unless "
            "this page type is intentionally numbered.",
            "Remove the page number unless this page type is intentionally numbered.",
        )

    return (
        "Review needed: Problem: Page numbering may need review.",
        "",
    )


def _classify_visible_page_number_issue(
    finding: FindingView,
    details: Mapping[str, str],
) -> tuple[str | None, bool]:
    if finding.rule_id == "P013":
        if finding.issue_type == "p013_document_overview":
            return None, False
        synthetic_mapping = {
            "missing_page_number": "missing_page_number",
            "multiple_page_numbers": "duplicate_or_ambiguous_page_number",
            "inconsistent_position": "wrong_page_number_location",
            "mixed_numbering_style": "wrong_page_numbering_style",
            "sequence_gap": "wrong_page_number_sequence",
            "page_number_sequence_error": "wrong_page_number_sequence",
        }
        if finding.issue_type != "page_number_candidate":
            return synthetic_mapping.get(finding.issue_type), True
        try:
            candidate_count = int(details.get("candidate_count_on_page", "1") or "1")
        except ValueError:
            candidate_count = 1
        if candidate_count > 1:
            return "duplicate_or_ambiguous_page_number", True
        if details.get("position_type", "").strip() in {"top_center", "top_right", "other"}:
            return "wrong_page_number_location", True
        return None, False

    if finding.rule_id == "P019":
        mapping = {
            "missing_page_number": "missing_page_number",
            "multiple_page_numbers": "duplicate_or_ambiguous_page_number",
            "inconsistent_position": "wrong_page_number_location",
            "mixed_numbering_style": "wrong_page_numbering_style",
            "sequence_gap": "wrong_page_number_sequence",
            "page_number_sequence_error": "wrong_page_number_sequence",
        }
        return mapping.get(finding.issue_type), True

    if finding.rule_id == "P022":
        if finding.issue_type == "visible_page_number_on_no_number_page":
            return "page_number_should_be_suppressed", True
        return None, True

    if finding.rule_id == "P028":
        mapping = {
            "frontmatter_page_number_style_issue": "wrong_page_numbering_style",
            "body_page_roman_number": "wrong_page_numbering_style",
            "frontmatter_arabic_number": "wrong_page_numbering_style",
            "arabic_number_on_frontmatter_page": "wrong_page_numbering_style",
            "uppercase_roman_on_frontmatter_page": "wrong_page_numbering_style",
            "roman_number_on_body_page": "wrong_page_numbering_style",
        }
        return mapping.get(finding.issue_type), True

    if finding.rule_id in {"P029", "P037"}:
        return "wrong_page_number_sequence", True

    return None, True


def _apply_page_number_presentation(
    finding: FindingView,
    details: Mapping[str, str],
) -> tuple[FindingView, bool]:
    if finding.rule_id == "P013" and finding.issue_type == "p013_document_overview":
        return finding, False
    visible_issue_type, is_problem = _classify_visible_page_number_issue(finding, details)
    if visible_issue_type is None:
        if finding.rule_id == "P013":
            return (
                replace(
                    finding,
                    issue_type="detected_page_number_candidate",
                    issue_type_label=humanize_issue_type("detected_page_number_candidate"),
                    issue_type_explanation=explain_issue_type(
                        "", "detected_page_number_candidate"
                    ),
                    polished_comment=(
                        "Review needed: A page-number-like token was detected in the bottom "
                        "area on page "
                        f"{finding.page if finding.page is not None else 'this page'}. "
                        "This is an internal verification signal and is not counted as a "
                        "problem unless another finding reports a specific defect."
                    ),
                    suggested_fix="",
                    action_kind="",
                    action_label="",
                    detailed_explanation=_page_number_detail_text(
                        "detected_page_number_candidate", page=finding.page
                    ),
                ),
                False,
            )
        return finding, is_problem

    comment, suggested_fix = _page_number_comment_and_fix(
        finding.rule_id,
        visible_issue_type,
        page=finding.page,
        details=details,
    )
    return (
        replace(
            finding,
            issue_type=visible_issue_type,
            issue_type_label=humanize_issue_type(visible_issue_type),
            issue_type_explanation=explain_issue_type("", visible_issue_type),
            polished_comment=comment,
            suggested_fix=suggested_fix,
            detailed_explanation=_page_number_detail_text(
                visible_issue_type, page=finding.page
            ),
        ),
        is_problem,
    )


def build_report_view(
    report: Mapping[str, Any],
    *,
    pdf_page_sizes: Sequence[tuple[float, float]] | None = None,
) -> ReportView:
    """Convert an audit JSON payload into a GUI-friendly report view.

    *pdf_page_sizes* is the (width, height) of each page of the audited PDF,
    in order, when available. It lets ``has_highlight`` be computed against
    real page geometry (page-in-range and bbox-intersects-page-bounds)
    rather than just bbox shape validity; pass None when no PDF is available
    (e.g. TeX-source audits) to fall back to shape-only validation.
    """
    metadata = report.get("metadata", {})
    if not isinstance(metadata, Mapping):
        metadata = {}

    grouped = report.get("grouped_summary", {})
    if not isinstance(grouped, Mapping):
        grouped = {}

    audit_type = str(metadata.get("audit_type", "pdf"))
    is_source_audit = audit_type == "tex"

    all_finding_views: list[FindingView] = []
    finding_details_by_index: dict[int, dict[str, str]] = {}
    pages: set[int] = set()
    source_locations: set[tuple[str, str]] = set()
    raw_findings = report.get("findings", [])
    if isinstance(raw_findings, list):
        for index, item in enumerate(raw_findings):
            if not isinstance(item, Mapping):
                continue
            finding_view, _, details = _finding_view_from_item(
                item, is_source_audit=is_source_audit, pdf_page_sizes=pdf_page_sizes
            )
            finding_details_by_index[index] = details
            all_finding_views.append(finding_view)

    finding_views: list[FindingView] = []
    inventory_findings: list[FindingView] = []
    visible_view_by_index: dict[int, FindingView] = {}
    visible_indexes: set[int] = set()
    for index, finding_view in enumerate(all_finding_views):
        details = finding_details_by_index.get(index, {})
        visible_view = finding_view
        is_problem = True
        if visible_view.category == "page_numbering":
            visible_view, is_problem = _apply_page_number_presentation(visible_view, details)
        if is_problem:
            visible_indexes.add(index)
            visible_view_by_index[index] = visible_view
            finding_views.append(visible_view)
            page = visible_view.page
            if page is not None:
                pages.add(page)
            location_key = (
                (visible_view.source_file, visible_view.source_line)
                if (visible_view.source_file or visible_view.source_line)
                else None
            )
            if location_key is not None:
                source_locations.add(location_key)
        elif visible_view.issue_type == "detected_page_number_candidate":
            inventory_findings.append(visible_view)

    counts_by_severity = {
        "PASS": sum(1 for finding in finding_views if finding.severity == "PASS"),
        "WARNING": sum(1 for finding in finding_views if finding.severity == "WARNING"),
        "FAIL": sum(1 for finding in finding_views if finding.severity == "FAIL"),
    }
    counts_by_category: dict[str, int] = {}
    counts_by_rule: dict[str, int] = {}
    for finding in finding_views:
        counts_by_category[finding.category] = counts_by_category.get(finding.category, 0) + 1
        counts_by_rule[finding.rule_id] = counts_by_rule.get(finding.rule_id, 0) + 1
    counts_by_category = dict(sorted(counts_by_category.items()))
    counts_by_rule = dict(sorted(counts_by_rule.items()))
    total = len(finding_views)

    rule_summaries: list[RuleSummaryView] = [
        RuleSummaryView(
            rule_id=rule_id,
            count=count,
            category=map_finding_rule_to_category(rule_id),
        )
        for rule_id, count in sorted(counts_by_rule.items())
    ]

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
                idx
                for idx in raw_indexes
                if (
                    isinstance(idx, int)
                    and idx in visible_indexes
                    and 0 <= idx < len(all_finding_views)
                )
            ]
            individual_views = [visible_view_by_index[idx] for idx in indices]
            if not individual_views:
                continue
            first = individual_views[0]
            group_rule_id = str(entry.get("rule_id", first.rule_id))
            group_issue_type = first.issue_type
            has_any_highlight = any(f.has_highlight for f in individual_views)
            page_values = sorted({f.page for f in individual_views if f.page is not None})
            location_values = sorted(
                {f.location_label for f in individual_views if f.location_label}
            )
            affected_compact = (
                _compact_page_ranges(page_values)
                if page_values
                else str(entry.get("locations_compact", "")).strip() or ", ".join(location_values)
            )
            grouped_problem_views.append(
                GroupedProblemView(
                    rule_id=group_rule_id,
                    category=first.category,
                    severity=first.severity,
                    issue_type=group_issue_type,
                    polished_comment=first.polished_comment,
                    suggested_fix=first.suggested_fix,
                    occurrence_count=len(individual_views),
                    affected_label="Pages" if page_values else "Locations",
                    affected_compact=affected_compact,
                    triage_tier=first.triage_tier,
                    confidence=first.confidence,
                    is_grouped=len(individual_views) > 1,
                    page_tokens=sorted(
                        {str(f.page) for f in individual_views if f.page is not None},
                        key=int,
                    ),
                    location_tokens=location_values,
                    individual_findings=individual_views,
                    detailed_explanation=first.detailed_explanation,
                    has_any_highlight=has_any_highlight,
                    issue_type_label=first.issue_type_label,
                    issue_type_explanation=first.issue_type_explanation,
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
                detailed_explanation=finding.detailed_explanation,
                has_any_highlight=finding.has_highlight,
                issue_type_label=finding.issue_type_label,
                issue_type_explanation=finding.issue_type_explanation,
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
        triage_panels=[
            panel
            for panel in _build_triage_panels(grouped)
            if panel.rule_id in counts_by_rule and panel.rule_id != "P013"
        ],
        grouped_problems=grouped_problem_views,
        findings=finding_views,
        inventory_findings=inventory_findings,
    )


def report_view_to_dict(view: ReportView) -> dict[str, Any]:
    """Serialize a ReportView for templates and in-memory job state."""
    return asdict(view)
