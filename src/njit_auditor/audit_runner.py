"""Python API for running the NJIT thesis PDF audit without the CLI layer."""

from __future__ import annotations

from pathlib import Path

from pymupdf import FileDataError

from njit_auditor.models import AuditFinding
from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.rules.abstract import run_abstract_checks
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
from njit_auditor.rules.pdf_lot_lof_entry_number_alignment import (
    check_pdf_lot_lof_entry_number_alignment,
)
from njit_auditor.rules.pdf_lot_lof_page_number_alignment import (
    check_pdf_lot_lof_page_number_alignment,
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
from njit_auditor.rules.pdf_toc_list_entry_spacing import check_pdf_toc_list_entry_spacing
from njit_auditor.rules.pdf_toc_list_formatting import check_pdf_toc_list_formatting
from njit_auditor.rules.pdf_toc_list_wrapped_spacing import check_pdf_toc_list_wrapped_spacing
from njit_auditor.rules.pdf_toc_terminal_period import check_pdf_toc_terminal_period


class AuditError(Exception):
    """Raised when the audit cannot proceed (corrupt/invalid PDF)."""


def run_pdf_audit(pdf_path: Path) -> list[AuditFinding]:
    """Run all P011–P054 PDF audit checks and return findings.

    Raises AuditError if the file cannot be opened or is not a valid PDF.
    """
    try:
        pdf_doc = load_pdf_layout(str(pdf_path))
    except (FileDataError, ValueError, RuntimeError) as exc:
        raise AuditError(f"Cannot read PDF: {exc}") from exc

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
    findings.extend(check_pdf_title_capitalization(pdf_doc))
    findings.extend(run_pdf_annotation_rule(str(pdf_path)))

    # Legacy abstract/page-number checks (TeX-era wrappers still useful for PDFs)
    findings.extend(run_abstract_checks(str(pdf_path)))

    return findings
