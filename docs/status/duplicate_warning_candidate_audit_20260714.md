# Duplicate-warning candidate audit (2026-07-14)

Privacy-safe aggregate analysis of offline duplicate candidates on built-in
evaluation samples after reduced PR #505 (`3d31ce9`).

**Tooling:** `njit_auditor.duplicate_candidate_analysis` +
`scripts/warning_duplicate_candidate_analysis.py`  
**Mode:** diagnostic only — no automatic suppress/merge.  
**Live server / port 8000:** untouched.

Machine-readable aggregates:
`~/overnight-njit-auditor-20260714/results/phase7a_duplicate_aggregates.json`
(not committed; `/results/` is gitignored).

## Method

For each available built-in sample ID (`ester_sample_a`…`d`):

1. Run the full PDF audit and build the same student-facing ReportView used by the web UI.
2. Analyze **visible** findings only.
3. Record geometric IoU candidates (different rule/issue_type, same page, IoU≥0.3)
   and shared normalized-wording candidates (different rule_id, same page).
4. Aggregate rule-pair counts, issue-type pair counts, and IoU buckets.
5. Do **not** record text, names, filenames, or dissertation snippets.

## Aggregate results

| Sample ID | Visible findings | Geometric candidates | Shared-wording candidates |
|---|---:|---:|---:|
| ester_sample_a | 23 | 0 | 0 |
| ester_sample_b | 39 | 0 | 0 |
| ester_sample_c | 38 | 0 | 0 |
| ester_sample_d | 210 | 10 | 3 |

### Geometric rule-pair totals (all samples)

| Rule pair | Count |
|---|---:|
| P029:wrong_page_number_sequence ↔ P037:wrong_page_number_sequence | 2 |
| P019:wrong_page_number_sequence ↔ P029:wrong_page_number_sequence | 1 |
| P011:margin_boundary_violation ↔ P018:missing_page_number | 1 |
| P018:inconsistent_hierarchy_indent ↔ P024:list_of_tables_title_case | 1 |
| P018:inconsistent_hierarchy_indent ↔ P046:lot_entry_number_column_misaligned | 1 |
| P024:list_of_tables_title_case ↔ P046:lot_entry_number_column_misaligned | 1 |
| P024:list_of_tables_title_case ↔ P024:unexpected_terminal_punctuation | 1 |
| P024:list_of_tables_title_case ↔ P053:lot_entry_has_terminal_period | 1 |
| P024:unexpected_terminal_punctuation ↔ P053:lot_entry_has_terminal_period | 1 |

Shared-wording candidates were a subset of the page-numbering family above
(P019/P029/P037 sequence pairs).

IoU buckets: all 10 geometric candidates were in **0.90–1.00** (near/exact overlap).

## Manual classification (code + privacy-safe metadata only)

| Candidate family | Classification | Notes |
|---|---|---|
| P019/P029/P037 `wrong_page_number_sequence` overlaps | **same underlying condition with different remediation / regime checks** | Complementary detectors across front-matter/body/roman anchors; not safe to auto-merge without Esther/product rules |
| P024 title-case ↔ P024/P053 terminal punctuation on LOT | **same location, different formatting properties** | Capitals vs terminal period are distinct student actions |
| P018 hierarchy indent ↔ P024/P046 LOT layout | **complementary checks** | Indent vs number-column vs title case can co-fire on one entry |
| P011 margin ↔ P018 missing page number | **likely coincidence / needs Esther judgment** | High IoU does not prove one root cause |
| P024 unexpected terminal punctuation ↔ P053 lot terminal period | **genuine duplicate (presentation family)** | Closest to a presentation-only overlap, but still not auto-suppressed here because ownership of LOT terminal-period messaging may be intentional dual coverage |

## Decision for this overnight pass

**No automatic suppress/merge and no presentation-only “fix” PR opened.**

Rationale: even the P024↔P053 terminal-period pair needs an explicit product decision about
which rule owns student-facing LOT punctuation. Other families are complementary or
require Esther judgment. Document only.

## Follow-ups (optional)

- Maintainer/Esther review of P019/P029/P037 overlap policy.
- Decide single owner for LOT terminal-period messaging (P024 vs P053) before any
  presentation merge.
- Re-run this aggregate after future detector changes; keep outputs under ignored
  `results/` with sample IDs only.
