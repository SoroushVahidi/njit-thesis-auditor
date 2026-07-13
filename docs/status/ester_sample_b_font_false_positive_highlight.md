# Ester Sample B Font False Positive / Highlight Fix

**Recorded:** 2026-07-09
**Branch:** `fix/ester-sample-b-font-false-positive-highlight`
**Baseline:** `origin/main` @ `c4d4065` (PR #492 + PR #493 merged)
**Worktree:** `/home/soroush/njit-thesis-auditor/njit-thesis-auditor-clean-worktrees/fix-ester-sample-b-font-false-positive-highlight`

## Ester's concern

Sample B page 5: the auditor highlighted text that appears to be correct-size
text, and the feedback was incorrect. Ester's own notes name **P063**.

## Which rule actually reproduces on Sample B page 5: P026, not P063

- **P063** (`pdf_appendix_body_headings.py`) checks appendix heading label
  formatting (e.g. "Appendix A" letter-sequence conventions in body-page
  headings). It does not evaluate font size/family at all, and it does not
  fire anywhere on the built-in Sample B fixture (`ester_sample_b`) — page 5
  has no appendix heading content.
- **P026** (`pdf_font_compliance.py`, `possible_body_font_size_issue`) is the
  rule that actually reproduces on page 5, both before this fix and in the
  prior repo audit (`docs/status/ester_sample_b_feedback_audit.md`, item
  SB-16). This is consistent with what Ester described: an incorrect
  font-related warning with a highlight on text that looks like it's already
  the right size.
- No mapping/rule-ID rename was needed or applied. P026 is the correct rule
  identity for this finding; P063 was never involved. The document title kept
  "P063" only because that's how Ester referred to it informally — internally
  the reproduced defect has always been P026.

## Root cause

Page 5 of the Sample B fixture is the **Approval Page** — a committee
signature block (advisor/committee member names, titles, and "Date" lines),
not body prose. NJIT's own Approval Page convention (and this document's
LaTeX template) legitimately renders that block in a smaller font (measured
10.9pt, `CMR10`) than the 12pt body-text size the P026 rule enforces
elsewhere.

`pdf_font_compliance.py` already has a page-skip gate,
`_page_has_named_heading`, meant to exempt exactly this kind of front-matter
page (Approval Page, Biographical Sketch, Acknowledgements, Table of
Contents, References, etc.) from body-font-size measurement — the same
design already used to exempt those pages from other content-shape rules.

The gate failed here because of a text-extraction artifact: this PDF's
heading line for "APPROVAL PAGE" extracts with **no space** between the
words (`"APPROVALPAGE"`), so the gate's exact-match check against
`EXPECTED_HEADINGS` never matched, the page was treated as an ordinary body
page, and 66/72 measured spans (the entire signature block) were flagged as
a 10.9pt-vs-12pt size violation. The highlighted bbox pointed at the first
violating span — the correctly-sized "Dr." on the first committee line —
which is exactly the "highlighted text that appears to be correct-size text"
Ester described.

This exact concatenated-heading extraction pattern was already known and
already fixed once, locally, inside `pdf_frontmatter_headings.py` (P038's
`_P038_CONCATENATED_HEADING_VARIANTS`) — but that fix was deliberately scoped
to P038 only and never reused by P026's independent page-skip gate.

## Bug category

Applying a body-font rule to exempt/front-matter text (the page should have
been exempted the same way Acknowledgements/Biographical Sketch/TOC/etc.
already are; it wasn't, purely because of a heading-text-extraction quirk).

## Fix

`src/njit_auditor/rules/pdf_font_compliance.py`:

- Added a rule-local `_CONCATENATED_HEADING_VARIANTS` map (mirroring the
  existing P038 pattern for the same four headings) and taught
  `_page_has_named_heading` to also match a line's concatenated form against
  it.
- No change to `EXPECTED_HEADINGS`, `FRONTMATTER_HEADING_VARIANTS`, or the
  P038 variant map — kept rule-local, matching the existing deliberate
  separation between P038 presence-detection and other rules' page-skip
  gates.
- No change to font-size tolerance, font-family acceptance lists, or
  candidate-span thresholds. Legitimate font checking is unchanged: a real
  10.9pt body-text page without a recognized front-matter heading still
  flags (see regression tests below).

## Before / after Sample B behavior

| | Before | After |
|---|---|---|
| P026 findings on Sample B | 1 (page 5, `possible_body_font_size_issue`, 10.9pt) | 0 |
| Page 5 findings overall | P026 (false positive) + 3× P012 (annotation detection, unrelated) | 3× P012 only |
| Highlight shown for the false positive | Yes — "Dr." on the first committee-member line (correct-size text) | N/A — no finding, no highlight |

Verified other Sample B front-matter pages with the same concatenated-heading
extraction pattern (Biographical Sketch page 6, Table of Contents pages
10–12) do not currently emit any P026 finding either before or after this
fix — the fix removes latent risk on those pages without changing observed
behavior on this fixture.

## Tests added

- `tests/test_ester_sample_a_correctness.py::test_ester_sample_b_p026_page5_approval_page_font_false_positive_resolved`
  — real Sample B fixture regression: page 5 has zero P026 findings.
- `tests/test_pdf_rules.py::test_p026_approval_page_concatenated_heading_signature_block_not_flagged`
  — synthetic Approval Page with concatenated heading + correct-size-for-that-page-type signature block: not flagged.
- `tests/test_pdf_rules.py::test_p026_biographical_sketch_concatenated_heading_not_flagged`
  — same pattern for a second concatenated heading in the fix's variant map.
- `tests/test_pdf_rules.py::test_p026_body_10_9pt_without_named_heading_still_flagged`
  — the exact real-document font size (10.9pt) on an ordinary body page with no front-matter heading is still flagged.
- `tests/test_pdf_rules.py::test_p026_concatenated_heading_that_is_not_a_known_variant_still_flagged`
  — a concatenated line that isn't a curated heading variant does not accidentally exempt the page.
- `tests/test_pdf_rules.py::test_p026_highlight_targets_offending_span_not_correct_text`
  — for a legitimate finding, the highlighted bbox is a wrong-size line, never a correct-size line on the same page.

## Test results

```
PYTHONPATH=<worktree> .../.venv/bin/python -m ruff check .
  All checks passed!

PYTHONPATH=<worktree> .../.venv/bin/python -m pytest -q \
  tests/test_ester_sample_a_correctness.py \
  tests/test_pdf_rules.py -k 'font or p026 or p063'
  35 passed

PYTHONPATH=<worktree> .../.venv/bin/python -m pytest -q
  2704 passed
```

## Deferred / out of scope

- **PR #483** (`audit/ester-sample-b-feedback`, docs-only audit doc) — not
  modified, not merged, no conflict/supersession decision made here. Out of
  scope per task instructions.
- P011/P019/P015/P020/P023/P016/P038/P051 Sample B items from the prior audit
  (`docs/status/ester_sample_b_feedback_audit.md`) — unrelated to this font
  fix; P011 (PR #493) and P019 (PR #492) are already merged separately.
