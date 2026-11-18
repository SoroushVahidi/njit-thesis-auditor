"""Synthetic administrator feedback boundaries and persistence tests."""

from __future__ import annotations

import importlib
import secrets
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest
from argon2 import PasswordHasher
from fastapi.testclient import TestClient
from starlette.routing import Route

from njit_auditor import admin_feedback, web_app


@pytest.fixture
def setup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, Any, Path, str]:
    runtime = tmp_path / "audits"
    runtime.mkdir()
    db_path = tmp_path / "private.sqlite3"
    password = secrets.token_urlsafe(24)
    monkeypatch.setenv("NJIT_AUDITOR_ADMIN_ENABLED", "1")
    monkeypatch.setenv("NJIT_AUDITOR_ADMIN_HTTPS_VERIFIED", "1")
    monkeypatch.setenv("NJIT_AUDITOR_ADMIN_PASSWORD_HASH", PasswordHasher().hash(password))
    monkeypatch.setenv("NJIT_AUDITOR_ADMIN_DB_PATH", str(db_path))
    monkeypatch.setenv("NJIT_AUDITOR_WEB_RUNTIME_DIR", str(runtime))
    monkeypatch.setattr(web_app, "RUNTIME_DIR", runtime)
    with web_app._jobs_lock:
        saved = dict(web_app._jobs)
        web_app._jobs.clear()
    client = TestClient(web_app.app, base_url="https://testserver", raise_server_exceptions=False)
    yield client, web_app, db_path, password
    client.close()
    with web_app._jobs_lock:
        web_app._jobs.clear()
        web_app._jobs.update(saved)


def _login(client: TestClient, password: str) -> str:
    page = client.get("/admin/login")
    assert page.status_code == 200
    csrf = client.cookies.get(admin_feedback._LOGIN_CSRF)
    assert csrf
    response = client.post("/admin/login", data={"password": password, "csrf_token": csrf},
                           headers={"Origin": "https://testserver"}, follow_redirects=False)
    assert response.status_code == 303
    cookie_header = response.headers["set-cookie"].lower()
    assert "secure" in cookie_header and "httponly" in cookie_header
    assert "samesite=strict" in cookie_header
    token = client.cookies.get(admin_feedback._COOKIE)
    assert token
    return token


def _job(wa: Any, *, count: int = 2) -> str:
    job_id = secrets.token_urlsafe(16)
    wa._job_dir(job_id).mkdir()
    (wa._job_dir(job_id) / "report.json").write_text('{"findings": []}', encoding="utf-8")
    (wa._job_dir(job_id) / "report.md").write_text("# Synthetic report", encoding="utf-8")
    (wa._job_dir(job_id) / "report.txt").write_text("Synthetic report", encoding="utf-8")
    findings = []
    for index in range(count):
        findings.append({
            "finding_id": f"f{index}", "rule_id": "P011", "issue_type": "margin_violation",
            "page": index + 1, "confidence_level": "medium", "confidence_label": "Medium",
            "category": "Margins", "student_topic": "Margins", "student_summary": "Check margin",
            "problem_anchor": f"problem-{index + 1}", "problem_number": index + 1,
            "technical_details": [], "action_kind": "explanation",
        })
    wa._set_job(wa.JobState(
        job_id=job_id, state="complete", created_at=datetime.now(timezone.utc).isoformat(),
        file_name="synthetic.pdf", findings=findings, finding_count=count,
    ))
    return job_id


def _save(client: TestClient, job_id: str, finding_id: str, classification: str,
          comment: str = "") -> Any:
    csrf = _csrf(client.cookies.get(admin_feedback._COOKIE, ""))
    return client.post(f"/audits/{job_id}/feedback/{finding_id}",
                       data={"csrf_token": csrf, "classification": classification,
                             "comment": comment},
                       headers={"Origin": "https://testserver"}, follow_redirects=False)


def _csrf(token: str) -> str:
    with admin_feedback._connection() as db:
        row = db.execute("SELECT csrf_token FROM sessions WHERE token_hash=?",
                         (admin_feedback._token_hash(token),)).fetchone()
    assert row is not None
    return str(row["csrf_token"])


