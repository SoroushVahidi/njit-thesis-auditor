"""Real local browser workflow, with a file gate instead of timing a fast audit."""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import pymupdf
import pytest
from desktop_session_support import wait_state
from test_about_browser import guard_external

from njit_auditor.synthetic_sample import sample_pdf

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = '''import json, os, sys, threading, time
from pathlib import Path
import uvicorn
from njit_auditor import web_app as web
root = Path(sys.argv[1])
real_audit = web.run_audit_for_uploaded_file
calls = 0
def gated_audit(*args, **kwargs):
    global calls
    calls += 1
    marker = root/'worker.tmp'
    marker.write_text(json.dumps({'calls': calls, 'pid': os.getpid(),
                                  'thread': threading.get_ident()}))
    marker.replace(root/'worker.json')
    deadline = time.monotonic()+45
    while not (root/'release').exists():
        if time.monotonic()>deadline:
            raise RuntimeError('Synthetic test gate was not released')
        time.sleep(.02)
    return real_audit(*args, **kwargs)
web.run_audit_for_uploaded_file = gated_audit
uvicorn.run(web.app, host='127.0.0.1', port=int(sys.argv[2]), log_level='warning',
            access_log=False)
'''


@contextmanager
def gated_website(directory: Path):
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    origin = f'http://127.0.0.1:{port}'
    env = {**os.environ, 'PYTHONPATH': str(ROOT/'src'),
           'NJIT_AUDITOR_WEB_RUNTIME_DIR': str(directory/'jobs')}
    with (directory/'server.log').open('wb') as log:
        process = subprocess.Popen([sys.executable, '-c', BOOTSTRAP, str(directory), str(port)],
                                   cwd=ROOT, env=env, stdout=log, stderr=log)
        try:
            deadline = time.monotonic()+20
            while True:
                assert process.poll() is None, 'Synthetic server exited; see server.log'
                try:
                    if httpx.get(origin+'/healthz', timeout=1, trust_env=False).status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                assert time.monotonic()<deadline, 'Synthetic server startup timed out'
                time.sleep(.05)
            yield origin
        finally:
            # Release only our gate so an assertion cannot leave a blocked worker.
            (directory/'release').touch()
            process.terminate()
            process.wait(timeout=15)


def click_pdf(page, context, link, suffix):
    """Follow the real rendered link; verify the real server's PDF response."""
    href = link.get_attribute('href')
    assert href and suffix in href
    with context.expect_event('response', predicate=lambda r: suffix in r.url) as pending:
        link.click()
    response = pending.value
    assert response.status == 200
    assert response.headers['content-type'].startswith('application/pdf')
    payload = context.request.get(response.url)
    assert payload.status == 200 and payload.body().startswith(b'%PDF-')
    return payload.body()


