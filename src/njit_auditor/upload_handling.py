"""Safe upload classification, validation, and ZIP extraction for the web GUI."""

from __future__ import annotations

import re
import stat
import zipfile
from enum import Enum
from pathlib import Path, PurePosixPath

DEFAULT_MAX_UPLOAD_BYTES = 50 * 1024 * 1024
DEFAULT_MAX_ZIP_FILES = 500
DEFAULT_MAX_ZIP_UNCOMPRESSED_BYTES = 200 * 1024 * 1024
DEFAULT_MAX_ZIP_SINGLE_FILE_BYTES = 50 * 1024 * 1024

ALLOWED_ZIP_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".tex",
        ".bib",
        ".cls",
        ".sty",
        ".bst",
        ".png",
        ".jpg",
        ".jpeg",
        ".pdf",
        ".eps",
        ".txt",
    }
)

PREFERRED_MAIN_TEX_NAMES: tuple[str, ...] = ("main.tex", "thesis.tex", "dissertation.tex")

_SAFE_NAME_RE = re.compile(r"[^a-zA-Z0-9._-]")


class UploadKind(str, Enum):
    """Supported upload categories for audit dispatch."""

    PDF = "pdf"
    TEX = "tex"
    ZIP = "zip"
    UNSUPPORTED = "unsupported"


class UploadValidationError(Exception):
    """Raised when an upload fails validation."""


class ZipExtractionError(Exception):
    """Raised when a ZIP archive cannot be safely extracted."""


class MainTexDetectionError(Exception):
    """Raised when main.tex cannot be determined unambiguously."""


def sanitize_upload_filename(name: str, *, default_ext: str = "") -> str:
    """Return a filesystem-safe basename preserving a known extension."""
    base = Path(name).name
    stem = Path(base).stem
    ext = Path(base).suffix.lower()
    safe_stem = _SAFE_NAME_RE.sub("_", stem)[:80] or "upload"
    if ext:
        return f"{safe_stem}{ext}"
    if default_ext:
        return f"{safe_stem}{default_ext}"
    return safe_stem


def classify_upload(path: Path) -> UploadKind:
    """Classify an on-disk upload by extension (caller validates magic bytes separately)."""
    if not path.is_file():
        msg = "The uploaded file is unavailable or is not a regular file."
        raise UploadValidationError(msg)

    ext = path.suffix.lower()
    if ext == ".pdf":
        return UploadKind.PDF
    if ext == ".tex":
        return UploadKind.TEX
    if ext == ".zip":
        return UploadKind.ZIP
    return UploadKind.UNSUPPORTED


def _validate_pdf_magic(path: Path) -> None:
    header = path.read_bytes()[:8]
    if len(header) < 4 or not header.startswith(b"%PDF"):
        msg = "File does not appear to be a valid PDF."
        raise UploadValidationError(msg)


def _validate_zip_magic(path: Path) -> None:
    if not zipfile.is_zipfile(path):
        msg = "File does not appear to be a valid ZIP archive."
        raise UploadValidationError(msg)


def _validate_tex_content(path: Path) -> None:
    try:
        sample = path.read_text(encoding="utf-8", errors="strict")[:8192]
    except UnicodeDecodeError as exc:
        msg = "TeX file is not valid UTF-8 text."
        raise UploadValidationError(msg) from exc
    if "\x00" in sample:
        msg = "TeX file contains binary content."
        raise UploadValidationError(msg)


def validate_upload_path(
    path: Path,
    max_size_bytes: int = DEFAULT_MAX_UPLOAD_BYTES,
    *,
    expected_kind: UploadKind | None = None,
) -> UploadKind:
    """Validate upload size/type and return the classified kind."""
    if not path.is_file():
        msg = "The uploaded file is unavailable or is not a regular file."
        raise UploadValidationError(msg)

    size = path.stat().st_size
    if size > max_size_bytes:
        msg = f"File exceeds maximum size of {max_size_bytes} bytes."
        raise UploadValidationError(msg)
    if size == 0:
        msg = "File is empty."
        raise UploadValidationError(msg)

    kind = classify_upload(path)
    if expected_kind is not None and kind != expected_kind:
        msg = f"Expected {expected_kind.value} upload, got {kind.value}."
        raise UploadValidationError(msg)
    if kind == UploadKind.UNSUPPORTED:
        msg = f"Unsupported file type: {path.suffix or '(no extension)'}"
        raise UploadValidationError(msg)

    if kind == UploadKind.PDF:
        if size < 8:
            msg = "PDF file is too small."
            raise UploadValidationError(msg)
        _validate_pdf_magic(path)
    elif kind == UploadKind.ZIP:
        _validate_zip_magic(path)
    elif kind == UploadKind.TEX:
        _validate_tex_content(path)

    return kind


