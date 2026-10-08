"""P013/P019 page-number positions on ``/Rotate 180`` pages (synthetic PDFs only).

Rotation-frames ADR (``docs/architecture/pdf_rotation_frames_adr.md``): a
folio's position describes where it sits on the authored sheet as it is read.

* A *content-turned* 180 page (an upright page stored upside down, then
  ``/Rotate 180``; reading frame 180) displays exactly like its ``/Rotate 0``
  control, so every candidate and every P013/P019/P028/P029/P037 verdict
  must match the control: its displayed-bottom folio is ``bottom_center``.
* A *viewer-only* 180 page (same content stream, ``/Rotate 180`` set on top;
  reading frame 0) keeps the ``/Rotate 0`` classification.
* Candidate boxes stay in box space either way.
"""

from __future__ import annotations

import ast
from collections.abc import Callable
from pathlib import Path

import fitz
import pytest

import njit_auditor.rules.pdf_page_numbers as page_numbers
from njit_auditor.pdf_highlight import build_highlighted_pdf
from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.pdf_models import PdfReadingFrame
from njit_auditor.rules.pdf_page_numbering_regime import check_pdf_page_numbering_regime
from njit_auditor.rules.pdf_page_numbers import (
    check_pdf_page_number_sequence,
    detect_page_number_candidates,
    run_pdf_page_number_candidates_rule,
)
from njit_auditor.rules.pdf_roman_section_anchors import check_pdf_roman_section_anchors
from njit_auditor.rules.pdf_roman_sequence import check_pdf_roman_sequence
from njit_auditor.student_pdf_report import build_combined_student_pdf_report

BODY = "Synthetic body sentence used only for page number geometry testing"
TARGET = 4  # 1-based page that gets re-encoded
FS = 12
BOX_KEYS = {"bbox", "document_page_label_bbox", "highlight_bboxes"}

Design = Callable[[fitz.Document, int], None]


def _width(text: str) -> float:
    return fitz.get_text_length(text, fontsize=FS)


def _portrait(
    doc: fitz.Document,
    folio: str | None,
    where: str = "bottom_center",
    extra: tuple[tuple[float, float, str], ...] = (),
) -> None:
    page = doc.new_page(width=612, height=792)
    for k in range(20):
        page.insert_text((108, 110 + 26 * k), BODY, fontsize=FS)
    for x, y, text in extra:
        page.insert_text((x, y), text, fontsize=FS)
    if folio is None:
        return
    x = 306 - _width(folio) / 2 if where.endswith("center") else 540 - _width(folio)
    y = 60 if where.startswith("top") else 750
    page.insert_text((x, y), folio, fontsize=FS)


def _landscape_cw(doc: fitz.Document, folio: str) -> None:
    page = doc.new_page(width=792, height=612)
    for k in range(14):
        page.insert_text((90, 130 + 26 * k), BODY + " wide table row", fontsize=FS)
    page.insert_text((40, 306 - _width(folio) / 2), folio, fontsize=FS, rotate=270)


def _on_target(target: Callable[[fitz.Document], None]) -> Design:
    def design(doc: fitz.Document, number: int) -> None:
        if number == TARGET:
            target(doc)
        else:
            _portrait(doc, str(number))

    return design


ROMAN = ["i", "ii", "iii", "iv", "v", "vi", "vii"]
DESIGNS: dict[str, Design] = {
    "valid_bottom_center": lambda doc, n: _portrait(doc, str(n)),
    "valid_bottom_right": lambda doc, n: _portrait(
        doc, str(n), "bottom_right" if n == TARGET else "bottom_center"
    ),
    "semantic_top_center": lambda doc, n: _portrait(
        doc, str(n), "top_center" if n == TARGET else "bottom_center"
    ),
    "missing": lambda doc, n: _portrait(doc, None if n == TARGET else str(n)),
    "wrong_value": lambda doc, n: _portrait(doc, "9" if n == TARGET else str(n)),
    "duplicate_number": lambda doc, n: _portrait(
        doc, str(n), extra=((306 - _width("4") / 2, 60, "4"),) if n == TARGET else ()
    ),
    "body_number_negative": lambda doc, n: _portrait(
        doc, str(n), extra=((300, 400, "17"),) if n == TARGET else ()
    ),
    "decimal_negative": lambda doc, n: _portrait(
        doc, str(n), extra=((306 - _width("4.2") / 2, 60, "4.2"),) if n == TARGET else ()
    ),
    "roman_front_matter": lambda doc, n: _portrait(doc, ROMAN[n - 1]),
    "intrinsic_landscape_cw": _on_target(lambda doc: _landscape_cw(doc, "4")),
}


