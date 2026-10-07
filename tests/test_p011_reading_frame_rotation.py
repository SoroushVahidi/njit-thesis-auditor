"""R011 in the detector reading frame (synthetic PDFs only).

Under the rotation-frames ADR, R011 measures a page as its authored content
reads upright (``PdfReadingFrame``) and stores finding boxes in the unrotated
box space:

* a viewer-only ``/Rotate`` (upright content, the viewer turns the sheet)
  keeps the ``/Rotate 0`` verdict exactly;
* a content-turned page (pdflscape landscape, or any page whose content reads
  upright only after ``/Rotate``) gets the verdict, side, binding edge,
  overflow and wording of its pixel-identical ``/Rotate 0`` control.

The binding edge still comes from the portrait page number's reading
direction, never from the ``/Rotate`` value, and the bottom-only allowances
follow the reading-frame bottom but never a binding edge.
"""

from __future__ import annotations

import ast
from collections.abc import Callable
from pathlib import Path

import fitz
import pytest

import njit_auditor.rules.pdf_margins as r011
from njit_auditor.pdf_highlight import build_highlighted_pdf, get_pdf_page_sizes
from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.pdf_models import PdfReadingFrame
from njit_auditor.polished_comments import _p011_margin_comment
from njit_auditor.rules.pdf_margins import run_pdf_margin_rule
from njit_auditor.student_pdf_report import build_combined_student_pdf_report

TEXT = "Synthetic landscape table row with several ordinary words"
FS = 11.0
# Allowed text rectangle per sheet (x0, y0, x1, y1) in the reading frame.
FRAMES = {
    "portrait": (108.0, 72.0, 540.0, 720.0),
    "cw": (72.0, 108.0, 720.0, 540.0),  # landscape, binding at the top
    "ccw": (72.0, 72.0, 720.0, 504.0),  # landscape, binding at the bottom
    "undetermined": (72.0, 72.0, 720.0, 540.0),  # landscape, no portrait folio
}
SEMANTIC = (
    "issue_type",
    "side",
    "worst_overflow_pt",
    "affected_line_count",
    "confidence",
    "page_orientation",
    "binding_edge",
    "suggested_fix",
    "page_context",
    "margin_content_kind",
    "affected_line_texts",
)
BOXES = (
    "bbox",
    "highlight_bboxes",
    "overflow_display_bboxes",
    "overflow_segment_bboxes",
    "margin_boundary_bbox",
)
Builder = Callable[[fitz.Document], None]


def _glyph_box() -> tuple[float, float, float, float]:
    doc = fitz.open()
    page = doc.new_page(width=792, height=612)
    page.insert_text((200, 300), TEXT, fontsize=FS)
    box = fitz.Rect(page.get_text("dict")["blocks"][0]["lines"][0]["bbox"])
    return 300 - box.y0, box.y1 - 300, box.x0 - 200, box.width


UP, DOWN, LEFT, WIDTH = _glyph_box()


def _sheet(doc: fitz.Document, sheet: str) -> fitz.Page:
    portrait = sheet == "portrait"
    page = doc.new_page(width=612 if portrait else 792, height=792 if portrait else 612)
    if sheet == "portrait":
        page.insert_text((303, 750), "7", fontsize=12)
    elif sheet == "cw":
        page.insert_text((50, 306), "81", fontsize=12, rotate=270)
    elif sheet == "ccw":
        page.insert_text((742, 306), "81", fontsize=12, rotate=90)
    return page


def edge(sheet: str, side: str, intrusion: float) -> Builder:
    """One line crossing the reading-frame *side* by *intrusion* pt, plus body text."""

    def build(doc: fitz.Document) -> None:
        page = _sheet(doc, sheet)
        x0, y0, x1, y1 = FRAMES[sheet]
        origin = {
            "top": (200.0, y0 - intrusion + UP),
            "bottom": (200.0, y1 + intrusion - DOWN),
            "left": (x0 - intrusion - LEFT, 300.0),
            "right": (x1 + intrusion - LEFT - WIDTH, 300.0),
            "clean": (200.0, 300.0),
        }[side]
        page.insert_text(origin, TEXT, fontsize=FS)
        for k in range(4):
            page.insert_text((x0 + 20, y0 + 60 + 20 * k), TEXT, fontsize=FS)

    return build


