"""Tests for high-volume warning group clarity (synthetic findings only).

Covers the "why does this repeat" framing added to grouped cards (job.html),
the same framing extended to the per-rule/per-issue-type drill-down page
(problem_group.html), the Markdown "Why this repeats" line, and the new
P019/P036 "Most common issues" triage panels.
"""

from __future__ import annotations

import json
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from njit_auditor.models import AuditFinding, Severity
from njit_auditor.report_outputs import audit_findings_to_json_dict, write_markdown_report
from njit_auditor.report_view import build_report_view, report_view_to_dict


def _payload(findings: list[AuditFinding]) -> dict[str, Any]:
    return audit_findings_to_json_dict(findings, {"audit_type": "pdf"})


def _p036_spacing_findings(count: int) -> list[AuditFinding]:
    return [
        AuditFinding(
            rule_id="P036",
            severity=Severity.WARNING,
            page=5 + i,
            message="spacing",
            details={
                "issue_type": "toc_inter_entry_spacing_too_tight",
                "section_type": "table_of_contents",
                "entry_pair_index": str(i),
                "gap_points": "4.0",
                "required_gap_points": "8.0",
                "confidence": "medium",
            },
        )
        for i in range(count)
    ]


def _p020_title_case_findings(count: int) -> list[AuditFinding]:
    words = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Eta", "Theta"]
    return [
        AuditFinding(
            rule_id="P020",
            severity=Severity.WARNING,
            page=3 + i,
            message="title case",
            details={
                "issue_type": "possible_title_capitalization_issue",
                "flagged_word": words[i % len(words)],
                "corrected_word": words[i % len(words)].upper(),
                "confidence": "medium",
            },
        )
        for i in range(count)
    ]


def _p026_family_findings(count: int) -> list[AuditFinding]:
    return [
        AuditFinding(
            rule_id="P026",
            severity=Severity.WARNING,
            page=10 + i,
            message="font family",
            details={
                "issue_type": "possible_body_font_family_issue",
                "observed_summary": "non-standard body font detected",
                "confidence": "low",
            },
        )
        for i in range(count)
    ]


def _p012_annotation_findings(count: int) -> list[AuditFinding]:
    return [
        AuditFinding(
            rule_id="P012",
            severity=Severity.WARNING,
            page=1 + i,
            message="annotation",
            details={
                "issue_type": "pdf_annotation_detected",
                "annotation_type": "highlight",
                "confidence": "high",
            },
        )
        for i in range(count)
    ]


def _p019_missing_number_findings(count: int) -> list[AuditFinding]:
    return [
        AuditFinding(
            rule_id="P019",
            severity=Severity.WARNING,
            page=20 + i,
            message="missing page number",
            details={
                "issue_type": "missing_page_number",
                "triage_tier": "high",
                "p019_triage_category": "high_signal_missing_page_number",
                "confidence": "medium",
            },
        )
        for i in range(count)
    ]


def _p011_margin_findings(count: int) -> list[AuditFinding]:
    return [
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=40 + i,
            message="Possible text crossing right margin.",
            details={
                "side": "right",
                "issue_type": "margin_boundary_violation",
                "worst_overflow_pt": "6.0",
                "affected_line_count": "2",
                "confidence": "medium",
                "triage_tier": "informational",
            },
        )
        for i in range(count)
    ]


_FORBIDDEN_INTERNAL_WORDS = (
    "detector",
    "grouping key",
    "bbox",
    "raw metadata",
    "cluster",
    "canonical issue",
)


def _assert_no_internal_jargon(text: str) -> None:
    lowered = text.lower()
    for word in _FORBIDDEN_INTERNAL_WORDS:
        assert word not in lowered, f"internal term {word!r} leaked into student-facing text"


# ---- Grouped card pattern_note (job.html) ----


def test_p036_grouped_card_pattern_note_explains_repeated_spacing() -> None:
    findings = _p036_spacing_findings(6)
    view = build_report_view(_payload(findings))
    card = view.grouped_problems[0]
    assert card.occurrence_count == 6
    assert "6 times" in card.pattern_note
    assert "Table of Contents" in card.pattern_note
    assert "same formatting issue repeated" in card.pattern_note
    assert card.suggested_fix
    assert card.confidence_label
    _assert_no_internal_jargon(card.pattern_note)


