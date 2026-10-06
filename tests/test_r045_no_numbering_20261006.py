"""R045: Biographical Sketch publication entries must not be numbered.

Ester, 2026-10-06: "The list of publications on this page MUST NOT BE
NUMBERED". They are not references: same citation format as the References
section, without the number in front. Synthetic text only.
"""

from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.rules.pdf_biosketch_publication_layout import (
    check_pdf_biosketch_publication_layout,
)

NUMBERED = "biosketch_publication_entry_numbered"


def _biosketch(
    path: Path,
    entries: list[list[tuple[float, str]]],
    *,
    line_step: float = 14.0,
    entry_step: float = 28.0,
    references_page: list[str] | None = None,
) -> Path:
    """Each entry is a list of (x, text) rows; rows are single-spaced."""
    doc = fitz.open()
    if references_page is not None:
        ref = doc.new_page(width=612, height=792)
        ref.insert_text((260, 70), "REFERENCES", fontsize=14, fontname="Times-Bold")
        y = 110.0
        for text in references_page:
            ref.insert_text((108, y), text, fontsize=12)
            y += 28.0
    page = doc.new_page(width=612, height=792)
    page.insert_text((200, 70), "BIOGRAPHICAL SKETCH", fontsize=14, fontname="Times-Bold")
    page.insert_text((108, 110), "Publications and Presentations:", fontname="Times-Bold")
    y = 136.0
    for entry in entries:
        for x, text in entry:
            page.insert_text((x, y), text, fontsize=12)
            y += line_step
        y += entry_step - line_step
    page.insert_text((300, 760), "iv", fontsize=12)
    doc.save(path)
    doc.close()
    return path


def _findings(path: Path) -> list[dict[str, str]]:
    return [
        f.details
        for f in check_pdf_biosketch_publication_layout(load_pdf_layout(str(path)))
        if f.rule_id == "P045"
    ]


def _numbering(path: Path) -> list[dict[str, str]]:
    return [d for d in _findings(path) if d["issue_type"] == NUMBERED]


def _entry(first: str, *, x: float = 108.0, rest_x: float = 126.0, lines: int = 2):
    rows = [(x, f"{first} Synthetic author list and title of the work, part one.")]
    rows += [(rest_x, f"Synthetic venue and details, wrapped line {n}.") for n in range(1, lines)]
    return rows


@pytest.mark.parametrize(
    ("labels", "style"),
    [
        (["[1]", "[2]"], "bracketed_number"),
        (["[11]", "[12]"], "bracketed_number"),
        (["(1)", "(2)"], "parenthesized_number"),
        (["1.", "2."], "number_with_period"),
        (["1)", "2)"], "number_with_parenthesis"),
    ],
)
def test_numbered_entries_are_reported(tmp_path: Path, labels: list[str], style: str) -> None:
    path = _biosketch(tmp_path / "n.pdf", [_entry(label) for label in labels])
    (finding,) = _numbering(path)
    assert finding["numbered_entry_count"] == "2"
    assert finding["numbering_style"] == style
    assert finding["bbox"]


@pytest.mark.parametrize("label", ["[1]", "1.", "(1)"])
def test_a_single_numbered_entry_is_reported(tmp_path: Path, label: str) -> None:
    """Numbering does not depend on the two-entry gate of the spacing checks."""
    path = _biosketch(tmp_path / "one.pdf", [_entry(label, lines=3)])
    (finding,) = _numbering(path)
    assert finding["numbered_entry_count"] == "1"


def test_many_numbered_entries_give_one_page_finding(tmp_path: Path) -> None:
    path = _biosketch(tmp_path / "many.pdf", [_entry(f"[{n}]") for n in range(1, 5)])
    (finding,) = _numbering(path)
    assert finding["numbered_entry_count"] == "4"


def test_unnumbered_entries_are_clean(tmp_path: Path) -> None:
    path = _biosketch(
        tmp_path / "plain.pdf", [_entry("Author, A."), _entry("Author, B.")]
    )
    assert _findings(path) == []


def test_citation_internal_numbers_are_not_numbering(tmp_path: Path) -> None:
    entries = [
        [
            (108.0, "Smith, J. (2024). Synthetic title of a journal article here."),
            (126.0, "12(3), pp. 10-25, doi:10.1109/5.771073, synthetic venue."),
        ],
        [
            (108.0, "Doe, A. Synthetic paper presented at a 2026 conference."),
            (126.0, "2026 International Conference on Synthetic Topics, No. 3."),
        ],
        [
            (108.0, "Roe, B. 3D synthetic imaging methods, Vol. 12, issue 3."),
            (126.0, "IEEE 802.11 synthetic workshop proceedings, pages 100-115."),
        ],
    ]
    assert _numbering(_biosketch(tmp_path / "cites.pdf", entries)) == []


