"""Tests for upload classification, ZIP safety, and audit dispatch."""

from __future__ import annotations

import stat
import zipfile
from pathlib import Path
from unittest.mock import patch

import fitz
import pytest

from njit_auditor.audit_runner import (
    UploadedAuditResult,
    run_audit_for_uploaded_file,
)
from njit_auditor.upload_handling import (
    ALLOWED_ZIP_EXTENSIONS,
    MainTexDetectionError,
    UploadKind,
    UploadValidationError,
    ZipExtractionError,
    classify_upload,
    detect_main_tex,
    safe_extract_zip,
    sanitize_upload_filename,
    validate_upload_path,
)


def _make_pdf(path: Path) -> None:
    doc = fitz.open()
    doc.new_page(width=612, height=792)
    doc.save(path)
    doc.close()


def _make_zip(path: Path, members: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        for name, data in members.items():
            zf.writestr(name, data)


# ---------------------------------------------------------------------------
# Classification and validation
# ---------------------------------------------------------------------------


def test_classify_valid_pdf(tmp_path: Path) -> None:
    pdf = tmp_path / "thesis.pdf"
    _make_pdf(pdf)
    assert classify_upload(pdf) == UploadKind.PDF
    assert validate_upload_path(pdf) == UploadKind.PDF


def test_classify_valid_tex(tmp_path: Path) -> None:
    tex = tmp_path / "main.tex"
    tex.write_text(
        r"\documentclass{report}" + "\n\\begin{document}\nHello\n\\end{document}\n",
        encoding="utf-8",
    )
    assert classify_upload(tex) == UploadKind.TEX
    assert validate_upload_path(tex) == UploadKind.TEX


@pytest.mark.parametrize("check", [classify_upload, validate_upload_path])
def test_missing_upload_error_excludes_filesystem_path(tmp_path: Path, check) -> None:
    path = tmp_path / "synthetic-private-filename.pdf"
    with pytest.raises(UploadValidationError, match="The uploaded file is unavailable") as error:
        check(path)
    assert str(path) not in str(error.value)


def test_invalid_pdf_magic_rejected(tmp_path: Path) -> None:
    bad = tmp_path / "fake.pdf"
    bad.write_bytes(b"NOTAPDF-content-here")
    with pytest.raises(UploadValidationError, match="valid PDF"):
        validate_upload_path(bad)


def test_unsupported_file_type_rejected(tmp_path: Path) -> None:
    docx = tmp_path / "thesis.docx"
    docx.write_bytes(b"PK\x03\x04fake")
    assert classify_upload(docx) == UploadKind.UNSUPPORTED
    with pytest.raises(UploadValidationError, match="Unsupported"):
        validate_upload_path(docx)


def test_oversized_file_rejected(tmp_path: Path) -> None:
    pdf = tmp_path / "big.pdf"
    _make_pdf(pdf)
    with pytest.raises(UploadValidationError, match="exceeds maximum size"):
        validate_upload_path(pdf, max_size_bytes=1)


def test_sanitize_upload_filename_strips_path() -> None:
    assert sanitize_upload_filename("../../evil/thesis.pdf") == "thesis.pdf"
    assert sanitize_upload_filename("my thesis!.pdf") == "my_thesis_.pdf"


# ---------------------------------------------------------------------------
# ZIP safety
# ---------------------------------------------------------------------------


def test_safe_zip_extraction_succeeds(tmp_path: Path) -> None:
    zpath = tmp_path / "project.zip"
    _make_zip(
        zpath,
        {
            "main.tex": rb"\documentclass{article}\n\\begin{document}\n\\end{document}\n",
            "refs.bib": b"@article{a, title={x}}",
        },
    )
    dest = tmp_path / "out"
    extracted = safe_extract_zip(zpath, dest)
    assert len(extracted) == 2
    assert (dest / "main.tex").exists()


def test_zip_slip_rejected(tmp_path: Path) -> None:
    zpath = tmp_path / "evil.zip"
    _make_zip(zpath, {"../escape.tex": rb"\documentclass{article}"})
    with pytest.raises(ZipExtractionError, match="Unsafe ZIP path"):
        safe_extract_zip(zpath, tmp_path / "out")


def test_absolute_zip_member_rejected(tmp_path: Path) -> None:
    zpath = tmp_path / "abs.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        info = zipfile.ZipInfo("/absolute.tex")
        zf.writestr(info, rb"\documentclass{article}")
    with pytest.raises(ZipExtractionError, match="Unsafe ZIP path"):
        safe_extract_zip(zpath, tmp_path / "out")


def test_too_many_zip_files_rejected(tmp_path: Path) -> None:
    zpath = tmp_path / "many.zip"
    members = {f"f{i}.tex": b"%" for i in range(5)}
    _make_zip(zpath, members)
    with pytest.raises(ZipExtractionError, match="too many files"):
        safe_extract_zip(zpath, tmp_path / "out", max_files=3)


def test_zip_uncompressed_size_limit_rejected(tmp_path: Path) -> None:
    zpath = tmp_path / "large.zip"
    _make_zip(zpath, {"big.tex": b"x" * 200})
    with pytest.raises(ZipExtractionError, match="uncompressed size"):
        safe_extract_zip(zpath, tmp_path / "out", max_total_uncompressed_bytes=50)


def test_unsafe_extension_in_zip_rejected(tmp_path: Path) -> None:
    zpath = tmp_path / "exe.zip"
    _make_zip(zpath, {"run.exe": b"MZ"})
    with pytest.raises(ZipExtractionError, match="Disallowed file type"):
        safe_extract_zip(zpath, tmp_path / "out")


def test_corrupt_zip_rejected(tmp_path: Path) -> None:
    bad = tmp_path / "bad.zip"
    bad.write_bytes(b"not-a-zip-archive")
    with pytest.raises(UploadValidationError, match="valid ZIP"):
        validate_upload_path(bad)


def test_duplicate_member_paths_rejected(tmp_path: Path) -> None:
    zpath = tmp_path / "dup.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.writestr("main.tex", rb"\documentclass{article}")
        zf.writestr("main.tex", rb"\documentclass{report}")
    with pytest.raises(ZipExtractionError, match="duplicate member path"):
        safe_extract_zip(zpath, tmp_path / "out")


def test_duplicate_normalized_member_paths_rejected(tmp_path: Path) -> None:
    zpath = tmp_path / "dup_norm.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        info1 = zipfile.ZipInfo("./main.tex")
        zf.writestr(info1, rb"\documentclass{article}")
        info2 = zipfile.ZipInfo("main.tex")
        zf.writestr(info2, rb"\documentclass{report}")
    with pytest.raises(ZipExtractionError, match="duplicate member path"):
        safe_extract_zip(zpath, tmp_path / "out")


def test_symlink_zip_entry_rejected(tmp_path: Path) -> None:
    zpath = tmp_path / "sym.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        info = zipfile.ZipInfo("link.tex")
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        zf.writestr(info, "/etc/passwd")
    with pytest.raises(ZipExtractionError, match="symlink"):
        safe_extract_zip(zpath, tmp_path / "out")


def test_single_oversized_member_rejected(tmp_path: Path) -> None:
    zpath = tmp_path / "big_one.zip"
    _make_zip(zpath, {"big.tex": b"x" * 200})
    with pytest.raises(ZipExtractionError, match="single-file size limit"):
        safe_extract_zip(zpath, tmp_path / "out", max_single_file_bytes=100)


# ---------------------------------------------------------------------------
# Main TeX detection
# ---------------------------------------------------------------------------


def test_detect_main_tex_prefers_main_tex(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    (project / "chapter.tex").write_text("no documentclass", encoding="utf-8")
    (project / "main.tex").write_text(
        r"\documentclass{report}" + "\n\\begin{document}\n\\end{document}\n",
        encoding="utf-8",
    )
    assert detect_main_tex(project).name == "main.tex"


def test_detect_main_tex_ambiguous_raises(tmp_path: Path) -> None:
    project = tmp_path / "proj"
    project.mkdir()
    for name in ("a.tex", "b.tex"):
        (project / name).write_text(
            r"\documentclass{report}" + "\n\\begin{document}\n\\end{document}\n",
            encoding="utf-8",
        )
    with pytest.raises(MainTexDetectionError, match="ambiguous"):
        detect_main_tex(project)


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


def test_dispatcher_pdf_calls_run_pdf_audit_full(tmp_path: Path) -> None:
    pdf = tmp_path / "thesis.pdf"
    _make_pdf(pdf)
    with patch("njit_auditor.audit_runner.run_pdf_audit_full", return_value=[]) as mock_pdf:
        result = run_audit_for_uploaded_file(pdf)
    mock_pdf.assert_called_once_with(pdf)
    assert result.upload_kind == UploadKind.PDF
    assert result.audit_type == "pdf"
    assert result.json_export_supported is True


def test_dispatcher_tex_export_supported(tmp_path: Path) -> None:
    tex = tmp_path / "main.tex"
    tex.write_text(
        r"\documentclass{report}" + "\n\\begin{document}\n\\end{document}\n",
        encoding="utf-8",
    )
    with patch(
        "njit_auditor.audit_runner.collect_tex_findings",
        return_value=(tex, 1, []),
    ) as mock_tex:
        result = run_audit_for_uploaded_file(tex)
    mock_tex.assert_called_once()
    assert result.upload_kind == UploadKind.TEX
    assert result.audit_type == "tex"
    assert result.json_export_supported is True
    assert result.limitation_note == ""


def test_dispatcher_zip_extracts_and_audits_tex(tmp_path: Path) -> None:
    zpath = tmp_path / "project.zip"
    _make_zip(
        zpath,
        {"main.tex": rb"\documentclass{report}\n\\begin{document}\n\\end{document}\n"},
    )
    work = tmp_path / "work"
    work.mkdir()
    with patch(
        "njit_auditor.audit_runner.collect_tex_findings",
        return_value=(work / "main.tex", 1, []),
    ) as mock_tex:
        result = run_audit_for_uploaded_file(zpath, work_dir=work)
    mock_tex.assert_called_once()
    assert result.upload_kind == UploadKind.ZIP
    assert result.audit_type == "tex"
    assert result.json_export_supported is True


def test_dispatcher_unsupported_raises(tmp_path: Path) -> None:
    bad = tmp_path / "file.docx"
    bad.write_bytes(b"PK\x03\x04")
    with pytest.raises(UploadValidationError):
        run_audit_for_uploaded_file(bad)


def test_dispatcher_pdf_integration(tmp_path: Path) -> None:
    """End-to-end PDF dispatch without monkeypatch."""
    pdf = tmp_path / "thesis.pdf"
    _make_pdf(pdf)
    result = run_audit_for_uploaded_file(pdf)
    assert isinstance(result, UploadedAuditResult)
    assert result.audit_type == "pdf"
    assert isinstance(result.findings, list)


def test_allowed_zip_extensions_include_tex() -> None:
    assert ".tex" in ALLOWED_ZIP_EXTENSIONS
