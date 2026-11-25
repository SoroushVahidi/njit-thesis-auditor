"""Synthetic PDF publication failures; no private fixtures or native Windows claims."""

import errno
from pathlib import Path

import fitz
import pytest
from test_offline_desktop import _pdf

from njit_auditor import pdf_publication
from njit_auditor.pdf_highlight import (
    build_highlighted_pdf,
    build_highlighted_single_page_pdf,
    build_single_page_pdf,
)
from njit_auditor.pdf_publication import atomic_pdf_output, complete_pdf


@pytest.mark.parametrize("failure", ["before", "partial", "invalid", "disk-full", "permission"])
@pytest.mark.parametrize("existing", [False, True])
def test_failed_generation_preserves_cache_and_cleans_staging(tmp_path, failure, existing):
    source, output = tmp_path / "source.pdf", tmp_path / "out.pdf"
    source.write_bytes(_pdf("normal"))
    previous = _pdf("unicode")
    if existing:
        output.write_bytes(previous)

    @atomic_pdf_output
    def broken(source, destination):
        assert destination != output and destination.parent.parent == output.parent
        if failure != "before":
            destination.write_bytes(b"%PDF-1.7\npartial")
        if failure == "invalid":
            return True
        error = errno.ENOSPC if failure == "disk-full" else errno.EACCES
        raise OSError(error, "Synthetic failure")

    with pytest.raises((OSError, ValueError)):
        broken(source, output)
    assert output.read_bytes() == previous if existing else not output.exists()
    assert not list(tmp_path.glob(".pdf-write-*"))


@pytest.mark.parametrize("error", [errno.EACCES, errno.ENOSPC, errno.EPERM])
def test_failed_replace_keeps_valid_output_and_retry_succeeds(tmp_path, monkeypatch, error):
    source, output = tmp_path / "source.pdf", tmp_path / "out.pdf"
    source.write_bytes(_pdf("normal"))
    previous = _pdf("unicode")
    output.write_bytes(previous)
    original = pdf_publication.os.replace

    def deny(src, dst):
        assert complete_pdf(Path(src))
        exc = OSError(error, "Synthetic Windows-style sharing/publication failure")
        exc.winerror = 32
        raise exc

    monkeypatch.setattr(pdf_publication.os, "replace", deny)
    with output.open("rb") as download:
        with pytest.raises(OSError):
            build_single_page_pdf(source, output, source_page_number=1)
        assert download.read() == previous
    assert output.read_bytes() == previous
    assert not list(tmp_path.glob(".pdf-write-*"))
    monkeypatch.setattr(pdf_publication.os, "replace", original)
    assert build_single_page_pdf(source, output, source_page_number=1)
    assert complete_pdf(output)


@pytest.mark.parametrize("kind", ["full", "page", "plain"])
def test_atomic_writers_preserve_successful_geometry_and_content(tmp_path, kind):
    source, output = tmp_path / "source.pdf", tmp_path / "out.pdf"
    source.write_bytes(_pdf("rotated"))
    box = (60, 60, 200, 90)
    if kind == "full":
        assert build_highlighted_pdf(source, output, {1: [box]}).has_highlight
    elif kind == "page":
        assert build_highlighted_single_page_pdf(
            source, output, source_page_number=1, boxes=[box]
        ).has_highlight
    else:
        assert build_single_page_pdf(source, output, source_page_number=1)
    assert complete_pdf(output)
    with fitz.open(source) as original, fitz.open(output) as result:
        assert result.page_count == 1
        assert result[0].rect == original[0].rect
        assert result[0].rotation == original[0].rotation
        assert result[0].get_text() == original[0].get_text()
        page = result[0]  # Keep the owner alive while inspecting annotation handles.
        annotations = list(page.annots() or [])
        assert len(annotations) == (0 if kind == "plain" else 1)
        if annotations:
            assert tuple(annotations[0].rect) == pytest.approx((59, 59, 201, 91))


def test_truncated_cache_is_not_complete_even_if_pymupdf_can_repair_it(tmp_path):
    output = tmp_path / "out.pdf"
    output.write_bytes(_pdf("normal")[:-6])
    with fitz.open(output) as document:
        assert document.page_count == 1  # Merely opening a PDF is insufficient.
    assert not complete_pdf(output)
