"""FastAPI web application for the NJIT thesis auditor upload UI."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import platform
import re
import secrets
import shutil
import subprocess
import threading
import urllib.parse
from collections.abc import Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
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
from njit_auditor.highlight_targeting import parse_highlight_bboxes_from_details
from njit_auditor.issue_type_explanations import (
    explain_issue_type,
    has_curated_issue_type_title,
    issue_type_title,
)
from njit_auditor.models import AuditFinding
from njit_auditor.pdf_highlight import (
    build_highlighted_pdf,
    build_highlighted_single_page_pdf,
    build_single_page_pdf,
    get_pdf_page_sizes,
    is_drawable_bbox,
)
from njit_auditor.report_outputs import (
    _high_volume_pattern_note,
    build_audit_report,
    compact_page_list,
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

_logger = logging.getLogger(__name__)

RUNTIME_DIR = Path(os.environ.get("NJIT_AUDITOR_WEB_RUNTIME_DIR", str(_DEFAULT_RUNTIME)))
MAX_UPLOAD_MB: int = int(os.environ.get("NJIT_AUDITOR_WEB_MAX_UPLOAD_MB", "50"))
MAX_UPLOAD_BYTES: int = MAX_UPLOAD_MB * 1024 * 1024
ENVIRONMENT_NAME: str = os.environ.get("NJIT_AUDITOR_WEB_ENVIRONMENT", "local-dev")

# Captured once per process (at import time) so /version reports when this
# worker actually started, not the time of the current request.
_PROCESS_START_TIME: datetime = datetime.now(timezone.utc)


def _read_git_metadata() -> tuple[str, str]:
    """Return (commit, branch) from local Git metadata, or ("unknown", "unknown").

    Deployment may run from a source tree without a usable Git checkout
    (e.g. an exported archive), so any failure here must degrade to
    "unknown" rather than raise.
    """
    repo_root = Path(__file__).resolve().parent.parent.parent
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=2,
            check=True,
        ).stdout.strip()
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=2,
            check=True,
        ).stdout.strip()
        return commit or "unknown", branch or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown", "unknown"


_GIT_COMMIT, _GIT_BRANCH = _read_git_metadata()


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


def _format_ttl(seconds: int) -> str:
    """Convert a TTL in seconds to a human-readable string like 'about 1 hour'."""
    if seconds < 3600:
        mins = max(1, round(seconds / 60))
        unit = "minute" if mins == 1 else "minutes"
        return f"about {mins} {unit}"
    hours = round(seconds / 3600)
    unit = "hour" if hours == 1 else "hours"
    return f"about {hours} {unit}"


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
    pdf_page_count: int = 0
    pdf_page_sizes: list[tuple[float, float]] = field(default_factory=list)
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


def _expired_job_notice() -> str:
    """Body text for the 'audit result no longer available' notice banner."""
    ttl = _format_ttl(JOB_TTL_SECONDS)
    return (
        f"This result may have expired or the server may have restarted — "
        f"results are kept for {ttl}. "
        f"Please upload the file again to start a new audit."
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
# PDF finding links (plain page-anchor vs. highlighted-PDF endpoint)
# ---------------------------------------------------------------------------


def _pdf_highlight_url(
    job_id: str,
    *,
    page: int | None,
    rule_id: str = "",
    issue_type: str = "",
    finding_index: int | None = None,
) -> str:
    """Return the highlighted-PDF URL for a finding."""
    params: dict[str, str] = {}
    if page is not None:
        params["page"] = str(page)
    if rule_id:
        params["rule_id"] = rule_id
    if issue_type:
        params["issue_type"] = issue_type
    if finding_index is not None:
        params["finding_index"] = str(finding_index)
    return f"/audits/{job_id}/highlighted-page.pdf?{urllib.parse.urlencode(params)}"


def _pdf_original_page_url(job_id: str, *, page: int | None) -> str:
    fragment = f"#page={page}" if page is not None else ""
    return f"/audits/{job_id}/pdf{fragment}"


def _pdf_action_url(
    job_id: str,
    *,
    page: int | None,
    action_kind: str,
    rule_id: str = "",
    issue_type: str = "",
    finding_index: int | None = None,
) -> str:
    if action_kind == "highlight":
        return _pdf_highlight_url(
            job_id,
            page=page,
            rule_id=rule_id,
            issue_type=issue_type,
            finding_index=finding_index,
        )
    if action_kind == "original_page" and page is not None:
        return _pdf_original_page_url(job_id, page=page)
    return ""


_templates.env.globals["pdf_finding_url"] = _pdf_highlight_url
_templates.env.globals["pdf_action_url"] = _pdf_action_url

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
    "frontmatter_structure": "Front matter / appendix structure",
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


def _category_slug(category: str) -> str:
    """Return a stable URL slug for a finding category."""
    return str(category).strip().replace("_", "-")


_templates.env.filters["category_slug"] = _category_slug


def _issue_type_slug(issue_type: str) -> str:
    """Return a stable URL slug for a finding issue_type."""
    return str(issue_type).strip().replace("_", "-")


def _issue_type_from_slug(slug: str) -> str:
    """Recover the original issue_type from its URL slug."""
    return str(slug).strip().replace("-", "_")


_templates.env.filters["issue_type_slug"] = _issue_type_slug


_CATEGORY_EXPLANATIONS: dict[str, str] = {
    "abstract_language": (
        "These examples point to abstract wording or structure that should be checked manually."
    ),
    "abstract_length": (
        "These examples relate to abstract length limits for the degree type detected in the PDF."
    ),
    "abstract_structure": (
        "These examples point to abstract structure issues that often affect "
        "approval-ready formatting."
    ),
    "annotations": (
        "These examples show comments or annotations that should usually be "
        "removed before submission."
    ),
    "capitalization_case": (
        "These examples show capitalization patterns that may be inconsistent with NJIT formatting "
        "expectations."
    ),
    "committee_approval_page": (
        "These examples focus on the approval page and similar "
        "committee-signature formatting details."
    ),
    "figure_format": (
        "These examples point to figure formatting issues that may need visual review in the PDF."
    ),
    "figure_table_format": (
        "These examples cover figure and table layout problems that often repeat across a document."
    ),
    "font_format": (
        "These examples show font-related issues such as inconsistent "
        "body-text sizing or family usage."
    ),
    "formatting_override": (
        "These examples point to formatting overrides that may break consistent document styling."
    ),
    "frontmatter_structure": (
        "This group covers several different front-matter and appendix-heading "
        "checks (ordering, dedication formatting, biosketch order, appendix "
        "letter labeling, and similar structure problems). Each example below "
        "shows its exact issue type so you can see precisely which check it "
        "failed."
    ),
    "heading_title": (
        "These examples point to heading or title formatting problems that can "
        "repeat across sections."
    ),
    "indentation": (
        "These examples show indentation patterns that may need review for "
        "consistent paragraph formatting."
    ),
    "labels_references": (
        "These examples relate to labels or cross-references that may need a manual check."
    ),
    "latex_linter": (
        "These examples come from source-side linting checks and are shown only when that audit "
        "type is used."
    ),
    "list_of_tables_figures_toc": (
        "These examples cover the table of contents and list pages, where formatting often repeats."
    ),
    "margin_or_overflow": (
        "These examples show text or objects that may be too close to the margins or spilling "
        "outside them."
    ),
    "page_numbering": (
        "These examples show page-numbering problems such as missing, misplaced, or inconsistent "
        "page numbers."
    ),
    "punctuation": (
        "These examples point to punctuation patterns that may not match the expected formatting "
        "style."
    ),
    "references_citations": (
        "These examples relate to references or citations that may need manual formatting review."
    ),
    "spacing_blank_lines": (
        "These examples show spacing or blank-line patterns that may be inconsistent."
    ),
    "table_format": (
        "These examples focus on table formatting problems that may need layout review."
    ),
    "title_page_metadata": (
        "These examples focus on title-page details that often affect submission formatting."
    ),
}


def _category_explanation(category: str) -> str:
    """Return simple student-facing help text for a category page."""
    return _CATEGORY_EXPLANATIONS.get(
        category,
        f'These examples show findings in the "{_humanize_cat(category)}" group.',
    )


def _input_label(rule: dict[str, Any]) -> str:
    """Return a web-facing input label for a rule.

    This website only ever runs the PDF path, so a rule that also has a
    CLI-only source-side implementation (e.g. P021) is still labeled "PDF
    (compiled)" here — the source-only label is reserved for rules that
    have no PDF path at all and are therefore excluded from this catalog.
    """
    inp = rule.get("input_required") or []
    if isinstance(inp, list):
        if "compiled_pdf" in inp or "pdf" in inp:
            return "PDF (compiled)"
        if "tex_source" in inp:
            return "TeX / ZIP source"
    phase = rule.get("phase", "") or ""
    if phase == "tex_source":
        return "TeX / ZIP source"
    return "PDF (compiled)"


def _severity_label(severity: str) -> str:
    """Map an internal severity code to a simple public label.

    Public-facing pages only distinguish "needs review" from "informational" —
    see the website wording simplification task for rationale.
    """
    mapping = {"fail": "Problem", "warning": "Problem", "info": "Information"}
    return mapping.get((severity or "").lower(), "Information" if severity else "—")


def _checkability_label(checkability: str | None) -> str:
    mapping = {
        "deterministic": "Exact check",
        "heuristic": "Pattern-based",
        "visual": "Visual check",
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
    if "experimental" in rule_type:
        # Experimental/opt-in rules (e.g. P082) are never enabled by default and
        # this website never passes an AuditOptions with them turned on, so they
        # never produce findings on a web PDF audit.
        return "technical"
    if "infrastructure-only" in notes:
        return "technical"
    if "reporting-only" in notes:
        return "technical"
    if phase == "docx_comments":
        return "technical"
    return "student"


_HEURISTIC_WORDING = [
    # Order matters: collapse the "heuristic check" bigram first so it
    # doesn't end up as the doubled-up "check check".
    (re.compile(r"\bHeuristic check\b"), "Automated check"),
    (re.compile(r"\bheuristic check\b"), "automated check"),
    (re.compile(r"\bHeuristically\b"), "Automatically"),
    (re.compile(r"\bheuristically\b"), "automatically"),
    (re.compile(r"\bHeuristics\b"), "Checks"),
    (re.compile(r"\bheuristics\b"), "checks"),
    (re.compile(r"\bHeuristic\b"), "Check"),
    (re.compile(r"\bheuristic\b"), "check"),
]

# A handful of canonical rule_definition/remediation strings reference
# LaTeX-specific authoring/implementation detail (e.g. LaTeX-only remediation
# commands, "implemented for both LaTeX source and compiled PDF"). This
# website only ever runs the PDF path, so those mentions are confusing here.
# Override just the public display text for those entries — the canonical
# rule data on disk (used by the CLI's source audit) is left untouched.
_RULE_TEXT_OVERRIDES: dict[str, dict[str, str]] = {
    "P021": {
        "rule_definition": (
            "PhD abstract maximum: 350 words. MS/Master abstract maximum: 150 "
            "words. Degree type is inferred from the document text. Word count "
            "uses conservative tokenization (letter-containing tokens only)."
        ),
    },
    "P023": {
        "remediation": (
            "Set body text to double line spacing. In Word: set paragraph line "
            "spacing to 'Double'."
        ),
    },
    "P026": {
        "rule_definition": (
            "NJIT guidelines require body text to use an accepted font family and 12pt size. "
            "Word documents should use Times New Roman or Arial. Documents prepared with "
            "common thesis templates often use Computer Modern or Latin Modern, which are "
            "also accepted. "
            "This check looks at ordinary body-text spans on each page for "
            "(A) font size outside 11.0-13.0pt and (B) font family outside accepted "
            "families (Times New Roman, Arial, Computer Modern, Latin Modern, and "
            "common near-equivalent serifs)."
        ),
        "remediation": (
            "Word users: set body text to Times New Roman or Arial at 12pt. "
            "For documents prepared with common thesis templates, Computer Modern or "
            "Latin Modern are accepted."
        ),
    },
    "P028": {
        "remediation": (
            "Use lowercase Roman numerals (i, ii, iii) for front-matter "
            "numbered pages and Arabic numerals (1, 2, 3) for body pages."
        ),
    },
    "P013": {
        "question": (
            "Are all visible page numbers located exactly at the designated "
            "bottom-center position, 0.5 inches from the bottom edge?"
        ),
        "rule_definition": (
            "Detect text that looks like a page number and record its position "
            "and style so it can be checked manually. This is a verification "
            "signal, not a confirmed formatting defect by itself — see the "
            "page-number sequence/style and page-numbering-regime rules for "
            "findings that flag a specific page-numbering problem. "
            "NJIT requires page numbers at the bottom of the page, centered, "
            "0.5 inches from the bottom edge."
        ),
        "remediation": (
            "Set page numbers at the bottom of the page, centered, and "
            "0.5 inches from the bottom edge. Verify the detected page number "
            "is visible and uses the correct numbering style for that section."
        ),
    },
}


def _websafe_rule_text(rule_id: str, field: str, text: str) -> str:
    """Rewrite internal authoring language (e.g. "heuristic", LaTeX-only
    remediation commands) for the public rules page without touching the
    canonical rule data on disk."""
    result = _RULE_TEXT_OVERRIDES.get(rule_id, {}).get(field, text)
    for pattern, replacement in _HEURISTIC_WORDING:
        result = pattern.sub(replacement, result)
    return result


_HIDDEN_PUBLIC_RULE_IDS = frozenset({"P015", "P018", "P026", "P039"})

# Parent rules whose TOC/LoT/LoF student-facing coverage is delegated to P018A–P018Q.
_P018_DELEGATED_PARENT_RULE_IDS = frozenset(
    {"P018", "P024", "P032", "P036", "P039", "P042", "P046", "P048"}
)

_P018_PUBLIC_CARD_SPECS: tuple[dict[str, Any], ...] = (
    {
        "id": "P018A",
        "parent_rule_id": "P018",
        "source_q_rule_ids": ("Q049",),
        "issue_types": ("toc_level_capitalization",),
        "title": (
            "In the Table of Contents, are all level-1 chapter titles displayed in all caps?"
        ),
        "how_to_correct": (
            "Change all level-1 chapter titles in the Table of Contents to all caps."
        ),
    },
    {
        "id": "P018B",
        "parent_rule_id": "P018",
        "source_q_rule_ids": ("Q050",),
        "issue_types": ("toc_level_capitalization",),
        "title": (
            "In the Table of Contents, are all level-2 section titles displayed in title case?"
        ),
        "how_to_correct": (
            "Change all level-2 section titles in the Table of Contents to title case."
        ),
    },
    {
        "id": "P018C",
        "parent_rule_id": "P018",
        "source_q_rule_ids": ("Q051",),
        "issue_types": ("toc_level_capitalization",),
        "title": (
            "In the Table of Contents, are all level-3 section titles displayed in "
            "sentence case?"
        ),
        "how_to_correct": (
            "Change all level-3 section titles in the Table of Contents to sentence case."
        ),
    },
    {
        "id": "P018D",
        "parent_rule_id": "P018",
        "source_q_rule_ids": ("Q052",),
        "issue_types": ("inconsistent_leader_dots",),
        "title": (
            "Is each Table of Contents entry connected to its page number by a "
            "consistent leader style?"
        ),
        "how_to_correct": "Right-align page numbers and use one consistent leader style.",
    },
    {
        "id": "P018E",
        "parent_rule_id": "P018",
        "source_q_rule_ids": ("Q053",),
        "issue_types": ("wrapped_entry_internal_spacing",),
        "title": (
            "Is every wrapped level-1 Table of Contents entry single-spaced internally?"
        ),
        "how_to_correct": "Single-space every wrapped level-1 Table of Contents entry.",
    },
    {
        "id": "P018F",
        "parent_rule_id": "P018",
        "source_q_rule_ids": ("Q054",),
        "issue_types": ("wrapped_entry_internal_spacing",),
        "title": (
            "Is every wrapped level-2 Table of Contents entry single-spaced internally?"
        ),
        "how_to_correct": "Single-space every wrapped level-2 Table of Contents entry.",
    },
    {
        "id": "P018G",
        "parent_rule_id": "P018",
        "source_q_rule_ids": ("Q055",),
        "issue_types": ("wrapped_entry_internal_spacing",),
        "title": (
            "Is every wrapped level-3 Table of Contents entry single-spaced internally?"
        ),
        "how_to_correct": "Single-space every wrapped level-3 Table of Contents entry.",
    },
    {
        "id": "P018H",
        "parent_rule_id": "P018",
        "source_q_rule_ids": ("Q056",),
        "issue_types": (
            "toc_l2_not_indented_relative_to_l1",
            "toc_l3_not_indented_relative_to_l2",
            "inconsistent_hierarchy_indent",
        ),
        "title": (
            "Are level-2 and level-3 Table of Contents entries indented to show hierarchy?"
        ),
        "how_to_correct": (
            "Indent level-2 and level-3 Table of Contents entries to show hierarchy."
        ),
    },
    {
        "id": "P018I",
        "parent_rule_id": "P018",
        "source_q_rule_ids": ("Q057",),
        "issue_types": ("toc_inter_entry_spacing_too_tight",),
        "title": (
            "Is there visible double spacing between consecutive Table of Contents "
            "section-title entries?"
        ),
        "how_to_correct": (
            "Add visible double spacing or a blank line between consecutive Table of "
            "Contents entries."
        ),
    },
    {
        "id": "P018J",
        "parent_rule_id": "P018",
        "source_q_rule_ids": ("Q058",),
        "issue_types": ("single_appendix_missing_title",),
        "title": (
            "If only one appendix is listed in the Table of Contents, does it begin with "
            "'APPENDIX' followed by its title?"
        ),
        "how_to_correct": (
            "Rename the single appendix entry to begin with 'APPENDIX' followed by its "
            "title."
        ),
    },
    {
        "id": "P018K",
        "parent_rule_id": "P018",
        "source_q_rule_ids": ("Q059",),
        "issue_types": ("multiple_appendix_missing_letter",),
        "title": (
            "If multiple appendices are listed in the Table of Contents, are they "
            "identified by letters?"
        ),
        "how_to_correct": (
            "Rename the appendix entries in the Table of Contents to use letter "
            "designations."
        ),
    },
    {
        "id": "P018L",
        "parent_rule_id": "P018",
        "source_q_rule_ids": ("Q067",),
        "issue_types": ("lot_inter_entry_spacing_too_tight",),
        "title": (
            "Is there visible double spacing between consecutive List of Tables entries?"
        ),
        "how_to_correct": (
            "Add visible double spacing or a blank line between consecutive List of Tables "
            "entries."
        ),
    },
    {
        "id": "P018M",
        "parent_rule_id": "P018",
        "source_q_rule_ids": ("Q068",),
        "issue_types": ("lot_entry_number_column_misaligned",),
        "title": (
            "Are all table numbers in the List of Tables aligned vertically in one left "
            "column?"
        ),
        "how_to_correct": (
            "Align all table numbers in the List of Tables into one vertical left column."
        ),
    },
    {
        "id": "P018N",
        "parent_rule_id": "P018",
        "source_q_rule_ids": ("Q069",),
        "issue_types": ("lot_page_number_column_misaligned",),
        "title": (
            "Are all List of Tables page numbers aligned vertically in one right column?"
        ),
        "how_to_correct": (
            "Align all List of Tables page numbers into one vertical right column."
        ),
    },
    {
        "id": "P018O",
        "parent_rule_id": "P018",
        "source_q_rule_ids": ("Q077",),
        "issue_types": ("lof_inter_entry_spacing_too_tight",),
        "title": (
            "Is there visible double spacing between consecutive List of Figures entries?"
        ),
        "how_to_correct": (
            "Add visible double spacing or a blank line between consecutive List of "
            "Figures entries."
        ),
    },
    {
        "id": "P018P",
        "parent_rule_id": "P018",
        "source_q_rule_ids": ("Q078",),
        "issue_types": ("lof_entry_number_column_misaligned",),
        "title": (
            "Are all figure numbers in the List of Figures aligned vertically in one left "
            "column?"
        ),
        "how_to_correct": (
            "Align all figure numbers in the List of Figures into one vertical left column."
        ),
    },
    {
        "id": "P018Q",
        "parent_rule_id": "P018",
        "source_q_rule_ids": ("Q079",),
        "issue_types": ("lof_page_number_column_misaligned",),
        "title": (
            "Are all List of Figures page numbers aligned vertically in one right column?"
        ),
        "how_to_correct": (
            "Align all List of Figures page numbers into one vertical right column."
        ),
    },
)

_P024_REMAINING_PUBLIC_CARD_SPECS: tuple[dict[str, Any], ...] = (
    {
        "id": "P024D",
        "parent_rule_id": "P024",
        "source_q_rule_ids": ("Q065",),
        "issue_types": ("list_of_tables_title_case",),
        "title": "In the List of Tables, are table titles displayed in title case?",
        "how_to_correct": "Change List of Tables entry titles to title case.",
    },
    {
        "id": "P024E",
        "parent_rule_id": "P024",
        "source_q_rule_ids": ("Q074",),
        "issue_types": ("list_of_figures_sentence_case",),
        "title": "In the List of Figures, are figure descriptions displayed in sentence case?",
        "how_to_correct": (
            "Change the List of Figures entry to sentence case. Capitalize only "
            "the first word, proper nouns, and acronyms."
        ),
    },
)

_P032_REMAINING_PUBLIC_CARD_SPECS: tuple[dict[str, Any], ...] = (
    {
        "id": "P032B",
        "parent_rule_id": "P032",
        "source_q_rule_ids": ("Q066",),
        "issue_types": ("wrapped_entry_internal_spacing",),
        "title": (
            "Does every wrapped List of Tables entry stay single-spaced between its first "
            "line and continuation line?"
        ),
        "how_to_correct": "Single-space each wrapped List of Tables entry internally.",
    },
    {
        "id": "P032C",
        "parent_rule_id": "P032",
        "source_q_rule_ids": ("Q076",),
        "issue_types": ("wrapped_entry_internal_spacing",),
        "title": (
            "Does every wrapped List of Figures entry stay single-spaced between its first "
            "line and continuation line?"
        ),
        "how_to_correct": "Single-space each wrapped List of Figures entry internally.",
    },
)

_P018_ENTRY_LEVEL_TO_CARD = {
    "1": "P018A",
    "2": "P018B",
    "3": "P018C",
}
_P018_Q_RULE_TO_CARD = {
    "Q049": "P018A",
    "Q050": "P018B",
    "Q051": "P018C",
    "Q052": "P018D",
    "Q053": "P018E",
    "Q054": "P018F",
    "Q055": "P018G",
    "Q056": "P018H",
    "Q057": "P018I",
    "Q058": "P018J",
    "Q059": "P018K",
    "Q067": "P018L",
    "Q068": "P018M",
    "Q069": "P018N",
    "Q077": "P018O",
    "Q078": "P018P",
    "Q079": "P018Q",
}
_P018_ENTRY_KIND_TO_CARD = {
    "toc_level_1": "P018E",
    "toc_level_2": "P018F",
    "toc_level_3": "P018G",
}
_P018_BACKEND_ISSUE_MAP: dict[tuple[str, str], str] = {
    ("P018", "inconsistent_leader_dots"): "P018D",
    ("P018", "inconsistent_hierarchy_indent"): "P018H",
    ("P039", "toc_l2_not_indented_relative_to_l1"): "P018H",
    ("P039", "toc_l3_not_indented_relative_to_l2"): "P018H",
    ("P036", "toc_inter_entry_spacing_too_tight"): "P018I",
    ("P036", "lot_inter_entry_spacing_too_tight"): "P018L",
    ("P036", "lof_inter_entry_spacing_too_tight"): "P018O",
    ("P042", "single_appendix_missing_title"): "P018J",
    ("P042", "multiple_appendix_missing_letter"): "P018K",
    ("P046", "lot_entry_number_column_misaligned"): "P018M",
    ("P046", "lof_entry_number_column_misaligned"): "P018P",
    ("P048", "lot_page_number_column_misaligned"): "P018N",
    ("P048", "lof_page_number_column_misaligned"): "P018Q",
}

_PUBLIC_RULE_ISSUE_REFERENCE: dict[tuple[str, str], str] = {
    ("P015", "unexpected_opening_indent"): "P015A",
    ("P015", "missing_later_indent"): "P015B",
    ("P026", "possible_body_font_family_issue"): "P026A",
    ("P026", "possible_body_font_size_issue"): "P026B",
}


def _detail_str(details: Mapping[str, Any] | None, key: str) -> str:
    if not details:
        return ""
    return str(details.get(key, "")).strip()


def _resolve_p018_public_card(
    rule_id: str,
    issue_type: str,
    *,
    source_q_rule_id: str = "",
    details: Mapping[str, Any] | None = None,
) -> str:
    """Map backend TOC/List findings to canonical P018A–P018Q public cards."""
    clean_rule_id = str(rule_id).strip()
    clean_issue_type = str(issue_type).strip()
    clean_q_rule = str(source_q_rule_id).strip()
    entry_level = _detail_str(details, "entry_level")
    entry_kind = _detail_str(details, "entry_kind")
    section_type = _detail_str(details, "section_type")

    if clean_q_rule in _P018_Q_RULE_TO_CARD:
        return _P018_Q_RULE_TO_CARD[clean_q_rule]

    if clean_issue_type == "toc_level_capitalization":
        if entry_level in _P018_ENTRY_LEVEL_TO_CARD:
            return _P018_ENTRY_LEVEL_TO_CARD[entry_level]

    if clean_issue_type == "wrapped_entry_internal_spacing":
        if entry_kind in _P018_ENTRY_KIND_TO_CARD:
            return _P018_ENTRY_KIND_TO_CARD[entry_kind]
        if section_type == "list_of_tables":
            return "P032B"
        if section_type == "list_of_figures":
            return "P032C"
        if section_type == "table_of_contents" or clean_rule_id == "P032":
            return "P018E"

    if clean_issue_type == "misaligned_page_number_column":
        if section_type == "list_of_tables":
            return "P018N"
        if section_type == "list_of_figures":
            return "P018Q"

    mapped = _P018_BACKEND_ISSUE_MAP.get((clean_rule_id, clean_issue_type))
    if mapped:
        return mapped

    return ""


def _atomic_public_card_dict(
    enriched: dict[str, Any],
    spec: dict[str, Any],
) -> dict[str, Any]:
    card = dict(enriched)
    card["id"] = spec["id"]
    card["title"] = spec["title"]
    card["what_it_checks"] = spec["title"]
    card["how_to_correct"] = spec["how_to_correct"]
    card["parent_rule_id"] = spec.get("parent_rule_id", "")
    card["source_q_rule_ids"] = list(spec.get("source_q_rule_ids", ()) or ())
    card["issue_types"] = list(spec.get("issue_types", ()) or ())
    return card


def _public_rule_reference_id(
    rule_id: str,
    *,
    issue_type: str = "",
    source_q_rule_id: str = "",
    details: Mapping[str, Any] | None = None,
) -> str:
    """Map a backend finding/rule to the student-facing /rules anchor ID."""
    clean_rule_id = str(rule_id).strip()
    clean_issue_type = str(issue_type).strip()
    clean_q_rule = str(source_q_rule_id).strip()

    p018_card = _resolve_p018_public_card(
        clean_rule_id,
        clean_issue_type,
        source_q_rule_id=clean_q_rule,
        details=details,
    )
    if p018_card:
        return p018_card

    mapped = _PUBLIC_RULE_ISSUE_REFERENCE.get((clean_rule_id, clean_issue_type))
    if mapped is not None:
        return mapped
    if clean_rule_id in _HIDDEN_PUBLIC_RULE_IDS:
        return ""
    return clean_rule_id if clean_rule_id in _public_rule_lookup() else ""


def _public_rule_reference_href(
    rule_id: str,
    *,
    issue_type: str = "",
    source_q_rule_id: str = "",
    details: Mapping[str, Any] | None = None,
) -> str:
    anchor_id = _public_rule_reference_id(
        rule_id,
        issue_type=issue_type,
        source_q_rule_id=source_q_rule_id,
        details=details,
    )
    return f"/rules#{anchor_id}" if anchor_id else ""


_templates.env.globals["public_rule_reference_id"] = _public_rule_reference_id
_templates.env.globals["public_rule_reference_href"] = _public_rule_reference_href


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

        # This website accepts PDF uploads only, so source-only checks (TeX / ZIP
        # input, no PDF path) never produce findings here. Keep them out of the
        # public catalog entirely; they remain available to the CLI's source audit.
        if _input_label(rule) == "TeX / ZIP source":
            continue

        notes = (rule.get("notes", "") or "")
        is_experimental = any(
            kw in notes.lower()
            for kw in ("experimental", "opt-in", "disabled by default")
        ) or "experimental" in (rule.get("rule_type", "") or "").lower()
        is_active_default = not is_experimental

        enriched: dict[str, Any] = {
            "id": rule_id,
            "title": _websafe_rule_text(
                rule_id, "question", rule.get("question", rule.get("title", rule_id))
            ),
            "section": rule.get("section", ""),
            "input_label": _input_label(rule),
            "severity_code": (rule.get("severity", "") or "").lower(),
            "severity_label": _severity_label(rule.get("severity", "")),
            "checkability": rule.get("checkability") or "",
            "checkability_label": _checkability_label(rule.get("checkability")),
            "what_it_checks": _websafe_rule_text(
                rule_id, "rule_definition", rule.get("rule_definition", "")
            ),
            "how_to_correct": _websafe_rule_text(
                rule_id, "remediation", rule.get("remediation", "")
            ),
            "is_experimental": is_experimental,
            "is_active_default": is_active_default,
            "implementation_status": rule.get("implementation_status", ""),
        }

        classification = _classify_rule(rule)
        if classification == "student":
            if rule_id in _P018_DELEGATED_PARENT_RULE_IDS:
                if rule_id == "P018":
                    student_rules.extend(
                        _atomic_public_card_dict(enriched, spec)
                        for spec in _P018_PUBLIC_CARD_SPECS
                    )
                elif rule_id == "P024":
                    student_rules.extend(
                        _atomic_public_card_dict(enriched, spec)
                        for spec in _P024_REMAINING_PUBLIC_CARD_SPECS
                    )
                elif rule_id == "P032":
                    student_rules.extend(
                        _atomic_public_card_dict(enriched, spec)
                        for spec in _P032_REMAINING_PUBLIC_CARD_SPECS
                    )
                continue
            if rule_id == "P026":
                # Public rules page splits P026 into two student-facing cards:
                # P026A (font family) and P026B (font size). Findings remain P026.
                p026a = dict(enriched)
                p026a["id"] = "P026A"
                p026a["title"] = (
                    "Does body text use an accepted font family "
                    "(Times New Roman, Arial, Computer Modern, or Latin Modern)?"
                )
                p026a["what_it_checks"] = (
                    "Checks ordinary body-text spans for font family outside accepted "
                    "options: Times New Roman, Arial, Computer Modern, Latin Modern, "
                    "and common near-equivalent serifs."
                )
                p026a["how_to_correct"] = (
                    "Set the source-document body font family to Times New Roman or Arial, "
                    "or use Computer Modern/Latin Modern in approved thesis templates."
                )

                p026b = dict(enriched)
                p026b["id"] = "P026B"
                p026b["title"] = (
                    "Does body text use 12pt font size "
                    "(11.0-13.0pt tolerance)?"
                )
                p026b["what_it_checks"] = (
                    "Checks ordinary body-text spans for font size outside the accepted "
                    "11.0-13.0pt range around a 12pt requirement."
                )
                p026b["how_to_correct"] = (
                    "Set body text to 12pt throughout the document."
                )

                student_rules.extend([p026a, p026b])
            elif rule_id == "P015":
                # Public rules page splits P015 into two student-facing cards:
                # P015A (first paragraph after heading flush-left) and P015B
                # (later body paragraphs indented). Findings remain P015.
                p015a = dict(enriched)
                p015a["id"] = "P015A"
                p015a["title"] = (
                    "Is the first paragraph after a level 1, 2, 3, or 4 heading "
                    "not indented?"
                )
                p015a["what_it_checks"] = p015a["title"]
                p015a["how_to_correct"] = (
                    "Remove the first-line indent from the first paragraph after the heading."
                )

                p015b = dict(enriched)
                p015b["id"] = "P015B"
                p015b["title"] = (
                    "Are all body paragraphs indented, excluding the first paragraph "
                    "after a heading?"
                )
                p015b["what_it_checks"] = p015b["title"]
                p015b["how_to_correct"] = (
                    "Apply a first-line indent to each body paragraph after the first "
                    "paragraph in the section."
                )

                student_rules.extend([p015a, p015b])
            else:
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
    if "experimental" in rule_type:
        return "Experimental / opt-in — not enabled in this website's PDF audit"
    if "infrastructure-only" in notes:
        return "Infrastructure scaffold — no standalone findings in this phase"
    if "reporting-only" in notes:
        return "Reporting-only refinement — no new raw findings"
    if phase == "docx_comments":
        return "DOCX comment extraction infrastructure"
    return "Technical entry"


@lru_cache(maxsize=1)
def _public_rule_lookup() -> dict[str, dict[str, Any]]:
    """Return public PDF rules keyed by rule ID."""
    catalog = _build_rule_catalog()
    rules = catalog.get("student_rules", [])
    if not isinstance(rules, list):
        return {}
    return {
        str(rule.get("id", "")): rule
        for rule in rules
        if isinstance(rule, dict) and str(rule.get("id", "")).strip()
    }


def _coerce_page_number(raw_page: Any) -> int | None:
    """Convert a stored page value to an integer when possible."""
    if raw_page is None or isinstance(raw_page, bool):
        return None
    try:
        return int(raw_page)
    except (TypeError, ValueError):
        return None


def _student_location_text(finding: dict[str, Any]) -> str:
    """Return a simple location label for a student-facing example card."""
    page = _coerce_page_number(finding.get("page"))
    location_label = str(finding.get("location_label", "")).strip()
    if page is not None:
        if not location_label or location_label == str(page):
            return f"Page {page}"
        if location_label.lower().startswith("page "):
            return location_label
        return f"Page {page} - {location_label}"
    if location_label:
        return location_label
    return "Document-wide overview"


def _short_rule_explanation(rule: dict[str, Any] | None) -> str:
    """Return a compact student-facing explanation for a rule group."""
    if not isinstance(rule, dict):
        return "These examples show all findings for this formatting check."

    text = " ".join(str(rule.get("what_it_checks", "")).split()).strip()
    if not text:
        return "These examples show all findings for this formatting check."

    sentence_parts = re.split(r"(?<=[.!?])\s+", text, maxsplit=1)
    first_sentence = sentence_parts[0].strip()
    if first_sentence and len(first_sentence) <= 220:
        return first_sentence
    return text[:217].rstrip() + "..."


def _available_job_categories(job: JobState) -> list[str]:
    """Return distinct finding categories available for a completed job."""
    categories = {
        str(finding.get("category", "")).strip()
        for finding in job.findings
        if str(finding.get("category", "")).strip()
    }
    return sorted(categories)


def _distinct_issue_types(findings: list[dict[str, Any]]) -> list[str]:
    """Return the distinct, non-empty issue_type values among *findings*."""
    return sorted(
        {
            str(finding.get("issue_type", "")).strip()
            for finding in findings
            if str(finding.get("issue_type", "")).strip()
        }
    )


def _single_issue_type_override(
    matching_findings: list[dict[str, Any]],
    *,
    curated_only: bool = False,
) -> tuple[str, str] | None:
    """Return a precise (title, explanation) when all findings share one issue type.

    A category page label is always a broad umbrella (e.g. "Front matter /
    appendix structure" covers ordering, dedication formatting, and appendix
    letter labeling), so it should switch to an issue-specific title whenever
    exactly one issue type is present, whether or not that title is hand
    curated. A rule page's canonical title is usually already specific to one
    check, so *curated_only* restricts the override there to hand-curated
    titles only — this avoids replacing an already-precise rule title (e.g.
    "Page-number candidates detected for verification") with a less specific,
    auto-generated one. Returns None when zero or more than one distinct
    issue type is present, or (if curated_only) no curated title exists.
    """
    issue_types = _distinct_issue_types(matching_findings)
    if len(issue_types) != 1:
        return None
    issue_type = issue_types[0]
    rule_id = next(
        (
            str(finding.get("rule_id", "")).strip()
            for finding in matching_findings
            if str(finding.get("issue_type", "")).strip() == issue_type
        ),
        "",
    )
    if curated_only and not has_curated_issue_type_title(rule_id, issue_type):
        return None
    return issue_type_title(rule_id, issue_type), explain_issue_type(rule_id, issue_type)


_MULTI_ISSUE_TYPE_NOTE = (
    "This page includes several different issue types under one heading. Each "
    "example below identifies its own exact issue type and explains what was "
    "observed, what NJIT expects, and what to fix."
)


def _with_multi_issue_type_note(
    explanation: str, matching_findings: list[dict[str, Any]]
) -> str:
    """Append a note clarifying that a broad group page mixes several issue types."""
    if len(_distinct_issue_types(matching_findings)) > 1:
        return f"{explanation} {_MULTI_ISSUE_TYPE_NOTE}"
    return explanation


def _problem_group_examples(
    job: JobState,
    *,
    findings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build template-ready example cards for a problem-group page.

    Trusts each finding's canonical ``has_highlight`` / ``action_kind`` /
    ``action_label`` fields (computed once in report_view.py and stored in
    job.findings) rather than recomputing bbox eligibility here, so every
    drill-down page applies the exact same PDF-action policy as the main
    results page.
    """
    rule_lookup = _public_rule_lookup()
    problem_number_by_identity = {
        id(finding): index
        for index, finding in enumerate(job.findings, start=1)
    }
    examples: list[dict[str, Any]] = []
    for finding in findings:
        rule_id = str(finding.get("rule_id", "")).strip()
        issue_type = str(finding.get("issue_type", "")).strip()
        page = _coerce_page_number(finding.get("page"))
        rule = rule_lookup.get(rule_id, {})
        has_highlight = bool(finding.get("has_highlight", False))
        action_kind = str(finding.get("action_kind", "")).strip() or "explanation"
        action_label = str(finding.get("action_label", "")).strip() or "Read explanation"
        no_highlight_reason = str(finding.get("no_highlight_reason", "")).strip()
        detailed_explanation = str(finding.get("detailed_explanation", "")).strip()
        issue_type_label = str(finding.get("issue_type_label", "")).strip()
        issue_type_explanation = str(finding.get("issue_type_explanation", "")).strip()
        problem_number_raw = finding.get("problem_number")
        if isinstance(problem_number_raw, int) and problem_number_raw > 0:
            problem_number = problem_number_raw
        else:
            problem_number = problem_number_by_identity.get(id(finding), 0)
        pdf_page_url = _pdf_action_url(
            job.job_id,
            page=page,
            action_kind=action_kind,
            rule_id=rule_id,
            issue_type=issue_type,
        )
        problem_anchor = (
            str(finding.get("problem_anchor", "")).strip()
            or (f"problem-{problem_number}" if problem_number > 0 else "")
        )
        examples.append(
            {
                "problem_number": problem_number,
                "problem_anchor": problem_anchor,
                "rule_id": rule_id,
                "rule_title": str(rule.get("title", "")).strip(),
                "category": str(finding.get("category", "")).strip(),
                "issue_type": issue_type,
                "polished_comment": str(finding.get("polished_comment", "")).strip(),
                "suggested_fix": str(finding.get("suggested_fix", "")).strip(),
                "location_text": _student_location_text(finding),
                "page": page,
                "pdf_page_url": pdf_page_url,
                "highlighted": has_highlight,
                "action_kind": action_kind,
                "action_label": action_label,
                "no_highlight_reason": no_highlight_reason,
                "detailed_explanation": detailed_explanation,
                "issue_type_label": issue_type_label,
                "issue_type_explanation": issue_type_explanation,
            }
        )

    return sorted(
        examples,
        key=lambda example: (
            example["page"] if example["page"] is not None else 10**9,
            example["rule_id"],
            example["location_text"],
            example["polished_comment"],
        ),
    )


