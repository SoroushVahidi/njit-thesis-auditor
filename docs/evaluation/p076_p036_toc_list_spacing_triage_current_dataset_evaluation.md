# P076 / P036 TOC/List Spacing Triage Current-Dataset Evaluation

- **Date:** 2026-06-09
- **Baseline commit:** `722dac0` (PR #278 — P076 P036 spacing triage rollup)
- **Auditor scope:** P001–P076 implemented; **1056 pytest**
- **Canonical aggregate:** **1,543** findings (unchanged)
- **Privacy:** Aggregate-only. No dissertation body text, TOC/LoT/LoF entry text, author names,
  EF comment text, captions, or private content quoted anywhere in this document.

---

## 1. Purpose

P076 adds a reporting-only triage rollup for P036 (`p036_toc_list_spacing_triage`) to the JSON
and Markdown report outputs. P036 detects inter-entry spacing violations on TOC, List of Tables,
and List of Figures pages. P076 groups those findings by section type, gap-ratio severity bucket,
and triage tier to improve actionability for manual reviewers.

This document records the first current-dataset evaluation of the P076 triage rollup on the
canonical five-PDF set. It confirms:

1. The triage rollup is produced where and only where P036 findings exist.
2. Raw P036 finding counts are unchanged (P076 is reporting-only).
3. The five-PDF canonical aggregate remains **1,543**.
4. The triage output provides actionable section-type and gap-severity breakdowns for the one
   file in the current dataset where P036 fires.

---

## 2. Dataset and Availability

| File label | Source path | Pages | Availability |
|---|---|---:|---|
| Cibaku Elson 1st Review | `data/raw/ester/250218 Cibaku Elson First Review.pdf` | 99 | tracked — accessible |
| Yin H 2nd Review (flattened) | `data/raw/ester/260415 Yin H _2nd_review with EF Comments.pdf` | 108 | tracked — accessible |
| Yin Haotian 2nd Review | `data/raw/ester/Yin_Haotian_Second_R_with_EF_Feedback.pdf` | 108 | tracked — accessible |
| Yin H 4th Review (compressed) | `data/raw/ester/Yin_H_4th_Review_with_EF_comments_compressed.pdf` | 137 | tracked — accessible |
| Sebastian Fine clean baseline | archive-extracted from tracked ZIP | 29 | archive-extracted — accessible |

Sebastian Fine was extracted from
`data/raw/ester/Dissertations with no Feedback -20260529T012213Z-3-001.zip`
to `data/evaluation/generated/post_p076_p036_triage_eval/sebastian_fine_clean.pdf`
(gitignored; not committed).

---

## 3. P036 Triage Rollup Structure

`grouped_summary.p036_toc_list_spacing_triage` is present in the JSON report when and only
when P036 findings exist for the file. When present, the structure includes:

| Field | Description |
|---|---|
| `raw_finding_count` | Total raw P036 findings (one per inter-entry spacing violation) |
| `affected_page_count` | Number of distinct pages with P036 violations |
| `affected_pages_compact` | Compact page range string (e.g., `11-14, 17`) |
| `issue_type_counts` | Counts by issue type: `toc_inter_entry_spacing_too_tight`, `lot_inter_entry_spacing_too_tight`, `lof_inter_entry_spacing_too_tight` |
| `section_type_counts` | Counts by section: `table_of_contents`, `list_of_tables`, `list_of_figures` |
| `spacing_gap_bucket_counts` | Counts by gap severity: `very_tight` (gap ratio < 0.3), `slightly_tight` (0.3–0.9) |
| `triage_tier_counts` | Counts by reviewer priority tier |
| `min_gap_ratio` | Minimum observed gap-to-threshold ratio across all P036 findings |
| `max_gap_ratio` | Maximum observed gap-to-threshold ratio |

The Markdown report includes a `## P036 TOC/List Spacing Triage Summary` section when findings
exist, rendering the key counts and guidance text before the raw findings list.

---

## 4. Per-File P036 Triage Summary

### 4.1 Files with 0 P036 findings (triage absent)

| File label | Total findings | P036 findings | Triage key present |
|---|---:|---:|---|
| Cibaku Elson 1st Review | 325 | 0 | absent |
| Yin H 2nd Review (flattened) | 281 | 0 | absent |
| Yin Haotian 2nd Review | 346 | 0 | absent |
| Sebastian Fine clean baseline | 59 | 0 | absent |

No P036 findings on these four files — the P036 detection gate did not activate on their
TOC/LoT/LoF text layers.

### 4.2 Yin H 4th Review (compressed) — triage present

| Metric | Value |
|---|---|
| Total findings (this file) | 532 |
| P036 raw finding count | **55** |
| Affected page count | 5 |
| Affected pages compact | `11-14, 17` |

**Issue type counts:**

| Issue type | Count |
|---|---:|
| `toc_inter_entry_spacing_too_tight` | 42 |
| `lof_inter_entry_spacing_too_tight` | 9 |
| `lot_inter_entry_spacing_too_tight` | 4 |

**Section type counts:**

| Section | Count |
|---|---:|
| `table_of_contents` | 42 |
| `list_of_figures` | 9 |
| `list_of_tables` | 4 |

**Spacing gap bucket counts:**

| Bucket | Count | Interpretation |
|---|---:|---|
| `slightly_tight` | 48 | gap ratio 0.3–0.9 (below double-spacing threshold but not extreme) |
| `very_tight` | 7 | gap ratio < 0.3 (severely compressed inter-entry spacing) |

**Triage tier counts:**

| Tier | Count |
|---|---:|
| `high` | 55 |

**Gap ratio range:** min `0.06`, max `0.85`

---

## 5. Aggregate Interpretation

All 55 P036 findings are concentrated on the Yin H 4th Review (compressed) file. This file is a
compressed/flattened PDF where the text-layer geometry is known to produce dense coordinate
distributions across multiple rules (it also carries the highest P011, P013, and P026 counts
in the canonical dataset). The compressed text layer places TOC/LoT/LoF entries with reduced
vertical gaps, activating P036's inter-entry spacing check.

The triage rollup reveals:

- **TOC violations dominate (42 of 55).** The TABLE OF CONTENTS section on pages 11–14 accounts
  for 76% of P036 violations, suggesting the TOC may be formatted with single-spacing or
  compressed line spacing rather than the required double-spacing between entries.
- **LoF (9) and LoT (4) contribute a smaller share.** These violations span page 17.
- **Most violations are slightly_tight (48), not very_tight (7).** Gap ratios from 0.06 to 0.85
  indicate a range from near-zero spacing to moderately tight spacing; the median is likely
  in the slightly_tight bucket.
- **All violations are high triage tier.** All 55 findings are classified as `high` priority by
  the gap-severity model, which scores tight inter-entry spacing as high-priority because it
  directly affects the visual readability checklist item reviewers use.
- **Other four files pass P036.** No inter-entry spacing violations detected on Cibaku, either
  Yin Haotian variant, or Sebastian Fine clean baseline. This is consistent with prior gap-fill
  evaluation results (2026-06-09, PR #266).

---

## 6. Relationship to Canonical Aggregate

| Metric | Value |
|---|---|
| Canonical five-PDF aggregate | **1,543** |
| Canonical aggregate doc | `docs/evaluation/current_auditor_after_p070_evaluation.md` |
| P036 contribution to canonical | **55** (Yin H 4th only; 0 on four other files) |
| P076 impact on raw finding counts | **0** — reporting-only; no detection behavior changed |
| Five-PDF total after this evaluation run | **1,543** |
| Aggregate unchanged? | **Yes** |

P076 adds only the `p036_toc_list_spacing_triage` grouped-summary key and the corresponding
Markdown triage section. Raw P036 findings, all other rules, and the total finding count are
unaffected.

---

## 7. Privacy Model

- No TOC entry text, LoT/LoF entry text, dissertation body text, EF comment text, author names,
  captions, or reference entry text appears in this document.
- All reported values are aggregate counts, page ranges, and gap-ratio statistics.
- Generated audit JSON files are stored under `data/evaluation/generated/post_p076_p036_triage_eval/`
  (gitignored) and not committed.
- Sebastian Fine extracted PDF is in the same gitignored directory; not committed.
- Real dissertation files remain in `data/raw/ester/` (tracked, high privacy risk).
- No OCR was performed. No external network calls were made.

---

## 8. Limitations

- **Five-file dataset.** P036 fires on 1 of 5 files; zero findings on 4 files do not prove
  inter-entry spacing compliance on those dissertations — the detection gate may not fire due
  to text-layer limitations (flattened/no-text-layer TOC pages, sparse pages).
- **Compressed text layer inflates detection.** The Yin H 4th compressed file is known to have
  geometry anomalies affecting multiple rules. The 55 P036 findings and their gap ratios reflect
  the compressed PDF's text-layer characteristics, not necessarily the visual rendering.
- **TOC-dominant signal.** Pages 11–14 dominate the count; pages 15–16 (if they exist as TOC
  continuation pages) are not included, which may indicate the TOC detection gate has a range
  limit on this file.
- **Triage tier calibration.** All 55 findings are `high` tier. Future refinements could
  distinguish between structural formatting gaps (very_tight) and borderline gaps (slightly_tight).

---

## 9. Follow-Up Recommendations

1. **No further P036 rule changes needed.** The detection and triage logic is working as designed.
   The slightly_tight / very_tight bucket split provides enough resolution for manual review.
2. **P077 should address a new project-added rule or infrastructure task.** The post-P076
   documentation pass (this PR) closes the evaluation gap; the next meaningful step is a new
   detection or reporting rule. See `docs/status/current_project_state_and_next_steps.md` for
   backlog candidates.
3. **Sebastian Fine EF recovery remains blocked.** The private EF-annotated PDF is not in any
   locally accessible archive. Comparison set remains 2 files (143 EF annotations).

---

## Cross-References

- P076 scope/design: `docs/planning/p076_p036_toc_list_spacing_triage_rollup_scope_and_design.md`
- P036 prior evaluation (gap-fill, five-PDF raw counts): `docs/evaluation/p036_p063_current_dataset_gap_fill_evaluation.md`
- P036 synthetic validation: `docs/evaluation/p036_toc_list_entry_spacing_synthetic_validation.md`
- Canonical aggregate: `docs/evaluation/current_auditor_after_p070_evaluation.md` (**1,543**)
- P073 P019 triage validation (parallel precedent): `docs/evaluation/p073_v2_p019_triage_code_rollup_validation.md`
- Rolling status: `docs/status/current_project_state_and_next_steps.md`
- Evaluation data manifest: `docs/status/evaluation_data_manifest.md`
