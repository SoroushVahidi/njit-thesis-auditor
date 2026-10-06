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

import os
import re
import subprocess
from pathlib import Path

import njit_auditor

UNKNOWN_CODE_SHA = "unknown"

_FULL_SHA_RE = re.compile(r"[0-9a-f]{40}")
_GIT_TIMEOUT_SECONDS = 5


def is_full_commit_sha(value: str) -> bool:
    return _FULL_SHA_RE.fullmatch(value) is not None


def git_output(work_tree: Path, *args: str) -> str | None:
    """Stdout of a read-only git command run against ``work_tree``, or ``None``."""
    # Inherited GIT_DIR/GIT_WORK_TREE/... (set inside git hooks, some CI
    # wrappers) override ``-C`` and would silently point at another repository.
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    try:
        result = subprocess.run(
            ["git", "-C", str(work_tree), *args],
            capture_output=True,
            text=True,
            timeout=_GIT_TIMEOUT_SECONDS,
            check=False,
            env=env,
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


def executing_repo_root(package_file: str | Path | None = None) -> Path | None:
    """Git work tree that ``package_file`` (default: the imported
    ``njit_auditor/__init__.py``) is tracked in, or ``None``.

    Follows the package's own location -- never cwd or another checkout. A
    worktree's ``.git`` file is handled like a ``.git`` directory.
    """
    package_init = Path(package_file or njit_auditor.__file__).resolve()
    work_tree = _enclosing_work_tree(package_init.parent)
    if work_tree is None:
        return None
    # Reject a package copy that is not part of this work tree's tracked
    # source (e.g. an installed copy inside a venv nested in another repo).
    relative = package_init.relative_to(work_tree).as_posix()
    if git_output(work_tree, "ls-files", "--error-unmatch", "--", relative) is None:
        return None
    return work_tree


def source_tree_code_sha(package_file: str | Path | None = None) -> str:
    """Commit SHA of :func:`executing_repo_root`, or ``UNKNOWN_CODE_SHA``."""
    work_tree = executing_repo_root(package_file)
    if work_tree is None:
        return UNKNOWN_CODE_SHA
    head = git_output(work_tree, "rev-parse", "--verify", "HEAD^{commit}")
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
