"""Synthetic tests for P067 — Bio Sketch publication/presentation year ordering."""

from __future__ import annotations

from pathlib import Path

import fitz

from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.pdf_models import PdfDocument
from njit_auditor.rules.pdf_biosketch_publication_ordering import (
    _MIN_COMPARABLE_ENTRIES,
    check_pdf_biosketch_publication_ordering,
)

_PAGE_W = 612.0
_PAGE_H = 792.0
_MARGIN_L = 108.0
_HANGING_X = 132.0
_CENTER_X = _PAGE_W / 2

_PLACEHOLDER_AUTHOR = "Placeholder Author"
_PLACEHOLDER_TITLE = "Placeholder Title"
_PLACEHOLDER_VENUE = "Placeholder Venue"
_PLACEHOLDER_URL = "https://placeholder.invalid/publication"
_PLACEHOLDER_DOI = "doi:10.0000/placeholder-record"


def _make_entry(label: str, year: int, *, multiline: bool = True) -> list[str]:
    first = f"{label}. {year}. {_PLACEHOLDER_VENUE}."
    if not multiline:
        return [first]
    return [
        first,
        "Additional synthetic continuation details for the same citation entry.",
    ]


def _make_biosketch_publication_doc(
    *,
    degree_years: list[int] | None = None,
    publication_entries: list[list[str]] | None = None,
    add_publication_heading: bool = True,
    double_heading: bool = False,
) -> fitz.Document:
    doc = fitz.open()
    page = doc.new_page(width=_PAGE_W, height=_PAGE_H)
    page.insert_text((_CENTER_X - 60, 100.0), "BIOGRAPHICAL SKETCH", fontsize=14)
    if double_heading:
        page.insert_text((_CENTER_X - 60, 130.0), "BIOGRAPHICAL SKETCH", fontsize=14)

    y = 180.0
    if degree_years:
        for year in degree_years:
            page.insert_text((_MARGIN_L, y), f"Placeholder Degree, {year}", fontsize=11)
            y += 22.0

    if add_publication_heading:
        y += 16.0
        page.insert_text((_MARGIN_L, y), "Publications and Presentations", fontsize=12)
        y += 24.0

    if publication_entries:
        for entry in publication_entries:
            for idx, line in enumerate(entry):
                x = _MARGIN_L if idx == 0 else _HANGING_X
                page.insert_text((x, y), line, fontsize=11)
                y += 14.0
            y += 28.0
    return doc


def _load(doc: fitz.Document, tmp_path: Path) -> PdfDocument:
    path = tmp_path / "p067_test.pdf"
    doc.save(str(path))
    doc.close()
    return load_pdf_layout(str(path))


