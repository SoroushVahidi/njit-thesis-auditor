"""Private administrator review store and web endpoints. Never used by offline routes."""

from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, urlencode

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

router = APIRouter(include_in_schema=False)
_HASHER = PasswordHasher()
_COOKIE = "__Host-njit-admin"
_LOGIN_CSRF = "__Host-njit-admin-login-csrf"
_SESSION_SECONDS = 8 * 3600
CLASSIFICATIONS = {
    "true_positive": "True Positive",
    "false_positive": "False Positive",
    "unclear": "Unclear / Needs Clarification",
    "other": "Other",
}
STATUSES = {"Open", "In Progress", "Resolved"}


def _enabled(request: Request) -> bool:
    return (
        not getattr(request.app.state, "offline_mode", False)
        and os.getenv("NJIT_AUDITOR_ADMIN_ENABLED") == "1"
        and os.getenv("NJIT_AUDITOR_ADMIN_HTTPS_VERIFIED") == "1"
        and request.url.scheme == "https"
        and os.getenv("NJIT_AUDITOR_ADMIN_PASSWORD_HASH", "").startswith("$argon2id$")
        and bool(os.getenv("NJIT_AUDITOR_ADMIN_DB_PATH", "").strip())
    )


def _db_path() -> Path:
    from njit_auditor import web_app

    raw = os.environ["NJIT_AUDITOR_ADMIN_DB_PATH"]
    path = Path(raw)
    if not path.is_absolute() or path.suffix != ".sqlite3":
        raise ValueError("Administrator database needs an absolute .sqlite3 path")
    if path.is_symlink() or path.parent.is_symlink():
        raise ValueError("Administrator database path may not be a symlink")
    path = path.resolve()
    repo = Path(__file__).resolve().parents[2]
    runtime = web_app.RUNTIME_DIR.resolve()
    if path.is_relative_to(repo) or path.is_relative_to(runtime):
        raise ValueError("Administrator database must be outside the repository and audit runtime")
    if not path.parent.is_dir() or path.parent.is_symlink():
        raise ValueError("Administrator database parent must be an existing real directory")
    if path.parent.stat().st_mode & 0o077:
        raise ValueError("Administrator database parent must be owner-only (0700)")
    return path


