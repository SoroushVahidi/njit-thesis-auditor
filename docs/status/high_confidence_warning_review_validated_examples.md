# Validated High-Confidence Warning Examples — 2026-07-10

**Type:** Manual review record. No detector code, UI, tests, rule IDs, issue types,
canonical rule data, or thresholds were changed while producing this document.

**Baseline:** `main` @ `1fa468876052bf8fe7890b164e466d1be19fc6ea` (includes merged
PR #496, "Remove duplicate top problem summary table").

## Context

Soroush manually reviewed several high-confidence warnings in the live UI (via
screenshots) and confirmed each example is correct as presented — the right rule
fired, the highlight points at the right evidence, and the suggested fix is
specific and actionable. These are recorded here so they are not re-litigated in
a future audit pass, and so future review effort is spent on genuinely uncertain
cases instead.

## Validated examples

### 1. P025 — page 1 — Digital Commons wrapper page

- **Verdict:** Correct high-confidence notice.
- The flagged page is a Digital Commons cover/wrapper page, not a page of the
  actual NJIT thesis/dissertation body.
- The message correctly explains that this wrapper page is not part of NJIT
  thesis formatting and can otherwise cause misleading margin, annotation, or
  page-number warnings on that page.

### 2. P011 — page 8 — Approval page right margin (affected text: "Date")

- **Verdict:** Correct high-confidence warning.
- The highlight lands on the actual offending "Date" label near the right
  margin, not on an unrelated region of the page.
- The suggested fix is appropriately specific: move the Date label/signature/date
  line layout left, or shorten the line, rather than a generic "fix your margins"
  instruction.

### 3. P011 — page 74 — References left margin, ~9 pt over

- **Verdict:** Correct high-confidence warning.
- The highlight shows reference-list entries crossing the required left margin.
- The suggested fix appropriately points at references paragraph indentation /
  hanging-indent settings rather than a generic margin instruction.

## Conclusion

No detector or wording change is needed for any of these three examples — they
were reviewed and classified as correct / no-change-needed.

## Note for future high-confidence review

Future review time on high-confidence warnings should focus on examples where
one of the following is actually in question, rather than re-checking cases like
the three above:

- the warning itself is false (the rule fired but the condition doesn't hold),
- the highlight region is wrong (points at the wrong text, page, or area), or
- the wording (message or suggested fix) is confusing, too generic, or doesn't
  match what's actually highlighted.
