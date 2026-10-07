"""Highlight clipping, location labels and markers on ``/Rotate`` pages (synthetic PDFs only).

PyMuPDF extracts text, image and drawing boxes -- and reads/writes annotation
rects -- in the page's *unrotated*, CropBox-relative space, while ``page.rect``
is the displayed size after ``/Rotate``. Presentation code must clip finding
boxes against bounds in that same unrotated space, and describe where a box
sits as the student sees the displayed page.

Every rotated variant here is built to look identical on screen to its
``/Rotate 0`` control (asserted by rendering), so the presentation must agree.
Detector decisions are not under test: boxes come straight from extraction.
"""

from __future__ import annotations

import copy
import pickle
from pathlib import Path

import fitz
import pytest

from njit_auditor.high_volume_student_preview import margin_location_label
from njit_auditor.pdf_highlight import (
    HighlightBox,
    PageBoxSpace,
    box_to_display_space,
    build_highlighted_pdf,
    build_highlighted_single_page_pdf,
    clip_box_to_page,
    display_page_size,
    get_pdf_page_sizes,
    has_visible_highlight,
    page_box_space,
    sub_page_location_label,
)
from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.report_view import build_report_view
from njit_auditor.rules.pdf_page_numbers import (
    check_pdf_page_number_sequence,
    detect_page_number_candidates,
)
from njit_auditor.student_pdf_report import build_combined_student_pdf_report

ROTATIONS = (0, 90, 180, 270)
BODY = "Synthetic body sentence used only for rotated presentation testing"
Box = tuple[float, float, float, float]


def _with_rotation(
    src: fitz.Document, rotation: int, pages: set[int] | None = None
) -> fitz.Document:
    """Re-encode *pages* (0-based; all when None) with ``/Rotate rotation`` so
    they display exactly as before (the pdflscape encoding)."""
    out = fitz.open()
    for index, src_page in enumerate(src):
        if rotation == 0 or (pages is not None and index not in pages):
            out.insert_pdf(src, from_page=index, to_page=index)
            continue
        width, height = src_page.rect.width, src_page.rect.height
        if rotation % 180 == 90:
            width, height = height, width
        page = out.new_page(width=width, height=height)
        page.show_pdf_page(page.rect, src, index, rotate=rotation)
        page.set_rotation(rotation)
    return fitz.open("pdf", out.tobytes())


def _pixels(doc: fitz.Document, page: int = 0) -> tuple[int, int, bytes]:
    pix = doc[page].get_pixmap(dpi=36, annots=True)
    return pix.width, pix.height, pix.samples


def _generic_source(*, cropbox: tuple[float, float, float, float] | None = None) -> fitz.Document:
    """A portrait page with text near the bottom and right edges, an image and
    a vector drawing, routed through a Form XObject like the rotated variants."""
    raw = fitz.open()
    page = raw.new_page(width=612, height=792)
    page.insert_text((80, 770), "EDGE BOTTOM LINE", fontsize=11)
    page.insert_text((480, 400), "RIGHTSIDE", fontsize=11)
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 40, 30), False)
    pix.clear_with(120)
    page.insert_image(fitz.Rect(300, 150, 420, 240), pixmap=pix)
    page.draw_rect(fitz.Rect(100, 500, 250, 600), color=(0, 0, 1), width=2)
    flat = fitz.open()
    target = flat.new_page(width=612, height=792)
    target.show_pdf_page(target.rect, raw, 0)
    if cropbox is not None:
        target.set_cropbox(fitz.Rect(*cropbox))
    return fitz.open("pdf", flat.tobytes())


def _object_boxes(path: Path) -> dict[str, Box]:
    """Boxes of each source object, as extraction reports them."""
    model = load_pdf_layout(str(path))
    page = model.pages[0]
    boxes: dict[str, Box] = {}
    for block in page.text_blocks:
        for line in block.lines:
            bbox = (line.bbox.x0, line.bbox.y0, line.bbox.x1, line.bbox.y1)
            if "EDGE" in line.text:
                boxes["text_bottom"] = bbox
            if "RIGHTSIDE" in line.text:
                boxes["text_right"] = bbox
    images = [g for g in page.graphic_blocks if g.kind == "image"]
    boxes["image"] = (images[0].bbox.x0, images[0].bbox.y0, images[0].bbox.x1, images[0].bbox.y1)
    with fitz.open(path) as doc:
        pdf_page = doc[0]
        drawing = [d["rect"] for d in pdf_page.get_drawings() if d.get("color") == (0.0, 0.0, 1.0)]
    boxes["drawing"] = tuple(drawing[0])  # type: ignore[assignment]
    return boxes


