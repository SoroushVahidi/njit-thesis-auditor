"""Python API for running the NJIT thesis PDF audit without the CLI layer."""

from __future__ import annotations

import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pymupdf import FileDataError

from njit_auditor.latex_linters import run_optional_latex_linters
from njit_auditor.latex_loader import load_tex_project
from njit_auditor.models import AuditFinding
from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.pdf_models import PdfDocument
from njit_auditor.rules.latex_abstract import (
    run_latex_abstract_checks,
    run_latex_abstract_word_count_check,
)
from njit_auditor.rules.latex_figures_tables import run_latex_figure_table_checks
from njit_auditor.rules.latex_labels import run_latex_label_checks
from njit_auditor.rules.latex_metadata import run_latex_graduation_month_check
from njit_auditor.rules.latex_risky_commands import run_latex_risky_command_checks
from njit_auditor.rules.latex_structure import run_latex_structure_checks
from njit_auditor.rules.pdf_abstract import check_pdf_abstract_word_count
from njit_auditor.rules.pdf_abstract_indentation import check_pdf_abstract_indentation
from njit_auditor.rules.pdf_acknowledgements_indentation import (
    check_pdf_acknowledgements_indentation,
)
from njit_auditor.rules.pdf_annotations import run_pdf_annotation_rule
from njit_auditor.rules.pdf_biosketch_bullet_spacing import check_pdf_biosketch_bullet_spacing
from njit_auditor.rules.pdf_biosketch_publication_layout import (
    check_pdf_biosketch_publication_layout,
)
from njit_auditor.rules.pdf_body_spacing import check_pdf_body_spacing
from njit_auditor.rules.pdf_captions import check_pdf_captions
from njit_auditor.rules.pdf_copyright_page import (
    check_pdf_copyright_author_format,
    check_pdf_copyright_page,
    check_pdf_copyright_year_format,
)
from njit_auditor.rules.pdf_dedication_page import check_pdf_dedication_page
from njit_auditor.rules.pdf_figure_table_layout import check_pdf_figure_table_layout
from njit_auditor.rules.pdf_font_compliance import check_pdf_font_compliance
from njit_auditor.rules.pdf_frontmatter_headings import check_pdf_frontmatter_headings
from njit_auditor.rules.pdf_frontmatter_no_page_number import (
    check_pdf_frontmatter_no_page_number,
)
from njit_auditor.rules.pdf_frontmatter_structure import check_pdf_frontmatter_structure
from njit_auditor.rules.pdf_heading_levels import check_pdf_heading_level_styles
from njit_auditor.rules.pdf_headings import check_named_frontmatter_headings
from njit_auditor.rules.pdf_indentation import check_pdf_indentation
from njit_auditor.rules.pdf_lof_terminal_punctuation import check_pdf_lof_terminal_punctuation
from njit_auditor.rules.pdf_lot_lof_column_header_style_alignment import (
    check_pdf_lot_lof_column_header_style_alignment,
    check_pdf_lot_lof_left_column_header_bold,
)
from njit_auditor.rules.pdf_lot_lof_column_headers import check_pdf_lot_lof_column_headers
from njit_auditor.rules.pdf_lot_lof_cross_page_entry_ordering import (
    check_pdf_lot_lof_cross_page_entry_ordering,
)
from njit_auditor.rules.pdf_lot_lof_entry_number_alignment import (
    check_pdf_lot_lof_entry_number_alignment,
)
from njit_auditor.rules.pdf_lot_lof_entry_number_ordering import (
    check_pdf_lot_lof_entry_number_ordering,
)
from njit_auditor.rules.pdf_lot_lof_entry_type import check_pdf_lot_lof_entry_type
from njit_auditor.rules.pdf_lot_lof_number_format import check_pdf_lot_lof_number_format
from njit_auditor.rules.pdf_lot_lof_page_number_alignment import (
    check_pdf_lot_lof_page_number_alignment,
)
from njit_auditor.rules.pdf_lot_lof_page_number_ordering import (
    check_pdf_lot_lof_page_number_ordering,
)
from njit_auditor.rules.pdf_lot_terminal_period import check_pdf_lot_terminal_period
from njit_auditor.rules.pdf_margins import run_pdf_margin_rule
from njit_auditor.rules.pdf_page_numbering_regime import check_pdf_page_numbering_regime
from njit_auditor.rules.pdf_page_numbers import (
    check_pdf_page_number_sequence,
    run_pdf_page_number_candidates_rule,
)
from njit_auditor.rules.pdf_roman_section_anchors import check_pdf_roman_section_anchors
from njit_auditor.rules.pdf_roman_sequence import check_pdf_roman_sequence
from njit_auditor.rules.pdf_spacing import check_pdf_spacing
from njit_auditor.rules.pdf_title_capitalization import check_pdf_title_capitalization
from njit_auditor.rules.pdf_title_consistency import check_pdf_title_consistency
from njit_auditor.rules.pdf_toc_alignment import check_pdf_toc_alignment
from njit_auditor.rules.pdf_toc_appendix_format import check_pdf_toc_appendix_format
from njit_auditor.rules.pdf_toc_continued_headings import check_pdf_toc_continued_headings
from njit_auditor.rules.pdf_toc_entry_hierarchy import check_pdf_toc_entry_hierarchy
from njit_auditor.rules.pdf_toc_entry_number_ordering import (
    check_pdf_toc_entry_number_ordering,
)
from njit_auditor.rules.pdf_toc_list_entry_spacing import check_pdf_toc_list_entry_spacing
from njit_auditor.rules.pdf_toc_list_formatting import check_pdf_toc_list_formatting
from njit_auditor.rules.pdf_toc_list_wrapped_spacing import check_pdf_toc_list_wrapped_spacing
from njit_auditor.rules.pdf_toc_page_number_ordering import (
    check_pdf_toc_page_number_ordering,
)
from njit_auditor.rules.pdf_toc_terminal_period import check_pdf_toc_terminal_period
from njit_auditor.upload_handling import (
    DEFAULT_MAX_UPLOAD_BYTES,
    MainTexDetectionError,
    UploadKind,
    UploadValidationError,
    ZipExtractionError,
    classify_upload,
    detect_main_tex,
    safe_extract_zip,
    validate_upload_path,
)

