# P037 Synthetic Validation — Section-Anchored Front-Matter Roman Numerals

- **Date:** 2026-06-02
- **Rule:** P037 — PDF front-matter section-anchored Roman numerals
- **Module:** `src/njit_auditor/rules/pdf_roman_section_anchors.py`
- **Test file:** `tests/test_pdf_rules.py` (12 P037 tests)
- **Validation type:** Synthetic only — no evaluation PDFs available in workspace

---

## Scope

P037 checks that named front-matter section pages carry the expected lowercase Roman numerals
per the NJIT dissertation template:

| Section | Expected value |
|---------|:--------------:|
| BIOGRAPHICAL SKETCH | iv (4) |
| DEDICATION (optional) | v (5) |
| ACKNOWLEDGEMENTS | vi (6) |
| TABLE OF CONTENTS | vii (7) |
| LIST OF TABLES | viii (8) |

The rule is gated on detecting a BIOGRAPHICAL SKETCH heading. If no such heading is found,
P037 emits nothing (conservative). DEDICATION is optional: if the heading is absent,
the template slot (v) is still counted for subsequent section expected values.

---

## Synthetic Test Results

| Test | Fixture | Expected behavior | Result |
|------|---------|-------------------|--------|
| Bio sketch at iv | Bio=iv, Ack=vi, TOC=vii, Chapter | No finding | ✅ Pass |
| Bio sketch at v (wrong) | Bio=v, Chapter | `roman_bio_sketch_not_iv` on bio page | ✅ Pass |
| Globally offset sequence (bio=v,ack=vii) | Bio=v, Ack=vii, TOC=viii, Chapter | `roman_bio_sketch_not_iv` | ✅ Pass |
| Dedication absent, Ack=vi | Bio=iv, Ack=vi, TOC=vii, LOT=viii, Chapter | No finding (v slot counted) | ✅ Pass |
| Dedication present, correct sequence | Bio=iv, Ded=v, Ack=vi, TOC=vii, Chapter | No finding | ✅ Pass |
| Dedication present, wrong numeral | Bio=iv, Ded=vi (should be v), Chapter | `roman_section_wrong_value` at dedication | ✅ Pass |
| TOC at wrong value | Bio=iv, Ack=vi, TOC=ix, Chapter | `roman_section_wrong_value` at TOC; expected vii | ✅ Pass |
| No BIOGRAPHICAL SKETCH heading | Ack=vi, TOC=vii, Chapter | No finding (gate condition) | ✅ Pass |
| Bio heading present, no candidate | Bio heading only, no page number, Chapter | No finding (skip) | ✅ Pass |
| Body page Roman numeral | Bio=iv, Chapter with Roman v | No finding on body page | ✅ Pass |
| Finding metadata privacy-safe | Bio=v (wrong) | Finding details: section_key, expected/observed numeral, page; no body text | ✅ Pass |
| CLI integration | Bio=v, Chapter → JSON report | P037 in output findings | ✅ Pass |

All 12 tests pass.

---

## Issue Types

| Issue type | Trigger |
|-----------|---------|
| `roman_bio_sketch_not_iv` | BIOGRAPHICAL SKETCH page has confident Roman candidate but value ≠ 4 |
| `roman_section_wrong_value` | Another section page has confident Roman candidate but value ≠ template expected |

---

## Privacy Notes

- All findings contain only: `page_number`, `section_key`, `issue_type`, `expected_roman`,
  `expected_value`, `observed_roman`, `observed_value`, `triage_tier`, `confidence`.
- No dissertation body text, section body content, author names, dedication prose, or
  biographical content is included in findings or this document.
- Synthetic fixture pages use placeholder headings only.

---

## Current-Dataset Evaluation

No current-dataset evaluation was run. Evaluation PDFs are unavailable in the workspace.
When evaluation PDFs become available, rerun locally into:

```
data/evaluation/generated/current_auditor_after_p037/
```

Do not commit generated outputs. Document aggregate P037 counts only in a future
`docs/evaluation/p037_current_dataset_evaluation.md`.

---

## Known Limitations

- DEDICATION is detected only when the heading text "DEDICATION" appears verbatim. A
  dedication page with no heading (or an alternate heading) is treated as absent, causing
  the slot to still be counted (v is reserved) — subsequent sections remain anchored to
  the fixed template values.
- Compressed PDFs with mis-extracted page-number coordinates may produce false negatives
  (candidate not found → skip) or false positives (wrong candidate picked).
- The rule assumes the NJIT template structure with bio sketch at page iv. Documents that
  deviate from this structure (e.g., alternate unnumbered interstitial pages) may produce
  spurious `roman_section_wrong_value` findings.
- LOF (List of Figures) is not included in P037 v1 (deferred per scope doc).
