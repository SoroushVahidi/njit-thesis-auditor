"""Synthetic equivalents of the November 5 historical-feedback counterexamples."""

from __future__ import annotations

from pathlib import Path

import pymupdf
import pytest
from test_pdf_rules import _make_regime_pdf
from test_r055_lof_segmentation import _doc, _line

from njit_auditor.pdf_layout import join_content_span_texts, load_pdf_layout
from njit_auditor.pdf_models import BBox, PdfTextSpan
from njit_auditor.rules.pdf_page_numbers import check_pdf_page_number_sequence
from njit_auditor.rules.pdf_roman_sequence import check_pdf_roman_sequence
from njit_auditor.rules.pdf_toc_list_formatting import check_pdf_toc_list_formatting


def _issues(findings):
    return [f.details.get("issue_type") for f in findings]


@pytest.mark.parametrize("first", ["1", "2", "100"])
def test_chapter_style_transition_is_independent_of_starting_value(tmp_path: Path, first: str):
    path = tmp_path / "transition.pdf"
    _make_regime_pdf(
        path,
        [
            ("TABLE OF CONTENTS", None, "v"),
            (None, "CHAPTER 1 INTRODUCTION", first),
            (None, None, "2"),
            (None, None, "3"),
        ],
    )
    issues = _issues(check_pdf_page_number_sequence(load_pdf_layout(str(path))))
    assert "mixed_numbering_style" not in issues
    if first != "1":
        assert "sequence_gap" in issues  # actual numeric defect still owned by P019


def test_reversion_to_roman_in_body_still_reports_mixed_style(tmp_path: Path):
    path = tmp_path / "mixed.pdf"
    _make_regime_pdf(
        path,
        [
            ("TABLE OF CONTENTS", None, "v"),
            (None, "CHAPTER 1 INTRODUCTION", "1"),
            (None, None, "ii"),
            (None, None, "3"),
        ],
    )
    assert "mixed_numbering_style" in _issues(
        check_pdf_page_number_sequence(load_pdf_layout(str(path)))
    )


@pytest.mark.parametrize("kind", ["outline", "image", "blank", "text"])
def test_unreadable_page_is_distinguished_from_missing_folio(tmp_path: Path, kind: str):
    path = tmp_path / "folio.pdf"
    with pymupdf.open() as pdf:
        for i, folio in enumerate(["v", None, "vii"]):
            p = pdf.new_page(width=612, height=792)
            if folio:
                p.insert_text((300, 770), folio)
            elif kind == "outline":
                # Visible vector strokes, no text layer: equivalent to outlined glyphs.
                p.draw_polyline([(300, 758), (303, 766), (306, 758)], color=(0, 0, 0))
                p.draw_line((309, 758), (309, 766), color=(0, 0, 0))
            elif kind == "image":
                image = pymupdf.Pixmap(pymupdf.csRGB, (0, 0, 120, 40), False)
                image.clear_with(200)
                p.insert_image(pymupdf.Rect(240, 720, 360, 760), pixmap=image)
            elif kind == "text":
                p.insert_text((108, 200), "Synthetic ordinary body text without a folio.")
        pdf.save(path)
    model = load_pdf_layout(str(path))
    assert model.pages[1].text_extraction_unavailable is (kind in {"outline", "image"})
    missing = "missing_page_number" in _issues(check_pdf_page_number_sequence(model))
    assert missing is (kind in {"blank", "text"})


@pytest.mark.parametrize(
    "last,issue",
    [
        ("vii", None),
        ("v", "roman_sequence_repeat"),
        ("iv", "roman_sequence_decrease"),
        ("viii", "roman_sequence_gap"),
    ],
)
def test_roman_sequence_accounts_for_intermediate_physical_page(tmp_path: Path, last, issue):
    path = tmp_path / "roman.pdf"
    _make_regime_pdf(
        path,
        [
            ("TABLE OF CONTENTS", None, "v"),
            (None, None, None),
            ("LIST OF FIGURES", None, last),
            (None, "CHAPTER 1 INTRODUCTION", "1"),
        ],
    )
    issues = _issues(check_pdf_roman_sequence(load_pdf_layout(str(path))))
    assert issues == ([] if issue is None else [issue])


def test_explicit_no_number_page_still_does_not_consume_visible_roman_step(tmp_path: Path):
    path = tmp_path / "exempt.pdf"
    _make_regime_pdf(
        path,
        [
            ("TABLE OF CONTENTS", None, "v"),
            ("APPROVAL PAGE", None, None),
            ("LIST OF FIGURES", None, "vi"),
            (None, "CHAPTER 1 INTRODUCTION", "1"),
        ],
    )
    assert check_pdf_roman_sequence(load_pdf_layout(str(path))) == []


@pytest.mark.parametrize("minor", ["of", "in", "and"])
@pytest.mark.parametrize("major", ["Impact", "impact"])
def test_font_metric_shift_does_not_glue_minor_word_to_small_cap_name(minor, major):
    row = _line(
        140,
        ("Table 2.1", 108, 160),
        (major, 165, 200),
        (minor, 205, 215),
        ("ExampleBrand", 220, 310),
        ("........", 450, 510),
        ("12", 528, 540),
    )
    for span in row.spans:
        span.baseline_y = 150
        span.size = 12
        span.font = "CMR12"
    smallcap = row.spans[3]
    smallcap.font = "CMCSC10"
    smallcap.bbox.y0 -= 2.6
    smallcap.bbox.y1 -= 2.6
    assert f"{minor} ExampleBrand" in join_content_span_texts(row.spans)
    findings = check_pdf_toc_list_formatting(
        _doc(
            [
                _line(80, ("LIST OF TABLES", 190, 350)),
                row,
                _line(170, ("Table 2.2 Another Correct Title .... 13", 108, 540)),
                _line(194, ("Table 2.3 Further Correct Title .... 14", 108, 540)),
            ]
        )
    )
    assert bool(findings) is (major == "impact")


def test_real_script_baseline_offset_does_not_gain_a_word_space():
    base = PdfTextSpan(text="X", size=12, baseline_y=110, bbox=BBox(x0=100, y0=100, x1=110, y1=112))
    sub = PdfTextSpan(
        text="index", size=8, baseline_y=115, bbox=BBox(x0=113, y0=105, x1=130, y1=113)
    )
    assert join_content_span_texts([base, sub]) == "Xindex"
