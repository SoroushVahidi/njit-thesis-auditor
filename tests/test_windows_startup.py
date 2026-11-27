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
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
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
assert 'njit_auditor.windows_launcher' not in sys.modules
assert 'tkinter' not in sys.modules
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

@pytest.mark.skipif(sys.platform != "win32", reason="Requires stock Win32 controls")
@pytest.mark.parametrize("dpi", [96, 120, 144, 192])
def test_native_dialog_keyboard_states_and_simulated_dpi(dpi):
    """Real controls, focus and callbacks; DPI values are simulated, not monitor changes."""
    import ctypes as c
    from ctypes import wintypes as w

    from njit_auditor.windows_launcher import (
        BROWSER_ERROR,
        OPENED,
        READY,
        STARTING,
        STOP_ERROR,
        STOPPING,
        WindowsLauncher,
    )

    alive = True
    server = SimpleNamespace(started=False, should_exit=False)
    events = []
    outcomes = iter([False, OSError("synthetic browser failure"), True, True])

    def open_browser():
        events.append("open")
        value = next(outcomes)
        if isinstance(value, Exception):
            raise value
        return value

    def quit_auditor():
        events.append("quit")
        return False

    window = WindowsLauncher(server, SimpleNamespace(is_alive=lambda: alive),
                             open_browser, quit_auditor)
    user = window.user
    user.GetFocus.restype = w.HWND
    user.GetFocus.argtypes = []
    user.IsWindowEnabled.argtypes = [w.HWND]
    user.GetClientRect.argtypes = [w.HWND, c.POINTER(w.RECT)]
    user.MapWindowPoints.argtypes = [w.HWND, w.HWND, c.c_void_p, w.UINT]
    user.GetKeyboardState.argtypes = [c.c_void_p]
    user.SetKeyboardState.argtypes = [c.c_void_p]

    def key(vk, shift=False):
        # Only this test thread's keyboard state and this owned dialog receive input.
        original = (c.c_ubyte * 256)()
        assert user.GetKeyboardState(original)
        modified = (c.c_ubyte * 256).from_buffer_copy(original)
        modified[0x10] = 0x80 if shift else 0
        try:
            assert user.SetKeyboardState(modified)
            for message in (0x100, 0x101):
                msg = w.MSG()
                msg.hWnd = user.GetFocus()
                msg.message, msg.wParam = message, vk
                msg.lParam = 1 if message == 0x100 else 0xC0000001
                window._message(msg)
        finally:
            assert user.SetKeyboardState(original)
        window.update()

    try:
        assert window.status == STARTING
        assert not user.IsWindowEnabled(window.controls["open"])
        assert user.GetFocus() == window.controls["quit"]
        server.started = True
        window.poll()
        assert window.status == READY
        assert user.GetFocus() == window.controls["open"]
        key(9)
        assert user.GetFocus() == window.controls["quit"]
        key(9, shift=True)
        assert user.GetFocus() == window.controls["open"]
        key(13)
        assert events == ["open"]
        assert window.status == BROWSER_ERROR
        key(32)
        assert events == ["open", "open"]
        assert window.status == BROWSER_ERROR
        key(13)
        assert window.status == OPENED
        key(32)
        assert events.count("open") == 4
        user.SetFocus(window.controls["quit"])
        key(13)
        assert events[-1] == "quit"
        assert events.count("open") == 4  # Enter on Quit must not invoke the default Open.
        assert window.status == STOP_ERROR
        key(32)
        assert events.count("quit") == 2
        assert window.status == STOP_ERROR
        suggested = w.RECT()
        assert user.GetWindowRect(window.hwnd, c.byref(suggested))
        # Deliver WM_DPICHANGED on the owner thread with a valid suggested RECT.
        # This exercises the real handler without changing desktop settings.
        window._dispatch(window.hwnd, 0x2E0, dpi | (dpi << 16), c.addressof(suggested))
        window.update()
        client = w.RECT()
        assert user.GetClientRect(window.hwnd, c.byref(client))
        for child in window.controls.values():
            bounds = w.RECT()
            assert user.GetWindowRect(child, c.byref(bounds))
            user.MapWindowPoints(None, window.hwnd, c.byref(bounds), 2)
            assert 0 <= bounds.left < bounds.right <= client.right
            assert 0 <= bounds.top < bounds.bottom <= client.bottom
        server.should_exit = True
        window.poll()
        assert window.status == STOPPING
        assert not user.IsWindowEnabled(window.controls["open"])
        alive = False
        window.poll()
        assert window.hwnd is None
    finally:
        window.destroy()

