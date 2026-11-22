"""Synthetic PDF and report regressions for R063/N01."""

from pathlib import Path

import pymupdf
import pytest

from njit_auditor.audit_runner import collect_pdf_layout_findings
from njit_auditor.models import AuditFinding
from njit_auditor.pdf_highlight import _draw_boxes_for_page, get_pdf_page_sizes
from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.report_outputs import audit_findings_to_json_dict
from njit_auditor.report_view import build_report_view
from njit_auditor.rules import pdf_appendix_body_headings
from njit_auditor.web_app import _highlight_boxes_by_page

_ISSUE = "appendix_subsection_missing_letter_prefix"


def _page(doc: pymupdf.Document, heading: str = "") -> pymupdf.Page:
    page = doc.new_page(width=612, height=792)
    if heading:
        _heading(page, heading)
    return page


def _heading(page: pymupdf.Page, title: str, y: int = 104) -> None:
    page.insert_textbox(
        (108, y, 540, y + 28), title, fontname="Times-Bold", fontsize=14,
        align=pymupdf.TEXT_ALIGN_CENTER,
    )


def _body_line(
    page: pymupdf.Page, text: str, y: int = 170, *, bold: bool = True, x: int = 108,
) -> None:
    page.insert_text((x, y), text, fontname="Times-Bold" if bold else "Times-Roman", fontsize=12)


def _toc_line(
    page: pymupdf.Page, text: str, y: int, folio: str = "", *, x: int = 108,
) -> None:
    page.insert_text((x, y), text, fontname="Times-Roman", fontsize=12)
    if folio:
        page.insert_text((540 - 6 * len(folio), y), folio, fontname="Times-Roman", fontsize=12)


def _findings(path: Path) -> list[AuditFinding]:
    return pdf_appendix_body_headings.check_pdf_appendix_body_headings(load_pdf_layout(str(path)))


def _subsections(findings: list[AuditFinding]) -> list[tuple[int | None, str, str]]:
    return [
        (finding.page, finding.details["appendix_location"], finding.details["expected_identifier"])
        for finding in findings if finding.details["issue_type"] == _ISSUE
    ]


@pytest.mark.parametrize("text,expected", [
    ("A.1 Instrument Calibration", []),
    ("A.2 Instrument Calibration", []),
    (".1 Instrument Calibration", [(2, "body", "A.1")]),
])
def test_owned_subsection_under_single_bare_appendix(
    tmp_path: Path, text: str, expected: list[tuple[int, str, str]],
) -> None:
    path = tmp_path / "single.pdf"
    with pymupdf.open() as doc:
        _page(doc, "CHAPTER 1 INTRODUCTION")
        page = _page(doc, "APPENDIX")
        _body_line(page, text)
        doc.save(path)
    assert _subsections(_findings(path)) == expected


def test_abc_ownership_same_page_and_page_boundary(tmp_path: Path) -> None:
    path = tmp_path / "three_appendices.pdf"
    with pymupdf.open() as doc:
        _page(doc, "CHAPTER 1 INTRODUCTION")
        references = _page(doc, "REFERENCES")
        _body_line(references, "Invented Author. (2020). Technical report.", bold=False)
        page = _page(doc, "APPENDIX A")
        _body_line(page, "3", 43, bold=False, x=525)
        _body_line(page, ".2 Instrument Calibration")
        _heading(page, "APPENDIX B", 310)
        _body_line(page, "B.1.7 Valid sentence-case subsection", 380)
        _body_line(page, ".1 Measurement Setup", 706)
        page = _page(doc)
        _body_line(page, ".2 Boundary Check", 112)
        page = _page(doc, "APPENDIX C")
        _body_line(page, "C.1 Instrument Calibration")
        doc.save(path)
    findings = _findings(path)
    assert _subsections(findings) == [
        (3, "body", "A.2"), (3, "body", "B.1"), (4, "body", "B.2"),
    ]
    assert {finding.details["issue_type"] for finding in findings} == {_ISSUE}


@pytest.mark.parametrize("first,second,old_issue", [
    ("APPENDIX A", "APPENDIX", "multiple_appendix_missing_letter"),
    ("APPENDIX A", "APPENDIX A", "appendix_letter_sequence_repeat"),
])
def test_ambiguous_owner_keeps_existing_ownership_findings(
    tmp_path: Path, first: str, second: str, old_issue: str,
) -> None:
    path = tmp_path / "ambiguous.pdf"
    with pymupdf.open() as doc:
        _page(doc, first)
        page = _page(doc, second)
        _body_line(page, ".1 Measurement Setup")
        doc.save(path)
    assert [finding.details["issue_type"] for finding in _findings(path)] == [old_issue]


