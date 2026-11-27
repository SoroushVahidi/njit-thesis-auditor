"""Exercise the no-console startup failure without claiming native qualification."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit

import httpx
import pytest
from desktop_session_support import desktop, wait_state
from test_offline_desktop import _pdf


@pytest.mark.parametrize("dpi", [96, 120, 144, 192])
def test_launcher_controls_fit_and_offer_browser_retry(dpi: int) -> None:
    tk = pytest.importorskip("tkinter")
    from tkinter import ttk

    from njit_auditor.offline_launcher import _configure_window

    try:
        window = tk.Tk()
    except tk.TclError:
        pytest.skip("Requires a graphical Tk session")
    try:
        window.tk.call("tk", "scaling", dpi / 72)
        server = SimpleNamespace(started=True, should_exit=False)
        thread = SimpleNamespace(is_alive=lambda: True)
        retry = _configure_window(window, server, thread, lambda: False, lambda: False)
        window.update()
        frame = window.winfo_children()[0]
        buttons = frame.winfo_children()[3]
        assert [button.cget("text") for button in buttons.winfo_children()] == [
            "Open auditor", "Quit",
        ]
        assert all(isinstance(button, ttk.Button) for button in buttons.winfo_children())
        assert window.winfo_reqwidth() <= window.winfo_width()
        assert window.winfo_reqheight() <= window.winfo_height()
        minimum_title_width = min(
            round(window.winfo_fpixels("300p")), int(window.winfo_screenwidth() * 0.9)
        )
        assert window.winfo_width() >= minimum_title_width
        retry()
        assert "Could not open your browser" in window.getvar(
            frame.winfo_children()[2].cget("textvariable")
        )
        buttons.winfo_children()[1].invoke()
        assert "Try Quit again" in window.getvar(frame.winfo_children()[2].cget("textvariable"))
    finally:
        window.destroy()


def test_launcher_without_console_streams_starts_and_quits(tmp_path: Path) -> None:
    state = tmp_path / "state.json"
    diagnostic = tmp_path / "startup-exceptions.txt"
    env = {
        **os.environ,
        "LOCALAPPDATA": str(tmp_path / "profile"),
        "XDG_DATA_HOME": str(tmp_path / "profile"),
    }
    code = """
import sys, threading, traceback
from pathlib import Path
def record(kind, value, tb):
    with Path(sys.argv[2]).open('a', encoding='utf-8') as output:
        traceback.print_exception(kind, value, tb, file=output)
sys.excepthook = record
threading.excepthook = lambda args: record(args.exc_type, args.exc_value, args.exc_traceback)
sys.stdout = None
sys.stderr = None
from njit_auditor.offline_launcher import run_desktop
run_desktop(headless=True, open_browser=False, state_file=Path(sys.argv[1]))
"""
    process = subprocess.Popen([sys.executable, "-c", code, str(state), str(diagnostic)], env=env)
    try:
        deadline = time.monotonic() + 20
        while not state.exists():
            assert process.poll() is None, "Windowed startup failed:\n" + (
                diagnostic.read_text(encoding="utf-8") if diagnostic.exists() else "No traceback"
            )
            assert time.monotonic() < deadline, "Windowed startup timed out"
            time.sleep(0.05)
        # File publication is tiny, but do not race the writer while loading it.
        for _ in range(100):
            try:
                url = json.loads(state.read_text())["url"]
                break
            except (json.JSONDecodeError, KeyError):
                time.sleep(0.01)
        else:
            raise AssertionError("Incomplete startup state")
        parsed = urlsplit(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        with httpx.Client(base_url=origin, follow_redirects=True) as client:
            page = client.get(url)
            assert page.status_code == 200
            assert "NJIT Thesis Auditor" in page.text
            csrf = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
            assert client.get("/help").status_code == 200
            assert client.get("/rules").status_code == 200
            result = client.post("/quit", data={"csrf_token": csrf}, headers={"Origin": origin})
            assert result.status_code == 200
        assert process.wait(timeout=15) == 0
        assert not state.exists()
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=15)


@pytest.mark.skipif(sys.platform != "win32", reason="Exercises native Windows byte-range locking")
def test_same_profile_second_launch_is_rejected_without_touching_first_audit(tmp_path):
    with desktop(tmp_path / "first") as server:
        root = server.profile / "NJIT Thesis Auditor"
        sentinel = root / "tmp" / "active-work.txt"
        sentinel.write_text("synthetic active work", encoding="utf-8")
        response = server.client.post(
            "/audits", data={"csrf_token": server.csrf},
            files={"file": ("synthetic.pdf", _pdf("normal"), "application/pdf")},
            headers={"Origin": server.origin}, follow_redirects=False,
        )
        assert response.status_code == 303
        job = response.headers["location"]
        assert wait_state(server.client, server.origin, job, {"complete", "failed"})[
            "state"
        ] == "complete"
        before = server.client.get(job + "/download/json").content
        second_state = tmp_path / "second.json"
        second = subprocess.run(
            [sys.executable, "-m", "njit_auditor.offline_launcher", "--headless",
             "--no-browser", "--state-file", str(second_state)],
            env=server.env, capture_output=True, timeout=15, creationflags=0x08000000,
        )
        assert second.returncode != 0
        assert b"NJIT Thesis Auditor is already running" in second.stderr
        assert not second_state.exists()
        assert sentinel.read_text(encoding="utf-8") == "synthetic active work"
        assert server.process.poll() is None
        assert server.client.get(job + "/download/json").content == before
        assert server.client.get("/help").status_code == 200
