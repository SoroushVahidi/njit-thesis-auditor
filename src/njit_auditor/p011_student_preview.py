"""Privacy-safe P011 page-level rollup when multiple margin sides fail on one page."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, MutableSet, Sequence
from dataclasses import dataclass, field

from njit_auditor.high_volume_student_preview import _MARGIN_SIDE_LABELS
from njit_auditor.polished_comments import REVIEW_PREFIX

P011_RULE_ID = "P011"
P011_ISSUE_TYPE = "margin_boundary_violation"


def is_p011_margin_finding(rule_id: str, issue_type: str) -> bool:
    return rule_id == P011_RULE_ID and issue_type == P011_ISSUE_TYPE


def _side_short_label(side: str) -> str:
    return _MARGIN_SIDE_LABELS.get(side.strip(), side.replace("_margin", "").strip() or "margin")


@dataclass(frozen=True)
class P011PagePresentationStats:
    page: int
    sides: tuple[str, ...]
    raw_finding_count: int


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
    if len(short_labels) == 2:
        return f"Page {page} — {short_labels[0]} and {short_labels[1]} margins"
    joined = ", ".join(short_labels[:-1])
    return f"Page {page} — {joined}, and {short_labels[-1]} margins"


def p011_combined_rolled_up_comment(stats: P011PagePresentationStats) -> str:
    side_phrase = p011_page_location_label(stats.page, stats.sides).split(" — ", 1)[-1]
    body = (
        f"Likely problem: Page {stats.page} has {stats.raw_finding_count} margin-boundary "
        f"issues affecting the {side_phrase}. Text on this page appears too close to or "
        "beyond more than one required margin. Review the whole page layout, including "
        "tables, figures, long lines, headers, and footers, then correct each affected side."
    )
    return f"{REVIEW_PREFIX} {body}".strip()


def p011_combined_suggested_fix(stats: P011PagePresentationStats) -> str:
    sides = ", ".join(_side_short_label(side) for side in stats.sides)
    return (
        f"Move overflowing content back inside the required {sides} margins on page "
        f"{stats.page}, then re-export and re-run the auditor."
    )


def p011_combined_rolled_up_explanation(stats: P011PagePresentationStats) -> str:
    location = p011_page_location_label(stats.page, stats.sides)
    return (
        f"Observed: {location}. The auditor flagged {stats.raw_finding_count} separate "
        "margin-boundary warnings on this page because text crosses more than one required "
        "margin side. Expected: body content should stay inside NJIT page margins on every "
        "side. What to check or fix: inspect the whole page, not just one highlight. If a "
        "highlight is shown, it is representative of one affected side only."
    )


def p011_combined_no_highlight_reason(stats: P011PagePresentationStats) -> str:
    return (
        f"This page-level margin summary covers {stats.raw_finding_count} affected sides. "
        "Open the original PDF on this page and review every margin side listed in the "
        "summary."
    )


def collect_p011_margin_pages_from_serialized(
    serialized_findings: Sequence[Mapping[str, object]],
) -> dict[int, list[tuple[int, str]]]:
    by_page: dict[int, list[tuple[int, str]]] = defaultdict(list)
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
        by_page[page_int].append((index, side))
    return dict(by_page)


def init_p011_display_state(
    page_entries: Mapping[int, Sequence[tuple[int, str]]],
) -> P011DisplayState:
    state = P011DisplayState()
    for page, entries in page_entries.items():
        sides = tuple(sorted({side for _, side in entries if side}))
        stats = P011PagePresentationStats(
            page=page,
            sides=sides,
            raw_finding_count=len(entries),
        )
        state.page_stats[page] = stats
        if len(entries) > 1:
            state.multi_side_pages.add(page)
            anchor_index = min(entries, key=lambda item: item[0])[0]
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
