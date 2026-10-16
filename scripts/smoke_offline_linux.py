"""Exercise the built Linux executable with synthetic data and no real browser.

The browser launch URL travels through a private Unix socket and is never
written to a log or regular file. Optional strace elides network payloads.
"""

from __future__ import annotations

import argparse
import http.cookiejar
import os
import re
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import fitz


def request(
    opener: urllib.request.OpenerDirector,
    url: str,
    *,
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, bytes, str]:
    outgoing = urllib.request.Request(url, data=data, headers=headers or {})
    try:
        with opener.open(outgoing, timeout=20) as response:
            return response.status, response.read(), response.geturl()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), exc.geturl()


def synthetic_pdf() -> bytes:
    doc = fitz.open()
    doc.new_page().insert_text((60, 80), "Synthetic offline package smoke test")
    data = doc.tobytes()
    doc.close()
    return data


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--trace", type=Path, help="strace bind/connect output prefix")
    args = parser.parse_args()
    executable = args.bundle / "NJIT Thesis Auditor"
    if not executable.is_file():
        raise SystemExit(f"Missing executable: {executable}")

    with tempfile.TemporaryDirectory(prefix="njit-offline-smoke-") as scratch:
        root = Path(scratch)
        sock_path = root / "browser.sock"
        wrapper = root / "browser-wrapper"
        wrapper.write_text(
            "#!/usr/bin/env python3\n"
            "import os, socket, sys\n"
            "with socket.socket(socket.AF_UNIX) as s:\n"
            "    s.connect(os.environ['OFFLINE_SMOKE_SOCKET'])\n"
            "    s.sendall(sys.argv[-1].encode('utf-8'))\n",
            encoding="utf-8",
        )
        wrapper.chmod(0o700)
        receiver = socket.socket(socket.AF_UNIX)
        receiver.bind(str(sock_path))
        receiver.listen(1)
        receiver.settimeout(20)
        env = os.environ.copy()
        env.update(
            {
                "BROWSER": str(wrapper),
                "OFFLINE_SMOKE_SOCKET": str(sock_path),
                "XDG_DATA_HOME": str(root / "profile"),
            }
        )
        command = [str(executable), "--headless"]
        if args.trace:
            command = [
                "strace",
                "-ff",
                "-e",
                "trace=bind,connect,sendto,sendmsg",
                "-s",
                "0",
                "-o",
                str(args.trace),
                *command,
            ]
        process = subprocess.Popen(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            connection, _ = receiver.accept()
            with connection:
                launch_url = connection.recv(4096).decode("utf-8")
            parsed = urllib.parse.urlsplit(launch_url)
            assert parsed.scheme == "http" and parsed.hostname == "127.0.0.1"
            assert parsed.port is not None and parsed.path == "/_session/start"
            base = f"http://127.0.0.1:{parsed.port}"
            opener = urllib.request.build_opener(
                urllib.request.ProxyHandler({}),
                urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),
            )
            assert request(opener, base + "/")[0] == 403
            assert request(opener, base + "/audits/x/pdf")[0] == 403
            assert request(opener, base + "/audits/x/download/json")[0] == 403
            assert request(opener, launch_url)[0] == 200
            assert request(opener, launch_url)[0] == 403
            status, html, _ = request(opener, base + "/")
            assert status == 200
            csrf_match = re.search(rb'name="csrf_token" value="([^"]+)"', html)
            assert csrf_match is not None
            csrf = csrf_match.group(1)
            boundary = b"njit-synthetic-boundary"
            body = (
                b"--" + boundary + b"\r\n"
                b'Content-Disposition: form-data; name="csrf_token"\r\n\r\n'
                + csrf
                + b"\r\n--"
                + boundary
                + b"\r\n"
                b'Content-Disposition: form-data; name="file"; filename="synthetic.pdf"\r\n'
                b"Content-Type: application/pdf\r\n\r\n"
                + synthetic_pdf()
                + b"\r\n--"
                + boundary
                + b"--\r\n"
            )
            status, _, job_url = request(
                opener,
                base + "/audits",
                data=body,
                headers={
                    "Origin": base,
                    "Content-Type": "multipart/form-data; boundary=njit-synthetic-boundary",
                },
            )
            assert status == 200 and "/audits/" in job_url
            for _ in range(100):
                status, payload, _ = request(opener, job_url + "/status")
                if status == 200 and b'"state":"complete"' in payload:
                    break
                time.sleep(0.1)
            else:
                raise AssertionError("synthetic audit did not complete")
            for suffix in (
                "/pdf",
                "/download/json",
                "/download/markdown",
                "/download/text",
                "/download/student-report.pdf",
                "/highlighted-page.pdf?page=1",
            ):
                assert request(opener, job_url + suffix)[0] == 200, suffix
            assert (
                request(
                    opener,
                    base + "/quit",
                    data=b"csrf_token=" + csrf,
                    headers={"Origin": base, "Content-Type": "application/x-www-form-urlencoded"},
                )[0]
                == 200
            )
            process.wait(timeout=30)
            assert process.returncode == 0
            managed = root / "profile" / "njit-thesis-auditor"
            assert not any((managed / "audits").iterdir())
            assert not any((managed / "tmp").iterdir())
            try:
                request(opener, base + "/")
            except urllib.error.URLError:
                pass  # Connection refusal proves the listener is gone.
            else:
                raise AssertionError("listener still answered after Quit")
            print("PASS: packaged Linux synthetic audit, protected routes, reports, Quit, cleanup")
        finally:
            receiver.close()
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)
            process.communicate(timeout=10)


if __name__ == "__main__":
    main()
