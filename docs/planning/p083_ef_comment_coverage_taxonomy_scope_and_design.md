# P083 Scope and Design: EF-Comment Coverage Taxonomy and In-Scope Gap Register

- **Rule ID:** P083
- **Rule type:** evaluation_task
- **Phase:** evaluation_task
- **Status:** implemented (2026-06-10)
- **Implementation:** `data/processed/ef_comment_coverage.json`
- **Analysis:** `docs/evaluation/ef_comment_coverage_analysis.md`
- **Candidate rules:** `docs/planning/ef_comment_candidate_rules.md`
- **Tests:** `tests/test_p083_coverage_schema.py`

---

## 1. Motivation

After P082, the auditor covers P001–P082 with 81 detection and infrastructure rules. The P080
DOCX extraction unlocked 52 EF reviewer comments from 2 DOCX dissertation drafts (22 from
DOCX_3RD_A, 30 from DOCX_3RD_B). A combined picture including comparison PDFs brings the
known EF feedback inventory to 614 items across 14 files, but only 52 are individually
accessible via text extraction.

The goal of P083 is to answer: **how well does the current P001–P082 auditor cover the
EF reviewer feedback that is structurally machine-checkable?** This analysis drives a
principled decision about whether any remaining gaps justify new detection rules.

---

## 2. Scope

**In scope:**
- Classify all 52 DOCX-extracted EF comments against the auditor taxonomy.
- Record taxonomy class, matched rule IDs, confidence, and gap notes for each comment.
- Compute aggregate coverage metrics (SIM/SIP/SMI/SBL rates).
- Identify SMI gaps and evaluate each against the five-gate evidence bar.

**Out of scope:**
- Adding new detectors (P084+ scope).
- Changing any existing detector behavior or thresholds.
- Changing the canonical five-PDF aggregate (1,543 unchanged).
- Analyzing PDF-comparison comments individually (only category-level counts are available
  for those files; the analysis doc covers them separately).
- Claiming coverage over the full 614-comment corpus (only the 52 DOCX-extracted comments
  are individually represented; PDF-comparison comments are category-level estimates).

---

## 3. Taxonomy

| Class | Meaning | Action |
|---|---|---|
| `SIM` | Structural In-scope Matched | Auditor fires on this category; finding is captured |
| `SIP` | Structural In-scope Partial | Auditor has a rule but exact page/instance match is uncertain |
| `SMI` | Structural Missing Implementation | In-scope but no current rule detects this specific pattern |
| `SBL` | Structural Blocked | In-scope but technically blocked (semantic, image-embedded, cross-entry) |
| `SEM` | Semantic/Editorial | Out of scope — content/meaning issue |
| `PRF` | Preference/Style | Out of scope — reviewer preference without NJIT guideline backing |
| `AMB` | Ambiguous | Insufficient information to classify |

Coverage rate = (SIM + SIP) / (SIM + SIP + SMI + SBL) — excludes out-of-scope rows.

---

## 4. Data source

The 52 coverage rows are **estimated from the category-level breakdown** documented in
`docs/evaluation/post_p080_docx_pdf_overlap_evaluation.md`. The P080 DOCX extractor produced
per-comment metadata (IDs, dates, char counts, truncated previews) stored in the private
gitignored `data/evaluation/generated/` directory. The committed coverage table derives row
counts and taxonomy classifications from those categories; individual comment text, dates, and
page assignments are not committed.

Comment IDs are deterministic SHA-256 prefixes of `(doc_alias, comment_category, ordinal)`.
They are not reversible to the original DOCX comment data.

---

## 5. Five-gate evidence policy

A structural gap may become a future detector only if it passes all five gates:

1. **Guideline reference:** the pattern is backed by an explicit NJIT guideline requirement
   (Q-rule or formatting spec section).
2. **Multi-document occurrence:** at least 3 dissertation files show this pattern (not just
   one or two outliers).
3. **Heuristic detectability:** the pattern is detectable from PDF text-layer metadata alone
   (no OCR, no semantic parsing, no cross-entry comparison).
4. **False-positive estimate:** a hand-check of 5 clean-baseline pages or documents shows
   ≤1 false-positive trigger.
5. **Actionability:** a student can fix the issue based on the advisory without re-reading
   their entire dissertation.

Any gap that fails a gate is documented in `docs/planning/ef_comment_candidate_rules.md`
with the blocking gate noted.

---

## 6. Privacy constraints

- No raw reviewer text in any committed file.
- No student names, private file paths, or dissertation body text.
- `comment_summary` fields are analyst-normalized structural descriptions, not quoted
  reviewer language.
- `doc_alias` values do not contain student names or raw filenames.
- `comment_id` values are deterministic but not reversible to original DOCX comment IDs.
