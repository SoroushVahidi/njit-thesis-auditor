"""Python API for running the NJIT thesis PDF audit without the CLI layer."""

from __future__ import annotations

import logging
import shutil
import traceback
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pymupdf
from pymupdf import FileDataError

from njit_auditor.audit_options import DEFAULT_AUDIT_OPTIONS, AuditOptions
from njit_auditor.digital_commons_student_preview import (
    digital_commons_advisory_suggested_fix,
)
from njit_auditor.digital_commons_wrapper import (
    detect_digital_commons_wrapper_pages,
    digital_commons_wrapper_metadata,
    page_identity_details,
    without_wrapper_pages,
)
from njit_auditor.latex_linters import run_optional_latex_linters
from njit_auditor.latex_loader import load_tex_project
from njit_auditor.models import AuditFinding, Severity
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
from njit_auditor.rules.pdf_abstract import (
    check_pdf_abstract_keywords,
    check_pdf_abstract_word_count,
)
from njit_auditor.rules.pdf_abstract_indentation import check_pdf_abstract_indentation
from njit_auditor.rules.pdf_acknowledgements_indentation import (
    check_pdf_acknowledgements_indentation,
)
from njit_auditor.rules.pdf_annotations import run_pdf_annotation_rule
from njit_auditor.rules.pdf_appendix_body_headings import check_pdf_appendix_body_headings
from njit_auditor.rules.pdf_approval_page_committee_blocks import (
    check_pdf_approval_page_committee_blocks,
)
from njit_auditor.rules.pdf_biosketch_birth_information import (
    check_pdf_biosketch_birth_information,
)
from njit_auditor.rules.pdf_biosketch_bullet_spacing import check_pdf_biosketch_bullet_spacing
from njit_auditor.rules.pdf_biosketch_degree_ordering import (
    check_pdf_biosketch_degree_ordering,
)
from njit_auditor.rules.pdf_biosketch_publication_layout import (
    check_pdf_biosketch_publication_layout,
)
from njit_auditor.rules.pdf_biosketch_publication_ordering import (
    check_pdf_biosketch_publication_ordering,
)
from njit_auditor.rules.pdf_body_heading_spacing import check_pdf_body_heading_spacing
from njit_auditor.rules.pdf_body_spacing import check_pdf_body_spacing
from njit_auditor.rules.pdf_captions import check_pdf_captions
from njit_auditor.rules.pdf_copyright_page import (
    check_pdf_copyright_author_format,
    check_pdf_copyright_page,
    check_pdf_copyright_year_format,
)
from njit_auditor.rules.pdf_dedication_centering_italic import (
    check_pdf_dedication_centering_italic,
)
from njit_auditor.rules.pdf_dedication_page import check_pdf_dedication_page
from njit_auditor.rules.pdf_figure_table_layout import check_pdf_figure_table_layout
from njit_auditor.rules.pdf_first_chapter_heading import check_pdf_first_chapter_heading
from njit_auditor.rules.pdf_font_compliance import check_pdf_font_compliance
from njit_auditor.rules.pdf_frontmatter_headings import check_pdf_frontmatter_headings
from njit_auditor.rules.pdf_frontmatter_no_page_number import (
    check_pdf_frontmatter_no_page_number,
)
from njit_auditor.rules.pdf_frontmatter_structure import (
    check_pdf_frontmatter_structure,
    check_pdf_title_page_graduation_month,
)
from njit_auditor.rules.pdf_heading_levels import check_pdf_heading_level_styles
from njit_auditor.rules.pdf_headings import check_named_frontmatter_headings
from njit_auditor.rules.pdf_indentation import check_pdf_indentation
from njit_auditor.rules.pdf_landscape_page_number_orientation import (
    check_pdf_landscape_page_number_orientation,
)
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
from njit_auditor.rules.pdf_references_citations_structural import (
    check_pdf_references_citations_structural,
)
from njit_auditor.rules.pdf_roman_section_anchors import check_pdf_roman_section_anchors
from njit_auditor.rules.pdf_roman_sequence import check_pdf_roman_sequence
from njit_auditor.rules.pdf_spacing import check_pdf_spacing
from njit_auditor.rules.pdf_title_capitalization import check_pdf_title_capitalization
from njit_auditor.rules.pdf_title_consistency import check_pdf_title_consistency
from njit_auditor.rules.pdf_toc_alignment import check_pdf_toc_alignment
from njit_auditor.rules.pdf_toc_appendix_format import check_pdf_toc_appendix_format
from njit_auditor.rules.pdf_toc_continued_headings import check_pdf_toc_continued_headings
from njit_auditor.rules.pdf_toc_cross_page_entry_ordering import (
    check_pdf_toc_cross_page_entry_ordering,
)
from njit_auditor.rules.pdf_toc_entry_hierarchy import check_pdf_toc_entry_hierarchy
from njit_auditor.rules.pdf_toc_entry_number_ordering import (
    check_pdf_toc_entry_number_ordering,
)
from njit_auditor.rules.pdf_toc_leader_consistency import check_pdf_toc_leader_consistency
from njit_auditor.rules.pdf_toc_list_entry_spacing import check_pdf_toc_list_entry_spacing
from njit_auditor.rules.pdf_toc_list_formatting import check_pdf_toc_list_formatting
from njit_auditor.rules.pdf_toc_list_wrapped_spacing import check_pdf_toc_list_wrapped_spacing
from njit_auditor.rules.pdf_toc_page_number_ordering import (
    check_pdf_toc_page_number_ordering,
)
from njit_auditor.rules.pdf_toc_terminal_period import check_pdf_toc_terminal_period
from njit_auditor.rules.pdf_unnumbered_bold_heading import check_pdf_unnumbered_bold_heading
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