def _control(design: Design) -> fitz.Document:
    src = fitz.open()
    for number in range(1, 8):
        design(src, number)
    return fitz.open("pdf", src.tobytes())


def _content_turned(control: fitz.Document, pages: set[int]) -> fitz.Document:
    """Store *pages* (0-based) upside down and display them upright with /Rotate 180."""
    out = fitz.open()
    for index, src_page in enumerate(control):
        if index not in pages:
            out.insert_pdf(control, from_page=index, to_page=index)
            continue
        page = out.new_page(width=src_page.rect.width, height=src_page.rect.height)
        page.show_pdf_page(page.rect, control, index, rotate=180)
        page.set_rotation(180)
    return out


def _viewer_only(control: fitz.Document, pages: set[int]) -> fitz.Document:
    out = fitz.open("pdf", control.tobytes())
    for index in pages:
        out[index].set_rotation(180)
    return out


def _same_pixels(a: fitz.Document, b: fitz.Document) -> bool:
    return all(
        x.get_pixmap(dpi=30).samples == y.get_pixmap(dpi=30).samples
        for x, y in zip(a, b, strict=True)
    )


def _save(doc: fitz.Document, tmp_path: Path, name: str) -> Path:
    path = tmp_path / f"{name}.pdf"
    doc.save(path)
    return path


def _pair(
    tmp_path: Path, name: str, *, family: str = "turned", pages: set[int] | None = None
) -> tuple[Path, Path]:
    control = _control(DESIGNS[name])
    pages = {TARGET - 1} if pages is None else pages
    variant = (_content_turned if family == "turned" else _viewer_only)(control, pages)
    if family == "turned":
        assert _same_pixels(control, variant)
    return _save(control, tmp_path, f"{name}_control"), _save(variant, tmp_path, f"{name}_{family}")


def _candidates(path: Path) -> list[tuple[int, str, str, str, int | None]]:
    model = load_pdf_layout(str(path))
    return sorted(
        (c.page_number, c.text, c.position_type, c.location, c.value)
        for c in detect_page_number_candidates(model)
    )


def _semantics(path: Path) -> list[tuple[str, int, str, str, tuple[tuple[str, str], ...]]]:
    """Every page-number-family finding, without its (box-space) boxes."""
    model = load_pdf_layout(str(path))
    findings = [
        *run_pdf_page_number_candidates_rule(model),
        *check_pdf_page_number_sequence(model),
        *check_pdf_roman_sequence(model),
        *check_pdf_roman_section_anchors(model),
        *check_pdf_page_numbering_regime(model),
    ]
    return sorted(
        (
            f.rule_id,
            f.page or 0,
            f.severity.value,
            f.message,
            tuple(sorted((k, str(v)) for k, v in f.details.items() if k not in BOX_KEYS)),
        )
        for f in findings
    )


def _p019(path: Path) -> list[tuple[int | None, str]]:
    model = load_pdf_layout(str(path))
    return [(f.page, f.details["issue_type"]) for f in check_pdf_page_number_sequence(model)]


def _target_candidates(path: Path) -> list[tuple[str, str, str]]:
    return [(text, pos, loc) for page, text, pos, loc, _ in _candidates(path) if page == TARGET]


# --- content-turned 180 --------------------------------------------------------------------


def test_content_turned_180_folio_is_classified_as_displayed(tmp_path: Path) -> None:
    """Replaces the interim ``test_rotate_180_page_is_classified_in_text_space``.

    The upside-down-stored folio sits at the top of box space, but the page
    reads upright at /Rotate 180, so the folio is the displayed bottom-centre
    page number (ADR family table: "180: displayed bottom = bottom_center").
    """
    control, turned = _pair(tmp_path, "valid_bottom_center")
    page = load_pdf_layout(str(turned)).pages[TARGET - 1]
    assert page.page_rotation == 180
    assert PdfReadingFrame.for_page(page).reading_rotation == 180
    assert _target_candidates(turned) == [("4", "bottom_center", "bottom")]
    assert _p019(turned) == []
    assert _candidates(turned) == _candidates(control)


