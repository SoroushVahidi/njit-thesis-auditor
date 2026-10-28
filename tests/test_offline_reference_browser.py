"""Real browser navigation; optionally repeat against an actual Linux frozen launcher.

NJIT_REFERENCE_EXECUTABLE=/absolute/path/to/launcher adds frozen cases. The
source fixture denies application socket/DNS calls; browser egress is blocked
in every case. Frozen egress needs separate OS tracing or disconnected testing.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from test_offline_desktop import _pdf
from test_offline_desktop_browser import DesktopSession, desktop_process  # noqa: F401


@pytest.fixture(params=["source"] + (["frozen"] if os.getenv("NJIT_REFERENCE_EXECUTABLE") else []))
def reference_session(request, tmp_path):
    if request.param == "source":
        yield request.getfixturevalue("desktop_process")
        return
    assert sys.platform == "linux", "This optional frozen-launch fixture requires native Linux"
    executable = Path(os.environ["NJIT_REFERENCE_EXECUTABLE"]).resolve(strict=True)
    capture = tmp_path / "launch-url"
    stub = tmp_path / "open-browser"
    stub.write_text('#!/bin/sh\numask 077\nprintf \'%s\' "$1" > "$NJIT_CAPTURE_URL"\n')
    stub.chmod(0o700)
    empty_path = tmp_path / "empty-path"
    empty_path.mkdir()
    env = {
        **os.environ,
        "XDG_DATA_HOME": str(tmp_path / "data"),
        "BROWSER": str(stub) + " %s",
        "NJIT_CAPTURE_URL": str(capture),
        "PATH": str(empty_path),
    }
    with (tmp_path / "launcher.log").open("w") as log:
        process = subprocess.Popen(
            [str(executable), "--headless"], cwd=tmp_path, env=env,
            stdout=log, stderr=subprocess.STDOUT,
        )
        try:
            for _ in range(100):
                assert process.poll() is None, "Frozen launcher exited before startup"
                if capture.is_file():
                    break
                time.sleep(0.05)
            else:
                pytest.fail("Frozen launcher did not open the browser")
            url = capture.read_text()
            yield DesktopSession(process, url, f"http://{urlsplit(url).netloc}")
        finally:
            if process.poll() is None:
                process.terminate()
            process.wait(timeout=10)
    output = (tmp_path / "launcher.log").read_text()
    assert str(tmp_path) not in output and "ticket=" not in output


@pytest.mark.parametrize("engine", ["chromium", "firefox"])
@pytest.mark.parametrize("width,height", [(320, 800), (390, 844), (768, 1024), (1440, 900)])
def test_reference_navigation_and_external_failure(reference_session, engine, width, height):
    playwright = pytest.importorskip("playwright.sync_api")
    session = reference_session
    with playwright.sync_playwright() as pw:
        browser_type = getattr(pw, engine)
        if not Path(browser_type.executable_path).is_file():
            if os.environ.get("NJIT_REQUIRE_BROWSER") == "1":
                pytest.fail(f"Install the {engine} Playwright browser")
            pytest.skip(f"{engine} unavailable")
        browser = browser_type.launch(headless=True)
        context = browser.new_context(viewport={"width": width, "height": height})
        external, errors, failed_local = [], [], []

        def local_only(route):
            if urlsplit(route.request.url).netloc != urlsplit(session.base).netloc:
                external.append(route.request.url)
                route.abort()
            else:
                route.continue_()

        context.route("**/*", local_only)
        context.on("page", lambda p: p.on("pageerror", lambda e: errors.append(str(e))))
        context.on(
            "response", lambda r: failed_local.append(r.status)
            if r.url.startswith(session.base + "/") and r.status >= 400 else None,
        )
        page = context.new_page()
        page.goto(session.url)
        for destination, heading in (
            ("Help", "Help & Terminology"), ("Rule Reference", "Rule Reference")
        ):
            page.locator(".site-nav__link").filter(has_text=destination).click()
            assert page.get_by_role("heading", name=heading, exact=True).is_visible()
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
        # Exercise the locally bundled filter script and hash navigation.
        page.locator("#rule-search").fill("R011")
        assert page.locator("#P011").is_visible()
        page.locator("#rule-filter-reset").click()
        assert page.locator("#rule-search").input_value() == ""
        page.locator(".site-nav__brand").click()
        page.locator("#file").set_input_files({
            "name": "synthetic.pdf", "mimeType": "application/pdf", "buffer": _pdf("normal"),
        })
        page.get_by_role("button", name="Start audit", exact=True).click()
        page.locator(".finding-card").first.wait_for(timeout=15000)
        results = page.url
        rule_link = page.locator('.finding-card a[href^="/rules#"]').first
        target = rule_link.get_attribute("href")
        rule_link.click()
        assert page.locator("#" + target.split("#", 1)[1]).is_visible()
        page.go_back()
        assert page.url == results
        page.locator('.site-nav__link[href="/help"]').click()
        assert "only in your local application data" in page.inner_text("body")
        page.goto(results)
        page.locator('.site-nav__link[href="/rules"]').click()
        assert page.locator("#P011").is_visible()
        assert not external and not errors and not failed_local
        # An unreachable official reference must leave the local app open.
        page.goto(results)
        official = page.locator('a[href^="https://"]').first
        assert official.get_attribute("target") == "_blank"
        assert "internet required" in official.inner_text()
        with context.expect_event("requestfailed"):
            with context.expect_page() as popup:
                official.click()
        popup.value.close()
        assert page.url == results
        assert len(external) == 1 and not errors and not failed_local
        page.locator('.site-nav__link[href="/help"]').click()
        page.get_by_role("button", name="Quit", exact=True).click()
        assert "Auditor closed" in page.inner_text("body")
        session.process.wait(timeout=12)
        assert session.process.returncode == 0
        browser.close()