# Rule IDs added in P055–P068 (post-P054). Used by parity tests.
PDF_AUDIT_POST_P054_RULE_IDS: tuple[str, ...] = (
    "P055",
    "P056",
    "P057",
    "P058",
    "P059",
    "P060",
    "P061",
    "P062",
    "P063",
    "P064",
    "P065",
    "P066",
    "P067",
    "P068",
)

# Callable names for P055–P068 checks in execution order (parity tests).
PDF_AUDIT_POST_P054_CALLABLE_NAMES: tuple[str, ...] = (
    "check_pdf_lot_lof_entry_type",
    "check_pdf_lot_lof_number_format",
    "check_pdf_lot_lof_page_number_ordering",
    "check_pdf_toc_page_number_ordering",
    "check_pdf_lot_lof_entry_number_ordering",
    "check_pdf_toc_entry_number_ordering",
    "check_pdf_lot_lof_cross_page_entry_ordering",
    "check_pdf_toc_cross_page_entry_ordering",
    "check_pdf_appendix_body_headings",
    "check_pdf_references_citations_structural",
    "check_pdf_dedication_centering_italic",
    "check_pdf_biosketch_degree_ordering",
    "check_pdf_biosketch_publication_ordering",
    "check_pdf_approval_page_committee_blocks",
)


class AuditError(Exception):
    """Raised when the audit cannot proceed (corrupt/invalid PDF)."""


_logger = logging.getLogger(__name__)


