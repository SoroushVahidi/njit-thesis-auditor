# Sample B Annotation Ground-Truth Forensics (privacy-safe summary)

**Recorded:** 2026-07-10 (original investigation in PR #504)  
**Sanitized for commit:** 2026-07-14 (PR #505 reduction after #508)  
**Internal sample key:** `ester_sample_b` only — no private filenames, student names,
annotation text, or dissertation body quotes are retained here.

## Purpose

Determine whether `ester_sample_b`'s native PDF annotations are a usable evaluation
ground-truth signal, whether detector logic is contaminated by annotation content,
and which general formatting defects remain uncaught.

## Privacy posture

- Runtime code must never read annotation `/Contents` for detection decisions.
- Production detectors must not reference Sample B, private filenames, authors,
  page numbers tied to a specific private sample, or exact private phrases.
- This committed summary keeps only aggregate counts and general conclusions.
- Private path metadata, SHA hashes, personal names, and redacted quote snippets
  from the original investigation notes were removed before reuse in the reduced
  #505 branch.

## Aggregate findings (safe to record)

- Dozens of native highlight/text annotations exist on the sample; a single
  reviewer author wrote them.
- Annotations are useful as a **coarse** ground-truth signal, not a complete
  benchmark: many marks repeat the same underlying defect, and some marks lack
  written comments.
- No evidence that production detectors condition on annotation text, author
  names, filenames, or Sample B identifiers.

## General detector gap closed (P015)

A reproducible false negative: incorrectly indented **continuation lines** after
displayed equations (or similar mid-paragraph breaks) were not flagged because
existing P015A/P015B checks did not cover that shape.

Fix (general heuristics only):

- Merge same-baseline, same-style line fragments before paragraph grouping.
- Emit `unexpected_indent_on_continuation_line` when a lowercase-led connector
  continuation is indented like a new paragraph.
- Protect genuine new paragraphs that open with mixed-case terms (`pH`, `mRNA`,
  `eBay`, …) or bracket/citation markers (`[12] …`, `(a) …`).

Synthetic regression coverage lives in `tests/test_p015_body_indent_ester_split.py`.

## Deferred / not acted on here

- Broader Sample B medium-confidence P011 pages needing Esther judgment.
- Using private annotation geometry as an automated training/eval harness in CI.
- Any sample-specific special-casing in production code (explicitly rejected).
