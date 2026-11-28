#!/usr/bin/env python3
"""Run privacy-safe CI against one immutable Git commit, without GitHub credentials.

The test subprocess sees an archive of the requested commit. Confidential raw
documents are omitted before extraction. Results are evidence for that commit
and interpreter on this host; this program does not publish a GitHub check.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path

SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parent.parent
PRIVATE_PREFIXES = ("data/raw/ester", "data/evaluation/private")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def execute(command: list[str], log: Path, *, cwd: Path, env: dict[str, str]) -> int:
    with log.open("w") as stream:
        stream.write("command: " + json.dumps(command) + "\n")
        stream.flush()
        result = subprocess.run(command, cwd=cwd, env=env, stdout=stream, stderr=subprocess.STDOUT)
        stream.write(f"\nexit_code: {result.returncode}\n")
    return result.returncode


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def snapshot(repo: Path, commit: str, dest: Path) -> None:
    archive = dest.parent / "source.tar"
    with archive.open("wb") as stream:
        subprocess.run(
            [
                "git",
                "-C",
                str(repo),
                "archive",
                "--format=tar",
                commit,
                "--",
                ".",
                ":!data/raw/ester",
                ":!data/evaluation/private",
            ],
            stdout=stream,
            check=True,
        )
    dest.mkdir()
    with tarfile.open(archive) as bundle:
        for item in bundle:
            name = item.name.removeprefix("./").rstrip("/")
            if not name:
                continue
            if any(name == prefix or name.startswith(prefix + "/") for prefix in PRIVATE_PREFIXES):
                raise RuntimeError("private path entered source archive")
            if Path(name).is_absolute() or ".." in Path(name).parts:
                raise RuntimeError("unsafe archive path")
            if not (item.isdir() or item.isfile()):
                raise RuntimeError("archive contains a link or unsupported entry")
            target = dest / name
            if item.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                source_file = bundle.extractfile(item)
                if source_file is None:
                    raise RuntimeError("missing archived file content")
                with source_file, target.open("wb") as output_file:
                    shutil.copyfileobj(source_file, output_file)
                target.chmod(item.mode & 0o777)
    archive.unlink()


def write_manifest(path: Path, data: dict[str, object]) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    os.chmod(temporary, 0o600)
    temporary.replace(path)


def install_private_read_guard(repo: Path) -> None:
    """Reject Python and PyMuPDF opens of known raw-document locations."""
    root = repo.parent.parent
    parents = (repo, root, root / "main", *(root / "worktrees").glob("*"))
    private_roots = tuple(
        (parent / suffix).resolve() for parent in parents for suffix in PRIVATE_PREFIXES
    )

    def blocked(value: object) -> bool:
        if isinstance(value, bytes):
            if len(value) > 4096 or b"\x00" in value:
                return False
            value = os.fsdecode(value)
        if not isinstance(value, (str, os.PathLike)):
            return False
        path = Path(value).resolve()
        return any(path == private or private in path.parents for private in private_roots)

    def audit(event: str, arguments: tuple[object, ...]) -> None:
        if event == "open" and arguments and blocked(arguments[0]):
            raise RuntimeError("private document read blocked")

    sys.addaudithook(audit)
    import fitz

    original_open = fitz.open

    def safe_fitz_open(*args: object, **kwargs: object) -> object:
        if (args and blocked(args[0])) or blocked(kwargs.get("filename")):
            raise RuntimeError("private document read blocked")
        return original_open(*args, **kwargs)

    fitz.open = safe_fitz_open


def pytest_child(repo: Path, snapshot_dir: Path, exclusions: Path, result_path: Path) -> int:
    install_private_read_guard(repo)
    import pytest

    specification = json.loads(exclusions.read_text())
    selectors = set(specification["selectors"])
    expected_count = specification["expected_count"]

    class Selection:
        def __init__(self) -> None:
            self.selected = 0
            self.deselected = 0
            self.seen: set[str] = set()
            self.regressions: list[str] = []
            self.regressions_passed: list[str] = []
            self.passed = 0
            self.skipped = 0
            self.failed = 0

        def pytest_collection_modifyitems(self, items: list[pytest.Item]) -> None:
            self.seen = {item.nodeid for item in items}
            present = {item.nodeid.split("[", 1)[0] for item in items}
            missing = selectors - present
            if missing:
                raise pytest.UsageError(
                    f"privacy exclusion inventory stale: {len(missing)} missing"
                )
            selected = [item for item in items if item.nodeid.split("[", 1)[0] not in selectors]
            removed = [item for item in items if item.nodeid.split("[", 1)[0] in selectors]
            self.selected, self.deselected = len(selected), len(removed)
            if self.deselected != expected_count:
                raise pytest.UsageError(
                    f"privacy exclusion count changed: {self.deselected} != {expected_count}"
                )
            self.regressions = sorted(
                item.nodeid
                for item in selected
                if "test_pdf_generation_failure_keeps_exception_details_out_of_logs" in item.nodeid
            )
            items[:] = selected
            if removed:
                items[0].config.hook.pytest_deselected(items=removed)

        def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
            if report.when == "call" and report.passed:
                self.passed += 1
                if report.nodeid in self.regressions:
                    self.regressions_passed.append(report.nodeid)
            if report.skipped:
                self.skipped += 1
            if report.failed:
                self.failed += 1

        def pytest_collectreport(self, report: pytest.CollectReport) -> None:
            if report.skipped:
                self.skipped += 1

    plugin = Selection()
    code = int(pytest.main(["-q", "--tb=short", "--disable-warnings"], plugins=[plugin]))
    write_manifest(
        result_path,
        {
            "exit_code": code,
            "collected": len(plugin.seen),
            "selected": plugin.selected,
            "deselected": plugin.deselected,
            "passed": plugin.passed,
            "skipped": plugin.skipped,
            "failed": plugin.failed,
            "expected_exclusions": expected_count,
            "pdf_exception_regressions_selected": plugin.regressions,
            "pdf_exception_regressions_passed": sorted(plugin.regressions_passed),
        },
    )
    return code


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--sha", required=True, help="full 40-character commit SHA")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--python", required=True, type=Path)
    parser.add_argument("--internal-pytest", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--snapshot", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--exclusions", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--result", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.internal_pytest:
        assert args.snapshot and args.exclusions and args.result
        return pytest_child(args.repo.resolve(), args.snapshot, args.exclusions, args.result)

    repo = args.repo.resolve()
    commit = args.sha.lower()
    if (
        not re.fullmatch(r"[0-9a-f]{40}", commit)
        or git(repo, "rev-parse", f"{commit}^{{commit}}") != commit
    ):
        parser.error("--sha must identify an existing exact commit")
    python = args.python.resolve()
    version = subprocess.check_output(
        [str(python), "-c", "import sys; print('.'.join(map(str, sys.version_info[:3])))"],
        text=True,
    ).strip()
    minor = ".".join(version.split(".")[:2])
    if (
        minor not in ("3.10", "3.11", "3.12")
        or platform.system() != "Linux"
        or platform.machine() != "x86_64"
    ):
        parser.error("only Python 3.10-3.12 on x86_64 Linux has a reviewed dependency lock")
    lock = ROOT / "ci" / f"requirements-py{minor.replace('.', '')}-linux.txt"
    exclusions = ROOT / "ci/private_test_exclusions.json"
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)
    os.chmod(output, 0o700)
    source = output / "source"
    manifest_path = output / "manifest.json"
    data: dict[str, object] = {
        "schema": 1,
        "status": "FAILED",
        "commit": commit,
        "tree": git(repo, "rev-parse", f"{commit}^{{tree}}"),
        "runner_sha256": sha256(SCRIPT),
        "lock_sha256": sha256(lock),
        "exclusions_sha256": sha256(exclusions),
        "python": version,
        "platform": platform.platform(),
        "started_at_utc": utc_now(),
        "source_archive_excludes": list(PRIVATE_PREFIXES),
        "steps": [],
    }
    write_manifest(manifest_path, data)
    try:
        snapshot(repo, commit, source)
        venv = output / "venv"
        env = os.environ.copy()
        env.update({"PYTHONNOUSERSITE": "1", "PIP_CONFIG_FILE": os.devnull, "UV_NO_CONFIG": "1"})
        steps = [
            ("venv", [str(python), "-m", "venv", str(venv)], output),
            (
                "dependencies",
                [
                    "uv",
                    "pip",
                    "sync",
                    "--python",
                    str(venv / "bin/python"),
                    "--require-hashes",
                    str(lock),
                ],
                output,
            ),
            (
                "project",
                [
                    "uv",
                    "pip",
                    "install",
                    "--python",
                    str(venv / "bin/python"),
                    "--no-build-isolation",
                    "--no-deps",
                    "--editable",
                    str(source),
                ],
                output,
            ),
            ("ruff", [str(venv / "bin/ruff"), "check", "."], source),
            ("mypy", [str(venv / "bin/mypy"), "src"], source),
            (
                "pytest",
                [
                    str(venv / "bin/python"),
                    str(SCRIPT),
                    "--repo",
                    str(repo),
                    "--sha",
                    commit,
                    "--output-dir",
                    str(output),
                    "--python",
                    str(python),
                    "--internal-pytest",
                    "--snapshot",
                    str(source),
                    "--exclusions",
                    str(exclusions),
                    "--result",
                    str(output / "pytest_result.json"),
                ],
                source,
            ),
        ]
        for name, command, cwd in steps:
            log = output / f"{name}.log"
            code = execute(command, log, cwd=cwd, env=env)
            data["steps"].append(
                {"name": name, "exit_code": code, "log": log.name, "sha256": sha256(log)}
            )  # type: ignore[union-attr]
            write_manifest(manifest_path, data)
            if code:
                return code
        pytest_result = json.loads((output / "pytest_result.json").read_text())
        data["pytest"] = pytest_result
        data["status"] = "COMPLETED_SUCCESS"
        return 0
    except Exception as exc:
        data["error"] = f"{type(exc).__name__}: {exc}"
        return 1
    finally:
        data["finished_at_utc"] = utc_now()
        write_manifest(manifest_path, data)
        print(f"{data['status']} commit={commit} python={version} manifest={manifest_path}")


if __name__ == "__main__":
    sys.exit(main())
