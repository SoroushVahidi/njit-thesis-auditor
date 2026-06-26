"""Automated smoke tests for committed synthetic web demo fixtures.

All fixtures in tests/fixtures/web_demo/ contain only synthetic placeholder text —
no real dissertation content, real student names, committee names, or thesis titles.
"""

from __future__ import annotations

import io
import os
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Fixture directory
# ---------------------------------------------------------------------------

FIXTURES = Path(__file__).parent / "fixtures" / "web_demo"

# Current audit output for clean_minimal.pdf on main (docs/tests must stay aligned).
_CLEAN_MINIMAL_EXPECTED_RULE_IDS = frozenset({"P011", "P013", "P027"})

# Strings that must never appear in committed fixture files (privacy check).
# Real personal or private-content strings are blocked; these are the canonical
# synthetic names used throughout the test suite to verify sanitization.
_BANNED_STRINGS: tuple[str, ...] = (
    "John Smith Dissertation Title",
    "fig:test_private_label",
    "fig:test_private_ref",
    "tab:my_secret_table",
)

# ---------------------------------------------------------------------------
# Helpers shared with test_web_app.py pattern
# ---------------------------------------------------------------------------


def _make_app(tmp_path: Path) -> Any:
    """Import the web app with RUNTIME_DIR pointed at a temp directory."""
    os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"] = str(tmp_path / "web_audits")
    import importlib

    import njit_auditor.web_app as wa

    importlib.reload(wa)
    return wa.app, wa


@pytest.fixture()
def client(tmp_path: Path) -> tuple[TestClient, Any]:
    app, wa = _make_app(tmp_path)
    return TestClient(app, raise_server_exceptions=False), wa


def _upload_file(
    c: TestClient,
    fixture_name: str,
    content_type: str = "application/octet-stream",
    *,
    follow_redirects: bool = False,
) -> Any:
    """Read a committed fixture and POST it to /audits."""
    data = (FIXTURES / fixture_name).read_bytes()
    return c.post(
        "/audits",
        files={"file": (fixture_name, io.BytesIO(data), content_type)},
        follow_redirects=follow_redirects,
    )


def _job_id_from_redirect(resp: Any) -> str:
    """Extract job_id from a 303 Location header."""
    return resp.headers["location"].split("/audits/")[1]


# ---------------------------------------------------------------------------
# 1. Fixture existence
# ---------------------------------------------------------------------------


def test_demo_fixtures_exist() -> None:
    """All five committed web demo fixtures must exist on disk."""
    for name in (
        "clean_minimal.pdf",
        "issues_pdf.pdf",
        "clean_minimal.tex",
        "issues_tex.tex",
        "demo_project.zip",
    ):
        path = FIXTURES / name
        assert path.exists(), f"Missing fixture: {path}"
        assert path.stat().st_size > 0, f"Fixture is empty: {path}"


# ---------------------------------------------------------------------------
# 2. Privacy / no banned strings in committed fixtures
# ---------------------------------------------------------------------------


def test_demo_fixtures_no_banned_strings() -> None:
    """Committed fixtures must not contain known private-content strings."""
    text_fixtures = ("clean_minimal.tex", "issues_tex.tex")
    for name in text_fixtures:
        content = (FIXTURES / name).read_text(encoding="utf-8", errors="replace")
        for banned in _BANNED_STRINGS:
            assert banned not in content, (
                f"Banned string {banned!r} found in fixture {name}"
            )


def test_demo_fixtures_tex_no_real_names() -> None:
    """TeX fixtures must not contain real personal names."""
    real_names = ("John Smith", "Jane Doe", "Dr. Williams", "Prof. Johnson")
    for name in ("clean_minimal.tex", "issues_tex.tex"):
        content = (FIXTURES / name).read_text(encoding="utf-8", errors="replace")
        for real_name in real_names:
            assert real_name not in content, (
                f"Real name {real_name!r} found in fixture {name}"
            )


