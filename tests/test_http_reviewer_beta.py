"""Synthetic public audit and opt-in HTTP reviewer workflow."""

from __future__ import annotations

import secrets
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pymupdf
import pytest
from fastapi.testclient import TestClient

from njit_auditor import admin_accounts, admin_feedback, web_app


@pytest.fixture
def reviewer_site(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[TestClient, Path]]:
    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    runtime = tmp_path / "audits"
    runtime.mkdir()
    db_path = private / "feedback.sqlite3"
    monkeypatch.setenv("NJIT_AUDITOR_ADMIN_DB_PATH", str(db_path))
    monkeypatch.setenv("NJIT_AUDITOR_ADMIN_SESSION_KEY", secrets.token_urlsafe(32))
    monkeypatch.setenv("NJIT_AUDITOR_REVIEWER_HTTP_BETA_ENABLED", "1")
    monkeypatch.delenv("NJIT_AUDITOR_ADMIN_ENABLED", raising=False)
    monkeypatch.setattr(web_app, "RUNTIME_DIR", runtime)
    with web_app._jobs_lock:
        saved = dict(web_app._jobs)
        web_app._jobs.clear()
    client = TestClient(web_app.app, base_url="http://testserver", raise_server_exceptions=False)
    try:
        yield client, db_path
    finally:
        client.close()
        with web_app._jobs_lock:
            web_app._jobs.clear()
            web_app._jobs.update(saved)


def _login(client: TestClient, username: str, password: str, *, next_url: str = "/"):
    page = client.get("/reviewer/login", params={"next": next_url})
    assert page.status_code == 200 and "Reviewer Access" in page.text
    csrf = client.cookies.get(admin_feedback._REVIEWER_LOGIN_CSRF)
    return client.post("/reviewer/login", data={
        "username": username, "password": password, "csrf_token": csrf, "next": next_url,
    }, headers={"Origin": "http://testserver"}, follow_redirects=False)


def test_http_reviewer_complete_synthetic_audit_workflow(
    reviewer_site: tuple[TestClient, Path],
) -> None:
    client, db_path = reviewer_site
    password = secrets.token_urlsafe(24)
    account_id = admin_accounts.create_account("ester", password, role="reviewer")
    admin_accounts.create_account("soroush", secrets.token_urlsafe(24), role="reviewer")
    operator_password = secrets.token_urlsafe(24)
    admin_accounts.create_account("operator", operator_password)

    doc = pymupdf.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((72, 100), "Synthetic thesis audit text for reviewer testing.")
    page.add_text_annot((100, 200), "Synthetic annotation")
    pdf = doc.tobytes()
    doc.close()
    anonymous = client.post("/audits", files={
        "file": ("synthetic.pdf", pdf, "application/pdf"),
    }, follow_redirects=False)
    assert anonymous.status_code == 303
    job_url = anonymous.headers["location"]
    job_id = job_url.rsplit("/", 1)[1]
    job = web_app._get_job(job_id)
    assert job is not None and job.state == "complete" and job.findings
    finding_id = str(job.findings[0]["finding_id"])
    page = client.get(job_url)
    assert page.status_code == 200
    assert "Reviewer Access" in page.text
    assert f"Reviewer feedback for {finding_id}" not in page.text
    form_url = f"/audits/{job_id}/feedback/{finding_id}"
    assert client.post(form_url, data={"classification": "other"},
                       headers={"Origin": "http://testserver"}).status_code == 403

    wrong = _login(client, "ester", secrets.token_urlsafe(24), next_url=job_url)
    assert wrong.status_code == 401
    assert password not in wrong.text
    assert _login(client, "operator", operator_password).status_code == 401
    login = _login(client, "ester", password, next_url=job_url)
    assert login.status_code == 303 and login.headers["location"] == job_url
    assert "httponly" in login.headers["set-cookie"].lower()
    assert "samesite=strict" in login.headers["set-cookie"].lower()
    assert "secure" not in login.headers["set-cookie"].lower()
    token = client.cookies.get(admin_feedback._REVIEWER_COOKIE)
    assert token
    results = client.get(job_url)
    assert f"Reviewer feedback for {finding_id}" in results.text
    assert 'value="true_positive"' in results.text
    assert 'value="false_positive"' in results.text
    assert 'value="unclear"' in results.text
    assert 'value="other"' in results.text
    assert "Feedback dashboard" not in results.text

    comment = "Synthetic reviewer observation, not dissertation text."
    csrf = admin_feedback._session_csrf(token)
    assert client.post(form_url, data={"csrf_token": csrf, "classification": "unclear",
                                       "comment": comment},
                       headers={"Origin": "http://elsewhere.invalid"}).status_code == 403
    saved = client.post(form_url, data={"csrf_token": csrf, "classification": "unclear",
                                        "comment": comment},
                        headers={"Origin": "http://testserver"}, follow_redirects=False)
    assert saved.status_code == 303
    with sqlite3.connect(db_path) as db:
        row = db.execute("""SELECT f.audit_ref,f.finding_ref,f.classification,f.comment,
            f.created_at,a.username,a.role FROM feedback f JOIN admins a
            ON a.id=f.submitted_by_admin_id WHERE f.audit_ref=?""", (job_id,)).fetchone()
        assert row is not None
        assert row[0:4] == (job_id, finding_id, "unclear", comment)
        assert row[4] and row[5:] == ("ester", "reviewer")
        assert db.execute("SELECT count(*) FROM feedback").fetchone()[0] == 1
        stored_id = db.execute("SELECT id FROM admins WHERE username='ester'").fetchone()[0]
        assert stored_id == account_id
        assert db.execute("PRAGMA user_version").fetchone()[0] == 5

    assert client.get("/admin/feedback").status_code == 403
    assert client.post("/admin/feedback/anything", data={"action": "delete"},
                       headers={"Origin": "http://testserver"}).status_code == 403
    assert client.get("/admin/login", headers={"X-Forwarded-Proto": "https"}).status_code == 503
    for extension in ("json", "markdown", "text", "student-report.pdf"):
        export = client.get(f"/audits/{job_id}/download/{extension}")
        assert export.status_code == 200
        assert comment.encode() not in export.content
        if extension == "student-report.pdf":
            with pymupdf.open(stream=export.content, filetype="pdf") as report:
                assert comment not in " ".join(page.get_text() for page in report)
    public = TestClient(web_app.app, base_url="http://testserver")
    try:
        assert public.get(job_url).status_code == 200
        assert comment not in public.get(job_url).text
        assert public.post(form_url, data={"classification": "other"},
                           headers={"Origin": "http://testserver"}).status_code == 403
    finally:
        public.close()


