"""Synthetic-only adapter for pdf-edit-engine 0.2.0 at cee1d2cc.

The upstream MIT package is installed separately; no upstream source is copied.
This is a compatibility experiment, not anonymization or encryption.
"""

from __future__ import annotations

import argparse
import os
import random
import re
import secrets
import string
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import fitz
from pypdf import PdfReader
from pypdf.generic import (
    ArrayObject,
    ByteStringObject,
    ContentStream,
    FloatObject,
    IndirectObject,
    NameObject,
    NumberObject,
    TextStringObject,
)

from njit_auditor.experimental_pdf_text import (
    _FONTS,
    _MAX_BYTES,
    _MAX_PAGES,
    UnsupportedPDF,
    _page_glyphs,
)

Strategy = Literal["random", "width", "structural", "balanced"]
_GENERIC_HEADINGS = frozenset(
    {
        "TABLE OF CONTENTS",
        "LIST OF FIGURES",
        "LIST OF TABLES",
        "APPROVAL PAGE",
        "BIOGRAPHICAL SKETCH",
        "ACKNOWLEDGEMENTS",
        "ABSTRACT",
        "REFERENCES",
        "INTRODUCTION",
        "METHODS",
        "RESULTS",
        "Page",
        "Figure",
        "Table",
    }
)
_STRUCTURAL_PREFIXES = (
    re.compile(r"^(?:CHAPTER|APPENDIX)\s+(?:[1-9][0-9]*|[A-Z])\b"),
    re.compile(r"^(?:Figure|Table)\s+[1-9][0-9]*(?:\.[0-9]+)*\b"),
)
_SAFE_TEXT_OPERATORS = {b"q", b"Q", b"BT", b"ET", b"Tf", b"Tm", b"TJ", b"Tj"}
_FONT_ALIASES = frozenset({"/helv", "/hebo", "/tiro", "/tibo", "/tiit", "/cour", "/cobo"})
_MAX_OBJECTS = 2048


class UnsupportedEditorPDF(ValueError):
    """The source or an edit falls outside this narrow experiment."""


@dataclass(frozen=True)
class LineEdit:
    page: int
    text: str
    replacement: str
    center: tuple[float, float]


@dataclass(frozen=True)
class EditorSummary:
    strategy: Strategy
    edited_lines: int
    preserved_generic_lines: int
    font_preserved_edits: int


def _sanitize_metadata_and_id(source: Path, destination: Path, title: str) -> None:
    """Write a fresh PDF without source metadata, catalog Info, or trailer IDs."""
    try:
        import pikepdf
    except ImportError as exc:
        raise RuntimeError("Pinned pikepdf dependency is unavailable") from exc
    metadata_stage = destination.with_name("metadata-stage.pdf")
    with fitz.open(source) as doc:
        metadata = {key: "" for key in doc.metadata if key != "format"}
        metadata["title"] = title
        doc.set_metadata(metadata)
        doc.save(metadata_stage, garbage=4, deflate=True)
    with pikepdf.Pdf.open(metadata_stage) as pdf:
        if "/Info" in pdf.Root:
            del pdf.Root["/Info"]
        pdf.trailer.ID = pikepdf.Array(
            [pikepdf.String(secrets.token_bytes(16)), pikepdf.String(secrets.token_bytes(16))]
        )
        pdf.save(destination)