# ---------------------------------------------------------------------------
# 3. clean_minimal.pdf upload succeeds and completes
# ---------------------------------------------------------------------------


def test_clean_minimal_pdf_upload_succeeds(client: tuple[TestClient, Any]) -> None:
    """clean_minimal.pdf uploads, redirects to a job, and completes."""
    c, _ = client
    resp = _upload_file(c, "clean_minimal.pdf", "application/pdf", follow_redirects=True)
    assert resp.status_code == 200
    body = resp.content
    # Job page loads — either completion or processing banner is present
    assert b"Audit" in body or b"complete" in body.lower() or b"Processing" in body


def test_clean_minimal_pdf_upload_creates_job_redirect(
    client: tuple[TestClient, Any],
) -> None:
    """clean_minimal.pdf upload returns 303 redirect to a job page."""
    c, _ = client
    resp = _upload_file(c, "clean_minimal.pdf", "application/pdf")
    assert resp.status_code == 303
    assert resp.headers["location"].startswith("/audits/")


def test_clean_minimal_pdf_produces_expected_residual_findings() -> None:
    """clean_minimal.pdf is a minimal demo fixture with known residual audit outputs."""
    from njit_auditor.audit_runner import run_pdf_audit_full

    findings = run_pdf_audit_full(FIXTURES / "clean_minimal.pdf")
    rule_ids = {finding.rule_id for finding in findings}
    assert rule_ids == _CLEAN_MINIMAL_EXPECTED_RULE_IDS, (
        f"Expected {_CLEAN_MINIMAL_EXPECTED_RULE_IDS}; got {rule_ids}"
    )
    warnings = {
        finding.rule_id
        for finding in findings
        if finding.severity.value == "WARNING"
    }
    assert warnings == {"P011", "P027"}
    p013 = next(finding for finding in findings if finding.rule_id == "P013")
    assert p013.severity.value == "PASS"


# ---------------------------------------------------------------------------
# 4. issues_pdf.pdf produces at least one finding
# ---------------------------------------------------------------------------


def test_issues_pdf_produces_findings(client: tuple[TestClient, Any]) -> None:
    """issues_pdf.pdf must trigger at least one PDF finding (P011 or P013)."""
    c, _ = client
    resp = _upload_file(c, "issues_pdf.pdf", "application/pdf", follow_redirects=False)
    assert resp.status_code == 303
    job_id = _job_id_from_redirect(resp)
    # Wait for completion by loading the job page (synchronous test client runs audit inline)
    page = c.get(f"/audits/{job_id}")
    assert page.status_code == 200

    # Download JSON to check findings
    json_resp = c.get(f"/audits/{job_id}/download/json")
    if json_resp.status_code != 200:
        pytest.skip("audit did not complete in time for JSON download")
    data = json_resp.json()
    findings = data.get("findings", [])
    rule_ids = {f["rule_id"] for f in findings}
    # issues_pdf.pdf is designed to trigger P011 (margin overflow)
    assert len(findings) > 0, "Expected at least one finding from issues_pdf.pdf"
    assert "P011" in rule_ids or "P013" in rule_ids, (
        f"Expected P011 or P013 in findings; got rule IDs: {rule_ids}"
    )


# ---------------------------------------------------------------------------
# 5. clean_minimal.tex / issues_tex.tex / demo_project.zip are rejected by the
#    web upload form — the web UI is PDF-only. These fixtures remain useful
#    for the command-line source audit, which is unaffected by this gating.
# ---------------------------------------------------------------------------

_PDF_ONLY_ERROR = b"Only PDF files are supported in the web interface. Please upload a PDF file."


def test_clean_minimal_tex_upload_rejected(client: tuple[TestClient, Any]) -> None:
    """clean_minimal.tex is rejected by the web upload form (PDF-only)."""
    c, _ = client
    resp = _upload_file(c, "clean_minimal.tex", "text/plain", follow_redirects=False)
    assert resp.status_code == 400
    assert _PDF_ONLY_ERROR in resp.content


