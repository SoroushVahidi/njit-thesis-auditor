"""P018 leader placement for TOC, List of Tables, and List of Figures.

Ester's 2026-09-23 clarification: leader dots begin right after the title
(after the final line of a wrapped title), and one space between the end of
the title and the first dot is allowed. The previously confirmed List of
Figures example (a visible multi-space gap before the leader) remains ground
truth; these tests reproduce its *shape* with invented titles only.
"""

from pathlib import Path

import fitz
import pytest

from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.rules.pdf_toc_alignment import check_pdf_toc_alignment

FONT = "tiro"
SIZE = 12.0
DOTS = "." * 30
GAP_ISSUE = "title_to_leader_gap_too_wide"
EARLY_ISSUE = "leader_dots_before_final_title_line"
HEADINGS = {
    "list_of_figures": "LIST OF FIGURES",
    "list_of_tables": "LIST OF TABLES",
    "table_of_contents": "TABLE OF CONTENTS",
}
TITLES = {
    "list_of_figures": ("1.1 Map of the survey area", "1.2 Seasonal sample counts"),
    "list_of_tables": ("1.1 Summary of survey sites", "1.2 Seasonal sample counts"),
    "table_of_contents": ("1.1 Background", "1.2 Study Design"),
}


def _render(tmp_path: Path, heading: str, rows: list[tuple[float, float, str]]) -> Path:
    pdf_path = tmp_path / "list.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((250, 90), heading, fontname=FONT, fontsize=SIZE)
    for x, y, text in rows:
        page.insert_text((x, y), text, fontname=FONT, fontsize=SIZE)
    doc.save(pdf_path)
    doc.close()
    return pdf_path


def _p018(pdf_path: Path, issue_type: str) -> list:
    model = load_pdf_layout(str(pdf_path))
    return [
        f
        for f in check_pdf_toc_alignment(model)
        if f.rule_id == "P018" and f.details.get("issue_type") == issue_type
    ]


def _entry(title: str, spaces: int, page: int) -> str:
    return f"{title}{' ' * spaces}{DOTS} {page}"


@pytest.mark.parametrize("page_type", sorted(HEADINGS))
@pytest.mark.parametrize("spaces", [0, 1])
def test_leader_directly_after_title_or_one_space_is_allowed(
    tmp_path: Path, page_type: str, spaces: int
) -> None:
    first, second = TITLES[page_type]
    rows = [
        (108.0, 140.0, _entry(first, spaces, 3)),
        (108.0, 168.0, _entry(second, spaces, 5)),
    ]
    assert _p018(_render(tmp_path, HEADINGS[page_type], rows), GAP_ISSUE) == []


@pytest.mark.parametrize("page_type", sorted(HEADINGS))
def test_visibly_excessive_title_to_leader_gap_is_flagged(
    tmp_path: Path, page_type: str
) -> None:
    first, second = TITLES[page_type]
    rows = [
        (108.0, 140.0, _entry(first, 5, 3)),
        (108.0, 168.0, _entry(second, 0, 5)),
    ]
    findings = _p018(_render(tmp_path, HEADINGS[page_type], rows), GAP_ISSUE)
    assert len(findings) == 1
    details = findings[0].details
    assert details["page_type"] == page_type
    assert details["affected_entry_count"] == "1"
    assert float(details["observed_gap_pt"]) > float(details["allowed_gap_pt"])
    assert float(details["observed_gap_spaces"]) >= 4.5


def test_single_entry_list_page_is_still_checked(tmp_path: Path) -> None:
    """The confirmed example sits on a one-entry list page, so this absolute
    check must not depend on the peer-count gate the relative checks use."""

    rows = [(108.0, 140.0, _entry("1.1 Map of the survey area", 5, 4))]
    assert len(_p018(_render(tmp_path, "LIST OF FIGURES", rows), GAP_ISSUE)) == 1


