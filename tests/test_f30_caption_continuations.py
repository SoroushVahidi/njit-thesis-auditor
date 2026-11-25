"""Invented figure descriptions exercise real glyph and image extraction."""

from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.pdf_models import (
    BBox,
    PdfDocument,
    PdfPage,
    PdfTextBlock,
    PdfTextLine,
    PdfTextSpan,
    format_bbox_detail,
)
from njit_auditor.rules.pdf_caption_continuations import (
    LogicalCaption,
    PageCaptionEnd,
    detect_logical_caption_lines,
    locate_page_caption_end,
)
from njit_auditor.rules.pdf_caption_spacing import ISSUE_TYPE, check_page_caption_spacing
from njit_auditor.rules.pdf_captions import CaptionLine, check_pdf_captions, detect_caption_lines
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


_START = "Figure 2.1 Measurement geometry in the reference panel"
_MIDDLE = "as compared with the control frame"
_END = "under the same measurement method"


def _pdf(
    path: Path,
    rows: tuple[str, ...],
    *,
    pitch: float = 14,
    rotation: int = 0,
    landscape: bool = False,
    side_row: str = "",
) -> Path:
    with fitz.open() as doc:
        page = doc.new_page(width=792 if landscape else 612, height=612 if landscape else 792)
        page.draw_rect(fitz.Rect(110, 75, 510, 300), color=(0, 0, 0))
        page.insert_text(
            (72, 330), "\n".join(rows), fontname="tiro", fontsize=12, lineheight=pitch / 12
        )
        if side_row:
            page.insert_text((400, 330 + pitch), side_row, fontname="tiro", fontsize=12)
        page.set_rotation(rotation)
        doc.save(path)
    return path


def _punctuation(path: Path):
    return [
        finding
        for finding in check_pdf_captions(load_pdf_layout(str(path)))
        if finding.details["issue_type"] in {
            "missing_terminal_punctuation", "unexpected_terminal_period"
        }
    ]


@pytest.mark.parametrize(
    ("rows", "pitch", "expected"),
    [
        ((_START + ".",), 14, ()),
        ((_START,), 14, (_START,)),
        ((_START, _END + "."), 14, ()),
        ((_START, _MIDDLE, _END + "."), 14, ()),
        ((_START, _MIDDLE, _END), 14, (_END,)),
        ((_START, _MIDDLE, _END + "."), 24, ()),
        ((_START, _MIDDLE, _END + "."), 28, ()),
        ((_START, _MIDDLE, _END), 24, (_END,)),
        ((_START + " using", "an independent optical reference."), 24, ()),
        ((_START + " using", "an independent optical reference"), 24,
         ("an independent optical reference",)),
        ((_START, "This independent paragraph supplies a period."), 14, (_START,)),
        ((_START + ".", "This independent paragraph has no period"), 14, ()),
        ((_START, "Figure 2.2 Independent figure caption."), 14, (_START,)),
        ((_START, "Figure 2.2", "an unrelated caption ends here."), 14, (_START,)),
        ((_START + ".", "Figure 2.2 Independent figure caption"), 14,
         ("Figure 2.2 Independent figure caption",)),
        ((_START, "Footnote: This annotation supplies a period."), 14, (_START,)),
        ((_START, "[4] This note has its own period."), 14, (_START,)),
        ((_START, "12."), 14, (_START,)),
    ],
)
def test_figure_punctuation_uses_owned_end(tmp_path, rows, pitch, expected):
    path = _pdf(tmp_path / "caption.pdf", rows, pitch=pitch)
    model = load_pdf_layout(str(path))
    # These tight surrounding rows deliberately share an extraction block.
    if len(rows) > 1 and pitch == 14 and not rows[-1][0].isdigit():
        assert len(model.pages[0].text_blocks) == 1
    assert [row.details["line_preview"] for row in _punctuation(path)] == list(expected)


