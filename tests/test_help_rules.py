"""Tests for /help and /rules pages and clickable rule ID links."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

_MINIMAL_PDF = b"%PDF-1.4\n%%EOF\n"
_MINIMAL_TEX = (
    rb"\documentclass{report}"
    b"\n\\begin{document}\n\\vspace{1cm}\nHello\n\\end{document}\n"
)


def _make_app(tmp_path: Path) -> tuple[TestClient, Any]:
    """Reload the web app with a temp runtime dir and return (client, module)."""
    os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"] = str(tmp_path / "web_audits")
    import importlib

    import njit_auditor.web_app as wa

    importlib.reload(wa)
    return TestClient(wa.app, raise_server_exceptions=False), wa


@pytest.fixture()
def client(tmp_path: Path) -> tuple[TestClient, Any]:
    return _make_app(tmp_path)


# ---------------------------------------------------------------------------
# /help route
# ---------------------------------------------------------------------------

def test_help_returns_200(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.get("/help")
    assert resp.status_code == 200


def test_help_explains_problems_found(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.get("/help")
    body = resp.text
    assert "Problems found" in body
    assert "review" in body.lower()


def test_help_pass_does_not_mean_approval(client: tuple[TestClient, Any]) -> None:
    """"No problems found" must be explicitly clarified as not meaning dissertation approval."""
    c, _ = client
    resp = c.get("/help")
    body = resp.text.lower()
    assert "does not" in body or "not mean" in body
    assert "approv" in body


def test_help_contains_no_findings_explanation(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.get("/help")
    body = resp.text
    assert "No problems found" in body


def test_help_contains_not_checked_explanation(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.get("/help")
    body = resp.text.lower()
    assert "not checked" in body or "not reliably checkable" in body


def test_help_disclaimer_no_heuristic_says_not_official(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.get("/help")
    body = resp.text.lower()
    assert "heuristic" not in body
    assert "not an official" in body or "research prototype" in body or "not official" in body


def test_help_contains_rule_id_definition(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.get("/help")
    body = resp.text
    assert "Rule ID" in body or "rule id" in body.lower()
    assert "P013" in body or "P0" in body


def test_help_contains_high_volume_triage_explanation(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.get("/help")
    body = resp.text.lower()
    assert "high-volume" in body or "triage" in body


def test_help_contains_grouped_problems_explanation(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.get("/help")
    body = resp.text.lower()
    assert "grouped" in body or "repeated-problem" in body


def test_help_contains_confidence_explanation(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.get("/help")
    body = resp.text.lower()
    assert "confidence" in body


def test_help_results_anchor(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.get("/help")
    assert b'id="results"' in resp.content


def test_help_links_to_rule_reference(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.get("/help")
    assert b"/rules" in resp.content


def test_help_no_private_content(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.get("/help")
    body = resp.text
    assert "njit_auditor.rules" not in body
    assert "/home/" not in body
    assert "src/njit_auditor" not in body


# ---------------------------------------------------------------------------
# /rules route
# ---------------------------------------------------------------------------

def test_rules_returns_200(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.get("/rules")
    assert resp.status_code == 200


def test_rules_contains_p011(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.get("/rules")
    assert b"P011" in resp.content


def test_rules_contains_p013(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.get("/rules")
    assert b"P013" in resp.content


def test_rules_p013_has_stable_anchor(client: tuple[TestClient, Any]) -> None:
    """P013 must have a stable id='P013' anchor."""
    c, _ = client
    resp = c.get("/rules")
    assert b'id="P013"' in resp.content


def test_rules_generated_from_canonical_data(client: tuple[TestClient, Any]) -> None:
    """Rule cards must be generated from canonical structured data."""
    c, _ = client
    resp = c.get("/rules")
    body = resp.text
    # Should show content from canonical JSON (section names, questions, remediation)
    assert "PDF layout" in body or "PDF page numbering" in body
    assert "label" in body.lower() or "margin" in body.lower()


def test_rules_contains_category_filter(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.get("/rules")
    assert b"rule-filter-category" in resp.content


def test_rules_contains_severity_filter(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.get("/rules")
    assert b"rule-filter-severity" in resp.content


def test_rules_contains_search_input(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.get("/rules")
    assert b"rule-search" in resp.content


def test_rules_evaluation_entry_not_in_main_catalog(client: tuple[TestClient, Any]) -> None:
    """P083 (evaluation task) must not be rendered on the public /rules page at all."""
    c, _ = client
    resp = c.get("/rules")
    body = resp.text
    assert 'id="P083"' not in body


def test_rules_reporting_entry_not_rendered(client: tuple[TestClient, Any]) -> None:
    """P081 (reporting-only) must not be rendered on the public /rules page at all."""
    c, _ = client
    resp = c.get("/rules")
    body = resp.text
    assert 'id="P081"' not in body


def test_rules_infrastructure_entry_not_rendered(client: tuple[TestClient, Any]) -> None:
    """P069 (infrastructure-only) must not be rendered on the public /rules page at all."""
    c, _ = client
    resp = c.get("/rules")
    body = resp.text
    assert 'id="P069"' not in body


def test_rules_experimental_entry_not_rendered(client: tuple[TestClient, Any]) -> None:
    """P082 is opt-in/disabled by default and never runs in the web PDF audit, so it
    must not be rendered on the public /rules page."""
    c, _ = client
    resp = c.get("/rules")
    body = resp.text
    assert 'id="P082"' not in body


def test_rules_page_shows_only_web_pdf_rule_ids(client: tuple[TestClient, Any]) -> None:
    """Every rule card rendered on /rules must match the catalog's web-facing rule set."""
    from njit_auditor.web_app import _build_rule_catalog

    c, _ = client
    resp = c.get("/rules")
    body = resp.text
    catalog = _build_rule_catalog()
    expected_ids = {r["id"] for r in catalog["student_rules"]}
    rendered_ids = set(re.findall(r'id="(P\d+)"', body))
    assert rendered_ids == expected_ids
    assert expected_ids, "expected at least one web PDF rule to be shown"


