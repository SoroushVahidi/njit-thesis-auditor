"""Ester-aligned P015 body indentation split tests."""

from __future__ import annotations

import importlib
import os
from pathlib import Path

import fitz
import pytest
from fastapi.testclient import TestClient

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
from njit_auditor.rules.pdf_indentation import _effective_row_start_x, check_pdf_indentation

_REPO_ROOT = Path(__file__).resolve().parents[1]
_BODY_TEXT = "Lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod."


def _span(
    text: str,
    *,
    bold: bool = False,
    italic: bool = False,
    font: str | None = None,
    x0: float = 108.0,
    x1: float = 504.0,
    y0: float = 50.0,
    y1: float = 62.0,
) -> PdfTextSpan:
    return PdfTextSpan(
        text=text,
        font=font or ("TimesNewRomanPSMT-Bold" if bold else "TimesNewRomanPSMT"),
        size=12.0,
        bold=bold,
        italic=italic,
        bbox=BBox(x0=x0, y0=y0, x1=x1, y1=y1),
    )


def _line(
    text: str,
    *,
    x0: float = 108.0,
    x1: float = 504.0,
    y0: float = 50.0,
    y1: float = 62.0,
    bold: bool = False,
    italic: bool = False,
    font: str | None = None,
) -> PdfTextLine:
    sp = _span(text, bold=bold, italic=italic, font=font, x0=x0, x1=x1, y0=y0, y1=y1)
    return PdfTextLine(
        text=text,
        bbox=BBox(x0=x0, y0=y0, x1=x1, y1=y1),
        spans=[sp],
    )


def _block(*lines: PdfTextLine) -> PdfTextBlock:
    return PdfTextBlock(
        bbox=BBox(
            x0=min(ln.bbox.x0 for ln in lines),
            y0=min(ln.bbox.y0 for ln in lines),
            x1=max(ln.bbox.x1 for ln in lines),
            y1=max(ln.bbox.y1 for ln in lines),
        ),
        lines=list(lines),
        text=" ".join(ln.text for ln in lines),
    )


def _page(page_number: int, *blocks: PdfTextBlock) -> PdfPage:
    return PdfPage(page_number=page_number, width=612.0, height=792.0, text_blocks=list(blocks))


def _doc(*pages: PdfPage) -> PdfDocument:
    return PdfDocument(path="synthetic", pages=list(pages))


def _body_line(y0: float, *, indent: bool, left_margin: float = 108.0) -> PdfTextLine:
    x0 = left_margin + (36.0 if indent else 0.0)
    return _line(_BODY_TEXT, x0=x0, x1=504.0, y0=y0, y1=y0 + 12.0)


def _draw_paragraph(
    page: fitz.Page,
    *,
    first_x: float,
    rest_x: float,
    y: float,
    lines: int = 4,
) -> None:
    page.insert_text((first_x, y), "Synthetic paragraph line for indentation checks here.")
    for idx in range(1, lines):
        page.insert_text(
            (rest_x, y + (idx * 14)),
            "Continuation synthetic paragraph line text for indentation checks.",
        )


@pytest.mark.parametrize(
    ("inner_divider", "outside_paragraph", "cell_baseline", "expected_baseline"),
    [(True, False, 368, None), (False, False, 368, 368),
     (True, True, 368, 538), (True, False, 409, 409)],
)
def test_p015_excludes_only_verified_table_rows(
    tmp_path: Path, inner_divider: bool, outside_paragraph: bool,
    cell_baseline: int, expected_baseline: int | None,
) -> None:
    path = tmp_path / "table-and-body.pdf"
    with fitz.open() as pdf:
        pdf.new_page(width=612, height=792)
        page = pdf.new_page(width=612, height=792)
        for y in (65, 135, 205):
            _draw_paragraph(page, first_x=144, rest_x=108, y=y)
        page.insert_text((108, 300), "Table 4.1 Configuration Descriptions")
        for x in (105, 510):
            page.draw_line((x, 320), (x, 448))
        if inner_divider:
            page.draw_line((434, 320), (434, 448))
        for y in (320, 350, 448):
            page.draw_line((105, y), (510, y))
        page.insert_text((110, 339), "Parameter")
        page.insert_text((447, 339), "Result")
        _draw_paragraph(page, first_x=108, rest_x=108, y=cell_baseline)
        if outside_paragraph:
            _draw_paragraph(page, first_x=108, rest_x=108, y=538)
        pdf.save(path)

    document = load_pdf_layout(str(path))
    source_lines = [line for block in document.pages[1].text_blocks for line in block.lines]
    findings = check_pdf_indentation(document)
    assert [line for block in document.pages[1].text_blocks for line in block.lines] == source_lines
    if expected_baseline is None:
        assert findings == []
        return
    target, = [line for line in source_lines if line.baseline_y == expected_baseline]
    finding, = findings
    assert finding.rule_id == "P015" and finding.page == 2
    assert finding.details["issue_type"] == "missing_later_indent"
    assert finding.details["bbox"] == format_bbox_detail(target.bbox)
    assert "body paragraph" in finding.details["suggested_fix"]


