"""Lightweight CURRENT_STATUS drift-prevention checks.

These tests keep the canonical status entry point discoverable and force the
status snapshot fields (SHA + pytest count) to stay synchronized between:

- ``docs/status/CURRENT_STATUS.md``
- ``data/processed/evaluation_data_manifest.json``

They intentionally do **not** require network access. A strict collect-count
ratchet against a live ``pytest --collect-only`` inventory is available via
``NJITA_STRICT_STATUS_DRIFT=1`` because environments can differ slightly in
how optional/skipping tests are collected.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

MANIFEST_PATH = Path("data/processed/evaluation_data_manifest.json")
CURRENT_STATUS_PATH = Path("docs/status/CURRENT_STATUS.md")
STATUS_README_PATH = Path("docs/status/README.md")
TOP_README_PATH = Path("README.md")


def _load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_status_readme_points_at_current_status_entry_point() -> None:
    text = STATUS_README_PATH.read_text(encoding="utf-8")
    assert "CURRENT_STATUS.md" in text
    assert re.search(r"\[CURRENT_STATUS\.md\]\(CURRENT_STATUS\.md\)", text)


def test_top_readme_mentions_current_status_entry_point() -> None:
    text = TOP_README_PATH.read_text(encoding="utf-8")
    assert "docs/status/CURRENT_STATUS.md" in text


def test_current_status_matches_manifest_snapshot_fields() -> None:
    manifest = _load_manifest()
    status = CURRENT_STATUS_PATH.read_text(encoding="utf-8")
    sha = str(manifest["main_commit_used_for_status_snapshot"])
    count = int(manifest["pytest_count_used_for_status_snapshot"])
    skips = int(manifest["pytest_skips_used_for_status_snapshot"])
    assert re.fullmatch(r"[0-9a-f]{7}", sha)
    assert sha in status
    assert f"{count} passed" in status
    assert f"{skips} skipped" in status
    assert manifest["auditor_rule_state"]["pytest_count_used_for_status_snapshot"] == count
    assert manifest["auditor_rule_state"]["pytest_skips_used_for_status_snapshot"] == skips
    assert manifest["auditor_rule_state"]["main_commit_used_for_status_snapshot"] == sha


def test_optional_strict_collect_count_matches_manifest_snapshot() -> None:
    if os.environ.get("NJITA_STRICT_STATUS_DRIFT") != "1":
        return
    manifest = _load_manifest()
    passed = int(manifest["pytest_count_used_for_status_snapshot"])
    skipped = int(manifest["pytest_skips_used_for_status_snapshot"])
    expected = passed + skipped
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "tests"],
        check=True,
        capture_output=True,
        text=True,
    )
    match = re.search(r"(\d+) tests collected", proc.stdout)
    assert match, proc.stdout
    collected = int(match.group(1))
    assert collected == expected, (
        f"Collected {collected} tests but status snapshot records "
        f"{passed} passed plus {skipped} skipped ({expected} collected). "
        "Update BOTH docs/status/CURRENT_STATUS.md and "
        "data/processed/evaluation_data_manifest.json when recording a new snapshot."
    )
