# Ester Sample A Correctness Pass 1

**Recorded:** 2026-07-08  
**Branch:** `fix/ester-sample-a-correctness-pass1`  
**Base:** `fix/ester-email-alignment-audit` / PR #481 (still open when this pass started)

## Scope

This pass continued from the completed Ester wording/alignment work and focused only on reproducible **detector/highlight correctness** issues for Sample A.

Out of scope:

- broad student-facing wording rewrites
- deep detector redesigns
- Gemini / API / external-service integrations
- speculative fixes for issues that could not be reproduced confidently

## Sources Used

- `docs/status/ester_email_alignment_audit.md`
- `docs/status/ester_student_facing_alignment_pass1.md`
- `data/specs/ester_warning_wording_map.json`
- `docs/status/ester_sample_a_correctness_alignment.md`
- existing PDF, web, and Sample A regression tests
- built-in Sample A fixture: `data/raw/ester/250218 Cibaku Elson First Review.pdf`

`Sample A feedback.docx` was **not** available in the repo, so this pass stayed grounded in reproduced behavior rather than guessing at missing source material.

## Baseline Reproduction

Starting from PR #481 behavior, Sample A reproduced as:

- **35 student-facing problems**
- `P011` 19
- `P015` 5
- `P013` 2
- `P028` 2
- `P019` 1
- `P051` 1
- `P044` 1
- `P016` 1
- `P027` 1
- `P020` 1
- `P012` 1

The clearest reproduced failures were:

- `P044` on page 1 highlighting the dissertation title instead of the first Abstract paragraph
- `P013` / `P028` on TOC pages 10-11 preferring TOC destination numbers over the real bottom-center Roman page number
- `P027` treating ordinary body text beginning with `Chapter` as a Level 1 heading
- `P015` flagging algorithm/code-like blocks, lowercase continuation splits, and the paragraph after a split numbered heading

## Fixed In This Pass

### P013 / P028 front-matter page-number false positives

Fixed the candidate-selection path so front-matter pages that already have a bottom-center Roman numeral drop competing bottom-right Arabic TOC/list destination numbers.

Result:

- Sample A `P013` page-order problems on pages 10-11 are gone
- Sample A `P028` front-matter style false positives on pages 10-11 are gone
- the real page-number candidate still remains available internally for detector logic and inventory views

### P044 abstract first-paragraph targeting

Fixed Abstract paragraph collection so centered dissertation-title/byline preamble text between `ABSTRACT` and the body is not treated as paragraph 1.

Result:

- Sample A page 1 `P044` false positive is gone
- the first real Abstract paragraph is now the target paragraph for Q002/Q003 checks

### P027 heading false positive

Tightened Level 1 chapter detection so mixed-case body sentences beginning with `Chapter ...` no longer qualify as `CHAPTER` / `APPENDIX` headings.

Result:

- Sample A page 21 `P027` false positive is gone
- residual web-demo expectations were updated to reflect removal of the old false positive

### P015 indentation false positives

Added conservative suppression for three reproduced bad cases:

- algorithm/code-like blocks
- lowercase continuation-style paragraph splits
- first paragraph after a split numbered heading such as `4.3` + `Problem Formulation`

Result:

- Sample A algorithm-line false positive is gone
- Sample A continuation/split-heading false positives are gone
- Sample A `P015` problem count dropped from **5** to **1**

## Already Satisfied Before This Pass

These were verified and kept intact:

- PR #481 already removed the Sample A `P038` missing-front-matter false positives
- `P038` `required_heading_missing` still appears as a student-facing document-level problem when present, with an honest no-highlight explanation
- `P012` student-facing rollup already lists affected pages when known; this pass added regression coverage so that behavior stays visible

## Post-Fix Sample A State

Sample A now reproduces as:

- **25 student-facing problems**
- `P011` 19
- `P015` 1
- `P019` 1
- `P051` 1
- `P016` 1
- `P020` 1
- `P012` 1

Resolved from Ester’s latest Sample A concerns:

- `P044` abstract-title highlight false positive
- `P013` / `P028` TOC-page-number false positives on pages 10-11
- `P027` body-text heading false positive
- `P015` algorithm / continuation / split-heading false positives
- `P012` page-list visibility remains satisfied and now has regression coverage
- `P038` student visibility/no-highlight behavior remains satisfied and now has regression coverage

## Deferred

These remain intentionally deferred:

- `P011` disputed margin findings
  - pages 26 / 43 / 54 still looked like genuine bottom-margin overflows under current geometry
  - no strong evidence yet of page-number/header/artifact contamination
  - rule strictness was left unchanged
- `P019` document-level mixed numbering style
  - likely needs deeper numbering-region logic, not a presentation-only fix
- remaining `P015` page 26 finding
  - still reproducible; not clearly a false positive from current evidence
- `P016` page 1 spacing
  - failure mode not yet clear enough for a safe fix
- `P051` copyright year
  - failure mode not yet clear enough for a safe fix

## Files Changed

- `src/njit_auditor/rules/pdf_abstract_indentation.py`
- `src/njit_auditor/rules/pdf_page_numbers.py`
- `src/njit_auditor/rules/pdf_page_numbering_regime.py`
- `src/njit_auditor/rules/pdf_heading_levels.py`
- `src/njit_auditor/rules/pdf_indentation.py`
- `tests/test_pdf_rules.py`
- `tests/test_ester_sample_a_correctness.py`
- `tests/test_web_demo_fixtures.py`

## Tests

Targeted:

- `PYTHONPATH=src /home/soroush/njit-thesis-auditor/main/.venv/bin/python -m pytest tests/test_pdf_rules.py -k 'p013 or p015 or p027 or p028 or p044' tests/test_ester_sample_a_correctness.py`
- `PYTHONPATH=src /home/soroush/njit-thesis-auditor/main/.venv/bin/python -m pytest tests/test_ester_sample_a_correctness.py`

Full suite:

- `PYTHONPATH=src /home/soroush/njit-thesis-auditor/main/.venv/bin/python -m pytest`
- result: **2662 passed, 4 warnings**

## Commit / PR Readiness

This branch is ready for commit / PR for a focused Sample A correctness pass.

The remaining disputed items are detector-policy questions or deeper highlight work, not unfinished fallout from the fixes above.
