"""R035 under viewer-only ``/Rotate`` (synthetic PDFs only).

A viewer-only ``/Rotate`` turns already-upright content in the viewer; the
page's reading frame stays the unrotated box space. Under the rotation-frames
ADR such a page must get exactly the R035 verdict of the same page at
``/Rotate 0``: same tolerance (18 pt portrait, 50 pt landscape), same drift,
same boxes. Before the fix R035 read the *displayed* size and landscape flag,
so a quarter turn moved the text-area centre and swapped the tolerances.

Content-turned controls (the same pixels re-encoded so they read upright only
after ``/Rotate``) are checked alongside so the fix cannot regress them.
"""

from __future__ import annotations

import ast
from collections.abc import Callable
from pathlib import Path

import fitz
import pytest

import njit_auditor.rules.pdf_figure_table_layout as r035
from njit_auditor.pdf_highlight import (
    box_to_display_space,
    build_highlighted_pdf,
    display_page_size,
    get_pdf_page_sizes,
    sub_page_location_label,
)
from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.pdf_models import PdfReadingFrame
from njit_auditor.rules.pdf_figure_table_layout import check_pdf_figure_table_layout
from njit_auditor.student_pdf_report import build_combined_student_pdf_report

BODY = "Synthetic body sentence used only for rotation geometry testing of the auditor."
FIG_CAPTION = "Figure 7.1 A synthetic figure used for rotation semantics testing"
TAB_CAPTION = "Table 7.1 A synthetic ruled table used for rotation testing"
Builder = Callable[[fitz.Page, float], None]


def _pixmap() -> fitz.Pixmap:
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 16, 16), False)
    pix.clear_with(90)
    return pix


def _size(orient: str) -> tuple[float, float]:
    return (612.0, 792.0) if orient == "portrait" else (792.0, 612.0)


def _center(orient: str) -> float:
    return (108 + _size(orient)[0] - 72) / 2  # R035 text-area centre


def _centered(page: fitz.Page, text: str, y: float, cx: float) -> None:
    page.insert_text((cx - fitz.get_text_length(text, fontsize=12) / 2, y), text, fontsize=12)


def _page(doc: fitz.Document, orient: str, prose: bool = True) -> fitz.Page:
    width, height = _size(orient)
    page = doc.new_page(width=width, height=height)
    if orient == "portrait":
        page.insert_text((300, 750), "7", fontsize=12)
        if prose:
            for k in range(4):
                page.insert_text((108, 110 + 18 * k), BODY, fontsize=11)
            for k in range(6):
                page.insert_text((108, 640 + 16 * k), BODY, fontsize=11)
    else:
        page.insert_text((40, 300), "7", fontsize=12, rotate=270)  # portrait folio
        if prose:
            page.insert_text((108, 100), BODY, fontsize=11)
            page.insert_text((108, 560), BODY + " More prose here.", fontsize=11)
            page.insert_text((108, 576), BODY, fontsize=11)
    return page


def figure(orient: str, drift: float = 0.0, caption: str = "below", prose: bool = True):
    def build(doc: fitz.Document) -> None:
        page = _page(doc, orient, prose)
        center = _center(orient)
        cx = center + drift
        top = 300.0 if orient == "portrait" else 150.0
        width, height = (260, 200) if orient == "portrait" else (400, 250)
        if caption == "above":
            _centered(page, FIG_CAPTION, top - 10, center)
            top += 10
        page.insert_image(
            fitz.Rect(cx - width / 2, top, cx + width / 2, top + height), pixmap=_pixmap()
        )
        if caption == "below":
            _centered(page, FIG_CAPTION, top + height + 30, center)

    return build


def table(orient: str, drift: float = 0.0, caption: str = "above", style: str = "ruled"):
    def build(doc: fitz.Document) -> None:
        page = _page(doc, orient)
        center = _center(orient)
        top = 300.0 if orient == "portrait" else 150.0
        width = 360.0 if orient == "portrait" else 440.0
        x0 = center + drift - width / 2
        rows = ["Header alpha beta", "Row one alpha", "Row two beta", "Row three gamma"]
        if caption == "above":
            _centered(page, TAB_CAPTION, top - 10, center)
        else:
            top -= 20
        ys = [top, top + 25, top + 25 * len(rows) + 10]
        if style == "toprule":
            ys = [ys[0], ys[-1]]
        for y in ys:
            page.draw_line((x0, y), (x0 + width, y), color=(0, 0, 0), width=0.8)
        if style == "grid":
            for xv in (x0, x0 + width / 2, x0 + width):
                page.draw_line((xv, ys[0]), (xv, ys[-1]), color=(0, 0, 0), width=0.8)
        for k, row in enumerate(rows):
            while fitz.get_text_length(row + " 12.5", fontsize=11) < width - 24:
                row += " 12.5"
            page.insert_text((x0 + 8, top + 17 + k * 25 + (6 if k else 0)), row, fontsize=11)
        if caption == "below":
            _centered(page, TAB_CAPTION, ys[-1] + 28, center)

    return build


