"""FastAPI web application for the NJIT thesis auditor upload UI."""

from __future__ import annotations

import json
import os
import secrets
import shutil
import threading
import urllib.parse
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from njit_auditor.audit_runner import AuditError, run_audit_for_uploaded_file
from njit_auditor.models import AuditFinding
from njit_auditor.report_outputs import build_audit_report, write_markdown_report
from njit_auditor.report_view import build_report_view, report_view_to_dict
from njit_auditor.upload_handling import (
    UploadKind,
    UploadValidationError,
    sanitize_upload_filename,
    validate_upload_path,
)
from njit_auditor.web_samples import (
    copy_builtin_sample_to_job,
    get_builtin_sample,
    list_builtin_samples,
)
from njit_auditor.web_url_fetch import FetchError, fetch_pdf_url

# ---------------------------------------------------------------------------
# Configuration from environment
# ---------------------------------------------------------------------------

_DEFAULT_RUNTIME = Path(".runtime") / "web_audits"
_DEFAULT_JOB_TTL_SECONDS = 86400

RUNTIME_DIR = Path(os.environ.get("NJIT_AUDITOR_WEB_RUNTIME_DIR", str(_DEFAULT_RUNTIME)))
MAX_UPLOAD_MB: int = int(os.environ.get("NJIT_AUDITOR_WEB_MAX_UPLOAD_MB", "50"))
MAX_UPLOAD_BYTES: int = MAX_UPLOAD_MB * 1024 * 1024


def _parse_positive_int_env(name: str, default: int) -> int:
    """Parse a positive integer environment variable, falling back safely."""
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


JOB_TTL_SECONDS: int = _parse_positive_int_env(
    "NJIT_AUDITOR_WEB_JOB_TTL_SECONDS",
    _DEFAULT_JOB_TTL_SECONDS,
)

# ---------------------------------------------------------------------------
# Job store (in-memory + runtime files on disk)
# ---------------------------------------------------------------------------

_ALLOWED_WEB_EXTENSIONS = frozenset({".pdf", ".tex", ".zip"})


@dataclass
class JobState:
    job_id: str
    state: str  # pending | running | complete | failed
    created_at: str
    file_name: str
    audit_type: str = "pdf"
    finished_at: str | None = None
    finding_count: int = 0
    warn_count: int = 0
    fail_count: int = 0
    error_message: str = ""
    findings: list[dict[str, Any]] = field(default_factory=list)
    grouped_summary: list[dict[str, Any]] = field(default_factory=list)
    report_view: dict[str, Any] = field(default_factory=dict)
    md_preview: str = ""

    def to_status_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "state": self.state,
            "created_at": self.created_at,
            "finished_at": self.finished_at,
            "finding_count": self.finding_count,
            "file_name": self.file_name,
        }


_jobs: dict[str, JobState] = {}
_jobs_lock = threading.Lock()


def _get_job(job_id: str) -> JobState | None:
    with _jobs_lock:
        return _jobs.get(job_id)


def _set_job(job: JobState) -> None:
    with _jobs_lock:
        _jobs[job.job_id] = job


def _job_dir(job_id: str) -> Path:
    return RUNTIME_DIR / job_id


def _stored_upload_path(jdir: Path, ext: str) -> Path:
    """Return the on-disk path for a job upload with a known extension."""
    return jdir / f"upload{ext}"


def _resolve_job_upload_path(jdir: Path, file_name: str) -> Path:
    """Locate the stored upload file for a job (PDF, TeX, or ZIP)."""
    ext = Path(file_name).suffix.lower()
    if ext in _ALLOWED_WEB_EXTENSIONS:
        candidate = _stored_upload_path(jdir, ext)
        if candidate.exists():
            return candidate
    for fallback_ext in (".pdf", ".tex", ".zip"):
        candidate = _stored_upload_path(jdir, fallback_ext)
        if candidate.exists():
            return candidate
    return _stored_upload_path(jdir, ".pdf")


def _parse_job_timestamp(value: str) -> datetime:
    """Parse an ISO timestamp from job state, defaulting to epoch UTC."""
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return datetime.fromtimestamp(0, tz=timezone.utc)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _is_under_runtime(path: Path) -> bool:
    """Return True when *path* resolves inside the configured runtime directory."""
    try:
        path.resolve().relative_to(RUNTIME_DIR.resolve())
    except ValueError:
        return False
    return True


