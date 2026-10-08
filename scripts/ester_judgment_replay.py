"""Replay private reviewer judgments against the real student web pipeline.

The JSON manifest and dissertations are deliberately supplied from outside the
tracked repository. Run with ``PYTHONPATH=src python scripts/ester_judgment_replay.py
--manifest /private/manifest.json --output-dir /private/replay``. Cached reports
can be checked with ``--cached`` after a run. The manifest schema is exercised
in ``tests/test_ester_judgment_replay_framework.py``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _page(value: Any) -> int | None:
    return int(value) if value not in (None, "") else None


def _boxes(raw: Any) -> list[tuple[float, float, float, float]]:
    if isinstance(raw, list) and len(raw) == 4:
        return [tuple(float(part) for part in raw)]  # type: ignore[return-value]
    if not isinstance(raw, str):
        return []
    result = []
    for chunk in raw.split("|"):
        try:
            box = tuple(float(part.strip()) for part in chunk.split(","))
        except ValueError:
            continue
        if len(box) == 4:
            result.append(box)
    return result


def _overlaps(a: tuple[float, ...], b: tuple[float, ...]) -> bool:
    return min(a[2], b[2]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[1], b[1])


def _target_boxes(finding: dict[str, Any]) -> list[tuple[float, float, float, float]]:
    details = finding.get("details", {})
    return (
        _boxes(details.get("highlight_bboxes"))
        or _boxes(details.get("bbox"))
        or _boxes(finding.get("bbox"))
    )


def matches(
    finding: dict[str, Any], selector: dict[str, Any], *, allow_missing_geometry: bool = False
) -> bool:
    """Match rule, issue, page and the target's own evidence; never use rule alone."""
    if finding.get("rule_id") != selector["rule_id"]:
        return False
    if _page(finding.get("page")) != _page(selector.get("page")):
        return False
    details = finding.get("details", {})
    issue = finding.get("issue_type") or details.get("issue_type")
    if issue not in selector["issue_types"] and "*" not in selector["issue_types"]:
        return False
    for key, value in selector.get("detail_equals", {}).items():
        if str(details.get(key, "")) != str(value):
            return False
    for key, value in selector.get("detail_contains", {}).items():
        if str(value).lower() not in str(details.get(key, "")).lower():
            return False
    if "target_bbox" in selector:
        anchor = tuple(float(part) for part in selector["target_bbox"])
        boxes = _target_boxes(finding)
        if not boxes and allow_missing_geometry:
            return True
        if not any(_overlaps(anchor, box) for box in boxes):
            return False
    return True


def _audit_document(path: Path, runtime_root: Path) -> dict[str, Any]:
    os.environ["NJIT_AUDITOR_WEB_RUNTIME_DIR"] = tempfile.mkdtemp(
        prefix="ester_replay_", dir=runtime_root
    )
    from fastapi.testclient import TestClient

    from njit_auditor import web_app

    with TestClient(web_app.app) as client:
        response = client.post(
            "/audits",
            files={"file": ("thesis.pdf", path.read_bytes(), "application/pdf")},
            follow_redirects=False,
        )
        if response.status_code != 303:
            raise RuntimeError(f"upload failed: HTTP {response.status_code}")
        job_id = response.headers["location"].rsplit("/", 1)[-1]
        job = web_app._get_job(job_id)
        raw = client.get(f"/audits/{job_id}/download/json").json()
        return {
            "state": job.state,
            "failed_check_count": getattr(job, "failed_check_count", None),
            "findings": job.findings,
            "raw": raw,
        }


def verify_case(case: dict[str, Any], report: dict[str, Any]) -> list[str]:
    selector = case["target"]
    raw = [
        f
        for f in report["raw"]["findings"]
        if matches(f, selector, allow_missing_geometry=case["judgment"] != "FP")
    ]
    card_selector = {
        k: v for k, v in selector.items() if k not in ("detail_equals", "detail_contains")
    }
    cards = [
        f
        for f in report["findings"]
        if matches(f, card_selector, allow_missing_geometry=case["judgment"] != "FP")
    ]
    errors = []
    if case["judgment"] == "FP":
        if raw:
            errors.append("rejected target emitted")
    elif case["judgment"] in ("TP", "REVIEWER_VIOLATION"):
        if not raw:
            errors.append("target absent from raw findings")
        if not cards:
            errors.append("target absent from student cards")
        if case.get("highlight_required") and not any(f.get("has_highlight") for f in cards):
            errors.append("student card has no highlight")
        for anchor in case.get("required_highlight_targets", []):
            if not any(
                _overlaps(tuple(float(v) for v in anchor), box)
                for finding in raw
                for box in _boxes(finding.get("details", {}).get("highlight_bboxes"))
            ):
                errors.append("required highlighted subtarget absent")
    else:
        errors.append("unknown judgment")
    return errors


def _same_finding(before: dict[str, Any], after: dict[str, Any]) -> bool:
    if any(before.get(key) != after.get(key) for key in ("rule_id", "page", "issue_type")):
        return False
    old_boxes, new_boxes = _target_boxes(before), _target_boxes(after)
    return (
        not old_boxes
        or not new_boxes
        or any(_overlaps(old, new) for old in old_boxes for new in new_boxes)
    )


