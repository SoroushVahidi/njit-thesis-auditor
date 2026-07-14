# Terminology

## "Esther," not "Ester" (in prose)

The project's formatting-review collaborator's name is spelled **Esther Flaim**. New prose in
documentation, comments, and PR text should use "Esther."

As of this audit (2026-07-13), the tracked codebase spells the name "Ester" 342 times across
`docs/` (208), `scripts/` (54), `tests/` (30), `src/` (8), and `README.md` (2) — and "Esther"
zero times. This is not a typo to sweep in one commit: `ester_*` is load-bearing as an
**identifier prefix**, not just a name spelling, across:

- Data files: `data/specs/ester_p_rule_feedback.json`, `data/specs/ester_q_matrix.json`,
  `data/raw/ester/` (private dissertation samples).
- Evaluation sample IDs used throughout tests and the web UI: `ester_sample_a`, `ester_sample_b`,
  `ester_sample_c`, `ester_sample_d`.
- Scripts: `scripts/ester_rule_consistency_audit.py`, `scripts/evaluate_ester_pdf_comments.py`.
- Test modules: `tests/test_ester_*.py`, `tests/test_p015_body_indent_ester_split.py`, etc.
- Docs filenames: `docs/status/ester_*.md`, `docs/sources/ester_materials.md`,
  `docs/planning/ester_*.md`.

**Decision made in this audit:** follow the task's own instruction — normalize the *name* to
"Esther" in prose going forward, but do **not** rename `ester_*` identifiers (files, sample IDs,
JSON keys, function/variable names, module names). Renaming those would touch dozens of files,
break every existing PR/branch that references them by path, and risks silently breaking a test
or script that matches on the literal string `"ester_sample_a"` somewhere. That's a
compatibility-breaking rename the task explicitly said not to do in this pass.

**What this audit actually changed:**

- `docs/sources/ester_materials.md`: fixed "Ester Farfan" → "Esther Flaim" (a different, factual
  name-spelling error — see that file's own note — not the identifier-prefix question above).
- New documentation added by this audit (`docs/status/CURRENT_STATUS.md`, `docs/ROADMAP.md`,
  `docs/RULE_ARCHITECTURE.md`, `docs/EVALUATION_DATA.md`, `docs/DEPLOYMENT.md`, this file) uses
  "Esther" in prose while referring to `ester_*` identifiers by their exact, unchanged names.
- Existing files with "Ester" in prose were **not** bulk-edited — that's still open work, tracked
  in `docs/ROADMAP.md` as low-risk-but-tedious cleanup, best done a few files at a time alongside
  other edits to those files rather than as one large diff.

If you're adding new code or docs: use "Esther" for the person, keep using `ester_*` for anything
that has to match an existing identifier, filename, or fixture, and don't invent a third spelling.

## Other terms

See [docs/RULE_ARCHITECTURE.md](RULE_ARCHITECTURE.md)'s vocabulary table for the standard
meaning of: finding, warning, issue type, public question / public rule card, remediation,
detector, reporting-only rule, experimental rule, and evaluation sample.

## "Initial MVP" language

Earlier documentation (including the top-level `README.md`) described this project as "the
initial MVP." As of this audit, the project implements P001–P083 (82 rules), has a deployed web
UI under continuous iteration, and is materially beyond an initial MVP stage. This audit removed
that phrase from `README.md`; if you find it elsewhere, it's safe to update — it's descriptive
language, not a versioned claim anything depends on.
