# Phase 1 TeX Demo

Run:

```bash
njit-audit tex examples/latex/good_minimal_thesis/main.tex
njit-audit tex examples/latex/bad_minimal_thesis/main.tex
njit-audit tex examples/latex/bad_minimal_thesis/main.tex --linters
```

Expected behavior:

- Good example should report mostly `PASS` with no `FAIL` findings.
- Bad example should report targeted `WARNING` and `FAIL` findings with file/line hints and suggested fixes.

Ester rules demonstrated:

- `Q004` abstract forbidden terms (`paper`/`article`)
- `Q005` abstract first-person pronouns
- `Q006` graduation month validity

Project-added rules demonstrated:

- `P001` risky formatting commands
- `P002` duplicate labels
- `P003` labels containing spaces
- `P004` missing `\ref{}`/`\eqref{}` targets
- `P005` missing figure/table captions
- `P006` missing figure/table labels
- `P007` caption punctuation
- `P008` required TeX structure presence
- `P009` optional ChkTeX linter findings (when installed)
- `P010` optional lacheck linter findings (when installed)

Limitations:

- no TeX compile step
- no PDF visual/layout checks
- regex-based parser (not full TeX AST)
- optional linters are external local tools and are skipped if not installed