# Rule IDs added in P055–P061 (post-P054). Used by parity tests.
PDF_AUDIT_POST_P054_RULE_IDS: tuple[str, ...] = (
    "P055",
    "P056",
    "P057",
    "P058",
    "P059",
    "P060",
    "P061",
)

# Callable names for P055–P061 checks in execution order (parity tests).
PDF_AUDIT_POST_P054_CALLABLE_NAMES: tuple[str, ...] = (
    "check_pdf_lot_lof_entry_type",
    "check_pdf_lot_lof_number_format",
    "check_pdf_lot_lof_page_number_ordering",
    "check_pdf_toc_page_number_ordering",
    "check_pdf_lot_lof_entry_number_ordering",
    "check_pdf_toc_entry_number_ordering",
    "check_pdf_lot_lof_cross_page_entry_ordering",
)


class AuditError(Exception):
    """Raised when the audit cannot proceed (corrupt/invalid PDF)."""


TEX_JSON_EXPORT_LIMITATION = (
    "TeX source audit completed, but JSON/Markdown web export is not yet supported. "
    "Use njit-audit tex for console output."
)


@dataclass(frozen=True)
class UploadedAuditResult:
    """Structured result from :func:`run_audit_for_uploaded_file`."""

    upload_kind: UploadKind
    audit_type: str
    findings: list[AuditFinding]
    main_tex_path: Path | None = None
    loaded_tex_file_count: int | None = None
    json_export_supported: bool = True
    limitation_note: str = ""


def collect_tex_findings(
    main_tex_path: str | Path, include_optional_linters: bool = False
) -> tuple[Path, int, list[AuditFinding]]:
    """Load TeX project and run all P001–P010 source checks."""
    input_path = Path(main_tex_path)
    project = load_tex_project(input_path)
    findings: list[AuditFinding] = []
    findings.extend(run_latex_abstract_checks(project))
    findings.extend(run_latex_abstract_word_count_check(project))
    findings.extend(run_latex_graduation_month_check(project))
    findings.extend(run_latex_structure_checks(project))
    findings.extend(run_latex_risky_command_checks(project))
    findings.extend(run_latex_label_checks(project))
    findings.extend(run_latex_figure_table_checks(project))
    if include_optional_linters:
        findings.extend(run_optional_latex_linters(input_path))
    return project.main_path, len(project.files), findings


