"""Invented figure descriptions exercise real glyph and image extraction."""

from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.pdf_models import PdfDocument
from njit_auditor.rules.pdf_caption_continuations import (
    LogicalCaption,
    detect_logical_caption_lines,
)
from njit_auditor.rules.pdf_captions import check_pdf_captions, detect_caption_lines
from njit_auditor.rules.pdf_figure_number_structure import check_pdf_figure_number_structure


def render_caption(
    tmp_path: Path, *, source: list[str] | None = None, tail: list[str] | None = None,
    following: str | None = "2.1 Results", graphic: bool = True,
) -> tuple[Path, PdfDocument]:
    source = source if source is not None else [
        "Figure 1.1 Synthetic measurements collected using",
    ]
    tail = tail if tail is not None else [
        "two laboratory instruments and a calibrated reference.",
    ]
    path = tmp_path / "synthetic.pdf"
    with fitz.open() as document:
        first = document.new_page(width=612, height=792)
        top = 718 - 14 * (len(source) - 1)
        if graphic:
            pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 4, 4), False)
            pix.clear_with(80)
            first.insert_image(
                fitz.Rect(108, top - 125, 510, top - 28), pixmap=pix, keep_proportion=False,
            )
        for i, text in enumerate(source):
            first.insert_text((108, top + i * 14), text, fontsize=12, fontname="tiro")
        first.insert_text((300, 750), "10", fontname="tiro", fontsize=12)
        second = document.new_page(width=612, height=792)
        for i, text in enumerate(tail):
            second.insert_text((108, 84 + i * 14), text, fontsize=12, fontname="tiro")
        if following:
            second.insert_text((144, 112 + len(tail) * 14), following,
                               fontname="tiro", fontsize=12)
        second.insert_text((300, 750), "11", fontname="tiro", fontsize=12)
        document.save(path)
    return path, load_pdf_layout(str(path))


def logical(doc: PdfDocument) -> list[LogicalCaption]:
    return [c for c in detect_logical_caption_lines(doc) if isinstance(c, LogicalCaption)]


def missing(doc: PdfDocument) -> list:
    return [f for f in check_pdf_captions(doc)
            if f.details.get("issue_type") == "missing_terminal_punctuation"]


def test_one_page_forward_is_logical_not_a_violation(tmp_path: Path) -> None:
    _, doc = render_caption(tmp_path)
    assert len(detect_caption_lines(doc)) == 1
    assert not detect_caption_lines(doc)[0].caption_body.endswith(".")
    (caption,) = logical(doc)
    assert caption.caption_body.endswith("reference.")
    references = [(f.page_number, f.document_page_label) for f in caption.fragments]
    assert references == [(1, "10"), (2, "11")]
    assert caption.page_number == 1  # preserve the original figure identity
    assert check_pdf_captions(doc) == []  # a page crossing is not itself a warning


@pytest.mark.parametrize("code", ["7XYZ).", "1234)."])
def test_code_leading_one_line_continuation(tmp_path: Path, code: str) -> None:
    _, doc = render_caption(tmp_path, source=[
        "Figure 1.1 Synthetic observation from station (code:",
    ], tail=[code])
    assert len(logical(doc)) == 1
    assert check_pdf_captions(doc) == []


def test_eight_line_continuation_stops_before_prose(tmp_path: Path) -> None:
    _, doc = render_caption(tmp_path, tail=[
        "two independent laboratory instruments under controlled conditions,",
        "with a synthetic reference used for each comparison. The groups",
        "were assessed using a common calibration procedure and a shared",
        "set of observations. Each panel shows the experimental response",
        "for one group, while the markers indicate the reference values.",
        "The solid line represents the central estimate and the shaded",
        "area represents the interval estimated from repeated measurements",
        "under the same conditions.",
    ], following="Ordinary prose resumes here and must remain separate.")
    (caption,) = logical(doc)
    assert len(caption.fragments[1].lines) == 8
    assert "Ordinary prose" not in caption.caption_body
    assert missing(doc) == []


