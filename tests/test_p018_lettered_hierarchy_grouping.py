"""Privacy-safe regressions for P018 lettered appendix hierarchy grouping.

Covers the false positive where lettered-only TOC continuation pages compared
APPENDIX/REFERENCES roots with lettered subsections (A.2, B.1) as peers.
"""

from __future__ import annotations

from pathlib import Path

import fitz

from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.pdf_models import BBox, PdfTextLine, PdfTextSpan
from njit_auditor.rules.pdf_toc_alignment import (
    TocEntryLine,
    _hierarchy_group_dot_conformity_ratio,
    _parse_toc_hierarchy_level,
    _select_worst_leader_dots_entry,
    check_pdf_toc_alignment,
)


def _draw_toc_entry(
    page: fitz.Page, y: float, label_x: float, label: str, page_num_x: float
) -> None:
    page.insert_text((label_x, y), label)
    page.insert_text((page_num_x, y), "12")


def _entry(text: str, *, indent_x: float, y0: float, has_leader_dots: bool) -> TocEntryLine:
    span = PdfTextSpan(
        text=text,
        font="Times-Roman",
        size=12.0,
        bbox=BBox(x0=indent_x, y0=y0, x1=indent_x + max(40.0, len(text) * 5.0), y1=y0 + 12.0),
    )
    line = PdfTextLine(
        text=text,
        spans=[span],
        bbox=span.bbox,
    )
    return TocEntryLine(
        line=line,
        cleaned_text=text,
        page_number_token="12",
        page_number_right_x=520.0,
        indent_x=indent_x,
        has_leader_dots=has_leader_dots,
    )


def _hierarchy_findings(model) -> list:
    return [
        f
        for f in check_pdf_toc_alignment(model)
        if f.rule_id == "P018" and f.details.get("issue_type") == "inconsistent_hierarchy_indent"
    ]


def test_parse_toc_hierarchy_level_numeric_lettered_and_roots() -> None:
    assert _parse_toc_hierarchy_level("1 INTRODUCTION .... 1") == 1
    assert _parse_toc_hierarchy_level("1.1 Background .... 2") == 2
    assert _parse_toc_hierarchy_level("1.1.1 Detail .... 3") == 3
    assert _parse_toc_hierarchy_level("A.1 Basic Bounds .... 10") == 2
    assert _parse_toc_hierarchy_level("B.2.1 Nested Note .... 11") == 3
    assert _parse_toc_hierarchy_level("APPENDIX A SYNTHETIC TITLE .... 20") == 1
    assert _parse_toc_hierarchy_level("APPENDIX B ANOTHER TITLE .... 30") == 1
    assert _parse_toc_hierarchy_level("REFERENCES .... 40") == 1
    assert _parse_toc_hierarchy_level("CHAPTER 1 INTRODUCTION .... 1") == 1
    # Ambiguous / unclassified titles stay None.
    assert _parse_toc_hierarchy_level("Motivation without a number .... 5") is None
    assert _parse_toc_hierarchy_level("A Bare Letter Title .... 6") is None


def test_philip_equivalent_lettered_appendix_page_no_hierarchy_false_positive(
    tmp_path: Path,
) -> None:
    """Lettered-only TOC page: APPENDIX/REFERENCES at chapter x; A.n/B.n at L2 x."""
    pdf_path = tmp_path / "toc_lettered_appendix_page.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((220, 90), "TABLE OF CONTENTS", fontsize=16, fontname="Times-Bold")
    y = 140.0
    # Prior appendix L2 rows (continuation page), then appendix root, then more L2, then refs.
    for label in (
        "A.2 Synthetic Inequality Away From Extremes ....",
        "A.3 Synthetic Inequality Near Extremes ....",
    ):
        _draw_toc_entry(page, y, 124.7, label, 520)
        y += 24
    _draw_toc_entry(page, y, 108.4, "APPENDIX B SYNTHETIC CONVEX FUNCTIONALS ....", 520)
    y += 24
    for label in (
        "B.1 Local Synthetic Spaces ....",
        "B.2 Lower Semicontinuous Synthetic Maps ....",
        "B.3 Signed Synthetic Measures ....",
        "B.4 Convex Synthetic Functionals ....",
    ):
        _draw_toc_entry(page, y, 124.7, label, 520)
        y += 24
    _draw_toc_entry(page, y, 108.4, "REFERENCES ....", 520)
    doc.save(pdf_path)
    doc.close()

    assert _hierarchy_findings(load_pdf_layout(str(pdf_path))) == []


