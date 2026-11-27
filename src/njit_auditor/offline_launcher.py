"""Browser desktop launcher for the local-only auditor."""

from __future__ import annotations

import sys

if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "--desktop-worker":
    from njit_auditor.desktop_worker import main as worker_main

    raise SystemExit(worker_main(sys.argv[2:]))

import argparse
import importlib
import json
import os
import secrets
import socket
import tempfile
import threading
import urllib.parse
import webbrowser
from pathlib import Path
from typing import BinaryIO

import uvicorn

from njit_auditor.desktop_metadata import DESKTOP_VERSION, desktop_build_info
from njit_auditor.offline_app import (
    create_offline_app,
    is_link_or_junction,
    local_data_root,
    prepare_local_storage,
    remove_local_storage_child,
)
from njit_auditor.resource_paths import resource_path


def _single_instance_lock(root: Path) -> BinaryIO:
    if is_link_or_junction(root):
        raise RuntimeError("The local application data directory must not be a link")
    lock_path = root / "desktop.lock"
    if is_link_or_junction(lock_path):
        raise RuntimeError("The local application lock file must not be a link")
    lock_file = lock_path.open("a+b")
    if lock_file.tell() == 0:
        lock_file.write(b"0")
        lock_file.flush()
    lock_file.seek(0)
    try:
        if sys.platform == "win32":
            msvcrt = importlib.import_module("msvcrt")
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as exc:
        lock_file.close()
        raise RuntimeError("NJIT Thesis Auditor is already running") from exc
    return lock_file


def run_desktop(
    *, headless: bool = False, open_browser: bool = True, state_file: Path | None = None
) -> None:
    from njit_auditor.desktop_network import restrict_network

    # Windows asyncio creates its internal wakeup socket pair over loopback TCP.
    # Permit literal loopback only; remote addresses and DNS remain prohibited.
    restrict_network(allow_loopback=True)
    root_dir = local_data_root()
    root_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    with _single_instance_lock(root_dir):
        prepare_local_storage(root_dir)
        previous_tempdir = tempfile.tempdir
        tempfile.tempdir = str(root_dir / "tmp")
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(("127.0.0.1", 0))
        listener.listen(128)
        port = listener.getsockname()[1]
        ticket = secrets.token_urlsafe(32)
        application = create_offline_app(
            port=port,
            data_root=root_dir,
            launch_ticket=ticket,
            on_quit=lambda: setattr(server, "should_exit", True),
        )
        config = uvicorn.Config(
            application,
            host="127.0.0.1",
            port=port,
            access_log=False,
            # PyInstaller windowed builds set sys.stdout/stderr to None. Uvicorn's
            # default formatter calls stdout.isatty(), preventing startup there.
            log_config=None,
            log_level="warning",
            server_header=False,
            proxy_headers=False,
            timeout_graceful_shutdown=5,
        )
        server = uvicorn.Server(config)
        thread = threading.Thread(target=lambda: server.run(sockets=[listener]), daemon=False)
        thread.start()
        url = f"http://127.0.0.1:{port}/_session/start?ticket={urllib.parse.quote(ticket)}"
        state_written = False
        try:
            window = None
            if not headless:
                try:
                    import tkinter as tk
                except ImportError:
                    # Browser mode is usable on Linux builds without Tcl/Tk;
                    # the interface itself has a visible Quit action.
                    pass
                else:
                    _request_system_dpi_awareness()
                    try:
                        window = tk.Tk()
                    except tk.TclError:
                        window = None
                    if window is not None:
                        open_from_launcher = _configure_window(
                            window,
                            server,
                            thread,
                            lambda: webbrowser.open(url),
                            application.state.request_quit,
                        )
                        window.update_idletasks()
            for _ in range(100):
                if server.started or not thread.is_alive():
                    break
                thread.join(0.05)
            if not server.started:
                if window is not None:
                    from tkinter import messagebox

                    messagebox.showerror(
                        "NJIT Thesis Auditor", "The local auditor could not start.", parent=window
                    )
                    window.destroy()
                raise RuntimeError("The local auditor server did not start")
            if state_file is not None:
                # Explicit test harness opt-in, never enabled for student launches.
                with state_file.open("x", encoding="utf-8") as state:
                    os.chmod(state_file, 0o600)
                    json.dump({"url": url, "pid": os.getpid()}, state)
                state_written = True
            if open_browser:
                if window is not None:
                    open_from_launcher()
                elif not webbrowser.open(url):
                    raise RuntimeError("No default browser could be opened")
            if headless or window is None:
                thread.join()
            else:
                window.mainloop()
        finally:
            if state_written and state_file is not None:
                state_file.unlink(missing_ok=True)
            application.state.request_quit()
            thread.join(timeout=10)
            if thread.is_alive():
                server.force_exit = True
                thread.join(timeout=2)
            if thread.is_alive():
                raise RuntimeError("The local auditor did not stop")
            listener.close()
            temp_dir = root_dir / "tmp"
            if not is_link_or_junction(temp_dir):
                for child in temp_dir.iterdir():
                    remove_local_storage_child(child)
            tempfile.tempdir = previous_tempdir