def references_final_line(sheet: str) -> Builder:
    """A references page whose last entry line dips 8 pt past the reading-frame
    bottom boundary, directly above a horizontal page number."""

    def build(doc: fitz.Document) -> None:
        page = _sheet(doc, sheet)
        x0, y0, x1, y1 = FRAMES[sheet]
        last = y1 + 8.0 - DOWN
        page.insert_text(((x0 + x1) / 2 - 30, y0 + 30), "REFERENCES", fontsize=FS)
        for step in range(6, 0, -1):
            page.insert_text((x0 + 12, last - 13.0 * step), f"[{7 - step}] {TEXT}", fontsize=FS)
        page.insert_text(
            (x0 + 12, last), "https://doi.org/10.0000/synthetic.reference", fontsize=FS
        )
        page.insert_text((392, 600), "82", fontsize=FS)

    return build


LABEL_RIGHT_EDGE, TEXT_X = 102.5, 108.4
ENTRY = "A. Author and B. Author, A synthetic article title, Journal, 2020."
CONTINUATION = "vol. 12, no. 3, pp. 45-67, a continuation line of the entry."


def _references_page(
    doc: fitz.Document, heading: str | None, first: int, count: int, text_x: float, folio: str
) -> None:
    page = doc.new_page(width=612, height=792)
    font = fitz.Font("tiro")
    writer = fitz.TextWriter(page.rect)
    if heading:
        writer.append((240, 90), heading, font=font, fontsize=FS)
    y = 130.0
    for number in range(first, first + count):
        label = f"[{number}]"
        label_x = LABEL_RIGHT_EDGE - font.text_length(label, fontsize=FS)
        writer.append((label_x, y), label, font=font, fontsize=FS)
        writer.append((text_x, y), ENTRY, font=font, fontsize=FS)
        writer.append((text_x + 36, y + 15), CONTINUATION, font=font, fontsize=FS)
        y += 40
    writer.append((303, 750), folio, font=font, fontsize=12)
    writer.write_text(page)


def references(text_x: float = TEXT_X) -> Builder:
    return lambda doc: _references_page(doc, "REFERENCES", 9, 4, text_x, "7")


def references_continuation(doc: fitz.Document) -> None:
    _references_page(doc, "REFERENCES", 81, 12, TEXT_X, "7")
    _references_page(doc, None, 93, 1, TEXT_X, "8")  # one entry, no heading


# ---------------------------------------------------------------------------
# Encodings
# ---------------------------------------------------------------------------


def _control(tmp_path: Path, build: Builder) -> Path:
    """The authored pages, routed through an XObject like the turned variants."""
    src = fitz.open()
    build(src)
    flat = fitz.open()
    for index, page in enumerate(src):
        out = flat.new_page(width=page.rect.width, height=page.rect.height)
        out.show_pdf_page(out.rect, src, index)
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / "control.pdf"
    flat.save(path)
    return path


def _viewer_only(control: Path, rotation: int) -> Path:
    doc = fitz.open(control)
    for page in doc:
        page.set_rotation(rotation)
    path = control.with_name(f"viewer_r{rotation}.pdf")
    doc.save(path)
    return path


def _content_turned(control: Path, rotation: int) -> Path:
    """Pixel-identical re-encoding whose content reads upright only after /Rotate.

    A landscape page at 90/270 is the pdflscape encoding (portrait MediaBox).
    """
    src = fitz.open(control)
    out = fitz.open()
    for index, page in enumerate(src):
        width, height = page.rect.width, page.rect.height
        if rotation % 180 == 90:
            width, height = height, width
        turned = out.new_page(width=width, height=height)
        turned.show_pdf_page(turned.rect, src, index, rotate=rotation)
        turned.set_rotation(rotation)
    doc = fitz.open("pdf", out.tobytes())
    for a, b in zip(src, doc):
        assert a.get_pixmap(dpi=30).samples == b.get_pixmap(dpi=30).samples
    path = control.with_name(f"turned_r{rotation}.pdf")
    doc.save(path)
    return path


def _warnings(path: Path) -> list[dict[str, str]]:
    findings = run_pdf_margin_rule(load_pdf_layout(str(path)))
    return [
        {"page": str(f.page), "message": f.message, **f.details}
        for f in findings
        if f.severity.value == "WARNING"
    ]


