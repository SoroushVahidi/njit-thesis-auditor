# P076 Scope and Design — P036 TOC/LoT/LoF Inter-Entry Spacing Triage Rollup

- **Date:** 2026-06-09
- **Baseline commit:** `f62df07` (PR #276 — non-inventory P075 policy and guard)
- **Scope:** reporting-only P036 triage rollup
- **Validation baseline:** **1045 pytest**; ruff clean; mypy 87 source files
- **Aggregate baseline:** canonical five-PDF total **1,543** (unchanged)
- **Type:** report-output refinement only; no detection behavior change

---

## 1. Problem Statement

P036 (`pdf_toc_list_entry_spacing.py`) currently contributes **55 findings** to the canonical
five-PDF dataset, making it one of the higher-volume PDF rules after the post-P070 aggregate
stabilized at **1,543** findings. Those findings are useful but noisy to review as raw per-page
warnings because they are emitted one entry-pair at a time with no compact rollup by section,
page range, or spacing severity.

The report pipeline already has dedicated JSON/Markdown triage rollups for:

- P011 margin/overflow
- P012 annotation/comment cleanup
- P013 page-number candidates
- P019 page-numbering triage (P073)
- P026 font compliance

P036 has no comparable rollup yet. P076 should close that gap by adding a privacy-safe,
reporting-only summary that helps reviewers identify where TOC/LoT/LoF spacing issues cluster,
without altering raw findings or detection thresholds.

---

## 2. Current P036 Behavior

### 2.1 Rule module and behavior

- **Rule ID:** `P036`
- **Module:** `src/njit_auditor/rules/pdf_toc_list_entry_spacing.py`
- **Purpose:** detect insufficient vertical spacing between distinct TOC, List of Tables, and
  List of Figures entries after wrapped internal continuation logic has already been handled by P032
- **Detection mode:** heuristic, PDF-layout only
- **Severity:** `warning`
- **No finding suppression:** every qualifying tight inter-entry pair is emitted as a raw finding

### 2.2 Issue types

P036 maps section type directly to issue type via `ISSUE_TYPE_BY_SECTION`:

- `table_of_contents` -> `toc_inter_entry_spacing_too_tight`
- `list_of_tables` -> `lot_inter_entry_spacing_too_tight`
- `list_of_figures` -> `lof_inter_entry_spacing_too_tight`

This means section/list type is derivable two ways:

1. directly from `details["section_type"]`
2. indirectly from the issue-type prefix (`toc_`, `lot_`, `lof_`)

Because the finding details already include `section_type`, no metadata enrichment is required for
P076. Issue-type prefix inference can remain a defensive fallback only.

### 2.3 Current detail fields on raw findings

Each P036 finding currently includes these privacy-safe detail keys:

- `page_number`
- `section_type`
- `issue_type`
- `entry_pair_index`
- `gap_points`
- `required_gap_points`
- `local_line_height_points`
- `gap_ratio`
- `triage_tier`
- `source_q_rule_ids`

Current semantics:

- `gap_points` is the observed vertical gap between the last line of one entry and the first line
  of the next entry
- `required_gap_points` is the minimum gap required by the conservative double-spacing heuristic
- `local_line_height_points` is the local line-height estimate used to normalize the gap
- `gap_ratio` is `gap_points / local_line_height_points`
- `triage_tier` is already assigned by the rule:
  - `high` when `gap_ratio < 1.1`
  - `medium` when `1.1 <= gap_ratio < 1.4`
  - `low` otherwise, though current emission logic means only sub-threshold values are emitted

### 2.4 Current-dataset evidence

From `docs/evaluation/p036_p063_current_dataset_gap_fill_evaluation.md`:

- **Total P036 findings:** `55`
- **Issue-type breakdown:**
  - `toc_inter_entry_spacing_too_tight`: `42`
  - `lof_inter_entry_spacing_too_tight`: `9`
  - `lot_inter_entry_spacing_too_tight`: `4`
- **File concentration:** all 55 findings occurred on **Yin H 4th (compressed)**

Implications for P076:

- a rollup is justified because the rule is high-volume enough to merit compact reviewer guidance
- section-level grouping is immediately useful because the dominant cluster is TOC-heavy
- the runtime report rollup should stay single-document in shape; cross-document concentration is
  useful for evaluation docs, but not a per-report JSON field

### 2.5 Privacy properties

P036 is already privacy-safe for rollup purposes because it exposes only:

- rule IDs
- issue types
- section/list labels
- page numbers
- numeric spacing metadata
- triage tier

It does **not** require quoting:

- TOC entry text
- chapter names
- figure/table titles
- captions
- dissertation body text

---

## 3. Proposed JSON Rollup

### 3.1 Integration point

Future implementation should add to `src/njit_auditor/report_outputs.py`:

- `P036_RULE_ID = "P036"`
- `build_p036_toc_list_spacing_triage_summary(findings)`
- grouped-summary key: `p036_toc_list_spacing_triage`

And wire it into `build_grouped_summary()` the same way P011/P012/P013/P019/P026 are added.

### 3.2 Proposed field set

Recommended JSON structure:

| Field | Meaning |
|---|---|
| `raw_finding_count` | Total P036 findings preserved in the report |
| `affected_page_count` | Unique page count with at least one P036 finding |
| `affected_pages_compact` | Compact page-range string via `compact_page_list()` |
| `issue_type_counts` | Counts by exact P036 issue type |
| `section_type_counts` | Counts by `table_of_contents`, `list_of_tables`, `list_of_figures`, optional `unknown` |
| `section_page_ranges` | Compact page ranges per section/list type |
| `triage_tier_counts` | Counts by `high` / `medium` / `low` from existing raw findings |
| `spacing_gap_bucket_counts` | Counts by numeric gap-ratio bucket for quick severity grouping |
| `min_gap_ratio` | Lowest observed `gap_ratio` across P036 findings |
| `max_gap_ratio` | Highest observed `gap_ratio` across P036 findings |
| `recommended_action` | Reviewer guidance sentence(s) |
| `triage_note` | Short statement that raw findings are preserved and summarized only |

### 3.3 Recommended spacing-gap buckets

Because numeric gap metadata already exists, P076 should use report-output logic only to bucket
the existing `gap_ratio` values. Proposed buckets:

- `severely_tight_lt_1_10`
- `tight_1_10_to_1_24`
- `near_threshold_1_25_to_1_39`
- `unknown`

These buckets are additive only. They do not change P036’s raw `triage_tier`, threshold, or
finding count.

### 3.4 JSON fields deliberately omitted

The runtime JSON rollup should **not** include:

- document/file labels from multi-document evaluation runs
- entry text
- chapter titles
- figure/table captions
- inferred remediation beyond generic list-spacing guidance

Cross-document concentration belongs in evaluation docs, not in a single-document report summary.

---

## 4. Proposed Markdown Section

### 4.1 Heading and placement

Recommended heading:

- `## P036 TOC/List Spacing Triage Summary`

Recommended placement in `write_markdown_report()`:

- after the grouped "Repeated Findings Summary"
- alongside the other dedicated triage sections
- before `## Findings by Rule`

A practical insertion point is after P019 or adjacent to the other formatting-heavy rollups.
Exact ordering is less important than keeping all triage sections together before raw findings.

### 4.2 Content shape

Recommended Markdown content:

1. brief explanatory paragraph:
   - reporting-only summary
   - raw findings unchanged
   - manual review still required
2. metric table:
   - raw finding count
   - affected pages
   - high / medium / low counts
3. issue type counts
4. section/list type counts
5. section page ranges
6. spacing-gap bucket counts
7. reviewer guidance
8. compact affected-page range note
9. final reminder that raw findings remain under `Findings by Rule -> P036`

### 4.3 Reviewer guidance content

Recommended guidance:

- high-volume clusters may indicate a systematic TOC/LoT/LoF spacing pattern rather than isolated defects
- review TOC pages first when `toc_inter_entry_spacing_too_tight` dominates
- then review LoF and LoT sections by compact page range
- on compressed PDFs, coordinate artifacts can exaggerate spacing anomalies, so spot-check severe clusters first

This guidance stays privacy-safe because it references only rule IDs, section labels, page ranges,
and numeric categories.

---

## 5. Proposed Implementation Shape

Future implementation should be scoped as:

1. Add `P036_RULE_ID = "P036"` in `report_outputs.py`
2. Add `build_p036_toc_list_spacing_triage_summary(findings)`
3. Include the new summary in `build_grouped_summary()` under:
   - `p036_toc_list_spacing_triage`
4. Add Markdown renderer:
   - `_format_p036_triage_section(grouped)`
5. Add it to `write_markdown_report()` with the other triage sections
6. Keep all raw P036 findings unchanged in JSON and Markdown findings lists

No change is needed in:

- `src/njit_auditor/rules/pdf_toc_list_entry_spacing.py`
- detection thresholds
- issue types
- canonical aggregate

---

## 6. Test Plan

P076 implementation should be covered with **synthetic findings only**. No real PDFs or generated
outputs are needed for the implementation PR.

### 6.1 Report-output tests

Add tests in `tests/test_report_outputs.py` for:

- summary absent when there are no findings
- summary absent when findings exist but none are P036
- JSON summary present when P036 findings exist
- raw finding count preserved
- issue type counts correct
- section/list type counts correct from `section_type`
- section page ranges compact correctly
- affected pages compact correctly
- triage tier counts correct
- spacing-gap bucket counts correct from numeric `gap_ratio`
- Markdown section rendered when P036 findings exist
- Markdown section absent when no P036 findings exist
- coexistence with P011/P012/P013/P019/P026 rollups

### 6.2 Detection-regression safety

Add one small regression assertion in `tests/test_pdf_rules.py` only if useful for documentation:

- confirm raw P036 finding details still contain `section_type`, `gap_ratio`, and `triage_tier`

This should remain minimal because P076 is a report-output task, not a rule task.

### 6.3 Privacy assertions

Synthetic tests should confirm that the rollup never requires:

- entry text
- headings
- titles
- captions
- body text

Tests should be constructed from synthetic `AuditFinding` instances with only numeric and
categorical detail keys.

---

## 7. Acceptance Criteria

P076 implementation is complete when:

- P036 raw findings are unchanged
- canonical aggregate remains **1,543** on the established baseline
- JSON report includes `p036_toc_list_spacing_triage` when P036 findings are present
- Markdown report includes a P036 triage section when P036 findings are present
- section/list type counts and page ranges are derived without quoting entry text
- spacing-gap buckets use existing numeric metadata only
- tests pass

---

## 8. Deferred / Non-Goals

P076 should **not** do any of the following:

- change P036 detection thresholds
- suppress P036 findings
- reclassify P036 warnings
- add new issue types
- rerun the current dataset as part of the scoping PR
- commit generated outputs
- inspect private data under `data/evaluation/private/`

Also deferred:

- any cross-document concentration field in runtime report JSON
- any attempt to infer true/false positives from document text
- any normalization of compressed-PDF coordinate artifacts beyond reviewer guidance

---

## 9. Recommended Implementation Branch

- `rules/p076-p036-triage-rollup`

The implementation PR should remain report-output focused and avoid touching detection logic.
