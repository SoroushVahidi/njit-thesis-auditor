"""One-folder build. Run from repository root: pyinstaller --noconfirm packaging/offline_desktop.spec."""

from pathlib import Path
import sys
import json
import platform
import subprocess
import runpy
from PyInstaller.config import CONF
from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(SPECPATH).parent
sys.path.insert(0, str(ROOT / "src"))
from njit_auditor.desktop_metadata import DESKTOP_VERSION, FILE_VERSION

resources = Path(CONF["workpath"]) / "desktop-resources"
resources.mkdir(parents=True, exist_ok=True)
collect_notices = runpy.run_path(str(ROOT / "scripts/collect_desktop_licenses.py"))["collect"]
collect_notices(resources / "third-party-licenses")
commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
(resources / "desktop-build-info.json").write_text(json.dumps({
    "version": DESKTOP_VERSION, "commit": commit,
    "system": platform.system(), "architecture": platform.machine(),
    "python": platform.python_version(),
}), encoding="utf-8")
version_file = resources / "windows-version.txt"
version_file.write_text(f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={FILE_VERSION!r}, prodvers={FILE_VERSION!r},
    mask=0x3f, flags=0, OS=0x40004, fileType=1, subtype=0, date=(0, 0)),
  kids=[StringFileInfo([StringTable('040904B0', [
    StringStruct('CompanyName', 'Soroush Vahidi'),
    StringStruct('FileDescription', 'NJIT Thesis Auditor — local PDF auditing'),
    StringStruct('FileVersion', '{DESKTOP_VERSION}'),
    StringStruct('ProductVersion', '{DESKTOP_VERSION}'),
    StringStruct('ProductName', 'NJIT Thesis Auditor'),
    StringStruct('OriginalFilename', 'NJIT Thesis Auditor.exe')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])])""", encoding="utf-8")
TEMPLATES = (
    "_macros.html", "base.html", "help.html", "job.html",
    "problem_group.html", "rules.html",
)
DATA = [
    (str(ROOT / "src/njit_auditor/templates" / name), "src/njit_auditor/templates")
    for name in TEMPLATES
]
DATA += [
    (str(resources / "desktop-build-info.json"), "."),
    (str(resources / "third-party-licenses"), "third-party-licenses"),
    (str(ROOT / "assets/icons/njit-auditor.ico"), "assets/icons"),
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
    hiddenimports=collect_submodules("njit_auditor.rules") + ["njit_auditor.desktop_worker"] + (["msvcrt"] if sys.platform == "win32" else []),
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
    icon=str(ROOT / "assets/icons/njit-auditor.ico") if sys.platform == "win32" else None,
    version=str(version_file) if sys.platform == "win32" else None,
)
coll = COLLECT(
    exe, a.binaries, a.datas, strip=False, upx=False,
    name="NJIT Thesis Auditor",
)