@pytest.mark.parametrize(
    "rows",
    [
        (_START, "calibration details that could belong to either block."),
        (_START, "with different conditions in an independent line."),
        (_START, _MIDDLE, "unrelated appendix prose supplies a period."),
    ],
)
def test_ambiguous_block_never_supplies_terminal_punctuation(tmp_path, rows):
    path = _pdf(tmp_path / "ambiguous.pdf", rows, pitch=24)
    model = load_pdf_layout(str(path))
    first, = detect_caption_lines(model)
    end = locate_page_caption_end(model.pages[0], first)
    assert end is not None
    assert not end.resolved
    assert [line.text for line in end.lines] == [_START]
    assert _punctuation(path) == []


def test_parallel_column_never_supplies_terminal_punctuation(tmp_path):
    path = _pdf(
        tmp_path / "parallel.pdf", (_START, _MIDDLE, _END + "."),
        pitch=24, side_row="Other column.",
    )
    model = load_pdf_layout(str(path))
    first, = detect_caption_lines(model)
    end = locate_page_caption_end(model.pages[0], first)
    assert end is not None
    assert not end.resolved
    assert [line.text for line in end.lines] == [_START]


def test_irregular_pitch_with_plausible_ending_does_not_produce_advice(tmp_path):
    path = tmp_path / "irregular.pdf"
    with fitz.open() as doc:
        page = doc.new_page(width=612, height=792)
        for baseline, text in zip((330, 354, 375), (_START, _MIDDLE, _END + "."), strict=True):
            page.insert_text((72, baseline), text, fontname="tiro", fontsize=12)
        doc.save(path)
    model = load_pdf_layout(str(path))
    first, = detect_caption_lines(model)
    end = locate_page_caption_end(model.pages[0], first)
    assert end is not None and not end.resolved
    assert [line.text for line in end.lines] == [_START]
    assert _punctuation(path) == []


def test_interleaved_glyph_does_not_move_highlight_to_a_partial_line():
    # The main extraction block contains the wrap. A raised glyph in another
    # block sorts between the last two full lines.
    rows = [
        PdfTextLine(text=text, bbox=BBox(x0=72, x1=420, y0=y, y1=y + 12))
        for y, text in zip((100, 114, 128), (_START, _MIDDLE, _END), strict=True)
    ]
    glyph = PdfTextLine(text="α", bbox=BBox(x0=360, x1=370, y0=122, y1=133))
    page = PdfPage(
        page_number=1,
        width=612,
        height=792,
        text_blocks=[
            PdfTextBlock(lines=rows, bbox=BBox(x0=72, x1=420, y0=100, y1=140), text=""),
            PdfTextBlock(lines=[glyph], bbox=glyph.bbox, text=glyph.text),
        ],
    )
    model = PdfDocument(path="synthetic.pdf", pages=[page])
    first, = detect_caption_lines(model)
    assert locate_page_caption_end(page, first) is None
    finding, = check_pdf_captions(model)
    assert finding.details["bbox"] == format_bbox_detail(rows[0].bbox)
    assert finding.details["caption_end_preview"].endswith(_END)


@pytest.mark.parametrize("period", ["", ".", ".."])
def test_wrapped_table_preserves_the_existing_table_title_policy(tmp_path, period):
    path = _pdf(
        tmp_path / "table.pdf",
        (
            "Table 3.1 Accuracy of Synthetic Survey Methods and",
            "Reference Measurements for Both Groups" + period,
        ),
        pitch=24,
    )
    findings = _punctuation(path)
    if not period:
        assert findings == []
        return
    finding, = findings
    assert finding.details["issue_type"] == "unexpected_terminal_period"
    assert finding.details["line_preview"] == "Reference Measurements for Both Groups" + period
    assert finding.details["suggested_fix"] == "Remove the final period from this table title."


@pytest.mark.parametrize(("landscape", "rotation"), [(True, 0), (False, 90)])
def test_caption_ownership_uses_horizontal_text_coordinates(tmp_path, landscape, rotation):
    path = _pdf(
        tmp_path / "unusual.pdf", (_START, _MIDDLE, _END),
        pitch=24, landscape=landscape, rotation=rotation,
    )
    finding, = _punctuation(path)
    page, = load_pdf_layout(str(path)).pages
    tail, = [line for block in page.text_blocks for line in block.lines if line.text == _END]
    assert finding.page == page.page_number == 1
    assert finding.details["bbox"] == format_bbox_detail(tail.bbox)


