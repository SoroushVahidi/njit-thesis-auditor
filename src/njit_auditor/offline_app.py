"""Authenticated, local-only route set around the existing PDF audit UI."""

from __future__ import annotations

import hmac
import logging
import os
import secrets
import shutil
import threading
import time
from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.routing import Route

from njit_auditor import web_app
from njit_auditor.resource_paths import resource_path

SESSION_SECONDS = 8 * 60 * 60
IDLE_SECONDS = 30 * 60
COOKIE_NAME = "njit_offline_session"
FORM_OVERHEAD_BYTES = 1024 * 1024
SMALL_FORM_BYTES = 16 * 1024
TICKET_SECONDS = 2 * 60
_DISALLOWED = {"/healthz", "/version", "/openapi.json", "/audits/url", "/audits/sample"}
_delete_after_finish: set[str] = set()
_delete_lock = threading.Lock()
_cleanup_failed = False


class _NoSensitiveLogFilter(logging.Filter):
    """Keep job access tokens, PDF paths, and exception details out of logs."""

    def filter(self, record: logging.LogRecord) -> bool:
        return False


def _is_link_or_junction(path: Path) -> bool:
    """Reject symlinks and Windows NTFS junctions at deletion boundaries."""
    return path.is_symlink() or getattr(path, "is_junction", lambda: False)()


def _remove_entry(path: Path) -> None:
    if getattr(path, "is_junction", lambda: False)():
        path.rmdir()
    elif path.is_symlink():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


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


def prepare_local_storage(root: Path) -> Path:
    """Clear abandoned audit workspaces before a new single-instance launch."""
    if _is_link_or_junction(root):
        raise RuntimeError("Unsafe local storage directory")
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    if _is_link_or_junction(root):
        raise RuntimeError("Unsafe local storage directory")
    os.chmod(root, 0o700)
    audits = root / "audits"
    for directory in (audits, root / "tmp"):
        if _is_link_or_junction(directory):
            raise RuntimeError("Unsafe local storage directory")
        directory.mkdir(mode=0o700, exist_ok=True)
        if _is_link_or_junction(directory):
            raise RuntimeError("Unsafe local storage directory")
        os.chmod(directory, 0o700)
        for child in directory.iterdir():
            _remove_entry(child)
    return audits


def _delete_job(job_id: str) -> str:
    global _cleanup_failed
    if _is_link_or_junction(web_app.RUNTIME_DIR.parent) or _is_link_or_junction(
        web_app.RUNTIME_DIR
    ):
        _cleanup_failed = True
        return "failed"
    with web_app._jobs_lock:
        job = web_app._jobs.get(job_id)
        if job is not None and job.state in ("pending", "running"):
            with _delete_lock:
                _delete_after_finish.add(job_id)
            return "pending"
        web_app._jobs.pop(job_id, None)
    workspace = web_app.RUNTIME_DIR / job_id
    if _is_link_or_junction(workspace):
        try:
            _remove_entry(workspace)
        except OSError:
            pass
        else:
            return "deleted"
    elif web_app._delete_job_workspace(job_id):
        return "deleted"
    with _delete_lock:
        _cleanup_failed = True
    return "failed"


def _after_audit(job_id: str) -> None:
    # The shared engine can include an absolute upload path in exception
    # messages. Do not expose that path through the local browser interface.
    with web_app._jobs_lock:
        job = web_app._jobs.get(job_id)
        if job is not None and job.state == "failed":
            job.error_message = (
                "This PDF could not be audited. Check that it is a valid, "
                "unencrypted PDF and try again."
            )
    with _delete_lock:
        pending = job_id in _delete_after_finish
        _delete_after_finish.discard(job_id)
    if pending:
        _delete_job(job_id)


