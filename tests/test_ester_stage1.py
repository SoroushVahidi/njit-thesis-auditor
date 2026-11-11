"""November 9/10 authority and section-ownership regressions; synthetic text only."""

import fitz
import pytest

from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.report_outputs import audit_findings_to_json_dict
from njit_auditor.report_view import build_report_view
from njit_auditor.rules.pdf_frontmatter_no_page_number import check_pdf_frontmatter_no_page_number
from njit_auditor.rules.pdf_page_numbering_regime import check_pdf_page_numbering_regime
from njit_auditor.rules.pdf_roman_section_anchors import check_pdf_roman_section_anchors
from njit_auditor.rules.pdf_roman_sequence import check_pdf_roman_sequence
from njit_auditor.rules.pdf_toc_entry_number_ordering import check_pdf_toc_entry_number_ordering
from njit_auditor.rules.pdf_toc_list_formatting import check_pdf_toc_list_formatting


def _pdf(tmp_path, pages):
    path = tmp_path / "synthetic.pdf"
    doc = fitz.open()
    for heading, folio, lines in pages:
        page = doc.new_page(width=612, height=792)
        if heading:
            page.insert_text((210, 85), heading, fontsize=12, fontname="Times-Bold")
        if folio:
            page.insert_text((300, 770), folio, fontsize=12)
        for x, y, text in lines:
            page.insert_text((x, y), text, fontsize=10)
    doc.save(path)
    doc.close()
    return load_pdf_layout(str(path))


@pytest.mark.parametrize("continuations", [1, 2, 3])
@pytest.mark.parametrize("stray", [None, "ii", "2"])
@pytest.mark.parametrize("bio", ["iv", "v"])
def test_abstract_span_does_not_anchor_bio(tmp_path, continuations, stray, bio):
    pages = [("ABSTRACT", None, [])]
    pages += [(None, stray if i == 0 else None, [(108, 140, "Abstract prose continues here.")])
              for i in range(continuations)]
    pages += [(None, None, [(108, 140, "Submitted in partial fulfillment of the requirements"),
                           (108, 170, "Doctor of Philosophy, New Jersey Institute of Technology")]),
              (None, None, [(108, 300, "Copyright 2026")]),
              ("APPROVAL PAGE", None, []),
              ("BIOGRAPHICAL SKETCH", bio, []),
              ("ACKNOWLEDGEMENTS", "v" if bio == "iv" else "vi", []),
              ("CHAPTER 1 INTRODUCTION", "1", [])]
    doc = _pdf(tmp_path, pages)
    no_numbers = check_pdf_frontmatter_no_page_number(doc)
    assert [(f.page, f.details["page_type"]) for f in no_numbers] == (
        [(2, "abstract")] if stray else [])
    assert check_pdf_page_numbering_regime(doc) == []
    assert check_pdf_roman_sequence(doc) == []
    anchors = check_pdf_roman_section_anchors(doc)
    assert [f.details["issue_type"] for f in anchors] == (
        ["roman_bio_sketch_not_iv"] if bio == "v" else [])


@pytest.mark.parametrize("following,issue", [
    ("xxix", None), ("xxviii", "roman_sequence_repeat"),
    ("xxvii", "roman_sequence_decrease"), ("xxx", "roman_sequence_gap"),
])
@pytest.mark.parametrize("symbol", ["v", "m"])
def test_symbols_never_replace_actual_folio(tmp_path, following, issue, symbol):
    doc = _pdf(tmp_path, [
        ("TABLE OF CONTENTS", "xxviii", [(108, 700, symbol)]),
        (None, following, []), ("CHAPTER 1 INTRODUCTION", "1", []),
    ])
    assert [f.details["issue_type"] for f in check_pdf_roman_sequence(doc)] == (
        [issue] if issue else [])


@pytest.mark.parametrize("number,x,ambiguous", [("5.42", 170, True), ("5.42", 138, False),
                                               ("5.4.2", 170, False), ("5.12", 138, False)])
def test_missing_dot_review_precedes_case(tmp_path, number, x, ambiguous):
    rows = [(138, 140, "5.4 Methods for the Study .... 10"),
            (170, 165, "5.4.1 Initial calibration procedure .... 11"),
            (x, 190, f"{number} Further calibration procedure .... 12"),
            (138, 215, "5.5 Results of the Study .... 13")]
    doc = _pdf(tmp_path, [("TABLE OF CONTENTS", "vii", rows)])
    structural = check_pdf_toc_entry_number_ordering(doc)
    case = check_pdf_toc_list_formatting(doc)
    assert bool(structural) == ambiguous
    assert bool(case) == (not ambiguous and number != "5.4.2")
    if ambiguous:
        assert structural[0].details["possible_section_number"] == "5.4.2"
        assert structural[0].details["bbox"]


def test_list_case_actions_and_section_categories(tmp_path):
    doc = _pdf(tmp_path, [
        ("LIST OF TABLES", "viii", [(108, 140, "Table 1.1 Summary of measured results .... 12")]),
        ("LIST OF FIGURES", "ix", [
            (108, 140, "Figure 1.1 Summary of Measured Results .... 12"),
            (108, 165, "Figure 1.2 Summary of measured results .... 13"),
            (108, 190, "Figure 1.3 Results for NASA and FFT .... 14"),
            (108, 215, "Figure 1.4 Results for Markov and Fourier methods .... 15"),
            (108, 240, "Figure 1.5 First view. Second view. Third view. .... 16"),
        ]),
        ("CHAPTER 1 INTRODUCTION", "1", [
            (108, 140, "We use Markov and Fourier methods in the study."),
            (108, 165, "We compare Markov and Fourier methods again."),
            (108, 190, "We compare measured results with measured results.")]),
    ])
    findings = check_pdf_toc_list_formatting(doc)
    assert [(f.page, f.details["entry_index"]) for f in findings] == [(1, "0"), (2, "0")]
    view = build_report_view(audit_findings_to_json_dict(findings, {"audit_type": "pdf"}))
    assert {f.category for f in view.findings} == {"list_of_tables", "list_of_figures"}
    for finding in view.findings:
        if finding.category == "list_of_figures":
            assert "sentence case" in finding.suggested_fix
            assert "figure description" in finding.suggested_fix
            assert "table title" not in finding.suggested_fix
        else:
            assert "Title Case" in finding.suggested_fix
            assert "figure" not in finding.suggested_fix
