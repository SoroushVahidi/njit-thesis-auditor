"""Authenticated, local-only route set around the existing PDF audit UI."""

from __future__ import annotations

import asyncio
import hmac
import os
import secrets
import shutil
import stat
import threading
import time
from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from jinja2 import TemplateNotFound
from starlette.exceptions import HTTPException
from starlette.requests import ClientDisconnect
from starlette.routing import Route

from njit_auditor import web_app
from njit_auditor.desktop_executor import DesktopExecutor
from njit_auditor.desktop_exports import PdfExportExecutor
from njit_auditor.request_body_limit import (
    BODY_TOO_LARGE,
    INVALID_BODY,
    MULTIPART_OVERHEAD_BYTES,
    RequestBodyLimitMiddleware,
    read_csrf_token,
)
from njit_auditor.resource_paths import resource_path

SESSION_SECONDS = 8 * 60 * 60
IDLE_SECONDS = 30 * 60
COOKIE_NAME = "njit_offline_session"
_DISALLOWED = {"/healthz", "/version", "/audits/url", "/audits/sample", "/desktop"}
_delete_after_finish: set[str] = set()
_delete_lock = threading.Lock()
_cleanup_failed = False


def _session_unavailable(request: Request, error: str) -> HTMLResponse | JSONResponse:
    """Explain recovery without granting access or exposing a launch credential."""
    response: HTMLResponse | JSONResponse
    if (
        "text/html" in request.headers.get("accept", "").lower()
        and request.headers.get("sec-fetch-mode", "navigate") == "navigate"
    ):
        response = HTMLResponse(
            '<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<title>Reopen your session — NJIT Thesis Auditor</title></head><body>'
            '<main><h1>This auditor session is unavailable</h1>'
            '<p>The session may have expired, or this tab may belong to an older launch.</p>'
            '<p>In the NJIT Thesis Auditor launcher window, choose <strong>Open auditor</strong> '
            'and continue in the tab it opens. If the app has closed or the session has expired, '
            'reopen the app using its shortcut.</p>'
            '<p>This request did not cancel, delete, or submit an audit. '
            'Keep any other working audit tab open. Quitting the app removes its temporary '
            'audit data; downloaded reports saved elsewhere are preserved.</p>'
            '</main></body></html>',
            status_code=403,
        )
    else:
        response = JSONResponse({"error": error}, status_code=403)
    response.headers.update({
        "Cache-Control": "no-store",
        "Referrer-Policy": "no-referrer",
        "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'; form-action 'none'",
    })
    return response


@dataclass
class DeletionSummary:
    deleted: int = 0
    pending: int = 0
    failed: int = 0

    def add(self, result: str) -> None:
        if result == "deleted":
            self.deleted += 1
        elif result == "pending":
            self.pending += 1
        else:
            self.failed += 1


def local_data_root() -> Path:
    """Use an application-specific directory in the user's local profile."""
    if os.name == "nt":
        profile = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return profile / "NJIT Thesis Auditor"
    base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "njit-thesis-auditor"


def is_link_or_junction(path: Path) -> bool:
    """Detect links and Windows reparse points, including on Python 3.10/3.11."""
    if path.is_symlink():
        return True
    try:
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
    except FileNotFoundError:
        return False
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def remove_local_storage_child(path: Path) -> None:
    """Remove one entry without traversing a directory link or junction."""
    if is_link_or_junction(path):
        if not path.is_symlink() and stat.S_ISDIR(path.lstat().st_mode):
            path.rmdir()
        else:
            path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def prepare_local_storage(root: Path) -> Path:
    """Clear abandoned audit workspaces before a new single-instance launch."""
    if is_link_or_junction(root):
        raise RuntimeError("The local application data directory must not be a link")
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(root, 0o700)
    audits = root / "audits"
    for directory in (audits, root / "tmp"):
        if is_link_or_junction(directory):
            raise RuntimeError("The local audit storage directory must not be a link")
        directory.mkdir(mode=0o700, exist_ok=True)
        os.chmod(directory, 0o700)
        for child in directory.iterdir():
            remove_local_storage_child(child)
    return audits


def _delete_job(job_id: str) -> str:
    global _cleanup_failed
    with web_app._jobs_lock:
        job = web_app._jobs.get(job_id)
        if web_app._export_leases.get(job_id) or (
            job is not None and job.state in ("pending", "running")
        ):
            with _delete_lock:
                _delete_after_finish.add(job_id)
            return "pending"
        web_app._jobs.pop(job_id, None)
    if web_app._delete_job_workspace(job_id):
        return "deleted"
    with _delete_lock:
        _cleanup_failed = True
    return "failed"


def _after_audit(job_id: str) -> None:
    with _delete_lock:
        pending = job_id in _delete_after_finish
        _delete_after_finish.discard(job_id)
    if pending:
        _delete_job(job_id)