_GROUP_KIND_KICKERS: dict[str, str] = {
    "issue_type": "Examples of this exact problem",
    "rule": "Examples for this rule",
    "category": "Problems in this category",
}
_GROUP_KIND_HEADINGS: dict[str, str] = {
    "issue_type": "Examples of this exact problem",
    "rule": "All examples for this rule",
    "category": "All examples in this category",
}


def _group_pattern_note(examples: list[dict[str, Any]], pages: list[int]) -> str:
    """Explain why a problem-group page lists many examples, when safe.

    Mirrors the main results page's high-volume framing: only fires when every
    example on this drill-down page shares the same (rule_id, issue_type) pair,
    so the note never claims a single pattern for a page that actually mixes
    several distinct issues.
    """
    if len(examples) <= 1:
        return ""
    rule_ids = {str(example.get("rule_id", "")).strip() for example in examples}
    issue_types = {str(example.get("issue_type", "")).strip() for example in examples}
    if len(rule_ids) != 1 or len(issue_types) != 1:
        return ""
    rule_id = next(iter(rule_ids))
    issue_type = next(iter(issue_types))
    if not rule_id or not issue_type:
        return ""
    return _high_volume_pattern_note(
        rule_id,
        issue_type,
        len(examples),
        "Pages",
        compact_page_list(pages) if pages else "",
    )


