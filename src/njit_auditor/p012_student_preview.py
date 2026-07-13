"""Privacy-safe P012 page-level and document-level rollup for annotation warnings."""

from __future__ import annotations

from collections.abc import Mapping, MutableSet, Sequence
from dataclasses import dataclass, field

from njit_auditor.polished_comments import REVIEW_PREFIX

P012_RULE_ID = "P012"
P012_ISSUE_TYPE = "pdf_annotation_detected"

# Presentation-only thresholds (not detector thresholds).
P012_DOCUMENT_SUMMARY_MIN_AFFECTED_PAGES = 11
P012_DOCUMENT_SUMMARY_MIN_RAW_FINDINGS = 21


def is_p012_finding(rule_id: str, issue_type: str) -> bool:
    return rule_id == P012_RULE_ID and issue_type == P012_ISSUE_TYPE


def should_use_p012_document_summary(
    affected_page_count: int,
    raw_finding_count: int,
) -> bool:
    """Return True when high-volume P012 should collapse to one document-wide card."""
    return (
        affected_page_count >= P012_DOCUMENT_SUMMARY_MIN_AFFECTED_PAGES
        or raw_finding_count >= P012_DOCUMENT_SUMMARY_MIN_RAW_FINDINGS
    )


@dataclass(frozen=True)
class P012PresentationStats:
    raw_finding_count: int
    affected_page_count: int
    count_by_page: dict[int, int]
    pages_compact: str
    top_pages_phrase: str
    representative_page: int | None


@dataclass
class P012DisplayState:
    """Mutable presentation-layer visibility state for P012 findings."""

    document_summary_mode: bool = False
    document_summary_shown: bool = False
    summary_anchor_index: int | None = None
    stats: P012PresentationStats | None = None
    page_seen: MutableSet[str] = field(default_factory=set)


def build_p012_presentation_stats(count_by_page: Mapping[int, int]) -> P012PresentationStats:
    from njit_auditor.report_outputs import compact_page_list

    pages = sorted(count_by_page.keys())
    raw_finding_count = sum(count_by_page.values())
    top_pages = sorted(count_by_page.items(), key=lambda item: (-item[1], item[0]))[:5]
    top_pages_phrase = ""
    if top_pages:
        top_pages_phrase = "Most affected pages: " + ", ".join(
            f"{page} ({count})" for page, count in top_pages
        )
    return P012PresentationStats(
        raw_finding_count=raw_finding_count,
        affected_page_count=len(pages),
        count_by_page=dict(count_by_page),
        pages_compact=compact_page_list(pages),
        top_pages_phrase=top_pages_phrase,
        representative_page=pages[0] if pages else None,
    )


def init_p012_display_state(
    count_by_page: Mapping[int, int],
    summary_anchor_index: int | None,
) -> P012DisplayState:
    if not count_by_page:
        return P012DisplayState()
    stats = build_p012_presentation_stats(count_by_page)
    document_summary_mode = should_use_p012_document_summary(
        stats.affected_page_count,
        stats.raw_finding_count,
    )
    return P012DisplayState(
        document_summary_mode=document_summary_mode,
        summary_anchor_index=summary_anchor_index if document_summary_mode else None,
        stats=stats if document_summary_mode else None,
    )


def find_p012_summary_anchor_index(
    findings: Sequence[object],
    count_by_page: Mapping[int, int],
    *,
    rule_id_attr: str = "rule_id",
    issue_type_attr: str = "issue_type",
    page_attr: str = "page",
) -> int | None:
    if not count_by_page:
        return None
    min_page = min(count_by_page.keys())
    for index, finding in enumerate(findings):
        rule_id = str(getattr(finding, rule_id_attr, "")).strip()
        issue_type = str(getattr(finding, issue_type_attr, "")).strip()
        page = getattr(finding, page_attr, None)
        if is_p012_finding(rule_id, issue_type) and page == min_page:
            return index
    return None


