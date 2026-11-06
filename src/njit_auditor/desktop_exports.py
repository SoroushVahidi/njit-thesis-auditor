"""Bounded desktop PDF workers and immutable, completed export caches.

Supervisor threads do filesystem/process bookkeeping only. All PyMuPDF work,
including validation, runs beyond the existing contained worker's ready gate.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import os
import shutil
import tempfile
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastapi import Request
from fastapi.responses import FileResponse, HTMLResponse

from njit_auditor import web_app
from njit_auditor.desktop_executor import start_worker, worker_command
from njit_auditor.desktop_process import ProcessTree, prepare_containment
from njit_auditor.desktop_protocol import encode
from njit_auditor.pdf_publication import complete_pdf

EXPORT_DEADLINE_SECONDS = 120.0
MAX_ACTIVE_EXPORTS = 2


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def render_export(directory: Path, job: web_app.JobState, payload: dict[str, Any]) -> None:
    """Worker-only renderer: reuse the hosted rendering and response contracts."""
    handlers = {
        "student": web_app._prepare_student_pdf,
        "highlighted": web_app._prepare_highlighted_pdf,
        "page": web_app._prepare_highlighted_page_pdf,
    }
    request = Request(
        {
            "type": "http",
            "app": web_app.app,
            "method": "GET",
            "path": "/",
            "root_path": "",
            "headers": [],
            "query_string": b"",
            "scheme": "http",
            "server": ("127.0.0.1", 80),
        }
    )
    response = handlers[payload["kind"]](
        request, job.job_id, output_dir=directory, **payload["params"]
    )
    if not isinstance(response, FileResponse):
        raise ValueError("PDF export unavailable")
    path = Path(response.path)
    if not complete_pdf(path):
        raise ValueError("Incomplete PDF export")
    source = web_app._job_pdf_path(web_app._job_dir(job.job_id))
    if path != source and path.parent != directory:
        raise ValueError("Invalid export destination")
    result = {
        "source": path == source,
        "filename": path.name,
        "digest": file_digest(path),
        "headers": dict(response.headers),
    }
    (directory / ".desktop-result.json").write_text(json.dumps(result), encoding="utf-8")


@dataclass
class Operation:
    job_id: str
    end: float
    cancel: threading.Event = field(default_factory=threading.Event)
    done: threading.Event = field(default_factory=threading.Event)
    tree: ProcessTree | None = None
    directory: Path | None = None
    retained: bool = False


class ExportUnavailable(Exception):
    pass


class PdfExportExecutor:
    def __init__(
        self,
        *,
        deadline: float = EXPORT_DEADLINE_SECONDS,
        max_active: int = MAX_ACTIVE_EXPORTS,
        command: Callable[[Path], list[str]] = worker_command,
    ) -> None:
        if not math.isfinite(deadline) or deadline <= 0 or max_active < 1:
            raise ValueError("Positive finite export limits are required")
        prepare_containment()
        self.deadline = deadline
        self._command = command
        self._pool = ThreadPoolExecutor(max_workers=max_active, thread_name_prefix="pdf-export")
        self._lock = threading.RLock()
        self._closing = False
        self._operations: list[Operation] = []
        self.cleanup_failed = threading.Event()

    def _check(self, operation: Operation) -> None:
        if self._closing or operation.cancel.is_set() or time.monotonic() >= operation.end:
            raise ExportUnavailable("PDF export stopped")

    def _acquire(self, lock: Any, operation: Operation) -> None:
        while True:
            self._check(operation)
            if lock.acquire(timeout=0.025):
                return

    def _register(self, job_id: str) -> Operation:
        with self._lock, web_app._jobs_lock:
            job = web_app._jobs.get(job_id)
            if self._closing or job is None or job.state != "complete":
                raise ExportUnavailable("PDF export unavailable")
            operation = Operation(job_id, time.monotonic() + self.deadline)
            self._operations.append(operation)
            web_app._export_leases[job_id] = web_app._export_leases.get(job_id, 0) + 1
            return operation

    def _release(self, operation: Operation) -> None:
        with self._lock, web_app._jobs_lock:
            if operation not in self._operations:
                return
            self._operations.remove(operation)
            count = web_app._export_leases[operation.job_id] - 1
            if count:
                web_app._export_leases[operation.job_id] = count
            else:
                del web_app._export_leases[operation.job_id]
        if web_app._after_audit_task is not None:
            web_app._after_audit_task(operation.job_id)

    def _cleanup(self, operation: Operation) -> bool:
        try:
            if operation.tree is not None:
                operation.tree.stop()
            if operation.directory is not None:
                shutil.rmtree(operation.directory)
                operation.directory = None
        except Exception:
            # Keep ownership and the lease: deletion may never erase live work.
            self.cleanup_failed.set()
            operation.retained = True
            with self._lock:
                self._closing = True
            return False
        self._release(operation)
        return True

    def cancel(self, job_id: str | None = None, *, closing: bool = False) -> bool:
        with self._lock:
            if closing:
                self._closing = True
            operations = [op for op in self._operations if job_id is None or op.job_id == job_id]
            for operation in operations:
                operation.cancel.set()
        # Supervisors stop their own trees concurrently; never block the event loop.
        end = time.monotonic() + 5
        stopped = True
        for operation in operations:
            if not operation.done.wait(max(0, end - time.monotonic())):
                stopped = False
            elif operation.retained and not self._cleanup(operation):
                stopped = False
        return stopped

    def close(self) -> bool:
        stopped = self.cancel(closing=True)
        # Queued supervisors still run their finally blocks to release leases.
        self._pool.shutdown(wait=False)
        return stopped

    def _cached(self, directory: Path, source: Path) -> tuple[Path, dict[str, str]] | None:
        try:
            manifest = json.loads((directory / ".desktop-result.json").read_text("utf-8"))
            path = source if manifest["source"] else directory / manifest["filename"]
            if path != source and path.parent != directory:
                return None
            if file_digest(path) != manifest["digest"]:
                return None
            return path, manifest["headers"]
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def _run(
        self, operation: Operation, kind: str, params: dict[str, Any]
    ) -> tuple[Path, dict[str, str]]:
        locked = False
        job_lock = web_app._student_pdf_lock(operation.job_id)
        try:
            self._acquire(job_lock, operation)
            locked = True
            self._check(operation)
            job = web_app._get_job(operation.job_id)
            if job is None:
                raise ExportUnavailable()
            directory = web_app._job_dir(operation.job_id)
            source = web_app._job_pdf_path(directory)
            payload = {
                "operation": "pdf-export",
                "kind": kind,
                "params": params,
                "runtime_dir": str(web_app.RUNTIME_DIR.resolve()),
                "job": encode(vars(job)),
            }
            # Include raw findings and source identity; never reuse an earlier report
            # after the finding set or uploaded document changes.
            signature = hashlib.sha256(
                json.dumps(
                    [
                        payload,
                        encode(web_app._report_json_findings_for_highlight(job)),
                        source.stat().st_mtime_ns,
                        source.stat().st_size,
                    ],
                    sort_keys=True,
                ).encode()
            ).hexdigest()
            final = directory / (".export-" + signature)
            cached = self._cached(final, source)
            if cached is not None:
                self._check(operation)
                return cached
            # Never overwrite a download already in progress, even when a cache
            # fails its checksum. A new immutable generation gets a fresh pathname.
            if final.exists():
                # Quarantine an invalid generation without replacing any open file.
                os.replace(final, directory / (".invalid-export-" + os.urandom(8).hex()))
            operation.directory = Path(tempfile.mkdtemp(prefix=".export-tmp-", dir=directory))
            request = operation.directory / ".desktop-request.json"
            request.write_text(json.dumps(payload), encoding="utf-8")
            with self._lock:
                self._check(operation)
                process, operation.tree = start_worker(request, self._command)
                request.with_name(".desktop-ready").touch()
            while process.poll() is None:
                self._check(operation)
                operation.cancel.wait(0.025)
            self._check(operation)
            if process.returncode != 0:
                raise ExportUnavailable()
            operation.tree.stop()  # Includes descendants; all PDF handles are closed.
            generated = self._cached(operation.directory, source)
            if generated is None:
                raise ExportUnavailable()
            if generated[0] == source:
                # Best-effort highlight failures return the original PDF. Do not
                # cache that fallback: a later request must be able to retry.
                self._check(operation)
                return generated
            request.unlink()
            request.with_name(".desktop-ready").unlink()
            with self._lock:
                # Cancellation and publication share this boundary. A cancellation
                # accepted before this point cannot publish; after it, the artifact
                # is already complete and immutable.
                self._check(operation)
                os.replace(operation.directory, final)
                operation.directory = None
            cached = self._cached(final, source)
            if cached is None:
                raise ExportUnavailable()
            return cached
        finally:
            self._cleanup(operation)
            if locked:
                job_lock.release()
            operation.done.set()

    async def response(
        self, request: Request, job_id: str, kind: str, params: dict[str, Any]
    ) -> FileResponse | HTMLResponse:
        job = web_app._get_job(job_id)
        if job is None or job.state != "complete":
            return web_app._index_notice(request, web_app._expired_job_notice(), status_code=404)
        if job.audit_type != "pdf":
            return web_app._index_notice(request, "Only available for PDF audits.", status_code=404)
        if kind == "page" and params.get("page") is None:
            return web_app._index_notice(
                request, "This PDF page link is missing a page number.", status_code=400
            )
        operation = None
        try:
            operation = self._register(job_id)
            try:
                task = asyncio.get_running_loop().run_in_executor(
                    self._pool, self._run, operation, kind, params
                )
            except BaseException:
                self._release(operation)
                operation.done.set()
                raise
            try:
                while not task.done():
                    await asyncio.wait({task}, timeout=0.05)
                    if not task.done() and await request.is_disconnected():
                        operation.cancel.set()
                        break
                path, headers = await asyncio.shield(task)
            except asyncio.CancelledError:
                operation.cancel.set()
                # The supervised thread owns cleanup even if the HTTP task is cancelled again.
                try:
                    await asyncio.shield(task)
                except (Exception, asyncio.CancelledError):
                    pass
                raise
            except Exception:
                if not task.done():
                    operation.cancel.set()
                    try:
                        await asyncio.shield(task)
                    except Exception:
                        pass
                raise
            if web_app._get_job(job_id) is None or operation.cancel.is_set():
                raise ExportUnavailable()
            return FileResponse(path, media_type="application/pdf", headers=headers)
        except Exception:
            # No worker output, paths, document text, or job IDs enter logs/errors.
            job = web_app._get_job(job_id)
            if (
                kind == "highlighted"
                and job is not None
                and not (operation is not None and operation.cancel.is_set())
            ):
                source = web_app._job_pdf_path(web_app._job_dir(job_id))
                if source.is_file():
                    return FileResponse(
                        source,
                        media_type="application/pdf",
                        headers={
                            "Content-Disposition": 'inline; filename="'
                            + web_app._safe_pdf_disposition_filename(job.file_name)
                            + '"'
                        },
                    )
            return web_app._index_notice(
                request, "The PDF report could not be prepared. Please try again.", status_code=503
            )
