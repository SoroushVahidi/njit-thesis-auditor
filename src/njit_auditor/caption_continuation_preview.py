"""Student-facing context for punctuation at a reconstructed description end."""

from collections.abc import Mapping


def caption_continuation_explanation(details: Mapping[str, str]) -> str:
    start, end = details.get("caption_start_page", ""), details.get("caption_end_page", "")
    if not start.isdigit() or not end.isdigit() or int(end) != int(start) + 1:
        return ""

    def reference(page: str, key: str) -> str:
        label = details.get(key, "")
        suffix = f" (document page {label})" if label.isdigit() else ""
        return f"physical PDF page {page}{suffix}"

    first = reference(start, "caption_start_document_page_label")
    last = reference(end, "caption_end_document_page_label")
    return (
        f"This figure description continues from {first} to {last}. "
        "Its logical end appears to be missing terminal punctuation. "
        f"Check the final line on physical PDF page {end}; the highlight target is that line only. "
        "Crossing a page boundary alone is not a formatting violation."
    )
