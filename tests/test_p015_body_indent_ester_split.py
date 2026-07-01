"""Ester-aligned P015 body indentation split and front-matter Q-rule cards."""

from __future__ import annotations

import importlib
import json
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
)
from njit_auditor.rules.pdf_indentation import check_pdf_indentation

_REPO_ROOT = Path(__file__).resolve().parents[1]
_Q_MATRIX_PATH = _REPO_ROOT / "data/specs/ester_q_matrix.json"
_BODY_TEXT = "Lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod."


def _load_q_rules() -> dict[str, dict[str, str]]:
    rules = json.loads(_Q_MATRIX_PATH.read_text(encoding="utf-8"))["rules"]
    return {rule["id"]: rule for rule in rules}


def _span(
    text: str,
    *,
    bold: bool = False,
    x0: float = 108.0,
    x1: float = 504.0,
    y0: float = 50.0,
    y1: float = 62.0,
) -> PdfTextSpan:
    return PdfTextSpan(
        text=text,
        font="TimesNewRomanPSMT-Bold" if bold else "TimesNewRomanPSMT",
        size=12.0,
        bold=bold,
        italic=False,
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
) -> PdfTextLine:
    sp = _span(text, bold=bold, x0=x0, x1=x1, y0=y0, y1=y1)
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


@pytest.mark.parametrize(
    ("card_id", "q_id"),
    [("P044A", "Q002"), ("P044B", "Q003"), ("P043A", "Q044"), ("P043B", "Q045")],
)
def test_front_matter_atomic_cards_match_q_matrix(
    web_client, card_id: str, q_id: str
) -> None:
    _, wa = web_client
    q_rules = _load_q_rules()
    q_rule = q_rules[q_id]
    catalog = wa._build_rule_catalog()
    card = next(rule for rule in catalog["student_rules"] if rule["id"] == card_id)

    assert card["title"] == q_rule["question"]
    assert card["how_to_correct"] == q_rule["remediation"]


def test_public_mapping_splits_p015_issue_types(web_client) -> None:
    _, wa = web_client
    assert (
        wa._public_rule_reference_id("P015", issue_type="unexpected_opening_indent")
        == "P015A"
    )
    assert (
        wa._public_rule_reference_id("P015", issue_type="missing_later_indent") == "P015B"
    )


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
        if f.rule_id == "P015"
        and f.details.get("issue_type") == "unexpected_opening_indent"
    ]
    assert not findings
