"""Tests for TeX/source JSON/Markdown/report-view export parity."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from njit_auditor.audit_runner import run_audit_for_uploaded_file
from njit_auditor.models import AuditFinding, Severity
from njit_auditor.polished_comments import build_polished_comment, contains_blocked_detail_text
from njit_auditor.report_outputs import (
    build_audit_report,
    build_source_report,
    derive_source_issue_type,
    write_markdown_report,
)
from njit_auditor.report_view import build_report_view
from njit_auditor.upload_handling import UploadKind


def _source_findings() -> list[AuditFinding]:
    return [
        AuditFinding(
            rule_id="P001",
            severity=Severity.WARNING,
            message="Risky formatting override '\\vspace' detected.",
            details={
                "file": "/tmp/project/chapter1.tex",
                "line": "42",
                "command": "vspace",
                "suggested_fix": "Remove manual override.",
            },
        ),
        AuditFinding(
            rule_id="P004",
            severity=Severity.WARNING,
            message="Reference points to undefined label: 'fig:secret_diagram'",
            details={
                "file": "/tmp/project/main.tex",
                "line": "88",
                "label": "fig:secret_diagram",
                "suggested_fix": "Define the missing label.",
            },
        ),
        AuditFinding(
            rule_id="P005",
            severity=Severity.PASS,
            message="Figure/table caption and label checks passed.",
        ),
    ]


def test_derive_source_issue_types() -> None:
    assert derive_source_issue_type("P001", {"command": "vspace"}) == "risky_command"
    assert derive_source_issue_type("P004", {}) == "dangling_reference"
    assert derive_source_issue_type("P009", {"tool": "chktex"}) == "chktex_warning"


def test_build_source_report_json_shape() -> None:
    payload = build_source_report(
        _source_findings(),
        input_file_path="/tmp/main.tex",
        input_file_name="main.tex",
        input_kind="tex",
        main_tex_path="/tmp/main.tex",
        loaded_tex_file_count=3,
        job_id="src1",
    )
    meta = payload["metadata"]
    assert meta["audit_type"] == "tex"
    assert meta["input_kind"] == "tex"
    assert meta["main_tex_path"] == "/tmp/main.tex"
    assert meta["loaded_tex_file_count"] == "3"
    assert meta["total_findings"] == 3
    assert meta["counts_by_rule_id"]["P001"] == 1
    assert meta["source_location_count"] == 2

    finding = payload["findings"][0]
    assert finding["page"] is None
    assert finding["source_file"] == "chapter1.tex"
    assert finding["source_line"] == "42"
    assert finding["details"]["issue_type"] == "risky_command"


def test_build_source_report_is_json_serializable(tmp_path: Path) -> None:
    payload = build_source_report(
        _source_findings(),
        input_file_path=str(tmp_path / "main.tex"),
        input_file_name="main.tex",
    )
    out = tmp_path / "report.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["metadata"]["audit_type"] == "tex"
    assert "findings" in loaded


def test_source_markdown_export_privacy_safe(tmp_path: Path) -> None:
    md_path = tmp_path / "source.md"
    metadata = {
        "input_file_path": str(tmp_path / "main.tex"),
        "input_file_name": "main.tex",
        "audit_type": "tex",
        "input_kind": "tex",
        "main_tex_path": str(tmp_path / "main.tex"),
        "loaded_tex_file_count": "2",
    }
    write_markdown_report(_source_findings(), metadata, md_path)
    text = md_path.read_text(encoding="utf-8")
    assert "# NJIT Source Audit Report" in text
    assert "Findings by Rule" in text
    assert "chapter1.tex:42" in text
    assert "fig:secret_diagram" not in text
    assert "secret_diagram" not in text
    assert "Review needed" in text


def test_build_report_view_handles_source_locations() -> None:
    payload = build_source_report(
        _source_findings(),
        input_file_path="/tmp/main.tex",
        input_file_name="main.tex",
        input_kind="tex",
    )
    view = build_report_view(payload)
    assert view.pages == []
    assert any(card.label == "Source locations" for card in view.summary_cards)
    assert view.triage_panels == []
    p001 = next(f for f in view.findings if f.rule_id == "P001")
    assert p001.page is None
    assert p001.source_file == "chapter1.tex"
    assert p001.source_line == "42"
    assert p001.location_label == "chapter1.tex:42"
    assert p001.polished_comment


def test_pdf_report_behavior_unchanged() -> None:
    pdf_findings = [
        AuditFinding(
            rule_id="P011",
            severity=Severity.WARNING,
            page=2,
            message="Margin issue.",
            details={"issue_type": "margin_boundary_violation", "side": "left_margin"},
        )
    ]
    payload = build_audit_report(
        pdf_findings,
        {
            "input_file_path": "thesis.pdf",
            "input_file_name": "thesis.pdf",
            "audit_type": "pdf",
        },
    )
    assert payload["metadata"]["audit_type"] == "pdf"
    assert payload["findings"][0]["page"] == 2
    assert "source_file" not in payload["findings"][0]


_SOURCE_PRIVACY_CASES: list[tuple[str, str, dict[str, str], str]] = [
    (
        "P001",
        "risky_command",
        {"file": "main.tex", "line": "3", "command": "vspace"},
        "dissertation chapter text",
    ),
    (
        "P002",
        "duplicate_label",
        {"file": "main.tex", "line": "4", "label": "fig:private_figure"},
        "private_figure",
    ),
    (
        "P003",
        "invalid_label",
        {"file": "main.tex", "line": "5", "label": "bad label key"},
        "bad label key",
    ),
    (
        "P004",
        "dangling_reference",
        {"file": "main.tex", "line": "6", "ref": "fig:hidden"},
        "fig:hidden",
    ),
    (
        "P005",
        "missing_caption",
        {"file": "main.tex", "line": "7"},
        "Figure 3.1 Neural network",
    ),
    (
        "P006",
        "missing_label",
        {"file": "main.tex", "line": "8"},
        "Table 2.4 Results",
    ),
    (
        "P007",
        "caption_punctuation",
        {"file": "main.tex", "line": "9"},
        "Caption without period",
    ),
    (
        "P008",
        "abstract_structure",
        {"file": "main.tex", "line": "1"},
        "Abstract body sentence here",
    ),
    (
        "P009",
        "chktex_warning",
        {"file": "main.tex", "line": "10", "tool": "chktex"},
        r"\begin{abstract} private",
    ),
    (
        "P010",
        "lacheck_warning",
        {"file": "main.tex", "line": "11", "tool": "lacheck"},
        "author name string",
    ),
]


@pytest.mark.parametrize(
    ("rule_id", "issue_type", "details", "forbidden"),
    _SOURCE_PRIVACY_CASES,
)
def test_source_polished_comments_are_privacy_safe(
    rule_id: str,
    issue_type: str,
    details: dict[str, str],
    forbidden: str,
) -> None:
    comment = build_polished_comment(
        rule_id=rule_id,
        issue_type=issue_type,
        page=None,
        details=details,
    )
    assert forbidden not in comment
    assert contains_blocked_detail_text(comment, details) is False
    assert "Review needed" in comment


def test_dispatcher_tex_export_supported(tmp_path: Path) -> None:
    tex = tmp_path / "main.tex"
    tex.write_text(
        r"\documentclass{report}" + "\n\\begin{document}\n\\end{document}\n",
        encoding="utf-8",
    )
    with patch(
        "njit_auditor.audit_runner.collect_tex_findings",
        return_value=(tex, 1, _source_findings()),
    ):
        result = run_audit_for_uploaded_file(tex)
    assert result.upload_kind == UploadKind.TEX
    assert result.json_export_supported is True
    assert result.limitation_note == ""
    payload = build_audit_report(
        result.findings,
        {
            "input_file_path": str(tex),
            "input_file_name": tex.name,
            "audit_type": result.audit_type,
            "input_kind": "tex",
        },
    )
    assert payload["metadata"]["audit_type"] == "tex"


def test_dispatcher_zip_source_report(tmp_path: Path) -> None:
    zpath = tmp_path / "project.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.writestr(
            "main.tex",
            rb"\documentclass{report}\n\\begin{document}\n\\end{document}\n",
        )
    work = tmp_path / "work"
    work.mkdir()
    with patch(
        "njit_auditor.audit_runner.collect_tex_findings",
        return_value=(work / "main.tex", 1, _source_findings()),
    ):
        result = run_audit_for_uploaded_file(zpath, work_dir=work)
    assert result.upload_kind == UploadKind.ZIP
    assert result.json_export_supported is True
    payload = build_audit_report(
        result.findings,
        {
            "input_file_path": str(zpath),
            "input_file_name": zpath.name,
            "audit_type": "tex",
            "input_kind": "zip",
            "main_tex_path": str(work / "main.tex"),
            "loaded_tex_file_count": "1",
        },
    )
    assert payload["metadata"]["input_kind"] == "zip"
    assert payload["findings"][0]["source_file"] == "chapter1.tex"