@pytest.mark.parametrize("punctuation", ["", "."])
@pytest.mark.parametrize("pitch", [14, 24])
def test_actual_final_line_controls_report_card_and_both_pdf_routes(
    tmp_path, monkeypatch, punctuation, pitch
):
    from fastapi.testclient import TestClient

    from njit_auditor import web_app

    path = _pdf(tmp_path / "rendered.pdf", (_START, _MIDDLE, _END + punctuation), pitch=pitch)
    monkeypatch.setattr(web_app, "RUNTIME_DIR", tmp_path / "audits")
    page, = load_pdf_layout(str(path)).pages
    tail, = [
        line for block in page.text_blocks for line in block.lines if line.text.startswith(_END)
    ]
    advice = "End the figure description with a period."
    with TestClient(web_app.app) as client:
        post = client.post(
            "/audits",
            files={"file": (path.name, path.read_bytes(), "application/pdf")},
            follow_redirects=False,
        )
        assert post.status_code == 303
        base = post.headers["location"]
        assert client.get(base + "/status").json()["state"] == "complete"
        exported = client.get(base + "/download/json")
        assert exported.status_code == 200
        rows = exported.json()["findings"]
        job = web_app._get_job(base.rsplit("/", 1)[-1])
        assert job is not None
        cards = [
            card for card in job.findings if card["rule_id"] == "P017"
            and card["issue_type"] == "missing_terminal_punctuation"
        ]
        assert sum(
            card["rule_id"] == "P017" and card["issue_type"] == ISSUE_TYPE
            for card in job.findings
        ) == int(pitch == 24)
        report = client.get(base)
        assert report.status_code == 200
        complete = client.get(base + "/download/student-report.pdf")
        assert complete.status_code == 200
        with fitz.open(stream=complete.content) as doc:
            complete_rects = [a.rect for a in doc[0].annots()]
        if punctuation:
            assert not [
                row for row in rows if row["rule_id"] == "P017"
                and row["details"]["issue_type"] == "missing_terminal_punctuation"
            ]
            assert cards == []
            assert any(abs(rect.y0 - tail.bbox.y0) < 2 for rect in complete_rects) == (pitch == 24)
            assert advice not in report.text
            return

        card, = cards
        row = rows[int(card["finding_id"][1:])]
        assert row["page"] == card["page"] == 1
        assert row["details"]["bbox"] == format_bbox_detail(tail.bbox)
        assert advice in report.text and card["suggested_fix"] == advice
        for extension in ("markdown", "text"):
            export = client.get(base + "/download/" + extension)
            assert export.status_code == 200
            assert "missing terminal punctuation" in export.text.lower()
            assert f"What to check: {advice}" in export.text
        comments = client.get(base + "/download/comments.pdf")
        assert comments.status_code == 200
        for pdf in (complete, comments):
            with fitz.open(stream=pdf.content) as doc:
                exported_text = " ".join(" ".join(p.get_text() for p in doc).split())
            assert f"What to check: {advice}" in exported_text
        single = client.get(
            base + "/highlighted-page.pdf",
            params={"page": 1, "rule_id": "P017", "finding_id": card["finding_id"]},
        )
        assert single.status_code == 200
        with fitz.open(stream=single.content) as doc:
            rect, = [a.rect for a in doc[0].annots()]
        assert abs(rect.y0 - tail.bbox.y0) < 2
        assert rect in complete_rects


_TABLE = (
    "Table 4.1 Calibration Results for Test Objects and",
    "the Measured Range of Control Probes and",
    "the Measurements for Different Conditions",
)


