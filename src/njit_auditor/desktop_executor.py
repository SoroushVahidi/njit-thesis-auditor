"""Bounded desktop audit supervision; the hosted web executor is unchanged."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from njit_auditor import web_app
from njit_auditor.desktop_process import ProcessTree
from njit_auditor.desktop_protocol import decode, encode
from njit_auditor.resource_paths import resource_root

AUDIT_DEADLINE_SECONDS = 120.0
MAX_ACTIVE_AUDITS = 2
TIMEOUT_MESSAGE = "This audit took too long and was stopped. Try a smaller PDF or audit it again."
CANCEL_MESSAGE = "This audit was cancelled. You can start another audit."
FAILURE_MESSAGE = "Could not complete this audit. Check the PDF and try again."


def worker_command(request: Path) -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable, "--desktop-worker", str(request)]
    return [sys.executable, "-m", "njit_auditor.desktop_worker", str(request)]


class DesktopExecutor:
    def __init__(
        self,
        *,
        deadline: float = AUDIT_DEADLINE_SECONDS,
        command: Callable[[Path], list[str]] = worker_command,
    ) -> None:
        if deadline <= 0:
            raise ValueError("Audit deadline must be positive")
        self.deadline = deadline
        self.cleanup_failed = threading.Event()
        self._command = command
        self._lock = threading.Lock()
        self._slots = threading.BoundedSemaphore(MAX_ACTIVE_AUDITS)
        self._closing = threading.Event()
        self._cancel: dict[str, threading.Event] = {}
        self._trees: dict[str, ProcessTree] = {}
        self._deadlines: dict[str, float] = {}

    def register(self, job_id: str) -> None:
        # Capture acceptance time before the web framework queues the supervisor.
        with self._lock:
            self._deadlines[job_id] = time.monotonic() + self.deadline
            self._cancel.setdefault(job_id, threading.Event())

    def cancel(self, job_id: str) -> bool:
        with self._lock:
            job = web_app._get_job(job_id)
            if job is None or job.state not in {"pending", "running"}:
                return False
            event = self._cancel.setdefault(job_id, threading.Event())
            event.set()
            tree = self._trees.get(job_id)
        if tree is not None:
            tree.stop()
        return True

    def close(self) -> None:
        self._closing.set()
        with self._lock:
            for event in self._cancel.values():
                event.set()
            trees = list(self._trees.values())
        for tree in trees:
            tree.stop()

    def run(self, job_id: str) -> None:
        job = web_app._get_job(job_id)
        if job is None:
            return
        cancel = threading.Event()
        end = time.monotonic() + self.deadline
        acquired = False
        tree = None
        request = web_app._job_dir(job_id) / ".desktop-request.json"
        result = request.with_name(".desktop-result.json")
        ready = request.with_name(".desktop-ready")
        failure = FAILURE_MESSAGE
        completed = False
        with self._lock:
            cancel = self._cancel.setdefault(job_id, cancel)
            end = self._deadlines.get(job_id, end)
        try:
            while not self._closing.is_set() and not cancel.is_set():
                if time.monotonic() >= end:
                    failure = TIMEOUT_MESSAGE
                    break
                if self._slots.acquire(timeout=0.05):
                    acquired = True
                    break
            if not acquired:
                if cancel.is_set() or self._closing.is_set():
                    failure = CANCEL_MESSAGE
                return
            job.state = "running"
            web_app._set_job(job)
            request.write_text(
                json.dumps(
                    {
                        "runtime_dir": str(web_app.RUNTIME_DIR.resolve()),
                        "job": encode(vars(job)),
                    }
                ),
                encoding="utf-8",
            )
            env = os.environ.copy()
            env["FASTAPI_OTEL_AUTO_CONFIGURE"] = "false"
            if not getattr(sys, "frozen", False):
                env["PYTHONPATH"] = os.pathsep.join(
                    [str(resource_root() / "src"), env.get("PYTHONPATH", "")]
                )
            with self._lock:
                if self._closing.is_set() or cancel.is_set():
                    failure = CANCEL_MESSAGE
                    return
                process = subprocess.Popen(
                    self._command(request),
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=os.name != "nt",
                    creationflags=0x08000000 if os.name == "nt" else 0,  # CREATE_NO_WINDOW
                )
                try:
                    tree = ProcessTree(process)
                except BaseException:
                    process.kill()
                    process.wait(timeout=2)
                    raise
                self._trees[job_id] = tree
                # The worker cannot import/run the audit until tree containment exists.
                ready.touch()
            while process.poll() is None:
                if cancel.is_set() or self._closing.is_set():
                    failure = CANCEL_MESSAGE
                    return
                if time.monotonic() >= end:
                    failure = TIMEOUT_MESSAGE
                    return
                cancel.wait(min(0.05, max(0, end - time.monotonic())))
            if cancel.is_set() or self._closing.is_set():
                failure = CANCEL_MESSAGE
                return
            if time.monotonic() >= end:
                failure = TIMEOUT_MESSAGE
                return
            if process.returncode != 0:
                return
            # Stop any leftover descendants before reading data or deleting files.
            tree.stop()
            payload = decode(json.loads(result.read_text(encoding="utf-8")))
            if payload.get("job_id") != job_id or payload.get("state") not in {
                "complete",
                "failed",
            }:
                return
            with self._lock:
                if cancel.is_set() or self._closing.is_set():
                    failure = CANCEL_MESSAGE
                    return
                web_app._set_job(web_app.JobState(**payload))
                completed = True
        except Exception:
            # Never log worker output, exception text, document paths, or job IDs.
            failure = FAILURE_MESSAGE
        finally:
            if tree is not None:
                tree.stop()
            for path in (request, result, ready):
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    self.cleanup_failed.set()
            with self._lock:
                self._trees.pop(job_id, None)
                self._cancel.pop(job_id, None)
                self._deadlines.pop(job_id, None)
            if acquired:
                self._slots.release()
            if not completed:
                # Keep the short failure state, but remove uploaded and partial documents.
                if not web_app._delete_job_workspace(job_id):
                    self.cleanup_failed.set()
                    failure += (
                        " Some local files could not be deleted. Use Delete all local audit data."
                    )
                job.state = "failed"
                job.error_message = failure
                job.finished_at = datetime.now(timezone.utc).isoformat()
                web_app._set_job(job)
            if web_app._after_audit_task is not None:
                web_app._after_audit_task(job_id)