def test_http_reviewer_disabled_expiry_and_role_boundary(
    reviewer_site: tuple[TestClient, Path], monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, db_path = reviewer_site
    password = secrets.token_urlsafe(24)
    admin_accounts.create_account("soroush", password, role="reviewer")
    monkeypatch.delenv("NJIT_AUDITOR_REVIEWER_HTTP_BETA_ENABLED")
    assert "Reviewer Access" not in client.get("/").text
    assert client.get("/reviewer/login").status_code == 503
    monkeypatch.setenv("NJIT_AUDITOR_REVIEWER_HTTP_BETA_ENABLED", "1")
    assert _login(client, "soroush", password).status_code == 303
    token = client.cookies.get(admin_feedback._REVIEWER_COOKIE)
    assert token
    with sqlite3.connect(db_path) as db:
        db.execute("UPDATE sessions SET expires_at=0 WHERE token_hash=?",
                   (admin_feedback._token_hash(token),))
    assert "Reviewer Access" in client.get("/").text
    assert client.get("/admin/feedback").status_code == 403
    https = TestClient(web_app.app, base_url="https://testserver")
    try:
        monkeypatch.setenv("NJIT_AUDITOR_ADMIN_ENABLED", "1")
        monkeypatch.setenv("NJIT_AUDITOR_ADMIN_HTTPS_VERIFIED", "1")
        https.cookies.set(admin_feedback._COOKIE, token)
        assert https.get("/admin/feedback").status_code == 403
        page = https.get("/admin/login")
        csrf = https.cookies.get(admin_feedback._LOGIN_CSRF)
        assert page.status_code == 200 and csrf
        assert https.post("/admin/login", data={"username": "soroush",
                                                  "password": password, "csrf_token": csrf},
                          headers={"Origin": "https://testserver"}).status_code == 401
    finally:
        https.close()


def test_reviewer_account_name_is_limited(reviewer_site: tuple[TestClient, Path]) -> None:
    with pytest.raises(ValueError, match="soroush or ester"):
        admin_accounts.create_account("thirdperson", secrets.token_urlsafe(24), role="reviewer")


def test_existing_v4_admin_database_gains_role_without_losing_accounts(
    reviewer_site: tuple[TestClient, Path],
) -> None:
    _, db_path = reviewer_site
    password = secrets.token_urlsafe(24)
    account_id = admin_accounts.create_account("operator", password)
    feedback_id = secrets.token_urlsafe(16)
    with sqlite3.connect(db_path) as db:
        db.execute("""INSERT INTO feedback (
            id,audit_ref,finding_ref,rule_id,issue_type,original_confidence,
            classification,comment,context,created_at,updated_at,submitted_by_admin_id)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""", (
                feedback_id, "synthetic-job", "f7", "P011", "margin_violation", "medium",
                "unclear", "Preserved synthetic feedback", "Rule P011",
                "2026-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00", account_id,
            ))
        db.execute("ALTER TABLE admins DROP COLUMN role")
        db.execute("PRAGMA user_version=4")
    with admin_feedback._connection() as db:
        row = db.execute("SELECT id,role,password_hash FROM admins WHERE username='operator'")
        account = row.fetchone()
        assert account is not None and account["id"] == account_id
        assert account["role"] == "admin"
        assert admin_accounts._HASHER.verify(account["password_hash"], password)
        assert db.execute("PRAGMA user_version").fetchone()[0] == 5
        feedback = db.execute("SELECT finding_ref,comment,submitted_by_admin_id "
                              "FROM feedback WHERE id=?", (feedback_id,)).fetchone()
        assert tuple(feedback) == ("f7", "Preserved synthetic feedback", account_id)
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
