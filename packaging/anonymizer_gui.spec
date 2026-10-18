"""Build on Windows with: pyinstaller --noconfirm packaging/anonymizer_gui.spec."""

from pathlib import Path

from PyInstaller.utils.hooks import collect_all


ROOT = Path(SPECPATH).parent
editor_datas, editor_binaries, editor_hidden = collect_all("pdf_edit_engine")

analysis = Analysis(
    [str(ROOT / "src/njit_auditor/anonymizer_gui.py")],
    pathex=[str(ROOT / "src")],
    binaries=editor_binaries,
    datas=editor_datas,
    hiddenimports=editor_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "openpyxl", "njit_auditor.web_samples"],
    noarchive=False,
)
archive = PYZ(analysis.pure)
executable = EXE(
    archive, analysis.scripts, [], exclude_binaries=True,
    name="NJIT PDF Anonymizer", console=False,
)
COLLECT(
    executable, analysis.binaries, analysis.datas,
    name="NJIT PDF Anonymizer",
)