@pytest.fixture()
def web_client(tmp_path: Path) -> tuple[TestClient, object]:
    os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"] = str(tmp_path / "web_audits")
    import njit_auditor.web_app as wa

    importlib.reload(wa)
    return TestClient(wa.app, raise_server_exceptions=False), wa


def test_rules_page_hides_broad_p015_and_shows_atomic_cards(web_client) -> None:
    client, _ = web_client
    resp = client.get("/rules")
    body = resp.text
    assert resp.status_code == 200
    assert 'data-rule-id="P015A"' in body
    assert 'data-rule-id="P015B"' in body
    assert 'data-rule-id="P015"' not in body
    assert "front-matter/body" not in body.lower()


def test_p015_atomic_public_cards_have_ester_body_wording(web_client) -> None:
    _, wa = web_client
    catalog = wa._build_rule_catalog()
    by_id = {rule["id"]: rule for rule in catalog["student_rules"]}

    p015a = by_id["P015A"]
    p015b = by_id["P015B"]

    assert "first paragraph after" in p015a["title"].lower()
    assert "not indented" in p015a["title"].lower()
    assert "remove the first-line indent" in p015a["how_to_correct"].lower()
    assert "abstract" not in p015a["title"].lower()
    assert "acknowledgement" not in p015a["title"].lower()

    assert "body paragraphs indented" in p015b["title"].lower()
    assert "first paragraph after" in p015b["title"].lower()
    assert "apply a first-line indent" in p015b["how_to_correct"].lower()
    assert "abstract" not in p015b["title"].lower()
    assert "acknowledgement" not in p015b["title"].lower()


def test_public_mapping_splits_p015_issue_types(web_client) -> None:
    _, wa = web_client
    assert wa._public_rule_reference_id("P015", issue_type="unexpected_opening_indent") == "P015A"
    assert wa._public_rule_reference_id("P015", issue_type="missing_later_indent") == "P015B"


def test_p015b_flags_missing_later_indent_on_body_page() -> None:
    para1 = [_body_line(80.0 + i * 14.0, indent=(i == 0)) for i in range(4)]
    para2 = [_body_line(150.0 + i * 14.0, indent=(i == 0)) for i in range(4)]
    para3 = [_body_line(220.0 + i * 14.0, indent=False) for i in range(4)]
    doc = _doc(_page(10, _block(*para1), _block(*para2), _block(*para3)))
    findings = [f for f in check_pdf_indentation(doc) if f.rule_id == "P015"]
    assert any(f.details.get("issue_type") == "missing_later_indent" for f in findings)


def test_p015a_flags_indented_first_paragraph_after_section_heading(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p015a_section_heading_indented_opening.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    _draw_paragraph(page, first_x=190, rest_x=108, y=140)
    _draw_paragraph(page, first_x=190, rest_x=108, y=210)
    page.insert_text((108, 290), "2.4 Perceived Barriers and Challenges in Research")
    _draw_paragraph(page, first_x=190, rest_x=108, y=340, lines=4)
    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))
    findings = [f for f in check_pdf_indentation(model) if f.rule_id == "P015"]
    assert any(f.details.get("issue_type") == "unexpected_opening_indent" for f in findings)