def _connect() -> sqlite3.Connection:
    path = _db_path()
    flags = os.O_RDWR | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    try:
        os.fchmod(fd, 0o600)
    finally:
        os.close(fd)
    db = sqlite3.connect(path, timeout=10, isolation_level=None)
    try:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout=10000")
        db.execute("PRAGMA journal_mode=DELETE")
        db.execute("PRAGMA secure_delete=ON")
        db.execute("BEGIN IMMEDIATE")
        version = db.execute("PRAGMA user_version").fetchone()[0]
        if version == 0:
            schema = """
                CREATE TABLE feedback (
                    id TEXT PRIMARY KEY, audit_ref TEXT NOT NULL,
                    finding_ref TEXT NOT NULL, rule_id TEXT NOT NULL,
                    issue_type TEXT NOT NULL, pdf_page INTEGER,
                    original_confidence TEXT NOT NULL,
                    classification TEXT NOT NULL CHECK(classification IN
                        ('true_positive','false_positive','unclear','other')),
                    comment TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'Open' CHECK(status IN
                        ('Open','In Progress','Resolved')),
                    context TEXT NOT NULL, created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL, resolved_at TEXT
                );
                CREATE INDEX feedback_filter_idx ON feedback(
                    rule_id, classification, status, created_at);
                CREATE INDEX feedback_audit_idx ON feedback(audit_ref, finding_ref, created_at);
                CREATE TABLE sessions (
                    token_hash TEXT PRIMARY KEY, expires_at INTEGER NOT NULL
                );
                CREATE TABLE login_attempts (
                    bucket TEXT PRIMARY KEY, count INTEGER NOT NULL, reset_at INTEGER NOT NULL
                );
            """
            for statement in schema.split(";"):
                if statement.strip():
                    db.execute(statement)
            db.execute("PRAGMA user_version=3")
        elif version in (1, 2):
            if version == 1:
                # Preserve every existing review while removing the one-review-per-finding limit.
                db.execute("""CREATE TABLE feedback_v2 (
                id TEXT PRIMARY KEY, audit_ref TEXT NOT NULL,
                finding_ref TEXT NOT NULL, rule_id TEXT NOT NULL,
                issue_type TEXT NOT NULL, pdf_page INTEGER,
                original_confidence TEXT NOT NULL,
                classification TEXT NOT NULL CHECK(classification IN
                    ('true_positive','false_positive','unclear','other')),
                comment TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'Open' CHECK(status IN
                    ('Open','In Progress','Resolved')),
                context TEXT NOT NULL, created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL, resolved_at TEXT
            )""")
                db.execute("INSERT INTO feedback_v2 SELECT * FROM feedback")
                db.execute("DROP TABLE feedback")
                db.execute("ALTER TABLE feedback_v2 RENAME TO feedback")
                db.execute("""CREATE INDEX feedback_filter_idx ON feedback(
                rule_id, classification, status, created_at)""")
                db.execute("""CREATE INDEX feedback_audit_idx ON feedback(
                audit_ref, finding_ref, created_at)""")
            # Old schema stored plaintext CSRF tokens. Revoke these sessions on upgrade.
            db.execute("DROP TABLE sessions")
            db.execute("""CREATE TABLE sessions (
                token_hash TEXT PRIMARY KEY, expires_at INTEGER NOT NULL
            )""")
            db.execute("PRAGMA user_version=3")
        elif version != 3:
            raise RuntimeError("Unsupported administrator database schema")
        db.commit()
    except Exception:
        db.rollback()
        db.close()
        raise
    return db


@contextmanager
def _connection() -> Iterator[sqlite3.Connection]:
    db = _connect()
    try:
        with db:
            yield db
    finally:
        db.close()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _token_hash(token: str) -> str:
    key = os.environ["NJIT_AUDITOR_ADMIN_PASSWORD_HASH"].encode()
    return hmac.new(key, b"session:" + token.encode(), hashlib.sha256).hexdigest()


def _session_csrf(token: str) -> str:
    key = os.environ["NJIT_AUDITOR_ADMIN_PASSWORD_HASH"].encode()
    return hmac.new(key, b"csrf:" + token.encode(), hashlib.sha256).hexdigest()


def session(request: Request) -> dict[str, Any] | None:
    if not _enabled(request):
        return None
    token = request.cookies.get(_COOKIE, "")
    if not token or len(token) > 128:
        return None
    try:
        with _connection() as db:
            row = db.execute(
                "SELECT expires_at FROM sessions WHERE token_hash=?",
                (_token_hash(token),),
            ).fetchone()
    except (OSError, ValueError, RuntimeError, sqlite3.Error):
        return None
    if row is None or row["expires_at"] <= int(time.time()):
        return None
    return {"expires_at": row["expires_at"], "csrf_token": _session_csrf(token)}


def _origin_ok(request: Request) -> bool:
    expected = f"https://{request.url.netloc}"
    return request.headers.get("origin") == expected


async def _form(request: Request) -> dict[str, str]:
    content_type = request.headers.get("content-type", "").split(";", 1)[0]
    if content_type != "application/x-www-form-urlencoded":
        raise ValueError("Unsupported form type")
    if int(request.headers.get("content-length", "0") or "0") > 12000:
        raise ValueError("Form too large")
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 12000:
            raise ValueError("Form too large")
    try:
        parsed = parse_qs(body.decode("utf-8"), keep_blank_values=True)
    except UnicodeDecodeError as exc:
        raise ValueError("Invalid form encoding") from exc
    if any(len(values) != 1 for values in parsed.values()):
        raise ValueError("Duplicate form field")
    return {key: values[0] for key, values in parsed.items()}


