"""One-folder build. Run from repository root: pyinstaller --noconfirm packaging/offline_desktop.spec."""

from pathlib import Path
import sys

ROOT = Path(SPECPATH).parent
TEMPLATES = (
    "_macros.html", "base.html", "help.html", "job.html",
    "problem_group.html", "rules.html",
)
DATA = [
    (str(ROOT / "src/njit_auditor/templates" / name), "src/njit_auditor/templates")
    for name in TEMPLATES
]
DATA += [
    (str(ROOT / "src/njit_auditor/offline_templates/index.html"),
     "src/njit_auditor/offline_templates"),
    (str(ROOT / "data/processed/rules/project_added_rules.json"), "data/processed/rules"),
    (str(ROOT / "data/specs/ester_warning_wording_map.json"), "data/specs"),
    (str(ROOT / "assets/fonts/DejaVuSans.ttf"), "assets/fonts"),
    (str(ROOT / "assets/fonts/DejaVu-LICENSE.txt"), "assets/fonts"),
]

a = Analysis(
    [str(ROOT / "src/njit_auditor/offline_launcher.py")],
    pathex=[str(ROOT / "src")],
    binaries=[],
    datas=DATA,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "njit_auditor.web_samples",
        "njit_auditor.web_url_fetch",
        "njit_auditor.review_ledger",
        "njit_auditor.specs",
        "openpyxl",
        "pytest",
    ],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True,
    name="NJIT Thesis Auditor", debug=False, bootloader_ignore_signals=False,
    strip=False, upx=False, console=sys.platform != "win32",
)
coll = COLLECT(
    exe, a.binaries, a.datas, strip=False, upx=False,
    name="NJIT Thesis Auditor",
)
