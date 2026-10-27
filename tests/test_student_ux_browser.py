"""Actual Chromium workflow, synthetic PDFs and isolated loopback server only."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import httpx
import pytest

# Fixture transport exists only in this owned test process, never product code.
SERVER = """
from pathlib import Path
import urllib.error
from unittest.mock import patch
import uvicorn
import njit_auditor.web_app as wa
import njit_auditor.web_url_fetch as wf
pdf = Path(__import__('os').environ['UX_SYNTHETIC_PDF'])
def fetch(url, dest, max_bytes):
    if url == 'https://fixture.example/ok.pdf':
        dest.write_bytes(pdf.read_bytes())
        return
    codes = {'403': 403, '404': 404, 'unavailable': 503}
    key = url.rsplit('/', 1)[-1]
    def fail(*a, **kw):
        if key == 'timeout': raise TimeoutError('synthetic timeout')
        if key == 'html':
            raise wf.FetchError('Use a direct PDF link or upload a valid PDF.')
        raise urllib.error.HTTPError(url, codes[key], 'Forbidden', {}, None)
    with (
        patch('urllib.request.OpenerDirector.open', side_effect=fail),
        patch.object(wf, '_validate_url', return_value=url),
    ):
        wf.fetch_pdf_url(url, dest, max_bytes)
wa.fetch_pdf_url = fetch
uvicorn.run(wa.app, host='127.0.0.1',
            port=int(__import__('os').environ['UX_PORT']), log_level='error')
