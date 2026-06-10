"""Synthetic tests for P080 — DOCX comment and tracked-change extraction."""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

from njit_auditor.docx_comments import (
    COMMENT_PREVIEW_CHARS,
    count_docx_tracked_changes,
    extract_docx_comments,
    write_docx_comments_json,
    write_docx_comments_markdown,
)

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = f"{{{W_NS}}}"

_CONTENT_TYPES = """\
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml"
    ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>
"""

_RELS = """\
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1"
    Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"
    Target="word/document.xml"/>
</Relationships>
"""

_DOCUMENT_XML = """\
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body><w:p><w:r><w:t>Test body.</w:t></w:r></w:p></w:body>
</w:document>
"""

_DOCUMENT_XML_WITH_TRACKED = """\
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p>
      <w:ins w:id="1" w:author="EF" w:date="2025-01-01T00:00:00Z">
        <w:r><w:t>inserted text</w:t></w:r>
      </w:ins>
      <w:del w:id="2" w:author="EF" w:date="2025-01-01T00:00:00Z">
        <w:r><w:delText>deleted text</w:delText></w:r>
      </w:del>
      <w:ins w:id="3" w:author="EF" w:date="2025-01-02T00:00:00Z">
        <w:r><w:t>another insert</w:t></w:r>
      </w:ins>
    </w:p>
  </w:body>
</w:document>
"""


def _comments_xml(entries: list[tuple[str, str, str, str]]) -> str:
    """Build word/comments.xml with given (id, author, date, text) tuples."""
    parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        f'<w:comments xmlns:w="{W_NS}">',
    ]
    for cid, author, date, text in entries:
        parts.append(
            f'  <w:comment w:id="{cid}" w:author="{author}" w:date="{date}">'
            f'<w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:comment>'
        )
    parts.append("</w:comments>")
    return "\n".join(parts)


def _make_docx(tmp_path: Path, comments: list[tuple[str, str, str, str]] | None = None,
               document_xml: str = _DOCUMENT_XML) -> Path:
    out = tmp_path / "test.docx"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("[Content_Types].xml", _CONTENT_TYPES)
        zf.writestr("_rels/.rels", _RELS)
        zf.writestr("word/document.xml", document_xml)
        if comments is not None:
            zf.writestr("word/comments.xml", _comments_xml(comments))
    out.write_bytes(buf.getvalue())
    return out


def test_extract_comments_returns_expected_count(tmp_path: Path) -> None:
    docx = _make_docx(tmp_path, comments=[
        ("1", "EF", "2025-01-28T00:00:00Z", "Fix heading case"),
        ("2", "EF", "2025-01-28T00:00:00Z", "Add period"),
    ])
    result = extract_docx_comments(docx)
    assert len(result) == 2


def test_extract_comments_metadata_fields(tmp_path: Path) -> None:
    docx = _make_docx(tmp_path, comments=[
        ("42", "Ester Farfan", "2025-02-01T00:00:00Z", "Check margin"),
    ])
    result = extract_docx_comments(docx)
    assert result[0]["id"] == "42"
    assert result[0]["author"] == "Ester Farfan"
    assert result[0]["has_content"] is True
    assert "margin" in result[0]["truncated_preview"].lower()


def test_extract_comments_empty_text_flagged(tmp_path: Path) -> None:
    docx = _make_docx(tmp_path, comments=[("1", "EF", "2025-01-01T00:00:00Z", "")])
    result = extract_docx_comments(docx)
    assert result[0]["has_content"] is False
    assert result[0]["char_count"] == 0


def test_extract_comments_no_comments_xml_returns_empty(tmp_path: Path) -> None:
    docx = _make_docx(tmp_path, comments=None)
    result = extract_docx_comments(docx)
    assert result == []


def test_extract_comments_invalid_file_returns_empty(tmp_path: Path) -> None:
    bad = tmp_path / "bad.docx"
    bad.write_bytes(b"not a zip file")
    assert extract_docx_comments(bad) == []


def test_extract_comments_nonexistent_file_returns_empty(tmp_path: Path) -> None:
    missing = tmp_path / "missing.docx"
    assert extract_docx_comments(missing) == []


def test_extract_comments_truncation(tmp_path: Path) -> None:
    long_text = "word " * 60
    docx = _make_docx(tmp_path, comments=[("1", "EF", "2025-01-01T00:00:00Z", long_text)])
    result = extract_docx_comments(docx)
    assert len(result[0]["truncated_preview"]) <= COMMENT_PREVIEW_CHARS
    assert result[0]["truncated_preview"].endswith("...")


def test_count_tracked_changes_with_mixed_changes(tmp_path: Path) -> None:
    docx = _make_docx(tmp_path, document_xml=_DOCUMENT_XML_WITH_TRACKED)
    result = count_docx_tracked_changes(docx)
    assert result["insertions"] == 2
    assert result["deletions"] == 1


def test_count_tracked_changes_none_returns_zeros(tmp_path: Path) -> None:
    docx = _make_docx(tmp_path)
    result = count_docx_tracked_changes(docx)
    assert result == {"insertions": 0, "deletions": 0}


def test_count_tracked_changes_invalid_file_returns_zeros(tmp_path: Path) -> None:
    bad = tmp_path / "bad.docx"
    bad.write_bytes(b"garbage")
    assert count_docx_tracked_changes(bad) == {"insertions": 0, "deletions": 0}


def test_write_docx_comments_json(tmp_path: Path) -> None:
    comments = [{"id": "1", "author": "EF", "date": "2025-01-01", "truncated_preview": "Fix this",
                 "has_content": True, "char_count": 8}]
    tracked = {"insertions": 3, "deletions": 1}
    out = tmp_path / "out.json"
    write_docx_comments_json(comments, tracked, out)
    data = json.loads(out.read_text())
    assert data["comment_count"] == 1
    assert data["tracked_changes"] == tracked
    assert len(data["comments"]) == 1


def test_write_docx_comments_markdown(tmp_path: Path) -> None:
    comments = [
        {"id": "1", "author": "EF", "date": "2025-01-01",
         "truncated_preview": "Fix heading", "has_content": True, "char_count": 11}
    ]
    tracked = {"insertions": 2, "deletions": 0}
    out = tmp_path / "out.md"
    write_docx_comments_markdown(comments, tracked, out)
    text = out.read_text()
    assert "Total comments: 1" in text
    assert "Tracked insertions: 2" in text
    assert "EF" in text


def test_write_docx_comments_json_creates_parent_dirs(tmp_path: Path) -> None:
    out = tmp_path / "deep" / "nested" / "out.json"
    write_docx_comments_json([], {"insertions": 0, "deletions": 0}, out)
    assert out.exists()