def _request_system_dpi_awareness() -> None:
    if sys.platform == "win32":
        import ctypes

        # An existing executable manifest can already fix the process mode.
        ctypes.windll.user32.SetProcessDPIAware()


def _configure_window(window, server, thread, open_auditor, request_quit):
    import tkinter as tk
    from tkinter import ttk

    window.title("NJIT Thesis Auditor")
    if os.name == "nt":
        window.iconbitmap(default=str(resource_path("assets", "icons", "njit-auditor.ico")))
    frame = ttk.Frame(window, padding=("15p", "12p"))
    frame.pack(fill="both", expand=True)
    ttk.Label(frame, text="NJIT Thesis Auditor", font="TkHeadingFont").pack(anchor="w")
    ttk.Label(frame, text="Check thesis formatting in your browser.").pack(anchor="w", pady="4p")
    status = tk.StringVar(master=window, value="Starting the local auditor…")
    ttk.Label(frame, textvariable=status, wraplength="275p").pack(anchor="w", pady="8p")
    buttons = ttk.Frame(frame)
    buttons.pack(fill="x", pady=("0p", "9p"))

    def open_browser_window() -> None:
        if not server.started or server.should_exit:
            return
        try:
            opened = open_auditor()
        except (OSError, webbrowser.Error):
            opened = False
        status.set(
            "Auditor ready in your browser." if opened
            else "Could not open your browser. Check your default browser and try again."
        )

    def close_window() -> None:
        status.set("Stopping the local auditor…")
        window.update_idletasks()
        if not request_quit():
            status.set("Could not stop the audit yet. Try Quit again.")

    open_button = ttk.Button(buttons, text="Open auditor", command=open_browser_window)
    open_button.state(["disabled"])
    open_button.pack(side="left", padx=("0p", "6p"))
    ttk.Button(buttons, text="Quit", command=close_window).pack(side="left")
    build = desktop_build_info().get("build_version", DESKTOP_VERSION)
    ttk.Label(frame, text=f"Version {build} · Runs on this computer").pack(anchor="w")
    window.protocol("WM_DELETE_WINDOW", close_window)

    def update_window() -> None:
        if thread.is_alive() and not server.should_exit:
            if server.started and open_button.instate(["disabled"]):
                open_button.state(["!disabled"])
                open_button.focus_set()
                if status.get() == "Starting the local auditor…":
                    status.set("Ready to open in your browser.")
            window.after(250, update_window)
        else:
            window.destroy()

    window.after(250, update_window)
    window.update_idletasks()
    # Reserve room for the OS caption and controls at the effective Tk scale.
    caption_width = round(window.winfo_fpixels("300p"))
    screen_width_cap = max(1, int(window.winfo_screenwidth() * 0.9))
    window.minsize(
        max(window.winfo_reqwidth(), min(caption_width, screen_width_cap)),
        window.winfo_reqheight(),
    )
    return open_browser_window


def main() -> None:
    parser = argparse.ArgumentParser(description="Start the offline NJIT Thesis Auditor")
    parser.add_argument("--headless", action="store_true", help="Development smoke testing only")
    parser.add_argument("--no-browser", action="store_true", help="Development smoke testing only")
    parser.add_argument("--state-file", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        run_desktop(
            headless=args.headless, open_browser=not args.no_browser, state_file=args.state_file
        )
    except Exception:
        if args.headless:
            raise
        # A windowed executable has no console; never show paths/exception text.
        message = (
            "Could not open the local auditor. Close any other copy, check that "
            "your local application data folder is writable, and try again."
        )
        if os.name == "nt":
            ctypes = importlib.import_module("ctypes")
            ctypes.windll.user32.MessageBoxW(None, message, "NJIT Thesis Auditor", 0x10)
        else:
            print(message, file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
