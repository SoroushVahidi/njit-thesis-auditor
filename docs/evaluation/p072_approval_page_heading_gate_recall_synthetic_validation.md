# P072 Synthetic Validation — Approval Page Heading-Gate Recall Refinement

- **Auditor scope:** P001–P072 implemented
- **Baseline commit:** `045e93b` (PR #261 — P072 scoped)
- **Implementation commit:** see PR for P072
- **Privacy:** Aggregate test counts only; no real names, committee text, approval-page prose, or private content

---

## 1. Purpose

P072 is an infrastructure companion to P068. It adds a **structural localization fallback**:
when the heading gate finds 0 "APPROVAL PAGE" matches in a document, P072 scans
front-matter/ambiguous pages for the distinctive combination of role-label phrases
(e.g., "Dissertation Advisor", "Committee Member") and sufficient body lines.
If exactly 1 such page is found, existing P068 structural checks run on that page.

**No new issue types.** Existing P068 types (`approval_page_advisor_role_label_missing`,
`approval_page_signature_blocks_sparse`) fire when checks reach a structurally detected page.

---

## 2. Relationship to P068 and P069

| Rule | Role |
|---|---|
| **P068** | Checks committee role-label and signature/date structural quality on a detected approval page; requires heading gate match |
| **P069** | Improved general front-matter heading variant recall (ACKNOWLEDGMENTS → ACKNOWLEDGEMENTS); did NOT add new APPROVAL PAGE matches on comparison PDFs |
| **P072** | Adds structural fallback localization when heading text is absent; extends P068 reach without new issue types |

---

## 3. Infrastructure-Only Nature

P072 is infrastructure-only. It:
- Adds `_find_structural_approval_page_candidate()` to `pdf_approval_page_committee_blocks.py`
- Adds `_all_usable_lines()` helper (all page lines, no heading boundary)
- Adds `detected_via` field to P068 finding `details` (`"heading_gate"` or `"structural_fallback"`)
- Modifies `check_pdf_approval_page_committee_blocks()` to try the fallback when the gate returns 0 matches
- Does **not** add standalone P072 findings, rule IDs, or new issue types

---

## 4. Q-Rule and Guideline Basis

| Q-rule | Paraphrased requirement | P072 classification |
|---|---|---|
| Q013 | APPROVAL PAGE heading in all caps, bold, centered, near top | **Recall refinement** — structural fallback when heading text absent |
| Q014 | Approval Page has no visible page number | Already covered by P022 — no P072 action |
| Q015–Q020 | Committee honorifics, rank ordering, NJIT/external ordering, affiliation completeness | **Manual-only / deferred** — not in P072 scope |

---

## 5. Synthetic Test Coverage

14 tests in `tests/test_p072_approval_page_heading_gate_recall.py`:

| # | Test | Behavior verified |
|---|---|---|
| 1 | `test_heading_gate_detected_via_field` | Canonical heading path still works; `detected_via = "heading_gate"` |
| 2 | `test_structural_fallback_complete_page_no_findings` | Fallback fires on complete structural page; no findings (structural quality meets gates) |
| 3 | `test_structural_fallback_sparse_indicators_emits_finding` | Fallback fires; sparse indicators → `approval_page_signature_blocks_sparse` |
| 4 | `test_structural_fallback_major_professor_advisor_role` | "Major Professor" accepted as advisor-role phrase in fallback path |
| 5 | `test_structural_fallback_no_role_labels_skipped` | No role-label phrases → fallback skips (returns []) |
| 6 | `test_structural_fallback_below_role_label_gate_skipped` | Only 1 role label (< `_MIN_ROLE_LABELS = 2`) → skipped |
| 7 | `test_structural_fallback_multiple_candidates_skipped` | 2 qualifying pages → ambiguous, skipped |
| 8 | `test_structural_fallback_image_only_skipped` | Empty `text_blocks` → skipped |
| 9 | `test_structural_fallback_sparse_text_layer_skipped` | < `_MIN_BODY_LINES = 4` usable lines → skipped |
| 10 | `test_body_prose_committee_mention_not_triggered` | Body prose mentioning "committee" without role-label phrases → not triggered |
| 11 | `test_heading_present_fallback_not_activated` | When heading gate finds a match, fallback does not additionally fire |
| 12 | `test_detected_via_structural_fallback_in_finding` | Fallback finding has `detected_via = "structural_fallback"` |
| 13 | `test_privacy_no_private_text_in_fallback_finding` | No names, signatures, or private content in finding details |
| 14 | `test_existing_p068_behavior_preserved` | Existing P068 heading-path issue types still emit correctly; `detected_via = "heading_gate"` |

**All 14 tests pass.**

---

## 6. Privacy Model

- All test PDFs use clearly fake placeholder strings: `"Placeholder Member Synthetic"`, `"Placeholder Advisor Synthetic"`, and sequentially numbered variants
- No real committee names, advisor names, institution names, signature text, date values, or dissertation content appear in any fixture
- `detected_via` field is `"heading_gate"` or `"structural_fallback"` — no private text
- All other finding fields are numeric/boolean counts (unchanged from P068)
- Test 13 explicitly verifies that placeholder strings do not leak into serialized finding details

---

## 7. Limitations

- **Image-only approval pages:** If the entire approval page is a scanned image (no machine-readable text layer), `_all_usable_lines()` returns empty and the fallback skips silently. This is the expected and correct behavior — no OCR is performed.
- **Partial text layers:** If some text is extractable but role-label phrases are not present (e.g., only committee names, no role labels), the fallback skips.
- **Multiple structural candidates:** If ≥2 front-matter pages qualify structurally (role labels present on multiple pages), the fallback skips to avoid false positives.
- **No semantic validation:** Q015–Q020 (honorific format, rank ordering, NJIT/external ordering, affiliation completeness) remain manual-only. P072 does not improve coverage of those requirements.
- **Localization recall ≠ compliance:** A successfully located approval page with no P068 findings does not prove the approval page is compliant — it proves only that the structural-block template patterns were present.

---

## 8. Relationship to Current-Dataset Evaluation

Current-dataset evaluation (`docs/evaluation/p072_approval_page_heading_gate_recall_current_dataset_evaluation.md`)
documents the before/after P068 reach on the five evaluation PDFs using aggregate-only counts.
That document is produced separately and links back here.
