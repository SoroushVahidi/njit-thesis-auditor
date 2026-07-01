"""Atomic rule-reference catalog tests for the public /rules page."""

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

_MINIMAL_PDF = b"%PDF-1.4\n%%EOF\n"


def _make_app(tmp_path: Path) -> tuple[TestClient, Any]:
    os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"] = str(tmp_path / "web_audits")
    import importlib

    import njit_auditor.web_app as wa

    importlib.reload(wa)
    return TestClient(wa.app, raise_server_exceptions=False), wa


@pytest.fixture()
def client(tmp_path: Path) -> tuple[TestClient, Any]:
    return _make_app(tmp_path)


def test_rule_reference_catalog_replaces_known_broad_cards(client: tuple[TestClient, Any]) -> None:
    _, wa = client
    catalog = wa._build_rule_catalog()
    visible_ids = {rule["id"] for rule in catalog["student_rules"]}

    assert {"P026A", "P026B"} <= visible_ids
    assert {"P015A", "P015B"} <= visible_ids
    assert {"P014A", "P014B", "P014C", "P014D", "P014E", "P014F"} <= visible_ids
    assert {"P038A", "P038B", "P038C", "P038D", "P038E", "P038F"} <= visible_ids
    assert {"P030A", "P030B", "P030C"} <= visible_ids
    assert {"P032B", "P032C"} <= visible_ids
    assert {f"P018{letter}" for letter in "ABCDEFGHIJKLMNOPQ"} <= visible_ids
    assert {"P043A", "P043B", "P044A", "P044B"} <= visible_ids
    assert {"P024D", "P024E"} <= visible_ids

    assert {
        "P014",
        "P015",
        "P017",
        "P018",
        "P019",
        "P024",
        "P026",
        "P030",
        "P032",
        "P036",
        "P038",
        "P039",
        "P042",
        "P043",
        "P044",
        "P046",
        "P048",
    }.isdisjoint(visible_ids)
    assert {
        "P024A",
        "P024B",
        "P024C",
        "P032A",
        "P036A",
        "P036B",
        "P036C",
        "P042A",
        "P042B",
        "P046A",
        "P046B",
        "P048A",
        "P048B",
    }.isdisjoint(visible_ids)


def test_rule_reference_cards_avoid_known_non_atomic_wording(
    client: tuple[TestClient, Any],
) -> None:
    _, wa = client
    catalog = wa._build_rule_catalog()
    cards = catalog["student_rules"]
    blocked_patterns = (
        "font family and size",
        "sentence case and ending with terminal punctuation",
        "table of contents, list of tables, and list of figures",
        "all-caps, bold, and centered format at the top of the page",
        "first paragraph flush-left, subsequent paragraphs indented",
        "single appendix with a title, multiple appendices each identified by a letter",
        "figure/table",
    )

    for rule in cards:
        rendered = " ".join(
            [
                str(rule.get("title", "")).lower(),
                str(rule.get("how_to_correct", "")).lower(),
            ]
        )
        for pattern in blocked_patterns:
            assert pattern not in rendered, f"{rule['id']} still contains broad wording: {pattern}"


def test_font_split_cards_have_separate_atomic_wording(client: tuple[TestClient, Any]) -> None:
    _, wa = client
    catalog = wa._build_rule_catalog()
    by_id = {rule["id"]: rule for rule in catalog["student_rules"]}

    family = by_id["P026A"]
    size = by_id["P026B"]

    assert "accepted font family or type" in family["title"].lower()
    assert "12pt" not in family["how_to_correct"].lower()
    assert "times new roman" in family["how_to_correct"].lower()
    assert "computer modern" in family["how_to_correct"].lower()

    assert "12pt font size" in size["title"].lower()
    size_fix = size["how_to_correct"].lower()
    assert "times new roman" not in size_fix
    assert "arial" not in size_fix
    assert "computer modern" not in size_fix


def test_public_rule_reference_mapping_splits_indent_issue_types(
    client: tuple[TestClient, Any],
) -> None:
    _, wa = client

    assert wa._public_rule_reference_id(
        "P015",
        issue_type="unexpected_opening_indent",
    ) == "P015A"
    assert wa._public_rule_reference_id(
        "P015",
        issue_type="missing_later_indent",
    ) == "P015B"


def test_public_rule_reference_mapping_splits_frontmatter_indent_issue_types(
    client: tuple[TestClient, Any],
) -> None:
    _, wa = client

    assert wa._public_rule_reference_id(
        "P044",
        issue_type="abstract_first_paragraph_indented",
    ) == "P044A"
    assert wa._public_rule_reference_id(
        "P044",
        issue_type="abstract_subsequent_paragraph_not_indented",
    ) == "P044B"
    assert wa._public_rule_reference_id(
        "P043",
        issue_type="acknowledgements_first_paragraph_indented",
    ) == "P043A"
    assert wa._public_rule_reference_id(
        "P043",
        issue_type="acknowledgements_subsequent_paragraph_not_indented",
    ) == "P043B"