@pytest.mark.parametrize(
    ("rows", "pitch", "spacing", "missing_mark"),
    [
        ((_START, _END + "."), 14, False, False),
        ((_START, _MIDDLE, _END + "."), 14, False, False),
        ((_START, _MIDDLE, _END + "."), 18, False, False),
        ((_START, _MIDDLE, _END + "."), 24, True, False),
        ((_START, _MIDDLE, _END + "."), 28, True, False),
        ((_START, _MIDDLE, _END + "."), 22.3, False, False),
        ((_START, _MIDDLE, _END + "."), 22.5, True, False),
        ((_START, _MIDDLE, _END), 24, True, True),
        ((_START, _MIDDLE, _END), 14, False, True),
        ((_START + ".",), 24, False, False),
        ((_START + " using", "an optical reference."), 24, False, False),
        ((_START, _MIDDLE, "unrelated appendix text ends here."), 24, False, False),
        ((_START + ".", "The next paragraph describes the instrument.", _END + "."),
         24, False, False),
        (_TABLE, 14, False, False),
        (_TABLE, 24, True, False),
    ],
)
def test_caption_spacing_is_separate_from_terminal_punctuation(
    tmp_path: Path,
    rows: tuple[str, ...],
    pitch: float,
    spacing: bool,
    missing_mark: bool,
) -> None:
    path = _pdf(tmp_path / "spacing.pdf", rows, pitch=pitch)
    findings = check_pdf_captions(load_pdf_layout(str(path)))
    issues = [f.details["issue_type"] for f in findings]
    assert issues.count(ISSUE_TYPE) == int(spacing)
    assert issues.count("missing_terminal_punctuation") == int(missing_mark)


def _measured_end(
    *,
    pitches: tuple[float, float] = (24, 24),
    height: float = 15,
) -> PageCaptionEnd:
    rows = []
    for text, y in zip((_START, _MIDDLE, _END + "."), (100, 100 + pitches[0], 100 + sum(pitches)),
                       strict=True):
        box = BBox(x0=72, x1=360, y0=y - height + 2, y1=y + 2)
        span = PdfTextSpan(text=text, bbox=box, size=12, font="Times-Roman", baseline_y=y)
        rows.append(PdfTextLine(text=text, bbox=box, spans=[span], baseline_y=y))
    return PageCaptionEnd(tuple(rows), True)


@pytest.mark.parametrize(
    ("pitch", "height", "warns"),
    [(21.59, 14.5, False), (21.61, 14.5, True),
     (22.39, 16, False), (22.41, 16, True)],
)
def test_caption_spacing_calibration_boundaries(
    pitch: float, height: float, warns: bool
) -> None:
    caption = CaptionLine(1, _START, "figure", _START, "body")
    end = _measured_end(pitches=(pitch, pitch), height=height)
    assert (check_page_caption_spacing(caption, end) is not None) == warns


@pytest.mark.parametrize(
    "variant",
    ["larger_font", "new_family", "superscript", "subscript", "missing_baseline",
     "paragraph", "vertical", "uneven_gaps", "unresolved", "bold_label"],
)
def test_caption_spacing_requires_reliable_typographic_evidence(variant: str) -> None:
    caption = CaptionLine(1, _START, "figure", _START, "body")
    end = _measured_end(pitches=(24, 28) if variant == "uneven_gaps" else (24, 24))
    row = end.lines[1]
    span = row.spans[0]
    if variant == "larger_font":
        span.size = 14
    elif variant == "new_family":
        span.font = "Helvetica"
    elif variant in {"superscript", "subscript"}:
        row.spans.append(PdfTextSpan(
            text="2", bbox=span.bbox, size=8, font=span.font,
            baseline_y=120 if variant == "superscript" else 128,
        ))
    elif variant == "missing_baseline":
        span.baseline_y = None
    elif variant == "paragraph":
        row.text += "."
    elif variant == "vertical":
        row.line_dir = (0, 1)
    elif variant == "unresolved":
        end = PageCaptionEnd(end.lines, False)
    elif variant == "bold_label":
        end.lines[0].spans.append(PdfTextSpan(
            text="Figure 2.1", bbox=end.lines[0].bbox, size=12,
            font="Times-Bold", baseline_y=100, bold=True,
        ))
    result = check_page_caption_spacing(caption, end)
    assert (result is not None) == (variant == "bold_label")


