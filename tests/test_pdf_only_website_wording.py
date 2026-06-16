"""Consolidated checks that the public website reads as a simple, PDF-only,
student-facing tool: no "heuristic" jargon, no TeX/ZIP/LaTeX/source-audit
mentions, and no raw Pass/Warning/Error vocabulary — while the underlying
PDF upload, public PDF URL, sample audit, and export routes still work.
"""

from __future__ import annotations

import json
import os
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

_MINIMAL_PDF = b"%PDF-1.4\n%%EOF\n"

_BANNED_SUBSTRINGS = [
    "heuristic",
    "tex source",
    "zip source",
    "latex",
    "source audit",
    "command-line tool only",
    "internal inventory",
]

# Checked as word-boundary regexes rather than plain substrings, since
# ".tex"/".zip" collide with unrelated JS identifiers like "textContent".
_BANNED_PATTERNS = [
    re.compile(r"\.tex\b"),
    re.compile(r"\.zip\b"),
]


def _make_app(tmp_path: Path) -> tuple[TestClient, Any]:
    os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"] = str(tmp_path / "web_audits")
    import importlib

    import njit_auditor.web_app as wa

    importlib.reload(wa)
    return TestClient(wa.app, raise_server_exceptions=False), wa


@pytest.fixture()
def client(tmp_path: Path) -> tuple[TestClient, Any]:
    return _make_app(tmp_path)


def _assert_no_banned_terms(body: str) -> None:
    lowered = body.lower()
    for term in _BANNED_SUBSTRINGS:
        assert term not in lowered, f"banned term {term!r} found"
    for pattern in _BANNED_PATTERNS:
        match = pattern.search(lowered)
        assert match is None, f"banned pattern {pattern.pattern!r} found: {match}"