def test_p036_single_occurrence_has_no_pattern_note() -> None:
    findings = _p036_spacing_findings(1)
    view = build_report_view(_payload(findings))
    card = view.grouped_problems[0]
    assert card.occurrence_count == 1
    assert card.pattern_note == ""


def test_p020_grouped_card_pattern_note_explains_repeated_words() -> None:
    findings = _p020_title_case_findings(5)
    view = build_report_view(_payload(findings))
    card = view.grouped_problems[0]
    assert card.occurrence_count == 5
    assert "5 times" in card.pattern_note
    assert "different word" in card.pattern_note
    assert "Show individual occurrences" in card.pattern_note
    for word in ("Alpha", "Beta", "Gamma", "Delta", "Epsilon"):
        assert word not in card.pattern_note
    _assert_no_internal_jargon(card.pattern_note)


def test_p020_grouped_card_pattern_note_explains_confidence_band_split() -> None:
    findings = _p020_title_case_findings(5)
    view = build_report_view(_payload(findings))
    card = view.grouped_problems[0]
    assert "same capitalization reason and confidence" in card.pattern_note
    assert "not a duplicate" in card.pattern_note
    _assert_no_internal_jargon(card.pattern_note)


def test_p026_grouped_card_pattern_note_does_not_overstate_certainty() -> None:
    findings = _p026_family_findings(4)
    view = build_report_view(_payload(findings))
    card = view.grouped_problems[0]
    assert card.occurrence_count == 4
    assert "4 times" in card.pattern_note
    assert "body-text font pattern" in card.pattern_note
    assert "Times New Roman 12pt" in card.pattern_note
    _assert_no_internal_jargon(card.pattern_note)


def test_p012_grouped_card_pattern_note_does_not_expose_annotation_contents() -> None:
    findings = _p012_annotation_findings(7)
    view = build_report_view(_payload(findings))
    card = view.grouped_problems[0]
    assert card.occurrence_count == 7
    assert "7 times" in card.pattern_note
    assert "embedded annotations or comments" in card.pattern_note
    assert "Remove or flatten reviewer markup" in card.pattern_note
    # Only the generic remediation wording is present, never an annotation's
    # actual text/author/content.
    assert "wrote" not in card.pattern_note.lower()
    assert "said" not in card.pattern_note.lower()
    _assert_no_internal_jargon(card.pattern_note)


def test_p019_grouped_card_pattern_note_explains_document_pattern() -> None:
    findings = _p019_missing_number_findings(4)
    view = build_report_view(_payload(findings))
    card = view.grouped_problems[0]
    assert card.occurrence_count == 4
    assert "4 times" in card.pattern_note
    assert "one document-level numbering pattern" in card.pattern_note
    _assert_no_internal_jargon(card.pattern_note)


def test_p019_grouped_card_pattern_note_fires_for_remapped_visible_issue_type() -> None:
    """report_view.py remaps raw P019 issue types to student-facing ones for HTML

    (e.g. raw "multiple_page_numbers" -> visible "duplicate_or_ambiguous_page_number",
    see _classify_visible_page_number_issue). A grouped card's issue_type is the
    already-remapped value, so the pattern note must recognize it too, not just
    the raw rule-internal string.
    """
    findings = [
        AuditFinding(
            rule_id="P019",
            severity=Severity.WARNING,
            page=30 + i,
            message="multiple page numbers",
            details={
                "issue_type": "multiple_page_numbers",
                "triage_tier": "medium",
                "p019_triage_category": "multiple_page_numbers_manual_review",
                "confidence": "medium",
            },
        )
        for i in range(5)
    ]
    view = build_report_view(_payload(findings))
    card = view.grouped_problems[0]
    assert card.issue_type == "duplicate_or_ambiguous_page_number"
    assert card.occurrence_count == 5
    assert "5 times" in card.pattern_note
    assert "one document-level numbering pattern" in card.pattern_note
    _assert_no_internal_jargon(card.pattern_note)


def test_p011_grouped_card_pattern_note_explains_repeated_margin_violations() -> None:
    findings = _p011_margin_findings(5)
    view = build_report_view(_payload(findings))
    card = view.grouped_problems[0]
    assert card.occurrence_count == 5
    assert "5 times" in card.pattern_note
    assert "combined page-level card" in card.pattern_note
    assert "page margins" in card.pattern_note
    _assert_no_internal_jargon(card.pattern_note)