def test_p015a_not_flagged_for_flush_left_opening_after_heading(tmp_path: Path) -> None:
    pdf_path = tmp_path / "p015a_flush_opening_after_heading.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    _draw_paragraph(page, first_x=190, rest_x=108, y=140)
    _draw_paragraph(page, first_x=190, rest_x=108, y=210)
    page.insert_text((108, 290), "2.4 Perceived Barriers and Challenges in Research")
    _draw_paragraph(page, first_x=108, rest_x=108, y=340, lines=4)
    doc.save(pdf_path)
    doc.close()

    model = load_pdf_layout(str(pdf_path))
    findings = [
        f
        for f in check_pdf_indentation(model)
        if f.rule_id == "P015" and f.details.get("issue_type") == "unexpected_opening_indent"
    ]
    assert not findings


def test_p015_flags_unexpected_indent_on_equation_continuation_line() -> None:
    """A "where ..."-style clause continuing the sentence before a displayed

    equation should stay flush-left; a paragraph-style indent on it is a
    defect distinct from both P015A (opening indent) and P015B (missing
    later indent).
    """
    opening_para = [
        _line(
            "Prior sentence establishing a displayed equation context here.",
            x0=144.0,
            y0=80.0,
            y1=92.0,
        ),
        _line(
            "Continuation synthetic paragraph line text for indentation checks.",
            x0=108.0,
            y0=94.0,
            y1=106.0,
        ),
        _line(
            "Continuation synthetic paragraph line text for indentation checks.",
            x0=108.0,
            y0=108.0,
            y1=120.0,
        ),
    ]
    para = [
        _line(
            "where q denotes the closest point on the surface in this test.",
            x0=144.0,
            y0=170.0,
            y1=182.0,
        ),
        _line(
            "Lorem ipsum dolor sit amet consectetur adipiscing elit sed do.",
            x0=108.0,
            y0=184.0,
            y1=196.0,
        ),
        _line(
            "Lorem ipsum dolor sit amet consectetur adipiscing elit sed do.",
            x0=108.0,
            y0=198.0,
            y1=210.0,
        ),
    ]
    doc = _doc(_page(20, _block(*opening_para), _block(*para)))
    findings = [
        f
        for f in check_pdf_indentation(doc)
        if f.rule_id == "P015"
        and f.details.get("issue_type") == "unexpected_indent_on_continuation_line"
    ]
    assert len(findings) == 1


def test_p015_does_not_flag_bracketed_citation_led_paragraph_as_continuation() -> None:
    """A genuine new sentence like "[12] explored ..." starts with a lowercase

    letter right after its citation marker but is not a continuation clause,
    so an indent on it must not trip the continuation-indent check.
    """
    para = [
        _line(
            "[12] explored alternative implicit fields for shape work.", x0=144.0, y0=80.0, y1=92.0
        ),
        _line(
            "Lorem ipsum dolor sit amet consectetur adipiscing elit sed do.",
            x0=108.0,
            y0=94.0,
            y1=106.0,
        ),
        _line(
            "Lorem ipsum dolor sit amet consectetur adipiscing elit sed do.",
            x0=108.0,
            y0=108.0,
            y1=120.0,
        ),
    ]
    doc = _doc(_page(20, _block(*para)))
    findings = [
        f
        for f in check_pdf_indentation(doc)
        if f.rule_id == "P015"
        and f.details.get("issue_type") == "unexpected_indent_on_continuation_line"
    ]
    assert not findings


def test_p015_does_not_flag_paren_list_marker_led_paragraph_as_continuation() -> None:
    """A genuine new list/item sentence like '(a) represents ...' must not be
    treated as a lowercase continuation clause merely because the first letter
    inside the parentheses is lowercase.
    """
    para = [
        _line(
            "(a) represents the first measured quantity for this fixture case.",
            x0=144.0,
            y0=80.0,
            y1=92.0,
        ),
        _line(
            "Lorem ipsum dolor sit amet consectetur adipiscing elit sed do.",
            x0=108.0,
            y0=94.0,
            y1=106.0,
        ),
        _line(
            "Lorem ipsum dolor sit amet consectetur adipiscing elit sed do.",
            x0=108.0,
            y0=108.0,
            y1=120.0,
        ),
    ]
    doc = _doc(_page(20, _block(*para)))
    findings = [
        f
        for f in check_pdf_indentation(doc)
        if f.rule_id == "P015"
        and f.details.get("issue_type") == "unexpected_indent_on_continuation_line"
    ]
    assert not findings