def test_login_denial_rate_limit_and_secure_cookie(
    setup: tuple[TestClient, Any, Path, str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _, _, password = setup
    assert client.get("/admin/feedback").status_code == 403
    assert client.post("/admin/login", data={"password": password}).status_code == 403
    page = client.get("/admin/login")
    assert page.status_code == 200
    csrf = client.cookies.get(admin_feedback._LOGIN_CSRF)
    for _ in range(5):
        response = client.post("/admin/login", data={"password": secrets.token_urlsafe(8),
                                              "csrf_token": csrf},
                               headers={"Origin": "https://testserver"})
        assert response.status_code == 401
    assert client.post("/admin/login", data={"password": password, "csrf_token": csrf},
                       headers={"Origin": "https://testserver"}).status_code == 429
    monkeypatch.delenv("NJIT_AUDITOR_ADMIN_ENABLED")
    assert client.get("/admin/login").status_code == 503
    assert client.get("/").status_code == 200
    monkeypatch.setenv("NJIT_AUDITOR_ADMIN_ENABLED", "1")
    insecure = TestClient(web_app.app, base_url="http://testserver")
    assert insecure.get("/admin/login").status_code == 503


def test_feedback_lifecycle_privacy_and_restart(
    setup: tuple[TestClient, Any, Path, str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, wa, db_path, password = setup
    job_id = _job(wa)
    anonymous = TestClient(wa.app, base_url="https://testserver")
    assert "Administrator feedback" not in anonymous.get(f"/audits/{job_id}").text
    assert anonymous.post(f"/audits/{job_id}/feedback/f0", data={}).status_code == 403
    token = _login(client, password)
    cookie = client.get("/admin/login", follow_redirects=False)
    assert cookie.status_code == 303
    assert _save(client, job_id, "f0", "true_positive").status_code == 303
    assert _save(client, job_id, "f1", "false_positive", "Synthetic review note").status_code == 303
    records = admin_feedback.list_feedback()
    assert len(records) == 2
    assert {record["finding_ref"] for record in records} == {"f0", "f1"}
    assert all(record["rule_id"] == "P011" for record in records)
    assert db_path.stat().st_mode & 0o777 == 0o600
    assert b"Synthetic review note" not in anonymous.get(f"/audits/{job_id}").content
    assert b"Synthetic review note" not in anonymous.get("/").content
    for extension in ("json", "markdown", "text"):
        response = anonymous.get(f"/audits/{job_id}/download/{extension}")
        assert response.status_code == 200
        assert b"Synthetic review note" not in response.content
    assert _save(client, job_id, "f9", "other").status_code == 404
    assert _save(client, job_id, "f0", "unclear", "Clarification needed").status_code == 303
    assert admin_feedback.list_feedback(classification="unclear")[0]["finding_ref"] == "f0"
    today = datetime.now(timezone.utc).date().isoformat()
    filtered = client.get("/admin/feedback", params={"rule_id": "P011", "status": "Open",
                                                   "from_date": today, "to_date": today})
    assert filtered.status_code == 200 and "margin_violation" in filtered.text
    csrf = _csrf(token)
    feedback_id = admin_feedback.list_feedback(classification="unclear")[0]["id"]
    headers = {"Origin": "https://testserver"}
    def update(data: dict[str, str]) -> Any:
        return client.post(f"/admin/feedback/{feedback_id}",
                           data={"csrf_token": csrf, **data},
                           headers=headers, follow_redirects=False)
    assert update({"classification": "other", "comment": "Confidence should be Low.",
                   "status": "In Progress"}).status_code == 303
    assert (admin_feedback.list_feedback(status="In Progress")[0]["comment"]
            == "Confidence should be Low.")
    assert update({"status": "Resolved"}).status_code == 303
    assert admin_feedback.list_feedback(status="Resolved")[0]["resolved_at"]
    assert update({"status": "Open"}).status_code == 303
    assert admin_feedback.list_feedback(status="Open")[0]["resolved_at"] is None
    assert update({"action": "delete"}).status_code == 400
    assert update({"action": "delete", "confirm_delete": "yes"}).status_code == 303
    assert len(admin_feedback.list_feedback()) == 1
    assert _save(client, job_id, "f1", "other").status_code == 303
    wa.cleanup_expired_jobs(now=datetime.now(timezone.utc) + timedelta(days=2))
    assert wa._get_job(job_id) is None
    assert not wa._job_dir(job_id).exists()
    assert _save(client, job_id, "f1", "other").status_code == 404
    assert len(admin_feedback.list_feedback()) == 1
    reloaded = importlib.reload(wa)
    monkeypatch.setattr(reloaded, "RUNTIME_DIR", db_path.parent / "audits")
    restarted = TestClient(reloaded.app, base_url="https://testserver")
    restarted.cookies.set(admin_feedback._COOKIE, token)
    assert "Synthetic review note" not in restarted.get("/admin/feedback").text
    assert "margin_violation" in restarted.get("/admin/feedback").text


def test_session_expiration_csrf_and_concurrent_updates(
    setup: tuple[TestClient, Any, Path, str],
) -> None:
    client, wa, db_path, password = setup
    job_id = _job(wa)
    token = _login(client, password)
    assert _save(client, job_id, "f0", "true_positive").status_code == 303
    assert client.post(f"/audits/{job_id}/feedback/f0", data={"classification": "other"},
                       headers={"Origin": "https://testserver"}).status_code == 403
    csrf = _csrf(token)
    def write(index: int) -> int:
        other = TestClient(wa.app, base_url="https://testserver", raise_server_exceptions=False)
        other.cookies.set(admin_feedback._COOKIE, token)
        return other.post(f"/audits/{job_id}/feedback/f0",
                          data={"csrf_token": csrf, "classification": "other",
                                "comment": f"Concurrent {index}"},
                          headers={"Origin": "https://testserver"},
                          follow_redirects=False).status_code
    with ThreadPoolExecutor(max_workers=4) as pool:
        assert list(pool.map(write, range(8))) == [303] * 8
    assert len(admin_feedback.list_feedback()) == 1
    with sqlite3.connect(db_path) as db:
        db.execute("UPDATE sessions SET expires_at=0")
    assert client.get("/admin/feedback").status_code == 403
    assert client.post(
        f"/audits/{job_id}/feedback/f0",
        data={"csrf_token": csrf, "classification": "other"},
        headers={"Origin": "https://testserver"},
    ).status_code == 403


def test_logout_revokes_session(setup: tuple[TestClient, Any, Path, str]) -> None:
    client, _, _, password = setup
    token = _login(client, password)
    csrf = _csrf(token)
    response = client.post("/admin/logout", data={"csrf_token": csrf},
                           headers={"Origin": "https://testserver"},
                           follow_redirects=False)
    assert response.status_code == 303
    assert client.get("/admin/feedback").status_code == 403


def test_invalid_input_and_escaped_comments(
    setup: tuple[TestClient, Any, Path, str],
) -> None:
    client, wa, _, password = setup
    job_id = _job(wa, count=1)
    token = _login(client, password)
    csrf = _csrf(token)
    endpoint = f"/audits/{job_id}/feedback/f0"
    assert client.post(endpoint, data={"csrf_token": csrf},
                       headers={"Origin": "https://testserver"}).status_code == 400
    assert client.post(endpoint, data={"csrf_token": csrf, "classification": "other"},
                       headers={"Origin": "https://elsewhere.invalid"}).status_code == 403
    assert client.post(endpoint, data={"csrf_token": csrf, "classification": "other"},
                       headers={"Origin": "https://testserver"},
                       follow_redirects=False).status_code == 303
    assert _save(client, job_id, "f0", "other", "<script>synthetic()</script>").status_code == 303
    page = client.get("/admin/feedback")
    assert "&lt;script&gt;synthetic()&lt;/script&gt;" in page.text
    assert "<script>synthetic()</script>" not in page.text
    assert "<script>synthetic()</script>" not in client.get(f"/audits/{job_id}").text
    assert len(admin_feedback.list_feedback()) == 1


def test_offline_routes_exclude_admin_feedback(tmp_path: Path) -> None:
    from njit_auditor.offline_app import create_offline_app

    offline = create_offline_app(port=17391, data_root=tmp_path,
                                 launch_ticket=secrets.token_urlsafe(16))
    paths = {route.path for route in offline.router.routes if isinstance(route, Route)}
    assert "/admin/login" not in paths
    assert "/admin/feedback" not in paths
    assert "/audits/{job_id}/feedback/{finding_id}" not in paths


def test_feedback_never_enters_student_pdf_or_exports(
    setup: tuple[TestClient, Any, Path, str], tmp_path: Path,
) -> None:
    import pymupdf
    from test_web_app import _inject_complete_job

    client, wa, _, password = setup
    job_id = _inject_complete_job(wa, tmp_path)
    finding_id = wa._get_job(job_id).findings[0]["finding_id"]
    _login(client, password)
    comment = "Private synthetic administrator note 74821"
    assert _save(client, job_id, finding_id, "other", comment).status_code == 303
    for extension in ("json", "markdown", "text"):
        response = client.get(f"/audits/{job_id}/download/{extension}")
        assert response.status_code == 200
        assert comment.encode() not in response.content
    pdf = client.get(f"/audits/{job_id}/download/student-report.pdf")
    assert pdf.status_code == 200
    with pymupdf.open(stream=pdf.content, filetype="pdf") as document:
        assert comment not in "".join(page.get_text() for page in document)
