"""Tests for the /healthz and /version deployment endpoints."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient


def _make_app(tmp_path: Path) -> Any:
    """Import the web app with RUNTIME_DIR pointed at a temp directory."""
    os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"] = str(tmp_path / "web_audits")
    import importlib

    import njit_auditor.web_app as wa

    importlib.reload(wa)
    return wa.app, wa


@pytest.fixture()
def client(tmp_path: Path) -> tuple[TestClient, Any]:
    app, wa = _make_app(tmp_path)
    return TestClient(app, raise_server_exceptions=False), wa


# ---------------------------------------------------------------------------
# /healthz
# ---------------------------------------------------------------------------


def test_healthz_returns_200(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.get("/healthz")
    assert resp.status_code == 200


def test_healthz_body_is_minimal_and_ok(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.get("/healthz")
    body = resp.json()
    assert body["ok"] is True
    assert body["app"] == "njit-thesis-auditor"
    assert body["status"] == "healthy"


def test_healthz_does_not_leak_runtime_paths_or_filenames(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    c, _ = client
    resp = c.get("/healthz")
    text = resp.text
    assert str(tmp_path) not in text
    assert "upload.pdf" not in text
    assert os.sep + "home" + os.sep not in text


def test_healthz_does_not_require_an_audit_job(client: tuple[TestClient, Any]) -> None:
    # No job was created in this test; the endpoint must still succeed.
    c, _ = client
    resp = c.get("/healthz")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# /version
# ---------------------------------------------------------------------------


def test_version_returns_200(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    resp = c.get("/version")
    assert resp.status_code == 200


def test_version_contains_required_fields(client: tuple[TestClient, Any]) -> None:
    c, _ = client
    body = c.get("/version").json()
    for key in (
        "app",
        "commit",
        "branch",
        "process_start_time",
        "python_version",
        "environment",
    ):
        assert key in body, key
    assert body["app"] == "njit-thesis-auditor"


def test_version_does_not_leak_paths_filenames_or_env(
    client: tuple[TestClient, Any], tmp_path: Path
) -> None:
    c, _ = client
    text = c.get("/version").text
    assert str(tmp_path) not in text
    assert "upload.pdf" not in text
    assert "NJIT_AUDITOR_WEB_RUNTIME_DIR" not in text


def test_read_git_metadata_falls_back_to_unknown_when_git_unavailable(
    client: tuple[TestClient, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    _, wa = client

    def _boom(*_args: object, **_kwargs: object) -> object:
        raise FileNotFoundError("git executable not found")

    monkeypatch.setattr(subprocess, "run", _boom)
    commit, branch = wa._read_git_metadata()
    assert commit == "unknown"
    assert branch == "unknown"


def test_version_endpoint_survives_git_metadata_failure(
    client: tuple[TestClient, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    c, wa = client
    monkeypatch.setattr(wa, "_GIT_COMMIT", "unknown")
    monkeypatch.setattr(wa, "_GIT_BRANCH", "unknown")
    resp = c.get("/version")
    assert resp.status_code == 200
    body = resp.json()
    assert body["commit"] == "unknown"
    assert body["branch"] == "unknown"
