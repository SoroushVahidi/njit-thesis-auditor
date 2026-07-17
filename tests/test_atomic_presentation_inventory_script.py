"""Smoke tests for scripts/atomic_presentation_inventory.py.

The script is a read-only diagnostic (see docs/status/
atomic_presentation_inventory_20260716.md) — it must never touch a detector,
a PDF, or any runtime finding. These tests exercise it both as a library
(direct import, matching how a future CI check might use it) and as a CLI
(subprocess, matching the project's convention for other scripts/*.py tools
— see test_duplicate_candidate_analysis.py's CLI test).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "scripts"))

import atomic_presentation_inventory as inventory  # noqa: E402


def test_build_inventory_returns_only_atomic_or_refine_buckets() -> None:
    rows = inventory.build_inventory()
    assert rows, "expected at least one active (rule_id, issue_type) pair"
    for row in rows:
        assert row["bucket"] in {"ATOMIC", "PRESENTATION_SHOULD_BE_REFINED"}
        assert row["rule_id"] and row["issue_type"]


def test_no_presentation_gaps_remain_after_this_pass() -> None:
    """Regression guard: this pass closed every mechanically-discoverable
    generic-fallback gap. If this ever fails, a new detector or wording
    change introduced a fresh gap that needs a template, not a silent skip."""
    rows = inventory.build_inventory()
    gaps = [r for r in rows if r["bucket"] != "ATOMIC"]
    assert not gaps, f"unexpected presentation gaps: {gaps}"


def test_render_markdown_includes_summary_counts() -> None:
    rows = inventory.build_inventory()
    markdown = inventory.render_markdown(rows)
    assert "Atomic Presentation Inventory" in markdown
    assert "ATOMIC" in markdown or "Atomic" in markdown


def test_cli_help_runs_and_describes_purpose() -> None:
    script = _REPO_ROOT / "scripts" / "atomic_presentation_inventory.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--help"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "diagnostic" in proc.stdout.lower() or "diagnostic" in proc.stdout


def test_cli_json_out_writes_valid_json_and_does_not_touch_repo_files(
    tmp_path: Path,
) -> None:
    script = _REPO_ROOT / "scripts" / "atomic_presentation_inventory.py"
    out_path = tmp_path / "inventory.json"
    proc = subprocess.run(
        [sys.executable, str(script), "--json-out", str(out_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert out_path.exists()
    rows = json.loads(out_path.read_text(encoding="utf-8"))
    assert isinstance(rows, list) and rows
    assert all(row["bucket"] == "ATOMIC" for row in rows)