@pytest.mark.parametrize("name", sorted(DESIGNS))
@pytest.mark.parametrize("scope", ["target_page", "whole_document"])
def test_content_turned_180_matches_the_rotate_0_control(
    tmp_path: Path, name: str, scope: str
) -> None:
    """Candidates and every P013/P019/P028-regime/P029/P037 verdict agree."""
    pages = {TARGET - 1} if scope == "target_page" else set(range(7))
    control, turned = _pair(tmp_path, name, pages=pages)
    assert _candidates(turned) == _candidates(control)
    assert _semantics(turned) == _semantics(control)


def test_content_turned_180_top_folio_stays_top_center(tmp_path: Path) -> None:
    """Contrast: a folio at the displayed top is not rewritten to bottom_center."""
    control, turned = _pair(tmp_path, "semantic_top_center")
    assert _target_candidates(control) == [("4", "top_center", "top")]
    assert _target_candidates(turned) == [("4", "top_center", "top")]


def test_content_turned_180_bottom_right_folio_is_not_a_missing_page_number(
    tmp_path: Path,
) -> None:
    # Classified in box space this folio sat top-left ("other") and P019
    # reported a false missing_page_number.
    control, turned = _pair(tmp_path, "valid_bottom_right")
    assert _target_candidates(turned) == [("4", "bottom_right", "bottom")]
    assert _p019(turned) == _p019(control)
    assert (TARGET, "missing_page_number") not in _p019(turned)


def test_content_turned_180_missing_folio_is_still_reported(tmp_path: Path) -> None:
    _, turned = _pair(tmp_path, "missing")
    assert _target_candidates(turned) == []
    assert _p019(turned) == [(TARGET, "missing_page_number")]


def test_content_turned_180_wrong_value_is_a_sequence_gap(tmp_path: Path) -> None:
    control, turned = _pair(tmp_path, "wrong_value")
    assert _target_candidates(turned) == [("9", "bottom_center", "bottom")]
    issues = {issue for _, issue in _p019(turned)}
    assert "sequence_gap" in issues and "missing_page_number" not in issues
    assert _p019(turned) == _p019(control)


def test_content_turned_180_has_no_duplicate_or_body_candidates(tmp_path: Path) -> None:
    for name in ("valid_bottom_center", "body_number_negative", "decimal_negative"):
        _, turned = _pair(tmp_path, name)
        assert [c for c in _target_candidates(turned) if c[1] != "other"] == [
            ("4", "bottom_center", "bottom")
        ], name


def test_content_turned_180_landscape_keeps_its_edge_position(tmp_path: Path) -> None:
    control, turned = _pair(tmp_path, "intrinsic_landscape_cw")
    assert _target_candidates(control) == _target_candidates(turned) == [
        ("4", "left_center", "left")
    ]


# --- box space, CropBox, presentation -------------------------------------------------------


def _folio_line_box(path: Path, text: str) -> tuple[float, float, float, float]:
    with fitz.open(path) as doc:
        for block in doc[TARGET - 1].get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                if "".join(span["text"] for span in line["spans"]).strip() == text:
                    return tuple(line["bbox"])  # type: ignore[return-value]
    raise AssertionError(text)


@pytest.mark.parametrize("cropbox", [False, True])
def test_content_turned_180_candidate_box_stays_in_box_space(
    tmp_path: Path, cropbox: bool
) -> None:
    _, turned = _pair(tmp_path, "valid_bottom_center")
    if cropbox:
        doc = fitz.open(turned)
        page = doc[TARGET - 1]
        page.set_cropbox(fitz.Rect(4, 6, page.mediabox.width - 5, page.mediabox.height - 3))
        turned = turned.with_name("cropped.pdf")
        doc.save(turned)
    model = load_pdf_layout(str(turned))
    [candidate] = [c for c in detect_page_number_candidates(model) if c.page_number == TARGET]
    assert candidate.position_type == "bottom_center"
    assert candidate.bbox == pytest.approx(_folio_line_box(turned, "4"), abs=0.06)
    # Stored at the top of box space; the same box is the bottom of the reading frame.
    assert candidate.bbox is not None and candidate.bbox[1] < 100


