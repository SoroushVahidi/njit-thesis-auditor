# njit-thesis-auditor

`njit-thesis-auditor` is a local-first research prototype for auditing NJIT thesis/dissertation formatting.

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

### PDF layout audit (P011–P048)

```bash
njit-audit pdf path/to/thesis.pdf
njit-audit pdf path/to/thesis.pdf --json-out report.json --md-out report.md
```

Runs P011–P048 layout and formatting checks on digital PDFs. Optional `--json-out`
and `--md-out` flags write structured reports. The JSON report includes a
`grouped_summary` field that aggregates high-volume repeated findings by rule and
issue type for triage. High-volume rules also get optional **reporting-only** triage
rollups (detection unchanged):

| Rollup key | Rule | Purpose |
|---|---|---|
| `p011_margin_triage` | P011 | Margin side counts, overflow by side, page ranges |
| `p012_annotation_triage` | P012 | Annotation type counts and page ranges (no comment text) |
| `p013_triage` | P013 | Page-number candidate patterns and multi-candidate pages |
| `p026_font_triage` | P026 | Font/size issue counts and label page ranges |

The Markdown report includes a "Repeated Findings Summary" table and P011/P012/P013/P026
triage sections (when present) before the full raw findings.

Current PDF checks (P011–P048):

| Rule | Area | Check |
|------|------|-------|
| P011 | Margins | Text crossing 1.5"/1" margin boundaries; compression artifact guard reduces false positives on compressed PDFs |
| P012 | Annotations | Embedded PDF annotation objects |
| P013 | Page numbers | Page-number candidate detection (top/bottom zones) |
| P014 | Headings | Named front-matter heading style (bold/all-caps/centered/near-top) |
| P015 | Indentation | Paragraph indentation (first-para flush-left; subsequent indented) |
| P016 | Spacing | Spacing/blank-line gaps on front-matter pages |
| P017 | Captions | Caption/title punctuation and case signals |
| P018 | TOC/List | TOC/list entry alignment (leaders, page-number column, hierarchy) |
| P019 | Page numbers | Page-number sequence/style consistency |
| P020 | Capitalization | Title-case check for Level 2 headings and table titles |
| P021 | Abstract | Abstract word count (PhD ≤350, MS ≤150) |
| P022 | Page numbers | No visible page number on Abstract/Title/Approval/Copyright pages |
| P023 | Spacing | Body text double-spacing (line spacing ≥ 1.55× font size) |
| P024 | TOC/List | TOC/LoT/LoF entry capitalization and terminal punctuation |
| P025 | Front matter | Front-matter structure: abstract body, title-page elements, approval-page content |
| P026 | Font | Body text font compliance (Times New Roman 12pt or accepted equivalent) |
| P027 | Headings | Numbered heading level-specific style (L1 ALL CAPS, L2 Title Case, L3-5 Sentence case) |
| P028 | Page numbers | Front-matter Roman / body Arabic page-numbering regime |
| P029 | Page numbers | Front-matter lowercase Roman numeral ordering (sequence checks) |
| P030 | TOC/List | Multi-page TOC/LoT/LoF continued-heading checks on continuation pages |
| P031 | TOC/List | List of Tables/Figures column header labels (Table/Figure and Page) |
| P032 | TOC/List | Wrapped TOC/LoT/LoF entry internal spacing (continuation gap vs line height) |
| P033 | Front matter | Cross-page title consistency (Title Page, Abstract, Approval) |
| P034 | Front matter | Copyright Page top-margin header, year/author consistency with Title Page |
| P035 | Figures/Tables | Body-page figure/table centering and caption placement; **v1 text-layer bodies only** (image-only floats skipped); privacy-safe geometry metadata only |
| P036 | TOC/List | Inter-entry double spacing between distinct entries on TOC, LoT, and LoF pages; complements P032; privacy-safe geometry metadata only (no entry text) |
| P037 | Page numbers | Section-anchored front-matter Roman numerals: BIOGRAPHICAL SKETCH must be iv; DEDICATION (optional) v; ACKNOWLEDGEMENTS vi; TABLE OF CONTENTS vii; LIST OF TABLES viii; emits nothing if BIOGRAPHICAL SKETCH heading absent |
| P038 | Front matter | Required front-matter heading presence (APPROVAL PAGE, BIOGRAPHICAL SKETCH, ACKNOWLEDGEMENTS, TABLE OF CONTENTS) and known phrase-variant detection (covers DEDICATION, LIST OF TABLES, LIST OF FIGURES too; e.g. ACKNOWLEDGMENTS variant); gated: no findings if no headings detected; List of Tables/Figures never flagged as missing (optional); complements P014/P025/P030/P031; privacy-safe metadata only |
| P039 | TOC/List | TOC level indentation hierarchy: L2 entries should be indented right of L1, L3 entries right of L2; TOC-only (LoT/LoF excluded); gate: requires ≥2 child-level entries before flagging; privacy-safe geometry metadata only (no entry text); covers Q056 |
| P040 | TOC/List | List of Figures entry terminal punctuation: checks complete LoF entries (with page-number token) end with `.`, `?`, or `!`; LoF-only; skips wrap-continuation lines; privacy-safe counts/metadata only (no entry text); covers Q075 |
| P041 | Front matter | Dedication page top-margin header: checks no running header text is in the top 15% of the Dedication page; gate: skips if DEDICATION heading not detected; privacy-safe geometry metadata only (no dedication text); covers Q032 |
| P042 | TOC/List | TOC appendix entry format: single appendix should have APPENDIX + title; multiple appendices should each use APPENDIX + letter (A, B, C…); TOC-only; privacy-safe counts/metadata only (no entry text); covers Q058/Q059 |
| P043 | Indentation | Acknowledgements page paragraph indentation: first paragraph flush-left (Q044), subsequent paragraphs indented (Q045); Acknowledgements-page-only complement to P015; gate: skip if ACKNOWLEDGEMENTS heading absent or fewer than 2 paragraph blocks; privacy-safe geometry metadata only (no acknowledgements text) |
| P044 | Indentation | Abstract page paragraph indentation: first paragraph flush-left (Q002), subsequent paragraphs indented (Q003); Abstract-page-only complement to P015; gate: skip if ABSTRACT heading absent; skip Q003 if fewer than 2 paragraph blocks; privacy-safe geometry metadata only (no abstract text) |
| P045 | Indentation | Biographical Sketch publication paragraph layout: hanging indent detection (Q029), inter-entry spacing (Q028); Biographical-Sketch-page-only; gate: skip if BIOGRAPHICAL SKETCH heading absent or fewer than 2 multi-line blocks; privacy-safe geometry metadata only (no publication text, author names, or citation content) |
| P046 | TOC/List | LoT/LoF entry number left-column alignment: checks that table numbers (Q068) and figure numbers (Q078) are vertically aligned at a consistent left margin; LoT/LoF pages only; gate: skip if fewer than 3 entries detected; privacy-safe geometry metadata only (no table/figure title text) |
| P047 | Indentation | Biographical Sketch bullet/list section single-spacing: checks non-hanging-indent multi-line blocks for excessive internal line gaps (Q026); Biographical-Sketch-page-only; gate: skip sparse/ambiguous blocks; privacy-safe geometry metadata only (no bullet text, names, or citation content) |
| P048 | TOC/List | LoT/LoF page-number right-column alignment: checks that List of Tables page numbers (Q069) and List of Figures page numbers (Q079) align at a consistent right column; LoT/LoF pages only; gate: skip fewer than 3 complete entries; privacy-safe geometry metadata only (no entry text, table/figure titles, or captions) |

