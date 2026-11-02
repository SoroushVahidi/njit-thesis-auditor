"""Release configuration, public rendering, and real responsive browser checks."""

from __future__ import annotations

import importlib
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from njit_auditor.windows_download import WindowsDownload, windows_download

# Synthetic configuration only: this URL is never requested or published.
URL = (
    "https://github.com/SoroushVahidi/njit-thesis-auditor-desktop/releases/"
    "download/desktop-v1.0.0/NJIT-Thesis-Auditor-Setup-1.0.0.exe"
)
PREFIX = "NJIT_AUDITOR_WINDOWS_DOWNLOAD_"


def release_env(**overrides: str) -> dict[str, str]:
    values = {
        "URL": URL, "APPROVED": "1", "SHA256": "ab" * 32,
        "SIZE_BYTES": "104857600", "WINDOWS_VERSIONS": "Windows 11",
        "ARCHITECTURE": "x64", "EDITION": "njit", "NATIVE_TESTED": "1",
    }
    values.update(overrides)
    return {PREFIX + key: value for key, value in values.items()}



@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    for key in release_env():
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("NJIT_AUDITOR_WEB_RUNTIME_DIR", str(tmp_path / "jobs"))
    import njit_auditor.web_app as wa

    importlib.reload(wa)
    # Do not even enumerate private sample metadata in this suite.
    monkeypatch.setattr(wa, "list_builtin_samples", lambda: [])
    with TestClient(wa.app) as app_client:
        yield app_client


def approve(monkeypatch: pytest.MonkeyPatch, url: str = URL) -> None:
    for key, value in release_env(URL=url).items():
        monkeypatch.setenv(key, value)


def section(response: Any) -> str:
    assert response.status_code == 200
    return response.text.split('id="windows-download"', 1)[1].split("</section>", 1)[0]


@pytest.mark.parametrize("approval", ["", "0", "true", "yes", " 1", "1 "])
def test_unapproved_config_never_exposes_metadata(approval: str) -> None:
    assert windows_download(release_env(APPROVED=approval)) == (
        WindowsDownload()
    )


@pytest.mark.parametrize(
    "url",
    [
        "", "javascript:alert(1)", "data:text/html,test", "file:///tmp/setup.exe",
        URL.replace("https:", "http:"), URL.replace("https:", ""),
        URL.replace("github.com", "github.com.evil.example"),
        URL.replace("github.com", "github.com@evil.example"),
        URL.replace("github.com", "user:secret@github.com"),
        URL.replace("github.com", "github.com:443"),
        URL.replace("github.com", "127.0.0.1"),
        URL.replace("github.com", "[::1]"),
        URL.replace("github.com", "github.com."),
        URL.replace("njit-thesis-auditor-desktop", "njit-thesis-auditor"),
        URL.replace("SoroushVahidi", "another-owner"),
        URL.replace("/download/desktop-v1.0.0/", "/latest/download/"),
        URL.replace("/desktop-v1.0.0/", "/desktop-v2.0.0/"),
        URL.replace(".exe", ".zip"), URL.replace(".exe", ".exe/other"),
        URL.replace("/download/", "/%64ownload/"),
        URL.replace("/download/", "/../download/"),
        URL.replace("/download/", "\\download/"),
        URL.replace("github.com", "githu\u0432.com"),
        URL + "?token=secret", URL + "#fragment", URL + '\" onclick=\"alert(1)',
        URL + "\n", "\t" + URL, URL + "\x00", " " + URL, URL + " ", "x" * 513,
    ],
)
def test_unsafe_urls_fail_closed(url: str) -> None:
    assert windows_download(release_env(URL=url)) == (
        WindowsDownload()
    )


@pytest.mark.parametrize("version", ["1.0.0", "0.2.0-rc.1", "2.10.3"])
def test_approved_version_and_checksum_are_consistent(version: str) -> None:
    url = URL.replace("1.0.0", version)
    release = windows_download(
        release_env(URL=url, SHA256="AB" * 32)
    )
    assert release.url == url
    assert release.version == version
    assert release.sha256 == "ab" * 32
    assert release.release_notes_url.endswith(f"/tag/desktop-v{version}")


@pytest.mark.parametrize("digest", ["", "a" * 63, "a" * 65, "g" * 64, "<script>", "a" * 64 + "\n"])
def test_malformed_checksum_disables_release(digest: str) -> None:
    assert not windows_download(
        release_env(SHA256=digest)
    ).url


