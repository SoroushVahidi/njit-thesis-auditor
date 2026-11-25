"""Controls for a folio and wrapped-title punctuation in one PDF text span."""
import pytest
from test_standalone_folio_ownership import _doc, _line, _p018, _peer

from njit_auditor.pdf_models import format_bbox_detail
from njit_auditor.rules.pdf_toc_alignment import (
    detect_toc_like_pages,
    extract_toc_logical_entry_lines,
)
from njit_auditor.toc_list_student_preview import p018_short_suggested_fix

MISSING = "missing_page_number"


def _example(*, ending="(a synthetic measurement).118", edge=540, peers=4):
    return [
        *[_peer(115 + i * 24, i + 1) for i in range(peers)],
        _line(300, ("3.7 The title of a long illustration continues", 108, 510)),
        _line(315, (f"on the following row {ending}", 149, edge)),
        _line(750, ("xv", 300, 316)),
    ]


def test_final_hanging_glued_folio_requires_p018_presence_projection():
    doc = _doc(_example())
    context, = detect_toc_like_pages(doc)
    ordinary = extract_toc_logical_entry_lines(context)
    presence = extract_toc_logical_entry_lines(context, recover_displaced_leader_folio=True)

    assert ordinary[-1].page_number_token is None
    affected = presence[-1]
    assert affected.is_wrapped
    assert affected.page_number_token == "118"
    assert affected.page_number_right_x == 540
    assert affected.page_number_line is not None
    assert affected.page_number_line.bbox.y0 == 315
    assert not _p018(doc, MISSING)
    assert not _p018(doc, "misaligned_page_number_column")


@pytest.mark.parametrize(
    ("options", "heading"),
    [
        ({"ending": "for approximately 15.118"}, "LIST OF FIGURES"),
        ({"ending": "for model V.118"}, "LIST OF FIGURES"),
        ({"ending": "(a synthetic measurement)."}, "LIST OF FIGURES"),
        ({"edge": 465}, "LIST OF FIGURES"),
        ({"peers": 2}, "LIST OF FIGURES"),
        ({}, "LIST OF TABLES"),
        ({}, "TABLE OF CONTENTS"),
    ],
)
def test_excluded_final_rows_keep_missing_folio_advice(options, heading):
    rows = _example(**options)
    finding, = _p018(_doc(rows, heading), MISSING)
    assert finding.page == 12
    assert finding.details["affected_entry_count"] == "1"
    first, tail = rows[-3].bbox, rows[-2].bbox
    assert finding.details["bbox"] == format_bbox_detail(
        (first.x0, first.y0, max(first.x1, tail.x1), tail.y1)
    )
    assert p018_short_suggested_fix(MISSING).startswith("Add")