def _displayed(path: Path) -> list[tuple[object, ...]]:
    """Semantic fields plus every stored box as displayed (0.1 pt grid)."""
    out = []
    with fitz.open(path) as doc:
        for finding in _warnings(path):
            matrix = doc[int(finding["page"]) - 1].rotation_matrix
            boxes = tuple(
                tuple(
                    tuple(round(v, 1) for v in fitz.Rect(*map(float, chunk.split(","))) * matrix)
                    for chunk in finding.get(key, "").split(" | ")
                    if chunk
                )
                for key in BOXES
            )
            semantic = tuple(finding.get(key) for key in ("page", "message", *SEMANTIC))
            out.append((semantic, boxes))
    return sorted(out, key=str)


def _assert_same_display(control: Path, variant: Path) -> None:
    expected, actual = _displayed(control), _displayed(variant)
    assert [a for a, _ in actual] == [e for e, _ in expected]
    for (_, actual_boxes), (_, expected_boxes) in zip(actual, expected):
        for got, want in zip(actual_boxes, expected_boxes):
            assert len(got) == len(want)
            for g, w in zip(got, want):
                assert g == pytest.approx(w, abs=0.15)


SIDES = ("clean", "left", "right", "top", "bottom")
PORTRAIT_INTRUSIONS = {"clean": 0, "left": 6, "right": 6, "top": 6, "bottom": 13}


# ---------------------------------------------------------------------------
# Viewer-only /Rotate: exact /Rotate 0 verdict
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("rotation", (90, 180, 270))
@pytest.mark.parametrize("sheet", ("portrait", "cw", "ccw"))
@pytest.mark.parametrize("side", SIDES)
def test_viewer_only_rotation_keeps_the_rotate_0_verdict(
    tmp_path: Path, side: str, sheet: str, rotation: int
) -> None:
    control = _control(tmp_path, edge(sheet, side, PORTRAIT_INTRUSIONS[side]))
    expected = _warnings(control)
    assert bool(expected) is (side != "clean")
    assert _warnings(_viewer_only(control, rotation)) == expected


# ---------------------------------------------------------------------------
# pdflscape: clockwise sheet (/Rotate 90) and counter-clockwise sheet (/Rotate 270)
# ---------------------------------------------------------------------------

PDFLSCAPE = {"cw": 90, "ccw": 270}
LANDSCAPE_CASES = {
    "cw": [("clean", 0), ("top", 8), ("top", 22), ("left", 6), ("right", 6), ("bottom", 13)],
    "ccw": [("clean", 0), ("bottom", 8), ("bottom", 22), ("top", 6), ("left", 6), ("right", 6)],
}


@pytest.mark.parametrize(
    ("sheet", "side", "intrusion"),
    [(sheet, side, d) for sheet, cases in LANDSCAPE_CASES.items() for side, d in cases],
)
def test_pdflscape_matches_the_intrinsic_landscape_page(
    tmp_path: Path, sheet: str, side: str, intrusion: float
) -> None:
    control = _control(tmp_path, edge(sheet, side, intrusion))
    variant = _content_turned(control, PDFLSCAPE[sheet])
    page = load_pdf_layout(str(variant)).pages[0]
    frame = PdfReadingFrame.for_page(page)
    assert frame.box_size == (612.0, 792.0) and frame.reading_size == (792.0, 612.0)
    assert r011._margin_frame(page).binding_edge == ("top" if sheet == "cw" else "bottom")
    _assert_same_display(control, variant)
    found = _warnings(variant)
    if side == "clean":
        assert found == []
    else:
        [finding] = found
        assert finding["side"] == f"{side}_margin"
        assert finding["page_orientation"] == "landscape"
        assert finding["worst_overflow_pt"] == f"{intrusion:.1f}"


@pytest.mark.parametrize(("sheet", "edge_name"), [("cw", "top"), ("ccw", "bottom")])
def test_pdflscape_binding_finding_wording_matches_intrinsic(
    tmp_path: Path, sheet: str, edge_name: str
) -> None:
    control = _control(tmp_path, edge(sheet, edge_name, 22))
    variant = _content_turned(control, PDFLSCAPE[sheet])
    [intrinsic] = _warnings(control)
    [pdflscape] = _warnings(variant)
    phrase = f"{edge_name} margin (the 1.5-inch binding margin on this landscape page)"
    for details in (intrinsic, pdflscape):
        assert details["binding_edge"] == edge_name
        assert phrase in _p011_margin_comment(page=1, details=details)
    assert pdflscape["suggested_fix"] == intrinsic["suggested_fix"]


