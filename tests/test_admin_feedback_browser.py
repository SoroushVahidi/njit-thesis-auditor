"""Real local HTTPS browser review workflow with synthetic findings only."""

from __future__ import annotations

import os
import secrets
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path

import httpx
import pytest
from argon2 import PasswordHasher
from test_about_browser import guard_external

ROOT = Path(__file__).resolve().parents[1]
JOB_ID = "synthetic-admin-browser"
BOOTSTRAP = '''import os, sys
from datetime import datetime, timezone
from pathlib import Path
import uvicorn
from njit_auditor import web_app as web
job_id = sys.argv[3]
runtime = Path(os.environ['NJIT_AUDITOR_WEB_RUNTIME_DIR'])
(runtime / job_id).mkdir(parents=True)
findings = []
for index, confidence in enumerate(('low', 'high')):
    findings.append({
        'finding_id': f'f{index}', 'rule_id': 'P011',
        'issue_type': 'margin_violation', 'page': 1,
        'confidence_level': confidence, 'confidence_label': confidence.title(),
        'category': 'Margins', 'student_topic': 'Margins',
        'student_summary': f'Synthetic margin finding {index}',
        'problem_anchor': f'problem-{index + 1}',
        'problem_number': index + 1, 'technical_details': [],
        'action_kind': 'explanation',
    })
web._set_job(web.JobState(job_id=job_id, state='complete',
    created_at=datetime.now(timezone.utc).isoformat(), file_name='synthetic.pdf',
    findings=findings, finding_count=2))
uvicorn.run(web.app, host='127.0.0.1', port=int(sys.argv[1]),
            ssl_certfile=sys.argv[2] + '/cert.pem',
            ssl_keyfile=sys.argv[2] + '/key.pem',
            proxy_headers=False, access_log=False, log_level='warning')
'''


