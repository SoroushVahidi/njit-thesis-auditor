"""Tracked authority data follows the executing source tree; the ledger is
never selected implicitly.

All Git repositories are synthetic (``tmp_path``); the canonical shared
ledger is only ever *selected* here, never opened or written.
"""

from __future__ import annotations

import inspect
import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from njit_auditor.review_ledger import cli
from njit_auditor.review_ledger.paths import (
    CANONICAL_SHARED_LEDGER_ROOT,
    LEDGER_ROOT_ENV,
    LedgerPathError,
    authority_matrix_path,
    ester_feedback_packages_dir,
    select_ledger_root,
)
from njit_auditor.review_ledger.provenance import git_output

from .git_fixtures import (
    PACKAGE_MARKER_FILE,
    PKG_INIT,
    commit_all,
    git,
    import_package_from,
    make_repo,
    write_authority,
)
from .test_code_sha_provenance import _stub_migrate_dependencies

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")


@pytest.fixture(autouse=True)
def _no_ambient_ledger_env(monkeypatch) -> None:
    monkeypatch.delenv(LEDGER_ROOT_ENV, raising=False)


def _matrix_marker(path: Path) -> str:
    return str(json.loads(path.read_text(encoding="utf-8"))["marker"])


def _package_marker(directory: Path) -> str:
    return (directory / PACKAGE_MARKER_FILE).read_text(encoding="utf-8").strip()


def _two_worktrees(tmp_path: Path) -> tuple[Path, Path, str]:
    """Primary checkout A (marker A) plus a worktree B whose own commit says B."""
    primary, first = make_repo(tmp_path / "main", authority_marker="A")
    worktree = tmp_path / "worktrees" / "b"
    git(primary, "worktree", "add", "-q", "--detach", str(worktree), first)
    write_authority(worktree, "B")
    return primary, worktree, commit_all(worktree, "authority B")


# -- tracked authority resolution ----------------------------------------------------


def test_authority_follows_executing_worktree_not_cwd(tmp_path: Path, monkeypatch) -> None:
    primary, worktree, _b_head = _two_worktrees(tmp_path)
    monkeypatch.chdir(primary)
    import_package_from(monkeypatch, worktree / PKG_INIT)

    assert _matrix_marker(authority_matrix_path()) == "B"
    assert _package_marker(ester_feedback_packages_dir()) == "B"
    assert authority_matrix_path().is_relative_to(worktree)


def test_missing_tracked_authority_fails_without_fallback(tmp_path: Path, monkeypatch) -> None:
    _decoy, _ = make_repo(tmp_path / "main", authority_marker="decoy")
    repo, _ = make_repo(tmp_path / "bare_pkg")  # source tree without authority files
    monkeypatch.chdir(_decoy)
    import_package_from(monkeypatch, repo / PKG_INIT)

    with pytest.raises(LedgerPathError, match="could not be resolved from the executing"):
        authority_matrix_path()
    with pytest.raises(LedgerPathError, match="could not be resolved from the executing"):
        ester_feedback_packages_dir()


def test_untracked_authority_files_are_rejected(tmp_path: Path, monkeypatch) -> None:
    repo, _ = make_repo(tmp_path / "pkg")
    write_authority(repo, "uncommitted")  # present on disk, never committed
    import_package_from(monkeypatch, repo / PKG_INIT)

    with pytest.raises(LedgerPathError):
        authority_matrix_path()
    with pytest.raises(LedgerPathError):
        ester_feedback_packages_dir()


def test_no_source_tree_fails_loudly(tmp_path: Path, monkeypatch) -> None:
    pkg = tmp_path / "exported/src/njit_auditor"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    import_package_from(monkeypatch, pkg / "__init__.py")

    with pytest.raises(LedgerPathError, match="not a tracked file in any Git work tree"):
        authority_matrix_path()


def test_code_sha_and_authority_come_from_the_same_worktree(
    tmp_path: Path, monkeypatch
) -> None:
    """Central invariant: EXECUTING_CODE_WORKTREE == TRACKED_AUTHORITY_DATA_WORKTREE."""
    primary, worktree, b_head = _two_worktrees(tmp_path)
    monkeypatch.chdir(primary)
    import_package_from(monkeypatch, worktree / PKG_INIT)
    _stub_migrate_dependencies(monkeypatch)
    seen: dict[str, Path] = {}

    def capture_matrix(_ledger, matrix_json_path, **_kw):
        seen["matrix"] = matrix_json_path
        return SimpleNamespace(rules_in_matrix=0, resolutions_created=0,
                               skipped_no_decision=0, skipped_already_present=0)

    def capture_packages(packages_dir):
        seen["packages"] = packages_dir
        return SimpleNamespace(packages_scanned=0, rows_read=0, rows_with_verdict=0,
                               rows_blank=0, rows_unparseable=0)

    monkeypatch.setattr(cli, "import_authority_matrix", capture_matrix)
    monkeypatch.setattr(cli, "scan_xlsx_packages", capture_packages)

    cli.migrate(tmp_path / "ledger")

    rounds = (tmp_path / "ledger/review_rounds.jsonl").read_text().splitlines()
    stamped = {json.loads(line)["code_sha"] for line in rounds}
    authority_tree = Path(git_output(seen["matrix"].parent, "rev-parse", "--show-toplevel") or "")
    authority_head = git_output(authority_tree, "rev-parse", "HEAD")
    assert stamped == {b_head} == {authority_head}
    assert authority_tree.resolve() == worktree.resolve()
    assert _matrix_marker(seen["matrix"]) == "B"
    assert _package_marker(seen["packages"]) == "B"