def test_gap_measured_across_separate_title_and_leader_spans(tmp_path: Path) -> None:
    title = "1.1 Map of the survey area"
    title_end = 108.0 + fitz.get_text_length(title, fontname=FONT, fontsize=SIZE)
    near = [(108.0, 140.0, title), (title_end + 3.0, 140.0, f"{DOTS} 3")]
    far = [(108.0, 140.0, title), (title_end + 20.0, 140.0, f"{DOTS} 3")]
    near_dir = tmp_path / "near"
    near_dir.mkdir()
    far_dir = tmp_path / "far"
    far_dir.mkdir()
    assert _p018(_render(near_dir, "LIST OF FIGURES", near), GAP_ISSUE) == []
    assert len(_p018(_render(far_dir, "LIST OF FIGURES", far), GAP_ISSUE)) == 1


def test_small_extraction_noise_beyond_one_space_is_not_flagged(tmp_path: Path) -> None:
    title = "1.1 Map of the survey area"
    space = fitz.get_text_length(" ", fontname=FONT, fontsize=SIZE)
    title_end = 108.0 + fitz.get_text_length(title, fontname=FONT, fontsize=SIZE)
    rows = [(108.0, 140.0, title), (title_end + space + 1.0, 140.0, f"{DOTS} 3")]
    assert _p018(_render(tmp_path, "LIST OF FIGURES", rows), GAP_ISSUE) == []


def test_grid_aligned_spaced_leaders_are_not_flagged(tmp_path: Path) -> None:
    """LaTeX-style leaders place single dots on a fixed grid, so the first dot
    can land up to one leader pitch past the title end without any typed gap."""

    title = "1.1 Map of the survey area"
    title_end = 108.0 + fitz.get_text_length(title, fontname=FONT, fontsize=SIZE)
    pitch = 9.0
    first_dot = title_end + 11.5
    rows: list[tuple[float, float, str]] = [(108.0, 140.0, title)]
    rows.extend((first_dot + pitch * k, 140.0, ".") for k in range(20))
    rows.append((540.0, 140.0, "3"))
    assert _p018(_render(tmp_path, "LIST OF FIGURES", rows), GAP_ISSUE) == []


def test_wrapped_title_with_leaders_after_final_line_is_allowed(tmp_path: Path) -> None:
    rows = [
        (108.0, 140.0, "1.1 Sampling design for the long survey of the"),
        (130.0, 154.0, _entry("coastal sites", 1, 5)),
        (108.0, 182.0, _entry("1.2 Summary chart", 0, 7)),
    ]
    pdf = _render(tmp_path, "LIST OF FIGURES", rows)
    assert _p018(pdf, GAP_ISSUE) == []
    assert _p018(pdf, EARLY_ISSUE) == []


def test_wrapped_title_with_excessive_final_line_gap_is_flagged(tmp_path: Path) -> None:
    rows = [
        (108.0, 140.0, "1.1 Sampling design for the long survey of the"),
        (130.0, 154.0, _entry("coastal sites", 6, 5)),
        (108.0, 182.0, _entry("1.2 Summary chart", 0, 7)),
    ]
    assert len(_p018(_render(tmp_path, "LIST OF TABLES", rows), GAP_ISSUE)) == 1


def test_leaders_on_earlier_line_of_wrapped_title_are_flagged(tmp_path: Path) -> None:
    rows = [
        (108.0, 140.0, f"1.1 Sampling design for the long survey {DOTS}"),
        (130.0, 154.0, "of the coastal sites"),
        (540.0, 154.0, "5"),
        (108.0, 182.0, _entry("1.2 Summary chart", 0, 7)),
    ]
    pdf = _render(tmp_path, "TABLE OF CONTENTS", rows)
    findings = _p018(pdf, EARLY_ISSUE)
    assert len(findings) == 1
    assert findings[0].details["affected_entry_count"] == "1"
    assert _p018(pdf, GAP_ISSUE) == []