# ---------------------------------------------------------------------------
# Bottom-only allowances follow the reading-frame bottom, never a binding edge
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("encoding", ("intrinsic", "pdflscape"))
def test_ordinary_reading_bottom_keeps_the_allowance(tmp_path: Path, encoding: str) -> None:
    control = _control(tmp_path, edge("cw", "bottom", 8))
    path = control if encoding == "intrinsic" else _content_turned(control, 90)
    assert _warnings(path) == []


@pytest.mark.parametrize("encoding", ("intrinsic", "pdflscape"))
def test_binding_bottom_does_not_get_the_allowance(tmp_path: Path, encoding: str) -> None:
    control = _control(tmp_path, edge("ccw", "bottom", 8))
    path = control if encoding == "intrinsic" else _content_turned(control, 270)
    assert [(f["side"], f["binding_edge"]) for f in _warnings(path)] == [
        ("bottom_margin", "bottom")
    ]


@pytest.mark.parametrize("encoding", ("intrinsic", "pdflscape"))
def test_references_final_line_allowance_follows_the_reading_bottom(
    tmp_path: Path, encoding: str
) -> None:
    ordinary = _control(tmp_path / "cw", references_final_line("cw"))
    binding = _control(tmp_path / "ccw", references_final_line("ccw"))
    if encoding == "pdflscape":
        ordinary, binding = _content_turned(ordinary, 90), _content_turned(binding, 270)
    assert _warnings(ordinary) == []
    assert [f["side"] for f in _warnings(binding)] == ["bottom_margin"]


def test_portrait_references_final_line_allowance_survives_content_turning(
    tmp_path: Path,
) -> None:
    control = _control(tmp_path, references_final_line("portrait"))
    assert _warnings(control) == []
    for rotation in (90, 180, 270):
        assert _warnings(_content_turned(control, rotation)) == []


# ---------------------------------------------------------------------------
# Content-turned portrait pages keep portrait policy
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("rotation", (90, 180, 270))
@pytest.mark.parametrize(
    ("side", "intrusion"),
    [
        ("clean", 0),
        ("left", 6),
        ("left", 30),
        ("right", 20),
        ("top", 20),
        ("bottom", 8),
        ("bottom", 30),
    ],
)
def test_content_turned_portrait_page_keeps_portrait_policy(
    tmp_path: Path, side: str, intrusion: float, rotation: int
) -> None:
    control = _control(tmp_path, edge("portrait", side, intrusion))
    variant = _content_turned(control, rotation)
    page = load_pdf_layout(str(variant)).pages[0]
    assert PdfReadingFrame.for_page(page).policy_orientation == "portrait"
    margin = r011._margin_frame(page)
    assert (margin.binding_edge, margin.allowed_x0) == ("left", r011.LEFT_MARGIN_PT)
    _assert_same_display(control, variant)
    assert all("page_orientation" not in f for f in _warnings(variant))


@pytest.mark.parametrize("rotation", (90, 180, 270))
@pytest.mark.parametrize("sheet", ("cw", "ccw"))
def test_content_turned_landscape_page_matches_control(
    tmp_path: Path, sheet: str, rotation: int
) -> None:
    for side, intrusion in LANDSCAPE_CASES[sheet]:
        control = _control(tmp_path / f"{side}{intrusion}", edge(sheet, side, intrusion))
        _assert_same_display(control, _content_turned(control, rotation))


# ---------------------------------------------------------------------------
# Page numbers, unknown binding edge, References
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("rotation", (0, 90, 270))
@pytest.mark.parametrize("sheet", ("portrait", "cw", "ccw"))
def test_page_number_is_never_a_violation(tmp_path: Path, sheet: str, rotation: int) -> None:
    control = _control(tmp_path, edge(sheet, "clean", 0))
    for path in (
        [control]
        if rotation == 0
        else [_viewer_only(control, rotation), _content_turned(control, rotation)]
    ):
        assert _warnings(path) == []


