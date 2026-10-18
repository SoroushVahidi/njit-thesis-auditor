"""Synthetic-only PDF text replacement experiment.

This reconstructs a new, text-only PDF from extracted character positions. It
does not edit or copy the source PDF's objects. It is not encryption and is not
approved for confidential documents.
"""

from __future__ import annotations

import argparse
import math
import os
import secrets
import string
import tempfile
from dataclasses import dataclass
from pathlib import Path

import fitz


class UnsupportedPDF(ValueError):
    """The source exceeds the narrow, measurable scope of this experiment."""


_FONTS = {
    "Helvetica": "helv",
    "Helvetica-Bold": "hebo",
    "Helvetica-Oblique": "heit",
    "Helvetica-BoldOblique": "hebi",
    "Times-Roman": "tiro",
    "Times-Bold": "tibo",
    "Times-Italic": "tiit",
    "Times-BoldItalic": "tibi",
    "Courier": "cour",
    "Courier-Bold": "cobo",
    "Courier-Oblique": "coit",
    "Courier-BoldOblique": "cobi",
}
_LOWER = "bcdfghjklmnpqrstvwxyz"
_UPPER = _LOWER.upper()
_DIGITS = string.digits
_SYMBOLS = string.punctuation
_MAX_PAGES = 12
_MAX_GLYPHS = 30_000
_MAX_BYTES = 5_000_000
_MAX_WIDTH_DELTA_PT = 0.25


@dataclass(frozen=True)
class _Glyph:
    char: str
    origin: tuple[float, float]
    width: float
    font: str
    size: float
    color: tuple[float, float, float]


@dataclass(frozen=True)
class TransformSummary:
    pages: int
    replaced_characters: int
    retained_layout_punctuation: int
    max_glyph_width_delta_pt: float


def _color(rgb: int) -> tuple[float, float, float]:
    return ((rgb >> 16 & 255) / 255, (rgb >> 8 & 255) / 255, (rgb & 255) / 255)


def _replacement(char: str, *, font: str, size: float, width: float) -> tuple[str, float]:
    if char in _DIGITS:
        alphabet = _DIGITS
    elif char in string.ascii_letters:
        # Broaden to punctuation when necessary (e.g. a narrow capital I).
        # This keeps the PDF font size and text matrix unchanged.
        alphabet = _LOWER + _UPPER + _SYMBOLS
    else:
        return char, 0.0
    choices: list[tuple[float, str]] = []
    for candidate in alphabet:
        if candidate == char:
            continue
        candidate_width = fitz.get_text_length(candidate, fontname=font, fontsize=size)
        if candidate_width <= 0:
            continue
        delta = abs(width - candidate_width)
        if delta <= _MAX_WIDTH_DELTA_PT:
            choices.append((delta, candidate))
    if not choices:
        raise UnsupportedPDF(f"No similar-width substitute for a {font} glyph at {size:g} pt")
    choices.sort()
    best = choices[0][0]
    close = [candidate for error, candidate in choices if error <= best + 0.01]
    return secrets.choice(close), best


def _page_glyphs(page: fitz.Page, page_number: int) -> list[_Glyph]:
    if page.rotation or page.cropbox != page.mediabox:
        raise UnsupportedPDF(f"Page {page_number}: rotated or cropped pages are unsupported")
    if page.first_annot is not None or page.get_links() or any(page.widgets()):
        raise UnsupportedPDF(f"Page {page_number}: annotations, links, or forms are unsupported")
    if page.get_images(full=True) or page.get_drawings() or page.get_xobjects():
        raise UnsupportedPDF(
            f"Page {page_number}: images, drawings, or form objects are unsupported"
        )
    raw = page.get_text("rawdict", sort=False)
    glyphs: list[_Glyph] = []
    for block in raw.get("blocks", []):
        if block.get("type") != 0:
            raise UnsupportedPDF(f"Page {page_number}: non-text content is unsupported")
        for line in block.get("lines", []):
            direction = line.get("dir", (1.0, 0.0))
            if (
                line.get("wmode", 0) != 0
                or abs(direction[0] - 1.0) > 0.001
                or abs(direction[1]) > 0.001
            ):
                raise UnsupportedPDF(f"Page {page_number}: non-horizontal text is unsupported")
            for span in line.get("spans", []):
                font = _FONTS.get(str(span.get("font", "")))
                if font is None:
                    raise UnsupportedPDF(f"Page {page_number}: non-standard font is unsupported")
                size = float(span["size"])
                if not math.isfinite(size) or size <= 0 or size > 72:
                    raise UnsupportedPDF(f"Page {page_number}: invalid font size")
                if int(span.get("alpha", 255)) != 255:
                    raise UnsupportedPDF(f"Page {page_number}: transparent text is unsupported")
                color = _color(int(span.get("color", 0)))
                for item in span.get("chars", []):
                    char = str(item.get("c", ""))
                    if len(char) != 1 or char not in string.printable or char in "\r\n\t\x0b\x0c":
                        raise UnsupportedPDF(f"Page {page_number}: non-ASCII text is unsupported")
                    bbox = item["bbox"]
                    origin = item["origin"]
                    width = float(bbox[2]) - float(bbox[0])
                    if not all(math.isfinite(float(v)) for v in (*bbox, *origin)) or width <= 0:
                        raise UnsupportedPDF(f"Page {page_number}: invalid character geometry")
                    if (
                        float(bbox[0]) < 0
                        or float(bbox[1]) < 0
                        or float(bbox[2]) > page.rect.width
                        or float(bbox[3]) > page.rect.height
                    ):
                        raise UnsupportedPDF(f"Page {page_number}: off-page text is unsupported")
                    glyphs.append(
                        _Glyph(
                            char=char,
                            origin=(float(origin[0]), float(origin[1])),
                            width=width,
                            font=font,
                            size=size,
                            color=color,
                        )
                    )
    return glyphs