def _csrf_ok(request: Request, submitted: str, authenticated: dict[str, Any] | None) -> bool:
    if not _origin_ok(request):
        return False
    expected = (
        authenticated["csrf_token"] if authenticated else request.cookies.get(_LOGIN_CSRF, "")
    )
    return bool(expected) and hmac.compare_digest(str(expected), submitted)


def _deny(request: Request, status: int = 403, message: str = "Administrator access unavailable.",
          login_csrf: str = "") -> HTMLResponse:
    from njit_auditor import web_app

    response = web_app._render(
        request, "admin_login.html", {"error": message, "login_csrf": login_csrf}, status
    )
    response.headers["Cache-Control"] = "no-store"
    return response


def _require(request: Request) -> dict[str, Any] | None:
    return session(request)


def _rate_bucket(request: Request) -> str:
    # Password hash is deployment-specific key material; never persist raw client IPs.
    key = os.environ["NJIT_AUDITOR_ADMIN_PASSWORD_HASH"].encode()
    ip = request.client.host if request.client else "unknown"
    return hmac.new(key, ip.encode(), hashlib.sha256).hexdigest()


def _rate_limited(db: sqlite3.Connection, bucket: str, now: int) -> bool:
    for key, limit in ((bucket, 5), ("global", 30)):
        row = db.execute(
            "SELECT count, reset_at FROM login_attempts WHERE bucket=?", (key,)
        ).fetchone()
        if row and row["reset_at"] > now and row["count"] >= limit:
            return True
    return False


def _record_failure(db: sqlite3.Connection, bucket: str, now: int) -> None:
    for key in (bucket, "global"):
        db.execute("""INSERT INTO login_attempts(bucket,count,reset_at) VALUES (?,1,?)
            ON CONFLICT(bucket) DO UPDATE SET
            count=CASE WHEN reset_at<=? THEN 1 ELSE count+1 END,
            reset_at=CASE WHEN reset_at<=? THEN excluded.reset_at ELSE reset_at END""",
            (key, now + 900, now, now))


@router.get("/admin/login", response_class=HTMLResponse)
async def login_page(request: Request) -> Response:
    from njit_auditor import web_app

    if not _enabled(request):
        return _deny(request, 503)
    if session(request):
        return RedirectResponse("/admin/feedback", status_code=303)
    csrf = secrets.token_urlsafe(32)
    response = web_app._render(request, "admin_login.html", {"login_csrf": csrf})
    response.set_cookie(_LOGIN_CSRF, csrf, secure=True, httponly=True, samesite="strict", path="/")
    response.headers["Cache-Control"] = "no-store"
    return response


@router.post("/admin/login")
async def login(request: Request) -> Response:
    if not _enabled(request):
        return _deny(request, 503)
    try:
        form = await _form(request)
        password = str(form.get("password", ""))
        csrf = str(form.get("csrf_token", ""))
    except (ValueError, TypeError):
        return _deny(request)
    if not _csrf_ok(request, csrf, None):
        return _deny(request)
    now = int(time.time())
    bucket = _rate_bucket(request)
    denial_status = 0
    token = ""
    with _connection() as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("DELETE FROM sessions WHERE expires_at<=?", (now,))
        db.execute("DELETE FROM login_attempts WHERE reset_at<=?", (now,))
        if _rate_limited(db, bucket, now):
            denial_status = 429
        else:
            try:
                valid = bool(_HASHER.verify(
                    os.environ["NJIT_AUDITOR_ADMIN_PASSWORD_HASH"], password
                ))
            except (VerificationError, InvalidHashError):
                valid = False
            if not valid:
                _record_failure(db, bucket, now)
                denial_status = 401
            else:
                db.execute("DELETE FROM login_attempts WHERE bucket=?", (bucket,))
                token = secrets.token_urlsafe(32)
                db.execute("INSERT INTO sessions VALUES (?,?)", (
                    _token_hash(token), now + _SESSION_SECONDS
                ))
    if denial_status:
        message = ("Too many login attempts. Try again later." if denial_status == 429
                   else "Invalid credentials.")
        return _deny(request, denial_status, message, csrf)
    response = RedirectResponse("/admin/feedback", status_code=303)
    response.set_cookie(_COOKIE, token, secure=True, httponly=True, samesite="strict",
                        path="/", max_age=_SESSION_SECONDS)
    response.delete_cookie(_LOGIN_CSRF, path="/", secure=True, httponly=True, samesite="strict")
    response.headers["Cache-Control"] = "no-store"
    return response