@pytest.mark.parametrize("rotation", (0, 90, 270))
def test_unknown_binding_edge_stays_conservative(tmp_path: Path, rotation: int) -> None:
    def encode(control: Path) -> Path:
        return control if rotation == 0 else _content_turned(control, rotation)

    inside_both = encode(_control(tmp_path / "a", edge("undetermined", "top", 30)))
    certain = encode(_control(tmp_path / "b", edge("undetermined", "top", 45)))
    lenient_bottom = encode(_control(tmp_path / "c", edge("undetermined", "bottom", 8)))
    assert r011._margin_frame(load_pdf_layout(str(certain)).pages[0]).binding_edge == (
        "undetermined"
    )
    [inside_finding] = _warnings(inside_both)
    [certain_finding] = _warnings(certain)
    for finding in (inside_finding, certain_finding):
        assert finding["side"] == "top_margin" and finding["binding_edge"] == "undetermined"
        assert "binding margin" not in _p011_margin_comment(page=1, details=finding)
    assert _warnings(lenient_bottom) == []


ENCODINGS = [("viewer", 90), ("viewer", 270), ("turned", 90), ("turned", 180), ("turned", 270)]


def _encode(control: Path, family: str, rotation: int) -> Path:
    return (
        _viewer_only(control, rotation)
        if family == "viewer"
        else _content_turned(control, rotation)
    )


def _assert_equivalent(control: Path, family: str, rotation: int) -> None:
    """Viewer-only: identical in box space. Content-turned: identical as displayed."""
    variant = _encode(control, family, rotation)
    if family == "viewer":
        assert _warnings(variant) == _warnings(control)
    else:
        _assert_same_display(control, variant)


@pytest.mark.parametrize(("family", "rotation"), ENCODINGS)
def test_outdented_reference_labels_stay_exempt(tmp_path: Path, family: str, rotation: int) -> None:
    control = _control(tmp_path, references())
    assert _warnings(control) == []
    assert _warnings(_encode(control, family, rotation)) == []


@pytest.mark.parametrize(("family", "rotation"), ENCODINGS)
def test_reference_entry_text_crossing_still_reports(
    tmp_path: Path, family: str, rotation: int
) -> None:
    control = _control(tmp_path, references(TEXT_X - 14))
    expected = _warnings(control)
    assert [f["side"] for f in expected] == ["left_margin"]
    _assert_equivalent(control, family, rotation)


@pytest.mark.parametrize(("family", "rotation"), ENCODINGS)
def test_references_continuation_survives_rotation(
    tmp_path: Path, family: str, rotation: int
) -> None:
    control = _control(tmp_path, references_continuation)
    assert _warnings(control) == []
    variant = _encode(control, family, rotation)
    assert set(r011._reference_label_columns(load_pdf_layout(str(variant)))) == {1, 2}
    assert _warnings(variant) == []


# ---------------------------------------------------------------------------
# Stored boxes, presentation, B2, static guard
# ---------------------------------------------------------------------------


def _offending_line_box(path: Path, needle: str) -> tuple[float, ...]:
    page = load_pdf_layout(str(path)).pages[0]
    [line] = [
        line for block in page.text_blocks for line in block.lines if line.text.startswith(needle)
    ]
    return tuple(round(v, 1) for v in (line.bbox.x0, line.bbox.y0, line.bbox.x1, line.bbox.y1))


@pytest.mark.parametrize("cropbox", (False, True))
@pytest.mark.parametrize("rotation", (0, 90, 180, 270))
def test_stored_box_is_the_source_line_in_box_space(
    tmp_path: Path, rotation: int, cropbox: bool
) -> None:
    def build(doc: fitz.Document) -> None:
        page = _sheet(doc, "portrait")
        page.insert_text((200, 300), TEXT, fontsize=FS)
        page.insert_text((70, 400), "Offending " + TEXT, fontsize=FS)

    control = _control(tmp_path, build)
    path = control if rotation == 0 else _content_turned(control, rotation)
    if cropbox:
        doc = fitz.open(path)
        doc[0].set_cropbox(fitz.Rect(4, 6, doc[0].mediabox.width - 5, doc[0].mediabox.height - 3))
        path = path.with_name("cropped.pdf")
        doc.save(path)
    [finding] = _warnings(path)
    assert finding["side"] == "left_margin"
    stored = tuple(float(v) for v in finding["bbox"].split(","))
    assert stored == pytest.approx(_offending_line_box(path, "Offending"), abs=0.06)


