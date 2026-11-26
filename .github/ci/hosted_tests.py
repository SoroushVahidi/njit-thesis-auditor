"""Explicit hosted test inventory; never loaded by the default local pytest suite."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN = ("data/raw", "data/evaluation", "docs/evaluation/ester_feedback", "results")


def inventory(root: Path) -> dict:
    manifest = json.loads((root / ".github/ci/tests.json").read_text())
    hosted, local = set(manifest["hosted"]), set(manifest["local_only"])
    actual = {p.relative_to(root).as_posix() for p in (root / "tests").rglob("test_*.py")}
    support = {p.relative_to(root).as_posix() for p in (root / "tests").rglob("*.py")
               if not p.name.startswith("test_")}
    if support != set(manifest["support"]):
        raise ValueError("Test support changed: review helpers/conftest before hosted collection")
    if hosted & local or hosted | local != actual or len(hosted) != len(manifest["hosted"]):
        raise ValueError("Test inventory changed: classify every module before hosted collection")
    if not hosted or any(not reason for reason in manifest["local_only"].values()):
        raise ValueError("Empty hosted selection or missing local-only explanation")
    if any(node.split("::")[0] not in hosted for node in manifest["browser"]):
        raise ValueError("Browser selection must be a subset of reviewed hosted modules")
    return manifest


def check_workspace(root: Path) -> None:
    # Do not read or print any private filenames or contents on failure.
    if any((root / name).exists() for name in FORBIDDEN):
        raise ValueError("Private fixture roots must be absent; use the documented sparse checkout")
    if os.environ.get("NJIT_ESTER_AUDIT_SOURCE_MANIFEST"):
        raise ValueError("Private replay environment is forbidden in hosted validation")
    if os.environ.get("GIT_LFS_SKIP_SMUDGE") != "1":
        raise ValueError("LFS smudging must be disabled")
    if subprocess.check_output(["git", "remote"], cwd=root).strip():
        raise ValueError("Remove checkout remotes before executing hosted code")
    excluded = subprocess.check_output(
        ["git", "config", "--local", "--get", "lfs.fetchexclude"], cwd=root, text=True
    ).strip()
    if excluded != "*":
        raise ValueError("All LFS fetching must be excluded")
    paths = subprocess.check_output(["git", "ls-files", "-z"], cwd=root)
    attributes = subprocess.check_output(
        ["git", "check-attr", "-z", "--stdin", "filter"], input=paths, cwd=root
    ).split(b"\0")
    for name, _, kind in zip(attributes[0::3], attributes[1::3], attributes[2::3]):
        path = root / os.fsdecode(name)
        if kind == b"lfs" and path.is_file():
            with path.open("rb") as stream:
                if not stream.read(100).startswith(b"version https://git-lfs.github.com/spec/v1\n"):
                    raise ValueError("Materialized LFS content is forbidden in hosted validation")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("group", choices=("check", "test", "browser"))
    parser.add_argument("--collect-only", action="store_true")
    parser.add_argument("--shard", type=int, default=0)
    parser.add_argument("--shards", type=int, default=1)
    args = parser.parse_args()
    check_workspace(ROOT)
    manifest = inventory(ROOT)
    print(f"Hosted inventory: {len(manifest['hosted'])} modules; "
          f"{len(manifest['local_only'])} local-only modules (not collected)", flush=True)
    if args.group == "check":
        return 0
    if not 0 <= args.shard < args.shards:
        parser.error("Invalid shard")
    nodes = manifest["browser" if args.group == "browser" else "hosted"]
    nodes = nodes[args.shard::args.shards]
    if not nodes:
        parser.error("Empty shard")
    output = ROOT / ".runtime" / f"hosted-{args.group}-{args.shard}.xml"
    output.parent.mkdir(exist_ok=True)
    env = os.environ.copy()
    for name in ("PYTEST_ADDOPTS", "PYTEST_PLUGINS", "NJITA_STRICT_STATUS_DRIFT"):
        env.pop(name, None)
    env.update(PYTHONPATH=str(ROOT / "src"), PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
               PYTHONDONTWRITEBYTECODE="1")
    command = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *nodes]
    if args.collect_only:
        command.append("--collect-only")
    else:
        command.append(f"--junitxml={output}")
    code = subprocess.call(command, cwd=ROOT, env=env)
    if code == 0 and args.group == "browser" and not args.collect_only:
        suites = list(ET.parse(output).iter("testsuite"))
        if not sum(int(s.attrib["tests"]) for s in suites) or any(
            int(s.attrib["skipped"]) for s in suites
        ):
            raise ValueError("Browser coverage must execute without skips")
    return code


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ValueError as error:
        sys.exit(str(error))
