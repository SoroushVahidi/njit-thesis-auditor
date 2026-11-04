"""Package and verify captured synthetic production evidence without network access."""

from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import io
import json
from pathlib import Path

BASELINE = "4efd780dde53eea907a714df8bfed86e923ef86a"
PRODUCTION_URL = "http://128.235.41.222:8000"
FIXTURE_NAMES = {
    "structured.pdf",
    "normal.pdf",
    "rotated.pdf",
    "unicode.pdf",
    "annotated.pdf",
    "low-text.pdf",
}
EXPORTS = [
    "download/json",
    "download/markdown",
    "download/text",
    "download/student-report.pdf",
    "pdf",
    "pdf/highlighted",
    "highlighted-page.pdf?page=1",
]
FILES = FIXTURE_NAMES | {"reference.json", "provenance.json"}
MAX_EXPANDED_BYTES = 20 * 1024 * 1024


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def verify_payloads(payloads: dict[str, bytes]) -> dict:
    require(set(payloads) == FILES, "Reference file inventory is incomplete or unexpected")
    provenance = json.loads(payloads["provenance.json"])
    require(provenance["capture_url"] == PRODUCTION_URL, "Reference is not from production")
    require(provenance["capture_kind"] == "live-production-http", "Wrong reference origin")
    for key in ("version_before", "version_after"):
        require(provenance[key]["commit"] == BASELINE, "Production source version mismatch")
        require(provenance[key]["environment"] == "production", "Not a production capture")
    require(bool(provenance["captured_at_utc"]), "Missing capture time")
    require(len(provenance["capture_tool_sha256"]) == 64, "Missing capture tool identity")
    expected_hashes = {name: digest(payloads[name]) for name in FILES - {"provenance.json"}}
    require(provenance["payload_sha256"] == expected_hashes, "Captured payload hash mismatch")
    reference = json.loads(payloads["reference.json"])
    require(reference["source_commit"] == BASELINE, "Reference source version mismatch")
    require(set(reference["fixtures"]) == FIXTURE_NAMES, "Incomplete fixture coverage")
    require(set(reference["references"]) == {"/help", "/rules"}, "Missing Help/Rule Reference")
    require(all(reference["references"].values()), "Empty Help/Rule Reference")
    for name, snapshot in reference["fixtures"].items():
        require(payloads[name].startswith(b"%PDF-"), f"Invalid PDF input: {name}")
        require(snapshot["pdf"] == digest(payloads[name]), f"Original PDF mismatch: {name}")
        require(
            set(snapshot) == set(EXPORTS) | {"finding_cards", "groups"},
            f"Missing exports/findings: {name}",
        )
        require(
            set(snapshot["download/json"])
            == {"metadata", "grouped_summary", "grouped_findings", "findings"},
            f"Incomplete audit JSON: {name}",
        )
        for key in (
            "download/markdown",
            "download/text",
            "download/student-report.pdf",
            "pdf/highlighted",
            "highlighted-page.pdf?page=1",
        ):
            require(bool(snapshot[key]), f"Empty export {key}: {name}")
    return reference


def load_reference(directory: Path) -> dict:
    return verify_payloads({name: (directory / name).read_bytes() for name in FILES})


def pack(directory: Path, artifact: Path, manifest_path: Path) -> None:
    payloads = {name: (directory / name).read_bytes() for name in FILES}
    verify_payloads(payloads)
    encoded = {
        name: base64.b64encode(data).decode("ascii") for name, data in sorted(payloads.items())
    }
    buffer = io.BytesIO()
    with gzip.GzipFile(filename="", fileobj=buffer, mode="wb", mtime=0) as stream:
        stream.write(json.dumps(encoded, sort_keys=True).encode())
    archive = buffer.getvalue()
    manifest = {
        "format_version": 1,
        "artifact": artifact.name,
        "source_commit": BASELINE,
        "capture_url": PRODUCTION_URL,
        "size_bytes": len(archive),
        "sha256": digest(archive),
        "files": {
            name: {"size_bytes": len(data), "sha256": digest(data)}
            for name, data in sorted(payloads.items())
        },
    }
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_bytes(archive)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def unpack(manifest_path: Path, output: Path) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    require(manifest["format_version"] == 1, "Unsupported reference format")
    require(manifest["source_commit"] == BASELINE, "Manifest source version mismatch")
    require(manifest["capture_url"] == PRODUCTION_URL, "Manifest origin mismatch")
    name = manifest["artifact"]
    require(
        Path(name).name == name and "/" not in name and "\\" not in name,
        "Invalid artifact filename",
    )
    artifact = manifest_path.parent / name
    archive = artifact.read_bytes()
    require(
        len(archive) == manifest["size_bytes"] and digest(archive) == manifest["sha256"],
        "Reference artifact size/SHA-256 mismatch",
    )
    with gzip.open(artifact, "rb") as stream:
        expanded = stream.read(MAX_EXPANDED_BYTES + 1)
    require(len(expanded) <= MAX_EXPANDED_BYTES, "Reference artifact exceeds size limit")
    encoded = json.loads(expanded)
    require(
        set(encoded) == FILES and set(manifest["files"]) == FILES,
        "Reference file inventory is incomplete or unexpected",
    )
    payloads = {name: base64.b64decode(value, validate=True) for name, value in encoded.items()}
    for name, data in payloads.items():
        require(
            manifest["files"][name] == {"size_bytes": len(data), "sha256": digest(data)},
            f"Reference member size/SHA-256 mismatch: {name}",
        )
    reference = verify_payloads(payloads)
    # No output is written until integrity, origin and coverage checks all pass.
    output.mkdir(parents=True, exist_ok=False)
    for name, data in payloads.items():
        (output / name).write_bytes(data)
    return reference


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    package = sub.add_parser("pack")
    package.add_argument("--directory", type=Path, required=True)
    package.add_argument("--artifact", type=Path, required=True)
    package.add_argument("--manifest", type=Path, required=True)
    verify = sub.add_parser("unpack")
    verify.add_argument("--manifest", type=Path, required=True)
    verify.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "pack":
        pack(args.directory, args.artifact, args.manifest)
    else:
        unpack(args.manifest, args.output)
    print(f"Verified six production fixtures, exports and references at {BASELINE}")


if __name__ == "__main__":
    main()
