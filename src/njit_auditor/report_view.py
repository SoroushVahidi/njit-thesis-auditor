"""GUI-ready report view DTOs built from existing audit JSON payloads."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field, replace
from typing import Any

from njit_auditor.evaluation import map_finding_rule_to_category
from njit_auditor.finding_explanations import (
    build_detailed_explanation,
    build_no_highlight_guidance,
    get_action_kind,
    get_action_label,
    get_no_highlight_reason,
)
from njit_auditor.issue_type_explanations import explain_issue_type, humanize_issue_type
from njit_auditor.pdf_highlight import (
    has_visible_highlight,
    is_drawable_bbox,
    sub_page_location_label,
)
from njit_auditor.polished_comments import (
    P032_ENTRY_KIND_LABELS,
    build_polished_comment,
    finalize_student_facing_comment_and_fix,
    resolve_suggested_fix_for_display,
    title_case_reason_short_label,
    title_case_subject_label,
)
from njit_auditor.report_outputs import (
    _source_location_basename,
    format_source_location,
)

_TRIAGE_KEYS: tuple[tuple[str, str, str], ...] = (
    ("p011_margin_triage", "P011", "Margin / overflow summary"),
    ("p013_triage", "P013", "Page-number candidates summary"),
    ("p026_font_triage", "P026", "Body font summary"),
)

_PAGE_TYPE_SECTION_LABELS: dict[str, str] = {
    "table_of_contents": "Table of Contents",
    "list_of_tables": "List of Tables",
    "list_of_figures": "List of Figures",
}

_LIST_LOCATION_RULE_IDS = frozenset(
    {"P018", "P024", "P032", "P036", "P040", "P046", "P053"}
)

_CONFIDENCE_ORDER: tuple[str, ...] = ("high", "medium", "low")
_CONFIDENCE_LABELS: dict[str, str] = {
    "high": "High",
    "medium": "Medium",
    "low": "Low",
}


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
    problem_number: int = 0
    problem_anchor: str = ""
    suggested_fix: str = ""
    triage_tier: str = ""
    confidence: str = ""
    confidence_level: str = ""
    confidence_label: str = ""
    confidence_css_class: str = ""
    source_file: str = ""
    source_line: str = ""
    location_label: str = ""
    bbox: tuple[float, float, float, float] | None = None
    # Actionability fields (presentation layer only — never change detection semantics)
    action_kind: str = ""       # "highlight" | "original_page" | "explanation"
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
    problem_numbers: list[int] = field(default_factory=list)
    problem_number_label: str = ""
    problem_anchor: str = ""
    triage_tier: str = ""
    confidence: str = ""
    confidence_level: str = ""
    confidence_label: str = ""
    confidence_css_class: str = ""
    confidence_levels: list[str] = field(default_factory=list)
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


def _p015_location_label(rule_id: str, issue_type: str, details: Mapping[str, str]) -> str:
    """Return a paragraph-specific location label for P015 indentation findings.

    P015 always knows which paragraph on the page it flagged, so this is more
    precise than the generic page-quadrant label other rules fall back to.
    Returns "" for every other rule, which leaves their location_label
    computation unchanged.
    """
    if rule_id != "P015":
        return ""
    if issue_type == "unexpected_opening_indent":
        return "First line of the opening paragraph"
    if issue_type == "missing_later_indent":
        paragraph_index = str(details.get("paragraph_index", "")).strip()
        if paragraph_index:
            return f"First line of body paragraph {paragraph_index}"
    return ""


def _section_label_from_details(details: Mapping[str, str]) -> str:
    page_type = details.get("page_type", "").strip()
    if page_type:
        return _PAGE_TYPE_SECTION_LABELS.get(page_type, "")
    section_type = details.get("section_type", "").strip()
    return _P036_SECTION_LABELS.get(section_type, "")


def enriched_pdf_location_label(
    rule_id: str,
    issue_type: str,
    details: Mapping[str, str],
    page: int | None,
    *,
    bbox_label: str = "",
) -> str:
    """Return a privacy-safe location label using list/caption metadata when available."""
    page_prefix = f"Page {page}" if page is not None else ""
    section_label = _section_label_from_details(details)
    entry_kind_label = P032_ENTRY_KIND_LABELS.get(details.get("entry_kind", "").strip(), "")
    entry_index = details.get("entry_index", "").strip()
    pair_index = details.get("entry_pair_index", "").strip()
    float_number = details.get("float_number", "").strip()

    if rule_id == "P036" and issue_type in _P036_SPACING_ISSUE_TYPES:
        try:
            pair_start = int(pair_index) + 1
            pair_clause = f"spacing between entries {pair_start}-{pair_start + 1}"
        except ValueError:
            pair_clause = "spacing between consecutive entries"
        if page_prefix and section_label:
            return f"{page_prefix} — {section_label}, {pair_clause}"
        if page_prefix:
            return f"{page_prefix} — {pair_clause}"

    if entry_index.isdigit():
        entry_num = int(entry_index) + 1
        kind_label = entry_kind_label or section_label or "list"
        if page_prefix:
            return f"{page_prefix} — {kind_label} entry {entry_num}"
        return f"{kind_label} entry {entry_num}"

    if float_number and rule_id == "P035":
        noun = "Table" if "table" in issue_type else "Figure"
        if page_prefix:
            return f"{page_prefix} — {noun} {float_number}"

    if section_label and page_prefix and rule_id in _LIST_LOCATION_RULE_IDS:
        return f"{page_prefix} — {section_label}"

    if bbox_label:
        return bbox_label
    return ""


def _finalize_finding_display(finding: FindingView) -> FindingView:
    comment, fix = finalize_student_facing_comment_and_fix(
        finding.rule_id,
        finding.issue_type,
        finding.polished_comment,
        finding.suggested_fix,
    )
    return replace(finding, polished_comment=comment, suggested_fix=fix)


def _normalize_confidence(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in _CONFIDENCE_LABELS:
        return normalized
    return ""


def _ordered_confidence_levels(values: Sequence[str]) -> list[str]:
    normalized = {_normalize_confidence(value) for value in values}
    normalized.discard("")
    return [level for level in _CONFIDENCE_ORDER if level in normalized]


def _confidence_level(levels: Sequence[str]) -> str:
    ordered = _ordered_confidence_levels(levels)
    if len(ordered) == 1:
        return ordered[0]
    if ordered:
        return "mixed"
    return ""


def _confidence_label(levels: Sequence[str]) -> str:
    ordered = _ordered_confidence_levels(levels)
    if len(ordered) == 1:
        return f"{_CONFIDENCE_LABELS[ordered[0]]} confidence"
    if ordered:
        joined = ", ".join(_CONFIDENCE_LABELS[level] for level in ordered)
        return f"Mixed confidence: {joined}"
    return "Needs review"


def _confidence_css_class(levels: Sequence[str]) -> str:
    ordered = _ordered_confidence_levels(levels)
    if len(ordered) == 1:
        return f"confidence-badge--{ordered[0]}"
    if ordered:
        return "confidence-badge--mixed"
    return "confidence-badge--unknown"


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
    issue_type = str(details.get("issue_type", ""))
    bbox_label = sub_page_location_label(bbox, page_size)
    location_label = (
        format_source_location(details)
        if is_source_audit
        else (
            _p015_location_label(rule_id, issue_type, details)
            or enriched_pdf_location_label(
                rule_id,
                issue_type,
                details,
                page,
                bbox_label=bbox_label,
            )
        )
    )
    severity = str(item.get("severity", "WARNING"))
    category = map_finding_rule_to_category(rule_id, details)
    confidence = _normalize_confidence(str(details.get("confidence", "")))
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
            problem_number=0,
            problem_anchor="",
            severity=severity,
            issue_type=issue_type,
            polished_comment=polished,
            suggested_fix=resolve_suggested_fix_for_display(
                rule_id,
                issue_type,
                existing=str(details.get("suggested_fix", "")),
            ),
            triage_tier=str(details.get("triage_tier", "")),
            confidence=confidence,
            confidence_level=confidence,
            confidence_label=_confidence_label([confidence]),
            confidence_css_class=_confidence_css_class([confidence]),
            source_file=source_file,
            source_line=source_line,
            location_label=location_label,
            bbox=bbox,
            action_kind=get_action_kind(has_highlight=has_highlight, page=page),
            action_label=get_action_label(has_highlight=has_highlight, page=page),
            has_highlight=has_highlight,
            no_highlight_reason=get_no_highlight_reason(
                has_highlight=has_highlight,
                page=page,
                rule_id=rule_id,
                issue_type=issue_type,
                details=details,
                location_label=location_label,
            ),
            detailed_explanation=build_detailed_explanation(
                rule_id=rule_id,
                issue_type=issue_type,
                details=details,
                page=page,
                has_highlight=has_highlight,
                location_label=location_label,
            ),
            issue_type_label=humanize_issue_type(issue_type),
            issue_type_explanation=explain_issue_type(rule_id, issue_type, details=details),
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


def _problem_prefix(confidence: str) -> str:
    return "Problem" if confidence.strip().lower() == "high" else "Likely problem"


def _margin_side_label(side: str) -> str:
    labels = {
        "left_margin": "left margin",
        "right_margin": "right margin",
        "top_margin": "top margin",
        "bottom_margin": "bottom margin",
        "left": "left margin",
        "right": "right margin",
        "top": "top margin",
        "bottom": "bottom margin",
    }
    return labels.get(side.strip().lower(), "required page margin")


def _margin_overflow_extras(details: Mapping[str, str]) -> list[str]:
    overflow = details.get("worst_overflow_pt", "").strip()
    line_count = details.get("affected_line_count", "").strip()
    extras: list[str] = []
    if overflow:
        extras.append(f"about {overflow}pt beyond the boundary")
    if line_count:
        noun = "line" if line_count == "1" else "lines"
        extras.append(f"across {line_count} text {noun}")
    return extras


def _margin_overflow_detail_phrase(details: Mapping[str, str]) -> str:
    extras = _margin_overflow_extras(details)
    if not extras:
        return ""
    return f" ({'; '.join(extras)})"


def _margin_observed_phrase(details: Mapping[str, str]) -> str:
    side = _margin_side_label(details.get("side", ""))
    if side == "required page margin":
        base = "Some content appears too close to or beyond a required page margin"
    else:
        base = f"Content appears to cross the required {side} boundary"
    extras = _margin_overflow_extras(details)
    if not extras:
        return base
    return f"{base} ({'; '.join(extras)})"


def _margin_issue_type_explanation(details: Mapping[str, str], *, page: int | None) -> str:
    side = _margin_side_label(details.get("side", ""))
    page_text = f" on page {page}" if page is not None else ""
    if side == "required page margin":
        return (
            "This means the auditor found content that appears too close to or beyond "
            f"a required page margin{page_text}, but it could not determine the exact side."
        )
    return (
        "This means the auditor found content that appears to cross the required "
        f"{side} boundary{page_text}."
    )


def _margin_detailed_explanation(
    details: Mapping[str, str], *, page: int | None, has_highlight: bool, location_label: str
) -> str:
    side = _margin_side_label(details.get("side", ""))
    observed = _margin_observed_phrase(details)
    if side == "required page margin":
        why = (
            "the detector found layout content outside the expected body area, but the "
            "stored metadata does not identify which margin side was crossed"
        )
    else:
        why = (
            f"body content should stay inside the {side}, not extend beyond the required "
            "page boundary"
        )
    page_text = f" on page {page}" if page is not None else ""
    no_highlight_text = (
        ""
        if has_highlight
        else " "
        + build_no_highlight_guidance(
            rule_id="P011",
            issue_type="margin_boundary_violation",
            details=dict(details),
            page=page,
            location_label=location_label,
        )
    )
    return (
        f"Observed: {observed}{page_text}. "
        "Expected: Content should stay inside NJIT's required page margins "
        "(left 1.5 inches; right, top, and bottom 1 inch). "
        f"Why this is suspicious: {why}. "
        "What to check or fix: inspect tables, figures, long lines, indentation, "
        "headers, and footers on this page."
        f"{no_highlight_text}"
    )


def _margin_comment_and_fix(
    *, page: int | None, details: Mapping[str, str], confidence: str
) -> tuple[str, str]:
    page_label = str(page) if page is not None else "this page"
    prefix = _problem_prefix(confidence)
    side = _margin_side_label(details.get("side", ""))
    if side == "required page margin":
        comment = (
            "Review needed: "
            f"{prefix}: Some content on page {page_label} appears too close to or beyond "
            "a required page margin. The auditor could not determine the exact margin "
            "side from the available metadata. NJIT formatting expects body content to "
            "remain inside the required page margins. Review tables, figures, long "
            "lines, indentation, headers, and footers on this page."
        )
        fix = (
            "Move the flagged content back inside the required page margins and inspect "
            "tables, figures, long lines, indentation, headers, and footers on this page."
        )
        return comment, fix
    overflow_detail = _margin_overflow_detail_phrase(details)
    comment = (
        "Review needed: "
        f"{prefix}: Content on page {page_label} appears to cross the required {side} "
        f"boundary{overflow_detail}. NJIT formatting expects body content to remain inside "
        "the required page margins. Review the highlighted area if available, or inspect "
        "tables, figures, long lines, indentation, headers, and footers on this page."
    )
    fix = (
        f"Move the flagged content back inside the required {side} and correct any "
        "table, figure, long-line, indentation, header, or footer layout causing the overflow."
    )
    return comment, fix


def _font_issue_kind(issue_type: str) -> str:
    if issue_type == "possible_body_font_size_issue":
        return "size"
    return "family"


def _font_role_text(details: Mapping[str, str]) -> tuple[str, str]:
    text_role = details.get("text_role", "").strip().replace("_", " ")
    if text_role:
        role = text_role.capitalize()
        role_fix = text_role
    else:
        role = "Body text"
        role_fix = "body text"
    return role, role_fix


def _font_expected_family(details: Mapping[str, str]) -> str:
    return details.get("expected_font", "").strip() or details.get("expected", "").strip() or (
        "Times New Roman or an accepted Times-compatible font"
    )


def _font_expected_size(details: Mapping[str, str]) -> str:
    expected = details.get("expected_size", "").strip() or details.get("expected", "").strip()
    if expected:
        return expected
    return "12pt"


def _font_observed_value(details: Mapping[str, str]) -> str:
    return details.get("observed_font", "").strip() or details.get("observed_size", "").strip() or (
        details.get("observed_summary", "").strip()
    )


def _font_issue_type_explanation(
    details: Mapping[str, str], *, issue_type: str, page: int | None
) -> str:
    role, _ = _font_role_text(details)
    observed = _font_observed_value(details)
    page_text = f" on page {page}" if page is not None else ""
    if _font_issue_kind(issue_type) == "size":
        if observed:
            return (
                f"This means sampled {role.lower()} spans{page_text} appear at {observed} "
                "instead of the expected 12pt body-text size."
            )
        return (
            f"This means sampled {role.lower()} spans{page_text} appear not to match "
            "the expected 12pt body-text size, but the precise observed size was unavailable."
        )
    if observed:
        return (
            f"This means sampled {role.lower()} spans{page_text} appear to use {observed} "
            "instead of Times New Roman or another accepted Times-compatible font."
        )
    return (
        f"This means sampled {role.lower()} spans{page_text} appear not to use the "
        "expected font family, but the precise observed font name was unavailable."
    )


def _font_detailed_explanation(
    details: Mapping[str, str],
    *,
    issue_type: str,
    page: int | None,
    has_highlight: bool,
    location_label: str,
) -> str:
    role, role_fix = _font_role_text(details)
    observed = _font_observed_value(details)
    span_count = details.get("affected_span_count", "").strip()
    candidate_count = details.get("candidate_count", "").strip()
    if _font_issue_kind(issue_type) == "size":
        expected = _font_expected_size(details)
        if observed:
            observed_text = f"{role} spans appear at {observed}"
        else:
            observed_text = (
                f"Some {role.lower()}-like spans appear not to match the expected size, "
                "but the precise observed value was unavailable"
            )
    else:
        expected = _font_expected_family(details)
        if observed:
            observed_text = f"{role} spans appear to use {observed}"
        else:
            observed_text = (
                f"Some {role.lower()}-like spans appear not to match the expected font family, "
                "but the precise observed value was unavailable"
            )
    count_bits: list[str] = []
    if span_count:
        noun = "span" if span_count == "1" else "spans"
        count_bits.append(f"{span_count} flagged {noun}")
    if candidate_count:
        noun = "candidate" if candidate_count == "1" else "candidates"
        count_bits.append(f"{candidate_count} sampled {noun}")
    counts_text = f" ({'; '.join(count_bits)})" if count_bits else ""
    page_text = f" on page {page}" if page is not None else ""
    no_highlight_text = (
        ""
        if has_highlight
        else " "
        + build_no_highlight_guidance(
            rule_id="P026",
            issue_type=issue_type,
            details=dict(details),
            page=page,
            location_label=location_label,
        )
    )
    return (
        f"Observed: {observed_text}{counts_text}{page_text}. "
        f"Expected: {role} should use {expected}. "
        "Why this is suspicious: the detector repeatedly saw a non-matching font pattern "
        "in body-text-like spans on this page. "
        f"What to check or fix: confirm whether the flagged text is {role_fix}, a caption, "
        "a heading, table text, a footnote, or another exception, then update the source "
        f"document's font settings if needed.{no_highlight_text}"
    )


def _font_comment_and_fix(
    *, issue_type: str, page: int | None, details: Mapping[str, str], confidence: str
) -> tuple[str, str]:
    prefix = _problem_prefix(confidence)
    page_label = str(page) if page is not None else "this page"
    role, role_fix = _font_role_text(details)
    observed = _font_observed_value(details)
    if _font_issue_kind(issue_type) == "size":
        expected = _font_expected_size(details)
        if observed:
            comment = (
                "Review needed: "
                f"{prefix}: {role} on page {page_label} appears to use font size {observed}. "
                f"NJIT expects {role_fix} to use {expected}. Update the source document's "
                f"{role_fix} style or verify whether the flagged text is a permitted exception "
                "such as a table, figure caption, heading, or footnote."
            )
        else:
            comment = (
                "Review needed: "
                f"{prefix}: Some {role_fix}-like spans on page {page_label} appear not to "
                f"match NJIT's expected font size. The auditor could not extract a precise "
                f"observed size value for this card. NJIT expects {role_fix} to use {expected}. "
                "Review the explanation and verify whether the flagged text is a permitted "
                "exception such as a table, figure caption, heading, or footnote."
            )
        fix = (
            f"Update the source document's {role_fix} font size to {expected} and verify "
            "whether the flagged text is body text or a permitted exception."
        )
        return comment, fix

    expected = _font_expected_family(details)
    if observed:
        comment = (
            "Review needed: "
            f"{prefix}: {role} on page {page_label} appears to use font family {observed}. "
            "NJIT expects "
            f"{role_fix} to use {expected}. Update the source document's {role_fix} style if "
            "this text is part of the main body."
        )
    else:
        comment = (
            "Review needed: "
            f"{prefix}: Some {role_fix}-like spans on page {page_label} appear not to match "
            "NJIT's expected font family. The auditor could not extract a precise observed "
            f"font value for this card. NJIT expects {role_fix} to use {expected}. Review "
            "the explanation and confirm whether the flagged text is body text or another "
            "text role."
        )
    fix = (
        f"Update the source document's {role_fix} font family to {expected} and verify "
        "whether the flagged text is body text or a permitted exception."
    )
    return comment, fix


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


def _problem_number_label(problem_numbers: Sequence[int]) -> str:
    if not problem_numbers:
        return ""
    compact = _compact_page_ranges([int(number) for number in problem_numbers])
    if len(set(problem_numbers)) == 1:
        return f"Problem {compact}"
    return f"Problems {compact}"
def _page_number_detail_text(issue_type: str, *, page: int | None) -> str:
    text = explain_issue_type("", issue_type)
    if page is not None:
        return f"{text} This finding is on page {page}."
    return text


_MAX_PLAUSIBLE_SEQUENCE_PAGE_NUMBER = 9999


def _plausible_page_sequence_value(value: str) -> bool:
    """Reject implausible Arabic sequence values such as a misdetected long digit run.

    Roman-numeral or placeholder text values are not int-parseable and are left
    as-is; this only guards against an absurdly large Arabic number slipping
    through from a misdetected page-number candidate.
    """
    try:
        number = int(value)
    except ValueError:
        return True
    return 0 <= number <= _MAX_PLAUSIBLE_SEQUENCE_PAGE_NUMBER


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
        if not _plausible_page_sequence_value(observed) or not _plausible_page_sequence_value(
            expected
        ):
            return (
                "Review needed: Problem: "
                f"The page-number sequence on page {page_label} looks inconsistent; "
                "please manually check the nearby page numbers.",
                "Manually check the page numbers near this page for a sequence error.",
            )
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
                    no_highlight_reason="",
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
    detailed_explanation = _page_number_detail_text(
        visible_issue_type, page=finding.page
    )
    if not finding.has_highlight and finding.page is not None:
        guidance = build_no_highlight_guidance(
            rule_id=finding.rule_id,
            issue_type=visible_issue_type,
            details=dict(details),
            page=finding.page,
            location_label=finding.location_label,
        )
        detailed_explanation = (
            f"{detailed_explanation} "
            f"{guidance}"
        )
    return (
        replace(
            finding,
            issue_type=visible_issue_type,
            issue_type_label=humanize_issue_type(visible_issue_type),
            issue_type_explanation=explain_issue_type("", visible_issue_type),
            polished_comment=comment,
            suggested_fix=suggested_fix,
            detailed_explanation=detailed_explanation,
        ),
        is_problem,
    )


def _apply_margin_presentation(
    finding: FindingView,
    details: Mapping[str, str],
) -> tuple[FindingView, bool]:
    if finding.rule_id != "P011" or finding.issue_type != "margin_boundary_violation":
        return finding, True
    comment, suggested_fix = _margin_comment_and_fix(
        page=finding.page,
        details=details,
        confidence=finding.confidence,
    )
    return (
        replace(
            finding,
            polished_comment=comment,
            suggested_fix=suggested_fix,
            no_highlight_reason=(
                finding.no_highlight_reason
                if finding.has_highlight
                else build_no_highlight_guidance(
                    rule_id=finding.rule_id,
                    issue_type=finding.issue_type,
                    details=dict(details),
                    page=finding.page,
                    location_label=finding.location_label,
                )
            ),
            detailed_explanation=_margin_detailed_explanation(
                details,
                page=finding.page,
                has_highlight=finding.has_highlight,
                location_label=finding.location_label,
            ),
            issue_type_explanation=_margin_issue_type_explanation(details, page=finding.page),
        ),
        True,
    )


def _apply_font_presentation(
    finding: FindingView,
    details: Mapping[str, str],
) -> tuple[FindingView, bool]:
    if finding.rule_id != "P026":
        return finding, True
    if finding.issue_type not in {
        "possible_body_font_family_issue",
        "possible_body_font_size_issue",
    }:
        return finding, True
    comment, suggested_fix = _font_comment_and_fix(
        issue_type=finding.issue_type,
        page=finding.page,
        details=details,
        confidence=finding.confidence,
    )
    return (
        replace(
            finding,
            polished_comment=comment,
            suggested_fix=suggested_fix,
            no_highlight_reason=(
                finding.no_highlight_reason
                if finding.has_highlight
                else build_no_highlight_guidance(
                    rule_id=finding.rule_id,
                    issue_type=finding.issue_type,
                    details=dict(details),
                    page=finding.page,
                    location_label=finding.location_label,
                )
            ),
            detailed_explanation=_font_detailed_explanation(
                details,
                issue_type=finding.issue_type,
                page=finding.page,
                has_highlight=finding.has_highlight,
                location_label=finding.location_label,
            ),
            issue_type_explanation=_font_issue_type_explanation(
                details,
                issue_type=finding.issue_type,
                page=finding.page,
            ),
        ),
        True,
    )


def _title_case_issue_label(details: Mapping[str, str]) -> str:
    subject = title_case_subject_label(details.get("source", ""))
    reason_label = title_case_reason_short_label(details.get("expected_or_reason", ""))
    return f"Possible title-case issue ({subject}, {reason_label})"


def _title_case_subject_and_rule_clause(details: Mapping[str, str]) -> tuple[str, str]:
    if details.get("source", "") == "caption":
        return "table title", "NJIT requires table titles to use Title Case"
    return (
        "Level 2 heading",
        "NJIT requires Level 2 headings (e.g. 1.1, 1.2) to use Title Case",
    )


def _apply_title_case_presentation(
    finding: FindingView,
    details: Mapping[str, str],
) -> tuple[FindingView, bool]:
    """Distinguish same-page P020 occurrences by the offending word.

    Overrides only the display comment after grouping has already been
    computed upstream (on the word-independent comment), so repeated
    same-page occurrences with the same source/reason still collapse into
    one grouped card; only the per-occurrence text shown when expanded
    differs. The flagged word and its corrected capitalization come from
    this student's own uploaded PDF, so showing them here (unlike the
    generic build_polished_comment() text) is safe.
    """
    if finding.rule_id != "P020" or finding.issue_type != "possible_title_capitalization_issue":
        return finding, True
    finding = replace(finding, issue_type_label=_title_case_issue_label(details))
    flagged_word = details.get("flagged_word", "").strip()
    corrected_word = details.get("corrected_word", "").strip()
    if not flagged_word or not corrected_word:
        return finding, True
    page_label = str(finding.page) if finding.page is not None else "this page"
    subject, rule_clause = _title_case_subject_and_rule_clause(details)
    comment = (
        f"Likely problem: In a {subject} on page {page_label}, the word "
        f"'{flagged_word}' should be capitalized as '{corrected_word}'. "
        f"{rule_clause} (capitalize the first word, last word, and all "
        "major words of 4+ letters)."
    )
    return replace(finding, polished_comment=comment), True


_P036_SPACING_ISSUE_TYPES: frozenset[str] = frozenset(
    {
        "toc_inter_entry_spacing_too_tight",
        "lot_inter_entry_spacing_too_tight",
        "lof_inter_entry_spacing_too_tight",
    }
)
_P036_SECTION_LABELS: dict[str, str] = {
    "table_of_contents": "Table of Contents",
    "list_of_tables": "List of Tables",
    "list_of_figures": "List of Figures",
}


def _p036_entry_pair_label(details: Mapping[str, str]) -> str:
    try:
        index = int(details.get("entry_pair_index", "").strip())
    except ValueError:
        return "two consecutive entries"
    return f"entries {index + 1}-{index + 2}"


def _p036_spacing_detail_phrase(details: Mapping[str, str]) -> str:
    gap_points = details.get("gap_points", "").strip()
    required_gap_points = details.get("required_gap_points", "").strip()
    gap_ratio = details.get("gap_ratio", "").strip()
    extras: list[str] = []
    if gap_points:
        extras.append(f"observed gap {gap_points}pt")
    if required_gap_points:
        extras.append(f"expected at least {required_gap_points}pt")
    if gap_ratio:
        extras.append(f"about {gap_ratio}x the expected spacing")
    if not extras:
        return ""
    return f" ({'; '.join(extras)})"


def _apply_spacing_presentation(
    finding: FindingView,
    details: Mapping[str, str],
) -> tuple[FindingView, bool]:
    """Distinguish same-page P036 occurrences by entry pair and gap metrics.

    This only overrides the display comment after grouping has already been
    computed upstream (on the generic, pair-independent comment), so repeated
    same-page occurrences still collapse into one grouped card; only the
    per-occurrence text shown when expanded differs.
    """
    if finding.rule_id != "P036" or finding.issue_type not in _P036_SPACING_ISSUE_TYPES:
        return finding, True
    page_label = str(finding.page) if finding.page is not None else "this page"
    section_label = _P036_SECTION_LABELS.get(details.get("section_type", ""), "TOC/list")
    pair_label = _p036_entry_pair_label(details)
    detail_phrase = _p036_spacing_detail_phrase(details)
    comment = (
        f"Likely problem: The spacing between {pair_label} of the {section_label} on "
        f"page {page_label} appears tighter than expected{detail_phrase}. NJIT expects "
        "consistent, comfortably readable spacing between consecutive entries. "
        "Increase the spacing between these entries to match the rest of the list."
    )
    return replace(finding, polished_comment=comment), True


_P035_FLOAT_ISSUE_LABELS: dict[str, str] = {
    "table_caption_not_above_body": (
        "Likely problem: A table caption on page {page}{float_clause} does not "
        "appear above the table body. NJIT expects table captions to appear above the table."
    ),
    "figure_caption_not_below_body": (
        "Likely problem: A figure caption on page {page}{float_clause} does not "
        "appear below the figure body. NJIT expects figure captions to appear below the figure."
    ),
    "table_body_not_centered": (
        "Likely problem: A table body block on page {page}{float_clause} does not "
        "appear centered within the text area. Center the table within the page margins."
    ),
    "figure_body_not_centered": (
        "Likely problem: A figure body block on page {page}{float_clause} does not "
        "appear centered within the text area. Center the figure within the page margins."
    ),
}
_P035_TABLE_ISSUE_TYPES: frozenset[str] = frozenset(
    {"table_caption_not_above_body", "table_body_not_centered"}
)


def _apply_float_layout_presentation(
    finding: FindingView,
    details: Mapping[str, str],
) -> tuple[FindingView, bool]:
    """Distinguish P035 occurrences by the affected table/figure number.

    Overrides only the display comment after grouping has already been
    computed upstream (on the float-number-independent comment).
    """
    template = _P035_FLOAT_ISSUE_LABELS.get(finding.issue_type)
    if finding.rule_id != "P035" or template is None:
        return finding, True
    page_label = str(finding.page) if finding.page is not None else "this page"
    float_number = details.get("float_number", "").strip()
    if float_number:
        noun = "Table" if finding.issue_type in _P035_TABLE_ISSUE_TYPES else "Figure"
        float_clause = f" for {noun} {float_number}"
    else:
        float_clause = ""
    comment = template.format(page=page_label, float_clause=float_clause)
    return replace(finding, polished_comment=comment), True


def _apply_lof_punctuation_presentation(
    finding: FindingView,
    details: Mapping[str, str],
) -> tuple[FindingView, bool]:
    """Distinguish same-page P040 occurrences by the affected entry's index.

    Overrides only the display comment after grouping has already been
    computed upstream (on the entry-index-independent comment).
    """
    if finding.rule_id != "P040" or finding.issue_type != "lof_entry_missing_terminal_punctuation":
        return finding, True
    page_label = str(finding.page) if finding.page is not None else "this page"
    raw_index = details.get("entry_index", "").strip()
    try:
        entry_clause = f" (entry #{int(raw_index) + 1})"
    except ValueError:
        entry_clause = ""
    comment = (
        f"Problem: A List of Figures entry{entry_clause} on page {page_label} appears "
        "to be missing terminal punctuation. Every figure description in the List of "
        "Figures should end with a period, question mark, or exclamation point."
    )
    return replace(finding, polished_comment=comment), True


_P018_ENTRY_TEMPLATES: dict[str, str] = {
    "misaligned_page_number_column": (
        "Likely problem: On page {page}{count_clause}, a TOC, List of Tables, or List "
        "of Figures entry has a page-number column that does not align with the "
        "dominant column on this list page. Align entry page numbers to the same "
        "right-hand column throughout the list."
    ),
    "missing_page_number": (
        "Likely problem: On page {page}{count_clause}, a TOC, List of Tables, or List "
        "of Figures entry appears to be missing its trailing page number. Add the "
        "missing page number for this entry."
    ),
    "inconsistent_leader_dots": (
        "Likely problem: On page {page}{count_clause}, leader dots or spacing before "
        "page numbers are inconsistent with the dominant style on this list page. Use "
        "consistent leader-dot spacing between entry text and page numbers."
    ),
    "inconsistent_hierarchy_indent": (
        "Likely problem: On page {page}{count_clause}, entry indentation does not "
        "match the expected hierarchy level for this TOC or list page. Adjust "
        "indentation so chapter, section, and subsection entries visually reflect "
        "their level."
    ),
}


def _p018_count_clause(details: Mapping[str, str]) -> str:
    count = details.get("affected_entry_count", "").strip()
    delta = details.get("worst_delta_pt", "").strip()
    extras: list[str] = []
    if count:
        noun = "entry" if count == "1" else "entries"
        extras.append(f"{count} {noun} affected")
    if delta:
        extras.append(f"worst offset about {delta}pt")
    if not extras:
        return ""
    return f" ({'; '.join(extras)})"


def _apply_toc_alignment_presentation(
    finding: FindingView,
    details: Mapping[str, str],
) -> tuple[FindingView, bool]:
    """Surface P018's per-page affected entry count and worst offset.

    Overrides only the display comment after grouping has already been
    computed upstream (on the count/offset-independent comment).
    """
    template = _P018_ENTRY_TEMPLATES.get(finding.issue_type)
    if finding.rule_id != "P018" or template is None:
        return finding, True
    page_label = str(finding.page) if finding.page is not None else "this page"
    comment = template.format(page=page_label, count_clause=_p018_count_clause(details))
    return replace(finding, polished_comment=comment), True


_P014_ATTRIBUTE_LABELS: tuple[tuple[str, str], ...] = (
    ("centered", "centered"),
    ("near_top", "near the top of the page"),
    ("bold", "bold"),
    ("all_caps", "in all capital letters"),
)


def _apply_named_heading_presentation(
    finding: FindingView,
    details: Mapping[str, str],
) -> tuple[FindingView, bool]:
    """Name which P014 layout attribute(s) failed instead of a generic message.

    The detector already records centered/near_top/bold/all_caps booleans in
    details; this only selects which ones to mention.
    """
    if finding.rule_id != "P014":
        return finding, True
    page_label = str(finding.page) if finding.page is not None else "this page"
    heading = details.get("heading", "").strip()
    heading_clause = f" ('{heading}')" if heading else ""
    failed_labels = [
        label
        for key, label in _P014_ATTRIBUTE_LABELS
        if details.get(key, "").strip().lower() == "false"
    ]
    if failed_labels:
        issue_clause = ", ".join(f"not {label}" for label in failed_labels)
        fix = f"Make this heading {', '.join(failed_labels)}."
    else:
        issue_clause = "not formatted to NJIT's heading style"
        fix = "Place this heading centered near the top in bold all-caps."
    comment = (
        f"Problem: The front-matter heading{heading_clause} on page {page_label} is "
        f"{issue_clause}. NJIT requires named front-matter headings to be centered "
        "near the top of the page, in bold, and in all capital letters."
    )
    return replace(finding, polished_comment=comment, suggested_fix=fix), True


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
        elif visible_view.rule_id == "P011":
            visible_view, is_problem = _apply_margin_presentation(visible_view, details)
        elif visible_view.rule_id == "P026":
            visible_view, is_problem = _apply_font_presentation(visible_view, details)
        elif visible_view.rule_id == "P020":
            visible_view, is_problem = _apply_title_case_presentation(visible_view, details)
        elif visible_view.rule_id == "P036":
            visible_view, is_problem = _apply_spacing_presentation(visible_view, details)
        elif visible_view.rule_id == "P035":
            visible_view, is_problem = _apply_float_layout_presentation(visible_view, details)
        elif visible_view.rule_id == "P040":
            visible_view, is_problem = _apply_lof_punctuation_presentation(visible_view, details)
        elif visible_view.rule_id == "P018":
            visible_view, is_problem = _apply_toc_alignment_presentation(visible_view, details)
        elif visible_view.rule_id == "P014":
            visible_view, is_problem = _apply_named_heading_presentation(visible_view, details)
        if is_problem:
            visible_view = _finalize_finding_display(visible_view)
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

    numbered_finding_views: list[FindingView] = []
    for problem_number, index in enumerate(sorted(visible_indexes), start=1):
        numbered_view = replace(
            visible_view_by_index[index],
            problem_number=problem_number,
            problem_anchor=f"problem-{problem_number}",
        )
        visible_view_by_index[index] = numbered_view
        numbered_finding_views.append(numbered_view)
    finding_views = numbered_finding_views

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
            confidence_levels = _ordered_confidence_levels(
                [finding.confidence_level for finding in individual_views]
            )
            problem_numbers = [f.problem_number for f in individual_views if f.problem_number > 0]
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
                    problem_numbers=problem_numbers,
                    problem_number_label=_problem_number_label(problem_numbers),
                    problem_anchor=first.problem_anchor,
                    polished_comment=first.polished_comment,
                    suggested_fix=first.suggested_fix,
                    occurrence_count=len(individual_views),
                    affected_label="Pages" if page_values else "Locations",
                    affected_compact=affected_compact,
                    triage_tier=first.triage_tier,
                    confidence=first.confidence,
                    confidence_level=_confidence_level(confidence_levels),
                    confidence_label=_confidence_label(confidence_levels),
                    confidence_css_class=_confidence_css_class(confidence_levels),
                    confidence_levels=confidence_levels,
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
                problem_numbers=([finding.problem_number] if finding.problem_number > 0 else []),
                problem_number_label=(
                    _problem_number_label([finding.problem_number])
                    if finding.problem_number > 0
                    else ""
                ),
                problem_anchor=finding.problem_anchor,
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
                confidence_level=finding.confidence_level,
                confidence_label=finding.confidence_label,
                confidence_css_class=finding.confidence_css_class,
                confidence_levels=_ordered_confidence_levels([finding.confidence_level]),
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
