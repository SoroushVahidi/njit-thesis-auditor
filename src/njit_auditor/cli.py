"""CLI entry point for NJIT thesis auditing."""

from __future__ import annotations

from pathlib import Path

import typer
from pymupdf import FileDataError
from rich.console import Console

from njit_auditor.latex_linters import run_optional_latex_linters
from njit_auditor.latex_loader import load_tex_project
from njit_auditor.models import AuditFinding
from njit_auditor.pdf_comments import (
    extract_pdf_annotations,
    remove_pdf_annotations,
    write_annotations_json,
    write_annotations_markdown,
)
from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.pdf_loader import load_document_info
from njit_auditor.report import render_pdf_layout_report, render_report, render_tex_report
from njit_auditor.report_outputs import write_json_report, write_markdown_report
from njit_auditor.rules.abstract import run_abstract_checks
from njit_auditor.rules.latex_abstract import (
    run_latex_abstract_checks,
    run_latex_abstract_word_count_check,
)
from njit_auditor.rules.latex_figures_tables import run_latex_figure_table_checks
from njit_auditor.rules.latex_labels import run_latex_label_checks
from njit_auditor.rules.latex_metadata import run_latex_graduation_month_check
from njit_auditor.rules.latex_risky_commands import run_latex_risky_command_checks
from njit_auditor.rules.latex_structure import run_latex_structure_checks
from njit_auditor.rules.page_numbers import run_page_number_rule
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
from njit_auditor.rules.pdf_margins import run_pdf_margin_rule
from njit_auditor.rules.pdf_page_numbering_regime import (
    check_pdf_page_numbering_regime,
)
from njit_auditor.rules.pdf_page_numbers import (
    check_pdf_page_number_sequence,
    run_pdf_page_number_candidates_rule,
)
from njit_auditor.rules.pdf_roman_section_anchors import (
    check_pdf_roman_section_anchors,
)
from njit_auditor.rules.pdf_roman_sequence import (
    check_pdf_roman_sequence,
)
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
from njit_auditor.rules.title_page import run_title_page_month_check

app = typer.Typer(help="Local-first NJIT thesis/dissertation formatting auditor")
pdf_comments_app = typer.Typer(help="PDF annotation extraction and clean-copy workflow.")
console = Console()


def collect_tex_findings(
    main_tex_path: str, include_optional_linters: bool = False
) -> tuple[Path, int, list[AuditFinding]]:
    """Load TeX project and run all phase-1 source checks."""
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


@app.command()
def audit(pdf_path: str) -> None:
    """Audit a thesis/dissertation PDF using local checks only."""
    input_path = Path(pdf_path)
    if not input_path.exists():
        console.print(f"[red]File not found:[/red] {input_path}")
        raise typer.Exit(code=1)

    if input_path.suffix.lower() != ".pdf":
        console.print("[red]Only PDF input is supported in the initial MVP.[/red]")
        raise typer.Exit(code=1)

    doc_info = load_document_info(str(input_path))

    findings: list[AuditFinding] = []
    findings.extend(run_page_number_rule(str(input_path)))
    findings.extend(run_abstract_checks(str(input_path)))
    findings.extend(run_title_page_month_check(str(input_path)))

    render_report(console, doc_info, findings)


@app.command()
def tex(main_tex_path: str, linters: bool = False) -> None:
    """Audit a TeX source project without compiling it."""
    input_path = Path(main_tex_path)
    if not input_path.exists():
        console.print(f"[red]File not found:[/red] {input_path}")
        raise typer.Exit(code=1)
    if input_path.suffix.lower() != ".tex":
        console.print("[red]Input must be a .tex file for source-only audit.[/red]")
        raise typer.Exit(code=1)

    main_path, loaded_file_count, findings = collect_tex_findings(
        main_tex_path, include_optional_linters=linters
    )

    render_tex_report(
        console,
        main_file=str(main_path),
        loaded_file_count=loaded_file_count,
        findings=findings,
    )