def collect_pdf_layout_findings(
    pdf_doc: PdfDocument, pdf_path: str | Path
) -> list[AuditFinding]:
    """Run the full P011–P061 PDF layout audit on a loaded document.

    This is the canonical rule sequence shared by the CLI and web UI.
    """
    path_str = str(pdf_path)
    findings: list[AuditFinding] = []
    findings.extend(run_pdf_page_number_candidates_rule(pdf_doc))
    findings.extend(check_pdf_page_number_sequence(pdf_doc))
    findings.extend(check_pdf_page_numbering_regime(pdf_doc))
    findings.extend(check_pdf_roman_sequence(pdf_doc))
    findings.extend(check_pdf_roman_section_anchors(pdf_doc))
    findings.extend(check_pdf_frontmatter_no_page_number(pdf_doc))
    findings.extend(run_pdf_margin_rule(pdf_doc))
    findings.extend(check_named_frontmatter_headings(pdf_doc))
    findings.extend(check_pdf_frontmatter_headings(pdf_doc))
    findings.extend(check_pdf_frontmatter_structure(pdf_doc))
    findings.extend(check_pdf_title_consistency(pdf_doc))
    findings.extend(check_pdf_copyright_page(pdf_doc))
    findings.extend(check_pdf_copyright_year_format(pdf_doc))
    findings.extend(check_pdf_copyright_author_format(pdf_doc))
    findings.extend(check_pdf_dedication_page(pdf_doc))
    findings.extend(check_pdf_abstract_word_count(pdf_doc))
    findings.extend(check_pdf_indentation(pdf_doc))
    findings.extend(check_pdf_abstract_indentation(pdf_doc))
    findings.extend(check_pdf_acknowledgements_indentation(pdf_doc))
    findings.extend(check_pdf_biosketch_publication_layout(pdf_doc))
    findings.extend(check_pdf_biosketch_bullet_spacing(pdf_doc))
    findings.extend(check_pdf_spacing(pdf_doc))
    findings.extend(check_pdf_body_spacing(pdf_doc))
    findings.extend(check_pdf_font_compliance(pdf_doc))
    findings.extend(check_pdf_captions(pdf_doc))
    findings.extend(check_pdf_figure_table_layout(pdf_doc))
    findings.extend(check_pdf_heading_level_styles(pdf_doc))
    findings.extend(check_pdf_toc_alignment(pdf_doc))
    findings.extend(check_pdf_toc_list_formatting(pdf_doc))
    findings.extend(check_pdf_toc_continued_headings(pdf_doc))
    findings.extend(check_pdf_lot_lof_column_headers(pdf_doc))
    findings.extend(check_pdf_lot_lof_entry_number_alignment(pdf_doc))
    findings.extend(check_pdf_lot_lof_page_number_alignment(pdf_doc))
    findings.extend(check_pdf_lot_lof_column_header_style_alignment(pdf_doc))
    findings.extend(check_pdf_lot_lof_left_column_header_bold(pdf_doc))
    findings.extend(check_pdf_toc_list_wrapped_spacing(pdf_doc))
    findings.extend(check_pdf_toc_list_entry_spacing(pdf_doc))
    findings.extend(check_pdf_toc_entry_hierarchy(pdf_doc))
    findings.extend(check_pdf_toc_appendix_format(pdf_doc))
    findings.extend(check_pdf_lof_terminal_punctuation(pdf_doc))
    findings.extend(check_pdf_lot_terminal_period(pdf_doc))
    findings.extend(check_pdf_toc_terminal_period(pdf_doc))
    findings.extend(check_pdf_lot_lof_entry_type(pdf_doc))
    findings.extend(check_pdf_lot_lof_number_format(pdf_doc))
    findings.extend(check_pdf_lot_lof_page_number_ordering(pdf_doc))
    findings.extend(check_pdf_toc_page_number_ordering(pdf_doc))
    findings.extend(check_pdf_lot_lof_entry_number_ordering(pdf_doc))
    findings.extend(check_pdf_toc_entry_number_ordering(pdf_doc))
    findings.extend(check_pdf_lot_lof_cross_page_entry_ordering(pdf_doc))
    findings.extend(check_pdf_title_capitalization(pdf_doc))
    findings.extend(run_pdf_annotation_rule(path_str))
    return findings


