"""R045 spacing findings carry the geometry of the lines they describe.

Ester (2026-10-05) confirmed Patrick's Bio Sketch publications were not single
spaced; the auditor reported it without a highlight. The wrapped-spacing
finding now highlights the offending entry, and the missing-blank-line finding
highlights the two entry lines that sit too close.
"""

from __future__ import annotations

from pathlib import Path
from statistics import median

import pytest
from test_r045_no_numbering_20261006 import _biosketch, _entry, _findings

from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.rules.pdf_biosketch_publication_layout import (
    BLANK_LINE_MIN_PITCH_RATIO,
    _find_biosketch_page_and_heading_y,
    _line_step,
    _publication_section_rows,
    _Row,
    _split_entries,
    check_pdf_biosketch_publication_layout,
)


def _box(details: dict[str, str]) -> tuple[float, ...]:
    return tuple(float(v) for v in details["bbox"].split(","))


def test_wrapped_spacing_finding_highlights_the_offending_entry(tmp_path: Path) -> None:
    path = _biosketch(
        tmp_path / "double.pdf",
        [_entry("Author, A.", lines=3), _entry("Author, B.", lines=3)],
        line_step=24.0,
        entry_step=40.0,
    )
    (details,) = _findings(path)
    x0, y0, x1, y1 = _box(details)
    assert x0 <= 108.5 and x1 > 400  # the entry's rows, left edge to text end
    assert 2 * 24.0 - 1 <= y1 - y0 <= 3 * 24.0  # three rows of the first entry


def test_entry_gap_finding_highlights_the_two_adjacent_lines(tmp_path: Path) -> None:
    path = _biosketch(
        tmp_path / "tight.pdf",
        [_entry("Author, A."), _entry("Author, B."), _entry("Author, C.")],
        entry_step=14.0,
    )
    (details,) = _findings(path)
    _x0, y0, _x1, y1 = _box(details)
    assert y1 - y0 < 3 * 14.0  # last line of one entry and first of the next only


def test_line_step_ignores_an_accent_extending_only_the_upper_bbox_edge() -> None:
    earlier = _Row(108.0, 100.0, 112.0, "entry", 12.0, baseline_y=109.4)
    later = _Row(108.0, 121.0, 136.4, "accented entry", 12.0, baseline_y=133.8)
    assert _line_step(earlier, later) == pytest.approx(24.4)


def test_line_step_retains_smaller_bbox_edge_fallback_without_baselines() -> None:
    earlier = _Row(108.0, 100.0, 112.0, "entry", 12.0)
    later = _Row(108.0, 121.0, 136.4, "entry", 12.0)
    assert _line_step(earlier, later) == pytest.approx(21.0)


@pytest.mark.parametrize(
    ("entry_step", "expected_issue"),
    [
        (21.1, None),
        (20.9, "biosketch_publication_entry_spacing_not_double"),
    ],
)
def test_blank_line_pitch_boundary_with_wrapped_entries(
    tmp_path: Path, entry_step: float, expected_issue: str | None
) -> None:
    """At 14 pt within-entry pitch, the existing 1.5 ratio divides these cases."""
    path = _biosketch(
        tmp_path / "boundary.pdf",
        [_entry("Author, A.", lines=3), _entry("Author, B.", lines=3)],
        line_step=14.0,
        entry_step=entry_step,
    )
    issues = [details["issue_type"] for details in _findings(path)]
    assert issues == ([] if expected_issue is None else [expected_issue])


def test_baseline_step_preserves_a_tight_gap_despite_raised_bbox_top() -> None:
    earlier = _Row(108.0, 100.0, 112.0, "last wrapped line", 12.0, baseline_y=109.4)
    later = _Row(108.0, 116.9, 131.0, "accented next entry", 12.0, baseline_y=128.3)
    assert _line_step(earlier, later) == pytest.approx(18.9)


@pytest.mark.parametrize(
    ("filename", "sha256", "page_number", "entry_count", "affected_index"),
    [
        (
            "250204 Kang Qi PhD dissertation_1st review with EF comments.pdf",
            "a32c811163a0b3c86377ccf08221a6b0fffd4695b1283d61d3774c733b3f821c",
            5,
            5,
            2,
        ),
        (
            "250218 Cibaku Elson First Review.pdf",
            "234f6c951a2a6a07308a771af434628658ddc84f9684c54e51f6c9423ac6d6ad",
            6,
            6,
            1,
        ),
    ],
)
def test_near_threshold_real_publication_gaps_are_not_false_warnings(
    filename: str, sha256: str, page_number: int, entry_count: int, affected_index: int
) -> None:
    import hashlib

    path = Path(__file__).resolve().parents[1] / "data/raw/ester" / filename
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest == sha256
    document = load_pdf_layout(str(path))
    located = _find_biosketch_page_and_heading_y(document)
    assert located is not None
    page, heading_y = located
    assert page.page_number == page_number
    entries, method = _split_entries(_publication_section_rows(page, heading_y))
    assert method == "hanging_indent"
    assert len(entries) == entry_count
    within = [_line_step(a, b) for entry in entries for a, b in zip(entry, entry[1:])]
    boundary = _line_step(entries[affected_index][-1], entries[affected_index + 1][0])
    assert median(within) == pytest.approx(14.446, abs=0.01)
    assert boundary == pytest.approx(24.409, abs=0.01)
    assert boundary > BLANK_LINE_MIN_PITCH_RATIO * median(within)
    findings = check_pdf_biosketch_publication_layout(document)
    assert [
        finding
        for finding in findings
        if finding.details.get("issue_type") == "biosketch_publication_entry_spacing_not_double"
    ] == []