@app.command()
def pdf(
    pdf_path: str,
    json_out: str | None = typer.Option(None, "--json-out", help="Path to JSON report output."),
    md_out: str | None = typer.Option(None, "--md-out", help="Path to Markdown report output."),
) -> None:
    """Run Phase 2 foundation PDF layout audit."""

    input_path = Path(pdf_path)
    if not input_path.exists():
        console.print(f"[red]File not found:[/red] {input_path}")
        raise typer.Exit(code=1)
    if input_path.suffix.lower() != ".pdf":
        console.print("[red]Input must be a .pdf file for PDF layout audit.[/red]")
        raise typer.Exit(code=1)

    try:
        pdf_doc = load_pdf_layout(str(input_path))
    except (FileDataError, ValueError, RuntimeError) as exc:
        console.print(f"[red]Unable to read PDF:[/red] {input_path}")
        console.print(f"[yellow]Reason:[/yellow] {exc}")
        raise typer.Exit(code=1) from exc
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
    findings.extend(check_pdf_title_capitalization(pdf_doc))
    findings.extend(run_pdf_annotation_rule(str(input_path)))

    page_sizes = [(page.page_number, page.width, page.height) for page in pdf_doc.pages]
    render_pdf_layout_report(
        console,
        document_path=pdf_doc.path,
        page_sizes=page_sizes,
        findings=findings,
    )

    report_metadata = {
        "input_file_path": str(input_path),
        "input_file_name": input_path.name,
        "audit_type": "pdf",
    }
    if json_out:
        json_path = Path(json_out)
        try:
            write_json_report(findings, report_metadata, json_path)
        except OSError as exc:
            console.print(f"[red]Unable to write JSON report:[/red] {json_path}")
            console.print(f"[yellow]Reason:[/yellow] {exc}")
            raise typer.Exit(code=1) from exc
        console.print(f"[green]JSON report:[/green] {json_path}")
    if md_out:
        md_path = Path(md_out)
        try:
            write_markdown_report(findings, report_metadata, md_path)
        except OSError as exc:
            console.print(f"[red]Unable to write Markdown report:[/red] {md_path}")
            console.print(f"[yellow]Reason:[/yellow] {exc}")
            raise typer.Exit(code=1) from exc
        console.print(f"[green]Markdown report:[/green] {md_path}")


@pdf_comments_app.command("extract")
def pdf_comments_extract(
    input_pdf: str,
    json_out: str = typer.Option(..., "--json-out", help="Path to JSON annotation output."),
    md_out: str = typer.Option(..., "--md-out", help="Path to Markdown annotation output."),
) -> None:
    """Extract annotation metadata from PDF into JSON/Markdown."""
    input_path = Path(input_pdf)
    if not input_path.exists():
        console.print(f"[red]File not found:[/red] {input_path}")
        raise typer.Exit(code=1)
    if input_path.suffix.lower() != ".pdf":
        console.print("[red]Input must be a .pdf file.[/red]")
        raise typer.Exit(code=1)
    try:
        annotations = extract_pdf_annotations(input_path)
    except (FileDataError, ValueError, RuntimeError) as exc:
        console.print(f"[red]Unable to read PDF:[/red] {input_path}")
        console.print(f"[yellow]Reason:[/yellow] {exc}")
        raise typer.Exit(code=1) from exc

    json_path = Path(json_out)
    md_path = Path(md_out)
    write_annotations_json(annotations, json_path)
    write_annotations_markdown(annotations, md_path)
    console.print(f"[green]Extracted annotations:[/green] {len(annotations)}")
    console.print(f"[green]JSON:[/green] {json_path}")
    console.print(f"[green]Markdown:[/green] {md_path}")


@pdf_comments_app.command("clean")
def pdf_comments_clean(
    input_pdf: str,
    out: str = typer.Option(..., "--out", help="Path to cleaned PDF output."),
) -> None:
    """Create a copy of PDF with annotation objects removed."""
    input_path = Path(input_pdf)
    if not input_path.exists():
        console.print(f"[red]File not found:[/red] {input_path}")
        raise typer.Exit(code=1)
    if input_path.suffix.lower() != ".pdf":
        console.print("[red]Input must be a .pdf file.[/red]")
        raise typer.Exit(code=1)
    out_path = Path(out)
    if out_path.resolve() == input_path.resolve():
        console.print("[red]Output path must differ from input path.[/red]")
        raise typer.Exit(code=1)
    try:
        remove_pdf_annotations(input_path, out_path)
    except (FileDataError, ValueError, RuntimeError) as exc:
        console.print(f"[red]Unable to process PDF:[/red] {input_path}")
        console.print(f"[yellow]Reason:[/yellow] {exc}")
        raise typer.Exit(code=1) from exc
    console.print(f"[green]Clean PDF created:[/green] {out_path}")


app.add_typer(pdf_comments_app, name="pdf-comments")


if __name__ == "__main__":
    app()
