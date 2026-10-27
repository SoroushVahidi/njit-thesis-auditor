"""Real local launcher/browser flow with application egress denied (synthetic PDFs)."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx
import pytest

SERVER = r"""
import os, socket, webbrowser
from pathlib import Path

def deny(*args, **kwargs):
    raise AssertionError('Unexpected application network request')
socket.socket.connect = deny
socket.getaddrinfo = deny
socket.gethostbyname = deny
from njit_auditor import offline_launcher
offline_launcher.local_data_root = lambda: Path(os.environ["XDG_DATA_HOME"]) / "njit-thesis-auditor"
from njit_auditor.offline_launcher import run_desktop

def open_browser(url):
    path = Path(os.environ['DESKTOP_TEST_TICKET'])
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as output:
        output.write(url)
    return True
webbrowser.open = open_browser
if os.environ.get('DESKTOP_TEST_LIFECYCLE') == '1':
    import json,sys
    from njit_auditor import offline_app
    from njit_auditor.desktop_executor import DesktopExecutor,worker_command
    from njit_auditor.desktop_protocol import decode
    def command(request):
        payload=json.loads(request.read_text())
        if decode(payload['job'])['file_name']=='hang.pdf':
            code=("import os,pathlib,time; "
                  "f=pathlib.Path(os.environ['DESKTOP_TEST_PIDS']).open('a'); "
                  "f.write(str(os.getpid())+chr(10)); f.close(); time.sleep(60)")
            return [sys.executable,'-c',code]
        return worker_command(request)
    offline_app.DesktopExecutor=lambda:DesktopExecutor(deadline=5,command=command)
