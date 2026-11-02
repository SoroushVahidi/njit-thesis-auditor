"""Real loopback/browser regressions using synthetic PDFs and disposable profiles."""

from __future__ import annotations

import pytest
from desktop_session_support import csrf_token, desktop, wait_state
from fastapi.testclient import TestClient
from test_offline_desktop import _pdf

from njit_auditor import offline_app


@pytest.fixture
def browser():
    api = pytest.importorskip("playwright.sync_api")
    with api.sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        yield browser
        browser.close()


def upload(context, server, filename: str) -> str:
    response = context.request.post(
        server.origin + "/audits",
        headers={"Origin": server.origin},
        multipart={
            "csrf_token": server.csrf,
            "file": {"name": filename, "mimeType": "application/pdf", "buffer": _pdf("normal")},
        },
        max_redirects=0,
    )
    assert response.status == 303
    return response.headers["location"]


def test_cancel_pending_and_running_preserves_browser_session(tmp_path, browser):
    with desktop(tmp_path / "single", delayed=True) as server, browser.new_context() as context:
        page = context.new_page()
        assert page.goto(server.url).status == 200
        initial_cookies = context.cookies()
        # Occupy both worker slots; the third request must remain pending.
        first = upload(context, server, "cancel-running.pdf")
        second = upload(context, server, "cancel-blocker.pdf")
        wait_state(context.request, server.origin, first, {"running"})
        wait_state(context.request, server.origin, second, {"running"})
        queued = upload(context, server, "cancel-pending.pdf")
        wait_state(context.request, server.origin, queued, {"pending"})
        cancelled = []
        for job in (queued, first, second):
            assert page.goto(server.origin + job).status == 200
            page.get_by_role("button", name="Cancel audit", exact=True).click()
            status = wait_state(context.request, server.origin, job, {"failed", "cancelled"})
            assert server.process.poll() is None
            assert context.cookies() == initial_cookies
            assert context.request.get(server.origin + "/help").status == 200
            assert context.request.get(server.origin + "/rules").status == 200
            page.get_by_text("Audit canceled", exact=True).wait_for(timeout=10000)
            cancelled.append((status["state"], page.content()))
        assert page.goto(server.origin).status == 200
        recovered = upload(context, server, "recovery.pdf")
        assert wait_state(context.request, server.origin, recovered, {"complete", "failed"})[
            "state"
        ] == "complete"
        for state, html in cancelled:
            assert state == "cancelled"
            assert "Audit canceled" in html and "Audit another PDF" in html
            assert "Something went wrong" not in html


def test_two_profiles_share_browser_without_overwriting_sessions(tmp_path, browser):
    with desktop(tmp_path / "first") as first, desktop(tmp_path / "second") as second:
        assert first.origin != second.origin
        with browser.new_context() as context:
            page_a, page_b = context.new_page(), context.new_page()
            assert page_a.goto(first.url).status == 200
            assert page_b.goto(second.url).status == 200
            assert page_a.reload().status == 200
            assert page_b.reload().status == 200
            cookies = context.cookies()
            assert len(cookies) == 2
            assert len({cookie["name"] for cookie in cookies}) == 2
            assert all(cookie["httpOnly"] and cookie["sameSite"] == "Strict" for cookie in cookies)
            for server in (first, second):
                job = upload(context, server, "synthetic.pdf")
                assert wait_state(context.request, server.origin, job, {"complete", "failed"})[
                    "state"
                ] == "complete"
            # Re-authenticating either tab must not displace the other session.
            assert page_a.goto(first.url).status == 200
            assert page_b.reload().status == 200
            for origin, token in [(second.origin, first.csrf), (first.origin, second.csrf)]:
                response = context.request.post(
                    first.origin + "/audits/synthetic/cancel",
                    headers={"Origin": origin}, form={"csrf_token": token},
                    max_redirects=0,
                )
                assert response.status == 403
            # A token from the other server is never an acceptable replacement.
            first_cookie = next(c for c in cookies if c["value"] in first.client.cookies.values())
            second_cookie = next(c for c in cookies if c["value"] in second.client.cookies.values())
            context.add_cookies([{**first_cookie, "value": second_cookie["value"]}])
            assert page_a.reload().status == 403
            assert page_a.get_by_role(
                "heading", name="This auditor session is unavailable"
            ).is_visible()
            assert page_b.reload().status == 200
            assert page_a.goto(first.url).status == 200
            assert csrf_token(page_a.content()) == first.csrf


