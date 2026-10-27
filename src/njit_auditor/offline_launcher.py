"""Browser desktop launcher for the local-only auditor."""

from __future__ import annotations

import sys

if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "--desktop-worker":
    from njit_auditor.desktop_worker import main as worker_main

    raise SystemExit(worker_main(sys.argv[2:]))

import argparse
import importlib
import os
import secrets
import signal
import socket
import subprocess
import tempfile
import threading
import urllib.parse
import webbrowser
from pathlib import Path
from typing import BinaryIO

import uvicorn

from njit_auditor.desktop_metadata import DESKTOP_VERSION
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
        if os.name == "nt":
            msvcrt = importlib.import_module("msvcrt")
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as exc:
        lock_file.close()
        raise RuntimeError("NJIT Thesis Auditor is already running") from exc
    return lock_file


def run_desktop(*, headless: bool = False, open_browser: bool = True) -> None:
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
            log_level="warning",
            server_header=False,
            proxy_headers=False,
            timeout_graceful_shutdown=5,
        )
        server = uvicorn.Server(config)
        thread = threading.Thread(target=lambda: server.run(sockets=[listener]), daemon=False)
        thread.start()
        url = f"http://127.0.0.1:{port}/_session/start?ticket={urllib.parse.quote(ticket)}"
        previous_sigterm = None
        try:
            if sys.platform == "darwin" and threading.current_thread() is threading.main_thread():
                previous_sigterm = signal.signal(
                    signal.SIGTERM, lambda *_: application.state.request_quit()
                )
            window = None
            if not headless:
                try:
                    import tkinter as tk
                except ImportError:
                    # Browser mode is usable on Linux builds without Tcl/Tk;
                    # the interface itself has a visible Quit action.
                    pass
                else:
                    try:
                        window = tk.Tk()
                    except tk.TclError:
                        window = None
                    if window is not None:
                        _configure_window(
                            window,
                            server,
                            thread,
                            lambda: webbrowser.open(url),
                            application.state.request_quit,
                        )
                if sys.platform == "darwin" and window is None:
                    raise RuntimeError("The macOS application requires bundled Tcl/Tk")
            for _ in range(100):
                if server.started or not thread.is_alive():
                    break
                thread.join(0.05)
            if not server.started:
                raise RuntimeError("The local auditor server did not start")
            if open_browser and not webbrowser.open(url):
                raise RuntimeError("No default browser could be opened")
            if headless or window is None:
                thread.join()
            else:
                window.mainloop()
        finally:
            if previous_sigterm is not None:
                signal.signal(signal.SIGTERM, previous_sigterm)
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


def _configure_window(window, server, thread, open_auditor, request_quit) -> None:
    import tkinter as tk

    window.title("NJIT Thesis Auditor")
    window.geometry("400x220")
    if os.name == "nt":
        window.iconbitmap(default=str(resource_path("assets", "icons", "njit-auditor.ico")))
    tk.Label(window, text="NJIT Thesis Auditor", font=("Arial", 16)).pack(pady=12)
    tk.Label(window, text=f"Version {DESKTOP_VERSION} · Runs on this computer").pack()
    tk.Button(window, text="Open auditor", command=open_auditor).pack(pady=8)

    def close_window() -> None:
        if not request_quit():
            from tkinter import messagebox

            messagebox.showwarning(
                "NJIT Thesis Auditor", "Could not stop the audit yet. Try Quit again."
            )

    tk.Button(window, text="Quit", command=close_window).pack()
    window.protocol("WM_DELETE_WINDOW", close_window)
    if sys.platform == "darwin":
        # Tcl/Tk's default macOS Quit exits the interpreter without our cleanup.
        window.createcommand("tk::mac::Quit", close_window)
        window.createcommand("tk::mac::ReopenApplication", open_auditor)
        window.bind_all("<Command-q>", lambda _event: close_window())

    def update_window() -> None:
        if thread.is_alive() and not server.should_exit:
            window.after(250, update_window)
        else:
            window.destroy()

    window.after(250, update_window)


def main() -> None:
    parser = argparse.ArgumentParser(description="Start the offline NJIT Thesis Auditor")
    parser.add_argument("--headless", action="store_true", help="Development smoke testing only")
    parser.add_argument("--no-browser", action="store_true", help="Development smoke testing only")
    args = parser.parse_args()
    try:
        run_desktop(headless=args.headless, open_browser=not args.no_browser)
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
        elif sys.platform == "darwin":
            subprocess.run(
                ["/usr/bin/osascript", "-e", f'display alert "NJIT Thesis Auditor" '
                 f'message "{message}" as critical'],
                check=False,
                timeout=30,
            )
        else:
            print(message, file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
