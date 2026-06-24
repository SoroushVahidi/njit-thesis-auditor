"""Privacy-safe P012 page-level rollup for annotation/comment warnings."""

from __future__ import annotations

from collections.abc import Mapping, MutableSet

from njit_auditor.polished_comments import REVIEW_PREFIX

P012_RULE_ID = "P012"
P012_ISSUE_TYPE = "pdf_annotation_detected"


def is_p012_finding(rule_id: str, issue_type: str) -> bool:
    return rule_id == P012_RULE_ID and issue_type == P012_ISSUE_TYPE


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


def p012_rolled_up_suggested_fix(annotation_count: int) -> str:
    if annotation_count <= 1:
        return "Resolve or remove the annotation or comment, then upload a clean PDF."
    return (
        "Resolve or remove every annotation and comment on this page, then check "
        "all other affected pages before uploading a clean PDF."
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


def consume_p012_display_slot(page: int | None, seen: MutableSet[str]) -> bool:
    """Return True when a P012 finding should remain visible at presentation layer."""
    token = str(page) if page is not None else "document"
    if token in seen:
        return False
    seen.add(token)
    return True


def count_p012_annotations_by_page(
    findings: list[Mapping[str, object]],
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
