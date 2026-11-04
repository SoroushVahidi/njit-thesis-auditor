"""Actual About navigation and offline browser behavior with synthetic state."""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import pytest
from desktop_session_support import desktop, wait_state

ROOT = Path(__file__).resolve().parents[1]
RELEASES = 'https://github.com/SoroushVahidi/njit-thesis-auditor-desktop'


@contextmanager
def website(tmp_path: Path):
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    origin = f'http://127.0.0.1:{port}'
    bootstrap = '''from datetime import datetime, timezone
import uvicorn
from njit_auditor import web_app as web
for state in ['pending', 'running', 'complete', 'failed']:
    web._set_job(web.JobState(job_id='about-'+state, state=state,
                 created_at=datetime.now(timezone.utc).isoformat(), file_name='synthetic.pdf'))
uvicorn.run(web.app, host='127.0.0.1', port=PORT, log_level='warning', access_log=False)
'''.replace('PORT', str(port))
    env = {**os.environ, 'PYTHONPATH': str(ROOT/'src'),
           'NJIT_AUDITOR_WEB_RUNTIME_DIR': str(tmp_path/'jobs')}
    with (tmp_path/'server.log').open('wb') as log:
        process = subprocess.Popen([sys.executable, '-c', bootstrap], cwd=ROOT,
                                   env=env, stdout=log, stderr=log)
        try:
            deadline = time.monotonic()+20
            while True:
                assert process.poll() is None, 'Isolated About test server exited'
                try:
                    if httpx.get(origin+'/healthz', timeout=1, trust_env=False).status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                assert time.monotonic() < deadline, 'Isolated About test server did not start'
                time.sleep(.1)
            yield origin
        finally:
            process.terminate()
            process.wait(timeout=15)


def guard_external(context):
    attempts = []

    def guard(route):
        if urlsplit(route.request.url).hostname == '127.0.0.1':
            route.continue_()
        else:
            attempts.append(route.request.url)
            route.abort()
    context.route('**/*', guard)
    return attempts


def keyboard_about(page, origin):
    link = page.get_by_role('navigation').get_by_role('link', name='About Us', exact=True)
    assert link.get_attribute('class') == 'site-nav__link'
    link.focus()
    assert link.evaluate('el => el === document.activeElement')
    page.keyboard.press('Enter')
    page.wait_for_url(origin+'/about')
    assert page.get_by_role('heading', name='About Us', exact=True).is_visible()
    assert link.get_attribute('aria-current') == 'page'
    assert not page.evaluate('document.documentElement.scrollWidth > innerWidth')
    main = page.locator('#about-content')
    contact = main.get_by_role('link', name='sv96@njit.edu', exact=True)
    assert contact.get_attribute('href') == 'mailto:sv96@njit.edu'
    contact.focus()
    page.keyboard.press('Tab')
    releases = main.get_by_role('link', name='Windows desktop downloads and release notes')
    assert releases.evaluate('el => el === document.activeElement')
    assert releases.get_attribute('href') == RELEASES
    assert main.locator('img, iframe, script, link').count() == 0


@pytest.mark.parametrize('width', [390, 1440])
def test_about_keyboard_navigation_on_upload_status_results_and_help(tmp_path: Path, width: int):
    api = pytest.importorskip('playwright.sync_api')
    with website(tmp_path) as origin, api.sync_playwright() as runner:
        browser = runner.chromium.launch()
        try:
            context = browser.new_context(viewport={'width': width, 'height': 950})
            attempts = guard_external(context)
            page = context.new_page()
            for path in ['/', '/audits/about-pending', '/audits/about-running',
                         '/audits/about-complete', '/audits/about-failed', '/help', '/rules']:
                assert page.goto(origin+path).status == 200
                keyboard_about(page, origin)
            assert attempts == []
        finally:
            browser.close()


def test_desktop_about_works_with_external_network_blocked(tmp_path: Path):
    api = pytest.importorskip('playwright.sync_api')
    with desktop(tmp_path/'desktop') as server, api.sync_playwright() as runner:
        browser = runner.chromium.launch()
        try:
            context = browser.new_context(viewport={'width': 390, 'height': 950})
            attempts = guard_external(context)
            page = context.new_page()
            assert page.goto(server.url).status == 200
            keyboard_about(page, server.origin)
            assert 'This page is bundled with the app.' in page.content()
            page.goto(server.origin)
            with page.expect_download() as pending:
                page.get_by_role('link', name='Download sample PDF', exact=True).click()
            sample = tmp_path/'synthetic-example.pdf'
            pending.value.save_as(sample)
            assert pending.value.failure() is None
            page.locator('input[type=file]').set_input_files(sample)
            page.get_by_role('button', name='Start audit', exact=True).click()
            page.wait_for_url('**/audits/*')
            job = urlsplit(page.url).path
            wait_state(context.request, server.origin, job, {'complete'})
            page.reload()
            keyboard_about(page, server.origin)
            for path in ['/help', '/rules']:
                assert page.goto(server.origin+path).status == 200
                keyboard_about(page, server.origin)
            assert attempts == []
        finally:
            browser.close()
