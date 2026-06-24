"""Tests for warning-actionability quick wins (synthetic metadata only)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.polished_comments import (
    GLOBAL_AUTOMATED_REVIEW_NOTE,
    VERIFY_SUFFIX,
    build_polished_comment,
)
from njit_auditor.report_outputs import (
    audit_findings_to_json_dict,
    write_markdown_report,
)
from njit_auditor.report_view import build_report_view, enriched_pdf_location_label


def _payload(findings: list[AuditFinding]) -> dict[str, Any]:
    return audit_findings_to_json_dict(findings, {"audit_type": "pdf"})


def test_grouped_card_surfaces_suggested_fix_for_p018() -> None:
    findings = [
        AuditFinding(
            rule_id="P018",
            severity=Severity.WARNING,
            page=12,
            message="missing page number",
            details={
                "issue_type": "missing_page_number",
                "page_type": "table_of_contents",
                "confidence": "medium",
            },
        )
    ]
    view = build_report_view(_payload(findings))
    card = view.grouped_problems[0]
    assert card.suggested_fix
    assert card.suggested_fix not in card.polished_comment


def test_grouped_card_surfaces_suggested_fix_for_p036() -> None:
    findings = [
        AuditFinding(
            rule_id="P036",
            severity=Severity.WARNING,
            page=12,
            message="spacing",
            details={
                "issue_type": "toc_inter_entry_spacing_too_tight",
                "section_type": "table_of_contents",
                "entry_pair_index": "2",
                "gap_points": "4.0",
                "required_gap_points": "8.0",
                "confidence": "medium",
            },
        )
    ]
    view = build_report_view(_payload(findings))
    card = view.grouped_problems[0]
    assert card.suggested_fix
    assert "Increase the spacing" not in card.polished_comment or card.suggested_fix


def test_grouped_card_surfaces_suggested_fix_for_p040() -> None:
    findings = [
        AuditFinding(
            rule_id="P040",
            severity=Severity.WARNING,
            page=15,
            message="punctuation",
            details={
                "issue_type": "lof_entry_missing_terminal_punctuation",
                "entry_index": "1",
                "confidence": "high",
            },
        )
    ]
    view = build_report_view(_payload(findings))
    card = view.grouped_problems[0]
    assert card.suggested_fix
    assert VERIFY_SUFFIX not in card.polished_comment


def test_grouped_card_surfaces_suggested_fix_for_p033_and_p051() -> None:
    for rule_id, issue_type, page in (
        ("P033", "frontmatter_title_mismatch", 2),
        ("P051", "copyright_year_not_found", 4),
    ):
        findings = [
            AuditFinding(
                rule_id=rule_id,
                severity=Severity.WARNING,
                page=page,
                message="issue",
                details={
                    "issue_type": issue_type,
                    "confidence": "high",
                    "reference_page_role": "title",
                    "copyright_marker_detected": "true",
                },
            )
        ]
        view = build_report_view(_payload(findings))
        card = view.grouped_problems[0]
        assert card.suggested_fix
        assert VERIFY_SUFFIX not in card.polished_comment


def test_p020_comment_and_fix_are_not_duplicated_on_card() -> None:
    findings = [
        AuditFinding(
            rule_id="P020",
            severity=Severity.WARNING,
            page=3,
            message="title case",
            details={
                "issue_type": "possible_title_capitalization_issue",
                "flagged_word": "Alpha",
                "corrected_word": "ALPHA",
                "confidence": "medium",
            },
        )
    ]
    view = build_report_view(_payload(findings))
    card = view.grouped_problems[0]
    assert card.suggested_fix
    assert card.suggested_fix not in card.polished_comment


def test_markdown_has_global_caveat_not_per_line_verify_suffix(tmp_path: Path) -> None:
    findings = [
        AuditFinding(
            rule_id="P999",
            severity=Severity.WARNING,
            page=1,
            message="generic",
            details={"issue_type": "totally_unmapped_issue_type"},
        )
    ]
    md_path = tmp_path / "report.md"
    write_markdown_report(findings, {"audit_type": "pdf"}, md_path)
    text = md_path.read_text(encoding="utf-8")
    assert GLOBAL_AUTOMATED_REVIEW_NOTE in text
    assert VERIFY_SUFFIX not in text


def test_confidence_not_embedded_in_polished_comment() -> None:
    comment = build_polished_comment(
        rule_id="P011",
        issue_type="margin_boundary_violation",
        page=2,
        details={"side": "left_margin", "confidence": "medium"},
    )
    assert "Confidence:" not in comment


def test_enriched_location_uses_entry_index() -> None:
    label = enriched_pdf_location_label(
        "P040",
        "lof_entry_missing_terminal_punctuation",
        {"entry_index": "1", "page_type": "list_of_figures"},
        15,
    )
    assert label == "Page 15 — List of Figures entry 2"


def test_enriched_location_uses_section_type_for_p018() -> None:
    label = enriched_pdf_location_label(
        "P018",
        "missing_page_number",
        {"page_type": "list_of_tables"},
        14,
    )
    assert label == "Page 14 — List of Tables"


def test_enriched_location_uses_worst_entry_index_for_p018() -> None:
    label = enriched_pdf_location_label(
        "P018",
        "misaligned_page_number_column",
        {
            "page_type": "table_of_contents",
            "worst_entry_index": "3",
            "affected_entry_count": "2",
        },
        12,
    )
    assert label == "Page 12 — Table of Contents, worst affected entry 4"


def test_enriched_location_uses_affected_entry_preview_for_p018() -> None:
    label = enriched_pdf_location_label(
        "P018",
        "misaligned_page_number_column",
        {
            "page_type": "table_of_contents",
            "worst_entry_index": "3",
            "affected_entry_count": "2",
            "affected_entry_preview": "Chapter 3 Methodology Overview",
        },
        12,
    )
    assert label == "Page 12 — Table of Contents, affected entry: 'Chapter 3 Methodology Overview'"


def test_enriched_location_uses_affected_count_for_p018_without_worst_entry() -> None:
    label = enriched_pdf_location_label(
        "P018",
        "missing_page_number",
        {"page_type": "list_of_tables", "affected_entry_count": "3"},
        14,
    )
    assert label == "Page 14 — List of Tables, 3 affected entries"


def test_enriched_location_uses_entry_index_for_p046() -> None:
    label = enriched_pdf_location_label(
        "P046",
        "lot_entry_number_column_misaligned",
        {"section_type": "list_of_tables", "entry_index": "1"},
        15,
    )
    assert label == "Page 15 — List of Tables entry 2"


def test_enriched_location_uses_affected_entry_preview_for_p046() -> None:
    label = enriched_pdf_location_label(
        "P046",
        "lot_entry_number_column_misaligned",
        {
            "section_type": "list_of_tables",
            "entry_index": "1",
            "affected_entry_preview": "Table 2 Synthetic model performance",
        },
        15,
    )
    assert (
        label == "Page 15 — List of Tables, affected entry: 'Table 2 Synthetic model performance'"
    )


def test_enriched_location_uses_affected_count_for_p046_without_entry_index() -> None:
    label = enriched_pdf_location_label(
        "P046",
        "lof_entry_number_column_misaligned",
        {"section_type": "list_of_figures", "affected_entry_count": "1"},
        20,
    )
    assert label == "Page 20 — List of Figures, 1 affected entry"


def test_enriched_location_uses_pair_index_for_p036() -> None:
    label = enriched_pdf_location_label(
        "P036",
        "toc_inter_entry_spacing_too_tight",
        {"section_type": "table_of_contents", "entry_pair_index": "2"},
        12,
    )
    assert label == "Page 12 — Table of Contents, spacing between entries 3-4"


def test_enriched_location_uses_entry_previews_for_p036() -> None:
    label = enriched_pdf_location_label(
        "P036",
        "toc_inter_entry_spacing_too_tight",
        {
            "section_type": "table_of_contents",
            "entry_pair_index": "2",
            "previous_entry_preview": "Chapter 1 Introduction",
            "next_entry_preview": "Chapter 2 Background",
        },
        12,
    )
    assert label == (
        "Page 12 — Table of Contents, between 'Chapter 1 Introduction' and 'Chapter 2 Background'"
    )


def test_enriched_location_falls_back_when_no_metadata() -> None:
    label = enriched_pdf_location_label("P019", "wrong_page_number_sequence", {}, 9)
    assert label == ""


@pytest.fixture()
def web_client(tmp_path: Path) -> tuple[TestClient, Any]:
    import importlib
    import os

    os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"] = str(tmp_path / "web_audits")
    import njit_auditor.web_app as wa

    importlib.reload(wa)
    return TestClient(wa.app, raise_server_exceptions=False), wa


def test_results_page_shows_confidence_badge_not_prose(
    web_client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    import os
    import secrets
    from datetime import datetime, timezone

    from njit_auditor.report_view import build_report_view, report_view_to_dict

    c, wa = web_client
    findings = [
        AuditFinding(
            rule_id="P018",
            severity=Severity.WARNING,
            page=12,
            message="missing page number",
            details={
                "issue_type": "missing_page_number",
                "page_type": "table_of_contents",
                "confidence": "medium",
            },
        )
    ]
    payload = audit_findings_to_json_dict(findings, {"audit_type": "pdf"})
    view = build_report_view(payload)
    view_dict = report_view_to_dict(view)
    job_id = secrets.token_urlsafe(12)
    jdir = Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"]) / job_id
    jdir.mkdir(parents=True)
    (jdir / "upload.pdf").write_bytes(b"%PDF-1.4\n%%EOF\n")
    (jdir / "report.json").write_text(json.dumps(payload), encoding="utf-8")
    wa._set_job(
        wa.JobState(
            job_id=job_id,
            state="complete",
            created_at=datetime.now(timezone.utc).isoformat(),
            file_name="sample.pdf",
            audit_type="pdf",
            finding_count=view.total_findings,
            warn_count=1,
            fail_count=0,
            findings=list(view_dict.get("findings", [])),
            grouped_summary=[],
            report_view=view_dict,
            md_preview="# Audit Report\n",
        )
    )
    html = c.get(f"/audits/{job_id}").text
    assert "confidence-badge" in html
    assert "Medium confidence" in html
    assert "Confidence: medium" not in html
    assert "Suggested fix:" in html
