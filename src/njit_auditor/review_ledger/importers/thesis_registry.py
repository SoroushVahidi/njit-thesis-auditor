"""Maps the private evaluation corpus's document short names to ledger
``Thesis``/``ThesisVersion`` records.

Reuses the exact corpus list and private-data path convention already
established in ``scripts/ester_batch/lib.py`` (``DOCS``,
``PRIVATE_DATA_DIR``) rather than inventing a second one. Elbert is
excluded, matching that existing convention -- see
``docs/status/CURRENT_STATUS.md``'s "Current Evaluation Corpus" section.

Nothing here reads dissertation body text; only the file's bytes (for a
SHA-256 content hash) and its short display name (already a
non-identifying alias by existing project convention -- these are the
same seven short names already used throughout
``docs/evaluation/ester_feedback/*.xlsx`` and every dated status doc).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from njit_auditor.review_ledger.identifiers import make_thesis_id, make_thesis_version_id
from njit_auditor.review_ledger.models import Thesis, ThesisVersion
from njit_auditor.review_ledger.store import EsterReviewLedger

PRIVATE_DATA_DIR = Path("/home/soroush/njit-thesis-auditor/main/data/evaluation/private")

# Matches scripts/ester_batch/lib.py's DOCS exactly (Elbert excluded).
CORPUS_DOCUMENTS: tuple[tuple[str, str], ...] = (
    ("Philip", "Philip_Zaleski_Thesis_Revised (1).pdf"),
    ("Muyeed", "Muyeed_Dissertation (4).pdf"),
    ("Anthony", "Anthony.Sena 3rd Review Draft.pdf"),
    ("Praneeth", "Praneeth Ivan Joel. FNU_3rd review draft.pdf"),
    ("Patrick", "Thesis Patrick Grice July 22.pdf"),
    ("Youra", "5_Youra_Shin_PhD_Dissertation_Document_3rd review.pdf"),
    ("Sebastian", "Sebastian.Fine Revised 1st Dissertation Draft_Revision3.pdf"),
)


@dataclass(frozen=True)
class RegisteredDocument:
    short_name: str
    pdf_path: Path
    thesis_id: str
    thesis_version_id: str
    sha256: str
    available: bool


def sha256_of_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def register_corpus(
    ledger: EsterReviewLedger,
    *,
    first_seen_at: str,
    private_data_dir: Path = PRIVATE_DATA_DIR,
) -> list[RegisteredDocument]:
    """Ensure a ``Thesis``/current ``ThesisVersion`` exists for every corpus
    document whose PDF is actually present on disk right now.

    A document whose PDF file is missing is still returned (with
    ``available=False``) so callers can report it, but no ``Thesis``/
    ``ThesisVersion`` row is created for it -- there is nothing to hash.
    Safe to call repeatedly: an existing ``Thesis``/``ThesisVersion`` with
    the same deterministic id is detected and reused, not re-added.
    """
    registered: list[RegisteredDocument] = []
    for short_name, filename in CORPUS_DOCUMENTS:
        pdf_path = private_data_dir / filename
        thesis_id = make_thesis_id(short_name)

        if thesis_id not in ledger.theses:
            ledger.add_thesis(Thesis(thesis_id=thesis_id, display_label=short_name))

        if not pdf_path.exists():
            registered.append(
                RegisteredDocument(
                    short_name=short_name,
                    pdf_path=pdf_path,
                    thesis_id=thesis_id,
                    thesis_version_id="",
                    sha256="",
                    available=False,
                )
            )
            continue

        sha256 = sha256_of_file(pdf_path)
        thesis_version_id = make_thesis_version_id(thesis_id, sha256)
        if thesis_version_id not in ledger.thesis_versions:
            ledger.add_thesis_version(
                ThesisVersion(
                    thesis_version_id=thesis_version_id,
                    thesis_id=thesis_id,
                    sha256=sha256,
                    source_format="pdf",
                    page_count=None,
                    first_seen_at=first_seen_at,
                    current=True,
                )
            )
        registered.append(
            RegisteredDocument(
                short_name=short_name,
                pdf_path=pdf_path,
                thesis_id=thesis_id,
                thesis_version_id=thesis_version_id,
                sha256=sha256,
                available=True,
            )
        )
    return registered