def test_polling_recovers_after_browser_cookie_loss_without_cancelling_audit(tmp_path, browser):
    with desktop(tmp_path / "lost-cookie", delayed=True) as server:
        with browser.new_context() as context:
            page = context.new_page()
            page.goto(server.url)
            job = upload(context, server, "cancel-cookie-loss.pdf")
            wait_state(context.request, server.origin, job, {"running"})
            assert page.goto(server.origin + job).status == 200
            context.clear_cookies()
            page.get_by_role("heading", name="This auditor session is unavailable").wait_for(
                timeout=10000
            )
            assert server.process.poll() is None
            assert server.client.get(job + "/status").json()["state"] == "running"
            # Only the existing launch ticket restores access, not the recovery page.
            assert page.goto(server.url).status == 200
            assert page.goto(server.origin + job).status == 200
            page.get_by_role("button", name="Cancel audit", exact=True).click()
            page.get_by_text("Audit canceled", exact=True).wait_for(timeout=10000)


@pytest.mark.parametrize("reason", ["missing", "invalid", "expired"])
def test_session_recovery_is_html_for_navigation_and_json_for_api(tmp_path, monkeypatch, reason):
    root = tmp_path / "app"
    offline_app.prepare_local_storage(root)
    app = offline_app.create_offline_app(port=17391, data_root=root, launch_ticket="test-ticket")
    with TestClient(app, base_url="http://127.0.0.1:17391") as client:
        if reason != "missing":
            assert client.get("/_session/start?ticket=test-ticket").status_code == 200
        if reason == "invalid":
            for cookie in client.cookies.jar:
                cookie.value = "wrong-session"
        if reason == "expired":
            real_clock = offline_app.time.monotonic
            monkeypatch.setattr(offline_app.time, "monotonic", lambda: real_clock() + 40000)
        for method, path in [("GET", "/"), ("GET", "/audits/synthetic"),
                             ("POST", "/audits/synthetic/cancel")]:
            response = client.request(
                method, path,
                headers={"Accept": "text/html", "Origin": "http://127.0.0.1:17391"},
            )
            assert response.status_code == 403
            assert response.headers["content-type"].startswith("text/html")
            assert "Open auditor" in response.text
            assert "session" in response.text.lower()
            assert "test-ticket" not in response.text
            assert app.state.csrf_token not in response.text
            assert "Set-Cookie" not in response.headers
            assert response.headers["Cache-Control"] == "no-store"
            assert response.headers["Referrer-Policy"] == "no-referrer"
            assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
        response = client.get("/audits/synthetic/status", headers={"Accept": "application/json"})
        assert response.status_code == 403
        assert response.json() == {"error": "desktop session expired or unavailable"}
        response = client.get(
            "/audits/synthetic/status",
            headers={"Accept": "text/html", "Sec-Fetch-Mode": "cors"},
        )
        assert response.status_code == 403
        assert response.headers["content-type"].startswith("application/json")
        # Recovery must never relax any earlier request-origin checks.
        for headers in ({"Host": "evil.example"}, {"Origin": "http://evil.example"},
                        {"Sec-Fetch-Site": "cross-site"}):
            response = client.get("/", headers={"Accept": "text/html", **headers})
            assert response.status_code == 403
            assert response.headers["content-type"].startswith("application/json")
        assert client.get("/_session/start?ticket=wrong").status_code == 403
