"""Controls for a displaced figure folio bracketed by independently paged entries."""
import pytest
from test_standalone_folio_ownership import _doc, _line, _p018, _peer

from njit_auditor.pdf_models import format_bbox_detail
from njit_auditor.toc_list_student_preview import p018_short_suggested_fix

MISSING = "missing_page_number"
MISALIGNED = "misaligned_page_number_column"


def _example(*, tail="finishing with an unpunctuated description", token="42",
             following="3.4", following_folio="56", following_edge=540):
    return [
        _peer(105, 1),
        _peer(129, 2),
        _line(162, ("3.2 Previous independent figure ....", 108, 460), ("39", 528, 540)),
        _line(205, ("3.3 Long figure title spans several printed rows", 108, 515)),
        _line(219, ("with a wrapped preceding line of text", 149, 495)),
        _line(233, (tail, 149, 480)),
        _line(259, (token, 149, 162)),
        _line(282, (f"{following} Following independent figure ....", 108, 460),
              (following_folio, following_edge - 12, following_edge)),
    ]


def test_confirmed_displaced_folio_gets_alignment_advice_on_its_numeral():
    rows = _example()
    document = _doc(rows)
    assert not _p018(document, MISSING)
    finding, = _p018(document, MISALIGNED)
    assert finding.page == 12
    assert finding.details["destination_folio"] == "42"
    assert finding.details["bbox"] == format_bbox_detail(rows[-2].bbox)
    assert finding.details["highlight_bboxes"] == format_bbox_detail(rows[-2].bbox)
    assert p018_short_suggested_fix(MISALIGNED).startswith("Align")


@pytest.mark.parametrize(
    ("options", "heading"),
    [
        ({"tail": "the calculated expression is x ="}, "LIST OF FIGURES"),
        ({"tail": "the variable y"}, "LIST OF FIGURES"),
        ({"token": "39"}, "LIST OF FIGURES"),
        ({"token": "56"}, "LIST OF FIGURES"),
        ({"token": "xiv"}, "LIST OF FIGURES"),
        ({"following": "4.4"}, "LIST OF FIGURES"),
        ({"following": "3.5"}, "LIST OF FIGURES"),
        ({"following_edge": 512}, "LIST OF FIGURES"),
        ({}, "LIST OF TABLES"),
        ({}, "TABLE OF CONTENTS"),
    ],
)
def test_unconfirmed_standalone_row_does_not_clear_missing_folio(options, heading):
    document = _doc(_example(**options), heading)
    finding, = _p018(document, MISSING)
    assert finding.page == 12
    assert finding.details["affected_entry_count"] == "1"
    assert p018_short_suggested_fix(MISSING).startswith("Add")
    assert all("destination_folio" not in item.details for item in _p018(document, MISALIGNED))


def test_numeral_between_hanging_rows_is_not_a_destination_folio():
    rows = _example()
    rows.insert(-1, _line(270, ("more of the same hanging caption", 149, 473)))
    finding, = _p018(_doc(rows), MISSING)
    assert finding.details["affected_entry_count"] == "1"
