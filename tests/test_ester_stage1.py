"""November 9/10 authority and section-ownership regressions; synthetic text only."""

import json

import fitz
import pytest

from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.report_outputs import (
    audit_findings_to_json_dict,
    write_json_report,
    write_markdown_report,
)
from njit_auditor.report_text import write_text_report
from njit_auditor.report_view import build_report_view
from njit_auditor.rules.pdf_frontmatter_no_page_number import check_pdf_frontmatter_no_page_number
from njit_auditor.rules.pdf_page_numbering_regime import check_pdf_page_numbering_regime
from njit_auditor.rules.pdf_roman_section_anchors import check_pdf_roman_section_anchors
from njit_auditor.rules.pdf_roman_sequence import check_pdf_roman_sequence
from njit_auditor.rules.pdf_toc_alignment import check_pdf_toc_alignment
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
def test_missing_dot_review_precedes_case_and_indent(tmp_path, number, x, ambiguous):
    rows = [(138, 140, "5.4 Methods for the Study .... 10"),
            (170, 165, "5.4.1 Initial calibration procedure .... 11"),
            (x, 190, f"{number} Further calibration procedure .... 12"),
            (138, 215, "5.5 Results of the Study .... 13")]
    doc = _pdf(tmp_path, [("TABLE OF CONTENTS", "vii", rows)])
    structural = check_pdf_toc_entry_number_ordering(doc)
    case = check_pdf_toc_list_formatting(doc)
    assert bool(structural) == ambiguous
    assert bool(case) == (not ambiguous and number != "5.4.2")
    assert not [f for f in check_pdf_toc_alignment(doc)
                if f.details["issue_type"] == "inconsistent_hierarchy_indent"]
    if ambiguous:
        assert structural[0].details["possible_section_number"] == "5.4.2"
        assert structural[0].details["bbox"]


@pytest.mark.parametrize("number", ["5.12", "5.42"])
@pytest.mark.parametrize("indent", [138, 170])
def test_two_digit_level_two_keeps_case_and_indent_checks(tmp_path, number, indent):
    rows = [(138, 140, "5.10 Initial Methods .... 10"),
            (138, 165, "5.11 Further Methods .... 11"),
            (indent, 190, f"{number} Further calibration procedure .... 12"),
            (138, 215, "5.43 Final Methods .... 13")]
    doc = _pdf(tmp_path, [("TABLE OF CONTENTS", "vii", rows)])
    assert check_pdf_toc_entry_number_ordering(doc) == []
    case = check_pdf_toc_list_formatting(doc)
    assert [f.details["entry_index"] for f in case] == ["2"]
    alignment = [f for f in check_pdf_toc_alignment(doc)
                 if f.details["issue_type"] == "inconsistent_hierarchy_indent"]
    assert bool(alignment) == (indent == 170)
    if alignment:
        assert alignment[0].details["worst_entry_index"] == "2"
        assert alignment[0].details["worst_delta_pt"] == "32.0"


def test_missing_dot_does_not_hide_neighbor_or_other_page_indent(tmp_path):
    def pages(number):
        return [("TABLE OF CONTENTS", "vii", [
            (138, 140, "5.1 Initial Methods .... 10"),
            (138, 165, "5.4 Further Methods .... 11"),
            (170, 190, "5.4.1 Initial calibration procedure .... 12"),
            (170, 215, f"{number} Further calibration procedure .... 13"),
            (155, 240, "5.5 Final Methods .... 14"),
            (138, 265, "5.6 Other Methods .... 15"),
        ]), ("TABLE OF CONTENTS (Continued)", "viii", [
            (138, 140, "6.1 Initial Methods .... 16"),
            (138, 165, "6.2 Further Methods .... 17"),
            (170, 190, "6.3 Final Methods .... 18"),
            (138, 215, "6.4 Other Methods .... 19"),
        ])]

    corrected = _pdf(tmp_path, pages("5.4.2"))
    ambiguous = _pdf(tmp_path, pages("5.42"))
    expected = check_pdf_toc_alignment(corrected)
    actual = check_pdf_toc_alignment(ambiguous)
    assert actual == expected
    hierarchy = [f for f in actual
                 if f.details["issue_type"] == "inconsistent_hierarchy_indent"]
    assert [(f.page, f.details["worst_entry_index"]) for f in hierarchy] == [(1, "4"), (2, "2")]
    assert [f.details["affected_entry_count"] for f in hierarchy] == ["1", "1"]


