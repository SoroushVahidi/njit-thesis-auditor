"""Inspect planted strings and residual structure in synthetic replacement PDFs."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import fitz
from pypdf import PdfReader

from scripts.experimental_anonpdf_adapter import transform_with_anonpdf
from scripts.experimental_pdf_engine_adapter import transform_with_pdf_edit_engine

PLANTED = (
    "DR_ASTRA_9C73",
    "QUASAR-FUSION PROJECT",
    "AUTHOR LENA ARBOR",
    "SECRET PANEL DATA",
)


def generate_planted_fixture(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with fitz.open() as doc:
        page = doc.new_page(width=612, height=792)
        page.insert_text((140, 110), "TABLE OF CONTENTS", fontname="hebo", fontsize=14)
        for index, text in enumerate(PLANTED):
            page.insert_text((108, 160 + 26 * index), text, fontsize=12)
        page.insert_text((300, 736), "i", fontsize=12)
        doc.set_metadata(
            {"title": "SYNTHETIC QUASAR-FUSION PROJECT", "author": "AUTHOR LENA ARBOR"}
        )
        doc.save(path, garbage=4, deflate=True)


def inspect(source: Path, output: Path) -> dict[str, Any]:
    with fitz.open(source) as doc:
        source_text = "\n".join(page.get_text() for page in doc)
    with fitz.open(output) as doc:
        output_text = "\n".join(page.get_text() for page in doc)
        metadata = dict(doc.metadata)
        object_text = "\n".join(
            doc.xref_object(xref)
            + "\n"
            + (doc.xref_stream(xref) or b"").decode("latin-1", errors="ignore")
            for xref in range(1, doc.xref_length())
        )
        attachments = doc.embfile_count()
        images = sum(len(page.get_images(full=True)) for page in doc)
        annotations = sum(page.first_annot is not None for page in doc)
        layers = len(doc.get_ocgs())
    pypdf_text = "\n".join(page.extract_text() or "" for page in PdfReader(output).pages)
    raw = output.read_bytes()
    planted_presence = {
        token: {
            "pymupdf": token.lower() in output_text.lower(),
            "pypdf": token.lower() in pypdf_text.lower(),
            "objects": token.lower() in object_text.lower(),
            "raw_bytes": token.lower().encode() in raw.lower(),
            "metadata": token.lower() in str(metadata).lower(),
        }
        for token in PLANTED
    }
    return {
        "planted_presence": planted_presence,
        "output_metadata": metadata,
        "attachments": attachments,
        "images": images,
        "annotations": annotations,
        "hidden_layers": layers,
        "incremental_history_markers": raw.count(b"%%EOF"),
        "word_length_pattern_equal": [
            len(word) for word in re.findall(r"[A-Za-z0-9]+", source_text)
        ]
        == [len(word) for word in re.findall(r"[A-Za-z0-9]+", output_text)],
        "generic_heading_retained": "TABLE OF CONTENTS" in output_text,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--anonpdf-script", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = args.directory / "synthetic_planted.pdf"
    generate_planted_fixture(source)
    results: dict[str, Any] = {}
    for strategy in ("random", "width", "structural"):
        destination = args.directory / f"synthetic_planted_engine_{strategy}.pdf"
        transform_with_pdf_edit_engine(source, destination, strategy)
        results[strategy] = inspect(source, destination)
    fallback = args.directory / "synthetic_planted_anonpdf.pdf"
    transform_with_anonpdf(source, fallback, args.anonpdf_script)
    results["anonpdf_fixed"] = inspect(source, fallback)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
