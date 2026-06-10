"""Utilities for extracting comment and tracked-change metadata from DOCX files."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
COMMENT_PREVIEW_CHARS = 120


def _truncate(text: str, max_chars: int = COMMENT_PREVIEW_CHARS) -> str:
    clean = " ".join(text.split())
    if len(clean) <= max_chars:
        return clean
    return clean[: max_chars - 3] + "..."


def extract_docx_comments(docx_path: Path) -> list[dict[str, Any]]:
    """Extract comment metadata from a DOCX file without reproducing body text.

    Reads word/comments.xml from the DOCX ZIP. Returns per-comment metadata
    (id, author, date, truncated preview, has_content flag). Returns an empty
    list if the file has no comments part or cannot be opened.
    """
    try:
        with zipfile.ZipFile(docx_path) as zf:
            if "word/comments.xml" not in zf.namelist():
                return []
            xml_bytes = zf.read("word/comments.xml")
    except (zipfile.BadZipFile, KeyError, OSError):
        return []

    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return []

    tag_comment = f"{{{W_NS}}}comment"
    tag_t = f"{{{W_NS}}}t"

    comments: list[dict[str, Any]] = []
    for comment_el in root.iter(tag_comment):
        cid = comment_el.get(f"{{{W_NS}}}id", "")
        author = comment_el.get(f"{{{W_NS}}}author") or None
        date = comment_el.get(f"{{{W_NS}}}date") or None
        texts = [t.text or "" for t in comment_el.iter(tag_t)]
        full_text = " ".join(texts).strip()
        comments.append(
            {
                "id": cid,
                "author": author,
                "date": date,
                "truncated_preview": _truncate(full_text),
                "has_content": bool(full_text),
                "char_count": len(full_text),
            }
        )
    return comments


def count_docx_tracked_changes(docx_path: Path) -> dict[str, int]:
    """Count tracked insertions and deletions in word/document.xml.

    Returns a dict with "insertions" and "deletions" counts. Returns zeros
    if the document part is absent or unreadable.
    """
    try:
        with zipfile.ZipFile(docx_path) as zf:
            if "word/document.xml" not in zf.namelist():
                return {"insertions": 0, "deletions": 0}
            xml_bytes = zf.read("word/document.xml")
    except (zipfile.BadZipFile, KeyError, OSError):
        return {"insertions": 0, "deletions": 0}

    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return {"insertions": 0, "deletions": 0}

    tag_ins = f"{{{W_NS}}}ins"
    tag_del = f"{{{W_NS}}}del"
    return {
        "insertions": sum(1 for _ in root.iter(tag_ins)),
        "deletions": sum(1 for _ in root.iter(tag_del)),
    }


def write_docx_comments_json(
    comments: list[dict[str, Any]],
    tracked: dict[str, int],
    output_path: Path,
) -> None:
    """Write aggregate comment metadata and tracked-change counts as JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "comment_count": len(comments),
        "tracked_changes": tracked,
        "comments": comments,
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_docx_comments_markdown(
    comments: list[dict[str, Any]],
    tracked: dict[str, int],
    output_path: Path,
) -> None:
    """Write aggregate comment metadata and tracked-change counts as Markdown."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Extracted DOCX Comments and Tracked Changes",
        "",
        f"- Total comments: {len(comments)}",
        f"- Tracked insertions: {tracked.get('insertions', 0)}",
        f"- Tracked deletions: {tracked.get('deletions', 0)}",
        "",
    ]
    if comments:
        lines += [
            "## Comments",
            "",
            "| # | Author | Date | Preview |",
            "|---|--------|------|---------|",
        ]
        for i, c in enumerate(comments, 1):
            author = c.get("author") or "—"
            date = str(c.get("date") or "—")[:10]
            preview = c.get("truncated_preview") or "*(no text)*"
            lines.append(f"| {i} | {author} | {date} | {preview} |")
        lines.append("")
    output_path.write_text("\n".join(lines), encoding="utf-8")
