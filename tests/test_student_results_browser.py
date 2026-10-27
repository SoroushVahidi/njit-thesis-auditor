"""Real Chromium/Firefox presentation checks against an owned synthetic fixture server."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

from njit_auditor.student_confidence import CONFIDENCE_COLORS

SERVER = """
import os
from pathlib import Path
import uvicorn
from test_web_app import _make_app,_inject_complete_job_with_findings
from test_student_results_presentation import sample_findings
root=Path(os.environ['PRESENTATION_ROOT'])
app,wa=_make_app(root)
job=_inject_complete_job_with_findings(wa,root,findings=sample_findings(),
    file_name='synthetic.pdf',audit_type='pdf')
(root/'job-id').write_text(job)
uvicorn.run(app,host='127.0.0.1',port=int(os.environ['PRESENTATION_PORT']),log_level='error')
"""


@pytest.fixture(scope="module")
def presentation_site(tmp_path_factory):
    root = Path(__file__).resolve().parents[1]
    temporary = tmp_path_factory.mktemp("student-presentation")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join([str(root / "src"), str(root / "tests")]),
        "PRESENTATION_ROOT": str(temporary),
        "PRESENTATION_PORT": str(port),
    }
    with (temporary / "server.log").open("w") as log:
        process = subprocess.Popen(
            [sys.executable, "-c", SERVER], cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT
        )
        base = f"http://127.0.0.1:{port}"
        try:
            for _ in range(80):
                assert process.poll() is None, "Synthetic server exited before startup"
                try:
                    if httpx.get(base + "/healthz", timeout=0.5).status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(0.05)
            else:
                pytest.fail("Synthetic server startup timed out")
            yield base, (temporary / "job-id").read_text()
        finally:
            process.terminate()
            process.wait(timeout=10)


@pytest.mark.parametrize("engine", ["chromium", "firefox"])
@pytest.mark.parametrize("width,height", [(320, 800), (390, 844), (768, 1024), (1440, 900)])
def test_results_confidence_accessibility(presentation_site, tmp_path, engine, width, height):
    playwright = pytest.importorskip("playwright.sync_api")
    base, job = presentation_site
    screenshots = Path(os.environ.get("NJIT_PRESENTATION_SCREENSHOTS", str(tmp_path)))
    screenshots.mkdir(parents=True, exist_ok=True)
    with playwright.sync_playwright() as pw:
        browser_type = getattr(pw, engine)
        if not Path(browser_type.executable_path).is_file():
            if os.environ.get("NJIT_REQUIRE_BROWSER") == "1":
                pytest.fail(f"Install {engine} with python -m playwright install {engine}")
            pytest.skip(f"{engine} binary not available")
        browser = browser_type.launch(headless=True)
        page = browser.new_page(viewport={"width": width, "height": height})
        errors, external = [], []
        page.on("pageerror", lambda error: errors.append(str(error)))

        def route(request):
            if request.request.url.startswith(base + "/"):
                request.continue_()
            else:
                external.append(request.request.url)
                request.abort()

        page.route("**/*", route)
        page.goto(f"{base}/audits/{job}")
        assert page.locator(".student-disclosure").count() == 1
        assert "Partly checked" not in page.locator("body").inner_text()
        assert page.locator(".finding-card").count() == 3
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        for level, palette in CONFIDENCE_COLORS.items():
            badge = page.locator(f".finding-card .confidence-badge--{level}")
            assert badge.inner_text() == f"{level.title()} confidence"
            get_colors = "e => [getComputedStyle(e).color, getComputedStyle(e).backgroundColor]"
            computed = badge.evaluate(get_colors)
            expected = [
                "rgb(" + ", ".join(str(int(color[i : i + 2], 16)) for i in (1, 3, 5)) + ")"
                for color in [palette["foreground"], palette["background"]]
            ]
            assert computed == expected
            card = badge.locator("xpath=ancestor::article")
            badge_box = badge.bounding_box()
            for button in card.locator(".finding-card__action a").all():
                box = button.bounding_box()
                assert not (
                    badge_box["x"] < box["x"] + box["width"]
                    and box["x"] < badge_box["x"] + badge_box["width"]
                    and badge_box["y"] < box["y"] + box["height"]
                    and box["y"] < badge_box["y"] + badge_box["height"]
                )
            chip = page.locator(f'[data-confidence-filter="{level}"]')
            chip.focus()
            page.keyboard.press("Enter")
            assert chip.get_attribute("aria-pressed") == "true"
            assert chip.evaluate(get_colors) == expected
            assert page.locator(".finding-card:visible").count() == 1
            assert badge.is_visible()
            page.locator('[data-confidence-filter=""]').click()
        page.locator(".finding-card").first.locator("summary").first.focus()
        page.keyboard.press("Enter")
        explanation = page.locator(".finding-card").first.locator("details").first
        assert explanation.get_attribute("open") is not None
        page.locator(".finding-card").first.locator("summary").first.click()
        page.screenshot(path=str(screenshots / f"results-{engine}-{width}.png"), full_page=True)
        page.get_by_role("link", name="About", exact=True).focus()
        page.keyboard.press("Enter")
        page.wait_for_url(base + "/about")
        summary = page.locator("#coverage > summary")
        summary.focus()
        page.keyboard.press("Enter")
        assert page.locator("#coverage").get_attribute("open") is not None
        page.locator("#coverage details").first.locator("summary").click()
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        checklist = page.get_by_role(
            "link", name="NJIT's official thesis checklist and review process"
        )
        assert checklist.count() == 1
        page.screenshot(path=str(screenshots / f"about-{engine}-{width}.png"), full_page=True)
        assert not errors and not external
        browser.close()