@pytest.fixture(
    scope="module", params=[None, (20.0, 10.0, 600.0, 790.0)], ids=["mediabox", "cropbox"]
)
def generic_variants(
    request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory
) -> dict[int, Path]:
    base = _generic_source(cropbox=request.param)
    tmp = tmp_path_factory.mktemp("generic")
    paths: dict[int, Path] = {}
    for rotation in ROTATIONS:
        doc = _with_rotation(base, rotation)
        assert _pixels(doc) == _pixels(base)
        paths[rotation] = tmp / f"r{rotation}.pdf"
        doc.save(paths[rotation])
    return paths


# ---------------------------------------------------------------------------
# Same-space bounds and the display transform
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("rotation", ROTATIONS)
@pytest.mark.parametrize("cropbox", [None, (40.0, 30.0, 600.0, 780.0)])
def test_box_space_and_display_transform_match_pymupdf(
    rotation: int, cropbox: tuple[float, float, float, float] | None
) -> None:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    if cropbox is not None:
        page.set_cropbox(fitz.Rect(*cropbox))
    page.insert_text((100, 700), "LOWEDGE", fontsize=12)
    page.set_rotation(rotation)
    page = fitz.open("pdf", doc.tobytes())[0]
    space = page_box_space(page)
    unrotated = page.rect * page.derotation_matrix
    assert (unrotated.x0, unrotated.y0) == (0, 0)  # CropBox-relative, even when offset
    assert tuple(space) == (unrotated.width, unrotated.height)
    assert space.rotation == rotation
    assert display_page_size(space) == (page.rect.width, page.rect.height)
    word = fitz.Rect(page.get_text("words")[0][:4])
    assert fitz.Rect(*clip_box_to_page(tuple(word), *space) or ()) == word  # type: ignore[arg-type]
    expected = word * page.rotation_matrix
    assert box_to_display_space(tuple(word), space) == pytest.approx(tuple(expected))  # type: ignore[arg-type]


def test_plain_tuple_page_size_is_treated_as_unrotated() -> None:
    box = (10.0, 20.0, 30.0, 40.0)
    assert box_to_display_space(box, (612.0, 792.0)) == box
    assert display_page_size((612.0, 792.0)) == (612.0, 792.0)
    assert PageBoxSpace(612.0, 792.0, 450).rotation == 90
    assert PageBoxSpace(612.0, 792.0, -90).rotation == 270
    assert PageBoxSpace(612.0, 792.0, 45).rotation == 0


def test_page_box_space_survives_copy_and_pickle() -> None:
    space = PageBoxSpace(612.0, 792.0, 90)
    for clone in (copy.copy(space), copy.deepcopy(space), pickle.loads(pickle.dumps(space))):
        assert isinstance(clone, PageBoxSpace)
        assert tuple(clone) == (612.0, 792.0)
        assert clone.rotation == 90


def test_portrait_page_sizes_are_unchanged(tmp_path: Path) -> None:
    path = tmp_path / "portrait.pdf"
    with fitz.open() as doc:
        doc.new_page(width=612, height=792)
        doc.new_page(width=792, height=612)
        doc.save(path)
    assert get_pdf_page_sizes(path) == [(612.0, 792.0), (792.0, 612.0)]
    assert [s.rotation for s in get_pdf_page_sizes(path)] == [0, 0]


# ---------------------------------------------------------------------------
# Clipping, drawing and labels across rotations
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("obj", ["text_bottom", "text_right", "image", "drawing"])
def test_highlight_survives_and_renders_identically_at_every_rotation(
    generic_variants: dict[int, Path], obj: str, tmp_path: Path
) -> None:
    rendered = {}
    for rotation, path in generic_variants.items():
        box = _object_boxes(path)[obj]
        size = get_pdf_page_sizes(path)[0]
        assert clip_box_to_page(box, *size) == box  # retained, not truncated
        assert has_visible_highlight(box, page=1, page_count=1, page_size=size)
        output = tmp_path / f"{obj}_r{rotation}.pdf"
        result = build_highlighted_pdf(path, output, {1: [box]})
        assert result.drawn_count == 1 and result.skipped_count == 0
        with fitz.open(output) as doc:
            page = doc[0]
            rects = [fitz.Rect(a.rect) for a in page.annots()]
            assert len(rects) == 1 and rects[0].contains(fitz.Rect(*box))
            rendered[rotation] = _pixels(doc)
    assert all(pix == rendered[0] for pix in rendered.values())