run_desktop(headless=True)
"""


@dataclass
class DesktopSession:
    process: Any = field(repr=False)
    url: str = field(repr=False)
    base: str


@pytest.fixture()
def desktop_process(tmp_path: Path) -> Any:
    root = Path(__file__).parents[1]
    ticket = tmp_path / "launch-ticket"
    env = {
        **os.environ,
        "PYTHONPATH": str(root / "src"),
        "XDG_DATA_HOME": str(tmp_path / "local-data"),
        "LOCALAPPDATA": str(tmp_path / "local-data"),
        "DESKTOP_TEST_TICKET": str(ticket),
    }
    log = (tmp_path / "launcher.log").open("w")
    process = subprocess.Popen(
        [sys.executable, "-c", SERVER], cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT
    )
    try:
        for _ in range(100):
            assert process.poll() is None, "Local launcher stopped before browser startup"
            if ticket.is_file():
                break
            time.sleep(0.05)
        else:
            pytest.fail("Local launcher did not open the browser")
        url = ticket.read_text()
        base = f"http://{urlsplit(url).netloc}"
        yield DesktopSession(process, url, base)
    finally:
        if process.poll() is None:
            process.terminate()
        process.wait(timeout=10)
        log.close()
        output = (tmp_path / "launcher.log").read_text()
        assert "ticket=" not in output and "Unexpected application network request" not in output
        assert str(tmp_path) not in output and "Synthetic body" not in output


@pytest.mark.parametrize("width,height", [(390, 844), (1440, 900)])
def test_local_launcher_corrected_cards_exports_and_quit(
    desktop_process: Any, tmp_path: Path, width: int, height: int
) -> None:
    from test_student_correction_subtypes import EXPECTED_ACTIONS, correction_pdfs

    playwright = pytest.importorskip("playwright.sync_api")
    process, url, base = desktop_process.process, desktop_process.url, desktop_process.base
    screenshots = Path(os.environ.get("NJIT_DESKTOP_SCREENSHOTS", str(tmp_path)))
    screenshots.mkdir(parents=True, exist_ok=True)
    with playwright.sync_playwright() as pw:
        if not Path(pw.chromium.executable_path).is_file():
            if os.environ.get("NJIT_REQUIRE_BROWSER") == "1":
                pytest.fail("Install Chromium with python -m playwright install chromium")
            pytest.skip("Chromium unavailable")
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": width, "height": height}, accept_downloads=True
        )
        external = []

        def local_only(route):
            if not route.request.url.startswith(base + "/"):
                external.append(route.request.url)
                route.abort()
            else:
                route.continue_()

        context.route("**/*", local_only)
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        assert httpx.get(base, timeout=3).status_code == 403
        page.goto(url)
        assert page.url == base + "/" and "ticket=" not in page.url
        page.keyboard.press("Tab")
        assert page.get_by_role("link", name="Skip to content").evaluate(
            "e => e === document.activeElement"
        )
        with page.expect_navigation(wait_until="domcontentloaded"):
            page.get_by_role("link", name="About", exact=True).click()
        assert "audited on this computer" in page.locator("#privacy").inner_text()
        assert "configured server" not in page.inner_text("body")
        page.screenshot(path=str(screenshots / f"about-{width}.png"), full_page=True)
        seen = set()
        for fixture in correction_pdfs(tmp_path / "pdfs"):
            page.goto(base)
            page.locator("#file").set_input_files(str(fixture))
            page.get_by_role("button", name="Start audit", exact=True).click()
            page.locator(".finding-card").first.wait_for(timeout=15000)
            audit_url = page.url
            for key, action in EXPECTED_ACTIONS.items():
                card = page.locator(".finding-card").filter(has_text=action).first
                if card.count():
                    seen.add(key)
                    details = card.locator("details.finding-explanation")
                    assert details.get_attribute("open") is None
                    card.scroll_into_view_if_needed()
                    page.screenshot(path=str(screenshots / f"{key[1]}-{width}.png"))
                    details.locator(":scope > summary").focus()
                    page.keyboard.press("Enter")
                    assert "Full correction:" in card.inner_text()
                    page.keyboard.press("Enter")
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            # Authenticated real exports; anonymous access stays denied.
            for suffix in ("json", "markdown", "text", "student-report.pdf"):
                path = audit_url + "/download/" + suffix
                assert httpx.get(path, timeout=3).status_code == 403
                response = context.request.get(path)
                assert response.status == 200
                if suffix.endswith("pdf"):
                    assert response.body().startswith(b"%PDF")
            link = page.locator(".finding-card__action a").first
            assert context.request.get(base + link.get_attribute("href")).status == 200
            page.locator("#filter-page").select_option(index=1)
            assert page.locator(".finding-card:visible").count() > 0
            page.locator("#filter-reset").click()
            with page.expect_navigation():
                page.locator("#sort-problems").select_option("confidence_desc")
            with page.expect_navigation(wait_until="domcontentloaded"):
                page.get_by_role("button", name="Delete this audit", exact=True).click()
            assert "Local audit data was deleted" in page.inner_text("body")
            assert context.request.get(audit_url + "/status").status == 404
        assert seen == set(EXPECTED_ACTIONS)
        # A corrupt PDF produces a safe failed state and allows another audit.
        page.locator("#file").set_input_files(
            {
                "name": "corrupt.pdf",
                "mimeType": "application/pdf",
                "buffer": b"%PDF-synthetic-corrupt",
            }
        )
        page.get_by_role("button", name="Start audit", exact=True).click()
        page.get_by_text("Audit could not complete", exact=True).wait_for(timeout=15000)
        assert str(tmp_path) not in page.inner_text("body")
        page.get_by_role("button", name="Quit", exact=True).click()
        process.wait(timeout=10)
        assert process.returncode == 0 and not errors and not external
        with socket.socket() as sock:
            assert sock.connect_ex(("127.0.0.1", urlsplit(base).port)) != 0
        for directory in (tmp_path / "local-data").rglob("audits"):
            assert not any(directory.iterdir())
        for directory in (tmp_path / "local-data").rglob("tmp"):
            assert not any(directory.iterdir())
        (screenshots / f"browser-{width}.json").write_text(
            json.dumps(
                {
                    "width": width,
                    "corrected_subtypes": len(seen),
                    "external_requests": external,
                    "javascript_errors": errors,
                    "launcher_exit_code": process.returncode,
                },
                indent=2,
            )
        )
        browser.close()


@pytest.mark.parametrize("width", [390, 1440])
def test_disabled_download_preview_fits(width, tmp_path, monkeypatch) -> None:
    from fastapi.testclient import TestClient

    from njit_auditor import desktop_download, web_app

    playwright = pytest.importorskip("playwright.sync_api")
    monkeypatch.setattr(
        desktop_download,
        "desktop_release",
        lambda: desktop_download.parse_release({"preview": True}),
    )
    html = TestClient(web_app.app).get("/").text
    with playwright.sync_playwright() as pw:
        if not Path(pw.chromium.executable_path).is_file():
            pytest.skip("Chromium unavailable")
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": width, "height": 900})
        page.set_content(html)
        section = page.locator("#desktop-download")
        assert section.get_by_role("button", name="Download Desktop App").is_disabled()
        assert section.get_by_role("link").count() == 0
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        section.scroll_into_view_if_needed()
        folder = Path(os.environ.get("NJIT_DESKTOP_SCREENSHOTS", str(tmp_path)))
        folder.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(folder / f"download-preview-{width}.png"))
        browser.close()


@pytest.fixture()
def bounded_desktop_process(request, monkeypatch, tmp_path):
    monkeypatch.setenv("DESKTOP_TEST_LIFECYCLE", "1")
    monkeypatch.setenv("DESKTOP_TEST_PIDS", str(tmp_path / "worker-pids"))
    return request.getfixturevalue("desktop_process")


def test_timeout_cancel_quit_and_reopen_via_real_browser(bounded_desktop_process, tmp_path):
    from test_offline_desktop import _pdf

    playwright = pytest.importorskip("playwright.sync_api")
    session = bounded_desktop_process
    with playwright.sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(session.url)

        def upload(name):
            page.goto(session.base)
            page.locator("#file").set_input_files(
                {
                    "name": name,
                    "mimeType": "application/pdf",
                    "buffer": _pdf("normal"),
                }
            )
            page.get_by_role("button", name="Start audit", exact=True).click()

        upload("hang.pdf")
        page.get_by_text("This audit took too long", exact=False).wait_for(timeout=15000)
        upload("normal.pdf")
        page.locator(".finding-card").first.wait_for(timeout=10000)
        upload("hang.pdf")
        page.get_by_role("button", name="Cancel audit", exact=True).click()
        page.get_by_text("This audit was cancelled", exact=False).wait_for(timeout=10000)
        upload("hang.pdf")
        page.get_by_role("button", name="Quit", exact=True).click()
        session.process.wait(timeout=5)
        assert session.process.returncode == 0
        for line in (tmp_path / "worker-pids").read_text().splitlines():
            with pytest.raises(ProcessLookupError):
                os.kill(int(line), 0)
        for folder in (tmp_path / "local-data").rglob("audits"):
            assert not any(folder.iterdir())
        ticket = tmp_path / "reopen-ticket"
        root = Path(__file__).parents[1]
        env = {
            **os.environ,
            "PYTHONPATH": str(root / "src"),
            "XDG_DATA_HOME": str(tmp_path / "local-data"),
            "LOCALAPPDATA": str(tmp_path / "local-data"),
            "DESKTOP_TEST_TICKET": str(ticket),
            "DESKTOP_TEST_LIFECYCLE": "0",
        }
        reopened = subprocess.Popen(
            [sys.executable, "-c", SERVER],
            cwd=root,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            for _ in range(100):
                assert reopened.poll() is None
                if ticket.is_file():
                    break
                time.sleep(0.05)
            assert ticket.is_file()
            page.goto(ticket.read_text())
            page.locator("#file").set_input_files(
                {
                    "name": "reopened.pdf",
                    "mimeType": "application/pdf",
                    "buffer": _pdf("normal"),
                }
            )
            page.get_by_role("button", name="Start audit", exact=True).click()
            page.locator(".finding-card").first.wait_for(timeout=10000)
            page.get_by_role("button", name="Quit", exact=True).click()
            reopened.wait(timeout=5)
            assert reopened.returncode == 0
        finally:
            if reopened.poll() is None:
                reopened.terminate()
            reopened.wait(timeout=10)
        browser.close()
