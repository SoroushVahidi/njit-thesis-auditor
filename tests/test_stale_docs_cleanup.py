"""Regression tests for stale-doc cleanup and PR #305 supersession checks."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

_REPO = Path(__file__).resolve().parents[1]
_MATRIX = _REPO / "docs/planning/finding_actionability_matrix.md"
_STATUS = _REPO / "docs/status/stale_docs_cleanup_20260619.md"

_FORBIDDEN_LABELS = (
    "Open PDF page",
    "Open first example page",
)


@pytest.fixture()
def client(tmp_path: Path) -> tuple[TestClient, Any]:
    os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"] = str(tmp_path / "web_audits")
    import importlib

    import njit_auditor.web_app as wa

    importlib.reload(wa)
    return TestClient(wa.app, raise_server_exceptions=False), wa
_MATRIX = _REPO / "docs/planning/finding_actionability_matrix.md"
_STATUS = _REPO / "docs/status/stale_docs_cleanup_20260619.md"

_FORBIDDEN_LABELS = (
    "Open PDF page",
    "Open first example page",
)


def test_finding_actionability_matrix_has_historical_banner() -> None:
    text = _MATRIX.read_text(encoding="utf-8")
    assert "Historical note" in text
    assert "must not" in text.lower() or "must not be treated" in text
    assert "Current policy" in text


def test_finding_actionability_matrix_current_policy_labels() -> None:
    text = _MATRIX.read_text(encoding="utf-8")
    policy_start = text.index("## Current policy")
    policy_end = text.index("## Column definitions", policy_start)
    policy = text[policy_start:policy_end]
    assert "Open highlighted PDF page" in policy
    assert "Open original PDF page" in policy
    assert "Read explanation" in policy
    assert "stable problem number" in policy.lower()
    assert "forbidden" in policy.lower()
    # Forbidden labels may appear only as examples of what not to use.
    for line in policy.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or stripped.startswith("| Condition"):
            continue
        if "Forbidden" in stripped:
            continue
        for forbidden in _FORBIDDEN_LABELS:
            assert forbidden not in stripped


def test_stale_docs_cleanup_status_doc_exists() -> None:
    assert _STATUS.is_file()
    body = _STATUS.read_text(encoding="utf-8")
    assert "njit_rule_inventory.json" in body
    assert "Left untouched" in body or "left untouched" in body.lower()
    assert "PR #305" in body


def test_manual_qa_checklist_no_open_pdf_page_in_actionability_section() -> None:
    qa = (_REPO / "docs/web_ui_manual_qa_checklist.md").read_text(encoding="utf-8")
    section_start = qa.index("### 5a. Actionability Checks")
    section_end = qa.index("## 6. Problem Pages", section_start)
    section = qa[section_start:section_end]
    assert "Read explanation" in section
    assert "Open PDF page" not in section
    assert "Open first example page" not in section


def test_index_page_sample_download_and_upload_ui_present(
    client: tuple[TestClient, object],
) -> None:
    """Direct sample audits coexist with downloads and ordinary PDF uploads."""
    c, _ = client
    resp = c.get("/")
    assert resp.status_code == 200
    body = resp.text
    for obsolete in (
        'type="url"', 'name="pdf_url"', 'name="document_url"', 'name="doc_url"',
        'name="url"', 'action="/audits/url"', 'action="/audits/sample"',
        "example-thesis-box", "fill-example-url",
    ):
        assert obsolete not in body

    assert 'href="/sample.pdf"' in body
    assert "Download sample PDF" in body
    assert "Sample Documents" in body
    assert 'action="/sample-audits"' in body
    assert "Audit Selected Sample" in body
    assert "New_Submitted_Thesis.pdf" in body
    sample = c.get("/sample.pdf")
    assert sample.status_code == 200
    assert sample.headers["content-type"].startswith("application/pdf")
    assert "attachment" in sample.headers["content-disposition"]
    assert sample.content.startswith(b"%PDF-")

    upload_form = re.search(r'<form action="/audits"[^>]*>(.*?)</form>', body, re.DOTALL)
    assert upload_form is not None
    assert 'method="post"' in upload_form.group(0)
    assert 'enctype="multipart/form-data"' in upload_form.group(0)
    file_input = re.search(r'<input\s+type="file"[^>]*>', upload_form.group(1))
    assert file_input is not None
    assert 'name="file"' in file_input.group(0)
    assert 'accept=".pdf"' in file_input.group(0)
    assert "required" in file_input.group(0)
    assert '<button type="submit">Start audit</button>' in upload_form.group(1)