def test_no_biosketch_page_no_findings(tmp_path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page(width=_PAGE_W, height=_PAGE_H)
    page.insert_text((_MARGIN_L, 100.0), "ABSTRACT", fontsize=14)
    page.insert_text((_MARGIN_L, 160.0), "Synthetic abstract prose.", fontsize=11)
    findings = check_pdf_biosketch_publication_ordering(_load(doc, tmp_path))
    assert findings == []


def test_biosketch_without_publication_zone_no_findings(tmp_path: Path) -> None:
    doc = _make_biosketch_publication_doc(
        degree_years=[2022, 2019, 2015],
        add_publication_heading=False,
    )
    findings = check_pdf_biosketch_publication_ordering(_load(doc, tmp_path))
    assert findings == []


def test_descending_publication_years_no_findings(tmp_path: Path) -> None:
    doc = _make_biosketch_publication_doc(
        publication_entries=[
            _make_entry(f"{_PLACEHOLDER_AUTHOR} Alpha {_PLACEHOLDER_TITLE}", 2024),
            _make_entry(f"{_PLACEHOLDER_AUTHOR} Beta {_PLACEHOLDER_TITLE}", 2021),
            _make_entry(f"{_PLACEHOLDER_AUTHOR} Gamma {_PLACEHOLDER_TITLE}", 2018),
        ]
    )
    findings = check_pdf_biosketch_publication_ordering(_load(doc, tmp_path))
    assert findings == []


def test_ascending_publication_years_emit_finding(tmp_path: Path) -> None:
    doc = _make_biosketch_publication_doc(
        publication_entries=[
            _make_entry(f"{_PLACEHOLDER_AUTHOR} Alpha {_PLACEHOLDER_TITLE}", 2015),
            _make_entry(f"{_PLACEHOLDER_AUTHOR} Beta {_PLACEHOLDER_TITLE}", 2019),
            _make_entry(f"{_PLACEHOLDER_AUTHOR} Gamma {_PLACEHOLDER_TITLE}", 2023),
        ]
    )
    findings = check_pdf_biosketch_publication_ordering(_load(doc, tmp_path))
    assert any(
        f.details.get("issue_type") == "biosketch_publication_order_suspicious"
        for f in findings
    )


def test_equal_years_allowed_no_finding(tmp_path: Path) -> None:
    doc = _make_biosketch_publication_doc(
        publication_entries=[
            _make_entry(f"{_PLACEHOLDER_AUTHOR} Alpha {_PLACEHOLDER_TITLE}", 2024),
            _make_entry(f"{_PLACEHOLDER_AUTHOR} Beta {_PLACEHOLDER_TITLE}", 2024),
            _make_entry(f"{_PLACEHOLDER_AUTHOR} Gamma {_PLACEHOLDER_TITLE}", 2022),
        ]
    )
    findings = check_pdf_biosketch_publication_ordering(_load(doc, tmp_path))
    assert findings == []


def test_too_few_candidates_skip(tmp_path: Path) -> None:
    entries = [
        _make_entry(f"{_PLACEHOLDER_AUTHOR} Alpha {_PLACEHOLDER_TITLE}", 2024),
        _make_entry(f"{_PLACEHOLDER_AUTHOR} Beta {_PLACEHOLDER_TITLE}", 2022),
    ]
    assert len(entries) == _MIN_COMPARABLE_ENTRIES - 1
    doc = _make_biosketch_publication_doc(publication_entries=entries)
    findings = check_pdf_biosketch_publication_ordering(_load(doc, tmp_path))
    assert findings == []


def test_ambiguous_multi_year_entry_skipped(tmp_path: Path) -> None:
    doc = _make_biosketch_publication_doc(
        publication_entries=[
            _make_entry(f"{_PLACEHOLDER_AUTHOR} Alpha {_PLACEHOLDER_TITLE}", 2024),
            [
                f"{_PLACEHOLDER_AUTHOR}. {_PLACEHOLDER_TITLE}. 2019. {_PLACEHOLDER_VENUE}.",
                "Additional synthetic continuation updated in 2020 for archival notes.",
            ],
            _make_entry(f"{_PLACEHOLDER_AUTHOR} Gamma {_PLACEHOLDER_TITLE}", 2018),
        ]
    )
    findings = check_pdf_biosketch_publication_ordering(_load(doc, tmp_path))
    assert findings == []


def test_image_only_page_skips(tmp_path: Path) -> None:
    doc = fitz.open()
    doc.new_page(width=_PAGE_W, height=_PAGE_H)
    findings = check_pdf_biosketch_publication_ordering(_load(doc, tmp_path))
    assert findings == []


def test_multiple_biosketch_headings_skip(tmp_path: Path) -> None:
    doc = _make_biosketch_publication_doc(
        publication_entries=[
            _make_entry(f"{_PLACEHOLDER_AUTHOR} Alpha {_PLACEHOLDER_TITLE}", 2015),
            _make_entry(f"{_PLACEHOLDER_AUTHOR} Beta {_PLACEHOLDER_TITLE}", 2019),
            _make_entry(f"{_PLACEHOLDER_AUTHOR} Gamma {_PLACEHOLDER_TITLE}", 2023),
        ],
        double_heading=True,
    )
    findings = check_pdf_biosketch_publication_ordering(_load(doc, tmp_path))
    assert findings == []


def test_education_zone_years_do_not_trigger_p067(tmp_path: Path) -> None:
    doc = _make_biosketch_publication_doc(
        degree_years=[2015, 2019, 2023],
        publication_entries=[
            _make_entry(f"{_PLACEHOLDER_AUTHOR} Alpha {_PLACEHOLDER_TITLE}", 2024),
            _make_entry(f"{_PLACEHOLDER_AUTHOR} Beta {_PLACEHOLDER_TITLE}", 2021),
            _make_entry(f"{_PLACEHOLDER_AUTHOR} Gamma {_PLACEHOLDER_TITLE}", 2018),
        ],
    )
    findings = check_pdf_biosketch_publication_ordering(_load(doc, tmp_path))
    assert findings == []


def test_long_prose_line_with_year_excluded(tmp_path: Path) -> None:
    prose_line = (
        "This synthetic narrative mentions 2015 and continues as plain prose without "
        "citation punctuation or list style structure in the publications zone"
    )
    doc = _make_biosketch_publication_doc(
        publication_entries=[
            [prose_line],
            _make_entry(f"{_PLACEHOLDER_AUTHOR} Beta {_PLACEHOLDER_TITLE}", 2019),
            _make_entry(f"{_PLACEHOLDER_AUTHOR} Gamma {_PLACEHOLDER_TITLE}", 2023),
        ]
    )
    findings = check_pdf_biosketch_publication_ordering(_load(doc, tmp_path))
    assert findings == []


def test_privacy_no_biosketch_or_publication_text_in_findings(tmp_path: Path) -> None:
    doc = _make_biosketch_publication_doc(
        publication_entries=[
            _make_entry(f"{_PLACEHOLDER_AUTHOR} Alpha {_PLACEHOLDER_TITLE}", 2015),
            _make_entry(f"{_PLACEHOLDER_AUTHOR} Beta {_PLACEHOLDER_TITLE}", 2019),
            _make_entry(f"{_PLACEHOLDER_AUTHOR} Gamma {_PLACEHOLDER_TITLE}", 2023),
        ]
    )
    findings = check_pdf_biosketch_publication_ordering(_load(doc, tmp_path))
    assert findings
    forbidden = {
        _PLACEHOLDER_AUTHOR.lower(),
        _PLACEHOLDER_TITLE.lower(),
        _PLACEHOLDER_VENUE.lower(),
        "placeholder",
        "synthetic continuation details",
    }
    for finding in findings:
        assert finding.rule_id == "P067"
        payload = " ".join([finding.message, *finding.details.values()]).lower()
        for token in forbidden:
            assert token not in payload


def test_privacy_doi_and_url_not_leaked(tmp_path: Path) -> None:
    doc = _make_biosketch_publication_doc(
        publication_entries=[
            _make_entry(f"{_PLACEHOLDER_AUTHOR} Alpha {_PLACEHOLDER_TITLE}", 2015),
            [
                f"{_PLACEHOLDER_AUTHOR}. {_PLACEHOLDER_TITLE}. 2017. {_PLACEHOLDER_VENUE}.",
                f"Record links: {_PLACEHOLDER_DOI} {_PLACEHOLDER_URL}",
            ],
            _make_entry(f"{_PLACEHOLDER_AUTHOR} Beta {_PLACEHOLDER_TITLE}", 2019),
            _make_entry(f"{_PLACEHOLDER_AUTHOR} Gamma {_PLACEHOLDER_TITLE}", 2023),
        ]
    )
    findings = check_pdf_biosketch_publication_ordering(_load(doc, tmp_path))
    assert findings
    payload = " ".join([findings[0].message, *findings[0].details.values()]).lower()
    assert "doi:" not in payload
    assert "http://" not in payload
    assert "https://" not in payload
    assert "placeholder.invalid" not in payload
