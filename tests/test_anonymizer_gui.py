"""Headless checks for the Windows-usable local file-picker path."""

from __future__ import annotations

import sys
import types
from pathlib import Path

from njit_auditor import anonymizer_gui


def test_file_picker_uses_separate_output_and_verifies_auditor(
    monkeypatch, tmp_path: Path
) -> None:
    source = tmp_path / "synthetic-source.pdf"
    source.write_bytes(b"synthetic original sentinel")
    destination = tmp_path / "synthetic-output.pdf"
    dialogs: list[tuple[str, str]] = []

    class Root:
        def withdraw(self) -> None:
            pass

        def destroy(self) -> None:
            pass

    fake_tk = types.ModuleType("tkinter")
    fake_tk.Tk = Root  # type: ignore[attr-defined]
    fake_tk.filedialog = types.SimpleNamespace(  # type: ignore[attr-defined]
        askopenfilename=lambda **_kwargs: str(source),
        asksaveasfilename=lambda **_kwargs: str(destination),
    )
    fake_tk.messagebox = types.SimpleNamespace(  # type: ignore[attr-defined]
        showinfo=lambda title, message, **_kwargs: dialogs.append((title, message)),
        showerror=lambda title, message, **_kwargs: dialogs.append((title, message)),
    )
    monkeypatch.setitem(sys.modules, "tkinter", fake_tk)

    def fake_anonymize(input_path: Path, output_path: Path, **kwargs: object) -> dict[str, int]:
        assert input_path == source
        assert output_path == destination
        assert kwargs == {"authorized": True, "verify_auditor": True}
        destination.write_bytes(b"synthetic output")
        return {"pages": 1}

    monkeypatch.setattr(anonymizer_gui, "anonymize", fake_anonymize)
    anonymizer_gui.select_and_anonymize()
    assert source.read_bytes() == b"synthetic original sentinel"
    assert destination.read_bytes() == b"synthetic output"
    assert dialogs[0][0] == "Anonymization complete"
