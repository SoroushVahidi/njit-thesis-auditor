# Phase 1 Realistic TeX Fixture

This fixture provides a more realistic synthetic NJIT-style multi-file LaTeX
project for evaluating the Phase 1 source-only auditor before adding deeper
parsing or PDF/layout phases.

Why this fixture exists:

- validate recursive loading over frontmatter/chapters/backmatter structure
- exercise rule coverage in a layout closer to real thesis source trees
- avoid any real student dissertation content

How to run:

```bash
njit-audit tex examples/latex/njit_style_synthetic_thesis/main.tex
njit-audit tex examples/latex/njit_style_synthetic_thesis_bad/main.tex
```

What it demonstrates:

- good synthetic tree: expected no `FAIL` findings, valid Q006 metadata month
- bad synthetic tree: expected Q004/Q005/Q006 findings plus multiple project
  rule warnings/failures (labels, risky commands, missing structure details)

Privacy note:

- all content in this fixture is synthetic
- no real student text or private dissertation content is included
