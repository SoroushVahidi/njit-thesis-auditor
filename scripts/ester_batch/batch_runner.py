"""Unattended, resumable batch runner: generate one Ester evaluation package
(Rxxx_Ester_Auditor_Feedback.{xlsx,pdf}) per currently-implemented, PDF-applicable
rule, across the same seven dissertations, skipping the already-complete R011.

Designed to run for a long time inside tmux, updating a durable status file
atomically after every rule so progress can be inspected without parsing the
terminal log, and so the batch can be safely interrupted and resumed.
"""

from __future__ import annotations

import datetime
import json
import subprocess
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_rule_package import build_rule  # noqa: E402
from discover_rules import discover  # noqa: E402
from lib import OUTPUT_DIR, REPO_ROOT  # noqa: E402

STATUS_PATH = OUTPUT_DIR / "all_rules_batch_status.json"
MANIFEST_PATH = OUTPUT_DIR / "all_rules_batch_manifest.json"
COMPLETE_MARKER_PATH = OUTPUT_DIR / "ALL_RULES_BATCH_COMPLETE.json"
LOG_DIR = REPO_ROOT / "logs"
ERROR_LOG_DIR = LOG_DIR / "ester_all_rules_batch_errors"


def now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def base_commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


def atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(path)


def package_looks_valid(ester_id: str) -> bool:
    xlsx_path = OUTPUT_DIR / f"{ester_id}_Ester_Auditor_Feedback.xlsx"
    pdf_path = OUTPUT_DIR / f"{ester_id}_Ester_Auditor_Feedback.pdf"
    if not xlsx_path.exists() or not pdf_path.exists():
        return False
    try:
        import fitz
        import openpyxl

        wb = openpyxl.load_workbook(xlsx_path, read_only=True)
        if ester_id not in wb.sheetnames:
            return False
        with fitz.open(str(pdf_path)) as doc:
            if doc.page_count < 1:
                return False
    except Exception:
        return False
    return True


def main() -> None:
    started_at = now_iso()
    commit = base_commit()

    print(f"[{now_iso()}] Starting all-rules Ester batch. base_commit={commit}", flush=True)

    manifest = discover()
    manifest["generated_at"] = now_iso()
    atomic_write_json(MANIFEST_PATH, manifest)

    applicable = [
        r for r in manifest["rules"] if r["applicable_to_batch"] and not r["already_complete"]
    ]
    already_complete_ids = [r["ester_id"] for r in manifest["rules"] if r["already_complete"]]
    skipped = [r for r in manifest["rules"] if not r["applicable_to_batch"]]

    print(
        f"[{now_iso()}] Discovered {len(manifest['rules'])} rules: "
        f"{len(applicable)} to process, {len(already_complete_ids)} already complete, "
        f"{len(skipped)} skipped (not applicable).",
        flush=True,
    )

    status = {
        "started_at": started_at,
        "base_commit": commit,
        "rules_discovered": [r["ester_id"] for r in manifest["rules"]],
        "total_to_process": len(applicable),
        "current_rule": None,
        "completed_rules": list(already_complete_ids),
        "failed_rules": {},
        "skipped_rules": {r["ester_id"]: r["skip_reason"] for r in skipped},
        "last_update": now_iso(),
        "finished": False,
    }
    atomic_write_json(STATUS_PATH, status)

    for entry in applicable:
        internal_id = entry["internal_id"]
        ester_id = entry["ester_id"]
        status["current_rule"] = ester_id
        status["last_update"] = now_iso()
        atomic_write_json(STATUS_PATH, status)

        if package_looks_valid(ester_id):
            print(f"[{now_iso()}] {ester_id}: existing package looks valid, skipping rebuild.", flush=True)
            status["completed_rules"].append(ester_id)
            status["last_update"] = now_iso()
            atomic_write_json(STATUS_PATH, status)
            continue

        print(f"[{now_iso()}] {ester_id} ({internal_id}): building package...", flush=True)
        try:
            result = build_rule(internal_id, ester_id)
            if result["validation_problems"]:
                raise RuntimeError(
                    f"validation failed: {result['validation_problems']}"
                )
            print(
                f"[{now_iso()}] {ester_id}: OK — "
                f"{result['documents_with_findings']} doc(s) with findings, "
                f"{result['documents_with_no_finding']} with none, "
                f"{result['pdf_page_count']} PDF pages.",
                flush=True,
            )
            status["completed_rules"].append(ester_id)
        except Exception as exc:  # noqa: BLE001
            ERROR_LOG_DIR.mkdir(parents=True, exist_ok=True)
            error_log_path = ERROR_LOG_DIR / f"{ester_id}.log"
            error_log_path.write_text(
                f"{now_iso()}\nRule: {ester_id} ({internal_id})\n"
                f"Exception: {exc}\n\n{traceback.format_exc()}",
                encoding="utf-8",
            )
            print(f"[{now_iso()}] {ester_id}: FAILED — {exc} (see {error_log_path})", flush=True)
            status["failed_rules"][ester_id] = {
                "internal_id": internal_id,
                "error": str(exc),
                "traceback_log": str(error_log_path),
            }

        status["last_update"] = now_iso()
        atomic_write_json(STATUS_PATH, status)

    status["current_rule"] = None
    status["finished"] = True
    status["last_update"] = now_iso()
    atomic_write_json(STATUS_PATH, status)

    generated_artifacts = sorted(
        str(p.relative_to(REPO_ROOT)) for p in OUTPUT_DIR.glob("R*_Ester_Auditor_Feedback.*")
    )
    completion = {
        "finished_at": now_iso(),
        "base_commit": commit,
        "rules_discovered": len(manifest["rules"]),
        "completed_count": len(status["completed_rules"]),
        "skipped_count": len(status["skipped_rules"]),
        "failed_count": len(status["failed_rules"]),
        "manifest_path": str(MANIFEST_PATH.relative_to(REPO_ROOT)),
        "status_path": str(STATUS_PATH.relative_to(REPO_ROOT)),
        "generated_artifacts": generated_artifacts,
    }
    atomic_write_json(COMPLETE_MARKER_PATH, completion)
    print(f"[{now_iso()}] Batch finished. {completion}", flush=True)


if __name__ == "__main__":
    main()
