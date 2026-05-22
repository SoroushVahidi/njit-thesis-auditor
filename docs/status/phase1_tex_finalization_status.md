# Phase 1 TeX Finalization Status

## 1. What Phase 1 currently supports

Phase 1 provides local, source-only auditing for LaTeX projects without requiring TeX compilation or PDF rendering.

Current capabilities include:

- Recursive `\input{}` / `\include{}` loading
- Abstract checks with `pylatexenc`-assisted LaTeX-to-text conversion
- Graduation month checks (source-level heuristic)
- Structure presence checks (abstract, TOC, lists, chapter, bibliography)
- Risky formatting command detection
- Label/reference consistency checks
- Figure/table caption and label checks
- Optional local linter integration (`chktex`, `lacheck`)

## 2. Exact commands

```bash
njit-audit tex path/to/main.tex
njit-audit tex path/to/main.tex --linters
```

## 3. Rules currently covered

- Ester rules:
  - `Q004`
  - `Q005`
  - `Q006` (partially implemented, source-level heuristic)
- Project-added rules:
  - `P001` through `P010`

## 4. What is still not covered

- PDF visual/layout rules
- Compiled LaTeX log warning analysis
- Robust full TeX AST parsing
- DOCX file auditing
- Committee/human-metadata-dependent rules

## 5. Recommended remaining steps before calling TeX-source phase finalized

- Test on real or anonymized NJIT-style TeX projects
- Add optional `plasTeX` (or stronger AST backend) only if regex/`pylatexenc` proves insufficient
- Improve metadata/template detection where false positives/negatives remain
- Add final usage examples for student/reviewer workflows

## 6. Privacy note

- Processing is local/offline
- No paid APIs are used
- No external document upload is required