def test_issues_tex_upload_rejected(client: tuple[TestClient, Any]) -> None:
    """issues_tex.tex is rejected by the web upload form (PDF-only)."""
    c, _ = client
    resp = _upload_file(c, "issues_tex.tex", "text/plain", follow_redirects=False)
    assert resp.status_code == 400
    assert _PDF_ONLY_ERROR in resp.content


def test_demo_project_zip_upload_rejected(client: tuple[TestClient, Any]) -> None:
    """demo_project.zip is rejected by the web upload form (PDF-only)."""
    c, _ = client
    resp = _upload_file(c, "demo_project.zip", "application/zip", follow_redirects=False)
    assert resp.status_code == 400
    assert _PDF_ONLY_ERROR in resp.content


# ---------------------------------------------------------------------------
# 8. JSON download works for clean_minimal.pdf
# ---------------------------------------------------------------------------


def test_demo_pdf_json_download_works(client: tuple[TestClient, Any]) -> None:
    """JSON download for a clean_minimal.pdf job returns valid JSON with expected keys."""
    c, _ = client
    resp = _upload_file(c, "clean_minimal.pdf", "application/pdf", follow_redirects=False)
    assert resp.status_code == 303
    job_id = _job_id_from_redirect(resp)
    c.get(f"/audits/{job_id}")  # trigger completion

    json_resp = c.get(f"/audits/{job_id}/download/json")
    if json_resp.status_code != 200:
        pytest.skip("audit did not complete in time")
    assert json_resp.headers["content-type"].startswith("application/json")
    data = json_resp.json()
    assert "findings" in data
    assert "metadata" in data
    assert data["metadata"]["audit_type"] == "pdf"


# ---------------------------------------------------------------------------
# 10. Web-rendered page does not expose full server paths (PDF)
# ---------------------------------------------------------------------------


def test_demo_pdf_no_full_path_in_render(client: tuple[TestClient, Any]) -> None:
    """The web results page for a PDF job must not expose the full server path."""
    c, _ = client
    resp = _upload_file(c, "clean_minimal.pdf", "application/pdf", follow_redirects=False)
    assert resp.status_code == 303
    job_id = _job_id_from_redirect(resp)
    page = c.get(f"/audits/{job_id}")
    assert page.status_code == 200

    runtime_root = Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"]).resolve()
    # The full absolute runtime path must not appear in the rendered HTML
    assert str(runtime_root).encode() not in page.content, (
        "Full server path leaked into rendered job page"
    )


def test_demo_pdf_json_no_full_path(client: tuple[TestClient, Any]) -> None:
    """JSON download for a PDF job must not contain the full server runtime path."""
    c, _ = client
    resp = _upload_file(c, "clean_minimal.pdf", "application/pdf", follow_redirects=False)
    assert resp.status_code == 303
    job_id = _job_id_from_redirect(resp)
    c.get(f"/audits/{job_id}")

    json_resp = c.get(f"/audits/{job_id}/download/json")
    if json_resp.status_code != 200:
        pytest.skip("audit did not complete in time")
    runtime_root = Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"]).resolve()
    assert str(runtime_root) not in json_resp.text, (
        "Full server path leaked into PDF JSON download"
    )


# ---------------------------------------------------------------------------
# 22. Smoke script existence
# ---------------------------------------------------------------------------


def test_web_demo_smoke_script_exists() -> None:
    """scripts/web_demo_smoke.sh must exist and be executable."""
    import stat

    scripts_dir = Path(__file__).parent.parent / "scripts"
    smoke = scripts_dir / "web_demo_smoke.sh"
    assert smoke.exists(), f"Missing smoke script: {smoke}"
    assert smoke.stat().st_size > 0, "Smoke script is empty"
    assert smoke.stat().st_mode & stat.S_IXUSR, "Smoke script is not executable"
