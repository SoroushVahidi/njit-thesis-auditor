# Phase 2 PDF Layout Foundation

Phase 2 begins PDF-first auditing with layout-aware extraction, not document
reconstruction.

Why exact PDF reconstruction is not the goal:

- PDF content streams are optimized for rendering, not lossless semantic round-trip.
- Reconstructing text and layout into an identical PDF is not practical for robust
  compliance checks.
- Instead, we extract geometric structure and audit directly against layout signals.

Backend:

- First backend: PyMuPDF (`fitz`)
- Coordinates are represented in PDF points.

PDF command supports optional structured output paths:

- `njit-audit pdf thesis.pdf --json-out report.json --md-out report.md`

Initial checks implemented:

- `P013`: page-number candidate detection in top/bottom zones
- `P011`: possible text crossing assumed margin boundaries
- `P012`: PDF annotations/comments detection
- `P014`: named front-matter heading layout/style heuristics
- `P015`: paragraph indentation heuristics for front-matter/body text
- `P016`: spacing/blank-line heuristics for front-matter pages
- `P017`: caption/title punctuation and case heuristics for figure/table lines
- `P018`: TOC/list alignment heuristics for entry formatting consistency
- `P019`: page-number sequence/style heuristics on candidate page numbers
- `P020`: title-case capitalization heuristics for Level 2 headings and table titles
- `P021`: abstract word-count check on Abstract page (conservative; single-page extraction)
- `P023`: body-text double-spacing check (body pages only; requires ≥8 suspicious gaps, ≥60% fraction, median ratio < 1.55×)
- `P024`: TOC/LoT/LoF entry capitalization and terminal punctuation (Q049–Q050 and LoT period; level classified by numbering pattern + indentation)
- `P025`: front-matter structure and required-elements (abstract body, title page degree/institution, approval page content, front-matter order)
- `P022`: no visible page number on named no-number front-matter pages (Abstract, Title, Approval, Copyright)
- `P023`: body-text double-spacing check (body pages only; conservative threshold; ≥8 suspicious gaps, ≥60% fraction, median ratio < 1.55×)
- `P024`: TOC/LoT/LoF entry capitalization and terminal punctuation (level classified by numbering pattern + indentation)
- `P026`: body font compliance (size ≈12pt, family = Times New Roman or accepted equivalent; ≥5 violations AND ≥50% of body spans)
- `P027`: numbered heading level-specific style (L1 ALL CAPS, L2 Title Case, L3-5 Sentence case; inferred from section-number patterns)
- `P028`: page-numbering regime (front-matter pages → lowercase Roman; body pages → Arabic; region detected from named headings + CHAPTER heading)
- `P029`: front-matter lowercase Roman numeral ordering (sequence checks for i, ii, iii...; flags repeats/gaps/decreases; candidates with value > 50 excluded as implausible TOC/noise artifacts)

P013 refinement notes:

- Candidate extraction remains unchanged (same top/bottom-zone detector used by P019/P022/P028/P029).
- Warning emission is now grouped to **one P013 warning per page** (instead of one per candidate line), reducing repeated noise on pages with multiple number-like tokens.
- P013 warnings now include structured triage details:
  - `issue_type=page_number_candidate`
  - `candidate_count_on_page`
  - representative `candidate_sample`
  - `position_type` and `number_style`
  - conservative `confidence` (`low`/`medium`)

P018/P024 round-2 refinement notes:

- TOC/List page detection now tolerates heading variants with:
  - trailing punctuation (e.g., `TABLE OF CONTENTS.`)
  - continuation suffixes (e.g., `LIST OF TABLES (CONTINUED)`, `... CONTINUED`)
- This is a detection-scope refinement only; P018/P024 issue semantics and thresholds are unchanged.

P014 refinement notes:

- Centering check now compares against text-area center `(LEFT_MARGIN_PT + page.width - RIGHT_MARGIN_PT) / 2`
  rather than physical page center. NJIT's asymmetric margins (1.5" left, 1" right) place the
  text area center 18pt right of the page center; using page center produced false positives on
  all tested PDFs. Fixed in clean-baseline investigation (2026-05-29).

P014 checks (heuristic):

- expected named heading text match for:
  `ABSTRACT`, `APPROVAL PAGE`, `BIOGRAPHICAL SKETCH`, `ACKNOWLEDGEMENTS`,
  `TABLE OF CONTENTS`, `LIST OF TABLES`, `LIST OF FIGURES`
- near-top zone check (`y0 <= 2.0in`, 72pt/in)
- horizontal centering check (line center within `12pt` of page center)
- all-caps check
- bold inference from extracted span style metadata and font-name hints

P015 checks (heuristic, conservative):

- groups nearby text-layer lines into paragraph candidates
- ignores named front-matter heading lines and page-number-like lines
- ignores short lines and TOC/list pages (`TABLE OF CONTENTS`, `LIST OF TABLES`,
  `LIST OF FIGURES`)
- computes paragraph first-line indent as:
  `first_line_x - median(continuation_line_x)`
- emits warnings only for strong cases:
  - opening paragraph on `ABSTRACT` page appears unexpectedly indented
  - later paragraph appears to be missing expected first-line indent
- excludes likely references/bibliography pages, captions, and list/bullet patterns
- groups repeated same-page findings per issue type to reduce noise

P016 checks (heuristic, conservative):

- line-level spacing checks on text-layer geometry
- currently focused on named front-matter pages only
- ignores page-number-like lines, TOC/list pages, and references-like pages
- skips likely caption-heavy noise patterns
- computes adaptive spacing thresholds from median extracted line height
- flags only strong spacing cases:
  - suspiciously large blank gap after a front-matter heading
  - excessive blank space between likely paragraph groups
  - repeated excessive line gaps on the same page
- groups repeated same-page findings by issue type to reduce noise

P017 checks (heuristic, conservative):

- detects caption-like lines beginning with `Figure`, `Fig.`, or `Table` plus number token
- applies context-aware checks for body pages, `LIST OF TABLES`, and `LIST OF FIGURES`
- flags only obvious issues:
  - missing terminal punctuation on figure captions
  - unexpected terminal periods for table entries in `LIST OF TABLES`
  - obvious table punctuation artifacts (for example double terminal periods)
- includes optional low-confidence case-style hints only for sufficiently long captions
- ignores ambiguous short lines and non-caption regions (for example TOC/references)

P018 checks (heuristic, conservative):

- runs only on pages with named headings:
  `TABLE OF CONTENTS`, `LIST OF TABLES`, `LIST OF FIGURES`
- extracts likely entry lines below heading and infers right-side page-number tokens
- checks grouped page-level issues:
  - page-number column misalignment (right-edge outliers)
  - likely entries missing page-number tokens
  - inconsistent visible leader-dot usage when dot style is dominant
  - obvious hierarchy indentation outliers
- groups repeated same-page issues by issue type to reduce noise

P019 checks (heuristic, conservative):

- builds on page-number candidate detection from top/bottom page zones
- classifies candidate style (`arabic`, `roman_lower`, `roman_upper`) and position
- flags only obvious grouped issues:
  - likely missing page number when neighboring pages have candidates
  - multiple page-number candidates on one page
  - inconsistent page-number position vs dominant pattern
  - obvious candidate sequence gaps
  - mixed numbering styles in candidate regions
- does not yet enforce full NJIT policy-specific page-number rules

P020 checks (heuristic, conservative):

- applies only to title-like text regions, not body paragraphs
- checked regions:
  - bold heading-like lines (≤150 chars, not all-caps front-matter labels, not on
    references or TOC pages) — targets Level 2 headings (X.x), which use Title Case
  - table caption title bodies from existing caption detection (table only;
    figure captions use sentence case and are excluded)