def test_body_negative_controls(tmp_path: Path) -> None:
    path = tmp_path / "negative.pdf"
    with pymupdf.open() as doc:
        chapter = _page(doc, "CHAPTER 1 INTRODUCTION")
        _body_line(chapter, ".1 Unowned Example")
        page = _page(doc, "APPENDIX")
        _body_line(page, ".1 percent of observations were excluded", 160)
        _body_line(page, ".2 Pa was recorded in the chamber", 185)
        _body_line(page, ".3 Sensors were checked before use", 210)
        _body_line(page, ".4 A = B + C", 235)
        _body_line(page, ".5 Author (2020)", 260)
        _body_line(page, ".6 The appendix is described in this paragraph.", 285)
        _body_line(page, "See Appendix A for a .7 measurement.", 310, bold=False)
        _body_line(page, "0.8 Measurement Setup", 335, bold=False)
        _body_line(page, ".9", 360)
        _body_line(page, "Instrument Calibration", 360, x=150, bold=False)
        _heading(page, "CHAPTER 2 CONCLUSION", 458)
        _body_line(page, ".1 Main Chapter Example", 512)
        page = _page(doc, "REFERENCES")
        _body_line(page, ".1 Source Layout Example")
        page = _page(doc)
        _body_line(page, ".2 Citation Continuation")
        doc.save(path)
    assert _findings(path) == []


def test_body_stops_at_unowned_appendix_continuation(tmp_path: Path) -> None:
    path = tmp_path / "unowned_continuation.pdf"
    with pymupdf.open() as doc:
        _page(doc, "APPENDIX")
        page = _page(doc, "APPENDIX (Continued)")
        _body_line(page, ".1 Instrument Setup")
        page = _page(doc, "APPENDIX B (Continued)")
        _body_line(page, ".2 Ambiguous Measurement")
        doc.save(path)
    assert _subsections(_findings(path)) == [(2, "body", "A.1")]


def test_toc_ownership_wrapped_title_and_detached_folios(tmp_path: Path) -> None:
    path = tmp_path / "toc.pdf"
    with pymupdf.open() as doc:
        toc = _page(doc, "TABLE OF CONTENTS")
        _toc_line(toc, "CHAPTER 1 INTRODUCTION", 158, "1")
        _toc_line(toc, ".1 Chapter Example", 179, "1", x=126)
        _toc_line(toc, "APPENDIX A MEASUREMENTS", 205, "70")
        _toc_line(toc, "A.1 Instrument Calibration", 226, "71", x=126)
        _toc_line(toc, ".2 Measurement Setup with", 248, x=126)
        _toc_line(toc, "a Wrapped Title", 264, "72", x=150)
        _toc_line(toc, "APPENDIX B RESULTS", 290, "80")
        _toc_line(toc, "B.1.7 Valid hierarchy", 311, "81", x=126)
        _toc_line(toc, ".1", 332, x=126)
        _toc_line(toc, "Instrument Results", 332, "82", x=151)
        _toc_line(toc, ". . . . .", 353, "83", x=126)
        _toc_line(toc, ".2 No Folio", 384, x=126)
        _toc_line(toc, ".3 Misaligned Folio 84", 412, x=126)
        _toc_line(toc, "REFERENCES", 442, "90")
        _toc_line(toc, ".1 Reference Entry", 464, "90", x=126)
        _page(doc, "CHAPTER 1 INTRODUCTION")
        _page(doc, "APPENDIX A")
        _page(doc, "APPENDIX B")
        doc.save(path)
    findings = _findings(path)
    assert _subsections(findings) == [
        (1, "table of contents", "A.2"), (1, "table of contents", "B.1"),
    ]
    assert all("bbox" in finding.details for finding in findings)


def test_toc_does_not_infer_prefix_under_ambiguous_bare_entries(tmp_path: Path) -> None:
    path = tmp_path / "ambiguous_toc.pdf"
    with pymupdf.open() as doc:
        toc = _page(doc, "TABLE OF CONTENTS")
        _toc_line(toc, "APPENDIX MEASUREMENTS", 160, "70")
        _toc_line(toc, ".1 Measurement Setup", 184, "71", x=126)
        _toc_line(toc, "APPENDIX RESULTS", 212, "80")
        _toc_line(toc, ".1 Instrument Results", 236, "81", x=126)
        _page(doc, "APPENDIX")
        doc.save(path)
    assert _findings(path) == []


