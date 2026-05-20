"""CLI entry point for NJIT thesis auditing."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from njit_auditor.models import AuditFinding
from njit_auditor.pdf_loader import load_document_info
from njit_auditor.report import render_report
from njit_auditor.rules.abstract import run_abstract_checks
from njit_auditor.rules.page_numbers import run_page_number_rule
from njit_auditor.rules.title_page import run_title_page_month_check

app = typer.Typer(help="Local-first NJIT thesis/dissertation formatting auditor")
console = Console()


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


if __name__ == "__main__":
    app()
