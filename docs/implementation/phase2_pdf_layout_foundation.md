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
- `P011`: possible text outside assumed margin rectangle
- `P012`: PDF annotations/comments detection

Current limitations:

- digital PDFs with text layers only
- no OCR yet
- no computer vision yet
- no TOC/heading/indentation verification yet
- heuristic foundation checks, not final NJIT compliance verdicts
