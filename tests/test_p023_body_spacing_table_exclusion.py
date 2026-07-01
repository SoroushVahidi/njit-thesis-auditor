"""Regression tests for P023 body-spacing table/caption exclusion and paragraph highlights."""

from __future__ import annotations

from pathlib import Path

import fitz

from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.rules.pdf_body_spacing import check_pdf_body_spacing

_BODY_LINE = (
    "Synthetic body paragraph text line for double-spacing verification test number {idx}."
)


def _save_pdf(path: Path, draw) -> None:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    draw(page)
    doc.save(path)
    doc.close()


def test_table_page_with_compact_cells_only_no_p023(tmp_path: Path) -> None:
    """Compact table body/caption text must not trigger P023 body-spacing warnings."""
    pdf_path = tmp_path / "table_only.pdf"
    _save_pdf(
        pdf_path,
        lambda page: (
            page.insert_text(
                (108, 70),
                "Table 4.1 Alignment of Research Questions and Survey Items",
                fontsize=12,
            ),
            page.insert_text((111, 110), "Research Question", fontsize=12),
            page.insert_text((340, 110), "Corresponding Survey Items", fontsize=12),
            page.insert_text(
                (111, 150),
                "RQ1: What benefits do warehouse workers perceive in exoskeleton use?",
                fontsize=12,
            ),
            page.insert_text(
                (340, 137),
                "Benefits Q1–Q3 (simplifying job duties, reducing fatigue, productivity)",
                fontsize=12,
            ),
            page.insert_text(
                (111, 163),
                "RQ2: What barriers do workers anticipate when considering exoskeleton use?",
                fontsize=12,
            ),
            page.insert_text(
                (340, 150),
                "Barriers Q1–Q4 (sharing devices, storage concerns, maintenance concerns)",
                fontsize=12,
            ),
            page.insert_text(
                (108, 624),
                (
                    "The four domains were designed as conceptual groupings "
                    "rather than as unidimensional"
                ),
                fontsize=12,
            ),
            page.insert_text(
                (108, 652),
                (
                    "psychometric scales. Each domain aggregates several related, "
                    "but not identical, items."
                ),
                fontsize=12,
            ),
        ),
    )

    findings = check_pdf_body_spacing(load_pdf_layout(str(pdf_path)))
    assert not findings


def test_table_caption_only_compact_spacing_no_p023(tmp_path: Path) -> None:
    pdf_path = tmp_path / "caption_only.pdf"
    y_positions = [140, 153, 166, 179, 192, 205]
    _save_pdf(
        pdf_path,
        lambda page: (
            page.insert_text(
                (108, 70),
                "Table 2.1 Example compact table caption text here",
                fontsize=12,
            ),
            *[
                page.insert_text((340, y), _BODY_LINE.format(idx=idx), fontsize=12)
                for idx, y in enumerate(y_positions)
            ],
        ),
    )

    findings = check_pdf_body_spacing(load_pdf_layout(str(pdf_path)))
    assert not findings


def test_single_spaced_body_paragraph_warns_with_bbox_and_snippet(tmp_path: Path) -> None:
    pdf_path = tmp_path / "single_paragraph.pdf"
    y_positions = [140, 152, 164, 176, 188, 200, 212, 224, 236, 248, 260]
    first_line = _BODY_LINE.format(idx=0)
    _save_pdf(
        pdf_path,
        lambda page: [
            page.insert_text((108, y), _BODY_LINE.format(idx=idx), fontsize=12)
            for idx, y in enumerate(y_positions)
        ],
    )

    findings = check_pdf_body_spacing(load_pdf_layout(str(pdf_path)))
    assert len(findings) == 1
    finding = findings[0]
    assert finding.rule_id == "P023"
    assert finding.details.get("issue_type") == "possible_body_text_not_double_spaced"
    assert finding.details.get("affected_text_snippet", "").startswith(first_line[:40])
    assert finding.details.get("bbox")
    assert finding.details.get("confidence") == "medium"
    assert finding.details.get("median_body_gap_pt")


def test_vague_page_level_warning_suppressed_without_localized_paragraph(tmp_path: Path) -> None:
    """Sparse mixed lines without a qualifying paragraph must not emit Medium P023."""
    pdf_path = tmp_path / "sparse.pdf"
    _save_pdf(
        pdf_path,
        lambda page: (
            page.insert_text((108, 200), _BODY_LINE.format(idx=0), fontsize=12),
            page.insert_text((108, 212), _BODY_LINE.format(idx=1), fontsize=12),
        ),
    )

    findings = check_pdf_body_spacing(load_pdf_layout(str(pdf_path)))
    assert not findings


def test_references_page_skipped_for_p023(tmp_path: Path) -> None:
    pdf_path = tmp_path / "references.pdf"
    y_positions = [140, 152, 164, 176, 188, 200, 212, 224, 236, 248, 260]
    doc = fitz.open()
    page0 = doc.new_page(width=612, height=792)
    page0.insert_text((200, 90), "CHAPTER 1", fontsize=16, fontname="Times-Bold")
    page0.insert_text((108, 140), _BODY_LINE.format(idx=0), fontsize=12)
    page0.insert_text((108, 164), _BODY_LINE.format(idx=1), fontsize=12)
    page0.insert_text((108, 188), _BODY_LINE.format(idx=2), fontsize=12)
    ref = doc.new_page(width=612, height=792)
    ref.insert_text((250, 90), "REFERENCES", fontsize=16, fontname="Times-Bold")
    for idx, y in enumerate(y_positions):
        ref.insert_text((108, y), _BODY_LINE.format(idx=idx), fontsize=12)
    doc.save(pdf_path)
    doc.close()

    findings = check_pdf_body_spacing(load_pdf_layout(str(pdf_path)))
    assert not any(f.rule_id == "P023" for f in findings)
