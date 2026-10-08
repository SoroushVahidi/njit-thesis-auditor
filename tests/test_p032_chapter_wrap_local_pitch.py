"""Chapter-title wraps can be compared with a single-spaced wrap on the same TOC."""

from pathlib import Path

import fitz

from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.rules.pdf_toc_list_wrapped_spacing import check_pdf_toc_list_wrapped_spacing


def _toc(path: Path, *, chapter_pitch: float, with_reference: bool = True) -> None:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((190, 90), "TABLE OF CONTENTS", fontname="Times-Bold", fontsize=16)
    for number, y in ((2, 140.0), (3, 260.0)):
        page.insert_text((108, y), f"{number} SYNTHETIC CHAPTER TITLE EXTENDS", fontsize=12)
        page.insert_text((126, y + chapter_pitch), "ACROSS ANOTHER LINE", fontsize=12)
        page.insert_text((520, y + chapter_pitch), str(number * 10), fontsize=12)
    if with_reference:
        page.insert_text((129, 400), "3.2.2 Long subsection title extending", fontsize=12)
        page.insert_text((126, 413.8), "to a second line", fontsize=12)
    doc.save(path)
    doc.close()


def test_double_spaced_chapter_wrap_uses_local_single_wrap_and_has_target_bbox(
    tmp_path: Path,
) -> None:
    path = tmp_path / "toc.pdf"
    _toc(path, chapter_pitch=20.7)
    findings = check_pdf_toc_list_wrapped_spacing(load_pdf_layout(str(path)))
    chapter_findings = [f for f in findings if f.details.get("entry_kind") == "toc_level_1"]
    assert len(chapter_findings) == 2
    assert all(f.rule_id == "P032" and f.page == 1 for f in chapter_findings)
    assert all(f.details.get("bbox") for f in chapter_findings)
    assert all(len(f.details["highlight_bboxes"].split(" | ")) == 2 for f in chapter_findings)
    assert len({f.details["bbox"] for f in chapter_findings}) == 2


def test_single_spaced_chapter_wrap_is_not_reported(tmp_path: Path) -> None:
    path = tmp_path / "toc.pdf"
    _toc(path, chapter_pitch=13.8)
    assert check_pdf_toc_list_wrapped_spacing(load_pdf_layout(str(path))) == []


def test_chapter_wrap_abstains_without_local_spacing_reference(tmp_path: Path) -> None:
    path = tmp_path / "toc.pdf"
    _toc(path, chapter_pitch=20.7, with_reference=False)
    assert check_pdf_toc_list_wrapped_spacing(load_pdf_layout(str(path))) == []