def find_p012_summary_anchor_index_from_serialized(
    serialized_findings: Sequence[Mapping[str, object]],
    count_by_page: Mapping[int, int],
) -> int | None:
    if not count_by_page:
        return None
    min_page = min(count_by_page.keys())
    for index, finding in enumerate(serialized_findings):
        rule_id = str(finding.get("rule_id", "")).strip()
        details_raw = finding.get("details", {})
        details = details_raw if isinstance(details_raw, Mapping) else {}
        issue_type = str(details.get("issue_type", "")).strip()
        page_raw = finding.get("page")
        try:
            page = int(str(page_raw)) if page_raw is not None else None
        except ValueError:
            page = None
        if is_p012_finding(rule_id, issue_type) and page == min_page:
            return index
    return None


def consume_p012_finding_visibility(
    *,
    page: int | None,
    finding_index: int,
    state: P012DisplayState,
) -> bool:
    """Return True when a P012 finding should remain visible at presentation layer."""
    if state.document_summary_mode:
        if state.document_summary_shown:
            return False
        if finding_index != state.summary_anchor_index:
            return False
        state.document_summary_shown = True
        return True
    return consume_p012_display_slot(page, state.page_seen)


def p012_location_label(page: int | None, annotation_count: int) -> str:
    """Return a student-facing Where label for a rolled-up P012 page warning."""
    if annotation_count <= 0:
        annotation_count = 1
    if page is None:
        if annotation_count == 1:
            return "PDF annotations/comments detected"
        return f"{annotation_count} PDF annotations/comments detected"
    if annotation_count == 1:
        return f"Page {page} — PDF annotations/comments detected"
    return f"Page {page} — {annotation_count} PDF annotations/comments detected"


def p012_document_location_label(stats: P012PresentationStats) -> str:
    return (
        "Document-wide — "
        f"{stats.raw_finding_count} PDF annotations/comments detected "
        f"across {stats.affected_page_count} pages"
    )


def p012_rolled_up_comment(*, page: int | None, annotation_count: int) -> str:
    """Return a rolled-up student-facing comment for one P012 page card."""
    if annotation_count <= 0:
        annotation_count = 1
    if page is None:
        page_phrase = "this document"
    else:
        page_phrase = f"page {page}"
    if annotation_count == 1:
        body = (
            "Likely problem: The uploaded PDF appears to already contain "
            f"annotations or comments on {page_phrase}. These refer to markup left "
            "in the original file you uploaded, not highlights added by this auditor. "
            "Before final submission, accept or reject reviewer changes, remove "
            "comments, highlights, or other markup, and upload a clean copy."
        )
    else:
        body = (
            f"Likely problem: The uploaded PDF appears to contain {annotation_count} "
            f"annotations or comments on {page_phrase}. These refer to markup left "
            "in the original file you uploaded, not highlights added by this auditor. "
            "Open this page, resolve every annotation or comment, and repeat for all "
            "affected pages before submitting a clean copy."
        )
    return f"{REVIEW_PREFIX} {body}".strip()


def p012_document_rolled_up_comment(stats: P012PresentationStats) -> str:
    pages_clause = f"Affected pages include: {stats.pages_compact}."
    top_clause = f" {stats.top_pages_phrase}." if stats.top_pages_phrase else ""
    body = (
        "Likely problem: The uploaded PDF appears to contain "
        f"{stats.raw_finding_count} annotations or comments (such as sticky notes, "
        f"highlights, or reviewer comments) across {stats.affected_page_count} pages. "
        "These refer to markup already present in the original file you uploaded, not "
        "highlights added by this auditor. "
        f"{pages_clause}{top_clause} Before final submission, open the PDF in your "
        "editor, accept or reject all reviewer changes, remove any remaining comments "
        "or markup, export a clean PDF, and re-run the auditor."
    )
    return f"{REVIEW_PREFIX} {body}".strip()


def p012_rolled_up_suggested_fix(annotation_count: int) -> str:
    if annotation_count <= 1:
        return "Resolve or remove the annotation or comment, then upload a clean PDF."
    return (
        "Resolve or remove every annotation and comment on this page, then check "
        "all other affected pages before uploading a clean PDF."
    )


def p012_document_suggested_fix() -> str:
    return (
        "Remove, resolve, or flatten every PDF annotation and comment on the "
        "affected pages listed above, export a clean PDF, and re-run the auditor."
    )


