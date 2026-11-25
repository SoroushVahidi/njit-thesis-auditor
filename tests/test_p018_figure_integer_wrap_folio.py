"""Controls for the folio on a first hanging figure row with a title number."""
import pytest
from test_standalone_folio_ownership import _doc, _line, _p018, _peer

from njit_auditor.pdf_models import format_bbox_detail
from njit_auditor.rules.pdf_toc_alignment import (
    detect_toc_like_pages,
    extract_toc_logical_entry_lines,
)
from njit_auditor.toc_list_student_preview import p018_short_suggested_fix

MISSING = "missing_page_number"


def _example(*, tail="13 dBm, and another value.", following="3.8", edge=540, peers=3,
             first_title="A synthetic title continues at the end of this typography row"):
    return [
        *[_peer(115 + i * 24, i + 1) for i in range(peers)],
        _line(205, (f"3.7 {first_title}", 108, 510)),
        _line(219, (tail, 149, 453), ("30", edge - 12, edge)),
        _line(242, (f"{following} Next dotted figure entry ....", 108, 464), ("34", 528, 540)),
    ]


def test_first_hanging_figure_row_retains_its_destination_folio():
    doc = _doc(_example())
    context, = detect_toc_like_pages(doc)
    ordinary = extract_toc_logical_entry_lines(context)
    presence = extract_toc_logical_entry_lines(context, recover_displaced_leader_folio=True)

    assert [row.page_number_token for row in ordinary[-3:]] == [None, "30", "34"]
    assert [row.page_number_token for row in presence[-2:]] == ["30", "34"]
    affected = presence[-2]
    assert affected.is_wrapped
    assert affected.page_number_line is not None
    assert affected.page_number_line.bbox.y0 == 219
    assert not _p018(doc, MISSING)
    assert not _p018(doc, "misaligned_page_number_column")


@pytest.mark.parametrize(
    ("options", "heading"),
    [
        ({"tail": "13.1 Distinct numbered figure entry."}, "LIST OF FIGURES"),
        ({"tail": "13 Distinct numbered figure entry."}, "LIST OF FIGURES"),
        ({"following": "4.1"}, "LIST OF FIGURES"),
        ({"edge": 467}, "LIST OF FIGURES"),
        ({"peers": 0}, "LIST OF FIGURES"),
        ({"first_title": "This title stops."}, "LIST OF FIGURES"),
        ({}, "TABLE OF CONTENTS"),
        ({}, "LIST OF TABLES"),
    ],
)
def test_unsupported_numeric_rows_keep_the_missing_folio_finding(options, heading):
    rows = _example(**options)
    finding, = _p018(_doc(rows, heading), MISSING)
    assert finding.page == 12
    assert finding.details["bbox"] == format_bbox_detail(rows[-3].bbox)
    assert p018_short_suggested_fix(MISSING).startswith("Add")