@pytest.mark.parametrize("multi_sentence", [False, True])
def test_period_ending_fragment_with_panel_continuation(
    tmp_path: Path, multi_sentence: bool,
) -> None:
    multi = ["Figure 1.1 Synthetic experiment. Top, comparison of the models."]
    source = multi if multi_sentence else [
        "Figure 1.1 Synthetic experiment with two views,",
        "Top, comparison of the models.",
    ]
    _, doc = render_caption(tmp_path, source=source, tail=[
        "Bottom right, comparison with a synthetic reference.",
    ])
    assert len(logical(doc)) == 1
    assert missing(doc) == []
    if multi_sentence:
        assert detect_caption_lines(doc) == []  # legacy prose guard stays intact


def test_real_missing_punctuation_targets_final_page_and_line(tmp_path: Path) -> None:
    _, doc = render_caption(tmp_path, tail=[
        "two instruments and an independent reference",
        "under the same synthetic conditions",
    ])
    (finding,) = missing(doc)
    assert finding.page == 2
    assert finding.severity.value == "WARNING" and finding.details["confidence"] == "high"
    assert finding.details["document_page_label"] == "11"
    assert finding.details["line_preview"] == "under the same synthetic conditions"
    terminal = next(line for b in doc.pages[1].text_blocks for line in b.lines
                    if line.text.startswith("under the same"))
    assert float(finding.details["bbox"].split(",")[1]) == pytest.approx(terminal.bbox.y0, abs=0.1)
    assert float(finding.details["caption_start_bbox"].split(",")[1]) > 600
    assert float(finding.details["caption_end_bbox"].split(",")[1]) < 100
    assert finding.details["caption_start_page"] == "1"
    assert finding.details["caption_end_page"] == "2"


@pytest.mark.parametrize("tail", [
    ["Ordinary body prose happens to end with punctuation."],
    ["two instruments and a reference."],
    ["Bottom right, an unrelated discussion with punctuation."],
])
def test_complete_near_bottom_caption_missing_period_is_not_repaired(
    tmp_path: Path, tail: list[str],
) -> None:
    _, doc = render_caption(tmp_path, source=[
        "Figure 1.1 Synthetic measurements from the complete experiment",
    ], tail=tail)
    assert logical(doc) == []
    assert any(f.page == 1 for f in missing(doc))


@pytest.mark.parametrize("tail", [
    ["2.1 A new section"], ["CHAPTER 2"], ["Source: A synthetic archive."],
    ["Note: Additional information."], ["Figure 1.2 An unrelated caption without punctuation"],
    ["Table 1.1 Synthetic Measurements"], ["REFERENCES"], [],
])
def test_structural_breaks_are_not_continuations(tmp_path: Path, tail: list[str]) -> None:
    _, doc = render_caption(tmp_path, tail=tail)
    assert logical(doc) == []
    assert any(f.page == 1 for f in missing(doc))


def test_source_note_does_not_supply_missing_terminal_punctuation(tmp_path: Path) -> None:
    _, doc = render_caption(tmp_path, tail=[
        "two instruments under synthetic conditions", "Source: A synthetic archive.",
    ])
    (caption,) = logical(doc)
    assert "Source:" not in caption.caption_body
    assert len(caption.fragments[1].lines) == 1
    assert missing(doc)[0].page == 2