def test_numbered_chapter_and_subsection_hierarchy_consistent(tmp_path: Path) -> None:
    pdf_path = tmp_path / "toc_numeric_consistent.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((220, 90), "TABLE OF CONTENTS", fontsize=16, fontname="Times-Bold")
    _draw_toc_entry(page, 140, 108, "1 INTRODUCTION ....", 520)
    _draw_toc_entry(page, 160, 124, "1.1 Background ....", 520)
    _draw_toc_entry(page, 180, 124, "1.2 Methods ....", 520)
    _draw_toc_entry(page, 200, 124, "1.3 Results ....", 520)
    _draw_toc_entry(page, 220, 108, "2 LITERATURE ....", 520)
    doc.save(pdf_path)
    doc.close()
    assert _hierarchy_findings(load_pdf_layout(str(pdf_path))) == []


def test_lettered_appendix_subsections_consistent_indent(tmp_path: Path) -> None:
    pdf_path = tmp_path / "toc_lettered_l2_consistent.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((220, 90), "TABLE OF CONTENTS", fontsize=16, fontname="Times-Bold")
    _draw_toc_entry(page, 140, 108, "APPENDIX A SYNTHETIC PROOFS ....", 520)
    _draw_toc_entry(page, 160, 124, "A.1 First Lemma ....", 520)
    _draw_toc_entry(page, 180, 124, "A.2 Second Lemma ....", 520)
    _draw_toc_entry(page, 200, 124, "A.3 Third Lemma ....", 520)
    doc.save(pdf_path)
    doc.close()
    assert _hierarchy_findings(load_pdf_layout(str(pdf_path))) == []


def test_appendix_and_references_roots_align_as_level_one(tmp_path: Path) -> None:
    pdf_path = tmp_path / "toc_roots_level_one.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((220, 90), "TABLE OF CONTENTS", fontsize=16, fontname="Times-Bold")
    _draw_toc_entry(page, 140, 108, "APPENDIX A SYNTHETIC TITLE ONE ....", 520)
    _draw_toc_entry(page, 160, 108, "APPENDIX B SYNTHETIC TITLE TWO ....", 520)
    _draw_toc_entry(page, 180, 108, "REFERENCES ....", 520)
    # Extra level-1 peers so a comparison could form; all aligned → no warning.
    _draw_toc_entry(page, 200, 108, "1 INTRODUCTION ....", 520)
    _draw_toc_entry(page, 220, 108, "2 METHODS ....", 520)
    doc.save(pdf_path)
    doc.close()
    assert _hierarchy_findings(load_pdf_layout(str(pdf_path))) == []


def test_genuine_lettered_same_level_outlier_still_detected(tmp_path: Path) -> None:
    pdf_path = tmp_path / "toc_lettered_l2_outlier.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((220, 90), "TABLE OF CONTENTS", fontsize=16, fontname="Times-Bold")
    _draw_toc_entry(page, 140, 108, "APPENDIX A SYNTHETIC TITLE ....", 520)
    _draw_toc_entry(page, 160, 124, "A.1 Aligned One ....", 520)
    _draw_toc_entry(page, 180, 124, "A.2 Aligned Two ....", 520)
    _draw_toc_entry(page, 200, 124, "A.3 Aligned Three ....", 520)
    _draw_toc_entry(page, 220, 180, "A.4 Misaligned Four ....", 520)
    doc.save(pdf_path)
    doc.close()
    findings = _hierarchy_findings(load_pdf_layout(str(pdf_path)))
    assert findings, "A clear lettered L2 indent outlier must remain detectable"
    assert float(findings[0].details.get("worst_delta_pt", "0")) > 10.0


