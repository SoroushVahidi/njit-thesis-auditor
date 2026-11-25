"""A number inside an LoF title cannot supply the absent destination folio."""

from pathlib import Path

import pymupdf
import pytest

from njit_auditor.audit_runner import run_pdf_audit_full
from njit_auditor.pdf_highlight import build_highlighted_single_page_pdf
from njit_auditor.report_outputs import build_audit_report
from njit_auditor.report_view import build_report_view


@pytest.mark.parametrize("terminal_folio", [False, True])
def test_p018_does_not_count_visible_interior_title_number(
    tmp_path: Path, terminal_folio: bool,
) -> None:
    path = tmp_path / "interior-number.pdf"
    with pymupdf.open() as doc:
        doc.new_page(width=612, height=792)
        page = doc.new_page(width=612, height=792)
        page.insert_text((225, 80), "LIST OF FIGURES", fontname="Times-Bold", fontsize=14)
        for index in range(3):
            y = 120 + index * 25
            page.insert_text((108, y), f"2.{index + 1} Reference Control ................")
            page.insert_text((529, y), str(30 + index))
        page.insert_text((108, 196), "3.1 Synthetic measurement")
        page.insert_text((290, 196), "100")
        page.insert_text((325, 196), "units per interval")
        if terminal_folio:
            page.insert_text((529, 196), "100")
        doc.save(path)
    all_findings = run_pdf_audit_full(path)
    findings = [
        f for f in all_findings
        if f.rule_id == "P018" and f.details["issue_type"] == "missing_page_number"
    ]
    if terminal_folio:
        assert not findings
    else:
        missing, = findings
        assert missing.page == 2
        assert missing.details["affected_entry_count"] == "1"
        assert missing.details["worst_entry_index"] == "3"
        assert "Synthetic measurement" in missing.details["affected_entry_preview"]
        box = tuple(map(float, missing.details["bbox"].split(",")))
        x0, y0, x1, y1 = box
        assert x0 == 108 and x1 > 325
        assert y0 < 196 < y1
        report = build_audit_report(all_findings, {"audit_type": "pdf"})
        index, = [
            i for i, item in enumerate(report["findings"])
            if item["rule_id"] == "P018" and item["details"]["issue_type"] == "missing_page_number"
        ]
        assert index == len(report["findings"]) - 1
        card, = [
            f for f in build_report_view(report).findings
            if f.rule_id == "P018" and f.issue_type == "missing_page_number"
        ]
        assert card.finding_id == f"f{index}"
        assert card.page == 2 and card.bbox == box and card.has_highlight
        assert "missing trailing page number" in card.suggested_fix
        result = build_highlighted_single_page_pdf(
            path, tmp_path / "focused.pdf", source_page_number=card.page, boxes=[card.bbox],
        )
        assert result.drawn_count == 1 and result.pages_highlighted == [1]