def test_content_turned_180_folio_highlight_renders_like_the_control(tmp_path: Path) -> None:
    control, turned = _pair(tmp_path, "valid_bottom_center")
    renders = {}
    for label, path in (("control", control), ("turned", turned)):
        model = load_pdf_layout(str(path))
        [candidate] = [
            c for c in detect_page_number_candidates(model) if c.page_number == TARGET
        ]
        assert candidate.bbox is not None
        out = path.with_name(f"{label}_hl.pdf")
        result = build_highlighted_pdf(path, out, {TARGET: [candidate.bbox]})  # type: ignore[list-item]
        assert result.drawn_count == 1
        with fitz.open(out) as doc:
            pix = doc[TARGET - 1].get_pixmap(dpi=72)
            renders[label] = (pix.width, pix.height, pix.samples)
        combined = build_combined_student_pdf_report(
            path,
            path.with_name(f"{label}_combined.pdf"),
            [
                {
                    "problem_number": 1,
                    "page": TARGET,
                    "rule_id": "P019",
                    "public_rule_reference_id": "R019",
                    "issue_type_label": "Page number",
                    "polished_comment": "Check this page number.",
                    "suggested_fix": "Check the page number.",
                    "location_label": "Bottom of page",
                    "confidence_label": "High confidence",
                }
            ],
            boxes_by_problem={1: [candidate.bbox]},  # type: ignore[dict-item]
            file_name="thesis.pdf",
        )
        assert combined.highlight_boxes_drawn == 1 and combined.markers_drawn == 1
    assert renders["turned"] == renders["control"]


# --- viewer-only 180 ------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    [
        "valid_bottom_center",
        "missing",
        "wrong_value",
        "duplicate_number",
        "body_number_negative",
        "semantic_top_center",
    ],
)
def test_viewer_only_180_keeps_the_rotate_0_classification(tmp_path: Path, name: str) -> None:
    control, viewer = _pair(tmp_path, name, family="viewer")
    page = load_pdf_layout(str(viewer)).pages[TARGET - 1]
    assert page.page_rotation == 180
    assert PdfReadingFrame.for_page(page).reading_rotation == 0
    assert _candidates(viewer) == _candidates(control)
    assert _semantics(viewer) == _semantics(control)
    model_c, model_v = load_pdf_layout(str(control)), load_pdf_layout(str(viewer))
    assert [c.bbox for c in detect_page_number_candidates(model_v)] == [
        c.bbox for c in detect_page_number_candidates(model_c)
    ]


# --- B2 freeze ------------------------------------------------------------------------------


def test_b2_upside_down_majority_is_a_known_deferred_limitation(tmp_path: Path) -> None:
    """B2 (reading-frame confidence) is deferred; the inference is unchanged.

    Upside-down notes that outweigh the upright body on a viewer-only
    /Rotate 180 page make the character-weighted inference choose frame 180,
    so the folio is classified on that flipped sheet. Pinned so a B2 fix
    (confidence/abstention) changes it deliberately.
    """

    def design(doc: fitz.Document, number: int) -> None:
        if number != TARGET:
            _portrait(doc, str(number))
            return
        page = doc.new_page(width=612, height=792)
        for k in range(3):
            page.insert_text((108, 110 + 26 * k), BODY, fontsize=FS)
        for k in range(5):
            page.insert_text((500, 400 + 26 * k), BODY, fontsize=FS, rotate=180)
        page.insert_text((306 - _width("4") / 2, 750), "4", fontsize=FS)

    control = _control(design)
    viewer = _viewer_only(control, {TARGET - 1})
    control_path = _save(control, tmp_path, "b2_control")
    viewer_path = _save(viewer, tmp_path, "b2_viewer")
    frame = PdfReadingFrame.for_page(load_pdf_layout(str(viewer_path)).pages[TARGET - 1])
    assert frame.reading_rotation == 180
    assert _target_candidates(control_path) == [("4", "bottom_center", "bottom")]
    assert _target_candidates(viewer_path) == [("4", "top_center", "top")]


# --- static guard ---------------------------------------------------------------------------


def test_half_turn_is_decided_by_the_reading_frame_not_the_rotate_value() -> None:
    """The only comparison with 180 is against the inferred reading rotation."""
    tree = ast.parse(Path(page_numbers.__file__).read_text(encoding="utf-8"))
    compares_with_180 = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Compare)
        and any(
            isinstance(side, ast.Constant) and side.value == 180
            for side in [node.left, *node.comparators]
        )
    ]
    assert compares_with_180
    for node in compares_with_180:
        assert isinstance(node.left, ast.Attribute) and node.left.attr == "reading_rotation"
    assert "page.rotation" not in Path(page_numbers.__file__).read_text(encoding="utf-8")
