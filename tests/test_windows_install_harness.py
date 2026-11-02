"""Do not bind the installer wizard to the bootstrap PID or another app's UI."""

import runpy
from pathlib import Path
from types import SimpleNamespace

import pytest

HARNESS = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "scripts/validate_windows_install.py")
)
SELECT = HARNESS["select_installer_window"]
PREFLIGHT = HARNESS["require_no_auditor_processes"]
FINISH = HARNESS["finish_installer"]


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


class LaunchCheckbox:
    def __init__(self, state=1, *, visible=True, enabled=True, responds=True):
        self.state = state
        self.visible = visible
        self.enabled = enabled
        self.responds = responds
        self.clicks = 0

    def window_text(self):
        return "&Launch NJIT Thesis Auditor"

    def is_visible(self):
        return self.visible

    def is_enabled(self):
        return self.enabled

    def get_toggle_state(self):
        return self.state

    def toggle(self):
        # The Windows provider's failing Toggle path must never be used.
        raise OSError(-2146233079, "UI Automation Toggle failed")

    def click_input(self):
        self.clicks += 1
        if self.responds:
            self.state = 1 - self.state


class CompletionPage:
    def __init__(self, checkboxes, *, ready=True):
        self.checkboxes = checkboxes
        self.ready = ready
        self.finish_clicks = 0

    def child_window(self, **kwargs):
        assert kwargs == {"title_re": ".*Finish.*", "control_type": "Button"}
        return SimpleNamespace(
            exists=lambda timeout: self.ready,
            is_enabled=lambda: self.ready,
            click_input=self.click_finish,
        )

    def descendants(self, **kwargs):
        assert kwargs == {"control_type": "CheckBox"}
        assert self.ready, "Do not inspect launch controls on earlier wizard pages"
        return self.checkboxes

    def click_finish(self):
        self.finish_clicks += 1


@pytest.mark.parametrize("initial_state", [0, 1])
def test_finish_uses_mouse_and_never_rechecks_launch_on_repeated_polls(initial_state):
    checkbox = LaunchCheckbox(initial_state)
    page = CompletionPage([checkbox], ready=False)
    assert FINISH(page) is False
    assert FINISH(page) is False
    assert checkbox.clicks == page.finish_clicks == 0
    page.ready = True
    assert FINISH(page) is True
    assert checkbox.state == 0
    assert FINISH(page) is True
    assert checkbox.state == 0
    assert checkbox.clicks == initial_state


@pytest.mark.parametrize(
    "checkboxes",
    [
        [],
        [LaunchCheckbox(), LaunchCheckbox()],
        [LaunchCheckbox(visible=False)],
        [LaunchCheckbox(enabled=False)],
        [LaunchCheckbox(2)],
        [LaunchCheckbox(None)],
        [LaunchCheckbox(responds=False)],
    ],
)
def test_finish_refuses_missing_ambiguous_or_unverified_launch_controls(checkboxes):
    page = CompletionPage(checkboxes)
    with pytest.raises(RuntimeError, match="refusing to click Finish"):
        FINISH(page)
    assert page.finish_clicks == 0


@pytest.mark.parametrize(
    "operation",
    ["window_text", "is_visible", "is_enabled", "get_toggle_state", "click_input"],
)
def test_inaccessible_uia_control_never_allows_finish(monkeypatch, operation):
    checkbox = LaunchCheckbox()
    page = CompletionPage([checkbox])

    def unavailable():
        raise OSError(-2146233079, "UI Automation provider unavailable")

    monkeypatch.setattr(checkbox, operation, unavailable)
    with pytest.raises(RuntimeError, match="refusing to click Finish") as error:
        FINISH(page)
    assert isinstance(error.value.__cause__, OSError)
    assert page.finish_clicks == checkbox.clicks == 0


def test_state_becoming_inaccessible_after_click_does_not_allow_finish(monkeypatch):
    checkbox = LaunchCheckbox()
    page = CompletionPage([checkbox])

    def read_state():
        if checkbox.clicks:
            raise OSError("UIA state unavailable after mouse input")
        return 1

    monkeypatch.setattr(checkbox, "get_toggle_state", read_state)
    with pytest.raises(RuntimeError, match="refusing to click Finish"):
        FINISH(page)
    assert checkbox.clicks == 1
    assert page.finish_clicks == 0


def test_inaccessible_checkbox_enumeration_does_not_allow_finish(monkeypatch):
    page = CompletionPage([LaunchCheckbox()])

    def unavailable(**kwargs):
        raise OSError("UIA descendants unavailable")

    monkeypatch.setattr(page, "descendants", unavailable)
    with pytest.raises(RuntimeError, match="refusing to click Finish"):
        FINISH(page)
    assert page.finish_clicks == 0


def test_ambiguous_wizards_cannot_reach_completion_interaction():
    pages = [window(11), window(22)]
    with pytest.raises(RuntimeError, match="Multiple owned"):
        FINISH(SELECT(pages, {11, 22}))
