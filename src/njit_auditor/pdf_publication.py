"""Publish closed, validated PDFs on the destination filesystem."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import Any, TypeVar

import fitz

T = TypeVar("T")


def complete_pdf(path: Path) -> bool:
    """Reject missing, truncated and repairable PDFs, including old partial caches.

    Call only in the rendering process, never in a desktop supervisor thread.
    """
    try:
        with path.open("rb") as stream:
            stream.seek(max(0, path.stat().st_size - 1024))
            if not stream.read().rstrip().endswith(b"%%EOF"):
                return False
        with fitz.open(path) as document:
            if not document.is_pdf or document.is_repaired or document.page_count < 1:
                return False
            for page in document:
                # Force page-tree access before accepting the complete artifact.
                _ = page.rect
        return True
    except Exception:
        return False


def atomic_pdf_output(builder: Callable[..., T]) -> Callable[..., T]:
    """Keep the previous output intact on generation/validation/replace failure.

    A sharing violation is a failed publication, not a reason to unlink the old
    file. Callers can retry after its reader closes. Every handle owned by the
    builder and validator is closed before the single atomic replacement.
    """

    @wraps(builder)
    def write(source_pdf: Path, output_pdf: Path, *args: Any, **kwargs: Any) -> T:
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
