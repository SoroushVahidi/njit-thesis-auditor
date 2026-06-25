"""Privacy-safe P026 page-level and pattern-level rollup for body-font warnings."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, MutableSet, Sequence
from dataclasses import dataclass, field

from njit_auditor.polished_comments import REVIEW_PREFIX

P026_RULE_ID = "P026"
P026_FAMILY_ISSUE_TYPE = "possible_body_font_family_issue"
P026_SIZE_ISSUE_TYPE = "possible_body_font_size_issue"
P026_ISSUE_TYPES = frozenset({P026_FAMILY_ISSUE_TYPE, P026_SIZE_ISSUE_TYPE})

# Presentation-only thresholds (not detector thresholds).
P026_DOCUMENT_SUMMARY_MIN_AFFECTED_PAGES = 11
P026_DOCUMENT_SUMMARY_MIN_RAW_FINDINGS = 21


def is_p026_finding(rule_id: str, issue_type: str) -> bool:
    return rule_id == P026_RULE_ID and issue_type in P026_ISSUE_TYPES


def p026_pattern_key(issue_type: str, details: Mapping[str, str]) -> tuple[str, str, str]:
    """Build a presentation rollup key from issue type and safe metadata fields."""
    return (
        issue_type.strip(),
        details.get("observed_summary", "").strip(),
        details.get("expected", "").strip(),
    )


def should_use_p026_document_summary(
    affected_page_count: int,
    raw_finding_count: int,
) -> bool:
    """Return True when a repeated P026 pattern should collapse to one document card."""
    return (
        affected_page_count >= P026_DOCUMENT_SUMMARY_MIN_AFFECTED_PAGES
        or raw_finding_count >= P026_DOCUMENT_SUMMARY_MIN_RAW_FINDINGS
    )


@dataclass(frozen=True)
class P026PatternPresentationStats:
    issue_type: str
    observed_summary: str
    expected: str
    raw_finding_count: int
    affected_page_count: int
    pages_compact: str
    representative_page: int | None


@dataclass
class P026DisplayState:
    """Mutable presentation-layer visibility state for P026 findings."""

    pattern_stats: dict[tuple[str, str, str], P026PatternPresentationStats] = field(
        default_factory=dict
    )
    document_mode_patterns: set[tuple[str, str, str]] = field(default_factory=set)
    pattern_anchors: dict[tuple[str, str, str], int] = field(default_factory=dict)
    pattern_document_shown: set[tuple[str, str, str]] = field(default_factory=set)
    page_pattern_seen: MutableSet[tuple[tuple[str, str, str], str]] = field(
        default_factory=set
    )


def _safe_observed_phrase(observed_summary: str) -> str:
    observed = observed_summary.strip()
    if not observed:
        return ""
    if len(observed) > 60:
        return f"{observed[:57]}..."
    return observed


def _expected_family_phrase(expected: str) -> str:
    cleaned = expected.strip()
    if cleaned:
        return cleaned
    return "Times New Roman or an accepted equivalent"


def _expected_size_phrase(expected: str) -> str:
    cleaned = expected.strip()
    if cleaned:
        return cleaned
    return "12pt"


def build_p026_pattern_presentation_stats(
    pattern_key: tuple[str, str, str],
    pages: Sequence[int],
) -> P026PatternPresentationStats:
    from njit_auditor.report_outputs import compact_page_list

    issue_type, observed_summary, expected = pattern_key
    sorted_pages = sorted(set(pages))
    return P026PatternPresentationStats(
        issue_type=issue_type,
        observed_summary=observed_summary,
        expected=expected,
        raw_finding_count=len(sorted_pages),
        affected_page_count=len(sorted_pages),
        pages_compact=compact_page_list(sorted_pages),
        representative_page=sorted_pages[0] if sorted_pages else None,
    )


def collect_p026_pattern_pages(
    findings: Sequence[object],
    *,
    rule_id_attr: str = "rule_id",
    issue_type_attr: str = "issue_type",
    page_attr: str = "page",
    details_attr: str = "details",
) -> dict[tuple[str, str, str], list[tuple[int, int]]]:
    by_pattern: dict[tuple[str, str, str], list[tuple[int, int]]] = defaultdict(list)
    for index, finding in enumerate(findings):
        rule_id = str(getattr(finding, rule_id_attr, "")).strip()
        if rule_id != P026_RULE_ID:
            continue
        issue_type = str(getattr(finding, issue_type_attr, "")).strip()
        details_raw = getattr(finding, details_attr, {})
        details = details_raw if isinstance(details_raw, Mapping) else {}
        if not issue_type:
            issue_type = str(details.get("issue_type", "")).strip()
        if issue_type not in P026_ISSUE_TYPES:
            continue
        page = getattr(finding, page_attr, None)
        if page is None:
            continue
        try:
            page_int = int(page)
        except (TypeError, ValueError):
            continue
        key = p026_pattern_key(issue_type, details)
        by_pattern[key].append((index, page_int))
    return dict(by_pattern)


def collect_p026_pattern_pages_from_serialized(
    serialized_findings: Sequence[Mapping[str, object]],
) -> dict[tuple[str, str, str], list[tuple[int, int]]]:
    by_pattern: dict[tuple[str, str, str], list[tuple[int, int]]] = defaultdict(list)
    for index, finding in enumerate(serialized_findings):
        rule_id = str(finding.get("rule_id", "")).strip()
        if rule_id != P026_RULE_ID:
            continue
        details_raw = finding.get("details", {})
        details = details_raw if isinstance(details_raw, Mapping) else {}
        issue_type = str(details.get("issue_type", "")).strip()
        if issue_type not in P026_ISSUE_TYPES:
            continue
        page_raw = finding.get("page")
        if page_raw is None:
            continue
        try:
            page_int = int(str(page_raw))
        except ValueError:
            continue
        key = p026_pattern_key(issue_type, details)
        by_pattern[key].append((index, page_int))
    return dict(by_pattern)


def init_p026_display_state(
    pattern_pages: Mapping[tuple[str, str, str], Sequence[tuple[int, int]]],
) -> P026DisplayState:
    state = P026DisplayState()
    for pattern_key, entries in pattern_pages.items():
        pages = [page for _, page in entries]
        stats = build_p026_pattern_presentation_stats(pattern_key, pages)
        state.pattern_stats[pattern_key] = stats
        if should_use_p026_document_summary(
            stats.affected_page_count,
            stats.raw_finding_count,
        ):
            state.document_mode_patterns.add(pattern_key)
            min_page = min(pages)
            anchor_index = next(
                index for index, page in entries if page == min_page
            )
            state.pattern_anchors[pattern_key] = anchor_index
    return state


def consume_p026_finding_visibility(
    *,
    pattern_key: tuple[str, str, str],
    page: int | None,
    finding_index: int,
    state: P026DisplayState,
) -> bool:
    """Return True when a P026 finding should remain visible at presentation layer."""
    if pattern_key in state.document_mode_patterns:
        if pattern_key in state.pattern_document_shown:
            return False
        if finding_index != state.pattern_anchors.get(pattern_key):
            return False
        state.pattern_document_shown.add(pattern_key)
        return True
    token = (pattern_key, str(page) if page is not None else "document")
    if token in state.page_pattern_seen:
        return False
    state.page_pattern_seen.add(token)
    return True


def p026_page_location_label(
    *,
    page: int | None,
    issue_type: str,
    observed_summary: str,
    expected: str,
) -> str:
    observed = _safe_observed_phrase(observed_summary)
    if issue_type == P026_SIZE_ISSUE_TYPE:
        expected_phrase = _expected_size_phrase(expected)
        if page is None:
            base = "Document-wide — body text"
        else:
            base = f"Page {page} — body text"
        if observed:
            return f"{base} uses {observed} where {expected_phrase} is expected"
        return f"{base}, possible font size issue"
    expected_phrase = _expected_family_phrase(expected)
    if page is None:
        base = "Document-wide — body text"
    else:
        base = f"Page {page} — body text"
    if observed:
        return f"{base} uses {observed} where {expected_phrase} is expected"
    return f"{base}, possible font family issue"


def p026_document_location_label(stats: P026PatternPresentationStats) -> str:
    observed = _safe_observed_phrase(stats.observed_summary)
    if stats.issue_type == P026_SIZE_ISSUE_TYPE:
        expected_phrase = _expected_size_phrase(stats.expected)
        if observed:
            return (
                "Document-wide — body text uses "
                f"{observed} where {expected_phrase} is expected on "
                f"{stats.affected_page_count} pages"
            )
        return (
            "Document-wide — body text font-size issue detected on "
            f"{stats.affected_page_count} pages"
        )
    expected_phrase = _expected_family_phrase(stats.expected)
    if observed:
        return (
            "Document-wide — body text uses "
            f"{observed} where {expected_phrase} is expected on "
            f"{stats.affected_page_count} pages"
        )
    return (
        "Document-wide — body text font-family issue detected on "
        f"{stats.affected_page_count} pages"
    )


def p026_document_rolled_up_comment(stats: P026PatternPresentationStats) -> str:
    observed = _safe_observed_phrase(stats.observed_summary)
    pages_clause = f"Affected pages include: {stats.pages_compact}."
    if stats.issue_type == P026_SIZE_ISSUE_TYPE:
        expected_phrase = _expected_size_phrase(stats.expected)
        if observed:
            issue_clause = (
                f"body text appears to use {observed} on "
                f"{stats.affected_page_count} pages"
            )
        else:
            issue_clause = (
                f"body text may not match the expected font size on "
                f"{stats.affected_page_count} pages"
            )
    else:
        expected_phrase = _expected_family_phrase(stats.expected)
        if observed:
            issue_clause = (
                f"body text appears to use {observed} on "
                f"{stats.affected_page_count} pages"
            )
        else:
            issue_clause = (
                f"body text may not use the expected font family on "
                f"{stats.affected_page_count} pages"
            )
    body = (
        f"Likely problem: Across this document, {issue_clause} where "
        f"{expected_phrase} is expected. {pages_clause} "
        "This card summarizes multiple pages with the same font pattern. "
        "Apply the required NJIT body-text font and size consistently, export "
        "a clean PDF, and re-run the auditor."
    )
    return f"{REVIEW_PREFIX} {body}".strip()


def p026_document_suggested_fix(stats: P026PatternPresentationStats) -> str:
    if stats.issue_type == P026_SIZE_ISSUE_TYPE:
        return (
            "Set body text to the required 12pt font size on every affected page "
            "listed above, export a clean PDF, and re-run the auditor."
        )
    return (
        "Set body text to Times New Roman 12pt (or an accepted equivalent) on "
        "every affected page listed above, export a clean PDF, and re-run the auditor."
    )


def p026_document_rolled_up_explanation(stats: P026PatternPresentationStats) -> str:
    observed = _safe_observed_phrase(stats.observed_summary)
    if stats.issue_type == P026_SIZE_ISSUE_TYPE:
        expected_phrase = _expected_size_phrase(stats.expected)
        observed_text = (
            f"body-text spans appear to use {observed}"
            if observed
            else "body-text spans may not match the expected font size"
        )
    else:
        expected_phrase = _expected_family_phrase(stats.expected)
        observed_text = (
            f"body-text spans appear to use {observed}"
            if observed
            else "body-text spans may not use the expected font family"
        )
    text = (
        f"Observed: Across {stats.affected_page_count} pages, {observed_text}. "
        f"Expected: Body text should use {expected_phrase}. "
        "Why this is suspicious: the detector repeatedly saw the same non-matching "
        "font pattern in body-text-like spans on multiple pages. "
        f"What to check or fix: review every affected page. Affected pages include: "
        f"{stats.pages_compact}."
    )
    if stats.representative_page is not None:
        text += (
            f" No single highlight covers every occurrence. Open page "
            f"{stats.representative_page} as a representative starting point, then "
            "review every listed affected page in the original PDF."
        )
    return text


def p026_document_no_highlight_reason(stats: P026PatternPresentationStats) -> str:
    if stats.representative_page is None:
        return (
            "No exact highlight is available for this document-wide font summary. "
            "Open the original PDF and review the affected pages listed in the summary."
        )
    return (
        "No exact highlight is available for this document-wide font summary. "
        f"Open page {stats.representative_page} as a representative starting point, "
        "then review every affected page listed in the summary."
    )
