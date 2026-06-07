"""FastAPI web application for the NJIT thesis auditor upload UI."""

from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import threading
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from njit_auditor.audit_runner import AuditError, run_pdf_audit_full
from njit_auditor.models import AuditFinding, Severity
from njit_auditor.report_outputs import audit_findings_to_json_dict, write_markdown_report
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
RUNTIME_DIR = Path(os.environ.get("NJIT_AUDITOR_WEB_RUNTIME_DIR", str(_DEFAULT_RUNTIME)))
MAX_UPLOAD_MB: int = int(os.environ.get("NJIT_AUDITOR_WEB_MAX_UPLOAD_MB", "50"))
MAX_UPLOAD_BYTES: int = MAX_UPLOAD_MB * 1024 * 1024

# ---------------------------------------------------------------------------
# Job store (in-memory + runtime files on disk)
# ---------------------------------------------------------------------------

_ALLOWED_EXTENSIONS = {".pdf"}
_SAFE_NAME_RE = re.compile(r"[^a-zA-Z0-9._-]")


def _safe_filename(name: str) -> str:
    stem = Path(name).stem
    safe = _SAFE_NAME_RE.sub("_", stem)[:80] or "upload"
    return f"{safe}.pdf"


@dataclass
class JobState:
    job_id: str
    state: str  # pending | running | complete | failed
    created_at: str
    file_name: str
    finished_at: str | None = None
    finding_count: int = 0
    warn_count: int = 0
    fail_count: int = 0
    error_message: str = ""
    findings: list[dict[str, Any]] = field(default_factory=list)
    grouped_summary: list[dict[str, Any]] = field(default_factory=list)
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


# ---------------------------------------------------------------------------
# FastAPI app + templates
# ---------------------------------------------------------------------------

app = FastAPI(title="NJIT Thesis Auditor", docs_url=None, redoc_url=None)
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
    """Execute the PDF audit in a background thread and update job state."""
    job = _get_job(job_id)
    if job is None:
        return

    job.state = "running"
    _set_job(job)

    jdir = _job_dir(job_id)
    pdf_path = jdir / "upload.pdf"

    try:
        findings: list[AuditFinding] = run_pdf_audit_full(pdf_path)
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
        "audit_type": "pdf",
        "job_id": job_id,
    }

    # Write JSON report
    json_report_path = jdir / "report.json"
    payload = audit_findings_to_json_dict(findings, metadata)
    json_report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    # Write Markdown report
    md_report_path = jdir / "report.md"
    write_markdown_report(findings, metadata, md_report_path)

    # Build display structures (privacy-safe: issue_type and message only)
    serialized = [
        {
            "rule_id": f.rule_id,
            "severity": f.severity.value,
            "page": f.page,
            "issue_type": f.details.get("issue_type", ""),
            "message": f.message,
        }
        for f in findings
    ]

    grouped_rows: list[dict[str, Any]] = []
    for entry in payload.get("grouped_summary", {}).get("high_volume_rules", []):
        grouped_rows.append(
            {
                "rule_id": entry.get("rule_id", ""),
                "count": entry.get("count", 0),
                "category": entry.get("category", ""),
                "top_issue_types": ", ".join(
                    t.get("issue_type", "") for t in entry.get("top_issue_types", [])[:3]
                ),
            }
        )

    md_preview = md_report_path.read_text(encoding="utf-8")[:6000]

    job.state = "complete"
    job.finding_count = len(findings)
    job.warn_count = sum(1 for f in findings if f.severity == Severity.WARNING)
    job.fail_count = sum(1 for f in findings if f.severity == Severity.FAIL)
    job.findings = serialized
    job.grouped_summary = grouped_rows
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

    if ext not in _ALLOWED_EXTENSIONS:
        return _index_error(
            request,
            f"Only PDF files are accepted. Got: {ext or '(no extension)'}",
        )

    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        return _index_error(request, f"File exceeds the {MAX_UPLOAD_MB} MB limit.", status_code=413)
    if len(content) < 8:
        return _index_error(request, "File is too small to be a valid PDF.")
    if not content[:4].startswith(b"%PDF"):
        return _index_error(request, "The uploaded file does not appear to be a PDF.")

    job_id = secrets.token_urlsafe(16)
    jdir = _job_dir(job_id)
    jdir.mkdir(parents=True, exist_ok=True)

    safe_name = _safe_filename(filename)
    (jdir / "upload.pdf").write_bytes(content)

    job = JobState(
        job_id=job_id,
        state="pending",
        created_at=datetime.now(timezone.utc).isoformat(),
        file_name=safe_name,
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

    job_id = secrets.token_urlsafe(16)
    jdir = _job_dir(job_id)
    jdir.mkdir(parents=True, exist_ok=True)

    try:
        url_path = urllib.parse.urlparse(url).path
        url_basename = Path(url_path).name
        safe_name = (
            _safe_filename(url_basename)
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

    job_id = secrets.token_urlsafe(16)
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

    safe_name = _safe_filename(Path(info.rel_path).name)
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
    job = _get_job(job_id)
    if job is None:
        return _index_error(
            request,
            f"Job '{job_id[:12]}' not found. It may have expired.",
            status_code=404,
        )

    return _render(
        request,
        "job.html",
        {
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
            "md_preview": job.md_preview,
        },
    )


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
