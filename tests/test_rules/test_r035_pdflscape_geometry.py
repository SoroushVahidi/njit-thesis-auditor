"""R035 on pdflscape landscape pages (synthetic PDFs only).

A pdflscape landscape page keeps a portrait MediaBox with ``/Rotate 90`` (or
270) and draws its content sideways, so it *displays* exactly like an
intrinsic 792x612 landscape page. PyMuPDF reports every box in the unrotated
space, where the figure sits beside its caption and visible table rules are
vertical. R035 asks a visual question, so it must measure such a page in its
displayed reading frame and reach the same verdict as the intrinsic page.

Every variant below is asserted to render identically to its intrinsic
control. Arbitrary whole-page ``/Rotate`` is out of scope here, except that a
viewer-only rotation (already-upright content turned in the viewer) must keep
its existing behaviour.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import fitz
import pytest

from njit_auditor.models import AuditFinding
from njit_auditor.pdf_highlight import (
    build_highlighted_pdf,
    get_pdf_page_sizes,
    sub_page_location_label,
)
from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.pdf_models import reading_frame_rotation
from njit_auditor.rules.pdf_figure_table_layout import check_pdf_figure_table_layout

CENTER = (108 + 792 - 72) / 2  # R035's landscape text-area centre
BODY = "Synthetic body sentence used only for geometry testing of the auditor here."
QUARTER_TURNS = (90, 270)
Builder = Callable[[fitz.Document], None]


def _pixmap() -> fitz.Pixmap:
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 16, 16), False)
    pix.clear_with(90)
    return pix


def _portrait(doc: fitz.Document, number: int) -> None:
    page = doc.new_page(width=612, height=792)
    for k in range(22):
        page.insert_text((108, 110 + 26 * k), BODY, fontsize=12)
    page.insert_text((303, 750), str(number), fontsize=12)


def _centered_text(page: fitz.Page, text: str, y: float) -> None:
    width = fitz.get_text_length(text, fontsize=12)
    page.insert_text((CENTER - width / 2, y), text, fontsize=12)


def _landscape(doc: fitz.Document) -> fitz.Page:
    page = doc.new_page(width=792, height=612)
    page.insert_text((40, 300), "2", fontsize=12, rotate=270)  # portrait folio
    return page


def figure(drift: float = 0.0, caption: str = "below", unrelated: bool = False) -> Builder:
    def build(doc: fitz.Document) -> None:
        page = _landscape(doc)
        cx, top = CENTER + drift, 150.0
        text = "Figure 2.1 A synthetic landscape figure used for rotation testing"
        if caption == "above":
            _centered_text(page, text, 140)
            top = 160.0
        page.insert_image(fitz.Rect(cx - 200, top, cx + 200, top + 250), pixmap=_pixmap())
        if caption == "below":
            _centered_text(page, text, top + 280)
        if unrelated:
            page.insert_text(
                (108, 540),
                "An unrelated sentence of ordinary body prose follows here.",
                fontsize=12,
            )
            page.insert_text(
                (108, 556), "It continues with a second line of ordinary prose for it.", fontsize=12
            )

    return build


def table(drift: float = 0.0, caption: str = "above") -> Builder:
    def build(doc: fitz.Document) -> None:
        page = _landscape(doc)
        width = 440.0
        x0 = CENTER + drift - width / 2
        text = "Table 2.1 A synthetic ruled table used for rotation testing"
        rows = [
            "Header alpha beta",
            "Row one alpha",
            "Row two beta",
            "Row three gamma",
            "Row four delta",
        ]
        top = 155.0 if caption == "above" else 140.0
        if caption == "above":
            _centered_text(page, text, 140)
        rule_ys = [top, top + 25, top + 25 * len(rows) + 10]
        for y in rule_ys:
            page.draw_line((x0, y), (x0 + width, y), color=(0, 0, 0), width=0.8)
        for k, row in enumerate(rows):
            while fitz.get_text_length(row + " 12.5", fontsize=11) < width - 24:
                row += " 12.5"
            page.insert_text((x0 + 8, top + 17 + k * 25 + (6 if k else 0)), row, fontsize=11)
        if caption == "below":
            _centered_text(page, text, rule_ys[-1] + 28)

    return build


def _encode(control: fitz.Document, rotation: int) -> fitz.Document:
    """Re-encode page 2 pdflscape-style: portrait MediaBox + ``/Rotate``."""
    if rotation == 0:
        return control
    out = fitz.open()
    for index, src_page in enumerate(control):
        if index != 1:
            out.insert_pdf(control, from_page=index, to_page=index)
            continue
        width, height = src_page.rect.width, src_page.rect.height
        if rotation % 180 == 90:
            width, height = height, width
        page = out.new_page(width=width, height=height)
        page.show_pdf_page(page.rect, control, index, rotate=rotation)
        page.set_rotation(rotation)
    return fitz.open("pdf", out.tobytes())


def _pixels(doc: fitz.Document, dpi: int = 30) -> tuple[int, int, bytes]:
    pix = doc[1].get_pixmap(dpi=dpi)
    return pix.width, pix.height, pix.samples


def _variant(tmp_path: Path, build: Builder, rotation: int) -> Path:
    src = fitz.open()
    _portrait(src, 1)
    build(src)
    _portrait(src, 3)
    flat = fitz.open()
    for index, src_page in enumerate(src):
        page = flat.new_page(width=src_page.rect.width, height=src_page.rect.height)
        page.show_pdf_page(page.rect, src, index)
    control = fitz.open("pdf", flat.tobytes())
    doc = _encode(control, rotation)
    assert _pixels(doc) == _pixels(control)
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / f"variant_r{rotation}.pdf"
    doc.save(path)
    return path


def _displayed(path: Path, raw: str | None) -> tuple[float, ...] | None:
    if not raw:
        return None
    with fitz.open(path) as doc:
        page = doc[1]
        rect = fitz.Rect(*(float(v) for v in raw.split(","))) * page.rotation_matrix
    return tuple(round(v, 1) for v in rect)


def _semantics(path: Path) -> list[tuple[object, ...]]:
    """Each R035 finding as displayed: type, drift, severity and display boxes."""
    findings: list[AuditFinding] = check_pdf_figure_table_layout(load_pdf_layout(str(path)))
    return [
        (
            f.page,
            f.details["issue_type"],
            f.details.get("center_delta_points"),
            f.details.get("allowed_center_delta_points"),
            str(f.severity),
            _displayed(path, f.details.get("bbox")),
            _displayed(path, f.details.get("body_bbox")),
            _displayed(path, f.details.get("caption_bbox")),
        )
        for f in findings
    ]


SCENARIOS: dict[str, tuple[Builder, str | None, str | None]] = {
    # name: (builder, expected issue type, expected drift)
    "figure_centered": (figure(0), None, None),
    "figure_below_threshold": (figure(45), None, None),
    "figure_above_threshold": (figure(55), "figure_body_not_centered", "55.0"),
    "figure_62pt_right": (figure(62), "figure_body_not_centered", "62.0"),
    "figure_62pt_left": (figure(-62), "figure_body_not_centered", "62.0"),
    "figure_caption_above": (figure(0, caption="above"), "figure_caption_not_below_body", None),
    "figure_with_unrelated_text": (figure(0, unrelated=True), None, None),
    "table_centered": (table(0), None, None),
    "table_62pt": (table(62), "table_body_not_centered", "62.0"),
    "table_caption_below": (table(0, caption="below"), "table_caption_not_above_body", None),
}


@pytest.mark.parametrize("name", sorted(SCENARIOS))
def test_intrinsic_landscape_control_verdict(tmp_path: Path, name: str) -> None:
    build, issue, drift = SCENARIOS[name]
    found = _semantics(_variant(tmp_path, build, 0))
    if issue is None:
        assert found == []
    else:
        assert [(f[1], f[2]) for f in found] == [(issue, drift)]


@pytest.mark.parametrize("rotation", QUARTER_TURNS)
@pytest.mark.parametrize("name", sorted(SCENARIOS))
def test_pdflscape_verdict_matches_intrinsic_landscape(
    tmp_path: Path, name: str, rotation: int
) -> None:
    build = SCENARIOS[name][0]
    control = _semantics(_variant(tmp_path / "control", build, 0))
    assert _semantics(_variant(tmp_path / "rotated", build, rotation)) == control


@pytest.mark.parametrize("rotation", (0, *QUARTER_TURNS))
def test_visually_horizontal_table_rules_are_recognised(tmp_path: Path, rotation: int) -> None:
    path = _variant(tmp_path, table(62), rotation)
    model = load_pdf_layout(str(path))
    rules = model.pages[1].horizontal_rules
    assert len(rules) == 3
    with fitz.open(path) as doc:
        page = doc[1]
        displayed = [fitz.Rect(r.x0, r.y0, r.x1, r.y1) * page.rotation_matrix for r in rules]
    assert all(rect.width >= 400 and rect.height <= 2 for rect in displayed)
    # Stored in unrotated space like every other box on the page.
    if rotation:
        assert all(r.x1 - r.x0 <= 2 for r in rules)


@pytest.mark.parametrize("rotation", QUARTER_TURNS)
def test_pdflscape_finding_box_highlights_the_displayed_figure(
    tmp_path: Path, rotation: int
) -> None:
    control_path = _variant(tmp_path / "control", figure(62), 0)
    rotated_path = _variant(tmp_path / "rotated", figure(62), rotation)
    outputs = {}
    labels = {}
    for label, path in (("control", control_path), ("rotated", rotated_path)):
        [finding] = check_pdf_figure_table_layout(load_pdf_layout(str(path)))
        box = tuple(float(v) for v in finding.details["bbox"].split(","))
        labels[label] = sub_page_location_label(box, get_pdf_page_sizes(path)[1])  # type: ignore[arg-type]
        out = path.with_name(f"{label}_hl.pdf")
        assert build_highlighted_pdf(path, out, {2: [box]}).drawn_count == 1  # type: ignore[list-item]
        with fitz.open(out) as doc:
            # 72 dpi: at 30 dpi the annotation border's antialiasing differs by
            # a few levels on a quarter-turned page.
            outputs[label] = _pixels(doc, dpi=72)
    assert labels["rotated"] == labels["control"] == "Near page center"
    assert outputs["rotated"] == outputs["control"]


@pytest.mark.parametrize("rotation", (90, 180, 270))
@pytest.mark.parametrize("name", ["figure_62pt_right", "table_62pt", "figure_caption_above"])
def test_viewer_only_rotation_keeps_existing_measurement(
    tmp_path: Path, name: str, rotation: int
) -> None:
    """Upright landscape content with ``/Rotate`` set on top displays sideways;
    it is not a pdflscape page and keeps the unrotated-frame measurement."""
    control = _variant(tmp_path, SCENARIOS[name][0], 0)
    doc = fitz.open(control)
    doc[1].set_rotation(rotation)
    turned = tmp_path / "viewer_only.pdf"
    doc.save(turned)
    expected = check_pdf_figure_table_layout(load_pdf_layout(str(control)))
    model = load_pdf_layout(str(turned))
    actual = check_pdf_figure_table_layout(model)
    assert [f.details["bbox"] for f in actual] == [f.details["bbox"] for f in expected]
    assert len(model.pages[1].horizontal_rules) == len(
        load_pdf_layout(str(control)).pages[1].horizontal_rules
    )


def test_reading_frame_rotation() -> None:
    sideways_down = [((0.0, -1.0), 40)]
    assert reading_frame_rotation(0, sideways_down) == 0
    assert reading_frame_rotation(90, sideways_down) == 90
    assert reading_frame_rotation(270, [((0.0, 1.0), 40)]) == 270
    assert reading_frame_rotation(180, [((-1.0, 0.0), 40)]) == 180
    # Already upright text: /Rotate only turns the sheet in the viewer.
    assert reading_frame_rotation(90, [((1.0, 0.0), 40)]) == 0
    # The dominant writing direction decides; a sideways folio does not.
    assert reading_frame_rotation(90, [((1.0, 0.0), 400), ((0.0, -1.0), 2)]) == 0
    assert reading_frame_rotation(90, []) == 0
    assert reading_frame_rotation(90, [(None, 40)]) == 0
    assert reading_frame_rotation(450, sideways_down) == 90


def test_portrait_page_is_measured_unchanged(tmp_path: Path) -> None:
    src = fitz.open()
    page = src.new_page(width=612, height=792)
    page.insert_image(fitz.Rect(214, 150, 474, 390), pixmap=_pixmap())  # +20 pt from 324
    page.insert_text(
        (180, 420), "Figure 1.1 A synthetic portrait figure for this test", fontsize=12
    )
    path = tmp_path / "portrait.pdf"
    src.save(path)
    [finding] = check_pdf_figure_table_layout(load_pdf_layout(str(path)))
    assert finding.details["issue_type"] == "figure_body_not_centered"
    assert finding.details["center_delta_points"] == "20.0"
    assert finding.details["bbox"] == "214.0,150.0,474.0,390.0"