def _verify_object_graph(reader: PdfReader) -> None:
    """Accept only the small PDF object schema made by our synthetic generator."""
    try:
        trailer = reader.trailer
        if set(trailer) - {"/Size", "/Root", "/Info", "/ID"}:
            raise UnsupportedEditorPDF("Unverified PDF trailer")
        if int(trailer["/Size"]) > _MAX_OBJECTS:
            raise UnsupportedEditorPDF("PDF object count exceeds synthetic experiment limit")
        root_ref = trailer.raw_get("/Root")
        if not isinstance(root_ref, IndirectObject):
            raise UnsupportedEditorPDF("Inline catalog unsupported")
        root = root_ref.get_object()
        if set(root) - {"/Type", "/Pages", "/Info"} or root.get("/Type") != "/Catalog":
            raise UnsupportedEditorPDF("Unverified catalog")
        if "/Info" in root and (
            set(root["/Info"]) != {"/Producer"}
            or root["/Info"]["/Producer"] != f"MuPDF {fitz.VersionBind}"
        ):
            raise UnsupportedEditorPDF("Unverified inline catalog metadata")
        tree_ref = root.raw_get("/Pages")
        if not isinstance(tree_ref, IndirectObject):
            raise UnsupportedEditorPDF("Inline page tree unsupported")
        tree = tree_ref.get_object()
        if set(tree) != {"/Type", "/Count", "/Kids"} or tree["/Type"] != "/Pages":
            raise UnsupportedEditorPDF("Unverified page tree")
        children = tree["/Kids"]
        if not isinstance(children, ArrayObject) or len(children) != len(reader.pages):
            raise UnsupportedEditorPDF("Unverified page children")
        seen = {root_ref.idnum, tree_ref.idnum}
        if "/Info" in trailer:
            info_ref = trailer.raw_get("/Info")
            if not isinstance(info_ref, IndirectObject):
                raise UnsupportedEditorPDF("Inline trailer metadata unsupported")
            seen.add(info_ref.idnum)
            if set(info_ref.get_object()) - {
                "/Title",
                "/Author",
                "/Subject",
                "/Keywords",
                "/Creator",
                "/Producer",
                "/CreationDate",
                "/ModDate",
                "/Trapped",
            }:
                raise UnsupportedEditorPDF("Unverified trailer metadata")
        for page_ref in children:
            if not isinstance(page_ref, IndirectObject):
                raise UnsupportedEditorPDF("Inline page unsupported")
            seen.add(page_ref.idnum)
            page = page_ref.get_object()
            if (
                set(page)
                != {
                    "/Type",
                    "/MediaBox",
                    "/Rotate",
                    "/Resources",
                    "/Parent",
                    "/Contents",
                }
                or page["/Type"] != "/Page"
                or page.raw_get("/Parent") != tree_ref
            ):
                raise UnsupportedEditorPDF("Unverified page object")
            resource_ref = page.raw_get("/Resources")
            if not isinstance(resource_ref, IndirectObject):
                raise UnsupportedEditorPDF("Inline resource dictionary unsupported")
            seen.add(resource_ref.idnum)
            resources = resource_ref.get_object()
            if set(resources) != {"/Font"}:
                raise UnsupportedEditorPDF("Unverified resource dictionary")
            fonts = resources["/Font"]
            if not isinstance(fonts, dict) or not fonts or not set(fonts).issubset(_FONT_ALIASES):
                raise UnsupportedEditorPDF("Unverified font map")
            for font_ref in fonts.values():
                if not isinstance(font_ref, IndirectObject):
                    raise UnsupportedEditorPDF("Inline font unsupported")
                seen.add(font_ref.idnum)
                font = font_ref.get_object()
                if (
                    set(font) != {"/Type", "/Subtype", "/BaseFont", "/Encoding"}
                    or font["/Type"] != "/Font"
                    or font["/Subtype"] != "/Type1"
                    or font["/Encoding"] != "/WinAnsiEncoding"
                    or not isinstance(font["/BaseFont"], NameObject)
                ):
                    raise UnsupportedEditorPDF("Unverified font object")
            streams = page.raw_get("/Contents")
            if not isinstance(streams, ArrayObject) or not streams:
                raise UnsupportedEditorPDF("Unsupported content stream list")
            for stream_ref in streams:
                if not isinstance(stream_ref, IndirectObject):
                    raise UnsupportedEditorPDF("Inline content stream unsupported")
                seen.add(stream_ref.idnum)
                if dict(stream_ref.get_object()) != {"/Filter": "/FlateDecode"}:
                    raise UnsupportedEditorPDF("Unverified content stream dictionary")
        if seen != set(range(1, int(trailer["/Size"]))):
            raise UnsupportedEditorPDF("Unverified or unreachable PDF objects")
    except UnsupportedEditorPDF:
        raise
    except Exception as exc:
        raise UnsupportedEditorPDF("Cannot verify PDF object graph") from exc


