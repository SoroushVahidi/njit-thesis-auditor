"""Synthetic bundle-content checks for the one-folder privacy gate."""

from pathlib import Path

from scripts.inspect_offline_bundle import EXPECTED, inspect_bundle


def test_bundle_inspector_finds_private_files_outside_allowlisted_resources(tmp_path: Path) -> None:
    internal = tmp_path / "_internal"
    for relative in EXPECTED:
        file = internal / relative
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(b"synthetic resource")
    assert inspect_bundle(tmp_path) == (set(), set(), set())

    private_pdf = internal / "third_party" / "synthetic-private.pdf"
    private_pdf.parent.mkdir(parents=True)
    private_pdf.write_bytes(b"synthetic, not a real dissertation")
    missing, extra, suspicious = inspect_bundle(tmp_path)
    assert not missing and not extra
    assert suspicious == {"_internal/third_party/synthetic-private.pdf"}
