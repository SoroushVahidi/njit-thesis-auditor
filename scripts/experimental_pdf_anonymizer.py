"""Local, synthetic-only PDF replacement experiment with a fail-closed gate.

Requires separately installed pdf-edit-engine 0.2.0 (MIT) and pikepdf (MPL-2.0).
This is not a confidentiality certification or a real-dissertation tool.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import re
import socket
import subprocess
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import fitz
import pikepdf
from pypdf import PdfReader

from scripts.evaluate_pdf_editor_adaptation import (
    _anchor_comparison,
    _geometry_detail,
    _strict_comparison,
)
from scripts.evaluate_synthetic_obfuscation import evaluate_pair
from scripts.experimental_pdf_engine_adapter import (
    _GENERIC_HEADINGS,
    UnsupportedEditorPDF,
    transform_with_pdf_edit_engine,
)

_ALLOW_WORDS = {
    *re.findall(r"[a-z]+", " ".join(_GENERIC_HEADINGS).lower()),
    "chapter",
    "appendix",
    "thesis",
    "dissertation",
}


@contextmanager
def _block_network() -> Iterator[None]:
    """Stop ordinary Python socket connections for the whole CLI process."""

    def deny(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("Network access is disabled in this local experiment")

    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex
    original_sendto = socket.socket.sendto
    original_sendmsg = getattr(socket.socket, "sendmsg", None)
    original_create = socket.create_connection
    socket.socket.connect = deny  # type: ignore[method-assign]
    socket.socket.connect_ex = deny  # type: ignore[method-assign]
    socket.socket.sendto = deny  # type: ignore[method-assign]
    if original_sendmsg is not None:
        socket.socket.sendmsg = deny  # type: ignore[method-assign]
    socket.create_connection = deny  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket.connect = original_connect  # type: ignore[method-assign]
        socket.socket.connect_ex = original_connect_ex  # type: ignore[method-assign]
        socket.socket.sendto = original_sendto  # type: ignore[method-assign]
        if original_sendmsg is not None:
            socket.socket.sendmsg = original_sendmsg  # type: ignore[method-assign]
        socket.create_connection = original_create  # type: ignore[assignment]


def _extract_with_command(command: list[str]) -> str:
    try:
        result = subprocess.run(command, capture_output=True, timeout=30, check=True)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise UnsupportedEditorPDF("Independent PDF text extractor failed") from exc
    return result.stdout.decode("utf-8", errors="replace")


def _privacy_scan(source: Path, output: Path, planted_tokens: tuple[str, ...]) -> dict[str, Any]:
    """Inspect several parsers and raw/decoded objects without reporting source text."""
    with fitz.open(source) as original:
        source_text = "\n".join(page.get_text() for page in original)
    with fitz.open(output) as transformed:
        fitz_text = "\n".join(page.get_text() for page in transformed)
        metadata = dict(transformed.metadata)
        xref_length = transformed.xref_length()
        object_bytes = b"\n".join(
            transformed.xref_object(xref).encode("utf-8", errors="replace")
            + b"\n"
            + (transformed.xref_stream(xref) or b"")
            for xref in range(1, xref_length)
        )
        structures = {
            "attachments": transformed.embfile_count(),
            "images": sum(len(page.get_images(full=True)) for page in transformed),
            "annotations": sum(page.first_annot is not None for page in transformed),
            "links": sum(len(page.get_links()) for page in transformed),
            "form_fields": sum(sum(1 for _ in page.widgets()) for page in transformed),
            "form_xobjects": sum(len(page.get_xobjects()) for page in transformed),
            "optional_layers": len(transformed.get_ocgs()),
            "xml_metadata": bool(transformed.get_xml_metadata()),
        }
    reader = PdfReader(output, strict=True)
    pypdf_text = "\n".join(page.extract_text() or "" for page in reader.pages)
    poppler_text = _extract_with_command(["pdftotext", "-layout", str(output), "-"])
    mupdf_text = _extract_with_command(
        ["mutool", "draw", "-q", "-F", "txt", "-o", "-", str(output)]
    )
    with pikepdf.Pdf.open(output) as pdf:
        pike_objects = b"\n".join(
            str(obj).encode("utf-8", errors="replace")
            + (obj.read_bytes() if isinstance(obj, pikepdf.Stream) else b"")
            for obj in pdf.objects
        )
        structures["pikepdf_attachments"] = len(pdf.attachments)
        structures["catalog_extra_keys"] = len(set(pdf.Root.keys()) - {"/Type", "/Pages", "/Info"})
        structures["trailer_extra_keys"] = len(
            set(pdf.trailer.keys()) - {"/Size", "/ID", "/Root", "/Info"}
        )
        structures["page_extra_keys"] = sum(
            len(
                set(page.keys())
                - {"/Type", "/MediaBox", "/Contents", "/Parent", "/Rotate", "/Resources"}
            )
            + len(set(page.Resources.keys()) - {"/Font"})
            for page in pdf.pages
        )
    raw = output.read_bytes()
    all_surfaces = {
        "pymupdf_text": fitz_text.encode(),
        "pypdf_text": pypdf_text.encode(),
        "poppler_text": poppler_text.encode(),
        "mutool_text": mupdf_text.encode(),
        "pymupdf_objects": object_bytes,
        "pikepdf_objects": pike_objects,
        "raw_bytes": raw,
        "metadata": str(metadata).encode(),
    }

    def recovered_token(token: str, data: bytes) -> bool:
        folded = token.casefold()
        representations = (
            folded.encode(),
            folded.encode("utf-16-be"),
            folded.encode("utf-16-le"),
            folded.encode().hex().encode(),
        )
        return any(representation in data.lower() for representation in representations)

    recovered = {
        surface: sum(recovered_token(token, data) for token in planted_tokens)
        for surface, data in all_surfaces.items()
    }
    source_words = {
        word.casefold() for word in re.findall(r"[A-Za-z]{5,}", source_text)
    } - _ALLOW_WORDS
    source_word_lengths = [len(word) for word in re.findall(r"[A-Za-z0-9]+", source_text)]
    output_word_lengths = [len(word) for word in re.findall(r"[A-Za-z0-9]+", fitz_text)]
    extracted = "\n".join((fitz_text, pypdf_text, poppler_text, mupdf_text)).casefold()
    recovered_word_count = sum(
        bool(re.search(rf"\b{re.escape(word)}\b", extracted)) for word in source_words
    )
    source_lines = [
        line.strip().casefold() for line in source_text.splitlines() if len(line.strip()) >= 8
    ]
    object_text = (object_bytes + pike_objects + raw).decode("latin-1", errors="ignore").casefold()
    generic_lines = {line.casefold() for line in _GENERIC_HEADINGS}
    recovered_line_count = sum(
        line in object_text
        for line in source_lines
        if line not in generic_lines
        and not re.fullmatch(r"(?:chapter|appendix)\s+(?:[0-9]+|[a-z])", line)
    )
    history_markers = raw.count(b"%%EOF")
    object_definitions = sorted(
        int(match.group(1)) for match in re.finditer(rb"(?m)^(\d+)\s+\d+\s+obj\b", raw)
    )
    residual_definitions = object_definitions != list(range(1, xref_length))
    if (
        any(recovered.values())
        or recovered_word_count
        or recovered_line_count
        or any(structures.values())
        or history_markers != 1
        or residual_definitions
        or b"/Prev" in raw
        or any(
            value for key, value in metadata.items() if key not in {"format", "title", "encryption"}
        )
    ):
        raise UnsupportedEditorPDF("Privacy or residual-structure gate failed")
    return {
        "planted_token_count": len(planted_tokens),
        "recovered_token_counts_by_surface": recovered,
        "recovered_nonstructural_source_words": recovered_word_count,
        "recovered_source_lines_in_objects": recovered_line_count,
        "residual_structures": structures,
        "eof_markers": history_markers,
        "unindexed_or_duplicate_object_definitions": residual_definitions,
        "source_word_count": len(source_word_lengths),
        "word_length_pattern_equal": source_word_lengths == output_word_lengths,
        "source_layout_disclosed": True,
        "reidentification_risk_assessed": False,
    }


def _run_local(
    source: Path,
    destination: Path,
    *,
    seed: int,
    planted_tokens: tuple[str, ...] = (),
    max_line_drift_pt: float = 0.25,
) -> dict[str, Any]:
    """Publish only after format, auditor, and technical privacy gates pass."""
    if importlib.metadata.version("pdf-edit-engine") != "0.2.0":
        raise UnsupportedEditorPDF("The pinned upstream editor version is required")
    source, destination = Path(source), Path(destination)
    if not source.is_file() or destination.exists() or source.resolve() == destination.resolve():
        raise FileExistsError("Input must exist and output must be a new, separate path")
    if max_line_drift_pt < 0:
        raise ValueError("Maximum line drift must be nonnegative")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="synthetic-anonymizer-", dir=destination.parent
    ) as name:
        stage = Path(name) / "candidate.pdf"
        summary = transform_with_pdf_edit_engine(source, stage, "balanced", seed=seed)
        comparison = evaluate_pair(source, stage)
        detail = _geometry_detail(source, stage)
        anchors = _anchor_comparison(source, stage)
        strict = _strict_comparison(source, stage)
        if (
            not comparison["page_sizes_identical"]
            or comparison["original_blocks"] != comparison["transformed_blocks"]
            or comparison["original_lines"] != comparison["transformed_lines"]
            or comparison["original_characters"] != comparison["transformed_characters"]
            or comparison["font_name_matches"] != comparison["original_characters"]
            or comparison["max_font_size_delta_pt"] != 0
            or detail["max_line_start_x_delta_pt"] > 0.01
            or detail["max_line_start_y_delta_pt"] > 0.01
            or detail["max_line_end_x_delta_pt"] > max_line_drift_pt
            or strict["lost"]
            or strict["introduced"]
        ):
            raise UnsupportedEditorPDF("Layout or auditor-equivalence gate failed")
        privacy = _privacy_scan(source, stage, planted_tokens)
        report = {
            "status": "SYNTHETIC_TECHNICAL_GATES_PASSED",
            "upstream": "AryanBV/pdf-edit-engine 0.2.0 @ cee1d2cc042f84d0fb02c874765509c04a8624ac",
            "seed": seed,
            "edited_lines": summary.edited_lines,
            "preserved_generic_lines": summary.preserved_generic_lines,
            "pages": comparison["pages"],
            "blocks": comparison["original_blocks"],
            "lines": comparison["original_lines"],
            "characters": comparison["original_characters"],
            "max_character_bbox_delta_pt": comparison["max_character_bbox_delta_pt"],
            "max_line_bbox_delta_pt": comparison["max_line_bbox_delta_pt"],
            "geometry": detail,
            "auditor": {
                "original": strict["original"],
                "full_box_matched": strict["matched"],
                "lost": strict["lost"],
                "introduced": strict["introduced"],
                "per_rule": strict["per_rule"],
                "anchor": anchors,
            },
            "privacy": privacy,
            "real_confidential_dissertations_supported": False,
            "output_safe_to_share": False,
        }
        os.link(stage, destination)
        return report


def run(
    source: Path,
    destination: Path,
    *,
    seed: int,
    planted_tokens: tuple[str, ...] = (),
    max_line_drift_pt: float = 0.25,
) -> dict[str, Any]:
    """Run the synthetic gate with outbound Python sockets blocked."""
    with _block_network():
        try:
            return _run_local(
                source,
                destination,
                seed=seed,
                planted_tokens=planted_tokens,
                max_line_drift_pt=max_line_drift_pt,
            )
        except (UnsupportedEditorPDF, FileExistsError, ValueError):
            raise
        except Exception:
            raise UnsupportedEditorPDF(
                "Unexpected local transformation or verification failure"
            ) from None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--planted-token", action="append", default=[])
    parser.add_argument("--max-line-drift-pt", type=float, default=0.25)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if (
        args.report.exists()
        or args.report.resolve() in {args.source.resolve(), args.destination.resolve()}
    ):
        parser.error("Report path must be new and distinct from input and output")
    try:
        report = run(
            args.source,
            args.destination,
            seed=args.seed,
            planted_tokens=tuple(args.planted_token),
            max_line_drift_pt=args.max_line_drift_pt,
        )
    except (UnsupportedEditorPDF, FileExistsError, ValueError) as exc:
        parser.exit(2, f"Refused: {exc}\n")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("Synthetic technical gates passed. Confidentiality and sharing are not certified.")


if __name__ == "__main__":
    main()