@pytest.mark.parametrize("ambiguity", [
    "no_graphic", "nonadjacent", "original_gap", "rotation", "content_rotation", "vertical",
    "font", "indent", "column", "edge_graphic",
])
def test_ambiguous_continuations_abstain(tmp_path: Path, ambiguity: str) -> None:
    _, doc = render_caption(tmp_path, graphic=ambiguity != "no_graphic")
    first = next(line for b in doc.pages[1].text_blocks for line in b.lines
                 if line.text.startswith("two"))
    if ambiguity == "nonadjacent":
        doc.pages[1].page_number = 3
    elif ambiguity == "original_gap":
        doc.pages[1].original_page_number = 3
    elif ambiguity == "rotation":
        doc.pages[1].page_rotation = 90
    elif ambiguity == "content_rotation":
        first.line_dir = (-1, 0)
    elif ambiguity == "vertical":
        first.wmode = 1
    elif ambiguity == "font":
        for span in first.spans:
            span.font = "Courier"
    elif ambiguity == "indent":
        first.bbox.x0 += 36
    elif ambiguity == "edge_graphic":
        anchor = next(line for block in doc.pages[0].text_blocks for line in block.lines
                      if line.text.startswith("Figure"))
        graphic = doc.pages[0].graphic_blocks[0]
        graphic.bbox.x0, graphic.bbox.x1 = 0, anchor.bbox.x0 + 1
    elif ambiguity == "column":
        other = first.model_copy(deep=True)
        other.bbox.x0, other.bbox.x1 = 400, 540
        doc.pages[1].text_blocks[0].lines.append(other)
    assert logical(doc) == []
    assert any(f.page == 1 for f in missing(doc))


def test_no_jump_over_blank_page(tmp_path: Path) -> None:
    _, doc = render_caption(tmp_path)
    third = doc.pages[1].model_copy(deep=True)
    third.page_number, third.original_page_number = 3, 3
    doc.pages[1].text_blocks = []
    doc.pages.append(third)
    assert logical(doc) == [] and missing(doc)[0].page == 1


@pytest.mark.parametrize("separate_label", [False, True])
def test_continued_label_is_one_p088_identity_but_real_duplicates_survive(
    tmp_path: Path, separate_label: bool,
) -> None:
    tail = (["Figure 1.1 (Continued)", "Further synthetic measurements."]
            if separate_label else ["Figure 1.1 (Continued) Further synthetic measurements."])
    _, doc = render_caption(tmp_path, source=[
        "Figure 1.1 Synthetic reference measurement.",
    ], tail=tail)
    assert len(detect_caption_lines(doc)) == (1 if separate_label else 2)
    assert len(detect_logical_caption_lines(doc)) == 1
    assert check_pdf_figure_number_structure(doc) == []
    continuation = next(line for b in doc.pages[1].text_blocks for line in b.lines
                        if line.text.startswith("Figure"))
    continuation.text = "Figure 1.1 Another independent synthetic measurement."
    assert logical(doc) == []
    assert check_pdf_figure_number_structure(doc)  # genuine duplicate retained


def test_multisentence_prose_guard_is_not_globally_weakened(tmp_path: Path) -> None:
    _, doc = render_caption(tmp_path, source=[
        "Figure 1.1 Synthetic observations are discussed here. This is ordinary prose.",
    ])
    assert detect_logical_caption_lines(doc) == []


