"""Compare a running packaged desktop against actual online synthetic-audit outputs.

Reference capture needs network access; desktop validation blocks non-loopback
browser requests. No private documents or samples are loaded. Evidence stays local.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import pymupdf
from desktop_reference import BASELINE, EXPORTS, PRODUCTION_URL, load_reference
from lxml import html
from playwright.sync_api import sync_playwright

from njit_auditor.synthetic_sample import sample_pdf


def fixtures() -> dict[str, bytes]:
    result = {"structured.pdf": sample_pdf()}
    for kind in ["normal", "rotated", "unicode", "annotated", "low-text"]:
        with pymupdf.open() as doc:
            page = doc.new_page(width=612, height=792)
            if kind != "low-text":
                page.insert_text((45, 55), "Synthetic résumé — CHAPTER 1", fontsize=12)
                page.insert_text(
                    (72, 110), "Synthetic paragraph for deterministic parity.", fontsize=12
                )
            if kind == "rotated":
                page.set_rotation(90)
            if kind == "annotated":
                page.add_text_annot((90, 150), "Synthetic reviewer annotation")
            result[kind + ".pdf"] = doc.tobytes(no_new_id=True)
    return result


def normalized(value):
    if isinstance(value, dict):
        return {
            k: normalized(v)
            for k, v in value.items()
            if k not in {"job_id", "created_at", "finished_at", "generated_at", "input_file_path"}
        }
    if isinstance(value, (list, tuple)):
        return [normalized(v) for v in value]
    if isinstance(value, float):
        return round(value, 5)
    if isinstance(value, str):
        value = re.sub(r"(?m)^- Generated at: .+$", "- Generated at: <time>", value)
        value = re.sub(r"(?m)^(Audit date/time \(UTC\): ).+$", r"\1<time>", value)
        return re.sub(r"/audits/[a-f0-9]{32}", "/audits/<job>", value)
    return value


def pdf_content(payload: bytes):
    with pymupdf.open(stream=payload, filetype="pdf") as doc:
        pages = []
        for page in doc:
            annotations = []
            for annotation in page.annots() or []:
                annotations.append(
                    {
                        "type": annotation.type,
                        "rect": tuple(annotation.rect),
                        "vertices": annotation.vertices,
                        "colors": annotation.colors,
                        "content": annotation.info.get("content", ""),
                    }
                )
            # Point/Rect objects are serialized via coordinates, never binary IDs/dates.
            drawings = json.loads(json.dumps(page.get_drawings(), default=list))
            pages.append(
                {
                    "text": page.get_text(),
                    "drawings": drawings,
                    "annotations": annotations,
                    "rotation": page.rotation,
                    "rect": tuple(page.rect),
                }
            )
        return normalized(pages)


def references(request) -> dict:
    result = {}
    for path in ["/help", "/rules"]:
        response = request.get(path)
        assert response.status == 200, path
        tree = html.fromstring(response.text())
        # These sections are byte-identical shared Help explanations. The first
        # section intentionally describes local vs server processing separately.
        if path == "/help":
            nodes = tree.xpath('//section[@id and @id!="how-it-works"]')
        else:
            nodes = tree.xpath("//main") or tree.xpath("//body")
            for node in tree.xpath("//nav|//footer|//script|//style"):
                node.drop_tree()
        result[path] = [" ".join(n.text_content().split()) for n in nodes]
    return result


def snapshot(request, job: str) -> dict:
    deadline = time.monotonic() + 120
    while True:
        status = request.get(job + "/status").json()
        if status["state"] in {"complete", "failed"}:
            break
        if time.monotonic() > deadline:
            raise TimeoutError("Synthetic audit did not finish")
        time.sleep(0.2)
    assert status["state"] == "complete", status
    result = {}
    for suffix in EXPORTS:
        response = request.get(job + "/" + suffix)
        assert response.status == 200, (suffix, response.status)
        payload = response.body()
        if suffix == "pdf":
            value = hashlib.sha256(payload).hexdigest()
        elif "pdf" in suffix:
            value = pdf_content(payload)
        elif suffix.endswith("json"):
            value = normalized(response.json())
        else:
            value = normalized(payload.decode())
        result[suffix] = value
    page = html.fromstring(request.get(job).text())
    result["finding_cards"] = [
        normalized(" ".join(n.text_content().split())) for n in page.xpath("//article[@data-rule]")
    ]
    group_paths = sorted(
        {
            link[len(job) :].split("#", 1)[0]
            for link in page.xpath("//a/@href")
            if link.startswith(job + "/problems/")
        }
    )
    result["groups"] = {}
    for path in group_paths:
        response = request.get(job + path)
        assert response.status in {200, 404}, (path, response.status)
        tree = html.fromstring(response.text())
        # Keep all finding text, explanations and links, excluding shared nav/privacy.
        nodes = tree.xpath("//table|//article[@data-rule]") if response.status == 200 else []
        result["groups"][path] = {
            "status": response.status,
            "content": [normalized(" ".join(n.text_content().split())) for n in nodes],
        }
    return normalized(result)


def capture(url: str, directory: Path) -> None:
    assert url.rstrip("/") == PRODUCTION_URL, "Capture must use the authoritative production host"
    directory.mkdir(parents=True, exist_ok=False)
    with sync_playwright() as p:
        request = p.request.new_context(base_url=url, timeout=120000)
        version = request.get("/version").json()
        assert version["commit"] == BASELINE, (
            "Production changed; refresh parity baseline deliberately"
        )
        manifest = {"source_commit": BASELINE, "references": references(request), "fixtures": {}}
        for name, data in fixtures().items():
            (directory / name).write_bytes(data)
            response = request.post(
                "/audits",
                multipart={"file": {"name": name, "mimeType": "application/pdf", "buffer": data}},
                max_redirects=0,
            )
            assert response.status == 303
            manifest["fixtures"][name] = snapshot(request, response.headers["location"])
        (directory / "reference.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        after = request.get("/version").json()
        assert after["commit"] == version["commit"] == BASELINE, "Production changed during capture"
        provenance = {
            "capture_kind": "live-production-http",
            "capture_url": PRODUCTION_URL,
            "captured_at_utc": datetime.now(timezone.utc).isoformat(),
            "version_before": version,
            "version_after": after,
            "capture_tool_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "payload_sha256": {
                path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                for path in sorted(directory.iterdir())
            },
        }
        (directory / "provenance.json").write_text(
            json.dumps(provenance, indent=2), encoding="utf-8"
        )
        request.dispose()
    load_reference(directory)
    print("Captured six synthetic audits from verified production source")


def validate(
    executable: Path | None, directory: Path, output: Path, profile_root: Path | None = None
) -> None:
    reference = load_reference(directory)
    if executable and os.name == "nt":
        import psutil
        from validate_windows_install import require_no_auditor_processes

        require_no_auditor_processes(psutil.process_iter(["name"]))
    output.mkdir(parents=True, exist_ok=True)
    root = profile_root.resolve() if profile_root is not None else output.resolve() / "profile"
    root.mkdir(exist_ok=True)
    state = output.resolve() / "launch.json"
    assert not state.exists(), "Refusing to overwrite an existing session file"
    env = os.environ.copy()
    env["LOCALAPPDATA"] = str(root)
    env["XDG_DATA_HOME"] = str(root)
    if executable:
        env.pop("PYTHONPATH", None)
        env.pop("PYTHONHOME", None)
        env["PATH"] = os.pathsep.join(
            [
                env.get("SystemRoot", "C:\\Windows"),
                env.get("SystemRoot", "C:\\Windows") + "\\System32",
            ]
        )
        # Keep the native launcher, but use only the owned Chromium context below.
        # Opening the default browser would interfere with manual GUI sessions.
        command = [str(executable.resolve()), "--no-browser"]
    else:
        command = [
            sys.executable,
            "-m",
            "njit_auditor.offline_launcher",
            "--headless",
            "--no-browser",
        ]
    process = subprocess.Popen(command + ["--state-file", str(state)], env=env)
    try:
        deadline = time.monotonic() + 30
        while not state.exists():
            assert process.poll() is None, "Application exited before startup"
            if time.monotonic() > deadline:
                raise TimeoutError("No application startup state")
            time.sleep(0.1)
        while True:
            try:
                launch = json.loads(state.read_text(encoding="utf-8"))["url"]
                break
            except (json.JSONDecodeError, KeyError):
                if time.monotonic() > deadline:
                    raise TimeoutError("Incomplete startup state") from None
                time.sleep(0.05)
        origin = launch.split("/_session/")[0]
        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context(viewport={"width": 1440, "height": 1000}, base_url=origin)
            external = []

            def guard(route):
                if urlparse(route.request.url).hostname != "127.0.0.1":
                    external.append(route.request.url)
                    route.abort()
                else:
                    route.continue_()

            context.route("**/*", guard)
            page = context.new_page()
            page.goto(launch)
            assert references(context.request) == reference["references"], "Help/Rules differ"
            for name, expected in reference["fixtures"].items():
                page.goto(origin)
                page.locator("input[type=file]").set_input_files(str(directory / name))
                page.get_by_role("button", name="Start audit", exact=True).click()
                page.wait_for_url("**/audits/*")
                job = urlparse(page.url).path
                actual = snapshot(context.request, job)
                (output / (name + ".actual.json")).write_text(
                    json.dumps(actual, indent=2), encoding="utf-8"
                )
                assert actual == expected, f"Unexplained parity difference: {name}"
                page.reload()
                assert page.get_by_role("link", name="Help", exact=True).is_visible()
                page.screenshot(path=str(output / (name + ".png")), full_page=True)
            assert not external, f"Unexpected browser network requests: {external}"
            page.get_by_role("button", name="Quit", exact=True).click()
            browser.close()
        assert process.wait(timeout=20) == 0
        assert not state.exists(), "Launch credential was not cleaned"
        app_root = root / ("NJIT Thesis Auditor" if os.name == "nt" else "njit-thesis-auditor")
        assert not list((app_root / "audits").iterdir()), "Temporary audits remain after Quit"
        assert not list((app_root / "tmp").iterdir()), "Temporary files remain after Quit"
        (output / "result.json").write_text(
            json.dumps(
                {
                    "parity": "passed",
                    "fixtures": len(reference["fixtures"]),
                    "packaged": executable is not None,
                    "platform": sys.platform,
                    "source_commit": reference["source_commit"],
                    "external_browser_requests": external,
                    "startup": "passed",
                    "shutdown": "passed",
                    "temporary_cleanup": "passed",
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print("Six online/desktop audits, all exports, highlights, references and shutdown matched")
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=20)
        state.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-url")
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--executable", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.capture_url:
        capture(args.capture_url, args.reference)
    else:
        if args.output is None:
            parser.error("--output required for validation")
        validate(args.executable, args.reference, args.output)


if __name__ == "__main__":
    main()
