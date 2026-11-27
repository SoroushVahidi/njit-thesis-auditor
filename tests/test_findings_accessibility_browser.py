"""Local browser coverage for findings-first navigation and control semantics."""

import re
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from desktop_session_support import desktop, wait_state
from test_about_browser import guard_external
from test_http_reviewer_browser import JOB_ID, reviewer_site


def _tab_to(page, locator, *, limit=35):
    for _ in range(limit):
        page.keyboard.press("Tab")
        if locator.evaluate("el => el === document.activeElement"):
            return
    pytest.fail("The named control was not reached in the keyboard tab sequence")


def _enter_main(page):
    skip = page.get_by_role("link", name="Skip to main content")
    page.keyboard.press("Tab")
    assert skip.evaluate("el => el === document.activeElement")
    assert skip.bounding_box()["y"] >= 0
    assert skip.evaluate("el => getComputedStyle(el).outlineStyle") == "solid"
    page.keyboard.press("Enter")
    main = page.get_by_role("main")
    assert main.count() == 1
    assert main.evaluate("el => el === document.activeElement")
    return main


def _contrast(colors):
    def luminance(css):
        values = [float(channel) / 255 for channel in re.findall(r"[0-9.]+", css)[:3]]
        linear = [
            value / 12.92 if value <= 0.04045 else ((value + .055) / 1.055) ** 2.4
            for value in values
        ]
        return sum(x * factor for x, factor in zip(linear, [.2126, .7152, .0722], strict=True))
    light, dark = sorted((luminance(color) for color in colors), reverse=True)
    return (light + .05) / (dark + .05)


def _assert_controls_fit_and_are_readable(page):
    assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
    for selector in (".confidence-badge", ".confidence-filter__chip", ".finding-card__action .btn"):
        locators = page.locator(selector).all()
        for control in locators:
            if control.is_visible():
                colors = control.evaluate(
                    "el => { const c = getComputedStyle(el); return [c.color, c.backgroundColor]; }"
                )
                assert _contrast(colors) >= 4.5
    select = page.get_by_role("combobox", name="Sort findings")
    if select.is_visible():
        colors = select.evaluate(
            "el => { const c = getComputedStyle(el); return [c.borderColor, c.backgroundColor]; }"
        )
        assert _contrast(colors) >= 3


@pytest.mark.parametrize("width", [320, 1400])
def test_findings_first_keyboard_and_stable_reference(tmp_path: Path, width: int):
    api = pytest.importorskip("playwright.sync_api")
    with reviewer_site(tmp_path) as (origin, _), api.sync_playwright() as runner:
        browser = runner.chromium.launch()
        try:
            context = browser.new_context(viewport={"width": width, "height": 850})
            attempts = guard_external(context)
            page = context.new_page()
            audit_url = f"{origin}/audits/{JOB_ID}"
            assert page.goto(audit_url).status == 200
            main = _enter_main(page)
            assert main.get_by_role("heading", level=1, name="Audit complete").is_visible()
            nav = main.get_by_role("navigation", name="Jump to section")
            assert nav.get_by_role("link").all_text_contents()[:2] == [
                "Findings in page order", "Downloads"
            ]
            findings = main.get_by_role("region", name="Findings in page order")
            _tab_to(page, nav.get_by_role("link", name="Findings in page order"))
            page.keyboard.press("Enter")
            assert findings.evaluate("el => el === document.activeElement")
            assert page.evaluate("""() => {
                const a = document.getElementById('section-findings');
                const b = document.getElementById('section-coverage');
                return Boolean(a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING);
            }""")
            card = findings.get_by_role("article")
            assert card.get_by_role("heading", level=3).is_visible()
            assert "High confidence" in card.aria_snapshot()
            assert card.get_attribute("id") == "problem-1"
            assert card.get_by_text("Report reference 1").is_visible()
            assert "Showing 1 of 1 findings" in findings.get_by_role("status").aria_snapshot()
            _assert_controls_fit_and_are_readable(page)

            sort = findings.get_by_role("combobox", name="Sort findings")
            page.keyboard.press("Tab")
            assert findings.get_by_role("searchbox", name="Search findings").evaluate(
                "el => el === document.activeElement"
            )
            page.keyboard.press("Tab")
            assert sort.evaluate("el => el === document.activeElement")
            page.keyboard.press("ArrowDown")
            assert page.url.endswith("#section-findings")
            page.keyboard.press("Tab")
            apply = findings.get_by_role("button", name="Apply sort")
            assert apply.evaluate("el => el === document.activeElement")
            page.keyboard.press("Enter")
            page.wait_for_url("**?sort=confidence_desc#section-findings")
            findings = main.get_by_role("region", name="Findings by confidence")
            assert findings.evaluate("el => el === document.activeElement")
            card = findings.get_by_role("article")
            assert findings.get_by_text("Report reference 1").is_visible()
            assert card.get_attribute("id") == "problem-1"

            low = findings.get_by_role("button", name="Low", exact=True)
            low.focus()
            page.keyboard.press("Space")
            assert low.get_attribute("aria-pressed") == "true"
            assert not card.is_visible()
            assert "Showing 0 of 1 findings" in findings.get_by_role("status").aria_snapshot()
            empty = findings.get_by_text("No findings match your search and filters.", exact=False)
            assert empty.is_visible()
            reset = findings.get_by_role("button", name="Reset filters")
            _tab_to(page, reset)
            page.keyboard.press("Enter")
            assert card.is_visible()

            downloads = main.get_by_role("region", name="Downloads")
            text_export = downloads.get_by_role("link", name=re.compile("Full Student Report"))
            assert text_export.is_visible()
            assert attempts == []
        finally:
            browser.close()


