"""Portable macOS policy tests. Simulations do not establish native qualification."""

from __future__ import annotations

import json
import plistlib
import runpy
import signal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from njit_auditor import desktop_process, offline_app, offline_launcher
from njit_auditor.desktop_process import ProcessTree

ROOT = Path(__file__).parents[1]


def test_macos_storage_uses_private_application_support(monkeypatch, tmp_path):
    monkeypatch.setattr(offline_app.sys, "platform", "darwin")
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    root = offline_app.local_data_root()
    assert root == tmp_path / "Library/Application Support/NJIT Thesis Auditor"
    offline_app.prepare_local_storage(root)
    assert root.stat().st_mode & 0o777 == 0o700
    assert (root / "audits").stat().st_mode & 0o777 == 0o700
    assert (root / "tmp").stat().st_mode & 0o777 == 0o700


def test_native_menu_quit_and_window_close_use_supervisor(monkeypatch):
    import sys

    commands, bindings, protocols = {}, {}, {}
    fake_tk = SimpleNamespace(
        Label=lambda *a, **k: SimpleNamespace(pack=lambda **kw: None),
        Button=lambda *a, **k: SimpleNamespace(pack=lambda **kw: None),
    )
    monkeypatch.setitem(sys.modules, "tkinter", fake_tk)
    monkeypatch.setattr(offline_launcher.sys, "platform", "darwin")
    window = Mock()
    window.createcommand.side_effect = lambda key, fn: commands.update({key: fn})
    window.bind_all.side_effect = lambda key, fn: bindings.update({key: fn})
    window.protocol.side_effect = lambda key, fn: protocols.update({key: fn})
    request_quit, open_browser = Mock(return_value=True), Mock()
    offline_launcher._configure_window(window, Mock(), Mock(), open_browser, request_quit)
    commands["tk::mac::Quit"]()
    bindings["<Command-q>"](None)
    protocols["WM_DELETE_WINDOW"]()
    assert request_quit.call_count == 3
    commands["tk::mac::ReopenApplication"]()
    open_browser.assert_called_once()
    window.destroy.assert_not_called()


def test_macos_group_must_disappear_before_cleanup(monkeypatch):
    monkeypatch.setattr(desktop_process.sys, "platform", "darwin")
    process = Mock(pid=127654)
    killpg = Mock(side_effect=[None, None, ProcessLookupError()])
    monkeypatch.setattr(desktop_process.os, "killpg", killpg)
    tree = ProcessTree(process)
    tree.stop()
    assert killpg.call_args_list[0].args == (process.pid, signal.SIGKILL)
    assert killpg.call_args_list[-1].args == (process.pid, 0)
    process.wait.assert_called_once_with(timeout=2)
    assert tree._closed


def test_macos_retains_ownership_when_descendants_persist(monkeypatch):
    monkeypatch.setattr(desktop_process.sys, "platform", "darwin")
    monkeypatch.setattr(desktop_process.os, "killpg", Mock())
    clock = iter([0, 3])
    monkeypatch.setattr(desktop_process.time, "monotonic", lambda: next(clock))
    tree = ProcessTree(Mock(pid=127654))
    with pytest.raises(OSError, match="descendants did not stop"):
        tree.stop()
    assert not tree._closed


def test_mac_builder_rejects_non_native_hosts(monkeypatch):
    build = runpy.run_path(str(ROOT / "packaging/build_offline_macos.py"))
    monkeypatch.setattr(build["platform"], "system", lambda: "Linux")
    with pytest.raises(RuntimeError, match="native Mac"):
        build["require_native_mac"]("arm64")


def test_bundle_inspector_rejects_external_framework_link(monkeypatch, tmp_path):
    namespace = runpy.run_path(str(ROOT / "scripts/inspect_macos_bundle.py"))
    monkeypatch.setattr(namespace["platform"], "system", lambda: "Darwin")
    bundle = tmp_path / "Synthetic.app"
    resources = bundle / "Contents/Resources"
    for name in namespace["REQUIRED"]:
        path = resources / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("synthetic")
    (resources / "desktop-build-info.json").write_text(
        json.dumps({"system": "Darwin", "architecture": "arm64", "macos_build_version": "26.0"})
    )
    (bundle / "Contents/Info.plist").write_bytes(
        plistlib.dumps({"CFBundleExecutable": "Synthetic", "LSMinimumSystemVersion": "26.0"})
    )
    executable = bundle / "Contents/MacOS/Synthetic"
    executable.parent.mkdir()
    executable.write_bytes(b"synthetic")
    (bundle / "external-framework").symlink_to(tmp_path)
    with pytest.raises(ValueError, match="External bundle symlink"):
        namespace["inspect_bundle"](bundle, "arm64")


def test_missing_native_runtime_notices_stop_packaging(monkeypatch, tmp_path):
    import sys

    namespace = runpy.run_path(str(ROOT / "scripts/collect_macos_runtime_licenses.py"))
    runtime = SimpleNamespace(
        available=True,
        is_macos_system_framework=False,
        tcl_data_dir=str(tmp_path / "lib/tcl8.6"),
        tcl_shared_library=None,
        tcl_version=(8, 6),
    )
    monkeypatch.setitem(
        sys.modules, "PyInstaller.utils.hooks.tcl_tk", SimpleNamespace(tcltk_info=runtime)
    )
    monkeypatch.delenv("NJIT_MACOS_TCL_LICENSE", raising=False)
    with pytest.raises(RuntimeError, match="Missing tcl notice"):
        namespace["collect"](tmp_path)
    assert not (tmp_path / "NATIVE-RUNTIME-NOTICES.json").exists()


def test_native_runtime_notices_preserve_selected_version(monkeypatch, tmp_path):
    import sys

    namespace = runpy.run_path(str(ROOT / "scripts/collect_macos_runtime_licenses.py"))
    runtime = SimpleNamespace(
        available=True,
        is_macos_system_framework=False,
        tcl_data_dir=None,
        tcl_shared_library=None,
        tcl_version=(8, 6),
        tk_data_dir=None,
        tk_shared_library=None,
        tk_version=(8, 6),
    )
    monkeypatch.setitem(
        sys.modules, "PyInstaller.utils.hooks.tcl_tk", SimpleNamespace(tcltk_info=runtime)
    )
    for name in ("tcl", "tk"):
        notice = tmp_path / f"installed-{name}-license"
        notice.write_text(f"synthetic-{name}-notice")
        monkeypatch.setenv(f"NJIT_MACOS_{name.upper()}_LICENSE", str(notice))
    namespace["collect"](tmp_path)
    manifest = json.loads((tmp_path / "NATIVE-RUNTIME-NOTICES.json").read_text())
    assert [entry["name"] for entry in manifest] == ["tcl", "tk"]
    assert all(entry["version"] == [8, 6] for entry in manifest)
    assert (tmp_path / "tcl-LICENSE.txt").read_text() == "synthetic-tcl-notice"
    assert (tmp_path / "tk-LICENSE.txt").read_text() == "synthetic-tk-notice"