def _problem_group_context(
    *,
    job: JobState,
    group_title: str,
    group_kind: str,
    group_key: str,
    group_explanation: str,
    examples: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build template context for a category-, rule-, or issue-type-specific problem page.

    ``group_kind`` controls how broad the page's scope actually is — "rule" and
    "category" pages can span multiple distinct issue types, so their kicker/heading
    text must not claim to show the exact same problem (only "issue_type" pages do).
    """
    pages = sorted(
        {
            page
            for page in (_coerce_page_number(example.get("page")) for example in examples)
            if page is not None
        }
    )
    hero_action_kind = "none"
    hero_action_label = ""
    hero_action_url = ""
    for example in examples:
        if example.get("action_kind") == "highlight" and example.get("pdf_page_url"):
            hero_action_kind = "highlight"
            hero_action_label = str(example.get("action_label", "")).strip()
            hero_action_url = str(example["pdf_page_url"])
            break
    if hero_action_kind == "none":
        for example in examples:
            if example.get("action_kind") == "original_page" and example.get("pdf_page_url"):
                hero_action_kind = "original_page"
                hero_action_label = str(example.get("action_label", "")).strip()
                hero_action_url = str(example["pdf_page_url"])
                break
    if hero_action_kind == "none" and examples:
        hero_action_kind = "explanation"
        hero_action_label = "Read explanation"
        hero_action_url = "#examples"
    return {
        "job_id": job.job_id,
        "file_name": job.file_name,
        "audit_page_url": f"/audits/{job.job_id}",
        "group_title": group_title,
        "group_kind": group_kind,
        "group_key": group_key,
        "group_explanation": group_explanation,
        "pattern_note": _group_pattern_note(examples, pages),
        "group_kicker": _GROUP_KIND_KICKERS.get(group_kind, "Examples of this problem"),
        "group_examples_heading": _GROUP_KIND_HEADINGS.get(group_kind, "Examples of this problem"),
        "example_count": len(examples),
        "pages_to_review": compact_page_list(pages) if pages else "",
        "examples": examples,
        "hero_action_kind": hero_action_kind,
        "hero_action_label": hero_action_label,
        "hero_action_url": hero_action_url,
    }


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




def _job_page_context(job: JobState) -> dict[str, Any]:
    """Build template context for the job results page (PDF audits only)."""
    report_view = job.report_view or {}
    pages = report_view.get("pages", []) or []
    counts_by_rule = report_view.get("counts_by_rule", {}) or {}
    counts_by_category = report_view.get("counts_by_category", {}) or {}
    category_summary = sorted(
        [{"category": cat, "count": count} for cat, count in counts_by_category.items()],
        key=lambda r: (-r["count"], r["category"]),
    )

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
        "problems_found_count": job.fail_count + job.warn_count,
        "pages_affected": len(pages),
        "rules_flagged": len(counts_by_rule),
        "grouped_problem_count": len(report_view.get("grouped_problems", []) or []),
        "filter_rules": filter_rules,
        "filter_severities": filter_severities,
        "filter_categories": filter_categories,
        "filter_pages": filter_pages,
        "text_layer_quality": job.text_layer_quality,
        "category_summary": category_summary,
        "inventory_finding_count": len(report_view.get("inventory_findings", []) or []),
    }


def _index_error(request: Request, error: str, status_code: int = 400) -> HTMLResponse:
    return _render(
        request,
        "index.html",
        {"error": error, "max_upload_mb": MAX_UPLOAD_MB, "builtin_samples": list_builtin_samples()},
        status_code=status_code,
    )


def _index_notice(request: Request, notice: str, status_code: int = 404) -> HTMLResponse:
    return _render(
        request,
        "index.html",
        {
            "notice": notice,
            "max_upload_mb": MAX_UPLOAD_MB,
            "builtin_samples": list_builtin_samples(),
        },
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

    pdf_page_sizes: list[tuple[float, float]] = []
    if result.audit_type == "pdf":
        try:
            pdf_page_sizes = get_pdf_page_sizes(upload_path)
        except Exception:  # noqa: BLE001
            pdf_page_sizes = []
    job.pdf_page_sizes = pdf_page_sizes
    job.pdf_page_count = len(pdf_page_sizes)

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

    view = build_report_view(web_payload, pdf_page_sizes=pdf_page_sizes)
    view_dict = report_view_to_dict(view)
    raw_findings = web_payload.get("findings", [])
    if not isinstance(raw_findings, list):
        raw_findings = []

    serialized = []
    for index, fv in enumerate(view_dict.get("findings", [])):
        raw_details: dict[str, Any] = {}
        if index < len(raw_findings) and isinstance(raw_findings[index], dict):
            details = raw_findings[index].get("details", {})
            if isinstance(details, dict):
                raw_details = {str(k): v for k, v in details.items()}
        public_ref = _public_rule_reference_id(
            str(fv.get("rule_id", "")),
            issue_type=str(fv.get("issue_type", "")),
            source_q_rule_id=str(raw_details.get("source_q_rule_id", "")),
            details=raw_details,
        )
        serialized.append(
            {
                "rule_id": fv["rule_id"],
                "public_rule_reference_id": public_ref,
                "severity": fv["severity"],
            "page": fv["page"],
            "problem_number": fv.get("problem_number", 0),
            "problem_anchor": fv.get("problem_anchor", ""),
            "issue_type": fv["issue_type"],
            "category": fv["category"],
            "polished_comment": fv["polished_comment"],
            "suggested_fix": fv.get("suggested_fix", ""),
            "triage_tier": fv.get("triage_tier", ""),
            "confidence": fv.get("confidence", ""),
            "source_file": fv.get("source_file", ""),
            "source_line": fv.get("source_line", ""),
            "location_label": fv.get("location_label", ""),
            "bbox": fv.get("bbox"),
            "action_kind": fv.get("action_kind", ""),
            "action_label": fv.get("action_label", ""),
            "has_highlight": fv.get("has_highlight", False),
            "no_highlight_reason": fv.get("no_highlight_reason", ""),
            "detailed_explanation": fv.get("detailed_explanation", ""),
            "issue_type_label": fv.get("issue_type_label", ""),
                "issue_type_explanation": fv.get("issue_type_explanation", ""),
            }
        )

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


@app.get("/healthz")
async def healthz() -> JSONResponse:
    """Lightweight liveness probe: no job lookup, no filesystem scan, no I/O."""
    return JSONResponse({"ok": True, "app": "njit-thesis-auditor", "status": "healthy"})


@app.get("/version")
async def version() -> JSONResponse:
    """Safe deployment metadata: no local paths, env vars, or upload content."""
    return JSONResponse(
        {
            "app": "njit-thesis-auditor",
            "commit": _GIT_COMMIT,
            "branch": _GIT_BRANCH,
            "process_start_time": _PROCESS_START_TIME.isoformat(),
            "python_version": platform.python_version(),
            "environment": ENVIRONMENT_NAME,
        }
    )


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


@app.get("/audits/sample", response_model=None)
async def get_audits_sample_guard() -> RedirectResponse:
    """Redirect accidental GET /audits/sample to the upload page.

    Same route-collision class as get_audits_url_guard above: without this guard,
    GET /audits/sample would be matched by the parameterised /audits/{job_id} route
    with job_id="sample", producing a confusing "job not found" error message.
    """
    return RedirectResponse(url="/", status_code=302)


@app.get("/audits/{job_id}", response_class=HTMLResponse)
async def job_page(request: Request, job_id: str) -> HTMLResponse:
    cleanup_expired_jobs()
    job = _get_job(job_id)
    if job is None:
        return _index_notice(request, _expired_job_notice(), status_code=404)

    return _render(request, "job.html", _job_page_context(job))


@app.get("/audits/{job_id}/problems/category/{category_slug}", response_class=HTMLResponse)
async def category_problem_page(
    request: Request, job_id: str, category_slug: str
) -> HTMLResponse:
    cleanup_expired_jobs()
    job = _get_job(job_id)
    if job is None:
        return _index_notice(request, _expired_job_notice(), status_code=404)
    if job.state != "complete" or job.audit_type != "pdf":
        return _index_error(
            request,
            "This problem group is not available for that audit.",
            status_code=404,
        )

    matched_category = next(
        (
            category
            for category in _available_job_categories(job)
            if _category_slug(category) == category_slug
        ),
        "",
    )
    if not matched_category:
        return _index_error(
            request,
            "That problem group was not found for this audit.",
            status_code=404,
        )

    matching_findings = [
        finding
        for finding in job.findings
        if str(finding.get("category", "")).strip() == matched_category
    ]
    if not matching_findings:
        return _index_error(
            request,
            "That problem group was not found for this audit.",
            status_code=404,
        )

    override = _single_issue_type_override(matching_findings)
    if override is not None:
        group_title, group_explanation = override
    else:
        group_title = _humanize_cat(matched_category)
        group_explanation = _with_multi_issue_type_note(
            _category_explanation(matched_category), matching_findings
        )
    context = _problem_group_context(
        job=job,
        group_title=group_title,
        group_kind="category",
        group_key=matched_category,
        group_explanation=group_explanation,
        examples=_problem_group_examples(job, findings=matching_findings),
    )
    return _render(request, "problem_group.html", context)


@app.get("/audits/{job_id}/problems/rule/{rule_id}", response_class=HTMLResponse)
async def rule_problem_page(request: Request, job_id: str, rule_id: str) -> HTMLResponse:
    cleanup_expired_jobs()
    job = _get_job(job_id)
    if job is None:
        return _index_notice(request, _expired_job_notice(), status_code=404)
    if job.state != "complete" or job.audit_type != "pdf":
        return _index_error(
            request,
            "This problem group is not available for that audit.",
            status_code=404,
        )

    matching_findings = [
        finding for finding in job.findings if str(finding.get("rule_id", "")).strip() == rule_id
    ]
    if not matching_findings:
        return _index_error(
            request,
            "That problem group was not found for this audit.",
            status_code=404,
        )

    rule = _public_rule_lookup().get(rule_id, {})
    override = _single_issue_type_override(matching_findings, curated_only=True)
    if override is not None:
        group_title, group_explanation = override
    else:
        group_title = str(rule.get("title", "")).strip() or f"Rule {rule_id}"
        group_explanation = _with_multi_issue_type_note(
            _short_rule_explanation(rule), matching_findings
        )
    context = _problem_group_context(
        job=job,
        group_title=group_title,
        group_kind="rule",
        group_key=rule_id,
        group_explanation=group_explanation,
        examples=_problem_group_examples(job, findings=matching_findings),
    )
    return _render(request, "problem_group.html", context)


@app.get(
    "/audits/{job_id}/problems/rule/{rule_id}/issue-type/{issue_type_slug}",
    response_class=HTMLResponse,
)
async def issue_type_problem_page(
    request: Request, job_id: str, rule_id: str, issue_type_slug: str
) -> HTMLResponse:
    """Show all findings for a specific (rule_id, issue_type) combination."""
    cleanup_expired_jobs()
    job = _get_job(job_id)
    if job is None:
        return _index_notice(request, _expired_job_notice(), status_code=404)
    if job.state != "complete" or job.audit_type != "pdf":
        return _index_error(
            request,
            "This problem group is not available for that audit.",
            status_code=404,
        )

    issue_type = _issue_type_from_slug(issue_type_slug)
    matching_findings = [
        f
        for f in job.findings
        if str(f.get("rule_id", "")).strip() == rule_id
        and str(f.get("issue_type", "")).strip() == issue_type
    ]
    if not matching_findings:
        return _index_error(
            request,
            "That problem group was not found for this audit.",
            status_code=404,
        )

    group_title = issue_type_title(rule_id, issue_type)
    group_explanation = explain_issue_type(rule_id, issue_type)
    context = _problem_group_context(
        job=job,
        group_title=group_title,
        group_kind="issue_type",
        group_key=issue_type,
        group_explanation=group_explanation,
        examples=_problem_group_examples(job, findings=matching_findings),
    )
    return _render(request, "problem_group.html", context)


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


def _safe_pdf_disposition_filename(file_name: str) -> str:
    """Return a Content-Disposition-safe filename for an inline PDF response."""
    name = (file_name or "document.pdf").strip()
    for unsafe in ('"', "\\", "\n", "\r"):
        name = name.replace(unsafe, "_")
    return name or "document.pdf"


@app.get("/audits/{job_id}/pdf", response_model=None)
async def serve_job_pdf(job_id: str) -> FileResponse | JSONResponse:
    """Serve the uploaded PDF inline (not as a forced download) for the embedded viewer."""
    job = _get_job(job_id)
    if job is None or job.state != "complete":
        return JSONResponse({"error": "not available"}, status_code=404)
    if job.audit_type != "pdf":
        return JSONResponse({"error": "not a PDF audit"}, status_code=404)
    pdf_path = _job_pdf_path(_job_dir(job_id))
    if not _is_under_runtime(pdf_path) or not pdf_path.exists():
        return JSONResponse({"error": "PDF not found"}, status_code=404)
    safe_filename = _safe_pdf_disposition_filename(job.file_name)
    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{safe_filename}"'},
    )


def _coerce_bbox(raw: Any) -> tuple[float, float, float, float] | None:
    """Coerce a stored finding bbox value into a 4-tuple of floats, if drawable."""
    if not isinstance(raw, (list, tuple)) or len(raw) != 4:
        return None
    try:
        box = (float(raw[0]), float(raw[1]), float(raw[2]), float(raw[3]))
    except (TypeError, ValueError):
        return None
    return box if is_drawable_bbox(box) else None


def _bbox_from_finding_entry(
    finding: Mapping[str, Any],
) -> tuple[float, float, float, float] | None:
    """Return a drawable bbox from a serialized finding's bbox or details rect."""
    bbox = _coerce_bbox(finding.get("bbox"))
    if bbox is not None:
        return bbox
    details = finding.get("details", {})
    if not isinstance(details, Mapping):
        return None
    for key in ("bbox", "rect"):
        raw = str(details.get(key, "")).strip()
        if not raw:
            continue
        parts = [part.strip() for part in raw.split(",")]
        if len(parts) != 4:
            continue
        try:
            box = (float(parts[0]), float(parts[1]), float(parts[2]), float(parts[3]))
        except ValueError:
            continue
        if is_drawable_bbox(box):
            return box
    return None


def _finding_issue_type(finding: Mapping[str, Any]) -> str:
    issue_type = str(finding.get("issue_type", "")).strip()
    if issue_type:
        return issue_type
    details = finding.get("details", {})
    if isinstance(details, Mapping):
        return str(details.get("issue_type", "")).strip()
    return ""


def _report_json_findings_for_highlight(job: JobState) -> list[dict[str, Any]]:
    """Load raw audit findings for highlight box extraction."""
    jdir = _job_dir(job.job_id)
    json_path = jdir / "report.json"
    if not json_path.exists():
        return job.findings
    try:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return job.findings
    raw_findings = payload.get("findings", [])
    if not isinstance(raw_findings, list):
        return job.findings
    enriched: list[dict[str, Any]] = []
    for finding in raw_findings:
        if not isinstance(finding, Mapping):
            continue
        entry = dict(finding)
        bbox = _bbox_from_finding_entry(entry)
        if bbox is not None:
            entry["bbox"] = bbox
        entry["issue_type"] = _finding_issue_type(entry)
        enriched.append(entry)
    return enriched or job.findings


def _matching_findings_for_highlight(
    job: JobState,
    *,
    page: int | None,
    rule_id: str,
    issue_type: str,
    finding_index: int | None,
) -> list[dict[str, Any]]:
    """Return job findings matching the highlight request's filters."""
    source_findings = _report_json_findings_for_highlight(job)
    if finding_index is not None and 0 <= finding_index < len(job.findings):
        visible = job.findings[finding_index]
        page_no = _coerce_page_number(visible.get("page"))
        rule = str(visible.get("rule_id", "")).strip()
        issue = str(visible.get("issue_type", "")).strip()
        matches = source_findings
        if page_no is not None:
            matches = [f for f in matches if _coerce_page_number(f.get("page")) == page_no]
        if rule:
            matches = [f for f in matches if str(f.get("rule_id", "")) == rule]
        if issue:
            matches = [f for f in matches if _finding_issue_type(f) == issue]
        return matches

    matches = source_findings
    if page is not None:
        matches = [f for f in matches if _coerce_page_number(f.get("page")) == page]
    if rule_id:
        matches = [f for f in matches if str(f.get("rule_id", "")) == rule_id]
    if issue_type:
        matches = [f for f in matches if _finding_issue_type(f) == issue_type]
    return matches


def _highlight_boxes_by_page(
    findings: list[dict[str, Any]],
) -> dict[int, list[tuple[float, float, float, float]]]:
    """Group parsed bounding boxes by 1-based page number across matched findings."""
    boxes_by_page: dict[int, list[tuple[float, float, float, float]]] = {}
    for finding in findings:
        page = _coerce_page_number(finding.get("page"))
        if page is None:
            continue
        details_raw = finding.get("details", {})
        details = (
            {str(k): str(v) for k, v in details_raw.items()}
            if isinstance(details_raw, Mapping)
            else {}
        )
        rule_id = str(finding.get("rule_id", ""))
        issue_type = _finding_issue_type(finding)
        boxes = parse_highlight_bboxes_from_details(
            details,
            rule_id=rule_id,
            issue_type=issue_type,
        )
        if not boxes:
            bbox = _bbox_from_finding_entry(finding)
            if bbox is not None:
                boxes = [bbox]
        for bbox in boxes:
            boxes_by_page.setdefault(page, []).append(bbox)
    return boxes_by_page


def _highlight_cache_path(
    jdir: Path,
    *,
    page: int | None,
    rule_id: str,
    issue_type: str,
    finding_index: int | None,
) -> Path:
    """Return a stable, filesystem-safe cache path for a highlighted PDF copy."""
    key = f"{page}|{rule_id}|{issue_type}|{finding_index}"
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]
    return jdir / f"highlighted-{digest}.pdf"


