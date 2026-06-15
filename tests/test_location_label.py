"""Tests for sub-page location labels in PDF findings."""

from __future__ import annotations

import json
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import fitz  # type: ignore[import-untyped]
import pytest
from fastapi.testclient import TestClient

_MINIMAL_PDF = b"%PDF-1.4\n%%EOF\n"


# ---------------------------------------------------------------------------
# _build_pdf_sublocation unit tests
# ---------------------------------------------------------------------------

from njit_auditor.report_view import _build_pdf_sublocation  # noqa: E402


@pytest.mark.parametrize("rule_id,details,expected", [
    # P011: side + affected_line_count
    ("P011", {"side": "left_margin", "affected_line_count": "3"},
     "left margin, 3 line(s)"),
    ("P011", {"side": "right_margin", "affected_line_count": "1"},
     "right margin, 1 line(s)"),
    ("P011", {"side": "bottom_margin"}, "bottom margin"),
    ("P011", {}, ""),
    # P013: position_type
    ("P013", {"position_type": "bottom_center"}, "bottom center zone"),
    ("P013", {"position_type": "top_right"}, "top right zone"),
    ("P013", {}, ""),
    # P014: heading
    ("P014", {"heading": "ABSTRACT"}, "heading 'ABSTRACT'"),
    ("P014", {"heading": "TABLE OF CONTENTS"}, "heading 'TABLE OF CONTENTS'"),
    ("P014", {}, ""),
    # P017: caption_number present
    ("P017", {"caption_type": "figure", "caption_number": "3.2",
               "line_preview": "Figure 3.2 Some caption body text"},
     "figure 3.2 caption"),
    # P017: caption_number present, table
    ("P017", {"caption_type": "table", "caption_number": "4.1",
               "line_preview": "Table 4.1 Some table title"},
     "table 4.1 caption"),
    # P017: no caption_number — fallback to line_preview
    ("P017", {"caption_type": "figure",
               "line_preview": "Figure 3.2 Some caption body text"},
     "figure: Figure 3.2 Some caption body text"),
    # P017: empty
    ("P017", {}, ""),
    # P019: candidate_text
    ("P019", {"candidate_text": "xii"}, "pn 'xii'"),
    ("P019", {"candidate_text": "iv"}, "pn 'iv'"),
    ("P019", {}, ""),
    # P020: line_preview
    ("P020", {"line_preview": "Results And Discussion"}, "'Results And Discussion'"),
    ("P020", {}, ""),
    # P024: line_preview with leader dots
    ("P024", {"line_preview": "Chapter 3 Methodology....42"}, "TOC: 'Chapter 3 Methodology'"),
    ("P024", {"line_preview": "Introduction"}, "TOC: 'Introduction'"),
    ("P024", {}, ""),
    # P026: observed_summary
    ("P026", {"observed_summary": "CMR10, CMR12"}, "font: CMR10, CMR12"),
    ("P026", {"observed_summary": "10pt, 11pt"}, "font: 10pt, 11pt"),
    ("P026", {}, ""),
    # P027: line_preview
    ("P027", {"line_preview": "3.1 Data Collection"}, "heading '3.1 Data Collection'"),
    ("P027", {}, ""),
    # P029: candidate_text + expected_value
    ("P029", {"candidate_text": "iii", "expected_value": "iv"},
     "numeral 'iii', expected 'iv'"),
    ("P029", {"candidate_text": "v"}, "numeral 'v'"),
    ("P029", {}, ""),
    # P030: expected_heading
    ("P030", {"expected_heading": "TABLE OF CONTENTS (Continued)"},
     "'TABLE OF CONTENTS (Continued)' missing"),
    ("P030", {}, ""),
    # P031: observed_header_labels
    ("P031", {"observed_header_labels": "Number Title Page"},
     "headers: Number Title Page"),
    ("P031", {}, ""),
    # P035: float_type + float_number
    ("P035", {"float_type": "figure", "float_number": "3.2"}, "figure 3.2"),
    ("P035", {"float_type": "table", "float_number": "1"}, "table 1"),
    ("P035", {"float_type": "figure"}, "figure"),
    ("P035", {}, ""),
    # P037: section_key + expected_roman + observed_roman
    ("P037", {"section_key": "abstract", "expected_roman": "ii", "observed_roman": "iii"},
     "abstract: expected 'ii', got 'iii'"),
    ("P037", {"section_key": "table_of_contents",
               "expected_roman": "iv", "observed_roman": "v"},
     "table of contents: expected 'iv', got 'v'"),
    ("P037", {}, ""),
    # P038: required_heading_missing
    ("P038", {"issue_type": "required_heading_missing",
               "expected_heading": "BIOGRAPHICAL SKETCH"},
     "missing: 'BIOGRAPHICAL SKETCH'"),
    # P038: heading_phrase_not_exact
    ("P038", {"issue_type": "heading_phrase_not_exact",
               "observed_heading_normalized": "ACKNOWLEDGMENTS",
               "expected_heading": "ACKNOWLEDGEMENTS"},
     "variant 'ACKNOWLEDGMENTS' → 'ACKNOWLEDGEMENTS'"),
    ("P038", {}, ""),
    # P074: detected_month
    ("P074", {"detected_month": "October"}, "graduation month: October"),
    ("P074", {}, ""),
    # P082: location_bucket
    ("P082", {"location_bucket": "top_margin"}, "pn at top margin"),
    ("P082", {"location_bucket": "bottom_center"}, "pn at bottom center"),
    ("P082", {}, ""),
    # Unknown rule
    ("P999", {"side": "left"}, ""),
    ("UNKNOWN", {}, ""),
    # Empty rule_id
    ("", {}, ""),
])
def test_build_pdf_sublocation(
    rule_id: str, details: dict[str, str], expected: str
) -> None:
    result = _build_pdf_sublocation(rule_id, details)
    assert result == expected, f"rule={rule_id} details={details}: got {result!r}"