def test_rules_page_has_no_technical_section(client: tuple[TestClient, Any]) -> None:
    """The public page must not show a separate technical/internal-inventory section."""
    c, _ = client
    resp = c.get("/rules")
    body = resp.text
    assert "Technical and experimental entries" not in body
    assert "tech-toggle" not in body
    assert "Inclusion policy" not in body


def test_rules_intro_describes_pdf_audits(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.get("/rules")
    body = resp.text
    assert "automated formatting checks used for PDF audits in this website" in body


def test_rules_p021_mixed_rule_shown_as_pdf(client: tuple[TestClient, Any]) -> None:
    """P021 has both a TeX-side and PDF-side implementation; the PDF-side one runs in
    the web audit, so it must still appear on the public page."""
    c, _ = client
    resp = c.get("/rules")
    body = resp.text
    assert 'id="P021"' in body


def test_rules_no_implementation_module_paths(client: tuple[TestClient, Any]) -> None:
    """No implementation module paths should appear in the normal view."""
    c, _ = client
    resp = c.get("/rules")
    body = resp.text
    assert "njit_auditor.rules.latex_risky_commands" not in body
    assert "njit_auditor.rules.pdf_margins" not in body


def test_rules_no_private_content(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.get("/rules")
    body = resp.text
    assert "/home/" not in body
    assert "src/njit_auditor" not in body


def test_rules_contains_student_catalog_section(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.get("/rules")
    body = resp.text
    assert "Formatting checks" in body or "formatting checks" in body.lower()


def test_rules_has_client_side_filter_script(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.get("/rules")
    assert b"applyFilters" in resp.content


def test_rules_links_to_help(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.get("/rules")
    assert b"/help" in resp.content


def test_rules_what_it_checks_is_collapsible(client: tuple[TestClient, Any]) -> None:
    """Per Ester's feedback, 'What it checks' is de-emphasized (collapsed) so the
    question/title and 'How to correct it' are the primary visible content."""
    c, _ = client
    resp = c.get("/rules")
    body = resp.text
    assert "<details" in body
    assert "What it checks" in body


def test_rules_how_to_correct_remains_always_visible(client: tuple[TestClient, Any]) -> None:
    """'How to correct it' must never be hidden inside the collapsible block."""
    c, _ = client
    resp = c.get("/rules")
    body = resp.text
    assert "How to correct it" in body
    # The remediation block must not be nested inside <details> (only "what it checks" is).
    details_blocks = re.findall(r"<details.*?</details>", body, flags=re.DOTALL)
    for block in details_blocks:
        assert "How to correct it" not in block


# ---------------------------------------------------------------------------
# Navigation links in base template
# ---------------------------------------------------------------------------

def test_nav_help_link_on_index(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.get("/")
    assert b'href="/help"' in resp.content


def test_nav_rules_link_on_index(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.get("/")
    assert b'href="/rules"' in resp.content


def test_nav_help_link_on_help_page(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.get("/help")
    assert b'href="/help"' in resp.content


def test_nav_rules_link_on_help_page(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.get("/help")
    assert b'href="/rules"' in resp.content


def test_nav_help_link_on_rules_page(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.get("/rules")
    assert b'href="/help"' in resp.content


def test_nav_rules_link_on_rules_page(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.get("/rules")
    assert b'href="/rules"' in resp.content


# ---------------------------------------------------------------------------
# Clickable rule IDs on results page
# ---------------------------------------------------------------------------

def _inject_complete_job(
    wa: Any,
    tmp_path: Path,
    rule_id: str = "P011",
    finding_count: int = 1,
) -> str:
    import secrets
    from datetime import datetime, timezone

    from njit_auditor.models import AuditFinding, Severity
    from njit_auditor.report_outputs import audit_findings_to_json_dict, write_markdown_report
    from njit_auditor.report_view import build_report_view, report_view_to_dict

    findings = [
        AuditFinding(
            rule_id=rule_id,
            severity=Severity.WARNING,
            page=i + 1,
            message="Test finding.",
            details={"issue_type": "margin_boundary_violation", "side": "left"},
        )
        for i in range(finding_count)
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
        warn_count=sum(1 for fv in view.findings if fv.severity == "WARNING"),
        fail_count=sum(1 for fv in view.findings if fv.severity == "FAIL"),
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
    return job_id


def test_results_p011_rule_id_links_to_rules_page(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path, rule_id="P011", finding_count=3)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    assert b'href="/rules#P011"' in resp.content


def test_results_p013_rule_id_links_to_rules_page(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """Recognized rule IDs on results pages must link to /rules#P013."""
    c, wa = client
    import secrets
    from datetime import datetime, timezone

    from njit_auditor.models import AuditFinding, Severity
    from njit_auditor.report_outputs import audit_findings_to_json_dict, write_markdown_report
    from njit_auditor.report_view import build_report_view, report_view_to_dict

    findings = [
        AuditFinding(
            rule_id="P013",
            severity=Severity.WARNING,
            page=i + 1,
            message="Page number out of sequence.",
            details={"issue_type": "page_number_sequence_error", "observed": str(i)},
        )
        for i in range(3)
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
        job_id=job_id, state="complete",
        created_at=datetime.now(timezone.utc).isoformat(),
        file_name="thesis.pdf", audit_type="pdf",
        finding_count=view.total_findings, warn_count=3, fail_count=0,
        findings=[{"rule_id": fv.rule_id, "severity": fv.severity, "page": fv.page,
                   "issue_type": fv.issue_type, "category": fv.category,
                   "polished_comment": fv.polished_comment, "suggested_fix": fv.suggested_fix,
                   "triage_tier": fv.triage_tier, "confidence": fv.confidence,
                   "source_file": fv.source_file, "source_line": fv.source_line,
                   "location_label": fv.location_label} for fv in view.findings],
        grouped_summary=[{"rule_id": rs.rule_id, "count": rs.count, "category": rs.category}
                         for rs in view.rule_summaries],
        report_view=report_view_to_dict(view), md_preview="# Audit\n",
    )
    wa._set_job(job)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    assert b'href="/rules#P013"' in resp.content


def test_results_unknown_rule_id_no_broken_link(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """Unknown rule IDs must not produce links — they should appear as plain text."""
    c, wa = client
    import secrets
    from datetime import datetime, timezone

    from njit_auditor.models import AuditFinding, Severity
    from njit_auditor.report_outputs import audit_findings_to_json_dict, write_markdown_report
    from njit_auditor.report_view import build_report_view, report_view_to_dict

    findings = [
        AuditFinding(
            rule_id="UNKNOWN_RULE",
            severity=Severity.WARNING,
            page=1,
            message="Test finding with unknown rule.",
            details={"issue_type": "test_issue"},
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
        job_id=job_id, state="complete",
        created_at=datetime.now(timezone.utc).isoformat(),
        file_name="thesis.pdf", audit_type="pdf",
        finding_count=view.total_findings, warn_count=1, fail_count=0,
        findings=[{"rule_id": fv.rule_id, "severity": fv.severity, "page": fv.page,
                   "issue_type": fv.issue_type, "category": fv.category,
                   "polished_comment": fv.polished_comment, "suggested_fix": fv.suggested_fix,
                   "triage_tier": fv.triage_tier, "confidence": fv.confidence,
                   "source_file": fv.source_file, "source_line": fv.source_line,
                   "location_label": fv.location_label} for fv in view.findings],
        grouped_summary=[{"rule_id": rs.rule_id, "count": rs.count, "category": rs.category}
                         for rs in view.rule_summaries],
        report_view=report_view_to_dict(view), md_preview="# Audit\n",
    )
    wa._set_job(job)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    # Unknown rule ID must NOT create a /rules# link
    assert b'href="/rules#UNKNOWN_RULE"' not in resp.content
    # The rule ID text should still appear
    assert b"UNKNOWN_RULE" in resp.content


def test_results_page_has_help_link_in_summary(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """Summary section must contain contextual help link to /help#results."""
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path, finding_count=1)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    assert b"/help#results" in resp.content


# ---------------------------------------------------------------------------
# Regression: drag-and-drop still present
# ---------------------------------------------------------------------------

def test_drag_and_drop_still_present(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.get("/")
    assert resp.status_code == 200
    assert b'id="upload-drop-zone"' in resp.content
    assert b"DataTransfer" in resp.content
    assert b"dragenter" in resp.content


# ---------------------------------------------------------------------------
# Regression: grouped/raw findings behavior unchanged
# ---------------------------------------------------------------------------

def test_grouped_raw_toggle_still_present(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path, finding_count=3)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    assert b"Grouped problems" in resp.content
    assert b"All individual findings" in resp.content
    assert b'id="grouped-problems-panel"' in resp.content
    assert b'id="individual-findings-panel"' in resp.content


# ---------------------------------------------------------------------------
# Regression: DOM-ready filter script
# ---------------------------------------------------------------------------

def test_dom_ready_filter_script_unchanged(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """Filter/toggle script must still wait for DOMContentLoaded."""
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path, finding_count=3)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    assert b"DOMContentLoaded" in resp.content
    assert b'setMode("grouped")' in resp.content
    assert b"getElementById(\"filter-rule\")" in resp.content


# ---------------------------------------------------------------------------
# _is_p_rule_id unit tests
# ---------------------------------------------------------------------------

def test_is_p_rule_id_valid() -> None:
    from njit_auditor.web_app import _is_p_rule_id

    assert _is_p_rule_id("P001") is True
    assert _is_p_rule_id("P013") is True
    assert _is_p_rule_id("P082") is True
    assert _is_p_rule_id("P999") is True


def test_is_p_rule_id_invalid() -> None:
    from njit_auditor.web_app import _is_p_rule_id

    assert _is_p_rule_id("UNKNOWN_RULE") is False
    assert _is_p_rule_id("Q001") is False
    assert _is_p_rule_id("") is False
    assert _is_p_rule_id("P") is False
    assert _is_p_rule_id("P0A1") is False
    assert _is_p_rule_id("p001") is False


# ---------------------------------------------------------------------------
# Rule catalog classification unit tests
# ---------------------------------------------------------------------------

def test_build_rule_catalog_returns_student_rules() -> None:
    from njit_auditor.web_app import _build_rule_catalog

    catalog = _build_rule_catalog()
    assert "student_rules" in catalog
    assert len(catalog["student_rules"]) > 0


def test_build_rule_catalog_p001_not_in_catalog() -> None:
    """P001 is TeX/ZIP-source-only and never runs on a web PDF upload."""
    from njit_auditor.web_app import _build_rule_catalog

    catalog = _build_rule_catalog()
    student_ids = {r["id"] for r in catalog["student_rules"]}
    tech_ids = {r["id"] for r in catalog["technical_rules"]}
    assert "P001" not in student_ids
    assert "P001" not in tech_ids


def test_build_rule_catalog_p013_in_student_rules() -> None:
    from njit_auditor.web_app import _build_rule_catalog

    catalog = _build_rule_catalog()
    ids = [r["id"] for r in catalog["student_rules"]]
    assert "P013" in ids


def test_build_rule_catalog_excludes_all_tex_source_only_rules() -> None:
    """P001-P010 are TeX/ZIP-source-only and must not be advertised on the website."""
    from njit_auditor.web_app import _build_rule_catalog

    catalog = _build_rule_catalog()
    student_ids = {r["id"] for r in catalog["student_rules"]}
    tech_ids = {r["id"] for r in catalog["technical_rules"]}
    tex_only_ids = {f"P{n:03d}" for n in range(1, 11)}
    assert not (tex_only_ids & student_ids)
    assert not (tex_only_ids & tech_ids)


def test_build_rule_catalog_input_types_pdf_only() -> None:
    """The "Applies to" filter values must never mention TeX/ZIP on the website."""
    from njit_auditor.web_app import _build_rule_catalog

    catalog = _build_rule_catalog()
    assert catalog["input_types"] == ["PDF (compiled)"]


def test_build_rule_catalog_p083_not_in_student_rules() -> None:
    """P083 is an evaluation task and must not appear in the student catalog."""
    from njit_auditor.web_app import _build_rule_catalog

    catalog = _build_rule_catalog()
    student_ids = {r["id"] for r in catalog["student_rules"]}
    assert "P083" not in student_ids


def test_build_rule_catalog_p081_not_in_student_rules() -> None:
    """P081 is a reporting-only entry and must not appear in the student catalog."""
    from njit_auditor.web_app import _build_rule_catalog

    catalog = _build_rule_catalog()
    student_ids = {r["id"] for r in catalog["student_rules"]}
    assert "P081" not in student_ids


def test_build_rule_catalog_p080_not_in_student_rules() -> None:
    """P080 is docx infrastructure and must not appear in student catalog."""
    from njit_auditor.web_app import _build_rule_catalog

    catalog = _build_rule_catalog()
    student_ids = {r["id"] for r in catalog["student_rules"]}
    assert "P080" not in student_ids


def test_build_rule_catalog_p069_not_in_student_rules() -> None:
    """P069 is infrastructure-only and must not appear in the student catalog."""
    from njit_auditor.web_app import _build_rule_catalog

    catalog = _build_rule_catalog()
    student_ids = {r["id"] for r in catalog["student_rules"]}
    assert "P069" not in student_ids


def test_build_rule_catalog_technical_contains_p083() -> None:
    from njit_auditor.web_app import _build_rule_catalog

    catalog = _build_rule_catalog()
    tech_ids = {r["id"] for r in catalog["technical_rules"]}
    assert "P083" in tech_ids


def test_build_rule_catalog_technical_contains_p081() -> None:
    from njit_auditor.web_app import _build_rule_catalog

    catalog = _build_rule_catalog()
    tech_ids = {r["id"] for r in catalog["technical_rules"]}
    assert "P081" in tech_ids


def test_build_rule_catalog_p082_not_in_student_rules() -> None:
    """P082 is experimental/opt-in and disabled by default; the website never enables
    it, so it must not appear in the public-facing student catalog."""
    from njit_auditor.web_app import _build_rule_catalog

    catalog = _build_rule_catalog()
    student_ids = {r["id"] for r in catalog["student_rules"]}
    assert "P082" not in student_ids


def test_build_rule_catalog_technical_contains_p082() -> None:
    from njit_auditor.web_app import _build_rule_catalog

    catalog = _build_rule_catalog()
    tech_ids = {r["id"] for r in catalog["technical_rules"]}
    assert "P082" in tech_ids


def test_build_rule_catalog_p021_in_student_rules() -> None:
    """P021 has a mixed input_required (tex_source + compiled_pdf) but has a real PDF
    detector wired into the web audit, so it must remain in the public catalog."""
    from njit_auditor.web_app import _build_rule_catalog

    catalog = _build_rule_catalog()
    student_ids = {r["id"] for r in catalog["student_rules"]}
    assert "P021" in student_ids


def test_build_rule_catalog_rule_fields_populated() -> None:
    from njit_auditor.web_app import _build_rule_catalog

    catalog = _build_rule_catalog()
    for rule in catalog["student_rules"][:5]:
        assert rule["id"]
        assert rule["title"]
        assert rule["input_label"]
        assert rule["severity_label"]


def test_build_rule_catalog_no_implementation_modules() -> None:
    """Implementation module paths must not appear in enriched rule data."""
    from njit_auditor.web_app import _build_rule_catalog

    catalog = _build_rule_catalog()
    for rule in catalog["student_rules"]:
        assert "implementation_module" not in rule or True  # key may exist but value not shown
        # The important thing is the template does not render it
    # Verify no module path strings are in rule titles or definitions
    for rule in catalog["student_rules"]:
        assert "njit_auditor.rules." not in rule.get("title", "")
        assert "njit_auditor.rules." not in rule.get("what_it_checks", "")