@pytest.mark.parametrize(
    ("obj", "label"),
    [
        ("text_bottom", "Footer area"),
        ("text_right", "Right margin"),
        ("image", "body text"),
        ("drawing", "body text"),
    ],
)
def test_location_label_describes_the_displayed_page(
    generic_variants: dict[int, Path], obj: str, label: str
) -> None:
    for path in generic_variants.values():
        box = _object_boxes(path)[obj]
        assert sub_page_location_label(box, get_pdf_page_sizes(path)[0]) == label


def test_box_outside_the_page_is_still_clipped_or_rejected(
    generic_variants: dict[int, Path],
) -> None:
    size = get_pdf_page_sizes(generic_variants[90])[0]
    width, height = size
    assert clip_box_to_page((width - 10, 50, width + 40, 80), *size) == (width - 10, 50, width, 80)
    assert clip_box_to_page((width + 5, 50, width + 40, 80), *size) is None
    assert clip_box_to_page((10, height + 1, 40, height + 20), *size) is None
    assert clip_box_to_page((10, 50, 10, 80), *size) is None
    assert clip_box_to_page((float("nan"), 50, 40, 80), *size) is None
    assert not has_visible_highlight((width + 5, 50, width + 40, 80), page=1, page_size=size)
    assert sub_page_location_label((width + 5, 50, width + 40, 80), size) == ""


# ---------------------------------------------------------------------------
# P013 folio on a pdflscape landscape page (the confirmed real control)
# ---------------------------------------------------------------------------


def _p013_document(tmp_path: Path, rotation: int, sheet: str) -> Path:
    src = fitz.open()
    for number in range(1, 8):
        folio = str(number)
        half = fitz.get_text_length(folio, fontsize=12) / 2
        if number != 4:
            page = src.new_page(width=612, height=792)
            for k in range(20):
                page.insert_text((108, 110 + 26 * k), BODY, fontsize=12)
            page.insert_text((306 - half, 750), folio, fontsize=12)
            continue
        page = src.new_page(width=792, height=612)
        for k in range(14):
            page.insert_text((90, 130 + 26 * k), BODY, fontsize=12)
        if sheet == "cw":
            page.insert_text((40, 306 - half), folio, fontsize=12, rotate=270)
        else:
            page.insert_text((752, 306 + half), folio, fontsize=12, rotate=90)
    control = fitz.open("pdf", src.tobytes())
    doc = _with_rotation(control, rotation, {3})
    assert _pixels(doc, 3) == _pixels(control, 3)
    path = tmp_path / f"p013_{sheet}_r{rotation}.pdf"
    doc.save(path)
    return path


@pytest.mark.parametrize(
    ("rotation", "sheet", "label"),
    [(90, "cw", "Left margin"), (270, "ccw", "Right margin")],
)
def test_p013_folio_highlight_renders_on_pdflscape_page(
    tmp_path: Path, rotation: int, sheet: str, label: str
) -> None:
    control = _p013_document(tmp_path, 0, sheet)
    rotated = _p013_document(tmp_path, rotation, sheet)
    model = load_pdf_layout(str(rotated))
    assert check_pdf_page_number_sequence(model) == []
    candidate = [c for c in detect_page_number_candidates(model) if c.page_number == 4][0]
    box = tuple(float(v) for v in candidate.bbox)
    size = get_pdf_page_sizes(rotated)[3]
    assert box[3] > size[1] - 60  # the folio is near the bottom of the unrotated space
    assert clip_box_to_page(box, *size) == box  # type: ignore[arg-type]
    assert sub_page_location_label(box, size) == label  # type: ignore[arg-type]

    control_box = [
        tuple(float(v) for v in c.bbox)
        for c in detect_page_number_candidates(load_pdf_layout(str(control)))
        if c.page_number == 4
    ][0]
    assert sub_page_location_label(control_box, get_pdf_page_sizes(control)[3]) == label  # type: ignore[arg-type]

    out_rotated, out_control = tmp_path / "hl_rot.pdf", tmp_path / "hl_ctl.pdf"
    assert build_highlighted_pdf(rotated, out_rotated, {4: [box]}).drawn_count == 1  # type: ignore[list-item]
    assert build_highlighted_pdf(control, out_control, {4: [control_box]}).drawn_count == 1  # type: ignore[list-item]
    with fitz.open(out_rotated) as a, fitz.open(out_control) as b:
        assert _pixels(a, 3) == _pixels(b, 3)

    single = tmp_path / "single.pdf"
    result = build_highlighted_single_page_pdf(rotated, single, source_page_number=4, boxes=[box])  # type: ignore[list-item]
    assert result.has_highlight


