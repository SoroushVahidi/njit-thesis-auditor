"""Synthetic administrator feedback boundaries and persistence tests."""

from __future__ import annotations

import importlib
import os
import secrets
import shutil
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from starlette.routing import Route

from njit_auditor import admin_accounts, admin_feedback, web_app


@pytest.fixture
def setup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, Any, Path, str]:
    runtime = tmp_path / "audits"
    runtime.mkdir()
    db_path = tmp_path / "private.sqlite3"
    password = secrets.token_urlsafe(24)
    username = "reviewer" + secrets.token_hex(4)
    monkeypatch.setenv("NJIT_AUDITOR_ADMIN_ENABLED", "1")
    monkeypatch.setenv("NJIT_AUDITOR_ADMIN_HTTPS_VERIFIED", "1")
    monkeypatch.setenv("NJIT_AUDITOR_ADMIN_SESSION_KEY", secrets.token_urlsafe(32))
    monkeypatch.delenv("NJIT_AUDITOR_ADMIN_PASSWORD_HASH", raising=False)
    monkeypatch.setenv("NJIT_AUDITOR_ADMIN_DB_PATH", str(db_path))
    monkeypatch.setenv("NJIT_AUDITOR_WEB_RUNTIME_DIR", str(runtime))
    monkeypatch.setattr(web_app, "RUNTIME_DIR", runtime)
    with web_app._jobs_lock:
        saved = dict(web_app._jobs)
        web_app._jobs.clear()
    admin_accounts.create_account(username, password)
    client = TestClient(web_app.app, base_url="https://testserver", raise_server_exceptions=False)
    yield client, web_app, db_path, password
    client.close()
    with web_app._jobs_lock:
        web_app._jobs.clear()
        web_app._jobs.update(saved)


