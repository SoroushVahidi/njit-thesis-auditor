# P044 Abstract Indentation Synthetic Validation

- **Date:** 2026-06-03
- **Rule:** P044 — Abstract page paragraph indentation (Q002/Q003)
- **Status:** **Synthetic validation only** — current-dataset audit not run (evaluation PDFs unavailable)
- **Baseline main at implementation:** `8485e52` (PR #120 — Implement P044 Abstract indentation checks)

---

## Validation summary

| Check | Result |
|-------|--------|
| Synthetic unit tests | **9 passed** |
| `ruff check .` | ✅ Clean |
| `mypy src` | ✅ Clean (58 source files) |
| `python -m pytest` | ✅ **507 passed** |

---

## Synthetic test coverage

| Test | Scenario | Expected outcome | Pass |
|------|----------|-----------------|------|
| `test_p044_no_abstract_page_no_findings` | No ABSTRACT heading on page | No P044 findings | ✅ |
| `test_p044_one_paragraph_q002_only_no_q003` | Single paragraph below heading | Q002 checked; no Q003 finding (gate) | ✅ |
| `test_p044_correct_format_no_findings` | First para flush-left (x=108); second para indented (x=140) | No P044 findings | ✅ |
| `test_p044_first_paragraph_indented_warns` | First para indented (x=150) | `abstract_first_paragraph_indented` (Q002) | ✅ |
| `test_p044_subsequent_paragraph_not_indented_warns` | Second para flush-left (x=108 same as first) | `abstract_subsequent_paragraph_not_indented` (Q003) | ✅ |
| `test_p044_text_before_heading_ignored` | Pre-heading text at far-left x=40; body paragraphs at x=108/140 | No false positive from pre-heading text contaminating margin | ✅ |
| `test_p044_finding_metadata_no_private_content` | Indented first para; flush second para | Findings contain geometry metadata only; no abstract text | ✅ |
| `test_p044_q002_source_q_rule_id` | First para indented | `source_q_rule_id` = `Q002` in finding | ✅ |
| `test_p044_q003_source_q_rule_id` | Second para flush-left | `source_q_rule_id` = `Q003` in finding | ✅ |

---

## Issue types

| Issue type | Q-rule | Condition |
|-----------|--------|-----------|
| `abstract_first_paragraph_indented` | Q002 | First Abstract paragraph first-line x0 exceeds `left_margin + INDENT_THRESHOLD_PT (18pt)` |
| `abstract_subsequent_paragraph_not_indented` | Q003 | Subsequent Abstract paragraph first-line x0 is less than `left_margin + INDENT_THRESHOLD_PT (18pt)`; gate: skip if fewer than 2 paragraph blocks |

---

## Canonical aggregate baseline (unchanged)

| Field | Value |
|-------|-------|
| Canonical pre-P035/…/P044 five-PDF aggregate | **1,446** total findings |
| `generated_for_commit` | `00b9c2d` |
| Canonical eval doc | `docs/evaluation/current_auditor_after_p034_evaluation.md` |

P044 does not alter the canonical 1,446 baseline. The baseline was established before P035
and has not been updated by a full P001–P044 rerun.

---

## P044 v1 limitations

| Limitation | Detail |
|-----------|--------|
| Heading detection gate | Emits nothing if ABSTRACT heading is not in the text layer (compressed/flattened PDFs) |
| Q003 gate | Emits no `abstract_subsequent_paragraph_not_indented` if fewer than 2 paragraph blocks found; many abstracts are single-paragraph |
| Continuation lines only | Considers first-line x-position of each paragraph block; not a full paragraph-flow analysis |
| Left-margin derivation | Left margin is the minimum x0 across all body lines on the abstract section; may be affected by very short lines |
| P015 overlap | P015 may also flag the abstract opening paragraph via `unexpected_opening_indent`; P044 uses distinct issue types and does not conflict |

---

## Current-dataset evaluation

No P044 current-dataset finding counts are available. The full set of five evaluation PDFs
(including Sebastian Fine, which is ZIP-only) was not available in the workspace at the time
of implementation.

When evaluation PDFs are available locally:

1. Run `njit-audit pdf` on the five canonical evaluation PDFs.
2. Collect P044 aggregate counts only (no per-PDF abstract text).
3. Save outputs to `data/evaluation/generated/current_auditor_after_p044/` (gitignored).
4. Add a summary of aggregate P044 counts to a separate current-dataset evaluation doc.
5. Do **not** update `generated_for_commit` unless the run is complete and validated.

---

## Privacy

Findings from P044 contain geometry metadata only:
`page_number`, `issue_type`, `paragraph_index`, `observed_x0`, `expected_left_margin`,
`indent_delta_points`, `required_indent_points`, `triage_tier`, `source_q_rule_id`.
No Abstract paragraph text, thesis title, author names, or other private content is quoted.

Generated audit outputs remain gitignored under `data/evaluation/generated/` and must not
be committed.
