# Phase 1 Milestone Summary

## 1. Project goal

`njit-thesis-auditor` is a free, local-first NJIT thesis/dissertation formatting auditor intended to support students and reviewers with private, offline checks.

## 2. Current milestone

Phase 1 delivers a TeX-source-only auditing workflow that runs before LaTeX compilation and before PDF layout inspection.

## 3. What has been implemented

- Ester materials organized under `data/raw/ester/`
- 79 Ester front-matter rules extracted into machine-readable JSON
- 47 feedback comments extracted as example artifacts
- NJIT rule inventory (`data/processed/rules/njit_rule_inventory.json`)
- 8 project-added TeX-source rules (`data/processed/rules/project_added_rules.json`)
- CLI command: `njit-audit tex path/to/main.tex`
- Recursive `\input{}` and `\include{}` source loading
- Abstract forbidden-term checks
- Abstract first-person pronoun checks
- Graduation month validation
- Required structure checks (abstract/TOC/lists/chapters/bibliography)
- Risky manual formatting command checks
- Label integrity checks (duplicate labels, invalid labels, missing refs)
- Figure/table caption and label checks
- Synthetic good/bad demo examples for repeatable demonstrations

## 4. Rule coverage

- `Q004` (abstract forbidden terms): implemented
- `Q005` (abstract first-person pronouns): implemented
- `Q006` (graduation month): partially implemented (heuristic source-context detection)
- Many Ester rules remain dependent on compiled PDF/layout verification
- Some rules require template reference data and/or human metadata for reliable validation

## 5. Demo commands

```bash
njit-audit tex examples/latex/good_minimal_thesis/main.tex
njit-audit tex examples/latex/bad_minimal_thesis/main.tex
```

## 6. Privacy model

- Processing is local/offline by design
- No paid APIs are required
- No external document upload is required
- Raw dissertation/review files must remain private
- Processed rule artifacts avoid inclusion of full dissertation body text

## 7. Limitations

- Regex-based source parsing
- No TeX compilation step yet
- No PDF visual/layout checks yet
- No DOCX support yet
- No full LaTeX AST parser yet

## 8. Recommended next phases

- Phase 1.1: improve TeX parsing with `pylatexenc` or `plasTeX`
- Phase 1.2: integrate `ChkTeX`/`lacheck` as optional local linters
- Phase 2: compile/log auditing via `latexmk` or `tectonic`
- Phase 3: PDF layout auditing via PyMuPDF/pdfplumber
- Phase 4: optional DOCX/comment extraction support