def test_caption_spacing_ignores_adjacent_content_and_deduplicates(tmp_path: Path) -> None:
    path = tmp_path / "adjacent.pdf"
    with fitz.open() as doc:
        page = doc.new_page(width=612, height=792)
        page.insert_text((72, 240), "Introductory paragraph above the figure.", fontsize=12)
        page.insert_text(
            (72, 330), "\n".join((_START, _MIDDLE, _END + ".")),
            fontname="tiro", fontsize=12, lineheight=2,
        )
        page.insert_text((72, 400), "Figure 2.2 Independent description.", fontsize=12)
        page.insert_text((72, 425), "The next body paragraph starts here.", fontsize=12)
        doc.save(path)
    model = load_pdf_layout(str(path))
    spacing, = [f for f in check_pdf_captions(model) if f.details["issue_type"] == ISSUE_TYPE]
    assert spacing.details["caption_line_count"] == "3"
    expected_lines = [
        line for block in model.pages[0].text_blocks for line in block.lines
        if line.text in {_START, _MIDDLE, _END + "."}
    ]
    assert spacing.details["highlight_bboxes"].split(" | ") == [
        format_bbox_detail(line.bbox) for line in expected_lines
    ]


@pytest.mark.parametrize(("landscape", "rotation"), [(False, 0), (True, 0), (False, 90)])
def test_caption_spacing_cards_exports_and_highlight_routes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, landscape: bool, rotation: int
) -> None:
    from fastapi.testclient import TestClient

    from njit_auditor import web_app

    path = _pdf(tmp_path / "rendered-spacing.pdf", (_START, _MIDDLE, _END + "."),
                pitch=24, landscape=landscape, rotation=rotation)
    monkeypatch.setattr(web_app, "RUNTIME_DIR", tmp_path / "audits")
    with TestClient(web_app.app) as client:
        post = client.post(
            "/audits",
            files={"file": (path.name, path.read_bytes(), "application/pdf")},
            follow_redirects=False,
        )
        assert post.status_code == 303
        base = post.headers["location"]
        assert client.get(base + "/status").json()["state"] == "complete"
        report = client.get(base + "/download/json").json()
        p017, = [row for row in report["findings"] if row["rule_id"] == "P017"]
        assert p017["severity"] == "WARNING"
        assert p017["details"]["issue_type"] == ISSUE_TYPE
        assert p017["page"] == 1
        assert p017["details"]["caption_median_baseline_distance_pt"] == "24.00"
        assert len(p017["details"]["highlight_bboxes"].split(" | ")) == 3
        job = web_app._get_job(base.rsplit("/", 1)[-1])
        assert job is not None
        card, = [row for row in job.findings if row["rule_id"] == "P017"]
        assert card["issue_type"] == ISSUE_TYPE and card["has_highlight"] and card["page"] == 1
        instruction = "Apply single line spacing within the highlighted figure description."
        assert card["suggested_fix"] == instruction
        assert instruction in client.get(base).text
        for ext in ("markdown", "text"):
            export = client.get(base + "/download/" + ext)
            assert export.status_code == 200
            assert "wide internal line spacing" in export.text.lower()
            assert instruction in export.text
        single = client.get(base + "/highlighted-page.pdf", params={
            "page": 1, "rule_id": "P017", "finding_id": card["finding_id"]})
        complete = client.get(base + "/download/student-report.pdf")
        assert single.status_code == complete.status_code == 200
        with fitz.open(stream=single.content) as focused, fitz.open(
            stream=complete.content
        ) as full:
            targets = {tuple(mark.rect) for mark in focused[0].annots()}
            other = {tuple(mark.rect) for mark in full[0].annots()}
            assert len(targets) == 3 and targets <= other
            for box in p017["details"]["highlight_bboxes"].split(" | "):
                y0 = float(box.split(",")[1])
                assert any(abs(rect[1] - y0) < 2 for rect in targets)