def transform_synthetic_pdf(source: Path, destination: Path) -> TransformSummary:
    """Write a fresh PDF from a marked synthetic, text-only source.

    Alphanumeric characters are replaced independently. Whitespace and
    punctuation remain to retain word spacing, line structure and leaders.
    Their patterns remain a privacy limitation. An existing destination is
    never overwritten.
    """
    source = Path(source)
    destination = Path(destination)
    if not source.is_file() or source.stat().st_size > _MAX_BYTES:
        raise UnsupportedPDF("Source is absent or exceeds the 5 MB experiment limit")
    if destination.exists() or source.resolve() == destination.resolve():
        raise FileExistsError("Destination must be a new path")
    operations: list[list[tuple[_Glyph, str]]] = []
    replaced = 0
    punctuation = 0
    max_width_delta = 0.0
    with fitz.open(source) as original:
        if original.needs_pass or original.is_encrypted:
            raise UnsupportedPDF("Encrypted PDFs are unsupported")
        if not str(original.metadata.get("title", "")).startswith("SYNTHETIC "):
            raise UnsupportedPDF("Only PDFs marked SYNTHETIC in the title are accepted")
        if len(original) == 0 or len(original) > _MAX_PAGES:
            raise UnsupportedPDF("Page count exceeds the experiment limit")
        if original.embfile_count() or original.is_form_pdf:
            raise UnsupportedPDF("Attachments or form fields are unsupported")
        total = 0
        for number, page in enumerate(original, 1):
            glyphs = _page_glyphs(page, number)
            total += len(glyphs)
            if total > _MAX_GLYPHS:
                raise UnsupportedPDF("Character count exceeds the experiment limit")
            page_ops: list[tuple[_Glyph, str]] = []
            for glyph in glyphs:
                if glyph.char.isspace():
                    continue
                substitute, width_delta = _replacement(
                    glyph.char, font=glyph.font, size=glyph.size, width=glyph.width
                )
                if glyph.char.isalnum():
                    replaced += 1
                else:
                    punctuation += 1
                max_width_delta = max(max_width_delta, width_delta)
                page_ops.append((glyph, substitute))
            operations.append(page_ops)
        sizes = [(float(page.rect.width), float(page.rect.height)) for page in original]

    output = fitz.open()
    try:
        for (width, height), page_ops in zip(sizes, operations, strict=True):
            page = output.new_page(width=width, height=height)
            for glyph, substitute in page_ops:
                origin = fitz.Point(glyph.origin)
                page.insert_text(
                    origin,
                    substitute,
                    fontsize=glyph.size,
                    fontname=glyph.font,
                    color=glyph.color,
                )
        output.set_metadata({"title": "SYNTHETIC obfuscated layout experiment"})
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            prefix=".obfuscation-poc-", suffix=".pdf", dir=destination.parent, delete=False
        ) as temporary:
            temp_path = Path(temporary.name)
        try:
            output.save(temp_path, garbage=4, deflate=True)
            os.link(temp_path, destination)
        finally:
            temp_path.unlink(missing_ok=True)
    finally:
        output.close()
    return TransformSummary(len(operations), replaced, punctuation, max_width_delta)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    result = transform_synthetic_pdf(args.source, args.destination)
    print(result)
    print("Experiment only: layout patterns remain; never use this for confidential documents.")


if __name__ == "__main__":
    main()
