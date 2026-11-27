"""Curated built-in sample PDF registry for the web audit UI."""

from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent.parent


@dataclass(frozen=True)
class SampleInfo:
    sample_id: str
    label: str
    rel_path: str  # path relative to _REPO_ROOT

    @property
    def abs_path(self) -> Path:
        return (_REPO_ROOT / self.rel_path).resolve()


_CURATED: list[SampleInfo] = [
    SampleInfo(
        sample_id="ester_sample_a",
        label="Sample A ? first review (EF-annotated)",
        rel_path="data/raw/ester/250218 Cibaku Elson First Review.pdf",
    ),
    SampleInfo(
        sample_id="ester_sample_b",
        label="Sample B ? second review with EF feedback",
        rel_path="data/raw/ester/Yin_Haotian_Second_R_with_EF_Feedback.pdf",
    ),
    SampleInfo(
        sample_id="ester_sample_c",
        label="Sample C ? second review with EF comments",
        rel_path="data/raw/ester/260415 Yin H _2nd_review with EF Comments.pdf",
    ),
    SampleInfo(
        sample_id="ester_sample_d",
        label="Sample D ? fourth review compressed (EF-annotated)",
        rel_path="data/raw/ester/Yin_H_4th_Review_with_EF_comments_compressed.pdf",
    ),
]

_BY_ID: dict[str, SampleInfo] = {s.sample_id: s for s in _CURATED}

# These four exact files were the public website's historical sample choices.
# Pin their bytes so the download route cannot expose a different fixture under
# a familiar sample ID if the source files change later.
_PUBLIC_SAMPLE_SHA256 = {
    "ester_sample_a": "234f6c951a2a6a07308a771af434628658ddc84f9684c54e51f6c9423ac6d6ad",
    "ester_sample_b": "dccea83030fe01c90d996ff3a1b901e2d56eaac6fe06ba51eea7c884bfc6d56b",
    "ester_sample_c": "dbfdc9b820c46cf10570d802911c92b1b5ed31583a72f59cfadf2b5286e31eee",
    "ester_sample_d": "cbf4497727dc106cd8c26e5f0c6786a45b6c5df42405254796e164200690e209",
}


def list_builtin_samples() -> list[SampleInfo]:
    """Return curated samples that currently exist as local PDF files."""
    return [s for s in _CURATED if s.abs_path.exists() and s.abs_path.is_file()]


def get_builtin_sample(sample_id: str) -> SampleInfo:
    """Return SampleInfo for a known curated ID. Raises ValueError for unknowns."""
    if sample_id not in _BY_ID:
        raise ValueError(f"Unknown sample ID: {sample_id!r}")
    return _BY_ID[sample_id]


def get_public_sample(sample_id: str) -> SampleInfo:
    """Return only an unchanged, historically public website sample PDF."""
    if sample_id not in _PUBLIC_SAMPLE_SHA256:
        raise ValueError("Unknown public sample ID.")
    info = get_builtin_sample(sample_id)
    src = info.abs_path
    try:
        src.relative_to(_REPO_ROOT.resolve())
    except ValueError:
        raise ValueError("Sample path escapes repository root.") from None
    if not src.is_file():
        raise FileNotFoundError("Public sample is unavailable.")
    digest = hashlib.sha256()
    with src.open("rb") as pdf:
        if pdf.read(4) != b"%PDF":
            raise ValueError("Public sample is not a PDF.")
        pdf.seek(0)
        for chunk in iter(lambda: pdf.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != _PUBLIC_SAMPLE_SHA256[sample_id]:
        raise ValueError("Public sample does not match the approved version.")
    return info


def read_public_sample(sample_id: str, max_bytes: int) -> tuple[SampleInfo, bytes]:
    """Return only the exact approved PDF bytes, bounded by the upload limit.

    Recheck the bytes after reading: the source could change between the registry
    check and the copy into an audit job.
    """
    info = get_public_sample(sample_id)
    with info.abs_path.open("rb") as pdf:
        content = pdf.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise ValueError("Sample exceeds the upload size limit.")
    if hashlib.sha256(content).hexdigest() != _PUBLIC_SAMPLE_SHA256[sample_id]:
        raise ValueError("Public sample does not match the approved version.")
    return info, content


def copy_builtin_sample_to_job(sample_id: str, destination_path: Path) -> None:
    """Validate and copy the sample PDF to destination_path."""
    info = get_builtin_sample(sample_id)
    src = info.abs_path

    # Defense-in-depth: verify resolved path stays under repo root.
    repo = _REPO_ROOT.resolve()
    try:
        src.relative_to(repo)
    except ValueError:
        raise ValueError("Sample path escapes repository root.") from None

    if not src.exists():
        raise FileNotFoundError("Sample file not found on this server.")

    with src.open("rb") as f:
        header = f.read(4)
    if header != b"%PDF":
        raise ValueError("Sample file is not a valid PDF.")

    shutil.copy2(src, destination_path)

