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

### Web upload UI

A browser-based upload form is available via the bundled FastAPI application:

```bash
./scripts/run_web_gui.sh              # starts on 0.0.0.0:8000
# or
python -m uvicorn njit_auditor.web_app:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000` in a browser. The web UI accepts **PDF**, **TeX (.tex)**, and
**ZIP** uploads through the same form. PDF uploads run the **current implemented PDF layout
audit** (P011–P068 and P074 standalone checks plus P069–P073 infrastructure/reporting
refinements);
TeX and ZIP uploads run **P001–P010** source audits (ZIP is safely extracted and main
`.tex` is detected — no LaTeX compilation). All supported uploads use
`run_audit_for_uploaded_file()` and provide JSON/Markdown downloads. Three additional audit
methods are available:

- **Upload a PDF file** — select a local file and submit.
- **Audit a public PDF URL** — paste a direct public PDF link and submit.
  Server downloads the PDF safely: only `http://` and `https://` schemes are accepted;
  `localhost`, private IP ranges (10.x.x.x, 172.16–31.x.x, 192.168.x.x, etc.), and
  hostnames resolving to internal addresses are blocked. ZIP files are not supported for URL audit.
- **Audit a built-in sample PDF** — select a local repository evaluation sample from the dropdown
  and submit. These are private dissertation samples available only on servers where the repository
  is checked out. Do not expose built-in samples on a public site unless authorized.

Download JSON or Markdown reports from the results page. The results page shows a status
banner, summary cards, severity/category overview, high-volume triage panels (P011/P013/P026),
client-side finding filters (rule, severity, category, page), and privacy-safe polished
comments per finding. Web-generated JSON/Markdown use basename-only paths (CLI exports are
unchanged). Completed jobs and runtime files are removed automatically after 24 hours by default
(`NJIT_AUDITOR_WEB_JOB_TTL_SECONDS`). The upload page explains local privacy-safe processing
and which input formats the web UI supports. Use
`njit-audit tex --json-out report.json --md-out report.md` for CLI source audit exports.
For persistent always-on hosting, start in a detached tmux session:

```bash
tmux new -d -s thesis-auditor-web \
  'cd /path/to/njit-thesis-auditor && ./scripts/run_web_gui.sh'
```

See [docs/web_gui_mvp.md](docs/web_gui_mvp.md) for full setup, environment variables, firewall notes,
reverse proxy configuration (nginx/Caddy), and operations commands (check logs, restart, stop).
See [docs/web_ui_manual_qa_checklist.md](docs/web_ui_manual_qa_checklist.md) for the manual browser
QA checklist (upload flows, download verification, privacy checks, known limitations).
See [docs/web_ui_demo_guide.md](docs/web_ui_demo_guide.md) for the end-to-end demo guide using
synthetic fixtures (install, run, step-by-step upload flow, privacy statement, caveats).

**Demo fixtures:** The directory `tests/fixtures/web_demo/` contains committed synthetic
test files (PDF, TeX, ZIP) for manual QA and automated smoke tests. All content is
synthetic placeholder text — no real dissertation content. See
[docs/planning/synthetic_web_demo_fixtures.md](docs/planning/synthetic_web_demo_fixtures.md)
for fixture details and
[docs/web_ui_manual_qa_checklist.md](docs/web_ui_manual_qa_checklist.md) for the QA
scenario mapping.

### PDF layout audit (current implemented PDF rule set)

```bash
njit-audit pdf path/to/thesis.pdf
njit-audit pdf path/to/thesis.pdf --json-out report.json --md-out report.md
```

Runs the current implemented PDF layout and formatting checks on digital PDFs (P011–P068
and P074 standalone rules plus P069–P073 infrastructure/reporting refinements). Optional `--json-out`
and `--md-out` flags write structured reports. The JSON report includes a
`grouped_summary` field that aggregates high-volume repeated findings by rule and
issue type for triage. High-volume rules also get optional **reporting-only** triage
rollups (detection unchanged):