def test_public_rule_reference_mapping_splits_font_issue_types(
    client: tuple[TestClient, Any],
) -> None:
    _, wa = client

    assert wa._public_rule_reference_id(
        "P026",
        issue_type="possible_body_font_family_issue",
    ) == "P026A"
    assert wa._public_rule_reference_id(
        "P026",
        issue_type="possible_body_font_size_issue",
    ) == "P026B"


def test_public_rule_reference_mapping_splits_p024_lof_sentence_case(
    client: tuple[TestClient, Any],
) -> None:
    _, wa = client

    assert wa._public_rule_reference_id(
        "P024",
        issue_type="list_of_figures_sentence_case",
        source_q_rule_id="Q074",
    ) == "P024E"


def test_public_rule_reference_mapping_splits_p018_toc_capitalization(
    client: tuple[TestClient, Any],
) -> None:
    _, wa = client

    assert wa._public_rule_reference_id(
        "P024",
        issue_type="toc_level_capitalization",
        source_q_rule_id="Q049",
        details={"entry_level": "1"},
    ) == "P018A"
    assert wa._public_rule_reference_id(
        "P018",
        issue_type="inconsistent_leader_dots",
        source_q_rule_id="Q052",
    ) == "P018D"


def test_results_font_findings_link_to_split_public_cards(
    client: tuple[TestClient, Any],
) -> None:
    c, wa = client
    findings = [
        AuditFinding(
            rule_id="P026",
            severity=Severity.WARNING,
            page=5,
            message="Family issue.",
            details={
                "issue_type": "possible_body_font_family_issue",
                "expected": "Times New Roman or accepted equivalent",
                "observed_summary": "Georgia",
                "confidence": "medium",
            },
        ),
        AuditFinding(
            rule_id="P026",
            severity=Severity.WARNING,
            page=6,
            message="Size issue.",
            details={
                "issue_type": "possible_body_font_size_issue",
                "expected": "12pt (±1pt tolerance: 11.0–13.0pt)",
                "observed_summary": "11.0pt",
                "confidence": "medium",
            },
        ),
    ]
    job_id = secrets.token_urlsafe(16)
    runtime = Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"])
    jdir = runtime / job_id
    jdir.mkdir(parents=True, exist_ok=True)
    (jdir / "upload.pdf").write_bytes(_MINIMAL_PDF)
    metadata = {"input_file_name": "thesis.pdf", "audit_type": "pdf", "job_id": job_id}
    payload = audit_findings_to_json_dict(findings, metadata)
    (jdir / "report.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_markdown_report(findings, metadata, jdir / "report.md")
    view = build_report_view(payload)

    job = wa.JobState(
        job_id=job_id,
        state="complete",
        created_at=datetime.now(timezone.utc).isoformat(),
        file_name="thesis.pdf",
        audit_type="pdf",
        finding_count=view.total_findings,
        warn_count=2,
        fail_count=0,
        findings=[
            {
                "rule_id": fv.rule_id,
                "severity": fv.severity,
                "page": fv.page,
                "issue_type": fv.issue_type,
                "category": fv.category,
                "polished_comment": fv.polished_comment,
                "suggested_fix": fv.suggested_fix,
                "triage_tier": fv.triage_tier,
                "confidence": fv.confidence,
                "confidence_level": fv.confidence_level,
                "confidence_label": fv.confidence_label,
                "confidence_css_class": fv.confidence_css_class,
                "source_file": fv.source_file,
                "source_line": fv.source_line,
                "location_label": fv.location_label,
            }
            for fv in view.findings
        ],
        grouped_summary=[
            {"rule_id": rs.rule_id, "count": rs.count, "category": rs.category}
            for rs in view.rule_summaries
        ],
        report_view=report_view_to_dict(view),
        md_preview="# Audit\n",
    )
    wa._set_job(job)

    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    body = resp.text
    assert 'href="/rules#P026A"' in body
    assert 'href="/rules#P026B"' in body


def test_results_lof_sentence_case_findings_link_to_p024e_and_use_atomic_fix(
    client: tuple[TestClient, Any],
) -> None:
    c, wa = client
    findings = [
        AuditFinding(
            rule_id="P024",
            severity=Severity.WARNING,
            page=15,
            message="List of Figures entry may not follow sentence-case style.",
            details={
                "issue_type": "list_of_figures_sentence_case",
                "page_type": "list_of_figures",
                "entry_index": "0",
                "line_preview": "Figure 4.1 Relationship between Benefits and Readiness",
                "source_q_rule_id": "Q074",
                "confidence": "medium",
            },
        )
    ]
    job_id = secrets.token_urlsafe(16)
    runtime = Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"])
    jdir = runtime / job_id
    jdir.mkdir(parents=True, exist_ok=True)
    (jdir / "upload.pdf").write_bytes(_MINIMAL_PDF)
    metadata = {"input_file_name": "thesis.pdf", "audit_type": "pdf", "job_id": job_id}
    payload = audit_findings_to_json_dict(findings, metadata)
    (jdir / "report.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_markdown_report(findings, metadata, jdir / "report.md")
    view = build_report_view(payload)

    rendered = next(f for f in view.findings if f.issue_type == "list_of_figures_sentence_case")
    assert rendered.suggested_fix == (
        "Change the List of Figures entry to sentence case. Capitalize only the "
        "first word, proper nouns, and acronyms."
    )
    lower_fix = rendered.suggested_fix.lower()
    for token in ("table of contents", "list of tables", "level 1", "level 2"):
        assert token not in lower_fix

    job = wa.JobState(
        job_id=job_id,
        state="complete",
        created_at=datetime.now(timezone.utc).isoformat(),
        file_name="thesis.pdf",
        audit_type="pdf",
        finding_count=view.total_findings,
        warn_count=1,
        fail_count=0,
        findings=[
            {
                "rule_id": fv.rule_id,
                "severity": fv.severity,
                "page": fv.page,
                "issue_type": fv.issue_type,
                "category": fv.category,
                "polished_comment": fv.polished_comment,
                "suggested_fix": fv.suggested_fix,
                "triage_tier": fv.triage_tier,
                "confidence": fv.confidence,
                "confidence_level": fv.confidence_level,
                "confidence_label": fv.confidence_label,
                "confidence_css_class": fv.confidence_css_class,
                "source_file": fv.source_file,
                "source_line": fv.source_line,
                "location_label": fv.location_label,
            }
            for fv in view.findings
        ],
        grouped_summary=[
            {"rule_id": rs.rule_id, "count": rs.count, "category": rs.category}
            for rs in view.rule_summaries
        ],
        report_view=report_view_to_dict(view),
        md_preview="# Audit\n",
    )
    wa._set_job(job)

    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    body = resp.text
    assert 'href="/rules#P024E"' in body
    assert "Change the List of Figures entry to sentence case." in body


def test_results_p018_leader_findings_link_to_p018d(
    client: tuple[TestClient, Any],
) -> None:
    c, wa = client
    from njit_auditor.models import AuditFinding, Severity

    findings = [
        AuditFinding(
            rule_id="P018",
            severity=Severity.WARNING,
            page=7,
            message="Leader dots inconsistent.",
            details={
                "issue_type": "inconsistent_leader_dots",
                "source_q_rule_id": "Q052",
                "section_type": "table_of_contents",
                "confidence": "medium",
            },
        )
    ]
    job_id = secrets.token_urlsafe(16)
    runtime = Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"])
    jdir = runtime / job_id
    jdir.mkdir(parents=True, exist_ok=True)
    (jdir / "upload.pdf").write_bytes(_MINIMAL_PDF)
    metadata = {"input_file_name": "thesis.pdf", "audit_type": "pdf", "job_id": job_id}
    payload = audit_findings_to_json_dict(findings, metadata)
    (jdir / "report.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_markdown_report(findings, metadata, jdir / "report.md")
    view = build_report_view(payload)

    job = wa.JobState(
        job_id=job_id,
        state="complete",
        created_at=datetime.now(timezone.utc).isoformat(),
        file_name="thesis.pdf",
        audit_type="pdf",
        finding_count=view.total_findings,
        warn_count=1,
        fail_count=0,
        findings=[
            {
                "rule_id": fv.rule_id,
                "public_rule_reference_id": wa._public_rule_reference_id(
                    fv.rule_id,
                    issue_type=fv.issue_type,
                    source_q_rule_id=str(
                        payload["findings"][0].get("details", {}).get("source_q_rule_id", "")
                    ),
                    details=payload["findings"][0].get("details", {}),
                ),
                "severity": fv.severity,
                "page": fv.page,
                "issue_type": fv.issue_type,
                "category": fv.category,
                "polished_comment": fv.polished_comment,
                "suggested_fix": fv.suggested_fix,
                "triage_tier": fv.triage_tier,
                "confidence": fv.confidence,
                "confidence_level": fv.confidence_level,
                "confidence_label": fv.confidence_label,
                "confidence_css_class": fv.confidence_css_class,
                "source_file": fv.source_file,
                "source_line": fv.source_line,
                "location_label": fv.location_label,
            }
            for fv in view.findings
        ],
        grouped_summary=[],
        report_view=report_view_to_dict(view),
        md_preview="# Audit\n",
    )
    wa._set_job(job)

    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    assert 'href="/rules#P018D"' in resp.text


def test_rules_page_renders_split_font_cards_not_combined_p026(
    client: tuple[TestClient, Any],
) -> None:
    c, _ = client
    resp = c.get("/rules")
    body = resp.text

    assert 'data-rule-id="P026A"' in body
    assert 'data-rule-id="P026B"' in body
    assert 'data-rule-id="P026"' not in body
    assert "Does the body text use Times New Roman 12pt" not in body