def delete_all_local_audits() -> DeletionSummary:
    """Delete finished audits and queue running ones for removal on completion."""
    global _cleanup_failed
    result = DeletionSummary()
    if _is_link_or_junction(web_app.RUNTIME_DIR.parent) or _is_link_or_junction(
        web_app.RUNTIME_DIR
    ):
        result.failed = 1
        _cleanup_failed = True
        return result
    with web_app._jobs_lock:
        ids = list(web_app._jobs)
    for job_id in ids:
        result.add(_delete_job(job_id))
    try:
        children = list(web_app.RUNTIME_DIR.iterdir())
    except OSError:
        result.failed += 1
        _cleanup_failed = True
        return result
    for child in children:
        if child.name in ids:
            continue
        if _is_link_or_junction(child) or not child.is_dir():
            try:
                _remove_entry(child)
            except OSError:
                result.add("failed")
            else:
                result.add("deleted")
        else:
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
) -> FastAPI:
    """Build an offline app with a separate route table and per-launch session."""
    web_app.RUNTIME_DIR = data_root / "audits"
    global _cleanup_failed
    _cleanup_failed = False
    session = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(32)
    ticket_lock = threading.Lock()
    current_ticket = launch_ticket
    ticket_issued_at = time.monotonic()
    expires_at = time.monotonic() + SESSION_SECONDS
    last_activity = time.monotonic()
    allowed_host = f"127.0.0.1:{port}"
    allowed_origin = f"http://{allowed_host}"
    tmp_lock = threading.Lock()
    active_uploads = 0
    tmp_cleanup_requested = False

    def clear_requested_tmp() -> str:
        nonlocal tmp_cleanup_requested
        global _cleanup_failed
        with tmp_lock:
            if not tmp_cleanup_requested:
                return "deleted"
            with web_app._jobs_lock:
                busy = any(j.state in ("pending", "running") for j in web_app._jobs.values())
            if active_uploads or busy:
                return "pending"
            if _is_link_or_junction(data_root) or _is_link_or_junction(data_root / "tmp"):
                _cleanup_failed = True
                return "failed"
            failed = False
            try:
                children = list((data_root / "tmp").iterdir())
            except OSError:
                _cleanup_failed = True
                return "failed"
            for child in children:
                try:
                    _remove_entry(child)
                except OSError:
                    failed = True
            tmp_cleanup_requested = failed
            if failed:
                _cleanup_failed = True
            return "failed" if failed else "deleted"

    def request_tmp_cleanup() -> str:
        nonlocal tmp_cleanup_requested
        with tmp_lock:
            tmp_cleanup_requested = True
        return clear_requested_tmp()

    def after_audit(job_id: str) -> None:
        _after_audit(job_id)
        clear_requested_tmp()

    web_app._after_audit_task = after_audit

    def request_quit_cleanup() -> str:
        result = delete_all_local_audits()
        tmp_status = request_tmp_cleanup()
        if result.failed or tmp_status == "failed":
            return "failed"
        return "pending" if result.pending or tmp_status == "pending" else "deleted"

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        web_logger = logging.getLogger(web_app.__name__)
        no_sensitive_log = _NoSensitiveLogFilter()
        web_logger.addFilter(no_sensitive_log)
        expiry_timer = threading.Timer(SESSION_SECONDS, on_quit) if on_quit is not None else None
        idle_stop = threading.Event()

        def idle_watchdog() -> None:
            while not idle_stop.wait(60):
                if time.monotonic() - last_activity < IDLE_SECONDS:
                    continue
                with web_app._jobs_lock:
                    busy = any(j.state in ("pending", "running") for j in web_app._jobs.values())
                if not busy and on_quit is not None:
                    on_quit()
                    return

        idle_thread = threading.Thread(target=idle_watchdog, daemon=True)
        if expiry_timer is not None:
            expiry_timer.daemon = True
            expiry_timer.start()
            idle_thread.start()
        try:
            # Desktop data is cleared at startup and Quit; the online sweeper
            # is unnecessary here and may traverse a replaced runtime link.
            yield
        finally:
            web_logger.removeFilter(no_sensitive_log)
            if expiry_timer is not None:
                expiry_timer.cancel()
                idle_stop.set()
                idle_thread.join(timeout=1)
            result = delete_all_local_audits()
            tmp_status = request_tmp_cleanup()
            if result.failed or tmp_status == "failed":
                logging.getLogger(__name__).warning(
                    "Local cleanup was incomplete on Quit (%d audit workspace failures).",
                    result.failed,
                )

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
    offline.state.offline_mode = True
    offline.state.csrf_token = csrf
    offline.state.data_root = data_root
    offline.state.request_quit_cleanup = request_quit_cleanup

    def issue_launch_ticket() -> str:
        nonlocal current_ticket, ticket_issued_at
        with ticket_lock:
            current_ticket = secrets.token_urlsafe(32)
            ticket_issued_at = time.monotonic()
            return current_ticket

    offline.state.issue_launch_ticket = issue_launch_ticket

    templates = Jinja2Templates(
        directory=[
            str(resource_path("src", "njit_auditor", "offline_templates")),
            str(resource_path("src", "njit_auditor", "templates")),
        ]
    )
    templates.env.globals.update(web_app._templates.env.globals)
    templates.env.filters.update(web_app._templates.env.filters)
    templates.env.globals["retention_notice"] = lambda: (
        "This audit is stored only in your local application data until you delete it "
        "or quit. Downloaded reports saved elsewhere are yours to manage."
    )
    templates.env.globals["offline_cleanup_failed"] = lambda: _cleanup_failed
    offline.state.templates = templates

    @offline.middleware("http")
    async def protect(request: Request, call_next):
        nonlocal last_activity, active_uploads
        if any(
            _is_link_or_junction(path)
            for path in (data_root, data_root / "audits", data_root / "tmp")
        ):
            return JSONResponse({"error": "unsafe local storage"}, status_code=503)
        if request.headers.get("host") != allowed_host:
            return JSONResponse({"error": "invalid host"}, status_code=403)
        if request.headers.get("sec-fetch-site", "") == "cross-site":
            return JSONResponse({"error": "cross-site request denied"}, status_code=403)
        origin = request.headers.get("origin")
        try:
            referer = urlsplit(request.headers.get("referer", ""))
        except ValueError:
            return JSONResponse({"error": "invalid origin"}, status_code=403)
        same_origin_null = (
            origin == "null"
            and request.headers.get("sec-fetch-site") == "same-origin"
            and referer.scheme == "http"
            and referer.netloc == allowed_host
            and referer.path != "/_session/start"
        )
        if origin is not None and origin != allowed_origin and not same_origin_null:
            return JSONResponse({"error": "invalid origin"}, status_code=403)
        is_upload = request.url.path == "/audits" and request.method == "POST"
        if is_upload:
            with tmp_lock:
                active_uploads += 1
        try:
            if request.url.path != "/_session/start":
                cookie = request.cookies.get(COOKIE_NAME, "")
                if time.monotonic() >= expires_at or not hmac.compare_digest(cookie, session):
                    return JSONResponse(
                        {"error": "desktop session expired or unavailable"}, status_code=403
                    )
                if request.method not in ("GET", "HEAD", "OPTIONS"):
                    if origin != allowed_origin and not same_origin_null:
                        return JSONResponse({"error": "origin required"}, status_code=403)
                    # Bound the body before Starlette parses multipart data.
                    limit = (
                        web_app.MAX_UPLOAD_BYTES + FORM_OVERHEAD_BYTES
                        if is_upload
                        else SMALL_FORM_BYTES
                    )
                    length = request.headers.get("content-length")
                    if length is not None:
                        try:
                            if int(length) > limit:
                                return JSONResponse(
                                    {"error": "request body too large"}, status_code=413
                                )
                        except ValueError:
                            return JSONResponse(
                                {"error": "invalid content length"}, status_code=400
                            )
                    body = bytearray()
                    async for chunk in request.stream():
                        if len(body) + len(chunk) > limit:
                            return JSONResponse(
                                {"error": "request body too large"}, status_code=413
                            )
                        body.extend(chunk)
                    # BaseHTTPMiddleware replays _body to the routed request.
                    request._body = bytes(body)
                    form = await request.form()
                    submitted = str(form.get("csrf_token", ""))
                    if not hmac.compare_digest(submitted, csrf):
                        return JSONResponse({"error": "invalid CSRF token"}, status_code=403)
                last_activity = time.monotonic()
            response = await call_next(request)
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
        finally:
            if is_upload:
                with tmp_lock:
                    active_uploads -= 1
                clear_requested_tmp()

    @offline.get("/_session/start", include_in_schema=False)
    async def start_session(ticket: str = ""):
        nonlocal current_ticket
        with ticket_lock:
            if (
                time.monotonic() >= expires_at
                or time.monotonic() - ticket_issued_at >= TICKET_SECONDS
                or not current_ticket
                or not hmac.compare_digest(ticket, current_ticket)
            ):
                return JSONResponse({"error": "invalid launch ticket"}, status_code=403)
            current_ticket = ""
        response = RedirectResponse("/", status_code=303)
        response.set_cookie(
            COOKIE_NAME,
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

    @offline.post("/audits/{job_id}/delete")
    async def delete_audit(job_id: str):
        status = _delete_job(job_id)
        return RedirectResponse(f"/?deletion={status}", status_code=303)

    @offline.post("/local-data/delete-all")
    async def delete_all():
        result = delete_all_local_audits()
        tmp_status = request_tmp_cleanup()
        status = (
            "failed"
            if result.failed or tmp_status == "failed"
            else "pending"
            if result.pending or tmp_status == "pending"
            else "deleted"
        )
        return RedirectResponse(f"/?deletion={status}", status_code=303)

    @offline.post("/quit")
    async def quit_app():
        status = request_quit_cleanup()
        if status == "failed":
            return HTMLResponse(
                "<p>Some local audit files could not be deleted. "
                "Please <a href='/'>try Delete all local audit data again</a> "
                "before quitting.</p>",
                status_code=500,
            )
        if on_quit is not None:
            on_quit()
        if status == "pending":
            return HTMLResponse("<p>The auditor will close after the active audit finishes.</p>")
        return HTMLResponse("<p>Auditor closed. You may close this tab.</p>")

    return offline
