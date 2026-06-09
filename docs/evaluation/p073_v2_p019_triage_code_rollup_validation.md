# P073 v2 — P019 Page-Numbering Triage Code Rollup Validation

- **Date:** 2026-06-09
- **Baseline commit:** `5448fa9` (PR #269)
- **P073 v1 triage doc:** `docs/evaluation/p073_p019_page_numbering_triage_rollup.md`
- **Scope:** Reporting/metadata enhancement only — no detection behavior changed

---

## 1. Summary

P073 v2 adds privacy-safe triage metadata to P019 page-numbering findings and wires a grouped
triage summary into JSON/Markdown reports. Raw P019 findings are not modified, suppressed, or
filtered. The canonical five-PDF aggregate remains **1,543**.

---

## 2. Implementation

### 2.1 Triage metadata on P019 findings

Added to every P019 finding in `check_pdf_page_number_sequence()` via a post-deduplication step
in `src/njit_auditor/rules/pdf_page_numbers.py`. Three new detail keys are attached:

| Detail key | Type | Description |
|---|---|---|
| `triage_tier` | `"high"` / `"medium"` / `"low"` | Reviewer priority signal |
| `p019_triage_category` | stable string slug | Finding sub-category |
| `triage_reason` | short string | Human-readable rationale |

### 2.2 Issue-type to triage-tier mapping

| issue_type | triage_tier | p019_triage_category |
|---|---|---|
| `sequence_gap` | `high` | `high_signal_sequence_gap` |
| `missing_page_number` | `high` | `high_signal_missing_page_number` |
| `mixed_numbering_style` | `medium` | `mixed_numbering_manual_review` |
| `multiple_page_numbers` | `medium` | `multiple_page_numbers_manual_review` |
| `inconsistent_position` | `low` | `position_inconsistency_artifact_suspected` |

Rationale for tier assignments matches P073 v1 cause-category classification:
- `sequence_gap` fires on all 5 files including clean baseline — highest-signal
- `missing_page_number` — confirmed structural gap; high actionability
- `mixed_numbering_style` — boundary detection not available; conservative medium
- `multiple_page_numbers` — may be artifact (EF annotation); medium pending context
- `inconsistent_position` — predominates on EF PDFs (artifact-likely); low

Far-boundary mixed-numbering refinement is **deferred** (requires boundary detection not
currently available without invasive changes).

### 2.3 Grouped summary function

`build_p019_page_numbering_triage_summary(findings)` added to
`src/njit_auditor/report_outputs.py`. Returns `None` when no P019 findings exist.

Summary fields:

| Field | Description |
|---|---|
| `total_findings` | P019 finding count |
| `by_issue_type` | counts by issue_type |
| `by_triage_tier` | counts by tier |
| `by_category` | counts by p019_triage_category |
| `high_priority_count` | high-tier count |
| `medium_priority_count` | medium-tier count |
| `low_priority_count` | low-tier count |
| `affected_pages_compact` | compact page range string |
| `review_guidance` | short reviewer guidance string |

### 2.4 JSON output

`build_grouped_summary()` now includes `p019_page_numbering_triage` when P019 findings exist.
Key is absent when no P019 findings are present.

### 2.5 Markdown output

`write_markdown_report()` now renders a `## P019 Page-Numbering Triage Summary` section
(after P012 and before Findings by Rule) for PDF audits. Section includes tier counts,
issue-type counts, and reviewer guidance. No dissertation text or candidate strings appear.

---

## 3. Tests

17 new tests added across two files:

**`tests/test_report_outputs.py`** (13 new tests):
- `test_p019_triage_absent_when_no_findings`
- `test_p019_triage_absent_when_no_p019_findings`
- `test_p019_sequence_gap_is_high_priority`
- `test_p019_missing_page_number_is_high_priority`
- `test_p019_multiple_page_numbers_is_medium_priority`
- `test_p019_inconsistent_position_is_low_priority`
- `test_p019_triage_groups_counts_correctly`
- `test_p019_triage_in_grouped_summary`
- `test_p019_triage_absent_in_grouped_summary_when_no_p019`
- `test_p019_raw_findings_preserved_in_json`
- `test_markdown_report_includes_p019_triage_section`
- `test_p019_triage_section_absent_when_no_p019`
- `test_all_five_triage_rollups_coexist`

**`tests/test_pdf_rules.py`** (4 new tests):
- `test_p019_sequence_gap_finding_has_triage_metadata`
- `test_p019_missing_page_number_finding_has_triage_metadata`
- `test_p019_inconsistent_position_finding_has_triage_metadata`
- `test_p019_raw_finding_count_unchanged_by_triage`

---

## 4. Validation

| Check | Result |
|---|---|
| `ruff check .` | clean |
| `mypy src` | 87 source files, no issues |
| `python -m pytest` | **1031 passed** (1014 baseline + 17 new) |
| P019 issue types preserved | ✅ unchanged |
| Canonical five-PDF aggregate | **1,543** — unchanged (triage is metadata-only) |
| Raw P019 finding count | unchanged (post-deduplication count identical) |

---

## 5. Deferred refinements

| Item | Status |
|---|---|
| Far-boundary mixed-numbering classification | Deferred — requires body-start boundary detection not currently available |
| EF-aware artifact classification for `multiple_page_numbers` | Deferred — file-level EF context not in current report pipeline |
| Possible future `inconsistent_position` suppression | **Permanently deferred** — raw findings must remain unchanged per P073 design constraint |

---

## 6. Privacy model

- No page text, candidate text, or dissertation content in any triage field
- Triage fields contain only stable string slugs, tier labels, and counts
- `affected_pages_compact` contains only page numbers (not page content)
- Generated outputs remain in gitignored `data/evaluation/generated/p073_p019_triage/`
