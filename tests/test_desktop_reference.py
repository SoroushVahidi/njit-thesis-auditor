"""The pinned production oracle must be intact and complete before native parity."""

from __future__ import annotations

import json
import runpy
import shutil
import socket
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
API = runpy.run_path(str(ROOT / "scripts/desktop_reference.py"))
MANIFEST = ROOT / "tests/fixtures/desktop_reference/production-4efd780-v1.manifest.json"


def test_pinned_production_reference_unpacks_without_network(tmp_path, monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("Reference verification must not access the network")

    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(socket, "getaddrinfo", denied)
    reference = API["unpack"](MANIFEST, tmp_path / "verified")
    assert reference["source_commit"] == API["BASELINE"]
    assert set(reference["fixtures"]) == API["FIXTURE_NAMES"]
    assert API["load_reference"](tmp_path / "verified") == reference


@pytest.mark.parametrize("field", ["archive", "source_commit", "capture_url", "files"])
def test_corrupt_or_wrong_origin_artifact_rejected_before_extraction(tmp_path, field):
    manifest = json.loads(MANIFEST.read_text())
    archive = tmp_path / manifest["artifact"]
    shutil.copyfile(MANIFEST.parent / archive.name, archive)
    if field == "archive":
        archive.write_bytes(archive.read_bytes() + b"tampered")
    elif field == "files":
        manifest["files"]["reference.json"]["sha256"] = "0" * 64
    else:
        manifest[field] = "wrong origin"
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError):
        API["unpack"](manifest_path, tmp_path / "output")
    assert not (tmp_path / "output").exists()


@pytest.mark.parametrize(
    "change",
    [
        "missing_fixture",
        "missing_export",
        "missing_help",
        "wrong_version",
        "local_origin",
        "changed_pdf",
        "changed_expected_findings",
    ],
)
def test_incomplete_or_modified_evidence_is_rejected(tmp_path, change):
    directory = tmp_path / "reference"
    API["unpack"](MANIFEST, directory)
    payloads = {p.name: p.read_bytes() for p in directory.iterdir()}
    reference = json.loads(payloads["reference.json"])
    provenance = json.loads(payloads["provenance.json"])
    if change == "missing_fixture":
        del reference["fixtures"]["normal.pdf"]
    elif change == "missing_export":
        del reference["fixtures"]["normal.pdf"]["pdf/highlighted"]
    elif change == "missing_help":
        del reference["references"]["/help"]
    elif change == "wrong_version":
        provenance["version_after"]["commit"] = "0" * 40
    elif change == "local_origin":
        provenance["capture_url"] = "http://127.0.0.1:8000"
    elif change == "changed_pdf":
        payloads["normal.pdf"] += b"\nchanged"
    else:
        reference["fixtures"]["normal.pdf"]["download/json"]["findings"] = []
    payloads["reference.json"] = json.dumps(reference).encode()
    if change != "changed_expected_findings":
        # Even a rehashed manifest cannot hide missing coverage or wrong origin.
        provenance["payload_sha256"] = {
            name: API["digest"](data)
            for name, data in payloads.items()
            if name != "provenance.json"
        }
    payloads["provenance.json"] = json.dumps(provenance).encode()
    with pytest.raises(ValueError):
        API["verify_payloads"](payloads)


def test_verified_artifact_repack_preserves_all_evidence(tmp_path):
    API["unpack"](MANIFEST, tmp_path / "input")
    artifact = tmp_path / json.loads(MANIFEST.read_text())["artifact"]
    API["pack"](tmp_path / "input", artifact, tmp_path / "manifest.json")
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert manifest["files"] == json.loads(MANIFEST.read_text())["files"]
    assert API["unpack"](tmp_path / "manifest.json", tmp_path / "output") == API[
        "load_reference"
    ](tmp_path / "input")
