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

Initial checks implemented:

- `P013`: page-number candidate detection in top/bottom zones
- `P011`: possible text crossing assumed margin boundaries
- `P012`: PDF annotations/comments detection
- `P014`: named front-matter heading layout/style heuristics

P014 checks (heuristic):

- expected named heading text match for:
  `ABSTRACT`, `APPROVAL PAGE`, `BIOGRAPHICAL SKETCH`, `ACKNOWLEDGEMENTS`,
  `TABLE OF CONTENTS`, `LIST OF TABLES`, `LIST OF FIGURES`
- near-top zone check (`y0 <= 2.0in`, 72pt/in)
- horizontal centering check (line center within `12pt` of page center)
- all-caps check
- bold inference from extracted span style metadata and font-name hints

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
- optional front-matter sections are not yet required to exist in every PDF
- heuristic foundation checks, not final NJIT compliance verdicts

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
