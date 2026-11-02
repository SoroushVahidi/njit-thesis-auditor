"""Exercise real Git CRLF checkout conversion and the unchanged production gate."""

from __future__ import annotations

import json
import runpy
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CATALOG = Path("data/processed/rules/project_added_rules.json")
RUNNER = Path("src/njit_auditor/audit_runner.py")


def checkout(tmp_path: Path, *, attributes: bool):
    def git(*args: str) -> bytes:
        return subprocess.check_output(["git", *args], cwd=tmp_path, stderr=subprocess.PIPE)

    git("init", "-q")
    git("config", "core.autocrlf", "true")
    git("config", "core.eol", "crlf")
    git("config", "core.safecrlf", "false")
    paths = [CATALOG, RUNNER] + [
        p.relative_to(ROOT) for p in sorted((ROOT / "src/njit_auditor/rules").glob("*.py"))
    ]
    if attributes:
        (tmp_path / ".gitattributes").write_bytes((ROOT / ".gitattributes").read_bytes())
    for relative in paths:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        # Use committed blobs, not the test host's possibly converted working tree.
        target.write_bytes(
            subprocess.check_output(["git", "show", f"HEAD:{relative.as_posix()}"], cwd=ROOT)
        )
    git("add", ".")
    git(
        "-c",
        "user.name=Checkout Test",
        "-c",
        "user.email=checkout@example.invalid",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "-qm",
        "Synthetic parity checkout",
    )
    for relative in paths:
        (tmp_path / relative).unlink()
    git("checkout-index", "--all", "--force")
    (tmp_path / "docs").mkdir()
    main = runpy.run_path(str(ROOT / "scripts/build_desktop_parity_matrix.py"))["main"]
    main.__globals__["ROOT"] = tmp_path
    main.__globals__["BASELINE"] = git("rev-parse", "HEAD").decode().strip()
    return git, paths, main


def test_unpinned_windows_checkout_reproduces_catalog_failure(tmp_path: Path) -> None:
    git, _, main = checkout(tmp_path, attributes=False)
    blob = git("show", f"HEAD:{CATALOG.as_posix()}")
    working = (tmp_path / CATALOG).read_bytes()
    assert b"\r\n" not in blob
    assert working != blob
    assert working == blob.replace(b"\n", b"\r\n")
    assert json.loads(working) == json.loads(blob)
    with pytest.raises(AssertionError):
        main()


def test_pinned_windows_checkout_preserves_every_parity_input(tmp_path: Path) -> None:
    git, paths, main = checkout(tmp_path, attributes=True)
    for relative in paths:
        blob = git("show", f"HEAD:{relative.as_posix()}")
        assert (tmp_path / relative).read_bytes() == blob, relative
    main()


@pytest.mark.parametrize(
    "relative", [CATALOG, RUNNER, Path("src/njit_auditor/rules/pdf_margins.py")]
)
def test_substantive_drift_still_fails(tmp_path: Path, relative: Path) -> None:
    _, _, main = checkout(tmp_path, attributes=True)
    target = tmp_path / relative
    if relative == CATALOG:
        rules = json.loads(target.read_bytes())
        rules[0]["rule_definition"] += " Synthetic unauthorized change."
        target.write_bytes(json.dumps(rules).encode())
    else:
        target.write_bytes(target.read_bytes() + b"\nUNAUTHORIZED_THRESHOLD = 999\n")
    with pytest.raises(AssertionError):
        main()