def _delete_job_workspace(job_id: str) -> None:
    """Delete a job workspace directory when it is safely under RUNTIME_DIR."""
    jdir = _job_dir(job_id)
    if not _is_under_runtime(jdir):
        return
    if jdir.exists():
        shutil.rmtree(jdir, ignore_errors=True)


def cleanup_expired_jobs(now: datetime | None = None) -> int:
    """Evict expired in-memory jobs and delete their runtime workspaces.

    Jobs in ``pending`` or ``running`` state are never removed, even when older
    than the TTL. Orphan directories under :data:`RUNTIME_DIR` without an
    in-memory job are removed when their mtime exceeds the TTL.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    expired_ids: list[str] = []
    with _jobs_lock:
        for job_id, job in list(_jobs.items()):
            if job.state in ("pending", "running"):
                continue
            created = _parse_job_timestamp(job.created_at)
            if (now - created).total_seconds() > JOB_TTL_SECONDS:
                expired_ids.append(job_id)
        for job_id in expired_ids:
            _jobs.pop(job_id, None)

    removed = len(expired_ids)
    for job_id in expired_ids:
        _delete_job_workspace(job_id)

    if RUNTIME_DIR.exists():
        for child in RUNTIME_DIR.iterdir():
            if not child.is_dir() or not _is_under_runtime(child):
                continue
            with _jobs_lock:
                if child.name in _jobs:
                    continue
            mtime = datetime.fromtimestamp(child.stat().st_mtime, tz=timezone.utc)
            if (now - mtime).total_seconds() > JOB_TTL_SECONDS:
                shutil.rmtree(child, ignore_errors=True)
                removed += 1

    return removed


def _web_export_metadata(metadata: dict[str, str]) -> dict[str, str]:
    """Return metadata with filesystem paths reduced to basenames for web export."""
    exported = dict(metadata)
    for key in ("input_file_path", "main_tex_path"):
        value = exported.get(key, "").strip()
        if value:
            exported[key] = Path(value).name
    return exported


def _web_export_findings(findings: list[AuditFinding]) -> list[AuditFinding]:
    """Return findings with source file paths reduced to basenames for web export."""
    exported: list[AuditFinding] = []
    for finding in findings:
        details = dict(finding.details)
        file_path = details.get("file", "").strip()
        if file_path:
            details["file"] = Path(file_path).name
        exported.append(
            AuditFinding(
                rule_id=finding.rule_id,
                severity=finding.severity,
                message=finding.message,
                page=finding.page,
                details=details,
            )
        )
    return exported


def _new_job_id() -> str:
    """Create a new job id after sweeping expired jobs."""
    cleanup_expired_jobs()
    return secrets.token_urlsafe(16)


def _job_not_found_message(job_id: str) -> str:
    ttl_hours = JOB_TTL_SECONDS / 3600
    return (
        f"Job '{job_id[:12]}' was not found. "
        f"Completed jobs are removed after about {ttl_hours:g} hours."
    )


# ---------------------------------------------------------------------------
# FastAPI app + templates
# ---------------------------------------------------------------------------


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    cleanup_expired_jobs()
    yield


app = FastAPI(
    title="NJIT Thesis Auditor",
    docs_url=None,
    redoc_url=None,
    lifespan=_lifespan,
)
_templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def _render(
    request: Request,
    template: str,
    context: dict[str, Any],
    status_code: int = 200,
) -> HTMLResponse:
    """Render a Jinja2 template using the Starlette 1.x API."""
    return _templates.TemplateResponse(
        request=request, name=template, context=context, status_code=status_code
    )


def _highest_severity_label(counts: dict[str, int]) -> tuple[str, str]:
    """Return (severity code, human label) for the highest present severity."""
    if counts.get("FAIL", 0) > 0:
        return "FAIL", "Error (FAIL)"
    if counts.get("WARNING", 0) > 0:
        return "WARNING", "Warning"
    if counts.get("PASS", 0) > 0:
        return "PASS", "Pass"
    return "NONE", "None"


def _job_page_context(job: JobState) -> dict[str, Any]:
    """Build template context for the job results page."""
    report_view = job.report_view or {}
    counts_by_severity = report_view.get("counts_by_severity", {}) or {}
    highest_sev, highest_label = _highest_severity_label(
        {str(k): int(v) for k, v in counts_by_severity.items()}
    )
    pages = report_view.get("pages", []) or []
    counts_by_rule = report_view.get("counts_by_rule", {}) or {}

    filter_rules = sorted({str(f.get("rule_id", "")) for f in job.findings if f.get("rule_id")})
    filter_severities = sorted(
        {str(f.get("severity", "")) for f in job.findings if f.get("severity")}
    )
    filter_categories = sorted(
        {str(f.get("category", "")) for f in job.findings if f.get("category")}
    )
    filter_pages = sorted(
        {str(f.get("page")) for f in job.findings if f.get("page") is not None},
        key=lambda x: int(x),
    )
    filter_locations = sorted(
        {
            str(f.get("location_label"))
            for f in job.findings
            if f.get("location_label")
        }
    )
    ext = Path(job.file_name).suffix.lower()
    audit_type = job.audit_type or ("tex" if ext in {".tex", ".zip"} else "pdf")
    is_source_audit = audit_type == "tex"
    locations_affected = 0
    if is_source_audit:
        locations_affected = len(
            {
                (f.get("source_file"), f.get("source_line"))
                for f in job.findings
                if f.get("source_file") or f.get("source_line")
            }
        )
    audit_scope_label = (
        "TeX source audit (P001–P010)"
        if is_source_audit
        else "PDF layout audit (P011–P061)"
    )

    return {
        "job_id": job.job_id,
        "state": job.state,
        "created_at": job.created_at,
        "finished_at": job.finished_at,
        "file_name": job.file_name,
        "finding_count": job.finding_count,
        "warn_count": job.warn_count,
        "fail_count": job.fail_count,
        "error_message": job.error_message,
        "findings": job.findings,
        "grouped_summary": job.grouped_summary,
        "report_view": job.report_view,
        "md_preview": job.md_preview,
        "highest_severity": highest_sev,
        "highest_severity_label": highest_label,
        "pages_affected": len(pages),
        "locations_affected": locations_affected,
        "is_source_audit": is_source_audit,
        "audit_scope_label": audit_scope_label,
        "rules_flagged": len(counts_by_rule),
        "filter_rules": filter_rules,
        "filter_severities": filter_severities,
        "filter_categories": filter_categories,
        "filter_pages": filter_pages,
        "filter_locations": filter_locations,
    }


def _index_error(request: Request, error: str, status_code: int = 400) -> HTMLResponse:
    return _render(
        request,
        "index.html",
        {"error": error, "max_upload_mb": MAX_UPLOAD_MB, "builtin_samples": list_builtin_samples()},
        status_code=status_code,
    )


# ---------------------------------------------------------------------------
# Background audit task
# ---------------------------------------------------------------------------

def _run_audit_task(job_id: str) -> None:
    """Execute an upload audit in a background thread and update job state."""
    job = _get_job(job_id)
    if job is None:
        return

    job.state = "running"
    _set_job(job)

    jdir = _job_dir(job_id)
    upload_path = _resolve_job_upload_path(jdir, job.file_name)

    try:
        result = run_audit_for_uploaded_file(
            upload_path,
            max_size_bytes=MAX_UPLOAD_BYTES,
            work_dir=jdir,
        )
        findings = result.findings
    except UploadValidationError as exc:
        job.state = "failed"
        job.error_message = str(exc)
        job.finished_at = datetime.now(timezone.utc).isoformat()
        _set_job(job)
        return
    except AuditError as exc:
        job.state = "failed"
        job.error_message = str(exc)
        job.finished_at = datetime.now(timezone.utc).isoformat()
        _set_job(job)
        return
    except Exception:  # noqa: BLE001
        job.state = "failed"
        job.error_message = "An unexpected error occurred during the audit."
        job.finished_at = datetime.now(timezone.utc).isoformat()
        _set_job(job)
        return

    metadata: dict[str, str] = {
        "input_file_name": job.file_name,
        "audit_type": result.audit_type,
        "job_id": job_id,
        "input_file_path": str(upload_path),
    }
    if result.audit_type == "tex":
        metadata["input_kind"] = (
            "zip" if result.upload_kind == UploadKind.ZIP else "tex"
        )
        if result.main_tex_path is not None:
            metadata["main_tex_path"] = str(result.main_tex_path)
        if result.loaded_tex_file_count is not None:
            metadata["loaded_tex_file_count"] = str(result.loaded_tex_file_count)

    export_metadata = _web_export_metadata(metadata)
    export_findings = _web_export_findings(findings)

    # Write JSON report (web exports use basename-only paths)
    json_report_path = jdir / "report.json"
    payload = build_audit_report(export_findings, export_metadata)
    json_report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    # Write Markdown report
    md_report_path = jdir / "report.md"
    write_markdown_report(export_findings, export_metadata, md_report_path)

    view = build_report_view(payload)
    view_dict = report_view_to_dict(view)

    serialized = [
        {
            "rule_id": fv["rule_id"],
            "severity": fv["severity"],
            "page": fv["page"],
            "issue_type": fv["issue_type"],
            "category": fv["category"],
            "polished_comment": fv["polished_comment"],
            "triage_tier": fv.get("triage_tier", ""),
            "confidence": fv.get("confidence", ""),
            "source_file": fv.get("source_file", ""),
            "source_line": fv.get("source_line", ""),
            "location_label": fv.get("location_label", ""),
        }
        for fv in view_dict.get("findings", [])
    ]

    grouped_rows = [
        {
            "rule_id": rs["rule_id"],
            "count": rs["count"],
            "category": rs["category"],
            "top_issue_types": "",
        }
        for rs in view_dict.get("rule_summaries", [])
    ]

    md_preview = md_report_path.read_text(encoding="utf-8")[:6000]

    job.state = "complete"
    job.audit_type = result.audit_type
    job.finding_count = view.total_findings
    job.warn_count = int(view.counts_by_severity.get("WARNING", 0))
    job.fail_count = int(view.counts_by_severity.get("FAIL", 0))
    job.findings = serialized
    job.grouped_summary = grouped_rows
    job.report_view = view_dict
    job.md_preview = md_preview
    job.finished_at = datetime.now(timezone.utc).isoformat()
    _set_job(job)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, error: str = "") -> HTMLResponse:
    return _render(
        request,
        "index.html",
        {"error": error, "max_upload_mb": MAX_UPLOAD_MB, "builtin_samples": list_builtin_samples()},
    )


@app.post("/audits", response_model=None)
async def submit_audit(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
) -> RedirectResponse | HTMLResponse:
    filename = file.filename or "upload.bin"
    ext = Path(filename).suffix.lower()

    if ext not in _ALLOWED_WEB_EXTENSIONS:
        return _index_error(
            request,
            "Supported uploads: PDF (.pdf), TeX source (.tex), and ZIP (.zip). "
            f"Got: {ext or '(no extension)'}",
        )

    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        return _index_error(request, f"File exceeds the {MAX_UPLOAD_MB} MB limit.", status_code=413)

    job_id = _new_job_id()
    jdir = _job_dir(job_id)
    jdir.mkdir(parents=True, exist_ok=True)

    safe_name = sanitize_upload_filename(filename, default_ext=ext or ".pdf")
    upload_path = _stored_upload_path(jdir, ext)
    upload_path.write_bytes(content)

    try:
        validate_upload_path(upload_path, MAX_UPLOAD_BYTES)
    except UploadValidationError as exc:
        shutil.rmtree(jdir, ignore_errors=True)
        return _index_error(request, str(exc))

    pending_audit_type = "tex" if ext in {".tex", ".zip"} else "pdf"
    job = JobState(
        job_id=job_id,
        state="pending",
        created_at=datetime.now(timezone.utc).isoformat(),
        file_name=safe_name,
        audit_type=pending_audit_type,
    )
    _set_job(job)
    background_tasks.add_task(_run_audit_task, job_id)

    return RedirectResponse(url=f"/audits/{job_id}", status_code=303)


@app.post("/audits/url", response_model=None)
async def submit_audit_url(
    request: Request,
    background_tasks: BackgroundTasks,
    pdf_url: str = Form(default=""),
) -> RedirectResponse | HTMLResponse:
    url = pdf_url.strip()
    if not url:
        return _index_error(request, "Please provide a PDF URL.")

    job_id = _new_job_id()
    jdir = _job_dir(job_id)
    jdir.mkdir(parents=True, exist_ok=True)

    try:
        url_path = urllib.parse.urlparse(url).path
        url_basename = Path(url_path).name
        safe_name = (
            sanitize_upload_filename(url_basename, default_ext=".pdf")
            if url_basename.lower().endswith(".pdf")
            else "url_download.pdf"
        )
    except Exception:
        safe_name = "url_download.pdf"

    try:
        fetch_pdf_url(url, jdir / "upload.pdf", MAX_UPLOAD_BYTES)
    except FetchError as exc:
        shutil.rmtree(jdir, ignore_errors=True)
        return _index_error(request, str(exc))

    job = JobState(
        job_id=job_id,
        state="pending",
        created_at=datetime.now(timezone.utc).isoformat(),
        file_name=safe_name,
    )
    _set_job(job)
    background_tasks.add_task(_run_audit_task, job_id)
    return RedirectResponse(url=f"/audits/{job_id}", status_code=303)


@app.post("/audits/sample", response_model=None)
async def submit_audit_sample(
    request: Request,
    background_tasks: BackgroundTasks,
    sample_id: str = Form(default=""),
) -> RedirectResponse | HTMLResponse:
    sid = sample_id.strip()
    if not sid:
        return _index_error(request, "Please select a built-in sample.")

    try:
        info = get_builtin_sample(sid)
    except ValueError:
        return _index_error(request, "Unknown or invalid sample selection.")

    job_id = _new_job_id()
    jdir = _job_dir(job_id)
    jdir.mkdir(parents=True, exist_ok=True)

    try:
        copy_builtin_sample_to_job(sid, jdir / "upload.pdf")
    except FileNotFoundError:
        shutil.rmtree(jdir, ignore_errors=True)
        return _index_error(request, "The selected sample file is not available on this server.")
    except ValueError as exc:
        shutil.rmtree(jdir, ignore_errors=True)
        return _index_error(request, str(exc))
    except Exception:  # noqa: BLE001
        shutil.rmtree(jdir, ignore_errors=True)
        return _index_error(request, "An error occurred loading the sample file.")

    safe_name = sanitize_upload_filename(Path(info.rel_path).name, default_ext=".pdf")
    job = JobState(
        job_id=job_id,
        state="pending",
        created_at=datetime.now(timezone.utc).isoformat(),
        file_name=safe_name,
    )
    _set_job(job)
    background_tasks.add_task(_run_audit_task, job_id)
    return RedirectResponse(url=f"/audits/{job_id}", status_code=303)


@app.get("/audits/{job_id}", response_class=HTMLResponse)
async def job_page(request: Request, job_id: str) -> HTMLResponse:
    cleanup_expired_jobs()
    job = _get_job(job_id)
    if job is None:
        return _index_error(
            request,
            _job_not_found_message(job_id),
            status_code=404,
        )

    return _render(request, "job.html", _job_page_context(job))


@app.get("/audits/{job_id}/status")
async def job_status(job_id: str) -> JSONResponse:
    job = _get_job(job_id)
    if job is None:
        return JSONResponse({"error": "job not found"}, status_code=404)
    return JSONResponse(job.to_status_dict())


@app.get("/audits/{job_id}/download/json", response_model=None)
async def download_json(job_id: str) -> FileResponse | JSONResponse:
    job = _get_job(job_id)
    if job is None or job.state != "complete":
        return JSONResponse({"error": "report not available"}, status_code=404)
    report_path = _job_dir(job_id) / "report.json"
    if not report_path.exists():
        return JSONResponse({"error": "report file missing"}, status_code=404)
    return FileResponse(
        path=str(report_path),
        media_type="application/json",
        filename=f"audit_{job_id[:8]}.json",
    )


@app.get("/audits/{job_id}/download/markdown", response_model=None)
async def download_markdown(job_id: str) -> FileResponse | JSONResponse:
    job = _get_job(job_id)
    if job is None or job.state != "complete":
        return JSONResponse({"error": "report not available"}, status_code=404)
    report_path = _job_dir(job_id) / "report.md"
    if not report_path.exists():
        return JSONResponse({"error": "report file missing"}, status_code=404)
    return FileResponse(
        path=str(report_path),
        media_type="text/markdown",
        filename=f"audit_{job_id[:8]}.md",
    )
