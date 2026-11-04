"""About content, navigation and bundled offline resources; synthetic jobs only."""
from __future__ import annotations

import ast
import importlib
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from njit_auditor import offline_app
from njit_auditor.desktop_network import is_loopback_address, loopback_connect, loopback_connect_ex

ROOT = Path(__file__).resolve().parents[1]
RELEASES = 'https://github.com/SoroushVahidi/njit-thesis-auditor-desktop'


@pytest.fixture()
def web(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setenv('NJIT_AUDITOR_WEB_RUNTIME_DIR', str(tmp_path/'web'))
    import njit_auditor.web_app as module
    importlib.reload(module)
    return module


def test_about_content_and_downloads_link(web: Any) -> None:
    with TestClient(web.app) as client:
        response = client.get('/about')
    assert response.status_code == 200
    text = response.text
    for section in ['About the tool', 'Development and acknowledgments', 'Feedback and downloads']:
        assert section in text
    for person in ['Soroush Vahidi', 'Ester Flaim', 'Ioannis Koutis', 'Sotirios G. Ziavras']:
        assert person in text
    assert 'Professor Ioannis Koutis, for early project discussions.' in text
    assert 'Esther Flaim' not in text
    assert 'May 2026' in text and 'November 2026' in text
    assert 'Computer Science PhD student' in text
    assert 'not an official NJIT product' in text
    assert 'does not replace Graduate Studies review' in text
    assert 'href="mailto:sv96@njit.edu"' in text
    assert f'href="{RELEASES}"' in text
    assert 'Windows desktop downloads and release notes' in text
    assert 'public source repository' not in text
    assert 'mail.google.com' not in text and 'Message-ID' not in text
    assert 'aria-current="page">About Us</a>' in text


@pytest.mark.parametrize('state', ['pending', 'running', 'complete', 'failed'])
def test_about_navigation_on_audit_states(web: Any, state: str) -> None:
    web._set_job(web.JobState(job_id='about-navigation', state=state,
                             created_at=datetime.now(timezone.utc).isoformat(),
                             file_name='synthetic.pdf'))
    with TestClient(web.app) as client:
        response = client.get('/audits/about-navigation')
    assert response.status_code == 200
    assert '<a href="/about" class="site-nav__link">About Us</a>' in response.text


@pytest.mark.parametrize('path', ['/', '/help', '/rules'])
def test_about_navigation_on_reference_and_upload_pages(web: Any, path: str) -> None:
    with TestClient(web.app) as client:
        response = client.get(path)
    assert response.status_code == 200
    assert '<a href="/about" class="site-nav__link">About Us</a>' in response.text


def test_future_desktop_bundle_allowlist_contains_about() -> None:
    spec = ast.parse((ROOT/'packaging/offline_desktop.spec').read_text())
    templates = next(ast.literal_eval(node.value) for node in ast.walk(spec)
                     if isinstance(node, ast.Assign)
                     and any(isinstance(t, ast.Name) and t.id == 'TEMPLATES' for t in node.targets))
    assert 'about.html' in templates
    verifier = ast.parse((ROOT/'scripts/verify_windows_bundle.py').read_text())
    resources = next(ast.literal_eval(node.value) for node in ast.walk(verifier)
                     if isinstance(node, ast.Assign)
                     and any(isinstance(t, ast.Name) and t.id == 'resources' for t in node.targets))
    assert 'src/njit_auditor/templates/about.html' in resources


def test_about_renders_from_bundle_without_external_network(
    web: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundle = tmp_path/'bundle'
    for directory, names in [('templates', ['base.html', 'about.html']),
                             ('offline_templates', ['index.html'])]:
        target = bundle/'src/njit_auditor'/directory
        target.mkdir(parents=True)
        for name in names:
            (target/name).write_bytes((ROOT/'src/njit_auditor'/directory/name).read_bytes())
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, '_MEIPASS', str(bundle), raising=False)
    monkeypatch.setattr(web, 'RUNTIME_DIR', web.RUNTIME_DIR)
    monkeypatch.setattr(web, '_after_audit_task', web._after_audit_task)
    monkeypatch.setattr(web, '_jobs', {})
    attempts = []

    def deny(*args, **kwargs):
        attempts.append('external')
        raise AssertionError('External network requested by local About page')

    def connect(sock, address):
        if is_loopback_address(sock.family, address):
            return loopback_connect(sock, address)
        return deny()

    def connect_ex(sock, address):
        if is_loopback_address(sock.family, address):
            return loopback_connect_ex(sock, address)
        return deny()

    monkeypatch.setattr(socket.socket, 'connect', connect)
    monkeypatch.setattr(socket.socket, 'connect_ex', connect_ex)
    monkeypatch.setattr(socket, 'getaddrinfo', deny)
    monkeypatch.setattr(socket, 'create_connection', deny)
    data = tmp_path/'profile'
    offline_app.prepare_local_storage(data)
    app = offline_app.create_offline_app(port=17391, data_root=data, launch_ticket='about-ticket')
    with TestClient(app, base_url='http://127.0.0.1:17391') as client:
        assert client.get('/_session/start?ticket=about-ticket').status_code == 200
        response = client.get('/about')
        assert response.status_code == 200
        assert 'This page is bundled with the app.' in response.text
        assert 'Email and release links require an internet connection.' in response.text
        assert 'Ester Flaim' in response.text
        assert f'href="{RELEASES}"' in response.text
        assert app.state.templates.env.loader.searchpath == [
            str(bundle/'src/njit_auditor/offline_templates'),
            str(bundle/'src/njit_auditor/templates'),
        ]
    assert attempts == []
