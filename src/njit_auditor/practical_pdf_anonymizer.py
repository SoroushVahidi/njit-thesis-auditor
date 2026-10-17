"""Local content anonymization for inspectable, text based academic PDFs.

The PDF editor is an optional, separately installed MIT dependency. Inputs are
never sent to a service. Unsupported content is refused before publication.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import logging
import os
import random
import re
import string
import tempfile
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pymupdf as fitz
from pypdf import PdfReader
from pypdf.generic import ContentStream, DictionaryObject


class UnsupportedPDF(ValueError):
    """The source cannot be safely edited within the supported grammar."""


_GENERIC = {
    "ABSTRACT",
    "TABLE OF CONTENTS",
    "LIST OF FIGURES",
    "LIST OF TABLES",
    "REFERENCES",
    "ACKNOWLEDGEMENTS",
    "APPROVAL PAGE",
    "BIOGRAPHICAL SKETCH",
}
_PREFIX = re.compile(
    r"^(?:(?:CHAPTER|APPENDIX)\s+(?:\d+|[A-Z])|(?:Table|Figure)\s+\d+(?:\.\d+)*)\b",
    re.IGNORECASE,
)
_FOLIO = re.compile(r"(?:\d{1,4}|[ivxlcdm]{1,8})$")
_DANGEROUS_OPERATORS = {b"Do", b"BI", b"ID", b"EI", b"BDC", b"BMC", b"DP", b"MP"}
_SAFE_OPERATORS = {
    b"q",
    b"Q",
    b"cm",
    b"w",
    b"J",
    b"j",
    b"M",
    b"d",
    b"ri",
    b"i",
    b"gs",
    b"CS",
    b"cs",
    b"SC",
    b"SCN",
    b"sc",
    b"scn",
    b"G",
    b"g",
    b"RG",
    b"rg",
    b"K",
    b"k",
    b"BT",
    b"ET",
    b"Tc",
    b"Tw",
    b"Tz",
    b"TL",
    b"Tf",
    b"Tr",
    b"Ts",
    b"Td",
    b"TD",
    b"Tm",
    b"T*",
    b"Tj",
    b"TJ",
    b"'",
    b'"',
}
_MAX_BYTES = 100 * 1024 * 1024
_MAX_PAGES = 250
_BASE14 = {
    "helvetica": "helv",
    "helveticabold": "hebo",
    "helveticaoblique": "heit",
    "timesroman": "tiro",
    "timesbold": "tibo",
    "timesitalic": "tiit",
    "timesbolditalic": "tibi",
    "courier": "cour",
    "courierbold": "cobo",
    "courieroblique": "coit",
    "courierboldoblique": "cobi",
}


def _positions_to_keep(text: str, box: fitz.Rect, page: fitz.Page) -> set[int]:
    keep: set[int] = set()
    for label in _GENERIC:
        if text.upper().startswith(label) and (
            len(text) == len(label) or text[len(label)] in " :.-\t"
        ):
            keep.update(range(len(label)))
    if (
        _FOLIO.fullmatch(text)
        and box.y0 >= page.cropbox.height * 0.84
        and abs((box.x0 + box.x1) / 2 - page.cropbox.width / 2) < page.cropbox.width * 0.2
    ):
        return set(range(len(text)))
    match = _PREFIX.search(text)
    if match:
        keep.update(range(*match.span()))
    if "..." in text:
        match = _FOLIO.search(text)
        if match:
            keep.update(range(*match.span()))
    return keep


def _font_key(name: str) -> str:
    key = re.sub(r"[^a-z0-9]", "", re.sub(r"^[A-Z]{6}\+", "", name).lower())
    return re.sub(r"(?:book|regular)$", "", key)


def _font_for_span(doc: fitz.Document, page: fitz.Page, name: str, text: str) -> fitz.Font:
    key = _font_key(name)
    for xref, _ext, _kind, base, _resource, _encoding, _referencer in page.get_fonts(full=True):
        candidate = _font_key(base)
        if candidate == key or candidate.startswith(key) or key.startswith(candidate):
            try:
                extracted = doc.extract_font(xref)
                if extracted[3]:
                    font = fitz.Font(fontbuffer=extracted[3])
                    if all(font.has_glyph(ord(char)) for char in text if char.isalnum()):
                        return font
                    # Subset PDFs often remove the Unicode cmap entirely.
                    # The pinned editor can extend from an exact local font.
                    from pdf_edit_engine.system_fonts import find_font

                    candidates = [
                        name,
                        name.replace(" ", ""),
                        name.removesuffix(" Book").removesuffix(" Regular").replace(" ", ""),
                    ]
                    installed = next(
                        (path for candidate in candidates if (path := find_font(candidate))), None
                    )
                    if installed:
                        return fitz.Font(fontfile=installed)
                    raise UnsupportedPDF(
                        f"Font {name!r} is subsetted without a usable local full font"
                    )
            except UnsupportedPDF:
                raise
            except (RuntimeError, ValueError) as exc:
                raise UnsupportedPDF(f"Font {name!r} cannot be measured") from exc
    # PDF Base14 fonts have no embedded font program.
    if key in _BASE14:
        return fitz.Font(fontname=_BASE14[key])
    raise UnsupportedPDF(f"Font {name!r} has no usable embedded program")


def _validate_font_resources(resources: DictionaryObject, where: str) -> None:
    fonts_ref = resources.get("/Font")
    if fonts_ref is None:
        return
    fonts = fonts_ref.get_object()
    if not isinstance(fonts, DictionaryObject):
        raise UnsupportedPDF(f"{where}: malformed font resources")
    font_keys = {
        "/Type", "/Subtype", "/Name", "/BaseFont", "/Encoding", "/FirstChar",
        "/LastChar", "/Widths", "/FontDescriptor", "/ToUnicode", "/DescendantFonts",
        "/CIDSystemInfo", "/DW", "/W", "/DW2", "/W2", "/CIDToGIDMap",
    }
    descriptor_keys = {
        "/Type", "/FontName", "/FontFamily", "/FontStretch", "/FontWeight",
        "/Flags", "/FontBBox", "/ItalicAngle", "/Ascent", "/Descent",
        "/Leading", "/CapHeight", "/XHeight", "/StemV", "/StemH",
        "/AvgWidth", "/MaxWidth", "/MissingWidth", "/FontFile", "/FontFile2",
        "/FontFile3", "/CharSet", "/Style", "/Lang", "/CIDSet",
    }
    stream_keys = {
        "/Filter", "/Length", "/DecodeParms", "/Length1", "/Length2",
        "/Length3", "/Subtype", "/Type", "/CMapName", "/CIDSystemInfo",
    }

    def inspect_font(font_ref: Any) -> None:
        font = font_ref.get_object()
        if not isinstance(font, DictionaryObject) or set(font) - font_keys:
            raise UnsupportedPDF(f"{where}: unverified font dictionary")
        for related in font.get("/DescendantFonts", []):
            inspect_font(related)
        descriptor_ref = font.get("/FontDescriptor")
        if descriptor_ref is not None:
            descriptor = descriptor_ref.get_object()
            if not isinstance(descriptor, DictionaryObject) or set(descriptor) - descriptor_keys:
                raise UnsupportedPDF(f"{where}: unverified font descriptor")
            for key in ("/FontFile", "/FontFile2", "/FontFile3", "/CIDSet"):
                if key in descriptor:
                    embedded = descriptor[key].get_object()
                    if not isinstance(embedded, DictionaryObject) or set(embedded) - stream_keys:
                        raise UnsupportedPDF(f"{where}: unverified embedded font stream")
        if "/ToUnicode" in font:
            unicode_map = font["/ToUnicode"].get_object()
            if not isinstance(unicode_map, DictionaryObject) or set(unicode_map) - stream_keys:
                raise UnsupportedPDF(f"{where}: unverified Unicode map stream")
        if "/CIDSystemInfo" in font:
            cid_info = font["/CIDSystemInfo"].get_object()
            if not isinstance(cid_info, DictionaryObject) or set(cid_info) - {
                "/Registry", "/Ordering", "/Supplement",
            }:
                raise UnsupportedPDF(f"{where}: unverified CID system information")
        encoding = font.get("/Encoding")
        if encoding is not None:
            encoding = encoding.get_object()
            if isinstance(encoding, DictionaryObject) and set(encoding) - {
                "/Type", "/BaseEncoding", "/Differences",
            }:
                raise UnsupportedPDF(f"{where}: unverified font encoding")

    for font_ref in fonts.values():
        inspect_font(font_ref)


def _preflight(
    source: Path,
) -> tuple[list[dict[str, Any]], dict[str, int], dict[int, list[tuple[float, ...]]]]:
    if not source.is_file() or source.stat().st_size > _MAX_BYTES:
        raise UnsupportedPDF("Input is absent or exceeds the 100 MB limit")
    if source.read_bytes()[:5] != b"%PDF-":
        raise UnsupportedPDF("Input is not a PDF")
    try:
        reader = PdfReader(source, strict=True)
    except Exception as exc:
        raise UnsupportedPDF("PDF parser cannot read the input") from exc
    if reader.is_encrypted:
        raise UnsupportedPDF("Encrypted PDFs are unsupported")
    root = reader.trailer["/Root"]
    if not isinstance(root, DictionaryObject):
        raise UnsupportedPDF("Unverified PDF catalog")
    risky_root = set(root) & {
        "/AcroForm",
        "/Names",
        "/OpenAction",
        "/AA",
        "/Outlines",
        "/StructTreeRoot",
        "/OCProperties",
        "/Metadata",
        "/Collection",
        "/PieceInfo",
        "/Perms",
    }
    if risky_root:
        raise UnsupportedPDF(f"Catalog structure unsupported: {', '.join(sorted(risky_root))}")
    if "/Info" in root:
        info = root["/Info"]
        if not isinstance(info, DictionaryObject) or set(info) != {"/Producer"}:
            raise UnsupportedPDF("Unverified inline catalog metadata")
    if set(root) - {
        "/Type",
        "/Pages",
        "/PageLayout",
        "/PageMode",
        "/Lang",
        "/ViewerPreferences",
        "/Info",
    }:
        raise UnsupportedPDF("Unverified catalog structure")
    # Every reachable page-tree node is retained by a PDF rewrite. Reject
    # custom data here as well as on leaf pages.
    seen_page_nodes: set[int] = set()

    def inspect_page_tree(node: DictionaryObject) -> None:
        if id(node) in seen_page_nodes:
            raise UnsupportedPDF("Cyclic /Pages tree")
        seen_page_nodes.add(id(node))
        allowed = {
            "/Type", "/Parent", "/Kids", "/Count", "/MediaBox", "/CropBox",
            "/Rotate", "/Resources",
        }
        if set(node) - allowed:
            raise UnsupportedPDF("Unverified /Pages tree property or metadata")
        if node.get("/Type") != "/Pages":
            raise UnsupportedPDF("Malformed /Pages tree")
        if "/Resources" in node:
            inherited = node["/Resources"].get_object()
            if not isinstance(inherited, DictionaryObject) or set(inherited) - {
                "/Font", "/ProcSet", "/XObject", "/ColorSpace", "/ExtGState",
            }:
                raise UnsupportedPDF("Unverified /Pages resource dictionary")
            _validate_font_resources(inherited, "/Pages")
        children = node.get("/Kids")
        if not isinstance(children, list):
            raise UnsupportedPDF("Malformed /Pages tree children")
        for child in children:
            actual = child.get_object()
            if not isinstance(actual, DictionaryObject):
                raise UnsupportedPDF("Malformed /Pages tree child")
            if actual.get("/Type") == "/Pages":
                inspect_page_tree(actual)

    page_tree = root.get("/Pages")
    if page_tree is None or not isinstance(page_tree.get_object(), DictionaryObject):
        raise UnsupportedPDF("Missing /Pages tree")
    inspect_page_tree(page_tree.get_object())
    plans: list[dict[str, Any]] = []
    counts: dict[str, int] = defaultdict(int)
    images: dict[int, list[tuple[float, ...]]] = defaultdict(list)
    with fitz.open(source) as doc:
        if doc.needs_pass or doc.is_encrypted or not 0 < len(doc) <= _MAX_PAGES:
            raise UnsupportedPDF("Encrypted, empty, or over 250 page PDF")
        if doc.embfile_count() or doc.is_form_pdf or doc.get_xml_metadata() or doc.get_ocgs():
            raise UnsupportedPDF("Attachment, form, XMP metadata, or optional layer")
        if len(reader.pages) != len(doc):
            raise UnsupportedPDF("PDF parsers disagree on page count")
        for index, page in enumerate(doc):
            if page.first_annot or page.get_links() or list(page.widgets() or []):
                raise UnsupportedPDF(f"Page {index + 1}: annotations, links, or form fields")
            if page.get_xobjects():
                raise UnsupportedPDF(f"Page {index + 1}: Form XObject")
            if page.get_drawings():
                raise UnsupportedPDF(f"Page {index + 1}: vector drawing or diagram")
            blocks = page.get_text("dict", flags=fitz.TEXTFLAGS_DICT)
            image_blocks = [block for block in blocks["blocks"] if block["type"] == 1]
            if image_blocks and not page.get_images(full=True):
                raise UnsupportedPDF(f"Page {index + 1}: inline or unindexed image")
            if page.get_images(full=True) and not image_blocks:
                raise UnsupportedPDF(f"Page {index + 1}: image lacks an occupied region")
            images[index] = [tuple(block["bbox"]) for block in image_blocks]
            if any(
                fitz.Rect(region).width < 80 or fitz.Rect(region).height < 25
                for region in images[index]
            ):
                raise UnsupportedPDF(f"Page {index + 1}: image too small for a legible placeholder")
            if any(
                kind == "ignore-text"
                or (kind in {"fill-image", "stroke-image"} and not image_blocks)
                for kind, _box in page.get_bboxlog()
            ):
                raise UnsupportedPDF(f"Page {index + 1}: hidden text or unlocated image")
            for trace in page.get_texttrace():
                if trace.get("type") == 3 or abs(trace.get("opacity", 1) - 1) > 0.001:
                    raise UnsupportedPDF(f"Page {index + 1}: invisible or translucent text")
            pdf_page = reader.pages[index]
            allowed_page = {
                "/Type",
                "/Parent",
                "/Resources",
                "/Contents",
                "/MediaBox",
                "/CropBox",
                "/Rotate",
            }
            if set(pdf_page) - allowed_page:
                raise UnsupportedPDF(f"Page {index + 1}: unverified page dictionary")
            if set(pdf_page) & {"/Annots", "/AA", "/Metadata", "/PieceInfo", "/Thumb", "/Trans"}:
                raise UnsupportedPDF(f"Page {index + 1}: hidden page structure")
            resources_ref = pdf_page.get("/Resources")
            resources = resources_ref.get_object() if resources_ref is not None else None
            allowed_resources = {"/Font", "/ProcSet"}
            if image_blocks:
                allowed_resources |= {"/XObject", "/ColorSpace", "/ExtGState"}
            if not isinstance(resources, DictionaryObject) or set(resources) - allowed_resources:
                raise UnsupportedPDF(f"Page {index + 1}: nontext or unverified resources")
            _validate_font_resources(resources, f"Page {index + 1}")
            stream = pdf_page.get_contents()
            if stream is None:
                raise UnsupportedPDF(f"Page {index + 1}: no content stream")
            raw_contents = pdf_page["/Contents"]
            streams = raw_contents if isinstance(raw_contents, list) else [raw_contents]
            for raw_stream in streams:
                content_stream = raw_stream.get_object()
                if not isinstance(content_stream, DictionaryObject) or set(content_stream) - {
                    "/Filter", "/Length", "/DecodeParms", "/DL",
                }:
                    raise UnsupportedPDF(f"Page {index + 1}: unverified content stream data")
            for operands, operator in ContentStream(stream, reader).operations:
                if operator == b"Do" and image_blocks:
                    continue
                if operator == b"gs":
                    raise UnsupportedPDF(f"Page {index + 1}: graphics state operator")
                if operator in _DANGEROUS_OPERATORS:
                    raise UnsupportedPDF(
                        f"Page {index + 1}: unsupported content operator {operator.decode()}"
                    )
                if operator not in _SAFE_OPERATORS:
                    raise UnsupportedPDF(
                        f"Page {index + 1}: unverified content operator {operator!r}"
                    )
                if operator == b"Tr" and operands and int(operands[0]) in {3, 7}:
                    raise UnsupportedPDF(f"Page {index + 1}: invisible or clipping text")
            page_spans = []
            for block in blocks["blocks"]:
                if block["type"] == 1:
                    continue
                if block["type"] != 0:
                    raise UnsupportedPDF(f"Page {index + 1}: nontext block")
                for line in block["lines"]:
                    if line["wmode"] != 0 or abs(line["dir"][1]) > 0.001:
                        raise UnsupportedPDF(f"Page {index + 1}: vertical or transformed text")
                    line_text = "".join(span["text"] for span in line["spans"])
                    line_keep = _positions_to_keep(line_text, fitz.Rect(line["bbox"]), page)
                    offset = 0
                    for span in line["spans"]:
                        value = span["text"]
                        if value.strip():
                            if "\ufffd" in value or any(ord(c) < 32 for c in value):
                                raise UnsupportedPDF(f"Page {index + 1}: undecodable text")
                            page_spans.append(
                                {
                                    "page": index,
                                    "text": value,
                                    "bbox": tuple(span["bbox"]),
                                    "origin": tuple(span["origin"]),
                                    "color": span["color"],
                                    "font": span["font"],
                                    "flags": span["flags"],
                                    "size": span["size"],
                                    "keep": {
                                        i - offset
                                        for i in line_keep
                                        if offset <= i < offset + len(value)
                                    },
                                }
                            )
                            counts[span["font"]] += 1
                        offset += len(value)
            extracted_count = sum(len(item["text"]) for item in page_spans)
            traced_count = sum(len(span["chars"]) for span in page.get_texttrace())
            if traced_count > extracted_count:
                raise UnsupportedPDF(f"Page {index + 1}: unextracted text glyphs")
            if not page_spans and traced_count:
                raise UnsupportedPDF(f"Page {index + 1}: no extractable text")
            if image_blocks and not page_spans:
                raise UnsupportedPDF(f"Page {index + 1}: image-only scan has no searchable text")
            for span in page_spans:
                text_rect = fitz.Rect(span["bbox"])
                if any((text_rect & fitz.Rect(region)).get_area() > 1 for region in images[index]):
                    raise UnsupportedPDF(
                        f"Page {index + 1}: text overlaps an image; image layering unsupported"
                    )
            plans.extend(page_spans)
    if not plans:
        raise UnsupportedPDF("No searchable PDF text")
    return plans, counts, images


def _replacement(
    text: str,
    keep: set[int],
    font: fitz.Font,
    size: float,
    alphabet: set[str],
    rng: random.Random,
    strategy: str,
) -> str:
    """Sample compatible glyphs while bounding cumulative position drift."""
    widths: dict[str, float] = {}
    candidates = alphabet | set(text) | set(string.ascii_letters + string.digits)
    candidates |= set("αβγδεζηθικλμνξοπρστυφχψωΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ")
    for char in sorted(candidates):
        if char.isalnum() and font.has_glyph(ord(char)):
            widths[char] = font.text_length(char, fontsize=size)
    # Error is the advance from the original prefix. Holding several nearby
    # prefixes avoids the large internal shifts caused by end-only balancing.
    beam: list[tuple[float, float, float, str]] = [(0.0, 0.0, 0.0, "")]
    for index, char in enumerate(text):
        if index in keep or not char.isalnum():
            beam = [(error, peak, total, output + char) for error, peak, total, output in beam]
            continue
        choices = [
            c
            for c in widths
            if c != char
            and c.isdigit() == char.isdigit()
            and c.isupper() == char.isupper()
            and c.islower() == char.islower()
            and (c.isascii() == char.isascii())
        ]
        if not choices:
            raise UnsupportedPDF("A font has too few compatible glyphs to replace substantive text")
        choices.sort()
        rng.shuffle(choices)
        source_width = widths.get(char, font.text_length(char, fontsize=size))
        choices.sort(key=lambda candidate: abs(widths[candidate] - source_width))
        choices = choices[: (16 if strategy == "random" else 12)]
        states: dict[int, tuple[float, float, float, str]] = {}
        for error, peak, total, output in beam:
            for candidate in choices:
                delta = widths[candidate] - source_width
                next_error = error + delta
                state = (
                    next_error,
                    max(peak, abs(next_error)),
                    total + abs(delta),
                    output + candidate,
                )
                bucket = round(next_error * 20)
                previous = states.get(bucket)
                if previous is None or (state[1], state[2]) < (previous[1], previous[2]):
                    states[bucket] = state
        beam = sorted(
            states.values(),
            key=lambda state: (abs(state[0]) + state[1] * 0.5 + state[2] * 0.01, state[1]),
        )[:192]
    target = font.text_length(text, fontsize=size)
    measured = [(abs(font.text_length(state[3], fontsize=size) - target), state) for state in beam]
    minimum = min(error for error, _state in measured)
    close = [state for error, state in measured if error <= minimum + 0.05]
    result = min(close, key=lambda state: (state[1], state[2]))[3]
    if result == text and len(keep) != len(text):
        raise UnsupportedPDF("Substantive span could not be changed")
    return result


def _audit_signature(path: Path) -> Counter[tuple[Any, ...]]:
    from njit_auditor.audit_runner import run_pdf_audit_full

    findings: Counter[tuple[Any, ...]] = Counter()
    for finding in run_pdf_audit_full(path):
        if finding.severity.value == "PASS":
            continue
        def geometry(field: str) -> tuple[float, ...]:
            return tuple(
                round(float(value), 1)
                for value in re.findall(r"-?\d+(?:\.\d+)?", str(finding.details.get(field) or ""))
            )

        classification_fields = (
            "confidence", "triage_tier", "side", "margin_content_kind", "page_context",
            "context", "heading_gap_position", "centered", "bold", "all_caps",
            "level", "classification", "section_key",
        )
        key = (
            finding.rule_id,
            finding.page,
            str(finding.details.get("issue_type", "")),
            finding.severity.value,
            geometry("bbox"),
            geometry("highlight_bboxes"),
            tuple(str(finding.details.get(field, "")) for field in classification_fields),
        )
        findings[key] += 1
    return findings


def _verify(
    source: Path,
    output: Path,
    planned: list[dict[str, Any]],
    image_regions: dict[int, list[tuple[float, ...]]],
    *,
    auditor: bool,
) -> dict[str, Any]:
    import pikepdf

    metrics: dict[str, Any] = {
        "pages": 0,
        "spans": 0,
        "text_blocks": 0,
        "lines": 0,
        "max_line_start_delta_pt": 0.0,
        "max_line_end_delta_pt": 0.0,
        "max_baseline_delta_pt": 0.0,
        "max_adjacent_spacing_delta_pt": 0.0,
        "max_font_size_delta_pt": 0.0,
        "font_mismatches": 0,
        "style_flag_mismatches": 0,
    }
    with fitz.open(source) as a, fitz.open(output) as b:
        if len(a) != len(b):
            raise UnsupportedPDF("Verification: page count changed")
        metrics["pages"] = len(a)
        for first, second in zip(a, b, strict=True):
            if (
                first.mediabox != second.mediabox
                or first.cropbox != second.cropbox
                or first.rotation != second.rotation
            ):
                raise UnsupportedPDF("Verification: page boxes or rotation changed")
        source_layout = [page.get_text("dict")["blocks"] for page in a]
        output_layout = [page.get_text("dict")["blocks"] for page in b]
        expected_images = sum(len(regions) for regions in image_regions.values())
        actual_images = [
            (number, tuple(block["bbox"]))
            for number, blocks in enumerate(output_layout)
            for block in blocks
            if block["type"] == 1
        ]
        if len(actual_images) != expected_images:
            raise UnsupportedPDF("Verification: synthetic image placeholder count changed")
        for page_number, box in actual_images:
            if not any(
                max(abs(x - y) for x, y in zip(box, region, strict=True)) <= 1
                for region in image_regions[page_number]
            ):
                raise UnsupportedPDF("Verification: synthetic image placeholder moved")
        source_block_count = sum(
            sum(block["type"] == 0 for block in blocks) for blocks in source_layout
        )
        output_block_count = sum(
            sum(block["type"] == 0 for block in blocks) for blocks in output_layout
        )
        source_lines_by_page = [
            [line for block in blocks if block["type"] == 0 for line in block["lines"]]
            for blocks in source_layout
        ]
        output_lines_by_page = [
            [line for block in blocks if block["type"] == 0 for line in block["lines"]]
            for blocks in output_layout
        ]
        source_lines = [line for lines in source_lines_by_page for line in lines]
        output_lines = [line for lines in output_lines_by_page for line in lines]
        if source_block_count != output_block_count or len(source_lines) != len(output_lines):
            raise UnsupportedPDF("Verification: text block or line count changed")
        metrics["text_blocks"] = source_block_count
        metrics["lines"] = len(source_lines)
        for old_lines, new_lines in zip(source_lines_by_page, output_lines_by_page, strict=True):
            for index in range(1, len(old_lines)):
                old_gap = old_lines[index]["bbox"][1] - old_lines[index - 1]["bbox"][1]
                new_gap = new_lines[index]["bbox"][1] - new_lines[index - 1]["bbox"][1]
                metrics["max_adjacent_spacing_delta_pt"] = max(
                    metrics["max_adjacent_spacing_delta_pt"], abs(old_gap - new_gap)
                )
        rendered = [
            span
            for blocks in output_layout
            for block in blocks
            if block["type"] == 0
            for line in block["lines"]
            for span in line["spans"]
            if span["text"].strip()
        ]
        if len(rendered) != len(planned):
            raise UnsupportedPDF("Verification: text span count changed")
        metrics["spans"] = len(rendered)
        for old, new in zip(planned, rendered, strict=True):
            if new["text"] != old["replacement"]:
                raise UnsupportedPDF("Verification: a planned text span was not replaced")
            x0, y0, x1, y1 = old["bbox"]
            nx0, ny0, nx1, ny1 = new["bbox"]
            metrics["max_line_start_delta_pt"] = max(
                metrics["max_line_start_delta_pt"], abs(x0 - nx0), abs(y0 - ny0)
            )
            metrics["max_line_end_delta_pt"] = max(
                metrics["max_line_end_delta_pt"], abs(x1 - nx1), abs(y1 - ny1)
            )
            metrics["max_font_size_delta_pt"] = max(
                metrics["max_font_size_delta_pt"], abs(old["size"] - new["size"])
            )
            metrics["max_baseline_delta_pt"] = max(
                metrics["max_baseline_delta_pt"],
                abs(old["origin"][0] - new["origin"][0]),
                abs(old["origin"][1] - new["origin"][1]),
            )
            metrics["font_mismatches"] += _font_key(old["font"]) != _font_key(new["font"])
            metrics["style_flag_mismatches"] += old["flags"] != new["flags"]
            if old["color"] != new["color"]:
                raise UnsupportedPDF("Verification: text color changed")
        if (
            metrics["max_line_start_delta_pt"] > 1.0
            or metrics["max_line_end_delta_pt"] > 4.0
            or metrics["max_font_size_delta_pt"] > 0.1
            or metrics["font_mismatches"]
            or metrics["style_flag_mismatches"]
        ):
            raise UnsupportedPDF("Verification: typography or line geometry changed materially")

        def character_boxes(doc: fitz.Document) -> list[tuple[float, float, float, float]]:
            return [
                tuple(char["bbox"])
                for page in (doc[i] for i in range(len(doc)))
                for block in page.get_text("rawdict")["blocks"]
                if block["type"] == 0
                for line in block["lines"]
                for span in line["spans"]
                for char in span["chars"]
            ]

        old_chars, new_chars = character_boxes(a), character_boxes(b)
        if len(old_chars) != len(new_chars):
            raise UnsupportedPDF("Verification: searchable character count changed")
        drifts = sorted(
            max(abs(x - y) for x, y in zip(old_box, new_box, strict=True))
            for old_box, new_box in zip(old_chars, new_chars, strict=True)
        )
        metrics["characters"] = len(old_chars)
        metrics["character_bbox_drift_p95_pt"] = (
            drifts[int(0.95 * (len(drifts) - 1))] if drifts else 0.0
        )
        metrics["character_bbox_drift_max_pt"] = drifts[-1] if drifts else 0.0
        if (
            metrics["character_bbox_drift_p95_pt"] > 5.0
            or metrics["character_bbox_drift_max_pt"] > 8.0
        ):
            raise UnsupportedPDF("Verification: character positions changed materially")
        output_text = "\n".join(page.get_text() for page in b)
        source_text = "\n".join(page.get_text() for page in a)

        class WarningCounter(logging.Handler):
            count = 0

            def emit(self, record: logging.LogRecord) -> None:
                if record.levelno >= logging.WARNING:
                    self.count += 1

        parser_log = logging.getLogger("pypdf")
        warning_counter = WarningCounter()
        previous_propagation = parser_log.propagate
        parser_log.addHandler(warning_counter)
        parser_log.propagate = False
        try:
            independent = PdfReader(output, strict=True)
            independent_text = "\n".join(page.extract_text() or "" for page in independent.pages)
        finally:
            parser_log.removeHandler(warning_counter)
            parser_log.propagate = previous_propagation
        if (
            not output_text.strip()
            or not independent_text.strip()
            or len(independent.pages) != len(b)
        ):
            raise UnsupportedPDF("Verification: output is not searchable by independent parser")
        token_pattern = r"\w+|[^\w\s]"
        if Counter(re.findall(token_pattern, output_text)) != Counter(
            re.findall(token_pattern, independent_text)
        ):
            raise UnsupportedPDF("Verification: PDF text parsers disagree on output content")
        # Exact substantive source lines must not survive in the new object graph.
        source_content_lines = {
            line.strip()
            for line in source_text.splitlines()
            if len(line.strip()) >= 8
            and line.strip() not in _GENERIC
            and not _PREFIX.fullmatch(line.strip())
        }
        if any(line in output_text or line in independent_text for line in source_content_lines):
            raise UnsupportedPDF("Verification: an original substantive line survived")
        metadata_values = [
            str(a.metadata.get(key) or "")
            for key in ("title", "author", "subject", "keywords", "creator")
        ]
        with pikepdf.Pdf.open(source) as original_pdf, pikepdf.Pdf.open(output) as pdf:
            original_ids = {bytes(value) for value in original_pdf.trailer.get("/ID", [])}
            output_ids = {bytes(value) for value in pdf.trailer.get("/ID", [])}
            if original_ids & output_ids:
                raise UnsupportedPDF("Verification: source document identifier survived")
            if "/Info" in pdf.trailer or "/Info" in pdf.Root or "/Metadata" in pdf.Root:
                raise UnsupportedPDF("Verification: source metadata survived")
            objects = b"\n".join(
                str(obj).encode("utf-8", errors="replace")
                + (obj.read_bytes() if isinstance(obj, pikepdf.Stream) else b"")
                for obj in pdf.objects
            )
            object_count = len(pdf.objects)
        raw = output.read_bytes()
        sensitive = [value for value in source_content_lines if len(value) >= 12]
        sensitive.extend(value for value in metadata_values if len(value) >= 4)
        representations = [
            re.escape(encoded)
            for value in sensitive
            for encoded in (
                value.encode("utf-8"),
                value.encode("utf-16-be"),
                value.encode("utf-16-le"),
            )
        ]
        if representations and re.search(b"|".join(representations), objects + raw, re.IGNORECASE):
            raise UnsupportedPDF("Verification: source text remains in PDF objects")
        structures = {
            "attachments": b.embfile_count(),
            "form_xobjects": sum(len(page.get_xobjects()) for page in b),
            "annotations": sum(page.first_annot is not None for page in b),
            "xml_metadata": bool(b.get_xml_metadata()),
            "optional_layers": len(b.get_ocgs()),
        }
        if any(structures.values()) or raw.count(b"%%EOF") != 1:
            raise UnsupportedPDF("Verification: residual structure or revision history")
        source_image_hashes = {
            hashlib.sha256(a.extract_image(entry[0])["image"]).digest()
            for page in a
            for entry in page.get_images(full=True)
        }
        output_image_hashes = {
            hashlib.sha256(b.extract_image(entry[0])["image"]).digest()
            for page in b
            for entry in page.get_images(full=True)
        }
        if source_image_hashes & output_image_hashes:
            raise UnsupportedPDF("Verification: original image bytes survived")
        metrics["content_cleanup"] = {
            "independent_parser_searchable": True,
            "independent_parser_tokens_equal": True,
            "independent_parser_warnings": warning_counter.count,
            "recovered_source_lines_or_metadata": 0,
            "residual_structures": structures,
            "synthetic_image_placeholders": expected_images,
            "recovered_source_image_streams": 0,
            "pdf_objects": object_count,
            "eof_markers": 1,
        }
    if auditor:
        before, after = _audit_signature(source), _audit_signature(output)
        lost, introduced = before - after, after - before
        metrics["auditor"] = {
            "source": sum(before.values()),
            "output": sum(after.values()),
            "matched": sum((before & after).values()),
            "lost": sum(lost.values()),
            "introduced": sum(introduced.values()),
            "lost_rules": sorted({key[0] for key in lost}),
            "introduced_rules": sorted({key[0] for key in introduced}),
        }
        if lost or introduced:
            raise UnsupportedPDF("Verification: auditor findings changed")
    return metrics


def _synthetic_placeholder_png(width: float, height: float) -> bytes:
    with fitz.open() as doc:
        page = doc.new_page(width=width, height=height)
        page.draw_rect(page.rect, color=(0.4, 0.4, 0.4), fill=(0.93, 0.93, 0.93))
        for y in range(12, int(height), 16):
            page.draw_line((0, y), (width, y), color=(0.83, 0.83, 0.83), width=0.5)
        label = "SYNTHETIC IMAGE" if width >= 145 else "SYNTHETIC"
        size = min(18.0, max(9.0, height * 0.3))
        while fitz.get_text_length(label, fontname="hebo", fontsize=size) > width - 8:
            size -= 0.5
        if size < 7:
            raise UnsupportedPDF("Image region too small for a legible placeholder")
        text_width = fitz.get_text_length(label, fontname="hebo", fontsize=size)
        x = (width - text_width) / 2
        baseline = height / 2 + size * 0.35
        page.draw_rect(
            fitz.Rect(x - 3, baseline - size - 2, x + text_width + 3, baseline + 3),
            color=(0.4, 0.4, 0.4),
            fill=(1, 1, 1),
        )
        page.insert_text(
            (x, baseline), label, fontname="hebo", fontsize=size, color=(0.2, 0.2, 0.2)
        )
        return page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False).tobytes("png")


def _redraw_with_local_fonts(
    source: Path,
    destination: Path,
    plans: list[dict[str, Any]],
    image_regions: dict[int, list[tuple[float, ...]]],
) -> None:
    """Rebuild text pages for subset fonts or replace raster figures."""
    by_page: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for item in plans:
        by_page[item["page"]].append(item)
    with fitz.open(source) as original, fitz.open() as output:
        for number, old in enumerate(original):
            if old.mediabox.x0 != 0 or old.mediabox.y0 != 0:
                raise UnsupportedPDF("Subset-font redraw needs a zero-origin MediaBox")
            page = output.new_page(width=old.mediabox.width, height=old.mediabox.height)
            if old.cropbox != old.mediabox:
                page.set_cropbox(old.cropbox)
            for box in image_regions[number]:
                region = fitz.Rect(box)
                placeholder = _synthetic_placeholder_png(region.width, region.height)
                page.insert_image(region, stream=placeholder, keep_proportion=False)
            resources: dict[str, str] = {}
            for item in by_page[number]:
                key = _font_key(item["font"])
                if key in _BASE14:
                    resource = _BASE14[key]
                else:
                    resource = resources.get(item["font"], "")
                    if not resource:
                        resource = f"AnonFont{len(resources)}"
                        font = _font_for_span(original, old, item["font"], item["text"])
                        page.insert_font(fontname=resource, fontbuffer=font.buffer)
                        resources[item["font"]] = resource
                color_number = int(item["color"])
                color = (
                    (color_number >> 16 & 255) / 255,
                    (color_number >> 8 & 255) / 255,
                    (color_number & 255) / 255,
                )
                page.insert_text(
                    item["origin"],
                    item["replacement"],
                    fontname=resource,
                    fontsize=item["size"],
                    color=color,
                )
            page.set_rotation(old.rotation)
        output.save(destination, garbage=4, deflate=True)


def anonymize(
    source: Path,
    destination: Path,
    *,
    authorized: bool = False,
    seed: int = 0,
    strategy: str = "width",
    verify_auditor: bool = False,
    verbose: bool = False,
) -> dict[str, Any]:
    """Create a fresh, searchable output only after every check succeeds."""
    if not authorized:
        raise UnsupportedPDF(
            "Confirm permission for local processing with --authorized-local-input"
        )
    try:
        if importlib.metadata.version("pdf-edit-engine") != "0.2.0":
            raise UnsupportedPDF("Install pdf-edit-engine 0.2.0 from pinned commit cee1d2cc")
    except importlib.metadata.PackageNotFoundError as exc:
        raise UnsupportedPDF("Install pinned pdf-edit-engine 0.2.0") from exc
    try:
        import pikepdf
        from pdf_edit_engine import Edit, batch_replace, find, replace
    except ImportError as exc:
        raise UnsupportedPDF(
            "Install the anonymizer dependencies: pikepdf and pdf-edit-engine"
        ) from exc
    if strategy not in {"random", "width"}:
        raise ValueError("Strategy must be random or width")
    source, destination = Path(source), Path(destination)
    if destination.exists() or source.resolve() == destination.resolve():
        raise FileExistsError("Output must be a new path distinct from input")
    if source.parent.resolve() == destination.parent.resolve() and source.name == destination.name:
        raise FileExistsError("Output cannot overwrite input")
    started = time.monotonic()
    planned, font_counts, image_regions = _preflight(source)
    if verbose:
        print(
            f"Preflight accepted {len(planned)} text spans across {len(font_counts)} fonts",
            flush=True,
        )
    rng = random.Random(seed)
    with fitz.open(source) as doc:
        chars: dict[str, set[str]] = defaultdict(set)
        for item in planned:
            chars[item["font"]].update(item["text"])
        for item in planned:
            page = doc[item["page"]]
            font = _font_for_span(doc, page, item["font"], item["text"])
            item["replacement"] = _replacement(
                item["text"], item["keep"], font, item["size"], chars[item["font"]], rng, strategy
            )
    destination.parent.mkdir(parents=True, exist_ok=True)
    events: Counter[str] = Counter()

    def accept_result(result: Any, page_number: int) -> None:
        if not result.success:
            raise UnsupportedPDF(f"Page {page_number + 1}: upstream replacement failed")
        report = result.fidelity_report
        for event in report.degradations:
            events[f"{event.kind}:{event.severity}"] += 1
        if report.overflow_detected:
            events["overflow_detected:warning"] += 1
        if (
            not report.font_preserved
            or report.font_substituted
            or report.reflow_applied
            or any(e.severity == "error" for e in report.degradations)
        ):
            kinds = ", ".join(f"{e.kind}:{e.severity}" for e in report.degradations)
            raise UnsupportedPDF(
                f"Page {page_number + 1}: upstream font/layout degradation ({kinds or 'unknown'})"
            )

    def distance(item: dict[str, Any], match: Any, doc: fitz.Document) -> float:
        page = doc[item["page"]]
        box = item["bbox"]
        target = (
            box[0] + page.cropbox.x0,
            page.mediabox.height - page.cropbox.y0 - (box[1] + box[3]) / 2,
        )
        return abs(match.bounding_box[0] - target[0]) + abs(
            (match.bounding_box[1] + match.bounding_box[3]) / 2 - target[1]
        )

    with tempfile.TemporaryDirectory(prefix="anonymize-", dir=destination.parent) as tmp:
        scratch = Path(tmp)
        current = source
        # Upstream batch_replace writes once. It is safe for globally unique,
        # nonoverlapping show operators; ambiguous spans use positioned edits.
        candidates: list[tuple[int, Any]] = []
        search_cache: dict[str, list[Any]] = {}
        image_placeholder_count = sum(len(regions) for regions in image_regions.values())
        redraw_required = image_placeholder_count > 0
        if not redraw_required:
            with fitz.open(source) as doc:
                for index, item in enumerate(planned):
                    if item["replacement"] == item["text"]:
                        continue
                    try:
                        if item["text"] not in search_cache:
                            search_cache[item["text"]] = find(str(source), item["text"])
                        matches = search_cache[item["text"]]
                    except Exception as exc:
                        raise UnsupportedPDF(
                            f"Page {item['page'] + 1}: upstream text search failed"
                        ) from exc
                    if len(matches) == 1 and matches[0].page_number == item["page"]:
                        if distance(item, matches[0], doc) <= 15:
                            candidates.append((index, matches[0]))
                    elif not matches:
                        redraw_required = True
        refs: Counter[tuple[int, int]] = Counter(
            (match.page_number, ref) for _index, match in candidates for ref in match.operator_refs
        )
        batch_indices = {
            index
            for index, match in candidates
            if all(refs[match.page_number, ref] == 1 for ref in match.operator_refs)
        }
        method = "upstream-stream-edit"
        if redraw_required:
            redraw_stage = scratch / "redraw.pdf"
            if verbose:
                print("Using local redraw for subset font or image placeholders", flush=True)
            _redraw_with_local_fonts(source, redraw_stage, planned, image_regions)
            current = redraw_stage
            batch_indices = set(range(len(planned)))
            method = (
                "local-redraw-with-synthetic-images"
                if image_placeholder_count
                else "local-font-redraw"
            )
        if batch_indices and not redraw_required:
            selected = sorted(batch_indices)
            if verbose:
                print(f"Batch editing {len(selected)} unique spans", flush=True)
            batch_stage = scratch / "batch.pdf"
            try:
                results = batch_replace(
                    str(source),
                    [Edit(planned[i]["text"], planned[i]["replacement"]) for i in selected],
                    str(batch_stage),
                    reflow=False,
                )
            except Exception as exc:
                raise UnsupportedPDF("Upstream batch replacement failed") from exc
            if len(results) != len(selected) or not batch_stage.is_file():
                raise UnsupportedPDF("Upstream batch replacement incomplete")
            for i, result in zip(selected, results, strict=True):
                accept_result(result, planned[i]["page"])
            current = batch_stage
        for index, item in enumerate(planned):
            if item["replacement"] == item["text"] or index in batch_indices:
                continue
            try:
                matches = find(str(current), item["text"], page=item["page"])
            except Exception as exc:
                raise UnsupportedPDF(
                    f"Page {item['page'] + 1}: upstream text search failed"
                ) from exc
            if not matches:
                raise UnsupportedPDF(
                    f"Page {item['page'] + 1}: upstream editor cannot locate text span"
                )
            with fitz.open(current) as doc:
                chosen = min(matches, key=lambda m: distance(item, m, doc))
                match_distance = distance(item, chosen, doc)
            if match_distance > 15:
                raise UnsupportedPDF(f"Page {item['page'] + 1}: ambiguous upstream text match")
            next_path = scratch / f"edit-{index:06d}.pdf"
            try:
                result = replace(
                    str(current), chosen, item["replacement"], str(next_path), reflow=False
                )
            except Exception as exc:
                raise UnsupportedPDF(
                    f"Page {item['page'] + 1}: upstream replacement failed"
                ) from exc
            if not next_path.is_file():
                raise UnsupportedPDF(f"Page {item['page'] + 1}: upstream output missing")
            accept_result(result, item["page"])
            if current != source:
                current.unlink()
            current = next_path
            if verbose and (index + 1) % 25 == 0:
                print(f"Edited {index + 1}/{len(planned)} spans", flush=True)
        stage = scratch / "clean.pdf"
        with pikepdf.Pdf.open(current) as pdf:
            if "/Info" in pdf.trailer:
                del pdf.trailer["/Info"]
            if "/Info" in pdf.Root:
                del pdf.Root["/Info"]
            if "/Metadata" in pdf.Root:
                del pdf.Root["/Metadata"]
            for key in ("/PageLayout", "/PageMode", "/Lang", "/ViewerPreferences"):
                if key in pdf.Root:
                    del pdf.Root[key]
            pdf.trailer["/ID"] = pikepdf.Array(
                [pikepdf.String(os.urandom(16)), pikepdf.String(os.urandom(16))]
            )
            pdf.save(stage, linearize=False, compress_streams=True)
        metrics = _verify(source, stage, planned, image_regions, auditor=verify_auditor)
        os.link(stage, destination)
    return {
        "status": "COMPLETED_SUCCESS",
        "description": "content-anonymized PDF with formatting preserved",
        "pages": metrics["pages"],
        "spans": metrics["spans"],
        "font_families": len(font_counts),
        "font_spans": dict(font_counts),
        "strategy": strategy,
        "seed": seed,
        "upstream_degradations": dict(events),
        "batched_spans": 0 if redraw_required else len(batch_indices),
        "method": method,
        "synthetic_image_placeholders": image_placeholder_count,
        "fidelity": metrics,
        "duration_seconds": round(time.monotonic() - started, 3),
        "limitations": "Text PDFs and simple raster figures; no unlinkability guarantee",
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="anonymize", description="Local PDF content anonymization"
    )
    parser.add_argument("source", type=Path)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("-o", "--output", type=Path)
    target.add_argument("--output-dir", type=Path)
    parser.add_argument("--strategy", choices=["random", "width"], default="width")
    parser.add_argument(
        "--authorized-local-input",
        action="store_true",
        help="Confirm you are authorized to process this PDF locally",
    )
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--verify-auditor", action="store_true")
    parser.add_argument(
        "--verify-fidelity",
        action="store_true",
        help="Run the mandatory geometry and text checks (always enabled)",
    )
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    destination = args.output or args.output_dir / f"{args.source.stem}-anonymized.pdf"
    if args.report and (
        args.report.exists()
        or args.report.resolve() in {args.source.resolve(), destination.resolve()}
    ):
        parser.error("Report must be new and distinct from input and output")
    try:
        report = anonymize(
            args.source,
            destination,
            authorized=args.authorized_local_input,
            seed=args.seed,
            strategy=args.strategy,
            verify_auditor=args.verify_auditor,
            verbose=args.verbose,
        )
    except (UnsupportedPDF, FileExistsError, ValueError) as exc:
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(
                json.dumps({"status": "FAILED", "reason": str(exc)}, indent=2) + "\n"
            )
        parser.exit(2, f"Refused: {exc}\n")
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(f"Created {destination}: content-anonymized PDF with formatting preserved.")
    print("No guarantee of source unlinkability.")


if __name__ == "__main__":
    main()