def _highlight_page_cache_path(
    jdir: Path,
    *,
    page: int | None,
    rule_id: str,
    issue_type: str,
    finding_index: int | None,
) -> Path:
    """Return a stable cache path for a one-page highlighted PDF artifact."""
    key = f"page|{page}|{rule_id}|{issue_type}|{finding_index}"
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]
    return jdir / f"highlighted-page-{digest}.pdf"


@app.get("/audits/{job_id}/pdf/highlighted", response_model=None)
async def serve_job_pdf_highlighted(
    job_id: str,
    page: int | None = None,
    rule_id: str = "",
    issue_type: str = "",
    finding_index: int | None = None,
) -> FileResponse | JSONResponse:
    """Serve the uploaded PDF inline with a highlight for a specific finding.

    Falls back to the plain (unhighlighted) PDF when the matched finding(s)
    carry no bounding-box coordinates. The original uploaded PDF is never
    modified -- highlights are always drawn on a separate generated copy.
    """
    job = _get_job(job_id)
    if job is None or job.state != "complete":
        return JSONResponse({"error": "not available"}, status_code=404)
    if job.audit_type != "pdf":
        return JSONResponse({"error": "not a PDF audit"}, status_code=404)

    jdir = _job_dir(job_id)
    pdf_path = _job_pdf_path(jdir)
    if not _is_under_runtime(pdf_path) or not pdf_path.exists():
        return JSONResponse({"error": "PDF not found"}, status_code=404)

    headers = {
        "Content-Disposition": f'inline; filename="{_safe_pdf_disposition_filename(job.file_name)}"'
    }
    plain_response = FileResponse(
        path=str(pdf_path), media_type="application/pdf", headers=headers
    )

    # Highlight generation is a best-effort enhancement layered on top of the
    # always-available plain PDF: any unexpected failure below (bad query
    # params, an unanticipated PDF-geometry edge case, a filesystem race,
    # etc.) must fall back to the plain inline PDF rather than ever surface
    # as a 500 to the browser.
    try:
        matches = _matching_findings_for_highlight(
            job,
            page=page,
            rule_id=rule_id.strip(),
            issue_type=issue_type.strip(),
            finding_index=finding_index,
        )
        boxes_by_page = _highlight_boxes_by_page(matches)
        if not boxes_by_page:
            return plain_response

        cache_path = _highlight_cache_path(
            jdir, page=page, rule_id=rule_id, issue_type=issue_type, finding_index=finding_index
        )
        if not _is_under_runtime(cache_path):
            return plain_response

        if not cache_path.exists():
            result = build_highlighted_pdf(pdf_path, cache_path, boxes_by_page)
            if not result.has_highlight:
                _logger.warning(
                    "Highlight request for job %s matched %d finding(s) but drew no "
                    "visible annotation (skipped=%d); falling back to plain PDF.",
                    job_id,
                    len(matches),
                    result.skipped_count,
                )
        if not cache_path.exists():
            return plain_response

        return FileResponse(path=str(cache_path), media_type="application/pdf", headers=headers)
    except Exception:
        _logger.warning(
            "Highlighted PDF generation failed for job %s; falling back to plain PDF.",
            job_id,
            exc_info=True,
        )
        return plain_response