@router.post("/admin/logout")
async def logout(request: Request) -> Response:
    auth = _require(request)
    if auth is None:
        return _deny(request)
    try:
        form = await _form(request)
    except (ValueError, TypeError):
        return _deny(request, 400)
    if not _csrf_ok(request, str(form.get("csrf_token", "")), auth):
        return _deny(request)
    with _connection() as db:
        db.execute("DELETE FROM sessions WHERE token_hash=?", (
            _token_hash(request.cookies.get(_COOKIE, "")),))
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie(_COOKIE, path="/", secure=True, httponly=True, samesite="strict")
    return response


def list_feedback(*, page: int = 1, **filters: str) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[str] = []
    for field in ("rule_id", "classification", "status"):
        if filters.get(field):
            clauses.append(f"{field}=?")
            params.append(filters[field])
    if filters.get("from_date"):
        clauses.append("created_at>=?")
        params.append(filters["from_date"])
    if filters.get("to_date"):
        clauses.append("created_at<?")
        params.append(filters["to_date"] + "T23:59:59.999999+00:00")
    sql = "SELECT * FROM feedback" + (" WHERE " + " AND ".join(clauses) if clauses else "")
    with _connection() as db:
        return [
            dict(row) for row in db.execute(
                sql + " ORDER BY created_at DESC LIMIT 100 OFFSET ?", [*params, (page - 1) * 100]
            )
        ]


def list_feedback_for_audit(audit_ref: str) -> list[dict[str, Any]]:
    with _connection() as db:
        return [dict(row) for row in db.execute(
            "SELECT * FROM feedback WHERE audit_ref=? ORDER BY created_at DESC, id DESC",
            (audit_ref,))]


@router.get("/admin/feedback", response_class=HTMLResponse)
async def dashboard(request: Request) -> Response:
    from njit_auditor import web_app

    if _require(request) is None:
        return _deny(request)
    filters = {key: request.query_params.get(key, "") for key in
               ("rule_id", "classification", "status", "from_date", "to_date")}
    if (filters["classification"] not in (*CLASSIFICATIONS, "")
            or filters["status"] not in (*STATUSES, "")):
        return _deny(request, 400)
    if any(len(value) > 100 for value in filters.values()):
        return _deny(request, 400)
    try:
        page = int(request.query_params.get("page", "1"))
    except ValueError:
        return _deny(request, 400)
    if not 1 <= page <= 100000:
        return _deny(request, 400)
    records = list_feedback(page=page, **filters)
    page_filters = {key: value for key, value in filters.items() if value}
    def page_url(target: int) -> str:
        return "/admin/feedback?" + urlencode({**page_filters, "page": target})

    response = web_app._render(request, "admin_feedback.html", {
        "feedback": records, "filters": filters, "page": page,
        "previous_url": page_url(page - 1) if page > 1 else "",
        "next_url": page_url(page + 1) if len(records) == 100 else "",
        "classifications": CLASSIFICATIONS, "statuses": sorted(STATUSES),
        "notice": request.query_params.get("notice", "")[:100],
    })
    response.headers["Cache-Control"] = "no-store"
    return response


