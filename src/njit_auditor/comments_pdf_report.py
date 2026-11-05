"""Lay out the existing student text export as a standalone, comments-only PDF.

Only report text enters this renderer. It cannot copy, attach, or annotate the
uploaded dissertation. The complete student PDF renderer is independent.
"""

from __future__ import annotations

import io
import re
from functools import lru_cache
from html import escape
from threading import Lock
from typing import Any

import fitz
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate

from njit_auditor.coverage_disclosure import COVERAGE_AREAS, COVERAGE_HEADING
from njit_auditor.incomplete_audit import INCOMPLETE_AUDIT_TITLE
from njit_auditor.resource_paths import resource_path

_FONT_LOCK = Lock()
_INK = colors.HexColor("#12365a")


@lru_cache(maxsize=1)
def _fonts() -> tuple[TTFont, TTFont]:
    # Both fonts already ship with this application or its PyMuPDF dependency.
    # No system font lookup, download, new font asset, or optional dependency.
    with _FONT_LOCK:
        if "CommentsDejaVu" not in pdfmetrics.getRegisteredFontNames():
            primary = TTFont(
                "CommentsDejaVu",
                str(resource_path("assets", "fonts", "DejaVuSans.ttf")),
            )
            fallback = TTFont("CommentsCJK", io.BytesIO(fitz.Font("cjk").buffer))
            pdfmetrics.registerFont(primary)
            pdfmetrics.registerFont(fallback)
        else:
            primary = pdfmetrics.getFont("CommentsDejaVu")
            fallback = pdfmetrics.getFont("CommentsCJK")
    return primary, fallback


def _paragraph_text(text: str) -> str:
    primary, fallback = _fonts()
    runs: list[str] = []
    current_font = primary
    current: list[str] = []
    for char in text:
        font = (
            fallback
            if ord(char) not in primary.face.charToGlyph and ord(char) in fallback.face.charToGlyph
            else primary
        )
        if font is not current_font:
            runs.append(f'<font name="{current_font.fontName}">{escape("".join(current))}</font>')
            current = []
            current_font = font
        current.append(char)
    runs.append(f'<font name="{current_font.fontName}">{escape("".join(current))}</font>')
    return "".join(runs)


def _footer(canvas: Any, document: Any) -> None:
    canvas.setStrokeColor(colors.HexColor("#d1d9e2"))
    canvas.line(54, 38, 558, 38)
    canvas.setFillColor(colors.HexColor("#4b5563"))
    canvas.setFont("Helvetica", 8)
    canvas.drawString(54, 25, "NJIT Comments Report")
    canvas.drawRightString(558, 25, f"Report page {document.page}")


def _unicode_cmaps(document: fitz.Document) -> None:
    """Encode supplementary-plane characters as UTF-16 in this PDF only.

    ReportLab's TTFont CMaps emit e.g. <1F600> for an emoji; PDF requires
    <D83DDE00>. Repair the mapping without changing the glyphs or global font
    behavior (in particular, without affecting the Complete PDF Report).
    """
    for xref in range(1, document.xref_length()):
        kind, value = document.xref_get_key(xref, "ToUnicode")
        if kind != "xref":
            continue
        stream_xref = int(value.split()[0])
        cmap = document.xref_stream(stream_xref)
        fixed = re.sub(
            rb"(<[0-9A-Fa-f]+>\s*)<([0-9A-Fa-f]{5,6})>",
            lambda match: (
                match[1]
                + b"<"
                + chr(int(match[2], 16)).encode("utf-16-be").hex().upper().encode("ascii")
                + b">"
            ),
            cmap,
        )
        if fixed != cmap:
            document.update_stream(stream_xref, fixed)


def render_comments_pdf_report(report_text: str) -> bytes:
    """Preserve every line of the page-ordered student text report, with layout."""
    primary, _ = _fonts()
    body = ParagraphStyle(
        "CommentsBody",
        fontName=primary.fontName,
        fontSize=10,
        leading=15,
        spaceAfter=7,
        splitLongWords=True,
    )
    title = ParagraphStyle(
        "CommentsTitle",
        parent=body,
        fontSize=18,
        leading=24,
        textColor=_INK,
        spaceAfter=10,
        keepWithNext=True,
    )
    section = ParagraphStyle(
        "CommentsSection",
        parent=body,
        fontSize=13,
        leading=18,
        textColor=_INK,
        spaceBefore=13,
        spaceAfter=8,
        keepWithNext=True,
    )
    problem = ParagraphStyle(
        "CommentsProblem",
        parent=body,
        fontSize=11,
        leading=16,
        textColor=_INK,
        spaceBefore=10,
        keepWithNext=True,
    )
    coverage = ParagraphStyle(
        "CommentsCoverage",
        parent=body,
        fontSize=9.5,
        leading=14,
        spaceAfter=4,
    )
    coverage_title = ParagraphStyle(
        "CommentsCoverageTitle",
        parent=coverage,
        textColor=_INK,
        spaceBefore=6,
        keepWithNext=True,
    )
    page_label = ParagraphStyle("CommentsPageLabel", parent=body, keepWithNext=True)
    coverage_titles = {f"{area.title}: {area.status_label}" for area in COVERAGE_AREAS}
    in_coverage = False
    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=(612, 792),
        leftMargin=54,
        rightMargin=54,
        topMargin=50,
        bottomMargin=54,
        title="NJIT Thesis/Dissertation Comments Report",
        author="NJIT Thesis Auditor",
    )
    story: list[Any] = []
    for index, line in enumerate(report_text.splitlines()):
        if not line.strip():
            continue
        if line == COVERAGE_HEADING.upper():
            in_coverage = True
        elif line.startswith(("PDF PAGE ", "Problem #")) or line == "DOCUMENT-LEVEL FINDINGS":
            in_coverage = False
        style = coverage if in_coverage else body
        if index == 0:
            style = title
        elif line.startswith("Problem #"):
            style = problem
        elif line.startswith("PDF PAGE ") or line in {
            "Findings to check",
            "DOCUMENT-LEVEL FINDINGS",
            COVERAGE_HEADING.upper(),
            INCOMPLETE_AUDIT_TITLE.upper(),
        }:
            style = section
        elif line.startswith("Manuscript page:"):
            style = page_label
        elif in_coverage and line in coverage_titles:
            style = coverage_title
        story.append(Paragraph(_paragraph_text(line), style))
        if index == 0:
            story.append(Paragraph("Comments Report", section))
    if not story:
        story.append(Paragraph("NJIT Thesis/Dissertation Comments Report", title))
    document.build(story, onFirstPage=_footer, onLaterPages=_footer)
    with fitz.open(stream=buffer.getvalue(), filetype="pdf") as pdf:
        _unicode_cmaps(pdf)
        return pdf.tobytes(garbage=4, deflate=True)