@pytest.mark.parametrize(("sheet", "rotation"), [("cw", 90), ("ccw", 270)])
def test_pdflscape_binding_finding_highlights_the_displayed_line(
    tmp_path: Path, sheet: str, rotation: int
) -> None:
    edge_name = "top" if sheet == "cw" else "bottom"
    control = _control(tmp_path, edge(sheet, edge_name, 22))
    variant = _content_turned(control, rotation)
    renders = {}
    for label, path in (("control", control), ("variant", variant)):
        [finding] = _warnings(path)
        box = tuple(float(v) for v in finding["bbox"].split(","))
        out = path.with_name(f"{label}_hl.pdf")
        assert build_highlighted_pdf(path, out, {1: [box]}).drawn_count == 1  # type: ignore[list-item]
        with fitz.open(out) as doc:
            pix = doc[0].get_pixmap(dpi=72)
            renders[label] = (pix.width, pix.height, pix.samples)
        combined = build_combined_student_pdf_report(
            path,
            path.with_name(f"{label}_combined.pdf"),
            [
                {
                    "problem_number": 1,
                    "page": 1,
                    "rule_id": "P011",
                    "public_rule_reference_id": "R011",
                    "issue_type_label": "Margin issue",
                    "polished_comment": _p011_margin_comment(page=1, details=finding),
                    "suggested_fix": finding["suggested_fix"],
                    "location_label": f"{edge_name.title()} margin",
                    "confidence_label": "High confidence",
                }
            ],
            boxes_by_problem={1: [box]},  # type: ignore[dict-item]
            file_name="thesis.pdf",
        )
        assert combined.highlight_boxes_drawn == 1 and combined.markers_drawn == 1
    assert renders["variant"] == renders["control"]
    assert getattr(get_pdf_page_sizes(variant)[0], "rotation", 0) == rotation


def test_b2_near_tie_is_a_known_deferred_limitation(tmp_path: Path) -> None:
    """B2 (reading-frame confidence) is deferred, and the inference is unchanged.

    R011 now consumes the same character-weighted ``reading_frame_rotation``
    as R035. Sideways note text that outweighs the upright body on a
    viewer-only ``/Rotate 90`` page flips the inferred frame to 90, so R011
    measures the page in that frame: the 28 pt violation is still reported
    with the same overflow, but its side is named in the flipped frame
    (``top_margin``; the ``/Rotate 0`` page says ``left_margin``). This pins
    the current limitation; a B2 fix (confidence/abstention) must change it
    deliberately.
    """

    def build(doc: fitz.Document) -> None:
        page = _sheet(doc, "portrait")
        page.insert_text((200, 300), TEXT, fontsize=FS)
        page.insert_text((80, 400), TEXT, fontsize=FS)  # 28 pt into the 1.5 in left margin
        for k in range(2):
            page.insert_text((300 + 14 * k, 600), TEXT + " more", fontsize=10, rotate=90)

    control = _control(tmp_path, build)
    viewer = _viewer_only(control, 90)
    assert PdfReadingFrame.for_page(load_pdf_layout(str(control)).pages[0]).reading_rotation == 0
    assert PdfReadingFrame.for_page(load_pdf_layout(str(viewer)).pages[0]).reading_rotation == 90
    assert [(f["side"], f["worst_overflow_pt"]) for f in _warnings(control)] == [
        ("left_margin", "28.0")
    ]
    assert [(f["side"], f["worst_overflow_pt"]) for f in _warnings(viewer)] == [
        ("top_margin", "28.0")
    ]


def test_r011_policy_geometry_never_reads_the_displayed_page() -> None:
    """Static guard: R011 sizes and orientation come from PdfReadingFrame."""
    tree = ast.parse(Path(r011.__file__).read_text(encoding="utf-8"))
    leaks = [
        f"line {node.lineno}: {ast.unparse(node)}"
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and (
            node.attr in {"is_visually_landscape", "rect", "page_rotation", "rotation"}
            or (
                node.attr in {"width", "height"}
                and isinstance(node.value, ast.Name)
                and node.value.id in {"page", "source_page", "raw_page"}
            )
        )
    ]
    assert leaks == []
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    assert "text_space_size" not in names
