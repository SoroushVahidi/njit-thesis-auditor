"""Touch-first browser coverage for direct sample audits."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit

import pytest
from desktop_session_support import wait_state
from test_about_browser import guard_external, website

SAMPLE_IDS = ["synthetic_example", *(f"ester_sample_{letter}" for letter in "abcd")]


@pytest.mark.parametrize("browser_name,mobile,sample_id", [
    *(('webkit', True, sample_id) for sample_id in SAMPLE_IDS),
    ('chromium', False, 'synthetic_example'),
])
def test_direct_sample_audit_works_without_file_picker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    browser_name: str, mobile: bool, sample_id: str,
) -> None:
    api = pytest.importorskip('playwright.sync_api')
    monkeypatch.setenv('NJIT_AUDITOR_ADMIN_DB_PATH', str(tmp_path / 'private-feedback.sqlite3'))
    with website(tmp_path) as origin, api.sync_playwright() as runner:
        browser = getattr(runner, browser_name).launch()
        try:
            context = browser.new_context(
                viewport={'width': 390 if mobile else 1280, 'height': 844},
                is_mobile=mobile, has_touch=mobile,
            )
            attempts = guard_external(context)
            page = context.new_page()
            errors = []
            file_choosers = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('filechooser', lambda chooser: file_choosers.append(chooser))
            assert page.goto(origin).status == 200
            dropdown = page.get_by_label('Sample document')
            assert dropdown.is_visible()
            if mobile:
                dropdown.tap()
            dropdown.select_option(sample_id)
            button = page.get_by_role('button', name='Audit Selected Sample')
            if mobile:
                button.tap()
            else:
                button.click()
            page.wait_for_url('**/audits/*')
            job_path = urlsplit(page.url).path
            status = wait_state(context.request, origin, job_path, {'complete'})
            assert status['state'] == 'complete'
            assert page.reload().status == 200
            assert page.locator('#section-findings .finding-card').count() > 0
            assert page.locator('#section-downloads').is_visible()
            assert not page.evaluate('document.documentElement.scrollWidth > innerWidth + 1')
            assert file_choosers == []
            assert errors == []
            assert attempts == []
        finally:
            browser.close()
