# Ester Email Alignment Audit

**Recorded:** 2026-07-08  
**Branch:** `fix/ester-email-alignment-audit`  
**Base:** `origin/main` / `HEAD` = `2f4b0d7` (`Fix Sample A P038 false positives from concatenated PDF heading text. (#480)`)

## Worktree state at resume

- This worktree is based on the **latest current `origin/main` commit**, not an older detached baseline. `HEAD`, `origin/main`, and the merge-base are all `2f4b0d7`.
- The worktree already included PR #479 / PR #480 era Ester presentation work on `main`.
- `docs/status/ester_email_alignment_audit.md` did **not** exist at resume.
- `docs/status/ester_student_facing_alignment_pass1.md` was **not** present in this worktree; the prior pass summary was inspected from the neighboring clean worktree copy for continuity.
- Existing modified files in the worktree at resume were unrelated raw/fixture artifacts under `data/raw/...` and `tests/fixtures/web_demo/...`; they were left untouched.

## What was already aligned before this pass

### PR #479 and earlier presentation work already on `main`

- `data/specs/ester_warning_wording_map.json` exists and is already wired into student-facing issue labels through `student_facing_issue_label()`.
- Main results flow already puts **Findings in page order** before **Findings by topic**.
- Main student-facing cards already use Ester-style yes/no titles where the wording map explicitly applies.
- P011 already uses Ester's stricter margin question including **tables and figures** and retains the contextual margin-fix improvements from the earlier presentation slice.
- P012 already avoids generic “problem” phrasing and keeps page-level vs. document-level annotation wording separate.
- P013 already presents page-number findings as bottom-position/manual-verification style guidance rather than raw candidate jargon on the main student-facing path.
- PR #480 already fixed the Sample A P038 concatenated-heading false positives; that remains part of the base for this audit pass.

### Earlier docs/tests already covering the above

- `tests/test_ester_wording_and_page_order.py`
- `tests/test_ester_rule_wording_pass1.py`
- `tests/test_issue_type_explanations.py`
- `tests/test_p012_document_summary_rollup.py`
- `tests/test_problem_numbers_and_page_actions.py`

## What this resumed pass fixed

This pass made one narrow presentation-layer consistency fix and documented the current state.

### Fix applied

- `src/njit_auditor/polished_comments.py`
  The suggested-fix fallback now prefers Ester's wording-map remediation (`Column E`) when:
  - there is no issue-type-specific override, and
  - there is no detector-provided/context-specific suggested fix already present.

### Why this was a real remaining gap

Before this change, mapped student-facing titles already came from Ester's wording map, but fallback suggested fixes still came from `project_added_rules.json`. That caused small but real source-of-truth drift on mapped rules such as:

- **P012**
  Map: `Resolve or delete all annotations`
  Catalog fallback: `Resolve or delete all annotations before final submission.`
- **P013**
  Map: `Set page numbers on the bottom of the page, centered and 0.5 inches from margin`
  Catalog fallback: `Set page numbers at the bottom center of the page, 0.5 inches from the bottom edge.`
- **P068**
  Map and catalog both matched intent, but the catalog carried extra advisory wording not sourced from the map.

The new fallback keeps detector/context-specific fixes when they exist, so prior presentation improvements are preserved:

- P011 contextual fixes still win when present.
- Internal rule IDs / issue types / problem anchors remain unchanged in JSON, Markdown, and developer-facing structures.
- No detector, threshold, highlight, Gemini, or external-service changes were introduced.

## Which parts of Ester's latest email are now satisfied

Based on the repo-available mirror material and prior pass notes, the following email-driven asks are now satisfied on `main` after this pass:

- **Column C yes/no questions are the primary student-facing titles where a high-confidence mapping exists.**
- **Column E remediation now acts as the fallback student-facing suggested fix where a mapping exists.**
- **Page-order review is the primary workflow; topic grouping is secondary.**
- **P011 uses Ester's margin wording/remediation baseline while preserving contextual detector-supplied fixes when available.**
- **P012 does not invent affected-page wording on page-level cards; only document summaries list affected pages.**
- **P013 uses the expected bottom-position wording on the student-facing path instead of exposing raw candidate terminology as the main label.**
- **PR #480's P038 concatenated-heading Sample A false-positive fix remains in place.**

## What remains deferred

These items still require detector, geometry/highlight, policy, or source-access work and were intentionally **not** changed here:

- P014 / P015 / P017 / P018 broader atomic presentation splits beyond what is already on `main`
- P011 table/figure image geometry and strictness calibration
- P013 / P019 / P028 / P029 remaining page-number false positives and detector-volume issues
- P015 / P044 highlight-target precision
- P020 / P027 heading-case correctness disagreements against Ester's manual review
- P021 / P026 policy-constant confirmation
- P051 detector correctness/advisory calibration
- Item-by-item Sample A comparison against the inaccessible Google Doc benchmark

## Detector/highlight work still needed for Ester-email parity

- **Detector work needed**
  P013 / P019 / P028 / P029 page-number noise, P015 / P044 paragraph targeting, P020 / P027 heading-case mismatches, P051 advisory accuracy, and any deeper P014 / P017 / P018 / P038 splitting beyond already-exposed issue types.
- **Highlight work needed**
  P011 non-text margin evidence, P015 / P044 paragraph-level targeting, and other rules where the wording is now aligned but the visual pinpointing remains coarse or absent.

## Validation in this pass

Targeted Ester/report/web regression run in the repo virtualenv:

```bash
/home/soroush/njit-thesis-auditor/main/.venv/bin/python -m pytest -q \
  tests/test_ester_wording_and_page_order.py \
  tests/test_problem_numbers_and_page_actions.py \
  tests/test_ester_rule_wording_pass1.py \
  tests/test_web_audit_warning_fixes_batch2.py \
  tests/test_issue_type_explanations.py \
  tests/test_p012_document_summary_rollup.py
```

Result: **132 passed**, 1 `StarletteDeprecationWarning`, 0 failures.

## Summary

- **Already aligned before resume:** PR #479 / #480 student-facing wording, page-order-first UI, and Sample A P038 concatenated-heading fix.
- **Fixed in this resumed pass:** fallback suggested fixes now honor Ester's wording map where available.
- **Still deferred:** detector/highlight/policy work only.