| Rollup key | Rule | Purpose |
|---|---|---|
| `p011_margin_triage` | P011 | Margin side counts, overflow by side, page ranges |
| `p012_annotation_triage` | P012 | Annotation type counts and page ranges (no comment text) |
| `p013_triage` | P013 | Page-number candidate patterns and multi-candidate pages |
| `p019_page_numbering_triage` | P019 / P073 | Page-numbering triage tiers, categories, and reviewer guidance |
| `p026_font_triage` | P026 | Font/size issue counts and label page ranges |

The Markdown report includes a "Repeated Findings Summary" table and P011/P012/P013/P019/P026
triage sections (when present) before the full raw findings.

Current PDF checks (P011–P068 and P074 standalone; P069–P073 are infrastructure/reporting refinements with no standalone issue types for P069–P073):

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
| P049 | TOC/List | LoT/LoF Page-column header right-alignment and bold-style refinement: checks that the 'Page' column header is right-aligned with the page-number column anchor (Q064/Q073) and formatted in bold when font metadata is reliable; LoT/LoF pages only; gate: skip fewer than 3 complete entries; privacy-safe geometry/style metadata only (no entry text, captions, or titles) |
| P050 | TOC/List | LoT/LoF left-column header bold-style check: checks that the 'Table' column header (Q063) in LoT and 'Figure' column header (Q072) in LoF are formatted in bold when font metadata is reliable; LoT/LoF pages only; gate: skip if left-column header absent or fewer than 3 complete entries; bold check skipped when font metadata unavailable or ambiguous; privacy-safe style metadata only (no entry text, captions, header text, or titles) |
| P051 | Copyright | Copyright page year-format refinement: emits a low-confidence advisory when copyright page is detected but no copyright year token is found anywhere on the page (Q010); extends P034 copyright detection; improved extraction handles adjacent-line year patterns; skips pages where a year token exists but cannot be confidently attributed; privacy-safe metadata only (no copyright text, author names, or titles) |
| P052 | Copyright | Copyright page author-format refinement: emits a low-confidence advisory when copyright page and year are detected but no copyright owner name can be extracted (Q011); extends P034/P051 detection; improved extraction handles adjacent-line author patterns; only fires when year is confirmed; privacy-safe hash-only metadata (no author names, copyright text, or titles) |
| P053 | TOC/List | List of Tables entry terminal-period check: emits a warning when a complete LoT entry (with page-number token) ends with a terminal period (Q065); LoT pages only; gate: skip entries shorter than 10 chars and pages with fewer than 2 entries; symmetric counterpart to P040 (LoF entries must have terminal punctuation; LoT entries must not have terminal period); privacy-safe metadata only (no entry text, table titles, or captions) |
| P054 | TOC/List | TOC entry terminal-period absence check: emits a warning when a complete TOC entry ends with a terminal period (Q049/Q050/Q051); TOC pages only; gate: skip entries shorter than 10 chars and pages with fewer than 2 entries; symmetric counterpart to P053 (LoT entries must not have terminal period; TOC entries must not have terminal period); privacy-safe metadata only (no entry text, chapter titles, or headings) |
| P055 | TOC/List | LoT/LoF cross-type entry check: emits a warning when a complete List of Tables entry starts with "Figure" (`lot_entry_is_figure`) or a complete List of Figures entry starts with "Table" (`lof_entry_is_table`) (Q063/Q072 extension); gate: entry must have page-number token, text ≥ 10 chars, and clear type prefix (Figure/Table followed by digit); pages with fewer than 2 entries are skipped; privacy-safe metadata only (no entry text, figure/table titles, or captions) |
| P056 | TOC/List | LoT/LoF entry numbering format consistency check: emits a warning when a List of Tables or List of Figures section contains a mix of chapter-based (X.Y, e.g., Table 1.2) and sequential (N, e.g., Table 1) entry numbering formats (`lot_mixed_numbering_format`, `lof_mixed_numbering_format`) (Q063/Q072 extension); gate: entry must have page-number token, text ≥ 10 chars, and ≥ 2 entries of each format type on the page; appendix-prefixed entries (A.1) skipped; triage tier: low; privacy-safe metadata only (no entry text or titles) |
| P057 | TOC/List | LoT/LoF page-number ordering check: emits a warning when a List of Tables or List of Figures page contains complete entries whose listed page numbers are not in non-decreasing order (`lot_page_numbers_not_nondecreasing`, `lof_page_numbers_not_nondecreasing`) (Q069/Q079 refinement); gate: entry must have page-number token, text ≥ 10 chars, integer page number, and ≥ 3 comparable entries with ≥ 2 inversions before flagging; non-integer (roman numeral) page tokens skipped; TOC pages excluded; triage tier: medium; privacy-safe metadata only (no entry text, titles, or captions) |
| P058 | TOC/List | TOC page-number ordering check: emits a warning when a Table of Contents page contains body entries whose page numbers are not in non-decreasing order (`toc_page_numbers_not_nondecreasing`) (Q057 refinement); gate: entry must have page-number token, text ≥ 10 chars, integer page number, and ≥ 3 comparable entries with ≥ 2 inversions before flagging; roman-numeral (front-matter) entries skipped; LoT/LoF pages excluded; triage tier: medium; privacy-safe metadata only |
| P059 | TOC/List | LoT/LoF entry-number ordering check: emits a warning when a List of Tables or List of Figures page contains complete entries whose entry numbers (the numeric token following the "Table"/"Figure" label) are not in non-decreasing order (`lot_entry_numbers_not_nondecreasing`, `lof_entry_numbers_not_nondecreasing`) (Q063/Q072); gate: entry must have page-number token, text ≥ 10 chars, parseable entry number, and ≥ 3 comparable entries with ≥ 2 inversions before flagging; mixed sequential + chapter-based format pages skipped; appendix/letter-prefixed entries skipped; TOC pages excluded; triage tier: medium; privacy-safe metadata only |
| P060 | TOC/List | TOC section-number ordering check: emits a warning when a Table of Contents page contains parseable numeric section entries (entries starting with a bare number, e.g. "1 Introduction", "1.1 Background") whose section numbers are not in non-decreasing order (`toc_entry_numbers_not_nondecreasing`) (Q056/Q057 implied); gate: entry must have page-number token, text ≥ 10 chars, parseable section number, and ≥ 3 comparable entries with ≥ 2 inversions before flagging; word-prefix entries (CHAPTER, APPENDIX, ABSTRACT, etc.) skipped; LoT/LoF pages excluded; triage tier: medium; privacy-safe metadata only |
| P061 | TOC/List | LoT/LoF cross-page entry-number ordering check: emits a warning when consecutive same-type List of Tables or List of Figures pages span multiple pages and the combined entry-number sequence is not non-decreasing (`lot_cross_page_entry_numbers_not_nondecreasing`, `lof_cross_page_entry_numbers_not_nondecreasing`) (Q063/Q072 extension); gate: requires ≥2 consecutive pages, ≥3 combined comparable entries, and ≥2 inversions; mixed sequential + chapter-based runs skipped; non-consecutive pages not combined; cross-page companion to P059; triage tier: medium; privacy-safe metadata only |
| P062 | TOC/List | TOC cross-page section-number ordering check: emits a warning when consecutive TABLE OF CONTENTS pages have a combined section-number sequence that is not non-decreasing (`toc_cross_page_entry_numbers_not_nondecreasing`) (Q056/Q057 extension); gate: requires ≥2 consecutive TOC pages, ≥3 combined comparable entries, and ≥2 inversions; word-prefix entries (CHAPTER, APPENDIX, ABSTRACT) skipped; non-consecutive pages not combined; cross-page companion to P060 and symmetric counterpart to P061; triage tier: medium; privacy-safe metadata only |
| P063 | Appendices | Body-page appendix heading label check: emits a warning when body-page APPENDIX headings do not follow NJIT label conventions — a single appendix must use APPENDIX (no letter suffix); multiple appendices must each use APPENDIX A, APPENDIX B, etc. with consecutive letters starting from A (`single_appendix_uses_letter_label`, `multiple_appendix_missing_letter`, `appendix_letter_sequence_gap`, `appendix_letter_sequence_repeat`) (Q058/Q059 body-page extension); companion to P042 (TOC-side); gate: requires body region detection (CHAPTER/APPENDIX body heading) before scanning; skips documents with no body region detected; triage tier: medium; privacy-safe metadata only |
| P064 | References | References/citations structural check: emits a warning when no REFERENCES, BIBLIOGRAPHY, WORKS CITED, or LITERATURE CITED heading is found in a document with ≥5 body pages (`references_section_heading_not_detected`); emits a warning when multi-line reference entries show inconsistent hanging-indent patterns (`references_entry_indentation_inconsistent`); emits a warning when inter-entry vertical gaps are highly irregular (`references_entry_spacing_inconsistent`); does NOT enforce citation style (APA/IEEE/etc.) — style is advisor-dependent; gate: body region detection required; ≥5 entry candidates for B/C; ≥3 multi-line entries for B; x-variance < 50 pt; no multi-column layout; consistent blank-line separation between entries required for reliable grouping; triage tier: medium/low; privacy-safe geometry metadata only (no entry text, author names, DOIs, URLs) |
| P065 | Front matter | Dedication page centering and italic style check: emits `dedication_text_not_centered` and `dedication_text_not_italic` on a uniquely detected DEDICATION page when the main dedication text block is off-center or insufficiently italic; gates: ≥2 text lines for centering, ≥3 usable spans for italic, font metadata required for italic; privacy-safe geometry/style metadata only |
| P066 | Front matter | Biographical Sketch degree ordering check: detects year-bearing education entries above any Publications boundary and warns with `biosketch_degree_order_suspicious` when degree years are not most-recent-first; gates: unique BIOGRAPHICAL SKETCH heading, ≥3 comparable lines, >2-year inversion threshold; privacy-safe counts/year metadata only |
| P067 | Front matter | Biographical Sketch publication/presentation reverse-chronology check: detects a Publications/Presentations subsection on a uniquely detected Bio Sketch page, groups citation-like entries, extracts one representative year per entry, and warns with `biosketch_publication_order_suspicious` when comparable entries are not in descending order; skips ambiguous multi-year, DOI/URL-heavy, sparse, and nonstandard layouts; privacy-safe counts/year metadata only |
| P068 | Front matter | Approval Page committee/signature-block structural check: on a uniquely detected APPROVAL PAGE, counts curated advisor/committee role-label phrases and date/signature/underscore-blank indicators; warns with `approval_page_advisor_role_label_missing` or `approval_page_signature_blocks_sparse`; skips sparse/noisy/image-only pages; no committee names or signature text in findings |
| P074 | Front matter | Title Page graduation month validation: emits `title_page_graduation_month_invalid` when a detected title-page month/year line uses a month other than August, December, or May; silent when no month/year line is extractable; canonical five-PDF aggregate unchanged at 1,543 because the current dataset has 0 P074 findings |

