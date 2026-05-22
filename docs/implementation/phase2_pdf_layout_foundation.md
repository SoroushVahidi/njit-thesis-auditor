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
- no TOC/heading/indentation verification yet
- heuristic foundation checks, not final NJIT compliance verdicts
