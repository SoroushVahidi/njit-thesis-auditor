"""Ledger ``code_sha`` must name the commit of the source tree the auditor
was imported from -- never an unrelated checkout, cwd, or guessed value.

All Git repositories here are synthetic, built under ``tmp_path``.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from njit_auditor.review_ledger import cli, provenance
from njit_auditor.review_ledger.identifiers import make_thesis_id, make_thesis_version_id
from njit_auditor.review_ledger.importers.thesis_registry import RegisteredDocument
from njit_auditor.review_ledger.models import Thesis, ThesisVersion
from njit_auditor.review_ledger.paths import LedgerPathError
from njit_auditor.review_ledger.provenance import (
    UNKNOWN_CODE_SHA,
    resolve_code_sha,
    source_tree_code_sha,
)
from njit_auditor.review_ledger.store import EsterReviewLedger

from .git_fixtures import PKG_INIT as _PKG_INIT
from .git_fixtures import commit_all as _commit_all
from .git_fixtures import git as _git
from .git_fixtures import import_package_from as _import_package_from
from .git_fixtures import make_repo as _make_repo

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")

def test_normal_checkout_returns_its_head(tmp_path: Path) -> None:
    repo, head = _make_repo(tmp_path / "repo")
    assert source_tree_code_sha(repo / _PKG_INIT) == head


def test_worktree_returns_its_own_head_not_the_primary_checkout(tmp_path: Path) -> None:
    primary, first = _make_repo(tmp_path / "primary")
    worktree = tmp_path / "elsewhere" / "wt"
    _git(primary, "worktree", "add", "-q", "--detach", str(worktree), first)
    (primary / "extra.txt").write_text("x\n", encoding="utf-8")
    second = _commit_all(primary, "advance primary")

    assert (worktree / ".git").is_file()  # worktree marker is a file, not a dir
    assert source_tree_code_sha(primary / _PKG_INIT) == second
    assert source_tree_code_sha(worktree / _PKG_INIT) == first


def test_follows_package_location_not_cwd(tmp_path: Path, monkeypatch) -> None:
    repo, head = _make_repo(tmp_path / "pkg_repo")
    other, other_head = _make_repo(tmp_path / "unrelated_repo")
    monkeypatch.chdir(other)
    _import_package_from(monkeypatch, repo / _PKG_INIT)
    assert resolve_code_sha() == head != other_head


def test_ignores_inherited_git_environment(tmp_path: Path, monkeypatch) -> None:
    repo, head = _make_repo(tmp_path / "pkg_repo")
    other, other_head = _make_repo(tmp_path / "unrelated_repo")
    monkeypatch.setenv("GIT_DIR", str(other / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(other))
    assert source_tree_code_sha(repo / _PKG_INIT) == head != other_head


def test_explicit_sha_wins_and_is_normalized(tmp_path: Path, monkeypatch) -> None:
    repo, _head = _make_repo(tmp_path / "repo")
    _import_package_from(monkeypatch, repo / _PKG_INIT)
    explicit = "AB" * 20
    assert resolve_code_sha(explicit) == "ab" * 20


@pytest.mark.parametrize("bad", ["", "dca4820", "z" * 40, "a" * 41, "unknown"])
def test_invalid_explicit_sha_is_rejected(bad: str) -> None:
    with pytest.raises(ValueError):
        resolve_code_sha(bad)


def test_no_git_metadata_returns_unknown(tmp_path: Path) -> None:
    pkg = tmp_path / "exported/src/njit_auditor"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    assert source_tree_code_sha(pkg / "__init__.py") == UNKNOWN_CODE_SHA


def test_untracked_copy_inside_unrelated_repo_is_not_attributed_to_it(tmp_path: Path) -> None:
    outer, _head = _make_repo(tmp_path / "outer")
    copy = outer / ".venv/lib/site-packages/njit_auditor"
    copy.mkdir(parents=True)
    (copy / "__init__.py").write_text("", encoding="utf-8")
    assert source_tree_code_sha(copy / "__init__.py") == UNKNOWN_CODE_SHA


def test_repo_without_commits_returns_unknown(tmp_path: Path) -> None:
    repo = tmp_path / "empty"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "src/njit_auditor").mkdir(parents=True)
    (repo / _PKG_INIT).write_text("", encoding="utf-8")
    _git(repo, "add", "-A")  # tracked in the index, but HEAD does not exist
    assert source_tree_code_sha(repo / _PKG_INIT) == UNKNOWN_CODE_SHA


@pytest.mark.parametrize("stdout", ["", "not-a-sha", "a" * 39, "deadbeef\n" * 5])
def test_invalid_git_output_is_rejected(tmp_path: Path, monkeypatch, stdout: str) -> None:
    repo, _head = _make_repo(tmp_path / "repo")
    real_run = subprocess.run

    def fake_run(cmd, *args, **kwargs):
        if "rev-parse" in cmd:
            return subprocess.CompletedProcess(cmd, 0, stdout=stdout, stderr="")
        return real_run(cmd, *args, **kwargs)

    monkeypatch.setattr(provenance.subprocess, "run", fake_run)
    assert source_tree_code_sha(repo / _PKG_INIT) == UNKNOWN_CODE_SHA


def test_git_unavailable_returns_unknown(tmp_path: Path, monkeypatch) -> None:
    repo, _head = _make_repo(tmp_path / "repo")

    def raise_oserror(*args, **kwargs):
        raise FileNotFoundError("git")

    monkeypatch.setattr(provenance.subprocess, "run", raise_oserror)
    assert source_tree_code_sha(repo / _PKG_INIT) == UNKNOWN_CODE_SHA


def test_cli_code_sha_flag_is_passed_through(tmp_path: Path, monkeypatch) -> None:
    seen: dict[str, object] = {}
    monkeypatch.setattr(cli, "migrate", lambda root, **kw: seen.update(root=root, **kw))
    monkeypatch.setattr(
        "sys.argv",
        ["cli", "migrate", "--ledger-root", str(tmp_path / "l"), "--code-sha", "c" * 40],
    )
    cli.main()
    assert seen == {"root": tmp_path / "l", "code_sha": "c" * 40}


def _stub_migrate_dependencies(monkeypatch) -> None:
    """Replace corpus/importer I/O in ``cli.migrate`` with one synthetic doc."""

    def fake_register_corpus(ledger, *, first_seen_at, **_kw):
        thesis_id = make_thesis_id("SynthDoc")
        version_id = make_thesis_version_id(thesis_id, "0" * 64)
        if thesis_id not in ledger.theses:
            ledger.add_thesis(Thesis(thesis_id=thesis_id, display_label="SynthDoc"))
            ledger.add_thesis_version(
                ThesisVersion(
                    thesis_version_id=version_id,
                    thesis_id=thesis_id,
                    sha256="0" * 64,
                    source_format="pdf",
                    page_count=1,
                    first_seen_at=first_seen_at,
                )
            )
        return [
            RegisteredDocument("SynthDoc", Path("synthetic.pdf"), thesis_id, version_id,
                               "0" * 64, True)
        ]

    zero = SimpleNamespace(
        rules_in_matrix=0, resolutions_created=0, skipped_no_decision=0,
        skipped_already_present=0, total_known_cases=0, cases_created=0,
        cases_already_present=0, adjudications_created=0, adjudications_already_present=0,
        version_unresolved=[], total=0, applied=0, already_applied=0, skipped=0,
        packages_scanned=0, rows_read=0, rows_with_verdict=0, rows_blank=0,
        rows_unparseable=0, total_known_policies=0, policies_created=0,
        policies_already_present=0,
    )
    monkeypatch.setattr(cli, "register_corpus", fake_register_corpus)
    monkeypatch.setattr(
        cli, "run_audit_for_uploaded_file", lambda _path: SimpleNamespace(findings=[])
    )
    for name in ("import_authority_matrix", "migrate_known_cases",
                 "migrate_known_supersessions", "migrate_known_policies"):
        monkeypatch.setattr(cli, name, lambda *a, **k: zero)
    monkeypatch.setattr(cli, "scan_xlsx_packages", lambda *a, **k: zero)


def _stamped_shas(ledger_root: Path) -> set[object]:
    shas: set[object] = set()
    for name in ("review_rounds", "auditor_runs"):
        path = ledger_root / f"{name}.jsonl"
        shas |= {json.loads(line)["code_sha"] for line in path.read_text().splitlines()}
    return shas


def test_migrate_stamps_rows_with_executing_source_sha(tmp_path: Path, monkeypatch) -> None:
    repo, head = _make_repo(tmp_path / "pkg_repo", authority_marker="pkg")
    _other, other_head = _make_repo(tmp_path / "main", authority_marker="decoy")
    monkeypatch.chdir(_other)
    _import_package_from(monkeypatch, repo / _PKG_INIT)
    _stub_migrate_dependencies(monkeypatch)

    cli.migrate(ledger_root=tmp_path / "ledger")
    assert _stamped_shas(tmp_path / "ledger") == {head}
    assert other_head not in _stamped_shas(tmp_path / "ledger")


def test_migrate_explicit_sha_overrides_derived(tmp_path: Path, monkeypatch) -> None:
    repo, _head = _make_repo(tmp_path / "pkg_repo", authority_marker="pkg")
    _import_package_from(monkeypatch, repo / _PKG_INIT)
    _stub_migrate_dependencies(monkeypatch)

    cli.migrate(ledger_root=tmp_path / "ledger", code_sha="e" * 40)
    assert _stamped_shas(tmp_path / "ledger") == {"e" * 40}


def test_migrate_without_git_fails_before_writing_not_another_repo(
    tmp_path: Path, monkeypatch
) -> None:
    # No source tree -> tracked authority is unresolvable; migrate must fail
    # loudly before touching the ledger rather than borrow the decoy's data/SHA.
    pkg = tmp_path / "exported/src/njit_auditor"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    _decoy, _decoy_head = _make_repo(tmp_path / "main", authority_marker="decoy")
    monkeypatch.chdir(_decoy)
    _import_package_from(monkeypatch, pkg / "__init__.py")
    _stub_migrate_dependencies(monkeypatch)

    with pytest.raises(LedgerPathError, match="could not be resolved"):
        cli.migrate(ledger_root=tmp_path / "ledger")
    assert not (tmp_path / "ledger").exists()


def test_replay_without_git_records_unknown_not_another_repo(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    pkg = tmp_path / "exported/src/njit_auditor"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    _decoy, decoy_head = _make_repo(tmp_path / "main")
    monkeypatch.chdir(_decoy)
    _import_package_from(monkeypatch, pkg / "__init__.py")
    _stub_migrate_dependencies(monkeypatch)
    EsterReviewLedger(tmp_path / "ledger")  # an existing (empty) scratch ledger
    monkeypatch.setattr("sys.argv", ["cli", "replay", "--ledger-root", str(tmp_path / "ledger")])

    cli.main()
    runs = (tmp_path / "ledger/auditor_runs.jsonl").read_text().splitlines()
    assert {json.loads(line)["code_sha"] for line in runs} == {UNKNOWN_CODE_SHA}
    assert decoy_head not in (tmp_path / "ledger/auditor_runs.jsonl").read_text()
    assert "could not derive" in capsys.readouterr().err
