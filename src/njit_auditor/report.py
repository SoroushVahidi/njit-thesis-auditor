"""Reporting helpers for terminal output."""

from __future__ import annotations

from collections import Counter

from rich.console import Console
from rich.table import Table

from njit_auditor.models import AuditFinding, DocumentInfo, Severity


def _severity_color(severity: Severity) -> str:
    if severity == Severity.PASS:
        return "green"
    if severity == Severity.WARNING:
        return "yellow"
    return "red"


def render_report(console: Console, doc_info: DocumentInfo, findings: list[AuditFinding]) -> None:
    """Print a concise audit report."""
    console.print(f"[bold]Document[/bold]: {doc_info.path}")
    console.print(f"[bold]Pages[/bold]: {doc_info.page_count}")

    page_sizes = ", ".join(
        f"p{p.page_index + 1}: {p.width:.1f}x{p.height:.1f} pt" for p in doc_info.pages
    )
    console.print(f"[bold]Page sizes[/bold]: {page_sizes}")

    counts = Counter(item.severity for item in findings)
    console.print(
        "[bold]Summary[/bold]: "
        f"[green]PASS {counts.get(Severity.PASS, 0)}[/green], "
        f"[yellow]WARNING {counts.get(Severity.WARNING, 0)}[/yellow], "
        f"[red]FAIL {counts.get(Severity.FAIL, 0)}[/red]"
    )

    table = Table(title="Audit Findings")
    table.add_column("Severity", no_wrap=True)
    table.add_column("Rule", no_wrap=True)
    table.add_column("Page", no_wrap=True)
    table.add_column("Message")

    for finding in findings:
        color = _severity_color(finding.severity)
        page = str(finding.page) if finding.page is not None else "-"
        message = finding.message
        if finding.details:
            detail_parts = [f"{key}={value}" for key, value in finding.details.items()]
            message += f" ({'; '.join(detail_parts)})"

        table.add_row(
            f"[{color}]{finding.severity.value}[/{color}]",
            finding.rule_id,
            page,
            message,
        )

    console.print(table)
