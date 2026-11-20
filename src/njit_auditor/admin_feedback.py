"""Private administrator review store and web endpoints. Never used by offline routes."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import io
import os
import re
import secrets
import sqlite3
import time
import zipfile
from collections.abc import AsyncIterator, Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, urlencode

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from argon2.low_level import Type
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from starlette.datastructures import UploadFile
from starlette.formparsers import MultiPartException, MultiPartParser

router = APIRouter(include_in_schema=False)
_HASHER = PasswordHasher(type=Type.ID)
_COOKIE = "__Host-njit-admin"
_LOGIN_CSRF = "__Host-njit-admin-login-csrf"
_REVIEWER_COOKIE = "njit-reviewer-beta"
_REVIEWER_LOGIN_CSRF = "njit-reviewer-beta-login-csrf"
_REVIEWER_USERNAMES = {"soroush", "ester"}
_SESSION_SECONDS = 8 * 3600
CLASSIFICATIONS = {
    "true_positive": "True Positive",
    "false_positive": "False Positive",
    "unclear": "Unclear / Needs Clarification",
    "other": "Other",
}
STATUSES = {"Open", "In Progress", "Resolved"}
_FEEDBACK_SELECT = """SELECT f.*, submitter.username AS submitted_by_username,
    editor.username AS last_modified_by_username, resolver.username AS resolved_by_username
    FROM feedback AS f
    LEFT JOIN admins AS submitter ON submitter.id=f.submitted_by_admin_id
    LEFT JOIN admins AS editor ON editor.id=f.last_modified_by_admin_id
    LEFT JOIN admins AS resolver ON resolver.id=f.resolved_by_admin_id"""


def normalize_username(value: str) -> str:
    """Store and look up ASCII usernames in one canonical lowercase form."""
    candidate = value.strip()
    if not candidate.isascii() or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{2,31}", candidate):
        raise ValueError(
            "Username must be 3–32 ASCII letters, digits, dots, dashes, or underscores."
        )
    return candidate.lower()


def _secret_key() -> bytes | None:
    raw = os.getenv("NJIT_AUDITOR_ADMIN_SESSION_KEY", "")
    try:
        key = base64.b64decode(raw + "=" * (-len(raw) % 4), altchars=b"-_", validate=True)
    except (ValueError, binascii.Error):
        return None
    return key if len(key) >= 32 else None


def _required_key() -> bytes:
    key = _secret_key()
    if key is None:
        raise RuntimeError("Administrator session key is unavailable")
    return key


def _enabled(request: Request) -> bool:
    return (
        not getattr(request.app.state, "offline_mode", False)
        and os.getenv("NJIT_AUDITOR_ADMIN_ENABLED") == "1"
        and os.getenv("NJIT_AUDITOR_ADMIN_HTTPS_VERIFIED") == "1"
        and request.url.scheme == "https"
        and _secret_key() is not None
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
        db.execute("PRAGMA foreign_keys=ON")
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
            version = 3
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
            version = 3
        if version == 3:
            db.execute("""CREATE TABLE admins (
                id TEXT PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                active INTEGER NOT NULL CHECK(active IN (0,1)),
                created_at TEXT NOT NULL,
                display_name TEXT
            )""")
            for column in (
                "submitted_by_admin_id", "last_modified_by_admin_id", "resolved_by_admin_id"
            ):
                db.execute(f"ALTER TABLE feedback ADD COLUMN {column} TEXT REFERENCES admins(id)")
            # Shared-password sessions carry no individual identity and cannot survive migration.
            db.execute("DROP TABLE sessions")
            db.execute("""CREATE TABLE sessions (
                token_hash TEXT PRIMARY KEY,
                admin_id TEXT NOT NULL REFERENCES admins(id),
                expires_at INTEGER NOT NULL
            )""")
            db.execute("CREATE INDEX sessions_admin_idx ON sessions(admin_id)")
            db.execute("""CREATE TABLE feedback_deletions (
                feedback_id TEXT PRIMARY KEY,
                audit_ref TEXT NOT NULL,
                finding_ref TEXT NOT NULL,
                deleted_by_admin_id TEXT NOT NULL REFERENCES admins(id),
                deleted_at TEXT NOT NULL
            )""")
            version = 4
        if version == 4:
            db.execute("ALTER TABLE admins ADD COLUMN role TEXT NOT NULL DEFAULT 'admin' "
                       "CHECK(role IN ('admin','reviewer'))")
            db.execute("PRAGMA user_version=5")
        elif version != 5:
            raise RuntimeError("Unsupported administrator database schema")
        db.execute("""CREATE TABLE IF NOT EXISTS general_feedback (
            id TEXT PRIMARY KEY,
            submitted_by_admin_id TEXT NOT NULL REFERENCES admins(id),
            comment TEXT NOT NULL,
            attachment_name TEXT,
            attachment_data BLOB,
            created_at TEXT NOT NULL,
            CHECK(comment <> '' OR attachment_data IS NOT NULL)
        )""")
        db.execute("CREATE INDEX IF NOT EXISTS general_feedback_created_idx "
                   "ON general_feedback(created_at)")
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
    return hmac.new(_required_key(), b"session:" + token.encode(), hashlib.sha256).hexdigest()


def _session_csrf(token: str) -> str:
    return hmac.new(_required_key(), b"csrf:" + token.encode(), hashlib.sha256).hexdigest()


def _reviewer_enabled(request: Request) -> bool:
    return (
        not getattr(request.app.state, "offline_mode", False)
        and os.getenv("NJIT_AUDITOR_REVIEWER_HTTP_BETA_ENABLED") == "1"
        and request.url.scheme == "http"
        and _secret_key() is not None
        and bool(os.getenv("NJIT_AUDITOR_ADMIN_DB_PATH", "").strip())
    )


def _session_for(request: Request, cookie: str, role: str) -> dict[str, Any] | None:
    if role == "admin" and not _enabled(request):
        return None
    if role == "reviewer" and not _reviewer_enabled(request):
        return None
    token = request.cookies.get(cookie, "")
    if not token or len(token) > 128:
        return None
    try:
        with _connection() as db:
            row = db.execute(
                """SELECT s.expires_at, a.id AS admin_id, a.username, a.display_name
                FROM sessions AS s JOIN admins AS a ON a.id=s.admin_id
                WHERE s.token_hash=? AND a.active=1 AND a.role=?""",
                (_token_hash(token), role),
            ).fetchone()
    except (OSError, ValueError, RuntimeError, sqlite3.Error):
        return None
    if row is None or row["expires_at"] <= int(time.time()):
        return None
    return {**dict(row), "csrf_token": _session_csrf(token)}


def session(request: Request) -> dict[str, Any] | None:
    return _session_for(request, _COOKIE, "admin")


def reviewer_session(request: Request) -> dict[str, Any] | None:
    return _session_for(request, _REVIEWER_COOKIE, "reviewer")


def _origin_ok(request: Request, *, reviewer: bool = False) -> bool:
    expected = f"{'http' if reviewer else 'https'}://{request.url.netloc}"
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


def _csrf_ok(request: Request, submitted: str, authenticated: dict[str, Any] | None,
             *, reviewer: bool = False) -> bool:
    if not _origin_ok(request, reviewer=reviewer):
        return False
    expected = (
        authenticated["csrf_token"] if authenticated else request.cookies.get(
            _REVIEWER_LOGIN_CSRF if reviewer else _LOGIN_CSRF, "")
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


def _authorization_current(db: sqlite3.Connection, request: Request, admin_id: str,
                           *, reviewer: bool = False) -> bool:
    """Recheck revocation under the same write lock used for the feedback change."""
    token = request.cookies.get(_REVIEWER_COOKIE if reviewer else _COOKIE, "")
    if not token:
        return False
    row = db.execute(
        """SELECT 1 FROM sessions AS s JOIN admins AS a ON a.id=s.admin_id
        WHERE s.token_hash=? AND s.admin_id=? AND s.expires_at>? AND a.active=1 AND a.role=?""",
        (_token_hash(token), admin_id, int(time.time()), "reviewer" if reviewer else "admin"),
    ).fetchone()
    return row is not None


def _rate_bucket(request: Request) -> str:
    # Never persist raw client IPs; the configured key is outside this database.
    key = _required_key()
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


@lru_cache(maxsize=1)
def _dummy_hash() -> str:
    return _HASHER.hash(secrets.token_urlsafe(32))


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
        username = str(form.get("username", ""))
        password = str(form.get("password", ""))
        csrf = str(form.get("csrf_token", ""))
    except (ValueError, TypeError):
        return _deny(request)
    if not _csrf_ok(request, csrf, None):
        return _deny(request)
    try:
        canonical = normalize_username(username)
    except ValueError:
        canonical = ""
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
            account = db.execute(
                "SELECT id,password_hash,active FROM admins WHERE username=? AND role='admin'",
                (canonical,)
            ).fetchone()
            usable = bool(account and account["active"] and
                          str(account["password_hash"]).startswith("$argon2id$"))
            candidate_hash = str(account["password_hash"]) if usable else _dummy_hash()
            try:
                valid = bool(_HASHER.verify(candidate_hash, password)) and usable
            except (VerificationError, InvalidHashError):
                valid = False
            if not valid:
                _record_failure(db, bucket, now)
                denial_status = 401
            else:
                db.execute("DELETE FROM login_attempts WHERE bucket=?", (bucket,))
                token = secrets.token_urlsafe(32)
                db.execute("INSERT INTO sessions VALUES (?,?,?)", (
                    _token_hash(token), account["id"], now + _SESSION_SECONDS
                ))
    if denial_status:
        message = ("Too many login attempts. Try again later." if denial_status == 429
                   else "Invalid username or password.")
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


def _reviewer_next(value: str) -> str:
    return value if re.fullmatch(r"/audits/[A-Za-z0-9_-]{1,100}", value) else "/"


def _reviewer_deny(request: Request, status: int = 403,
                   message: str = "Reviewer access unavailable.",
                   login_csrf: str = "", next_url: str = "/") -> HTMLResponse:
    from njit_auditor import web_app

    response = web_app._render(request, "reviewer_login.html", {
        "error": message, "login_csrf": login_csrf, "next_url": next_url,
    }, status)
    response.headers["Cache-Control"] = "no-store"
    return response


@router.get("/reviewer/login", response_class=HTMLResponse)
async def reviewer_login_page(request: Request) -> Response:
    from njit_auditor import web_app

    if not _reviewer_enabled(request):
        return _reviewer_deny(request, 503)
    next_url = _reviewer_next(request.query_params.get("next", ""))
    if reviewer_session(request):
        return RedirectResponse(next_url, status_code=303)
    csrf = secrets.token_urlsafe(32)
    response = web_app._render(request, "reviewer_login.html", {
        "login_csrf": csrf, "next_url": next_url,
    })
    response.set_cookie(_REVIEWER_LOGIN_CSRF, csrf, secure=False, httponly=True,
                        samesite="strict", path="/")
    response.headers["Cache-Control"] = "no-store"
    return response


@router.post("/reviewer/login")
async def reviewer_login(request: Request) -> Response:
    if not _reviewer_enabled(request):
        return _reviewer_deny(request, 503)
    try:
        form = await _form(request)
        username = str(form.get("username", ""))
        password = str(form.get("password", ""))
        csrf = str(form.get("csrf_token", ""))
        next_url = _reviewer_next(str(form.get("next", "")))
    except (ValueError, TypeError):
        return _reviewer_deny(request)
    if not _csrf_ok(request, csrf, None, reviewer=True):
        return _reviewer_deny(request)
    try:
        canonical = normalize_username(username)
    except ValueError:
        canonical = ""
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
            account = db.execute(
                "SELECT id,password_hash,active FROM admins WHERE username=? AND role='reviewer'",
                (canonical if canonical in _REVIEWER_USERNAMES else "",),
            ).fetchone()
            usable = bool(account and account["active"] and
                          str(account["password_hash"]).startswith("$argon2id$"))
            candidate_hash = str(account["password_hash"]) if usable else _dummy_hash()
            try:
                valid = bool(_HASHER.verify(candidate_hash, password)) and usable
            except (VerificationError, InvalidHashError):
                valid = False
            if not valid:
                _record_failure(db, bucket, now)
                denial_status = 401
            else:
                db.execute("DELETE FROM login_attempts WHERE bucket=?", (bucket,))
                token = secrets.token_urlsafe(32)
                db.execute("INSERT INTO sessions VALUES (?,?,?)", (
                    _token_hash(token), account["id"], now + _SESSION_SECONDS
                ))
    if denial_status:
        message = ("Too many login attempts. Try again later." if denial_status == 429
                   else "Invalid username or password.")
        return _reviewer_deny(request, denial_status, message, csrf, next_url)
    response = RedirectResponse(next_url, status_code=303)
    response.set_cookie(_REVIEWER_COOKIE, token, secure=False, httponly=True,
                        samesite="strict", path="/", max_age=_SESSION_SECONDS)
    response.delete_cookie(_REVIEWER_LOGIN_CSRF, path="/", secure=False,
                           httponly=True, samesite="strict")
    response.headers["Cache-Control"] = "no-store"
    return response


@router.post("/reviewer/logout")
async def reviewer_logout(request: Request) -> Response:
    auth = reviewer_session(request)
    if auth is None:
        return _reviewer_deny(request)
    try:
        form = await _form(request)
    except (ValueError, TypeError):
        return _reviewer_deny(request, 400)
    if not _csrf_ok(request, str(form.get("csrf_token", "")), auth, reviewer=True):
        return _reviewer_deny(request)
    with _connection() as db:
        db.execute("DELETE FROM sessions WHERE token_hash=?", (
            _token_hash(request.cookies.get(_REVIEWER_COOKIE, "")),))
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie(_REVIEWER_COOKIE, path="/", secure=False,
                           httponly=True, samesite="strict")
    return response


def list_feedback(*, page: int = 1, **filters: str) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[str] = []
    for field in ("rule_id", "classification", "status"):
        if filters.get(field):
            clauses.append(f"f.{field}=?")
            params.append(filters[field])
    if filters.get("from_date"):
        clauses.append("f.created_at>=?")
        params.append(filters["from_date"])
    if filters.get("to_date"):
        clauses.append("f.created_at<?")
        params.append(filters["to_date"] + "T23:59:59.999999+00:00")
    sql = _FEEDBACK_SELECT + (" WHERE " + " AND ".join(clauses) if clauses else "")
    with _connection() as db:
        return [
            dict(row) for row in db.execute(
                sql + " ORDER BY f.created_at DESC LIMIT 100 OFFSET ?",
                [*params, (page - 1) * 100]
            )
        ]


def list_feedback_for_audit(audit_ref: str) -> list[dict[str, Any]]:
    with _connection() as db:
        return [dict(row) for row in db.execute(
            _FEEDBACK_SELECT +
            " WHERE f.audit_ref=? ORDER BY f.created_at DESC, f.id DESC",
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



_GENERAL_ATTACHMENT_BYTES = 4 * 1024 * 1024
_GENERAL_REQUEST_BYTES = _GENERAL_ATTACHMENT_BYTES + 16 * 1024
_GENERAL_EXTENSIONS = {".png", ".jpg", ".jpeg", ".pdf", ".docx"}


def _general_auth(request: Request) -> tuple[dict[str, Any] | None, bool]:
    admin = session(request)
    if admin is not None:
        return admin, False
    return reviewer_session(request), True


def _general_deny(request: Request, status: int = 403, message: str = "Access unavailable.",
                  *, reviewer: bool = True) -> HTMLResponse:
    if reviewer:
        return _reviewer_deny(request, status, message)
    return _deny(request, status, message)


@router.get("/reviewer/general-feedback", response_class=HTMLResponse)
async def general_feedback_page(request: Request) -> Response:
    from njit_auditor import web_app

    auth, is_reviewer = _general_auth(request)
    if auth is None:
        return _general_deny(request)
    with _connection() as db:
        query = """SELECT g.id, g.comment, g.attachment_name, g.created_at,
            a.username AS submitted_by FROM general_feedback g
            JOIN admins a ON a.id=g.submitted_by_admin_id"""
        if is_reviewer:
            rows = db.execute(query + " WHERE g.submitted_by_admin_id=?"
                              " ORDER BY g.created_at DESC LIMIT 100",
                              (auth["admin_id"],)).fetchall()
        else:
            rows = db.execute(query + " ORDER BY g.created_at DESC LIMIT 100").fetchall()
    response = web_app._render(request, "general_feedback.html", {
        "items": [dict(row) for row in rows],
        "notice": request.query_params.get("notice") == "saved",
        "max_attachment_mb": _GENERAL_ATTACHMENT_BYTES // (1024 * 1024),
    })
    response.headers["Cache-Control"] = "no-store"
    return response


def _valid_general_attachment(filename: str, content: bytes) -> bool:
    extension = Path(filename).suffix.lower()
    if not content or extension not in _GENERAL_EXTENSIONS:
        return False
    if extension == ".pdf":
        return content.startswith(b"%PDF-")
    if extension == ".png":
        return content.startswith(b"\x89PNG\r\n\x1a\n")
    if extension in {".jpg", ".jpeg"}:
        return content.startswith(b"\xff\xd8\xff")
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            entries = set(archive.namelist())
            return ("[Content_Types].xml" in entries
                    and "word/document.xml" in entries
                    and not any(name.lower().endswith(("vbaproject.bin", ".exe", ".js"))
                                for name in entries))
    except (OSError, ValueError, zipfile.BadZipFile):
        return False


@router.post("/reviewer/general-feedback")
async def save_general_feedback(request: Request) -> Response:
    auth, is_reviewer = _general_auth(request)
    if auth is None:
        return _general_deny(request)
    if not _origin_ok(request, reviewer=is_reviewer):
        return _general_deny(request)
    if request.headers.get("content-type", "").split(";", 1)[0] != "multipart/form-data":
        return _general_deny(request, 400, "Use the feedback form.", reviewer=is_reviewer)
    try:
        declared = int(request.headers.get("content-length", "0") or "0")
    except ValueError:
        return _general_deny(request, 400, "Invalid request.", reviewer=is_reviewer)
    if declared > _GENERAL_REQUEST_BYTES:
        return _general_deny(request, 413, "Attachment is too large.", reviewer=is_reviewer)

    async def limited_stream() -> AsyncIterator[bytes]:
        total = 0
        async for chunk in request.stream():
            total += len(chunk)
            if total > _GENERAL_REQUEST_BYTES:
                raise ValueError("Request too large")
            yield chunk

    attachment: UploadFile | None = None
    try:
        form = await MultiPartParser(request.headers, limited_stream(),
                                     max_files=1, max_fields=2,
                                     max_part_size=12000).parse()
        fields = form.multi_items()
        if len(fields) != len({name for name, _ in fields}):
            raise ValueError("Duplicate form field")
        if set(form.keys()) - {"csrf_token", "comment", "attachment"}:
            raise ValueError("Unexpected form field")
        csrf = form.get("csrf_token")
        comment = form.get("comment", "")
        candidate = form.get("attachment")
        if not isinstance(csrf, str) or not isinstance(comment, str):
            raise ValueError("Invalid form field")
        if candidate is not None and not isinstance(candidate, UploadFile):
            raise ValueError("Invalid attachment")
        attachment = candidate
        if not _csrf_ok(request, csrf, auth, reviewer=is_reviewer):
            return _general_deny(request)
        comment = comment.strip()
        if len(comment) > 4000:
            raise ValueError("Comment too long")
        filename: str | None = None
        content: bytes | None = None
        if attachment is not None and attachment.filename:
            filename = attachment.filename
            if (len(filename) > 120 or "\x00" in filename
                    or filename != Path(filename).name
                    or "\\" in filename):
                raise ValueError("Invalid attachment name")
            content = await attachment.read(_GENERAL_ATTACHMENT_BYTES + 1)
            if len(content) > _GENERAL_ATTACHMENT_BYTES:
                return _general_deny(request, 413, "Attachment is too large.",
                                     reviewer=is_reviewer)
            if not _valid_general_attachment(filename, content):
                raise ValueError("Unsupported attachment")
        if not comment and content is None:
            raise ValueError("Write a comment or attach a file")
        with _connection() as db:
            db.execute("BEGIN IMMEDIATE")
            if not _authorization_current(db, request, auth["admin_id"],
                                          reviewer=is_reviewer):
                return _general_deny(request)
            db.execute("""INSERT INTO general_feedback
                (id,submitted_by_admin_id,comment,attachment_name,attachment_data,created_at)
                VALUES (?,?,?,?,?,?)""",
                (secrets.token_urlsafe(16), auth["admin_id"], comment,
                 filename, content, _now()))
    except (ValueError, MultiPartException, UnicodeDecodeError):
        return _general_deny(request, 400, "Invalid feedback or attachment.",
                             reviewer=is_reviewer)
    finally:
        if attachment is not None:
            await attachment.close()
    return RedirectResponse("/reviewer/general-feedback?notice=saved", status_code=303)


@router.get("/reviewer/general-feedback/{feedback_id}/attachment")
async def download_general_attachment(request: Request, feedback_id: str) -> Response:
    auth, is_reviewer = _general_auth(request)
    if auth is None:
        return _general_deny(request)
    with _connection() as db:
        row = db.execute("""SELECT submitted_by_admin_id,attachment_name,attachment_data
            FROM general_feedback WHERE id=?""", (feedback_id,)).fetchone()
    if row is None or row["attachment_data"] is None or (
            is_reviewer and row["submitted_by_admin_id"] != auth["admin_id"]):
        return _general_deny(request, 404, "Attachment unavailable.",
                             reviewer=is_reviewer)
    response = Response(bytes(row["attachment_data"]),
                        media_type="application/octet-stream",
                        headers={"Content-Disposition": "attachment; filename*=UTF-8''" +
                                 quote(row["attachment_name"] or "attachment")})
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    return response


@router.post("/audits/{job_id}/feedback/{finding_id}")
async def save_finding_feedback(request: Request, job_id: str, finding_id: str) -> Response:
    from njit_auditor import web_app

    auth = _require(request)
    is_reviewer = auth is None
    if is_reviewer:
        auth = reviewer_session(request)
    if auth is None:
        return _deny(request)
    try:
        form = await _form(request)
    except (ValueError, TypeError):
        return _deny(request, 400)
    if not _csrf_ok(request, str(form.get("csrf_token", "")), auth,
                    reviewer=is_reviewer):
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
        if not _authorization_current(db, request, auth["admin_id"], reviewer=is_reviewer):
            return _deny(request)
        db.execute("""INSERT INTO feedback(id,audit_ref,finding_ref,rule_id,issue_type,
            pdf_page,original_confidence,classification,comment,status,context,created_at,updated_at,
            submitted_by_admin_id,last_modified_by_admin_id)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            secrets.token_urlsafe(16), job_id, finding_id, rule_id, issue_type, page,
            confidence, classification, comment, "Open", f"Rule {rule_id}; issue {issue_type}",
            now, now, auth["admin_id"], auth["admin_id"],
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
        if not _authorization_current(db, request, auth["admin_id"]):
            return _deny(request)
        row = db.execute("SELECT * FROM feedback WHERE id=?", (feedback_id,)).fetchone()
        if row is None:
            denial_status = 404
        elif action == "delete":
            if str(form.get("confirm_delete", "")) != "yes":
                denial_status = 400
            else:
                db.execute("""INSERT INTO feedback_deletions
                    (feedback_id,audit_ref,finding_ref,deleted_by_admin_id,deleted_at)
                    VALUES (?,?,?,?,?)""", (
                    feedback_id, row["audit_ref"], row["finding_ref"], auth["admin_id"], _now()
                ))
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
                resolved_by = row["resolved_by_admin_id"]
                if status == "Resolved" and row["status"] != "Resolved":
                    resolved_at = _now()
                    resolved_by = auth["admin_id"]
                elif status != "Resolved":
                    resolved_at = None
                    resolved_by = None
                db.execute("""UPDATE feedback SET classification=?,comment=?,status=?,
                    updated_at=?,resolved_at=?,last_modified_by_admin_id=?,resolved_by_admin_id=?
                    WHERE id=?""",
                    (classification, comment, status, _now(), resolved_at, auth["admin_id"],
                     resolved_by, feedback_id))
    if denial_status:
        return _deny(request, denial_status)
    return RedirectResponse("/admin/feedback?notice=saved", status_code=303)
