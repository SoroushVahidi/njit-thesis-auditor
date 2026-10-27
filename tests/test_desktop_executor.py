"""Deterministic desktop lifecycle cases using real, short-lived owned processes."""

from __future__ import annotations

import json
import os
import sys
import threading
from pathlib import Path
from typing import Any

import pytest
from test_offline_desktop import _pdf

from njit_auditor import desktop_executor, web_app
from njit_auditor.desktop_executor import (
    CANCEL_MESSAGE,
    FAILURE_MESSAGE,
    TIMEOUT_MESSAGE,
    DesktopExecutor,
    worker_command,
)
from njit_auditor.desktop_process import ProcessTree
from njit_auditor.desktop_protocol import decode, encode
from njit_auditor.offline_app import prepare_local_storage
from njit_auditor.pdf_highlight import HighlightBox, PageBoxSpace


@pytest.fixture()
def runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    audits = prepare_local_storage(tmp_path)
    monkeypatch.setattr(web_app, "RUNTIME_DIR", audits)
    monkeypatch.setattr(web_app, "_jobs", {})
    monkeypatch.setattr(web_app, "_after_audit_task", None)
    return audits


def job(runtime: Path, name: str) -> web_app.JobState:
    directory = runtime / name
    directory.mkdir()
    (directory / "upload.pdf").write_bytes(_pdf("normal"))
    value = web_app.JobState(
        job_id=name,
        state="pending",
        created_at="2026-10-26T00:00:00Z",
        file_name="synthetic.pdf",
    )
    web_app._set_job(value)
    return value


def hang(_request: Path) -> list[str]:
    return [sys.executable, "-c", "import time; time.sleep(60)"]


def track(monkeypatch: pytest.MonkeyPatch) -> tuple[list[Any], threading.Event]:
    processes = []
    started = threading.Event()

    def capture(process):
        value = ProcessTree(process)
        processes.append(process)
        started.set()
        return value

    monkeypatch.setattr(desktop_executor, "ProcessTree", capture)
    return processes, started


def test_normal_worker_retains_reports_and_geometry(runtime: Path) -> None:
    job(runtime, "normal")
    manager = DesktopExecutor(deadline=10)
    manager.run("normal")
    finished = web_app._get_job("normal")
    assert finished.state == "complete"
    assert finished.finding_count > 0
    assert isinstance(finished.pdf_page_sizes[0], PageBoxSpace)
    for name in ("report.json", "report.md", "report.txt"):
        assert (runtime / "normal" / name).is_file()
    assert not list((runtime / "normal").glob(".desktop-*"))
    assert not manager._trees and not manager._cancel
    assert not manager.cancel("normal")
    manager.close()


def test_timeout_kills_worker_cleans_input_and_allows_next_audit(runtime, monkeypatch) -> None:
    processes, _ = track(monkeypatch)
    job(runtime, "timeout")
    manager = DesktopExecutor(deadline=0.2, command=hang)
    manager.run("timeout")
    assert web_app._get_job("timeout").error_message == TIMEOUT_MESSAGE
    assert not (runtime / "timeout").exists()
    assert processes and all(p.poll() is not None for p in processes)
    manager.deadline = 10
    manager._command = worker_command
    job(runtime, "recovery")
    manager.run("recovery")
    assert web_app._get_job("recovery").state == "complete"
    manager.close()


def test_cancel_kills_worker_cleans_input_and_keeps_executor_usable(runtime, monkeypatch) -> None:
    processes, started = track(monkeypatch)
    job(runtime, "cancel")
    manager = DesktopExecutor(deadline=10, command=hang)
    thread = threading.Thread(target=manager.run, args=("cancel",))
    thread.start()
    assert started.wait(5)
    assert manager.cancel("cancel")
    thread.join(3)
    assert not thread.is_alive()
    assert web_app._get_job("cancel").error_message == CANCEL_MESSAGE
    assert not (runtime / "cancel").exists()
    assert all(p.poll() is not None for p in processes)
    manager.close()


def test_cancel_before_start_never_launches_a_worker(runtime, monkeypatch) -> None:
    processes, _ = track(monkeypatch)
    job(runtime, "queued")
    manager = DesktopExecutor(command=hang)
    assert manager.cancel("queued")
    manager.run("queued")
    assert not processes and not (runtime / "queued").exists()
    assert web_app._get_job("queued").error_message == CANCEL_MESSAGE
    manager.close()


