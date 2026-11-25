"""Validate and publish closed PDFs on the destination filesystem."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import Concatenate, ParamSpec, TypeVar

import fitz

P = ParamSpec("P")
T = TypeVar("T")


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pdf_signature(source: Path | None, payload: object) -> str:
    encoded = json.dumps(
        [file_digest(source) if source is not None else None, payload],
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(encoded.encode()).hexdigest()


def complete_pdf(path: Path, *, pages: int | None = None) -> bool:
    """Reject incomplete or repairable output in the rendering process."""
    try:
        if path.is_symlink():
            return False
        with path.open("rb") as stream:
            stream.seek(max(0, stream.seek(0, os.SEEK_END) - 1024))
            if not stream.read().rstrip().endswith(b"%%EOF"):
                return False
        with fitz.open(path) as document:
            if not document.is_pdf or document.is_repaired or document.page_count < 1:
                return False
            if pages is not None and document.page_count != pages:
                return False
            for page in document:
                _ = page.rect
        return True
    except (OSError, ValueError, RuntimeError):
        return False


def atomic_pdf_output(
    builder: Callable[Concatenate[Path, Path, P], T],
) -> Callable[Concatenate[Path, Path, P], T]:
    """Generate into a private temporary directory and atomically replace output."""

    @wraps(builder)
    def write(source_pdf: Path, output_pdf: Path, *args: P.args, **kwargs: P.kwargs) -> T:
        output_pdf.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".pdf-write-", dir=output_pdf.parent) as name:
            temporary = Path(name) / "output.pdf"
            result = builder(source_pdf, temporary, *args, **kwargs)
            if temporary.exists():
                if not complete_pdf(temporary):
                    raise ValueError("Incomplete PDF export")
                os.replace(temporary, output_pdf)
            return result

    return write
