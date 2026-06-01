# Current Auditor Evaluation After P034 (Full P001–P034 Snapshot)

## 1. Purpose and auditor version

- **Date:** 2026-06-01
- **Baseline commit:** `3871d23`
- **Validation (PR #70 baseline):** ruff, mypy, **383 pytest** passed
- **Auditor scope:** P001–P034 implemented (PDF layout audit **P011–P034**; TeX audit P001–P010 not run here)
- **Supersedes (partial):** `docs/evaluation/current_auditor_after_p014_p029_evaluation.md` (P001–P029 only, commit `6a0baaf`)
- **Generated artifacts (gitignored):** `data/evaluation/generated/current_auditor_after_p034/`

This is the first **full five-PDF aggregate snapshot** with P030–P034 included. Reporting is
**aggregate-only**: file labels, rule IDs, page numbers, and counts only. No dissertation body
text, title text, author names, or committee names are quoted.

**Note (2026-06-01):** P013 reporting was later refined for triage/actionability
(`docs/evaluation/p013_reporting_actionability_refinement.md`). Raw P013 finding counts in
this snapshot are unchanged; JSON/Markdown reports gain `grouped_summary.p013_triage`.

**Reporting refresh (2026-06-01):** Full five-PDF reports were regenerated after PR #71 into
gitignored `data/evaluation/generated/current_auditor_after_p034_p013_triage/`; see
`docs/evaluation/current_auditor_after_p034_p013_triage_refresh.md`. Aggregate counts
(1,446 total, 461 P013) match this document; only report structure/actionability differs.

**P026 reporting refinement (2026-06-01):** P026 triage rollup added (`p026_font_triage`);
see `docs/evaluation/p026_reporting_actionability_refinement.md`. Post-change rerun:
gitignored `data/evaluation/generated/current_auditor_after_p034_p026_triage/`. Raw P026
count (415) unchanged.

**P011 reporting refinement (2026-06-01):** P011 triage rollup added (`p011_margin_triage`);
see `docs/evaluation/p011_reporting_actionability_refinement.md`. Post-change rerun:
gitignored `data/evaluation/generated/current_auditor_after_p034_p011_triage/`. Raw P011
count (169) unchanged.

**Canonical full-triage outputs (2026-06-01):** Use
`data/evaluation/generated/current_auditor_after_p034_p011_triage/` for the latest
five-PDF JSON/Markdown with P011+P013+P026 triage. See
`docs/evaluation/current_auditor_after_p034_full_triage_refresh.md`. Older folders
(`current_auditor_after_p034/`, `…_p013_triage/`, `…_p026_triage/`) are historical.

**Current toolchain validation (2026-06-01):** ruff, mypy, **404 pytest** — reaffirmed on latest `main` (`1607111`, PRs #76–#77). Five-PDF finding counts in this doc match eval baseline `00b9c2d` (unchanged).
(reporting triage does not change the aggregate counts in §3).

---

## 2. Dataset inventory

| File label | Availability | Pages | Notes |
|---|---|---:|---|
| Cibaku Elson 1st review | tracked | 99 | EF-commented; extractable highlights |
| Yin H 2nd review (flattened) | tracked | 108 | EF-commented; flattened comments |
| Yin Haotian 2nd review | tracked | 108 | EF-commented; extractable highlights |
| Yin H 4th review (compressed) | tracked | 137 | EF-commented; compressed/flattened |
| Sebastian Fine clean baseline | archive-extracted | 29 | From tracked ZIP; not committed as standalone PDF |

Skipped: rule-matrix XLSX; archive-only materials not verified locally.

---

## 3. Finding counts by file (P011–P034)

| Rule | Cibaku | Yin H 2nd flat | Yin Haotian 2nd | Yin H 4th comp | Sebastian Fine | Total |
|------|-------:|---------------:|----------------:|---------------:|---------------:|------:|
| P011 | 21 | 33 | 33 | 70 | 12 | 169 |
| P012 | 78 | — | 65 | — | — | 143 |
| P013 | 95 | 104 | 104 | 133 | 25 | 461 |
| P014 | — | — | — | — | — | 0 |
| P015 | 5 | 13 | 13 | 8 | — | 39 |
| P016 | 1 | 2 | 2 | 4 | 2 | 11 |
| P017 | — | — | — | 23 | 1 | 24 |
| P018 | — | — | — | 17 | 2 | 19 |
| P019 | 8 | 15 | 15 | 25 | 4 | 67 |
| P020 | 2 | 1 | 1 | 30 | 3 | 37 |
| P021 | — | — | — | — | — | 0 |
| P022 | — | — | — | — | — | 0 |
| P023 | 6 | 4 | 4 | — | 1 | 15 |
| P024 | — | — | — | 12 | — | 12 |
| P025 | — | — | — | — | — | 0 |
| P026 | 92 | 103 | 103 | 117 | — | 415 |
| P027 | 1 | — | — | 2 | — | 3 |
| P028 | 8 | — | — | 8 | — | 16 |
| P029 | — | — | — | 12 | — | 12 |
| P030 | — | — | — | 3 | — | 3 |
| P031 | — | — | — | — | — | 0 |
| P032 | — | — | — | — | — | 0 |
| P033 | — | — | — | — | — | 0 |
| P034 | — | — | — | — | — | 0 |
| **Total** | **317** | **275** | **340** | **464** | **50** | **1,446** |

`—` = 0 findings for that rule on that file.

### Aggregate by rule (all five files)

| Rule | Total | Category (primary) |
|------|------:|---|
| P011 | 169 | margin_or_overflow |
| P012 | 143 | annotations |
| P013 | 461 | page_numbering |
| P014 | 0 | heading_title |
| P015 | 39 | indentation |
| P016 | 11 | spacing_blank_lines |
| P017 | 24 | punctuation / table_format |
| P018 | 19 | list_of_tables_figures_toc |
| P019 | 67 | page_numbering |
| P020 | 37 | capitalization_case |
| P021 | 0 | abstract_length |
| P022 | 0 | page_numbering |
| P023 | 15 | spacing_blank_lines |
| P024 | 12 | list_of_tables_figures_toc |
| P025 | 0 | frontmatter_structure |
| P026 | 415 | font_format |
| P027 | 3 | heading_title |
| P028 | 16 | page_numbering |
| P029 | 12 | page_numbering |
| P030 | 3 | list_of_tables_figures_toc |
| P031 | 0 | list_of_tables_figures_toc |
| P032 | 0 | list_of_tables_figures_toc |
| P033 | 0 | title_page_metadata |
| P034 | 0 | title_page_metadata |
| **Total** | **1,446** | |

### Aggregate by category (all five files)

| Category | Total |
|----------|------:|
| page_numbering | 556 |
| font_format | 415 |
| margin_or_overflow | 169 |
| annotations | 143 |
| indentation | 39 |
| capitalization_case | 37 |
| list_of_tables_figures_toc | 32 |
| spacing_blank_lines | 26 |
| punctuation | 20 |
| table_format | 6 |
| heading_title | 3 |

---

## 4. Per-file summary

| File label | Total findings | Main contributors | Notes |
|---|---:|---|---|
| Cibaku Elson 1st review | 317 | P013, P026, P012 | Annotation rule (P012) only on this file among EF set |
| Yin H 2nd review (flattened) | 275 | P013, P026, P011 | Mirrors Yin Haotian counts closely |
| Yin Haotian 2nd review | 340 | P013, P026, P012 | +65 P012 vs flattened twin |
| Yin H 4th review (compressed) | 464 | P011, P026, P013 | Highest volume; P030 (3), P017/P018/P024 active |
| Sebastian Fine clean baseline | 50 | P013, P011, P020 | Lowest volume; no P026 on this extract |

---

## 5. P030–P034 behavior (full-run counts)

| Rule | This snapshot | Per-rule evaluation notes |
|------|-------------:|---|
| **P030** | **3** (Yin H 4th only, pages 12–13 TOC, 18 LoF) | Matches `p030_current_dataset_evaluation.md` (missing continued headings) |
| **P031** | 0 | Matches post–PR #55 evaluation (header-band false positives fixed) |
| **P032** | 0 | Matches post–PR #59 evaluation (split page-number guard) |
| **P033** | 0 | Matches post–PR #64 evaluation; comparison runs on 2/5 in isolated P033 runs |
| **P034** | 0 | Matches post–PR #68 evaluation (middle-initial tolerance) |

P033 and P034 produce no warnings in this full audit despite running; isolated per-rule
evaluations documented comparison activity without material mismatches.

---

## 6. Comparison to historical P029 snapshot (`6a0baaf`)

The prior full snapshot (`current_auditor_after_p014_p029_evaluation.md`) reported **1,485**
findings with P001–P029 only. **Direct comparison is approximate** — rules and refinements
changed after P029 (P030–P034 added; P013 grouping; P029 boundary guard; P031/P032/P034 false-positive fixes).

### Grand total

| Snapshot | Commit era | Rules in PDF audit | Grand total |
|----------|------------|-------------------|------------:|
| Historical P029 | `6a0baaf` | P011–P029 | 1,485 |
| **Current P034** | `3871d23` | P011–P034 | **1,446** |

Net **−39** (−2.6%). Not interpreted as improved compliance — rule set and heuristics differ.

### Per-file totals

| File label | P029 snapshot | P034 snapshot | Δ |
|---|---:|---:|---:|
| Cibaku Elson 1st review | 321 | 317 | −4 |
| Yin H 2nd review (flattened) | 284 | 275 | −9 |
| Yin Haotian 2nd review | 349 | 340 | −9 |
| Yin H 4th review (compressed) | 477 | 464 | −13 |
| Sebastian Fine clean baseline | 54 | 50 | −4 |

### Overlapping rules (P011–P029 aggregate)

| Rule | P029 era total | Current total | Δ | Notes |
|------|---------------:|--------------:|---:|---|
| P011 | 169 | 169 | 0 | Unchanged |
| P012 | 143 | 143 | 0 | |
| P013 | 501 | 461 | −40 | Per-page grouping reduces duplicate line-level warnings |
| P014 | 0 | 0 | 0 | |
| P015–P028 | (same subtotal) | (same) | ~0 | No material drift on sampled rules |
| P029 | 14 | 12 | −2 | Sebastian 2→0 after plausible-Roman boundary guard |

**New in current snapshot only:** P030 (+3), P031–P034 (0 in full run).

---

## 7. Interpretation

### Main noise sources (by volume)

1. **P013** (461) — page-number candidate detector; high volume by design.
2. **P026** (415) — font family/size signals (often Computer Modern vs Times New Roman).
3. **P011** (169) — margin overflow; Yin H 4th compressed still highest (70).
4. **P012** (143) — PDF annotations on EF-commented files only.

### Low- or zero-finding rules on this dataset

- **P014, P021, P022, P025, P031–P034:** 0 across all five files (P022/P025 may still apply on other layouts).
- **P030:** 3 findings, all Yin H 4th multi-page TOC/LoF continued-heading gaps.
- **P029:** 12 findings, all Yin H 4th (`roman_sequence_repeat` pattern documented historically).

### Usefulness

This snapshot establishes a **P034-era baseline** for aggregate triage. It does not measure
precision/recall against human EF comments. Findings remain heuristic warnings requiring manual review.

---

## 8. Limitations

- PDF text layer only; no OCR.
- TeX rules (P001–P010) not included in this PDF run.
- Sebastian PDF extracted locally from ZIP; not committed.
- Per-file JSON/Markdown reports under `data/evaluation/generated/current_auditor_after_p034/` are gitignored.
- Count changes vs the P029 snapshot reflect new rules and refinements, not verified formatting improvements.
- Does not quote or reproduce dissertation content.

---

## 9. Related docs

- Historical P029 snapshot: `docs/evaluation/current_auditor_after_p014_p029_evaluation.md`
- P030–P034 per-rule evaluations: see `docs/status/current_project_state_and_next_steps.md` (evaluation index)
- Evaluation data manifest: `docs/status/evaluation_data_manifest.md`
