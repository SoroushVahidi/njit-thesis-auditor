"""Generate text-only synthetic PDFs for the obfuscation experiment."""

from __future__ import annotations

import argparse
from pathlib import Path

import fitz


def _line(page: fitz.Page, x: float, y: float, text: str, font: str, size: float) -> None:
    page.insert_text((x, y), text, fontname=font, fontsize=size)


def _save(doc: fitz.Document, path: Path, title: str) -> None:
    doc.set_metadata({"title": f"SYNTHETIC {title}", "author": "Synthetic fixture generator"})
    doc.save(path, garbage=4, deflate=True)
    doc.close()


def generate_fixtures(directory: Path) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []

    helvetica = fitz.open()
    page = helvetica.new_page(width=612, height=792)
    _line(page, 140, 145, "SYNTHETIC QUASAR ARRAY STUDY", "hebo", 16)
    _line(page, 205, 210, "A fabricated dissertation", "helv", 12)
    _line(page, 300, 736, "i", "helv", 12)
    page = helvetica.new_page(width=612, height=792)
    _line(page, 205, 102, "TABLE OF CONTENTS", "hebo", 14)
    _line(page, 110, 165, "CHAPTER 1. INTRODUCTION .............. 1", "helv", 12)
    _line(page, 110, 188, "CHAPTER 2. METHODS ................... 2", "helv", 12)
    _line(page, 300, 736, "ii", "helv", 12)
    page = helvetica.new_page(width=612, height=792)
    _line(page, 108, 105, "CHAPTER 1", "hebo", 14)
    _line(page, 108, 132, "INTRODUCTION", "hebo", 14)
    _line(page, 108, 177, "Synthetic particles drift across an invented grid.", "helv", 12)
    _line(page, 52, 202, "This fabricated line intentionally crosses the left margin.", "helv", 12)
    _line(page, 136, 226, "The next line has a visible first-line indentation.", "helv", 12)
    _line(page, 108, 242, "Its continuation keeps the same baseline spacing.", "helv", 12)
    _line(page, 300, 736, "1", "helv", 12)
    path = directory / "synthetic_helvetica.pdf"
    _save(helvetica, path, "Helvetica layout")
    paths.append(path)

    times = fitz.open()
    page = times.new_page(width=612, height=792)
    _line(page, 160, 108, "LIST OF FIGURES", "tibo", 14)
    _line(page, 110, 162, "Figure 1.1 Fabricated signals ........ 2", "tiro", 12)
    _line(page, 110, 184, "Figure 1.2 Imaginary orbit ........... 3", "tiro", 12)
    _line(page, 300, 736, "iv", "tiro", 12)
    page = times.new_page(width=612, height=792)
    _line(page, 108, 102, "CHAPTER 2", "tibo", 14)
    _line(page, 108, 130, "METHODS", "tibo", 14)
    _line(page, 108, 180, "An imaginary telescope collected fictional signals.", "tiro", 12)
    _line(page, 136, 206, "A second synthetic paragraph begins with an indent.", "tiro", 12)
    _line(page, 108, 223, "Its continuation uses regular Times text.", "tiro", 12)
    _line(page, 108, 268, "Figure 2.1: A nonexistent measurement.", "tiit", 11)
    _line(page, 300, 736, "2", "tiro", 12)
    path = directory / "synthetic_times.pdf"
    _save(times, path, "Times layout")
    paths.append(path)

    courier = fitz.open()
    page = courier.new_page(width=792, height=612)
    _line(page, 230, 85, "TABLE OF CONTENTS", "cobo", 14)
    _line(page, 108, 130, "CHAPTER 3. RESULTS ............... 7", "cour", 12)
    _line(page, 108, 153, "APPENDIX A. DATA ................. 9", "cour", 12)
    _line(page, 385, 550, "vi", "cour", 12)
    page = courier.new_page(width=792, height=612)
    _line(page, 108, 85, "CHAPTER 3", "cobo", 14)
    _line(page, 108, 118, "RESULTS", "cobo", 14)
    _line(page, 108, 165, "Invented observations fill this wide synthetic page.", "cour", 12)
    _line(page, 132, 190, "The first line of this paragraph is indented.", "cour", 12)
    _line(page, 108, 207, "A continuation line keeps fixed-width glyphs.", "cour", 12)
    _line(page, 385, 550, "7", "cour", 12)
    path = directory / "synthetic_courier_landscape.pdf"
    _save(courier, path, "Courier landscape layout")
    paths.append(path)
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    for path in generate_fixtures(args.directory):
        print(path)


if __name__ == "__main__":
    main()