def test_continuation_geometry_is_rendered_only_on_its_source_page(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient
    from test_web_app import _inject_complete_job_with_findings, _make_app

    source, doc = render_caption(tmp_path, tail=[
        "two synthetic instruments under comparable conditions",
        "without final punctuation",
    ])
    (finding,) = missing(doc)
    app, wa = _make_app(tmp_path)
    job_id = _inject_complete_job_with_findings(
        wa, tmp_path, findings=[finding], file_name="synthetic.pdf", audit_type="pdf", page_count=2,
    )
    upload = wa.RUNTIME_DIR / job_id / "upload.pdf"
    upload.write_bytes(source.read_bytes())
    before = upload.read_bytes()
    expected_y = float(finding.details["bbox"].split(",")[1])

    def check_context(text: str) -> None:
        import re
        from html import unescape

        clean = " ".join(unescape(re.sub(r"<[^>]+>", " ", text)).split())
        assert "physical PDF page 1 (document page 10)" in clean
        assert "physical PDF page 2 (document page 11)" in clean
        assert "the highlight target is that line only" in clean
        assert "Crossing a page boundary alone is not a formatting violation" in clean

    check_context((wa.RUNTIME_DIR / job_id / "report.txt").read_text())
    with TestClient(app) as client:
        base = f"/audits/{job_id}"
        for route in ("", "/problems/page/2", "/problems/rule/P017",
                      "/download/json", "/download/markdown", "/download/text"):
            response = client.get(base + route)
            assert response.status_code == 200
            check_context(response.text)
        payload = client.get(base + "/download/json").json()
        exported = payload["findings"][0]
        assert exported["page"] == exported["pdf_page"] == 2
        assert exported["document_page_label"] == "11"
        assert exported["details"] == {
            key: value for key, value in finding.details.items() if key != "source_q_rule_id"
        }
        original = client.get(base + "/pdf")
        assert original.status_code == 200 and original.content == before
        marked = client.get(base + "/pdf/highlighted", params={
            "page": 2, "rule_id": "P017", "issue_type": "missing_terminal_punctuation",
        })
        assert marked.status_code == 200
        with fitz.open(stream=marked.content, filetype="pdf") as pdf:
            assert pdf.page_count == 2 and not list(pdf[0].annots() or [])
            marked_page = pdf[1]
            (annotation,) = list(marked_page.annots() or [])
            assert abs(annotation.rect.y0 - expected_y) < 8
            assert annotation.rect.y1 < 150  # never includes the first-page bottom box
        combined = client.get(base + "/download/student-report.pdf")
        assert combined.status_code == 200
        with fitz.open(stream=combined.content, filetype="pdf") as pdf:
            assert not list(pdf[0].annots() or [])
            assert len(list(pdf[1].annots() or [])) == 1
            check_context(" ".join(p.get_text() for p in list(pdf)[2:]))
    assert upload.read_bytes() == before


def test_logical_association_does_not_mutate_geometry_consumers(tmp_path: Path) -> None:
    from njit_auditor.rules.pdf_body_spacing import check_pdf_body_spacing
    from njit_auditor.rules.pdf_font_compliance import check_pdf_font_compliance
    from njit_auditor.rules.pdf_lot_lof_entry_type import check_pdf_lot_lof_entry_type
    from njit_auditor.rules.pdf_title_capitalization import check_pdf_title_capitalization

    _, doc = render_caption(tmp_path)
    checks = [check_pdf_body_spacing, check_pdf_font_compliance,
              check_pdf_lot_lof_entry_type, check_pdf_title_capitalization]
    original = doc.model_dump()
    baseline = [check(doc) for check in checks]
    assert logical(doc)  # logical path is opt-in, with no edits to the PDF model
    assert doc.model_dump() == original
    assert [check(doc) for check in checks] == baseline


def test_last_page_retains_a_genuine_missing_period(tmp_path: Path) -> None:
    _, doc = render_caption(tmp_path)
    doc.pages = doc.pages[:1]
    assert logical(doc) == []
    assert missing(doc)[0].page == 1


def test_same_margin_double_spaced_prose_is_not_a_caption_tail(tmp_path: Path) -> None:
    _, doc = render_caption(tmp_path, tail=[
        "two synthetic measurements are discussed in this ordinary paragraph.",
        "The paragraph continues on a second double-spaced line.",
    ])
    second = next(line for block in doc.pages[1].text_blocks for line in block.lines
                  if line.text.startswith("The paragraph"))
    second.bbox.y0 += 14
    second.bbox.y1 += 14
    assert logical(doc) == []
    assert any(f.page == 1 for f in missing(doc))


@pytest.mark.parametrize("tail", [
    ["Figure 1.1 continued to show a stable synthetic response."],
    ["Figure 1.1 continuedgrowth is discussed in ordinary prose."],
    ["Figure 1.1 (continued to show a stable synthetic response."],
    ["Figure 1.1 continued) Further synthetic observations."],
    ["Figure 1.1 (Continued)"],
    ["Figure 1.1 (Continued) Source: A synthetic archive."],
    ["Figure 1.1 (Continued)", "Source: A synthetic archive."],
    ["Figure 1.1 (Continued) 2.1 Results"],
])
def test_continued_prose_or_label_without_description_cannot_repair_caption(
    tmp_path: Path, tail: list[str],
) -> None:
    _, doc = render_caption(tmp_path, source=[
        "Figure 1.1 Synthetic measurements from the complete experiment",
    ], tail=tail)
    assert logical(doc) == []
    assert any(f.page == 1 for f in missing(doc))
