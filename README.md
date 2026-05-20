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