- skips pages with REFERENCES, BIBLIOGRAPHY, TABLE OF CONTENTS headings
- ignores all-caps front-matter labels and page numbers
- NJIT title-case rules applied (per `Titles Examples Level 1 to 5.docx`):
  - first word must be capitalized
  - last word must be capitalized
  - words after subtitle separators (colon, em/en dash, double-hyphen) must be capitalized
  - minor words (a, an, the, and, but, or, for, nor, as, at, by, in, of, on, per, to, up,
    via) may be lowercase in the middle
  - all other words (including all words of 4+ letters) must be capitalized
- preserves all-caps acronyms (PDF, AI, MRI, NJIT, etc.)
- hyphenated words are skipped (conservative)
- words with digits, Greek letters, or math notation are skipped
- one finding per title-like line (first violation only)
- does not flag over-capitalization; only detects under-capitalization

P011 refinement notes:

- Uses line-level geometry (instead of only broad block boxes) where available.
- Ignores whitespace-only lines and tiny artifacts.
- Applies a 3pt overflow tolerance before flagging a violation.
- Excludes likely page-number candidates to avoid duplicate/low-value warnings.
- Groups repeated violations per page and per side (`left_margin`, `right_margin`,
  `top_margin`, `bottom_margin`) with worst-overflow and affected-line counts.
- Compression artifact guard: suppresses a page/side group when `affected_line_count ≥ 5`
  AND `worst_overflow < 8pt`. This pattern indicates a systematic PDF-coordinate shift
  rather than a real margin violation. Reduced false positives 53% on a compressed test PDF
  while leaving all normal-PDF findings unchanged.
- Adds `confidence` (low/medium/high) to finding details based on overflow magnitude and group size.

Current limitations:

- digital PDFs with text layers only; no OCR or scanned-PDF support
- no computer vision yet
- heading checks depend on text-layer quality; bold/italic metadata often absent
- indentation checks are heuristic and sensitive to PDF line segmentation artifacts
- paragraph grouping uses geometric thresholds and may over/under-group in complex layouts
- spacing checks are front-matter-focused and can miss issues outside named front matter
- caption/title checks depend on text-layer extraction and can miss multi-line caption context
- capitalization hints are intentionally conservative and may under-report style issues
- TOC/list alignment checks depend on line reconstruction and may miss subtle hierarchy/style defects
- page-number regime checks require CHAPTER heading detection to identify body start
- font compliance (P026): Computer Modern (LaTeX default) is flagged as non-Times — may be acceptable by department
- heading-level inference (P027): only checks numbered section headings (1.1, 1.1.1, etc.); unnumbered body headings are not classified
- all checks are heuristic signals, not final NJIT compliance verdicts; all findings require manual review
- structured report output is summary-oriented and intentionally avoids long text excerpts

## PDF Comment Workflow (Local-Only)

Phase 2 also supports a local reviewer-comment workflow:

- `njit-audit pdf-comments extract input.pdf --json-out ... --md-out ...`
- `njit-audit pdf-comments clean input.pdf --out clean.pdf`

Purpose:

- Extract annotation/comment objects for structured offline review.
- Create a "clean" PDF copy with annotation objects removed.
- Re-run PDF heuristics on the clean copy to compare automated findings with
  reviewer feedback at a high level.

Privacy cautions:

- Do not overwrite or modify raw dissertation PDFs.
- Keep generated evaluation outputs under ignored folders (for example
  `data/evaluation/generated/` or `data/evaluation/private/`).
- Do not commit full dissertation body text or long annotation text.

## Expert Comment Comparison (Deterministic)

Phase 2 now includes deterministic category-level comparison helpers for
reviewer comments vs automatic findings:

- `categorize_comment_text(...)` for keyword/regex comment categories
- category summaries for extracted comments and rule findings
- simple mapping from rule IDs (for example `P011`, `P012`, `P013`) to
  high-level categories

Notes:

- This is not semantic AI matching.
- It is designed to prioritize next rule implementation from real reviewer
  feedback while staying fully local/offline.