def test_reviewer_named_controls_and_keyboard_feedback(tmp_path: Path):
    api = pytest.importorskip("playwright.sync_api")
    with reviewer_site(tmp_path) as (origin, password), api.sync_playwright() as runner:
        browser = runner.chromium.launch()
        try:
            context = browser.new_context(viewport={"width": 320, "height": 850})
            attempts = guard_external(context)
            page = context.new_page()
            audit_url = f"{origin}/audits/{JOB_ID}"
            page.goto(f"{origin}/reviewer/login?next=/audits/{JOB_ID}")
            page.get_by_label("Username").fill("ester")
            page.get_by_label("Password").fill(password)
            page.get_by_role("button", name="Log in").press("Enter")
            page.wait_for_url(audit_url)
            main = _enter_main(page)
            group = main.get_by_role("group", name="Reviewer feedback for f0")
            option = group.get_by_role("radio", name=re.compile("Unclear"))
            _tab_to(page, group.get_by_role("radio", name=re.compile("True Positive")), limit=50)
            page.keyboard.press("ArrowRight")
            page.keyboard.press("ArrowRight")
            assert option.is_checked()
            page.keyboard.press("Tab")
            comments = main.get_by_role("textbox", name="Additional comments (optional)")
            assert comments.evaluate("el => el === document.activeElement")
            assert comments.evaluate("el => getComputedStyle(el).outlineStyle") == "solid"
            page.keyboard.type("Synthetic reviewer input")
            page.keyboard.press("Tab")
            assert main.get_by_label("Supporting files (optional)").evaluate(
                "el => el === document.activeElement"
            )
            page.keyboard.press("Tab")
            assert main.get_by_role("button", name="Save Feedback").evaluate(
                "el => el === document.activeElement"
            )
            page.keyboard.press("Enter")
            assert main.get_by_text("Feedback saved.").get_attribute("role") == "status"
            _assert_controls_fit_and_are_readable(page)
            assert attempts == []
        finally:
            browser.close()


def test_desktop_labeled_upload_and_results_at_narrow_width(tmp_path: Path):
    api = pytest.importorskip("playwright.sync_api")
    with desktop(tmp_path / "desktop") as server, api.sync_playwright() as runner:
        browser = runner.chromium.launch()
        try:
            context = browser.new_context(viewport={"width": 320, "height": 840})
            attempts = guard_external(context)
            page = context.new_page()
            assert page.goto(server.url).status == 200
            main = _enter_main(page)
            upload = main.get_by_label("Select PDF")
            _tab_to(page, upload)
            assert upload.get_attribute("aria-describedby") == "file-hint audit-time-hint"
            sample = context.request.get(server.origin + "/sample.pdf")
            assert sample.status == 200
            upload.set_input_files({
                "name": "synthetic.pdf",
                "mimeType": "application/pdf",
                "buffer": sample.body(),
            })
            _tab_to(page, main.get_by_role("button", name="Start audit"))
            page.keyboard.press("Enter")
            page.wait_for_url("**/audits/*")
            job = urlsplit(page.url).path
            wait_state(context.request, server.origin, job, {"complete"})
            page.reload()
            main = _enter_main(page)
            assert main.get_by_role("heading", level=1, name="Audit complete").is_visible()
            search = main.get_by_role("searchbox", name="Search findings")
            findings = main.get_by_role("region", name="Findings in page order")
            cards = findings.locator("article[data-rule]:visible")
            total = cards.count()
            assert total > 1
            rule = cards.first.get_attribute("data-rule")
            assert rule
            search.fill(rule.lower())
            page.wait_for_function(
                "([rule, total]) => { const cards = [...document.querySelectorAll("
                "'.finding-row:not(.finding-row--hidden)')]; return cards.length < total "
                "&& cards.some(card => card.dataset.rule === rule); }",
                arg=[rule, total],
            )
            assert main.locator("#filter-count").get_attribute("role") == "status"
            search.fill("zz_no_such_synthetic_finding zz")
            main.get_by_text("No findings match your search and filters.", exact=False).wait_for()
            assert cards.count() == 0
            main.get_by_role("button", name="Reset filters").click()
            assert search.input_value() == "" and cards.count() == total
            manual = main.locator(".coverage-details summary")
            actions = main.get_by_role("navigation", name="Audit actions")
            assert actions.get_by_role("link", name="Download PDF report").get_attribute(
                "href"
            ) == job + "/download/student-report.pdf"
            other = actions.get_by_role("link", name="Other export formats")
            page.emulate_media(forced_colors="active")
            other.focus()
            page.keyboard.press("Enter")
            assert page.get_by_role("region", name="Downloads").evaluate(
                "el => el === document.activeElement"
            )
            back = page.get_by_role("link", name="Back to audit overview")
            back.focus()
            page.keyboard.press("Enter")
            assert page.locator("#audit-overview").evaluate(
                "el => el === document.activeElement"
            )
            page.emulate_media(forced_colors=None)
            manual.focus()
            page.keyboard.press("Enter")
            assert main.get_by_text("Check yourself:", exact=True).first.is_visible()
            _assert_controls_fit_and_are_readable(page)
            assert attempts == []
        finally:
            browser.close()