def _login(client: TestClient, password: str, username: str | None = None) -> str:
    if username is None:
        username = admin_accounts.list_accounts()[0]["username"]
    page = client.get("/admin/login")
    assert page.status_code == 200
    csrf = client.cookies.get(admin_feedback._LOGIN_CSRF)
    assert csrf
    response = client.post("/admin/login", data={"username": username, "password": password,
                                                  "csrf_token": csrf},
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
        row = db.execute("SELECT expires_at FROM sessions WHERE token_hash=?",
                         (admin_feedback._token_hash(token),)).fetchone()
    assert row is not None
    return admin_feedback._session_csrf(token)


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
    assert len(admin_feedback.list_feedback()) == 3
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
    unconfirmed = update({"action": "delete"})
    assert unconfirmed.status_code == 400
    assert "Feedback dashboard" in unconfirmed.text
    assert update({"action": "delete", "confirm_delete": "yes"}).status_code == 303
    assert len(admin_feedback.list_feedback()) == 2
    assert _save(client, job_id, "f1", "other").status_code == 303
    wa.cleanup_expired_jobs(now=datetime.now(timezone.utc) + timedelta(days=2))
    assert wa._get_job(job_id) is None
    assert not wa._job_dir(job_id).exists()
    assert _save(client, job_id, "f1", "other").status_code == 404
    assert len(admin_feedback.list_feedback()) == 3
    reloaded = importlib.reload(wa)
    monkeypatch.setattr(reloaded, "RUNTIME_DIR", db_path.parent / "audits")
    restarted = TestClient(reloaded.app, base_url="https://testserver")
    restarted.cookies.set(admin_feedback._COOKIE, token)
    assert "Synthetic review note" in restarted.get("/admin/feedback").text
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
    records = admin_feedback.list_feedback()
    assert len(records) == 9
    assert {record["comment"] for record in records} == {
        "", *(f"Concurrent {index}" for index in range(8))
    }
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
    assert len(admin_feedback.list_feedback()) == 2


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

    client, wa, db_path, password = setup
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
    stored = db_path.read_bytes()
    assert b"%PDF-" not in stored and b"thesis.pdf" not in stored


def test_same_rule_page_sort_and_multiple_reviews_keep_exact_finding(
    setup: tuple[TestClient, Any, Path, str],
) -> None:
    client, wa, _, password = setup
    job_id = _job(wa)
    job = wa._get_job(job_id)
    assert job is not None
    job.findings[1]["page"] = 1
    job.findings[0]["confidence_level"] = "low"
    job.findings[1]["confidence_level"] = "high"
    _login(client, password)
    page = client.get(f"/audits/{job_id}?sort=confidence_desc")
    assert page.status_code == 200
    first = page.text.index(f'action="/audits/{job_id}/feedback/f1"')
    second = page.text.index(f'action="/audits/{job_id}/feedback/f0"')
    assert first < second
    assert _save(client, job_id, "f0", "true_positive", "First review").status_code == 303
    assert _save(client, job_id, "f0", "unclear", "Second review").status_code == 303
    assert _save(client, job_id, "f1", "false_positive", "Other finding").status_code == 303
    records = admin_feedback.list_feedback()
    assert {(r["finding_ref"], r["comment"]) for r in records} == {
        ("f0", "First review"), ("f0", "Second review"), ("f1", "Other finding")
    }
    assert all(r["audit_ref"] == job_id and r["rule_id"] == "P011" for r in records)
    assert all(r["pdf_page"] == 1 for r in records)
    sorted_page = client.get(f"/audits/{job_id}?sort=confidence_desc")
    assert sorted_page.text.index("Other finding") < sorted_page.text.index("First review")


def test_v1_migration_and_unknown_version_are_safe(
    setup: tuple[TestClient, Any, Path, str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, _, configured, _ = setup
    db_path = configured.parent / "legacy-v1.sqlite3"
    monkeypatch.setenv("NJIT_AUDITOR_ADMIN_DB_PATH", str(db_path))
    record_id = secrets.token_urlsafe(16)
    audit_ref = secrets.token_urlsafe(16)
    with sqlite3.connect(db_path) as db:
        db.executescript("""
            CREATE TABLE feedback (
                id TEXT PRIMARY KEY, audit_ref TEXT NOT NULL, finding_ref TEXT NOT NULL,
                rule_id TEXT NOT NULL, issue_type TEXT NOT NULL, pdf_page INTEGER,
                original_confidence TEXT NOT NULL, classification TEXT NOT NULL,
                comment TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'Open',
                context TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                resolved_at TEXT, UNIQUE(audit_ref, finding_ref)
            );
            CREATE TABLE sessions (token_hash TEXT PRIMARY KEY, csrf_token TEXT NOT NULL,
                                   expires_at INTEGER NOT NULL);
            CREATE TABLE login_attempts (bucket TEXT PRIMARY KEY, count INTEGER NOT NULL,
                                         reset_at INTEGER NOT NULL);
            PRAGMA user_version=1;
        """)
        db.execute("INSERT INTO feedback VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            record_id, audit_ref, "f0", "P011", "margin_violation", 1, "medium",
            "other", "Preserved synthetic review", "Open", "Rule P011", "2026-01-01T00:00:00+00:00",
            "2026-01-01T00:00:00+00:00", None,
        ))
    rows = admin_feedback.list_feedback()
    assert len(rows) == 1 and rows[0]["id"] == record_id
    with sqlite3.connect(db_path) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 5
        assert rows[0]["submitted_by_admin_id"] is None
        db.execute("""INSERT INTO feedback (id,audit_ref,finding_ref,rule_id,issue_type,
            pdf_page,original_confidence,classification,comment,status,context,created_at,
            updated_at,resolved_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            secrets.token_urlsafe(16), audit_ref, "f0", "P011", "margin_violation", 1,
            "medium", "unclear", "Second synthetic review", "Open", "Rule P011",
            "2026-01-02T00:00:00+00:00", "2026-01-02T00:00:00+00:00", None,
        ))
        assert db.execute("SELECT count(*) FROM feedback").fetchone()[0] == 2
        db.execute("PRAGMA user_version=99")
    with pytest.raises(RuntimeError, match="Unsupported administrator database schema"):
        admin_feedback.list_feedback()
    with sqlite3.connect(db_path) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 99
        assert db.execute("SELECT count(*) FROM feedback").fetchone()[0] == 2


def test_backup_restore_keeps_feedback_and_revokes_restored_sessions(
    setup: tuple[TestClient, Any, Path, str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, wa, db_path, password = setup
    job_id = _job(wa, count=1)
    _login(client, password)
    assert _save(client, job_id, "f0", "other", "Backup synthetic note").status_code == 303
    backup_path = db_path.parent / "backup.sqlite3"
    with sqlite3.connect(db_path) as source, sqlite3.connect(backup_path) as target:
        source.backup(target)
    with sqlite3.connect(backup_path) as backup:
        assert backup.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert backup.execute("PRAGMA user_version").fetchone()[0] == 5
        assert backup.execute("SELECT count(*) FROM feedback").fetchone()[0] == 1
    restored_path = db_path.parent / "restored.sqlite3"
    shutil.copy2(backup_path, restored_path)
    restored_path.chmod(0o600)
    monkeypatch.setenv("NJIT_AUDITOR_ADMIN_DB_PATH", str(restored_path))
    with sqlite3.connect(restored_path) as restored:
        restored.execute("DELETE FROM sessions")
    assert client.get("/admin/feedback").status_code == 403
    assert admin_feedback.list_feedback()[0]["comment"] == "Backup synthetic note"


def test_concurrent_login_throttle_survives_restart(
    setup: tuple[TestClient, Any, Path, str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, wa, _, password = setup
    assert password
    assert client.get("/admin/login").status_code == 200
    csrf = client.cookies.get(admin_feedback._LOGIN_CSRF)
    assert csrf

    def wrong_login(_: int) -> int:
        other = TestClient(wa.app, base_url="https://testserver", raise_server_exceptions=False)
        other.cookies.set(admin_feedback._LOGIN_CSRF, csrf)
        return other.post("/admin/login", data={"csrf_token": csrf,
                                                 "password": secrets.token_urlsafe(16)},
                          headers={"Origin": "https://testserver"}).status_code

    with ThreadPoolExecutor(max_workers=8) as pool:
        statuses = list(pool.map(wrong_login, range(8)))
    assert statuses.count(401) == 5 and statuses.count(429) == 3
    reloaded = importlib.reload(wa)
    monkeypatch.setattr(reloaded, "RUNTIME_DIR", Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"]))
    restarted = TestClient(reloaded.app, base_url="https://testserver")
    restarted.cookies.set(admin_feedback._LOGIN_CSRF, csrf)
    assert restarted.post("/admin/login", data={"csrf_token": csrf, "password": password},
                          headers={"Origin": "https://testserver"}).status_code == 429


def test_default_denial_forged_scheme_headers_and_secret_nonreflection(
    setup: tuple[TestClient, Any, Path, str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, wa, _, password = setup
    with admin_feedback._connection() as db:
        password_hash = db.execute("SELECT password_hash FROM admins").fetchone()[0]
    assert password_hash.startswith("$argon2id$")
    monkeypatch.delenv("NJIT_AUDITOR_ADMIN_ENABLED")
    assert client.get("/admin/login").status_code == 503
    assert client.get("/admin/feedback").status_code == 403
    assert client.get("/").status_code == 200
    monkeypatch.setenv("NJIT_AUDITOR_ADMIN_ENABLED", "1")
    monkeypatch.delenv("NJIT_AUDITOR_ADMIN_SESSION_KEY")
    assert client.get("/admin/login").status_code == 503
    monkeypatch.setenv("NJIT_AUDITOR_ADMIN_SESSION_KEY", secrets.token_urlsafe(32))
    monkeypatch.setenv("NJIT_AUDITOR_ADMIN_PASSWORD_HASH", password_hash)
    http = TestClient(wa.app, base_url="http://testserver")
    forged = {"X-Forwarded-Proto": "https", "Forwarded": "proto=https",
              "Origin": "https://testserver"}
    response = http.get("/admin/login", headers=forged)
    assert response.status_code == 503 and "set-cookie" not in response.headers
    assert http.post("/admin/login", headers=forged,
                     data={"password": password}).status_code == 503
    page = client.get("/admin/login")
    csrf = client.cookies.get(admin_feedback._LOGIN_CSRF)
    assert csrf
    wrong = client.post("/admin/login", data={"username": "unknown-reviewer",
                                             "password": secrets.token_urlsafe(12),
                                             "csrf_token": csrf},
                        headers={"Origin": "https://testserver"})
    assert wrong.status_code == 401
    assert password not in wrong.text and password_hash not in wrong.text
    assert password not in str(wrong.url) and password_hash not in str(wrong.url)
    assert password not in page.text and password_hash not in page.text


def test_all_admin_writes_require_csrf_and_feedback_is_not_enumerable(
    setup: tuple[TestClient, Any, Path, str],
) -> None:
    client, wa, _, password = setup
    job_id = _job(wa, count=1)
    token = _login(client, password)
    assert _save(client, job_id, "f0", "other", "Private synthetic comment").status_code == 303
    feedback_id = admin_feedback.list_feedback()[0]["id"]
    unauthorized = TestClient(wa.app, base_url="https://testserver")
    assert unauthorized.get("/admin/feedback").status_code == 403
    for target in (feedback_id, secrets.token_urlsafe(16)):
        result = unauthorized.post(f"/admin/feedback/{target}",
                                   data={"action": "delete", "confirm_delete": "yes"},
                                   headers={"Origin": "https://testserver"})
        assert result.status_code == 403
        assert "Private synthetic comment" not in result.text
    csrf = _csrf(token)
    assert client.post(f"/admin/feedback/{feedback_id}",
                       data={"action": "delete", "confirm_delete": "yes"},
                       headers={"Origin": "https://testserver"}).status_code == 403
    assert client.post(f"/admin/feedback/{feedback_id}",
                       data={"action": "delete", "confirm_delete": "yes",
                             "csrf_token": csrf},
                       headers={"Origin": "https://elsewhere.invalid"}).status_code == 403
    assert client.post("/admin/logout", data={"ignored": "1"},
                       headers={"Origin": "https://testserver"}).status_code == 403
    assert len(admin_feedback.list_feedback()) == 1
    injected = client.get("/admin/feedback", params={"rule_id": "P011' OR 1=1 --"})
    assert injected.status_code == 200 and "0 saved records shown" in injected.text


def test_database_path_permissions_and_links_fail_closed(
    setup: tuple[TestClient, Any, Path, str], monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _, wa, _, _ = setup
    unsafe = tmp_path / "world-readable"
    unsafe.mkdir(mode=0o755)
    monkeypatch.setenv("NJIT_AUDITOR_ADMIN_DB_PATH", str(unsafe / "feedback.sqlite3"))
    with pytest.raises(ValueError, match="owner-only"):
        admin_feedback.list_feedback()
    assert not (unsafe / "feedback.sqlite3").exists()
    link = tmp_path / "linked.sqlite3"
    link.symlink_to(tmp_path / "target.sqlite3")
    monkeypatch.setenv("NJIT_AUDITOR_ADMIN_DB_PATH", str(link))
    with pytest.raises(ValueError, match="symlink"):
        admin_feedback.list_feedback()
    monkeypatch.setenv("NJIT_AUDITOR_ADMIN_DB_PATH", str(wa.RUNTIME_DIR / "feedback.sqlite3"))
    with pytest.raises(ValueError, match="outside the repository and audit runtime"):
        admin_feedback.list_feedback()


def test_failed_migration_rolls_back_without_touching_prior_rows(
    setup: tuple[TestClient, Any, Path, str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, _, configured, _ = setup
    db_path = configured.parent / "broken-v1.sqlite3"
    monkeypatch.setenv("NJIT_AUDITOR_ADMIN_DB_PATH", str(db_path))
    marker = secrets.token_urlsafe(16)
    with sqlite3.connect(db_path) as db:
        db.execute("CREATE TABLE feedback (id TEXT PRIMARY KEY, marker TEXT NOT NULL)")
        db.execute("INSERT INTO feedback VALUES (?, ?)", (marker, "synthetic"))
        db.execute("PRAGMA user_version=1")
    with pytest.raises(sqlite3.Error):
        admin_feedback.list_feedback()
    with sqlite3.connect(db_path) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 1
        row = db.execute("SELECT marker FROM feedback WHERE id=?", (marker,)).fetchone()
        assert row is not None and row[0] == "synthetic"
        migrated = db.execute(
            "SELECT name FROM sqlite_master WHERE name='feedback_v2'"
        ).fetchone()
        assert migrated is None


def test_session_secrets_are_not_stored(
    setup: tuple[TestClient, Any, Path, str],
) -> None:
    client, wa, db_path, password = setup
    job_id = _job(wa, count=1)
    token = _login(client, password)
    csrf = _csrf(token)
    assert _save(client, job_id, "f0", "other", "Preserved synthetic note").status_code == 303
    with sqlite3.connect(db_path) as db:
        columns = {row[1] for row in db.execute("PRAGMA table_info(sessions)")}
        assert columns == {"token_hash", "admin_id", "expires_at"}
        stored = db.execute("SELECT token_hash FROM sessions").fetchone()[0]
        assert stored != token and stored != csrf
    data = db_path.read_bytes()
    assert token.encode() not in data and csrf.encode() not in data
    assert password.encode() not in data
    assert os.environ["NJIT_AUDITOR_ADMIN_SESSION_KEY"].encode() not in data
    assert client.get("/admin/feedback").status_code == 200


def test_two_accounts_attribution_revocation_and_legacy_hash_denial(
    setup: tuple[TestClient, Any, Path, str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, wa, db_path, first_password = setup
    job_id = _job(wa, count=1)
    first_username = admin_accounts.list_accounts()[0]["username"]
    second_password = secrets.token_urlsafe(24)
    second_id = admin_accounts.create_account("Second.Reviewer", second_password, "Second")
    first_id = admin_accounts.list_accounts()[0]["id"]
    assert admin_accounts.list_accounts()[1]["id"] == second_id
    first_token = _login(client, first_password, first_username.upper())
    assert _save(client, job_id, "f0", "true_positive", "First note").status_code == 303
    second = TestClient(wa.app, base_url="https://testserver")
    second_token = _login(second, second_password, "SECOND.REVIEWER")
    assert _save(second, job_id, "f0", "false_positive", "Second note").status_code == 303
    records = {item["comment"]: item for item in admin_feedback.list_feedback()}
    assert len(records) == 2
    assert records["First note"]["submitted_by_admin_id"] == first_id
    assert records["Second note"]["submitted_by_admin_id"] == second_id
    assert records["Second note"]["submitted_by_username"] == "second.reviewer"
    feedback_id = records["First note"]["id"]
    response = second.post(
        f"/admin/feedback/{feedback_id}",
        data={"csrf_token": _csrf(second_token), "status": "Resolved", "comment": "Updated"},
        headers={"Origin": "https://testserver"}, follow_redirects=False,
    )
    assert response.status_code == 303
    edited = next(item for item in admin_feedback.list_feedback() if item["id"] == feedback_id)
    assert edited["submitted_by_admin_id"] == first_id
    assert edited["last_modified_by_admin_id"] == second_id
    assert edited["resolved_by_admin_id"] == second_id
    admin_accounts.set_active("SECOND.REVIEWER", False)
    assert second.get("/admin/feedback").status_code == 403
    disabled_login = TestClient(wa.app, base_url="https://testserver")
    disabled_login.get("/admin/login")
    disabled_csrf = disabled_login.cookies.get(admin_feedback._LOGIN_CSRF)
    assert disabled_login.post(
        "/admin/login", data={"username": "second.reviewer", "password": second_password,
                              "csrf_token": disabled_csrf},
        headers={"Origin": "https://testserver"},
    ).status_code == 401
    with sqlite3.connect(db_path) as db:
        remaining = db.execute(
            "SELECT count(*) FROM sessions WHERE admin_id=?", (second_id,)
        ).fetchone()[0]
        assert remaining == 0
    admin_accounts.set_active("second.reviewer", True)
    _login(second, second_password, "second.reviewer")
    new_password = secrets.token_urlsafe(24)
    admin_accounts.reset_password("second.reviewer", new_password)
    assert second.get("/admin/feedback").status_code == 403
    _login(second, new_password, "second.reviewer")
    assert second.get("/admin/feedback").status_code == 200
    assert client.get("/admin/feedback").status_code == 200
    assert first_token != second_token
    delete_response = second.post(
        f"/admin/feedback/{feedback_id}",
        data={"csrf_token": _csrf(second.cookies.get(admin_feedback._COOKIE, "")),
              "action": "delete", "confirm_delete": "yes"},
        headers={"Origin": "https://testserver"}, follow_redirects=False,
    )
    assert delete_response.status_code == 303
    with sqlite3.connect(db_path) as db:
        tombstone = db.execute(
            "SELECT deleted_by_admin_id FROM feedback_deletions WHERE feedback_id=?",
            (feedback_id,),
        ).fetchone()
    assert tombstone is not None and tombstone[0] == second_id
    monkeypatch.setenv("NJIT_AUDITOR_ADMIN_PASSWORD_HASH", "legacy-shared-hash")
    anonymous = TestClient(wa.app, base_url="https://testserver")
    csrf_page = anonymous.get("/admin/login")
    assert csrf_page.status_code == 200
    csrf = anonymous.cookies.get(admin_feedback._LOGIN_CSRF)
    assert anonymous.post(
        "/admin/login", data={"username": "unknown", "password": first_password,
                              "csrf_token": csrf},
        headers={"Origin": "https://testserver"},
    ).status_code == 401


def test_version_3_migration_preserves_feedback_and_revokes_shared_sessions(
    setup: tuple[TestClient, Any, Path, str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, _, configured, _ = setup
    db_path = configured.parent / "legacy-v3.sqlite3"
    feedback_id = secrets.token_urlsafe(16)
    old_session = secrets.token_urlsafe(32)
    with sqlite3.connect(db_path) as db:
        db.executescript("""
            CREATE TABLE feedback (
                id TEXT PRIMARY KEY, audit_ref TEXT NOT NULL, finding_ref TEXT NOT NULL,
                rule_id TEXT NOT NULL, issue_type TEXT NOT NULL, pdf_page INTEGER,
                original_confidence TEXT NOT NULL, classification TEXT NOT NULL,
                comment TEXT NOT NULL, status TEXT NOT NULL, context TEXT NOT NULL,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL, resolved_at TEXT
            );
            CREATE TABLE sessions (token_hash TEXT PRIMARY KEY, expires_at INTEGER NOT NULL);
            CREATE TABLE login_attempts (
                bucket TEXT PRIMARY KEY, count INTEGER NOT NULL, reset_at INTEGER NOT NULL
            );
            PRAGMA user_version=3;
        """)
        db.execute("INSERT INTO feedback VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            feedback_id, "old-audit", "f0", "P011", "margin_violation", 1, "medium",
            "other", "Legacy review", "Open", "Rule P011", "2026-01-01T00:00:00+00:00",
            "2026-01-01T00:00:00+00:00", None,
        ))
        db.execute("INSERT INTO sessions VALUES (?,?)", (old_session, 9999999999))
    monkeypatch.setenv("NJIT_AUDITOR_ADMIN_DB_PATH", str(db_path))
    rows = admin_feedback.list_feedback()
    assert len(rows) == 1 and rows[0]["id"] == feedback_id
    assert rows[0]["submitted_by_admin_id"] is None
    assert rows[0]["last_modified_by_admin_id"] is None
    with sqlite3.connect(db_path) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 5
        assert db.execute("SELECT count(*) FROM sessions").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM admins").fetchone()[0] == 0
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_account_cli_requires_tty_and_never_exposes_password(
    setup: tuple[TestClient, Any, Path, str], monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _, _, _, password = setup
    monkeypatch.setattr(admin_accounts.sys.stdin, "isatty", lambda: False)
    assert admin_accounts.main(["create", "thirdreviewer"]) == 1
    assert "interactive terminal" in capsys.readouterr().err
    assert admin_accounts.main(["list"]) == 0
    output = capsys.readouterr()
    assert password not in output.out and "$argon2" not in output.out
    assert "thirdreviewer" not in output.out
    with pytest.raises(ValueError):
        admin_accounts.create_account("bad username", secrets.token_urlsafe(24))
    with pytest.raises(sqlite3.IntegrityError):
        existing = admin_accounts.list_accounts()[0]["username"]
        admin_accounts.create_account(existing.upper(), secrets.token_urlsafe(24))