def delete_all_local_audits() -> DeletionSummary:
    """Delete finished audits and queue running ones for removal on completion."""
    global _cleanup_failed
    result = DeletionSummary()
    with web_app._jobs_lock:
        ids = list(web_app._jobs)
    for job_id in ids:
        result.add(_delete_job(job_id))
    for child in web_app.RUNTIME_DIR.iterdir():
        if child.is_dir() and not child.is_symlink() and child.name not in ids:
            result.add("deleted" if web_app._remove_workspace(child) else "failed")
    with _delete_lock:
        _cleanup_failed = result.failed > 0
    return result


def create_offline_app(
    *,
    port: int,
    data_root: Path,
    launch_ticket: str,
    on_quit: Callable[[], None] | None = None,
    executor: DesktopExecutor | None = None,
    export_executor: PdfExportExecutor | None = None,
) -> FastAPI:
    """Build an offline app with a separate route table and per-launch session."""
    web_app.RUNTIME_DIR = data_root / "audits"
    web_app._after_audit_task = _after_audit
    manager = executor if executor is not None else DesktopExecutor()
    exports = export_executor if export_executor is not None else PdfExportExecutor()

    def request_quit() -> bool:
        exports_stopped = exports.close()
        if not manager.close() or not exports_stopped:
            return False
        if on_quit is not None:
            on_quit()
        return True

    global _cleanup_failed
    _cleanup_failed = False
    session = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(32)
    expires_at = time.monotonic() + SESSION_SECONDS
    last_activity = time.monotonic()
    allowed_host = f"127.0.0.1:{port}"
    allowed_origin = f"http://{allowed_host}"
    # Cookies are scoped by host/path, not TCP port. Two isolated desktop
    # profiles may share a browser; never overwrite another port's credential.
    cookie_name = f"{COOKIE_NAME}_{port}"

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        expiry_timer = (
            threading.Timer(SESSION_SECONDS, request_quit) if on_quit is not None else None
        )
        idle_stop = threading.Event()

        def idle_watchdog() -> None:
            while not idle_stop.wait(60):
                if time.monotonic() - last_activity < IDLE_SECONDS:
                    continue
                with web_app._jobs_lock:
                    busy = bool(web_app._export_leases) or any(
                        j.state in ("pending", "running") for j in web_app._jobs.values()
                    )
                if not busy and on_quit is not None:
                    request_quit()
                    return

        idle_thread = threading.Thread(target=idle_watchdog, daemon=True)
        if expiry_timer is not None:
            expiry_timer.daemon = True
            expiry_timer.start()
            idle_thread.start()
        try:
            async with web_app._lifespan(_app):
                yield
        finally:
            if expiry_timer is not None:
                expiry_timer.cancel()
                idle_stop.set()
                idle_thread.join(timeout=1)
            await asyncio.to_thread(exports.close)
            await asyncio.to_thread(manager.close)
            await asyncio.to_thread(delete_all_local_audits)

    offline = FastAPI(
        title="NJIT Thesis Auditor Offline",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
        telemetry={
            "tracing": False,
            "metrics": False,
            "logs": False,
            "operation_spans": False,
            "auto_configure": False,
        },
    )
    # The fixed eight-page example needs no job/cache lifecycle. Prepare it once
    # before serving, so this remaining PDF route does no PyMuPDF work on the loop.
    from njit_auditor.synthetic_sample import sample_pdf

    offline.state.synthetic_sample_pdf = sample_pdf()
    offline.state.offline_mode = True
    offline.state.audit_executor = manager.run
    offline.state.prepare_audit = manager.register
    offline.state.desktop_executor = manager
    offline.state.pdf_export_executor = exports
    offline.state.request_quit = request_quit
    offline.state.csrf_token = csrf
    offline.state.data_root = data_root

    templates = Jinja2Templates(
        directory=[
            str(resource_path("src", "njit_auditor", "offline_templates")),
            str(resource_path("src", "njit_auditor", "templates")),
        ]
    )
    templates.env.globals.update(web_app._templates.env.globals)
    templates.env.filters.update(web_app._templates.env.filters)
    templates.env.globals["retention_notice"] = (
        "This audit is stored only in your local application data until you delete it "
        "or quit. Downloaded reports saved elsewhere are yours to manage."
    )
    templates.env.globals["offline_cleanup_failed"] = (
        lambda: (_cleanup_failed or manager.cleanup_failed.is_set()
                 or exports.cleanup_failed.is_set())
    )
    offline.state.templates = templates

    @offline.exception_handler(TemplateNotFound)
    async def missing_page(request: Request, _exc: TemplateNotFound):
        # Do not depend on another template or expose the missing resource path.
        return HTMLResponse(
            '<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<title>Page unavailable — NJIT Thesis Auditor</title></head><body>'
            '<h1>This local page is unavailable</h1>'
            '<p>An application file is missing or damaged. Return to the auditor to continue. '
            'If this happens again, quit and replace the app with a complete copy.</p>'
            '<p><a href="/">Return to the auditor</a></p>'
            '<form action="/quit" method="post">'
            f'<input type="hidden" name="csrf_token" value="{csrf}">'
            '<button type="submit">Quit</button></form></body></html>',
            status_code=503,
        )

    @offline.middleware("http")
    async def protect(request: Request, call_next):
        nonlocal last_activity
        if request.headers.get("host") != allowed_host:
            return JSONResponse({"error": "invalid host"}, status_code=403)
        if request.headers.get("sec-fetch-site", "") == "cross-site":
            return JSONResponse({"error": "cross-site request denied"}, status_code=403)
        origin = request.headers.get("origin")
        if origin is not None and origin != allowed_origin:
            return JSONResponse({"error": "invalid origin"}, status_code=403)
        if request.url.path != "/_session/start":
            cookie = request.cookies.get(cookie_name, "")
            if time.monotonic() >= expires_at or not hmac.compare_digest(cookie, session):
                return _session_unavailable(
                    request, "desktop session expired or unavailable"
                )
            if request.method not in ("GET", "HEAD", "OPTIONS"):
                if origin != allowed_origin:
                    return JSONResponse({"error": "origin required"}, status_code=403)
                # The outer ASGI receive guard bounds bytes before this cache.
                # Keep body() for Starlette's downstream replay, and close this
                # separate CSRF parse's temporary files before the endpoint runs.
                try:
                    await request.body()
                    submitted = await read_csrf_token(request)
                except (HTTPException, ClientDisconnect) as exc:
                    status = exc.status_code if isinstance(exc, HTTPException) else 400
                    message = BODY_TOO_LARGE if status == 413 else INVALID_BODY
                    return HTMLResponse(
                        '<!doctype html><html lang="en"><meta charset="utf-8">'
                        '<title>Upload unavailable</title><main><h1>Could not start audit</h1>'
                        f'<p>{message}</p><p><a href="/">Return to the auditor</a></p>'
                        '</main></html>',
                        status_code=status,
                        headers={
                            "Cache-Control": "no-store",
                            "Referrer-Policy": "no-referrer",
                            "X-Content-Type-Options": "nosniff",
                            "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
                        },
                    )
                if not hmac.compare_digest(submitted, csrf):
                    return JSONResponse({"error": "invalid CSRF token"}, status_code=403)
            last_activity = time.monotonic()
        response = await call_next(request)
        # Chromium sends Origin: null for form POSTs from a no-referrer page.
        # Keep the launch ticket private, then allow same-origin form origins
        # without weakening Host, Origin, session, or CSRF validation.
        response.headers["Referrer-Policy"] = (
            "no-referrer" if request.url.path == "/_session/start" else "same-origin"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; connect-src 'self'; img-src 'self' data:; "
            "style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; "
            "object-src 'self'; frame-ancestors 'none'; form-action 'self'"
        )
        return response

    @offline.get("/_session/start", include_in_schema=False)
    async def start_session(request: Request, ticket: str = ""):
        if time.monotonic() >= expires_at or not hmac.compare_digest(ticket, launch_ticket):
            return _session_unavailable(request, "invalid launch ticket")
        response = RedirectResponse("/", status_code=303)
        response.set_cookie(
            cookie_name,
            session,
            httponly=True,
            samesite="strict",
            max_age=SESSION_SECONDS,
            path="/",
        )
        return response

    for route in web_app.app.router.routes:
        if isinstance(route, Route) and route.path not in _DISALLOWED:
            offline.router.routes.append(route)

    @offline.get("/app-icon.ico")
    async def app_icon():
        return FileResponse(resource_path("assets", "icons", "njit-auditor.ico"),
                            media_type="image/vnd.microsoft.icon")

    offline.add_api_route("/audits/sample", web_app.reject_shortcut_audit, methods=["POST"])

    @offline.post("/audits/{job_id}/cancel")
    async def cancel_audit(job_id: str):
        await asyncio.to_thread(exports.cancel, job_id)
        await asyncio.to_thread(manager.cancel, job_id)
        return RedirectResponse(f"/audits/{job_id}", status_code=303)

    @offline.post("/audits/{job_id}/delete")
    async def delete_audit(job_id: str):
        await asyncio.to_thread(exports.cancel, job_id)
        status = _delete_job(job_id)
        return RedirectResponse(f"/?deletion={status}", status_code=303)

    @offline.post("/local-data/delete-all")
    async def delete_all():
        await asyncio.to_thread(exports.cancel)
        result = delete_all_local_audits()
        if not result.failed and not result.pending:
            manager.cleanup_failed.clear()
        status = "failed" if result.failed else "pending" if result.pending else "deleted"
        return RedirectResponse(f"/?deletion={status}", status_code=303)

    @offline.post("/quit")
    async def quit_app(request: Request):
        if not await asyncio.to_thread(request_quit):
            return web_app._index_notice(
                request, "Could not stop the audit yet. Try Quit again.", status_code=503
            )
        return HTMLResponse("<p>Auditor closed. You may close this tab.</p>")

    # add_middleware inserts at the outside of the existing security middleware,
    # so its receive wrapper runs before Request.body() can accumulate a chunk.
    offline.add_middleware(
        RequestBodyLimitMiddleware,
        max_body_bytes=web_app.MAX_UPLOAD_BYTES + MULTIPART_OVERHEAD_BYTES,
    )
    return offline
