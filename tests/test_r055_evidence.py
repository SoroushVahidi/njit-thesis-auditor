"""Synthetic controls for R055 evidence, confidence, appendix and singleton scope."""

import pytest
from test_r055_lof_segmentation import _doc, _line

from njit_auditor.rules.pdf_lot_lof_entry_type import check_pdf_lot_lof_entry_type


def _entry(y=140, label="2.1", number="12"):
    return _line(
        y,
        (label, 108, 128),
        ("Synthetic list entry", 140, 400),
        ("........", 450, 510),
        (number, 528, 540),
    )


def _list(*entries, heading="LIST OF FIGURES"):
    return _doc([_line(80, (heading, 180, 360)), *entries])


def test_singleton_missing_prefix_has_exact_trace_and_high_confidence():
    (finding,) = check_pdf_lot_lof_entry_type(_list(_entry()))
    assert finding.details["issue_type"] == "lof_entry_missing_figure_prefix"
    assert finding.details["bbox"] == "108.0,140.0,128.0,152.0"
    assert finding.details["page_number_bbox"] == "528.0,140.0,540.0,152.0"
    assert finding.details["confidence"] == "high"
    assert finding.details["entry_id"].startswith("list-entry-")
    assert "Synthetic" not in str(finding.details)


@pytest.mark.parametrize("label", ["A.1", "B.1", "C.1", "D.1", "E.1", "I.1", "V.1", "1.1"])
@pytest.mark.parametrize(
    "heading,issue",
    [
        ("LIST OF FIGURES", "lof_entry_missing_figure_prefix"),
        ("LIST OF TABLES", "lot_entry_missing_table_prefix"),
    ],
)
def test_appendix_and_numeric_labels_follow_same_prefix_policy(label, heading, issue):
    (finding,) = check_pdf_lot_lof_entry_type(_list(_entry(label=label), heading=heading))
    assert finding.details["issue_type"] == issue


@pytest.mark.parametrize(
    "heading,prefix", [("LIST OF FIGURES", "Figure"), ("LIST OF TABLES", "Table")]
)
def test_singleton_correct_appendix_prefix_is_not_reported(heading, prefix):
    assert check_pdf_lot_lof_entry_type(_list(_entry(label=f"{prefix} A.1"), heading=heading)) == []


def test_wrong_type_appendix_entry_stays_detectable():
    (finding,) = check_pdf_lot_lof_entry_type(_list(_entry(label="Table A.1")))
    assert finding.details["issue_type"] == "lof_entry_is_table"


def test_entry_id_survives_insertion_and_report_index_change():
    original = _entry(y=200)
    (old,) = check_pdf_lot_lof_entry_type(_list(original))
    new = check_pdf_lot_lof_entry_type(_list(_entry(y=140, label="1.1"), original))[-1]
    assert old.details["entry_index"] != new.details["entry_index"]
    assert old.details["entry_id"] == new.details["entry_id"]
    assert old.details["source_row_id"] == new.details["source_row_id"]


def test_glued_prefix_without_character_geometry_is_not_promoted():
    row = _line(
        140, ("2.1Synthetic entry without a measurable label boundary", 108, 510), ("12", 528, 540)
    )
    (finding,) = check_pdf_lot_lof_entry_type(_list(row))
    assert finding.details["confidence"] == "medium"
    assert finding.details["prefix_geometry"] == "entry_span_fallback"


def test_glued_prefix_with_character_geometry_has_a_tight_anchor():
    row = _line(140, ("2.1Synthetic entry", 108, 210), ("12", 528, 540))
    span = row.spans[0]
    span.char_x_bounds = [(108 + i * 6, 114 + i * 6) for i in range(len(span.text))]
    (finding,) = check_pdf_lot_lof_entry_type(_list(row))
    assert finding.details["bbox"] == "108.0,140.0,126.0,152.0"
    assert finding.details["confidence"] == "high"


def test_fragmented_label_without_a_reliable_boundary_is_not_promoted():
    row = _line(140, ("2.", 108, 120), ("1 Synthetic entry", 120, 400), ("12", 528, 540))
    (finding,) = check_pdf_lot_lof_entry_type(_list(row))
    assert finding.details["confidence"] == "medium"


def test_separately_stored_wrapped_folio_keeps_the_violation():
    doc = _list(
        _line(140, ("2.1 Synthetic entry with a wrapped", 108, 510)),
        _line(154, ("continuation and leaders........", 150, 510), ("12", 528, 540)),
    )
    (finding,) = check_pdf_lot_lof_entry_type(doc)
    assert finding.details["issue_type"] == "lof_entry_missing_figure_prefix"
    assert "bbox" in finding.details


def test_fragmented_folio_is_not_high_confidence():
    row = _line(
        140,
        ("2.1", 108, 128),
        ("Synthetic entry", 140, 400),
        ("........", 450, 510),
        ("1", 528, 534),
        ("2", 534, 540),
    )
    (finding,) = check_pdf_lot_lof_entry_type(_list(row))
    assert finding.details["confidence"] == "medium"


def test_roman_title_fragment_is_not_a_high_confidence_folio():
    row = _line(
        140, ("2.1", 108, 128), ("Synthetic continuation ending in", 140, 480), ("LC", 520, 540)
    )
    findings = check_pdf_lot_lof_entry_type(_list(row))
    assert all(f.details["confidence"] != "high" for f in findings)


@pytest.mark.parametrize(
    "text", ["12", "in a synthetic continuation", "C Ordinary capitalized prose"]
)
def test_singleton_noise_does_not_become_a_missing_prefix_warning(text):
    assert check_pdf_lot_lof_entry_type(_list(_line(140, (text, 108, 400)))) == []


def test_table_of_contents_is_outside_r055_scope():
    assert check_pdf_lot_lof_entry_type(_list(_entry(), heading="TABLE OF CONTENTS")) == []
