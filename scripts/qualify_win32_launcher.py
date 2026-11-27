"""Qualify an exact Windows package and owned stock-control source windows.

Usage: python scripts/qualify_win32_launcher.py --executable PATH --output DIRECTORY
Optional: --baseline-executable PATH --build-root PATH. This script NEVER builds.
Requires qualification-only psutil, pywin32, pywinauto, comtypes and Pillow.
No browser is launched, no global keys/settings are changed. All captures use
PrintWindow on owned windows. Source callback/DPI injection is labelled simulated.
A nonzero exit means a failed or unavailable required qualification, not a pass.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

TITLE = "NJIT Thesis Auditor"


def wait_for(check, timeout=20):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        value = check()
        if value:
            return value
        time.sleep(0.05)
    raise TimeoutError("Owned-window qualification timed out")


def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def snapshot(hwnd, label, output):
    """Window-only PrintWindow capture, adapted from the verified native probe."""
    from ctypes import wintypes

    import win32gui
    import win32ui
    from PIL import Image

    win32gui.UpdateWindow(hwnd)
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    width, height = right - left, bottom - top
    dc = win32gui.GetWindowDC(hwnd)
    source = win32ui.CreateDCFromHandle(dc)
    memory = source.CreateCompatibleDC()
    bitmap = win32ui.CreateBitmap()
    bitmap.CreateCompatibleBitmap(source, width, height)
    saved = memory.SelectObject(bitmap)
    try:
        user = ctypes.WinDLL("user32", use_last_error=True)
        user.PrintWindow.argtypes = (wintypes.HWND, wintypes.HDC, wintypes.UINT)
        if not user.PrintWindow(hwnd, memory.GetSafeHdc(), 2):
            raise ctypes.WinError(ctypes.get_last_error())
        picture = Image.frombuffer(
            "RGB", (width, height), bitmap.GetBitmapBits(True), "raw", "BGRX", 0, 1
        )
        if not any(lo != hi for lo, hi in picture.getextrema()):
            raise RuntimeError("Capture did not contain a painted window")
        picture.save(output / f"{label}.png")
        user.GetDpiForWindow.argtypes = (wintypes.HWND,)
        return {"window_size": [width, height], "actual_window_dpi": user.GetDpiForWindow(hwnd)}
    finally:
        if saved:
            memory.SelectObject(saved)
        memory.DeleteDC()
        source.DeleteDC()
        win32gui.DeleteObject(bitmap.GetHandle())
        win32gui.ReleaseDC(hwnd, dc)


def _accessibility(hwnd, view):
    """Independent UIA and direct MSAA providers from the verified probe."""
    records = {"control": [], "raw": [], "msaa": []}
    if view in ("control", "raw"):
        from pywinauto.uia_defines import IUIA, get_elem_interface

        print("Acquiring owned UIA root", flush=True)
        automation = IUIA().iuia
        root = automation.ElementFromHandle(hwnd)
        pid = root.CurrentProcessId
        walker = automation.ControlViewWalker if view == "control" else automation.RawViewWalker
        print("Walking bounded UIA " + view + " view", flush=True)
        stack = [walker.GetFirstChildElement(root)]
        visited = 0
        while stack and visited < 100:
            child = stack.pop()
            visited += 1
            if not child:
                continue
            sibling = walker.GetNextSiblingElement(child)
            if sibling:
                stack.append(sibling)
            if child.CurrentProcessId != pid:
                continue
            row = {
                "name": child.CurrentName,
                "type": child.CurrentControlType,
                "class": child.CurrentClassName,
                "enabled": child.CurrentIsEnabled,
                "keyboard_focusable": child.CurrentIsKeyboardFocusable,
            }
            if view == "control":
                try:
                    legacy = get_elem_interface(child, "LegacyIAccessible")
                    row["legacy"] = {"name": legacy.CurrentName, "role": legacy.CurrentRole}
                except Exception as exc:
                    row["legacy_error"] = type(exc).__name__
            records[view].append(row)
            sub = walker.GetFirstChildElement(child)
            if sub:
                stack.append(sub)
    else:
        try:
            from ctypes import wintypes

            import comtypes
            import comtypes.client
            from comtypes.automation import VARIANT, IDispatch

            lib = comtypes.client.GetModule(str(Path(os.environ["WINDIR"]) / "System32/oleacc.dll"))
            interface = lib.IAccessible
            ole = ctypes.OleDLL("oleacc")
            accessible = ole.AccessibleObjectFromWindow
            accessible.argtypes = (
                wintypes.HWND,
                wintypes.DWORD,
                ctypes.POINTER(comtypes.GUID),
                ctypes.POINTER(ctypes.POINTER(interface)),
            )
            accessible.restype = ctypes.c_long
            children = ole.AccessibleChildren
            children.argtypes = (
                ctypes.POINTER(interface),
                wintypes.LONG,
                wintypes.LONG,
                ctypes.POINTER(VARIANT),
                ctypes.POINTER(wintypes.LONG),
            )
            children.restype = ctypes.c_long
            obj = ctypes.POINTER(interface)()
            result = accessible(hwnd, 0xFFFFFFFC, ctypes.byref(interface._iid_), ctypes.byref(obj))
            if result < 0:
                raise OSError(f"AccessibleObjectFromWindow HRESULT {result}")

            def inspect(obj, child, depth):
                if depth > 8 or len(records["msaa"]) >= 100:
                    return
                row = {"depth": depth}
                for prop in ("accName", "accRole", "accState"):
                    try:
                        row[prop] = getattr(obj, prop)[child]
                    except Exception as exc:
                        row[prop + "Error"] = type(exc).__name__
                records["msaa"].append(row)
                count = 0 if child else min(40, obj.accChildCount)
                if not count:
                    return
                values = (VARIANT * count)()
                actual = wintypes.LONG()
                if children(obj, 0, count, values, ctypes.byref(actual)) < 0:
                    raise OSError("AccessibleChildren failed")
                for item in values[: actual.value]:
                    value = item.value
                    if isinstance(value, int):
                        inspect(obj, value, depth + 1)
                    elif isinstance(value, ctypes.POINTER(IDispatch)):
                        inspect(value.QueryInterface(interface), 0, depth + 1)

            inspect(obj, 0, 0)
        except Exception as exc:
            records["msaa_error"] = f"{type(exc).__name__}: {exc}"
    return records


UNAVAILABLE_PROVIDERS = {}


def accessibility(hwnd, output):
    """Bound each independent provider in a disposable, owned process tree."""
    result = {"control": [], "raw": [], "msaa": [], "unverified": {}}
    for view in ("control", "raw", "msaa"):
        if view in UNAVAILABLE_PROVIDERS:
            result["unverified"][view] = UNAVAILABLE_PROVIDERS[view]
            continue
        directory = output / ("accessibility-" + view + "-" + uuid.uuid4().hex)
        directory.mkdir()
        evidence = directory / "accessibility.json"
        owner = OwnedProcess(
            [
                sys.executable,
                "-B",
                str(Path(__file__).resolve()),
                "--accessibility-child",
                str(hwnd),
                "--accessibility-view",
                view,
                "--output",
                str(evidence),
            ],
            directory,
            env={
                **os.environ,
                "PYTHONDONTWRITEBYTECODE": "1",
                "TEMP": str(directory),
                "TMP": str(directory),
            },
        )
        try:
            if owner.process.wait(timeout=20) != 0:
                raise RuntimeError("Provider failed; see owned probe log")
            data = read_state(evidence)
            if not data:
                raise RuntimeError("Provider produced no evidence")
            for key in ("control", "raw", "msaa"):
                result[key].extend(data[key])
            if data.get("msaa_error"):
                raise RuntimeError(data["msaa_error"])
        except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
            UNAVAILABLE_PROVIDERS[view] = f"{type(exc).__name__}: {exc}"
            result["unverified"][view] = UNAVAILABLE_PROVIDERS[view]
        finally:
            write(directory / "cleanup.json", owner.close())
    return result


class OwnedProcess:
    """Sample only a launched child and its descendants; retain identities for cleanup."""

    def __init__(self, command, directory, **kwargs):
        import psutil

        self.psutil = psutil
        self.log = (directory / "child.log").open("wb")
        self.process = subprocess.Popen(command, stdout=self.log, stderr=self.log, **kwargs)
        self.known = {self.process.pid: psutil.Process(self.process.pid)}
        self.samples = []
        self.done = threading.Event()
        self.sampler = threading.Thread(target=self._sample, daemon=True)
        self.sampler.start()

    def _sample(self):
        while not self.done.is_set():
            for proc in list(self.known.values()):
                try:
                    for child in proc.children(recursive=True):
                        self.known.setdefault(child.pid, child)
                except self.psutil.Error:
                    pass
            rows = []
            for proc in list(self.known.values()):
                try:
                    if proc.is_running():
                        rows.append(
                            {
                                "pid": proc.pid,
                                "name": proc.name(),
                                "rss_bytes": proc.memory_info().rss,
                            }
                        )
                except self.psutil.Error:
                    pass
            self.samples.append(
                {
                    "at": time.monotonic(),
                    "processes": rows,
                    "tree_rss_bytes": sum(row["rss_bytes"] for row in rows),
                }
            )
            self.done.wait(0.05)

    def assert_window(self, hwnd):
        import win32gui
        import win32process

        if not win32gui.IsWindow(hwnd):
            raise RuntimeError("Owned window no longer exists")
        pid = win32process.GetWindowThreadProcessId(hwnd)[1]
        proc = self.known.get(pid)
        if not proc or not proc.is_running():
            raise RuntimeError("Refusing to interact with an unowned window")

    def window(self, title=TITLE):
        import win32gui
        import win32process

        def gather():
            if self.process.poll() is not None:
                raise RuntimeError(f"Owned process exited {self.process.returncode}")
            found = []

            def inspect(hwnd, _):
                if (
                    win32gui.IsWindowVisible(hwnd)
                    and win32gui.GetWindowText(hwnd) == title
                    and win32process.GetWindowThreadProcessId(hwnd)[1] in self.known
                ):
                    found.append(hwnd)

            win32gui.EnumWindows(inspect, None)
            return found[0] if found else None

        return wait_for(gather)

    def close(self):
        self.done.set()
        self.sampler.join(timeout=3)
        survivors = []
        for proc in reversed(list(self.known.values())):
            try:
                if proc.is_running():
                    survivors.append(proc)
                    proc.terminate()
            except self.psutil.Error:
                pass
        _, remaining = self.psutil.wait_procs(survivors, timeout=5)
        for proc in remaining:
            try:
                proc.kill()
            except self.psutil.Error:
                pass
        _, remaining = self.psutil.wait_procs(remaining, timeout=5)
        self.log.close()
        if remaining:
            raise RuntimeError("Owned process cleanup failed")
        return {"forced_cleanup_pids": [p.pid for p in survivors], "remaining_owned_processes": 0}


def owned_key(owner, hwnd, target, vk, shift=False):
    """Post keys to an owned child only. Never use SendInput or global keyboard hooks.

    AttachThreadInput provides the actual dialog focus/keyboard state. Restore
    the original state and detach even on failure; this changes no settings.
    """
    from ctypes import wintypes as w

    import win32gui
    import win32process

    owner.assert_window(hwnd)
    if not win32gui.IsChild(hwnd, target):
        raise RuntimeError("Input target is not an owned native child")
    user = ctypes.WinDLL("user32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32")
    kernel.GetCurrentThreadId.restype = w.DWORD
    user.AttachThreadInput.argtypes = [w.DWORD, w.DWORD, w.BOOL]
    user.GetFocus.restype = w.HWND
    user.SetFocus.argtypes = [w.HWND]
    user.SetFocus.restype = w.HWND
    user.GetKeyboardState.argtypes = [ctypes.c_void_p]
    user.SetKeyboardState.argtypes = [ctypes.c_void_p]
    user.PostMessageW.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM]
    current, other = kernel.GetCurrentThreadId(), win32process.GetWindowThreadProcessId(hwnd)[0]
    if not user.AttachThreadInput(current, other, True):
        raise ctypes.WinError(ctypes.get_last_error())
    original = (ctypes.c_ubyte * 256)()
    have_state = False
    try:
        user.SetFocus(target)
        if user.GetFocus() != target:
            raise RuntimeError("Could not establish real focus on owned control")
        if not user.GetKeyboardState(original):
            raise ctypes.WinError(ctypes.get_last_error())
        have_state = True
        state = (ctypes.c_ubyte * 256).from_buffer_copy(original)
        state[0x10] = 0x80 if shift else 0
        if not user.SetKeyboardState(state):
            raise ctypes.WinError(ctypes.get_last_error())
        if not user.PostMessageW(target, 0x100, vk, 1):
            raise ctypes.WinError(ctypes.get_last_error())
        if not user.PostMessageW(target, 0x101, vk, 0xC0000001):
            raise ctypes.WinError(ctypes.get_last_error())
        time.sleep(0.15)
        return user.GetFocus()
    finally:
        if have_state:
            user.SetKeyboardState(original)
        user.AttachThreadInput(current, other, False)


def buttons(hwnd):
    import win32gui

    class Button:
        def __init__(self, identifier):
            self.handle = win32gui.GetDlgItem(hwnd, identifier)
            if win32gui.GetClassName(self.handle).lower() != "button":
                raise RuntimeError("Expected a stock native button")

        def is_enabled(self):
            return win32gui.IsWindowEnabled(self.handle)

    return [Button(identifier) for identifier in (101, 102)]


def verify_accessibility(records, status):
    for view, field in (("control", "name"), ("raw", "name"), ("msaa", "accName")):
        names = [str(row.get(field, "")).replace("&", "") for row in records[view]]
        for expected in ("Open auditor", "Quit", status, "Version "):
            if not any(expected in name for name in names):
                raise AssertionError(f"{view} missing accessible name {expected!r}")


def capture_state(owner, hwnd, output, label, expected=None):
    owner.assert_window(hwnd)
    result = {
        "capture": snapshot(hwnd, label, output),
        "accessibility": accessibility(hwnd, output),
    }
    write(output / f"{label}.json", result)
    if expected:
        try:
            verify_accessibility(result["accessibility"], expected)
        except AssertionError as exc:
            result["failed_or_unverified"] = str(exc)
            write(output / f"{label}.json", result)
    return result


def layout_bounds(hwnd):
    """Check client containment and measured text height with the actual control font."""
    from ctypes import wintypes as w

    import win32gui

    user, gdi = ctypes.WinDLL("user32"), ctypes.WinDLL("gdi32")
    user.SendMessageW.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM]
    user.SendMessageW.restype = ctypes.c_ssize_t
    user.DrawTextW.argtypes = [w.HDC, w.LPCWSTR, ctypes.c_int, ctypes.POINTER(w.RECT), w.UINT]
    gdi.SelectObject.argtypes = [w.HDC, w.HANDLE]
    gdi.SelectObject.restype = w.HANDLE
    client = win32gui.GetClientRect(hwnd)
    rows = []

    def inspect(child, _):
        text = win32gui.GetWindowText(child)
        if not text:
            return
        left, top, right, bottom = win32gui.GetWindowRect(child)
        left, top = win32gui.ScreenToClient(hwnd, (left, top))
        right, bottom = win32gui.ScreenToClient(hwnd, (right, bottom))
        contained = 0 <= left < right <= client[2] and 0 <= top < bottom <= client[3]
        dc = win32gui.GetDC(child)
        previous = gdi.SelectObject(dc, user.SendMessageW(child, 0x31, 0, 0))
        try:
            rect = w.RECT(0, 0, right - left, 0)
            user.DrawTextW(dc, text, -1, ctypes.byref(rect), 0x400 | 0x10)  # CALCRECT/WORDBREAK
            fits = rect.bottom <= bottom - top and rect.right <= right - left
        finally:
            gdi.SelectObject(dc, previous)
            win32gui.ReleaseDC(child, dc)
        rows.append(
            {
                "text": text,
                "bounds": [left, top, right, bottom],
                "contained": contained,
                "measured_text_fits": fits,
            }
        )

    win32gui.EnumChildWindows(hwnd, inspect, None)
    if not rows or not all(row["contained"] and row["measured_text_fits"] for row in rows):
        raise AssertionError(f"Control layout failed: {rows}")
    return rows


def source_child(output):
    """Only source qualification injects state and callbacks; never part of the package."""
    from types import SimpleNamespace

    from njit_auditor.windows_launcher import WindowsLauncher

    server = SimpleNamespace(started=False, should_exit=False)
    state = {"open_calls": 0, "quit_calls": 0, "simulated_callbacks": True, "pid": os.getpid()}
    finished = False

    def open_browser():
        state["open_calls"] += 1
        return state["open_calls"] > 1

    def quit_auditor():
        state["quit_calls"] += 1
        if state["quit_calls"] == 1:
            return False
        server.should_exit = True
        return True

    class SourceWindow(WindowsLauncher):
        def poll(self):
            super().poll()
            state.update(status=self.status, simulated_dpi=self.dpi)
            write(output / "source-state.json", state)

        def _dispatch(self, hwnd, message, wp, lp):
            nonlocal finished
            if message == 0x8003:
                finished = True
                self.poll()
                return 1
            if message == 0x8002:
                server.started = True
                self.poll()
                return 1
            if message == 0x8001:
                from ctypes import wintypes as w

                rect = w.RECT()
                self.user.GetWindowRect(hwnd, ctypes.byref(rect))
                super()._dispatch(hwnd, 0x2E0, wp | (wp << 16), ctypes.addressof(rect))
                state.update(simulated_dpi=wp)
                write(output / "source-state.json", state)
                return 1
            return super()._dispatch(hwnd, message, wp, lp)

    thread = SimpleNamespace(is_alive=lambda: not finished)
    window = SourceWindow(server, thread, open_browser, quit_auditor)
    try:
        window.mainloop()
    finally:
        window.destroy()


def qualify_source(output, build_root):
    import win32gui

    directory = output / "source-simulated"
    directory.mkdir()
    env = {**os.environ, "PYTHONPATH": str(build_root / "src"), "PYTHONDONTWRITEBYTECODE": "1"}
    owner = OwnedProcess(
        [
            sys.executable,
            "-B",
            str(Path(__file__).resolve()),
            "--source-child",
            "--output",
            str(directory),
        ],
        directory,
        cwd=build_root,
        env=env,
    )
    row = {"state_and_dpi": "simulated source callbacks and WM_DPICHANGED layout path"}
    try:
        hwnd = owner.window()
        row["starting"] = capture_state(owner, hwnd, directory, "starting", "Starting the local")
        open_button, quit_button = buttons(hwnd)
        assert not open_button.is_enabled()
        owner.assert_window(hwnd)
        win32gui.PostMessage(hwnd, 0x8002, 0, 0)
        wait_for(lambda: open_button.is_enabled())
        row["ready"] = capture_state(owner, hwnd, directory, "ready", "Ready to open")
        open_handle, quit_handle = open_button.handle, quit_button.handle
        assert owned_key(owner, hwnd, open_handle, 9) == quit_handle
        assert owned_key(owner, hwnd, quit_handle, 9, shift=True) == open_handle
        row["tab_shift_tab"] = "passed with real focus"
        owned_key(owner, hwnd, open_handle, 13)
        wait_for(
            lambda: (
                "Could not open" in read_state(directory / "source-state.json").get("status", "")
            )
        )
        row["browser_error"] = capture_state(
            owner, hwnd, directory, "browser-error", "Could not open"
        )
        owned_key(owner, hwnd, open_handle, 32)
        wait_for(
            lambda: "Auditor ready" in read_state(directory / "source-state.json").get("status", "")
        )
        row["recovery"] = capture_state(owner, hwnd, directory, "recovery", "Auditor ready")
        row["simulated_dpi_layout"] = []
        for dpi in (96, 120, 144, 192):
            owner.assert_window(hwnd)
            win32gui.PostMessage(hwnd, 0x8001, dpi, 0)
            wait_for(
                lambda: read_state(directory / "source-state.json").get("simulated_dpi") == dpi
            )
            item = capture_state(owner, hwnd, directory, f"simulated-dpi-{dpi}")
            item.update(simulated_dpi=dpi, layout=layout_bounds(hwnd))
            row["simulated_dpi_layout"].append(item)
        # Failed Quit lets Enter and Space be checked without replacing production callbacks.
        owned_key(owner, hwnd, quit_handle, 13)
        wait_for(lambda: read_state(directory / "source-state.json").get("quit_calls") == 1)
        row["quit_retry"] = capture_state(owner, hwnd, directory, "quit-retry", "Try Quit again")
        owned_key(owner, hwnd, quit_handle, 32)
        row["stopping"] = capture_state(owner, hwnd, directory, "stopping", "Stopping the local")
        owner.assert_window(hwnd)
        win32gui.PostMessage(hwnd, 0x8003, 0, 0)
        assert owner.process.wait(timeout=10) == 0
        row["callback_evidence"] = read_state(directory / "source-state.json")
        assert row["callback_evidence"]["open_calls"] == 2
        assert row["callback_evidence"]["quit_calls"] == 2
    finally:
        row["cleanup"] = owner.close()
        write(directory / "result.json", row)
    return row


def read_state(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def console_child(executable, output):
    """Run a package from an owned console, without changing console/profile settings."""
    from ctypes import wintypes as w

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetConsoleWindow.restype = w.HWND
    hwnd = kernel.GetConsoleWindow()
    members = (w.DWORD * 64)()
    kernel.GetConsoleProcessList.argtypes = [ctypes.POINTER(w.DWORD), w.DWORD]
    count = kernel.GetConsoleProcessList(members, 64)
    write(output / "console.json", {"hwnd": hwnd, "pids": list(members[:count])})
    return subprocess.call(
        [str(executable), "--no-browser", "--state-file", str(output / "state.json")]
    )


def qualify_package(executable, output, build_root, label, console=False):
    directory = output / label
    directory.mkdir()
    settings = directory / "settings"
    settings.mkdir()
    env = {
        **os.environ,
        "LOCALAPPDATA": str(settings),
        "XDG_DATA_HOME": str(settings),
        "TEMP": str(settings),
        "TMP": str(settings),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    command = [str(executable), "--no-browser", "--state-file", str(directory / "state.json")]
    if console:
        command = [
            sys.executable,
            "-B",
            str(Path(__file__).resolve()),
            "--console-child",
            "--executable",
            str(executable),
            "--output",
            str(directory),
        ]
    tick = time.monotonic()
    owner = OwnedProcess(
        command, directory, cwd=build_root, env=env, creationflags=0x10 if console else 0
    )
    row = {
        "executable": str(executable),
        "sha256": hashlib.sha256(executable.read_bytes()).hexdigest(),
        "browser": "suppressed with --no-browser; no default browser changes",
    }
    try:
        hwnd = owner.window()
        wait_for(lambda: read_state(directory / "state.json").get("pid"))
        row["ready_seconds"] = round(time.monotonic() - tick, 3)
        row["ready_memory"] = owner.samples[-1] if owner.samples else {}
        if label == "baseline":
            # Older Tk packages are measured as observed; native-control
            # requirements apply to the candidate, not retroactively to Tk.
            row["ready"] = capture_state(owner, hwnd, directory, "baseline-ready")
            import win32gui

            owner.assert_window(hwnd)
            win32gui.PostMessage(hwnd, 0x10, 0, 0)
            assert owner.process.wait(timeout=20) == 0
            row["gui_quit"] = "owned WM_CLOSE exited successfully"
            return row
        open_button, quit_button = buttons(hwnd)
        wait_for(lambda: open_button.is_enabled())
        row["ready_seconds"] = round(time.monotonic() - tick, 3)
        temporary = settings / TITLE / "tmp"
        (temporary / "synthetic-cleanup.txt").write_text("qualification only", encoding="utf-8")
        row["ready"] = capture_state(owner, hwnd, directory, "packaged-ready", "Ready to open")
        row["layout"] = layout_bounds(hwnd)
        assert owned_key(owner, hwnd, open_button.handle, 9) == quit_button.handle
        assert owned_key(owner, hwnd, quit_button.handle, 9, shift=True) == open_button.handle
        row["tab_shift_tab"] = "passed with real focus"
        if console:
            # The console handle is returned by our owned wrapper, never enumerated globally.
            console_info = read_state(directory / "console.json")
            console_hwnd = console_info.get("hwnd")
            if not console_info.get("pids") or not all(
                pid in owner.known for pid in console_info["pids"]
            ):
                raise RuntimeError("Refusing capture of a console with unowned attached processes")
            if console_hwnd:
                row["console"] = snapshot(console_hwnd, "owned-console", directory)
                row["console_125_percent"] = (
                    "verified at actual 120 DPI"
                    if row["console"]["actual_window_dpi"] == 120
                    else "unverified: owned console is not at 120 DPI; no global settings changed"
                )
            else:
                row["console_125_percent"] = "unverified: no capturable console HWND"
        owned_key(owner, hwnd, quit_button.handle, 13)
        assert owner.process.wait(timeout=20) == 0
        wait_for(lambda: not (directory / "state.json").exists())
        temporary = settings / TITLE / "tmp"
        row["gui_quit"] = "Enter on focused Quit exited successfully"
        row["state_file_removed"] = True
        row["temporary_directory_empty"] = temporary.is_dir() and not any(temporary.iterdir())
        assert row["temporary_directory_empty"]
        _, remaining = owner.psutil.wait_procs(list(owner.known.values()), timeout=5)
        row["natural_exit_remaining_pids"] = [proc.pid for proc in remaining]
        assert not row["natural_exit_remaining_pids"]
    finally:
        row["memory_samples"] = owner.samples
        row["peak_sampled_tree_rss_bytes"] = max(
            (sample["tree_rss_bytes"] for sample in owner.samples), default=0
        )
        row["cleanup"] = owner.close()
        write(directory / "result.json", row)
    return row


def positive_control(output, build_root):
    directory = output / "character-map"
    directory.mkdir()
    owner = OwnedProcess(
        [str(Path(os.environ["WINDIR"]) / "System32/charmap.exe")], directory, cwd=build_root
    )
    row = {}
    try:
        hwnd = owner.window("Character Map")
        row = capture_state(owner, hwnd, directory, "positive-control")
        for view in ("control", "raw", "msaa"):
            assert row["accessibility"][view], f"Character Map {view} positive control failed"
        owner.assert_window(hwnd)
        import win32gui

        win32gui.PostMessage(hwnd, 0x10, 0, 0)
        assert owner.process.wait(timeout=8) == 0
    finally:
        row["cleanup"] = owner.close()
        write(directory / "result.json", row)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--baseline-executable", type=Path)
    parser.add_argument("--build-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--source-only",
        action="store_true",
        help="Qualify source only; packaged checks explicitly remain unverified",
    )
    parser.add_argument("--source-child", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--accessibility-child", type=int, help=argparse.SUPPRESS)
    parser.add_argument(
        "--accessibility-view", choices=("control", "raw", "msaa"), help=argparse.SUPPRESS
    )
    parser.add_argument("--console-child", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if sys.platform != "win32":
        parser.error("Native Windows qualification is unverified on this platform")
    args.output = args.output.resolve()
    args.build_root = args.build_root.resolve()
    # Geometry/capture must use the same physical coordinate space as the dialog.
    user = ctypes.WinDLL("user32")
    user.SetThreadDpiAwarenessContext.argtypes = [ctypes.c_void_p]
    user.SetThreadDpiAwarenessContext.restype = ctypes.c_void_p
    user.SetThreadDpiAwarenessContext(ctypes.c_void_p(-4))
    if args.accessibility_child:
        # UIAutomation requires MTA. Match pywinauto's normal initialization
        # order even though we configure the local comtypes cache first.
        sys.coinit_flags = 0
        import comtypes.client

        cache = args.output.parent / "comtypes-cache"
        cache.mkdir(exist_ok=True)
        comtypes.client.gen_dir = str(cache)
        write(args.output, _accessibility(args.accessibility_child, args.accessibility_view))
        return 0
    if args.source_child:
        source_child(args.output)
        return 0
    if args.console_child:
        return console_child(args.executable, args.output)
    if not args.source_only and not args.executable:
        parser.error("--executable is required unless --source-only is selected")
    if args.output.exists() and any(args.output.iterdir()):
        parser.error("--output must be a new or empty directory to preserve prior evidence")
    args.output.mkdir(parents=True, exist_ok=True)
    results = {
        "scope": "owned processes/windows only; no builds or browser launches",
        "physical_monitor_dpi_transitions": "unverified; source layout checks use simulated DPI",
    }
    failed = False
    operations = [
        ("positive_control", lambda: positive_control(args.output, args.build_root)),
        ("source", lambda: qualify_source(args.output, args.build_root)),
    ]
    if args.executable:
        executable = args.executable.resolve(strict=True)
        operations.extend(
            [
                (
                    "packaged",
                    lambda: qualify_package(executable, args.output, args.build_root, "packaged"),
                ),
                (
                    "console",
                    lambda: qualify_package(
                        executable, args.output, args.build_root, "console", console=True
                    ),
                ),
            ]
        )
    else:
        results["packaged"] = "unverified: source-only mode; no packaged executable supplied"
    if args.baseline_executable:
        baseline = args.baseline_executable.resolve(strict=True)
        operations.append(
            (
                "baseline",
                lambda: qualify_package(baseline, args.output, args.build_root, "baseline"),
            )
        )
    for name, operation in operations:
        try:
            results[name] = operation()
            if contains_unverified(results[name]):
                failed = True
            if name == "console" and results[name]["console_125_percent"].startswith("unverified"):
                failed = True
        except Exception as exc:
            results[name] = {"failed_or_unverified": f"{type(exc).__name__}: {exc}"}
            failed = True
        write(args.output / "qualification.json", results)
    print(str(args.output / "qualification.json"))
    return 1 if failed else 0


def contains_unverified(value):
    if isinstance(value, dict):
        return any(
            (key in ("failed_or_unverified", "unverified") and bool(item))
            or contains_unverified(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(contains_unverified(item) for item in value)
    return False


if __name__ == "__main__":
    raise SystemExit(main())
