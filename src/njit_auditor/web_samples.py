"""Curated built-in sample PDF registry for the web audit UI."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent.parent


@dataclass(frozen=True)
class SampleInfo:
    sample_id: str
    label: str
    rel_path: str  # path relative to _REPO_ROOT
    public: bool = False

    @property
    def abs_path(self) -> Path:
        return (_REPO_ROOT / self.rel_path).resolve()


_CURATED: list[SampleInfo] = [
    SampleInfo(
        sample_id="synthetic_demo",
        label="Synthetic formatting demo",
        rel_path="tests/fixtures/web_demo/issues_pdf.pdf",
        public=True,
    ),
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


def list_builtin_samples() -> list[SampleInfo]:
    """Expose only public synthetic samples that exist on this server."""
    return [s for s in _CURATED if s.public and s.abs_path.exists() and s.abs_path.is_file()]


def get_builtin_sample(sample_id: str) -> SampleInfo:
    """Return SampleInfo for a known curated ID. Raises ValueError for unknowns."""
    if sample_id not in _BY_ID:
        raise ValueError(f"Unknown sample ID: {sample_id!r}")
    return _BY_ID[sample_id]


def copy_builtin_sample_to_job(sample_id: str, destination_path: Path) -> None:
    """Validate and copy a public sample PDF to destination_path."""
    info = get_builtin_sample(sample_id)
    if not info.public:
        raise ValueError("This sample is unavailable in the public web audit.")
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