**Infrastructure/reporting refinements (no standalone issue types):** P069 front-matter heading gate recall; P070 TOC/LoT/LoF entry parser recall; P071 references-section localization recall (P064 companion); P072 approval-page heading-gate recall; P073 P019 page-numbering triage rollup.

All findings are heuristic warnings and require manual review.

### Current canonical artifacts (P072 era)

| Artifact | Path |
|---|---|
| Full repository audit | `docs/status/full_repository_audit_after_p071.md` (P072 note added) |
| Canonical five-PDF aggregate (**1,543** findings) | `docs/evaluation/current_auditor_after_p070_evaluation.md` (unchanged post-P072) |
| Latest EF overlap | `docs/evaluation/ef_overlap_after_p072_evaluation.md` |
| P069 gate-recall eval | `docs/evaluation/p069_frontmatter_heading_gate_recall_current_dataset_evaluation.md` |
| P070 parser-recall eval | `docs/evaluation/p070_toc_lot_lof_entry_parser_recall_current_dataset_evaluation.md` |
| P071 localization eval | `docs/evaluation/p071_references_section_localization_recall_current_dataset_evaluation.md` |
| P072 detection-mode eval | `docs/evaluation/p072_approval_page_heading_gate_recall_current_dataset_evaluation.md` |
| Current validation | Repository progress: P001–P075 (P001–P074 inventory rules + P075 test-only hygiene); **1043 pytest** |

