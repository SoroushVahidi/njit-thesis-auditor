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

## LaTeX source-only audit

```bash
njit-audit tex path/to/main.tex
```

This phase does not compile TeX and does not inspect generated PDFs.
It only detects problems visible in source files by recursively loading `\input{}` and `\include{}` trees and running lightweight local checks.
PDF visual/layout validation will be added in later phases.

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
