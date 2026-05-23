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

P011 refinement notes:

- Uses line-level geometry (instead of only broad block boxes) where available.
- Ignores whitespace-only lines and tiny artifacts.
- Applies a 3pt overflow tolerance before flagging a violation.
- Excludes likely page-number candidates to avoid duplicate/low-value warnings.
- Groups repeated violations per page and per side (`left_margin`, `right_margin`,
  `top_margin`, `bottom_margin`) with worst-overflow and affected-line counts.

Current limitations:

- digital PDFs with text layers only
- no OCR yet
- no computer vision yet
- heading checks are deterministic/heuristic only and depend on text-layer quality
- indentation checks are heuristic and sensitive to PDF line segmentation artifacts
- paragraph grouping uses geometric thresholds and may over/under-group in complex layouts
- current missing-indent detection is conservative and may miss subtle cases
- spacing checks are front-matter-focused and can miss issues outside named front matter
- spacing thresholds depend on extracted line boxes and can be affected by PDF text-layer quirks
- caption/title checks depend on text-layer extraction and can miss multi-line caption context
- capitalization hints are intentionally conservative and may under-report style issues
- TOC/list alignment checks depend on line reconstruction and may miss subtle hierarchy/style defects
- optional front-matter sections are not yet required to exist in every PDF
- heuristic foundation checks, not final NJIT compliance verdicts
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