All findings are heuristic warnings and require manual review.

### LaTeX source audit (P001–P010)

```bash
njit-audit tex path/to/main.tex
njit-audit tex path/to/main.tex --linters
```

Checks TeX source files without compiling. Recursively loads `\input{}`/`\include{}`
trees and runs lightweight checks including risky commands, duplicate labels,
missing captions, structure commands, and abstract language checks.
Optional local linters (`chktex`, `lacheck`) can be enabled with `--linters` if installed.

Current TeX checks (P001–P010, Q004, Q005, Q006):

| Rule | Check |
|------|-------|
| P001 | Risky manual formatting commands |
| P002 | Duplicate `\label` identifiers |
| P003 | Whitespace in label names |
| P004 | Unresolved `\ref`/`\eqref` targets |
| P005 | Missing `\caption` in figure/table environments |
| P006 | Missing `\label` in figure/table environments |
| P007 | Caption terminal punctuation |
| P008 | Required document structure commands |
| P009 | chktex warnings (optional) |
| P010 | lacheck warnings (optional) |
| Q004 | Abstract forbidden words ("paper"/"article") |
| Q005 | Abstract first-person pronouns |
| Q006 | Graduation month validation (Aug/Dec/May) |

### PDF comment extraction

```bash
njit-audit pdf-comments extract input.pdf --json-out comments.json --md-out comments.md
njit-audit pdf-comments clean input.pdf --out clean.pdf
```