"""


@pytest.fixture()
def browser_site(tmp_path: Path) -> Any:
    root = Path(__file__).resolve().parents[1]
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    fixture = root / "tests/fixtures/web_demo/issues_pdf.pdf"
    env = os.environ.copy()
    env.update(
        PYTHONPATH=str(root / "src"),
        PYTHONDONTWRITEBYTECODE="1",
        NJIT_AUDITOR_WEB_RUNTIME_DIR=str(tmp_path / "jobs"),
        NJIT_AUDITOR_WEB_ENVIRONMENT="isolated-synthetic-browser",
        UX_PORT=str(port),
        UX_SYNTHETIC_PDF=str(fixture),
    )
    log = (tmp_path / "server.log").open("w")
    process = subprocess.Popen(
        [sys.executable, "-c", SERVER], cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT
    )
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(60):
            assert process.poll() is None, (tmp_path / "server.log").read_text()
            try:
                if httpx.get(base + "/healthz", timeout=0.5).status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(0.1)
        else:
            pytest.fail("Isolated browser server failed to start")
        yield base, fixture
    finally:
        process.terminate()
        process.wait(timeout=10)
        log.close()


@pytest.mark.parametrize("width,height", [(320, 800), (390, 844), (768, 1024), (1440, 900)])
def test_student_workflow(browser_site: Any, width: int, height: int, tmp_path: Path) -> None:
    if os.environ.get("NJIT_REQUIRE_BROWSER") == "1":
        import playwright.sync_api as playwright
    else:
        playwright = pytest.importorskip("playwright.sync_api")

    base, fixture = browser_site
    screenshots = Path(os.environ.get("NJIT_UX_SCREENSHOTS", str(tmp_path)))
    screenshots.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    with playwright.sync_playwright() as pw:
        if not Path(pw.chromium.executable_path).is_file():
            if os.environ.get("NJIT_REQUIRE_BROWSER") == "1":
                pytest.fail("Chromium missing: run python -m playwright install chromium")
            pytest.skip("Chromium missing: run python -m playwright install chromium")
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": width, "height": height})
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        page.set_default_timeout(15000)

        def fits() -> None:
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")

        page.goto(base)
        fits()
        page.screenshot(path=str(screenshots / f"after-home-{width}.png"), full_page=True)
        page.get_by_role("link", name="About", exact=True).focus()
        page.keyboard.press("Enter")
        page.wait_for_url(base + "/about")
        fits()
        privacy = page.locator("#privacy")
        assert "anyone" in privacy.inner_text().lower()
        summary = privacy.get_by_text("What is stored?", exact=True)
        summary.focus()
        page.keyboard.press("Enter")
        assert privacy.locator("details").get_attribute("open") is not None
        page.screenshot(path=str(screenshots / f"after-about-{width}.png"), full_page=True)

        page.goto(base)
        page.locator("#file").set_input_files(str(fixture))
        page.get_by_role("button", name="Start audit", exact=True).click()
        page.locator(".finding-card").first.wait_for()
        result_url = page.url
        fits()
        page.screenshot(path=str(screenshots / f"after-results-{width}.png"), full_page=True)
        page.locator("#section-findings").scroll_into_view_if_needed()
        page.screenshot(path=str(screenshots / f"after-findings-{width}.png"))
        cards = page.locator(".finding-card:visible")
        assert cards.count() == 2
        assert "Suggested fix:" in cards.first.inner_text()
        explanation = cards.first.locator("details").filter(
            has=page.get_by_text("Why is this flagged?", exact=True)
        )
        assert explanation.get_attribute("open") is None
        explanation.locator(":scope > summary").focus()
        page.keyboard.press("Enter")
        assert explanation.get_attribute("open") is not None
        pdf_link = cards.first.locator(".finding-card__action a").first
        pdf_link.focus()
        assert pdf_link.evaluate("e => e === document.activeElement")
        assert page.request.get(base + pdf_link.get_attribute("href")).status == 200
        page.locator("#filter-rule").select_option("P011")
        fits()
        assert cards.count() == 2
        page.locator("#filter-page").select_option("1")
        assert cards.count() == 1 and "Problem 1 of 1" in cards.first.inner_text()
        assert page.locator("#filter-count").get_attribute("role") == "status"
        page.locator("#filter-reset").click()
        assert cards.count() == 2
        with page.expect_navigation(wait_until="domcontentloaded"):
            page.locator("#sort-problems").select_option("confidence_desc")
        fits()
        for suffix in ["json", "markdown", "text", "student-report.pdf"]:
            response = page.request.get(result_url + "/download/" + suffix)
            assert response.status == 200
            if suffix.endswith(".pdf"):
                assert response.body().startswith(b"%PDF")
        page.get_by_text("More export formats", exact=True).click()
        assert page.get_by_role("link", name="Download JSON", exact=True).is_visible()
        for case, message in [
            ("403", "The source website blocked the request."),
            ("404", "The PDF wasn't found"),
            ("timeout", "download timed out"),
            ("html", "direct PDF link"),
        ]:
            page.goto(base)
            page.get_by_text("Use a public PDF link", exact=True).click()
            page.locator("#pdf_url").fill("https://fixture.example/" + case)
            page.get_by_role("button", name="Audit PDF URL", exact=True).click()
            assert message in page.locator('[role="alert"]').inner_text()
            fits()
            if case == "403":
                page.screenshot(path=str(screenshots / f"after-error-{width}.png"), full_page=True)
        page.goto(base)
        page.get_by_text("Use a public PDF link", exact=True).click()
        page.locator("#pdf_url").fill("https://fixture.example/ok.pdf")
        page.get_by_role("button", name="Audit PDF URL", exact=True).click()
        page.locator(".finding-card").first.wait_for()
        assert not errors
        (screenshots / f"browser-{width}.json").write_text(
            json.dumps(
                {
                    "width": width,
                    "javascript_errors": errors,
                    "result": "PASS",
                    "browser": browser.version,
                },
                indent=2,
            )
        )
        browser.close()


@pytest.mark.parametrize("width,height", [(390, 844), (1440, 900)])
def test_affected_corrections_fit_and_keep_details(
    browser_site: Any, width: int, height: int, tmp_path: Path
) -> None:
    from test_student_correction_subtypes import EXPECTED_ACTIONS, correction_pdfs

    if os.environ.get("NJIT_REQUIRE_BROWSER") == "1":
        import playwright.sync_api as playwright
    else:
        playwright = pytest.importorskip("playwright.sync_api")
    base, _ = browser_site
    screenshots = Path(os.environ.get("NJIT_UX_SCREENSHOTS", str(tmp_path)))
    screenshots.mkdir(parents=True, exist_ok=True)
    seen = set()
    with playwright.sync_playwright() as pw:
        if not Path(pw.chromium.executable_path).is_file():
            if os.environ.get("NJIT_REQUIRE_BROWSER") == "1":
                pytest.fail("Chromium missing: run python -m playwright install chromium")
            pytest.skip("Chromium missing: run python -m playwright install chromium")
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": width, "height": height})
        errors: list[str] = []
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        for fixture in correction_pdfs(tmp_path / "corrections"):
            page.goto(base)
            page.locator("#file").set_input_files(str(fixture))
            page.get_by_role("button", name="Start audit", exact=True).click()
            page.locator(".finding-card").first.wait_for(timeout=15000)
            for key, action in EXPECTED_ACTIONS.items():
                cards = page.locator(".finding-card").filter(has_text=action)
                if not cards.count():
                    continue
                seen.add(key)
                card = cards.first
                card.scroll_into_view_if_needed()
                details = card.locator("details.finding-explanation")
                assert details.get_attribute("open") is None
                assert action in card.inner_text()
                assert "Full correction:" not in card.inner_text()
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                page.screenshot(path=str(screenshots / f"correction-{width}-{key[1]}.png"))
                details.locator(":scope > summary").click()
                assert "Full correction:" in card.inner_text()
                assert "source text is incomplete" not in card.inner_text()
                details.locator(":scope > summary").click()
        assert seen == set(EXPECTED_ACTIONS)
        assert not errors
        browser.close()
