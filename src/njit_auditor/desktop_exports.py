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
from starlette.background import BackgroundTask

from njit_auditor import web_app
from njit_auditor.desktop_executor import start_worker, worker_command
from njit_auditor.desktop_process import ProcessTree, is_link_or_junction, prepare_containment
from njit_auditor.desktop_protocol import decode, encode
from njit_auditor.pdf_publication import complete_pdf, file_digest

EXPORT_DEADLINE_SECONDS = 120.0
MAX_ACTIVE_EXPORTS = 2
MAX_PENDING_EXPORTS = 16
MAX_CACHED_EXPORTS_PER_AUDIT = 256
MAX_CACHED_EXPORT_BYTES_PER_AUDIT = 512 * 1024 * 1024


def render_export(directory: Path, job: web_app.JobState, payload: dict[str, Any]) -> None:
    """Worker-only renderer: reuse the hosted rendering and response contracts."""
    handlers = {
        "student": web_app._prepare_student_pdf,
        "comments": web_app._prepare_comments_pdf,
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
        request,
        job.job_id,
        output_dir=directory,
        raw_findings=decode(payload["raw_findings"]),
        **payload["params"],
    )
    if not isinstance(response, FileResponse):
        raise ValueError("PDF export unavailable")
    path = Path(response.path)
    source = web_app._job_pdf_path(web_app._job_dir(job.job_id))
    if path != source:
        expected_pages = 1 if payload["kind"] == "page" else None
        if path.parent != directory or not complete_pdf(path, pages=expected_pages):
            raise ValueError("Incomplete PDF export")
    result = {
        "source": path == source,
        "filename": path.name,
        "digest": file_digest(path),
        "headers": dict(response.headers),
        "retry": getattr(request.state, "retry_export", False),
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
    response_directory: Path | None = None


class ExportUnavailable(Exception):
    pass


class ExportCacheLimit(ExportUnavailable):
    pass


class PdfExportExecutor:
    def __init__(
        self,
        *,
        deadline: float = EXPORT_DEADLINE_SECONDS,
        max_active: int = MAX_ACTIVE_EXPORTS,
        max_cached_exports: int = MAX_CACHED_EXPORTS_PER_AUDIT,
        max_cache_bytes: int = MAX_CACHED_EXPORT_BYTES_PER_AUDIT,
        command: Callable[[Path], list[str]] = worker_command,
    ) -> None:
        if not math.isfinite(deadline) or deadline <= 0 or max_active < 1:
            raise ValueError("Positive finite export limits are required")
        if max_cached_exports < 1 or max_cache_bytes < 1:
            raise ValueError("Positive export cache limits are required")
        prepare_containment()
        self.max_cached_exports = max_cached_exports
        self.max_cache_bytes = max_cache_bytes
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
            if (
                self._closing
                or job is None
                or job.state != "complete"
                or len(self._operations) >= MAX_PENDING_EXPORTS
            ):
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

    def _cached(
        self,
        directory: Path,
        source: Path,
    ) -> tuple[Path, dict[str, str], bool] | None:
        try:
            stamp = directory / ".desktop-result.json"
            if (
                not web_app._is_under_runtime(directory)
                or is_link_or_junction(directory)
                or is_link_or_junction(stamp)
            ):
                return None
            manifest = json.loads(stamp.read_text("utf-8"))
            if not isinstance(manifest["source"], bool) or not isinstance(manifest["retry"], bool):
                return None
            filename = manifest["filename"]
            if not isinstance(filename, str) or Path(filename).name != filename:
                return None
            path = source if manifest["source"] else directory / filename
            if (
                is_link_or_junction(path)
                or not path.is_file()
                or file_digest(path) != manifest["digest"]
            ):
                return None
            disposition = manifest["headers"].get("content-disposition")
            if not isinstance(disposition, str) or "\r" in disposition or "\n" in disposition:
                return None
            return path, {"Content-Disposition": disposition}, manifest["retry"]
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            return None

    @staticmethod
    def _directory_bytes(directory: Path) -> int:
        total = 0
        for path in directory.rglob("*"):
            if is_link_or_junction(path):
                raise ExportUnavailable("Invalid export cache")
            if path.is_file():
                total += path.stat().st_size
        return total

    def _check_cache_budget(
        self,
        directory: Path,
        additional_bytes: int = 0,
        *,
        replaceable: tuple[Path, ...] = (),
    ) -> None:
        # Called under the per-job writer lock. Include old and quarantined
        # generations: neither may grow indefinitely or be deleted under a reader.
        count = size = 0
        for child in directory.iterdir():
            if (
                child in replaceable
                or child.name.startswith(".export-tmp-")
                or not child.name.startswith((".export-", ".invalid-export-"))
            ):
                continue
            if is_link_or_junction(child) or not child.is_dir():
                raise ExportUnavailable("Invalid export cache")
            count += 1
            size += self._directory_bytes(child)
        if count >= self.max_cached_exports or size + additional_bytes > self.max_cache_bytes:
            raise ExportCacheLimit()
        if additional_bytes == 0 and size >= self.max_cache_bytes:
            raise ExportCacheLimit()

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
                "raw_findings": encode(web_app._report_json_findings_for_highlight(job)),
            }
            if (
                not web_app._is_deletable_workspace(directory)
                or not source.is_file()
                or is_link_or_junction(source)
            ):
                raise ExportUnavailable()
            source_digest = file_digest(source)

            def inputs_changed() -> bool:
                current = encode(web_app._report_json_findings_for_highlight(job))
                return (
                    current != payload["raw_findings"]
                    or encode(vars(job)) != payload["job"]
                    or file_digest(source) != source_digest
                )

            # Include raw findings and source bytes, even when timestamps match.
            signature = hashlib.sha256(
                json.dumps(
                    [
                        payload,
                        source_digest,
                    ],
                    sort_keys=True,
                ).encode()
            ).hexdigest()
            generation = ".export-" + signature + "-"
            stale = []
            for candidate in directory.glob(generation + "*"):
                cached = self._cached(candidate, source)
                if cached is not None and not cached[2]:
                    self._check(operation)
                    if inputs_changed():
                        raise ExportUnavailable()
                    return cached[0], cached[1]
                stale.append(candidate)
            with web_app._jobs_lock:
                # Two leases are owned by this operation and its request. Other
                # requests might still be streaming earlier generations by path.
                can_remove = web_app._export_leases.get(operation.job_id, 0) == 2
            replaceable = tuple(
                candidate
                for candidate in stale
                if can_remove and candidate.is_dir() and not is_link_or_junction(candidate)
            )
            self._check_cache_budget(directory, replaceable=replaceable)
            final = directory / (generation + os.urandom(8).hex())
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
            if generated is None or inputs_changed():
                raise ExportUnavailable()
            if generated[0] == source:
                # Best-effort highlight failures return the original PDF. Do not
                # cache that fallback: a later request must be able to retry.
                self._check(operation)
                return generated[0], generated[1]
            request.unlink()
            request.with_name(".desktop-ready").unlink()
            # Cache only the generated PDF and its digest. Worker inputs and
            # renderer-internal metadata do not need to survive the request.
            for child in operation.directory.iterdir():
                if child not in {generated[0], operation.directory / ".desktop-result.json"}:
                    child.unlink()
            if generated[2]:
                with self._lock:
                    self._check(operation)
                    operation.response_directory = operation.directory
                    operation.directory = None
                return generated[0], generated[1]
            self._check_cache_budget(
                directory,
                self._directory_bytes(operation.directory),
                replaceable=replaceable,
            )
            with self._lock:
                # Cancellation and publication share this boundary. A cancellation
                # accepted before this point cannot publish; after it, the artifact
                # is already complete and immutable.
                self._check(operation)
                os.replace(operation.directory, final)
                operation.directory = None
            for previous in replaceable:
                try:
                    shutil.rmtree(previous)
                except OSError:
                    self.cleanup_failed.set()
            cached = self._cached(final, source)
            if cached is None:
                raise ExportUnavailable()
            return cached[0], cached[1]
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
        if kind == "page":
            page = params.get("page")
            if page is None:
                return web_app._index_notice(
                    request, "This PDF page link is missing a page number.", status_code=400
                )
            if page < 1 or (job.pdf_page_count and page > job.pdf_page_count):
                return web_app._index_notice(
                    request,
                    f"Page {page} could not be extracted from this audit PDF.",
                    status_code=404,
                )
        operation = None
        task = None
        handed_off = False
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
            cleanup = (
                BackgroundTask(shutil.rmtree, operation.response_directory, ignore_errors=True)
                if operation.response_directory is not None
                else None
            )
            cached_response = FileResponse(
                path,
                media_type="application/pdf",
                headers=headers,
                background=cleanup,
            )
            handed_off = True
            return cached_response
        except ExportCacheLimit:
            return web_app._index_notice(
                request,
                "This audit has reached its local PDF export storage limit. "
                "Existing downloads remain available. Save your reports, then delete "
                "this local audit and upload the PDF again if you need more exports.",
                status_code=503,
            )
        except Exception:
            # No worker output, paths, document text, or job IDs enter logs/errors.
            job = web_app._get_job(job_id)
            if (
                kind == "highlighted"
                and job is not None
                and not (operation is not None and operation.cancel.is_set())
            ):
                source = web_app._job_pdf_path(web_app._job_dir(job_id))
                if (
                    web_app._is_deletable_workspace(source.parent)
                    and source.is_file()
                    and not is_link_or_junction(source)
                ):
                    return FileResponse(
                        source,
                        media_type="application/pdf",
                        headers={
                            "Content-Disposition": web_app._inline_pdf_disposition(job.file_name)
                        },
                    )
            if job is None:
                return web_app._index_notice(
                    request, web_app._expired_job_notice(), status_code=503
                )
            return web_app._pdf_export_failure_notice(
                request,
                "The PDF report could not be prepared. Please try again.",
                job_id,
                status_code=503,
            )
        finally:
            if operation is not None and not handed_off:

                def discard(_result: object = None) -> None:
                    if operation.response_directory is not None:
                        shutil.rmtree(operation.response_directory, ignore_errors=True)

                if task is not None and not task.done():
                    task.add_done_callback(discard)
                else:
                    discard()
