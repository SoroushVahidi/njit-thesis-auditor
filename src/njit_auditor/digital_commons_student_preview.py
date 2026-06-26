"""Student-facing wording for Digital Commons wrapper-page advisories."""

from __future__ import annotations


def digital_commons_advisory_comment(*, page_count: int, pages_compact: str) -> str:
    page_phrase = "page" if page_count == 1 else "pages"
    location = f"({pages_compact})" if pages_compact else ""
    return (
        "Likely notice: This PDF appears to include repository-generated Digital Commons "
        f"cover or copyright {page_phrase} {location} before the thesis manuscript. "
        "Those pages are not part of NJIT thesis formatting and can create misleading "
        "margin, annotation, or page-number warnings."
    ).replace("  ", " ").strip()


def digital_commons_advisory_suggested_fix() -> str:
    return (
        "Remove repository-generated Digital Commons cover, copyright, and metadata pages "
        "from the PDF before submitting your thesis manuscript, then re-run the auditor."
    )


def digital_commons_advisory_location_label(*, first_page: int, page_count: int) -> str:
    if page_count == 1:
        return f"Page {first_page} — Digital Commons wrapper page"
    return f"Pages starting at {first_page} — Digital Commons wrapper pages ({page_count} total)"