@app.get("/audits/{job_id}/highlighted-page.pdf", response_model=None)
async def serve_job_highlighted_page_pdf(
    job_id: str,
    page: int | None = None,
    rule_id: str = "",
    issue_type: str = "",
    finding_index: int | None = None,
) -> FileResponse | JSONResponse:
    """Serve a one-page highlighted PDF for per-finding report links."""
    job = _get_job(job_id)
    if job is None or job.state != "complete":
        return JSONResponse({"error": "not available"}, status_code=404)
    if job.audit_type != "pdf":
        return JSONResponse({"error": "not a PDF audit"}, status_code=404)
    if page is None:
        return JSONResponse({"error": "page required"}, status_code=400)

    jdir = _job_dir(job_id)
    pdf_path = _job_pdf_path(jdir)
    if not _is_under_runtime(pdf_path) or not pdf_path.exists():
        return JSONResponse({"error": "PDF not found"}, status_code=404)

    headers = {
        "Content-Disposition": 'inline; filename="highlighted-page.pdf"'
    }

    try:
        matches = _matching_findings_for_highlight(
            job,
            page=page,
            rule_id=rule_id.strip(),
            issue_type=issue_type.strip(),
            finding_index=finding_index,
        )
        boxes_by_page = _highlight_boxes_by_page(matches)
        page_boxes = boxes_by_page.get(page) or []

        cache_path = _highlight_page_cache_path(
            jdir,
            page=page,
            rule_id=rule_id,
            issue_type=issue_type,
            finding_index=finding_index,
        )
        if not _is_under_runtime(cache_path):
            return JSONResponse({"error": "invalid cache path"}, status_code=500)

        if not cache_path.exists():
            if page_boxes:
                result = build_highlighted_single_page_pdf(
                    pdf_path,
                    cache_path,
                    source_page_number=page,
                    boxes=page_boxes,
                )
                if not result.has_highlight:
                    _logger.warning(
                        "Page-focused highlight for job %s page=%s matched %d finding(s) "
                        "but drew no visible annotation (skipped=%d); serving single page only.",
                        job_id,
                        page,
                        len(matches),
                        result.skipped_count,
                    )
            if not cache_path.exists() and not build_single_page_pdf(
                pdf_path, cache_path, source_page_number=page
            ):
                return JSONResponse({"error": "page not available"}, status_code=404)

        return FileResponse(path=str(cache_path), media_type="application/pdf", headers=headers)
    except Exception:
        _logger.warning(
            "Page-focused highlighted PDF generation failed for job %s; "
            "attempting single-page extract.",
            job_id,
            exc_info=True,
        )
        cache_path = _highlight_page_cache_path(
            jdir,
            page=page,
            rule_id=rule_id,
            issue_type=issue_type,
            finding_index=finding_index,
        )
        if _is_under_runtime(cache_path) and build_single_page_pdf(
            pdf_path, cache_path, source_page_number=page
        ):
            return FileResponse(path=str(cache_path), media_type="application/pdf", headers=headers)
        return JSONResponse({"error": "highlight unavailable"}, status_code=500)


@app.get("/help", response_class=HTMLResponse)
async def help_page(request: Request) -> HTMLResponse:
    return _render(request, "help.html", {})


@app.get("/rules", response_class=HTMLResponse)
async def rules_page(request: Request) -> HTMLResponse:
    catalog = _build_rule_catalog()
    return _render(request, "rules.html", catalog)