# -- ledger selection ------------------------------------------------------------


def test_select_requires_an_explicit_choice() -> None:
    with pytest.raises(LedgerPathError, match="No ledger root selected"):
        select_ledger_root(ledger_root=None, shared_ledger=False, environ={})


def test_select_precedence_and_conflicts(tmp_path: Path) -> None:
    env = {LEDGER_ROOT_ENV: str(tmp_path / "env")}
    flag = tmp_path / "flag"
    assert select_ledger_root(ledger_root=flag, shared_ledger=False, environ=env).root == flag
    assert select_ledger_root(ledger_root=None, shared_ledger=False, environ=env).root == (
        tmp_path / "env"
    )
    shared = select_ledger_root(ledger_root=None, shared_ledger=True, environ={})
    assert shared.root == CANONICAL_SHARED_LEDGER_ROOT and shared.is_canonical_shared
    with pytest.raises(LedgerPathError, match="Conflicting"):
        select_ledger_root(ledger_root=flag, shared_ledger=True, environ={})
    with pytest.raises(LedgerPathError, match="Conflicting"):
        select_ledger_root(ledger_root=None, shared_ledger=True, environ=env)


def test_migrate_has_no_implicit_ledger_default() -> None:
    param = inspect.signature(cli.migrate).parameters["ledger_root"]
    assert param.default is inspect.Parameter.empty
    with pytest.raises(TypeError):
        cli.migrate()  # type: ignore[call-arg]


def _forbid_ledger_access(monkeypatch) -> None:
    def refuse(*_a, **_k):
        raise AssertionError("a ledger was opened or written")

    monkeypatch.setattr(cli, "EsterReviewLedger", refuse)
    monkeypatch.setattr(cli, "migrate", refuse)


@pytest.mark.parametrize("command", ["migrate", "replay"])
def test_cli_without_selection_refuses_before_touching_a_ledger(
    command: str, tmp_path: Path, monkeypatch, capsys
) -> None:
    monkeypatch.chdir(tmp_path)
    _forbid_ledger_access(monkeypatch)
    monkeypatch.setattr("sys.argv", ["cli", command])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2
    assert "No ledger root selected" in capsys.readouterr().err
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("command", ["migrate", "replay"])
def test_cli_conflicting_selection_fails(
    command: str, tmp_path: Path, monkeypatch, capsys
) -> None:
    _forbid_ledger_access(monkeypatch)
    monkeypatch.setattr(
        "sys.argv", ["cli", command, "--ledger-root", str(tmp_path), "--shared-ledger"]
    )
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2

    monkeypatch.setenv(LEDGER_ROOT_ENV, str(tmp_path / "env"))
    monkeypatch.setattr("sys.argv", ["cli", command, "--shared-ledger"])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2
    assert "Conflicting ledger selection" in capsys.readouterr().err


def test_cli_shared_ledger_selects_canonical_path(monkeypatch, capsys) -> None:
    seen: dict[str, object] = {}
    monkeypatch.setattr(cli, "migrate", lambda root, **kw: seen.update(root=root))
    monkeypatch.setattr(cli, "EsterReviewLedger", lambda *_a: pytest.fail("ledger opened"))
    monkeypatch.setattr("sys.argv", ["cli", "migrate", "--shared-ledger"])
    cli.main()
    assert seen == {"root": CANONICAL_SHARED_LEDGER_ROOT}
    assert "CANONICAL SHARED LEDGER" in capsys.readouterr().err


@pytest.mark.parametrize("via", ["flag", "env"])
def test_cli_migrate_writes_only_to_selected_root(
    via: str, tmp_path: Path, monkeypatch
) -> None:
    repo, head = make_repo(tmp_path / "pkg", authority_marker="pkg")
    work = tmp_path / "cwd"
    work.mkdir()
    monkeypatch.chdir(work)
    import_package_from(monkeypatch, repo / PKG_INIT)
    _stub_migrate_dependencies(monkeypatch)
    target = tmp_path / "scratch_ledger"
    argv = ["cli", "migrate"]
    if via == "flag":
        argv += ["--ledger-root", str(target)]
    else:
        monkeypatch.setenv(LEDGER_ROOT_ENV, str(target))
    monkeypatch.setattr("sys.argv", argv)

    cli.main()
    assert (target / "_ledger_meta.json").is_file()
    assert list(work.iterdir()) == []
    rounds = (target / "review_rounds.jsonl").read_text().splitlines()
    assert {json.loads(line)["code_sha"] for line in rounds} == {head}


def test_cli_replay_never_creates_a_missing_ledger(tmp_path: Path, monkeypatch, capsys) -> None:
    missing = tmp_path / "typo_ledger"
    monkeypatch.setattr("sys.argv", ["cli", "replay", "--ledger-root", str(missing)])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2
    assert "not an existing ledger" in capsys.readouterr().err
    assert not missing.exists()