@pytest.mark.skipif(sys.platform != "win32", reason="Requires native Windows dialog")
def test_native_source_gui_quit_cleans_up(tmp_path):
    import ctypes as c
    from ctypes import wintypes as w

    import psutil

    state = tmp_path / "state.json"
    profile = tmp_path / "profile"
    env = {
        **os.environ, "LOCALAPPDATA": str(profile), "XDG_DATA_HOME": str(profile),
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
    }
    process = subprocess.Popen(
        [sys.executable, "-B", "-c",
         "from pathlib import Path; import sys; "
         "from njit_auditor.offline_launcher import run_desktop; "
         "run_desktop(open_browser=False, state_file=Path(sys.argv[1]))", str(state)],
        env=env, creationflags=0x08000000,
    )
    user = c.WinDLL("user32")
    user.GetWindowThreadProcessId.argtypes = [w.HWND, c.POINTER(w.DWORD)]
    user.GetDlgItem.argtypes = [w.HWND, c.c_int]
    user.GetDlgItem.restype = w.HWND
    user.PostMessageW.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM]
    user.GetClassNameW.argtypes = [w.HWND, w.LPWSTR, c.c_int]
    user.IsWindowVisible.argtypes = [w.HWND]
    callback_type = c.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)
    user.EnumWindows.argtypes = [callback_type, w.LPARAM]
    owned = {}
    try:
        deadline = time.monotonic() + 30
        hwnd = None
        while hwnd is None or not state.exists():
            assert process.poll() is None
            assert time.monotonic() < deadline
            root = psutil.Process(process.pid)
            owned.update({p.pid: p for p in [root, *root.children(recursive=True)]})
            found = []

            def inspect(handle, _):
                pid = w.DWORD()
                user.GetWindowThreadProcessId(handle, c.byref(pid))
                if pid.value in owned and user.IsWindowVisible(handle):
                    kind = c.create_unicode_buffer(100)
                    user.GetClassNameW(handle, kind, 100)
                    if kind.value == "#32770":
                        found.append(handle)
                return True

            user.EnumWindows(callback_type(inspect), 0)
            hwnd = found[0] if found else None
            time.sleep(0.05)
        # A synthetic file verifies the normal launcher's final temp cleanup.
        temp = profile / "NJIT Thesis Auditor" / "tmp"
        (temp / "synthetic-cleanup.txt").write_text("qualification only", encoding="utf-8")
        quit_button = user.GetDlgItem(hwnd, 102)
        assert quit_button
        assert user.PostMessageW(quit_button, 0x100, 32, 1)
        assert user.PostMessageW(quit_button, 0x101, 32, 0xC0000001)
        assert process.wait(timeout=20) == 0
        assert not state.exists()
        assert not list(temp.iterdir())
        _, remaining = psutil.wait_procs(list(owned.values()), timeout=5)
        assert not remaining, [(p.pid, p.name()) for p in remaining]
    finally:
        # Include interpreter-shim descendants rather than leaving an orphan GUI.
        for child in reversed(list(owned.values())):
            try:
                if child.is_running():
                    child.terminate()
                    child.wait(timeout=5)
            except psutil.NoSuchProcess:
                pass
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)
