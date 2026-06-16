"""FastAPI web application for the NJIT thesis auditor upload UI."""

from __future__ import annotations

import json
import os
import re
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

from njit_auditor.audit_runner import (
    AuditError,
    classify_pdf_text_layer,
    run_audit_for_uploaded_file,
)
from njit_auditor.models import AuditFinding
from njit_auditor.report_outputs import (
    build_audit_report,
    sanitize_report_for_web_export,
    write_markdown_report,
)
from njit_auditor.report_view import build_report_view, report_view_to_dict
from njit_auditor.upload_handling import (
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

_PDF_ONLY_ERROR = "Only PDF files are supported in the web interface. Please upload a PDF file."


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
    text_layer_quality: str = ""  # "text_layer_ok" | "low_text" | "image_only" | ""
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


def _job_pdf_path(jdir: Path) -> Path:
    """Return the on-disk path for a job's uploaded PDF."""
    return jdir / "upload.pdf"


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

# ---------------------------------------------------------------------------
# Rule catalog helpers (canonical structured data)
# ---------------------------------------------------------------------------

_RULES_JSON_PATH = (
    Path(__file__).parent.parent.parent
    / "data" / "processed" / "rules" / "project_added_rules.json"
)

_P_RULE_RE = re.compile(r"^P\d+$")


def _is_p_rule_id(rule_id: str) -> bool:
    """Return True when rule_id follows the P### pattern."""
    return bool(rule_id) and bool(_P_RULE_RE.match(rule_id))


# Register as a Jinja2 global so templates can call it directly.
_templates.env.globals["is_p_rule_id"] = _is_p_rule_id

# ---------------------------------------------------------------------------
# Category humanization
# ---------------------------------------------------------------------------

_CATEGORY_LABELS: dict[str, str] = {
    "abstract_language": "Abstract language",
    "abstract_length": "Abstract length",
    "abstract_structure": "Abstract structure",
    "annotations": "Annotations / comments",
    "capitalization_case": "Capitalization",
    "committee_approval_page": "Approval page",
    "figure_format": "Figure formatting",
    "figure_table_format": "Figures / tables",
    "font_format": "Font formatting",
    "formatting_override": "Formatting overrides",
    "frontmatter_structure": "Front matter structure",
    "heading_title": "Headings / titles",
    "indentation": "Indentation",
    "labels_references": "Labels / cross-references",
    "latex_linter": "LaTeX linting",
    "list_of_tables_figures_toc": "TOC / lists",
    "margin_or_overflow": "Margins / overflow",
    "page_numbering": "Page numbering",
    "punctuation": "Punctuation",
    "references_citations": "References / citations",
    "spacing_blank_lines": "Spacing / blank lines",
    "table_format": "Table formatting",
    "title_page_metadata": "Title page",
}


def _humanize_cat(category: str) -> str:
    """Return a student-friendly display label for a raw category key."""
    return _CATEGORY_LABELS.get(str(category), str(category).replace("_", " ").capitalize())


_templates.env.filters["humanize_cat"] = _humanize_cat


def humanize_detail_key(value: str) -> str:
    """Replace underscores with spaces for student-facing display of raw detail keys."""
    return str(value).replace("_", " ")


_templates.env.filters["humanize_detail_key"] = humanize_detail_key


def _input_label(rule: dict[str, Any]) -> str:
    inp = rule.get("input_required") or []
    if isinstance(inp, list):
        if "tex_source" in inp and ("compiled_pdf" in inp or "pdf" in inp):
            return "TeX or PDF"
        if "tex_source" in inp:
            return "TeX / ZIP source"
        if "compiled_pdf" in inp or "pdf" in inp:
            return "PDF (compiled)"
    phase = rule.get("phase", "") or ""
    if phase == "tex_source":
        return "TeX / ZIP source"
    return "PDF (compiled)"


def _severity_label(severity: str) -> str:
    mapping = {"fail": "Error (FAIL)", "warning": "Warning", "info": "Info"}
    return mapping.get((severity or "").lower(), severity.upper() if severity else "—")


def _checkability_label(checkability: str | None) -> str:
    mapping = {
        "deterministic": "Exact check",
        "heuristic": "Pattern-based",
        "visual": "Visual / heuristic",
        "manual": "Manual review",
    }
    return mapping.get(checkability or "", "Pattern-based")


def _classify_rule(rule: dict[str, Any]) -> str:
    """Return 'student', 'technical', or 'excluded'."""
    phase = rule.get("phase", "") or ""
    notes = (rule.get("notes", "") or "").lower()
    rule_type = (rule.get("rule_type", "") or "").lower()

    if phase == "evaluation_task" or rule_type == "evaluation_task":
        return "technical"
    if rule_type in ("infrastructure", "reporting_refinement"):
        return "technical"
    if "infrastructure-only" in notes:
        return "technical"
    if "reporting-only" in notes:
        return "technical"
    if phase == "docx_comments":
        return "technical"
    return "student"


def _build_rule_catalog() -> dict[str, Any]:
    """Load P-rules from canonical source and classify for the rules page."""
    try:
        raw = json.loads(_RULES_JSON_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raw = []

    student_rules: list[dict[str, Any]] = []
    technical_rules: list[dict[str, Any]] = []

    for rule in raw:
        rule_id = rule.get("id", "")
        if not _is_p_rule_id(rule_id):
            continue

        notes = (rule.get("notes", "") or "")
        is_experimental = any(
            kw in notes.lower()
            for kw in ("experimental", "opt-in", "disabled by default")
        ) or "experimental" in (rule.get("rule_type", "") or "").lower()
        is_active_default = not is_experimental

        enriched: dict[str, Any] = {
            "id": rule_id,
            "title": rule.get("question", rule.get("title", rule_id)),
            "section": rule.get("section", ""),
            "input_label": _input_label(rule),
            "severity_code": (rule.get("severity", "") or "").lower(),
            "severity_label": _severity_label(rule.get("severity", "")),
            "checkability": rule.get("checkability") or "",
            "checkability_label": _checkability_label(rule.get("checkability")),
            "what_it_checks": rule.get("rule_definition", ""),
            "how_to_correct": rule.get("remediation", ""),
            "is_experimental": is_experimental,
            "is_active_default": is_active_default,
            "implementation_status": rule.get("implementation_status", ""),
        }

        classification = _classify_rule(rule)
        if classification == "student":
            student_rules.append(enriched)
        else:
            enriched["technical_reason"] = _technical_reason(rule)
            technical_rules.append(enriched)

    categories = sorted({r["section"] for r in student_rules if r["section"]})
    input_types = sorted({r["input_label"] for r in student_rules})
    severities = sorted({r["severity_label"] for r in student_rules if r["severity_label"] != "—"})

    return {
        "student_rules": student_rules,
        "technical_rules": technical_rules,
        "categories": categories,
        "input_types": input_types,
        "severities": severities,
        "total_student": len(student_rules),
        "total_technical": len(technical_rules),
    }


def _technical_reason(rule: dict[str, Any]) -> str:
    rule_type = (rule.get("rule_type", "") or "").lower()
    phase = (rule.get("phase", "") or "").lower()
    notes = (rule.get("notes", "") or "").lower()
    if rule_type == "evaluation_task" or phase == "evaluation_task":
        return "Evaluation task — no detector, no student findings"
    if rule_type == "infrastructure":
        return "Infrastructure capability — no standalone findings"
    if rule_type == "reporting_refinement":
        return "Reporting refinement — extends existing summaries, no new findings"
    if "infrastructure-only" in notes:
        return "Infrastructure scaffold — no standalone findings in this phase"
    if "reporting-only" in notes:
        return "Reporting-only refinement — no new raw findings"
    if phase == "docx_comments":
        return "DOCX comment extraction infrastructure"
    return "Technical entry"


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
    """Build template context for the job results page (PDF audits only)."""
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
        "rules_flagged": len(counts_by_rule),
        "grouped_problem_count": len(report_view.get("grouped_problems", []) or []),
        "filter_rules": filter_rules,
        "filter_severities": filter_severities,
        "filter_categories": filter_categories,
        "filter_pages": filter_pages,
        "text_layer_quality": job.text_layer_quality,
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
    upload_path = _job_pdf_path(jdir)

    try:
        result = run_audit_for_uploaded_file(
            upload_path,
            max_size_bytes=MAX_UPLOAD_BYTES,
            work_dir=jdir,
        )
        findings = result.findings
        job.text_layer_quality = classify_pdf_text_layer(upload_path)
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

    export_metadata = _web_export_metadata(metadata)
    export_findings = _web_export_findings(findings)

    # Write JSON report (web exports use basename-only paths, source labels/refs redacted)
    json_report_path = jdir / "report.json"
    payload = build_audit_report(export_findings, export_metadata)
    # Sanitize before writing: replace raw messages embedding label/ref names with
    # generic privacy-safe descriptions for source (TeX) audits.
    web_payload = sanitize_report_for_web_export(payload)
    json_report_path.write_text(json.dumps(web_payload, indent=2), encoding="utf-8")

    # Write Markdown report using sanitized findings so label/ref names do not
    # appear in the downloaded .md or in the in-page preview.
    md_report_path = jdir / "report.md"
    write_markdown_report(export_findings, export_metadata, md_report_path)

    view = build_report_view(web_payload)
    view_dict = report_view_to_dict(view)

    serialized = [
        {
            "rule_id": fv["rule_id"],
            "severity": fv["severity"],
            "page": fv["page"],
            "issue_type": fv["issue_type"],
            "category": fv["category"],
            "polished_comment": fv["polished_comment"],
            "suggested_fix": fv.get("suggested_fix", ""),
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

    if ext != ".pdf":
        return _index_error(request, _PDF_ONLY_ERROR)

    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        return _index_error(request, f"File exceeds the {MAX_UPLOAD_MB} MB limit.", status_code=413)

    job_id = _new_job_id()
    jdir = _job_dir(job_id)
    jdir.mkdir(parents=True, exist_ok=True)

    safe_name = sanitize_upload_filename(filename, default_ext=".pdf")
    upload_path = _job_pdf_path(jdir)
    upload_path.write_bytes(content)

    try:
        validate_upload_path(upload_path, MAX_UPLOAD_BYTES)
    except UploadValidationError as exc:
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


@app.get("/audits/url", response_model=None)
async def get_audits_url_guard() -> RedirectResponse:
    """Redirect accidental GET /audits/url to the upload page.

    A browser issues GET /audits/url when the user navigates back/forward after a
    failed URL-form submission (the POST error response leaves /audits/url in the
    address bar).  Without this guard the path would be matched by the parameterised
    /audits/{job_id} route with job_id="url", producing a confusing "job not found"
    error message.
    """
    return RedirectResponse(url="/", status_code=302)


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


@app.get("/audits/{job_id}/pdf", response_model=None)
async def serve_job_pdf(job_id: str) -> FileResponse | JSONResponse:
    """Serve the uploaded PDF inline for the embedded viewer."""
    job = _get_job(job_id)
    if job is None or job.state != "complete":
        return JSONResponse({"error": "not available"}, status_code=404)
    if job.audit_type != "pdf":
        return JSONResponse({"error": "not a PDF audit"}, status_code=404)
    pdf_path = _job_dir(job_id) / "upload.pdf"
    if not _is_under_runtime(pdf_path) or not pdf_path.exists():
        return JSONResponse({"error": "PDF not found"}, status_code=404)
    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        headers={"Content-Disposition": "inline"},
    )


@app.get("/help", response_class=HTMLResponse)
async def help_page(request: Request) -> HTMLResponse:
    return _render(request, "help.html", {})


@app.get("/rules", response_class=HTMLResponse)
async def rules_page(request: Request) -> HTMLResponse:
    catalog = _build_rule_catalog()
    return _render(request, "rules.html", catalog)
