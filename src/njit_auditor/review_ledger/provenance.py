"""Resolve the Git commit of the source tree the running auditor was imported from.

Ledger rows (``ReviewRound``/``AuditorRun``/``RegressionResult``/replay
``HistoryEvent``) record ``code_sha`` as provenance for "which code produced
this". That must be the commit of the checkout ``njit_auditor`` was actually
loaded from -- not the process cwd, not ``origin/main``, and not whichever
checkout happens to be named ``main`` (worktrees and the detached production
checkout each have their own HEAD).

Precedence:

1. an explicit caller-provided SHA (validated as a full 40-hex commit id);
2. ``git rev-parse HEAD`` of the Git work tree that contains the imported
   package, accepted only if the package is tracked by that work tree (so a
   copy that merely sits under some unrelated repository is not attributed
   to it);
3. :data:`UNKNOWN_CODE_SHA` -- never a guessed or unrelated SHA.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import njit_auditor

UNKNOWN_CODE_SHA = "unknown"

_FULL_SHA_RE = re.compile(r"[0-9a-f]{40}")
_GIT_TIMEOUT_SECONDS = 5


def is_full_commit_sha(value: str) -> bool:
    return _FULL_SHA_RE.fullmatch(value) is not None


def _git(work_tree: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(work_tree), *args],
            capture_output=True,
            text=True,
            timeout=_GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _enclosing_work_tree(start: Path) -> Path | None:
    """Nearest ancestor holding ``.git`` (a directory, or a file for worktrees)."""
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def source_tree_code_sha(package_file: str | Path | None = None) -> str:
    """Commit SHA of the work tree that ``package_file`` (default: the
    imported ``njit_auditor/__init__.py``) belongs to, or ``UNKNOWN_CODE_SHA``."""
    package_init = Path(package_file or njit_auditor.__file__).resolve()
    work_tree = _enclosing_work_tree(package_init.parent)
    if work_tree is None:
        return UNKNOWN_CODE_SHA
    # Reject a package copy that is not part of this work tree's tracked
    # source (e.g. an installed copy inside a venv nested in another repo).
    relative = package_init.relative_to(work_tree).as_posix()
    if _git(work_tree, "ls-files", "--error-unmatch", "--", relative) is None:
        return UNKNOWN_CODE_SHA
    head = _git(work_tree, "rev-parse", "--verify", "HEAD^{commit}")
    if head is None or not is_full_commit_sha(head):
        return UNKNOWN_CODE_SHA
    return head


def resolve_code_sha(explicit: str | None = None) -> str:
    """Code SHA to stamp on new ledger rows (see module docstring)."""
    if explicit is not None:
        normalized = explicit.strip().lower()
        if not is_full_commit_sha(normalized):
            raise ValueError(f"explicit code SHA must be a full 40-hex commit id: {explicit!r}")
        return normalized
    return source_tree_code_sha()
