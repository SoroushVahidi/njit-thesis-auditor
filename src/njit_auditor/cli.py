"""CLI entry point for NJIT thesis auditing."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from njit_auditor.latex_linters import run_optional_latex_linters
from njit_auditor.latex_loader import load_tex_project
from njit_auditor.models import AuditFinding
from njit_auditor.pdf_layout import load_pdf_layout
from njit_auditor.pdf_loader import load_document_info
from njit_auditor.report import render_pdf_layout_report, render_report, render_tex_report
from njit_auditor.rules.abstract import run_abstract_checks
from njit_auditor.rules.latex_abstract import run_latex_abstract_checks
from njit_auditor.rules.latex_figures_tables import run_latex_figure_table_checks
from njit_auditor.rules.latex_labels import run_latex_label_checks
from njit_auditor.rules.latex_metadata import run_latex_graduation_month_check
from njit_auditor.rules.latex_risky_commands import run_latex_risky_command_checks
from njit_auditor.rules.latex_structure import run_latex_structure_checks
from njit_auditor.rules.page_numbers import run_page_number_rule
from njit_auditor.rules.pdf_annotations import run_pdf_annotation_rule
from njit_auditor.rules.pdf_margins import run_pdf_margin_rule
from njit_auditor.rules.pdf_page_numbers import run_pdf_page_number_candidates_rule
from njit_auditor.rules.title_page import run_title_page_month_check

app = typer.Typer(help="Local-first NJIT thesis/dissertation formatting auditor")
console = Console()


def collect_tex_findings(
    main_tex_path: str, include_optional_linters: bool = False
) -> tuple[Path, int, list[AuditFinding]]:
    """Load TeX project and run all phase-1 source checks."""
    input_path = Path(main_tex_path)
    project = load_tex_project(input_path)
    findings: list[AuditFinding] = []
    findings.extend(run_latex_abstract_checks(project))
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
def pdf(pdf_path: str) -> None:
    """Run Phase 2 foundation PDF layout audit."""

    input_path = Path(pdf_path)
    if not input_path.exists():
        console.print(f"[red]File not found:[/red] {input_path}")
        raise typer.Exit(code=1)
    if input_path.suffix.lower() != ".pdf":
        console.print("[red]Input must be a .pdf file for PDF layout audit.[/red]")
        raise typer.Exit(code=1)

    pdf_doc = load_pdf_layout(str(input_path))
    findings: list[AuditFinding] = []
    findings.extend(run_pdf_page_number_candidates_rule(pdf_doc))
    findings.extend(run_pdf_margin_rule(pdf_doc))
    findings.extend(run_pdf_annotation_rule(str(input_path)))

    page_sizes = [(page.page_number, page.width, page.height) for page in pdf_doc.pages]
    render_pdf_layout_report(
        console,
        document_path=pdf_doc.path,
        page_sizes=page_sizes,
        findings=findings,
    )


if __name__ == "__main__":
    app()