def p012_rolled_up_explanation(
    *,
    page: int | None,
    annotation_count: int,
    has_highlight: bool,
    location_label: str,
) -> str:
    if annotation_count <= 0:
        annotation_count = 1
    if page is None:
        page_clause = "in the uploaded PDF"
    else:
        page_clause = f"on page {page}"
    observed = (
        "an annotation or comment"
        if annotation_count == 1
        else f"{annotation_count} annotations or comments"
    )
    text = (
        f"Observed: The uploaded PDF appears to already contain {observed} "
        f"{page_clause}. "
        "Expected: Before final submission, the PDF should be free of reviewer "
        "annotations, comments, sticky notes, and markup. "
        "Why this is suspicious: these findings refer to markup that was already "
        "present in the original file you uploaded -- they are not highlights added "
        "by this auditor to show you where to look. "
        "What to check or fix: open the original PDF in your editor, accept or "
        "reject all reviewer changes, delete remaining comments, highlights, or "
        "markup, and upload a clean copy before final submission."
    )
    if has_highlight and annotation_count > 1:
        text += (
            " This page contains multiple annotations or comments; the highlight "
            "shows one representative location."
        )
    elif not has_highlight:
        from njit_auditor.finding_explanations import build_no_highlight_guidance

        text += " " + build_no_highlight_guidance(
            rule_id=P012_RULE_ID,
            issue_type=P012_ISSUE_TYPE,
            details={},
            page=page,
            location_label=location_label,
        )
    return text


def p012_document_rolled_up_explanation(stats: P012PresentationStats) -> str:
    text = (
        "Observed: The uploaded PDF appears to contain "
        f"{stats.raw_finding_count} PDF annotations across "
        f"{stats.affected_page_count} pages. These may include sticky notes, "
        "text highlights, comment balloons, freehand drawings, or other reviewer "
        "markup embedded in the file. "
        "Expected: Before final submission, the PDF should be completely free of "
        "embedded annotations, reviewer comments, and markup. "
        "Why this is suspicious: these findings refer to markup that was already "
        "present in the original file you uploaded -- they are not highlights added "
        "by this auditor to show you where to look. "
        "What to check or fix: open the original PDF in your editor, accept or "
        "reject all reviewer changes, delete remaining comments, highlights, and "
        f"markup, then export a clean copy. Affected pages include: {stats.pages_compact}."
    )
    if stats.top_pages_phrase:
        text += f" {stats.top_pages_phrase}."
    if stats.representative_page is not None:
        text += (
            f" No single highlight covers every annotation. Open page "
            f"{stats.representative_page} as a starting point, then review every "
            "listed affected page in the original PDF."
        )
    return text


def p012_document_no_highlight_reason(stats: P012PresentationStats) -> str:
    if stats.representative_page is None:
        return (
            "No exact highlight is available for this document-wide annotation summary. "
            "Open the original PDF and review the affected pages listed in the summary."
        )
    return (
        "No exact highlight is available for this document-wide annotation summary. "
        f"Open page {stats.representative_page} as a representative starting point, "
        f"then review the affected pages: {stats.pages_compact}."
    )


def consume_p012_display_slot(page: int | None, seen: MutableSet[str]) -> bool:
    """Return True when a page-level P012 finding should remain visible."""
    token = str(page) if page is not None else "document"
    if token in seen:
        return False
    seen.add(token)
    return True


def count_p012_annotations_by_page(
    findings: Sequence[Mapping[str, object]],
) -> dict[int, int]:
    """Count raw P012 annotation findings per page from serialized findings."""
    counts: dict[int, int] = {}
    for finding in findings:
        rule_id = str(finding.get("rule_id", "")).strip()
        details_raw = finding.get("details", {})
        details = details_raw if isinstance(details_raw, Mapping) else {}
        issue_type = str(details.get("issue_type", "")).strip()
        if not is_p012_finding(rule_id, issue_type):
            continue
        page_raw = finding.get("page")
        if page_raw is None:
            continue
        try:
            page = int(str(page_raw))
        except ValueError:
            continue
        counts[page] = counts.get(page, 0) + 1
    return counts