def test_p015_does_not_flag_flush_left_continuation_line() -> None:
    """A correctly unindented continuation line is not a defect."""
    para = [
        _line(
            "where q denotes the closest point on the surface in this test.",
            x0=108.0,
            y0=80.0,
            y1=92.0,
        ),
        _line(
            "Lorem ipsum dolor sit amet consectetur adipiscing elit sed do.",
            x0=108.0,
            y0=94.0,
            y1=106.0,
        ),
        _line(
            "Lorem ipsum dolor sit amet consectetur adipiscing elit sed do.",
            x0=108.0,
            y0=108.0,
            y1=120.0,
        ),
    ]
    doc = _doc(_page(20, _block(*para)))
    findings = [
        f
        for f in check_pdf_indentation(doc)
        if f.rule_id == "P015"
        and f.details.get("issue_type") == "unexpected_indent_on_continuation_line"
    ]
    assert not findings


@pytest.mark.parametrize(
    "fragment_x0, fragment_x1, font, bold",
    [
        (108.0, 120.0, "Symbol", False),
        (120.0, 140.0, "Symbol", False),
        (108.0, 140.0, None, True),
    ],
)
def test_p015_still_flags_indent_beside_unrelated_short_margin_fragment(
    fragment_x0: float, fragment_x1: float, font: str | None, bold: bool
) -> None:
    """A discarded label, including one touching the prose, is not its prefix."""
    opening = [
        _line(_BODY_TEXT, x0=144.0, y0=80.0, y1=92.0),
        _line(_BODY_TEXT, x0=108.0, y0=94.0, y1=106.0),
        _line(_BODY_TEXT, x0=108.0, y0=108.0, y1=120.0),
    ]
    continuation = [
        _line(
            "where q denotes the closest point on the surface in this test.",
            x0=144.0,
            y0=170.0,
            y1=182.0,
        ),
        _line(_BODY_TEXT, x0=108.0, y0=184.0, y1=196.0),
        _line(_BODY_TEXT, x0=108.0, y0=198.0, y1=210.0),
    ]
    margin_fragment = _line(
        "Eq.", x0=fragment_x0, x1=fragment_x1, y0=170.0, y1=182.0, font=font, bold=bold
    )
    doc = _doc(_page(20, _block(*opening), _block(margin_fragment), _block(*continuation)))
    findings = check_pdf_indentation(doc)
    assert any(
        finding.details.get("issue_type") == "unexpected_indent_on_continuation_line"
        for finding in findings
    )


def test_p015_close_disconnected_fragment_cannot_rejoin_paragraph() -> None:
    """Row correction during grouping must not hide a nearby real indent."""
    opening = [
        _line(_BODY_TEXT, x0=144.0, y0=80.0, y1=92.0),
        _line(_BODY_TEXT, x0=108.0, y0=94.0, y1=106.0),
        _line("The formula describes the quantity,", x0=108.0, y0=108.0, y1=120.0),
    ]
    label = _line("Eq.", x0=108.0, x1=140.0, y0=128.0, y1=140.0)
    continuation = [
        _line(
            "where q denotes the closest point on the surface in this test.",
            x0=144.0,
            y0=128.0,
            y1=140.0,
        ),
        _line(_BODY_TEXT, x0=108.0, y0=142.0, y1=154.0),
        _line(_BODY_TEXT, x0=108.0, y0=156.0, y1=168.0),
    ]
    doc = _doc(_page(20, _block(*opening), _block(label), _block(*continuation)))
    assert any(
        f.details.get("issue_type") == "unexpected_indent_on_continuation_line"
        for f in check_pdf_indentation(doc)
    )


@pytest.mark.parametrize(
    "fragment, fragment_x0, fragment_x1, font",
    [
        ("and", 108.0, 120.0, None),  # 24-point gap, same font
        ("where", 108.0, 131.0, None),  # just beyond the 12-point limit
        ("and", 50.0, 120.0, None),  # distant left edge and gap
        ("and", 125.0, 140.0, None),  # close edge, wrong body margin
        ("where", 108.0, 140.0, "CourierNew"),  # near, but different font
    ],
)
def test_p015_disconnected_lowercase_fragment_cannot_rejoin_during_grouping(
    fragment: str, fragment_x0: float, fragment_x1: float, font: str | None
) -> None:
    opening = [
        _line(_BODY_TEXT, x0=144.0, y0=80.0, y1=92.0),
        _line(_BODY_TEXT, x0=108.0, y0=94.0, y1=106.0),
        _line("The formula describes the quantity,", x0=108.0, y0=108.0, y1=120.0),
    ]
    continuation = [
        _line(
            "where q denotes the closest point on the surface in this test.",
            x0=144.0,
            y0=128.0,
            y1=140.0,
        ),
        _line(_BODY_TEXT, x0=108.0, y0=142.0, y1=154.0),
        _line(_BODY_TEXT, x0=108.0, y0=156.0, y1=168.0),
    ]
    margin_fragment = _line(
        fragment, x0=fragment_x0, x1=fragment_x1, y0=128.0, y1=140.0, font=font
    )
    doc = _doc(_page(20, _block(*opening), _block(margin_fragment), _block(*continuation)))
    assert any(
        finding.details.get("issue_type") == "unexpected_indent_on_continuation_line"
        for finding in check_pdf_indentation(doc)
    )


