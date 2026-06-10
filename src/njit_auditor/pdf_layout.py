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

LANDSCAPE_ASPECT_THRESHOLD = 1.02


def _parse_line_dir(raw_dir: object) -> tuple[float, float] | None:
    if not isinstance(raw_dir, (list, tuple)) or len(raw_dir) < 2:
        return None
    return (float(raw_dir[0]), float(raw_dir[1]))


def _is_visually_landscape(width: float, height: float) -> bool:
    return width > height * LANDSCAPE_ASPECT_THRESHOLD


def _style_flags_from_font_name(font_name: str | None) -> tuple[bool, bool]:
    """Infer bold/italic from PDF font name including Computer Modern variants."""
    if not font_name:
        return False, False
    lowered = font_name.lower()
    base = lowered.split("+")[-1]
    bold = (
        "bold" in lowered
        or "black" in lowered
        or "heavy" in lowered
        or base.startswith("cmbx")
    )
    italic = (
        "italic" in lowered
        or "oblique" in lowered
        or base.startswith("cmti")
        or base.startswith("cmsl")
    )
    return bold, italic


def load_pdf_layout(pdf_path: str) -> PdfDocument:
    """Load a layout-aware PDF model for downstream auditing."""

    pages: list[PdfPage] = []
    with fitz.open(pdf_path) as doc:
        for page_index, page in enumerate(doc, start=1):
            page_width = float(page.rect.width)
            page_height = float(page.rect.height)
            page_model = PdfPage(
                page_number=page_index,
                width=page_width,
                height=page_height,
                page_rotation=int(page.rotation),
                is_visually_landscape=_is_visually_landscape(page_width, page_height),
                text_blocks=[],
            )

            page_dict = page.get_text("dict")
            for block in page_dict.get("blocks", []):
                if block.get("type") != 0:
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
                    wmode_raw = line.get("wmode")
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
                            line_dir=_parse_line_dir(line.get("dir")),
                            wmode=int(wmode_raw) if wmode_raw is not None else None,
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