def test_title_ending_period_before_separated_leader_is_title_punctuation(
    tmp_path: Path,
) -> None:
    """A terminal period attached to the title is not the first leader dot, so
    a wide gap after it is still measured."""

    rows = [
        (108.0, 140.0, f"1.1 Map of the survey area.      {DOTS} 3"),
        (108.0, 168.0, _entry("1.2 Summary chart.", 0, 7)),
    ]
    assert len(_p018(_render(tmp_path, "LIST OF FIGURES", rows), GAP_ISSUE)) == 1


def test_glyph_geometry_is_recorded_only_on_leader_pages(tmp_path: Path) -> None:
    pdf_path = tmp_path / "two_pages.pdf"
    doc = fitz.open()
    leader_page = doc.new_page(width=612, height=792)
    leader_page.insert_text((108, 140), _entry("1.1 Background", 0, 3), fontname=FONT)
    body_page = doc.new_page(width=612, height=792)
    body_page.insert_text((108, 140), "Ordinary body text without leaders.", fontname=FONT)
    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))
    leader_spans = [s for b in model.pages[0].text_blocks for ln in b.lines for s in ln.spans]
    body_spans = [s for b in model.pages[1].text_blocks for ln in b.lines for s in ln.spans]
    assert leader_spans and all(
        s.char_x_bounds is not None and len(s.char_x_bounds) == len(s.text)
        for s in leader_spans
    )
    assert body_spans and all(s.char_x_bounds is None for s in body_spans)


LIST_TITLES = (
    "1.1 Map of the survey area",
    "1.2 Seasonal sample counts by site",
    "1.3 Water column profile",
    "1.4 Station layout overview for the bay",
)


def _gap_findings(rows: list[tuple[float, float, str]], tmp_path: Path, heading: str) -> list:
    return _p018(_render(tmp_path, heading, rows), GAP_ISSUE)


def test_typed_leaders_allow_one_space_but_not_two(tmp_path: Path) -> None:
    """Typed (non-grid) leaders start wherever the title ends, so no grid-phase
    allowance applies: one space passes, two spaces are an excess gap."""

    def rows(spaces_on_third: int) -> list[tuple[float, float, str]]:
        return [
            (108.0, 140.0 + 28.0 * i, _entry(title, spaces_on_third if i == 2 else 1, i + 3))
            for i, title in enumerate(LIST_TITLES)
        ]

    one_dir = tmp_path / "one"
    one_dir.mkdir()
    assert _gap_findings(rows(1), one_dir, "LIST OF FIGURES") == []
    two_dir = tmp_path / "two"
    two_dir.mkdir()
    findings = _gap_findings(rows(2), two_dir, "LIST OF FIGURES")
    assert len(findings) == 1
    assert findings[0].details["leader_layout"] == "typed"
    assert 1.8 <= float(findings[0].details["observed_gap_spaces"]) <= 2.2