def test_build_pdf_sublocation_long_preview_truncated() -> None:
    long_preview = "A" * 100
    result = _build_pdf_sublocation("P020", {"line_preview": long_preview})
    assert len(result) <= 43  # 40 chars + quotes + ellipsis
    assert "…" in result


def test_build_pdf_sublocation_long_heading_truncated() -> None:
    long_heading = "VERY LONG HEADING TITLE THAT EXCEEDS THE LIMIT FOR DISPLAY"
    result = _build_pdf_sublocation("P014", {"heading": long_heading})
    # "heading '" prefix + up to 40 chars + ellipsis + "'" = at most ~52 chars
    assert len(result) <= 55
    assert "heading" in result
    assert "…" in result


def test_build_pdf_sublocation_missing_details_returns_empty() -> None:
    assert _build_pdf_sublocation("P011", {}) == ""
    assert _build_pdf_sublocation("P013", {}) == ""
    assert _build_pdf_sublocation("P017", {}) == ""
    assert _build_pdf_sublocation("P038", {}) == ""


# ---------------------------------------------------------------------------
# P017 caption_number metadata tests
# ---------------------------------------------------------------------------

def test_p017_finding_includes_caption_number(tmp_path: Path) -> None:
    """P017 findings must include caption_number when a numbered caption is detected."""
    from njit_auditor.pdf_layout import load_pdf_layout
    from njit_auditor.rules.pdf_captions import check_pdf_captions

    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    caption_text = "Figure 3.2 shows the experimental setup with detailed results."
    page.insert_text((72, 300), caption_text, fontsize=10)
    pdf_path = tmp_path / "test_captions.pdf"
    doc.save(str(pdf_path))
    doc.close()

    pdf_doc = load_pdf_layout(str(pdf_path))
    findings = check_pdf_captions(pdf_doc)
    p017 = [f for f in findings if f.rule_id == "P017"]
    if p017:
        f = p017[0]
        assert "caption_number" in f.details, "caption_number missing from P017 details"
        assert f.details["caption_number"] == "3.2"


def test_p017_sublocation_uses_caption_number() -> None:
    """_build_pdf_sublocation should produce 'figure 3.2 caption' when caption_number set."""
    result = _build_pdf_sublocation("P017", {
        "caption_type": "figure",
        "caption_number": "3.2",
        "line_preview": "Figure 3.2 Some caption body text here.",
    })
    assert result == "figure 3.2 caption"


def test_p017_sublocation_fallback_without_caption_number() -> None:
    """_build_pdf_sublocation falls back to line_preview when caption_number absent."""
    result = _build_pdf_sublocation("P017", {
        "caption_type": "figure",
        "line_preview": "Figure 5.1 Caption body here",
    })
    assert result.startswith("figure:")
    assert "Figure 5.1" in result


# ---------------------------------------------------------------------------
# Template render tests — PDF location label display
# ---------------------------------------------------------------------------

def _make_app(tmp_path: Path) -> tuple[TestClient, Any]:
    os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"] = str(tmp_path / "web_audits")
    import importlib

    import njit_auditor.web_app as wa

    importlib.reload(wa)
    return TestClient(wa.app, raise_server_exceptions=False), wa


@pytest.fixture()
def client(tmp_path: Path) -> tuple[TestClient, Any]:
    return _make_app(tmp_path)


