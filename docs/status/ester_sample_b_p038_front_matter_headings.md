# Ester Sample B P038 Front-Matter Heading False Positive Fix

**Recorded:** 2026-07-09
**Branch:** `fix/ester-sample-b-p038-front-matter-headings`
**Base:** `main` @ `cd00498` (PR #488 merged)

## Scope

Narrow follow-up to `docs/status/ester_sample_b_feedback_audit.md` item SB-09.
Ester's Sample B feedback flagged one P038 problem:

- **Page 9** — the auditor flagged the ACKNOWLEDGEMENTS heading as a
  "heading phrase not exact" problem, even though (in Ester's judgment) the
  heading is correct. She also noted the auditor separately behaves as if a
  required ACKNOWLEDGEMENTS heading is missing with vague, document-level
  language, and that front matter should be analyzed page-by-page with
  specific remediation per page.

Out of scope (left for later, separate branches): P011, P019, P020, P023,
P026/P063 font false positives, and margin/page-numbering issues — per
`docs/status/ester_sample_b_feedback_audit.md`.

## Source of truth

The live Google Sheet ("NJIT Thesis Auditor Formatting Rules") and Gmail/Drive
were not accessible in this environment (same 401 / no-connector limitation
recorded in prior status docs). Used local mirrors instead:

- `data/specs/ester_q_matrix.json` — **Q036**: *"Does the Acknowledgements
  page display the exact word correctly formatted? The Acknowledgements page
  must display 'ACKNOWLEDGEMENTS' in all caps, bold, centered, and at the
  top."* Remediation: *"Format the heading 'ACKNOWLEDGEMENTS' correctly."*
- `docs/status/ester_sample_b_feedback_audit.md` (SB-09): *"Keep front-matter
  heading detection explicit and do not treat ACKNOWLEDGEMENTS as missing
  when the heading is present / variant-matched."*

`data/specs/ester_warning_wording_map.json` and
`data/specs/ester_p_rule_feedback.json` have no P038-keyed entry (P038 sits
outside Ester's originally mapped P011–P018/P042+ range), so no Column C/E
text existed to copy verbatim for this rule.

## Investigation

Reproduced on the real Sample B fixture
(`get_builtin_sample("ester_sample_b")` → `run_pdf_audit_full`). Exactly one
raw `P038` finding existed before the fix — **not** two conflicting findings
as the "also missing, document-level" framing in Ester's feedback might
suggest:

```
page: 9
issue_type: heading_phrase_not_exact
expected_heading: ACKNOWLEDGEMENTS
observed_heading_normalized: ACKNOWLEDGMENTS
```

### Root cause

Dumping page 9's raw text layer (`load_pdf_layout`) confirms the heading
literally reads `"ACKNOWLEDGMENTS"` — the standard American spelling, with
no missing middle "E" — and this is a genuine character-for-character match
to the PDF's real text, not a text-extraction artifact (unlike the
comma/space-gluing issues seen in prior Sample B fixes; intra-word characters
were not dropped here).

`src/njit_auditor/rules/pdf_frontmatter_headings.py` runs two checks:

1. **`required_heading_missing`** — a required heading (from `_REQUIRED_HEADINGS`)
   not found anywhere in the document. Presence is determined by
   `_p038_detected_heading_set`, which already treats `"ACKNOWLEDGMENTS"` as
   equivalent to `"ACKNOWLEDGEMENTS"` via the shared
   `FRONTMATTER_HEADING_VARIANTS` map (`pdf_frontmatter_heading_gate.py`) —
   so this check correctly did **not** fire for page 9. There was never a
   second, document-level "missing" finding alongside the page-9 finding on
   this document; Ester's framing describes what the *combination* of the
   page-9 phrase-mismatch wording and the rule's general "required heading"
   design reads like to a non-engineer reviewer, not two simultaneous findings.
2. **`heading_phrase_not_exact`** — reused that *same* shared, deliberately
   tolerant `FRONTMATTER_HEADING_VARIANTS` map to *also* flag the heading as
   a wording problem requiring correction. That map exists to let several
   *other* rules (P041, P044–P047, P065–P068, TOC/list detection) tolerantly
   locate the Acknowledgements section regardless of spelling — it was never
   meant to double as a list of "genuinely wrong, must-fix" phrasings. American
   English commonly drops the middle "e" in "acknowledgements"; both spellings
   are standard dictionary forms of the same word, not a formatting defect.
   Reusing the gate's acceptance list as an error list was the actual bug —
   confirmed by Ester's live review as a false positive.

## Fix

`src/njit_auditor/rules/pdf_frontmatter_headings.py`:

- Added `_P038_FLAGGED_PHRASE_VARIANTS: dict[str, str] = {}` — a new,
  P038-local map for phrase variants that are genuine wording defects worth
  flagging, deliberately separate from the shared, tolerant
  `FRONTMATTER_HEADING_VARIANTS` gate map. Documented why it starts empty:
  no currently-known variant is a confirmed defect (a concatenated/no-space
  heading is a layout artifact already handled separately by
  `_P038_CONCATENATED_HEADING_VARIANTS` for presence detection, not a
  different phrase).
- Check 2 (`heading_phrase_not_exact`) now reads from
  `_P038_FLAGGED_PHRASE_VARIANTS` instead of the shared
  `FRONTMATTER_HEADING_VARIANTS`, so it no longer flags NJIT-accepted
  equivalent spellings.
- Check 1 (`required_heading_missing`) and `_p038_detected_heading_set` are
  **unchanged** — they still use the shared `FRONTMATTER_HEADING_VARIANTS`
  map, so a heading present under an accepted spelling continues to count as
  present, and a genuinely absent required heading is still reported exactly
  as before. This directly guards against re-introducing a "present but also
  reported missing" conflict.
- Updated the function's docstring to state both gating rules explicitly.

No change to `FRONTMATTER_HEADING_VARIANTS` itself (kept untouched to avoid
any risk to the other rules that share it for section localization), and no
change to page-specific location/remediation wiring — `report_view.py`'s
existing P038 location-label logic (`"Front matter — required heading
missing: {expected}"` for document-level findings, `"{page_prefix} —
{expected} heading phrase"` for page-specific ones) and the existing
`_NO_HIGHLIGHT_DOC_REASON` text ("This finding is document-level and does
not correspond to a specific page or visual location.") already state
clearly, honestly, and without any page-specific claim exactly what kind of
finding is being shown; no change was needed there.

## Result

- Sample B page 9: zero `P038` findings — the accepted American spelling is
  no longer reported as a phrase mismatch, and was never reported as missing.
- A genuinely different missing required heading (e.g. BIOGRAPHICAL SKETCH)
  is still reported via `required_heading_missing`, unaffected
  (regression-tested).
- An accepted variant spelling and a different genuinely-missing heading in
  the same document produce no duplicated or conflicting findings for the
  same section (regression-tested).
- Correctly spelled canonical headings (`"ACKNOWLEDGEMENTS"`) continue to
  produce no findings (pre-existing coverage, unaffected).

## Files Changed

- `src/njit_auditor/rules/pdf_frontmatter_headings.py`
- `tests/test_pdf_rules.py`
- `tests/test_ester_sample_a_correctness.py`
- `docs/status/ester_sample_b_p038_front_matter_headings.md` (this file)

## Tests

Added:

- `test_p038_accepted_variant_and_missing_heading_do_not_conflict` — synthetic
  PDF: American spelling accepted (no finding at all) alongside a genuinely
  missing different heading (still reported); the two checks never conflict
  or duplicate.
- `test_ester_sample_b_p038_acknowledgements_page9_not_flagged` — real Sample
  B fixture: page 9 produces zero `P038` findings.

Updated (previously locked in the false-positive behavior; now assert the
corrected behavior):

- `test_p038_acknowledgments_variant_warns` →
  `test_p038_acknowledgments_american_spelling_accepted_no_finding` — the
  American spelling now produces no findings instead of asserting a phrase
  mismatch.
- `test_p038_finding_metadata_privacy_safe` — heading list changed to omit
  ACKNOWLEDGEMENTS entirely (still exercises `required_heading_missing`
  metadata privacy; the American-spelling case it previously used no longer
  produces any finding to check).
- `test_p038_cli_includes_rule` — same change, for the same reason.
- `test_ester_sample_b_p012_p038_visibility_stable` →
  `test_ester_sample_b_p012_visibility_stable` — dropped the `P038 == 1
  finding on page 9` assertion (that was locking in the false positive);
  P012 assertions unchanged. The corrected P038 expectation (zero findings)
  is covered by the new fixture-level test above.

Existing P038/front-matter/heading coverage not touched above continues to
pass unchanged (missing-heading checks for APPROVAL PAGE, BIOGRAPHICAL
SKETCH, TABLE OF CONTENTS; optional-heading non-flagging for DEDICATION,
LIST OF TABLES, LIST OF FIGURES; flattened-PDF no-finding gate).

Targeted:

```bash
/home/soroush/njit-thesis-auditor/main/.venv/bin/python -m ruff check .
PYTHONPATH=src /home/soroush/njit-thesis-auditor/main/.venv/bin/python -m pytest -q \
  tests/test_ester_sample_a_correctness.py \
  tests/test_pdf_rules.py -k 'p038 or front_matter or heading'
```

Full suite:

```bash
PYTHONPATH=src /home/soroush/njit-thesis-auditor/main/.venv/bin/python -m pytest -q
```

Result: 2683 passed (2681 pre-existing + 2 net new; 3 existing tests updated
in place), ruff clean.

## Deferred / Still Open

Per `docs/status/ester_sample_b_feedback_audit.md`:

- P011 margin false positives (pages 1, 24, 39).
- P019 highlight targeting + document-level numbering presentation.
- P063 font-formatting / highlight targeting (page 5).
- P020 table-title / heading-level specificity — resolved separately in
  PR #488.
- P023 spacing / figure-description exception handling — resolved separately
  in PR #487.
- Duplicate section presentation — resolved separately in PR #486.
- P051 category rename — resolved separately in PR #485.