def test_flush_continuation_starting_with_a_number_is_not_numbering(tmp_path: Path) -> None:
    """No hanging indent: one wrapped line happens to begin "(2) pp."."""
    entries = [
        [
            (108.0, "Smith, J. Synthetic title of a journal article, vol. 7, no."),
            (108.0, "(2) pp. 10-25, synthetic journal name and year 2024 here."),
        ],
        [(108.0, "Doe, A. Second synthetic entry title for the test case.")],
    ]
    assert _numbering(_biosketch(tmp_path / "flush.pdf", entries)) == []


@pytest.mark.parametrize("label", ["(a)", "I.", "a."])
def test_unsupported_label_forms_are_not_reported(tmp_path: Path, label: str) -> None:
    path = _biosketch(tmp_path / "u.pdf", [_entry(label), _entry(label)])
    assert _numbering(path) == []


def test_missing_hanging_indent_alone_is_not_a_violation(tmp_path: Path) -> None:
    entries = [_entry("Author, A.", rest_x=108.0), _entry("Author, B.", rest_x=108.0)]
    path = _biosketch(tmp_path / "nohang.pdf", entries)
    assert _findings(path) == []


def test_single_spacing_and_blank_line_checks_still_apply(tmp_path: Path) -> None:
    double = _biosketch(
        tmp_path / "double.pdf",
        [_entry("Author, A.", lines=3), _entry("Author, B.", lines=3)],
        line_step=24.0,
        entry_step=40.0,
    )
    assert [d["issue_type"] for d in _findings(double)] == [
        "biosketch_publication_wrapped_line_spacing_not_single"
    ]
    tight = _biosketch(
        tmp_path / "tight.pdf",
        [_entry("Author, A."), _entry("Author, B."), _entry("Author, C.")],
        entry_step=14.0,
    )
    assert [d["issue_type"] for d in _findings(tight)] == [
        "biosketch_publication_entry_spacing_not_double"
    ]


def test_numbered_references_section_is_not_checked(tmp_path: Path) -> None:
    """References are numbered by design; only the Bio Sketch list is checked."""
    path = _biosketch(
        tmp_path / "refs.pdf",
        [_entry("Author, A."), _entry("Author, B.")],
        references_page=[
            "[1] Synthetic reference entry one with author and title.",
            "[2] Synthetic reference entry two with author and title.",
        ],
    )
    assert _findings(path) == []


def test_numbering_maps_to_the_r045_card_with_explicit_wording() -> None:
    import njit_auditor.web_app as wa
    from njit_auditor.finding_explanations import build_detailed_explanation
    from njit_auditor.issue_type_explanations import explain_issue_type, issue_type_title
    from njit_auditor.polished_comments import _ISSUE_REMEDIATION_OVERRIDES, build_polished_comment
    from njit_auditor.report_outputs import public_display_rule_id

    assert wa._public_rule_reference_id("P045", issue_type=NUMBERED) == "P045"
    assert public_display_rule_id("P045") == "R045"
    card = {r["id"]: r for r in wa._build_rule_catalog()["student_rules"]}["P045"]
    assert "unnumbered" in card["title"]
    assert "must not be numbered" in card["what_it_checks"]
    assert "Remove the numbers" in card["how_to_correct"]
    assert "References section" in card["how_to_correct"]
    assert "hanging indent is optional" in card["how_to_correct"].lower()

    details = {"numbered_entry_count": "2", "numbering_style": "bracketed_number"}
    texts = [
        build_polished_comment(rule_id="P045", issue_type=NUMBERED, page=5, details=details),
        build_detailed_explanation(rule_id="P045", issue_type=NUMBERED, page=5, details=details),
        explain_issue_type("P045", NUMBERED, details),
        _ISSUE_REMEDIATION_OVERRIDES[("P045", NUMBERED)],
    ]
    for text in texts:
        lower = text.lower()
        assert "number" in lower
        assert "should be numbered" not in lower
        assert "year" not in lower
        assert "P045" not in text
    assert "must not be numbered" in texts[0]
    assert "References" in texts[3]
    assert "numbered" in issue_type_title("P045", NUMBERED).lower()
    # Spacing findings get only their own fix, not the numbering advice.
    spacing_fix = _ISSUE_REMEDIATION_OVERRIDES[
        ("P045", "biosketch_publication_wrapped_line_spacing_not_single")
    ]
    assert "number" not in spacing_fix.lower()