# ---------------------------------------------------------------------------
# Markers: overflow numbers and combined-report problem badges
# ---------------------------------------------------------------------------


def _marker_words(page: fitz.Page) -> list[tuple[str, fitz.Rect, tuple[float, float]]]:
    """Marker text, its displayed rect and its displayed writing direction."""
    found = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            for span in line["spans"]:
                text = span["text"].strip()
                if text.lstrip("#").isdigit():
                    direction = fitz.Point(line["dir"]) * fitz.Matrix(page.rotation)
                    found.append(
                        (
                            text,
                            fitz.Rect(span["bbox"]) * page.rotation_matrix,
                            (round(direction.x), round(direction.y)),
                        )
                    )
    return found


def test_overflow_markers_and_problem_badges_are_upright_and_placed_identically(
    generic_variants: dict[int, Path], tmp_path: Path
) -> None:
    placements = {}
    for rotation, path in generic_variants.items():
        line = _object_boxes(path)["text_right"]
        x0, y0, x1, y1 = line
        overflow_a = HighlightBox(x0, y0, x1, y1, kind="overflow")
        overflow_b = HighlightBox(*_object_boxes(path)["text_bottom"], kind="overflow")
        output = tmp_path / f"markers_r{rotation}.pdf"
        finding = {
            "problem_number": 1,
            "page": 1,
            "rule_id": "P011",
            "public_rule_reference_id": "R011",
            "issue_type_label": "Margin issue",
            "polished_comment": "Text crosses the margin.",
            "suggested_fix": "Move it inside the margin.",
            "location_label": "Right margin",
            "confidence_label": "High confidence",
        }
        result = build_combined_student_pdf_report(
            path,
            output,
            [finding],
            boxes_by_problem={1: [overflow_a, overflow_b]},
            file_name="thesis.pdf",
        )
        assert result.highlight_boxes_drawn == 2 and result.markers_drawn == 1
        with fitz.open(output) as doc:
            page = doc[0]
            words = _marker_words(page)
            assert {w[0] for w in words} == {"1", "2", "#1"}
            assert all(w[2] == (1, 0) for w in words)  # upright to the viewer
            placements[rotation] = sorted((w[0], tuple(round(v) for v in w[1])) for w in words)
            assert _pixels(doc) == _pixels(fitz.open(tmp_path / "markers_r0.pdf"))
    assert all(p == placements[0] for p in placements.values())


# ---------------------------------------------------------------------------
# Report view and rule-specific wording
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("rotation", ROTATIONS)
def test_report_view_highlight_is_rotation_invariant(
    generic_variants: dict[int, Path], rotation: int
) -> None:
    path = generic_variants[rotation]
    x0, y0, x1, y1 = _object_boxes(path)["text_bottom"]
    payload = {
        "metadata": {"audit_type": "pdf"},
        "findings": [
            {
                "rule_id": "P012",
                "severity": "WARNING",
                "page": 1,
                "message": "Annotation detected.",
                "details": {
                    "issue_type": "pdf_annotation_detected",
                    "rect": f"{x0},{y0},{x1},{y1}",
                },
            }
        ],
    }
    view = build_report_view(payload, pdf_page_sizes=get_pdf_page_sizes(path))
    [finding] = [f for f in view.findings if f.rule_id == "P012"]
    assert finding.has_highlight
    assert finding.action_kind == "highlight"


@pytest.mark.parametrize("bbox_label", ["Left margin", "Top of page", ""])
def test_rule_specific_landscape_side_is_not_replaced_by_generic_label(bbox_label: str) -> None:
    details = {"side": "top_margin", "page_orientation": "landscape", "binding_edge": "top"}
    label = margin_location_label(details, 95, bbox_label=bbox_label)
    assert "top margin" in label.lower()
    if bbox_label:
        assert bbox_label not in label
