"""Where the review ledger's provenance-sensitive inputs and outputs live.

Two deliberately different policies:

- **Tracked authority data** (the Ester authority matrix, the per-rule
  feedback packages) is part of the source tree, so it is resolved from
  the same Git work tree as the executing ``njit_auditor`` package
  (:func:`~njit_auditor.review_ledger.provenance.executing_repo_root`).
  Code from commit X therefore always reads authority data from commit X.
  If that tree cannot be found, or lacks the tracked file, resolution fails
  -- it never falls back to another checkout or to cwd.

- **The ledger itself** is mutable private state and is never chosen
  implicitly. A caller must select it with ``--ledger-root PATH``, the
  ``NJIT_AUDITOR_LEDGER_ROOT`` environment variable, or ``--shared-ledger``
  for the canonical shared Ester ledger.

The private dissertation corpus is shared read-only data and stays at its
canonical location (``importers.thesis_registry.PRIVATE_DATA_DIR``).
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import njit_auditor
from njit_auditor.review_ledger.provenance import executing_repo_root, git_output

AUTHORITY_MATRIX_RELPATH = Path("docs/status/ester_authority_matrix_20260902.json")
ESTER_FEEDBACK_PACKAGES_RELDIR = Path("docs/evaluation/ester_feedback")

CANONICAL_SHARED_LEDGER_ROOT = Path(
    "/home/soroush/njit-thesis-auditor/main/data/evaluation/private/ester_review_ledger"
)
LEDGER_ROOT_ENV = "NJIT_AUDITOR_LEDGER_ROOT"

NO_LEDGER_SELECTED_MESSAGE = (
    "No ledger root selected. Use --ledger-root PATH for a scratch/private ledger, "
    f"set {LEDGER_ROOT_ENV}, or pass --shared-ledger to explicitly use the "
    "canonical shared Ester ledger."
)


class LedgerPathError(RuntimeError):
    """A provenance-sensitive path could not be resolved safely."""


def _require_repo_root(repo_root: Path | None) -> Path:
    if repo_root is not None:
        return repo_root
    root = executing_repo_root()
    if root is None:
        raise LedgerPathError(
            "Tracked Ester authority data could not be resolved from the executing "
            f"source tree: {Path(njit_auditor.__file__).resolve().parent} is not a "
            "tracked file in any Git work tree"
        )
    return root


def _tracked_files(repo_root: Path, relative: Path) -> list[str]:
    listing = git_output(repo_root, "ls-files", "--", relative.as_posix())
    return listing.splitlines() if listing else []


def authority_matrix_path(repo_root: Path | None = None) -> Path:
    """The tracked authority matrix in the executing source tree."""
    root = _require_repo_root(repo_root)
    path = root / AUTHORITY_MATRIX_RELPATH
    if not path.is_file() or not _tracked_files(root, AUTHORITY_MATRIX_RELPATH):
        raise LedgerPathError(
            "Tracked Ester authority data could not be resolved from the executing "
            f"source tree: {root} has no tracked {AUTHORITY_MATRIX_RELPATH}"
        )
    return path


def ester_feedback_packages_dir(repo_root: Path | None = None) -> Path:
    """The tracked Ester feedback-package directory in the executing source tree."""
    root = _require_repo_root(repo_root)
    path = root / ESTER_FEEDBACK_PACKAGES_RELDIR
    if not path.is_dir() or not _tracked_files(root, ESTER_FEEDBACK_PACKAGES_RELDIR):
        raise LedgerPathError(
            "Tracked Ester authority data could not be resolved from the executing "
            f"source tree: {root} has no tracked {ESTER_FEEDBACK_PACKAGES_RELDIR}/"
        )
    return path


@dataclass(frozen=True)
class LedgerSelection:
    root: Path
    source: str  # "--ledger-root", the env var name, or "--shared-ledger"

    @property
    def is_canonical_shared(self) -> bool:
        return self.root.resolve() == CANONICAL_SHARED_LEDGER_ROOT.resolve()


def select_ledger_root(
    *,
    ledger_root: Path | None,
    shared_ledger: bool,
    environ: Mapping[str, str] | None = None,
) -> LedgerSelection:
    """Resolve an explicit ledger selection; never returns an implicit default.

    Precedence: ``--ledger-root`` > ``NJIT_AUDITOR_LEDGER_ROOT``; either one
    combined with ``--shared-ledger`` is a conflict and raises.
    """
    env_value = (os.environ if environ is None else environ).get(LEDGER_ROOT_ENV, "").strip()
    if shared_ledger and ledger_root is not None:
        raise LedgerPathError("Conflicting ledger selection: --ledger-root and --shared-ledger")
    if shared_ledger and env_value:
        raise LedgerPathError(
            f"Conflicting ledger selection: {LEDGER_ROOT_ENV} is set and --shared-ledger "
            f"was passed; unset {LEDGER_ROOT_ENV} or drop --shared-ledger"
        )
    if ledger_root is not None:
        return LedgerSelection(ledger_root, "--ledger-root")
    if env_value:
        return LedgerSelection(Path(env_value), LEDGER_ROOT_ENV)
    if shared_ledger:
        return LedgerSelection(CANONICAL_SHARED_LEDGER_ROOT, "--shared-ledger")
    raise LedgerPathError(NO_LEDGER_SELECTED_MESSAGE)
