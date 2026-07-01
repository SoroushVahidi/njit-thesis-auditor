"""Student-facing wording for Digital Commons wrapper-page advisories."""

from __future__ import annotations

WRAPPER_PREPROCESSING_ISSUE_TYPE = "digital_commons_wrapper_pages_detected"


def is_wrapper_preprocessing_notice(*, rule_id: str, issue_type: str) -> bool:
    return (
        rule_id == "P025"
        and issue_type == WRAPPER_PREPROCESSING_ISSUE_TYPE
    )


def digital_commons_advisory_comment(*, page_count: int, pages_compact: str) -> str:
    page_phrase = "page" if page_count == 1 else "pages"
    if pages_compact:
        location = f"({pages_compact})"
    else:
        location = f"({page_count} {page_phrase})"
    return (
        "This PDF includes repository-generated Digital Commons pages "
        f"{location} before the thesis manuscript. The auditor excluded these pages "
        "from thesis-formatting checks and uses manuscript/PDF page labels to avoid "
        "confusion."
    )


def digital_commons_advisory_suggested_fix() -> str:
    return (
        "If this is a manuscript you plan to submit, remove repository-generated "
        "cover/copyright pages before submission. If this is a Digital Commons "
        "download, no action is needed; the auditor has excluded these pages from "
        "formatting checks."
    )


def digital_commons_advisory_location_label(*, first_page: int, page_count: int) -> str:
    if page_count == 1:
        return f"Page {first_page} — repository wrapper page"
    return f"Pages starting at {first_page} — repository wrapper pages ({page_count} total)"
