"""Offline reference pages, bundle resources, and safe recovery (synthetic data only)."""

from __future__ import annotations

import ast
import shutil
import socket
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from jinja2 import BaseLoader, DictLoader, TemplateNotFound

from njit_auditor import web_app
from njit_auditor.offline_app import create_offline_app, prepare_local_storage

ROOT = Path(__file__).resolve().parents[1]
HOST = "http://127.0.0.1:17391"


@pytest.fixture()
def reference_client(tmp_path, monkeypatch):
    monkeypatch.setattr(web_app, "RUNTIME_DIR", tmp_path / "audits")
    monkeypatch.setattr(web_app, "_after_audit_task", None)
    prepare_local_storage(tmp_path)
    app = create_offline_app(port=17391, data_root=tmp_path, launch_ticket="synthetic-ticket")
    with TestClient(app, base_url=HOST) as client:
        client.get("/_session/start?ticket=synthetic-ticket")
        yield client


def test_reference_pages_need_no_network_and_keep_local_navigation(reference_client, monkeypatch):
    attempts = []

    def deny(*args, **kwargs):
        attempts.append(True)
        raise AssertionError("Unexpected external connection")

    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(socket, "getaddrinfo", deny)
    monkeypatch.setattr(socket, "gethostbyname", deny)
    for path in ("/", "/help", "/rules", "/about"):
        response = reference_client.get(path)
        assert response.status_code == 200
        assert 'href="/help"' in response.text and 'href="/rules"' in response.text
        assert 'href="/"' in response.text
        assert "create_offline_app.&lt;locals&gt;" not in response.text
        assert "Cache-Control" in response.headers
    assert 'id="P011"' in reference_client.get("/rules").text
    assert "only in your local application data" in reference_client.get("/help").text
    assert attempts == []


@pytest.mark.parametrize("path", ["/help", "/rules"])
def test_reference_pages_preserve_request_protection(reference_client, path):
    client = reference_client
    for headers in (
        {"Host": "localhost:17391"},
        {"Origin": "https://example.invalid"},
        {"Sec-Fetch-Site": "cross-site"},
    ):
        assert client.get(path, headers=headers).status_code == 403
    # The Quit form on reference pages must still require Origin and CSRF.
    assert client.post("/quit").status_code == 403
    assert client.post("/quit", headers={"Origin": HOST}).status_code == 403
    client.cookies.clear()
    assert client.get(path).status_code == 403


@pytest.mark.parametrize("page", ["/help", "/rules"])
@pytest.mark.parametrize("missing", ["page", "base"])
def test_missing_template_has_safe_recovery_without_other_pages_breaking(
    reference_client, monkeypatch, page, missing, tmp_path, caplog
):
    env = reference_client.app.state.templates.env
    original = env.loader
    name = "base.html" if missing == "base" else page[1:] + ".html"

    class MissingTemplateLoader(BaseLoader):
        def get_source(self, environment, template):
            if template == name:
                raise TemplateNotFound(str(tmp_path / "sensitive-marker" / template))
            return original.get_source(environment, template)

    monkeypatch.setattr(env, "loader", MissingTemplateLoader())
    env.cache.clear()
    response = reference_client.get(page)
    assert response.status_code == 503
    assert "complete copy" in response.text
    assert 'href="/"' in response.text and 'action="/quit"' in response.text
    assert str(tmp_path) not in response.text + caplog.text
    assert "sensitive-marker" not in response.text + caplog.text
    assert "Traceback" not in response.text + caplog.text
    assert "default-src 'self'" in response.headers["Content-Security-Policy"]
    assert reference_client.post("/quit", headers={"Origin": HOST}).status_code == 403
    monkeypatch.setattr(env, "loader", original)
    env.cache.clear()
    assert reference_client.get(page).status_code == 200
    assert reference_client.get("/").status_code == 200


@pytest.mark.parametrize("offline", [True, False])
@pytest.mark.parametrize(
    "damage", ["missing", "invalid-json", "null", "empty", "object", "entry", "encoding", "denied"]
)
def test_unavailable_catalog_is_not_reported_as_zero_rules(
    reference_client, monkeypatch, tmp_path, offline, damage
):
    catalog = tmp_path / "damaged-catalog.json"
    if damage != "missing":
        catalog.write_text({
            "invalid-json": "{", "null": "null", "object": "{}", "entry": "[null]",
        }.get(damage, "[]"))
    if damage == "encoding":
        catalog.write_bytes(b"\xff\xfe")
    if damage == "denied":
        original_read = Path.read_text

        def read(path, *args, **kwargs):
            if path == catalog:
                raise PermissionError("sensitive-path-marker")
            return original_read(path, *args, **kwargs)

        monkeypatch.setattr(Path, "read_text", read)
    monkeypatch.setattr(web_app, "_RULES_JSON_PATH", catalog)
    client = reference_client if offline else TestClient(web_app.app)
    response = client.get("/rules")
    assert response.status_code == 503
    assert "Rule Reference is unavailable" in response.text
    assert "0 rules" not in response.text and "sensitive-path-marker" not in response.text
    assert str(tmp_path) not in response.text
    assert client.get("/help").status_code == 200


def test_spec_resources_resolve_from_frozen_root_without_checkout_or_cwd(
    tmp_path, monkeypatch, reference_client
):
    # Evaluate only the actual spec's data declarations, without building binaries.
    # This exercises the common data layout used by native platform packagers.
    spec = ast.parse((ROOT / "packaging/offline_desktop.spec").read_text())
    namespace = {"ROOT": ROOT, "resources": tmp_path / "generated"}
    for node in spec.body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            selected = node.targets[0].id in {"TEMPLATES", "DATA"}
        else:
            selected = isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name)
            selected = selected and node.target.id == "DATA"
        if selected:
            exec(compile(ast.Module(body=[node], type_ignores=[]), "spec-data", "exec"), namespace)
    bundle = tmp_path / "frozen"
    for source, destination in namespace["DATA"]:
        source = Path(source)
        if not source.is_file():
            # Build provenance and third-party notices are generated by the builder.
            assert source.is_relative_to(namespace["resources"])
            continue
        target = bundle / destination / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    expected = web_app._build_rule_catalog()["total_student"]
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(bundle), raising=False)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        web_app, "_RULES_JSON_PATH", bundle / "data/processed/rules/project_added_rules.json"
    )
    # Build a new template loader only after switching to the frozen resource root.
    app = create_offline_app(port=17391, data_root=tmp_path, launch_ticket="bundle-ticket")
    with TestClient(app, base_url=HOST) as client:
        client.get("/_session/start?ticket=bundle-ticket")
        for path in ("/help", "/rules", "/about", "/app-icon.ico"):
            assert client.get(path).status_code == 200
        assert f"{expected} rules" in client.get("/rules").text
    # Confirm an omitted template cannot silently fall back to the source checkout.
    env = app.state.templates.env
    env.cache.clear()
    monkeypatch.setattr(env, "loader", DictLoader({}))
    with TestClient(app, base_url=HOST) as client:
        client.get("/_session/start?ticket=bundle-ticket", follow_redirects=False)
        assert client.get("/help").status_code == 503
