"""Bounded validation of private feedback files; never render or follow links."""

from __future__ import annotations

import io
import stat
import warnings
import zipfile
import zlib
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree as ET

from PIL import Image
from pypdf import PdfReader
from pypdf.errors import PyPdfError

MAX_ATTACHMENT_BYTES = 4 * 1024 * 1024
MAX_IMAGE_PIXELS = 16_000_000
MAX_PDF_PAGES = 500
MAX_ZIP_ENTRIES = 512
MAX_ZIP_BYTES = 32 * 1024 * 1024
MAX_ZIP_ENTRY_BYTES = 8 * 1024 * 1024
MAX_XML_BYTES = 2 * 1024 * 1024
MAX_COMPRESSION_RATIO = 200
_TYPES = "http://schemas.openxmlformats.org/package/2006/content-types"
_RELS = "http://schemas.openxmlformats.org/package/2006/relationships"
_WORD = {"http://schemas.openxmlformats.org/wordprocessingml/2006/main",
         "http://purl.oclc.org/ooxml/wordprocessingml/main"}
_DOCUMENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
_DOCUMENT_RELS = {
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument",
    "http://purl.oclc.org/ooxml/officeDocument/relationships/officeDocument",
}


class _NoDTD(ET.TreeBuilder):
    def doctype(self, name: str, pubid: str | None, system: str | None) -> None:
        raise ValueError("Document type declarations are not supported")


class _PdfStream(io.BytesIO):
    """Bound parser I/O, including malformed object/reference traversal."""

    def __init__(self, content: bytes) -> None:
        super().__init__(content)
        self._remaining = 64 * 1024 * 1024
        self._operations = 200_000

    def read(self, size: int | None = -1) -> bytes:
        self._operations -= 1
        if self._operations < 0:
            raise ValueError("PDF parser budget exceeded")
        result = super().read(size)
        self._remaining -= len(result)
        if self._remaining < 0:
            raise ValueError("PDF parser budget exceeded")
        return result


def _valid_image(content: bytes, expected: str) -> bool:
    # Pillow stops at the IEND type without checking its length or CRC.
    # Walk bounded chunk lengths so an appended IEND cannot hide an earlier,
    # incomplete end chunk. Pillow verifies the preceding chunks below.
    if expected == "PNG":
        offset = 8
        while offset + 12 <= len(content):
            if content[offset + 4:offset + 8] == b"IEND":
                if content[offset:] != b"\x00\x00\x00\x00IEND\xaeB\x60\x82":
                    return False
                break
            offset += 12 + int.from_bytes(content[offset:offset + 4], "big")
        else:
            return False
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(io.BytesIO(content), formats=[expected]) as image:
            if image.width * image.height > MAX_IMAGE_PIXELS or getattr(image, "n_frames", 1) != 1:
                return False
            image.verify()
        # JPEG verify() alone does not decode its entropy stream. Decode under
        # the pixel bound to detect truncation, without displaying/rendering it.
        with Image.open(io.BytesIO(content), formats=[expected]) as image:
            image.load()
    return True


def _valid_pdf(content: bytes) -> bool:
    if not content.startswith(b"%PDF-") or not content.rstrip().endswith(b"%%EOF"):
        return False
    with _PdfStream(content) as stream:
        reader = PdfReader(stream, strict=True)
        if reader.is_encrypted or not 0 < len(reader.pages) <= MAX_PDF_PAGES:
            return False
        # Resolve page structure, never page content, actions or embedded files.
        return all(page.get("/Type") == "/Page" and len(page.mediabox) == 4
                   for page in reader.pages)


def _valid_docx(content: bytes) -> bool:
    xml: dict[str, ET.Element] = {}
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        entries = archive.infolist()
        names = [entry.filename for entry in entries]
        if (len(entries) > MAX_ZIP_ENTRIES or len(set(names)) != len(names)
                or sum(entry.file_size for entry in entries) > MAX_ZIP_BYTES):
            return False
        total = 0
        for entry in entries:
            path = PurePosixPath(entry.filename)
            if (path.is_absolute() or ".." in path.parts or "\\" in entry.filename
                    or entry.flag_bits & 1
                    or stat.S_ISLNK(entry.external_attr >> 16)
                    or entry.file_size > MAX_ZIP_ENTRY_BYTES
                    or entry.file_size > max(1, entry.compress_size) * MAX_COMPRESSION_RATIO
                    or entry.filename.lower().endswith(("vbaproject.bin", ".exe", ".js"))):
                return False
            is_xml = entry.filename.endswith((".xml", ".rels"))
            data = bytearray()
            size = 0
            with archive.open(entry) as member:
                while chunk := member.read(65536):
                    size += len(chunk)
                    total += len(chunk)
                    if (size > MAX_ZIP_ENTRY_BYTES or total > MAX_ZIP_BYTES
                            or (is_xml and size > MAX_XML_BYTES)):
                        return False
                    if is_xml:
                        data.extend(chunk)
                # Reading every member through EOF verifies its ZIP CRC.
            if is_xml:
                xml[entry.filename] = ET.fromstring(data, parser=ET.XMLParser(target=_NoDTD()))
    types, document, rels = (xml.get(name) for name in (
        "[Content_Types].xml", "word/document.xml", "_rels/.rels"))
    if types is None or document is None or rels is None:
        return False
    return (
        types.tag == f"{{{_TYPES}}}Types"
        and any(item.get("PartName") == "/word/document.xml"
                and item.get("ContentType") == _DOCUMENT_TYPE
                for item in types.findall(f"{{{_TYPES}}}Override"))
        and any(document.tag == f"{{{ns}}}document"
                and document.find(f"{{{ns}}}body") is not None for ns in _WORD)
        and rels.tag == f"{{{_RELS}}}Relationships"
        and any(item.get("Type") in _DOCUMENT_RELS
                and item.get("Target", "").lstrip("/") == "word/document.xml"
                and item.get("TargetMode", "Internal") == "Internal"
                for item in rels.findall(f"{{{_RELS}}}Relationship"))
    )


def valid_attachment(filename: str, content: bytes) -> bool:
    """Validate supported, unencrypted files within explicit resource bounds."""
    if not 0 < len(content) <= MAX_ATTACHMENT_BYTES:
        return False
    extension = Path(filename).suffix.lower()
    try:
        if extension in {".png", ".jpg", ".jpeg"}:
            return _valid_image(content, "PNG" if extension == ".png" else "JPEG")
        if extension == ".pdf":
            return _valid_pdf(content)
        if extension == ".docx":
            return _valid_docx(content)
    except (OSError, ValueError, SyntaxError, RuntimeError, KeyError, IndexError,
            TypeError, AssertionError, OverflowError, EOFError, zlib.error,
            PyPdfError, zipfile.BadZipFile, ET.ParseError,
            Image.DecompressionBombWarning, Image.DecompressionBombError):
        return False
    return False
