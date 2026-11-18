"""Neutral synthetic cases for Ester's November 17 context corrections."""
from __future__ import annotations

import pytest
from test_ester_r018_r024_r040_regressions import _doc as list_doc
from test_heading_split_number_title import _doc as body_doc
from test_heading_split_number_title import _words_line

from njit_auditor.pdf_models import PdfDocument
from njit_auditor.rules.pdf_heading_levels import check_pdf_heading_level_styles
from njit_auditor.rules.pdf_lot_lof_entry_type import check_pdf_lot_lof_entry_type
from njit_auditor.rules.pdf_title_capitalization import check_pdf_title_capitalization
from njit_auditor.rules.pdf_toc_alignment import (
    detect_toc_like_pages,
    extract_toc_logical_entry_lines,
)
from njit_auditor.rules.pdf_toc_list_formatting import (
    _classify_toc_level,
    check_pdf_toc_list_formatting,
)


def toc(label: str, title: str = "Detailed synthetic results") -> PdfDocument:
    return list_doc("TABLE OF CONTENTS", [
        ("APPENDIX B SYNTHETIC EXAMPLES .... 90", 108, 540, 140),
        ("B.1 Reference Methods .... 91", 126, 540, 164),
        (f"{label} {title} .... 92", 126, 540, 188),
    ])


@pytest.mark.parametrize("root", ["A", "B", "I", "Z", "1", "12"])
@pytest.mark.parametrize("tail,level", [(".1", 2), (".1.7", 3), (".1.7.2", None),
                                       (".1.7.2.3", None)])
def test_numbering_depth_precedes_toc_indentation(root, tail, level):
    doc = toc(root + tail)
    entries = extract_toc_logical_entry_lines(detect_toc_like_pages(doc)[0])
    assert _classify_toc_level(entries[-1], [108, 126]) == level


def test_reported_appendix_sentence_case_is_not_requested_in_title_case():
    assert check_pdf_toc_list_formatting(toc("B.1.7")) == []


@pytest.mark.parametrize("label", ["B.1.7", "1.1.7"])
def test_genuine_level3_excess_capitals_are_preserved(label):
    (finding,) = check_pdf_toc_list_formatting(toc(label, "Detailed Synthetic Results"))
    assert finding.details["entry_level"] == "3"
    assert finding.details["source_q_rule_id"] == "Q051"
    assert "sentence case" in finding.message


@pytest.mark.parametrize("label", ["B.2", "1.2"])
def test_genuine_level2_lowercase_major_word_is_preserved(label):
    (finding,) = check_pdf_toc_list_formatting(toc(label))
    assert finding.details["entry_level"] == "2"
    assert check_pdf_toc_list_formatting(toc(label, "Detailed Synthetic Results")) == []


def test_continued_toc_and_wrapped_appendix_entry():
    doc = list_doc("TABLE OF CONTENTS (Continued)", [
        ("APPENDIX B SYNTHETIC EXAMPLES .... 90", 108, 540, 140),
        ("B.1 Reference Methods .... 91", 126, 540, 164),
        ("B.1.7 Detailed synthetic", 126, 490, 188),
        ("results .... 92", 150, 540, 203),
    ])
    assert check_pdf_toc_list_formatting(doc) == []


@pytest.mark.parametrize("label,level", [("A.1", 2), ("B.1.7", 3),
                                        ("B.1.7.2", 4), ("B.1.7.2.3", 5), ("2.1.7", 3)])
def test_body_appendix_depth_and_true_positives(label, level):
    text = "detailed synthetic results" if level == 2 else "Detailed Synthetic Results"
    doc = body_doc(_words_line([f"{label} {text}"], 108))
    findings = check_pdf_heading_level_styles(doc)
    assert any(f.details["inferred_level"] == str(level) for f in findings)
    if level >= 3:
        assert check_pdf_title_capitalization(doc) == []


def test_split_appendix_number_and_sentence_case_title():
    doc = body_doc(_words_line(["B.1.7"], 108),
                   _words_line(["Detailed", "synthetic", "results"], 149))
    assert check_pdf_heading_level_styles(doc) == []
    assert check_pdf_title_capitalization(doc) == []


@pytest.mark.parametrize("text", ["68.4 percent of participants responded.",
                                 "B.1.7 identifies a specimen in this paragraph.",
                                 "1.1.7 is a software version label."])
def test_plain_numeric_and_specimen_labels_are_not_headings(text):
    doc = body_doc(_words_line(text.split(), 108, bold=False))
    assert check_pdf_heading_level_styles(doc) == []
    assert check_pdf_title_capitalization(doc) == []


@pytest.mark.parametrize("label", ["1.1", "B.1", "I.1", "1.2.3", "Figure 1.1"])
def test_lof_heading_and_numeric_entries_are_valid(label):
    doc = list_doc("LIST OF FIGURES", [(f"{label} Synthetic description. .... 12",108,540,140)])
    assert check_pdf_lot_lof_entry_type(doc) == []


def test_numeric_multiline_lof_entry_and_continued_page():
    doc = list_doc("LIST OF FIGURES (Continued)", [
        ("B.1 Synthetic description with a reference to Fig. 2.1",108,510,140),
        ("and its continuation. .... 12",150,540,155),
        ("B.2 Another synthetic description. .... 13",108,540,180),
        ("B.3 Final synthetic description. .... 14",108,540,205),
    ])
    assert check_pdf_lot_lof_entry_type(doc) == []


