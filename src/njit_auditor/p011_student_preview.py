"""Privacy-safe P011 page-level rollup when multiple margin sides fail on one page."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, MutableSet, Sequence
from dataclasses import dataclass, field

from njit_auditor.high_volume_student_preview import _MARGIN_SIDE_LABELS

P011_RULE_ID = "P011"
P011_ISSUE_TYPE = "margin_boundary_violation"


def is_p011_margin_finding(rule_id: str, issue_type: str) -> bool:
    return rule_id == P011_RULE_ID and issue_type == P011_ISSUE_TYPE


def _side_short_label(side: str) -> str:
    return _MARGIN_SIDE_LABELS.get(side.strip(), side.replace("_margin", "").strip() or "margin")


def _join_margin_labels(labels: Sequence[str]) -> str:
    cleaned = [label for label in labels if label]
    if not cleaned:
        return "page margins"
    if len(cleaned) == 1:
        return f"{cleaned[0]} margin"
    if len(cleaned) == 2:
        return f"{cleaned[0]} and {cleaned[1]} margins"
    return f"{', '.join(cleaned[:-1])}, and {cleaned[-1]} margins"


@dataclass(frozen=True)
class P011SideStats:
    """Per-side overflow/line-count detail for one margin-boundary finding."""

    side: str
    worst_overflow_pt: float
    affected_line_count: int


@dataclass(frozen=True)
class P011PagePresentationStats:
    page: int
    sides: tuple[str, ...]
    raw_finding_count: int
    highlight_bboxes: tuple[tuple[float, float, float, float], ...] = ()
    side_stats: tuple[P011SideStats, ...] = ()


@dataclass
class P011DisplayState:
    page_stats: dict[int, P011PagePresentationStats] = field(default_factory=dict)
    multi_side_pages: set[int] = field(default_factory=set)
    page_anchors: dict[int, int] = field(default_factory=dict)
    multi_side_shown: set[int] = field(default_factory=set)
    single_side_seen: MutableSet[tuple[int, str]] = field(default_factory=set)


def p011_page_location_label(page: int, sides: Sequence[str]) -> str:
    short_labels = sorted({_side_short_label(side) for side in sides if side.strip()})
    if not short_labels:
        return f"Page {page} — margin boundary"
    if len(short_labels) == 1:
        return f"Page {page} — {short_labels[0]} margin"
    return f"Page {page} — {_join_margin_labels(short_labels)}"


def _side_breakdown_phrase(side_stats: Sequence[P011SideStats]) -> str:
    """Return a per-side "side (~X pt over, N line(s))" breakdown, or "" if unavailable.

    This replaces vague "N separate margin-boundary warnings" phrasing with the
    exact overflow amount and affected-line count for each side, so a mixed-side
    page (e.g. top + right) reads as clearly separated evidence per side rather
    than one undifferentiated count.
    """
    if not side_stats:
        return ""
    parts = []
    for stat in sorted(side_stats, key=lambda s: _side_short_label(s.side)):
        label = _side_short_label(stat.side)
        line_word = "line" if stat.affected_line_count == 1 else "lines"
        parts.append(
            f"{label} margin (~{stat.worst_overflow_pt:.1f} pt over, "
            f"{stat.affected_line_count} {line_word} affected)"
        )
    return "Side detail: " + "; ".join(parts) + "."


def p011_combined_rolled_up_comment(stats: P011PagePresentationStats) -> str:
    side_phrase = _join_margin_labels([_side_short_label(side) for side in stats.sides])
    base = (
        f"Likely problem: Page {stats.page} has content that may be too close to the "
        f"{side_phrase}. The auditor flagged {stats.raw_finding_count} separate "
        "margin-boundary warnings on this page. NJIT's margin rule is strict: no text, "
        "tables, or figures should cross a required margin boundary, even by a small "
        "amount. Review the highlighted areas if available, or inspect the full page "
        "layout including headers, footers, page numbers, tables, figures, captions, "
        "and long lines."
    )
    breakdown = _side_breakdown_phrase(stats.side_stats)
    return f"{base} {breakdown}" if breakdown else base


def p011_combined_suggested_fix(stats: P011PagePresentationStats) -> str:
    side_phrase = _join_margin_labels([_side_short_label(side) for side in stats.sides])
    return (
        f"Check the page header, page number, tables, figures, captions, and any long "
        f"lines on page {stats.page}. Move any content that crosses the required "
        f"{side_phrase} back inside the allowed page area."
    )


def p011_combined_rolled_up_explanation(stats: P011PagePresentationStats) -> str:
    location = p011_page_location_label(stats.page, stats.sides)
    if stats.highlight_bboxes:
        highlight_note = (
            "If highlights are shown, each one marks one affected margin side on this page."
        )
    else:
        highlight_note = (
            "No exact text span could be highlighted for every affected side, so this is "
            "a page-level layout review."
        )
    breakdown = _side_breakdown_phrase(stats.side_stats)
    breakdown_clause = f" {breakdown}" if breakdown else ""
    return (
        f"Observed: {location}. The auditor flagged {stats.raw_finding_count} separate "
        "margin-boundary warnings on this page because text crosses more than one required "
        "margin side. Expected: body content should stay inside NJIT page margins on every "
        f"side, even by a small amount. What to check or fix: inspect the whole page, not "
        f"just one area. {highlight_note}{breakdown_clause}"
    )


def p011_combined_no_highlight_reason(stats: P011PagePresentationStats) -> str:
    if stats.highlight_bboxes:
        return ""
    return (
        f"This page-level margin summary covers {stats.raw_finding_count} affected sides. "
        "Open the original PDF on this page and review every margin side listed in the "
        "summary."
    )


@dataclass(frozen=True)
class P011SerializedEntry:
    """One P011 finding's presentation-relevant fields, extracted from JSON."""

    index: int
    side: str
    bbox: tuple[float, float, float, float] | None
    highlight_bboxes: tuple[tuple[float, float, float, float], ...]
    worst_overflow_pt: float
    affected_line_count: int


