"""Private desktop worker protocol. No listener, credentials, or remote requests."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path

from njit_auditor.desktop_network import restrict_network


def execute(request: Path) -> int:
    ready = request.with_name(".desktop-ready")
    end = time.monotonic() + 5
    while not ready.is_file():
        if time.monotonic() >= end:
            return 1
        time.sleep(0.01)
    # Containment has been assigned by the supervisor before any audit imports.
    restrict_network()
    payload = json.loads(request.read_text(encoding="utf-8"))
    runtime = Path(payload["runtime_dir"])
    os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"] = str(runtime)
    os.environ["FASTAPI_OTEL_AUTO_CONFIGURE"] = "false"
    tempfile.tempdir = str(
        request.parent if payload.get("operation") == "pdf-export" else runtime.parent / "tmp"
    )
    from njit_auditor import web_app
    from njit_auditor.desktop_protocol import decode, encode

    web_app.RUNTIME_DIR = runtime
    job = web_app.JobState(**decode(payload["job"]))
    web_app._set_job(job)
    if payload.get("operation") == "pdf-export":
        # This dispatch is reached through the same frozen entrypoint, ready gate
        # and network restriction as audits. No multiprocessing or PDF threads.
        from njit_auditor.desktop_exports import render_export

        render_export(request.parent, job, payload)
        return 0
    web_app._run_audit_task(job.job_id)
    result = web_app._get_job(job.job_id)
    if result is None:
        return 1
    request.with_name(".desktop-result.json").write_text(
        json.dumps(encode(vars(result))), encoding="utf-8"
    )
    return 0


def main(arguments: list[str] | None = None) -> int:
    args = sys.argv[1:] if arguments is None else arguments
    if len(args) != 1:
        return 1
    try:
        return execute(Path(args[0]))
    except BaseException:
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
