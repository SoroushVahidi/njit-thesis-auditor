"""Synthetic Git repositories for review-ledger provenance tests.

Everything is built under pytest's ``tmp_path``; nothing reads the user's
real checkouts. Not itself a test module.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

from njit_auditor.review_ledger import provenance
from njit_auditor.review_ledger.paths import (
    AUTHORITY_MATRIX_RELPATH,
    ESTER_FEEDBACK_PACKAGES_RELDIR,
)

PKG_INIT = "src/njit_auditor/__init__.py"
PACKAGE_MARKER_FILE = "MARKER.txt"


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def commit_all(repo: Path, message: str) -> str:
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", message)
    return git(repo, "rev-parse", "HEAD")


def write_authority(root: Path, marker: str) -> None:
    """Tracked-authority stand-ins carrying ``marker`` (synthetic content only)."""
    matrix = root / AUTHORITY_MATRIX_RELPATH
    matrix.parent.mkdir(parents=True, exist_ok=True)
    matrix.write_text(json.dumps({"marker": marker}) + "\n", encoding="utf-8")
    packages = root / ESTER_FEEDBACK_PACKAGES_RELDIR
    packages.mkdir(parents=True, exist_ok=True)
    (packages / PACKAGE_MARKER_FILE).write_text(marker + "\n", encoding="utf-8")


def make_repo(root: Path, *, authority_marker: str | None = None) -> tuple[Path, str]:
    """A committed repo with ``src/njit_auditor/__init__.py`` (and, optionally,
    the tracked authority files). Content is unique per repo so identical
    commits never collide across repos."""
    root.mkdir(parents=True)
    git(root, "init", "-q")
    (root / "src/njit_auditor").mkdir(parents=True)
    (root / PKG_INIT).write_text(f"# synthetic {root}\n", encoding="utf-8")
    if authority_marker is not None:
        write_authority(root, authority_marker)
    return root, commit_all(root, "initial")


def import_package_from(monkeypatch, package_init: Path) -> None:
    """Make the resolvers see ``njit_auditor`` as imported from ``package_init``."""
    monkeypatch.setattr(provenance, "njit_auditor", SimpleNamespace(__file__=str(package_init)))
