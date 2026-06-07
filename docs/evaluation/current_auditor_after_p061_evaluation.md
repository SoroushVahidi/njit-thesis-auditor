# Current Auditor Evaluation After P061 (Full P001–P061 Snapshot)

## 1. Purpose and auditor version

- **Date:** 2026-06-07
- **Baseline commit:** `ffea4e3b24915112b53fc4d6bb107f7d59e01779` (PR #205 — post-P061 status refresh)
- **Validation:** ruff, mypy, **744 pytest** passed
- **Auditor scope:** P001–P061 implemented (PDF layout audit **P011–P061**; TeX audit P001–P010 not run here)
- **Supersedes (for full aggregate):** `docs/evaluation/current_auditor_after_p034_evaluation.md` (P011–P034 only; **1,446** findings; historical baseline)
- **Generated artifacts (gitignored):** `data/evaluation/generated/current_auditor_after_p061/`

This is the first **full five-PDF aggregate snapshot** with P035–P061 included. Reporting is
**aggregate-only**: file labels, rule IDs, page numbers, and counts only. No dissertation body
text, title text, author names, committee names, captions, or entry titles are quoted.

**Historical baseline preserved:** The P034-era canonical aggregate (**1,446** findings;
`generated_for_commit: 00b9c2d`) remains the pre-P035 reference. This document records a new
P061-era full rerun at commit `ffea4e3` without replacing that historical metadata field.

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

## 3. Finding counts by file (P011–P061)

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
| P035 | — | — | — | 13 | 1 | 14 |
| P036 | — | — | — | 77 | — | 77 |
| P037 | — | — | — | 2 | 1 | 3 |
| P038 | 4 | 4 | 4 | 2 | 2 | 16 |
| P039 | — | — | — | — | — | 0 |
| P040 | — | — | — | 12 | 1 | 13 |
| P041 | — | — | — | — | — | 0 |
| P042 | — | — | — | — | — | 0 |
| P043 | — | — | — | — | — | 0 |
| P044 | 3 | 1 | 1 | 1 | 1 | 7 |
| P045 | — | — | — | — | — | 0 |
| P046 | — | — | — | 2 | — | 2 |
| P047 | — | — | — | — | — | 0 |
| P048 | — | — | — | 1 | — | 1 |
| P049 | — | — | — | 1 | — | 1 |
| P050 | — | — | — | — | — | 0 |
| P051 | 1 | 1 | 1 | — | — | 3 |
| P052 | — | — | — | — | — | 0 |
| P053 | — | — | — | 2 | — | 2 |
| P054 | — | — | — | 1 | — | 1 |
| P055 | — | — | — | — | — | 0 |
| P056 | — | — | — | — | — | 0 |
| P057 | — | — | — | — | — | 0 |
| P058 | — | — | — | 1 | — | 1 |
| P059 | — | — | — | — | — | 0 |
| P060 | — | — | — | — | — | 0 |
| P061 | — | — | — | — | — | 0 |
| **Total** | **325** | **281** | **346** | **579** | **56** | **1,587** |

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
| P031–P034 | 0 | list_of_tables_figures_toc / title_page_metadata |
| P035 | 14 | table_format / figure_format |
| P036 | 77 | list_of_tables_figures_toc |
| P037 | 3 | page_numbering |
| P038 | 16 | heading_title |
| P039–P043 | 0 | (various) |
| P044 | 7 | indentation |
| P045–P047 | 0 | (various) |
| P048–P049 | 2 | list_of_tables_figures_toc |
| P050 | 0 | list_of_tables_figures_toc |
| P051 | 3 | title_page_metadata |
| P052 | 0 | title_page_metadata |
| P053–P054 | 3 | list_of_tables_figures_toc |
| P055–P060 | 0 | list_of_tables_figures_toc |
| P061 | 0 | list_of_tables_figures_toc |
| **Total** | **1,587** | |

### Aggregate by category (all five files)

| Category | Total |
|----------|------:|
| page_numbering | 559 |
| font_format | 415 |
| margin_or_overflow | 169 |
| annotations | 143 |
| list_of_tables_figures_toc | 130 |
| indentation | 46 |
| capitalization_case | 37 |
| spacing_blank_lines | 26 |
| punctuation | 20 |
| heading_title | 19 |
| table_format | 13 |
| figure_format | 7 |
| title_page_metadata | 3 |

---

## 4. Per-file summary

| File label | Total findings | Main contributors | Notes |
|---|---:|---|---|
| Cibaku Elson 1st review | 325 | P013, P026, P012 | +8 vs P034 snapshot (P038, P044, P051) |
| Yin H 2nd review (flattened) | 281 | P013, P026, P011 | +6 vs P034 snapshot (P038, P044, P051) |
| Yin Haotian 2nd review | 346 | P013, P026, P012 | +6 vs P034 snapshot (P038, P044, P051) |
| Yin H 4th review (compressed) | 579 | P011, P026, P013, P036 | +115 vs P034 snapshot; P036 dominant new rule |
| Sebastian Fine clean baseline | 56 | P013, P011, P020 | +6 vs P034 snapshot (P035, P037, P038, P040, P044) |

---

## 5. P061 in this full aggregate

| Metric | Value |
|---|---|
| **P061 total** | **0** across five files |
| LoT cross-page runs detected | Yin H 4th only (0 comparable entries) — see formal P061 eval |
| LoF cross-page runs detected | Yin H 4th only (one 2-page run; insufficient comparable entries) |
| Comparable entries available for P061 | **None** on any file under P059 parsing gates |

**Interpretation:** Zero P061 findings **do not prove** LoT/LoF cross-page entry-number ordering
compliance. On this dataset, evaluation PDFs provide sparse multi-page LoT/LoF text-layer
extraction; P061 did not encounter a qualifying cross-page comparable sequence (≥2 pages,
≥3 comparable entries, ≥2 inversions). This matches the formal P061-only evaluation in
`docs/evaluation/p061_current_dataset_evaluation.md` (PR #204).

---

## 6. Comparison to historical P034 snapshot

| Snapshot | Commit era | Rules in PDF audit | Grand total |
|----------|------------|-------------------|------------:|
| Historical P034 (canonical baseline) | `00b9c2d` | P011–P034 | **1,446** |
| **Current P061 (this snapshot)** | `ffea4e3` | P011–P061 | **1,587** |

Net **+141** (+9.8%). **Do not interpret as worse compliance** — the increase is explained
entirely by **new rules P035–P061** (141 findings), while the P011–P034 subtotal remains
**1,446** (unchanged).

### Per-file totals vs P034 snapshot

| File label | P034 snapshot | P061 snapshot | Δ |
|---|---:|---:|---:|
| Cibaku Elson 1st review | 317 | 325 | +8 |
| Yin H 2nd review (flattened) | 275 | 281 | +6 |
| Yin Haotian 2nd review | 340 | 346 | +6 |
| Yin H 4th review (compressed) | 464 | 579 | +115 |
| Sebastian Fine clean baseline | 50 | 56 | +6 |

### New-rule increment (P035–P061 only)

| Rule | New findings | Primary file(s) |
|------|-------------:|---|
| P036 | 77 | Yin H 4th compressed |
| P035 | 14 | Yin H 4th (13), Sebastian (1) |
| P038 | 16 | All five files (low volume each) |
| P040 | 13 | Yin H 4th (12), Sebastian (1) |
| P044 | 7 | All five files |
| P037 | 3 | Yin H 4th (2), Sebastian (1) |
| P051 | 3 | Cibaku, Yin H 2nd flat, Yin Haotian 2nd |
| P053 | 2 | Yin H 4th |
| P046 | 2 | Yin H 4th |
| P048, P049, P054, P058 | 1 each | Yin H 4th |
| P039–P043, P045–P047, P050, P052, P055–P061 | 0 | — |

---

## 7. Interpretation

### Main noise sources (by volume)

1. **P013** (461) — page-number candidate detector; high volume by design.
2. **P026** (415) — font family/size signals.
3. **P011** (169) — margin overflow; Yin H 4th compressed still highest (70).
4. **P012** (143) — PDF annotations on EF-commented files only.
5. **P036** (77) — new in this snapshot; TOC/list entry spacing on Yin H 4th only.

### Low- or zero-finding rules on this dataset

- **P014, P021, P022, P025, P031–P034, P039–P043, P045–P047, P050, P052, P055–P061:** 0 across all five files.
- **P030:** 3 findings, all Yin H 4th (continued-heading gaps).
- **P061:** 0 — insufficient comparable cross-page LoT/LoF sequences (see §5).

### Usefulness

This snapshot establishes a **P061-era full aggregate baseline** for triage across all
implemented PDF rules. It does not measure precision/recall against human EF comments.
Findings remain heuristic warnings requiring manual review.

---

## 8. Limitations

- PDF text layer only; no OCR.
- TeX rules (P001–P010) not included in this PDF run.
- Sebastian PDF extracted locally from ZIP to gitignored `.extracted/` path; not committed.
- Per-file JSON/Markdown reports under `data/evaluation/generated/current_auditor_after_p061/` are gitignored.
- Count changes vs the P034 snapshot reflect new rules P035–P061, not verified formatting improvements.
- P061 zero findings reflect sparse LoT/LoF comparable-entry extraction, especially on compressed PDFs.
- Does not quote or reproduce dissertation content.

---

## 9. Related docs

- Historical P034 canonical snapshot: `docs/evaluation/current_auditor_after_p034_evaluation.md`
- P061 formal per-rule evaluation: `docs/evaluation/p061_current_dataset_evaluation.md`
- P035 local subset (pre-full-rerun): `docs/evaluation/p035_current_dataset_evaluation.md`
- Evaluation data manifest: `docs/status/evaluation_data_manifest.md`
- Project status: `docs/status/current_project_state_and_next_steps.md`