def _grid_rows(extra_cells_on_second: int) -> list[tuple[float, float, str]]:
    """Spaced single-dot leaders on one page-wide 9 pt grid (LaTeX dotfill)."""

    pitch = 9.0
    rows: list[tuple[float, float, str]] = []
    for i, title in enumerate(LIST_TITLES):
        y = 140.0 + 28.0 * i
        title_end = 108.0 + fitz.get_text_length(title, fontname=FONT, fontsize=SIZE)
        first_cell = (int(title_end // pitch) + 1) * pitch
        if i == 1:
            first_cell += pitch * extra_cells_on_second
        rows.append((108.0, y, title))
        dot_count = int((520 - first_cell) // pitch)
        rows.extend((first_cell + 3.0 + pitch * k, y, ".") for k in range(dot_count))
        rows.append((540.0, y, str(i + 3)))
    return rows


def test_grid_aligned_leaders_accept_grid_phase_but_not_skipped_cells(tmp_path: Path) -> None:
    ok_dir = tmp_path / "ok"
    ok_dir.mkdir()
    assert _gap_findings(_grid_rows(0), ok_dir, "TABLE OF CONTENTS") == []
    bad_dir = tmp_path / "bad"
    bad_dir.mkdir()
    findings = _gap_findings(_grid_rows(2), bad_dir, "TABLE OF CONTENTS")
    assert len(findings) == 1
    assert findings[0].details["leader_layout"] == "grid"


def test_earlier_line_leader_detected_on_list_of_figures(tmp_path: Path) -> None:
    rows = [
        (108.0, 140.0, f"1.1 Sampling design for the long survey {DOTS}"),
        (130.0, 154.0, "of the coastal sites"),
        (540.0, 154.0, "5"),
        (108.0, 182.0, f"1.2 Water column profile across the survey {DOTS}"),
        (130.0, 196.0, "transect"),
        (540.0, 196.0, "7"),
        (108.0, 224.0, _entry("1.3 Summary chart", 0, 9)),
    ]
    findings = _p018(_render(tmp_path, "LIST OF FIGURES", rows), EARLY_ISSUE)
    assert len(findings) == 1
    assert findings[0].details["affected_entry_count"] == "2"


def test_leader_row_with_detached_lower_page_number_is_not_an_earlier_line_leader(
    tmp_path: Path,
) -> None:
    """A page number set slightly below its own leader row belongs to that row;
    it is not a wrapped title line."""

    rows = [
        (108.0, 140.0, f"1.1 Sampling design for the long survey {DOTS}"),
        (540.0, 147.0, "5"),
        (108.0, 175.0, _entry("1.2 Summary chart", 0, 7)),
    ]
    assert _p018(_render(tmp_path, "TABLE OF CONTENTS", rows), EARLY_ISSUE) == []


def test_leader_row_followed_by_new_numbered_entry_is_not_an_earlier_line_leader(
    tmp_path: Path,
) -> None:
    rows = [
        (108.0, 140.0, f"1.1 Sampling design for the long survey {DOTS}"),
        (108.0, 154.0, "1.2 Summary chart for all sites"),
        (540.0, 154.0, "7"),
    ]
    assert _p018(_render(tmp_path, "TABLE OF CONTENTS", rows), EARLY_ISSUE) == []


def test_final_line_gap_is_measured_from_the_final_title_glyph(tmp_path: Path) -> None:
    """Earlier wrapped lines carry no leaders and are never measured; the
    final line's own last glyph is the reference."""

    first = "1.1 Sampling design for the long survey of the"
    last = "coastal sites"
    last_end = 130.0 + fitz.get_text_length(last, fontname=FONT, fontsize=SIZE)
    rows = [
        (108.0, 140.0, first),
        (130.0, 154.0, last),
        (last_end + 20.0, 154.0, f"{DOTS} 5"),
        (108.0, 182.0, _entry("1.2 Summary chart", 0, 7)),
    ]
    findings = _p018(_render(tmp_path, "LIST OF TABLES", rows), GAP_ISSUE)
    assert len(findings) == 1
    assert abs(float(findings[0].details["observed_gap_pt"]) - 20.0) < 0.6


def test_confidence_policy_for_leader_placement_issue_types(tmp_path: Path) -> None:
    """Gap findings always rest on exact glyph geometry (medium); an
    earlier-line leader depends on inferring that two rows are one entry (low)."""

    gap_dir = tmp_path / "gap"
    gap_dir.mkdir()
    gap_rows = [(108.0, 140.0, _entry("1.1 Map of the survey area", 5, 4))]
    gap = _p018(_render(gap_dir, "LIST OF FIGURES", gap_rows), GAP_ISSUE)
    assert [f.details["confidence"] for f in gap] == ["medium"]

    early_dir = tmp_path / "early"
    early_dir.mkdir()
    early_rows = [
        (108.0, 140.0, f"1.1 Sampling design for the long survey {DOTS}"),
        (130.0, 154.0, "of the coastal sites"),
        (540.0, 154.0, "5"),
    ]
    early = _p018(_render(early_dir, "TABLE OF CONTENTS", early_rows), EARLY_ISSUE)
    assert [f.details["confidence"] for f in early] == ["low"]