def run_pdf_audit_full(pdf_path: str | Path) -> list[AuditFinding]:
    """Run all P011–P061 PDF audit checks and return findings.

    Raises AuditError if the file cannot be opened or is not a valid PDF.
    """
    try:
        pdf_doc = load_pdf_layout(str(pdf_path))
    except (FileDataError, ValueError, RuntimeError) as exc:
        raise AuditError(f"Cannot read PDF: {exc}") from exc

    return collect_pdf_layout_findings(pdf_doc, pdf_path)


def run_pdf_audit(pdf_path: Path) -> list[AuditFinding]:
    """Backward-compatible alias for :func:`run_pdf_audit_full`."""
    return run_pdf_audit_full(pdf_path)


def run_audit_for_uploaded_file(
    path: Path,
    *,
    max_size_bytes: int = DEFAULT_MAX_UPLOAD_BYTES,
    work_dir: Path | None = None,
    include_optional_linters: bool = False,
) -> UploadedAuditResult:
    """Dispatch an on-disk upload to the correct audit mode (PDF, TeX, or ZIP→TeX)."""
    kind = validate_upload_path(path, max_size_bytes)

    if kind == UploadKind.PDF:
        try:
            findings = run_pdf_audit_full(path)
        except AuditError as exc:
            raise UploadValidationError(str(exc)) from exc
        return UploadedAuditResult(
            upload_kind=kind,
            audit_type="pdf",
            findings=findings,
            json_export_supported=True,
        )

    if kind == UploadKind.TEX:
        try:
            main_path, loaded_count, findings = collect_tex_findings(
                path, include_optional_linters=include_optional_linters
            )
        except (FileNotFoundError, OSError, ValueError) as exc:
            raise UploadValidationError(f"Cannot audit TeX file: {exc}") from exc
        return UploadedAuditResult(
            upload_kind=kind,
            audit_type="tex",
            findings=findings,
            main_tex_path=main_path,
            loaded_tex_file_count=loaded_count,
            json_export_supported=False,
            limitation_note=TEX_JSON_EXPORT_LIMITATION,
        )

    if kind == UploadKind.ZIP:
        extract_parent = work_dir if work_dir is not None else path.parent
        extract_dir = extract_parent / f"{path.stem}_extracted"
        cleanup_extract = work_dir is None
        try:
            safe_extract_zip(path, extract_dir)
            main_tex = detect_main_tex(extract_dir)
            main_path, loaded_count, findings = collect_tex_findings(
                main_tex, include_optional_linters=include_optional_linters
            )
        except (ZipExtractionError, MainTexDetectionError) as exc:
            if cleanup_extract and extract_dir.exists():
                shutil.rmtree(extract_dir, ignore_errors=True)
            raise UploadValidationError(str(exc)) from exc
        except (FileNotFoundError, OSError, ValueError) as exc:
            if cleanup_extract and extract_dir.exists():
                shutil.rmtree(extract_dir, ignore_errors=True)
            raise UploadValidationError(f"Cannot audit extracted TeX project: {exc}") from exc

        return UploadedAuditResult(
            upload_kind=kind,
            audit_type="tex",
            findings=findings,
            main_tex_path=main_path,
            loaded_tex_file_count=loaded_count,
            json_export_supported=False,
            limitation_note=TEX_JSON_EXPORT_LIMITATION,
        )

    unsupported = classify_upload(path)
    msg = f"Unsupported upload type: {unsupported.value}"
    raise UploadValidationError(msg)


def iter_pdf_audit_post_p054_callables() -> list[tuple[str, Callable[..., Any]]]:
    """Return P055–P061 rule callables in audit execution order (for tests)."""
    import njit_auditor.audit_runner as mod

    return [(name, getattr(mod, name)) for name in PDF_AUDIT_POST_P054_CALLABLE_NAMES]
