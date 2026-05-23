# njit-thesis-auditor

`njit-thesis-auditor` is an early research prototype for auditing NJIT thesis/dissertation formatting.

This project is:
- local-first and free
- offline by default for document analysis
- not an official NJIT tool

The initial MVP does **not** send documents to any external service and does not use paid APIs.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Usage

```bash
njit-audit audit thesis.pdf
```

The command currently:
- loads the PDF
- prints page count and page sizes
- runs initial local rules
- prints a report with `PASS`, `WARNING`, and `FAIL` severities

## PDF layout audit

```bash
njit-audit pdf path/to/thesis.pdf
njit-audit pdf path/to/thesis.pdf --json-out report.json --md-out report.md
```

This command runs the Phase 2 layout foundation checks on digital PDFs:
page-size extraction, page-number candidates, possible margin-boundary text,
and annotation/comment detection.
Optional `--json-out` and `--md-out` outputs write structured reports for
office/student review workflows.
It also includes conservative page-number sequence/style validation signals.

## LaTeX source-only audit

```bash
njit-audit tex path/to/main.tex
njit-audit tex path/to/main.tex --linters
```

This phase does not compile TeX and does not inspect generated PDFs.
It only detects problems visible in source files by recursively loading `\input{}` and `\include{}` trees and running lightweight local checks.
Optional local linters (`chktex`, `lacheck`) can be enabled with `--linters` if installed.
If they are missing, the audit continues and reports that they were skipped.
PDF visual/layout validation will be added in later phases.

## Demo examples

Try the synthetic fixtures:

- `examples/latex/good_minimal_thesis/main.tex`
- `examples/latex/bad_minimal_thesis/main.tex`

Run:

```bash
njit-audit tex examples/latex/good_minimal_thesis/main.tex
njit-audit tex examples/latex/bad_minimal_thesis/main.tex
```

More docs:
- `docs/status/phase1_milestone_summary.md`
- `docs/status/phase1_tex_finalization_status.md`
- `docs/status/phase2_pdf_milestone_summary.md`
- `docs/status/current_capabilities_for_graduate_studies.md`
- `docs/demo/phase1_tex_demo.md`
- `docs/demo/graduate_studies_pdf_audit_workflow.md`
- `docs/rules/rule_inventory.md`

## Roadmap

- front matter rules
- margins
- page numbering
- TOC / List of Tables / List of Figures checks
- figures, tables, captions
- references/bibliography checks
- optional DOCX support
- optional VLM/API fallback later

## Privacy model

This version is designed for local processing only. Keep thesis/dissertation files on your own machine.