def test_refresh_preserves_worker_and_actual_pdf_links(tmp_path: Path):
    api = pytest.importorskip('playwright.sync_api')
    # Generated in memory: no checked-in/LFS/private PDF, public release or production service.
    with pymupdf.open(stream=sample_pdf(), filetype='pdf') as document:
        document[0].insert_text((12, 180), 'Synthetic margin-crossing example only.', fontsize=12)
        upload = document.tobytes()
        upload_pages = document.page_count
    with gated_website(tmp_path) as origin, api.sync_playwright() as runner:
        browser = runner.chromium.launch()
        try:
            context = browser.new_context(accept_downloads=True)
            attempts = guard_external(context)
            posts = []
            context.on('request', lambda r: posts.append(urlsplit(r.url).path)
                       if r.method == 'POST' else None)
            page = context.new_page()
            assert page.goto(origin).status == 200
            page.locator('input[type=file]').set_input_files(
                {'name': 'synthetic-workflow.pdf', 'mimeType': 'application/pdf', 'buffer': upload})
            page.get_by_role('button', name='Start audit', exact=True).click()
            page.wait_for_url('**/audits/*')
            job = urlsplit(page.url).path
            wait_state(context.request, origin, job, {'running'})
            # The gate is inside the actual audit call, after the job becomes running.
            deadline = time.monotonic()+10
            while not (tmp_path/'worker.json').exists():
                assert time.monotonic()<deadline
                page.wait_for_timeout(20)
            worker = (tmp_path/'worker.json').read_bytes()
            assert json.loads(worker)['calls'] == 1
            assert page.reload().status == 200
            assert urlsplit(page.url).path == job
            assert page.get_by_text('Processing audit', exact=False).is_visible()
            pages = [('Help', '/help'), ('Rule Reference', '/rules'), ('About Us', '/about')]
            for label, path in pages:
                page.get_by_role('navigation').get_by_role('link', name=label, exact=True).click()
                page.wait_for_url(origin+path)
                page.go_back()
                page.wait_for_url(origin+job)
            assert (tmp_path/'worker.json').read_bytes() == worker
            assert wait_state(context.request, origin, job, {'running'})['state'] == 'running'
            assert len(list((tmp_path/'jobs').glob('*/upload.pdf'))) == 1
            assert posts == ['/audits'], 'Refresh/navigation must not resubmit the PDF'
            (tmp_path/'release').touch()
            wait_state(context.request, origin, job, {'complete'})
            page.reload()
            page.locator('#section-downloads').wait_for()
            assert page.reload().status == 200
            assert urlsplit(page.url).path == job
            assert (tmp_path/'worker.json').read_bytes() == worker
            assert posts == ['/audits']
            original = click_pdf(page, context, page.locator('#open-pdf-btn'), job+'/pdf')
            assert original == upload
            highlight = page.locator('a[href*="/highlighted-page.pdf"]').first
            highlight.wait_for()
            marked = click_pdf(page, context, highlight, job+'/highlighted-page.pdf')
            with pymupdf.open(stream=marked, filetype='pdf') as document:
                assert document.page_count == 1
                assert document[0].get_drawings() or list(document[0].annots())
            with page.expect_download() as pending:
                page.get_by_role('link', name='Download Complete PDF Report', exact=True).click()
            download = pending.value
            assert download.failure() is None
            target = tmp_path/'complete-report.pdf'
            download.save_as(target)
            with pymupdf.open(target) as document:
                assert document.page_count>upload_pages
            assert attempts == [], 'This workflow must never contact external services'
        finally:
            browser.close()


def test_upload_only_errors_remain_clear_after_browser_refresh(tmp_path: Path):
    api = pytest.importorskip('playwright.sync_api')
    with gated_website(tmp_path) as origin, api.sync_playwright() as runner:
        browser = runner.chromium.launch()
        try:
            context = browser.new_context(accept_downloads=True)
            attempts = guard_external(context)
            posts = []
            context.on('request', lambda r: posts.append(urlsplit(r.url).path)
                       if r.method == 'POST' else None)
            page = context.new_page()
            page.goto(origin)
            assert page.locator('input[type=url], input[name=pdf_url]').count() == 0
            assert page.locator('form[action="/audits/url"], '
                                'form[action="/audits/sample"]').count() == 0
            with page.expect_download() as pending:
                page.get_by_role('link', name='Download sample PDF', exact=True).click()
            assert pending.value.failure() is None
            assert not (tmp_path/'worker.json').exists()
            for endpoint in ['/audits', '/audits/url', '/audits/sample']:
                page.goto(origin)
                page.evaluate('''endpoint => {
                    const form = document.createElement('form');
                    form.method = 'post'; form.action = endpoint;
                    const input = document.createElement('input');
                    input.name = 'pdf_url'; input.value = 'https://example.invalid/thesis.pdf';
                    form.append(input); document.body.append(form); form.submit();
                }''', endpoint)
                page.wait_for_url('**/?error=*')
                message = page.get_by_role('alert')
                assert 'Please upload your document to start an audit.' in message.inner_text()
                before = list(posts)
                assert page.reload().status == 400
                assert 'Please upload your document to start an audit.' in message.inner_text()
                assert posts == before
                page.get_by_role('navigation').get_by_role('link', name='Help', exact=True).click()
                page.wait_for_url(origin+'/help')
                assert 'Upload a thesis or dissertation PDF.' in page.locator('body').inner_text()
                page.go_back()
                page.wait_for_url('**/?error=*')
                assert posts == before
            assert not (tmp_path/'worker.json').exists()
            assert not list((tmp_path/'jobs').glob('*/upload.pdf'))
            assert attempts == []
        finally:
            browser.close()