def _control(tmp_path: Path, build: Callable[[fitz.Document], None]) -> Path:
    """The page as authored, routed through an XObject like the variants."""
    src = fitz.open()
    build(src)
    flat = fitz.open()
    page = flat.new_page(width=src[0].rect.width, height=src[0].rect.height)
    page.show_pdf_page(page.rect, src, 0)
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / "control.pdf"
    flat.save(path)
    return path


def _viewer_only(control: Path, rotation: int) -> Path:
    doc = fitz.open(control)
    doc[0].set_rotation(rotation)
    path = control.with_name(f"viewer_r{rotation}.pdf")
    doc.save(path)
    return path


def _content_turned(control: Path, rotation: int) -> Path:
    """Pixel-identical re-encoding whose content reads upright only after /Rotate."""
    src = fitz.open(control)
    width, height = src[0].rect.width, src[0].rect.height
    if rotation % 180 == 90:
        width, height = height, width
    out = fitz.open()
    page = out.new_page(width=width, height=height)
    page.show_pdf_page(page.rect, src, 0, rotate=rotation)
    page.set_rotation(rotation)
    doc = fitz.open("pdf", out.tobytes())
    assert doc[0].get_pixmap(dpi=30).samples == src[0].get_pixmap(dpi=30).samples
    path = control.with_name(f"turned_r{rotation}.pdf")
    doc.save(path)
    return path


def _findings(path: Path) -> list[tuple[object, ...]]:
    """Each R035 finding with its drift, tolerance, severity and box-space boxes."""
    model = load_pdf_layout(str(path))
    return [
        (
            f.details["issue_type"],
            f.details.get("center_delta_points"),
            f.details["allowed_center_delta_points"],
            f.severity.value,
            f.details.get("bbox"),
            f.details.get("body_bbox"),
            f.details.get("caption_bbox"),
        )
        for f in check_pdf_figure_table_layout(model)
    ]


def _displayed_findings(path: Path) -> list[tuple[object, ...]]:
    """Each R035 finding as displayed, boxes on a 1 pt grid."""
    with fitz.open(path) as doc:
        matrix = doc[0].rotation_matrix

        def shown(raw: object) -> tuple[int, ...] | None:
            if not isinstance(raw, str):
                return None
            rect = fitz.Rect(*(float(v) for v in raw.split(","))) * matrix
            return tuple(round(v) for v in rect)

        return [(*f[:4], *(shown(raw) for raw in f[4:])) for f in _findings(path)]


FIGURE_THRESHOLDS = [
    # (orientation, drift, expected drift or None, tolerance)
    ("portrait", 0, None, "18"),
    ("portrait", 17, None, "18"),
    ("portrait", 19, "19.0", "18"),
    ("portrait", 62, "62.0", "18"),
    ("portrait", -62, "62.0", "18"),
    ("landscape", 0, None, "50"),
    ("landscape", 45, None, "50"),
    ("landscape", 51, "51.0", "50"),
    ("landscape", 62, "62.0", "50"),
    ("landscape", -62, "62.0", "50"),
]


@pytest.mark.parametrize("rotation", (0, 90, 270))
@pytest.mark.parametrize(("orient", "drift", "expected", "tolerance"), FIGURE_THRESHOLDS)
def test_viewer_only_figure_centering_matches_rotate_0(
    tmp_path: Path, orient: str, drift: float, expected: str | None, tolerance: str, rotation: int
) -> None:
    control = _control(tmp_path, figure(orient, drift))
    found = _findings(_viewer_only(control, rotation) if rotation else control)
    if expected is None:
        assert found == []
    else:
        assert [f[:4] for f in found] == [
            ("figure_body_not_centered", expected, tolerance, "WARNING")
        ]
    assert found == _findings(control)