def test_mixed_numeric_and_lettered_hierarchies_do_not_cross_compare(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "toc_mixed_numeric_lettered.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((220, 90), "TABLE OF CONTENTS", fontsize=16, fontname="Times-Bold")
    _draw_toc_entry(page, 140, 108, "5 FINAL CHAPTER ....", 520)
    _draw_toc_entry(page, 160, 124, "5.1 Wrap-Up ....", 520)
    _draw_toc_entry(page, 180, 124, "5.2 Outlook ....", 520)
    _draw_toc_entry(page, 200, 124, "5.3 Summary ....", 520)
    _draw_toc_entry(page, 220, 108, "APPENDIX A SYNTHETIC TITLE ....", 520)
    _draw_toc_entry(page, 240, 124, "A.1 First Appendix Section ....", 520)
    _draw_toc_entry(page, 260, 124, "A.2 Second Appendix Section ....", 520)
    _draw_toc_entry(page, 280, 124, "A.3 Third Appendix Section ....", 520)
    _draw_toc_entry(page, 300, 108, "REFERENCES ....", 520)
    doc.save(pdf_path)
    doc.close()
    assert _hierarchy_findings(load_pdf_layout(str(pdf_path))) == []


def test_ambiguous_unclassified_titles_do_not_warn(tmp_path: Path) -> None:
    """Unclassified titles at mixed indents must not invent a hierarchy warning."""
    pdf_path = tmp_path / "toc_ambiguous_unclassified.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((220, 90), "TABLE OF CONTENTS", fontsize=16, fontname="Times-Bold")
    _draw_toc_entry(page, 140, 108, "Synthetic Unnumbered Title One ....", 520)
    _draw_toc_entry(page, 160, 140, "Synthetic Unnumbered Title Two ....", 520)
    _draw_toc_entry(page, 180, 108, "Synthetic Unnumbered Title Three ....", 520)
    _draw_toc_entry(page, 200, 160, "Synthetic Unnumbered Title Four ....", 520)
    doc.save(pdf_path)
    doc.close()
    assert _hierarchy_findings(load_pdf_layout(str(pdf_path))) == []


def test_leader_dot_ranking_uses_lettered_hierarchy_groups() -> None:
    """Hierarchy-aware leader ranking must group lettered L2 separately from roots."""
    entries = [
        _entry(
            "APPENDIX A SYNTHETIC TITLE .... 10",
            indent_x=108.4,
            y0=140.0,
            has_leader_dots=True,
        ),
        _entry("A.1 First Section 11", indent_x=124.7, y0=164.0, has_leader_dots=True),
        _entry("A.2 Second Section 12", indent_x=124.7, y0=188.0, has_leader_dots=True),
        _entry(
            "A.3 Third Section Without Dots 13",
            indent_x=124.7,
            y0=212.0,
            has_leader_dots=False,
        ),
        _entry("A.4 Fourth Section 14", indent_x=124.7, y0=236.0, has_leader_dots=True),
    ]
    missing = [entries[3]]
    positions = {e: i for i, e in enumerate(entries)}
    # Four lettered L2 peers; three dotted → conformity 0.75 for the missing entry.
    assert _hierarchy_group_dot_conformity_ratio(entries[3], entries) == 0.75
    # APPENDIX root is a different level and must not dilute the L2 ratio.
    assert _hierarchy_group_dot_conformity_ratio(entries[0], entries) == 0.0
    chosen = _select_worst_leader_dots_entry(entries, missing, positions)
    assert chosen is entries[3]