def test_quit_stops_running_and_queued_work_without_orphans(runtime, monkeypatch) -> None:
    processes, started = track(monkeypatch)
    manager = DesktopExecutor(command=hang)
    threads = []
    for name in ("first", "second", "queued"):
        job(runtime, name)
        thread = threading.Thread(target=manager.run, args=(name,))
        threads.append(thread)
        thread.start()
    assert started.wait(5)
    manager.close()
    for thread in threads:
        thread.join(3)
        assert not thread.is_alive()
    assert processes and all(p.poll() is not None for p in processes)
    assert not any(runtime.iterdir())
    assert not manager._trees
    manager.close()  # idempotent
    job(runtime, "after-close")
    manager.run("after-close")
    assert web_app._get_job("after-close").error_message == CANCEL_MESSAGE
    assert not (runtime / "after-close").exists()


def test_queued_wait_also_has_a_deadline(runtime) -> None:
    manager = DesktopExecutor(deadline=0.1)
    for _ in range(desktop_executor.MAX_ACTIVE_AUDITS):
        manager._slots.acquire()
    job(runtime, "queued-timeout")
    manager.run("queued-timeout")
    assert web_app._get_job("queued-timeout").error_message == TIMEOUT_MESSAGE
    assert not (runtime / "queued-timeout").exists()
    for _ in range(desktop_executor.MAX_ACTIVE_AUDITS):
        manager._slots.release()
    manager.close()


def test_worker_crash_has_safe_message_and_no_output(runtime, caplog, capfd) -> None:
    def crash(_request):
        return [sys.executable, "-c", "import sys; print('synthetic-private-marker'); sys.exit(3)"]

    manager = DesktopExecutor(command=crash)
    job(runtime, "crash")
    manager.run("crash")
    assert web_app._get_job("crash").error_message == FAILURE_MESSAGE
    assert not (runtime / "crash").exists()
    output = capfd.readouterr()
    assert "synthetic-private-marker" not in output.out + output.err + caplog.text
    manager.close()


def test_containment_failure_never_releases_worker(runtime, monkeypatch) -> None:
    processes = []

    def fail(process):
        processes.append(process)
        raise OSError("synthetic containment failure")

    monkeypatch.setattr(desktop_executor, "ProcessTree", fail)
    manager = DesktopExecutor(command=hang)
    job(runtime, "uncontained")
    manager.run("uncontained")
    assert processes and all(p.poll() is not None for p in processes)
    assert not (runtime / "uncontained").exists()
    assert web_app._get_job("uncontained").error_message == FAILURE_MESSAGE
    manager.close()


def test_transport_preserves_rotation_styles_tuples_and_integer_keys() -> None:
    value = {
        1: {
            "space": PageBoxSpace(600, 800, 270),
            "box": HighlightBox(1, 2, 3, 4, kind="guide"),
            "questions": [("Review this?", "Yes")],
        }
    }
    restored = decode(json.loads(json.dumps(encode(value))))
    assert restored == value
    assert restored[1]["space"].rotation == 270
    assert restored[1]["box"].kind == "guide"
    assert isinstance(restored[1]["questions"][0], tuple)


def test_frozen_worker_reexecutes_app_without_python(monkeypatch) -> None:
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", "NJIT Thesis Auditor.exe")
    assert worker_command(Path("request.json")) == [
        "NJIT Thesis Auditor.exe",
        "--desktop-worker",
        "request.json",
    ]


