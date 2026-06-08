# Current Auditor Evaluation After P064 (Full P001–P064 Snapshot)

## 1. Purpose and auditor version

- **Date:** 2026-06-08
- **Baseline commit:** `769d580` (post PR #229 — P064 current-dataset evaluation complete)
- **Validation:** ruff passed, mypy passed, **910 pytest** passed
- **Auditor scope:** P001–P064 implemented (PDF layout audit **P011–P064**; TeX audit P001–P010 not run here)
- **Supersedes (for full aggregate):** `docs/evaluation/current_auditor_after_p063_evaluation.md` (P011–P063; **1,587** findings; P063-era baseline)
- **Generated artifacts (gitignored):** `data/evaluation/generated/current_auditor_after_p064/`

This is the **full five-PDF aggregate snapshot with P064 included**. Reporting is
**aggregate-only**: file labels, rule IDs, page numbers, and counts only. No dissertation body
text, title text, author names, committee names, captions, reference entry text, citation
text, or any other dissertation content is quoted.

**Historical baselines preserved:**
- P034-era canonical aggregate: **1,446** findings (`generated_for_commit: 00b9c2d`).
- P061-era aggregate: **1,587** findings (commit `ffea4e3`).
- P062-era aggregate: **1,587** findings (commit `36373c9`).
- P063-era aggregate: **1,587** findings (commit `f170be5`).
All remain unchanged in their respective documents.

---

## 2. Dataset inventory

| File label | Availability | Pages | Notes |
|---|---|---:|---|
| Cibaku Elson 1st Review | tracked | 99 | EF-commented; extractable highlights |
| Yin H 2nd Review (flattened) | tracked | 108 | EF-commented; flattened comments |
| Yin Haotian 2nd Review | tracked | 108 | EF-commented; extractable highlights |
| Yin H 4th Review (compressed) | tracked | 137 | EF-commented; compressed/flattened |
| Sebastian Fine clean baseline | archive-extracted | 29 | From tracked ZIP; not committed as standalone PDF |

Sebastian Fine was extracted from
`data/raw/ester/Dissertations with no Feedback -20260529T012213Z-3-001.zip` to a local
temporary path for this run and was not committed.

Skipped: rule-matrix XLSX; archive-only materials not verified locally.

---

## 3. Finding counts by file (P011–P064)

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
| P062 | — | — | — | — | — | 0 |
| P063 | — | — | — | — | — | 0 |
| P064 | — | — | — | — | — | 0 |
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
| P017 | 24 | punctuation |
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
| P040 | 13 | list_of_tables_figures_toc |
| P044 | 7 | indentation |
| P045–P047 | 0 | (various) |
| P046 | 2 | list_of_tables_figures_toc |
| P048 | 1 | list_of_tables_figures_toc |
| P049 | 1 | list_of_tables_figures_toc |
| P050 | 0 | list_of_tables_figures_toc |
| P051 | 3 | title_page_metadata |
| P052 | 0 | title_page_metadata |
| P053 | 2 | list_of_tables_figures_toc |
| P054 | 1 | list_of_tables_figures_toc |
| P055–P061 | 0 | list_of_tables_figures_toc |
| P058 | 1 | list_of_tables_figures_toc |
| P062 | 0 | list_of_tables_figures_toc |
| P063 | 0 | heading_title |
| P064 | 0 | references_citations |
| **Total** | **1,587** | |

### Aggregate by category (all five files)

| Category | Total |
|----------|------:|
| page_numbering | 559 |
| font_format | 415 |
| margin_or_overflow | 169 |
| annotations | 143 |
| list_of_tables_figures_toc | 132 |
| indentation | 46 |
| capitalization_case | 37 |
| spacing_blank_lines | 26 |
| punctuation | 24 |
| heading_title | 19 |
| table_format / figure_format | 14 |
| title_page_metadata | 3 |
| references_citations | 0 |

---

## 4. Per-file summary

| File label | Total findings | Main contributors | Notes |
|---|---:|---|---|
| Cibaku Elson 1st Review | 325 | P013, P026, P012 | Unchanged vs P063 snapshot |
| Yin H 2nd Review (flattened) | 281 | P013, P026, P011 | Unchanged vs P063 snapshot |
| Yin Haotian 2nd Review | 346 | P013, P026, P012 | Unchanged vs P063 snapshot |
| Yin H 4th Review (compressed) | 579 | P011, P026, P013, P036 | Unchanged vs P063 snapshot |
| Sebastian Fine clean baseline | 56 | P013, P011, P020 | Unchanged vs P063 snapshot |

---

## 5. P064 in this full aggregate

| Metric | Value |
|---|---|
| **P064 total** | **0** across five files |
| `references_section_heading_not_detected` | 0 |
| `references_entry_indentation_inconsistent` | 0 |
| `references_entry_spacing_inconsistent` | 0 |
| Files reaching entry-level checks (B and C) | 2 of 5 |
| Files skipped by conservative gates | 3 of 5 |

**Skip conditions by file:**

| File | Skip condition |
|---|---|
| Cibaku Elson 1st Review | High x-variance (59.7 pt > 50 pt threshold) — EF annotation artifacts widen geometric spread |
| Yin H 2nd Review (flattened) | No body region detected — collapsed inter-word spacing ("CHAPTER1") in text layer |
| Yin Haotian 2nd Review | No body region detected — same text-layer issue as Yin H 2nd |
| Yin H 4th Review (compressed) | Reached checks; 52 entries / 5 section pages — no inconsistency detected |
| Sebastian Fine clean baseline | Reached checks; 24 entries / 3 section pages — no inconsistency detected |

**Interpretation:** Zero P064 findings do not prove references/citations compliance.
Three of five files were skipped by conservative gates before entry-level checks could run.
For those three files, P064 makes no claim about the formatting quality of the references
section. For Yin H 4th and Sebastian Fine, the references sections passed P064's
conservative geometric thresholds for consistency.

Zero P064 findings may reflect:
1. Genuinely consistent references section formatting (files reaching entry checks), **or**
2. Skip conditions triggered by text-layer limitations (files skipped before checks), **or**
3. Conservative threshold settings that do not fire on moderate inconsistencies.

The detailed per-file gate analysis is in `docs/evaluation/p064_current_dataset_evaluation.md`.

---

## 6. Comparison to historical snapshots

| Snapshot | Commit era | Rules in PDF audit | Grand total |
|----------|------------|-------------------|------------:|
| Historical P034 (canonical baseline) | `00b9c2d` | P011–P034 | **1,446** |
| P061-era aggregate | `ffea4e3` | P011–P061 | **1,587** |
| P062-era aggregate | `36373c9` | P011–P062 | **1,587** |
| P063-era aggregate | `f170be5` | P011–P063 | **1,587** |
| **P064-era aggregate (this snapshot)** | `769d580` | P011–P064 | **1,587** |

Net delta P063→P064: **0** (P064 adds no findings on this dataset).
Net delta P034→P064: **+141** (+9.8%). This increase is explained entirely by new rules P035–P063.
P064 does not contribute to the delta.

### Per-file totals vs prior snapshots

| File label | P034 snapshot | P061 snapshot | P062 snapshot | P063 snapshot | P064 snapshot | Δ (P064 vs P063) |
|---|---:|---:|---:|---:|---:|---:|
| Cibaku Elson 1st Review | 317 | 325 | 325 | 325 | 325 | 0 |
| Yin H 2nd Review (flattened) | 275 | 281 | 281 | 281 | 281 | 0 |
| Yin Haotian 2nd Review | 340 | 346 | 346 | 346 | 346 | 0 |
| Yin H 4th Review (compressed) | 464 | 579 | 579 | 579 | 579 | 0 |
| Sebastian Fine clean baseline | 50 | 56 | 56 | 56 | 56 | 0 |

---

## 7. Interpretation

### Main noise sources (by volume)

1. **P013** (461) — page-number candidate detector; high volume by design.
2. **P026** (415) — font family/size signals; real noncompliance on most PDFs.
3. **P011** (169) — margin overflow; Yin H 4th compressed still highest (70).
4. **P012** (143) — PDF annotations on EF-commented files only (Cibaku 78, Yin Haotian 65).
5. **P036** (77) — TOC/list inter-entry spacing; Yin H 4th compressed only.

### Zero- or low-finding rules on this dataset

- **P014, P021, P022, P025, P031–P034, P039–P043, P045–P047, P050, P052, P055–P060, P062–P064:** 0 across all five files.
- **P030:** 3 findings, all Yin H 4th (continued-heading gaps).
- **P061, P062, P063:** 0 — insufficient comparable entries/sequences or no qualifying body-region appendix headings detected.
- **P064:** 0 — 3 of 5 files skipped by conservative gates; 2 of 5 passed entry-level checks. See §5 for details.

### Largest categories

| Rank | Category | Total |
|---:|---|---:|
| 1 | page_numbering | 559 |
| 2 | font_format | 415 |
| 3 | margin_or_overflow | 169 |
| 4 | annotations | 143 |
| 5 | list_of_tables_figures_toc | 132 |

---

## 8. Privacy limitations and dataset limitations

- PDF text layer only; no OCR. Flattened/compressed PDFs may have reduced extractable content.
- TeX rules (P001–P010) not included in this PDF run.
- Sebastian Fine PDF extracted locally from ZIP to a temporary path; not committed.
- Per-file JSON/summary reports under `data/evaluation/generated/current_auditor_after_p064/`
  are gitignored and must not be committed.
- Ordering rules (P057–P062) have conservative gates (≥3 comparable entries, ≥2 inversions)
  that yield 0 findings on sparse or word-prefix-dominated list/TOC structures; 0 findings
  do not prove compliance.
- P063 (body-page appendix heading check) has a body-region gate (CHAPTER or APPENDIX body
  heading required); 0 findings do not prove appendix compliance if body heading detection
  gate is not met on a given PDF.
- P064 (references/citations structural check) has conservative skip conditions: high x-variance,
  no body region detected, too few entry candidates. 0 findings do not prove compliance on
  files where skip conditions apply. See `docs/evaluation/p064_current_dataset_evaluation.md`.
- P020 (title capitalization) fires only where bold font metadata is available; recall is low
  on PDFs without reliable font metadata.
- Count changes vs the P034 snapshot reflect new rules P035–P064, not verified formatting improvements.
- This dataset contains five PDFs from a small cohort and may not be representative of all
  dissertation formatting patterns at NJIT.
- No dissertation body text, title text, author names, committee names, captions, reference entry
  text, or citation content is quoted in this document.

---

## 9. Related docs

- Historical P034 canonical snapshot: `docs/evaluation/current_auditor_after_p034_evaluation.md`
- P061 full-aggregate snapshot (historical): `docs/evaluation/current_auditor_after_p061_evaluation.md`
- P062 full-aggregate snapshot (historical): `docs/evaluation/current_auditor_after_p062_evaluation.md`
- P063 full-aggregate snapshot (prior era): `docs/evaluation/current_auditor_after_p063_evaluation.md`
- P064 current-dataset evaluation: `docs/evaluation/p064_current_dataset_evaluation.md`
- P064 design doc: `docs/planning/p064_references_citations_structural_check_scope_and_design.md`
- EF overlap analysis (post-P063): `docs/evaluation/ef_overlap_after_p063_evaluation.md`
- Real-thesis pairing and EF overlap readiness: `docs/evaluation/real_thesis_pairing_and_ef_overlap_readiness.md`
- Evaluation data manifest: `docs/status/evaluation_data_manifest.md`
- Project status: `docs/status/current_project_state_and_next_steps.md`
- Full repository audit (P063-era): `docs/status/full_repository_audit_after_p063.md`
