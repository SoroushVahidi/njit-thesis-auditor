"""Real browser checks for card filtering and responsive presentation."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest


@pytest.mark.parametrize("width,height", [(390, 844), (1400, 900)])
def test_synthetic_cards_filter_sort_and_fit_screen(
    tmp_path: Path, width: int, height: int
) -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    root = Path(__file__).resolve().parents[1]
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "src")
    env["NJIT_AUDITOR_WEB_RUNTIME_DIR"] = str(tmp_path / "jobs")
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "njit_auditor.web_app:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=root,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(80):
            try:
                if httpx.get(base + "/", timeout=1).status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(0.1)
        else:
            pytest.fail("isolated test server did not start")

        fixture = root / "tests" / "fixtures" / "web_demo" / "issues_pdf.pdf"
        result = httpx.post(
            base + "/audits",
            files={"file": (fixture.name, fixture.read_bytes(), "application/pdf")},
            follow_redirects=False,
            timeout=30,
        )
        assert result.status_code == 303
        url = base + result.headers["location"]
        runner = playwright.sync_playwright()
        try:
            playwright_instance = runner.__enter__()
            browser = playwright_instance.chromium.launch(headless=True)
        except Exception as exc:
            runner.__exit__(None, None, None)
            pytest.skip(f"Chromium unavailable: {type(exc).__name__}")
        try:
            page = browser.new_page(viewport={"width": width, "height": height})
            page.goto(url, wait_until="domcontentloaded")
            cards = page.locator("#individual-findings-panel .finding-card")
            cards.first.wait_for(timeout=30000)
            assert cards.count() == 2
            assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
            assert cards.first.locator(".finding-card__problem").inner_text() == "Problem 1 of 2"
            assert cards.first.locator(".finding-card__rule").inner_text() == "MARGINS"
            assert cards.first.inner_text().count("Page 1") == 1
            assert (
                cards.first.locator(".finding-card__confidence").inner_text().endswith("confidence")
            )

            page.locator("#filter-page").select_option("1")
            visible = page.locator("#individual-findings-panel .finding-card:visible")
            assert visible.count() == 1
            assert visible.first.locator(".finding-card__problem").inner_text() == "Problem 1 of 1"
            assert page.locator("#filter-count").inner_text() == "Showing 1 of 2 findings"
            pdf_link = visible.first.locator(".finding-card__action a").first
            pdf_link.focus()
            assert pdf_link.evaluate("element => document.activeElement === element")
            assert "PDF" in pdf_link.inner_text()

            page.locator("#filter-reset").click()
            assert page.locator("#individual-findings-panel .finding-card:visible").count() == 2
            page.locator("#sort-problems").select_option("confidence_desc")
            page.wait_for_load_state("domcontentloaded")
            assert page.locator(".finding-card__problem").first.inner_text() == "Problem 1 of 2"
            assert page.locator(".finding-card__problem").last.inner_text() == "Problem 2 of 2"
            assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
        finally:
            browser.close()
            runner.__exit__(None, None, None)
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
