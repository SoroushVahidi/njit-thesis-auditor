"""Utilities for extracting and removing PDF annotations/comments."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import fitz

PREVIEW_MAX_CHARS = 120


def _truncate_preview(text: str, max_chars: int = PREVIEW_MAX_CHARS) -> str:
    clean = " ".join(text.split())
    if len(clean) <= max_chars:
        return clean
    return clean[: max_chars - 3] + "..."


def extract_pdf_annotations(pdf_path: Path) -> list[dict[str, Any]]:
    """Extract annotation metadata from a PDF without reading page body text."""

    annotations: list[dict[str, Any]] = []
    with fitz.open(pdf_path) as doc:
        for page_index, page in enumerate(doc, start=1):
            annot = page.first_annot
            while annot is not None:
                info = annot.info or {}
                content = str(info.get("content", "") or "").strip()
                annot_type = str(annot.type[1] if isinstance(annot.type, tuple) else annot.type)
                author = str(info.get("title", "") or "").strip() or None
                rect = annot.rect
                annotations.append(
                    {
                        "page_number": page_index,
                        "subtype": annot_type,
                        "author": author,
                        "content": content if content else None,
                        "truncated_preview": _truncate_preview(content) if content else "",
                        "bbox": [float(rect.x0), float(rect.y0), float(rect.x1), float(rect.y1)],
                        "has_content": bool(content),
                    }
                )
                annot = annot.next
    return annotations


def remove_pdf_annotations(input_pdf: Path, output_pdf: Path) -> None:
    """Create a copy of PDF with annotations removed."""

    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    with fitz.open(input_pdf) as doc:
        for page in doc:
            annots: list[fitz.Annot] = []
            annot = page.first_annot
            while annot is not None:
                annots.append(annot)
                annot = annot.next
            for item in annots:
                page.delete_annot(item)
        doc.save(output_pdf)


def write_annotations_json(annotations: list[dict[str, Any]], output_path: Path) -> None:
    """Write annotation metadata JSON output."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(annotations, indent=2), encoding="utf-8")


def write_annotations_markdown(annotations: list[dict[str, Any]], output_path: Path) -> None:
    """Write annotation metadata as markdown table."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Extracted PDF Annotations",
        "",
        f"- Total annotations: {len(annotations)}",
        "",
        "| Page | Subtype | Author | Has Content | Preview | BBox |",
        "|---|---|---|---|---|---|",
    ]
    for item in annotations:
        preview = str(item.get("truncated_preview", "")).replace("|", " ")
        if len(preview) > PREVIEW_MAX_CHARS:
            preview = _truncate_preview(preview)
        bbox = item.get("bbox", [])
        bbox_str = ", ".join(f"{float(v):.1f}" for v in bbox) if isinstance(bbox, list) else "-"
        lines.append(
            "| "
            + f"{item.get('page_number', '-')}"
            + " | "
            + f"{item.get('subtype', '-')}"
            + " | "
            + f"{item.get('author') or '-'}"
            + " | "
            + f"{item.get('has_content', False)}"
            + " | "
            + f"{preview or '-'}"
            + " | "
            + f"{bbox_str or '-'}"
            + " |"
        )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
