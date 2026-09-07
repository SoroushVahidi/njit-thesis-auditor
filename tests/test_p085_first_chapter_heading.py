"""Regression tests for the Ester-confirmed first-body CHAPTER 1 requirement."""

from pathlib import Path

import fitz

from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.rules.pdf_first_chapter_heading import check_pdf_first_chapter_heading
from njit_auditor.rules.pdf_page_numbering_regime import check_pdf_page_numbering_regime
from njit_auditor.rules.pdf_page_numbers import check_pdf_page_number_sequence


def _make_pdf(path: Path, first_body_heading: str, later_heading: str | None = None) -> None:
    doc = fitz.open()
    toc = doc.new_page(width=612, height=792)
    toc.insert_text((220, 100), "TABLE OF CONTENTS", fontsize=14)
    toc.insert_text((300, 750), "i", fontsize=12)
    body = doc.new_page(width=612, height=792)
    body.insert_text((108, 100), first_body_heading, fontsize=16)
    body.insert_text((108, 140), "Body paragraph text.", fontsize=12)
    body.insert_text((300, 750), "1", fontsize=12)
    if later_heading is not None:
        later = doc.new_page(width=612, height=792)
        later.insert_text((108, 100), later_heading, fontsize=16)
        later.insert_text((300, 750), "2", fontsize=12)
    doc.save(path)
    doc.close()


def test_first_body_chapter_one_passes(tmp_path: Path) -> None:
    path = tmp_path / "chapter_one.pdf"
    _make_pdf(path, "CHAPTER 1 INTRODUCTION")
    findings = check_pdf_first_chapter_heading(load_pdf_layout(str(path)))
    assert findings == []


def test_introduction_before_later_chapter_one_is_reported(tmp_path: Path) -> None:
    path = tmp_path / "late_chapter_one.pdf"
    _make_pdf(path, "INTRODUCTION", "CHAPTER 1 METHODS")
    model = load_pdf_layout(str(path))
    findings = check_pdf_first_chapter_heading(model)
    assert len(findings) == 1
    assert findings[0].page == 2
    assert findings[0].details["observed_heading"] == "INTRODUCTION"
    assert findings[0].details["issue_type"] == "missing_first_chapter_one_heading"
    assert check_pdf_page_number_sequence(model) == []
    assert check_pdf_page_numbering_regime(model) == []


def test_extracted_chapter1_without_space_is_accepted(tmp_path: Path) -> None:
    path = tmp_path / "mashed_chapter_one.pdf"
    _make_pdf(path, "CHAPTER1 INTRODUCTION")
    assert check_pdf_first_chapter_heading(load_pdf_layout(str(path))) == []