@router.post("/audits/{job_id}/feedback/{finding_id}")
async def save_finding_feedback(request: Request, job_id: str, finding_id: str) -> Response:
    from njit_auditor import web_app

    auth = _require(request)
    if auth is None:
        return _deny(request)
    try:
        form = await _form(request)
    except (ValueError, TypeError):
        return _deny(request, 400)
    if not _csrf_ok(request, str(form.get("csrf_token", "")), auth):
        return _deny(request)
    classification = str(form.get("classification", ""))
    comment = str(form.get("comment", ""))
    if classification not in CLASSIFICATIONS or len(comment) > 4000:
        return _deny(
            request, 400, "Choose a classification and keep comments under 4000 characters."
        )
    web_app.cleanup_expired_jobs()
    job = web_app._get_job(job_id)
    if job is None or job.state != "complete" or job.audit_type != "pdf":
        return _deny(request, 404, "This audit has expired or is unavailable.")
    raw_index = web_app.parse_finding_id(finding_id)
    if raw_index is None or raw_index < 0:
        return _deny(request, 404, "This finding is unavailable.")
    finding = next((f for f in job.findings if f.get("finding_id") == finding_id), None)
    if finding is None:
        return _deny(request, 404, "This finding is unavailable.")
    rule_id = str(finding.get("rule_id", ""))
    issue_type = str(finding.get("issue_type", ""))
    confidence = str(finding.get("confidence_level", ""))
    if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,50}", rule_id):
        return _deny(request, 400, "This finding has an invalid rule reference.")
    if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,100}", issue_type):
        issue_type = "unspecified"
    if confidence not in {"high", "medium", "low"}:
        confidence = "unknown"
    page = web_app._coerce_page_number(finding.get("page"))
    now = _now()
    with _connection() as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("""INSERT INTO feedback(id,audit_ref,finding_ref,rule_id,issue_type,
            pdf_page,original_confidence,classification,comment,status,context,created_at,updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,'Open',?,?,?)""", (
            secrets.token_urlsafe(16), job_id, finding_id, rule_id, issue_type, page,
            confidence, classification, comment, f"Rule {rule_id}; issue {issue_type}", now, now,
        ))
    anchor = quote(str(finding.get("problem_anchor", "")))
    return RedirectResponse(f"/audits/{quote(job_id)}?feedback=saved#{anchor}", status_code=303)


@router.post("/admin/feedback/{feedback_id}")
async def update_feedback(request: Request, feedback_id: str) -> Response:
    auth = _require(request)
    if auth is None:
        return _deny(request)
    try:
        form = await _form(request)
    except (ValueError, TypeError):
        return _deny(request, 400)
    if not _csrf_ok(request, str(form.get("csrf_token", "")), auth):
        return _deny(request)
    action = str(form.get("action", "save"))
    if action not in {"save", "delete"}:
        return _deny(request, 400)
    denial_status = 0
    with _connection() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT * FROM feedback WHERE id=?", (feedback_id,)).fetchone()
        if row is None:
            denial_status = 404
        elif action == "delete":
            if str(form.get("confirm_delete", "")) != "yes":
                denial_status = 400
            else:
                db.execute("DELETE FROM feedback WHERE id=?", (feedback_id,))
        else:
            classification = str(form.get("classification", row["classification"]))
            comment = str(form.get("comment", row["comment"]))
            status = str(form.get("status", row["status"]))
            if (classification not in CLASSIFICATIONS or status not in STATUSES
                    or len(comment) > 4000):
                denial_status = 400
            else:
                resolved_at = row["resolved_at"]
                if status == "Resolved" and row["status"] != "Resolved":
                    resolved_at = _now()
                elif status != "Resolved":
                    resolved_at = None
                db.execute("""UPDATE feedback SET classification=?,comment=?,status=?,
                    updated_at=?,resolved_at=? WHERE id=?""",
                    (classification, comment, status, _now(), resolved_at, feedback_id))
    if denial_status:
        return _deny(request, denial_status)
    return RedirectResponse("/admin/feedback?notice=saved", status_code=303)