def test_wrapped_body_heading_and_toc_continuation_keep_physical_pages(tmp_path: Path) -> None:
    path = tmp_path / "wrapped.pdf"
    with pymupdf.open() as doc:
        toc = _page(doc, "TABLE OF CONTENTS")
        _toc_line(toc, "APPENDIX MEASUREMENTS", 160, "70")
        toc = _page(doc, "TABLE OF CONTENTS (Continued)")
        _toc_line(toc, ".1 Instrument Setup", 180, "71", x=126)
        page = _page(doc, "APPENDIX")
        _body_line(page, ".1 Instrument Setup with a", 170)
        _body_line(page, "Wrapped Heading", 185, x=130)
        doc.save(path)
    assert _subsections(_findings(path)) == [
        (3, "body", "A.1"), (2, "table of contents", "A.1"),
    ]


@pytest.mark.parametrize("isolated_token", [False, True])
def test_number_only_highlight_and_unrelated_output_preservation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, isolated_token: bool,
) -> None:
    path = tmp_path / "report.pdf"
    with pymupdf.open() as doc:
        toc = _page(doc, "TABLE OF CONTENTS")
        _toc_line(toc, "CHAPTER 1 INTRODUCTION", 158, "1")
        _toc_line(toc, "APPENDIX MEASUREMENTS", 182, "70")
        _toc_line(toc, ".1 Measurement Setup", 206, "71", x=126)
        _page(doc, "CHAPTER 1 INTRODUCTION")
        page = _page(doc, "APPENDIX")
        _body_line(page, ".1" if isolated_token else ".1 Measurement Setup")
        if isolated_token:
            _body_line(page, "Measurement Setup", x=150)
        doc.save(path)

    doc_layout = load_pdf_layout(str(path))
    findings = collect_pdf_layout_findings(doc_layout, path)
    with monkeypatch.context() as patch:
        patch.setattr(pdf_appendix_body_headings, "check_appendix_subsections", lambda *_: [])
        baseline = collect_pdf_layout_findings(doc_layout, path)
        assert [finding for finding in findings if _ISSUE != finding.details.get("issue_type")] == (
            baseline
        )
    report = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    rows = [entry for entry in report["findings"] if entry["details"].get("issue_type") == _ISSUE]
    assert sorted(row["page"] for row in rows) == [1, 3]
    view = build_report_view(report, pdf_page_sizes=get_pdf_page_sizes(path))
    cards = {card.finding_id: card for card in view.findings}
    for row in rows:
        card = cards[f'f{report["findings"].index(row)}']
        assert card.has_highlight and "A.1" in card.suggested_fix
        assert ".1" in card.polished_comment and "missing" in card.polished_comment
    highlighted = _highlight_boxes_by_page(rows)
    with pymupdf.open(path) as pdf:
        for physical_page in (1, 3):
            page = pdf[physical_page - 1]
            (identifier,) = page.search_for(".1")
            row = next(row for row in rows if row["page"] == physical_page)
            x0, y0, x1, y1 = (float(value) for value in row["details"]["bbox"].split(","))
            assert (x0, y0, x1, y1) == pytest.approx(tuple(identifier), abs=0.1)
            _draw_boxes_for_page(page, highlighted[physical_page])
            (annotation,) = page.annots()
            assert tuple(annotation.rect) == pytest.approx(
                (x0 - 1, y0 - 1, x1 + 1, y1 + 1), abs=0.1,
            )


def test_missing_character_geometry_has_no_highlight(tmp_path: Path) -> None:
    path = tmp_path / "unmeasured.pdf"
    with pymupdf.open() as doc:
        page = _page(doc, "APPENDIX")
        _body_line(page, ".1 Measurement Setup")
        doc.save(path)
    layout = load_pdf_layout(str(path))
    for block in layout.pages[0].text_blocks:
        for line in block.lines:
            for span in line.spans:
                span.char_x_bounds = None
    (finding,) = pdf_appendix_body_headings.check_pdf_appendix_body_headings(layout)
    assert finding.details["expected_identifier"] == "A.1"
    assert "bbox" not in finding.details
    report = audit_findings_to_json_dict([finding], {"audit_type": "pdf"})
    assert _highlight_boxes_by_page(report["findings"]) == {}