def _preserved_positions(
    text: str,
    *,
    bbox: tuple[float, float, float, float],
    page_width: float,
    page_height: float,
) -> set[int]:
    if text in _GENERIC_HEADINGS:
        return set(range(len(text)))
    # A numeric value is not automatically a folio. Only a short, centered
    # footer in the synthetic fixture grammar may be retained as one.
    if (
        re.fullmatch(r"(?:[0-9]{1,4}|[ivxlcdm]{1,8})", text)
        and bbox[1] >= 0.85 * page_height
        and abs((bbox[0] + bbox[2]) / 2 - page_width / 2) <= 0.2 * page_width
    ):
        return set(range(len(text)))
    positions: set[int] = set()
    for pattern in _STRUCTURAL_PREFIXES:
        match = pattern.search(text)
        if match:
            positions.update(range(*match.span()))
    for match in re.finditer(r"\b(?:dissertation|thesis)\b", text, flags=re.IGNORECASE):
        positions.update(range(*match.span()))
    if re.search(r"\.{3,}", text):
        match = re.search(r"\b(?:[0-9]{1,4}|[ivxlcdm]{1,8})$", text)
        if match:
            positions.update(range(*match.span()))
    return positions


def _substitute(char: str, font: str, size: float, strategy: Strategy, rng: random.Random) -> str:
    if char in string.ascii_lowercase:
        alphabet = string.ascii_lowercase
    elif char in string.ascii_uppercase:
        alphabet = string.ascii_uppercase
    elif char in string.digits:
        alphabet = string.digits
    else:
        return char
    choices = [candidate for candidate in alphabet if candidate != char]
    if strategy == "random":
        return rng.choice(choices)
    width = fitz.get_text_length(char, fontname=font, fontsize=size)
    scores = [
        (abs(width - fitz.get_text_length(candidate, fontname=font, fontsize=size)), candidate)
        for candidate in choices
    ]
    best = min(score for score, _ in scores)
    return rng.choice([candidate for score, candidate in scores if score <= best + 0.01])


def _balanced_replacement(
    text: str, keep: set[int], font: str, size: float, rng: random.Random
) -> str:
    """Choose different glyphs while minimizing total line and glyph width drift.

    The upstream engine edits the original text-show operand. A beam over
    available Base14 glyph widths improves the line end without changing its
    text matrix or font. It does not remove width-pattern re-identification risk.
    """
    widths = {
        char: fitz.get_text_length(char, fontname=font, fontsize=size)
        for char in string.ascii_letters + string.digits
    }
    # error, cumulative per-glyph drift, output. Keep one best path per
    # centipoint of cumulative error, then retain a bounded diverse beam.
    beam: list[tuple[float, float, str]] = [(0.0, 0.0, "")]
    for index, char in enumerate(text):
        if index in keep or char not in widths:
            beam = [(error, drift, output + char) for error, drift, output in beam]
            continue
        alphabet = (
            string.ascii_lowercase
            if char.islower()
            else string.ascii_uppercase
            if char.isupper()
            else string.digits
        )
        candidates = [candidate for candidate in alphabet if candidate != char]
        rng.shuffle(candidates)
        candidates.sort(key=lambda candidate: abs(widths[candidate] - widths[char]))
        choices = candidates[:12]
        states: dict[int, tuple[float, float, str]] = {}
        for error, drift, output in beam:
            for candidate in choices:
                delta = widths[candidate] - widths[char]
                state = (error + delta, drift + abs(delta), output + candidate)
                bucket = round(state[0] * 100)
                previous = states.get(bucket)
                if previous is None or state[1] < previous[1]:
                    states[bucket] = state
        beam = sorted(states.values(), key=lambda item: (abs(item[0]) + 0.025 * item[1], item[1]))[
            :128
        ]
    return min(beam, key=lambda item: (abs(item[0]), item[1]))[2]


