# Phase 1 TeX Source Auditor

Phase 1 implements a source-only auditor for LaTeX projects without compiling documents.

Usage:

```bash
njit-audit tex path/to/main.tex
njit-audit tex path/to/main.tex --linters
```

Implemented capabilities:

- recursive `\input{}` and `\include{}` loading
- abstract forbidden-term detection (with `pylatexenc`-based LaTeX-to-text cleanup)
- abstract first-person pronoun detection (with `pylatexenc`-based LaTeX-to-text cleanup)
- abstract word-count validation with degree-type inference (PhD ≤350, MS ≤150)
- graduation month heuristic checks
- required TeX structure presence checks
- risky formatting command checks
- label/reference consistency checks
- figure/table caption/label/punctuation checks
- optional local linter checks (`chktex`, `lacheck`) when `--linters` is used

Ester rule coverage in Phase 1:

- Q004: implemented
- Q005: implemented
- P021: implemented (abstract word-count; no Q-rule equivalent in Q001–Q079)
- Q006: partially implemented (heuristic metadata/title-page context detection, prioritizing
  `\date{...}`/`graduation...`-style macros)

Project-added rules covered:

- risky formatting commands
- duplicate labels
- labels with spaces
- missing `\ref{}` / `\eqref{}` targets
- missing figure/table captions
- missing figure/table labels
- caption terminal punctuation
- required structure command presence

Known limitations:

- regex-based parsing only
- no TeX compilation step
- no PDF visual/layout checking
- no full TeX AST/model expansion support
- prose checks are improved by LaTeX-to-text conversion, but this still does not replace
  rendered PDF/layout validation
- external linters are optional local tools and may be unavailable on some machines

Next improvements:

- optional `pylatexenc` or `plasTeX` parsing backend
- optional ChkTeX integration
- `latexmk`/compiler log auditing
- PDF layout auditing tied to Ester visual rules
