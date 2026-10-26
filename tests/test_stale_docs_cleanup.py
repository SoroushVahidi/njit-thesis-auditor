"""Regression tests for stale-doc cleanup and PR #305 supersession checks."""

from __future__ import annotations

import os
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


def test_index_page_explains_url_import_limits(client: tuple[TestClient, object]) -> None:
    """The blocked example is replaced by an optional form and upload fallback."""
    c, _ = client
    resp = c.get("/")
    assert resp.status_code == 200
    body = resp.content
    assert b"example-thesis-box" not in body
    assert b"fill-example-url" not in body
    assert b"digitalcommons.njit.edu" not in body
    assert b"Some websites block downloads" in body
