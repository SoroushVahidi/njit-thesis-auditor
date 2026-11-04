"""Smoke-test the built application with one synthetic PDF, without installing it."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

from njit_auditor.synthetic_sample import sample_pdf


def smoke(executable: Path, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='njit-beta-smoke-') as directory:
        root = Path(directory)
        state = root / 'launch.json'
        source = root / 'synthetic.pdf'
        source.write_bytes(sample_pdf())
        env = {**os.environ, 'LOCALAPPDATA': str(root), 'XDG_DATA_HOME': str(root)}
        env.pop('PYTHONPATH', None)
        env.pop('PYTHONHOME', None)
        with (output / 'application.log').open('wb') as log:
            process = subprocess.Popen(
                [str(executable.resolve()), '--headless', '--no-browser',
                 '--state-file', str(state)],
                env=env, stdout=log, stderr=log,
            )
            try:
                deadline = time.monotonic() + 60
                while not state.exists():
                    assert process.poll() is None, 'Application exited before startup'
                    assert time.monotonic() < deadline, 'Application did not start'
                    time.sleep(0.1)
                launch = json.loads(state.read_text(encoding='utf-8'))['url']
                origin = launch.split('/_session/')[0]
                with sync_playwright() as runner:
                    browser = runner.chromium.launch()
                    context = browser.new_context(base_url=origin)
                    external = []

                    def guard(route):
                        if urlsplit(route.request.url).hostname != '127.0.0.1':
                            external.append(route.request.url)
                            route.abort()
                        else:
                            route.continue_()

                    context.route('**/*', guard)
                    page = context.new_page()
                    assert page.goto(launch).status == 200
                    for path in ['/help', '/rules']:
                        assert page.goto(origin + path).status == 200
                    page.goto(origin)
                    page.locator('input[type=file]').set_input_files(str(source))
                    page.get_by_role('button', name='Start audit', exact=True).click()
                    page.wait_for_url('**/audits/*')
                    job = urlsplit(page.url).path
                    deadline = time.monotonic() + 120
                    while True:
                        status = context.request.get(job + '/status').json()
                        if status['state'] in {'complete', 'failed'}:
                            break
                        assert time.monotonic() < deadline, 'Audit did not finish'
                        page.wait_for_timeout(200)
                    assert status['state'] == 'complete', status['state']
                    page.reload()
                    assert 'Finding 1 of' in page.content()
                    assert page.locator('time[data-local-time]').inner_text() != (
                        page.locator('time[data-local-time]').get_attribute('datetime')
                    )
                    for suffix in ['download/json', 'download/text', 'download/markdown',
                                   'download/student-report.pdf', 'pdf']:
                        response = context.request.get(job + '/' + suffix)
                        assert response.status == 200, suffix
                        payload = response.body()
                        if suffix.endswith('pdf'):
                            assert payload.startswith(b'%PDF-'), suffix
                        elif suffix.endswith('json'):
                            assert isinstance(response.json(), dict)
                        else:
                            payload.decode('utf-8')
                            assert b'\r\n' not in payload, suffix
                    assert not external, 'Unexpected browser network access'
                    page.get_by_role('button', name='Quit', exact=True).click()
                    browser.close()
                assert process.wait(timeout=30) == 0
                (output / 'result.json').write_text(json.dumps({
                    'startup': 'passed', 'synthetic_audit': 'passed',
                    'exports': 'passed', 'local_help_rules': 'passed',
                    'local_completion_time': 'passed', 'shutdown': 'passed',
                    'installer_lifecycle_tested': False, 'windows11_qualified': False,
                }, indent=2) + '\n', encoding='utf-8')
            finally:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=30)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--executable', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    smoke(args.executable, args.output)
