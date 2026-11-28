#!/usr/bin/env python3
"""Validate local CI manifests and prepare an unsigned, unpublished check proposal.

This intentionally has no network call or credential handling. A repository
owner must provision a restricted GitHub App and an independent trusted signer
before a check can become an authoritative branch gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSIONS = {"3.10", "3.11", "3.12"}
STEPS = ["venv", "dependencies", "project", "ruff", "mypy", "pytest"]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(paths: list[Path], sha: str, repo: Path) -> dict[str, object]:
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("expected SHA must be full length")
    if len(paths) != len(VERSIONS):
        raise ValueError("exactly one manifest per required Python version is needed")
    actual_tree = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", f"{sha}^{{tree}}"], text=True
    ).strip()
    manifests = [json.loads(path.read_text()) for path in paths]
    versions: set[str] = set()
    trees: set[str] = set()
    verified: list[dict[str, object]] = []
    for path, item in zip(paths, manifests, strict=True):
        version = ".".join(item["python"].split(".")[:2])
        if version in versions or version not in VERSIONS:
            raise ValueError("missing, duplicate, or unsupported Python version")
        versions.add(version)
        if item.get("commit") != sha or item.get("status") != "COMPLETED_SUCCESS":
            raise ValueError(f"stale or unsuccessful manifest: {path}")
        if (
            item.get("runner_sha256") != digest(ROOT / "scripts/codex_managed_ci.py")
            or item.get("exclusions_sha256") != digest(ROOT / "ci/private_test_exclusions.json")
            or item.get("lock_sha256")
            != digest(ROOT / "ci" / f"requirements-py{version.replace('.', '')}-linux.txt")
        ):
            raise ValueError(f"runner or dependency evidence changed: {path}")
        tree = item.get("tree")
        if tree != actual_tree:
            raise ValueError("invalid tree identity")
        trees.add(tree)
        steps = item.get("steps", [])
        if [step.get("name") for step in steps] != STEPS or any(
            step.get("exit_code") != 0 for step in steps
        ):
            raise ValueError(f"incomplete or failed checks: {path}")
        for step in steps:
            log = path.parent / step["log"]
            if not log.is_file():
                raise ValueError(f"missing log: {log}")
            if digest(log) != step.get("sha256"):
                raise ValueError(f"log checksum changed: {log}")
        pytest = item.get("pytest", {})
        if (
            pytest.get("exit_code") != 0
            or pytest.get("deselected") != 46
            or pytest.get("failed") != 0
            or len(pytest.get("pdf_exception_regressions_selected", [])) != 3
            or set(pytest.get("pdf_exception_regressions_passed", []))
            != set(pytest.get("pdf_exception_regressions_selected", []))
        ):
            raise ValueError(f"privacy selection or PDF regression evidence incomplete: {path}")
        verified.append(
            {
                "python": item["python"],
                "passed": pytest["passed"],
                "skipped": pytest["skipped"],
                "deselected": pytest["deselected"],
                "failed": pytest["failed"],
                "manifest": str(path.resolve()),
            }
        )
    if versions != VERSIONS or len(trees) != 1:
        raise ValueError("version coverage or tree identity differs")
    return {
        "sha": sha,
        "tree": trees.pop(),
        "verified": sorted(verified, key=lambda x: x["python"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--manifest", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        evidence = validate(args.manifest, args.expected_sha, args.repo.resolve())
    except (
        KeyError,
        TypeError,
        ValueError,
        OSError,
        json.JSONDecodeError,
        subprocess.CalledProcessError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1
    proposal = {
        "publication": "WITHHELD",
        "reason": "GitHub App identity, source restriction, and owner approval are not configured",
        "repository": "SoroushVahidi/njit-thesis-auditor",
        "check_name": "Codex managed CI / verified local",
        "requested_conclusion": "success",
        "evidence": evidence,
    }
    args.output.write_text(json.dumps(proposal, indent=2, sort_keys=True) + "\n")
    args.output.chmod(0o600)
    print(f"WITHHELD: validated evidence for {evidence['sha']}; no GitHub API call made")
    return 0


if __name__ == "__main__":
    sys.exit(main())
