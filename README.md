# njit-thesis-auditor

For the local desktop edition and build instructions, see [Offline desktop auditor](docs/implementation/offline_desktop.md).

`njit-thesis-auditor` is a local-first tool for auditing NJIT thesis/dissertation formatting
against NJIT Graduate Studies formatting guidelines. It tracks 86 project-added rule IDs
(`P001`-`P086`), including heuristic checks covering TeX source hygiene and
compiled-PDF layout — margins, fonts, spacing, headings, TOC/List of
Tables/List of Figures structure, page numbering, front matter, and references.

This project is:
- local-first and free — no paid APIs, no external service calls for document analysis
- not an official NJIT tool
- a heuristic aid for manual review, not a replacement for it (see **Limitations** below)

## Supported inputs

- **Compiled PDF** (the primary, actively developed surface) — via the web UI or `njit-audit pdf`.
- **TeX source trees** (uncompiled `\input`/`\include` trees) — via `njit-audit tex`.
- **PDF annotation extraction** (highlights, text notes) — via `njit-audit pdf-comments`.
- **DOCX tracked-changes/comments extraction** — via `njit-audit docx-comments`.

## Quick install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Web UI

```bash
./scripts/run_web_gui.sh              # starts on 0.0.0.0:8000
# or
python -m uvicorn njit_auditor.web_app:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000`. The public web UI is **PDF-only** and offers three entry points:

- **Upload a PDF file.**
- **Audit a public PDF URL** — server-side fetch is SSRF-guarded (only `http`/`https`, blocks
  localhost/private IP ranges and hostnames resolving to internal addresses).
- **Audit a built-in sample PDF** — a committed synthetic formatting example. Private evaluation
  files remain available to authorized command-line checks but are not exposed by the public sample route.

Results include summary cards, findings by topic, findings in page order, client-side filters
(rule/category/page/confidence), privacy-safe polished comments per finding, and a **Complete PDF
Report** download. That PDF contains the entire thesis with reliable formatting locations
highlighted, followed by page-ordered explanations for every student-visible finding. Findings
without an exact highlight still appear in the appended report. Plain text, Markdown, and JSON
downloads remain available. Treat downloaded complete reports as private thesis content. See
[the complete report guide](docs/features/combined_student_pdf_report.md). Web exports use
basename-only paths and strip several private-detail fields (see
**Privacy statement** below); CLI exports are not sanitized.

**After changing routes, Jinja globals/filters, or startup config, restart the server** —
template auto-reload does not cover Python-level route/registration changes.

For deploying and supervising a persistent instance, see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).
For the manual browser QA checklist, see
[docs/web_ui_manual_qa_checklist.md](docs/web_ui_manual_qa_checklist.md). For a synthetic-fixture
walkthrough, see [docs/web_ui_demo_guide.md](docs/web_ui_demo_guide.md).

## CLI usage

```bash
# PDF layout audit — the full implemented rule set
njit-audit pdf path/to/thesis.pdf
njit-audit pdf path/to/thesis.pdf --json-out report.json --md-out report.md
njit-audit pdf path/to/thesis.pdf --enable-experimental P082   # opt in to experimental rules

# TeX source audit (no compilation required)
njit-audit tex path/to/main.tex
njit-audit tex path/to/main.tex --linters   # optional chktex/lacheck if installed

# PDF annotation extraction
njit-audit pdf-comments extract input.pdf --json-out comments.json --md-out comments.md
njit-audit pdf-comments clean input.pdf --out clean.pdf
```

`--json-out` includes a `grouped_summary` that aggregates high-volume repeated findings by rule
and issue type, plus optional reporting-only triage rollups for the highest-volume rules (P011,
P012, P013/P081, P019/P073, P026/P081, P036/P076, P038/P077, P044/P079) — see
[docs/RULE_ARCHITECTURE.md](docs/RULE_ARCHITECTURE.md) for what each rollup covers and how it
relates to its parent detector rule.

The full current rule table (what each `P###` checks, its gates, and its privacy model) lives in
[docs/RULE_ARCHITECTURE.md](docs/RULE_ARCHITECTURE.md) rather than here, so this file doesn't grow
by one row every time a rule is added. Quick pointers:

- **Detector rules with standalone findings:** P011-P068, P074-P075, P078, P084-P086
  (default-enabled), plus P082 (experimental, opt-in only).
- **Reporting-only rules** (recall/precision refinements or triage rollups, no standalone
  finding): P069-P073, P076, P077, P079, P081.
- **Infrastructure/evaluation rules** (no standalone PDF finding): P080 and P083.
- All findings are heuristic warnings and require manual review — this tool does not "pass" or
  "fail" a document.

A legacy `njit-audit audit` command remains for backward compatibility (original page-number,
abstract, and title-month checks only, no export flags); use `njit-audit pdf` for the current
implemented audit.

## Demo examples

```bash
njit-audit tex examples/latex/good_minimal_thesis/main.tex
njit-audit tex examples/latex/bad_minimal_thesis/main.tex
```

## Report schema

The `--json-out` JSON report structure:

```json
{
  "metadata": {
    "total_findings": 42,
    "counts_by_severity": { "PASS": 0, "WARNING": 42, "FAIL": 0 },
    "counts_by_rule_id": { "P013": 15, "P026": 10, "...": "..." },
    "counts_by_category": { "page_numbering": 20, "font_format": 10, "...": "..." }
  },
  "grouped_summary": {
    "high_volume_rules": [
      {
        "rule_id": "P026",
        "count": 10,
        "category": "font_format",
        "issue_type_counts": { "possible_body_font_family_issue": 10 },
        "affected_page_count": 10,
        "affected_pages_compact": "3-12"
      }
    ],
    "by_rule_issue_type": { "...": "..." },
    "p011_margin_triage": { "...": "optional; present when P011 warnings exist" }
  },
  "findings": [ "..." ]
}
```

Rules with 5+ findings appear in `grouped_summary.high_volume_rules`. Optional `triage` keys
summarize patterns for manual review; they never replace raw findings, which are always preserved
in full.

## Privacy statement

Designed for local processing only — keep thesis/dissertation files on your own machine.

- **No external API calls during audit by default.** The only network operation is the optional
  `POST /audits/url` fetch, which is SSRF-guarded.
- **Web export privacy reduction:** web-generated JSON/Markdown downloads use basename-only paths
  and, for TeX/ZIP source audits, strip private-detail keys (`label`, `ref`, `caption`, `title`,
  `author`, `body`, `text`, and related source-snippet fields). CLI `--json-out`/`--md-out` output
  is **not** sanitized — treat CLI exports as containing whatever the input document contained.
  Web exports are privacy-*reduced*, not guaranteed fully anonymized.
- **Job TTL cleanup:** completed/failed web jobs and their runtime files are removed automatically
  after `NJIT_AUDITOR_WEB_JOB_TTL_SECONDS` (default 24h) by a background sweeper that runs at
  startup and every `NJIT_AUDITOR_WEB_CLEANUP_INTERVAL_SECONDS` (default 300), even when the
  server receives no requests. Pending/running jobs are never deleted.
- **No authentication or rate limiting by default.** A public deployment needs a reverse proxy,
  TLS, authentication, and rate limiting — see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).
- This repository's own evaluation data includes real, private student dissertations under
  `data/raw/ester/` (all 16 tracked paths are Git LFS pointers at the verified
  2026-10-12 commit; see [docs/EVALUATION_DATA.md](docs/EVALUATION_DATA.md)) — keep the repo private.

## Limitations

- **Heuristic, not authoritative.** Every finding requires manual review; this tool does not
  replace a human formatting reviewer and does not "certify" compliance.
- **Text-layer PDFs only for most checks.** Image-only figures/tables and scanned (non-native-text)
  pages are skipped by most detectors rather than guessed at — see
  [docs/ROADMAP.md](docs/ROADMAP.md) for the longer-term (not yet started) OCR/VLM direction.
- **NJIT-specific.** Rules encode NJIT Graduate Studies formatting guidance; they are not a
  general-purpose thesis formatting checker for other institutions.
- **English-language documents.** Detectors assume English prose conventions (capitalization,
  punctuation) and have not been validated on other languages.
- **No citation-style enforcement.** P064 checks references-section *structure* (presence,
  indentation, spacing consistency), not citation style (APA/IEEE/etc.), which is advisor-dependent.
- **Not every `P###` is a standalone student-visible rule** — some are reporting-only
  infrastructure or experimental/opt-in; see [docs/RULE_ARCHITECTURE.md](docs/RULE_ARCHITECTURE.md).

## Documentation map

| Doc | Purpose |
|---|---|
| [docs/README.md](docs/README.md) | Navigate current guides and dated research records. |
| [docs/status/CURRENT_STATUS.md](docs/status/CURRENT_STATUS.md) | Current SHA, test count, open PRs, next actions — the canonical "what's true right now." |
| [docs/REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md) | Setup, CI, private validation, and wheel-installation limits. |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Completed capabilities, near-term/policy-dependent/longer-term work. |
| [docs/RULE_ARCHITECTURE.md](docs/RULE_ARCHITECTURE.md) | Full rule table, taxonomy, and canonical metadata sources. |
| [docs/EVALUATION_DATA.md](docs/EVALUATION_DATA.md) | Evaluation samples, privacy rules, finding-review labeling taxonomy. |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Live-deployment procedure, smoke test, rollback. |
| [docs/TERMINOLOGY.md](docs/TERMINOLOGY.md) | Naming conventions ("Esther" vs. `ester_*` identifiers, etc.). |
| [docs/status/README.md](docs/status/README.md) | Index of historical/dated status and audit reports. |
| [docs/web_gui_mvp.md](docs/web_gui_mvp.md) | Web upload UI operations guide: current public FastAPI web UI behavior. |
| [docs/planning/synthetic_web_demo_fixtures.md](docs/planning/synthetic_web_demo_fixtures.md) | Synthetic PDF fixtures for web UI demos/screenshots. |

## Development

```bash
ruff check .
mypy src
python -m pytest
```

See [reproducibility](docs/REPRODUCIBILITY.md) for the tested Python versions,
Git LFS setup, private-data-dependent skips, and exact-SHA validation.
