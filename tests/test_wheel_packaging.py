"""Build and install real distributions without consulting checkout resources."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import venv
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
JSON_RESOURCES = (
    "data/processed/rules/project_added_rules.json",
    "data/specs/ester_warning_wording_map.json",
    "data/specs/ester_q_matrix.json",
    "data/specs/ester_q_current_authority_overlay.json",
)
TEMPLATES = (
    "_macros.html", "base.html", "help.html", "index.html",
    "job.html", "problem_group.html", "rules.html",
)


def run(*command: str, cwd: Path, env: dict[str, str]) -> str:
    result = subprocess.run(
        command, cwd=cwd, env=env, capture_output=True, text=True, timeout=150,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


def test_built_distributions_install_with_local_runtime_resources(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    for name in ("pyproject.toml", "README.md", "LICENSE", "setup.py", "MANIFEST.in"):
        if (ROOT / name).exists():
            shutil.copy2(ROOT / name, source / name)
    shutil.copytree(
        ROOT / "src", source / "src",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.egg-info"),
    )
    for name in JSON_RESOURCES:
        target = source / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, target)
    # Synthetic canaries exercise exclusion rules without reading private material.
    for name in (
        "data/raw/ester/private.pdf", "data/evaluation/private/corpus.pdf",
        "notes/development.log", ".env", "tests/fixtures/unneeded.pdf",
        "src/njit_auditor/credentials.json", "src/njit_auditor/debug.log",
        "src/njit_auditor/templates/unneeded.html",
        "data/specs/unneeded.json",
    ):
        target = source / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("SYNTHETIC_UNWANTED_PACKAGE_CANARY", encoding="utf-8")
    # Do not pass unrelated credentials into build/install/runtime subprocesses.
    env = {key: os.environ[key] for key in (
        "PATH", "HOME", "SYSTEMROOT", "TEMP", "TMP", "TMPDIR",
        "SSL_CERT_FILE", "REQUESTS_CA_BUNDLE", "PIP_NO_INDEX", "PIP_FIND_LINKS",
        "PIP_CACHE_DIR",
    ) if key in os.environ}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    dist = tmp_path / "dist"
    # build's default also builds the wheel from the newly generated sdist.
    run(sys.executable, "-m", "build", "--outdir", str(dist), str(source),
        cwd=tmp_path, env=env)
    expected = {
        f"njit_auditor/{name}": (ROOT / name).read_bytes() for name in JSON_RESOURCES
    } | {
        f"njit_auditor/templates/{name}":
        (ROOT / "src/njit_auditor/templates" / name).read_bytes() for name in TEMPLATES
    }
    wheel = next(dist.glob("*.whl"))
    with zipfile.ZipFile(wheel) as archive:
        members = archive.namelist()
        data_members = {name for name in members if name.startswith("njit_auditor/")
                        and not name.endswith(".py")}
        assert data_members == set(expected)
        for name, content in expected.items():
            assert archive.read(name) == content
        metadata = {name.split("/", 1)[0] for name in members if ".dist-info/" in name}
        assert len(metadata) == 1
        assert all(name.startswith(("njit_auditor/", next(iter(metadata)) + "/"))
                   for name in members)
        assert all(b"SYNTHETIC_UNWANTED_PACKAGE_CANARY" not in archive.read(name)
                   for name in members)
    with tarfile.open(next(dist.glob("*.tar.gz"))) as archive:
        for member in archive.getmembers():
            if member.isfile():
                file = archive.extractfile(member)
                assert file is not None
                assert b"SYNTHETIC_UNWANTED_PACKAGE_CANARY" not in file.read()
    clean = tmp_path / "venv"
    venv.EnvBuilder(with_pip=True).create(clean)
    python = clean / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    assert "include-system-site-packages = false" in (clean / "pyvenv.cfg").read_text()
    run(str(python), "-m", "pip", "install", str(wheel), "httpx", cwd=tmp_path, env=env)
    run(str(python), "-m", "pip", "check", cwd=tmp_path, env=env)
    cli = clean / ("Scripts/njit-audit.exe" if os.name == "nt" else "bin/njit-audit")
    run(str(cli), "--help", cwd=tmp_path, env=env)
    installed_check = (
        "import pathlib,sys,hashlib,json,njit_auditor; "
        "p=pathlib.Path(njit_auditor.__file__).parent; "
        "assert p.is_relative_to(pathlib.Path(sys.prefix)); "
        "print(json.dumps({str(f.relative_to(p)):hashlib.sha256(f.read_bytes()).hexdigest() "
        "for f in p.rglob('*') if f.is_file() and f.suffix in {'.html','.json'}}))"
    )
    installed = json.loads(run(str(python), "-I", "-c", installed_check, cwd=tmp_path, env=env))
    assert installed == {name.removeprefix("njit_auditor/"): hashlib.sha256(data).hexdigest()
                         for name, data in expected.items()}
    probe = ROOT / "tests/wheel_runtime_probe.py"
    snapshot = tmp_path / "snapshot.json"
    run(sys.executable, str(probe), str(snapshot), "--source", str(ROOT),
        cwd=tmp_path, env=env)
    source_snapshot = json.loads(snapshot.read_text())
    # Remove the staged build input to prevent any accidental resource fallback to it.
    shutil.rmtree(source)
    run(str(python), "-I", str(probe), str(snapshot), cwd=tmp_path, env=env)
    assert json.loads(snapshot.read_text()) == source_snapshot


def test_resource_paths_preserve_source_and_frozen_layouts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    from njit_auditor.resource_paths import resource_path, resource_root

    assert resource_root() == ROOT
    assert resource_path(*JSON_RESOURCES[0].split("/")) == ROOT / JSON_RESOURCES[0]
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert resource_root() == tmp_path
    assert resource_path(*JSON_RESOURCES[0].split("/")) == tmp_path / JSON_RESOURCES[0]