def _inject_complete_job(wa: Any, tmp_path: Path, finding_count: int = 3) -> str:
    """Inject a complete PDF-audit job with a mix of FAIL/WARNING findings."""
    from njit_auditor.models import AuditFinding, Severity
    from njit_auditor.report_outputs import audit_findings_to_json_dict, write_markdown_report
    from njit_auditor.report_view import build_report_view, report_view_to_dict

    findings = [
        AuditFinding(
            rule_id="P011" if i % 2 == 0 else "P013",
            severity=Severity.FAIL if i == 0 else Severity.WARNING,
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


# ---------------------------------------------------------------------------
# Banned-term sweep across public pages
# ---------------------------------------------------------------------------


def test_no_banned_terms_on_homepage(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.get("/")
    _assert_no_banned_terms(resp.text)


def test_no_banned_terms_on_help_page(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.get("/help")
    _assert_no_banned_terms(resp.text)


def test_no_banned_terms_on_rules_page(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.get("/rules")
    _assert_no_banned_terms(resp.text)


def test_no_banned_terms_on_results_page(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path, finding_count=3)
    resp = c.get(f"/audits/{job_id}")
    _assert_no_banned_terms(resp.text)


# ---------------------------------------------------------------------------
# Homepage is PDF-only and advisory
# ---------------------------------------------------------------------------


def test_homepage_states_pdf_only_advisory_local_processing(
    client: tuple[TestClient, Any],
) -> None:
    c, _ = client
    resp = c.get("/")
    assert resp.status_code == 200
    body = resp.text
    assert "thesis or dissertation PDF" in body
    assert "automatically" in body.lower()
    assert "advisory" in body.lower()
    assert "locally" in body.lower()


# ---------------------------------------------------------------------------
# Rule reference excludes source-only (TeX/ZIP) rules end-to-end
# ---------------------------------------------------------------------------


def test_rules_page_excludes_source_only_rule_ids(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.get("/rules")
    body = resp.text
    for n in range(1, 11):
        rule_id = f"P{n:03d}"
        assert f'id="{rule_id}"' not in body, f"{rule_id} should not be rendered on /rules"


def test_rules_page_excludes_internal_and_experimental_rule_ids(
    client: tuple[TestClient, Any],
) -> None:
    """Infrastructure, reporting-only, evaluation-only, and experimental/opt-in
    entries never produce findings in the web PDF audit and must not be rendered."""
    c, _ = client
    resp = c.get("/rules")
    body = resp.text
    hidden_ids = [
        "P069", "P070", "P071", "P072", "P073",
        "P076", "P077", "P079", "P080", "P081", "P082", "P083",
    ]
    for rule_id in hidden_ids:
        assert f'id="{rule_id}"' not in body, f"{rule_id} should not be rendered on /rules"


# ---------------------------------------------------------------------------
# Severity simplified to plain-language labels everywhere visible
# ---------------------------------------------------------------------------


def test_results_page_uses_simple_priority_labels_not_raw_severity(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path, finding_count=3)
    resp = c.get(f"/audits/{job_id}")
    body = resp.text
    assert "Problem" in body
    assert "Needs fixing" in body
    assert "Worth checking" in body
    # Raw severity tokens must not appear as standalone visible badge text.
    assert ">FAIL<" not in body
    assert ">WARNING<" not in body
    assert ">PASS<" not in body
    assert "Pass / Warning / Error" not in body


def test_rules_page_uses_simple_priority_labels(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.get("/rules")
    body = resp.text
    assert "Priority" in body
    assert ">FAIL<" not in body
    assert ">WARNING<" not in body


# ---------------------------------------------------------------------------
# Regression: core audit paths still work after the wording simplification
# ---------------------------------------------------------------------------


def test_pdf_upload_still_creates_job(client: tuple[TestClient, Any]) -> None:
    c, wa = client
    with patch.object(wa, "_run_audit_task", lambda job_id: None):
        resp = c.post(
            "/audits",
            files={"file": ("thesis.pdf", _MINIMAL_PDF, "application/pdf")},
            follow_redirects=False,
        )
    assert resp.status_code == 303
    assert resp.headers["location"].startswith("/audits/")


def test_public_pdf_url_audit_still_creates_job(client: tuple[TestClient, Any]) -> None:
    c, wa = client

    def _fake_fetch(url: str, dest: Path, max_bytes: int) -> None:
        dest.write_bytes(_MINIMAL_PDF)

    with patch.object(wa, "fetch_pdf_url", _fake_fetch):
        with patch.object(wa, "_run_audit_task", lambda job_id: None):
            resp = c.post(
                "/audits/url",
                data={"pdf_url": "https://example.com/thesis.pdf"},
                follow_redirects=False,
            )
    assert resp.status_code == 303
    assert resp.headers["location"].startswith("/audits/")


def test_sample_pdf_audit_still_creates_job(client: tuple[TestClient, Any]) -> None:
    c, wa = client
    from njit_auditor.web_samples import SampleInfo

    sample = SampleInfo(
        sample_id="ester_sample_a",
        label="Sample A — first review (EF-annotated)",
        rel_path="data/raw/ester/250218 Cibaku Elson First Review.pdf",
    )

    def fake_copy(sample_id: str, dest: Path) -> None:
        dest.write_bytes(_MINIMAL_PDF)

    with patch.object(wa, "list_builtin_samples", lambda: [sample]):
        with patch.object(wa, "get_builtin_sample", lambda sid: sample):
            with patch.object(wa, "copy_builtin_sample_to_job", fake_copy):
                with patch.object(wa, "_run_audit_task", lambda job_id: None):
                    resp = c.post(
                        "/audits/sample",
                        data={"sample_id": "ester_sample_a"},
                        follow_redirects=False,
                    )
    assert resp.status_code == 303
    assert resp.headers["location"].startswith("/audits/")


def test_json_export_still_works(client: tuple[TestClient, Any], tmp_path: Path) -> None:
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path)
    resp = c.get(f"/audits/{job_id}/download/json")
    assert resp.status_code == 200
    assert "findings" in resp.json()


def test_markdown_export_still_works(client: tuple[TestClient, Any], tmp_path: Path) -> None:
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path)
    resp = c.get(f"/audits/{job_id}/download/markdown")
    assert resp.status_code == 200


def test_results_page_still_renders(client: tuple[TestClient, Any], tmp_path: Path) -> None:
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    assert b"Problems found" in resp.content
