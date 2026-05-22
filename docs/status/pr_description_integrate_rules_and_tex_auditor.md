# Summary

This PR integrates Ester-derived rule assets with the Phase 1 TeX-source auditor and adds demo-ready fixtures, rule mapping, and documentation for stakeholder review.

# Major Changes

- Organized Ester source artifacts and derived rule data under `data/raw/ester/` and `data/processed/rules/`
- Added NJIT rule inventory (79 Ester rules) with phase/checkability/input metadata
- Added project-added TeX-source rule set (8 implemented checks)
- Added `njit-audit tex path/to/main.tex` Phase 1 source-only flow
- Added synthetic demo fixtures:
  - `examples/latex/good_minimal_thesis/main.tex`
  - `examples/latex/bad_minimal_thesis/main.tex`
- Improved TeX findings/report wording with clearer explanations and suggested fixes
- Added milestone/demo/status documentation
- Expanded test suite to cover loader/rules/inventory/demo CLI behavior

# How To Test

```bash
python -m pip install -e ".[dev]"
ruff check .
mypy src
python -m pytest
```

Run demo:

```bash
njit-audit tex examples/latex/good_minimal_thesis/main.tex
njit-audit tex examples/latex/bad_minimal_thesis/main.tex
```

# Rule Coverage

- Ester rules covered in Phase 1:
  - `Q004` implemented
  - `Q005` implemented
  - `Q006` partially implemented
- Project-added implemented checks:
  - `P001` risky commands
  - `P002` duplicate labels
  - `P003` labels containing spaces
  - `P004` missing ref targets
  - `P005` missing figure/table captions
  - `P006` missing figure/table labels
  - `P007` caption punctuation heuristic
  - `P008` required TeX structure presence

# Privacy Notes

- Local/offline-first processing
- No paid API dependency
- No external upload required for thesis/review files
- Documentation avoids exposing raw dissertation body text

# Limitations

- Source-only regex parser (no full AST)
- No compile/log analysis in this phase
- No PDF visual/layout validation in this phase
- No DOCX auditing yet

# Validation Status

- `ruff check .` passed
- `mypy src` passed
- `python -m pytest` passed

# Checklist

- [x] Added/updated rules inventory and project-added rules
- [x] Added Phase 1 TeX-source auditor docs and demo docs
- [x] Added synthetic good/bad TeX demo fixtures
- [x] Added/updated tests for rule mappings and demo behavior
- [x] Verified lint, type-check, and test suite
- [x] Kept student document handling private/offline
