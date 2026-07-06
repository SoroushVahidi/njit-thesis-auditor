"""Playwright regression: /help must not force horizontal page overflow at 390px."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

playwright = pytest.importorskip("playwright.sync_api")
sync_playwright = playwright.sync_playwright


def _make_app(tmp_path: Path):
    os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"] = str(tmp_path / "web_audits")
    import importlib

    import njit_auditor.web_app as wa

    importlib.reload(wa)
    return TestClient(wa.app, raise_server_exceptions=False), wa


@pytest.fixture()
def app_url(tmp_path: Path) -> str:
    import threading
    import time

    import uvicorn

    _, wa = _make_app(tmp_path)
    config = uvicorn.Config(wa.app, host="127.0.0.1", port=0, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.time() + 10
    while not server.started and time.time() < deadline:
        time.sleep(0.05)
    assert server.started
    host, port = server.servers[0].sockets[0].getsockname()[:2]
    yield f"http://{host}:{port}"
    server.should_exit = True
    thread.join(timeout=5)


def test_help_has_no_horizontal_overflow_at_390px(app_url: str) -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(viewport={"width": 390, "height": 844}).new_page()
        page.goto(f"{app_url}/help", wait_until="networkidle")
        overflow = page.evaluate(
            """() => {
              const doc = document.documentElement;
              const body = document.body;
              return doc.scrollWidth <= doc.clientWidth + 1
                && body.scrollWidth <= body.clientWidth + 1;
            }"""
        )
        browser.close()
    assert overflow is True