def _verify_content_operators(
    source: Path, expected_pages: int
) -> list[list[tuple[str, float, float, float]]]:
    """Account for every shown glyph in the narrow synthetic fixture grammar."""
    shown_pages: list[list[tuple[str, float, float, float]]] = []
    try:
        reader = PdfReader(source, strict=True)
        if len(reader.pages) != expected_pages:
            raise UnsupportedEditorPDF("PDF parsers disagree on page count")
        _verify_object_graph(reader)
        for page in reader.pages:
            resources = page.get("/Resources")
            if resources is None or set(resources.get_object()) != {"/Font"}:
                raise UnsupportedEditorPDF("Unverified page resources")
            font_map = resources.get_object().get("/Font")
            if font_map is None:
                raise UnsupportedEditorPDF("Missing font resource map")
            for font in font_map.get_object().values():
                if not hasattr(font, "get_object"):
                    raise UnsupportedEditorPDF("Unverified font resource entry")
                font_object = font.get_object()
                if (
                    not isinstance(font_object, dict)
                    or set(font_object) != {"/Type", "/Subtype", "/BaseFont", "/Encoding"}
                    or font_object.get("/Type") != "/Font"
                    or font_object.get("/Subtype") != "/Type1"
                    or font_object.get("/Encoding") != "/WinAnsiEncoding"
                ):
                    raise UnsupportedEditorPDF("Unverified font resource entry")
            contents = page.get_contents()
            if contents is None:
                raise UnsupportedEditorPDF("Missing page text stream")
            shown: list[tuple[str, float, float, float]] = []
            state = "outside"
            origin: tuple[float, float] | None = None
            size: float | None = None
            for operands, operator in ContentStream(contents, reader).operations:
                if operator not in _SAFE_TEXT_OPERATORS:
                    raise UnsupportedEditorPDF("Unsupported PDF content operator")
                if operator in {b"q", b"Q", b"BT", b"ET"} and operands:
                    raise UnsupportedEditorPDF("Unexpected graphics/text operator operands")
                if operator == b"q":
                    if state != "outside":
                        raise UnsupportedEditorPDF("Unexpected graphics state nesting")
                    state = "saved"
                elif operator == b"BT":
                    if state != "saved":
                        raise UnsupportedEditorPDF("Unverified text object")
                    state = "text"
                    origin, size = None, None
                if operator == b"Tf" and not (
                    state == "text"
                    and len(operands) == 2
                    and isinstance(operands[0], NameObject)
                    and str(operands[0]) in _FONT_ALIASES
                    and isinstance(operands[1], (NumberObject, FloatObject))
                    and 0 < float(operands[1]) <= 100
                ):
                    raise UnsupportedEditorPDF("Unsupported font operator")
                if operator == b"Tf":
                    size = float(operands[1])
                if operator == b"Tm" and not (
                    state == "text"
                    and len(operands) == 6
                    and all(isinstance(item, (NumberObject, FloatObject)) for item in operands)
                    and [float(value) for value in operands[:4]] == [1, 0, 0, 1]
                ):
                    raise UnsupportedEditorPDF("Unsupported text matrix")
                if operator == b"Tm":
                    origin = (float(operands[4]), float(operands[5]))
                if operator == b"TJ" and not (
                    state == "text"
                    and len(operands) == 1
                    and isinstance(operands[0], ArrayObject)
                    and all(
                        isinstance(
                            item,
                            (TextStringObject, ByteStringObject, NumberObject, FloatObject),
                        )
                        for item in operands[0]
                    )
                ):
                    raise UnsupportedEditorPDF("Unsupported text-show array")
                if operator == b"Tj" and not (
                    state == "text"
                    and len(operands) == 1
                    and isinstance(operands[0], (TextStringObject, ByteStringObject))
                ):
                    raise UnsupportedEditorPDF("Unsupported text-show operand")
                if operator in {b"Tj", b"TJ"}:
                    if origin is None or size is None:
                        raise UnsupportedEditorPDF("Text shown without verified position and font")
                    parts = operands[0] if operator == b"TJ" else operands
                    value = "".join(
                        item.decode("latin-1") if isinstance(item, ByteStringObject) else str(item)
                        for item in parts
                        if isinstance(item, (TextStringObject, ByteStringObject))
                    )
                    if not value or not value.isascii() or any(ord(char) < 32 for char in value):
                        raise UnsupportedEditorPDF("Unsupported text encoding or empty show")
                    shown.append((value, origin[0], origin[1], size))
                    state = "shown"
                elif operator == b"ET":
                    if state != "shown":
                        raise UnsupportedEditorPDF("Unverified text object")
                    state = "ending"
                elif operator == b"Q":
                    if state != "ending":
                        raise UnsupportedEditorPDF("Unbalanced graphics state")
                    state = "outside"
            if state != "outside":
                raise UnsupportedEditorPDF("Incomplete text or graphics state")
            shown_pages.append(shown)
        return shown_pages
    except UnsupportedEditorPDF:
        raise
    except Exception as exc:
        raise UnsupportedEditorPDF("Cannot verify PDF content operators") from exc


