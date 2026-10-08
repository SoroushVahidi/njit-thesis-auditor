"""R045 spacing findings carry the geometry of the lines they describe.

Ester (2026-10-05) confirmed Patrick's Bio Sketch publications were not single
spaced; the auditor reported it without a highlight. The wrapped-spacing
finding now highlights the offending entry, and the missing-blank-line finding
highlights the two entry lines that sit too close.
"""

from __future__ import annotations

from pathlib import Path

from test_r045_no_numbering_20261006 import _biosketch, _entry, _findings


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
