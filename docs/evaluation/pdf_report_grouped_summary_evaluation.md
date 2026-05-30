# PDF Report Grouped Summary Evaluation

## Purpose

The PDF auditor (P011–P026) can produce hundreds of findings on a single document,
especially for rules designed as high-volume candidate detectors (P013) or
per-page compliance checks (P026). This makes raw reports hard to triage quickly.

A grouped summary section was added to both JSON and Markdown reports to allow
Graduate Studies reviewers to quickly see which rules dominated, which pages were
affected, and what the dominant issue types were — without scrolling through
hundreds of raw findings.

Raw findings are fully preserved; the grouped summary is additive.

---

## Implementation

### JSON report: new `grouped_summary` field

The `grouped_summary` key is added at the top level of every JSON report alongside
the existing `metadata` and `findings` keys.

```
{
  "metadata": { ... },
  "grouped_summary": {
    "high_volume_rules": [ ... ],
    "by_rule_issue_type": { ... }
  },
  "findings": [ ... ]
}
```

**`high_volume_rules`**: list of per-rule summary objects for rules with ≥5 findings.  
Each entry includes:
- `rule_id`, `count`, `category`
- `issue_type_counts` — counts by `issue_type` detail value
- `affected_page_count`, `affected_pages_compact` — compact page-range string
- `observed_summary_sample` — top observed_summary values (if present in details)

**`by_rule_issue_type`**: complete cross-tabulation of all rules × issue_type pairs,
including rules below the high-volume threshold.

### Markdown report: new "Repeated Findings Summary" section

A table is inserted between the "Counts by Category" section and "Findings by Rule":

```
## Repeated Findings Summary

Rules with 5+ findings grouped for triage. Raw findings are listed below.
All findings are heuristic warnings requiring manual review.

| Rule  | Count | Category          | Pages | Top Issue Types |
|-------|------:|-------------------|------:|-----------------|
| P026  |   117 | font_format       |   117 | possible_body_font_family_issue×117 (Georgia, Arial) |
| P013  |   149 | page_numbering    |   132 | (no issue_type)×149 |
| P011  |   150 | margin_or_overflow|   124 | (no issue_type)×150 |
...
```

The section is omitted entirely when no rule reaches the threshold (≥5 findings).

---

## Evaluation on EF PDFs

Evaluated on `Yin_H_4th_Review_with_EF_comments_compressed.pdf` (137 pages,
the highest-finding PDF in the dataset).

**Total findings:** 463

**High-volume rules identified by grouped summary (6 of 16 active rules):**

| Rule | Count | Pages | Top Issue Types |
|------|------:|------:|-----------------|
| P011 | 150 | 124 | (no issue_type; per-instance margin candidates) |
| P013 | 149 | 132 | (no issue_type; page-number candidates globally) |
| P026 | 117 | 117 | possible_body_font_family_issue×117; observed: Georgia/Arial/Cambria |
| P019 | 25 | 11 | multiple_page_numbers×10, mixed_numbering_style×9, inconsistent_position×4, sequence_gap×2 |
| P024 | 12 | 3 | list_of_tables_title_case×8, unexpected_terminal_punctuation×2, toc_level_capitalization×1 |
| P014 | 10 | 10 | (no issue_type; named heading style warnings) |

**Compact page ranges** correctly identify clusters:
- P026: `2, 7, 9-10, 19-45, 47-51, 54-59, 61-131, 134-137` — nearly every body page
- P013: `6-137` — continuous across the full body
- P011: `1-2, 6-7, 9-13, ..., (124 pages total)` — truncated at 8 ranges

**Rules below high-volume threshold (not in summary):** P015, P016, P017, P018, P020, P021, P022, P023, P025 — each with 0–4 findings.

---

## Observations

**P026 grouping is the primary use case:** With 117 findings (one per body page), the
raw finding list is overwhelming. The grouped summary immediately surfaces:
- Total count and page range
- That all findings are `possible_body_font_family_issue`
- That Georgia, Arial, Cambria are the dominant fonts
- That no size warnings fired (0 `possible_body_font_size_issue`)

**P013 grouping clarifies intent:** P013 is a candidate detector that fires on every
page with a number-like token in the top/bottom zone. The summary shows 149 candidates
across 132 pages, making it clear this is systematic, not an error per page.

**P019 issue_type breakdown is useful:** Mixed numbering style (9 instances) and
multiple page numbers on one page (10 instances) are distinct actionable issues —
the grouped summary surfaces this without requiring the reviewer to read all 25 findings.

---

## Privacy Note

- No dissertation body text was read, quoted, or included in this document.
- The generated full JSON/Markdown reports are stored under
  `data/evaluation/generated/report_grouping/` which is gitignored.
- Only aggregate counts and page ranges are documented here.
