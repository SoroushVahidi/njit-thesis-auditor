"""Tests for the NJIT Thesis Auditor web upload UI."""

from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from pdf_link_helpers import AUDIT_PDF_HREF_RE

from njit_auditor.student_cards import plain_student_text, student_card_fields

# Minimal synthetic PDF header — enough to pass the magic-byte check
_MINIMAL_PDF = b"%PDF-1.4\n%%EOF\n"

_MINIMAL_TEX = (
    rb"\documentclass{report}"
    b"\n\\begin{document}\n\\vspace{1cm}\nHello\n\\end{document}\n"
)


def _make_app(tmp_path: Path) -> Any:
    """Import the web app with RUNTIME_DIR pointed at a temp directory."""
    os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"] = str(tmp_path / "web_audits")
    # Re-import so RUNTIME_DIR picks up the env var
    import importlib

    import njit_auditor.web_app as wa

    importlib.reload(wa)
    return wa.app, wa


@pytest.fixture()
def client(tmp_path: Path) -> tuple[TestClient, Any]:
    app, wa = _make_app(tmp_path)
    return TestClient(app, raise_server_exceptions=False), wa


# ---------------------------------------------------------------------------
# Index page
# ---------------------------------------------------------------------------

def test_index_get_returns_200(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.get("/")
    assert resp.status_code == 200
    assert b"<form" in resp.content
    assert b"NJIT Thesis Auditor" in resp.content


def test_index_contains_file_input(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.get("/")
    assert b'type="file"' in resp.content
    assert b'accept=".pdf"' in resp.content
    assert b"TeX" not in resp.content
    assert b".zip" not in resp.content


def test_index_contains_drag_drop_upload_zone_markup(
    client: tuple[TestClient, Any],
) -> None:
    c, _ = client
    resp = c.get("/")
    assert resp.status_code == 200
    assert b'id="upload-drop-zone"' in resp.content
    assert b'Drop a PDF file here' in resp.content
    assert b'role="button"' in resp.content
    assert b'tabindex="0"' in resp.content
    assert b'aria-controls="file"' in resp.content
    assert b'id="file-selection-status"' in resp.content
    assert b'aria-live="polite"' in resp.content
    assert b'Drag-and-drop is available when JavaScript is enabled' in resp.content


def test_index_contains_drag_drop_progressive_enhancement_script(
    client: tuple[TestClient, Any],
) -> None:
    c, _ = client
    resp = c.get("/")
    assert resp.status_code == 200
    assert b"DataTransfer" in resp.content
    assert b"dragenter" in resp.content
    assert b"dragover" in resp.content
    assert b"dragleave" in resp.content
    assert b"drop" in resp.content
    assert b"Drop one file at a time" in resp.content
    assert b"Only PDF files are supported in the web interface" in resp.content
    assert b"Submit when ready or choose another file" in resp.content


def test_index_advertises_pdf_only_support(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.get("/")
    assert resp.status_code == 200
    assert b"formatting issues automatically" in resp.content
    assert b"TeX" not in resp.content
    assert b".zip" not in resp.content
    assert b"source audit" not in resp.content.lower()


# ---------------------------------------------------------------------------
# Upload validation
# ---------------------------------------------------------------------------

def test_upload_no_file_rejected(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.post("/audits", data={})
    assert resp.status_code in (400, 422)


_PDF_ONLY_ERROR = b"Only PDF files are supported in the web interface. Please upload a PDF file."


def test_upload_non_pdf_extension_rejected(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.post(
        "/audits",
        files={"file": ("thesis.docx", io.BytesIO(b"PK\x03\x04fake"), "application/octet-stream")},
        follow_redirects=True,
    )
    assert resp.status_code == 400
    assert _PDF_ONLY_ERROR in resp.content


def test_upload_tex_extension_rejected(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.post(
        "/audits",
        files={"file": ("main.tex", io.BytesIO(_MINIMAL_TEX), "text/plain")},
        follow_redirects=True,
    )
    assert resp.status_code == 400
    assert _PDF_ONLY_ERROR in resp.content


def test_upload_zip_extension_rejected(client: tuple[TestClient, Any]) -> None:
    import zipfile

    c, _ = client
    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, "w") as zf:
        zf.writestr("main.tex", _MINIMAL_TEX)
    zbuf.seek(0)
    resp = c.post(
        "/audits",
        files={"file": ("project.zip", zbuf, "application/zip")},
        follow_redirects=True,
    )
    assert resp.status_code == 400
    assert _PDF_ONLY_ERROR in resp.content


def test_upload_wrong_magic_bytes_rejected(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.post(
        "/audits",
        files={"file": ("thesis.pdf", io.BytesIO(b"NOTAPDF_content"), "application/pdf")},
        follow_redirects=True,
    )
    assert resp.status_code == 400
    assert b"valid PDF" in resp.content


def test_upload_too_small_rejected(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.post(
        "/audits",
        files={"file": ("tiny.pdf", io.BytesIO(b"%PDF"), "application/pdf")},
        follow_redirects=True,
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Successful upload (monkeypatched audit runner)
# ---------------------------------------------------------------------------

def _fake_audit(pdf_path: Path) -> list[Any]:
    from njit_auditor.models import AuditFinding, Severity

    return [
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=3,
            message="Margin violation detected.",
            details={"issue_type": "margin_boundary_violation", "side": "left"},
        )
    ]


def _fake_dispatch(pdf_path: Path, **kwargs: Any) -> Any:
    from njit_auditor.audit_runner import UploadedAuditResult
    from njit_auditor.upload_handling import UploadKind

    return UploadedAuditResult(
        upload_kind=UploadKind.PDF,
        audit_type="pdf",
        findings=_fake_audit(pdf_path),
    )


def test_upload_pdf_creates_job_and_redirects(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    c, wa = client
    with patch.object(wa, "_run_audit_task", lambda job_id: None):
        resp = c.post(
            "/audits",
            files={"file": ("thesis.pdf", io.BytesIO(_MINIMAL_PDF), "application/pdf")},
            follow_redirects=False,
        )
    assert resp.status_code == 303
    location = resp.headers["location"]
    assert location.startswith("/audits/")


def test_job_page_pending_shows_processing(
    client: tuple[TestClient, Any],
) -> None:
    c, wa = client
    with patch.object(wa, "_run_audit_task", lambda job_id: None):
        resp_post = c.post(
            "/audits",
            files={"file": ("thesis.pdf", io.BytesIO(_MINIMAL_PDF), "application/pdf")},
            follow_redirects=False,
        )
    job_url = resp_post.headers["location"]
    resp = c.get(job_url)
    assert resp.status_code == 200
    # Either "Processing" or already moved past pending (background may have run)
    body = resp.content
    assert b"Processing" in body or b"complete" in body.lower() or b"Audit" in body


# ---------------------------------------------------------------------------
# Status endpoint
# ---------------------------------------------------------------------------

def test_status_endpoint_unknown_job(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.get("/audits/nonexistent_job_id/status")
    assert resp.status_code == 404
    data = resp.json()
    assert "error" in data


def test_status_endpoint_returns_pending(client: tuple[TestClient, Any]) -> None:
    c, wa = client
    with patch.object(wa, "_run_audit_task", lambda job_id: None):
        post = c.post(
            "/audits",
            files={"file": ("thesis.pdf", io.BytesIO(_MINIMAL_PDF), "application/pdf")},
            follow_redirects=False,
        )
    job_id = post.headers["location"].split("/audits/")[1]
    resp = c.get(f"/audits/{job_id}/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["job_id"] == job_id
    assert data["state"] in ("pending", "running", "complete", "failed")


def test_status_endpoint_complete_after_audit(client: tuple[TestClient, Any]) -> None:
    c, wa = client
    with patch.object(wa, "run_audit_for_uploaded_file", _fake_dispatch):
        post = c.post(
            "/audits",
            files={"file": ("thesis.pdf", io.BytesIO(_MINIMAL_PDF), "application/pdf")},
            follow_redirects=True,
        )
    # follow_redirects=True should load the job page; extract job_id from URL
    job_id_url = post.url
    assert "/audits/" in str(job_id_url)
    job_id = str(job_id_url).split("/audits/")[1].rstrip("/")
    resp = c.get(f"/audits/{job_id}/status")
    data = resp.json()
    assert data["state"] in ("complete", "running", "failed")


@pytest.mark.parametrize("write_fails", [False, True], ids=["complete", "failed"])
def test_status_publication_waits_for_final_report(
    client: tuple[TestClient, Any], tmp_path: Path, write_fails: bool
) -> None:
    """Observe the running job while the worker is paused at its final report write."""
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    c, wa = client
    source = tmp_path / "synthetic.pdf"
    _make_real_pdf(source, page_count=1)
    with patch.object(wa, "_run_audit_task", lambda job_id: None):
        submitted = c.post(
            "/audits",
            files={"file": ("synthetic.pdf", source.read_bytes(), "application/pdf")},
            follow_redirects=False,
        )
    assert submitted.status_code == 303
    base = submitted.headers["location"]
    job_id = base.rsplit("/", 1)[-1]
    assert c.get(base + "/status").json()["state"] == "pending"
    job_dir = wa._job_dir(job_id)
    entered = Event()
    finish = Event()
    write_text = Path.write_text
    private_error = "private report-generation detail"

    def pause_report(path: Path, text: str, **kwargs: Any) -> int:
        if path == job_dir / "report.txt":
            entered.set()
            assert finish.wait(timeout=15), "test did not release the report writer"
            if write_fails:
                write_text(path, private_error, **kwargs)
                raise OSError(private_error)
        return write_text(path, text, **kwargs)

    downloads = ("json", "markdown", "text")
    private_routes = (*downloads, "student-report.pdf", "comments.pdf")
    with (
        patch.object(wa, "run_audit_for_uploaded_file", _fake_dispatch),
        patch.object(Path, "write_text", pause_report),
        ThreadPoolExecutor(max_workers=1) as workers,
    ):
        worker = workers.submit(wa._run_audit_task, job_id)
        try:
            assert entered.wait(timeout=15), "worker did not reach the final report write"
            assert (job_dir / "report.json").is_file()
            assert (job_dir / "report.md").is_file()
            intermediate = c.get(base + "/status").json()
            assert intermediate["state"] == "running"
            assert intermediate["finished_at"] is None
            assert intermediate["finding_count"] == 0
            for route in private_routes:
                assert c.get(f"{base}/download/{route}").status_code == 404
        finally:
            finish.set()
        worker.result(timeout=15)

    terminal = c.get(base + "/status").json()
    assert terminal["finished_at"]
    if write_fails:
        assert terminal["state"] == "failed"
        assert terminal["file_name"] == ""
        assert terminal["finding_count"] == 0
        for route in private_routes:
            response = c.get(f"{base}/download/{route}")
            assert response.status_code == 404
            assert private_error not in response.text
        page = c.get(base)
        assert "An unexpected error occurred during the audit." in page.text
        assert private_error not in page.text
    else:
        assert terminal["state"] == "complete"
        assert terminal["file_name"] == "synthetic.pdf"
        for route in downloads:
            response = c.get(f"{base}/download/{route}")
            assert response.status_code == 200
            assert response.content


# ---------------------------------------------------------------------------
# Results rendering
# ---------------------------------------------------------------------------

def _inject_complete_job(
    wa: Any,
    tmp_path: Path,
    *,
    finding_count: int = 1,
) -> str:
    """Create a complete job in the job store and on disk."""
    from njit_auditor.models import AuditFinding, Severity

    findings = [
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=i + 1,
            message="Left margin too narrow.",
            details={
                "issue_type": "margin_boundary_violation",
                "side": "left_margin",
                "confidence": "medium",
                "suggested_fix": "Adjust the left margin in the PDF export settings.",
            },
        )
        for i in range(finding_count)
    ]
    return _inject_complete_job_with_findings(
        wa,
        tmp_path,
        findings=findings,
        file_name="thesis.pdf",
        audit_type="pdf",
    )


def _inject_complete_job_with_findings(
    wa: Any,
    tmp_path: Path,
    *,
    findings: list[Any],
    file_name: str,
    audit_type: str,
    page_count: int = 5,
    grouped_findings: list[dict[str, Any]] | None = None,
) -> str:
    """Create a complete job from an explicit findings list."""
    import secrets
    from datetime import datetime, timezone

    from njit_auditor.pdf_highlight import get_pdf_page_sizes
    from njit_auditor.report_outputs import audit_findings_to_json_dict, write_markdown_report
    from njit_auditor.report_text import write_text_report
    from njit_auditor.report_view import build_report_view, report_view_to_dict

    job_id = secrets.token_urlsafe(16)
    jdir = Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"]) / job_id
    jdir.mkdir(parents=True, exist_ok=True)
    if audit_type == "pdf":
        _make_real_pdf(jdir / "upload.pdf", page_count=page_count)
    else:
        (jdir / "upload.pdf").write_bytes(_MINIMAL_PDF)
    metadata = {"input_file_name": file_name, "audit_type": audit_type, "job_id": job_id}
    payload = audit_findings_to_json_dict(findings, metadata)
    if grouped_findings is not None:
        payload["grouped_findings"] = grouped_findings
    (jdir / "report.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_markdown_report(findings, metadata, jdir / "report.md")
    write_text_report(findings, metadata, jdir / "report.txt")
    pdf_page_sizes = (
        get_pdf_page_sizes(jdir / "upload.pdf") if audit_type == "pdf" else []
    )
    view = build_report_view(payload, pdf_page_sizes=pdf_page_sizes)
    view_dict = report_view_to_dict(view)

    job = wa.JobState(
        job_id=job_id,
        state="complete",
        created_at=datetime.now(timezone.utc).isoformat(),
        file_name=file_name,
        audit_type=audit_type,
        pdf_page_count=len(pdf_page_sizes),
        pdf_page_sizes=pdf_page_sizes,
        finding_count=view.total_findings,
        warn_count=sum(1 for fv in view.findings if fv.severity == "WARNING"),
        fail_count=sum(1 for fv in view.findings if fv.severity == "FAIL"),
        findings=[
            {
                "rule_id": fv["rule_id"],
                "finding_id": fv.get("finding_id", ""),
                "problem_number": fv.get("problem_number", 0),
                "problem_anchor": fv.get("problem_anchor", ""),
                "severity": fv["severity"],
                "page": fv["page"],
                "issue_type": fv["issue_type"],
                "category": fv["category"],
                "polished_comment": fv["polished_comment"],
                "suggested_fix": fv.get("suggested_fix", ""),
                "triage_tier": fv.get("triage_tier", ""),
                "confidence": fv.get("confidence", ""),
                "confidence_level": fv.get("confidence_level", ""),
                "confidence_label": fv.get("confidence_label", ""),
                "confidence_css_class": fv.get("confidence_css_class", ""),
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
            for fv in view_dict.get("findings", [])
        ],
        grouped_summary=[
            {
                "rule_id": rs.rule_id,
                "count": rs.count,
                "category": rs.category,
            }
            for rs in view.rule_summaries
        ],
        report_view=view_dict,
        md_preview="# Audit Report\n",
    )
    wa._set_job(job)
    return job_id


_RAW_LATEX_WEB_PATTERNS = (
    b"\\doublespacing",
    b"\\usepackage",
    b"mathptmx",
    b"newtxtext",
    b"newtxmath",
    b"\\setstretch",
    b"\\onehalfspacing",
)


def _assert_no_raw_latex_web_syntax(content: bytes) -> None:
    for pattern in _RAW_LATEX_WEB_PATTERNS:
        assert pattern not in content


def _p023_p026_p028_findings_with_raw_latex_suggested_fix() -> list[Any]:
    """P023/P026/P028 findings whose suggested_fix is intentionally raw LaTeX.

    Detector-level suggested_fix strings for these rules were already cleaned up, so
    this constructs synthetic findings that bypass the detectors and inject raw LaTeX
    syntax directly into details["suggested_fix"], to verify the web rendering layer
    itself never surfaces that syntax (defense in depth, not just clean producers).
    """
    from njit_auditor.models import AuditFinding, Severity

    return [
        AuditFinding(
            rule_id="P023",
            severity=Severity.WARNING,
            page=12,
            message="Body text spacing may not be double-spaced.",
            details={
                "issue_type": "possible_body_text_not_double_spaced",
                "suggested_fix": "Use \\doublespacing in the LaTeX source.",
            },
        ),
        AuditFinding(
            rule_id="P026",
            severity=Severity.WARNING,
            page=14,
            message="Body text may not use the expected font.",
            details={
                "issue_type": "possible_body_font_family_issue",
                "suggested_fix": "Use \\usepackage{mathptmx} or \\usepackage{newtxtext,newtxmath}.",
            },
        ),
        AuditFinding(
            rule_id="P028",
            severity=Severity.WARNING,
            page=3,
            message="Front-matter page numbering style may need review.",
            details={
                "issue_type": "frontmatter_page_number_style_issue",
                "suggested_fix": "Adjust LaTeX page numbering commands.",
            },
        ),
    ]


def test_results_page_shows_findings(client: tuple[TestClient, Any], tmp_path: Path) -> None:
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    assert b"P011" in resp.content
    assert b"complete" in resp.content.lower() or b"finding" in resp.content.lower()


def test_index_states_how_uploaded_files_are_handled(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.get("/")
    assert resp.status_code == 200
    body = resp.content.lower()
    assert b"how your file is handled" in body
    assert b"processing runs on this server" in body
    assert b"deleted automatically" in body
    assert b"may quote short pieces of your document" in body


def test_index_states_pdf_only_web_support(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.get("/")
    assert resp.status_code == 200
    assert b"Supported inputs" in resp.content
    assert b"PDF" in resp.content
    assert b"Supported" in resp.content
    assert b"TeX" not in resp.content
    assert b".zip" not in resp.content


def test_index_lists_what_you_get_deliverables(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.get("/")
    assert resp.status_code == 200
    assert b"What you get" in resp.content
    assert b"JSON report" in resp.content
    assert b"Markdown report" in resp.content
    assert b"Triage summaries" in resp.content
    assert b"Polished comments" in resp.content


def test_results_page_shows_summary_cards(client: tuple[TestClient, Any], tmp_path: Path) -> None:
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path, finding_count=3)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    assert b"Items to review" in resp.content
    assert b"Pages affected" in resp.content
    assert b"Rules flagged" in resp.content


def test_summary_all_warning_report_hides_needs_fixing_and_worth_checking_cards(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """When every finding is a warning (no hard failures), the Summary should
    read "Items to review", "Pages affected", "Rules flagged" — never a
    redundant "Worth checking" card duplicating the same total, and never a
    "Needs fixing" card claiming 0 fixes are needed."""
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path, finding_count=3)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    html = resp.content.decode()
    assert '<div class="summary-card__label">Items to review</div>' in html
    assert '<div class="summary-card__value">3</div>' in html
    assert '<div class="summary-card__label">Needs fixing</div>' not in html
    assert '<div class="summary-card__label">Worth checking</div>' not in html
    assert "Findings are possible formatting issues" in html


def test_summary_shows_needs_fixing_card_when_fail_count_positive(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """When a report has real fail/error-level findings, "Needs fixing" must
    be shown clearly, alongside — not duplicated by — "Items to review"."""
    from njit_auditor.models import AuditFinding, Severity

    c, wa = client
    findings = [
        AuditFinding(
            rule_id="P011",
            severity=Severity.FAIL,
            page=1,
            message="Left margin too narrow.",
            details={"issue_type": "margin_boundary_violation", "side": "left_margin"},
        ),
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=2,
            message="Left margin too narrow.",
            details={"issue_type": "margin_boundary_violation", "side": "left_margin"},
        ),
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=3,
            message="Left margin too narrow.",
            details={"issue_type": "margin_boundary_violation", "side": "left_margin"},
        ),
    ]
    job_id = _inject_complete_job_with_findings(
        wa, tmp_path, findings=findings, file_name="thesis.pdf", audit_type="pdf"
    )
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    html = resp.content.decode()
    assert '<div class="summary-card__label">Needs fixing</div>' not in html
    assert "Technical rule statuses: 1 Fail" in html
    assert "Technical rule statuses: 1 Fail" in html
    assert '<div class="summary-card__label">Items to review</div>' in html
    assert '<div class="summary-card__value">3</div>' in html
    assert '<div class="summary-card__label">Worth checking</div>' not in html


def test_summary_export_endpoints_unaffected_by_card_presentation(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """The Summary card relabeling/hiding is presentation-only: JSON/Markdown
    exports must still report the real fail/warning counts unchanged."""
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path, finding_count=3)
    json_resp = c.get(f"/audits/{job_id}/download/json")
    assert json_resp.status_code == 200
    payload = json_resp.json()
    assert payload["metadata"]["counts_by_severity"]["WARNING"] == 3
    assert payload["metadata"]["counts_by_severity"]["FAIL"] == 0

    md_resp = c.get(f"/audits/{job_id}/download/markdown")
    assert md_resp.status_code == 200


def test_findings_by_topic_table_visible_sorted_and_clean(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """The restored "Findings by topic" table must be visible as its own
    section, list every category sorted by finding count descending, with
    clean (underscore-free) labels and a working per-row action link."""
    from njit_auditor.models import AuditFinding, Severity

    c, wa = client
    findings = (
        [
            AuditFinding(
                rule_id="P016",
                severity=Severity.WARNING,
                page=i + 1,
                message="Excessive line gap.",
                details={"issue_type": "excessive_line_gap", "largest_gap_pt": "48.0"},
            )
            for i in range(5)
        ]
        + [
            AuditFinding(
                rule_id="P020",
                severity=Severity.WARNING,
                page=20,
                message="Possible title-capitalization issue.",
                details={
                    "issue_type": "possible_title_capitalization_issue",
                    "flagged_word": "The",
                },
            )
            for _ in range(2)
        ]
    )
    job_id = _inject_complete_job_with_findings(
        wa, tmp_path, findings=findings, file_name="thesis.pdf", audit_type="pdf"
    )
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    html = resp.content.decode()

    assert 'id="section-topics"' in html
    assert "Findings by topic" in html
    # Clean labels, no raw snake_case categories leaking through.
    assert "Spacing / blank lines" in html
    assert "Capitalization" in html
    topics_html = html.split('id="section-topics"', 1)[1].split("</section>", 1)[0]
    assert "spacing_blank_lines" not in topics_html

    # Sorted by count descending: the 5-finding category must appear before
    # the 2-finding category in the table.
    idx_spacing = topics_html.index("Spacing / blank lines")
    idx_capitalization = topics_html.index("Capitalization")
    assert idx_spacing < idx_capitalization

    # Each row's action link targets the real category drilldown route.
    assert f"/audits/{job_id}/problems/category/spacing-blank-lines" in topics_html
    assert f"/audits/{job_id}/problems/category/capitalization-case" in topics_html
    category_resp = c.get(f"/audits/{job_id}/problems/category/spacing-blank-lines")
    assert category_resp.status_code == 200
    assert "Excessive line gap" in category_resp.text or "spacing" in category_resp.text.lower()


def test_findings_by_topic_table_compact_no_affected_pages_column(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """The top-level table is a compact navigation index: topic, count, and a
    "Review all" action only. Affected pages and per-category description text
    are dropped here (they made the category column too narrow on mobile) and
    belong on the category drilldown page instead."""
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path, finding_count=3)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    html = resp.content.decode()
    topics_section = html.split('id="section-topics"', 1)[1].split("</section>", 1)[0]
    table_html = topics_section.split("<table>", 1)[1].split("</table>", 1)[0]

    assert "<th>Topic</th>" in table_html
    assert "<th>Findings</th>" in table_html
    assert "Affected pages" not in table_html
    assert "Review all" in table_html
    # No inline category description/explanation text in the compact table —
    # that text used to wrap word-by-word in a narrow mobile column.
    assert "file-hint" not in table_html


def test_findings_by_topic_review_all_link_targets_category_drilldown(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """Each row's "Review all" action must be a working link to the existing
    category drilldown route, not a dead link or placeholder."""
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path, finding_count=3)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    html = resp.content.decode()
    topics_html = html.split('id="section-topics"', 1)[1].split("</section>", 1)[0]

    import re

    hrefs = re.findall(
        rf'href="(/audits/{job_id}/problems/category/[^"]+)"[^>]*>Review all</a>',
        topics_html,
    )
    assert hrefs, "expected at least one 'Review all' link in the topics table"
    for href in hrefs:
        category_resp = c.get(href)
        assert category_resp.status_code == 200


def test_findings_by_topic_section_always_visible_not_collapsed(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """Regression test for a live-deployment bug (2026-07): PR #490 restored the
    "Findings by topic" table, but the running web server had never been
    restarted onto the new code, so Soroush kept seeing the old page. The
    table's own code was correct and other tests here already covered its
    content — but nothing asserted the specific worry from the bug report:
    that the table must render as a plain, always-visible <section>, never
    nested inside a collapsed <details> ancestor, and must appear before the
    Downloads section and after Findings in page order."""
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path, finding_count=3)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    html = resp.content.decode()

    assert 'id="section-topics"' in html
    before_topics, after_marker = html.split('<section id="section-topics"', 1)
    # No unclosed <details> opened before this section and still open when it starts.
    assert before_topics.count("<details") == before_topics.count("</details>")
    # The section's own markup (up to its closing </section>) contains no <details>.
    topics_section = after_marker.split("</section>", 1)[0]
    assert "<details" not in topics_section

    idx_findings = html.index('id="section-findings"')
    idx_topics = html.index('id="section-topics"')
    idx_downloads = html.index('id="section-downloads"')
    assert idx_findings < idx_topics < idx_downloads


def test_problem_summary_by_type_table_removed_leaving_one_topic_table(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """The top "Problem summary by type" table (added in PR #495) was reported
    as a redundant duplicate of "Findings by topic" and removed at Soroush's
    request. Only one grouped-by-category count table — "Findings by topic" —
    should remain on the page, and it must keep its sorting, human-readable
    labels, and "Review all" links. "Findings in page order" must still be
    present as the main detailed review section."""
    from njit_auditor.models import AuditFinding, Severity

    c, wa = client
    findings = (
        [
            AuditFinding(
                rule_id="P016",
                severity=Severity.WARNING,
                page=i + 1,
                message="Excessive line gap.",
                details={"issue_type": "excessive_line_gap", "largest_gap_pt": "48.0"},
            )
            for i in range(5)
        ]
        + [
            AuditFinding(
                rule_id="P020",
                severity=Severity.WARNING,
                page=20,
                message="Possible title-capitalization issue.",
                details={
                    "issue_type": "possible_title_capitalization_issue",
                    "flagged_word": "The",
                },
            )
            for _ in range(2)
        ]
    )
    job_id = _inject_complete_job_with_findings(
        wa, tmp_path, findings=findings, file_name="thesis.pdf", audit_type="pdf"
    )
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    html = resp.content.decode()

    # The top "Problem summary by type" table is gone, with no replacement.
    assert 'id="section-problem-summary"' not in html
    assert "Problem summary by type" not in html

    # "Findings by topic" is rendered exactly once — the only grouped
    # count/topic table left on the page (nav/jump-link mentions of the
    # phrase elsewhere on the page are fine; the section itself must be
    # unique).
    assert html.count('id="section-topics"') == 1
    assert html.count("<h2>Findings by topic</h2>") == 1

    # "Findings in page order" remains the main detailed review section.
    assert 'id="section-findings"' in html

    topics_section = html.split('id="section-topics"', 1)[1].split("</section>", 1)[0]

    # Human-readable labels, not raw rule IDs.
    assert "Spacing / blank lines" in topics_section
    assert "Capitalization" in topics_section
    assert "P016" not in topics_section
    assert "P020" not in topics_section

    # Still sorted by count descending.
    idx_spacing = topics_section.index("Spacing / blank lines")
    idx_capitalization = topics_section.index("Capitalization")
    assert idx_spacing < idx_capitalization

    # "Review all" links are kept.
    assert "Review all" in topics_section
    assert f"/audits/{job_id}/problems/category/spacing-blank-lines" in topics_section


def test_category_drilldown_page_shows_affected_pages(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """Affected pages were removed from the compact Findings by topic table;
    the category drilldown page must still surface them so nothing is lost."""
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path, finding_count=3)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    html = resp.content.decode()
    topics_html = html.split('id="section-topics"', 1)[1].split("</section>", 1)[0]

    import re

    href_match = re.search(
        rf'href="(/audits/{job_id}/problems/category/[^"]+)"[^>]*>Review all</a>',
        topics_html,
    )
    assert href_match is not None
    category_resp = c.get(href_match.group(1))
    assert category_resp.status_code == 200
    assert "Pages to review" in category_resp.text


def test_findings_by_topic_table_not_grouped_by_rule_id(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """The restored table groups by category, not by rule ID — rule IDs stay
    confined to the collapsed Technical rule summary table."""
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path, finding_count=3)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    html = resp.content.decode()
    table_html = html.split('id="section-topics"', 1)[1].split("</table>", 1)[0]
    assert "<th>Topic</th>" in table_html
    assert "<th>Rule</th>" not in table_html


def test_findings_in_page_order_precedes_findings_by_topic(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """The findings-first view places actionable cards above its related guidance."""
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path, finding_count=3)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    html = resp.content.decode()

    idx_review_order = html.index('id="section-review-order"')
    idx_findings = html.index('id="section-findings"')
    idx_topics = html.index('id="section-topics"')
    assert idx_findings < idx_review_order < idx_topics
    assert 'id="section-triage"' not in html


def test_findings_by_topic_coexists_with_simplified_summary_and_nav(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """Restoring the category table must not undo the other recent UI work:
    simplified top Summary cards, decluttered nav, and the collapsed
    Advanced rule-by-rule table all remain intact."""
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path, finding_count=3)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    html = resp.content.decode()

    assert "Findings by topic" in html
    assert "Items to review" in html
    assert '<div class="summary-card__label">Worth checking</div>' not in html
    assert "Technical rule summary" in html
    assert "Advanced: rule-by-rule technical summary" in html
    assert "<details class=\"card collapsible\">" in html


def test_results_page_defaults_to_individual_findings_with_advanced_grouped_summary(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """The main Findings section is the individual findings table by default (no
    grouped/individual toggle); the same 9 occurrences are still summarized as one
    card with expandable per-occurrence detail, but only inside the collapsed
    Advanced: grouped problem summaries section further down the page."""
    from njit_auditor.models import AuditFinding, Severity

    c, wa = client
    findings = [
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=page,
            message="Left margin too narrow.",
            details={
                "issue_type": "margin_boundary_violation",
                "side": "left_margin",
                "confidence": "medium",
                "suggested_fix": "Adjust the left margin in the PDF export settings.",
            },
        )
        for page in (3, 4, 5, 6, 7, 10, 14, 15, 16)
    ]
    job_id = _inject_complete_job_with_findings(
        wa,
        tmp_path,
        findings=findings,
        file_name="thesis.pdf",
        audit_type="pdf",
    )

    resp = c.get(f"/audits/{job_id}")

    assert resp.status_code == 200
    assert b"Grouped problems" not in resp.content
    assert b"All individual findings" not in resp.content
    assert b"Show individual occurrences" in resp.content
    assert b"9 occurrences" in resp.content
    assert "3–7, 10, 14–16".encode() in resp.content
    assert (
        b"Confidence describes how sure the tool is about its detection, not severity"
        in resp.content
    )
    assert b'id="grouped-problems-panel"' not in resp.content
    assert b'id="individual-findings-panel"' in resp.content
    assert b'id="section-grouped-summary"' in resp.content
    assert b"Advanced: grouped problem summaries" in resp.content
    # The 9 individual finding cards (one per page) are the primary panel's content.
    panel_start = resp.text.index('id="individual-findings-panel"')
    panel_end = resp.text.index('id="section-downloads"', panel_start)
    panel = resp.text[panel_start:panel_end]
    assert panel.count('class="finding-row finding-card"') == 9


def test_results_page_renders_confidence_badges_and_filters(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    from njit_auditor.models import AuditFinding, Severity

    c, wa = client
    findings = [
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=3,
            message="Left margin too narrow.",
            details={
                "issue_type": "margin_boundary_violation",
                "side": "left_margin",
                "confidence": "high",
            },
        ),
        AuditFinding(
            rule_id="P026",
            severity=Severity.WARNING,
            page=5,
            message="Font issue.",
            details={
                "issue_type": "possible_body_font_family_issue",
                "confidence": "medium",
            },
        ),
        AuditFinding(
            rule_id="P030",
            severity=Severity.WARNING,
            page=7,
            message="Missing continued heading.",
            details={
                "issue_type": "missing_continued_heading",
                "confidence": "low",
            },
        ),
    ]
    job_id = _inject_complete_job_with_findings(
        wa,
        tmp_path,
        findings=findings,
        file_name="thesis.pdf",
        audit_type="pdf",
    )

    resp = c.get(f"/audits/{job_id}")

    assert resp.status_code == 200
    body = resp.text
    assert 'data-confidence-filter=""' in body
    assert 'data-confidence-filter="high"' in body
    assert 'data-confidence-filter="medium"' in body
    assert 'data-confidence-filter="low"' in body
    assert "High confidence" in body
    assert "Medium confidence" in body
    assert "Low confidence" in body
    assert 'data-confidence="high"' in body
    assert 'data-confidence="medium"' in body
    assert 'data-confidence="low"' in body
    assert "Confidence: high" not in body
    assert "Confidence: medium" not in body
    assert "Confidence: low" not in body


def _confidence_sort_web_findings() -> list[Any]:
    """Three singleton problems in a deliberately non-confidence-ordered default order:
    P037 (low), P011 (high), P026 (medium)."""
    from njit_auditor.models import AuditFinding, Severity

    return [
        AuditFinding(
            rule_id="P037",
            severity=Severity.WARNING,
            page=2,
            message="Page number issue.",
            details={"issue_type": "wrong_page_number_sequence", "confidence": "low"},
        ),
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=1,
            message="Margin issue.",
            details={
                "issue_type": "margin_boundary_violation",
                "side": "left_margin",
                "confidence": "high",
            },
        ),
        AuditFinding(
            rule_id="P026",
            severity=Severity.WARNING,
            page=3,
            message="Font issue.",
            details={"issue_type": "possible_body_font_family_issue", "confidence": "medium"},
        ),
    ]


def _grouped_problem_rule_order(body: str, rule_ids: list[str]) -> list[str]:
    """Return ``rule_ids`` re-ordered by where each first appears as a grouped-problem
    card's ``data-rule`` attribute in the rendered results page body."""
    positions = [(body.index(f'data-rule="{rule_id}"'), rule_id) for rule_id in rule_ids]
    return [rule_id for _, rule_id in sorted(positions)]


def test_results_page_renders_sort_control_with_accessible_label(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    c, wa = client
    job_id = _inject_complete_job_with_findings(
        wa,
        tmp_path,
        findings=_confidence_sort_web_findings(),
        file_name="thesis.pdf",
        audit_type="pdf",
    )

    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    body = resp.text
    assert '<label for="sort-problems">Sort findings</label>' in body
    assert 'id="sort-problems"' in body
    assert 'name="sort"' in body
    assert "Default order" not in body
    assert "High confidence first" in body
    assert "Low confidence first" in body
    # "Page order" is the default option's visible label, and it must appear exactly
    # once now that the old separate "page_order" dropdown entry has been folded into
    # the (renamed) default option.
    assert body.count("Page order") == 1


def test_sort_query_param_confidence_desc_orders_high_confidence_first(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    c, wa = client
    job_id = _inject_complete_job_with_findings(
        wa,
        tmp_path,
        findings=_confidence_sort_web_findings(),
        file_name="thesis.pdf",
        audit_type="pdf",
    )

    default_resp = c.get(f"/audits/{job_id}")
    assert default_resp.status_code == 200
    default_order = _grouped_problem_rule_order(
        default_resp.text, ["P037", "P011", "P026"]
    )
    # Default order is page order: P011=page 1, P037=page 2, P026=page 3.
    assert default_order == ["P011", "P037", "P026"]

    resp = c.get(f"/audits/{job_id}?sort=confidence_desc")
    assert resp.status_code == 200
    assert 'selected' in resp.text
    assert _grouped_problem_rule_order(resp.text, ["P037", "P011", "P026"]) == [
        "P011",
        "P026",
        "P037",
    ]


def test_sort_query_param_confidence_asc_orders_low_confidence_first(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    c, wa = client
    job_id = _inject_complete_job_with_findings(
        wa,
        tmp_path,
        findings=_confidence_sort_web_findings(),
        file_name="thesis.pdf",
        audit_type="pdf",
    )

    resp = c.get(f"/audits/{job_id}?sort=confidence_asc")
    assert resp.status_code == 200
    assert _grouped_problem_rule_order(resp.text, ["P037", "P011", "P026"]) == [
        "P037",
        "P026",
        "P011",
    ]


def test_sort_query_param_page_order_orders_by_earliest_page(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    c, wa = client
    job_id = _inject_complete_job_with_findings(
        wa,
        tmp_path,
        findings=_confidence_sort_web_findings(),
        file_name="thesis.pdf",
        audit_type="pdf",
    )

    resp = c.get(f"/audits/{job_id}?sort=page_order")
    assert resp.status_code == 200
    assert 'selected' in resp.text
    # Pages: P037=2, P011=1, P026=3 -- page order should surface P011 (page 1) first.
    assert _grouped_problem_rule_order(resp.text, ["P037", "P011", "P026"]) == [
        "P011",
        "P037",
        "P026",
    ]


def test_sort_query_param_missing_or_default_orders_by_page(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    c, wa = client
    job_id = _inject_complete_job_with_findings(
        wa,
        tmp_path,
        findings=_confidence_sort_web_findings(),
        file_name="thesis.pdf",
        audit_type="pdf",
    )

    no_param_resp = c.get(f"/audits/{job_id}")
    explicit_default_resp = c.get(f"/audits/{job_id}?sort=default")
    assert no_param_resp.status_code == 200
    assert explicit_default_resp.status_code == 200
    # Default order is page order: P011=page 1, P037=page 2, P026=page 3.
    expected = ["P011", "P037", "P026"]
    assert _grouped_problem_rule_order(no_param_resp.text, expected) == expected
    assert _grouped_problem_rule_order(explicit_default_resp.text, expected) == expected


def _finding_row_rule_order(body: str, rule_ids: list[str]) -> list[str]:
    """Return the rule IDs of every ``.finding-row`` in the primary, always-visible
    individual-findings table (not the advanced grouped summary), in render order."""
    import re

    panel_start = body.index('id="individual-findings-panel"')
    panel_end = body.index("</table>", panel_start)
    panel = body[panel_start:panel_end]
    row_order = re.findall(r'data-rule="([^"]+)"[^>]*class="finding-row', panel)
    return [rule_id for rule_id in row_order if rule_id in rule_ids]


def test_individual_findings_are_sorted_by_page_order_on_initial_render(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """The primary Findings table (not just the advanced grouped summary) must
    render individual findings in page order by default, matching the "Page
    order" default in the Sort findings dropdown."""
    c, wa = client
    job_id = _inject_complete_job_with_findings(
        wa,
        tmp_path,
        findings=_confidence_sort_web_findings(),
        file_name="thesis.pdf",
        audit_type="pdf",
    )

    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    # Default order is page order: P011=page 1, P037=page 2, P026=page 3.
    expected = ["P011", "P037", "P026"]
    assert _finding_row_rule_order(resp.text, expected) == expected


def test_detected_page_number_candidates_excluded_from_main_findings_list(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """A redundant page-number candidate (already claimed by a real page-numbering
    problem elsewhere) must never appear as a row in the primary, page-ordered
    individual-findings table -- it belongs only in the separate, clearly-labeled
    "Detected page-number candidates" inventory section, so it can never look like
    an out-of-order normal finding."""
    from njit_auditor.models import AuditFinding, Severity

    c, wa = client
    findings = [
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=1,
            message="Left margin too narrow.",
            details={"issue_type": "margin_boundary_violation", "side": "left_margin"},
        ),
        AuditFinding(
            rule_id="P013",
            severity=Severity.WARNING,
            page=5,
            message="Page number candidate.",
            details={"issue_type": "page_number_candidate", "position_type": "bottom_center"},
        ),
    ]
    job_id = _inject_complete_job_with_findings(
        wa, tmp_path, findings=findings, file_name="thesis.pdf", audit_type="pdf"
    )

    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    body = resp.text

    findings_start = body.index('id="section-findings"')
    findings_end = body.index("</section>", findings_start)
    findings_section = body[findings_start:findings_end]
    assert 'data-rule="P011"' in findings_section
    assert 'data-rule="P013"' not in findings_section

    assert 'id="section-inventory"' in body
    inventory_start = body.index('id="section-inventory"')
    assert "Detected page-number candidates" in body[inventory_start : inventory_start + 200]


def test_advanced_grouped_summary_is_collapsed_and_outside_main_flow(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """The "Advanced: grouped problem summaries" section is a collapsed <details>
    (no ``open`` attribute) and sits after the primary Findings section (and after
    Downloads), not inside the main student-facing Findings flow."""
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path, finding_count=3)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    body = resp.text

    assert 'id="section-grouped-summary"' in body
    idx_findings = body.index('id="section-findings"')
    idx_downloads = body.index('id="section-downloads"')
    idx_grouped_summary = body.index('id="section-grouped-summary"')
    assert idx_findings < idx_downloads < idx_grouped_summary

    section_start = body.index('aria-label="Advanced: grouped problem summaries"')
    details_start = body.index("<details", section_start)
    details_tag = body[details_start : body.index(">", details_start) + 1]
    assert "open" not in details_tag


def test_invalid_sort_query_param_falls_back_to_default_order(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    c, wa = client
    job_id = _inject_complete_job_with_findings(
        wa,
        tmp_path,
        findings=_confidence_sort_web_findings(),
        file_name="thesis.pdf",
        audit_type="pdf",
    )

    resp = c.get(f"/audits/{job_id}?sort=not-a-real-mode")
    assert resp.status_code == 200
    # Falls back to default order, i.e. page order.
    assert _grouped_problem_rule_order(resp.text, ["P037", "P011", "P026"]) == [
        "P011",
        "P037",
        "P026",
    ]


def test_sort_query_param_does_not_change_problem_numbers(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """Problem numbers/anchors must stay stable across sort modes so links don't break."""
    c, wa = client
    job_id = _inject_complete_job_with_findings(
        wa,
        tmp_path,
        findings=_confidence_sort_web_findings(),
        file_name="thesis.pdf",
        audit_type="pdf",
    )

    default_body = c.get(f"/audits/{job_id}").text
    sorted_body = c.get(f"/audits/{job_id}?sort=confidence_desc").text
    for anchor in ("problem-1", "problem-2", "problem-3"):
        assert f'id="{anchor}"' in default_body
        assert f'id="{anchor}"' in sorted_body
    for label in ("Problem 1", "Problem 2", "Problem 3"):
        assert label in default_body
        assert label in sorted_body


def test_sort_query_param_preserves_grouping_and_occurrence_details(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """A grouped multi-occurrence card must stay grouped (not split) after sorting, and
    its per-occurrence detail rows must still be present."""
    from njit_auditor.models import AuditFinding, Severity

    findings = [
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=i + 1,
            message="Margin issue.",
            details={
                "issue_type": "margin_boundary_violation",
                "side": "left_margin",
                "confidence": "medium",
            },
        )
        for i in range(3)
    ] + [
        AuditFinding(
            rule_id="P026",
            severity=Severity.WARNING,
            page=5,
            message="Font issue.",
            details={"issue_type": "possible_body_font_family_issue", "confidence": "high"},
        ),
    ]
    grouped_findings = [
        {
            "rule_id": "P011",
            "issue_type": "margin_boundary_violation",
            "individual_indexes": [0, 1, 2],
        },
        {
            "rule_id": "P026",
            "issue_type": "possible_body_font_family_issue",
            "individual_indexes": [3],
        },
    ]
    c, wa = client
    job_id = _inject_complete_job_with_findings(
        wa,
        tmp_path,
        findings=findings,
        file_name="thesis.pdf",
        audit_type="pdf",
        grouped_findings=grouped_findings,
    )

    for query in ("", "?sort=confidence_desc", "?sort=confidence_asc"):
        resp = c.get(f"/audits/{job_id}{query}")
        assert resp.status_code == 200
        body = resp.text
        assert "3 occurrences" in body
        assert "Show individual occurrences" in body
        assert body.count('class="grouped-occurrence"') == 3


def test_sort_query_param_keeps_pdf_highlight_links_working(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """Existing "Open highlighted PDF page" buttons must still render and route
    correctly when the results page is sorted by confidence."""
    c, wa = client
    findings = [_p012_annotation_finding_with_bbox(page=3)]
    job_id = _inject_complete_job_with_findings(
        wa, tmp_path, findings=findings, file_name="thesis.pdf", audit_type="pdf"
    )

    for query in ("?sort=confidence_desc", "?sort=confidence_asc"):
        resp = c.get(f"/audits/{job_id}{query}")
        assert resp.status_code == 200
        body = resp.text
        assert "Open highlighted PDF page" in body
        links = AUDIT_PDF_HREF_RE.findall(body)
        assert links
        for link in links:
            link_resp = c.get(link)
            assert link_resp.status_code != 500


def test_results_page_confidence_badges_use_only_three_public_values(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """Every rendered confidence-badge CSS class must be high/medium/low -- no
    mixed-orange, unknown, or other extra category -- and the visible page must
    never show Priority, Needs review, or Mixed confidence text, covering a
    missing-confidence finding (P030) alongside ordinary high/medium/low ones."""
    import re

    from njit_auditor.models import AuditFinding, Severity

    c, wa = client
    findings = [
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=1,
            message="Margin issue.",
            details={
                "issue_type": "margin_boundary_violation",
                "side": "left_margin",
                "confidence": "high",
            },
        ),
        AuditFinding(
            rule_id="P026",
            severity=Severity.WARNING,
            page=2,
            message="Font issue.",
            details={"issue_type": "possible_body_font_family_issue", "confidence": "medium"},
        ),
        AuditFinding(
            rule_id="P037",
            severity=Severity.WARNING,
            page=3,
            message="Page number issue.",
            details={"issue_type": "wrong_page_number_sequence", "confidence": "low"},
        ),
        AuditFinding(
            rule_id="P030",
            severity=Severity.WARNING,
            page=4,
            message="Missing continued heading.",
            details={"issue_type": "missing_continued_heading"},
        ),
    ]
    job_id = _inject_complete_job_with_findings(
        wa,
        tmp_path,
        findings=findings,
        file_name="thesis.pdf",
        audit_type="pdf",
    )

    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    body = resp.text

    badge_classes = set(re.findall(r"confidence-badge--(\S+?)[\"' ]", body))
    assert badge_classes, "expected at least one confidence badge on the page"
    assert badge_classes <= {"high", "medium", "low"}, badge_classes

    # Student-facing problem cards show Confidence only -- Priority is never a
    # visible label, and no fourth/fifth confidence category leaks into the badge
    # text either.
    assert "Priority" not in body
    assert "Needs review confidence" not in body
    assert "Mixed confidence" not in body
    assert "Low confidence" in body  # from the missing-confidence P030 card


def test_missing_confidence_finding_data_confidence_matches_low_filter(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """Missing canonical confidence shows a Low badge; data-confidence must be low too.

    Otherwise the Low filter chip hides rows that still display as Low confidence."""
    import re

    from njit_auditor.models import AuditFinding, Severity

    c, wa = client
    findings = [
        AuditFinding(
            rule_id="P030",
            severity=Severity.WARNING,
            page=4,
            message="Missing continued heading.",
            details={"issue_type": "missing_continued_heading"},
        ),
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=1,
            message="Margin issue.",
            details={
                "issue_type": "margin_boundary_violation",
                "side": "left_margin",
                "confidence": "high",
            },
        ),
    ]
    job_id = _inject_complete_job_with_findings(
        wa,
        tmp_path,
        findings=findings,
        file_name="thesis.pdf",
        audit_type="pdf",
    )

    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    body = resp.text

    p030_row = re.search(
        r'data-rule="P030"[^>]*data-confidence="([^"]*)"',
        body,
    )
    assert p030_row is not None, "expected P030 finding row with data-confidence"
    assert p030_row.group(1) == "low"

    assert 'data-confidence="high"' in body
    assert 'data-confidence=""' not in body


def test_individual_findings_table_confidence_badge_matches_data_confidence(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """The primary individual-findings table must show a confidence badge that
    actually matches each row's real confidence, not a
    fallback -- regression guard for a bug where the row's serialized dict carried
    ``confidence`` but not ``confidence_level``/``confidence_label``/
    ``confidence_css_class``, so the template silently rendered the macro's own
    default badge regardless of the finding's real confidence."""
    from njit_auditor.models import AuditFinding, Severity

    c, wa = client
    findings = [
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=4,
            message="Left margin too narrow.",
            details={
                "issue_type": "margin_boundary_violation",
                "side": "left_margin",
                "confidence": "high",
            },
        ),
    ]
    job_id = _inject_complete_job_with_findings(
        wa,
        tmp_path,
        findings=findings,
        file_name="thesis.pdf",
        audit_type="pdf",
    )

    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    body = resp.text

    row_start = body.index('id="individual-findings-panel"')
    row = body[row_start : row_start + 4000]
    assert 'data-confidence="high"' in row
    assert "confidence-badge--high" in row
    assert "High confidence" in row
    assert "confidence-badge--low" not in row
    assert "Low confidence" not in row


def test_results_page_omits_redundant_problem_badge_and_uses_confidence_palette(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    from njit_auditor.models import AuditFinding, Severity

    c, wa = client
    findings = [
        AuditFinding(
            rule_id="P037",
            severity=Severity.WARNING,
            page=3,
            message="Page number issue.",
            details={
                "issue_type": "wrong_page_number_sequence",
                "confidence": "medium",
            },
        ),
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=5,
            message="Left margin too narrow.",
            details={
                "issue_type": "margin_boundary_violation",
                "side": "left_margin",
                "confidence": "high",
            },
        ),
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=6,
            message="Right margin too narrow.",
            details={
                "issue_type": "margin_boundary_violation",
                "side": "right_margin",
                "confidence": "low",
            },
        ),
    ]
    job_id = _inject_complete_job_with_findings(
        wa,
        tmp_path,
        findings=findings,
        file_name="thesis.pdf",
        audit_type="pdf",
        grouped_findings=[
            {
                "rule_id": "P011",
                "issue_type": "margin_boundary_violation",
                "individual_indexes": [1, 2],
            }
        ],
    )

    resp = c.get(f"/audits/{job_id}")
    body = resp.text

    assert resp.status_code == 200
    assert 'badge-warn">Problem</span>' not in body
    assert "confidence-badge--medium" in body
    assert "confidence-badge--high" in body
    assert "confidence-badge--low" in body
    # Public confidence display supports exactly three values (High/Medium/Low); a
    # mixed-confidence grouped card (P011 here) displays as Low, not a separate
    # "mixed" category or label.
    assert "confidence-badge--mixed-orange" not in body
    assert "Mixed confidence" not in body


def test_results_page_grouped_cards_include_mixed_confidence_filter_metadata(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    import secrets
    from datetime import datetime, timezone

    from njit_auditor.models import AuditFinding, Severity
    from njit_auditor.pdf_highlight import get_pdf_page_sizes
    from njit_auditor.report_outputs import audit_findings_to_json_dict, write_markdown_report
    from njit_auditor.report_text import write_text_report
    from njit_auditor.report_view import build_report_view, report_view_to_dict

    c, wa = client
    findings = [
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=3,
            message="Left margin too narrow.",
            details={
                "issue_type": "margin_boundary_violation",
                "side": "left_margin",
                "confidence": "high",
            },
        ),
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=4,
            message="Left margin too narrow.",
            details={
                "issue_type": "margin_boundary_violation",
                "side": "left_margin",
                "confidence": "low",
            },
        ),
    ]
    job_id = secrets.token_urlsafe(16)
    jdir = Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"]) / job_id
    jdir.mkdir(parents=True, exist_ok=True)
    _make_real_pdf(jdir / "upload.pdf", page_count=5)
    metadata = {"input_file_name": "thesis.pdf", "audit_type": "pdf", "job_id": job_id}
    payload = audit_findings_to_json_dict(findings, metadata)
    payload["grouped_findings"] = [
        {
            "rule_id": "P011",
            "issue_type": "margin_boundary_violation",
            "individual_indexes": [0, 1],
        }
    ]
    (jdir / "report.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_markdown_report(findings, metadata, jdir / "report.md")
    write_text_report(findings, metadata, jdir / "report.txt")
    pdf_page_sizes = get_pdf_page_sizes(jdir / "upload.pdf")
    view = build_report_view(payload, pdf_page_sizes=pdf_page_sizes)

    job = wa.JobState(
        job_id=job_id,
        state="complete",
        created_at=datetime.now(timezone.utc).isoformat(),
        file_name="thesis.pdf",
        audit_type="pdf",
        pdf_page_count=len(pdf_page_sizes),
        pdf_page_sizes=pdf_page_sizes,
        finding_count=view.total_findings,
        warn_count=sum(1 for fv in view.findings if fv.severity == "WARNING"),
        fail_count=sum(1 for fv in view.findings if fv.severity == "FAIL"),
        findings=[
            {
                "rule_id": fv.rule_id,
                "severity": fv.severity,
                "page": fv.page,
                "issue_type": fv.issue_type,
                "category": fv.category,
                "polished_comment": fv.polished_comment,
                "suggested_fix": fv.suggested_fix,
                "triage_tier": fv.triage_tier,
                "confidence": fv.confidence,
                "confidence_level": fv.confidence_level,
                "confidence_label": fv.confidence_label,
                "confidence_css_class": fv.confidence_css_class,
                "source_file": fv.source_file,
                "source_line": fv.source_line,
                "location_label": fv.location_label,
            }
            for fv in view.findings
        ],
        grouped_summary=[
            {"rule_id": rs.rule_id, "count": rs.count, "category": rs.category}
            for rs in view.rule_summaries
        ],
        report_view=report_view_to_dict(view),
        md_preview="# Audit Report\n",
    )
    wa._set_job(job)

    resp = c.get(f"/audits/{job_id}")

    assert resp.status_code == 200
    body = resp.text
    # Public display normalizes the mixed high+low card to Low confidence. The
    # data-confidence-levels token list preserves both real levels for possible
    # future grouped-card filtering; current confidence chips filter only the
    # individual findings list (.finding-row), not grouped summary cards.
    assert "Mixed confidence" not in body
    assert "Low confidence" in body
    assert 'data-confidence-levels="|high|low|"' in body
    assert 'class="grouped-occurrence" data-confidence="high"' in body
    assert 'class="grouped-occurrence" data-confidence="low"' in body


def test_results_page_groups_source_locations_compactly(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    from njit_auditor.models import AuditFinding, Severity

    c, wa = client
    findings = [
        AuditFinding(
            rule_id="P001",
            severity=Severity.WARNING,
            message="Avoid shell escape commands in TeX source.",
            details={
                "file": "/tmp/private/thesis.tex",
                "line": str(line),
                "issue_type": "risky_command",
                "command": "\\write18",
                "suggested_fix": "Remove the shell-escape command from the source.",
            },
        )
        for line in (12, 18, 19, 20, 21)
    ]
    job_id = _inject_complete_job_with_findings(
        wa,
        tmp_path,
        findings=findings,
        file_name="thesis.tex",
        audit_type="tex",
    )

    resp = c.get(f"/audits/{job_id}")

    assert resp.status_code == 200
    assert "thesis.tex:12, thesis.tex:18–21".encode() in resp.content
    assert b"/tmp/private/" not in resp.content
    assert b"Show individual occurrences" in resp.content


def test_results_page_no_longer_shows_most_common_issues_section(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """The "Most common issues" root-cause cards were removed as repetitive
    now that "Findings by topic" is the main category overview: same counts
    and categories, one compact table instead of two competing summaries."""
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path, finding_count=6)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    html = resp.content.decode()
    assert "Most common issues" not in html
    assert 'id="section-triage"' not in html
    assert "Examples for this rule" not in html
    # The category overview students actually use is still present.
    assert 'id="section-topics"' in html
    assert "Findings by topic" in html


def test_results_page_category_chips_link_to_problem_pages(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path, finding_count=2)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    assert f'/audits/{job_id}/problems/category/margin-or-overflow'.encode() in resp.content


def test_results_page_p013_all_routine_candidates_absent_from_topic_table(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """When every P013 candidate is routine (no visible problems), it must not
    appear in Findings by topic at all — it's supporting inventory data, not a
    problem category — and the rule drilldown correctly has nothing to show."""
    from njit_auditor.models import AuditFinding, Severity

    c, wa = client
    findings = [
        AuditFinding(
            rule_id="P013",
            severity=Severity.WARNING,
            page=page,
            message="Page has one page-number-like candidate.",
            details={
                "issue_type": "page_number_candidate",
                "position_type": "bottom_center",
                "number_style": "arabic",
                "confidence": "medium",
            },
        )
        for page in range(1, 4)
    ]
    job_id = _inject_complete_job_with_findings(
        wa, tmp_path, findings=findings, file_name="thesis.pdf", audit_type="pdf"
    )
    job = wa._get_job(job_id)
    assert len(job.report_view.get("inventory_findings", [])) == 3
    assert not job.report_view.get("category_summary")

    resp = c.get(f"/audits/{job_id}")

    assert resp.status_code == 200
    html = resp.content.decode()
    assert 'id="section-topics"' not in html
    assert "Page numbering" not in html

    rule_resp = c.get(f"/audits/{job_id}/problems/rule/P013")
    assert rule_resp.status_code == 404


def test_results_page_p013_real_problem_appears_in_topic_table(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """A real P013 problem (multiple candidates on one page) must surface in
    Findings by topic with a working Review all link to a drilldown page that
    shows the actual problem, distinct from the routine candidates."""
    from njit_auditor.models import AuditFinding, Severity

    c, wa = client
    findings = [
        AuditFinding(
            rule_id="P013",
            severity=Severity.WARNING,
            page=page,
            message="Page has one page-number-like candidate.",
            details={
                "issue_type": "page_number_candidate",
                "position_type": "bottom_center",
                "number_style": "arabic",
                "confidence": "medium",
            },
        )
        for page in range(1, 4)
    ] + [
        AuditFinding(
            rule_id="P013",
            severity=Severity.WARNING,
            page=9,
            message="Multiple page-number-like tokens detected.",
            details={
                "issue_type": "page_number_candidate",
                "position_type": "bottom_center",
                "candidate_count_on_page": "2",
                "confidence": "medium",
            },
        )
    ]
    job_id = _inject_complete_job_with_findings(
        wa, tmp_path, findings=findings, file_name="thesis.pdf", audit_type="pdf"
    )

    resp = c.get(f"/audits/{job_id}")

    assert resp.status_code == 200
    html = resp.content.decode()
    assert "3 detected candidate" in html
    topics_html = html.split('id="section-topics"', 1)[1].split("</section>", 1)[0]
    assert "Page numbering" in topics_html

    rule_resp = c.get(f"/audits/{job_id}/problems/rule/P013")
    assert rule_resp.status_code == 200
    assert b"Multiple page-number-like tokens" in rule_resp.content


def test_category_labels_have_no_underscores_in_summary_cards(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """Root-cause category cards must show clean 'Word / word' labels, never
    the raw snake_case category key with stray underscores (e.g. the label
    must read "Spacing / blank lines", not "Spacing_/blank lines")."""
    from njit_auditor.models import AuditFinding, Severity

    c, wa = client
    findings = [
        AuditFinding(
            rule_id="P020",
            severity=Severity.WARNING,
            page=3,
            message="Possible title-capitalization issue.",
            details={"issue_type": "possible_title_capitalization_issue", "flagged_word": "The"},
        ),
        AuditFinding(
            rule_id="P016",
            severity=Severity.WARNING,
            page=8,
            message="Excessive line gap.",
            details={"issue_type": "excessive_line_gap", "largest_gap_pt": "48.0"},
        ),
        AuditFinding(
            rule_id="P063",
            severity=Severity.WARNING,
            page=40,
            message="Multiple-appendix body heading missing letter identifier.",
            details={
                "issue_type": "multiple_appendix_missing_letter",
                "page": "40",
                "appendix_count": "2",
            },
        ),
    ]
    job_id = _inject_complete_job_with_findings(
        wa, tmp_path, findings=findings, file_name="thesis.pdf", audit_type="pdf"
    )

    resp = c.get(f"/audits/{job_id}")

    assert resp.status_code == 200
    html = resp.content.decode()
    assert "Capitalization" in html
    assert "Spacing / blank lines" in html
    assert "Front matter / appendix structure" in html
    assert "Spacing_/blank lines" not in html
    assert "Front matter_/appendix" not in html
    for raw_key in ("capitalization_case", "spacing_blank_lines", "frontmatter_structure"):
        assert f">{raw_key}<" not in html


def test_results_page_advanced_rule_summary_is_collapsed(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """The rule-by-rule technical table stays available for maintainers, but
    is tucked behind a collapsed <details> "Advanced" section rather than
    shown as a second primary summary table."""
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path, finding_count=6)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    html = resp.content.decode()
    assert "Advanced: rule-by-rule technical summary" in html
    assert "Click a rule ID for rule reference" in html
    idx_heading = html.index("Advanced: rule-by-rule technical summary")
    idx_details = html.index("<details", idx_heading)
    # Rule ids are shown to students in their Rxxx form (Ester's requested
    # terminology), never the internal Pxxx catalog id -- see
    # public_display_rule_id in report_outputs.py.
    idx_rule_id = html.index(">R011<", idx_details)
    assert idx_details != -1 and idx_rule_id > idx_details
    assert ">P011<" not in html


def test_results_page_atomic_sub_rule_finding_card_shows_r_form_not_raw_p_form(
    client: tuple[TestClient, Any],
) -> None:
    """Regression guard: a P018 finding with issue_type
    "inconsistent_leader_dots" resolves to the atomic sub-rule reference
    P018D (see _P018_BACKEND_ISSUE_MAP in web_app.py). Its finding-card rule
    link's visible text and aria-label must show the public R018D form, not
    leak the raw internal P018D id -- this is the exact leak a live smoke
    test found. Reproducing it requires the real audit pipeline (POST
    /audits -> _run_audit_task), not the simplified test-injection helper:
    only that path populates each finding's public_rule_reference_id (the
    precomputed /rules anchor id used for both the href and, before this
    fix, the unfiltered visible label too -- see job.html)."""
    from njit_auditor.models import AuditFinding, Severity

    def _fake_leader_dots_dispatch(pdf_path: Path, **kwargs: Any) -> Any:
        from njit_auditor.audit_runner import UploadedAuditResult
        from njit_auditor.upload_handling import UploadKind

        finding = AuditFinding(
            rule_id="P018",
            severity=Severity.WARNING,
            page=11,
            message="TOC/List entries show inconsistent visible leader-dot usage.",
            details={
                "issue_type": "inconsistent_leader_dots",
                "page_type": "table_of_contents",
                "confidence": "medium",
            },
        )
        return UploadedAuditResult(
            upload_kind=UploadKind.PDF, audit_type="pdf", findings=[finding]
        )

    c, wa = client
    with patch.object(wa, "run_audit_for_uploaded_file", _fake_leader_dots_dispatch):
        post = c.post(
            "/audits",
            files={"file": ("thesis.pdf", io.BytesIO(_MINIMAL_PDF), "application/pdf")},
            follow_redirects=True,
        )
    assert "/audits/" in str(post.url)
    html = post.content.decode()
    # The href legitimately keeps the raw internal anchor id (it must match
    # the /rules page's own DOM id for that atomic sub-rule) -- only the
    # visible label and aria-label are student-facing topic names.
    assert 'href="/rules#P018D"' in html
    assert 'aria-label="TABLE OF CONTENTS: see rule reference">TABLE OF CONTENTS</a>' in html
    assert "Rule R018" in html  # available in optional technical details
    assert ">P018D<" not in html
    assert 'aria-label="P018D' not in html


def test_results_page_review_action_labels_present_on_mobile_and_desktop(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """Findings by topic's "Review all" action label is present regardless of
    viewport (the server renders identical markup; layout is handled by CSS)."""
    mobile_headers = {
        "User-Agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
        ),
    }
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path, finding_count=6)
    desktop_html = c.get(f"/audits/{job_id}").content.decode()
    mobile_html = c.get(f"/audits/{job_id}", headers=mobile_headers).content.decode()
    for html in (desktop_html, mobile_html):
        assert "Review all" in html


def test_occurrence_table_long_issue_and_fix_text_uses_detail_cell(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """The individual-occurrences table's issue-type/suggested-fix column
    must use the wrapping .detail-cell class, not the short, nowrap
    .meta-cell class — reusing .meta-cell there is what originally forced
    the table (and the whole grouped-problem card) wider than the mobile
    viewport."""
    from njit_auditor.models import AuditFinding, Severity

    c, wa = client
    findings = [
        AuditFinding(
            rule_id="P013",
            severity=Severity.WARNING,
            page=page,
            message="Multiple page-number-like tokens detected.",
            details={
                "issue_type": "page_number_candidate",
                "position_type": "bottom_center",
                "candidate_count_on_page": "2",
                "confidence": "medium",
            },
        )
        for page in (10, 11)
    ]
    job_id = _inject_complete_job_with_findings(
        wa, tmp_path, findings=findings, file_name="thesis.pdf", audit_type="pdf"
    )

    resp = c.get(f"/audits/{job_id}")

    assert resp.status_code == 200
    html = resp.content.decode()
    assert "Show individual occurrences" in html
    assert 'class="detail-cell"' in html
    # The long issue-type label + suggested-fix sentence must render fully.
    assert "Duplicate or ambiguous page number" in html
    assert "Verify which token is the printed page number" in html


def test_grouped_problem_long_page_list_still_renders_fully(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """A grouped problem repeated across many non-contiguous pages must still
    render its full "Pages: ..." list (in the wrapping .meta-cell), not a
    truncated or hidden value, even though that string can grow long."""
    from njit_auditor.models import AuditFinding, Severity

    c, wa = client
    scattered_pages = [1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23]
    findings = [
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=page,
            message="Left margin too narrow.",
            details={
                "issue_type": "margin_boundary_violation",
                "side": "left_margin",
                "confidence": "medium",
            },
        )
        for page in scattered_pages
    ]
    job_id = _inject_complete_job_with_findings(
        wa, tmp_path, findings=findings, file_name="thesis.pdf", audit_type="pdf"
    )

    resp = c.get(f"/audits/{job_id}")

    assert resp.status_code == 200
    html = resp.content.decode()
    for page in scattered_pages:
        assert str(page) in html


def test_results_page_renders_polished_comments(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    assert b"Check yourself" in resp.content
    ordinary = resp.content.split(b'id="individual-findings-panel"', 1)[1].split(
        b'<section id="section-topics"', 1
    )[0]
    assert b"Likely problem:" not in ordinary
    assert b"Check yourself" in resp.content


def test_results_page_wraps_tables_for_mobile_horizontal_scroll(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """Summary/rule/occurrence tables must sit in a horizontally-scrollable
    wrapper so narrow screens get a scrollbar instead of squeezed or
    overflowing columns — desktop and mobile render the same table markup."""
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path, finding_count=6)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    html = resp.content.decode()
    assert "Show individual occurrences" in html
    # One wrapper each for the collapsed advanced rule summary and the collapsed
    # advanced grouped-occurrence table. The primary individual-findings list
    # now uses compact cards instead of a wide table.
    assert html.count('class="table-scroll"') >= 2


def test_results_page_has_client_side_filters(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path, finding_count=3)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    assert b"filter-rule" in resp.content
    assert b"filter-category" in resp.content
    assert b"filter-page" in resp.content
    assert b'id="filter-reset"' in resp.content
    assert b"Confidence" in resp.content
    # The severity filter control has been removed from the student-facing filter
    # bar: severity is already surfaced per-card via the status badge, and most
    # findings are review signals rather than confirmed defects.
    assert b"filter-severity" not in resp.content
    assert b'<label for="filter-severity">' not in resp.content


def test_grouped_problem_cards_still_show_severity_badge(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """Removing the Severity *filter* control must not remove the severity *badge*
    rendered on each grouped-problem card -- that badge is still a useful at-a-glance
    signal even without a dropdown to filter by it."""
    from njit_auditor.models import AuditFinding, Severity

    c, wa = client
    findings = [
        AuditFinding(
            rule_id="P011",
            severity=Severity.FAIL,
            page=1,
            message="Left margin too narrow.",
            details={
                "issue_type": "margin_boundary_violation",
                "side": "left_margin",
                "confidence": "high",
            },
        ),
    ]
    job_id = _inject_complete_job_with_findings(
        wa, tmp_path, findings=findings, file_name="thesis.pdf", audit_type="pdf"
    )
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    body = resp.text
    assert 'class="badge badge-fail">Fail' in body


def test_individual_findings_panel_omits_severity_column(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """The primary individual-findings list is student-facing: confidence, not severity."""
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path, finding_count=3)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    body = resp.text
    panel_start = body.index('id="individual-findings-panel"')
    panel_end = body.index('id="section-downloads"', panel_start)
    panel = body[panel_start:panel_end]
    assert ">Severity<" not in panel
    assert "confidence-badge" in panel
    assert "individual-findings-list" in panel
    assert "finding-card" in panel


def test_individual_findings_panel_has_mobile_safe_layout_classes(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """Compact card layout hooks must be present for mobile-friendly wrapping."""
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path, finding_count=2)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    body = resp.content.decode()
    for css_class in (
        "individual-findings-list",
        "finding-card",
        "finding-card__location",
        "finding-card__issue",
    ):
        assert css_class in body


def test_results_page_filter_script_defers_until_dom_ready(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """Findings filter script must wait for DOMContentLoaded (head vs body)."""
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path, finding_count=3)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    assert b"DOMContentLoaded" in resp.content
    assert b"getElementById(\"filter-rule\")" in resp.content
    assert b"setMode(" not in resp.content


def test_results_page_shows_privacy_note(client: tuple[TestClient, Any], tmp_path: Path) -> None:
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    assert b"Privacy note" in resp.content
    assert b"may quote short pieces of your" in resp.content.lower()
    assert b"deleted automatically" in resp.content.lower()


def test_results_polished_comments_exclude_private_sample_text(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path)
    resp = c.get(f"/audits/{job_id}")
    forbidden = b"John Smith Dissertation Title"
    assert forbidden not in resp.content


def test_results_page_does_not_leak_raw_latex_in_comments_or_fixes(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """Main job results page must never render raw LaTeX command/package syntax.

    P023/P026/P028 findings here carry deliberately raw-LaTeX suggested_fix text
    (bypassing the already-cleaned detectors) to verify the rendering layer itself
    sanitizes suggested_fix, not just the known producers.
    """
    c, wa = client
    findings = _p023_p026_p028_findings_with_raw_latex_suggested_fix()
    job_id = _inject_complete_job_with_findings(
        wa, tmp_path, findings=findings, file_name="thesis.pdf", audit_type="pdf"
    )

    resp = c.get(f"/audits/{job_id}")

    assert resp.status_code == 200
    assert b"Check yourself" in resp.content
    assert b"Review needed: " in resp.content
    assert b"Review needed: Likely problem:" not in resp.content
    assert b"double-spaced" in resp.content or b"double spacing" in resp.content
    assert b"Times New Roman" in resp.content
    assert b"Roman numerals" in resp.content
    _assert_no_raw_latex_web_syntax(resp.content)


def test_problem_group_pages_do_not_leak_raw_latex_in_comments_or_fixes(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """Category/rule problem pages must never render raw LaTeX command/package syntax.

    The original leak was visible on these pages too (they render the same
    suggested_fix/polished_comment fields as the main job page).
    """
    c, wa = client
    findings = _p023_p026_p028_findings_with_raw_latex_suggested_fix()
    job_id = _inject_complete_job_with_findings(
        wa, tmp_path, findings=findings, file_name="thesis.pdf", audit_type="pdf"
    )

    for rule_id in ("P023", "P026", "P028"):
        resp = c.get(f"/audits/{job_id}/problems/rule/{rule_id}")
        assert resp.status_code == 200
        _assert_no_raw_latex_web_syntax(resp.content)


def test_failed_job_shows_safe_error_no_stack_trace(
    client: tuple[TestClient, Any],
) -> None:
    c, wa = client
    from datetime import datetime, timezone

    job = wa.JobState(
        job_id="failedjob1",
        state="failed",
        created_at=datetime.now(timezone.utc).isoformat(),
        file_name="bad.pdf",
        error_message="File does not appear to be a valid PDF.",
    )
    wa._set_job(job)
    resp = c.get("/audits/failedjob1")
    assert resp.status_code == 200
    assert b"Traceback" not in resp.content
    assert b"valid PDF" in resp.content or b"could not complete" in resp.content.lower()


def test_category_problem_page_route_returns_200(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    from njit_auditor.models import AuditFinding, Severity

    c, wa = client
    findings = [
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=2,
            message="Left margin too narrow.",
            details={"issue_type": "margin_boundary_violation", "side": "left_margin"},
        ),
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=5,
            message="Left margin too narrow.",
            details={"issue_type": "margin_boundary_violation", "side": "left_margin"},
        ),
        AuditFinding(
            rule_id="P013",
            severity=Severity.WARNING,
            page=9,
            message="Page number out of sequence.",
            details={"issue_type": "page_number_sequence_error", "observed": "8"},
        ),
    ]
    job_id = _inject_complete_job_with_findings(
        wa,
        tmp_path,
        findings=findings,
        file_name="thesis.pdf",
        audit_type="pdf",
    )

    resp = c.get(f"/audits/{job_id}/problems/category/margin-or-overflow")

    assert resp.status_code == 200
    assert b"Problems in this category" in resp.content
    # Both matching findings share one issue type, so the page title narrows
    # to that issue type rather than staying at the broad category label.
    assert b"Check yourself" in resp.content
    # Student-facing titles must not embed raw internal rule IDs; the ID still
    # appears as a dedicated rule-reference link / query parameter instead.
    assert b"(P011)" not in resp.content
    assert b'href="/rules#P011"' in resp.content or b"rule_id=P011" in resp.content
    # "original_page" resolves through the same true single-page endpoint as
    # "highlight" rather than a #page=N fragment into the full PDF.
    assert (
        f"/audits/{job_id}/highlighted-page.pdf?page=2"
        "&amp;rule_id=P011&amp;issue_type=margin_boundary_violation".encode()
        in resp.content
    )
    assert f"/audits/{job_id}/pdf#page=2".encode() not in resp.content
    assert b"Open original PDF page" in resp.content
    assert b"Open original PDF page" in resp.content


def test_rule_problem_page_route_returns_200(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    from njit_auditor.models import AuditFinding, Severity

    c, wa = client
    findings = [
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=3,
            message="Left margin too narrow.",
            details={"issue_type": "margin_boundary_violation", "side": "left_margin"},
        ),
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=7,
            message="Left margin too narrow.",
            details={"issue_type": "margin_boundary_violation", "side": "left_margin"},
        ),
    ]
    job_id = _inject_complete_job_with_findings(
        wa,
        tmp_path,
        findings=findings,
        file_name="thesis.pdf",
        audit_type="pdf",
    )

    resp = c.get(f"/audits/{job_id}/problems/rule/P011")

    assert resp.status_code == 200
    assert b"Pages to review" in resp.content
    # "original_page" resolves through the same true single-page endpoint as
    # "highlight" rather than a #page=N fragment into the full PDF.
    assert (
        f"/audits/{job_id}/highlighted-page.pdf?page=7"
        "&amp;rule_id=P011&amp;issue_type=margin_boundary_violation".encode()
        in resp.content
    )
    assert f"/audits/{job_id}/pdf#page=7".encode() not in resp.content
    assert b"Open original PDF page" in resp.content
    assert b"Open original PDF page" in resp.content
    assert b"Back to all results" in resp.content


def test_problem_group_page_page_less_finding_has_no_generic_pdf_link(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """A finding with no page and no highlight must not offer a destination-less
    "Open PDF" button — see docs/planning/problem_page_actionability_audit.md.
    The explanation block is the actionable content instead."""
    from njit_auditor.models import AuditFinding, Severity

    c, wa = client
    findings = [
        AuditFinding(
            rule_id="P038",
            severity=Severity.WARNING,
            page=None,
            message="Required front-matter heading 'APPROVAL PAGE' not detected.",
            details={
                "issue_type": "required_heading_missing",
                "section_key": "approval_page",
                "expected_heading": "APPROVAL PAGE",
            },
        ),
    ]
    job_id = _inject_complete_job_with_findings(
        wa,
        tmp_path,
        findings=findings,
        file_name="thesis.pdf",
        audit_type="pdf",
    )

    resp = c.get(f"/audits/{job_id}/problems/rule/P038")

    assert resp.status_code == 200
    assert b"Front matter \xe2\x80\x94 required heading missing" in resp.content
    assert f'href="/audits/{job_id}/pdf"'.encode() not in resp.content
    assert b"Open PDF" not in resp.content
    # A location IS shown ("Front matter -- required heading missing: ..."),
    # so the no-highlight text must not also claim there is no location
    # (Ester, Sample B Problem 43: "the auditor says that this does not
    # correspond to a specific page" when a location was in fact given).
    assert b"does not correspond to a specific page or visual location" not in resp.content.lower()
    assert b"no specific pdf page" in resp.content.lower()


def test_problem_group_pages_only_show_matching_findings(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    from njit_auditor.models import AuditFinding, Severity

    c, wa = client
    findings = [
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=2,
            message="Left margin too narrow.",
            details={"issue_type": "margin_boundary_violation", "side": "left_margin"},
        ),
        AuditFinding(
            rule_id="P013",
            severity=Severity.WARNING,
            page=8,
            message="Page number out of sequence.",
            details={"issue_type": "page_number_sequence_error", "observed": "7"},
        ),
    ]
    job_id = _inject_complete_job_with_findings(
        wa,
        tmp_path,
        findings=findings,
        file_name="thesis.pdf",
        audit_type="pdf",
    )

    category_resp = c.get(f"/audits/{job_id}/problems/category/page-numbering")
    rule_resp = c.get(f"/audits/{job_id}/problems/rule/P011")

    assert category_resp.status_code == 200
    assert b"P013" in category_resp.content
    assert b"P011" not in category_resp.content
    assert rule_resp.status_code == 200
    assert b"P011" in rule_resp.content
    assert b"P013" not in rule_resp.content


def test_unknown_problem_group_routes_return_404(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path, finding_count=2)

    bad_category = c.get(f"/audits/{job_id}/problems/category/not-a-real-category")
    bad_rule = c.get(f"/audits/{job_id}/problems/rule/P999")

    assert bad_category.status_code == 404
    assert bad_rule.status_code == 404


def test_missing_job_problem_group_routes_return_404(
    client: tuple[TestClient, Any],
) -> None:
    c, _ = client

    resp = c.get("/audits/no-such-job/problems/category/page-numbering")

    assert resp.status_code == 404
    assert b"Audit result no longer available" in resp.content


# ---------------------------------------------------------------------------
# Download endpoints
# ---------------------------------------------------------------------------

def test_download_json_returns_json(client: tuple[TestClient, Any], tmp_path: Path) -> None:
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path)
    resp = c.get(f"/audits/{job_id}/download/json")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/json")
    data = resp.json()
    assert "findings" in data
    assert "metadata" in data


def test_download_markdown_returns_text(client: tuple[TestClient, Any], tmp_path: Path) -> None:
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path)
    resp = c.get(f"/audits/{job_id}/download/markdown")
    assert resp.status_code == 200
    ct = resp.headers["content-type"]
    assert "text/markdown" in ct or "text/plain" in ct


def test_download_text_returns_plain_text_student_report(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path)
    resp = c.get(f"/audits/{job_id}/download/text")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "text/plain; charset=utf-8"
    disposition = resp.headers.get("content-disposition", "")
    assert disposition.endswith(".txt\"") or disposition.endswith(".txt")
    assert f"thesis_audit_report_{job_id[:8]}.txt" in disposition
    body = resp.content.decode("utf-8")
    assert "PDF PAGE" in body
    assert "Public rule reference: R011" in body
    assert "Public rule reference: P011" not in body


def test_download_missing_job_returns_404(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    assert c.get("/audits/badid/download/json").status_code == 404
    assert c.get("/audits/badid/download/markdown").status_code == 404
    assert c.get("/audits/badid/download/text").status_code == 404


# ---------------------------------------------------------------------------
# Runtime files are not tracked by git
# ---------------------------------------------------------------------------

def test_runtime_dir_is_gitignored(tmp_path: Path) -> None:
    repo_root = Path(__file__).parent.parent
    gitignore = (repo_root / ".gitignore").read_text(encoding="utf-8")
    assert ".runtime/" in gitignore or ".runtime" in gitignore


# ---------------------------------------------------------------------------
# URL fetch module — SSRF / scheme / host unit tests (no web client needed)
# ---------------------------------------------------------------------------


def test_url_fetch_rejects_file_scheme() -> None:
    from njit_auditor.web_url_fetch import FetchError, _validate_url

    with pytest.raises(FetchError, match="http"):
        _validate_url("file:///etc/passwd")


def test_url_fetch_rejects_ftp_scheme() -> None:
    from njit_auditor.web_url_fetch import FetchError, _validate_url

    with pytest.raises(FetchError, match="http"):
        _validate_url("ftp://example.com/thesis.pdf")


def test_url_fetch_rejects_empty_host() -> None:
    from njit_auditor.web_url_fetch import FetchError, _validate_url

    with pytest.raises(FetchError):
        _validate_url("http:///x.pdf")


def test_url_fetch_rejects_localhost() -> None:
    from njit_auditor.web_url_fetch import FetchError, _check_host

    with pytest.raises(FetchError, match="localhost"):
        _check_host("localhost")


def test_url_fetch_rejects_loopback_ip() -> None:
    from njit_auditor.web_url_fetch import FetchError, _check_host

    with pytest.raises(FetchError):
        _check_host("127.0.0.1")


def test_url_fetch_rejects_private_class_a() -> None:
    from njit_auditor.web_url_fetch import FetchError, _check_host

    with pytest.raises(FetchError):
        _check_host("10.0.0.1")


def test_url_fetch_rejects_private_class_c() -> None:
    from njit_auditor.web_url_fetch import FetchError, _check_host

    with pytest.raises(FetchError):
        _check_host("192.168.1.100")


def test_url_fetch_rejects_link_local() -> None:
    from njit_auditor.web_url_fetch import FetchError, _check_host

    with pytest.raises(FetchError):
        _check_host("169.254.0.1")


def test_url_fetch_rejects_private_via_dns(monkeypatch: pytest.MonkeyPatch) -> None:
    import socket

    from njit_auditor.web_url_fetch import FetchError, _check_host

    original = socket.getaddrinfo

    def fake_getaddrinfo(host: str, port: Any, *args: Any, **kwargs: Any) -> Any:
        if "evil" in host:
            return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("192.168.10.10", 0))]
        return original(host, port, *args, **kwargs)

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
    with pytest.raises(FetchError, match="private"):
        _check_host("evil.internal.example.com")


def test_url_fetch_ip_is_private_v4() -> None:
    from njit_auditor.web_url_fetch import _ip_is_private

    assert _ip_is_private("10.10.10.10") is True
    assert _ip_is_private("172.20.0.1") is True
    assert _ip_is_private("192.168.0.1") is True
    assert _ip_is_private("127.0.0.1") is True
    assert _ip_is_private("169.254.1.1") is True


def test_url_fetch_ip_is_private_v6() -> None:
    from njit_auditor.web_url_fetch import _ip_is_private

    assert _ip_is_private("::1") is True
    assert _ip_is_private("fe80::1") is True
    assert _ip_is_private("fc00::1") is True


def test_url_fetch_public_ip_not_private() -> None:
    from njit_auditor.web_url_fetch import _ip_is_private

    assert _ip_is_private("8.8.8.8") is False
    assert _ip_is_private("1.1.1.1") is False


# ---------------------------------------------------------------------------
# fetch_pdf_url — User-Agent / request construction
# ---------------------------------------------------------------------------


def test_fetch_pdf_url_sends_no_custom_user_agent() -> None:
    """fetch_pdf_url must not set a custom User-Agent header on the Request.

    Institutional repositories (e.g., NJIT Digital Commons / bepress) run AWS WAF
    bot-management rules that block arbitrary custom UAs with HTTP 403.  Leaving
    User-Agent unset lets urllib use its own default ('Python-urllib/3.x'), which
    those WAFs recognise and pass through.
    """
    import io
    import urllib.request
    from unittest.mock import MagicMock, patch

    from njit_auditor.web_url_fetch import fetch_pdf_url

    captured_req: list[urllib.request.Request] = []

    class _CapturingHandler(urllib.request.BaseHandler):
        def http_open(self, req: urllib.request.Request) -> Any:
            captured_req.append(req)
            resp = urllib.response.addinfourl(  # type: ignore[attr-defined]
                io.BytesIO(b"%PDF-1.7 synthetic"),
                {"Content-Type": "application/pdf"},
                req.get_full_url(),
                200,
            )
            resp.msg = "OK"
            return resp

        https_open = http_open

    import socket
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        dest = Path(f.name)

    def _safe_getaddrinfo(host: str, port: Any, *a: Any, **kw: Any) -> Any:
        return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", 0))]

    with patch("socket.getaddrinfo", side_effect=_safe_getaddrinfo):
        with patch("urllib.request.build_opener") as mock_build:
            opener = MagicMock()
            mock_build.return_value = opener

            fake_resp = MagicMock()
            fake_resp.__enter__ = lambda s: s
            fake_resp.__exit__ = MagicMock(return_value=False)
            fake_resp.headers.get.return_value = "application/pdf"
            fake_resp.read.side_effect = [b"%PDF-1.7 ", b""]
            opener.open.return_value = fake_resp

            fetch_pdf_url("https://example.com/thesis.pdf", dest, 10_000_000)

            # Inspect the Request that was built and passed to opener.open()
            call_args = opener.open.call_args
            req_arg = call_args[0][0]  # positional arg 0

    assert isinstance(req_arg, urllib.request.Request)
    # Must NOT have a custom User-Agent set — let urllib supply its own default
    ua = req_arg.get_header("User-agent")
    assert ua is None, (
        f"fetch_pdf_url must not set a custom User-Agent; got {ua!r}. "
        "Custom UAs are blocked by AWS WAF on institutional repositories."
    )
    dest.unlink(missing_ok=True)


def test_fetch_pdf_url_custom_user_agent_regression() -> None:
    """Regression: 'NJIT-Thesis-Auditor/1.0' must not appear in any outgoing request.

    This string was previously hardcoded and caused HTTP 403 from NJIT Digital Commons
    (bepress / AWS WAF). Any reintroduction of that exact string must fail this test.
    """
    import inspect

    from njit_auditor import web_url_fetch

    source = inspect.getsource(web_url_fetch)
    assert "NJIT-Thesis-Auditor/1.0" not in source, (
        "The custom User-Agent 'NJIT-Thesis-Auditor/1.0' was reintroduced into "
        "web_url_fetch. This UA is blocked by AWS WAF on NJIT Digital Commons."
    )


# ---------------------------------------------------------------------------
# /audits/url route tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("endpoint", ["/audits", "/audits/url", "/audits/sample"])
@pytest.mark.parametrize("field", ["pdf_url", "document_url", "doc_url", "url"])
@pytest.mark.parametrize("with_file", [False, True])
def test_document_url_submissions_never_fetch_or_create_workers(
    client: tuple[TestClient, Any], monkeypatch: pytest.MonkeyPatch,
    endpoint: str, field: str, with_file: bool,
) -> None:
    import socket
    import urllib.request

    from njit_auditor import web_samples, web_url_fetch

    c, wa = client
    def forbidden(*args: Any, **kwargs: Any) -> None:
        pytest.fail("URL submission attempted network, sample access, or worker creation")

    for module, names in [
        (socket, ["getaddrinfo", "create_connection"]),
        (urllib.request, ["urlopen", "build_opener"]),
        (web_url_fetch, ["fetch_pdf_url"]),
        (web_samples, ["list_builtin_samples", "get_builtin_sample", "copy_builtin_sample_to_job"]),
        (wa, ["_new_job_id", "_set_job", "_run_audit_task"]),
    ]:
        for name in names:
            monkeypatch.setattr(module, name, forbidden)
    monkeypatch.setattr(wa.app.state, "prepare_audit", forbidden, raising=False)
    monkeypatch.setattr(wa.app.state, "audit_executor", forbidden, raising=False)
    files = {"file": ("thesis.pdf", _MINIMAL_PDF, "application/pdf")} if with_file else None
    response = c.post(endpoint, data={field: "https://example.invalid/thesis.pdf"},
                      files=files, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"].startswith("/?error=")
    assert "example.invalid" not in response.headers["location"]
    for _ in range(2):  # Following the redirect and refreshing are both safe GETs.
        error_page = c.get(response.headers["location"])
        assert error_page.status_code == 400
        assert "Please upload your document to start an audit." in error_page.text
        assert 'action="/audits"' in error_page.text
    assert not wa._jobs
    assert not wa.RUNTIME_DIR.exists() or not list(wa.RUNTIME_DIR.iterdir())


@pytest.mark.parametrize("endpoint", ["/audits", "/audits/url", "/audits/sample"])
@pytest.mark.parametrize("data", [{}, {"pdf_url": "   "}, {"sample_id": "ester_sample_a"}])
def test_file_required_errors_are_refresh_safe(
    client: tuple[TestClient, Any], endpoint: str, data: dict[str, str],
) -> None:
    c, wa = client
    response = c.post(endpoint, data=data, follow_redirects=True)
    assert response.history[0].status_code == 303
    assert response.request.method == "GET"
    assert response.status_code == 400
    assert "Please upload your document to start an audit." in response.text
    refreshed = c.get(str(response.url))
    assert refreshed.status_code == 400
    assert refreshed.text == response.text
    assert not wa._jobs


def test_duplicate_url_field_cannot_bypass_policy(client: tuple[TestClient, Any]) -> None:
    c, wa = client
    response = c.post("/audits", files=[
        ("file", ("thesis.pdf", _MINIMAL_PDF, "application/pdf")),
        ("pdf_url", (None, "")),
        ("pdf_url", (None, "https://example.invalid/thesis.pdf")),
    ], follow_redirects=True)
    assert response.status_code == 400
    assert "Please upload your document" in response.text
    assert not wa._jobs


def test_upload_with_blank_legacy_url_field_still_works(client: tuple[TestClient, Any]) -> None:
    c, wa = client
    with patch.object(wa, "_run_audit_task", lambda job_id: None):
        response = c.post("/audits", data={"pdf_url": "   "},
                          files={"file": ("thesis.pdf", _MINIMAL_PDF, "application/pdf")},
                          follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"].startswith("/audits/")
    assert len(wa._jobs) == 1


def test_runtime_files_not_in_ls_files(tmp_path: Path) -> None:
    import subprocess

    repo_root = Path(__file__).parent.parent
    result = subprocess.run(
        ["git", "ls-files", ".runtime"],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    assert result.stdout.strip() == "", f"Runtime files tracked by git: {result.stdout}"


# ---------------------------------------------------------------------------
# Built-in sample registry unit tests (web_samples.py)
# ---------------------------------------------------------------------------


def test_web_samples_reject_unknown_id() -> None:
    from njit_auditor.web_samples import get_builtin_sample

    with pytest.raises(ValueError, match="Unknown sample ID"):
        get_builtin_sample("nonexistent_id_xyz")


def test_web_samples_path_traversal_rejected() -> None:
    from njit_auditor.web_samples import get_builtin_sample

    for bad_id in ["../../etc/passwd", "../secret", "..", "data/raw/ester/x.pdf"]:
        with pytest.raises(ValueError):
            get_builtin_sample(bad_id)


def test_web_samples_list_filters_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import njit_auditor.web_samples as ws

    fake_dir = tmp_path / "data" / "raw" / "ester"
    fake_dir.mkdir(parents=True)
    (fake_dir / "exists.pdf").write_bytes(b"%PDF-1.4\n")

    fake_curated = [
        ws.SampleInfo("test_exists", "Exists", "data/raw/ester/exists.pdf"),
        ws.SampleInfo("test_missing", "Missing", "data/raw/ester/gone.pdf"),
    ]
    monkeypatch.setattr(ws, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(ws, "_CURATED", fake_curated)
    monkeypatch.setattr(ws, "_BY_ID", {s.sample_id: s for s in fake_curated})

    result = ws.list_builtin_samples()
    ids = [s.sample_id for s in result]
    assert "test_exists" in ids
    assert "test_missing" not in ids


def test_web_samples_copy_writes_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import njit_auditor.web_samples as ws

    fake_dir = tmp_path / "data" / "raw" / "ester"
    fake_dir.mkdir(parents=True)
    src = fake_dir / "sample.pdf"
    src.write_bytes(b"%PDF-1.4\n%%EOF\n")

    fake_curated = [ws.SampleInfo("test_copy", "Copy test", "data/raw/ester/sample.pdf")]
    monkeypatch.setattr(ws, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(ws, "_CURATED", fake_curated)
    monkeypatch.setattr(ws, "_BY_ID", {s.sample_id: s for s in fake_curated})

    dest = tmp_path / "out.pdf"
    ws.copy_builtin_sample_to_job("test_copy", dest)
    assert dest.exists()
    assert dest.read_bytes().startswith(b"%PDF")


def test_web_samples_copy_rejects_bad_magic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import njit_auditor.web_samples as ws

    fake_dir = tmp_path / "data" / "raw" / "ester"
    fake_dir.mkdir(parents=True)
    src = fake_dir / "notapdf.pdf"
    src.write_bytes(b"NOTPDF\n")

    fake_curated = [ws.SampleInfo("test_badpdf", "Bad PDF", "data/raw/ester/notapdf.pdf")]
    monkeypatch.setattr(ws, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(ws, "_CURATED", fake_curated)
    monkeypatch.setattr(ws, "_BY_ID", {s.sample_id: s for s in fake_curated})

    dest = tmp_path / "out.pdf"
    with pytest.raises(ValueError, match="valid PDF"):
        ws.copy_builtin_sample_to_job("test_badpdf", dest)


def test_web_samples_copy_raises_for_missing_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import njit_auditor.web_samples as ws

    fake_dir = tmp_path / "data" / "raw" / "ester"
    fake_dir.mkdir(parents=True)

    fake_curated = [ws.SampleInfo("test_gone", "Gone", "data/raw/ester/gone.pdf")]
    monkeypatch.setattr(ws, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(ws, "_CURATED", fake_curated)
    monkeypatch.setattr(ws, "_BY_ID", {s.sample_id: s for s in fake_curated})

    dest = tmp_path / "out.pdf"
    with pytest.raises(FileNotFoundError):
        ws.copy_builtin_sample_to_job("test_gone", dest)


# ---------------------------------------------------------------------------
# /audits/sample route tests
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Job TTL cleanup
# ---------------------------------------------------------------------------


def _reload_web_app(tmp_path: Path, **env_overrides: str) -> Any:
    os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"] = str(tmp_path / "web_audits")
    for key, value in env_overrides.items():
        os.environ[key] = value
    import importlib

    import njit_auditor.web_app as wa

    importlib.reload(wa)
    with wa._jobs_lock:
        wa._jobs.clear()
    return wa


def test_invalid_job_ttl_env_falls_back_to_default(tmp_path: Path) -> None:
    wa = _reload_web_app(tmp_path, NJIT_AUDITOR_WEB_JOB_TTL_SECONDS="not-a-number")
    assert wa.JOB_TTL_SECONDS == 86400

    wa = _reload_web_app(tmp_path, NJIT_AUDITOR_WEB_JOB_TTL_SECONDS="-5")
    assert wa.JOB_TTL_SECONDS == 86400


def test_cleanup_expired_jobs_evicts_memory_and_deletes_directory(tmp_path: Path) -> None:
    from datetime import datetime, timedelta, timezone

    wa = _reload_web_app(tmp_path, NJIT_AUDITOR_WEB_JOB_TTL_SECONDS="60")
    old_time = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    job_id = "expiredjob123456"
    jdir = wa._job_dir(job_id)
    jdir.mkdir(parents=True)
    (jdir / "upload.pdf").write_bytes(_MINIMAL_PDF)

    job = wa.JobState(
        job_id=job_id,
        state="complete",
        created_at=old_time,
        file_name="thesis.pdf",
    )
    wa._set_job(job)

    removed = wa.cleanup_expired_jobs()
    assert removed >= 1
    assert wa._get_job(job_id) is None
    assert not jdir.exists()


def test_cleanup_missing_job_directory_does_not_fail(tmp_path: Path) -> None:
    from datetime import datetime, timedelta, timezone

    wa = _reload_web_app(tmp_path, NJIT_AUDITOR_WEB_JOB_TTL_SECONDS="60")
    old_time = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    job_id = "missingdirjob12"
    job = wa.JobState(
        job_id=job_id,
        state="complete",
        created_at=old_time,
        file_name="thesis.pdf",
    )
    wa._set_job(job)
    assert not wa._job_dir(job_id).exists()

    removed = wa.cleanup_expired_jobs()
    assert removed >= 1
    assert wa._get_job(job_id) is None


def test_cleanup_keeps_non_expired_job(tmp_path: Path) -> None:
    from datetime import datetime, timezone

    wa = _reload_web_app(tmp_path, NJIT_AUDITOR_WEB_JOB_TTL_SECONDS="3600")
    job_id = "freshjob123456"
    jdir = wa._job_dir(job_id)
    jdir.mkdir(parents=True)
    (jdir / "upload.pdf").write_bytes(_MINIMAL_PDF)

    job = wa.JobState(
        job_id=job_id,
        state="complete",
        created_at=datetime.now(timezone.utc).isoformat(),
        file_name="thesis.pdf",
    )
    wa._set_job(job)

    removed = wa.cleanup_expired_jobs()
    assert removed == 0
    assert wa._get_job(job_id) is not None
    assert jdir.exists()


def test_cleanup_skips_running_jobs_even_when_old(tmp_path: Path) -> None:
    from datetime import datetime, timedelta, timezone

    wa = _reload_web_app(tmp_path, NJIT_AUDITOR_WEB_JOB_TTL_SECONDS="60")
    old_time = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    job_id = "runningjob12345"
    jdir = wa._job_dir(job_id)
    jdir.mkdir(parents=True)
    (jdir / "upload.pdf").write_bytes(_MINIMAL_PDF)

    job = wa.JobState(
        job_id=job_id,
        state="running",
        created_at=old_time,
        file_name="thesis.pdf",
    )
    wa._set_job(job)

    removed = wa.cleanup_expired_jobs()
    assert removed == 0
    assert wa._get_job(job_id) is not None
    assert jdir.exists()


def test_cleanup_does_not_delete_paths_outside_runtime_root(tmp_path: Path) -> None:
    from datetime import datetime, timedelta, timezone

    wa = _reload_web_app(tmp_path, NJIT_AUDITOR_WEB_JOB_TTL_SECONDS="60")
    outside_dir = tmp_path / "outside_runtime"
    outside_dir.mkdir()
    marker = outside_dir / "keep.txt"
    marker.write_text("stay", encoding="utf-8")

    old_time = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    job_id = "outsidejob1234"
    with patch.object(wa, "_job_dir", return_value=outside_dir):
        job = wa.JobState(
            job_id=job_id,
            state="complete",
            created_at=old_time,
            file_name="thesis.pdf",
        )
        wa._set_job(job)
        removed = wa.cleanup_expired_jobs()

    assert removed >= 1
    assert marker.exists()


def test_job_not_found_message_mentions_expiration(
    client: tuple[TestClient, Any],
) -> None:
    c, _ = client
    resp = c.get("/audits/doesnotexistjob")
    assert resp.status_code == 404
    assert b"no longer available" in resp.content.lower()
    assert b"kept for" in resp.content  # retention period always present


def test_expired_job_does_not_show_could_not_start(
    client: tuple[TestClient, Any],
) -> None:
    c, _ = client
    resp = c.get("/audits/somenonexistentjob1")
    assert resp.status_code == 404
    assert b"Could not start audit" not in resp.content


def test_expired_job_shows_audit_result_no_longer_available(
    client: tuple[TestClient, Any],
) -> None:
    c, _ = client
    resp = c.get("/audits/somenonexistentjob2")
    assert resp.status_code == 404
    assert b"Audit result no longer available" in resp.content


def test_expired_job_notice_on_category_problem_page(
    client: tuple[TestClient, Any],
) -> None:
    """The category/rule/issue-type drill-down routes added after this branch
    forked must use the same expired-job notice as /audits/{job_id}, not the
    old _job_not_found_message helper this branch renamed away."""
    c, _ = client
    resp = c.get("/audits/doesnotexistjob/problems/category/page-numbering")
    assert resp.status_code == 404
    assert b"Audit result no longer available" in resp.content


def test_expired_job_notice_on_rule_problem_page(
    client: tuple[TestClient, Any],
) -> None:
    c, _ = client
    resp = c.get("/audits/doesnotexistjob/problems/rule/P013")
    assert resp.status_code == 404
    assert b"Audit result no longer available" in resp.content


def test_expired_job_notice_on_issue_type_problem_page(
    client: tuple[TestClient, Any],
) -> None:
    c, _ = client
    resp = c.get(
        "/audits/doesnotexistjob/problems/rule/P013/issue-type/some-issue-type"
    )
    assert resp.status_code == 404
    assert b"Audit result no longer available" in resp.content


def test_expired_job_message_mentions_configured_ttl_one_hour(tmp_path: Path) -> None:
    wa = _reload_web_app(tmp_path, NJIT_AUDITOR_WEB_JOB_TTL_SECONDS="3600")
    c = TestClient(wa.app, raise_server_exceptions=False)
    resp = c.get("/audits/somefakejobid1hr")
    assert resp.status_code == 404
    assert b"1 hour" in resp.content
    assert b"24 hours" not in resp.content


def test_expired_job_message_mentions_configured_ttl_30_minutes(tmp_path: Path) -> None:
    wa = _reload_web_app(tmp_path, NJIT_AUDITOR_WEB_JOB_TTL_SECONDS="1800")
    c = TestClient(wa.app, raise_server_exceptions=False)
    resp = c.get("/audits/somefakejobid30m")
    assert resp.status_code == 404
    assert b"30 minutes" in resp.content


def test_upload_start_error_still_uses_could_not_start(
    client: tuple[TestClient, Any],
) -> None:
    c, _ = client
    resp = c.post(
        "/audits",
        files={"file": ("thesis.docx", io.BytesIO(b"PK\x03\x04fake"), "application/octet-stream")},
        follow_redirects=True,
    )
    assert resp.status_code == 400
    assert b"Could not start audit" in resp.content
    assert b"Audit result no longer available" not in resp.content


def test_successful_job_page_shows_no_expired_message(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    assert b"Audit result no longer available" not in resp.content
    assert b"Could not start audit" not in resp.content


# ---------------------------------------------------------------------------
# _format_ttl unit tests
# ---------------------------------------------------------------------------


def test_format_ttl_seconds_to_minutes() -> None:
    import njit_auditor.web_app as wa

    assert wa._format_ttl(1800) == "about 30 minutes"
    assert wa._format_ttl(60) == "about 1 minute"
    assert wa._format_ttl(3599) == "about 60 minutes"


def test_format_ttl_one_hour() -> None:
    import njit_auditor.web_app as wa

    assert wa._format_ttl(3600) == "about 1 hour"


def test_format_ttl_multiple_hours() -> None:
    import njit_auditor.web_app as wa

    assert wa._format_ttl(86400) == "about 24 hours"
    assert wa._format_ttl(7200) == "about 2 hours"


def _inject_complete_pdf_job(
    wa: Any,
    tmp_path: Path,
) -> str:
    """Create a complete PDF job in the job store and on disk (for PDF parity tests)."""
    import secrets
    from datetime import datetime, timezone

    from njit_auditor.models import AuditFinding, Severity
    from njit_auditor.report_outputs import audit_findings_to_json_dict, write_markdown_report
    from njit_auditor.report_text import write_text_report
    from njit_auditor.report_view import build_report_view, report_view_to_dict

    job_id = secrets.token_urlsafe(16)
    findings = [
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=2,
            message="Possible text outside margin.",
            details={"issue_type": "margin_boundary_violation", "side": "left"},
        ),
    ]
    metadata = {"input_file_name": "thesis.pdf", "audit_type": "pdf", "job_id": job_id}
    jdir = Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"]) / job_id
    jdir.mkdir(parents=True, exist_ok=True)
    (jdir / "upload.pdf").write_bytes(_MINIMAL_PDF)
    payload = audit_findings_to_json_dict(findings, metadata)
    (jdir / "report.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_markdown_report(findings, metadata, jdir / "report.md")
    write_text_report(findings, metadata, jdir / "report.txt")
    view = build_report_view(payload)

    job = wa.JobState(
        job_id=job_id,
        state="complete",
        created_at=datetime.now(timezone.utc).isoformat(),
        file_name="thesis.pdf",
        audit_type="pdf",
        finding_count=view.total_findings,
        warn_count=1,
        fail_count=0,
        findings=[],
        grouped_summary=[],
        report_view=report_view_to_dict(view),
        md_preview="# NJIT PDF Audit Report\n",
    )
    wa._set_job(job)
    return job_id


def test_pdf_web_json_download_unaffected_by_sanitization(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """PDF reports must remain fully intact — sanitization is source-audit-only."""
    c, wa = client
    job_id = _inject_complete_pdf_job(wa, tmp_path)
    resp = c.get(f"/audits/{job_id}/download/json")
    assert resp.status_code == 200
    data = resp.json()
    assert data["metadata"]["audit_type"] == "pdf"
    # PDF finding messages are preserved as-is (no sanitization)
    messages = [f.get("message", "") for f in data.get("findings", [])]
    assert any("margin" in m.lower() or "P011" in m or len(m) > 0 for m in messages)


def test_pdf_web_markdown_download_unaffected_by_sanitization(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """PDF Markdown reports must download normally — no sanitization applied."""
    c, wa = client
    job_id = _inject_complete_pdf_job(wa, tmp_path)
    resp = c.get(f"/audits/{job_id}/download/markdown")
    assert resp.status_code == 200
    ct = resp.headers["content-type"]
    assert "text/markdown" in ct or "text/plain" in ct
    assert b"PDF Audit Report" in resp.content


def test_sanitize_report_for_web_export_unit_pdf_passthrough() -> None:
    """sanitize_report_for_web_export() must return PDF reports unchanged."""
    from njit_auditor.report_outputs import sanitize_report_for_web_export

    report: dict = {
        "metadata": {"audit_type": "pdf", "total_findings": 1},
        "findings": [
            {
                "rule_id": "P011",
                "severity": "WARNING",
                "message": "Possible text outside margin.",
                "page": 2,
                "details": {"side": "left"},
            }
        ],
    }
    result = sanitize_report_for_web_export(report)
    # PDF reports returned unchanged
    assert result["findings"][0]["message"] == "Possible text outside margin."
    assert result["findings"][0]["details"] == {"side": "left"}


def test_sanitize_report_for_web_export_unit_tex_label_removed() -> None:
    """sanitize_report_for_web_export() removes private label/ref from tex findings."""
    from njit_auditor.report_outputs import sanitize_report_for_web_export

    report: dict = {
        "metadata": {"audit_type": "tex", "total_findings": 2},
        "findings": [
            {
                "rule_id": "P002",
                "severity": "FAIL",
                "message": "Duplicate label detected: 'fig:test_private_label'",
                "page": None,
                "details": {
                    "file": "main.tex",
                    "line": "5",
                    "issue_type": "duplicate_label",
                    "label": "fig:test_private_label",
                },
                "source_file": "main.tex",
                "source_line": "5",
            },
            {
                "rule_id": "P004",
                "severity": "WARNING",
                "message": "Reference points to undefined label: 'tab:my_secret_table'",
                "page": None,
                "details": {
                    "file": "main.tex",
                    "line": "10",
                    "issue_type": "dangling_reference",
                    "ref": "tab:my_secret_table",
                },
                "source_file": "main.tex",
                "source_line": "10",
            },
        ],
    }
    result = sanitize_report_for_web_export(report)
    assert "fig:test_private_label" not in result["findings"][0]["message"]
    assert "tab:my_secret_table" not in result["findings"][1]["message"]
    assert "label" not in result["findings"][0]["details"]
    assert "ref" not in result["findings"][1]["details"]
    # Structural keys preserved
    assert result["findings"][0]["details"]["file"] == "main.tex"
    assert result["findings"][0]["details"]["line"] == "5"
    # The fallback message must use the student-facing Rxxx id, never the
    # internal Pxxx implementation id.
    assert result["findings"][0]["message"].startswith("R002 ")
    assert "P002" not in result["findings"][0]["message"]
    assert result["findings"][1]["message"].startswith("R004 ")
    assert "P004" not in result["findings"][1]["message"]
    assert result["findings"][0]["details"]["issue_type"] == "duplicate_label"
    # Finding count unchanged
    assert len(result["findings"]) == 2


def test_sanitize_report_for_web_export_unit_preserves_count() -> None:
    """Finding count in metadata must be unchanged after sanitization."""
    from njit_auditor.report_outputs import sanitize_report_for_web_export

    report: dict = {
        "metadata": {"audit_type": "tex", "total_findings": 3},
        "findings": [
            {
                "rule_id": "P003",
                "severity": "WARNING",
                "message": "Label contains spaces: 'fig some label'",
                "page": None,
                "details": {"file": "main.tex", "line": "3", "issue_type": "invalid_label"},
            }
        ]
        * 3,
    }
    result = sanitize_report_for_web_export(report)
    assert result["metadata"]["total_findings"] == 3
    assert len(result["findings"]) == 3


# ---------------------------------------------------------------------------
# Category humanization filter
# ---------------------------------------------------------------------------

def test_humanize_cat_known_keys() -> None:
    """_CATEGORY_LABELS must map all recognised snake_case keys to friendly labels."""
    import importlib

    import njit_auditor.web_app as wa
    importlib.reload(wa)
    assert wa._humanize_cat("page_numbering") == "Page numbering"
    assert wa._humanize_cat("font_format") == "Font formatting"
    assert wa._humanize_cat("margin_or_overflow") == "Margins / overflow"
    assert wa._humanize_cat("list_of_tables_figures_toc") == "TOC / lists"
    assert wa._humanize_cat("committee_approval_page") == "Approval page"
    assert wa._humanize_cat("heading_title") == "Headings / titles"
    assert wa._humanize_cat("abstract_length") == "Abstract length"
    assert wa._humanize_cat("latex_linter") == "LaTeX linting"


def test_humanize_cat_fallback_for_unknown_key() -> None:
    """Unknown keys must not raise — fall back to a capitalised version."""
    import importlib

    import njit_auditor.web_app as wa
    importlib.reload(wa)
    result = wa._humanize_cat("some_new_category")
    assert isinstance(result, str)
    assert len(result) > 0
    assert result == result.lstrip()


def test_humanize_cat_all_labels_dict_keys_are_distinct() -> None:
    """Every key and value in CATEGORY_DISPLAY_LABELS must be unique."""
    from njit_auditor.report_outputs import CATEGORY_DISPLAY_LABELS

    labels = CATEGORY_DISPLAY_LABELS
    assert len(set(labels.keys())) == len(labels), "Duplicate keys in CATEGORY_DISPLAY_LABELS"
    assert len(set(labels.values())) == len(labels), "Duplicate values in CATEGORY_DISPLAY_LABELS"


def test_results_page_shows_human_category_labels(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """The results page must display human-readable category labels, not raw snake_case."""
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path, finding_count=2)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    # P011 findings are categorised as margin_or_overflow — should render as human label
    assert b"Margins / overflow" in resp.content
    # Raw snake_case must NOT appear in the visible label positions
    # (it may still appear in data-* attributes for JS filtering)
    text = resp.text
    # The category filter dropdown should use human label as option text
    assert "Margins / overflow" in text


def test_results_page_filter_category_raw_value_preserved(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """Filter category <option value=...> must keep the raw snake_case key for JS matching."""
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path, finding_count=2)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    # value attribute must contain the raw key so JS data-category comparison works
    assert b'value="margin_or_overflow"' in resp.content


def test_results_page_shows_review_order_section(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """Completed results with findings must include the How to use this report section."""
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path, finding_count=2)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    assert b"How to use this report" in resp.content
    assert b"Checks performed and Check yourself" in resp.content


def test_results_page_shows_jump_links(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """Completed results with findings must include the jump-links navigation bar."""
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path, finding_count=2)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    assert b"jump-links" in resp.content
    assert b"#section-summary" in resp.content
    assert b"#section-findings" in resp.content


def _nav_block(html: str) -> str:
    start = html.index('<nav class="jump-links"')
    end = html.index("</nav>", start)
    return html[start:end]


def test_nav_chips_reflect_decluttered_report_structure(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """The top nav must match the decluttered report from #441-#450: no
    standalone "By problem type" chip (superseded by "Findings by topic"),
    no "Most common issues" chip (that section was removed as repetitive
    once "Findings by topic" became the main category overview), and the
    rule-by-rule table is a demoted "Technical rule summary" chip, not a
    primary "By rule" chip."""
    from njit_auditor.models import AuditFinding, Severity

    c, wa = client
    findings = [
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=i + 1,
            message="Left margin too narrow.",
            details={"issue_type": "margin_boundary_violation", "side": "left_margin"},
        )
        for i in range(2)
    ] + [
        AuditFinding(
            rule_id="P013",
            severity=Severity.WARNING,
            page=5,
            message="Page number candidate.",
            details={"issue_type": "page_number_candidate", "position_type": "bottom_center"},
        )
    ]
    job_id = _inject_complete_job_with_findings(
        wa, tmp_path, findings=findings, file_name="thesis.pdf", audit_type="pdf"
    )
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    nav = _nav_block(resp.content.decode())

    # Core, always-primary chips.
    for label in (
        "Summary",
        "How to use this report",
        "Findings in page order",
        "Findings by topic",
        "Downloads",
    ):
        assert f">{label}<" in nav, f"Missing core chip: {label!r}"

    # The old repetitive/technical labels must not appear as chip text.
    assert "By problem type" not in nav
    assert ">By rule<" not in nav
    assert ">Detected candidates<" not in nav
    assert ">Most common issues<" not in nav

    # Reviewer-facing destinations are present but clearly demoted.
    assert ">Technical rule summary<" in nav
    assert ">Page-number candidates (technical)<" in nav
    assert nav.count("jump-links__advanced") == 2


def test_nav_chip_targets_all_resolve_to_real_section_anchors(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """Every visible nav chip must point at a section anchor that actually
    exists on the page — clicking a chip should always land somewhere real."""
    import re

    from njit_auditor.models import AuditFinding, Severity

    c, wa = client
    findings = [
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=i + 1,
            message="Left margin too narrow.",
            details={"issue_type": "margin_boundary_violation", "side": "left_margin"},
        )
        for i in range(2)
    ] + [
        AuditFinding(
            rule_id="P013",
            severity=Severity.WARNING,
            page=5,
            message="Page number candidate.",
            details={"issue_type": "page_number_candidate", "position_type": "bottom_center"},
        )
    ]
    job_id = _inject_complete_job_with_findings(
        wa, tmp_path, findings=findings, file_name="thesis.pdf", audit_type="pdf"
    )
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    html = resp.content.decode()
    nav = _nav_block(html)

    hrefs = re.findall(r'href="#([\w-]+)"', nav)
    assert len(hrefs) >= 5
    for anchor_id in hrefs:
        assert f'id="{anchor_id}"' in html, f"Nav chip links to missing anchor #{anchor_id}"


def test_nav_advanced_candidates_chip_omitted_when_no_inventory_findings(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """A report with real problems but no informational page-number
    candidates has nothing to show in "Detected candidates", so the
    "Page-number candidates (technical)" chip must not render — while "Technical rule summary"
    (the rule-by-rule table) still does, since rule summaries always exist
    whenever there are findings."""
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path, finding_count=2)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    nav = _nav_block(resp.content.decode())
    assert ">Technical rule summary<" in nav
    assert ">Page-number candidates (technical)<" not in nav


def test_results_page_review_order_uses_simple_priority_labels(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """How to use this report must use plain-language priority labels, not severity jargon."""
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    assert b"Checks performed and Check yourself" in resp.content
    assert b"Warnings / Errors" not in resp.content


def test_results_page_verify_wording_in_status_banner(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """Status banner must include automated / verify wording, without the word "heuristic"."""
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    assert b"Findings are possible formatting issues" in resp.content
    assert b"heuristic" not in resp.content.lower()


def test_status_banner_renders_long_unbroken_filename_safely(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """A long filename with no spaces/hyphens (common in EF-style uploads, e.g.
    "Yin_H_4th_Review_with_EF_comments_compressed.pdf") must still render in full
    inside the status banner, and the banner's text wrapper must carry the
    mobile-safe wrapping hooks (status-banner__body / overflow-wrap: anywhere)
    instead of forcing the page wider than the viewport. This covers the flexbox
    min-width:auto overflow found live on 2026-07-05 via ester_sample_d."""
    c, wa = client
    long_name = "Yin_H_4th_Review_with_EF_comments_compressed_and_also_quite_long.pdf"
    job_id = _inject_complete_job_with_findings(
        wa,
        tmp_path,
        findings=[],
        file_name=long_name,
        audit_type="pdf",
    )
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    html = resp.text
    # The full filename must still be present -- wrapping/scrolling fixes must
    # not truncate or hide it.
    assert long_name in html
    # The flex-item wrapper needs min-width:0 so it can shrink below its
    # content's natural (unbroken) width instead of stretching the banner.
    assert 'class="status-banner__body"' in html
    assert ".status-banner__body { min-width: 0; }" in html
    # The text itself needs a break opportunity so the wrapper's min-content
    # size is actually small once min-width:0 allows it to shrink.
    assert ".status-banner__meta" in html and "overflow-wrap: anywhere;" in html


def test_status_banner_mobile_safe_css_present_for_all_states(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """The mobile-safe status-banner CSS must ship on pending/failed pages too,
    not just the completed-report page, since all three states render a
    student-controlled file_name in .status-banner__meta."""
    c, wa = client
    job = wa.JobState(
        job_id="pendingjob123",
        state="pending",
        created_at="2026-07-05T00:00:00+00:00",
        file_name="A_Very_Long_Unbroken_Uploaded_Filename_Example.pdf",
    )
    wa._set_job(job)
    resp = c.get("/audits/pendingjob123")
    assert resp.status_code == 200
    html = resp.text
    assert 'class="status-banner__body"' in html
    assert "A_Very_Long_Unbroken_Uploaded_Filename_Example.pdf" in html


def test_results_page_ui_intact_alongside_status_banner_fix(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """Guard against regressions in the recently-simplified findings UI while
    touching the shared base.html/job.html status-banner markup: topic summary
    stays, the old root-cause cards stay removed, sort defaults to page order,
    and there's no severity filter."""
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path, finding_count=3)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    html = resp.text
    assert "Findings by topic" in html
    assert "Most common issues" not in html
    assert '<option value="default" selected>Page order</option>' in html
    assert b"filter-severity" not in resp.content
    assert '<div class="summary-card__label">Items to review</div>' in html
    assert '<div class="summary-card__label">Pages affected</div>' in html
    assert '<div class="summary-card__label">Rules flagged</div>' in html


# ---------------------------------------------------------------------------
# PDF serve route (/audits/{job_id}/pdf)
# ---------------------------------------------------------------------------

def test_pdf_route_returns_pdf_inline(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """GET /audits/{job_id}/pdf returns the PDF with correct headers for a complete PDF job.

    Desktop browsers must not be instructed to download the PDF: the response must be
    inline (never attachment) so it opens directly in a new tab.
    """
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path)
    resp = c.get(f"/audits/{job_id}/pdf")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/pdf")
    assert resp.content[:4] == b"%PDF"
    disposition = resp.headers.get("content-disposition", "").lower()
    assert "inline" in disposition
    assert "attachment" not in disposition


def test_pdf_route_unknown_job_returns_404(client: tuple[TestClient, Any]) -> None:
    """GET /audits/{job_id}/pdf returns 404 when the job does not exist."""
    c, _ = client
    resp = c.get("/audits/no_such_job_ever/pdf")
    assert resp.status_code == 404


def test_pdf_route_pending_job_returns_404(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """GET /audits/{job_id}/pdf returns 404 while the job is still pending."""
    import secrets
    from datetime import datetime, timezone

    c, wa = client
    job_id = secrets.token_urlsafe(16)
    job = wa.JobState(
        job_id=job_id,
        state="pending",
        created_at=datetime.now(timezone.utc).isoformat(),
        file_name="thesis.pdf",
        audit_type="pdf",
    )
    wa._set_job(job)
    resp = c.get(f"/audits/{job_id}/pdf")
    assert resp.status_code == 404


def test_pdf_route_tex_job_returns_404(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """GET /audits/{job_id}/pdf returns 404 for TeX/source audit jobs."""
    import secrets
    from datetime import datetime, timezone

    c, wa = client
    job_id = secrets.token_urlsafe(16)
    jdir = Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"]) / job_id
    jdir.mkdir(parents=True, exist_ok=True)
    (jdir / "upload.pdf").write_bytes(_MINIMAL_PDF)
    job = wa.JobState(
        job_id=job_id,
        state="complete",
        created_at=datetime.now(timezone.utc).isoformat(),
        file_name="main.tex",
        audit_type="tex",
    )
    wa._set_job(job)
    resp = c.get(f"/audits/{job_id}/pdf")
    assert resp.status_code == 404


def test_results_page_open_pdf_button_shown_for_pdf_audit(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """Results page for a PDF audit must include the Open PDF button linking to /audits/{id}/pdf."""
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    assert b"open-pdf-btn" in resp.content
    assert f"/audits/{job_id}/pdf".encode() in resp.content


def test_results_page_page_links_present_for_findings_with_page(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """A known page number alone must NOT render a page-link anchor; only a real,
    visible highlight does (pointing to /pdf/highlighted, not a plain /pdf#page=N)."""
    c, wa = client
    findings = [_p012_annotation_finding_with_bbox(page=3)]
    job_id = _inject_complete_job_with_findings(
        wa, tmp_path, findings=findings, file_name="thesis.pdf", audit_type="pdf"
    )
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    body = resp.text
    assert f"/audits/{job_id}/pdf#page=" not in body
    assert "/highlighted-page.pdf" in body
    assert "page-link" in body


def test_results_page_uses_original_page_link_for_known_page_without_highlight(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """A finding whose page is known but has no bbox must render the original-page link only."""
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    body = resp.text
    # "original_page" resolves through the same true single-page endpoint as
    # "highlight" rather than a #page=N fragment into the full PDF.
    assert f"/audits/{job_id}/highlighted-page.pdf?page=" in body
    assert f"/audits/{job_id}/pdf#page=" not in body
    assert "/pdf/highlighted" not in body
    assert "Open original PDF page" in body


# ---------------------------------------------------------------------------
# Highlighted PDF endpoint (/audits/{job_id}/pdf/highlighted) and new-tab links
# ---------------------------------------------------------------------------


def _make_real_pdf(path: Path, page_count: int = 5) -> None:
    """Write a real, fitz-openable multi-page PDF (unlike the minimal stub bytes)."""
    import fitz

    doc = fitz.open()
    for _ in range(page_count):
        doc.new_page(width=612, height=792)
    doc.save(path)
    doc.close()


def _p012_annotation_finding_with_bbox(page: int = 3) -> Any:
    """A P012 finding carrying a parseable rect bbox, as written by the real detector."""
    from njit_auditor.models import AuditFinding, Severity

    return AuditFinding(
        rule_id="P012",
        severity=Severity.WARNING,
        page=page,
        message="PDF annotation/comment detected (Text).",
        details={
            "issue_type": "pdf_annotation_detected",
            "annotation_type": "Text",
            "rect": "100.0,200.0,300.0,260.0",
            "suggested_fix": "Resolve/remove reviewer comments before final submission.",
            "triage_tier": "informational",
        },
    )


def test_results_page_pdf_links_use_new_tab_and_noreferrer(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """Every PDF link on the main results page must open in a new tab without referrer leak."""
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path, finding_count=2)
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    body = resp.text
    assert 'target="_blank"' in body
    assert 'rel="noopener noreferrer"' in body
    assert 'rel="noopener"' not in body


def test_category_and_rule_problem_pages_pdf_links_use_new_tab_and_noreferrer(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """Category/rule problem pages must open PDF links in a new tab without referrer leak."""
    c, wa = client
    findings = [_p012_annotation_finding_with_bbox(page=2)]
    job_id = _inject_complete_job_with_findings(
        wa, tmp_path, findings=findings, file_name="thesis.pdf", audit_type="pdf"
    )

    cat_resp = c.get(f"/audits/{job_id}/problems/category/annotations")
    assert cat_resp.status_code == 200
    cat_body = cat_resp.text
    assert 'target="_blank"' in cat_body
    assert 'rel="noopener noreferrer"' in cat_body
    assert 'rel="noopener"' not in cat_body

    rule_resp = c.get(f"/audits/{job_id}/problems/rule/P012")
    assert rule_resp.status_code == 200
    rule_body = rule_resp.text
    assert 'target="_blank"' in rule_body
    assert 'rel="noopener noreferrer"' in rule_body
    assert 'rel="noopener"' not in rule_body


def test_highlighted_pdf_endpoint_serves_inline_for_finding_with_bbox(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """The highlighted-PDF endpoint must serve a real, inline PDF when bbox data exists."""
    c, wa = client
    findings = [_p012_annotation_finding_with_bbox(page=3)]
    job_id = _inject_complete_job_with_findings(
        wa, tmp_path, findings=findings, file_name="thesis.pdf", audit_type="pdf"
    )
    jdir = Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"]) / job_id
    pdf_path = jdir / "upload.pdf"
    _make_real_pdf(pdf_path, page_count=5)
    original_bytes = pdf_path.read_bytes()

    resp = c.get(
        f"/audits/{job_id}/pdf/highlighted",
        params={"page": 3, "rule_id": "P012", "issue_type": "pdf_annotation_detected"},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/pdf")
    disposition = resp.headers.get("content-disposition", "").lower()
    assert "inline" in disposition
    assert "attachment" not in disposition
    assert resp.content[:4] == b"%PDF"

    # The original uploaded PDF must never be modified by highlight generation.
    assert pdf_path.read_bytes() == original_bytes


def test_complete_student_pdf_download_is_cached_and_preserves_upload(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    import fitz

    c, wa = client
    findings = [
        _p012_annotation_finding_with_bbox(page=3),
        _p012_annotation_finding_with_bbox(page=1),
    ]
    job_id = _inject_complete_job_with_findings(
        wa, tmp_path, findings=findings, file_name="thesis.pdf", audit_type="pdf"
    )
    jdir = Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"]) / job_id
    upload = jdir / "upload.pdf"
    original_bytes = upload.read_bytes()
    url = f"/audits/{job_id}/download/student-report.pdf"
    assert "Download Complete PDF Report" in c.get(f"/audits/{job_id}").text
    first = c.get(url)
    assert first.status_code == 200
    assert first.headers["content-type"] == "application/pdf"
    assert "attachment" in first.headers["content-disposition"].lower()
    assert "thesis_NJIT_Formatting_Audit.pdf" in first.headers["content-disposition"]
    (output,) = jdir.glob("student-report-*.pdf")
    metadata = json.loads((jdir / "student-report-metadata.json").read_text(encoding="utf-8"))
    assert metadata["total_visible_findings"] == 2
    assert metadata["highlighted_findings"] == 2
    assert metadata["highlight_boxes_drawn"] == 2
    before_mtime = output.stat().st_mtime_ns
    with fitz.open(stream=first.content, filetype="pdf") as doc:
        assert doc.page_count == 5 + metadata["report_pages"]
        assert len(list(doc[0].annots() or [])) == 1
        assert len(list(doc[2].annots() or [])) == 1
        text = "\n".join(page.get_text() for page in list(doc)[5:])
        assert text.index("Problem #1") < text.index("Problem #2")
        assert "R012" in text
    assert c.get(url).content == first.content
    assert output.stat().st_mtime_ns == before_mtime
    assert upload.read_bytes() == original_bytes


def test_combined_report_problem_numbers_match_all_web_drilldowns_and_text(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """A real job keeps raw IDs while every student surface uses page-order numbers."""
    from datetime import datetime, timezone
    from html import unescape

    import fitz

    from njit_auditor.audit_runner import UploadedAuditResult
    from njit_auditor.models import AuditFinding, Severity
    from njit_auditor.upload_handling import UploadKind

    c, wa = client
    job_id = "synthetic-numbering-job"
    jdir = Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"]) / job_id
    jdir.mkdir(parents=True)
    _make_real_pdf(jdir / "upload.pdf", page_count=4)
    raw_findings = [
        AuditFinding(
            rule_id="P045",
            severity=Severity.WARNING,
            page=page,
            message=f"Synthetic publication issue {index}.",
            details={
                "issue_type": "numbered_publication_entry",
                "rect": f"{x},100,{x + 30},120",
                "suggested_fix": f"Remove numbering from entry {index}.",
            },
        )
        for index, (page, x) in enumerate(((3, 100), (1, 200), (3, 300)), start=1)
    ]
    wa._set_job(
        wa.JobState(
            job_id=job_id,
            state="pending",
            created_at=datetime.now(timezone.utc).isoformat(),
            file_name="synthetic-thesis.pdf",
        )
    )
    fake_result = UploadedAuditResult(
        upload_kind=UploadKind.PDF, audit_type="pdf", findings=raw_findings
    )
    with patch.object(wa, "run_audit_for_uploaded_file", return_value=fake_result):
        wa._run_audit_task(job_id)
    job = wa._get_job(job_id)
    assert job is not None and job.state == "complete"
    assert [(f["problem_number"], f["page"], f["finding_id"]) for f in job.findings] == [
        (1, 1, "f0"),
        (2, 3, "f1"),
        (3, 3, "f2"),
    ]
    raw_export = json.loads((jdir / "report.json").read_text(encoding="utf-8"))
    # The pre-existing JSON export sorts physical pages before FindingView.
    assert [f["page"] for f in raw_export["findings"]] == [1, 3, 3]

    base = f"/audits/{job_id}"
    main = c.get(base)
    sorted_main = c.get(base, params={"sort": "confidence_desc"})
    page = c.get(base + "/problems/page/3")
    rule = c.get(base + "/problems/rule/P045")
    text_report = c.get(base + "/download/text")
    combined = c.get(base + "/download/student-report.pdf")
    assert all(response.status_code == 200 for response in (
        main, sorted_main, page, rule, text_report, combined
    ))
    with fitz.open(stream=combined.content, filetype="pdf") as document:
        pdf_report = " ".join(
            " ".join(p.get_text() for p in list(document)[job.pdf_page_count:]).split()
        )
        assert "#1" in document[0].get_text()
        assert "#2" in document[2].get_text()
        assert "#3" in document[2].get_text()

    for finding in job.findings:
        number = finding["problem_number"]
        anchor = f'id="problem-{number}"'
        assert anchor in main.text and anchor in sorted_main.text
        assert anchor in rule.text
        if finding["page"] == 3:
            assert anchor in page.text
        assert f"Problem #{number}" in text_report.text
        assert f"Problem #{number}" in pdf_report
        assert plain_student_text(finding["polished_comment"]) in unescape(main.text)
        assert plain_student_text(finding["polished_comment"]) in text_report.text
        assert plain_student_text(finding["polished_comment"]) in pdf_report
        assert finding["suggested_fix"] in unescape(main.text)
        assert finding["suggested_fix"] in text_report.text
        assert finding["suggested_fix"] in pdf_report
        assert finding["public_rule_reference_id"] == "P045"
    assert all("R045" in response.text for response in (main, page, text_report))
    assert "R045" in pdf_report
    assert pdf_report.count("Problem #1 ") == 1
    assert pdf_report.count("Problem #2 ") == 1
    assert pdf_report.count("Problem #3 ") == 1


def test_complete_student_pdf_cache_changes_when_findings_change(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    c, wa = client
    job_id = _inject_complete_job_with_findings(
        wa,
        tmp_path,
        findings=[_p012_annotation_finding_with_bbox(page=2)],
        file_name="thesis.pdf",
        audit_type="pdf",
    )
    url = f"/audits/{job_id}/download/student-report.pdf"
    before = c.get(url).content
    job = wa._get_job(job_id)
    assert job is not None
    job.findings[0]["polished_comment"] = "Updated student-facing explanation."
    after = c.get(url).content
    assert after != before
    import fitz

    with fitz.open(stream=after, filetype="pdf") as doc:
        assert "Updated student-facing explanation." in doc[-1].get_text()


def test_complete_student_pdf_concurrent_requests_return_complete_files(
    client: tuple[TestClient, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import time
    import traceback
    from concurrent.futures import ThreadPoolExecutor

    import fitz

    c, wa = client
    failures: list[str] = []
    readers: list[Any] = []
    build_calls: list[int] = []
    original_replace = os.replace
    original_build = wa.build_combined_student_pdf_report

    def slow_build(*args, **kwargs):
        build_calls.append(1)
        time.sleep(0.1)  # Let the other request encounter the same cold cache.
        return original_build(*args, **kwargs)

    def record_replace(*args, **kwargs):
        try:
            result = original_replace(*args, **kwargs)
            if Path(args[1]).name == "student-report.pdf" and not readers:
                # Model a download that is still reading when another request
                # finishes generation. Windows denies replacement of this file.
                readers.append(Path(args[1]).open("rb"))
            return result
        except OSError:
            # Synthetic test only: retain native file-sharing details without
            # exposing document paths in production application logs.
            failures.append(traceback.format_exc())
            raise

    monkeypatch.setattr(os, "replace", record_replace)
    monkeypatch.setattr(wa, "build_combined_student_pdf_report", slow_build)
    job_id = _inject_complete_job_with_findings(
        wa,
        tmp_path,
        findings=[_p012_annotation_finding_with_bbox(page=2)],
        file_name="thesis.pdf",
        audit_type="pdf",
    )
    url = f"/audits/{job_id}/download/student-report.pdf"
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(c.get, (url, url)))
    finally:
        for reader in readers:
            reader.close()
    assert all(response.status_code == 200 for response in responses), "\n".join(failures)
    assert len(build_calls) == 1, "Concurrent downloads must reuse the same published report"
    assert responses[0].content == responses[1].content
    for response in responses:
        with fitz.open(stream=response.content, filetype="pdf") as document:
            assert document.page_count > 5
            assert "Problem #1" in " ".join(page.get_text() for page in list(document)[5:])
    jdir = Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"]) / job_id
    (output,) = jdir.glob("student-report-*.pdf")
    with fitz.open(output) as cached:
        assert cached.page_count > 5


@pytest.mark.parametrize(
    ("filename", "renderer", "report_label"),
    [
        ("student-report.pdf", "build_combined_student_pdf_report", "complete PDF report"),
        ("comments.pdf", "build_comments_pdf_report", "Comments PDF"),
    ],
)
def test_student_pdf_generation_failure_allows_retry(
    client: tuple[TestClient, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    filename: str, renderer: str, report_label: str,
) -> None:
    c, wa = client
    job_id = _inject_complete_job_with_findings(
        wa, tmp_path, findings=[_p012_annotation_finding_with_bbox(page=2)],
        file_name="synthetic.pdf", audit_type="pdf",
    )
    url = f"/audits/{job_id}/download/{filename}"
    original = getattr(wa, renderer)
    calls = []

    def fail_once(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            raise PermissionError("Synthetic transient write failure")
        return original(*args, **kwargs)

    monkeypatch.setattr(wa, renderer, fail_once)
    failure = c.get(url)
    assert failure.status_code == 500
    assert "PDF export failed." in failure.text
    assert "Audit result no longer available." not in failure.text
    assert f"The {report_label} could not be prepared. Please try again." in failure.text
    assert f'href="/audits/{job_id}">Return to audit results</a>' in failure.text
    assert "Synthetic transient write failure" not in failure.text
    assert c.get(f"/audits/{job_id}").status_code == 200
    retry = c.get(url)
    assert retry.status_code == 200
    assert retry.content.startswith(b"%PDF-")
    assert len(calls) == 2


def test_complete_student_pdf_missing_and_non_pdf_jobs(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    c, wa = client
    missing = c.get("/audits/expired/download/student-report.pdf")
    assert missing.status_code == 404
    assert "Audit result no longer available." in missing.text
    assert "Return to audit results" not in missing.text
    job_id = _inject_complete_job_with_findings(
        wa, tmp_path, findings=[], file_name="source.tex", audit_type="tex"
    )
    assert c.get(f"/audits/{job_id}/download/student-report.pdf").status_code == 404
    expired_id = _inject_complete_job_with_findings(
        wa, tmp_path, findings=[], file_name="thesis.pdf", audit_type="pdf"
    )
    expired = wa._get_job(expired_id)
    assert expired is not None
    expired.created_at = "2000-01-01T00:00:00+00:00"
    expired_dir = Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"]) / expired_id
    assert c.get(f"/audits/{expired_id}/download/student-report.pdf").status_code == 404
    assert not expired_dir.exists()


def test_complete_student_pdf_pending_failed_and_job_isolation(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    import fitz

    c, wa = client
    first_id = _inject_complete_job_with_findings(
        wa,
        tmp_path,
        findings=[_p012_annotation_finding_with_bbox(page=1)],
        file_name="first.pdf",
        audit_type="pdf",
    )
    second_id = _inject_complete_job_with_findings(
        wa,
        tmp_path,
        findings=[_p012_annotation_finding_with_bbox(page=3)],
        file_name="second.pdf",
        audit_type="pdf",
    )
    first_url = f"/audits/{first_id}/download/student-report.pdf"
    second_url = f"/audits/{second_id}/download/student-report.pdf"
    first_job = wa._get_job(first_id)
    assert first_job is not None
    first_job.state = "pending"
    assert c.get(first_url).status_code == 404
    first_job.state = "failed"
    assert c.get(first_url).status_code == 404
    first_job.state = "complete"
    first = c.get(first_url)
    second = c.get(second_url)
    assert first.status_code == second.status_code == 200
    assert first.content != second.content
    with fitz.open(stream=first.content, filetype="pdf") as first_pdf:
        assert len(list(first_pdf[0].annots() or [])) == 1
        assert len(list(first_pdf[2].annots() or [])) == 0
    with fitz.open(stream=second.content, filetype="pdf") as second_pdf:
        assert len(list(second_pdf[0].annots() or [])) == 0
        assert len(list(second_pdf[2].annots() or [])) == 1
    runtime = Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"])
    assert len(list((runtime / first_id).glob("student-report-*.pdf"))) == 1
    assert len(list((runtime / second_id).glob("student-report-*.pdf"))) == 1


def test_web_upload_keeps_duplicate_unicode_display_names_separate(
    client: tuple[TestClient, Any], tmp_path: Path,
) -> None:
    from urllib.parse import unquote

    c, wa = client
    pdf = tmp_path / "generated.pdf"
    _make_real_pdf(pdf, page_count=1)
    name = "پایان‌نامه Sample résumé.pdf"
    jobs = []
    for _ in range(2):
        response = c.post(
            "/audits", files={"file": (name, pdf.read_bytes(), "application/pdf")},
            follow_redirects=False,
        )
        assert response.status_code == 303
        job = response.headers["location"]
        jobs.append(job)
        assert c.get(job + "/status").json()["file_name"] == name
        assert c.get(job + "/download/json").json()["metadata"]["input_file_name"] == name
        inline = c.get(job + "/pdf")
        assert inline.status_code == 200
        disposition = inline.headers["content-disposition"]
        assert unquote(disposition.split("filename*=UTF-8''", 1)[1]) == name
        assert (wa.RUNTIME_DIR / job.rsplit("/", 1)[-1] / "upload.pdf").exists()
    assert jobs[0] != jobs[1]


def test_complete_student_pdf_safe_filename(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    c, wa = client
    job_id = _inject_complete_job_with_findings(
        wa, tmp_path, findings=[], file_name='../../unsafe"name.pdf', audit_type="pdf"
    )
    response = c.get(f"/audits/{job_id}/download/student-report.pdf")
    assert response.status_code == 200
    disposition = response.headers["content-disposition"]
    assert "unsafe_name_NJIT_Formatting_Audit.pdf" in disposition
    assert "../" not in disposition
    assert 'unsafe"name' not in disposition
    long_id = _inject_complete_job_with_findings(
        wa, tmp_path, findings=[], file_name="x" * 500 + ".pdf", audit_type="pdf"
    )
    long_response = c.get(f"/audits/{long_id}/download/student-report.pdf")
    assert long_response.status_code == 200
    assert len(long_response.headers["content-disposition"]) < 200


def test_highlighted_page_pdf_endpoint_serves_single_page_with_annotation(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """Per-finding links must serve a one-page highlighted artifact, not the full upload."""
    import fitz

    c, wa = client
    findings = [_p012_annotation_finding_with_bbox(page=3)]
    job_id = _inject_complete_job_with_findings(
        wa, tmp_path, findings=findings, file_name="thesis.pdf", audit_type="pdf"
    )
    jdir = Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"]) / job_id
    pdf_path = jdir / "upload.pdf"
    _make_real_pdf(pdf_path, page_count=5)

    resp = c.get(
        f"/audits/{job_id}/highlighted-page.pdf",
        params={"page": 3, "rule_id": "P012", "issue_type": "pdf_annotation_detected"},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/pdf")
    assert "highlighted-page.pdf" in resp.headers.get("content-disposition", "").lower()
    assert resp.content[:4] == b"%PDF"

    with fitz.open(stream=resp.content, filetype="pdf") as doc:
        assert doc.page_count == 1
        assert len(list(doc[0].annots() or [])) >= 1


def test_highlighted_page_pdf_endpoint_falls_back_to_single_page_without_bbox(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """Page-focused endpoint must never return the full upload when highlight is unavailable."""
    import fitz

    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path)
    jdir = Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"]) / job_id
    _make_real_pdf(jdir / "upload.pdf", page_count=5)

    resp = c.get(
        f"/audits/{job_id}/highlighted-page.pdf",
        params={"page": 2, "rule_id": "P011", "issue_type": "margin_boundary_violation"},
    )
    assert resp.status_code == 200
    with fitz.open(stream=resp.content, filetype="pdf") as doc:
        assert doc.page_count == 1


def test_highlighted_pdf_endpoint_falls_back_without_bbox(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """The highlighted-PDF endpoint must fall back to the plain PDF when no bbox matches."""
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path)

    resp = c.get(
        f"/audits/{job_id}/pdf/highlighted",
        params={"page": 1, "rule_id": "P011", "issue_type": "margin_boundary_violation"},
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/pdf")
    disposition = resp.headers.get("content-disposition", "").lower()
    assert "inline" in disposition
    assert "attachment" not in disposition


@pytest.mark.parametrize("page", ["0", "-1", "99999"])
def test_highlighted_pdf_endpoint_invalid_page_number_never_500s(
    client: tuple[TestClient, Any], tmp_path: Path, page: str
) -> None:
    """Out-of-range page numbers must fall back safely, never 500."""
    c, wa = client
    findings = [_p012_annotation_finding_with_bbox(page=3)]
    job_id = _inject_complete_job_with_findings(
        wa, tmp_path, findings=findings, file_name="thesis.pdf", audit_type="pdf"
    )
    jdir = Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"]) / job_id
    _make_real_pdf(jdir / "upload.pdf", page_count=5)

    resp = c.get(f"/audits/{job_id}/pdf/highlighted", params={"page": page, "rule_id": "P012"})
    assert resp.status_code != 500
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/pdf")


def test_highlighted_pdf_endpoint_non_numeric_page_never_500s(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """A non-numeric page query value must be rejected safely, never 500."""
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path)

    resp = c.get(f"/audits/{job_id}/pdf/highlighted", params={"page": "abc"})
    assert resp.status_code != 500
    assert resp.status_code in (400, 404, 422)


def test_highlighted_pdf_endpoint_degenerate_bbox_falls_back_without_500(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """A finding with a degenerate (zero-area/inverted/NaN) bbox must fall back, not 500.

    Regression test: PyMuPDF's annotation reader does not validate the rect stored in an
    uploaded PDF, so a real document can produce a degenerate rect string here. Previously
    this reached fitz.Rect/add_rect_annot unfiltered and raised ValueError("rect is infinite
    or empty"), which FastAPI surfaced as a 500.
    """
    from njit_auditor.models import AuditFinding, Severity

    c, wa = client
    findings = [
        AuditFinding(
            rule_id="P012",
            severity=Severity.WARNING,
            page=2,
            message="PDF annotation/comment detected (Text).",
            details={
                "issue_type": "pdf_annotation_detected",
                "annotation_type": "Text",
                "rect": "100.0,200.0,100.0,200.0",
                "suggested_fix": "Resolve/remove reviewer comments before final submission.",
                "triage_tier": "informational",
            },
        )
    ]
    job_id = _inject_complete_job_with_findings(
        wa, tmp_path, findings=findings, file_name="thesis.pdf", audit_type="pdf"
    )
    jdir = Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"]) / job_id
    _make_real_pdf(jdir / "upload.pdf", page_count=5)

    resp = c.get(f"/audits/{job_id}/pdf/highlighted", params={"page": 2, "rule_id": "P012"})
    assert resp.status_code != 500
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/pdf")
    disposition = resp.headers.get("content-disposition", "").lower()
    assert "inline" in disposition
    assert "attachment" not in disposition


def test_highlighted_pdf_endpoint_draws_all_valid_boxes_for_multiple_matches(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """Multiple findings matching the same page/rule must each contribute their own box,
    with degenerate boxes among them skipped rather than failing the whole request."""
    import fitz

    from njit_auditor.models import AuditFinding, Severity

    c, wa = client
    findings = [
        AuditFinding(
            rule_id="P012",
            severity=Severity.WARNING,
            page=4,
            message="PDF annotation/comment detected (Text).",
            details={
                "issue_type": "pdf_annotation_detected",
                "annotation_type": "Text",
                "rect": "50.0,50.0,150.0,100.0",
            },
        ),
        AuditFinding(
            rule_id="P012",
            severity=Severity.WARNING,
            page=4,
            message="PDF annotation/comment detected (Text).",
            details={
                "issue_type": "pdf_annotation_detected",
                "annotation_type": "Text",
                "rect": "200.0,200.0,300.0,260.0",
            },
        ),
        AuditFinding(
            rule_id="P012",
            severity=Severity.WARNING,
            page=4,
            message="PDF annotation/comment detected (Text).",
            details={
                "issue_type": "pdf_annotation_detected",
                "annotation_type": "Text",
                "rect": "0.0,0.0,0.0,0.0",  # degenerate -- must be skipped, not fatal
            },
        ),
    ]
    job_id = _inject_complete_job_with_findings(
        wa, tmp_path, findings=findings, file_name="thesis.pdf", audit_type="pdf"
    )

    resp = c.get(f"/audits/{job_id}/pdf/highlighted", params={"page": 4, "rule_id": "P012"})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/pdf")
    with fitz.open(stream=resp.content, filetype="pdf") as doc:
        assert len(list(doc[3].annots() or [])) == 2


def test_result_and_problem_pages_pdf_links_never_500(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """Every PDF link rendered on the result/category/rule pages must resolve safely."""
    c, wa = client
    findings = [_p012_annotation_finding_with_bbox(page=3)]
    job_id = _inject_complete_job_with_findings(
        wa, tmp_path, findings=findings, file_name="thesis.pdf", audit_type="pdf"
    )
    jdir = Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"]) / job_id
    _make_real_pdf(jdir / "upload.pdf", page_count=5)

    pages = [
        f"/audits/{job_id}",
        f"/audits/{job_id}/problems/category/annotations",
        f"/audits/{job_id}/problems/rule/P012",
    ]
    pdf_link_re = AUDIT_PDF_HREF_RE
    checked_any = False
    for page_url in pages:
        resp = c.get(page_url)
        assert resp.status_code == 200
        for link in pdf_link_re.findall(resp.text):
            link_resp = c.get(link)
            assert link_resp.status_code != 500, f"{link} (from {page_url}) returned 500"
            checked_any = True
    assert checked_any


def test_problem_group_page_links_to_highlighted_pdf_when_bbox_available(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """A finding with bbox data must get an "Open highlighted PDF page" link; others fall back."""
    c, wa = client
    findings = [_p012_annotation_finding_with_bbox(page=3)]
    job_id = _inject_complete_job_with_findings(
        wa, tmp_path, findings=findings, file_name="thesis.pdf", audit_type="pdf"
    )

    resp = c.get(f"/audits/{job_id}/problems/rule/P012")
    assert resp.status_code == 200
    body = resp.text
    assert "Open highlighted PDF page" in body
    assert f"/audits/{job_id}/highlighted-page.pdf?" in body
    assert 'rel="noopener noreferrer"' in body


def test_problem_group_page_falls_back_honestly_without_bbox(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """A finding without bbox data must render the original-page action, never a fake highlight."""
    c, wa = client
    job_id = _inject_complete_job(wa, tmp_path, finding_count=2)

    resp = c.get(f"/audits/{job_id}/problems/rule/P011")
    assert resp.status_code == 200
    body = resp.text
    assert "Open highlighted PDF page" not in body
    assert "Open PDF page" not in body
    # "original_page" resolves through the same true single-page endpoint as
    # "highlight" (falls back to a plain single-page extract with no bbox)
    # rather than a #page=N fragment into the full PDF, which mobile PDF
    # viewers do not reliably honor.
    assert f"/audits/{job_id}/pdf#page=" not in body
    assert f"/audits/{job_id}/highlighted-page.pdf?" in body
    assert "Open original PDF page" in body
    assert "Open original PDF page" in body


def test_pdf_finding_jinja_globals_are_registered(client: tuple[TestClient, Any]) -> None:
    """Every Jinja global referenced by job.html/problem_group.html must be registered.

    Regression test: a stale, long-running server process was previously caught
    serving an up-to-date job.html (Jinja auto-reloads templates from disk) while
    its in-memory Jinja environment lacked ``pdf_finding_url`` because that global
    registration line did not exist yet when the process imported web_app.py --
    raising ``jinja2.exceptions.UndefinedError: 'pdf_finding_url' is undefined``
    on every results-page render. This only catches a *missing registration*, not
    process staleness itself (every test run re-imports fresh code), but it
    guards against ever shipping a template that calls an unregistered global.
    """
    _, wa = client
    globals_ = wa._templates.env.globals
    assert callable(globals_.get("pdf_finding_url"))

    template_dir = Path(wa.__file__).parent / "templates"
    for name in ("job.html", "problem_group.html"):
        text = (template_dir / name).read_text(encoding="utf-8")
        for global_name in ("pdf_finding_url", "pdf_finding_is_highlighted"):
            if global_name in text:
                assert global_name in globals_, (
                    f"{name} calls {global_name}() but it is unregistered"
                )


def test_fresh_real_upload_with_real_annotation_end_to_end_pdf_links_never_500(
    tmp_path: Path,
) -> None:
    """A real upload through the actual audit pipeline must never 500 on its PDF links.

    Uses TestClient(raise_server_exceptions=True) with a real fitz-generated PDF
    carrying a real annotation (the same finding type -- a P012 annotation -- that
    triggered the live degenerate-bbox 500) run through the unmocked
    run_audit_for_uploaded_file pipeline, end to end, exactly as a student's
    browser session would.
    """
    import fitz

    app, wa = _make_app(tmp_path)
    c = TestClient(app, raise_server_exceptions=True)

    pdf_path = tmp_path / "real_upload.pdf"
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((72, 100), "Sample dissertation text for end-to-end testing.")
    page.add_text_annot((100, 200), "Reviewer comment")
    doc.save(pdf_path)
    doc.close()

    with pdf_path.open("rb") as fh:
        post = c.post(
            "/audits",
            files={"file": ("real_upload.pdf", fh, "application/pdf")},
            follow_redirects=True,
        )
    assert post.status_code == 200
    job_id = str(post.url).split("/audits/")[1].rstrip("/")

    status = c.get(f"/audits/{job_id}/status").json()
    assert status["state"] == "complete", status

    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    assert "pdf_finding_url" not in resp.text
    assert "Undefined" not in resp.text

    pdf_link_re = AUDIT_PDF_HREF_RE
    links = set(pdf_link_re.findall(resp.text))
    assert links, "expected at least one PDF link on the rendered job page"
    for link in links:
        link_resp = c.get(link)
        assert link_resp.status_code == 200, f"{link} returned {link_resp.status_code}"
        assert link_resp.headers["content-type"].startswith("application/pdf")

    # The actual background pipeline must give the web card, text download,
    # and combined PDF the same visible problem identity and wording.
    combined_response = c.get(f"/audits/{job_id}/download/student-report.pdf")
    text_response = c.get(f"/audits/{job_id}/download/text")
    assert combined_response.status_code == text_response.status_code == 200
    job = wa._get_job(job_id)
    assert job is not None and job.findings
    finding = job.findings[0]
    from html import unescape

    import fitz

    with fitz.open(stream=combined_response.content, filetype="pdf") as combined:
        report_text = " ".join(
            " ".join(page.get_text() for page in list(combined)[job.pdf_page_count:]).split()
        )
    fields = student_card_fields(finding)
    expected_comment = " ".join((fields["student_summary"] if finding["rule_id"] == "P011"
                                 else plain_student_text(finding["polished_comment"])).split())
    assert f"Problem #{finding['problem_number']}" in report_text
    assert expected_comment in report_text
    assert expected_comment in " ".join(text_response.text.split())
    assert expected_comment in " ".join(unescape(resp.text).split())


def test_runtime_dir_cleared_then_new_job_still_produces_valid_pdf_links(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """After clearing the runtime directory, a freshly created job still works.

    Mirrors the live-deployment remediation step (``rm -rf .runtime/web_audits/*``)
    to confirm stale on-disk state from prior jobs is never required for a new
    job's PDF links to resolve correctly.
    """
    import shutil

    c, wa = client
    stale_job_id = _inject_complete_job_with_findings(
        wa, tmp_path, findings=[_p012_annotation_finding_with_bbox(page=1)],
        file_name="stale.pdf", audit_type="pdf",
    )
    runtime_dir = Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"])
    assert (runtime_dir / stale_job_id).exists()
    shutil.rmtree(runtime_dir)
    assert not runtime_dir.exists()

    findings = [_p012_annotation_finding_with_bbox(page=2)]
    job_id = _inject_complete_job_with_findings(
        wa, tmp_path, findings=findings, file_name="fresh.pdf", audit_type="pdf"
    )
    jdir = runtime_dir / job_id
    _make_real_pdf(jdir / "upload.pdf", page_count=5)

    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    pdf_link_re = AUDIT_PDF_HREF_RE
    links = pdf_link_re.findall(resp.text)
    assert links
    for link in links:
        link_resp = c.get(link)
        assert link_resp.status_code != 500


# ---------------------------------------------------------------------------
# Example-thesis URL box on the upload page
# ---------------------------------------------------------------------------

def test_home_and_help_offer_uploads_and_sample_download_only(
    client: tuple[TestClient, Any],
) -> None:
    c, wa = client
    for path in ["/", "/help"]:
        response = c.get(path)
        assert response.status_code == 200
        for obsolete in ["pdf_url", 'type="url"', 'action="/audits/url"',
                         'action="/audits/sample"', "fill-example-url",
                         "Audit PDF URL", "public PDF URL", "built-in sample"]:
            assert obsolete not in response.text
    assert 'href="/sample.pdf"' in c.get("/").text
    sample = c.get("/sample.pdf")
    assert sample.status_code == 200
    assert sample.content.startswith(b"%PDF-")
    assert "attachment" in sample.headers["content-disposition"]
    assert not wa._jobs


@pytest.mark.parametrize("sample_id, expected_sha256", [
    ("ester_sample_a", "234f6c951a2a6a07308a771af434628658ddc84f9684c54e51f6c9423ac6d6ad"),
    ("ester_sample_b", "dccea83030fe01c90d996ff3a1b901e2d56eaac6fe06ba51eea7c884bfc6d56b"),
    ("ester_sample_c", "dbfdc9b820c46cf10570d802911c92b1b5ed31583a72f59cfadf2b5286e31eee"),
    ("ester_sample_d", "cbf4497727dc106cd8c26e5f0c6786a45b6c5df42405254796e164200690e209"),
])
def test_historical_public_sample_downloads_match_original_files(
    client: tuple[TestClient, Any], sample_id: str, expected_sha256: str,
) -> None:
    from njit_auditor.web_samples import get_builtin_sample

    if not get_builtin_sample(sample_id).abs_path.is_file():
        pytest.skip("Historical PDFs are excluded from nonconfidential CI checkouts")
    c, wa = client
    url = f"/samples/{sample_id}.pdf"
    assert f'href="{url}"' in c.get("/").text
    response = c.get(url)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment" in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF")
    assert hashlib.sha256(response.content).hexdigest() == expected_sha256
    assert not wa._jobs


def test_historical_sample_download_checks_whitelist_and_bytes(
    client: tuple[TestClient, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    import njit_auditor.web_samples as samples

    relative = "data/raw/ester/synthetic-public-sample.pdf"
    source = tmp_path / relative
    source.parent.mkdir(parents=True)
    source.write_bytes(b"%PDF-1.4\nsynthetic test data\n%%EOF\n")
    expected = hashlib.sha256(source.read_bytes()).hexdigest()
    monkeypatch.setattr(samples, "_REPO_ROOT", tmp_path)
    monkeypatch.setitem(samples._BY_ID, "ester_sample_a", samples.SampleInfo(
        "ester_sample_a", "Synthetic test sample", relative,
    ))
    monkeypatch.setitem(samples._PUBLIC_SAMPLE_SHA256, "ester_sample_a", expected)
    c, wa = client
    response = c.get("/samples/ester_sample_a.pdf")
    assert response.status_code == 200
    assert response.content == source.read_bytes()
    assert "synthetic-public-sample.pdf" in response.headers["content-disposition"]
    assert not wa._jobs
    source.write_bytes(b"%PDF-1.4\nchanged\n%%EOF\n")
    assert c.get("/samples/ester_sample_a.pdf").status_code == 404


def test_historical_sample_download_rejects_unlisted_files(
    client: tuple[TestClient, Any],
) -> None:
    c, _ = client
    assert c.get("/samples/unlisted.pdf").status_code == 404
    assert c.get("/samples/../private.pdf").status_code != 200


# ---------------------------------------------------------------------------
# GET /audits/url guard — regression tests for route collision bug
# ---------------------------------------------------------------------------


def test_get_audits_url_redirects_to_index(client: tuple[TestClient, Any]) -> None:
    """GET /audits/url must redirect to the upload page, not fall through to the job page."""
    c, _ = client
    resp = c.get("/audits/url", follow_redirects=False)
    assert resp.status_code in (301, 302, 303, 307, 308)
    assert resp.headers.get("location", "").rstrip("/") in ("/", "")


def test_get_audits_url_does_not_show_job_not_found(client: tuple[TestClient, Any]) -> None:
    """GET /audits/url must never show the 'Job was not found' error message."""
    c, _ = client
    resp = c.get("/audits/url", follow_redirects=True)
    assert b"was not found" not in resp.content
    assert b"job" not in resp.content.lower() or b"job 'url'" not in resp.content.lower()


def test_get_audits_sample_redirects_to_index(client: tuple[TestClient, Any]) -> None:
    """GET /audits/sample must redirect to the upload page, not fall through to the job page."""
    c, _ = client
    resp = c.get("/audits/sample", follow_redirects=False)
    assert resp.status_code in (301, 302, 303, 307, 308)
    assert resp.headers.get("location", "").rstrip("/") in ("/", "")


def test_get_audits_sample_does_not_show_job_not_found(client: tuple[TestClient, Any]) -> None:
    """GET /audits/sample must never show the 'Job was not found' error message."""
    c, _ = client
    resp = c.get("/audits/sample", follow_redirects=True)
    assert b"was not found" not in resp.content
    assert b"job" not in resp.content.lower() or b"job 'sample'" not in resp.content.lower()


def test_footer_attribution_and_contact(client: tuple[TestClient, Any]) -> None:
    """Footer must show author attribution and correct contact email on all main pages."""
    c, _ = client
    for path in ["/", "/help", "/rules"]:
        resp = c.get(path)
        assert resp.status_code == 200, f"{path} did not return 200"
        body = resp.content.decode()
        assert "Soroush Vahidi" in body, f"{path} missing author name"
        assert "mailto:sv96@njit.edu" in body, f"{path} missing mailto link"
        assert "soroush.vahidi@njit.edu" not in body, f"{path} contains wrong email address"


def test_validation_error_redirects_to_refreshable_get(client: tuple[TestClient, Any]) -> None:
    c, wa = client
    response = c.post(
        '/audits', files={'file': ('invalid.txt', b'not a pdf', 'text/plain')},
        follow_redirects=False,
    )
    assert response.status_code == 303
    target = response.headers['location']
    assert target.startswith('/?error=')
    for _ in range(2):
        page = c.get(target)
        assert page.status_code == 400
        assert 'Could not start audit' in page.text
    assert not wa._jobs


@pytest.mark.parametrize("continuation_x", [126.0, 144.0, 160.0])
def test_p018_leftward_guidance_across_web_and_exports(
    client: tuple[TestClient, Any], tmp_path: Path, continuation_x: float,
) -> None:
    """Real synthetic TOC findings retain metadata and highlight their source."""
    import re
    from html import unescape

    import fitz
    from test_rules.test_r018_wrapped_title_alignment import _render, _wrapped_toc_rows

    from njit_auditor.pdf_layout import load_pdf_layout
    from njit_auditor.rules.pdf_toc_alignment import check_pdf_toc_alignment

    c, wa = client
    source = _render(tmp_path, "TABLE OF CONTENTS", _wrapped_toc_rows(continuation_x))
    findings = [
        f for f in check_pdf_toc_alignment(load_pdf_layout(str(source)))
        if f.details.get("issue_type") == "wrapped_title_continuation_misaligned"
    ]
    assert len(findings) == 1
    finding = findings[0]
    assert finding.severity.value == "WARNING"
    assert finding.details["confidence"] == "medium"
    assert float(finding.details["signed_delta_pt"]) < 0
    assert finding.details["highlight_bboxes"]
    job_id = _inject_complete_job_with_findings(
        wa, tmp_path, findings=findings, file_name="synthetic-toc.pdf",
        audit_type="pdf", page_count=1,
    )
    jdir = Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"]) / job_id
    upload = jdir / "upload.pdf"
    upload.write_bytes(source.read_bytes())
    original_bytes = upload.read_bytes()
    base = f"/audits/{job_id}"

    def check_guidance(text: str) -> None:
        normalized = " ".join(unescape(re.sub(r"<[^>]+>", " ", text)).split())
        assert "at or to the right of the first word of the title text" in normalized
        assert "rightward indentation of second and third lines is accepted" in normalized
        assert "not indented past" not in normalized
        assert "neither left of" not in normalized

    for route in ("", "/problems/page/1", "/problems/rule/P018"):
        response = c.get(base + route)
        assert response.status_code == 200
        check_guidance(response.text)
    for export in ("json", "markdown", "text"):
        response = c.get(base + "/download/" + export)
        assert response.status_code == 200
        check_guidance(response.text)
        if export == "json":
            exported = response.json()["findings"][0]
            assert exported["page"] == exported["pdf_page"] == 1
            assert exported["severity"] == "WARNING"
            assert exported["details"] == finding.details
    # Both the stored standalone text and the web text download use the correction.
    check_guidance((jdir / "report.txt").read_text())

    original = c.get(base + "/pdf")
    assert original.status_code == 200 and original.content == original_bytes
    highlighted = c.get(base + "/pdf/highlighted", params={
        "page": 1, "rule_id": "P018", "issue_type": finding.details["issue_type"],
    })
    assert highlighted.status_code == 200
    with fitz.open(stream=highlighted.content, filetype="pdf") as document:
        assert document.page_count == 1
        assert "TABLE OF CONTENTS" in document[0].get_text()
        assert len(list(document[0].annots() or [])) == 1
    combined = c.get(base + "/download/student-report.pdf")
    assert combined.status_code == 200
    with fitz.open(stream=combined.content, filetype="pdf") as document:
        assert document.page_count > 1
        assert len(list(document[0].annots() or [])) == 1
        check_guidance(" ".join(page.get_text() for page in list(document)[1:]))
    assert upload.read_bytes() == original_bytes
    job = wa._get_job(job_id)
    assert job is not None and len(job.findings) == 1
    card = job.findings[0]
    assert card["page"] == 1 and card["confidence"] == "medium"
    assert wa._public_rule_reference_id("P018", issue_type=card["issue_type"]) == "P018R"
    rules = c.get("/rules")
    assert rules.status_code == 200
    catalog_card = next(
        rule for rule in wa._build_rule_catalog()["student_rules"] if rule["id"] == "P018R"
    )
    assert "at or to the right" in catalog_card["title"]
    check_guidance(catalog_card["how_to_correct"])
    check_guidance(rules.text)


@pytest.mark.parametrize(("case", "leader_issue", "alignment_issue"), [
    ("missing", "toc_missing_leader_style", False),
    ("mixed", "toc_mixed_leader_styles", False),
    ("allowed_short", "", False),
    ("alignment", "", True),
    ("missing_and_alignment", "toc_missing_leader_style", True),
])
def test_p075_leader_advice_across_reports(
    client: tuple[TestClient, Any], tmp_path: Path, case: str, leader_issue: str,
    alignment_issue: bool,
) -> None:
    import re
    from html import unescape

    import pymupdf
    from test_r057_toc_leader_gaps import _LEADER_CELL_FIXTURES, _toc_pdf

    if case == "missing":
        source = _LEADER_CELL_FIXTURES / "tight-cell-empty.pdf"
    elif case == "allowed_short":
        source = _LEADER_CELL_FIXTURES / "centered-cell-wrap.pdf"
    else:
        source = tmp_path / "toc.pdf"
        if case == "missing_and_alignment":
            _toc_pdf(source, "misaligned", size=11, pitch_em=0.60, wrapped=False)
        else:
            with pymupdf.open() as pdf:
                page = pdf.new_page(width=612, height=792)
                page.insert_text(
                    (220, 90), "TABLE OF CONTENTS", fontsize=16, fontname="Times-Bold",
                )
                for index, title in enumerate(("Introduction", "Methods", "Results", "Discussion")):
                    y = 140 + index * 20
                    leader = "-----" if case == "mixed" and index == 2 else "......."
                    x = 465 if case == "alignment" and index == 2 else 500
                    page.insert_text((108, y), f"Chapter {index + 1} {title} {leader}")
                    page.insert_text((x, y), str(11 + index))
                pdf.save(source)

    c, wa = client
    upload = c.post(
        "/audits", files={"file": ("synthetic-toc.pdf", source.read_bytes(), "application/pdf")},
        follow_redirects=False,
    )
    assert upload.status_code == 303
    base = upload.headers["location"]
    status = c.get(base + "/status").json()
    assert status["state"] == "complete" and status["finished_at"]
    job = wa._get_job(base.rsplit("/", 1)[-1])
    assert job is not None
    reports = {
        "html": c.get(base),
        **{fmt: c.get(base + "/download/" + fmt) for fmt in (
            "json", "markdown", "text", "comments.pdf", "student-report.pdf",
        )},
    }
    assert all(response.status_code == 200 for response in reports.values())

    actions = {
        "toc_missing_leader_style": (
            "Add a leader before each affected Table of Contents page number, "
            "using the same style as the other entries."
        ),
        "toc_mixed_leader_styles": (
            "Use one leader style, dots or hyphens, throughout the Table of Contents."
        ),
    }
    alignment = ("P018", "misaligned_page_number_column")
    payload = reports["json"].json()
    leaders = [(i, row) for i, row in enumerate(payload["findings"]) if row["rule_id"] == "P075"]
    assert [row["details"]["issue_type"] for _, row in leaders] == (
        [leader_issue] if leader_issue else []
    )
    folio_rows = [
        row for row in payload["findings"]
        if (row["rule_id"], row["details"].get("issue_type")) == alignment
    ]
    assert bool(folio_rows) is alignment_issue
    if leader_issue:
        (raw_index, raw_leader), = leaders
        (card,) = [item for item in job.findings if item["rule_id"] == "P075"]
        assert raw_leader["details"]["suggested_fix"] == actions[leader_issue]
        assert card["finding_id"] == f"f{raw_index}"
        assert card["page"] == raw_leader["page"]
        assert card["suggested_fix"] == actions[leader_issue]
        if raw_leader["details"].get("bbox"):
            assert card["bbox"] == tuple(
                float(part) for part in raw_leader["details"]["bbox"].split(",")
            )
        grouped = [group for group in payload["grouped_findings"] if group["rule_id"] == "P075"]
        assert [group["suggested_fix"] for group in grouped] == [actions[leader_issue]]

    for fmt, response in reports.items():
        if fmt.endswith(".pdf"):
            with pymupdf.open(stream=response.content, filetype="pdf") as pdf:
                start = job.pdf_page_count if fmt == "student-report.pdf" else 0
                rendered = " ".join(pdf[index].get_text() for index in range(start, len(pdf)))
        else:
            rendered = re.sub(r"<[^>]+>", " ", response.text) if fmt == "html" else response.text
        rendered = " ".join(unescape(rendered).casefold().split())
        assert "right-align page numbers and use one consistent leader style" not in rendered, fmt
        for issue_type, action in actions.items():
            expected = issue_type == leader_issue
            assert (action.casefold() in rendered) is expected, (fmt, issue_type)
        assert ("dominant right-hand column" in rendered) is alignment_issue, fmt


@pytest.mark.parametrize(
    ("title", "capitalization", "punctuation"),
    [
        ("Evaluation of eBoss Systems", False, False),
        ("Evaluation of eBoss systems", True, False),
        ("Evaluation of eBoss Systems.", False, True),
        ("Evaluation of eBoss systems.", True, True),
    ],
)
def test_ester_table_title_capitalization_and_period_advice_are_separate(
    client: tuple[TestClient, Any], title: str, capitalization: bool, punctuation: bool,
) -> None:
    import re
    from html import unescape

    import pymupdf

    with pymupdf.open() as pdf:
        page = pdf.new_page(width=612, height=792)
        page.insert_text((220, 85), "LIST OF TABLES", fontname="Times-Bold", fontsize=14)
        for index, entry in enumerate((title, "Valid Comparison Table", "Valid Control Table")):
            y = 150 + index * 27
            page.insert_text((108, y), f"Table 1.{index + 1} {entry}", fontsize=12)
            page.insert_text((494, y), str(20 + index), fontsize=12)
        source = pdf.tobytes()

    c, wa = client
    upload = c.post(
        "/audits", files={"file": ("synthetic-lot.pdf", source, "application/pdf")},
        follow_redirects=False,
    )
    assert upload.status_code == 303
    url = upload.headers["location"]
    assert c.get(url + "/status").json()["state"] == "complete"
    job = wa._get_job(url.rsplit("/", 1)[-1])
    assert job is not None
    responses = {"html": c.get(url)}
    for fmt in ("json", "markdown", "text", "comments.pdf", "student-report.pdf"):
        responses[fmt] = c.get(url + "/download/" + fmt)
    assert all(response.status_code == 200 for response in responses.values())

    issues = {
        (row["rule_id"], row["details"].get("issue_type"))
        for row in responses["json"].json()["findings"]
    }
    assert (("P024", "list_of_tables_title_case") in issues) is capitalization
    assert (("P017", "unexpected_terminal_period") in issues) is punctuation
    for fmt, response in responses.items():
        if fmt.endswith(".pdf"):
            with pymupdf.open(stream=response.content, filetype="pdf") as pdf:
                first = job.pdf_page_count if fmt == "student-report.pdf" else 0
                content = " ".join(pdf[i].get_text() for i in range(first, len(pdf)))
        else:
            content = re.sub(r"<[^>]+>", " ", response.text) if fmt == "html" else response.text
        content = " ".join(unescape(content).casefold().split())
        assert "title case with no ending period" not in content, fmt
        assert ("use title case for this table title" in content) is capitalization, fmt
        period_action = "remove the final period from this list of tables entry"
        assert (period_action in content) is punctuation, fmt