def _is_safe_zip_member(name: str) -> bool:
    if name.startswith("/") or name.startswith("\\"):
        return False
    pure = PurePosixPath(name)
    if pure.is_absolute():
        return False
    return ".." not in pure.parts


def _normalize_zip_member_path(name: str) -> str:
    """Return a canonical relative path for duplicate-detection purposes.

    PurePosixPath strips leading './' and collapses redundant separators so
    that 'main.tex' and './main.tex' compare as equal.
    """
    return str(PurePosixPath(name))


def safe_extract_zip(
    zip_path: Path,
    dest_dir: Path,
    *,
    max_files: int = DEFAULT_MAX_ZIP_FILES,
    max_total_uncompressed_bytes: int = DEFAULT_MAX_ZIP_UNCOMPRESSED_BYTES,
    max_single_file_bytes: int = DEFAULT_MAX_ZIP_SINGLE_FILE_BYTES,
    allowed_extensions: frozenset[str] = ALLOWED_ZIP_EXTENSIONS,
) -> list[Path]:
    """Extract a ZIP archive safely into dest_dir.

    Returns paths of extracted files. Raises ZipExtractionError on unsafe content.
    """
    if not zipfile.is_zipfile(zip_path):
        msg = "Not a valid ZIP archive."
        raise ZipExtractionError(msg)

    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_resolved = dest_dir.resolve()
    extracted: list[Path] = []
    total_uncompressed = 0
    seen_paths: set[str] = set()

    with zipfile.ZipFile(zip_path) as zf:
        members = [info for info in zf.infolist() if not info.is_dir()]
        if len(members) > max_files:
            msg = f"ZIP contains too many files ({len(members)} > {max_files})."
            raise ZipExtractionError(msg)

        for info in members:
            if not _is_safe_zip_member(info.filename):
                msg = f"Unsafe ZIP path: {info.filename}"
                raise ZipExtractionError(msg)

            # Reject Unix symlink entries by inspecting external file attributes.
            unix_mode = info.external_attr >> 16
            if stat.S_ISLNK(unix_mode):
                msg = f"ZIP symlink entries are not allowed: {info.filename}"
                raise ZipExtractionError(msg)

            normalized = _normalize_zip_member_path(info.filename)
            if normalized in seen_paths:
                msg = f"ZIP contains duplicate member path: {info.filename}"
                raise ZipExtractionError(msg)
            seen_paths.add(normalized)

            ext = Path(info.filename).suffix.lower()
            if ext and ext not in allowed_extensions:
                msg = f"Disallowed file type in ZIP: {info.filename}"
                raise ZipExtractionError(msg)

            if info.file_size > max_single_file_bytes:
                msg = f"ZIP member exceeds single-file size limit: {info.filename}"
                raise ZipExtractionError(msg)

            total_uncompressed += info.file_size
            if total_uncompressed > max_total_uncompressed_bytes:
                msg = "ZIP uncompressed size exceeds limit."
                raise ZipExtractionError(msg)

            target = (dest_dir / info.filename).resolve()
            if not str(target).startswith(str(dest_resolved)):
                msg = f"ZIP path escapes destination directory: {info.filename}"
                raise ZipExtractionError(msg)

            zf.extract(info, path=dest_dir)
            extracted.append(target)

    return extracted


def detect_main_tex(project_dir: Path) -> Path:
    """Detect the main TeX file in an extracted project directory.

    Raises MainTexDetectionError when no candidate or multiple ambiguous candidates exist.
    """
    if not project_dir.is_dir():
        msg = f"Not a directory: {project_dir}"
        raise MainTexDetectionError(msg)

    candidates: list[Path] = []
    for tex_path in sorted(project_dir.rglob("*.tex")):
        if not tex_path.is_file():
            continue
        try:
            text = tex_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if r"\documentclass" in text:
            candidates.append(tex_path)

    if not candidates:
        msg = "No .tex file containing \\documentclass was found."
        raise MainTexDetectionError(msg)

    for preferred in PREFERRED_MAIN_TEX_NAMES:
        matches = [c for c in candidates if c.name.lower() == preferred]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            msg = f"Multiple {preferred} files found; cannot determine main TeX file."
            raise MainTexDetectionError(msg)

    if len(candidates) == 1:
        return candidates[0]

    shallowest_depth = min(len(c.relative_to(project_dir).parts) for c in candidates)
    shallow = [c for c in candidates if len(c.relative_to(project_dir).parts) == shallowest_depth]
    if len(shallow) == 1:
        return shallow[0]

    msg = "Multiple \\documentclass candidates found; main TeX file is ambiguous."
    raise MainTexDetectionError(msg)
