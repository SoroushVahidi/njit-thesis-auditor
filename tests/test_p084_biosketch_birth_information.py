"""Synthetic tests for P084 — Biographical Sketch birth-information check (Q023)."""

from __future__ import annotations

import json
from pathlib import Path

from njit_auditor.pdf_models import (
    BBox,
    PdfDocument,
    PdfPage,
    PdfTextBlock,
    PdfTextLine,
    PdfTextSpan,
)
from njit_auditor.rules.pdf_biosketch_birth_information import (
    check_pdf_biosketch_birth_information,
)
from njit_auditor.specs.q_rule_coverage import build_coverage_report

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _span(
    text: str,
    *,
    x0: float = 108.0,
    x1: float = 504.0,
    y0: float = 50.0,
    y1: float = 62.0,
    bold: bool = False,
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
    sp = _span(text, x0=x0, x1=x1, y0=y0, y1=y1, bold=bold)
    return PdfTextLine(text=text, bbox=BBox(x0=x0, y0=y0, x1=x1, y1=y1), spans=[sp])


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


def _page(*blocks: PdfTextBlock, page_number: int = 4) -> PdfPage:
    return PdfPage(
        page_number=page_number,
        width=612.0,
        height=792.0,
        text_blocks=list(blocks),
    )


def _doc(*pages: PdfPage) -> PdfDocument:
    return PdfDocument(path="synthetic", pages=list(pages))


def _biosketch_doc(
    body_lines: list[str],
    *,
    publication_lines: list[str] | None = None,
) -> PdfDocument:
    heading = _line("BIOGRAPHICAL SKETCH", x0=200.0, x1=412.0, y0=60.0, y1=72.0, bold=True)
    blocks = [_block(heading)]
    y = 100.0
    for text in body_lines:
        ln = _line(text, y0=y, y1=y + 12.0)
        blocks.append(_block(ln))
        y += 20.0
    if publication_lines:
        pub_heading = _line(
            "Publications and Presentations",
            x0=108.0,
            x1=420.0,
            y0=y + 10.0,
            y1=y + 22.0,
            bold=True,
        )
        blocks.append(_block(pub_heading))
        y += 40.0
        for text in publication_lines:
            ln = _line(text, y0=y, y1=y + 12.0)
            blocks.append(_block(ln))
            y += 20.0
    return _doc(_page(*blocks))


def _abstract_doc(lines: list[str]) -> PdfDocument:
    heading = _line("ABSTRACT", x0=240.0, x1=360.0, y0=60.0, y1=72.0, bold=True)
    blocks = [_block(heading)]
    y = 100.0
    for text in lines:
        ln = _line(text, y0=y, y1=y + 12.0)
        blocks.append(_block(ln))
        y += 20.0
    return _doc(_page(*blocks, page_number=2))


def test_biosketch_was_born_in_place_triggers_q023() -> None:
    findings = check_pdf_biosketch_birth_information(
        _biosketch_doc(["The student was born in Tehran and later pursued graduate study."])
    )
    assert len(findings) == 1
    assert findings[0].rule_id == "P084"
    assert findings[0].details.get("source_q_rule_id") == "Q023"


def test_biosketch_born_on_date_triggers_q023() -> None:
    findings = check_pdf_biosketch_birth_information(
        _biosketch_doc(["The student was born on May 1, 1995 and now studies engineering."])
    )
    assert len(findings) == 1
    assert "born_with_date" in str(findings[0].details.get("matched_pattern_types"))


def test_biosketch_date_of_birth_field_triggers_q023() -> None:
    findings = check_pdf_biosketch_birth_information(
        _biosketch_doc(["Date of birth: May 1, 1995"])
    )
    assert len(findings) == 1
    assert "date_of_birth_field" in str(findings[0].details.get("matched_pattern_types"))


def test_biosketch_place_of_birth_field_triggers_q023() -> None:
    findings = check_pdf_biosketch_birth_information(
        _biosketch_doc(["Place of birth: Tehran, Iran"])
    )
    assert len(findings) == 1
    assert "place_of_birth_field" in str(findings[0].details.get("matched_pattern_types"))


def test_education_dates_do_not_trigger() -> None:
    findings = check_pdf_biosketch_birth_information(
        _biosketch_doc(
            [
                "B.S., Placeholder University, 2018",
                "M.S., Placeholder Institute, 2020",
                "Ph.D., Placeholder Program, 2024",
            ]
        )
    )
    assert findings == []


def test_publication_years_do_not_trigger() -> None:
    findings = check_pdf_biosketch_birth_information(
        _biosketch_doc(
            ["The student completed doctoral study in 2024."],
            publication_lines=[
                "Placeholder Author. Placeholder Article Title. 2021.",
                "Placeholder Author. Placeholder Conference Paper. 2023.",
            ],
        )
    )
    assert findings == []


def test_body_text_outside_biosketch_does_not_trigger() -> None:
    findings = check_pdf_biosketch_birth_information(
        _abstract_doc(["The author was born in Tehran and later studied abroad."])
    )
    assert findings == []


def test_non_personal_birth_phrase_does_not_trigger() -> None:
    findings = check_pdf_biosketch_birth_information(
        _biosketch_doc(["The birth of the internet transformed modern communication."])
    )
    assert findings == []


def test_q023_coverage_changes_from_partial_to_implemented() -> None:
    q023 = next(r for r in build_coverage_report() if r.q_id == "Q023")
    assert q023.implementation_status == "implemented"
    assert q023.coverage_confidence == "medium"
    assert "P084" in q023.implementing_p_rules


def test_p084_catalog_entry_uses_q023_wording_and_remediation() -> None:
    rules = json.loads(
        (_REPO_ROOT / "data/processed/rules/project_added_rules.json").read_text(
            encoding="utf-8"
        )
    )
    p084 = next(r for r in rules if r["id"] == "P084")
    assert p084["source_q_rule_ids"] == ["Q023"]
    assert p084["question"] == (
        "Does the Biographical Sketch text exclude both place of birth and date of birth?"
    )
    assert p084["remediation"] == (
        "Remove place of birth and date of birth from the Biographical Sketch."
    )


def test_p084_warning_uses_required_student_facing_fix() -> None:
    finding = check_pdf_biosketch_birth_information(
        _biosketch_doc(["Birthplace: Tehran"])
    )[0]
    assert finding.message.startswith("Biographical Sketch appears to include")
    assert finding.details.get("suggested_fix") == (
        "Remove place of birth and date of birth from the Biographical Sketch."
    )
    assert finding.details.get("confidence") == "high"