def test_p015_connected_lowercase_prefix_rejoins_during_grouping() -> None:
    opening = [
        _line(_BODY_TEXT, x0=144.0, y0=80.0, y1=92.0),
        _line(_BODY_TEXT, x0=108.0, y0=94.0, y1=106.0),
        _line("The formula describes the quantity,", x0=108.0, y0=108.0, y1=120.0),
    ]
    prefix = _line("where q", x0=108.0, x1=140.0, y0=128.0, y1=140.0, italic=True)
    continuation = [
        _line(
            "denotes the closest point on the surface in this test.",
            x0=144.0,
            y0=128.0,
            y1=140.0,
        ),
        _line(_BODY_TEXT, x0=108.0, y0=142.0, y1=154.0),
        _line(_BODY_TEXT, x0=108.0, y0=156.0, y1=168.0),
    ]
    doc = _doc(_page(20, _block(*opening), _block(prefix), _block(*continuation)))
    assert not any(
        finding.details.get("issue_type") == "unexpected_indent_on_continuation_line"
        for finding in check_pdf_indentation(doc)
    )


@pytest.mark.parametrize("fragment_x1", [120.0, 131.0])
def test_p015_disconnected_lowercase_fragment_cannot_suppress_final_check(
    fragment_x1: float,
) -> None:
    opening = [
        _line(_BODY_TEXT, x0=144.0, y0=80.0, y1=92.0),
        _line(_BODY_TEXT, x0=108.0, y0=94.0, y1=106.0),
        _line(_BODY_TEXT, x0=108.0, y0=108.0, y1=120.0),
    ]
    prefix = _line("and", x0=108.0, x1=fragment_x1, y0=170.0, y1=182.0)
    continuation = [
        _line(
            "where q denotes the closest point on the surface in this test.",
            x0=144.0,
            y0=170.0,
            y1=182.0,
        ),
        _line(_BODY_TEXT, x0=108.0, y0=184.0, y1=196.0),
        _line(_BODY_TEXT, x0=108.0, y0=198.0, y1=210.0),
    ]
    doc = _doc(_page(20, _block(*opening), _block(prefix), _block(*continuation)))
    assert any(
        finding.details.get("issue_type") == "unexpected_indent_on_continuation_line"
        for finding in check_pdf_indentation(doc)
    )


@pytest.mark.parametrize("same_paragraph_gap", [True, False])
@pytest.mark.parametrize("fragment_gap", [12.0, 13.0])
@pytest.mark.parametrize("same_font", [True, False])
def test_p015_fragment_connectivity_boundary_in_both_paths(
    same_paragraph_gap: bool, fragment_gap: float, same_font: bool
) -> None:
    opening = [
        _line(_BODY_TEXT, x0=144.0, y0=80.0, y1=92.0),
        _line(_BODY_TEXT, x0=108.0, y0=94.0, y1=106.0),
        _line(
            "The formula describes the quantity,",
            x0=108.0,
            y0=108.0,
            y1=120.0,
        ),
    ]
    first_y = 128.0 if same_paragraph_gap else 170.0
    prefix = _line(
        "where q",
        x0=108.0,
        x1=144.0 - fragment_gap,
        y0=first_y,
        y1=first_y + 12.0,
        italic=True,
        font=None if same_font else "CourierNew",
    )
    continuation = [
        _line(
            "denotes the closest point on the surface in this test.",
            x0=144.0,
            y0=first_y,
            y1=first_y + 12.0,
        ),
        _line(_BODY_TEXT, x0=108.0, y0=first_y + 14.0, y1=first_y + 26.0),
        _line(_BODY_TEXT, x0=108.0, y0=first_y + 28.0, y1=first_y + 40.0),
    ]
    doc = _doc(_page(20, _block(*opening), _block(prefix), _block(*continuation)))
    flagged = any(
        finding.details.get("issue_type") == "unexpected_indent_on_continuation_line"
        for finding in check_pdf_indentation(doc)
    )
    assert flagged == (fragment_gap > 12.0 or not same_font)