def find_unexpected_removals(
    manifest: dict[str, Any],
    baseline: dict[str, dict[str, Any]],
    current: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Catch disappearing corpus findings, including ones Ester never adjudicated."""
    unexpected = []
    for name in baseline:
        for finding in baseline[name]["findings"]:
            if any(_same_finding(finding, now) for now in current[name]["findings"]):
                continue
            if any(
                allowed["document"] == name and matches(finding, allowed["target"])
                for allowed in manifest.get("allowed_removed", [])
            ):
                continue
            unexpected.append(
                {
                    "document": name,
                    "page": finding.get("page"),
                    "rule_id": finding.get("rule_id"),
                    "issue_type": finding.get("issue_type"),
                    "bbox": finding.get("bbox"),
                }
            )
    return unexpected


def find_disabled_or_retired_emissions(
    cases: list[dict[str, Any]], reports: dict[str, dict[str, Any]]
) -> list[str]:
    """Require disabled reporting paths and retired issue types to stay silent."""
    targets = {
        (case["target"]["rule_id"], issue)
        for case in cases
        if case["judgment"] == "FP" and case["disposition"] in ("disabled", "retired")
        for issue in case["target"]["issue_types"]
    }
    emitted = set()
    for report in reports.values():
        for finding in report["raw"]["findings"]:
            key = (finding["rule_id"], finding.get("details", {}).get("issue_type", ""))
            if key in targets:
                emitted.add(key)
    return [
        f"{rule}|{issue} emitted despite retired/disabled status" for rule, issue in sorted(emitted)
    ]


def verify_manifest(
    manifest: dict[str, Any],
    reports: dict[str, dict[str, Any]],
    baseline: dict[str, dict[str, Any]] | None = None,
    liveness: dict[str, int] | None = None,
) -> dict[str, Any]:
    cases = manifest["cases"]
    ids = [case["id"] for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("case IDs must be unique")
    if Counter(case["judgment"] for case in cases) != Counter(
        {"FP": 111, "TP": 20, "REVIEWER_VIOLATION": 5}
    ):
        raise ValueError("manifest must preserve all 131 judgments plus five additional violations")
    results = []
    for case in cases:
        report = reports[case["document"]]
        errors = verify_case(case, report)
        results.append({"id": case["id"], "judgment": case["judgment"], "errors": errors})
    liveness_errors = []
    resolved_rules = {
        case["target"]["rule_id"]
        for case in cases
        if case["judgment"] == "FP" and case["disposition"] == "resolved"
    }
    if liveness is None:
        liveness_errors.append("detector liveness evidence not supplied")
    else:
        for rule in sorted(resolved_rules):
            if not any(key.startswith(rule + "|") and count > 0 for key, count in liveness.items()):
                liveness_errors.append(f"{rule} has no positive detector evidence")
    unexpected = find_unexpected_removals(manifest, baseline, reports) if baseline else []
    return {
        "cases": results,
        "passed": sum(not result["errors"] for result in results),
        "failed": sum(bool(result["errors"]) for result in results),
        "unexpected_removed_findings": unexpected,
        "liveness_errors": liveness_errors,
        "disabled_detector_errors": find_disabled_or_retired_emissions(cases, reports),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--cached", action="store_true")
    parser.add_argument("--baseline-dir", type=Path)
    parser.add_argument("--liveness", type=Path)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    if manifest.get("schema") != 1:
        raise ValueError("unsupported manifest schema")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.output_dir.chmod(0o700)
    reports = {}
    for name, source in manifest["documents"].items():
        path = Path(source["path"])
        if not args.cached and _sha256(path) != source["sha256"]:
            raise ValueError(f"source hash mismatch: {name}")
        output = args.output_dir / f"{name}.json"
        report = (
            json.loads(output.read_text())
            if args.cached
            else _audit_document(path, args.output_dir)
        )
        if report["state"] != "complete" or report["failed_check_count"] != 0:
            raise RuntimeError(f"audit incomplete: {name}")
        if not args.cached:
            output.write_text(json.dumps(report, indent=1, default=str))
        reports[name] = report
    baseline = None
    if args.baseline_dir:
        baseline = {
            name: json.loads((args.baseline_dir / f"{name}.json").read_text())
            for name in manifest["documents"]
        }
    liveness = json.loads(args.liveness.read_text()) if args.liveness else None
    result = verify_manifest(manifest, reports, baseline, liveness)
    result["code_sha"] = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    (args.output_dir / "judgment_results.json").write_text(json.dumps(result, indent=2))
    print(f"{result['passed']}/{len(result['cases'])} case checks pass at {result['code_sha']}")
    for case in result["cases"]:
        if case["errors"]:
            print(f"{case['id']}: {', '.join(case['errors'])}")
    for finding in result["unexpected_removed_findings"]:
        print(f"unexpected removal: {finding}")
    for error in result["liveness_errors"]:
        print(f"liveness: {error}")
    for error in result["disabled_detector_errors"]:
        print(f"disabled detector: {error}")
    return int(
        bool(
            result["failed"]
            or result["unexpected_removed_findings"]
            or result["liveness_errors"]
            or result["disabled_detector_errors"]
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