@pytest.mark.parametrize(
    ("orient", "rotation", "tolerance"),
    [
        ("portrait", 90, 18.0),
        ("portrait", 270, 18.0),
        ("landscape", 90, 50.0),
        ("landscape", 270, 50.0),
    ],
)
def test_viewer_only_tolerance_follows_the_reading_frame(
    tmp_path: Path, orient: str, rotation: int, tolerance: float
) -> None:
    """The 18/50 pt choice comes from the reading frame, not the displayed sheet."""
    path = _viewer_only(_control(tmp_path, figure(orient, 0)), rotation)
    page = load_pdf_layout(str(path)).pages[0]
    assert page.is_visually_landscape is (orient == "portrait")  # display is sideways
    frame = PdfReadingFrame.for_page(page)
    assert frame.reading_rotation == 0 and frame.policy_orientation == orient
    body = r035.BBox(x0=200, y0=200, x1=300, y1=300)
    assert r035._centering_issue(frame, body)[2] == tolerance
    assert r035.CENTER_TOLERANCE_PT == 18.0
    assert r035.LANDSCAPE_CENTER_TOLERANCE_PT == 50.0


TABLES = {
    "centered_ruled": dict(drift=0),
    "off_center_ruled": dict(drift=62),
    "grid": dict(drift=62, style="grid"),
    "top_bottom_rules_only": dict(drift=62, style="toprule"),
    "centered_grid": dict(drift=0, style="grid"),
}


@pytest.mark.parametrize("rotation", (90, 270))
@pytest.mark.parametrize("orient", ("portrait", "landscape"))
@pytest.mark.parametrize("name", sorted(TABLES))
def test_viewer_only_table_matches_rotate_0(
    tmp_path: Path, name: str, orient: str, rotation: int
) -> None:
    control = _control(tmp_path, table(orient, **TABLES[name]))  # type: ignore[arg-type]
    variant = _viewer_only(control, rotation)
    expected = _findings(control)
    if TABLES[name]["drift"]:
        assert [f[:3] for f in expected] == [
            ("table_body_not_centered", "62.0", "18" if orient == "portrait" else "50")
        ]
    else:
        assert expected == []
    assert _findings(variant) == expected
    rules = [len(load_pdf_layout(str(p)).pages[0].horizontal_rules) for p in (control, variant)]
    assert rules[0] == rules[1] >= 2


CAPTIONS = {
    "figure_caption_below": figure("portrait", 0, caption="below"),
    "figure_caption_above": figure("portrait", 0, caption="above"),
    "table_caption_above": table("portrait", 0, caption="above"),
    "table_caption_below": table("portrait", 0, caption="below"),
    "landscape_figure_caption_above": figure("landscape", 0, caption="above"),
    "landscape_table_caption_below": table("landscape", 0, caption="below"),
}
CAPTION_EXPECTED = {
    "figure_caption_below": [],
    "figure_caption_above": ["figure_caption_not_below_body"],
    "table_caption_above": [],
    "table_caption_below": ["table_caption_not_above_body"],
    "landscape_figure_caption_above": ["figure_caption_not_below_body"],
    "landscape_table_caption_below": ["table_caption_not_above_body"],
}


@pytest.mark.parametrize("rotation", (90, 180, 270))
@pytest.mark.parametrize("name", sorted(CAPTIONS))
def test_viewer_only_caption_side_matches_rotate_0(
    tmp_path: Path, name: str, rotation: int
) -> None:
    control = _control(tmp_path, CAPTIONS[name])
    expected = _findings(control)
    assert [f[0] for f in expected] == CAPTION_EXPECTED[name]
    assert _findings(_viewer_only(control, rotation)) == expected


@pytest.mark.parametrize("orient", ("portrait", "landscape"))
@pytest.mark.parametrize("drift", (0, 19, 62))
def test_viewer_only_180_still_matches_rotate_0(tmp_path: Path, orient: str, drift: float) -> None:
    control = _control(tmp_path, figure(orient, drift))
    assert _findings(_viewer_only(control, 180)) == _findings(control)


CONTENT_TURNED = {
    "portrait_figure_62": figure("portrait", 62),
    "portrait_figure_17": figure("portrait", 17),
    "portrait_table_62": table("portrait", 62),
    "portrait_figure_caption_above": figure("portrait", 0, caption="above"),
    "landscape_figure_55": figure("landscape", 55),
    "landscape_table_caption_below": table("landscape", 0, caption="below"),
}