@contextmanager
def admin_site(directory: Path):
    private = directory / "private"
    private.mkdir(mode=0o700)
    subprocess.run([
        "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1",
        "-keyout", str(private / "key.pem"), "-out", str(private / "cert.pem"),
        "-subj", "/CN=127.0.0.1",
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    origin = f"https://127.0.0.1:{port}"
    password = secrets.token_urlsafe(24)
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src"),
           "NJIT_AUDITOR_ADMIN_ENABLED": "1",
           "NJIT_AUDITOR_ADMIN_HTTPS_VERIFIED": "1",
           "NJIT_AUDITOR_ADMIN_PASSWORD_HASH": PasswordHasher().hash(password),
           "NJIT_AUDITOR_ADMIN_DB_PATH": str(private / "feedback.sqlite3"),
           "NJIT_AUDITOR_WEB_RUNTIME_DIR": str(directory / "jobs")}
    with (directory / "server.log").open("wb") as log:
        process = subprocess.Popen(
            [sys.executable, "-c", BOOTSTRAP, str(port), str(private), JOB_ID],
            cwd=ROOT, env=env, stdout=log, stderr=log,
        )
        try:
            deadline = time.monotonic() + 20
            while True:
                assert process.poll() is None, "Isolated synthetic server exited"
                try:
                    if httpx.get(origin + "/healthz", timeout=1, verify=False,
                                 trust_env=False).status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                assert time.monotonic() < deadline, "Isolated synthetic server did not start"
                time.sleep(0.05)
            yield origin, password
        finally:
            process.terminate()
            process.wait(timeout=15)


def test_admin_review_browser_mobile_and_no_javascript_delete(tmp_path: Path) -> None:
    api = pytest.importorskip("playwright.sync_api")
    with admin_site(tmp_path) as (origin, password), api.sync_playwright() as runner:
        browser = runner.chromium.launch()
        try:
            context = browser.new_context(ignore_https_errors=True,
                                          viewport={"width": 390, "height": 844})
            attempts = guard_external(context)
            page = context.new_page()
            audit_url = f"{origin}/audits/{JOB_ID}"
            assert page.goto(audit_url).status == 200
            assert page.locator("form.admin-feedback").count() == 0
            page.get_by_role("link", name="Admin Login").click()
            page.get_by_label("Administrator password").fill(password)
            page.get_by_role("button", name="Log in").click()
            page.wait_for_url(origin + "/admin/feedback")
            assert page.get_by_role("link", name="Feedback dashboard").is_visible()
            assert page.get_by_role("button", name="Log out").is_visible()
            assert page.goto(audit_url).status == 200
            forms = page.locator("form.admin-feedback")
            assert forms.count() == 2
            assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
            for form in forms.all():
                assert form.locator('input[name="classification"]').count() == 4
                assert form.get_by_label("Additional comments (optional)").is_visible()
            page.locator("#sort-problems").select_option("confidence_desc")
            page.wait_for_url("**/audits/*?sort=confidence_desc")
            assert page.locator("form.admin-feedback").first.get_attribute("action").endswith("/f1")
            page.locator('[data-confidence-filter="high"]').click()
            assert page.locator("article.finding-card:visible").count() == 1
            assert page.locator("article.finding-card:visible form.admin-feedback").get_attribute(
                "action").endswith("/f1")
            page.locator("#filter-reset").click()
            assert page.locator("article.finding-card:visible").count() == 2
            first = page.locator('form[action$="/f0"]')
            first.locator('input[value="true_positive"]').check()
            first.get_by_label("Additional comments (optional)").fill("First synthetic review")
            first.get_by_role("button", name="Save Feedback").click()
            assert page.get_by_role("status").inner_text() == "Feedback saved."
            first = page.locator('form[action$="/f0"]')
            first.locator('input[value="unclear"]').check()
            first.get_by_label("Additional comments (optional)").fill("Second synthetic review")
            first.get_by_role("button", name="Save Feedback").click()
            second = page.locator('form[action$="/f1"]')
            second.locator('input[value="false_positive"]').check()
            second.get_by_role("button", name="Save Feedback").click()
            second = page.locator('form[action$="/f1"]')
            second.locator('input[value="other"]').check()
            second.get_by_label("Additional comments (optional)").fill("Fourth synthetic review")
            second.get_by_role("button", name="Save Feedback").click()
            assert page.get_by_text("2 saved administrator reviews").count() == 2
            page.get_by_role("link", name="Feedback dashboard").click()
            assert page.locator("article.card").count() == 4
            first_review = page.locator("article.card").first.locator("form").first
            first_review.locator('select[name="classification"]').select_option("true_positive")
            first_review.locator('select[name="status"]').select_option("Resolved")
            first_review.get_by_role("button", name="Save changes").click()
            assert page.get_by_text("Status: Resolved").count() == 1
            first_review = page.locator("article.card").first.locator("form").first
            first_review.locator('select[name="status"]').select_option("Open")
            first_review.get_by_role("button", name="Save changes").click()
            filters = page.locator('form[action="/admin/feedback"]')
            filters.locator('select[name="classification"]').select_option("true_positive")
            filters.get_by_role("button", name="Filter").click()
            assert page.locator("article.card").count() == 2
            no_js = browser.new_context(ignore_https_errors=True, java_script_enabled=False)
            no_js.add_cookies(context.cookies())
            no_js_page = no_js.new_page()
            no_js_page.goto(origin + "/admin/feedback")
            before = no_js_page.locator("article.card").count()
            delete_form = no_js_page.locator('form:has(button[value="delete"])').first
            delete_form.get_by_role("button", name="Delete feedback").click()
            assert no_js_page.locator("article.card").count() == before
            delete_form.locator('input[name="confirm_delete"]').check()
            delete_form.get_by_role("button", name="Delete feedback").click()
            assert no_js_page.locator("article.card").count() == before - 1
            outsider = browser.new_context(ignore_https_errors=True)
            outsider_page = outsider.new_page()
            outsider_page.goto(audit_url)
            assert outsider_page.locator("form.admin-feedback").count() == 0
            assert "First synthetic review" not in outsider_page.content()
            page.goto(origin)
            page.get_by_role("button", name="Log out").click()
            assert page.get_by_role("link", name="Admin Login").is_visible()
            assert attempts == []
        finally:
            browser.close()
    assert password not in (tmp_path / "server.log").read_text(encoding="utf-8")