No separate `current_auditor_after_p071_evaluation.md` — P071 did not change the five-PDF aggregate total.

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
- `docs/status/full_repository_audit_after_p071.md` — comprehensive post-P071 repository audit (P001–P071, EF overlap, gaps, next priorities)
- `docs/status/phase2_pdf_milestone_summary.md` — PDF audit milestone summary
- `docs/status/rule_coverage_audit.md` — Q-rule and P-rule coverage audit
- `docs/demo/graduate_studies_pdf_audit_workflow.md` — Graduate Studies workflow
- `docs/evaluation/current_auditor_after_p068_evaluation.md` — full PDF audit snapshot at P068 era (P011–P068, five evaluation PDFs; **1,590** findings; P068 adds 3; 3/5 files skipped at APPROVAL PAGE detection gate; 2/5 reached structural checks)
- `docs/evaluation/current_auditor_after_p067_evaluation.md` — full PDF audit snapshot at P067 era (P011–P067, five evaluation PDFs; **1,587** findings; P067 adds 0; 3/5 files skipped at heading detection; 2/5 reached BIOGRAPHICAL SKETCH but no qualifying Publications boundary)
- `docs/evaluation/current_auditor_after_p066_evaluation.md` — full PDF audit snapshot at P066 era (P011–P066, five evaluation PDFs; **1,587** findings; P066 adds 0; 3/5 files skipped at heading detection; 2/5 bio sketches detected and passed)
- `docs/evaluation/current_auditor_after_p065_evaluation.md` — full PDF audit snapshot at P065 era (P011–P065, five evaluation PDFs; **1,587** findings; P065 adds 0)
- `docs/evaluation/current_auditor_after_p064_evaluation.md` — full PDF audit snapshot at P064 era (P011–P064, five evaluation PDFs; **1,587** findings; P064 adds 0; post-P064 aggregate confirmed)
- `docs/evaluation/current_auditor_after_p063_evaluation.md` — full PDF audit snapshot at P063 era (P011–P063, five evaluation PDFs; **1,587** findings; P063 adds 0; prior to P064)
- `docs/evaluation/ef_overlap_after_p063_evaluation.md` — EF comment-vs-tool overlap refresh after P063; Cibaku (78 EF / 325 tool) and Yin Haotian (65 EF / 346 tool); P064 recommendation: references/citations structural check
- `docs/evaluation/p064_current_dataset_evaluation.md` — P064 five-PDF evaluation (2026-06-08, commit `dd0f022`); all 5 PDFs accessible; 0 P064 findings; 3 of 5 skipped by conservative gates; 2 of 5 reached entry checks and passed
- `docs/evaluation/current_auditor_after_p062_evaluation.md` — prior full PDF audit snapshot (P011–P062, five evaluation PDFs; **1,587** findings; P062 adds 0)
- `docs/evaluation/current_auditor_after_p061_evaluation.md` — historical full PDF audit snapshot (P011–P061, five evaluation PDFs; **1,587** findings; historical)
- `docs/evaluation/current_auditor_after_p034_evaluation.md` — historical pre-P035 full PDF audit snapshot (P011–P034; **1,446** findings)
- `docs/evaluation/p035_current_dataset_evaluation.md` — P035 local four-PDF subset (not a new canonical aggregate)
- `docs/evaluation/current_auditor_after_p034_full_triage_refresh.md` — canonical gitignored full reports with P011/P012/P013/P026 triage rollups (`current_auditor_after_p034_p011_triage/`; older `current_auditor_after_p034*` folders are historical/superseded)
- `docs/evaluation/p011_reporting_actionability_refinement.md` — P011 `p011_margin_triage` rollup
- `docs/evaluation/p012_reporting_actionability_refinement.md` — P012 `p012_annotation_triage` rollup
- `docs/evaluation/p013_reporting_actionability_refinement.md` — P013 `p013_triage` rollup
- `docs/evaluation/p026_reporting_actionability_refinement.md` — P026 `p026_font_triage` rollup
- `docs/evaluation/p036_toc_list_entry_spacing_synthetic_validation.md` — P036 synthetic validation
- `docs/evaluation/p036_current_dataset_evaluation.md` — P036 current-dataset status (gap-fill: 55 findings on Yin H 4th)
- `docs/evaluation/p036_p063_current_dataset_gap_fill_evaluation.md` — **P036–P063 five-PDF evaluation gap-fill** (2026-06-09): 27 rules; 8 with findings (P036: 55, P038: 16, P044: 7, P051: 3, P037: 3, P046: 2, P040: 1, P053: 1); all consistent with canonical 1,543
- `docs/planning/gui_scope_and_design.md` — GUI/web UI scope and design (local-only; evolve FastAPI MVP)
- `docs/planning/p061_scope_and_design.md` — P061 LoT/LoF cross-page entry-number ordering design
- `docs/evaluation/p061_current_dataset_evaluation.md` — P061 formal current-dataset evaluation (PR #204; 0 findings on five-PDF local subset; sparse comparable entries)
- `docs/planning/p062_scope_and_design.md` — P062 TOC cross-page section-number ordering design
- `docs/planning/p063_scope_and_design.md` — P063 body-page appendix heading label check design
- `docs/evaluation/current_auditor_after_p063_evaluation.md` — P063 formal current-dataset evaluation (2026-06-07; 0 P063 findings on five-PDF set; no qualifying body-region appendix heading sequence detected)
- `docs/planning/p064_references_citations_structural_check_scope_and_design.md` — P064 references/citations structural check scope and design (implemented PR #228)
- `docs/evaluation/p064_references_citations_structural_synthetic_validation.md` — P064 synthetic test coverage, privacy model, and limitations
- `docs/evaluation/current_auditor_after_p064_evaluation.md` — P064 formal current-dataset evaluation and full aggregate snapshot (2026-06-08; 0 P064 findings; post-P064 aggregate 1,587; 3/5 files skipped by conservative gates)
- `docs/planning/p065_dedication_centering_italic_scope_and_design.md` — P065 scope and design: dedication page centering/italic check (Q033/Q034; implemented 2026-06-08)
- `docs/planning/p066_biosketch_structural_ordering_scope_and_design.md` — P066 scope and design: bio-sketch degree ordering check (Q025; implemented PR #236)
- `docs/planning/p067_biosketch_publication_date_ordering_scope_and_design.md` — P067 scope and design: bio-sketch publication/presentation reverse-chronology check (Q027; implemented)
- `docs/planning/p069_frontmatter_heading_gate_recall_refinement_scope_and_design.md` — P069 scope and design: front-matter heading gate recall refinement (implemented; infrastructure)
- `docs/planning/p071_references_section_localization_recall_refinement_scope_and_design.md` — P071 scope and design: references section localization recall refinement (implemented; infrastructure companion to P064)
- `docs/planning/p072_approval_page_heading_gate_recall_refinement_scope_and_design.md` — P072 scope and design: approval-page heading-gate recall refinement (implemented; infrastructure companion to P068; structural fallback when heading text absent)
- `docs/planning/p073_p019_page_numbering_triage_rollup_scope_and_design.md` — P073 scope and design: P019 page-numbering triage rollup (v1+v2 implemented)
- `docs/evaluation/p073_p019_page_numbering_triage_rollup.md` — **P073 P019 triage rollup** (2026-06-09): 67 P019 findings classified; `sequence_gap` (6, all files) highest-signal; `multiple_page_numbers` + `inconsistent_position` on EF PDFs likely artifact-driven
- `docs/evaluation/p073_v2_p019_triage_code_rollup_validation.md` — P073 v2 code rollup validation: triage metadata added to P019 findings; `build_p019_page_numbering_triage_summary()` wired in JSON/Markdown reports; 17 new tests; canonical aggregate 1,543 unchanged
- `docs/evaluation/p072_approval_page_heading_gate_recall_synthetic_validation.md` — P072 synthetic validation (infrastructure-only; 14 tests)
- `docs/evaluation/p072_approval_page_heading_gate_recall_current_dataset_evaluation.md` — P072 full five-PDF detection-mode eval (complete; structural fallback 0 candidates on all 3 non-detecting files; image-embedded approval pages confirmed; aggregate unchanged 1,543)
- `docs/planning/p070_toc_lot_lof_entry_parser_recall_refinement_scope_and_design.md` — P070 scope and design: TOC/LoT/LoF entry parser recall refinement (implemented; infrastructure)
- `docs/evaluation/p070_toc_lot_lof_entry_parser_recall_synthetic_validation.md` — P070 synthetic validation (infrastructure-only; 12 tests)
- `docs/evaluation/p070_toc_lot_lof_entry_parser_recall_current_dataset_evaluation.md` — P070 five-PDF parser-reach eval (complete; post-P070 aggregate 1,543 findings)
- `docs/planning/p068_approval_page_committee_block_structural_scope_and_design.md` — P068 scope and design: approval page committee/signature-block structural check (implemented)
- `docs/evaluation/p068_approval_page_committee_blocks_synthetic_validation.md` — P068 synthetic test coverage, privacy model, and limitations
- `docs/evaluation/p068_current_dataset_evaluation.md` — P068 current-dataset evaluation (3 findings on 2/5 files; 3/5 skipped at detection gate; 2026-06-08)
- `docs/evaluation/p065_dedication_centering_italic_synthetic_validation.md` — P065 synthetic test coverage and gate verification (15/15 tests pass)
- `docs/evaluation/p065_current_dataset_evaluation.md` — P065 current-dataset evaluation (2026-06-08; 0 findings; all 5 PDFs skipped — no machine-readable DEDICATION heading detected)
- `docs/evaluation/current_auditor_after_p068_evaluation.md` — post-P068 full five-PDF aggregate snapshot (P011–P068; 1,590 findings; P068 adds 3; 2026-06-08)
- `docs/evaluation/current_auditor_after_p067_evaluation.md` — post-P067 full five-PDF aggregate snapshot (P011–P067; 1,587 findings; P067 adds 0; 2026-06-08)
- `docs/evaluation/current_auditor_after_p066_evaluation.md` — post-P066 full five-PDF aggregate snapshot (P011–P066; 1,587 findings; P066 adds 0; 2026-06-08)
- `docs/evaluation/current_auditor_after_p065_evaluation.md` — post-P065 full five-PDF aggregate snapshot (P011–P065; 1,587 findings; P065 adds 0; 2026-06-08)
- `docs/evaluation/p066_biosketch_degree_ordering_synthetic_validation.md` — P066 synthetic test coverage and gate verification (12/12 tests pass)
- `docs/evaluation/p066_current_dataset_evaluation.md` — P066 current-dataset evaluation (2026-06-08; 0 findings; 3/5 skipped — heading not detected; 2/5 detected and passed)
- `docs/evaluation/p067_biosketch_publication_ordering_synthetic_validation.md` — P067 synthetic test coverage, privacy model, and limitations
- `docs/evaluation/p067_current_dataset_evaluation.md` — P067 current-dataset evaluation (2026-06-08; 0 findings; 3/5 skipped at heading detection; 2/5 reached Bio Sketch but no qualifying Publications boundary detected)
- `docs/evaluation/current_auditor_after_p070_evaluation.md` — **current** full PDF audit snapshot (P011–P070, five evaluation PDFs; **1,543** findings; −47 vs P069-era; P070 infrastructure-only)
- `docs/evaluation/current_auditor_after_p069_evaluation.md` — full PDF audit snapshot at P069 era (P011–P069, five evaluation PDFs; **1,590** findings; unchanged vs P068-era; P069 infrastructure-only)
- `docs/evaluation/p069_frontmatter_heading_gate_recall_synthetic_validation.md` — P069 synthetic validation (infrastructure-only; 13 tests; no standalone findings)
- `docs/evaluation/p069_frontmatter_heading_gate_recall_current_dataset_evaluation.md` — P069 five-PDF gate-reach evaluation (ACKNOWLEDGEMENTS +4; P065–P068 totals unchanged)
- `docs/evaluation/ef_overlap_after_p068_evaluation.md` — EF comment-vs-tool overlap refresh after P068 on 2 extractable-comment PDFs (143 annotations; P064–P068 unchanged overlap on comparison set)
- `docs/evaluation/ef_overlap_after_p072_evaluation.md` — EF comment-vs-tool overlap refresh after P072; `committee_approval_page` gap unchanged (5 EF, 0 tool); structural fallback found 0 candidates; total 671 tool findings unchanged
- `docs/evaluation/ef_overlap_after_p071_evaluation.md` — EF comment-vs-tool overlap refresh after P071; P064 reaches 2/2 comparison PDFs; `references_citations` gap unchanged (9 EF, 0 tool)
- `docs/evaluation/real_thesis_pairing_and_ef_overlap_readiness.md` — real thesis data inventory, raw/commented pairing, EF comment extractability, overlap-readiness, and recurring evaluation workflow (P068-era refresh; Sebastian Fine EF recovery note added 2026-06-09)
- `docs/evaluation/sebastian_fine_ef_archive_recovery.md` — Sebastian Fine EF archive recovery attempt (2026-06-09): BLOCKED — EF-annotated version not found locally; comparison set remains 2 extractable files
- `docs/evaluation/p047_current_dataset_evaluation.md` — P047 gap-fill: 0 findings; Bio Sketch heading not detected
- `docs/evaluation/p058_current_dataset_evaluation.md` — P058 gap-fill: 0 findings; no TOC page-number ordering violations
- `docs/evaluation/p062_current_dataset_evaluation.md` — P062 gap-fill: 0 findings; no qualifying cross-page TOC sequence detected
- `docs/evaluation/p063_current_dataset_evaluation.md` — P063 gap-fill: 0 findings; body-region appendix detection gate not met
- `docs/evaluation/` — per-rule and historical evaluation docs (P011–P072 scope)

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

- **Local/runtime processing:** no external API calls during audit by default. Optional URL fetch (`POST /audits/url`) is the only network operation and is SSRF-guarded.
- **Web export privacy reduction:** web-generated JSON/Markdown downloads use basename-only paths and, for TeX/ZIP source audits, replace raw messages and remove private detail keys (`label`, `ref`, `caption`, `title`, `author`, `body`, `text`, and related source-snippet fields) via `sanitize_report_for_web_export()`. CLI `--json-out`/`--md-out` output is not sanitized. Note: web exports are privacy-reduced, not guaranteed fully anonymized.
- **Job TTL cleanup:** completed/failed jobs and their runtime files are automatically removed after `NJIT_AUDITOR_WEB_JOB_TTL_SECONDS` (default 24 h). In-memory job state is lost on server restart; on-disk files remain until TTL cleanup.
- **No authentication or rate limiting by default.** Public deployments need a reverse proxy, TLS, authentication, and rate limiting. See [docs/web_gui_mvp.md](docs/web_gui_mvp.md).

## Development

```bash
ruff check .
mypy src
python -m pytest
```