def test_missing_dot_precedence_survives_student_exports(tmp_path):
    rows = [(138, 140, "5.4 Methods for the Study .... 10"),
            (170, 165, "5.4.1 Initial calibration procedure .... 11"),
            (170, 190, "5.42 Further calibration procedure .... 12"),
            (138, 215, "5.5 Results of the Study .... 13")]
    doc = _pdf(tmp_path, [("TABLE OF CONTENTS", "vii", rows)])
    structural = check_pdf_toc_entry_number_ordering(doc)
    findings = (structural + check_pdf_toc_alignment(doc)
                + check_pdf_toc_list_formatting(doc))
    assert findings == structural
    assert len(structural) == 1
    metadata = {"audit_type": "pdf", "input_file_name": "synthetic.pdf"}
    json_path = tmp_path / "report.json"
    write_json_report(findings, metadata, json_path)
    payload = json.loads(json_path.read_text())
    exported = payload["findings"]
    assert len(exported) == 1
    assert exported[0]["public_rule_id"] == "R060"
    assert exported[0]["page"] == 1
    assert exported[0]["details"]["bbox"] == structural[0].details["bbox"]
    assert exported[0]["details"]["possible_section_number"] == "5.4.2"
    view = build_report_view(payload)
    assert len(view.findings) == 1
    assert view.findings[0].issue_type == "toc_subsection_number_ambiguous"
    assert view.findings[0].page == 1
    assert view.findings[0].bbox is not None
    assert "5.4.2" in view.findings[0].suggested_fix
    for writer, extension in [(write_markdown_report, "md"), (write_text_report, "txt")]:
        path = tmp_path / f"report.{extension}"
        writer(findings, metadata, path)
        text = path.read_text()
        assert "5.4.2" in text
        assert "R060" in text
        assert "R018" not in text
        assert "R024" not in text


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


def test_abstract_prose_does_not_create_copyright_boundary(tmp_path):
    doc = _pdf(tmp_path, [
        ("ABSTRACT", None, []),
        (None, "ii", [(108, 140, "We study copyright protection in digital archives.")]),
        (None, "iii", [(108, 140, "The abstract continues with the experimental results.")]),
        (None, None, [(108, 140, "Submitted in partial fulfillment of requirements at NJIT")]),
        (None, None, [(210, 300, "Copyright 2026")]),
        ("APPROVAL PAGE", None, []),
        ("BIOGRAPHICAL SKETCH", "iv", []),
        ("CHAPTER 1 INTRODUCTION", "1", []),
    ])
    assert [(f.page, f.details["page_type"]) for f in
            check_pdf_frontmatter_no_page_number(doc)] == [(2, "abstract"), (3, "abstract")]
    assert check_pdf_roman_sequence(doc) == []


@pytest.mark.parametrize("front_abstract", [True, False])
def test_body_abstract_is_not_reclassified_as_frontmatter(tmp_path, front_abstract):
    # In a partial manuscript without TOC/biosketch, the chapter remains the
    # boundary even when a later page has a recognizable list heading.
    pages = [("ABSTRACT", None, [])] if front_abstract else []
    doc = _pdf(tmp_path, pages + [
        ("CHAPTER 1 INTRODUCTION", "1", []),
        ("ABSTRACT", "2", [(108, 140, "A chapter-specific summary appears here.")]),
        ("LIST OF FIGURES", "3", []),
    ])
    assert check_pdf_frontmatter_no_page_number(doc) == []


@pytest.mark.parametrize("notice", ["Copyright 2026", "Copyright", "Copyright (c) 2026",
                                    "(c) 2026", "© 2026", "© Alex Test", "Copyright by Alex Test"])
def test_copyright_notice_still_ends_abstract_and_forbids_folio(tmp_path, notice):
    doc = _pdf(tmp_path, [
        ("ABSTRACT", None, []),
        (None, None, [(108, 140, "An unnumbered abstract continuation.")]),
        (None, "ii", [(210, 300, notice)]),
        ("APPROVAL PAGE", None, []),
        ("BIOGRAPHICAL SKETCH", "iv", []),
        ("CHAPTER 1 INTRODUCTION", "1", []),
    ])
    assert [(f.page, f.details["page_type"]) for f in
            check_pdf_frontmatter_no_page_number(doc)] == [(3, "copyright_page")]


@pytest.mark.parametrize("missing", [None, "cm", "2"])
@pytest.mark.parametrize("last,issue", [("vi", None), ("iv", "roman_sequence_repeat"),
                                       ("iii", "roman_sequence_decrease")])
def test_unreadable_folio_keeps_physical_count_and_endpoint_checks(tmp_path, missing, last, issue):
    doc = _pdf(tmp_path, [
        ("BIOGRAPHICAL SKETCH", "iv", []),
        (None, missing, []),
        ("ACKNOWLEDGEMENTS", last, []),
        ("CHAPTER 1 INTRODUCTION", "1", []),
    ])
    assert [f.details["issue_type"] for f in check_pdf_roman_sequence(doc)] == (
        [issue] if issue else [])