Extracts PDF annotation objects (highlights, text notes) to JSON/Markdown, or
creates a clean copy with annotation objects removed.

## Demo examples

Try the synthetic TeX fixtures:

```bash
njit-audit tex examples/latex/good_minimal_thesis/main.tex
njit-audit tex examples/latex/bad_minimal_thesis/main.tex
```

More docs:
- `docs/status/current_project_state_and_next_steps.md` — current implementation state and next steps
- `docs/status/phase2_pdf_milestone_summary.md` — PDF audit milestone summary
- `docs/status/rule_coverage_audit.md` — Q-rule and P-rule coverage audit
- `docs/demo/graduate_studies_pdf_audit_workflow.md` — Graduate Studies workflow
- `docs/evaluation/current_auditor_after_p034_evaluation.md` — canonical pre-P035 full PDF audit snapshot (P011–P034, five evaluation PDFs; **1,446** findings)
- `docs/evaluation/p035_current_dataset_evaluation.md` — P035 local four-PDF subset (not a new canonical aggregate)
- `docs/evaluation/current_auditor_after_p034_full_triage_refresh.md` — canonical gitignored full reports with all triage rollups (`current_auditor_after_p034_p011_triage/`)
- `docs/evaluation/p011_reporting_actionability_refinement.md` — P011 `p011_margin_triage` rollup
- `docs/evaluation/p012_reporting_actionability_refinement.md` — P012 `p012_annotation_triage` rollup
- `docs/evaluation/p013_reporting_actionability_refinement.md` — P013 `p013_triage` rollup
- `docs/evaluation/p026_reporting_actionability_refinement.md` — P026 `p026_font_triage` rollup
- `docs/evaluation/p036_toc_list_entry_spacing_synthetic_validation.md` — P036 synthetic validation
- `docs/evaluation/p036_current_dataset_evaluation.md` — P036 current-dataset status (not run; evaluation PDFs unavailable)
- `docs/evaluation/` — per-rule and historical evaluation docs (P011–P029 snapshot, P030–P036 synthetic/current-dataset)

## Report schema

The `--json-out` JSON report structure:

```json
{
  "metadata": {
    "total_findings": 42,
    "counts_by_severity": { "PASS": 0, "WARNING": 42, "FAIL": 0 },
    "counts_by_rule_id": { "P013": 15, "P026": 10, ... },
    "counts_by_category": { "page_numbering": 20, "font_format": 10, ... }
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
    "by_rule_issue_type": { ... },
    "p011_margin_triage": { "...": "optional; present when P011 warnings exist" },
    "p012_annotation_triage": { "...": "optional; present when P012 warnings exist" },
    "p013_triage": { "...": "optional; present when P013 warnings exist" },
    "p026_font_triage": { "...": "optional; present when P026 warnings exist" }
  },
  "findings": [ ... ]
}
```

Rules with 5+ findings appear in `grouped_summary.high_volume_rules`. Optional
`triage` keys summarize patterns for manual review; they do not replace raw findings.
Raw findings are always preserved in full.

## Privacy model

This version is designed for local processing only. Keep thesis/dissertation files on your own machine.

## Development

```bash
ruff check .
mypy src
python -m pytest
```
