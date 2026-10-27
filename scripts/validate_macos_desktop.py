"""Builder-only native frozen smoke/parity test; no external services or real dissertations."""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shlex
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from fastapi.testclient import TestClient
from inspect_macos_bundle import inspect_bundle

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from test_offline_desktop import (  # noqa: E402
    _normalize,
    _normalize_audit_time,
    _normalize_markdown,
    _pdf,
    _report_pdf_content,
)

from njit_auditor import web_app  # noqa: E402


def wait_for(predicate, message: str, seconds: float = 20) -> None:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if predicate():
            return
        time.sleep(0.05)
    raise RuntimeError(message)


def validate(bundle: Path) -> dict:
    architecture = platform.machine()
    inspection = inspect_bundle(bundle, architecture)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if inspection["build"]["commit"] != commit:
        raise RuntimeError("Validate the same source commit used to build the frozen app")
    executable = bundle / "Contents/MacOS/NJIT Thesis Auditor"
    outcomes = []
    with tempfile.TemporaryDirectory(prefix="njit-native-synthetic-") as directory:
        root = Path(directory)
        # HOME isolates macOS Application Support. No override is added to product code.
        local_root = root / "Library/Application Support/NJIT Thesis Auditor"
        opener = root / "capture-browser"
        ticket = root / "ticket"
        opener.write_text(
            "#!/bin/sh\numask 077\nprintf '%s' \"$1\" > " + shlex.quote(str(ticket)) + "\n",
            encoding="utf-8",
        )
        opener.chmod(0o700)
        environment = {
            **os.environ,
            "HOME": str(root),
            "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
            "BROWSER": shlex.quote(str(opener)) + " %s",
        }
        for attempt in range(2):
            ticket.unlink(missing_ok=True)
            with (root / "launcher.log").open("wb") as log:
                process = subprocess.Popen(
                    [str(executable), "--headless"],
                    env=environment,
                    cwd="/",
                    stdout=log,
                    stderr=subprocess.STDOUT,
                )
                client = None
                csrf = None
                try:

                    def started():
                        if process.poll() is not None:
                            raise RuntimeError("Frozen launcher stopped before opening browser")
                        return ticket.is_file() and ticket.stat().st_size > 0

                    wait_for(started, "Browser opener was not called")
                    url = ticket.read_text()
                    parsed = urlsplit(url)
                    assert parsed.hostname == "127.0.0.1"
                    base = f"http://{parsed.netloc}"
                    client = httpx.Client(
                        base_url=base, follow_redirects=True, timeout=30, trust_env=False
                    )
                    assert client.get("/").status_code == 403
                    home = client.get(url)
                    assert home.status_code == 200
                    csrf = re.search(r'name="csrf_token" value="([^"]+)"', home.text).group(1)
                    assert 'name="pdf_url"' not in home.text
                    headers = {"Origin": base}
                    assert client.get("/", headers={"Host": "evil.example"}).status_code == 403
                    assert (
                        client.get("/", headers={"Sec-Fetch-Site": "cross-site"}).status_code == 403
                    )
                    assert client.post("/quit", headers=headers).status_code == 403
                    assert client.post(
                        "/audits/url",
                        data={"pdf_url": "https://invalid.example/x", "csrf_token": csrf},
                        headers=headers,
                    ).status_code in {404, 405}
                    assert client.get("/about").status_code == 200
                    assert client.get("/rules").status_code == 200
                    malformed = client.post(
                        "/audits",
                        files={"file": ("bad.pdf", b"not a PDF")},
                        data={"csrf_token": csrf},
                        headers=headers,
                    )
                    assert malformed.status_code == 400
                    web_app.RUNTIME_DIR = root / "web-parity"
                    kinds = (
                        ("normal", "unicode", "rotated", "low_text")
                        if attempt == 0
                        else ("normal",)
                    )
                    for kind in kinds:
                        payload = _pdf(kind)
                        response = client.post(
                            "/audits",
                            files={"file": ("synthetic.pdf", payload, "application/pdf")},
                            data={"csrf_token": csrf},
                            headers=headers,
                            follow_redirects=False,
                        )
                        assert response.status_code == 303
                        job_url = response.headers["location"]
                        wait_for(
                            lambda: (
                                client.get(job_url + "/status").json()["state"]
                                in {"complete", "failed"}
                            ),
                            "Frozen audit did not finish",
                            125,
                        )
                        assert client.get(job_url + "/status").json()["state"] == "complete"
                        assert client.get(job_url).status_code == 200
                        with TestClient(web_app.app) as web:
                            uploaded = web.post(
                                "/audits",
                                files={"file": ("synthetic.pdf", payload, "application/pdf")},
                                follow_redirects=False,
                            )
                            assert uploaded.status_code == 303
                            web_url = uploaded.headers["location"]
                            for suffix in ("json", "markdown", "text", "student-report.pdf"):
                                path = "/download/" + suffix
                                frozen, source = client.get(job_url + path), web.get(web_url + path)
                                assert frozen.status_code == source.status_code == 200
                                if suffix == "json":
                                    assert _normalize(frozen.json()) == _normalize(source.json())
                                elif suffix == "markdown":
                                    assert _normalize_markdown(
                                        frozen.content
                                    ) == _normalize_markdown(source.content)
                                elif suffix == "text":
                                    assert _normalize_audit_time(
                                        frozen.text
                                    ) == _normalize_audit_time(source.text)
                                else:
                                    assert _report_pdf_content(
                                        frozen.content
                                    ) == _report_pdf_content(source.content)
                            for path in ("/pdf", "/highlighted-page.pdf?page=1"):
                                frozen, source = client.get(job_url + path), web.get(web_url + path)
                                assert frozen.status_code == source.status_code == 200
                                assert _report_pdf_content(frozen.content) == _report_pdf_content(
                                    source.content
                                )
                        outcomes.append(f"restart-{attempt}:{kind}:frozen-web-parity")
                    quit_response = client.post("/quit", data={"csrf_token": csrf}, headers=headers)
                    assert quit_response.status_code == 200
                    process.wait(timeout=15)
                    assert process.returncode == 0
                    assert not list((local_root / "audits").iterdir())
                    assert not list((local_root / "tmp").iterdir())
                    try:
                        client.get("/")
                    except httpx.TransportError:
                        pass
                    else:
                        raise AssertionError("Listener remained after Quit")
                    outcomes.append(f"restart-{attempt}:security-cleanup-quit")
                finally:
                    if process.poll() is None and client is not None and csrf is not None:
                        try:
                            client.post(
                                "/quit", data={"csrf_token": csrf}, headers={"Origin": base}
                            )
                        except httpx.HTTPError:
                            pass
                    if process.poll() is None:
                        # macOS SIGTERM uses the same supervised shutdown path.
                        process.terminate()
                        try:
                            process.wait(timeout=15)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait(timeout=5)
                            raise RuntimeError(
                                "Native cleanup failed; inspect owned descendants before retrying"
                            ) from None
                    if client:
                        client.close()
    return {
        "state": "COMPLETED_SUCCESS",
        "architecture": architecture,
        "macos": platform.mac_ver()[0],
        "outcomes": outcomes,
        "source_commit": inspection["build"]["commit"],
        "headless_frozen_smoke_tested": True,
        "finder_install_tested": False,
        "default_browser_tested": False,
        "os_network_disconnected_tested": False,
        "distribution_approved": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(
        json.dumps(validate(args.bundle.resolve()), indent=2) + "\n", encoding="utf-8"
    )
    print("COMPLETED_SUCCESS: frozen synthetic checks; complete the manual Mac checklist")


if __name__ == "__main__":
    main()
