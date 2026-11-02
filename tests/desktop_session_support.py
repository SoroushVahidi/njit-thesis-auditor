"""Owned, synthetic desktop processes; never use the user's app data or browser."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit

import httpx

from njit_auditor.desktop_process import ProcessTree

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = """
import json, sys
from pathlib import Path
from njit_auditor import offline_app
from njit_auditor.desktop_executor import DesktopExecutor, worker_command
from njit_auditor.desktop_protocol import decode
from njit_auditor.offline_launcher import run_desktop

if sys.argv[2] == 'delayed':
    def command(request):
        job = decode(json.loads(request.read_text(encoding='utf-8'))['job'])
        if job['file_name'].startswith('cancel-'):
            return [sys.executable, '-c', 'import time; time.sleep(120)']
        return worker_command(request)
    offline_app.DesktopExecutor = lambda: DesktopExecutor(command=command)
run_desktop(headless=True, open_browser=False, state_file=Path(sys.argv[1]))
"""


def csrf_token(html: str) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match, "Expected authenticated form"
    return match.group(1)


def wait_state(request, origin: str, job: str, wanted: set[str]) -> dict:
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        response = request.get(origin + job + "/status")
        # httpx and Playwright both expose json(), but different status properties.
        assert getattr(response, "status_code", getattr(response, "status", None)) == 200
        status = response.json()
        if status["state"] in wanted:
            return status
        time.sleep(0.05)
    raise AssertionError(f"Audit did not reach {wanted}; last state: {status['state']}")


@contextmanager
def desktop(directory: Path, *, delayed: bool = False):
    directory.mkdir(parents=True)
    profile = directory / "profile"
    state = directory / "launch.json"
    env = {
        **os.environ,
        "LOCALAPPDATA": str(profile),
        "XDG_DATA_HOME": str(profile),
        "PYTHONPATH": str(ROOT / "src"),
    }
    command = [sys.executable, "-c", BOOTSTRAP, str(state), "delayed" if delayed else "normal"]
    with (directory / "process.log").open("wb") as log:
        process = subprocess.Popen(
            command, env=env, stdout=log, stderr=log,
            creationflags=0x08000000 if os.name == "nt" else 0,
        )
        tree = None
        try:
            tree = ProcessTree(process)
            deadline = time.monotonic() + 25
            while True:
                assert process.poll() is None, "Test desktop exited; see process.log"
                try:
                    launch = json.loads(state.read_text(encoding="utf-8"))
                    break
                except (FileNotFoundError, json.JSONDecodeError):
                    assert time.monotonic() < deadline, "Test desktop startup timed out"
                    time.sleep(0.05)
            parsed = urlsplit(launch["url"])
            origin = f"{parsed.scheme}://{parsed.netloc}"
            with httpx.Client(base_url=origin, follow_redirects=True, trust_env=False) as client:
                page = client.get(launch["url"])
                assert page.status_code == 200
                try:
                    yield SimpleNamespace(
                        process=process, url=launch["url"], origin=origin, client=client,
                        csrf=csrf_token(page.text), profile=profile, state=state, env=env,
                    )
                finally:
                    response = client.post(
                        "/quit", data={"csrf_token": csrf_token(page.text)},
                        headers={"Origin": origin},
                    )
                    assert response.status_code == 200
                    assert process.wait(timeout=15) == 0
                    assert not state.exists()
        finally:
            # Only our owned tree, even if an assertion/startup/quit fails.
            if tree is not None:
                tree.stop()
            elif process.poll() is None:
                process.terminate()
                process.wait(timeout=15)
