# Phase 1 TeX Source Auditor

Phase 1 implements a source-only auditor for LaTeX projects without compiling documents.

Usage:

```bash
njit-audit tex path/to/main.tex
```

Implemented capabilities:

- recursive `\input{}` and `\include{}` loading
- abstract forbidden-term detection
- abstract first-person pronoun detection
- graduation month heuristic checks
- required TeX structure presence checks
- risky formatting command checks
- label/reference consistency checks
- figure/table caption/label/punctuation checks

Ester rule coverage in Phase 1:

- Q004: implemented
- Q005: implemented
- Q006: partially implemented (heuristic context detection)

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

Next improvements:

- optional `pylatexenc` or `plasTeX` parsing backend
- optional ChkTeX integration
- `latexmk`/compiler log auditing
- PDF layout auditing tied to Ester visual rules
