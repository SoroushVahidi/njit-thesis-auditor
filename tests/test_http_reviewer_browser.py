"""Browser coverage for the HTTP reviewer beta using synthetic findings only."""

from __future__ import annotations

import os
import re
import secrets
import socket
import sqlite3
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path

import httpx
import pytest
from test_about_browser import guard_external

ROOT = Path(__file__).resolve().parents[1]
JOB_ID = "synthetic-reviewer-browser"
BOOTSTRAP = '''import os, sys
from datetime import datetime, timezone
from pathlib import Path
import uvicorn
from njit_auditor import admin_accounts
from njit_auditor import web_app as web
if not admin_accounts.list_accounts():
    admin_accounts.create_account(
        'ester', os.environ.pop('NJIT_TEST_REVIEWER_PASSWORD'), role='reviewer')
job_id = sys.argv[2]
runtime = Path(os.environ['NJIT_AUDITOR_WEB_RUNTIME_DIR'])
(runtime / job_id).mkdir(parents=True, exist_ok=True)
finding = {
    'finding_id': 'f0', 'rule_id': 'P011', 'issue_type': 'margin_violation',
    'page': 1, 'confidence_level': 'high', 'confidence_label': 'High',
    'category': 'Margins', 'student_topic': 'Margins',
    'student_summary': 'Synthetic margin finding', 'problem_anchor': 'problem-1',
    'problem_number': 1, 'technical_details': [], 'action_kind': 'explanation',
}
web._set_job(web.JobState(job_id=job_id, state='complete',
    created_at=datetime.now(timezone.utc).isoformat(), file_name='synthetic.pdf',
    findings=[finding], finding_count=1))
uvicorn.run(web.app, host='127.0.0.1', port=int(sys.argv[1]),
            proxy_headers=False, access_log=False, log_level='warning')
'''


@contextmanager
def reviewer_site(directory: Path, password: str | None = None):
    private = directory / "private"
    private.mkdir(mode=0o700, exist_ok=True)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    origin = f"http://127.0.0.1:{port}"
    password = password or secrets.token_urlsafe(24)
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src"),
           "NJIT_AUDITOR_REVIEWER_HTTP_BETA_ENABLED": "1",
           "NJIT_AUDITOR_ADMIN_SESSION_KEY": secrets.token_urlsafe(32),
           "NJIT_TEST_REVIEWER_PASSWORD": password,
           "NJIT_AUDITOR_ADMIN_DB_PATH": str(private / "feedback.sqlite3"),
           "NJIT_AUDITOR_WEB_RUNTIME_DIR": str(directory / "jobs")}
    with (directory / "server.log").open("wb") as log:
        process = subprocess.Popen(
            [sys.executable, "-c", BOOTSTRAP, str(port), JOB_ID],
            cwd=ROOT, env=env, stdout=log, stderr=log,
        )
        try:
            deadline = time.monotonic() + 20
            while True:
                assert process.poll() is None, "Isolated reviewer server exited"
                try:
                    health = httpx.get(origin + "/healthz", timeout=1, trust_env=False)
                    if health.status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                assert time.monotonic() < deadline, "Isolated reviewer server did not start"
                time.sleep(0.05)
            yield origin, password
        finally:
            process.terminate()
            process.wait(timeout=15)


def test_reviewer_browser_submits_without_history(tmp_path: Path) -> None:
    api = pytest.importorskip("playwright.sync_api")
    with reviewer_site(tmp_path) as (origin, password), api.sync_playwright() as runner:
        browser = runner.chromium.launch()
        try:
            context = browser.new_context(viewport={"width": 390, "height": 844})
            attempts = guard_external(context)
            page = context.new_page()
            audit_url = f"{origin}/audits/{JOB_ID}"
            assert page.goto(audit_url).status == 200
            assert page.locator("form.admin-feedback").count() == 0
            page.get_by_label("Site navigation").get_by_role(
                "link", name="Reviewer Access"
            ).click()
            page.get_by_label("Username").fill("ester")
            page.get_by_label("Password").fill(password)
            page.get_by_role("button", name="Log in").click()
            page.goto(audit_url)
            create = page.locator('form[action$="/feedback/f0"]')
            create.locator('input[value="unclear"]').check()
            create.get_by_label("Additional comments (optional)").fill("First synthetic review")
            create.get_by_role("button", name="Save Feedback").click()
            assert page.get_by_text("Feedback saved.").is_visible()
            assert page.get_by_text("First synthetic review").count() == 0
            page.reload()
            assert page.get_by_text("First synthetic review").count() == 0
            assert page.get_by_text("Edit this feedback").count() == 0
            assert page.get_by_role("link", name="My Feedback").count() == 0
            assert context.request.get(origin + "/reviewer/feedback").status == 404
            assert context.request.post(origin + "/reviewer/feedback/unknown").status == 404
            assert attempts == []
        finally:
            browser.close()
    with sqlite3.connect(tmp_path / "private" / "feedback.sqlite3") as db:
        assert db.execute("SELECT classification,comment FROM feedback").fetchone() == (
            "unclear", "First synthetic review",
        )


def test_reviewer_submission_survives_server_restart_without_history(tmp_path: Path) -> None:
    password = secrets.token_urlsafe(24)
    for run in range(2):
        with reviewer_site(tmp_path, password) as (origin, _):
            with httpx.Client(trust_env=False) as client:
                login = client.get(origin + "/reviewer/login")
                assert login.status_code == 200
                login_csrf = client.cookies.get("njit-reviewer-beta-login-csrf")
                assert login_csrf
                response = client.post(origin + "/reviewer/login", data={
                    "username": "ester", "password": password,
                    "csrf_token": login_csrf, "next": "/",
                }, headers={"Origin": origin})
                assert response.status_code == 303
                if run == 0:
                    audit = client.get(origin + f"/audits/{JOB_ID}")
                    assert audit.status_code == 200
                    csrf_match = re.search(r'name="csrf_token" value="([^"]+)"', audit.text)
                    assert csrf_match
                    saved = client.post(origin + f"/audits/{JOB_ID}/feedback/f0", data={
                        "csrf_token": csrf_match.group(1), "classification": "other",
                        "comment": "Persisted synthetic review",
                    }, headers={"Origin": origin})
                    assert saved.status_code == 303
                else:
                    assert client.get(origin + "/reviewer/feedback").status_code == 404
                    assert "Persisted synthetic review" not in client.get(
                        origin + f"/audits/{JOB_ID}"
                    ).text
    with sqlite3.connect(tmp_path / "private" / "feedback.sqlite3") as db:
        assert db.execute("SELECT comment FROM feedback").fetchone() == (
            "Persisted synthetic review",
        )