def _planned_lines(source: Path, strategy: Strategy, *, seed: int | None = None) -> list[LineEdit]:
    if not source.is_file() or source.stat().st_size > _MAX_BYTES:
        raise UnsupportedEditorPDF("Source absent or exceeds synthetic experiment size limit")
    raw_pdf = source.read_bytes()
    if (
        raw_pdf.count(b"%%EOF") != 1
        or b"/Prev" in raw_pdf
        or not raw_pdf.rstrip().endswith(b"%%EOF")
    ):
        raise UnsupportedEditorPDF("Incremental-save history is unsupported")
    edits: list[LineEdit] = []
    rng = random.Random(seed) if seed is not None else random.SystemRandom()
    with fitz.open(source) as doc:
        if doc.xref_length() > _MAX_OBJECTS:
            raise UnsupportedEditorPDF("PDF object count exceeds synthetic experiment limit")
        definitions = sorted(
            int(match.group(1)) for match in re.finditer(rb"(?m)^(\d+)\s+\d+\s+obj\b", raw_pdf)
        )
        if definitions != list(range(1, doc.xref_length())):
            raise UnsupportedEditorPDF("Duplicate, residual, or unindexed PDF objects")
        if doc.needs_pass or doc.is_encrypted or not 0 < len(doc) <= _MAX_PAGES:
            raise UnsupportedEditorPDF("Encrypted or oversized PDF unsupported")
        if not str(doc.metadata.get("title", "")).startswith("SYNTHETIC "):
            raise UnsupportedEditorPDF("Only PDFs marked SYNTHETIC in the title are accepted")
        if doc.embfile_count() or doc.is_form_pdf or doc.get_xml_metadata() or doc.get_ocgs():
            raise UnsupportedEditorPDF("Attachments, forms, XMP, or hidden layers unsupported")
        shown_pages = _verify_content_operators(source, len(doc))
        if set(doc.xref_get_keys(doc.pdf_catalog())) - {"Type", "Pages", "Info"}:
            raise UnsupportedEditorPDF("Unverified catalog structures are unsupported")
        info_type, info_value = doc.xref_get_key(-1, "Info")
        if info_type == "xref":
            info_xref = int(info_value.split()[0])
            allowed_info = {
                "Title",
                "Author",
                "Subject",
                "Keywords",
                "Creator",
                "Producer",
                "CreationDate",
                "ModDate",
                "Trapped",
            }
            if set(doc.xref_get_keys(info_xref)) - allowed_info:
                raise UnsupportedEditorPDF("Unverified metadata fields are unsupported")
        for page_index, page in enumerate(doc):
            allowed_page = {"Type", "MediaBox", "Rotate", "Resources", "Parent", "Contents"}
            if set(doc.xref_get_keys(page.xref)) - allowed_page:
                raise UnsupportedEditorPDF("Unverified page structures are unsupported")
            resource_type, resource_value = doc.xref_get_key(page.xref, "Resources")
            if resource_type != "xref":
                raise UnsupportedEditorPDF("Inline or missing page resources are unsupported")
            resource_xref = int(resource_value.split()[0])
            if set(doc.xref_get_keys(resource_xref)) != {"Font"}:
                raise UnsupportedEditorPDF("Non-font page resources are unsupported")
            try:
                _page_glyphs(page, page_index + 1)
            except UnsupportedPDF as exc:
                raise UnsupportedEditorPDF(str(exc)) from exc
            for xref in page.get_contents():
                stream = doc.xref_stream(xref) or b""
                if re.search(rb"/ActualText\b|\b(?:BDC|BMC|EMC|MP|DP)\b", stream):
                    raise UnsupportedEditorPDF("Marked content and ActualText are unsupported")
                if re.search(rb"(?:^|\s)3\s+Tr(?:\s|$)", stream):
                    raise UnsupportedEditorPDF("Invisible text operators are unsupported")
            for entry in page.get_fonts(full=True):
                if (
                    str(entry[3]) not in _FONTS
                    or int(entry[0]) <= 0
                    or set(doc.xref_get_keys(int(entry[0])))
                    != {"Type", "Subtype", "BaseFont", "Encoding"}
                ):
                    raise UnsupportedEditorPDF("Only plain Base14 font resources are supported")
            shown = shown_pages[page_index]
            shown_index = 0
            for block in page.get_text("dict").get("blocks", []):
                if block.get("type") != 0:
                    raise UnsupportedEditorPDF("Non-text block unsupported")
                for line in block.get("lines", []):
                    spans = line.get("spans", [])
                    if len(spans) != 1:
                        raise UnsupportedEditorPDF("Mixed-font or fragmented lines unsupported")
                    span = spans[0]
                    text = str(span["text"])
                    font = _FONTS.get(str(span["font"]))
                    if not text or font is None:
                        raise UnsupportedEditorPDF("Unrecognized text span")
                    size = float(span["size"])
                    if shown_index >= len(shown):
                        raise UnsupportedEditorPDF("Extracted lines exceed verified text shows")
                    source_text, x, y, source_size = shown[shown_index]
                    shown_index += 1
                    origin = span.get("origin")
                    if (
                        source_text != text
                        or origin is None
                        or abs(x - float(origin[0])) > 0.25
                        or abs(page.rect.height - y - float(origin[1])) > 0.25
                        or abs(source_size - size) > 0.01
                    ):
                        raise UnsupportedEditorPDF("Text show is not fully accounted for")
                    bbox = tuple(float(value) for value in line["bbox"])
                    keep = (
                        _preserved_positions(
                            text,
                            bbox=bbox,
                            page_width=page.rect.width,
                            page_height=page.rect.height,
                        )
                        if strategy in {"structural", "balanced"}
                        else set()
                    )
                    if strategy == "balanced":
                        replacement = _balanced_replacement(text, keep, font, size, rng)
                    else:
                        replacement = "".join(
                            char if i in keep else _substitute(char, font, size, strategy, rng)
                            for i, char in enumerate(text)
                        )
                    if replacement == text and not keep:
                        raise UnsupportedEditorPDF("Unmodified nonstructural line")
                    edits.append(
                        LineEdit(
                            page_index,
                            text,
                            replacement,
                            (
                                (float(bbox[0]) + float(bbox[2])) / 2,
                                (float(bbox[1]) + float(bbox[3])) / 2,
                            ),
                        )
                    )
            if shown_index != len(shown):
                raise UnsupportedEditorPDF("Unextracted source text is unsupported")
    return edits