def test_descendant_is_stopped_with_worker_group(runtime, tmp_path) -> None:
    pid_file = tmp_path / "descendant.pid"

    def spawn(_request):
        code = (
            "import subprocess,sys,time,pathlib; "
            "p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)']); "
            f"pathlib.Path({str(pid_file)!r}).write_text(str(p.pid)); time.sleep(60)"
        )
        return [sys.executable, "-c", code]

    manager = DesktopExecutor(deadline=0.5, command=spawn)
    job(runtime, "tree")
    manager.run("tree")
    assert pid_file.is_file()
    pid = int(pid_file.read_text())
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        kernel = getattr(ctypes, "WinDLL")("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        kernel.GetExitCodeProcess.restype = wintypes.BOOL
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel.OpenProcess(0x1000, False, pid)  # QUERY_LIMITED_INFORMATION
        if handle:
            code = wintypes.DWORD()
            try:
                assert kernel.GetExitCodeProcess(handle, ctypes.byref(code))
                assert code.value != 259  # STILL_ACTIVE
            finally:
                kernel.CloseHandle(handle)
    else:
        # The Linux subreaper collects descendants instead of leaving zombie orphans.
        assert not Path(f"/proc/{pid}").exists()
    assert not (runtime / "tree").exists()
    manager.close()


def test_cleanup_failure_is_visible_and_can_be_retried(runtime, monkeypatch) -> None:
    job(runtime, "locked")
    manager = DesktopExecutor(deadline=0.05, command=hang)
    with monkeypatch.context() as patch:
        patch.setattr(web_app, "_delete_job_workspace", lambda _job_id: False)
        manager.run("locked")
    assert manager.cleanup_failed.is_set()
    assert "Some local files could not be deleted" in web_app._get_job("locked").error_message
    assert web_app._delete_job_workspace("locked")
    manager.close()


def test_deadline_begins_at_acceptance_before_supervisor_is_queued(runtime, monkeypatch) -> None:
    clock = [100.0]
    monkeypatch.setattr(desktop_executor.time, "monotonic", lambda: clock[0])
    manager = DesktopExecutor(deadline=1, command=hang)
    job(runtime, "delayed")
    manager.register("delayed")
    clock[0] = 102.0
    manager.run("delayed")
    assert web_app._get_job("delayed").error_message == TIMEOUT_MESSAGE
    assert not (runtime / "delayed").exists() and not manager._trees
    manager.close()


def test_termination_failure_keeps_ownership_and_does_not_log_private_errors(
    runtime, monkeypatch, caplog
):
    trees = []

    class UnavailableTermination:
        fail = True

        def __init__(self, process):
            self.real = ProcessTree(process)
            trees.append(self)

        def stop(self):
            if self.fail:
                raise OSError("synthetic-private-stop-path")
            self.real.stop()

    monkeypatch.setattr(desktop_executor, "ProcessTree", UnavailableTermination)
    job(runtime, "retained")
    manager = DesktopExecutor(deadline=0.1, command=hang)
    manager.run("retained")
    assert manager._trees and (runtime / "retained/upload.pdf").is_file()
    assert web_app._get_job("retained").state == "running"
    assert not manager.close()
    assert manager.cleanup_failed.is_set()
    assert "Try Quit again" in web_app._get_job("retained").error_message
    assert "synthetic-private-stop-path" not in caplog.text
    trees[0].fail = False
    assert manager.close()
    assert trees[0].real.process.poll() is not None
    assert web_app._delete_job_workspace("retained")


def test_quit_does_not_report_success_when_termination_is_unconfirmed(runtime, monkeypatch) -> None:
    from fastapi.testclient import TestClient

    from njit_auditor.offline_app import create_offline_app

    manager = DesktopExecutor()
    quit_called = threading.Event()
    app = create_offline_app(
        port=17391,
        data_root=runtime.parent,
        launch_ticket="ticket",
        on_quit=quit_called.set,
        executor=manager,
    )
    with TestClient(app, base_url="http://127.0.0.1:17391") as client:
        client.get("/_session/start?ticket=ticket")
        with monkeypatch.context() as patch:
            patch.setattr(manager, "close", lambda: False)
            response = client.post(
                "/quit",
                data={"csrf_token": app.state.csrf_token},
                headers={"Origin": "http://127.0.0.1:17391"},
            )
            assert response.status_code == 503
            assert "Try Quit again" in response.text and "Auditor closed" not in response.text
            assert not quit_called.is_set()


@pytest.mark.parametrize("failure", [None, "terminate", "query", "active", "close"])
def test_windows_job_requires_confirmed_empty_tree_before_release(monkeypatch, failure):
    """API contract simulation only; native Windows Job Objects still require testing."""
    from njit_auditor import desktop_process

    calls = []
    times = iter([100.0, 103.0])
    monkeypatch.setattr(desktop_process.time, "monotonic", lambda: next(times))

    class Kernel:
        def TerminateJobObject(self, handle, code):
            calls.append("terminate")
            return failure != "terminate"

        def QueryInformationJobObject(self, handle, kind, pointer, size, returned):
            calls.append("query")
            pointer._obj.ActiveProcesses = 1 if failure == "active" else 0
            return failure != "query"

        def CloseHandle(self, handle):
            calls.append("close")
            return failure != "close"

    tree = ProcessTree.__new__(ProcessTree)
    tree._job = 123
    tree._kernel = Kernel()
    if failure:
        with pytest.raises(OSError):
            tree._stop_windows_job()
        assert tree._job == 123
        if failure != "close":
            assert "close" not in calls
    else:
        tree._stop_windows_job()
        assert tree._job is None and calls == ["terminate", "query", "close"]
