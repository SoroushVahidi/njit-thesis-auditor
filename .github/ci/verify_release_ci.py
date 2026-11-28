"""Verify an exact GitHub Actions checkout and write a local deployment receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

VERSIONS = ("3.10", "3.11", "3.12")
REQUIRED_JOBS = {
    *(f"test ({version})" for version in VERSIONS),
    *(f"Minimum multipart dependencies ({version})" for version in VERSIONS),
    "Synthetic browser checks (3.12)",
}
SHA = re.compile(r"[a-f0-9]{40}")


def checkout_shas(log: bytes) -> list[str]:
    lines = log.decode("utf-8").splitlines()
    found = []
    for command, output in zip(lines, lines[1:]):
        if not re.fullmatch(r"\S+ \[command\]\S+/git log -1 --format=%H", command):
            continue
        match = re.fullmatch(r"\S+ ([a-f0-9]{40})", output)
        if match:
            found.append(match[1])
    return found


def verify_run(run, jobs, read_log, *, checkout, pr=None, head=None, base=None, parents=None):
    """Bind successful job logs to the current attempt, trigger and checkout."""
    if (
        run["path"] != ".github/workflows/ci.yml"
        or run["status"] != "completed"
        or run["conclusion"] != "success"
    ):
        raise ValueError("Expected a successful terminal CI run")
    require_merge_ref = False
    if pr is None:
        if run["event"] != "push" or run["head_sha"] != checkout:
            raise ValueError("Push run does not match the expected checkout")
    else:
        associations = run["pull_requests"]
        if run["event"] != "pull_request" or run["head_sha"] != head:
            raise ValueError("Pull request run does not match the expected head and base")
        if associations:
            if not any(
                item["number"] == pr and item["base"]["sha"] == base and item["head"]["sha"] == head
                for item in associations
            ):
                raise ValueError("Pull request run does not match the expected head and base")
        else:
            # GitHub can drop the run's PR association after the PR is merged.
            if parents != [base, head]:
                raise ValueError("Proposed merge does not have the expected parents")
            require_merge_ref = True

    if (
        len(jobs) != len(REQUIRED_JOBS)
        or {job["name"] for job in jobs} != REQUIRED_JOBS
        or any(
            job["run_attempt"] != run["run_attempt"]
            or job["status"] != "completed"
            or job["conclusion"] != "success"
            or not any(
                step["name"] == "Checkout without confidential fixtures"
                and step["conclusion"] == "success"
                for step in job["steps"]
            )
            for job in jobs
        )
    ):
        raise ValueError("Required jobs are missing or unsuccessful on this attempt")

    def verify_job(job):
        log = read_log(job["id"])
        shas = checkout_shas(log)
        if shas != [checkout]:
            raise ValueError(f"Wrong or ambiguous checkout in {job['name']}")
        if require_merge_ref:
            ref = f"+{checkout}:refs/remotes/pull/{pr}/merge"
            if not any(
                re.fullmatch(r"\S+ \[command\]\S+/git .* fetch .* " + re.escape(ref), line)
                for line in log.decode("utf-8").splitlines()
            ):
                raise ValueError(f"Missing PR merge ref in {job['name']}")
        return {
            **{key: job[key] for key in ("name", "id", "status", "conclusion", "html_url")},
            "checkout_shas": shas,
            "log_sha256": hashlib.sha256(log).hexdigest(),
        }

    with ThreadPoolExecutor(max_workers=4) as pool:
        receipts = list(pool.map(verify_job, jobs))
    return {
        **{key: run[key] for key in (
            "id", "event", "status", "conclusion", "head_sha", "html_url", "run_attempt"
        )},
        "expected_checkout": checkout,
        "pull_request": None if pr is None else {"number": pr, "head": head, "base": base},
        "gate_passed": True,
        "jobs": receipts,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=int)
    parser.add_argument("checkout")
    parser.add_argument("--repo", default="SoroushVahidi/njit-thesis-auditor")
    parser.add_argument("--pr", type=int)
    parser.add_argument("--head")
    parser.add_argument("--base")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not (
        SHA.fullmatch(args.checkout)
        and args.run > 0
        and re.fullmatch(r"[\w.-]+/[\w.-]+", args.repo, re.ASCII)
        and (
            (args.pr is None and args.head is None and args.base is None)
            or (args.pr and args.pr > 0 and SHA.fullmatch(args.head or "")
                and SHA.fullmatch(args.base or ""))
        )
    ):
        parser.error("Supply a full checkout SHA and, for pull requests, PR number and full SHAs")

    def api(endpoint):
        return subprocess.run(
            ["gh", "api", "--method", "GET", f"repos/{args.repo}/{endpoint}"],
            capture_output=True, check=True, timeout=45,
        ).stdout

    path = f"actions/runs/{args.run}"
    try:
        run = json.loads(api(path))
        attempt = run["run_attempt"]
        jobs = json.loads(api(f"{path}/attempts/{attempt}/jobs?per_page=20"))["jobs"]
        parents = None
        if args.pr and not run["pull_requests"]:
            commit = json.loads(api(f"git/commits/{args.checkout}"))
            if commit["sha"] != args.checkout:
                raise ValueError("GitHub returned a different merge commit")
            parents = [parent["sha"] for parent in commit["parents"]]
        receipt = verify_run(
            run, jobs, lambda job: api(f"actions/jobs/{job}/logs"),
            checkout=args.checkout, pr=args.pr, head=args.head, base=args.base, parents=parents,
        )
        if json.loads(api(path))["run_attempt"] != attempt:
            raise ValueError("The run was rerun while checking its evidence")
        fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(receipt, stream, indent=2)
            stream.write("\n")
    except (OSError, KeyError, TypeError, ValueError, subprocess.SubprocessError) as exc:
        parser.exit(1, f"CI receipt refused: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