def _parse_bbox_field(raw: str) -> tuple[float, float, float, float] | None:
    if not raw:
        return None
    parts = [part.strip() for part in raw.split(",")]
    if len(parts) != 4:
        return None
    try:
        return tuple(float(part) for part in parts)  # type: ignore[return-value]
    except ValueError:
        return None


def collect_p011_margin_pages_from_serialized(
    serialized_findings: Sequence[Mapping[str, object]],
) -> dict[int, list[P011SerializedEntry]]:
    by_page: dict[int, list[P011SerializedEntry]] = defaultdict(list)
    for index, finding in enumerate(serialized_findings):
        rule_id = str(finding.get("rule_id", "")).strip()
        if rule_id != P011_RULE_ID:
            continue
        details_raw = finding.get("details", {})
        details = details_raw if isinstance(details_raw, Mapping) else {}
        issue_type = str(details.get("issue_type", "")).strip()
        if issue_type != P011_ISSUE_TYPE:
            continue
        page_raw = finding.get("page")
        if page_raw is None:
            continue
        try:
            page_int = int(str(page_raw))
        except ValueError:
            continue
        side = str(details.get("side", "")).strip()
        bbox = _parse_bbox_field(str(details.get("bbox", "")).strip())
        precise_boxes = tuple(
            box
            for chunk in str(details.get("highlight_bboxes", "")).strip().split("|")
            if (box := _parse_bbox_field(chunk.strip())) is not None
        )
        guide_box = _parse_bbox_field(str(details.get("margin_boundary_bbox", "")).strip())
        entry_boxes = precise_boxes + ((guide_box,) if guide_box is not None else ())
        try:
            worst_overflow_pt = float(str(details.get("worst_overflow_pt", "0")).strip())
        except ValueError:
            worst_overflow_pt = 0.0
        try:
            affected_line_count = int(str(details.get("affected_line_count", "0")).strip())
        except ValueError:
            affected_line_count = 0
        by_page[page_int].append(
            P011SerializedEntry(
                index=index,
                side=side,
                bbox=bbox,
                highlight_bboxes=entry_boxes,
                worst_overflow_pt=worst_overflow_pt,
                affected_line_count=affected_line_count,
            )
        )
    return dict(by_page)


def init_p011_display_state(
    page_entries: Mapping[int, Sequence[P011SerializedEntry]],
) -> P011DisplayState:
    state = P011DisplayState()
    for page, entries in page_entries.items():
        sides = tuple(sorted({entry.side for entry in entries if entry.side}))
        highlight_bboxes = tuple(
            box
            for entry in entries
            for box in (entry.highlight_bboxes or ((entry.bbox,) if entry.bbox else ()))
        )
        side_stats = tuple(
            P011SideStats(
                side=entry.side,
                worst_overflow_pt=entry.worst_overflow_pt,
                affected_line_count=entry.affected_line_count,
            )
            for entry in entries
            if entry.side
        )
        stats = P011PagePresentationStats(
            page=page,
            sides=sides,
            raw_finding_count=len(entries),
            highlight_bboxes=highlight_bboxes,
            side_stats=side_stats,
        )
        state.page_stats[page] = stats
        if len(entries) > 1:
            state.multi_side_pages.add(page)
            anchor_index = min(entry.index for entry in entries)
            state.page_anchors[page] = anchor_index
    return state


def consume_p011_finding_visibility(
    *,
    page: int | None,
    side: str,
    finding_index: int,
    state: P011DisplayState,
) -> bool:
    if page is None:
        return True
    if page in state.multi_side_pages:
        if page in state.multi_side_shown:
            return False
        if finding_index != state.page_anchors.get(page):
            return False
        state.multi_side_shown.add(page)
        return True
    token = (page, side.strip())
    if token in state.single_side_seen:
        return False
    state.single_side_seen.add(token)
    return True
