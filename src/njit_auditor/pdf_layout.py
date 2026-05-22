"""PDF layout extraction using PyMuPDF."""

from __future__ import annotations

import fitz

from njit_auditor.pdf_models import (
    BBox,
    PdfDocument,
    PdfPage,
    PdfTextBlock,
    PdfTextLine,
    PdfTextSpan,
)


def _style_flags_from_font_name(font_name: str | None) -> tuple[bool, bool]:
    if not font_name:
        return False, False
    lowered = font_name.lower()
    return ("bold" in lowered), ("italic" in lowered or "oblique" in lowered)


def load_pdf_layout(pdf_path: str) -> PdfDocument:
    """Load a layout-aware PDF model for downstream auditing."""

    pages: list[PdfPage] = []
    with fitz.open(pdf_path) as doc:
        for page_index, page in enumerate(doc, start=1):
            page_model = PdfPage(
                page_number=page_index,
                width=float(page.rect.width),
                height=float(page.rect.height),
                text_blocks=[],
            )

            page_dict = page.get_text("dict")
            for block in page_dict.get("blocks", []):
                # PyMuPDF block type 0 is text; other types include images etc.
                if block.get("type") != 0:
                    # TODO: support image/vector blocks for richer layout checks.
                    continue
                if "bbox" not in block:
                    continue

                block_lines: list[PdfTextLine] = []
                block_text_chunks: list[str] = []
                for line in block.get("lines", []):
                    if "bbox" not in line:
                        continue
                    spans: list[PdfTextSpan] = []
                    span_text_chunks: list[str] = []
                    for span in line.get("spans", []):
                        text = str(span.get("text", ""))
                        if not text.strip():
                            continue
                        font_name = span.get("font")
                        bold, italic = _style_flags_from_font_name(
                            str(font_name) if font_name else None
                        )
                        span_model = PdfTextSpan(
                            text=text,
                            bbox=BBox(
                                x0=float(span["bbox"][0]),
                                y0=float(span["bbox"][1]),
                                x1=float(span["bbox"][2]),
                                y1=float(span["bbox"][3]),
                            ),
                            font=str(font_name) if font_name else None,
                            size=float(span["size"]) if span.get("size") is not None else None,
                            bold=bold,
                            italic=italic,
                        )
                        spans.append(span_model)
                        span_text_chunks.append(text)
                    if not spans:
                        continue
                    line_text = "".join(span_text_chunks).strip()
                    block_text_chunks.append(line_text)
                    block_lines.append(
                        PdfTextLine(
                            spans=spans,
                            bbox=BBox(
                                x0=float(line["bbox"][0]),
                                y0=float(line["bbox"][1]),
                                x1=float(line["bbox"][2]),
                                y1=float(line["bbox"][3]),
                            ),
                            text=line_text,
                        )
                    )

                if not block_lines:
                    continue
                block_text = "\n".join(part for part in block_text_chunks if part).strip()
                page_model.text_blocks.append(
                    PdfTextBlock(
                        lines=block_lines,
                        bbox=BBox(
                            x0=float(block["bbox"][0]),
                            y0=float(block["bbox"][1]),
                            x1=float(block["bbox"][2]),
                            y1=float(block["bbox"][3]),
                        ),
                        text=block_text,
                    )
                )
            pages.append(page_model)

    return PdfDocument(path=pdf_path, pages=pages)