@pytest.mark.parametrize("text,expected", [
    ("The results are shown in Figure 2.1.", 0),
    ("The results are shown in Fig. 2.1.", 1),
    ("See Fig. B.1 for the measured results.", 1),
    ("Fig. 2.1 shows the measured results.", 1),
    ("The label 2.1 identifies a measurement.", 0),
    ("The word fig describes a fruit.", 0),
    ("Figure 2.1 Synthetic caption describing the measured results.", 0),
    ("Fig. 2.1 Synthetic caption describing the measured results.", 0),
])
def test_body_reference_context(text, expected):
    doc = body_doc(_words_line([text], 108, bold=False))
    findings = check_pdf_lot_lof_entry_type(doc)
    assert len(findings) == expected
    assert all(f.details['issue_type'] == 'body_figure_reference_abbreviated' for f in findings)


def test_wrapped_reference_and_page_boundary():
    first = _words_line(["The results are shown in Fig."],108,bold=False)
    second = _words_line(["2.1 with further explanation."],108,bold=False,y0=316)
    doc = body_doc(first,second,same_block=True)
    assert len(check_pdf_lot_lof_entry_type(doc)) == 1
    doc.pages[0].text_blocks[0].lines = [first]
    other = body_doc(second)
    other.pages[0].page_number = 6
    doc.pages.extend(other.pages)
    assert check_pdf_lot_lof_entry_type(doc) == []


def test_lof_and_body_with_same_identifier_remain_independent():
    doc = list_doc("LIST OF FIGURES", [("2.1 Synthetic description. .... 12",108,540,140)])
    doc.pages += body_doc(_words_line(["See Fig. 2.1 for the results."],108,bold=False)).pages
    (finding,) = check_pdf_lot_lof_entry_type(doc)
    assert finding.page == 5
    assert finding.details['section_type'] == 'body'


def test_legacy_guidance_no_longer_demands_lof_prefix():
    from njit_auditor.polished_comments import resolve_suggested_fix_for_display
    fix = resolve_suggested_fix_for_display('P055','lof_entry_missing_figure_prefix')
    assert 'not required' in fix
    assert 'Prepend' not in fix


def test_export_and_report_preserve_body_advice():
    from njit_auditor.report_outputs import audit_findings_to_json_dict
    from njit_auditor.report_view import build_report_view
    findings = check_pdf_lot_lof_entry_type(body_doc(
        _words_line(["See Fig. 2.1 for the results."],108,bold=False)))
    assert len(findings) == 1
    exported = audit_findings_to_json_dict(findings, metadata={})
    view = build_report_view(exported)
    assert "body_figure_reference_abbreviated" in str(exported)
    assert "full word" in str(exported)
    assert "full word" in str(view)
    assert "Begin this List of Figures" not in str(exported) + str(view)


@pytest.mark.parametrize("label", ["B.1.7", "2.1.7"])
def test_glued_number_boundary_keeps_sentence_case_out_of_title_case(label):
    doc = body_doc(_words_line([label + "Detailed synthetic results"], 108))
    assert check_pdf_title_capitalization(doc) == []


def test_split_appendix_title_case_violation_is_still_found():
    doc = body_doc(_words_line(["B.1.7"], 108),
                   _words_line(["Detailed", "Synthetic", "Results"], 149))
    (finding,) = check_pdf_heading_level_styles(doc)
    assert finding.details["inferred_level"] == "3"


def test_caption_and_column_header_checks_are_preserved():
    from njit_auditor.rules.pdf_captions import check_pdf_captions
    from njit_auditor.rules.pdf_lot_lof_column_headers import check_pdf_lot_lof_column_headers
    caption = body_doc(_words_line(
        ["Figure 2.1 A synthetic description of the measured experimental results"], 108))
    assert check_pdf_lot_lof_entry_type(caption) == []
    assert any(f.details['issue_type'] == 'missing_terminal_punctuation'
               for f in check_pdf_captions(caption))
    lof = list_doc("LIST OF FIGURES", [
        ("1.1 Synthetic first description. .... 10", 108, 540, 140),
        ("1.2 Synthetic second description. .... 11", 108, 540, 164),
        ("1.3 Synthetic third description. .... 12", 108, 540, 188),
    ])
    assert check_pdf_lot_lof_entry_type(lof) == []
    assert check_pdf_lot_lof_column_headers(lof)


def test_real_pdf_extraction_keeps_appendix_and_figure_context(tmp_path):
    from reportlab.pdfgen.canvas import Canvas

    from njit_auditor.pdf_layout import load_pdf_layout
    path = tmp_path / 'synthetic.pdf'
    canvas = Canvas(str(path), pagesize=(612, 792))
    canvas.setFont('Times-Bold', 12)
    canvas.drawString(200, 712, 'TABLE OF CONTENTS')
    for y, x, text in [(652, 108, 'APPENDIX B SYNTHETIC EXAMPLES'),
                       (628, 126, 'B.1 Reference Methods'),
                       (604, 126, 'B.1.7 Detailed synthetic results')]:
        canvas.drawString(x, y, text)
        canvas.drawRightString(540, y, '92')
    canvas.showPage()
    canvas.setFont('Times-Bold', 12)
    canvas.drawString(200, 712, 'LIST OF FIGURES')
    canvas.setFont('Times-Roman', 12)
    for y, number in [(652, '1.1'), (628, '1.2'), (604, '1.3')]:
        canvas.drawString(108, y, f'{number} Synthetic description.')
        canvas.drawRightString(540, y, '12')
    canvas.showPage()
    canvas.setFont('Times-Roman', 12)
    canvas.drawString(108, 492, 'See Fig. 1.1 for the measured results.')
    canvas.save()
    doc = load_pdf_layout(str(path))
    assert check_pdf_toc_list_formatting(doc) == []
    (finding,) = check_pdf_lot_lof_entry_type(doc)
    assert finding.page == 3
    assert finding.details['section_type'] == 'body'