def _inject_pdf_job(
    wa: Any,
    tmp_path: Path,
    *,
    rule_id: str = "P011",
    page: int | None = 5,
    details: dict[str, str] | None = None,
    finding_count: int = 2,
) -> str:
    """Inject a complete PDF job; details defaults to P011 margin violation."""
    from njit_auditor.models import AuditFinding, Severity
    from njit_auditor.report_outputs import audit_findings_to_json_dict, write_markdown_report
    from njit_auditor.report_view import build_report_view, report_view_to_dict

    if details is None:
        details = {"issue_type": "margin_boundary_violation", "side": "left_margin",
                   "affected_line_count": "3"}

    findings = [
        AuditFinding(
            rule_id=rule_id,
            severity=Severity.WARNING,
            page=page,
            message="Test finding.",
            details=details,
        )
        for _ in range(finding_count)
    ]
    job_id = secrets.token_urlsafe(16)
    runtime = Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"])
    jdir = runtime / job_id
    jdir.mkdir(parents=True, exist_ok=True)
    (jdir / "upload.pdf").write_bytes(_MINIMAL_PDF)
    metadata = {"input_file_name": "thesis.pdf", "audit_type": "pdf", "job_id": job_id}
    payload = audit_findings_to_json_dict(findings, metadata)
    (jdir / "report.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_markdown_report(findings, metadata, jdir / "report.md")
    view = build_report_view(payload)
    view_dict = report_view_to_dict(view)

    job = wa.JobState(
        job_id=job_id,
        state="complete",
        created_at=datetime.now(timezone.utc).isoformat(),
        file_name="thesis.pdf",
        audit_type="pdf",
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
        report_view=view_dict,
        md_preview="# Audit\n",
    )
    wa._set_job(job)
    return job_id


def test_pdf_row_page_and_label_renders_arrow(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """PDF finding with page + location_label must render 'page → label'."""
    c, wa = client
    job_id = _inject_pdf_job(
        wa, tmp_path,
        rule_id="P011",
        page=42,
        details={"issue_type": "margin_boundary_violation", "side": "left_margin",
                 "affected_line_count": "3"},
        finding_count=3,
    )
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    body = resp.text
    # Should render page link and the label
    assert "→" in body
    assert "left margin" in body


def test_pdf_row_page_only_no_arrow(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """PDF finding with page but no location_label must render page only (no →)."""
    c, wa = client
    # P999 is unknown so sublocation returns ""
    job_id = _inject_pdf_job(
        wa, tmp_path,
        rule_id="P999",
        page=10,
        details={"issue_type": "some_issue"},
        finding_count=1,
    )
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    body = resp.text
    # page should be shown, no → arrow from sublocation
    assert "10" in body
    # The → arrow should not appear (no sublocation for P999)
    assert "→" not in body


def test_pdf_row_no_page_label_only(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """PDF finding with no page but has location_label must render label alone."""
    c, wa = client
    job_id = _inject_pdf_job(
        wa, tmp_path,
        rule_id="P038",
        page=None,
        details={
            "issue_type": "required_heading_missing",
            "expected_heading": "BIOGRAPHICAL SKETCH",
            "section_key": "biographical_sketch",
        },
        finding_count=1,
    )
    resp = c.get(f"/audits/{job_id}")
    assert resp.status_code == 200
    body = resp.text
    assert "missing:" in body or "BIOGRAPHICAL SKETCH" in body


def test_source_audit_still_renders_filename_line(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    """Source audit location_label must remain filename:line, not affected by PDF sublocation."""
    from njit_auditor.models import AuditFinding, Severity
    from njit_auditor.report_outputs import audit_findings_to_json_dict, write_markdown_report
    from njit_auditor.report_view import build_report_view, report_view_to_dict

    findings = [
        AuditFinding(
            rule_id="P001",
            severity=Severity.WARNING,
            page=None,
            message="Test tex finding.",
            details={"issue_type": "test", "file": "main.tex", "line": "42"},
        )
    ]
    job_id = secrets.token_urlsafe(16)
    runtime = Path(os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"])
    jdir = runtime / job_id
    jdir.mkdir(parents=True, exist_ok=True)
    (jdir / "upload.tex").write_bytes(b"\\documentclass{report}\n")
    metadata = {"input_file_name": "main.tex", "audit_type": "tex", "job_id": job_id}
    payload = audit_findings_to_json_dict(findings, metadata)
    (jdir / "report.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_markdown_report(findings, metadata, jdir / "report.md")
    view = build_report_view(payload)
    view_dict = report_view_to_dict(view)

    wa = client[1]
    job = wa.JobState(
        job_id=job_id,
        state="complete",
        created_at=datetime.now(timezone.utc).isoformat(),
        file_name="main.tex",
        audit_type="tex",
        finding_count=view.total_findings,
        warn_count=1, fail_count=0,
        findings=[
            {
                "rule_id": fv.rule_id, "severity": fv.severity, "page": fv.page,
                "issue_type": fv.issue_type, "category": fv.category,
                "polished_comment": fv.polished_comment, "suggested_fix": fv.suggested_fix,
                "triage_tier": fv.triage_tier, "confidence": fv.confidence,
                "source_file": fv.source_file, "source_line": fv.source_line,
                "location_label": fv.location_label,
            }
            for fv in view.findings
        ],
        grouped_summary=[
            {"rule_id": rs.rule_id, "count": rs.count, "category": rs.category}
            for rs in view.rule_summaries
        ],
        report_view=view_dict,
        md_preview="# Audit\n",
    )
    wa._set_job(job)
    resp = client[0].get(f"/audits/{job_id}")
    assert resp.status_code == 200
    body = resp.text
    # Source audit shows file:line location, not a PDF sublocation
    assert "main.tex" in body or "42" in body