def transform_with_pdf_edit_engine(
    source: Path, destination: Path, strategy: Strategy, *, seed: int | None = None
) -> EditorSummary:
    """Replace every extracted line using upstream content-stream edits.

    A fresh nonincremental PDF with generic metadata is written only after
    every edit succeeds. Complex/unverified sources are rejected.
    """
    if strategy not in ("random", "width", "structural", "balanced"):
        raise ValueError("Unknown replacement strategy")
    source, destination = Path(source), Path(destination)
    if destination.exists() or source.resolve() == destination.resolve():
        raise FileExistsError("Destination must be a new path")
    edits = _planned_lines(source, strategy, seed=seed)
    try:
        from pdf_edit_engine import find, replace
    except ImportError as exc:
        raise RuntimeError("Install pinned pdf-edit-engine in an isolated environment") from exc

    font_preserved = 0
    generic_lines = 0
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pdf-editor-poc-", dir=destination.parent) as tmp:
        scratch = Path(tmp)
        current = source
        for index, edit in enumerate(edits):
            if edit.text == edit.replacement:
                generic_lines += 1
                continue
            try:
                matches = find(str(current), edit.text, page=edit.page)
            except Exception:
                raise UnsupportedEditorPDF("Upstream editor could not search a line") from None
            if not matches:
                raise UnsupportedEditorPDF("Upstream editor could not locate a source line")
            with fitz.open(current) as doc:
                page_height = doc[edit.page].rect.height
            candidates = [
                (
                    abs(
                        page_height
                        - (match.bounding_box[1] + match.bounding_box[3]) / 2
                        - edit.center[1]
                    ),
                    abs((match.bounding_box[0] + match.bounding_box[2]) / 2 - edit.center[0]),
                    match,
                )
                for match in matches
            ]
            vertical, horizontal, chosen = min(candidates, key=lambda item: (item[0], item[1]))
            if vertical > 15 or horizontal > 70:
                raise UnsupportedEditorPDF(f"Upstream match location is ambiguous at line {index}")
            next_path = scratch / f"step-{index:04d}.pdf"
            try:
                result = replace(
                    str(current), chosen, edit.replacement, str(next_path), reflow=False
                )
            except Exception:
                raise UnsupportedEditorPDF("Upstream editor could not replace a line") from None
            if not result.success or not next_path.is_file():
                raise UnsupportedEditorPDF("Upstream edit failed or was refused")
            if (
                not result.fidelity_report.font_preserved
                or result.fidelity_report.overflow_detected
                or result.fidelity_report.reflow_applied
                or result.fidelity_report.glyphs_missing
            ):
                raise UnsupportedEditorPDF(
                    "Upstream edit changed fonts or triggered layout degradation"
                )
            font_preserved += 1
            current = next_path

        final_stage = scratch / "sanitized-id.pdf"
        _sanitize_metadata_and_id(
            current, final_stage, "SYNTHETIC PDF editor adaptation experiment"
        )
        with fitz.open(final_stage) as doc:
            actual = [
                str(span["text"])
                for page in doc
                for block in page.get_text("dict").get("blocks", [])
                for line in block.get("lines", [])
                for span in line.get("spans", [])
            ]
        if actual != [edit.replacement for edit in edits]:
            raise UnsupportedEditorPDF("Extracted output differs from planned replacement lines")
        os.link(final_stage, destination)
    return EditorSummary(strategy, len(edits) - generic_lines, generic_lines, font_preserved)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument(
        "--strategy", choices=("random", "width", "structural", "balanced"), required=True
    )
    parser.add_argument("--seed", type=int, help="Deterministic text seed for synthetic tests")
    args = parser.parse_args()
    print(
        transform_with_pdf_edit_engine(args.source, args.destination, args.strategy, seed=args.seed)
    )
    print("Synthetic experiment only; output is not certified anonymous or confidential.")


if __name__ == "__main__":
    main()