def test_p011_single_occurrence_has_no_pattern_note() -> None:
    findings = _p011_margin_findings(1)
    view = build_report_view(_payload(findings))
    card = view.grouped_problems[0]
    assert card.occurrence_count == 1
    assert card.pattern_note == ""


# ---- Markdown "Why this repeats" line ----


def test_markdown_includes_why_this_repeats_line_for_p036(tmp_path: Path) -> None:
    findings = _p036_spacing_findings(6)
    md_path = tmp_path / "report.md"
    write_markdown_report(findings, {"audit_type": "pdf"}, md_path)
    text = md_path.read_text(encoding="utf-8")
    assert "Why this repeats:" in text
    assert "Table of Contents" in text


def test_markdown_omits_why_this_repeats_line_for_single_occurrence(tmp_path: Path) -> None:
    findings = _p036_spacing_findings(1)
    md_path = tmp_path / "report.md"
    write_markdown_report(findings, {"audit_type": "pdf"}, md_path)
    text = md_path.read_text(encoding="utf-8")
    assert "Why this repeats:" not in text


# ---- "Most common issues" triage panels for P019/P036 ----


def test_report_view_includes_p019_triage_panel() -> None:
    findings = _p019_missing_number_findings(3)
    view = build_report_view(_payload(findings))
    panel = next(p for p in view.triage_panels if p.rule_id == "P019")
    assert panel.raw_finding_count == 3
    assert panel.affected_pages_compact
    assert panel.triage_note


def test_report_view_includes_p036_triage_panel() -> None:
    findings = _p036_spacing_findings(6)
    view = build_report_view(_payload(findings))
    panel = next(p for p in view.triage_panels if p.rule_id == "P036")
    assert panel.raw_finding_count == 6
    assert panel.affected_pages_compact
    assert panel.triage_note


def test_triage_panels_absent_when_no_matching_findings() -> None:
    findings = _p026_family_findings(2)
    view = build_report_view(_payload(findings))
    rule_ids = {p.rule_id for p in view.triage_panels}
    assert "P019" not in rule_ids
    assert "P036" not in rule_ids


# ---- Secondary drill-down page (problem_group.html) ----


@pytest.fixture()
def web_client(tmp_path: Path) -> tuple[TestClient, Any]:
    import importlib

    os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"] = str(tmp_path / "web_audits")
    import njit_auditor.web_app as wa

    importlib.reload(wa)
    return TestClient(wa.app, raise_server_exceptions=False), wa


def _set_up_job(wa: Any, findings: list[AuditFinding]) -> str:
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
            warn_count=len(findings),
            fail_count=0,
            findings=list(view_dict.get("findings", [])),
            grouped_summary=[],
            report_view=view_dict,
            md_preview="# Audit Report\n",
        )
    )
    return job_id


def test_rule_problem_page_shows_pattern_note_for_high_volume_p036(
    web_client: tuple[TestClient, Any],
) -> None:
    c, wa = web_client
    findings = _p036_spacing_findings(6)
    job_id = _set_up_job(wa, findings)
    html = c.get(f"/audits/{job_id}/problems/rule/P036").text
    assert "6 examples" in html
    assert "same formatting issue repeated" in html
    assert "What to check:" in html


def test_issue_type_problem_page_shows_pattern_note_for_high_volume_p012(
    web_client: tuple[TestClient, Any],
) -> None:
    c, wa = web_client
    findings = _p012_annotation_findings(5)
    job_id = _set_up_job(wa, findings)
    html = c.get(
        f"/audits/{job_id}/problems/rule/P012/issue-type/pdf-annotation-detected"
    ).text
    assert "embedded annotations or comments" in html
    assert "Remove or flatten reviewer markup" in html


def test_rule_problem_page_omits_pattern_note_when_mixed_issue_types(
    web_client: tuple[TestClient, Any],
) -> None:
    c, wa = web_client
    findings = _p019_missing_number_findings(2) + [
        AuditFinding(
            rule_id="P019",
            severity=Severity.WARNING,
            page=99,
            message="sequence gap",
            details={
                "issue_type": "sequence_gap",
                "triage_tier": "high",
                "p019_triage_category": "high_signal_sequence_gap",
                "observed_sequence": "12",
                "expected_sequence": "13",
                "confidence": "medium",
            },
        )
    ]
    job_id = _set_up_job(wa, findings)
    html = c.get(f"/audits/{job_id}/problems/rule/P019").text
    assert '<p class="problem-group-pattern-note">' not in html