@pytest.mark.parametrize("same_paragraph_gap", [True, False])
@pytest.mark.parametrize("left_gap", [6.0, 16.0])
@pytest.mark.parametrize("same_font", [True, False])
def test_p015_multifragment_prefix_requires_a_connected_chain_to_body_margin(
    same_paragraph_gap: bool, left_gap: float, same_font: bool
) -> None:
    opening = [
        _line(_BODY_TEXT, x0=144.0, y0=80.0, y1=92.0),
        _line(_BODY_TEXT, x0=108.0, y0=94.0, y1=106.0),
        _line("The formula describes the quantity,", x0=108.0, y0=108.0, y1=120.0),
    ]
    first_y = 128.0 if same_paragraph_gap else 170.0
    left = _line(
        "where the",
        x0=108.0,
        x1=166.0 - left_gap,
        y0=first_y,
        y1=first_y + 12.0,
        italic=True,
        font=None if same_font else "CourierNew",
    )
    middle = _line("value", x0=166.0, x1=190.0, y0=first_y, y1=first_y + 12.0)
    continuation = [
        _line(
            "denotes the closest point on the surface in this test.",
            x0=190.0,
            y0=first_y,
            y1=first_y + 12.0,
        ),
        _line(_BODY_TEXT, x0=108.0, y0=first_y + 14.0, y1=first_y + 26.0),
        _line(_BODY_TEXT, x0=108.0, y0=first_y + 28.0, y1=first_y + 40.0),
    ]
    doc = _doc(_page(20, _block(*opening), _block(left), _block(middle), _block(*continuation)))
    flagged = any(
        finding.details.get("issue_type") == "unexpected_indent_on_continuation_line"
        for finding in check_pdf_indentation(doc)
    )
    assert flagged == (left_gap > 12.0 or not same_font)


def test_p015_noncontinuation_row_retains_connected_extraction_prefix() -> None:
    prefix = _line("Model", x0=108.0, x1=155.4, y0=80.0, y1=92.0)
    following = _line(
        "Additional synthetic content on the same physical row.",
        x0=168.8,
        y0=80.0,
        y1=92.0,
    )
    assert _effective_row_start_x([prefix, following], 1, body_x=108.0) == 108.0


def test_p015_suppresses_connected_split_continuation_prefix() -> None:
    opening = [
        _line(_BODY_TEXT, x0=144.0, y0=80.0, y1=92.0),
        _line(_BODY_TEXT, x0=108.0, y0=94.0, y1=106.0),
        _line(_BODY_TEXT, x0=108.0, y0=108.0, y1=120.0),
    ]
    # Italic math and regular prose share a font family but do not get merged
    # into one extracted line by the same-style row merger.
    prefix = _line("where q", x0=108.0, x1=140.0, y0=170.0, y1=182.0, italic=True)
    suffix = [
        _line(
            "denotes the closest point on the surface in this test.", x0=144.0, y0=170.0, y1=182.0
        ),
        _line(_BODY_TEXT, x0=108.0, y0=184.0, y1=196.0),
        _line(_BODY_TEXT, x0=108.0, y0=198.0, y1=210.0),
    ]
    doc = _doc(_page(20, _block(*opening), _block(prefix), _block(*suffix)))
    assert not any(
        f.details.get("issue_type") == "unexpected_indent_on_continuation_line"
        for f in check_pdf_indentation(doc)
    )


