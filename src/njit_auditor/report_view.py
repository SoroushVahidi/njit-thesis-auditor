"""GUI-ready report view DTOs built from existing audit JSON payloads."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field, replace
from typing import Any

from njit_auditor.digital_commons_student_preview import (
    digital_commons_advisory_comment,
    digital_commons_advisory_location_label,
    digital_commons_advisory_suggested_fix,
)
from njit_auditor.digital_commons_wrapper import is_layout_warning_suppressed_on_wrapper_page
from njit_auditor.evaluation import map_finding_rule_to_category
from njit_auditor.finding_explanations import (
    build_detailed_explanation,
    build_no_highlight_guidance,
    get_action_kind,
    get_action_label,
    get_no_highlight_reason,
)
from njit_auditor.high_volume_student_preview import (
    abstract_indent_location_label,
    consume_grouped_finding_display_slot,
    font_location_label,
    margin_location_label,
    normalize_area_phrase,
)
from njit_auditor.highlight_targeting import resolve_primary_highlight_bbox
from njit_auditor.issue_type_explanations import explain_issue_type, humanize_issue_type
from njit_auditor.p011_student_preview import (
    P011PagePresentationStats,
    collect_p011_margin_pages_from_serialized,
    consume_p011_finding_visibility,
    init_p011_display_state,
    is_p011_margin_finding,
    p011_combined_no_highlight_reason,
    p011_combined_rolled_up_comment,
    p011_combined_rolled_up_explanation,
    p011_combined_suggested_fix,
    p011_page_location_label,
)
from njit_auditor.p012_student_preview import (
    P012PresentationStats,
    consume_p012_finding_visibility,
    find_p012_summary_anchor_index,
    init_p012_display_state,
    is_p012_finding,
    p012_document_location_label,
    p012_document_no_highlight_reason,
    p012_document_rolled_up_comment,
    p012_document_rolled_up_explanation,
    p012_document_suggested_fix,
    p012_location_label,
    p012_rolled_up_comment,
    p012_rolled_up_explanation,
    p012_rolled_up_suggested_fix,
)
from njit_auditor.p026_student_preview import (
    P026PatternPresentationStats,
    collect_p026_pattern_pages_from_serialized,
    consume_p026_finding_visibility,
    init_p026_display_state,
    is_p026_finding,
    p026_document_location_label,
    p026_document_no_highlight_reason,
    p026_document_rolled_up_comment,
    p026_document_rolled_up_explanation,
    p026_document_suggested_fix,
    p026_page_location_label,
    p026_pattern_key,
)
from njit_auditor.page_number_student_preview import (
    classify_visible_page_number_issue,
    consume_page_number_display_slot,
    is_page_number_rule,
    page_number_location_label,
)
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
    _high_volume_pattern_note,
    _source_location_basename,
    format_source_location,
)
from njit_auditor.title_case_student_preview import (
    affected_title_phrase,
    consume_p020_display_slot,
    p020_short_likely_problem,
    p020_short_suggested_fix,
    sanitize_title_case_line_preview,
)
from njit_auditor.toc_list_student_preview import (
    affected_entry_phrase,
    between_entries_phrase,
    is_toc_structural_column_label,
    p018_entry_location_suffix,
    p018_short_likely_problem,
    p018_short_suggested_fix,
    p036_short_likely_problem,
    p036_short_suggested_fix,
    sanitize_toc_list_entry_preview,
)

_TRIAGE_KEYS: tuple[tuple[str, str, str], ...] = (
    ("p011_margin_triage", "P011", "Margin / overflow summary"),
    ("p013_triage", "P013", "Page-number candidates summary"),
    ("p026_font_triage", "P026", "Body font summary"),
    ("p019_page_numbering_triage", "P019", "Page-numbering summary"),
    ("p036_toc_list_spacing_triage", "P036", "Table of Contents/List spacing summary"),
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
    page_display_label: str = ""
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
    problem_count: int = 0
    informational_count: int = 0


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
    page_display_tokens: list[str] = field(default_factory=list)
    location_tokens: list[str] = field(default_factory=list)
    individual_findings: list[FindingView] = field(default_factory=list)
    # Actionability fields for the group card
    detailed_explanation: str = ""  # group-level explanation
    has_any_highlight: bool = False  # whether any individual finding has a highlight
    # Issue-type display fields
    issue_type_label: str = ""        # readable label for the grouped issue type
    issue_type_explanation: str = ""  # student-facing explanation of what the issue means
    # Why a high-volume card repeats, shown up front (not buried in a details element)
    pattern_note: str = ""


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
    elif rule_id == "P019":
        by_category = triage.get("by_category", {})
        if isinstance(by_category, dict) and by_category:
            top = ", ".join(
                f"{k.replace('_', ' ')}: {v}" for k, v in sorted(by_category.items())[:4]
            )
            highlights.append(("Pattern types", top))
        high = int(triage.get("high_priority_count", 0) or 0)
        medium = int(triage.get("medium_priority_count", 0) or 0)
        low = int(triage.get("low_priority_count", 0) or 0)
        if high or medium or low:
            highlights.append(
                ("Review priority", f"high: {high}, medium: {medium}, low: {low}")
            )
    elif rule_id == "P036":
        section_counts = triage.get("section_type_counts", {})
        if isinstance(section_counts, dict) and section_counts:
            top = ", ".join(
                f"{_P036_SECTION_LABELS.get(k, k.replace('_', ' '))}: {v}"
                for k, v in sorted(section_counts.items())[:4]
            )
            highlights.append(("Affected sections", top))

    return highlights


def _build_triage_panels(
    grouped: Mapping[str, Any],
    counts_by_rule: Mapping[str, int],
    inventory_counts_by_rule: Mapping[str, int],
) -> list[TriagePanelView]:
    panels: list[TriagePanelView] = []
    for key, rule_id, title in _TRIAGE_KEYS:
        triage = grouped.get(key)
        if not isinstance(triage, Mapping):
            continue
        raw_finding_count = int(
            triage.get("raw_finding_count", triage.get("total_findings", 0)) or 0
        )
        triage_note = str(
            triage.get("triage_note") or triage.get("review_guidance") or ""
        ).strip()
        problem_count = int(counts_by_rule.get(rule_id, 0))
        # Use the same per-rule inventory tally the "Detected candidates"
        # section and the Markdown export are built from, rather than
        # raw_finding_count - problem_count: raw_finding_count can include
        # findings (e.g. P013's document-overview entry) that are neither a
        # visible problem nor an inventory candidate, which would otherwise
        # make this badge disagree with the list it links to.
        informational_count = int(inventory_counts_by_rule.get(rule_id, 0))
        panels.append(
            TriagePanelView(
                rule_id=rule_id,
                title=title,
                triage_note=triage_note,
                triage_tier=str(triage.get("triage_tier", "")).strip(),
                raw_finding_count=raw_finding_count,
                affected_pages_compact=str(triage.get("affected_pages_compact", "")).strip(),
                highlights=_build_triage_highlights(rule_id, triage),
                problem_count=problem_count,
                informational_count=informational_count,
            )
        )
    return panels


def _parse_wrapper_pages(metadata: Mapping[str, Any]) -> set[int]:
    raw = str(metadata.get("digital_commons_wrapper_pages", "")).strip()
    if not raw:
        return set()
    pages: set[int] = set()
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        try:
            pages.add(int(token))
        except ValueError:
            continue
    return pages


def _build_digital_commons_advisory_view(
    metadata: Mapping[str, Any],
) -> FindingView | None:
    wrapper_pages = sorted(_parse_wrapper_pages(metadata))
    if not wrapper_pages:
        return None
    page_count = int(
        str(metadata.get("digital_commons_wrapper_page_count", len(wrapper_pages)))
    )
    pages_compact = str(metadata.get("digital_commons_wrapper_pages_compact", "")).strip()
    first_page = wrapper_pages[0]
    location_label = digital_commons_advisory_location_label(
        first_page=first_page,
        page_count=page_count,
    )
    return FindingView(
        rule_id="P025",
        category="frontmatter_structure",
        page=first_page,
        page_display_label=str(first_page),
        problem_number=0,
        problem_anchor="",
        severity="WARNING",
        issue_type="digital_commons_wrapper_pages_detected",
        polished_comment=digital_commons_advisory_comment(
            page_count=page_count,
            pages_compact=pages_compact,
        ),
        suggested_fix=digital_commons_advisory_suggested_fix(),
        triage_tier="review",
        confidence="high",
        confidence_level="high",
        confidence_label="High confidence",
        confidence_css_class="confidence-badge--high",
        source_file="",
        source_line="",
        location_label=location_label,
        bbox=None,
        action_kind=get_action_kind(has_highlight=False, page=first_page),
        action_label=get_action_label(has_highlight=False, page=first_page),
        has_highlight=False,
        no_highlight_reason=(
            "Open the original PDF on the listed wrapper page(s) and remove the "
            "repository-generated cover or metadata pages before resubmitting."
        ),
        detailed_explanation=(
            "Observed: the PDF includes Digital Commons repository wrapper content before "
            "the thesis manuscript. Expected: submit only the thesis manuscript pages for "
            "formatting review. What to check or fix: remove repository cover, copyright, "
            "and citation pages so margin and layout warnings reflect your thesis rather "
            "than the download wrapper."
        ),
        issue_type_label="Digital Commons wrapper pages detected",
        issue_type_explanation=(
            "This means the PDF still includes NJIT Digital Commons repository pages that "
            "are not part of your thesis manuscript."
        ),
    )


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


def _page_display_label(details: Mapping[str, str], page: int | None) -> str:
    label = str(details.get("page_label", "")).strip()
    if label:
        return label
    if page is None:
        return ""
    return str(page)


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
    page_display = _page_display_label(details, page)
    if page is None:
        page_prefix = ""
    elif page_display and page_display != str(page):
        page_prefix = page_display
    else:
        page_prefix = f"Page {page}"
    section_label = _section_label_from_details(details)
    entry_kind_label = P032_ENTRY_KIND_LABELS.get(details.get("entry_kind", "").strip(), "")
    entry_index = details.get("entry_index", "").strip()
    pair_index = details.get("entry_pair_index", "").strip()
    float_number = details.get("float_number", "").strip()

    if rule_id == "P020" and issue_type == "possible_title_capitalization_issue":
        title_phrase = affected_title_phrase(
            sanitize_title_case_line_preview(details.get("line_preview", "")),
            source=details.get("source", ""),
        )
        if page_prefix and title_phrase:
            return f"{page_prefix} — {title_phrase}"

    if rule_id == "P011" and issue_type == "margin_boundary_violation":
        return margin_location_label(details, page, bbox_label=bbox_label)

    if rule_id == "P038":
        if issue_type == "required_heading_missing":
            expected_heading = details.get("expected_heading", "").strip()
            if expected_heading:
                return f"Front matter — required heading missing: {expected_heading}"
            return "Front matter — required heading missing"
        if issue_type == "heading_phrase_not_exact" and page_prefix:
            expected_heading = details.get("expected_heading", "").strip()
            if expected_heading:
                return f"{page_prefix} — {expected_heading} heading phrase"

    if rule_id == "P026" and issue_type in {
        "possible_body_font_family_issue",
        "possible_body_font_size_issue",
    }:
        return font_location_label(issue_type, details, page, bbox_label=bbox_label)

    if rule_id == "P044" and issue_type in {
        "abstract_first_paragraph_indented",
        "abstract_subsequent_paragraph_not_indented",
    }:
        return abstract_indent_location_label(
            issue_type, details, page, bbox_label=bbox_label
        )

    if rule_id == "P036" and issue_type in _P036_SPACING_ISSUE_TYPES:
        between = between_entries_phrase(
            details.get("previous_entry_preview", ""),
            details.get("next_entry_preview", ""),
        )
        if page_prefix and section_label and between:
            return f"{page_prefix} — {section_label}, {between}"
        try:
            pair_start = int(pair_index) + 1
            pair_clause = f"spacing between entries {pair_start}-{pair_start + 1}"
        except ValueError:
            pair_clause = "spacing between consecutive entries"
        if page_prefix and section_label:
            return f"{page_prefix} — {section_label}, {pair_clause}"
        if page_prefix:
            return f"{page_prefix} — {pair_clause}"

    preview = sanitize_toc_list_entry_preview(details.get("affected_entry_preview", ""))
    if preview and page_prefix and section_label and rule_id == "P018":
        suffix = p018_entry_location_suffix(preview)
        if suffix:
            return f"{page_prefix} — {section_label} {suffix}"

    if preview and page_prefix and section_label and rule_id in {"P046"}:
        return f"{page_prefix} — {section_label}, {affected_entry_phrase(preview)}"

    if rule_id == "P024" and entry_index.isdigit() and page_prefix:
        line_preview = sanitize_toc_list_entry_preview(details.get("line_preview", ""))
        kind_label = entry_kind_label or section_label or "list"
        if line_preview:
            return f"{page_prefix} — {kind_label}, {affected_entry_phrase(line_preview)}"

    if entry_index.isdigit():
        entry_num = int(entry_index) + 1
        kind_label = entry_kind_label or section_label or "list"
        if page_prefix:
            return f"{page_prefix} — {kind_label} entry {entry_num}"
        return f"{kind_label} entry {entry_num}"

    if rule_id == "P018" and page_prefix and section_label:
        worst_entry_index = details.get("worst_entry_index", "").strip()
        if worst_entry_index.isdigit() and not preview:
            worst_entry_num = int(worst_entry_index) + 1
            return f"{page_prefix} — {section_label}, entry {worst_entry_num} alignment issue"

    if rule_id in ("P018", "P046") and page_prefix and section_label:
        affected_count = details.get("affected_entry_count", "").strip()
        if affected_count.isdigit() and int(affected_count) > 0:
            noun = "entry" if affected_count == "1" else "entries"
            return f"{page_prefix} — {section_label}, {affected_count} affected {noun}"

    if float_number and rule_id == "P035":
        noun = "Table" if "table" in issue_type else "Figure"
        if page_prefix:
            return f"{page_prefix} — {noun} {float_number}"

    if section_label and page_prefix and rule_id in _LIST_LOCATION_RULE_IDS:
        return f"{page_prefix} — {section_label}"

    if page_prefix and bbox_label:
        return f"{page_prefix} — {normalize_area_phrase(bbox_label)}"
    if page_prefix and not is_page_number_rule(rule_id):
        return page_prefix
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
        return f"Confidence: {_CONFIDENCE_LABELS[ordered[0]]}"
    if ordered:
        return "Confidence: Mixed"
    return "Confidence: Needs review"


def _confidence_css_class(levels: Sequence[str]) -> str:
    ordered = _ordered_confidence_levels(levels)
    if len(ordered) == 1:
        return f"confidence-badge--{ordered[0]}"
    if not ordered:
        return "confidence-badge--unknown"
    level_set = set(ordered)
    if "high" in level_set:
        return "confidence-badge--mixed-orange"
    if "medium" in level_set:
        return "confidence-badge--medium"
    return "confidence-badge--low"


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
    issue_type = str(details.get("issue_type", ""))
    source_file = str(item.get("source_file", "")) or _source_location_basename(details)
    source_line = str(item.get("source_line", "")) or details.get("line", "")
    location_key = (source_file, source_line) if (source_file or source_line) else None
    bbox = resolve_primary_highlight_bbox(
        details,
        rule_id=rule_id,
        issue_type=issue_type,
    )
    page_count = len(pdf_page_sizes) if pdf_page_sizes else None
    page_size = (
        pdf_page_sizes[page - 1]
        if pdf_page_sizes and page is not None and 1 <= page <= len(pdf_page_sizes)
        else None
    )
    has_highlight = has_visible_highlight(
        bbox, page=page, page_count=page_count, page_size=page_size
    )
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
            page_display_label=_page_display_label(details, page),
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
        extras.append(f"{line_count} text {noun} affected")
    return extras


def _margin_affected_lines_clause(details: Mapping[str, str]) -> str:
    """Format a student-readable clause listing affected line text previews, if stored."""
    texts_raw = details.get("affected_line_texts", "").strip()
    if not texts_raw:
        return ""
    parts = [t.strip() for t in texts_raw.split("|") if t.strip()]
    if not parts:
        return ""
    if len(parts) == 1:
        return f' Affected text: "{parts[0]}".'
    previews = " and ".join(f'"{p}"' for p in parts[:3])
    suffix = " (and more)" if len(parts) > 3 else ""
    return f" Affected text lines include: {previews}{suffix}."


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
            f"{prefix}: Some content on page {page_label} appears too close to or beyond "
            "a required page margin. The auditor could not determine the exact margin "
            "side from the available metadata. NJIT formatting expects body content to "
            "remain inside the required page margins. Review tables, figures, long "
            "lines, indentation, headers, and footers on this page."
        )
        fix = (
            f"Check the page header, page number, tables, figures, captions, and any long "
            f"lines on page {page_label}. Move any content that crosses a required margin "
            "back inside the allowed page area."
        )
        return comment, fix
    overflow_detail = _margin_overflow_detail_phrase(details)
    lines_clause = _margin_affected_lines_clause(details)
    comment = (
        f"{prefix}: Content on page {page_label} appears to cross the required {side} "
        f"boundary{overflow_detail}. NJIT formatting expects body content to remain inside "
        "the required page margins. Review the highlighted area if available, or inspect "
        f"tables, figures, long lines, indentation, headers, and footers on this page."
        f"{lines_clause}"
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
    observed_font = details.get("observed_font", "").strip()
    if observed_font:
        return observed_font
    observed_size = details.get("observed_size", "").strip()
    if observed_size:
        return observed_size
    summary = details.get("observed_summary", "").strip()
    # Font detectors store short technical labels here (e.g. CMR12). Reject
    # sentence-like values that could be mis-ingested dissertation text.
    if summary and len(summary) <= 40 and "\n" not in summary:
        if " " not in summary or summary.endswith("pt"):
            return summary
    return ""


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
        if rule_id == "P028":
            region_label = {"front_matter": "front matter", "body": "body"}.get(
                details.get("page_region", "").strip(), ""
            )
            section_phrase = f"the {region_label} section" if region_label else "this section"
            if region_label == "front matter":
                convention = (
                    " NJIT requires preliminary pages (before Chapter 1) to use lowercase "
                    "Roman numerals such as i, ii, iii, iv."
                )
            elif region_label == "body":
                convention = (
                    " NJIT requires the main body (starting at Chapter 1) to use Arabic "
                    "numerals starting at 1."
                )
            else:
                convention = ""
            return (
                "Review needed: Problem: "
                f"The page number on page {page_label} appears to use {observed_style}, "
                f"but pages in {section_phrase} are expected to use {expected_style}."
                f"{convention} "
                "Update the page-numbering style for this section.",
                "Update the page-numbering style for this section.",
            )
        if rule_id == "P019":
            where = f"on page {page_label}" if page is not None else "across the document"
            return (
                "Review needed: Problem: "
                f"More than one page-numbering style was found {where} "
                f"({observed_style}), but NJIT requires one consistent style per section "
                f"(expected: {expected_style}). This is a broader consistency check; if a "
                "more specific front-matter/body style problem is also reported above for "
                "this page, fix that one first and re-check this warning afterward.",
                "Verify the numbering-style boundary between front matter and body, then "
                "correct any inconsistent pages.",
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
        if rule_id == "P029":
            return (
                "Review needed: Problem: "
                f"The Roman numeral page number on page {page_label} breaks the expected "
                f"front-matter sequence (observed: {observed}; expected: {expected}). This "
                "checks the page-to-page front-matter sequence specifically; if a broader "
                "document-wide sequence warning is also reported above for this page, fix "
                "this front-matter sequence issue first and re-check that warning afterward.",
                "Correct this page's Roman numeral so it continues the front-matter sequence.",
            )
        if rule_id == "P037":
            return (
                "Review needed: Problem: "
                f"The Roman numeral page number on page {page_label} does not match the "
                "value required by the NJIT front-matter template for this section "
                f"(observed: {observed}; expected: {expected}). This checks a specific "
                "section against its fixed template position, which is different from the "
                "general sequence check; if a broader sequence warning is also reported "
                "above for this page, fix this template-position issue first.",
                "Set this section's page number to the NJIT template's required Roman numeral.",
            )
        if rule_id == "P019":
            previous_value = details.get("previous_sequence_value", "").strip()
            next_value = details.get("next_sequence_value", "").strip()
            neighbor_parts: list[str] = []
            if previous_value:
                neighbor_parts.append(f"previous detected page number: {previous_value}")
            if next_value:
                neighbor_parts.append(f"next detected page number: {next_value}")
            neighbor_clause = (
                f" Nearby detected numbers: {'; '.join(neighbor_parts)}."
                if neighbor_parts
                else ""
            )
            sequence_confidence = details.get("sequence_confidence", "").strip() or details.get(
                "confidence", ""
            ).strip()
            confidence_clause = (
                f" Detection confidence: {sequence_confidence}."
                if sequence_confidence
                else ""
            )
            return (
                f"The printed page number on page {page_label} is '{observed}', but the "
                f"document-wide numbering sequence expected '{expected}' at this position."
                f"{neighbor_clause}{confidence_clause} If a more specific front-matter "
                "Roman-numeral sequence or section-template problem is also reported above "
                "for this page, fix that one first and re-check this warning afterward.",
                f"Change this page to '{expected}' or renumber nearby pages so the "
                "sequence is consecutive.",
            )
        return (
            "Review needed: Problem: "
            f"The page number on page {page_label} is '{observed}', but the numbering "
            f"sequence expected '{expected}' at this position. Change this page to "
            f"'{expected}' or renumber nearby pages so the sequence is consecutive.",
            f"Change this page to '{expected}' or renumber nearby pages so the sequence "
            "is consecutive.",
        )

    if visible_issue_type == "duplicate_or_ambiguous_page_number":
        candidate_tokens = details.get("candidate_tokens", "").strip()
        if candidate_tokens:
            return (
                f"Multiple plausible page-number tokens were detected on page {page_label}: "
                f"{candidate_tokens}. Verify which token is the printed page number and "
                "remove or correct any duplicates.",
                "Verify which token is the printed page number and remove or correct duplicates.",
            )
        return (
            f"Multiple page-number-like tokens were detected on page {page_label}. "
            "Verify which token is the printed page number and remove or correct duplicates.",
            "Verify which token is the printed page number and remove or correct duplicates.",
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
    return classify_visible_page_number_issue(
        finding.rule_id, finding.issue_type, details
    )


_VISIBLE_PAGE_NUMBER_PROBLEM_PHRASES: dict[str, str] = {
    "missing_page_number": "the missing-page-number problem already reported above for this page",
    "duplicate_or_ambiguous_page_number": (
        "the duplicate-or-ambiguous page-number problem already reported above for this page"
    ),
    "wrong_page_number_location": (
        "the wrong page-number location problem already reported above for this page"
    ),
    "wrong_page_numbering_style": (
        "the wrong page-numbering style problem already reported above for this page"
    ),
    "wrong_page_number_sequence": (
        "the page-number sequence problem already reported above for this page"
    ),
}


def _redundant_candidate_comment_and_explanation(
    visible_issue_type: str, *, page: int
) -> tuple[str, str]:
    """Explain a P013 candidate that restates a problem another rule already reported.

    Used only when another page-numbering rule (today, P019) reports a confirmed
    defect for the same page and the same synthetic problem type that P013's raw
    candidate detection would otherwise also show — see _collect_claimed_page_number_keys.
    """
    phrase = _VISIBLE_PAGE_NUMBER_PROBLEM_PHRASES.get(
        visible_issue_type, "the page-numbering problem already reported above for this page"
    )
    comment = (
        "Review needed: "
        f"A page-number-like token was detected on page {page}. This matches {phrase}, "
        "so it is not counted as a second, separate problem."
    )
    explanation = (
        f"This page-number signal is the same underlying issue as {phrase}. It is listed "
        "here only as supporting detail and does not add a new problem to fix."
    )
    return comment, explanation


def _collect_claimed_page_number_keys(
    all_finding_views: Sequence[FindingView],
    finding_details_by_index: Mapping[int, dict[str, str]],
) -> frozenset[tuple[str, int]]:
    """Find (visible_issue_type, page) pairs already reported by a non-P013 rule.

    P013 only detects page-number *candidates*. When another page-numbering rule
    (today, P019) reports a confirmed problem at the same synthetic issue type and
    page, P013's matching candidate finding restates the same defect and should not
    be shown as a second, indistinguishable top-level card.
    """
    claimed: set[tuple[str, int]] = set()
    for index, view in enumerate(all_finding_views):
        if view.category != "page_numbering" or view.rule_id == "P013":
            continue
        details = finding_details_by_index.get(index, {})
        visible_issue_type, is_problem = _classify_visible_page_number_issue(view, details)
        if is_problem and visible_issue_type is not None and view.page is not None:
            claimed.add((visible_issue_type, view.page))
    return frozenset(claimed)


def _apply_page_number_presentation(
    finding: FindingView,
    details: Mapping[str, str],
    *,
    claimed_keys: frozenset[tuple[str, int]] = frozenset(),
) -> tuple[FindingView, bool]:
    if finding.rule_id == "P013" and finding.issue_type == "p013_document_overview":
        return finding, False
    visible_issue_type, is_problem = _classify_visible_page_number_issue(finding, details)
    if (
        finding.rule_id == "P013"
        and visible_issue_type is not None
        and finding.page is not None
        and (visible_issue_type, finding.page) in claimed_keys
    ):
        comment, explanation = _redundant_candidate_comment_and_explanation(
            visible_issue_type, page=finding.page
        )
        return (
            replace(
                finding,
                issue_type="detected_page_number_candidate",
                issue_type_label=humanize_issue_type("detected_page_number_candidate"),
                issue_type_explanation=explain_issue_type("", "detected_page_number_candidate"),
                polished_comment=comment,
                suggested_fix="",
                action_kind="",
                action_label="",
                no_highlight_reason="",
                detailed_explanation=explanation,
            ),
            False,
        )
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
    location_label = page_number_location_label(
        finding.rule_id,
        visible_issue_type,
        details,
        finding.page,
        bbox_label=(
            finding.location_label
            if finding.location_label
            and not finding.location_label.startswith("Page ")
            else ""
        ),
    )
    raw_issue_type = str(details.get("issue_type", "")).strip()
    if finding.rule_id in {"P029", "P037"} and raw_issue_type:
        issue_type_explanation = explain_issue_type(
            finding.rule_id, raw_issue_type, details=dict(details)
        )
        detailed_explanation = build_detailed_explanation(
            rule_id=finding.rule_id,
            issue_type=raw_issue_type,
            details=dict(details),
            page=finding.page,
            has_highlight=finding.has_highlight,
            location_label=location_label,
        )
    else:
        issue_type_explanation = explain_issue_type("", visible_issue_type)
        detailed_explanation = _page_number_detail_text(
            visible_issue_type, page=finding.page
        )
    if not finding.has_highlight and finding.page is not None:
        guidance = build_no_highlight_guidance(
            rule_id=finding.rule_id,
            issue_type=visible_issue_type,
            details=dict(details),
            page=finding.page,
            location_label=location_label,
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
            issue_type_explanation=issue_type_explanation,
            polished_comment=comment,
            suggested_fix=suggested_fix,
            detailed_explanation=detailed_explanation,
            location_label=location_label,
        ),
        is_problem,
    )


def _apply_abstract_indent_presentation(
    finding: FindingView,
    details: Mapping[str, str],
) -> FindingView:
    if finding.rule_id != "P044":
        return finding
    bbox_only = (
        finding.location_label
        if finding.location_label and not finding.location_label.startswith("Page ")
        else ""
    )
    location_label = abstract_indent_location_label(
        finding.issue_type,
        details,
        finding.page,
        bbox_label=bbox_only,
    )
    return replace(finding, location_label=location_label)


def _apply_p012_presentation(
    finding: FindingView,
    details: Mapping[str, str],
    *,
    annotation_count: int,
    representative_bbox: tuple[float, float, float, float] | None,
    page_count: int | None,
    page_size: tuple[float, float] | None,
) -> tuple[FindingView, bool]:
    if not is_p012_finding(finding.rule_id, finding.issue_type):
        return finding, True
    location_label = p012_location_label(finding.page, annotation_count)
    comment = p012_rolled_up_comment(page=finding.page, annotation_count=annotation_count)
    suggested_fix = p012_rolled_up_suggested_fix(annotation_count)
    bbox = representative_bbox if representative_bbox is not None else finding.bbox
    has_highlight = has_visible_highlight(
        bbox,
        page=finding.page,
        page_count=page_count,
        page_size=page_size,
    )
    no_highlight_reason = (
        ""
        if has_highlight
        else build_no_highlight_guidance(
            rule_id=finding.rule_id,
            issue_type=finding.issue_type,
            details=dict(details),
            page=finding.page,
            location_label=location_label,
        )
    )
    return (
        replace(
            finding,
            polished_comment=comment,
            suggested_fix=suggested_fix,
            location_label=location_label,
            bbox=bbox,
            has_highlight=has_highlight,
            action_kind=get_action_kind(has_highlight=has_highlight, page=finding.page),
            action_label=get_action_label(has_highlight=has_highlight, page=finding.page),
            no_highlight_reason=no_highlight_reason,
            detailed_explanation=p012_rolled_up_explanation(
                page=finding.page,
                annotation_count=annotation_count,
                has_highlight=has_highlight,
                location_label=location_label,
            ),
        ),
        True,
    )


def _apply_p012_document_presentation(
    finding: FindingView,
    stats: P012PresentationStats,
) -> tuple[FindingView, bool]:
    if not is_p012_finding(finding.rule_id, finding.issue_type):
        return finding, True
    location_label = p012_document_location_label(stats)
    comment = p012_document_rolled_up_comment(stats)
    suggested_fix = p012_document_suggested_fix()
    return (
        replace(
            finding,
            page=None,
            polished_comment=comment,
            suggested_fix=suggested_fix,
            location_label=location_label,
            bbox=None,
            has_highlight=False,
            action_kind=get_action_kind(has_highlight=False, page=None),
            action_label=get_action_label(has_highlight=False, page=None),
            no_highlight_reason=p012_document_no_highlight_reason(stats),
            detailed_explanation=p012_document_rolled_up_explanation(stats),
        ),
        True,
    )


def _apply_p011_combined_presentation(
    finding: FindingView,
    stats: P011PagePresentationStats,
    *,
    pdf_page_sizes: Sequence[tuple[float, float]] | None = None,
) -> tuple[FindingView, bool]:
    if not is_p011_margin_finding(finding.rule_id, finding.issue_type):
        return finding, True
    location_label = p011_page_location_label(stats.page, stats.sides)
    comment = p011_combined_rolled_up_comment(stats)
    suggested_fix = p011_combined_suggested_fix(stats)
    bbox = None
    if stats.highlight_bboxes:
        if len(stats.highlight_bboxes) == 1:
            bbox = stats.highlight_bboxes[0]
        else:
            bbox = (
                min(box[0] for box in stats.highlight_bboxes),
                min(box[1] for box in stats.highlight_bboxes),
                max(box[2] for box in stats.highlight_bboxes),
                max(box[3] for box in stats.highlight_bboxes),
            )
    page_count = len(pdf_page_sizes) if pdf_page_sizes else None
    page_size = (
        pdf_page_sizes[stats.page - 1]
        if pdf_page_sizes and 1 <= stats.page <= len(pdf_page_sizes)
        else None
    )
    has_highlight = has_visible_highlight(
        bbox,
        page=stats.page,
        page_count=page_count,
        page_size=page_size,
    )
    no_highlight_reason = (
        ""
        if has_highlight
        else p011_combined_no_highlight_reason(stats)
    )
    return (
        replace(
            finding,
            polished_comment=comment,
            suggested_fix=suggested_fix,
            location_label=location_label,
            bbox=bbox if has_highlight else None,
            has_highlight=has_highlight,
            action_kind=get_action_kind(has_highlight=has_highlight, page=stats.page),
            action_label=get_action_label(has_highlight=has_highlight, page=stats.page),
            no_highlight_reason=no_highlight_reason,
            detailed_explanation=p011_combined_rolled_up_explanation(stats),
        ),
        True,
    )


def _apply_p026_document_presentation(
    finding: FindingView,
    stats: P026PatternPresentationStats,
) -> tuple[FindingView, bool]:
    if not is_p026_finding(finding.rule_id, finding.issue_type):
        return finding, True
    representative_page = stats.representative_page
    location_label = p026_document_location_label(stats)
    comment = p026_document_rolled_up_comment(stats)
    suggested_fix = p026_document_suggested_fix(stats)
    return (
        replace(
            finding,
            page=representative_page,
            polished_comment=comment,
            suggested_fix=suggested_fix,
            location_label=location_label,
            bbox=None,
            has_highlight=False,
            action_kind=get_action_kind(has_highlight=False, page=representative_page),
            action_label=get_action_label(has_highlight=False, page=representative_page),
            no_highlight_reason=p026_document_no_highlight_reason(stats),
            detailed_explanation=p026_document_rolled_up_explanation(stats),
        ),
        True,
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
    bbox_only = (
        finding.location_label
        if finding.location_label and not finding.location_label.startswith("Page ")
        else ""
    )
    location_label = margin_location_label(
        details, finding.page, bbox_label=bbox_only
    )
    return (
        replace(
            finding,
            polished_comment=comment,
            suggested_fix=suggested_fix,
            location_label=location_label,
            no_highlight_reason=(
                finding.no_highlight_reason
                if finding.has_highlight
                else build_no_highlight_guidance(
                    rule_id=finding.rule_id,
                    issue_type=finding.issue_type,
                    details=dict(details),
                    page=finding.page,
                    location_label=location_label,
                )
            ),
            detailed_explanation=_margin_detailed_explanation(
                details,
                page=finding.page,
                has_highlight=finding.has_highlight,
                location_label=location_label,
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
    location_label = p026_page_location_label(
        page=finding.page,
        issue_type=finding.issue_type,
        observed_summary=details.get("observed_summary", ""),
        expected=details.get("expected", ""),
    )
    return (
        replace(
            finding,
            polished_comment=comment,
            suggested_fix=suggested_fix,
            location_label=location_label,
            no_highlight_reason=(
                finding.no_highlight_reason
                if finding.has_highlight
                else build_no_highlight_guidance(
                    rule_id=finding.rule_id,
                    issue_type=finding.issue_type,
                    details=dict(details),
                    page=finding.page,
                    location_label=location_label,
                )
            ),
            detailed_explanation=_font_detailed_explanation(
                details,
                issue_type=finding.issue_type,
                page=finding.page,
                has_highlight=finding.has_highlight,
                location_label=location_label,
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
    """Short main-card wording for P020 title-case findings."""
    if finding.rule_id != "P020" or finding.issue_type != "possible_title_capitalization_issue":
        return finding, True
    finding = replace(finding, issue_type_label=_title_case_issue_label(details))
    flagged_word = details.get("flagged_word", "").strip()
    corrected_word = details.get("corrected_word", "").strip()
    if not flagged_word or not corrected_word:
        return finding, True
    comment = p020_short_likely_problem(flagged_word, corrected_word)
    suggested_fix = p020_short_suggested_fix(
        flagged_word,
        corrected_word,
        details.get("line_preview", ""),
    )
    return replace(finding, polished_comment=comment, suggested_fix=suggested_fix), True


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
    """Short main-card wording for P036 inter-entry spacing findings."""
    if finding.rule_id != "P036" or finding.issue_type not in _P036_SPACING_ISSUE_TYPES:
        return finding, True
    comment = p036_short_likely_problem(
        details.get("previous_entry_preview", ""),
        details.get("next_entry_preview", ""),
    )
    suggested_fix = p036_short_suggested_fix()
    return replace(finding, polished_comment=comment, suggested_fix=suggested_fix), True


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
    suggested_fix = finding.suggested_fix
    if finding.issue_type == "figure_caption_not_below_body":
        if float_number:
            suggested_fix = (
                f"Place the Figure {float_number} caption below the figure body. "
                "Keep the figure image and its caption together within the text area."
            )
        else:
            suggested_fix = (
                "Place the figure caption below the figure body. Keep the figure image "
                "and its caption together within the text area."
            )
    elif finding.issue_type == "table_caption_not_above_body" and float_number:
        suggested_fix = (
            f"Place the Table {float_number} caption above the table body. "
            "Keep the caption and table rows together within the text area."
        )
    return replace(finding, polished_comment=comment, suggested_fix=suggested_fix), True


def _apply_digital_commons_wrapper_presentation(
    finding: FindingView,
    details: Mapping[str, str],
    metadata: Mapping[str, Any],
) -> FindingView:
    wrapper_pages = sorted(_parse_wrapper_pages(metadata) or _parse_wrapper_pages(details))
    if not wrapper_pages:
        return finding
    page_count = int(
        str(
            details.get("digital_commons_wrapper_page_count")
            or metadata.get("digital_commons_wrapper_page_count")
            or len(wrapper_pages)
        )
    )
    pages_compact = str(
        details.get("digital_commons_wrapper_pages_compact")
        or metadata.get("digital_commons_wrapper_pages_compact")
        or ""
    ).strip()
    first_page = wrapper_pages[0]
    return replace(
        finding,
        polished_comment=digital_commons_advisory_comment(
            page_count=page_count,
            pages_compact=pages_compact,
        ),
        suggested_fix=digital_commons_advisory_suggested_fix(),
        location_label=digital_commons_advisory_location_label(
            first_page=first_page,
            page_count=page_count,
        ),
        issue_type_label="Digital Commons wrapper pages detected",
    )


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


_P018_SUGGESTED_FIXES: dict[str, str] = {
    "misaligned_page_number_column": (
        "Align the affected entry's page number with the dominant right-hand column "
        "used by nearby entries on this list page."
    ),
    "missing_page_number": (
        "Add the missing trailing page number to the affected entry."
    ),
    "inconsistent_leader_dots": (
        "Make the leader-dot spacing before the page number match the style used by "
        "nearby entries on this list page."
    ),
    "inconsistent_hierarchy_indent": (
        "Align the affected entry's left indent with other entries at the same "
        "hierarchy level on this list page."
    ),
}


def _apply_toc_alignment_presentation(
    finding: FindingView,
    details: Mapping[str, str],
) -> tuple[FindingView, bool]:
    """Short main-card wording for P018 TOC/list alignment findings."""
    if finding.rule_id != "P018":
        return finding, True
    preview = sanitize_toc_list_entry_preview(details.get("affected_entry_preview", ""))
    if (
        finding.issue_type == "missing_page_number"
        and preview
        and is_toc_structural_column_label(preview)
    ):
        return finding, False
    comment = p018_short_likely_problem(finding.issue_type)
    suggested_fix = p018_short_suggested_fix(finding.issue_type, finding.suggested_fix)
    page_label = str(finding.page) if finding.page is not None else None
    section_label = _section_label_from_details(details) or "Table of Contents"
    location_label = finding.location_label
    if preview and page_label is not None:
        location_label = (
            f"Page {page_label} — {section_label} {p018_entry_location_suffix(preview)}"
        )
    return replace(
        finding,
        polished_comment=comment,
        suggested_fix=suggested_fix,
        location_label=location_label,
    ), True


def _p046_count_clause(details: Mapping[str, str]) -> str:
    count = details.get("affected_entry_count", "").strip()
    if not count.isdigit() or int(count) <= 0:
        return ""
    noun = "entry" if count == "1" else "entries"
    return f" ({count} {noun} affected)"


def _apply_lot_lof_alignment_presentation(
    finding: FindingView,
    details: Mapping[str, str],
) -> tuple[FindingView, bool]:
    """Surface P046's affected-entry count without changing the grouping key.

    Overrides only the display comment after grouping has already been
    computed upstream (on the count-independent comment).
    """
    if finding.rule_id != "P046":
        return finding, True
    count_clause = _p046_count_clause(details)
    if not count_clause:
        return finding, True
    comment = finding.polished_comment.rstrip()
    if comment.endswith("."):
        comment = f"{comment[:-1]}{count_clause}."
    else:
        comment = f"{comment}{count_clause}"
    preview = details.get("affected_entry_preview", "").strip()
    if preview:
        comment = f"{comment.rstrip('.')}. Affected entry: '{preview}'."
    suggested_fix = (
        "Align the affected entry's left indent with the dominant entry-number "
        "column used by nearby entries on this list page."
    )
    return replace(finding, polished_comment=comment, suggested_fix=suggested_fix), True


_P014_ATTRIBUTE_LABELS: tuple[tuple[str, str], ...] = (
    ("centered", "centered"),
    ("near_top", "near the top of the page"),
    ("bold", "bold"),
    ("all_caps", "in all capital letters"),
)


_P014_HEADING_DISPLAY_NAMES: dict[str, str] = {
    "ABSTRACT": "Abstract",
    "APPROVAL PAGE": "Approval Page",
    "BIOGRAPHICAL SKETCH": "Biographical Sketch",
    "ACKNOWLEDGEMENTS": "Acknowledgements",
    "TABLE OF CONTENTS": "Table of Contents",
    "LIST OF TABLES": "List of Tables",
    "LIST OF FIGURES": "List of Figures",
}


def _p014_heading_display_name(heading: str) -> str:
    normalized = heading.strip().upper()
    return _P014_HEADING_DISPLAY_NAMES.get(normalized, heading.strip().title())


def _p014_issue_type_label(heading: str, failed_labels: list[str]) -> str:
    display_name = _p014_heading_display_name(heading) if heading else ""
    if failed_labels == ["centered"]:
        return "Front-matter heading may not be centered"
    if display_name:
        return f"{display_name} heading alignment issue"
    return "Front-matter heading alignment issue"


def _apply_named_heading_presentation(
    finding: FindingView,
    details: Mapping[str, str],
) -> tuple[FindingView, bool]:
    """Rewrite P014 findings with student-facing titles and attribute-specific wording."""
    if finding.rule_id != "P014":
        return finding, True
    page_label = str(finding.page) if finding.page is not None else "this page"
    heading = details.get("heading", "").strip()
    heading_clause = f' "{heading}"' if heading else ""
    failed_labels = [
        label
        for key, label in _P014_ATTRIBUTE_LABELS
        if details.get(key, "").strip().lower() == "false"
    ]
    centering_confidence = details.get("centering_confidence", "").strip().lower()
    only_centering_failed = failed_labels == ["centered"]

    if failed_labels:
        if only_centering_failed and centering_confidence == "borderline":
            comment = (
                f'The auditor detected the heading{heading_clause} as possibly off-center. '
                f'Please check whether "{heading}" is centered within the required text area. '
                "NJIT expects named front-matter headings to be centered near the top of the "
                "page, in bold, and in all capital letters."
            )
            fix = (
                f'Center the "{heading}" heading within the text area. '
                "Keep it bold and in all capital letters."
            )
        elif only_centering_failed:
            comment = (
                f'The front-matter heading{heading_clause} appears off-center. '
                "NJIT expects named front-matter headings to be centered near the top of the "
                "page, in bold, and in all capital letters."
            )
            fix = (
                f'Center the "{heading}" heading within the text area. '
                "Keep it bold and in all capital letters."
            )
        else:
            issue_clause = ", ".join(f"not {label}" for label in failed_labels)
            comment = (
                f"The front-matter heading{heading_clause} on page {page_label} is "
                f"{issue_clause}. NJIT requires named front-matter headings to be centered "
                "near the top of the page, in bold, and in all capital letters."
            )
            fix = f"Make this heading {', '.join(failed_labels)}."
    else:
        comment = (
            f"The front-matter heading{heading_clause} on page {page_label} does not match "
            "NJIT's expected heading style. NJIT requires named front-matter headings to be "
            "centered near the top of the page, in bold, and in all capital letters."
        )
        fix = "Place this heading centered near the top in bold all-caps."

    issue_type_label = _p014_issue_type_label(heading, failed_labels)
    issue_type = details.get("issue_type", "").strip() or "frontmatter_heading_layout_issue"
    no_highlight_reason = finding.no_highlight_reason
    if not finding.has_highlight and finding.page is not None:
        no_highlight_reason = (
            "This is a page-level alignment review. Compare the heading position against "
            "the center of the required text area on the opened PDF page."
        )
    detailed_explanation = finding.detailed_explanation
    if only_centering_failed and not finding.has_highlight:
        detailed_explanation = (
            f"{detailed_explanation} "
            "Compare the heading against the horizontal center of the required text area."
        ).strip()

    return (
        replace(
            finding,
            issue_type=issue_type,
            issue_type_label=issue_type_label,
            polished_comment=comment,
            suggested_fix=fix,
            no_highlight_reason=no_highlight_reason,
            detailed_explanation=detailed_explanation,
        ),
        True,
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

    claimed_page_number_keys = _collect_claimed_page_number_keys(
        all_finding_views, finding_details_by_index
    )

    p012_count_by_page: dict[int, int] = {}
    p012_rep_bbox_by_page: dict[int, tuple[float, float, float, float] | None] = {}
    if isinstance(raw_findings, list):
        for item in raw_findings:
            if not isinstance(item, Mapping):
                continue
            rule_id = str(item.get("rule_id", ""))
            details_raw = item.get("details", {})
            details = (
                {str(k): str(v) for k, v in details_raw.items()}
                if isinstance(details_raw, Mapping)
                else {}
            )
            if not is_p012_finding(rule_id, details.get("issue_type", "").strip()):
                continue
            page_raw = item.get("page")
            if page_raw is None:
                continue
            try:
                page = int(page_raw)
            except (TypeError, ValueError):
                continue
            p012_count_by_page[page] = p012_count_by_page.get(page, 0) + 1
            bbox = _parse_bbox_from_details(details)
            if page not in p012_rep_bbox_by_page:
                p012_rep_bbox_by_page[page] = bbox
            elif p012_rep_bbox_by_page[page] is None and bbox is not None:
                p012_rep_bbox_by_page[page] = bbox

    page_count = len(pdf_page_sizes) if pdf_page_sizes else None
    p012_display_state = init_p012_display_state(
        p012_count_by_page,
        find_p012_summary_anchor_index(all_finding_views, p012_count_by_page),
    )
    p026_display_state = init_p026_display_state(
        collect_p026_pattern_pages_from_serialized(
            [item for item in raw_findings if isinstance(item, Mapping)]
        )
        if isinstance(raw_findings, list)
        else {},
    )
    p011_display_state = init_p011_display_state(
        collect_p011_margin_pages_from_serialized(
            [item for item in raw_findings if isinstance(item, Mapping)]
        )
        if isinstance(raw_findings, list)
        else {},
    )

    finding_views: list[FindingView] = []
    inventory_findings: list[FindingView] = []
    visible_view_by_index: dict[int, FindingView] = {}
    visible_indexes: set[int] = set()
    p020_display_seen: set[tuple] = set()
    page_number_display_seen: set[tuple] = set()
    grouped_display_seen: set[tuple] = set()
    wrapper_pages = _parse_wrapper_pages(metadata)
    for index, finding_view in enumerate(all_finding_views):
        details = finding_details_by_index.get(index, {})
        visible_view = finding_view
        is_problem = True
        if is_layout_warning_suppressed_on_wrapper_page(
            visible_view.rule_id,
            visible_view.page,
            wrapper_pages,
        ):
            is_problem = False
        elif visible_view.category == "page_numbering":
            visible_view, is_problem = _apply_page_number_presentation(
                visible_view, details, claimed_keys=claimed_page_number_keys
            )
            if (
                is_problem
                and visible_view.issue_type
                and not consume_page_number_display_slot(
                    visible_view.rule_id,
                    visible_view.issue_type,
                    details,
                    page_number_display_seen,
                    page=visible_view.page,
                )
            ):
                is_problem = False
        elif visible_view.rule_id == "P011":
            page_stats = (
                p011_display_state.page_stats.get(visible_view.page)
                if visible_view.page is not None
                else None
            )
            if (
                visible_view.page is not None
                and visible_view.page in p011_display_state.multi_side_pages
                and page_stats is not None
            ):
                if index != p011_display_state.page_anchors.get(visible_view.page):
                    is_problem = False
                else:
                    visible_view, is_problem = _apply_p011_combined_presentation(
                        visible_view,
                        page_stats,
                        pdf_page_sizes=pdf_page_sizes,
                    )
            else:
                visible_view, is_problem = _apply_margin_presentation(visible_view, details)
        elif visible_view.rule_id == "P026":
            pattern_key = p026_pattern_key(visible_view.issue_type, details)
            pattern_stats = p026_display_state.pattern_stats.get(pattern_key)
            if (
                pattern_key in p026_display_state.document_mode_patterns
                and pattern_stats is not None
            ):
                if index != p026_display_state.pattern_anchors.get(pattern_key):
                    is_problem = False
                else:
                    visible_view, is_problem = _apply_p026_document_presentation(
                        visible_view,
                        pattern_stats,
                    )
            else:
                visible_view, is_problem = _apply_font_presentation(visible_view, details)
        elif (
            visible_view.rule_id == "P025"
            and visible_view.issue_type == "digital_commons_wrapper_pages_detected"
        ):
            visible_view = _apply_digital_commons_wrapper_presentation(
                visible_view,
                details,
                metadata,
            )
        elif visible_view.rule_id == "P020":
            visible_view, is_problem = _apply_title_case_presentation(visible_view, details)
            if is_problem and not consume_p020_display_slot(
                details,
                p020_display_seen,
                page=visible_view.page,
            ):
                is_problem = False
        elif visible_view.rule_id == "P036":
            visible_view, is_problem = _apply_spacing_presentation(visible_view, details)
        elif visible_view.rule_id == "P035":
            visible_view, is_problem = _apply_float_layout_presentation(visible_view, details)
        elif visible_view.rule_id == "P040":
            visible_view, is_problem = _apply_lof_punctuation_presentation(visible_view, details)
        elif visible_view.rule_id == "P018":
            visible_view, is_problem = _apply_toc_alignment_presentation(visible_view, details)
        elif visible_view.rule_id == "P046":
            visible_view, is_problem = _apply_lot_lof_alignment_presentation(visible_view, details)
        elif visible_view.rule_id == "P014":
            visible_view, is_problem = _apply_named_heading_presentation(visible_view, details)
        elif visible_view.rule_id == "P044":
            visible_view = _apply_abstract_indent_presentation(visible_view, details)
        elif is_p012_finding(visible_view.rule_id, visible_view.issue_type):
            if (
                p012_display_state.document_summary_mode
                and p012_display_state.stats is not None
            ):
                if index != p012_display_state.summary_anchor_index:
                    is_problem = False
                else:
                    visible_view, is_problem = _apply_p012_document_presentation(
                        visible_view,
                        p012_display_state.stats,
                    )
            else:
                page_size = (
                    pdf_page_sizes[visible_view.page - 1]
                    if pdf_page_sizes
                    and visible_view.page is not None
                    and 1 <= visible_view.page <= len(pdf_page_sizes)
                    else None
                )
                annotation_count = (
                    p012_count_by_page.get(visible_view.page, 1)
                    if visible_view.page is not None
                    else 1
                )
                representative_bbox = (
                    p012_rep_bbox_by_page.get(visible_view.page)
                    if visible_view.page is not None
                    else None
                )
                visible_view, is_problem = _apply_p012_presentation(
                    visible_view,
                    details,
                    annotation_count=annotation_count,
                    representative_bbox=representative_bbox,
                    page_count=page_count,
                    page_size=page_size,
                )

        if (
            is_problem
            and visible_view.rule_id in {"P024", "P036", "P044", "P046"}
            and not consume_grouped_finding_display_slot(
                visible_view.rule_id,
                visible_view.issue_type,
                details,
                grouped_display_seen,
                page=visible_view.page,
            )
        ):
            is_problem = False
        if (
            is_problem
            and is_p011_margin_finding(visible_view.rule_id, visible_view.issue_type)
            and not consume_p011_finding_visibility(
                page=visible_view.page,
                side=details.get("side", ""),
                finding_index=index,
                state=p011_display_state,
            )
        ):
            is_problem = False
        if (
            is_problem
            and is_p012_finding(visible_view.rule_id, visible_view.issue_type)
            and not consume_p012_finding_visibility(
                page=visible_view.page,
                finding_index=index,
                state=p012_display_state,
            )
        ):
            is_problem = False
        if (
            is_problem
            and is_p026_finding(visible_view.rule_id, visible_view.issue_type)
            and not consume_p026_finding_visibility(
                pattern_key=p026_pattern_key(visible_view.issue_type, details),
                page=visible_view.page,
                finding_index=index,
                state=p026_display_state,
            )
        ):
            is_problem = False
        if is_problem:
            visible_view = _finalize_finding_display(visible_view)
            visible_indexes.add(index)
            visible_view_by_index[index] = visible_view
            finding_views.append(visible_view)
            finding_page = visible_view.page
            if finding_page is not None:
                pages.add(finding_page)
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

    inventory_counts_by_rule: dict[str, int] = {}
    for inventory_finding in inventory_findings:
        inventory_counts_by_rule[inventory_finding.rule_id] = (
            inventory_counts_by_rule.get(inventory_finding.rule_id, 0) + 1
        )

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
            page_display_values = sorted(
                {f.page_display_label for f in individual_views if f.page_display_label}
            )
            location_values = sorted(
                {f.location_label for f in individual_views if f.location_label}
            )
            raw_affected_label = str(entry.get("affected_label", "")).strip()
            raw_affected_compact = str(entry.get("affected_compact", "")).strip()
            affected_compact = raw_affected_compact or (
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
                    affected_label=raw_affected_label or ("Pages" if page_values else "Locations"),
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
                    page_display_tokens=page_display_values,
                    location_tokens=location_values,
                    individual_findings=individual_views,
                    detailed_explanation=first.detailed_explanation,
                    has_any_highlight=has_any_highlight,
                    issue_type_label=first.issue_type_label,
                    issue_type_explanation=first.issue_type_explanation,
                    pattern_note=_high_volume_pattern_note(
                        group_rule_id,
                        group_issue_type,
                        len(individual_views),
                        "Pages" if page_values else "Locations",
                        affected_compact,
                    ),
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
                    finding.page_display_label
                    or finding.location_label
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
                page_display_tokens=(
                    [finding.page_display_label] if finding.page_display_label else []
                ),
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
            for panel in _build_triage_panels(grouped, counts_by_rule, inventory_counts_by_rule)
            if panel.rule_id in counts_by_rule
            or (panel.rule_id == "P013" and panel.raw_finding_count > 0)
        ],
        grouped_problems=grouped_problem_views,
        findings=finding_views,
        inventory_findings=inventory_findings,
    )


def report_view_to_dict(view: ReportView) -> dict[str, Any]:
    """Serialize a ReportView for templates and in-memory job state."""
    return asdict(view)
