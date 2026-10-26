"""Reproduce a before/after browser review using only the committed synthetic PDF.

Run with --baseline PATH --output PATH. Optionally supply a local axe-core script
with --axe-script PATH; no scripts or documents are fetched from external sites.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import httpx
from playwright.sync_api import sync_playwright

# Counts rendered explanatory text nodes once, excluding controls, headings,
# findings, code, and closed details. Shared navigation/footer are outside main.
VISIBLE_EXPLANATION = r"""() => {
 const root = document.querySelector('main') || document.body;
 const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
 const parts = [];
 while (walker.nextNode()) {
   const node = walker.currentNode, p = node.parentElement;
   if (!p.closest('p,.section-note,.privacy-note,.alert-info,.review-order-list')) continue;
   if (p.closest('script,style,code,button,select,.finding-card,.example-card,nav,footer'))
     continue;
   const closed = p.closest('details:not([open])');
   if (closed && !p.closest('summary')) continue;
   const range = document.createRange(); range.selectNodeContents(node);
   if (range.getBoundingClientRect().width && node.textContent.trim()) parts.push(node.textContent);
 }
 return parts.join(' ').replace(/\s+/g,' ').trim();
}"""


@contextmanager
def server(repo: Path, output: Path, label: str) -> Any:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = os.environ.copy()
    env.update(
        PYTHONPATH=str(repo / "src"),
        PYTHONDONTWRITEBYTECODE="1",
        NJIT_AUDITOR_WEB_RUNTIME_DIR=str(output / (label + "-runtime")),
        NJIT_AUDITOR_WEB_ENVIRONMENT="isolated-synthetic-review",
    )
    command = [
        sys.executable,
        "-m",
        "uvicorn",
        "njit_auditor.web_app:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--no-access-log",
    ]
    with (output / (label + "-server.log")).open("w") as log:
        process = subprocess.Popen(command, cwd=repo, env=env, stdout=log, stderr=subprocess.STDOUT)
        base = f"http://127.0.0.1:{port}"
        try:
            for _ in range(60):
                assert process.poll() is None, "Owned review server exited"
                try:
                    if httpx.get(base + "/healthz", timeout=0.5).status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(0.1)
            else:
                raise RuntimeError("Owned review server failed startup")
            yield base
        finally:
            process.terminate()
            process.wait(timeout=10)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--axe-script", type=Path)
    args = parser.parse_args()
    current = Path(__file__).resolve().parents[1]
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    fixture = current / "tests/fixtures/web_demo/issues_pdf.pdf"
    report: dict[str, Any] = {"fixture": str(fixture), "measurements": [], "errors": []}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        report["browser"] = browser.version
        for label, repo in [("before", args.baseline.resolve()), ("after", current)]:
            with server(repo, output, label) as base:
                report[label + "_version"] = httpx.get(base + "/version").json()
                page = browser.new_page()
                page.on("pageerror", lambda exc: report["errors"].append(str(exc)))
                response = page.request.post(
                    base + "/audits",
                    multipart={
                        "file": {
                            "name": "synthetic.pdf",
                            "mimeType": "application/pdf",
                            "buffer": fixture.read_bytes(),
                        },
                    },
                )
                assert response.ok
                results_url = response.url
                page.goto(results_url)
                page.locator(".finding-card").first.wait_for(timeout=15000)
                # Independent comparison excludes the per-job bearer ID only.
                export_response = page.request.get(results_url + "/download/json")
                assert export_response.status == 200
                exported = export_response.json()
                exported.get("metadata", {}).pop("job_id", None)
                exported.get("metadata", {}).pop("generated_at", None)
                (output / (label + "-findings.json")).write_text(json.dumps(exported, indent=2))
                for width, height in [(320, 800), (390, 844), (768, 1024), (1440, 900)]:
                    page.set_viewport_size({"width": width, "height": height})
                    for route, url in [("home", base), ("results", results_url)]:
                        page.goto(url)
                        page.wait_for_load_state("networkidle")
                        text = page.evaluate(VISIBLE_EXPLANATION)
                        (output / f"{label}-{route}-{width}-explanation.txt").write_text(text)
                        overflow = page.evaluate(
                            "document.documentElement.scrollWidth > innerWidth"
                        )
                        cards = page.locator(".finding-card").all_inner_texts()
                        report["measurements"].append(
                            {
                                "label": label,
                                "route": route,
                                "width": width,
                                "explanatory_words": len(re.findall(r"\b[\w’'-]+\b", text)),
                                "horizontal_overflow": overflow,
                                "cards": cards,
                            }
                        )
                        page.screenshot(
                            path=str(output / f"{label}-{route}-{width}.png"), full_page=True
                        )
                        if route == "results":
                            page.locator("#section-findings").scroll_into_view_if_needed()
                            page.screenshot(path=str(output / f"{label}-findings-{width}.png"))
                        if args.axe_script:
                            page.add_script_tag(path=str(args.axe_script))
                            scan = page.evaluate(
                                "async () => await axe.run(document, "
                                "{runOnly: {type:'tag', values:"
                                "['wcag2a','wcag2aa','wcag21a','wcag21aa']}})"
                            )
                            (output / f"{label}-{route}-{width}-axe.json").write_text(
                                json.dumps(scan, indent=2)
                            )
                    if label == "after":
                        page.goto(base + "/about")
                        assert page.locator("#privacy").is_visible()
                        page.screenshot(
                            path=str(output / f"after-about-{width}.png"), full_page=True
                        )
                        if args.axe_script:
                            page.add_script_tag(path=str(args.axe_script))
                            scan = page.evaluate("async () => await axe.run(document)")
                            (output / f"after-about-{width}-axe.json").write_text(
                                json.dumps(scan, indent=2)
                            )
                page.close()
        browser.close()
    report["findings_identical"] = (output / "before-findings.json").read_text() == (
        output / "after-findings.json"
    ).read_text()
    (output / "review.json").write_text(json.dumps(report, indent=2))
    print(
        json.dumps(
            {
                "findings_identical": report["findings_identical"],
                "javascript_errors": report["errors"],
                "output": str(output),
            }
        )
    )


if __name__ == "__main__":
    main()
