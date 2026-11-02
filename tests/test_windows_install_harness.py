"""Do not bind the installer wizard to the bootstrap PID or another app's UI."""

import runpy
from pathlib import Path
from types import SimpleNamespace

import pytest

SELECT = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "scripts/validate_windows_install.py")
)["select_installer_window"]
PREFLIGHT = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "scripts/validate_windows_install.py")
)["require_no_auditor_processes"]


def window(pid, *, title="Setup - NJIT Thesis Auditor", kind="TWizardForm", visible=True):
    return SimpleNamespace(
        process_id=lambda: pid,
        window_text=lambda: title,
        class_name=lambda: kind,
        is_visible=lambda: visible,
        handle=pid + 1000,
    )


def test_child_wizard_found_when_loader_has_no_window():
    child = window(22)
    assert SELECT([child], {11, 22}) is child


def test_same_title_from_unrelated_process_is_never_selected():
    child = window(22)
    unrelated = window(33)
    assert SELECT([unrelated, child], {11, 22}) is child
    assert SELECT([unrelated], {11, 22}) is None


@pytest.mark.parametrize(
    "candidate",
    [
        window(22, visible=False),
        window(22, kind="#32770"),
        window(22, title="Other setup"),
    ],
)
def test_wait_for_visible_actual_wizard(candidate):
    assert SELECT([candidate], {11, 22}) is None


def test_ambiguous_owned_wizards_are_rejected():
    with pytest.raises(RuntimeError, match="Multiple owned"):
        SELECT([window(11), window(22)], {11, 22})


def test_validation_refuses_existing_auditor_without_closing_it():
    class Existing:
        info = {"name": "NJIT Thesis Auditor.exe"}

        def terminate(self):
            pytest.fail("Validation must not terminate an existing audit")

    with pytest.raises(RuntimeError, match="already running"):
        PREFLIGHT([Existing()])
    PREFLIGHT([SimpleNamespace(info={"name": "unrelated.exe"}), SimpleNamespace(info={})])