@pytest.mark.parametrize("font", ["CourierNew", "MonotypeCorsiva"])
def test_p015_still_flags_indented_continuation_in_ordinary_fonted_prose(font: str) -> None:
    opening = [
        _line(_BODY_TEXT, x0=144.0, y0=80.0, y1=92.0),
        _line(_BODY_TEXT, x0=108.0, y0=94.0, y1=106.0),
        _line(_BODY_TEXT, x0=108.0, y0=108.0, y1=120.0),
    ]
    continuation = [
        _line(
            "where q denotes the closest point on the surface in this test.",
            x0=144.0,
            y0=170.0,
            y1=182.0,
            font=font,
        ),
        _line(_BODY_TEXT, x0=108.0, y0=184.0, y1=196.0, font=font),
        _line(_BODY_TEXT, x0=108.0, y0=198.0, y1=210.0, font=font),
    ]
    doc = _doc(_page(20, _block(*opening), _block(*continuation)))
    assert any(
        f.details.get("issue_type") == "unexpected_indent_on_continuation_line"
        for f in check_pdf_indentation(doc)
    )


def test_p015_monospace_comment_with_code_statements_is_not_body_prose() -> None:
    opening = [
        _line(_BODY_TEXT, x0=144.0, y0=80.0, y1=92.0),
        _line(_BODY_TEXT, x0=108.0, y0=94.0, y1=106.0),
        _line(_BODY_TEXT, x0=108.0, y0=108.0, y1=120.0),
    ]
    code = [
        _line(
            "where the signal is recorded for each sample",
            x0=144.0,
            y0=170.0,
            y1=182.0,
            font="CMTT10",
        ),
        _line("value=signal; % calculate", x0=108.0, y0=184.0, y1=196.0, font="CMTT10"),
        _line("plot(value);", x0=108.0, y0=198.0, y1=210.0, font="CMTT10"),
    ]
    doc = _doc(_page(20, _block(*opening), _block(*code)))
    assert not any(
        f.details.get("issue_type") == "unexpected_indent_on_continuation_line"
        for f in check_pdf_indentation(doc)
    )


@pytest.mark.parametrize("abbreviation", ["Eq.", "Fig.", "e.g.", "i.e."])
def test_p015_does_not_treat_abbreviation_period_as_completed_sentence(
    abbreviation: str,
) -> None:
    opening = [
        _line(_BODY_TEXT, x0=144.0, y0=80.0, y1=92.0),
        _line(_BODY_TEXT, x0=108.0, y0=94.0, y1=106.0),
        _line(f"The quantity is described by {abbreviation}", x0=108.0, y0=108.0, y1=120.0),
    ]
    continuation = [
        _line(
            "where q denotes the closest point on the surface in this test.",
            x0=144.0,
            y0=128.0,
            y1=140.0,
        ),
        _line(_BODY_TEXT, x0=108.0, y0=142.0, y1=154.0),
        _line(_BODY_TEXT, x0=108.0, y0=156.0, y1=168.0),
    ]
    doc = _doc(_page(20, _block(*opening), _block(*continuation)))
    assert any(
        f.details.get("issue_type") == "unexpected_indent_on_continuation_line"
        for f in check_pdf_indentation(doc)
    )


@pytest.mark.parametrize(
    "ending",
    ["et al.", "etc.", "cf.", "vs.", "Dr.", "U.S.", "et seq.", "ibid.", 'et al.")'],
)
def test_p015_ambiguous_abbreviation_period_preserves_continuation_finding(
    ending: str,
) -> None:
    opening = [
        _line(_BODY_TEXT, x0=144.0, y0=80.0, y1=92.0),
        _line(_BODY_TEXT, x0=108.0, y0=94.0, y1=106.0),
        _line(f"The quantity is described by {ending}", x0=108.0, y0=108.0, y1=120.0),
    ]
    continuation = [
        _line(
            "where q denotes the closest point on the surface in this test.",
            x0=144.0,
            y0=128.0,
            y1=140.0,
        ),
        _line(_BODY_TEXT, x0=108.0, y0=142.0, y1=154.0),
        _line(_BODY_TEXT, x0=108.0, y0=156.0, y1=168.0),
    ]
    doc = _doc(_page(20, _block(*opening), _block(*continuation)))
    assert any(
        finding.details.get("issue_type") == "unexpected_indent_on_continuation_line"
        for finding in check_pdf_indentation(doc)
    )