def test_default_and_request_parameters_cannot_enable_link(client: TestClient) -> None:
    for path in ("/", f"/?{PREFIX}URL={URL}&{PREFIX}APPROVED=1"):
        rendered = section(client.get(path, headers={PREFIX + "APPROVED": "1"}))
        assert "Download unavailable while release validation is pending" in rendered
        assert 'disabled aria-describedby="windows-download-pending"' in rendered
        assert "href=" not in rendered
        assert "Version " not in rendered
        assert URL not in rendered


def test_approved_link_and_runtime_rollback(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    approve(monkeypatch)
    monkeypatch.setenv(PREFIX + "SHA256", "a" * 64)
    rendered = section(client.get("/"))
    assert f'href="{URL}"' in rendered
    assert 'referrerpolicy="no-referrer"' in rendered
    assert "Download NJIT Thesis Auditor for Windows" in rendered
    assert "Version 1.0.0" in rendered
    assert "Windows 11 (x64)" in rendered
    assert "100.0 MiB (104,857,600 bytes)" in rendered
    assert "a" * 64 in rendered
    assert "Start menu" in rendered
    assert "No Python or technical setup required" in rendered
    assert "online auditor below processes uploads on this server" in rendered
    monkeypatch.setenv(PREFIX + "APPROVED", "0")
    assert "href=" not in section(client.get("/"))


def test_invalid_config_not_reflected_in_html(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    approve(monkeypatch, 'https://evil.example/<script>alert("secret")</script>')
    rendered = section(client.get("/"))
    assert "evil.example" not in rendered
    assert "secret" not in rendered
    assert "href=" not in rendered


def test_upload_error_and_help_rules_remain_available(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    approve(monkeypatch)
    response = client.post("/audits", files={"file": ("synthetic.txt", b"test", "text/plain")})
    assert response.status_code == 400
    assert f'href="{URL}"' in response.text
    assert "Could not start audit" in response.text
    for route in ("/help", "/rules", "/healthz"):
        assert client.get(route).status_code == 200


@pytest.mark.parametrize("width", [320, 390, 1440])
@pytest.mark.parametrize("available", [False, True])
def test_browser_layout_and_keyboard(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, width: int, available: bool
) -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    if available:
        approve(monkeypatch)
        monkeypatch.setenv(PREFIX + "SHA256", "a" * 64)
    # Render the actual HTTP response in Chromium. All network requests are denied;
    # the synthetic release URL must never be contacted, even during validation.
    with playwright.sync_playwright() as runner:
        browser = runner.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": width, "height": 900})
            page.route("**/*", lambda route: route.abort())
            page.set_content(client.get("/").text)
            panel = page.locator("#windows-download")
            assert panel.is_visible()
            assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
            if available:
                link = panel.get_by_role("link", name="Download for Windows", exact=True)
                assert link.get_attribute("href") == URL
                link.focus()
                assert link.evaluate("el => el === document.activeElement")
                page.keyboard.press("Tab")
                assert panel.get_by_role("link", name="Release notes", exact=False).evaluate(
                    "el => el === document.activeElement"
                )
                page.keyboard.press("Tab")
                page.keyboard.press("Enter")
                assert panel.locator("details").get_attribute("open") is not None
                assert panel.locator("code").is_visible()
                assert not page.evaluate("document.documentElement.scrollWidth > innerWidth")
            else:
                assert panel.get_by_role("button", name="Download for Windows").is_disabled()
                assert panel.locator("a").count() == 0
        finally:
            browser.close()


@pytest.mark.parametrize("key", list(release_env()))
def test_every_required_release_field_must_be_present(key: str) -> None:
    env = release_env()
    del env[key]
    assert windows_download(env) == WindowsDownload()


@pytest.mark.parametrize(("key", "value"), [
    ("EDITION", "generic"), ("EDITION", "Document Format Auditor"),
    ("NATIVE_TESTED", "0"),
    ("ARCHITECTURE", "arm64"), ("SIZE_BYTES", "0"), ("SIZE_BYTES", "-1"),
    ("SIZE_BYTES", "1.5"), ("SIZE_BYTES", "100 MB"), ("SIZE_BYTES", "9" * 13),
    ("WINDOWS_VERSIONS", "Windows XP"), ("WINDOWS_VERSIONS", "Windows 10"),
    ("WINDOWS_VERSIONS", "<script>"),
])
def test_unqualified_or_malformed_release_fails_closed(key: str, value: str) -> None:
    assert windows_download(release_env(**{key: value})) == WindowsDownload()


@pytest.mark.parametrize("versions", ["Windows 11"])
def test_only_qualified_windows_versions_are_displayed(versions: str) -> None:
    assert windows_download(release_env(WINDOWS_VERSIONS=versions)).windows_versions == versions
