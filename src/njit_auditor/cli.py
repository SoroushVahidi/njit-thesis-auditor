"""CLI entry point for NJIT thesis auditing."""

from __future__ import annotations

from pathlib import Path

import typer
from pymupdf import FileDataError
from rich.console import Console

from njit_auditor.audit_options import AuditOptions
from njit_auditor.audit_runner import collect_pdf_layout_findings, collect_tex_findings
from njit_auditor.docx_comments import (
    count_docx_tracked_changes,
    extract_docx_comments,
    write_docx_comments_json,
    write_docx_comments_markdown,
)
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
from njit_auditor.rules.page_numbers import run_page_number_rule
from njit_auditor.rules.title_page import run_title_page_month_check

app = typer.Typer(help="Local-first NJIT thesis/dissertation formatting auditor")
pdf_comments_app = typer.Typer(help="PDF annotation extraction and clean-copy workflow.")
docx_comments_app = typer.Typer(help="DOCX comment and tracked-change extraction.")
console = Console()


@app.command()
def audit(pdf_path: str) -> None:
    """[Legacy] Run only the original page-number/abstract/title-month checks.

    Kept for backward compatibility. For the full PDF layout audit
    (all implemented P011+ rules, JSON/Markdown export), use `njit-audit pdf` instead.
    """
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
def tex(
    main_tex_path: str,
    linters: bool = False,
    json_out: str | None = typer.Option(None, "--json-out", help="Path to JSON report output."),
    md_out: str | None = typer.Option(None, "--md-out", help="Path to Markdown report output."),
) -> None:
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

    report_metadata = {
        "input_file_path": str(input_path),
        "input_file_name": input_path.name,
        "audit_type": "tex",
        "input_kind": "tex",
        "main_tex_path": str(main_path),
        "loaded_tex_file_count": str(loaded_file_count),
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


@app.command()
def pdf(
    pdf_path: str,
    json_out: str | None = typer.Option(None, "--json-out", help="Path to JSON report output."),
    md_out: str | None = typer.Option(None, "--md-out", help="Path to Markdown report output."),
    enable_experimental: list[str] = typer.Option(
        [],
        "--enable-experimental",
        help="Enable experimental opt-in rules (e.g. P082). Repeatable.",
    ),
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

    audit_options = AuditOptions(experimental_rules=frozenset(enable_experimental))
    findings = collect_pdf_layout_findings(pdf_doc, input_path, options=audit_options)

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


@docx_comments_app.command("extract")
def docx_comments_extract(
    input_docx: str,
    json_out: str = typer.Option(..., "--json-out", help="Path to JSON output."),
    md_out: str = typer.Option(..., "--md-out", help="Path to Markdown output."),
) -> None:
    """Extract comment and tracked-change metadata from a DOCX into JSON/Markdown."""
    input_path = Path(input_docx)
    if not input_path.exists():
        console.print(f"[red]File not found:[/red] {input_path}")
        raise typer.Exit(code=1)
    if input_path.suffix.lower() != ".docx":
        console.print("[red]Input must be a .docx file.[/red]")
        raise typer.Exit(code=1)

    comments = extract_docx_comments(input_path)
    tracked = count_docx_tracked_changes(input_path)

    json_path = Path(json_out)
    md_path = Path(md_out)
    write_docx_comments_json(comments, tracked, json_path)
    write_docx_comments_markdown(comments, tracked, md_path)

    console.print(f"[green]Comments extracted:[/green] {len(comments)}")
    console.print(
        f"[green]Tracked changes:[/green] "
        f"{tracked['insertions']} insertions, {tracked['deletions']} deletions"
    )
    console.print(f"[green]JSON:[/green] {json_path}")
    console.print(f"[green]Markdown:[/green] {md_path}")


app.add_typer(docx_comments_app, name="docx-comments")


if __name__ == "__main__":
    app()