def _exception_location(exc: BaseException) -> str:
    """Return ``file:line in function`` frames for *exc*, innermost last.

    Deliberately omits the exception message, source lines, and directories:
    messages can carry upload paths (which contain the job ID that grants
    access to a report) or text extracted from the dissertation, and the web
    service logs to the system journal.
    """
    frames = traceback.extract_tb(exc.__traceback__)
    return " <- ".join(
        f"{Path(frame.filename).name}:{frame.lineno} in {frame.name}"
        for frame in reversed(frames)
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
    # Names of PDF checks that raised and were skipped (only when isolation is on).
    failed_checks: tuple[str, ...] = ()


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
    pdf_doc: PdfDocument,
    pdf_path: str | Path,
    *,
    options: AuditOptions | None = None,
    check_failures: list[str] | None = None,
) -> list[AuditFinding]:
    """Run the current implemented PDF layout audit on a loaded document.

    This is the canonical rule sequence shared by the CLI and web UI, including
    embedded infrastructure refinements (P069–P071) wired through existing checks.

    By default an exception in any check propagates, so evaluation and CLI runs
    fail loudly. When *check_failures* is a list, each check is isolated instead:
    a check that raises is logged with its traceback, its name is appended to
    the list, and the remaining checks still run.
    """

    def run_check(
        check: Callable[..., list[AuditFinding]], *args: Any, **kwargs: Any
    ) -> list[AuditFinding]:
        if check_failures is None:
            return check(*args, **kwargs)
        try:
            return check(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 - isolation is the point; logged below
            name = getattr(check, "__name__", type(check).__name__)
            _logger.error(
                "PDF check %s failed with %s at %s; continuing without it",
                name,
                type(exc).__name__,
                _exception_location(exc),
            )
            check_failures.append(name)
            return []

    path_str = str(pdf_path)
    audit_options = options or DEFAULT_AUDIT_OPTIONS
    wrapper_pages = detect_digital_commons_wrapper_pages(pdf_doc)
    content_doc = without_wrapper_pages(pdf_doc, wrapper_pages)
    findings: list[AuditFinding] = []
    findings.extend(
        run_check(run_pdf_page_number_candidates_rule, content_doc, skip_pages=wrapper_pages)
    )
    findings.extend(run_check(check_pdf_page_number_sequence, content_doc))
    findings.extend(
        run_check(
            check_pdf_landscape_page_number_orientation,
            content_doc,
            enabled=audit_options.is_experimental_enabled("P082"),
        )
    )
    findings.extend(run_check(check_pdf_page_numbering_regime, content_doc))
    findings.extend(run_check(check_pdf_roman_sequence, content_doc))
    findings.extend(run_check(check_pdf_roman_section_anchors, content_doc))
    findings.extend(run_check(check_pdf_frontmatter_no_page_number, content_doc))
    findings.extend(run_check(run_pdf_margin_rule, content_doc, skip_pages=wrapper_pages))
    findings.extend(run_check(check_named_frontmatter_headings, content_doc))
    findings.extend(run_check(check_pdf_frontmatter_headings, content_doc))
    findings.extend(run_check(check_pdf_frontmatter_structure, content_doc))
    findings.extend(run_check(check_pdf_title_page_graduation_month, content_doc))
    findings.extend(run_check(check_pdf_title_consistency, content_doc))
    findings.extend(run_check(check_pdf_copyright_page, content_doc))
    findings.extend(run_check(check_pdf_copyright_year_format, content_doc))
    findings.extend(run_check(check_pdf_copyright_author_format, content_doc))
    findings.extend(run_check(check_pdf_dedication_page, content_doc))
    findings.extend(run_check(check_pdf_abstract_word_count, content_doc))
    findings.extend(run_check(check_pdf_abstract_keywords, content_doc))
    findings.extend(run_check(check_pdf_indentation, content_doc))
    findings.extend(run_check(check_pdf_abstract_indentation, content_doc))
    findings.extend(run_check(check_pdf_acknowledgements_indentation, content_doc))
    findings.extend(run_check(check_pdf_biosketch_birth_information, content_doc))
    findings.extend(run_check(check_pdf_biosketch_publication_layout, content_doc))
    findings.extend(run_check(check_pdf_biosketch_bullet_spacing, content_doc))
    findings.extend(run_check(check_pdf_spacing, content_doc))
    findings.extend(run_check(check_pdf_body_spacing, content_doc))
    findings.extend(run_check(check_pdf_body_heading_spacing, content_doc))
    findings.extend(run_check(check_pdf_font_compliance, content_doc))
    findings.extend(run_check(check_pdf_captions, content_doc))
    findings.extend(run_check(check_pdf_figure_table_layout, content_doc))
    findings.extend(run_check(check_pdf_heading_level_styles, content_doc))
    findings.extend(run_check(check_pdf_first_chapter_heading, content_doc))
    findings.extend(run_check(check_pdf_unnumbered_bold_heading, content_doc))
    findings.extend(run_check(check_pdf_toc_alignment, content_doc))
    findings.extend(run_check(check_pdf_toc_leader_consistency, content_doc))
    findings.extend(run_check(check_pdf_toc_list_formatting, content_doc))
    findings.extend(run_check(check_pdf_toc_continued_headings, content_doc))
    findings.extend(run_check(check_pdf_lot_lof_column_headers, content_doc))
    findings.extend(run_check(check_pdf_lot_lof_entry_number_alignment, content_doc))
    findings.extend(run_check(check_pdf_lot_lof_page_number_alignment, content_doc))
    findings.extend(run_check(check_pdf_lot_lof_column_header_style_alignment, content_doc))
    findings.extend(run_check(check_pdf_lot_lof_left_column_header_bold, content_doc))
    findings.extend(run_check(check_pdf_toc_list_wrapped_spacing, content_doc))
    findings.extend(run_check(check_pdf_toc_list_entry_spacing, content_doc))
    findings.extend(run_check(check_pdf_toc_entry_hierarchy, content_doc))
    findings.extend(run_check(check_pdf_toc_appendix_format, content_doc))
    findings.extend(run_check(check_pdf_lof_terminal_punctuation, content_doc))
    findings.extend(run_check(check_pdf_lot_terminal_period, content_doc))
    findings.extend(run_check(check_pdf_toc_terminal_period, content_doc))
    findings.extend(run_check(check_pdf_lot_lof_entry_type, content_doc))
    findings.extend(run_check(check_pdf_lot_lof_number_format, content_doc))
    findings.extend(run_check(check_pdf_lot_lof_page_number_ordering, content_doc))
    findings.extend(run_check(check_pdf_toc_page_number_ordering, content_doc))
    findings.extend(run_check(check_pdf_lot_lof_entry_number_ordering, content_doc))
    findings.extend(run_check(check_pdf_toc_entry_number_ordering, content_doc))
    findings.extend(run_check(check_pdf_lot_lof_cross_page_entry_ordering, content_doc))
    findings.extend(run_check(check_pdf_toc_cross_page_entry_ordering, content_doc))
    findings.extend(run_check(check_pdf_appendix_body_headings, content_doc))
    findings.extend(run_check(check_pdf_references_citations_structural, content_doc))
    findings.extend(run_check(check_pdf_dedication_centering_italic, content_doc))
    findings.extend(run_check(check_pdf_biosketch_degree_ordering, content_doc))
    findings.extend(run_check(check_pdf_biosketch_publication_ordering, content_doc))
    findings.extend(run_check(check_pdf_approval_page_committee_blocks, content_doc))
    findings.extend(run_check(check_pdf_title_capitalization, content_doc))
    findings.extend(run_check(run_pdf_annotation_rule, path_str, skip_pages=wrapper_pages))
    if wrapper_pages:
        wrapper_meta = digital_commons_wrapper_metadata(sorted(wrapper_pages))
        first_page = min(wrapper_pages)
        findings.append(
            AuditFinding(
                rule_id="P025",
                severity=Severity.WARNING,
                page=first_page,
                message=(
                    "Repository-generated Digital Commons wrapper pages were detected "
                    "before the thesis manuscript."
                ),
                details={
                    "issue_type": "digital_commons_wrapper_pages_detected",
                    **wrapper_meta,
                    "triage_tier": "review",
                    "confidence": "high",
                    "suggested_fix": digital_commons_advisory_suggested_fix(),
                },
            )
        )
    page_details_by_number = {
        page.page_number: page_identity_details(page)
        for page in content_doc.pages
    }
    enriched_findings: list[AuditFinding] = []
    for finding in findings:
        page_details = (
            page_details_by_number.get(finding.page, {})
            if finding.page is not None
            else {}
        )
        if not page_details:
            enriched_findings.append(finding)
            continue
        merged_details = dict(page_details)
        merged_details.update(finding.details)
        enriched_findings.append(finding.model_copy(update={"details": merged_details}))
    findings = enriched_findings
    return findings


def run_pdf_audit_full(
    pdf_path: str | Path,
    *,
    options: AuditOptions | None = None,
    check_failures: list[str] | None = None,
) -> list[AuditFinding]:
    """Run all registered PDF layout audit checks and return findings.

    Raises AuditError if the file cannot be opened or is not a valid PDF.
    See :func:`collect_pdf_layout_findings` for *check_failures*.
    """
    try:
        pdf_doc = load_pdf_layout(str(pdf_path))
    except (FileDataError, ValueError, RuntimeError) as exc:
        raise AuditError(f"Cannot read PDF: {exc}") from exc

    return collect_pdf_layout_findings(
        pdf_doc, pdf_path, options=options, check_failures=check_failures
    )


def run_pdf_audit(pdf_path: Path) -> list[AuditFinding]:
    """Backward-compatible alias for :func:`run_pdf_audit_full`."""
    return run_pdf_audit_full(pdf_path)


def run_audit_for_uploaded_file(
    path: Path,
    *,
    max_size_bytes: int = DEFAULT_MAX_UPLOAD_BYTES,
    work_dir: Path | None = None,
    include_optional_linters: bool = False,
    isolate_check_failures: bool = False,
) -> UploadedAuditResult:
    """Dispatch an on-disk upload to the correct audit mode (PDF, TeX, or ZIP→TeX).

    With *isolate_check_failures*, a PDF check that raises is logged and
    skipped, and its name is reported in ``failed_checks``; otherwise the
    exception propagates.
    """
    kind = validate_upload_path(path, max_size_bytes)

    if kind == UploadKind.PDF:
        check_failures: list[str] = []
        try:
            if isolate_check_failures:
                findings = run_pdf_audit_full(path, check_failures=check_failures)
            else:
                findings = run_pdf_audit_full(path)
        except AuditError as exc:
            raise UploadValidationError(str(exc)) from exc
        return UploadedAuditResult(
            upload_kind=kind,
            audit_type="pdf",
            findings=findings,
            json_export_supported=True,
            failed_checks=tuple(check_failures),
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
            json_export_supported=True,
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
            json_export_supported=True,
        )

    unsupported = classify_upload(path)
    msg = f"Unsupported upload type: {unsupported.value}"
    raise UploadValidationError(msg)


def classify_pdf_text_layer(pdf_path: Path) -> str:
    """Return a text-layer quality label for a PDF's first five pages.

    Samples up to five pages and sums the length of all extractable text.
    Returns one of:
      - ``"image_only"``  — zero extractable characters across all sampled pages
      - ``"low_text"``    — some text, but fewer than 100 chars per sampled page
      - ``"text_layer_ok"`` — normal amount of extractable text
      - ``""``            — classification could not be performed (not a PDF / error)
    """
    try:
        with pymupdf.open(str(pdf_path)) as doc:
            n = min(5, len(doc))
            if n == 0:
                return "image_only"
            total_chars = sum(len(doc[i].get_text()) for i in range(n))
    except Exception:  # noqa: BLE001
        return ""
    if total_chars == 0:
        return "image_only"
    if total_chars < 100 * n:
        return "low_text"
    return "text_layer_ok"


def iter_pdf_audit_post_p054_callables() -> list[tuple[str, Callable[..., Any]]]:
    """Return P055–P068 rule callables in audit execution order (for tests)."""
    import njit_auditor.audit_runner as mod

    return [(name, getattr(mod, name)) for name in PDF_AUDIT_POST_P054_CALLABLE_NAMES]
