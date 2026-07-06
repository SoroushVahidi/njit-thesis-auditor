"""Regression test: the "Findings by topic" drill-down location text
(``_student_location_text`` in web_app.py) must not duplicate the page
number when a rule's ``location_label`` already names the page in a
non-"Page N" form (e.g. the plural "Pages starting at N ..." used by the
P025 Digital Commons wrapper-page notice).

Before this fix, a P025 multi-page wrapper finding rendered as:
    "Page 3 - Pages starting at 3 — Digital Commons wrapper pages (5 total)"
because the function only recognized labels starting with the singular
"page " (not "pages ") as already containing the page number.
"""
from __future__ import annotations

from njit_auditor.web_app import _student_location_text


def test_plural_pages_label_is_not_duplicated() -> None:
    finding = {
        "page": 3,
        "location_label": "Pages starting at 3 — Digital Commons wrapper pages (5 total)",
    }
    text = _student_location_text(finding)
    assert text == "Pages starting at 3 — Digital Commons wrapper pages (5 total)"
    assert not text.startswith("Page 3 -")


def test_singular_page_label_still_passes_through_unmodified() -> None:
    finding = {"page": 1, "location_label": "Page 1 — Digital Commons wrapper page"}
    assert _student_location_text(finding) == "Page 1 — Digital Commons wrapper page"


def test_typical_location_label_still_passes_through_unmodified() -> None:
    finding = {"page": 12, "location_label": "Page 12 — left margin"}
    assert _student_location_text(finding) == "Page 12 — left margin"


def test_non_page_prefixed_label_still_gets_page_number_prepended() -> None:
    """A label that does NOT already reference the page number at all
    (neither "page " nor "pages ") must still get "Page N - " prepended,
    so this fix doesn't silently drop location context for other rules."""
    finding = {"page": 7, "location_label": "left margin"}
    assert _student_location_text(finding) == "Page 7 - left margin"


def test_blank_location_label_falls_back_to_bare_page() -> None:
    finding = {"page": 5, "location_label": ""}
    assert _student_location_text(finding) == "Page 5"


def test_no_page_and_no_label_is_document_wide() -> None:
    finding = {"page": None, "location_label": ""}
    assert _student_location_text(finding) == "Document-wide overview"
