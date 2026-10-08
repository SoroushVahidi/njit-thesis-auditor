"""Student-facing notice for a web audit in which some checks could not run.

When the web job isolates a crashing PDF check (see
``audit_runner.collect_pdf_layout_findings``), every output a student can
read -- results page, text download, Markdown download, combined student PDF,
and JSON metadata -- carries the same notice, so an incomplete audit never
looks like a complete one.
"""

from __future__ import annotations

from collections.abc import Mapping

# Additive JSON/Markdown metadata key; present only when at least one check failed.
FAILED_CHECK_COUNT_KEY = "failed_check_count"

INCOMPLETE_AUDIT_TITLE = "Incomplete audit: some checks could not run on this file."


def incomplete_audit_notice(failed_check_count: int) -> str:
    """Return the notice body, or an empty string when every check ran."""
    if failed_check_count <= 0:
        return ""
    if failed_check_count == 1:
        counted = "1 automated check stopped"
        subject = "it looks"
    else:
        counted = f"{failed_check_count} automated checks stopped"
        subject = "they look"
    return (
        f"{counted} because of an internal error, so problems {subject} for may be "
        "missing from this report. The other checks ran normally. Verify your "
        "formatting by hand against the NJIT guidelines."
    )


def failed_check_count_from_metadata(metadata: Mapping[str, object]) -> int:
    """Read the failed-check count from report metadata (0 when absent or invalid)."""
    try:
        return max(0, int(str(metadata.get(FAILED_CHECK_COUNT_KEY, 0))))
    except ValueError:
        return 0