@pytest.mark.parametrize("rotation", (90, 180, 270))
@pytest.mark.parametrize("name", sorted(CONTENT_TURNED))
def test_content_turned_page_is_judged_as_displayed(
    tmp_path: Path, name: str, rotation: int
) -> None:
    control = _control(tmp_path, CONTENT_TURNED[name])
    assert _displayed_findings(_content_turned(control, rotation)) == _displayed_findings(control)


def test_b2_near_tie_fixture_keeps_current_behaviour(tmp_path: Path) -> None:
    """B2 (reading-frame confidence) is deferred: pin today's outcome, not a fix.

    Eight lines of sideways note text (320 chars) outweigh the landscape body
    (319 chars) on a viewer-only /Rotate 90 page, so the frame is inferred as
    90 and the 62 pt figure is missed. This test fails if the B1 fix changes
    that, which would mean B2 semantics changed without a decision.
    """

    def build(doc: fitz.Document) -> None:
        figure("landscape", 62)(doc)
        page = doc[0]
        for k in range(8):
            page.insert_text(
                (792 - 60 - 14 * k, 612 - 100),
                "A long sideways annotation block of text",
                fontsize=10,
                rotate=90,
            )

    control = _control(tmp_path, build)
    assert [f[:2] for f in _findings(control)] == [("figure_body_not_centered", "62.0")]
    variant = _viewer_only(control, 90)
    assert PdfReadingFrame.for_page(load_pdf_layout(str(variant)).pages[0]).reading_rotation == 90
    assert _findings(variant) == []


@pytest.mark.parametrize("rotation", (90, 270))
def test_viewer_only_finding_box_maps_to_box_space_and_highlights(
    tmp_path: Path, rotation: int
) -> None:
    control = _control(tmp_path, figure("portrait", 62))
    variant = _viewer_only(control, rotation)
    [expected] = check_pdf_figure_table_layout(load_pdf_layout(str(control)))
    [finding] = check_pdf_figure_table_layout(load_pdf_layout(str(variant)))
    assert finding.details == expected.details
    box = tuple(float(v) for v in finding.details["bbox"].split(","))
    with fitz.open(variant) as doc:
        image = doc[0].get_image_rects(doc[0].get_images()[0][0])[0]
    assert box == pytest.approx(tuple(image), abs=0.06)

    size = get_pdf_page_sizes(variant)[0]
    assert size == (612.0, 792.0) and getattr(size, "rotation", 0) == rotation
    label = sub_page_location_label(box, size)  # type: ignore[arg-type]
    shown = box_to_display_space(box, size)  # type: ignore[arg-type]
    assert label == sub_page_location_label(shown, display_page_size(size))

    out = variant.with_name("highlighted.pdf")
    assert build_highlighted_pdf(variant, out, {1: [box]}).drawn_count == 1  # type: ignore[list-item]
    combined = build_combined_student_pdf_report(
        variant,
        variant.with_name("combined.pdf"),
        [
            {
                "problem_number": 1,
                "page": 1,
                "rule_id": "P035",
                "public_rule_reference_id": "R035",
                "issue_type_label": "Figure centering",
                "polished_comment": "The figure may not be centered.",
                "suggested_fix": "Center the figure.",
                "location_label": label,
                "confidence_label": "Medium confidence",
            }
        ],
        boxes_by_problem={1: [box]},  # type: ignore[dict-item]
        file_name="thesis.pdf",
    )
    assert combined.highlight_boxes_drawn == 1 and combined.markers_drawn == 1


def test_r035_policy_geometry_never_reads_the_displayed_page() -> None:
    """Static guard: detector sizes and orientation come from PdfReadingFrame."""
    tree = ast.parse(Path(r035.__file__).read_text(encoding="utf-8"))
    leaks = [
        f"line {node.lineno}: {ast.unparse(node)}"
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and (
            node.attr in {"is_visually_landscape", "rect", "page_rotation"}
            or (
                node.attr in {"width", "height"}
                and isinstance(node.value, ast.Name)
                and node.value.id == "page"
            )
        )
    ]
    assert leaks == []
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == "njit_auditor.pdf_highlight"
        for alias in node.names
    }
    assert imported == set()
