"""Synthetic, private-data-free checks for the complete student PDF report."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

import fitz
import pytest

from njit_auditor.pdf_highlight import HighlightBox
from njit_auditor.student_pdf_report import (
    build_combined_student_pdf_report,
    ordered_student_findings,
    render_student_report_text,
)


def _source(path: Path, pages: int = 7) -> None:
    with fitz.open() as doc:
        for number in range(1, pages + 1):
            page = doc.new_page(width=600 + number, height=790 + number)
            page.insert_text((80, 100), f"Synthetic thesis page {number}")
            if number == pages:
                page.set_rotation(90)
        doc.save(path)


def _finding(number: int, page: int | None, *, long: bool = False) -> dict[str, object]:
    return {
        "problem_number": number,
        "page": page,
        "rule_id": "P012",
        "public_rule_reference_id": "P012",
        "issue_type_label": f"Annotation issue {number}",
        "polished_comment": (
            "Reviewer annotation detected near the résumé section. " + "Read this carefully. " * 190
            if long else f"Reviewer annotation {number} detected."
        ),
        "suggested_fix": "Remove reviewer notes before submission. " * (40 if long else 1),
        "location_label": "Upper-left area",
        "confidence_label": "High confidence",
    }


def _report_text(document: fitz.Document, thesis_pages: int) -> str:
    return "\n".join(page.get_text() for page in list(document)[thesis_pages:])


def test_complete_thesis_and_every_finding_in_report(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "combined.pdf"
    _source(source)
    before = source.read_bytes()
    # Deliberately shuffled input: physical page order must control the report.
    findings = [
        _finding(4, 7),
        _finding(5, None),
        _finding(2, 4),
        _finding(1, 1),
        _finding(3, 4),
    ]
    result = build_combined_student_pdf_report(
        source,
        output,
        findings,
        boxes_by_problem={
            1: [(80, 85, 180, 110)],
            2: [(80, 85, 180, 110)],
            3: [(250, 85, 340, 110)],
            4: [(80, 85, 180, 110)],
        },
        file_name="synthetic_thesis.pdf",
        manuscript_page_labels={4: "iv"},
    )
    assert source.read_bytes() == before
    assert result.total_visible_findings == 5
    assert result.highlighted_findings == 4
    assert result.document_level_findings == 1
    assert result.highlight_boxes_drawn == 4
    assert result.pages_with_highlights == 3
    assert result.markers_drawn == 4
    with fitz.open(source) as original, fitz.open(output) as combined:
        assert combined.page_count == 7 + result.report_pages
        for index in range(7):
            assert combined[index].rect == original[index].rect
            assert combined[index].rotation == original[index].rotation
            assert f"Synthetic thesis page {index+1}" in combined[index].get_text()
        for index, expected in ((0, 1), (3, 2), (6, 1)):
            assert len(list(combined[index].annots() or [])) == expected
        assert "#1" in combined[0].get_text()
        assert "#2" in combined[3].get_text()
        assert "#3" in combined[3].get_text()
        assert "#4" in combined[6].get_text()
        text = _report_text(combined, 7)
        assert [text.index(f"Problem #{number}") for number in range(1, 6)] == sorted(
            text.index(f"Problem #{number}") for number in range(1, 6)
        )
        assert "Manuscript page: iv" in text
        assert "DOCUMENT-LEVEL FINDINGS" in text
        assert combined.get_toc() == [
            [1, "Thesis", 1],
            [1, "Formatting Problems", 8],
        ]


def test_no_bbox_and_long_unicode_text_wrap_across_pages(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "combined.pdf"
    _source(source, pages=3)
    findings = [_finding(1, 2, long=True), _finding(2, 3)]
    result = build_combined_student_pdf_report(
        source,
        output,
        findings,
        boxes_by_problem={2: [(80, 85, 180, 110)]},
        file_name="résumé_thesis.pdf",
    )
    assert result.report_pages > 1
    assert result.highlighted_findings == 1
    assert result.unhighlighted_page_findings == 1
    with fitz.open(output) as doc:
        text = _report_text(doc, 3)
        assert "résumé" in text
        assert "Problem #1" in text and "Problem #2" in text
        assert "Exact visual highlight unavailable." in text
        assert "How to fix:" in text
        assert len(list(doc[1].annots() or [])) == 0
        assert len(list(doc[2].annots() or [])) == 1


def test_zero_findings_has_limited_one_page_report(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "combined.pdf"
    _source(source, pages=20)
    result = build_combined_student_pdf_report(
        source, output, [], boxes_by_problem={}, file_name="thesis.pdf"
    )
    # One page for the summary, plus the shared "what was checked" disclosure.
    assert result.report_pages <= 2
    assert result.highlight_boxes_drawn == 0
    with fitz.open(output) as doc:
        assert doc.page_count == 20 + result.report_pages
        assert (
            "No formatting problems were detected by the implemented checks"
            in doc[20].get_text()
        )
        assert all(len(list(doc[index].annots() or [])) == 0 for index in range(20))


def test_p011_special_box_styles_and_one_problem_marker(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "combined.pdf"
    _source(source, pages=1)
    finding = _finding(1, 1)
    finding["rule_id"] = "P011"
    result = build_combined_student_pdf_report(
        source,
        output,
        [finding],
        boxes_by_problem={1: [
            HighlightBox(80, 85, 180, 110, kind="line"),
            HighlightBox(175, 85, 190, 110, kind="overflow"),
            HighlightBox(190, 85, 193, 110, kind="guide"),
        ]},
        file_name="thesis.pdf",
    )
    assert result.highlight_boxes_drawn == 3
    assert result.markers_drawn == 1
    with fitz.open(output) as doc:
        assert len(list(doc[0].annots() or [])) == 3
        assert doc[0].get_text().count("#1") == 1


def test_order_and_text_use_existing_problem_numbers() -> None:
    findings = [_finding(3, None), _finding(2, 2), _finding(1, 1)]
    assert [f["problem_number"] for f in ordered_student_findings(findings)] == [1, 2, 3]
    text = render_student_report_text(findings, file_name="thesis.pdf")
    assert text.index("Problem #1") < text.index("Problem #2") < text.index("Problem #3")
    assert "Public rule reference: P012" not in text
    assert "R012" in text


def test_many_findings_on_one_page_are_not_capped(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "combined.pdf"
    _source(source, pages=1)
    findings = [_finding(number, 1) for number in range(1, 112)]
    boxes = {
        number: [(80, 90 + (number % 40) * 5, 180, 94 + (number % 40) * 5)]
        for number in range(1, 112)
    }
    result = build_combined_student_pdf_report(
        source, output, findings, boxes_by_problem=boxes, file_name="thesis.pdf"
    )
    assert result.total_visible_findings == 111
    assert result.highlight_boxes_drawn == 111
    assert result.highlighted_findings == 111
    with fitz.open(output) as doc:
        assert len(list(doc[0].annots() or [])) == 111
        assert "Problem #111" in _report_text(doc, 1)


def test_web_view_text_and_pdf_share_problem_identity_and_wording(tmp_path: Path) -> None:
    from njit_auditor.report_view import build_report_view

    source = tmp_path / "source.pdf"
    output = tmp_path / "combined.pdf"
    _source(source, pages=5)
    payload = {
        "metadata": {"audit_type": "pdf"},
        "findings": [
            {
                "rule_id": "P045",
                "page": page,
                "severity": "WARNING",
                "details": {
                    "issue_type": "numbered_publication_entry",
                    "suggested_fix": "Remove numbering from this entry.",
                },
            }
            for page in (4, 2)
        ],
    }
    view = build_report_view(payload, pdf_page_sizes=[(600, 790)] * 5)
    findings = [asdict(f) for f in view.findings]
    assert [(f["problem_number"], f["page"]) for f in findings] == [(1, 2), (2, 4)]
    text = render_student_report_text(findings, file_name="thesis.pdf")
    build_combined_student_pdf_report(
        source, output, findings, boxes_by_problem={}, file_name="thesis.pdf"
    )
    with fitz.open(output) as doc:
        pdf_text = _report_text(doc, 5)
    normalized_pdf_text = " ".join(pdf_text.split())
    for finding in findings:
        assert f"Problem #{finding['problem_number']}" in text
        assert f"Problem #{finding['problem_number']}" in pdf_text
        assert finding["polished_comment"] in text
        assert finding["polished_comment"] in normalized_pdf_text
        assert finding["suggested_fix"] in text
        assert finding["suggested_fix"] in normalized_pdf_text
    assert "R045" in text and "R045" in pdf_text


def test_original_annotations_and_very_long_filename_survive(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "combined.pdf"
    with fitz.open() as doc:
        page = doc.new_page(width=612, height=792)
        page.insert_text((80, 100), "Synthetic source text")
        page.insert_link({
            "kind": fitz.LINK_URI,
            "from": fitz.Rect(80, 85, 180, 110),
            "uri": "https://example.org/synthetic",
        })
        note = page.add_text_annot((200, 200), "Original reviewer note")
        note.update()
        doc.save(source)
    finding = _finding(1, 1)
    finding["polished_comment"] = "Unbroken " + "W" * 500
    result = build_combined_student_pdf_report(
        source,
        output,
        [finding],
        boxes_by_problem={1: [(80, 85, 200, 110)]},
        file_name="résumé_" + "x" * 500 + ".pdf",
    )
    with fitz.open(output) as doc:
        assert doc.page_count == 1 + result.report_pages
        assert len(list(doc[0].annots() or [])) == 2
        assert doc[0].get_links()[0]["uri"] == "https://example.org/synthetic"
        assert "Problem #1" in _report_text(doc, 1)


def test_generation_failure_never_exposes_partial_pdf(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "student-report.pdf"
    _source(source, pages=1)
    with patch("njit_auditor.student_pdf_report._report_pdf", side_effect=RuntimeError("layout")):
        with pytest.raises(RuntimeError, match="layout"):
            build_combined_student_pdf_report(
                source,
                output,
                [_finding(1, 1)],
                boxes_by_problem={1: [(80, 85, 180, 110)]},
                file_name="thesis.pdf",
            )
    assert not output.exists()


def test_problem_markers_stay_visible_at_all_page_edges(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "combined.pdf"
    with fitz.open() as document:
        document.new_page(width=612, height=792)
        document.save(source)
    boxes = {
        1: [(0, 0, 25, 20)],
        2: [(0, 770, 25, 792)],
        3: [(587, 300, 612, 320)],
        4: [(0, 300, 25, 320)],
    }
    result = build_combined_student_pdf_report(
        source,
        output,
        [_finding(number, 1) for number in range(1, 5)],
        boxes_by_problem=boxes,
        file_name="edges.pdf",
    )
    assert result.highlight_boxes_drawn == result.markers_drawn == 4
    with fitz.open(output) as document:
        page = document[0]
        markers = [
            span
            for block in page.get_text("dict")["blocks"]
            for line in block.get("lines", [])
            for span in line.get("spans", [])
            if span["text"].startswith("#")
        ]
        assert {span["text"] for span in markers} == {"#1", "#2", "#3", "#4"}
        assert all(page.rect.contains(fitz.Rect(span["bbox"])) for span in markers)
