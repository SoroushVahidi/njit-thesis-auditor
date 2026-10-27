"""Browser desktop launcher for the local-only auditor."""

from __future__ import annotations

import argparse
import importlib
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

from njit_auditor.offline_app import (
    create_offline_app,
    is_link_or_junction,
    local_data_root,
    prepare_local_storage,
    remove_local_storage_child,
)


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
        config = uvicorn.Config(
            create_offline_app(
                port=port,
                data_root=root_dir,
                launch_ticket=ticket,
                on_quit=lambda: setattr(server, "should_exit", True),
            ),
            host="127.0.0.1",
            port=port,
            access_log=False,
            log_level="warning",
            server_header=False,
            proxy_headers=False,
        )
        server = uvicorn.Server(config)
        thread = threading.Thread(target=lambda: server.run(sockets=[listener]), daemon=False)
        thread.start()
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
                    window = tk.Tk()
                    window.title("NJIT Thesis Auditor")
                    window.geometry("360x160")
                    tk.Label(window, text="NJIT Thesis Auditor", font=("Arial", 16)).pack(pady=16)
                    tk.Button(
                        window, text="Open auditor", command=lambda: webbrowser.open(url)
                    ).pack()
                    tk.Button(
                        window, text="Quit", command=lambda: setattr(server, "should_exit", True)
                    ).pack(pady=12)
                    window.protocol(
                        "WM_DELETE_WINDOW", lambda: setattr(server, "should_exit", True)
                    )

                    def update_window() -> None:
                        if thread.is_alive() and not server.should_exit:
                            window.after(250, update_window)
                        else:
                            window.destroy()

                    window.after(250, update_window)
            url = f"http://127.0.0.1:{port}/_session/start?ticket={urllib.parse.quote(ticket)}"
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
            server.should_exit = True
            thread.join(timeout=30)
            listener.close()
            temp_dir = root_dir / "tmp"
            if not is_link_or_junction(temp_dir):
                for child in temp_dir.iterdir():
                    remove_local_storage_child(child)
            tempfile.tempdir = previous_tempdir


def main() -> None:
    parser = argparse.ArgumentParser(description="Start the offline NJIT Thesis Auditor")
    parser.add_argument("--headless", action="store_true", help="Development smoke testing only")
    parser.add_argument("--no-browser", action="store_true", help="Development smoke testing only")
    args = parser.parse_args()
    run_desktop(headless=args.headless, open_browser=not args.no_browser)


if __name__ == "__main__":
    main()