@pytest.mark.parametrize("ending", ["the observation.", "et al.", "etc."])
def test_p015_completed_paragraph_with_capitalized_next_sentence_is_not_continuation(
    ending: str,
) -> None:
    opening = [
        _line(_BODY_TEXT, x0=144.0, y0=80.0, y1=92.0),
        _line(_BODY_TEXT, x0=108.0, y0=94.0, y1=106.0),
        _line(f"The quantity is described by {ending}", x0=108.0, y0=108.0, y1=120.0),
    ]
    next_paragraph = [
        _line(
            "Another observation starts a new paragraph in this test.",
            x0=144.0,
            y0=128.0,
            y1=140.0,
        ),
        _line(_BODY_TEXT, x0=108.0, y0=142.0, y1=154.0),
        _line(_BODY_TEXT, x0=108.0, y0=156.0, y1=168.0),
    ]
    doc = _doc(_page(20, _block(*opening), _block(*next_paragraph)))
    assert not any(
        finding.details.get("issue_type") == "unexpected_indent_on_continuation_line"
        for finding in check_pdf_indentation(doc)
    )


@pytest.mark.parametrize("quoted_question", ['"Why?"', '"Stop!"'])
def test_p015_quoted_punctuation_does_not_complete_sentence(quoted_question: str) -> None:
    opening = [
        _line(_BODY_TEXT, x0=144.0, y0=80.0, y1=92.0),
        _line(_BODY_TEXT, x0=108.0, y0=94.0, y1=106.0),
        _line(f"The reviewer asked {quoted_question}", x0=108.0, y0=108.0, y1=120.0),
    ]
    continuation = [
        _line("she repeated in the follow-up discussion.", x0=144.0, y0=128.0, y1=140.0),
        _line(_BODY_TEXT, x0=108.0, y0=142.0, y1=154.0),
        _line(_BODY_TEXT, x0=108.0, y0=156.0, y1=168.0),
    ]
    doc = _doc(_page(20, _block(*opening), _block(*continuation)))
    assert any(
        f.details.get("issue_type") == "unexpected_indent_on_continuation_line"
        for f in check_pdf_indentation(doc)
    )


@pytest.mark.parametrize(
    "opening_phrase",
    [
        "pH values were recorded across each trial for this test analysis.",
        "mRNA expression levels varied significantly across the samples tested.",
        "eBay listings were used as the primary data source for this test case.",
    ],
)
def test_p015_does_not_flag_mixed_case_led_new_paragraph_as_continuation(
    opening_phrase: str,
) -> None:
    """A genuine new, correctly indented paragraph that happens to open with a
    lowercase-led mixed-case scientific term or brand name (pH, mRNA, eBay)
    must not be mistaken for a continuation clause like "where q denotes ..."
    just because its very first letter is lowercase -- the internal uppercase
    letter is the general signal that this is a term/proper noun starting a
    fresh sentence, not a common all-lowercase connector word.
    """
    para = [
        _line(opening_phrase, x0=144.0, y0=80.0, y1=92.0),
        _line(
            "Lorem ipsum dolor sit amet consectetur adipiscing elit sed do.",
            x0=108.0,
            y0=94.0,
            y1=106.0,
        ),
        _line(
            "Lorem ipsum dolor sit amet consectetur adipiscing elit sed do.",
            x0=108.0,
            y0=108.0,
            y1=120.0,
        ),
    ]
    doc = _doc(_page(20, _block(*para)))
    findings = [
        f
        for f in check_pdf_indentation(doc)
        if f.rule_id == "P015"
        and f.details.get("issue_type") == "unexpected_indent_on_continuation_line"
    ]
    assert not findings


def test_p015_does_not_flag_page_opening_paragraph_as_continuation() -> None:
    """A page-opening indented paragraph that happens to start with a lowercase
    connector word is a new paragraph, not a same-page continuation line.
    """
    para = [
        _line(
            "where the reconstructed field remains valid for this test case.",
            x0=144.0,
            y0=80.0,
            y1=92.0,
        ),
        _line(
            "Lorem ipsum dolor sit amet consectetur adipiscing elit sed do.",
            x0=108.0,
            y0=94.0,
            y1=106.0,
        ),
        _line(
            "Lorem ipsum dolor sit amet consectetur adipiscing elit sed do.",
            x0=108.0,
            y0=108.0,
            y1=120.0,
        ),
    ]
    doc = _doc(_page(20, _block(*para)))
    findings = [
        f
        for f in check_pdf_indentation(doc)
        if f.rule_id == "P015"
        and f.details.get("issue_type") == "unexpected_indent_on_continuation_line"
    ]
    assert not findings
