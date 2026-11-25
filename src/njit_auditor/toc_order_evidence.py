"""Student-facing evidence for the representative section-order pair."""

import re
from collections.abc import Mapping

P062_ISSUE = "toc_cross_page_entry_numbers_not_nondecreasing"
_SECTION = re.compile(r"\d+(?:\.\d+)*")
_FOLIO = re.compile(r"(?:[0-9]{1,4}|[ivxlcdm]{1,12})", re.IGNORECASE)


def describe_p062_pair(details: Mapping[str, str]) -> str:
    """Describe an exact pair, while allowing older reports without pair metadata."""
    before = details.get("preceding_entry_number", "")
    after = details.get("following_entry_number", "")
    if not _SECTION.fullmatch(before) or not _SECTION.fullmatch(after):
        return ""
    before_page = details.get("preceding_entry_page", "")
    after_page = details.get("following_entry_page", "")
    if not before_page.isascii() or not before_page.isdecimal():
        return ""
    if not after_page.isascii() or not after_page.isdecimal():
        return ""

    def location(role: str, page: str) -> str:
        folio = details.get(f"{role}_entry_toc_folio", "")
        suffix = f" (printed TOC folio {folio})" if _FOLIO.fullmatch(folio) else ""
        return f"physical PDF page {page}{suffix}"

    if before_page == after_page:
        return (
            f"Section {before} appears before section {after} on "
            f"{location('following', after_page)}."
        )
    return (
        f"Section {before} on {location('preceding', before_page)} appears before "
        f"section {after} on {location('following', after_page)}."
    )
