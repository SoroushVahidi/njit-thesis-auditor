# P036–P063 Current-Dataset Evaluation Gap-Fill

- **Date:** 2026-06-09
- **Baseline commit:** `85a1326` (PR #265 — Sebastian Fine EF archive recovery documented)
- **Auditor scope:** P001–P072 implemented; **1014 pytest**; ruff clean; mypy 87 source files
- **Purpose:** Close current-dataset evaluation documentation gaps for P036–P063. All rules in this range previously had "not run" or "only 4/5 PDFs accessible" status. All five evaluation PDFs are now accessible (Sebastian Fine via ZIP extraction), enabling a canonical five-file evaluation.
- **Generated outputs:** `data/evaluation/generated/p036_p063_gap_fill/` — gitignored; not committed
- **Privacy:** Aggregate-only. No dissertation body text, TOC/LoT/LoF entry text, author names, EF comment text, reference entries, or any other private content quoted. File metadata and aggregate counts only.

---

## 1. Evaluation Dataset

| File label | Source | Pages | Availability |
|---|---|---:|---|
| Cibaku Elson 1st Review | `data/raw/ester/250218 Cibaku Elson First Review.pdf` | 99 | tracked — accessible |
| Yin H 2nd Review (flattened) | `data/raw/ester/260415 Yin H _2nd_review with EF Comments.pdf` | 108 | tracked — accessible |
| Yin Haotian 2nd Review | `data/raw/ester/Yin_Haotian_Second_R_with_EF_Feedback.pdf` | 108 | tracked — accessible |
| Yin H 4th Review (compressed) | `data/raw/ester/Yin_H_4th_Review_with_EF_comments_compressed.pdf` | 137 | tracked — accessible |
| Sebastian Fine clean baseline | archive-extracted from tracked ZIP | 29 | archive-extracted — accessible |

Sebastian Fine was extracted from `data/raw/ester/Dissertations with no Feedback -20260529T012213Z-3-001.zip`
to `data/evaluation/generated/p036_p063_gap_fill/sebastian_fine_clean.pdf` (gitignored; not committed).

---

## 2. P036–P063 Evaluation Status Inventory

| Rule | Short purpose | Issue type(s) | Eval doc existed? | Five-PDF eval before gap-fill | Gap-fill action |
|---|---|---|---|---|---|
| P036 | TOC/LoT/LoF inter-entry double spacing | `toc/lot/lof_inter_entry_spacing_too_tight` | Yes — "not run" | No | Run here |
| P037 | Section-anchored Roman numeral values | `roman_bio_sketch_not_iv`, `roman_section_wrong_value` | Yes — "not run" | No | Run here |
| P038 | Required front-matter heading presence/phrase | `required_heading_missing`, `heading_phrase_not_exact` | Yes — "not run" | No | Run here |
| P039 | TOC entry indentation hierarchy | `toc_heading_level_indentation_wrong` | Yes — "not run" | No | Run here |
| P040 | LoF entry terminal punctuation | `lof_entry_missing_terminal_punctuation` | Yes — "not run" | No | Run here |
| P041 | Dedication page top-margin header check | `dedication_page_has_running_header` | Yes — "not run" | No | Run here |
| P042 | TOC appendix entry format | `toc_single_appendix_uses_letter`, `toc_multiple_appendix_missing_letter`, `toc_appendix_letter_sequence_gap`, `toc_appendix_letter_sequence_repeat` | Yes — "not run" | No | Run here |
| P043 | Acknowledgements paragraph indentation | `acknowledgements_first_paragraph_indented`, `acknowledgements_subsequent_paragraph_not_indented` | Yes — "not run" | No | Run here |
| P044 | Abstract paragraph indentation | `abstract_first_paragraph_indented`, `abstract_subsequent_paragraph_not_indented` | Yes — "only 4/5" | No | Run here |
| P045 | Bio Sketch publication layout (hanging indent, spacing) | `biosketch_publications_not_hanging_indent`, `biosketch_publications_inter_entry_spacing_tight` | Yes — "only 4/5" | No | Run here |
| P046 | LoT/LoF entry number left-column alignment | `lot_entry_number_column_misaligned`, `lof_entry_number_column_misaligned` | Yes — "only 4/5" | No | Run here |
| P047 | Bio Sketch bullet/list section single-spacing | `biosketch_bullet_section_double_spaced` | No doc | No | Run here (stub created) |
| P048 | LoT/LoF page number right-column alignment | `lot_page_number_not_right_aligned`, `lof_page_number_not_right_aligned` | Yes — "only 4/5" | No | Run here |
| P049 | LoT/LoF Page-column header alignment/bold | `lot_page_column_header_not_right_aligned`, `lof_page_column_header_not_right_aligned`, `…_not_bold` | Yes — "only 4/5" | No | Run here |
| P050 | LoT/LoF left-column header bold style | `lot_table_header_not_bold`, `lof_figure_header_not_bold` | Yes — "only 4/5" | No | Run here |
| P051 | Copyright page year presence | `copyright_year_not_found` | Yes — "only 4/5" | No | Run here |
| P052 | Copyright page author presence | `copyright_author_not_found` | Yes — "only 4/5" | No | Run here |
| P053 | LoT entry terminal period | `lot_entry_has_terminal_period` | Yes — "only 4/5" | No | Run here |
| P054 | TOC entry terminal period absence | `toc_entry_has_terminal_period` | Yes — "only 4/5" | No | Run here |
| P055 | LoT/LoF cross-type entry check | `lot_entry_is_figure`, `lof_entry_is_table` | Yes — "only 4/5" | No | Run here |
| P056 | LoT/LoF entry numbering format consistency | `lot_mixed_numbering_format`, `lof_mixed_numbering_format` | Yes — "only 4/5" | No | Run here |
| P057 | LoT/LoF page-number ordering | `lot_page_numbers_not_nondecreasing`, `lof_page_numbers_not_nondecreasing` | Yes — "only 4/5" | No | Run here |
| P058 | TOC page-number ordering | `toc_page_numbers_not_nondecreasing` | No doc | No | Run here (stub created) |
| P059 | LoT/LoF entry-number ordering | `lot_entry_numbers_not_nondecreasing`, `lof_entry_numbers_not_nondecreasing` | Yes — "only 4/5" | No | Run here |
| P060 | TOC section-number ordering | `toc_entry_numbers_not_nondecreasing` | Yes — "only 4/5" | No | Run here |
| P061 | LoT/LoF cross-page entry-number ordering | `lot/lof_cross_page_entry_numbers_not_nondecreasing` | Yes — **formal eval (PR #204)** | **Yes** | **Already adequate — skipped** |
| P062 | TOC cross-page section-number ordering | `toc_cross_page_entry_numbers_not_nondecreasing` | No standalone doc | Ref. in full audit only | Run here (stub created) |
| P063 | Appendix body heading label check | `single_appendix_uses_letter_label`, `multiple_appendix_missing_letter`, `appendix_letter_sequence_gap`, `appendix_letter_sequence_repeat` | No standalone doc | No | Run here (stub created) |

**Total rules in gap-fill: 27** (P036–P060, P062, P063)
**Already adequate: 1** (P061 — formal five-PDF evaluation in PR #204)

---

## 3. Per-Rule Five-PDF Findings

### 3a. Rules with findings

#### P036 — TOC/LoT/LoF inter-entry double spacing

| File label | Findings |
|---|---:|
| Cibaku Elson 1st Review | 0 |
| Yin H 2nd Review (flattened) | 0 |
| Yin Haotian 2nd Review | 0 |
| Yin H 4th Review (compressed) | **55** |
| Sebastian Fine clean baseline | 0 |
| **Total** | **55** |

| Issue type | Count |
|---|---:|
| `toc_inter_entry_spacing_too_tight` | 42 |
| `lof_inter_entry_spacing_too_tight` | 9 |
| `lot_inter_entry_spacing_too_tight` | 4 |

**Notes:** All 55 findings on Yin H 4th (compressed). Dense TOC/LoT/LoF text layer on that file activates the spacing check. Other four files have no detected TOC/LoT/LoF entries with qualifying spacing gaps, or no TOC/LoT/LoF pages detected. Consistent with canonical aggregate (P036 = 55 post-P070; was 77 in P069-era before P070 parser refinement reduced overlap).

---

#### P037 — Section-anchored Roman numeral values

| File label | Findings |
|---|---:|
| Cibaku Elson 1st Review | 0 |
| Yin H 2nd Review (flattened) | 0 |
| Yin Haotian 2nd Review | 0 |
| Yin H 4th Review (compressed) | **2** |
| Sebastian Fine clean baseline | **1** |
| **Total** | **3** |

| Issue type | Count |
|---|---:|
| `roman_section_wrong_value` | 2 |
| `roman_bio_sketch_not_iv` | 1 |

**Notes:** Matches canonical aggregate (P037 = 3). `roman_bio_sketch_not_iv` fires on Sebastian Fine where the Bio Sketch page's Roman numeral does not match the expected iv value. `roman_section_wrong_value` fires on Yin H 4th.

---

#### P038 — Required front-matter heading presence/phrase

| File label | Findings |
|---|---:|
| Cibaku Elson 1st Review | **4** |
| Yin H 2nd Review (flattened) | **4** |
| Yin Haotian 2nd Review | **4** |
| Yin H 4th Review (compressed) | **2** |
| Sebastian Fine clean baseline | **2** |
| **Total** | **16** |

| Issue type | Count |
|---|---:|
| `required_heading_missing` | 14 |
| `heading_phrase_not_exact` | 2 |

**Notes:** Matches canonical aggregate (P038 = 16). Fires on all five files. `required_heading_missing` is the dominant issue type — one or more required front-matter headings (ABSTRACT, APPROVAL PAGE, BIOGRAPHICAL SKETCH, ACKNOWLEDGEMENTS, TABLE OF CONTENTS) not detected by the heading scanner. `heading_phrase_not_exact` fires on 2 files (e.g., ACKNOWLEDGMENTS variant). P038 reaching all 5 files is consistent with the heading scanner's cross-file behavior.

---

#### P040 — LoF entry terminal punctuation

| File label | Findings |
|---|---:|
| Cibaku Elson 1st Review | 0 |
| Yin H 2nd Review (flattened) | 0 |
| Yin Haotian 2nd Review | 0 |
| Yin H 4th Review (compressed) | 0 |
| Sebastian Fine clean baseline | **1** |
| **Total** | **1** |

| Issue type | Count |
|---|---:|
| `lof_entry_missing_terminal_punctuation` | 1 |

**Notes:** Matches canonical aggregate (P040 = 1). Only Sebastian Fine's LoF triggers the terminal-punctuation check — 1 complete LoF entry lacks a terminal period, question mark, or exclamation mark. Other files' LoF pages are absent or all entries pass or skip (flattened/compressed text layer).

---

#### P044 — Abstract paragraph indentation

| File label | Findings |
|---|---:|
| Cibaku Elson 1st Review | **3** |
| Yin H 2nd Review (flattened) | **1** |
| Yin Haotian 2nd Review | **1** |
| Yin H 4th Review (compressed) | **1** |
| Sebastian Fine clean baseline | **1** |
| **Total** | **7** |

| Issue type | Count |
|---|---:|
| `abstract_subsequent_paragraph_not_indented` | 6 |
| `abstract_first_paragraph_indented` | 1 |

**Notes:** Matches canonical aggregate (P044 = 7). Fires on all five files. Most common issue: subsequent abstract paragraphs not indented (Q003). One file also has first paragraph indented (Q002). Cibaku shows the highest count (3), likely due to multiple abstract paragraphs or geometry detection on EF-annotated text.

---

#### P046 — LoT/LoF entry number left-column alignment

| File label | Findings |
|---|---:|
| Cibaku Elson 1st Review | 0 |
| Yin H 2nd Review (flattened) | 0 |
| Yin Haotian 2nd Review | 0 |
| Yin H 4th Review (compressed) | **2** |
| Sebastian Fine clean baseline | 0 |
| **Total** | **2** |

| Issue type | Count |
|---|---:|
| `lot_entry_number_column_misaligned` | 1 |
| `lof_entry_number_column_misaligned` | 1 |

**Notes:** Matches canonical aggregate (P046 = 2). Both on Yin H 4th compressed only. Detected LoT and LoF entries on that file show misaligned left-column x-positions.

---

#### P051 — Copyright page year presence

| File label | Findings |
|---|---:|
| Cibaku Elson 1st Review | **1** |
| Yin H 2nd Review (flattened) | **1** |
| Yin Haotian 2nd Review | **1** |
| Yin H 4th Review (compressed) | 0 |
| Sebastian Fine clean baseline | 0 |
| **Total** | **3** |

| Issue type | Count |
|---|---:|
| `copyright_year_not_found` | 3 |

**Notes:** Matches canonical aggregate (P051 = 3). P051 fires when a copyright page is detected but no year token found in adjacent lines. Fires on Cibaku, Yin H flat, Yin Haotian — copyright page detected but year parsing fails on those three files. Yin H 4th and Sebastian Fine either have no detected copyright page or year parsing succeeds.

---

#### P053 — LoT entry terminal period

| File label | Findings |
|---|---:|
| Cibaku Elson 1st Review | 0 |
| Yin H 2nd Review (flattened) | 0 |
| Yin Haotian 2nd Review | 0 |
| Yin H 4th Review (compressed) | **1** |
| Sebastian Fine clean baseline | 0 |
| **Total** | **1** |

| Issue type | Count |
|---|---:|
| `lot_entry_has_terminal_period` | 1 |

**Notes:** Matches canonical aggregate (P053 = 1). One complete LoT entry on Yin H 4th ends with a period. Other files' LoT pages are absent, sparse, or all entries pass.

---

### 3b. Rules with 0 findings — five-PDF outcomes

| Rule | Five-PDF total | Outcome category | Notes |
|---|---:|---|---|
| P039 | 0 | Gate not met or no violations | TOC hierarchy: requires multiple distinct-level entries with measurable indentation; conservative gate; no indentation inversions detected |
| P041 | 0 | Detection gate not met | No machine-readable DEDICATION heading found in first 15 pages of any file (shared limitation with P065) |
| P042 | 0 | Detection gate not met | No APPENDIX entries detected in any file's TOC |
| P043 | 0 | Detection gate not met or passes | Acknowledgements indentation: section not detected on most files; those detected pass |
| P045 | 0 | Detection gate not met | Bio Sketch publication layout: BIOGRAPHICAL SKETCH heading or Publications subsection boundary not detected |
| P047 | 0 | Detection gate not met | Bio Sketch bullet single-spacing: BIOGRAPHICAL SKETCH heading not detected on 3/5; bullet section not detected on 2/5 that reach it |
| P048 | 0 | No violations detected | LoT/LoF page-number right-column alignment: detected entries pass alignment check or insufficient entries |
| P049 | 0 | No violations detected | LoT/LoF Page-column header alignment/bold: no violations detected |
| P050 | 0 | No violations detected | LoT/LoF left-column header bold: no violations or header absent |
| P052 | 0 | Copyright year required gate not met | P052 only fires when copyright year is confirmed; on files where P051 fires (year not found), P052 cannot fire |
| P054 | 0 | No violations detected | No TOC entries ending with `.` detected |
| P055 | 0 | No violations detected | No LoT entry starting with "Figure" or LoF entry starting with "Table" |
| P056 | 0 | No violations detected | No mixed chapter-based + sequential numbering format within any LoT/LoF section |
| P057 | 0 | No violations or insufficient entries | No LoT/LoF page-number inversions with ≥2 inversions detected |
| P058 | 0 | No violations or insufficient entries | No TOC page-number inversions with ≥2 inversions detected |
| P059 | 0 | No violations or insufficient entries | No LoT/LoF entry-number inversions with ≥2 inversions detected |
| P060 | 0 | No violations or insufficient entries | No TOC section-number inversions with ≥2 inversions detected |
| P062 | 0 | No qualifying multi-page TOC detected | No cross-page TOC numeric-sequence violation; consistent with prior full-audit result |
| P063 | 0 | Detection gate not met | No body-region appendix heading sequence detected; consistent with prior full-audit result |

Zero findings do not prove compliance — they indicate either no qualifying sequences were detected on this five-PDF set, or the rules' conservative gates were not met.

---

## 4. P061 — Already Adequately Evaluated

P061 (LoT/LoF cross-page entry-number ordering) has a formal five-PDF current-dataset evaluation
performed in PR #204 (commit `8930c88`). **0** P061 findings across all five files; documented in
`docs/evaluation/p061_current_dataset_evaluation.md`. No gap-fill action needed.

---

## 5. Summary Table: Findings by Rule and File

| Rule | Cibaku | Yin H 2nd flat | Yin Haotian 2nd | Yin H 4th | Sebastian Fine | **Total** |
|---|---:|---:|---:|---:|---:|---:|
| P036 | 0 | 0 | 0 | **55** | 0 | **55** |
| P037 | 0 | 0 | 0 | **2** | **1** | **3** |
| P038 | **4** | **4** | **4** | **2** | **2** | **16** |
| P039 | 0 | 0 | 0 | 0 | 0 | 0 |
| P040 | 0 | 0 | 0 | 0 | **1** | **1** |
| P041 | 0 | 0 | 0 | 0 | 0 | 0 |
| P042 | 0 | 0 | 0 | 0 | 0 | 0 |
| P043 | 0 | 0 | 0 | 0 | 0 | 0 |
| P044 | **3** | **1** | **1** | **1** | **1** | **7** |
| P045 | 0 | 0 | 0 | 0 | 0 | 0 |
| P046 | 0 | 0 | 0 | **2** | 0 | **2** |
| P047 | 0 | 0 | 0 | 0 | 0 | 0 |
| P048 | 0 | 0 | 0 | 0 | 0 | 0 |
| P049 | 0 | 0 | 0 | 0 | 0 | 0 |
| P050 | 0 | 0 | 0 | 0 | 0 | 0 |
| P051 | **1** | **1** | **1** | 0 | 0 | **3** |
| P052 | 0 | 0 | 0 | 0 | 0 | 0 |
| P053 | 0 | 0 | 0 | **1** | 0 | **1** |
| P054 | 0 | 0 | 0 | 0 | 0 | 0 |
| P055 | 0 | 0 | 0 | 0 | 0 | 0 |
| P056 | 0 | 0 | 0 | 0 | 0 | 0 |
| P057 | 0 | 0 | 0 | 0 | 0 | 0 |
| P058 | 0 | 0 | 0 | 0 | 0 | 0 |
| P059 | 0 | 0 | 0 | 0 | 0 | 0 |
| P060 | 0 | 0 | 0 | 0 | 0 | 0 |
| P062 | 0 | 0 | 0 | 0 | 0 | 0 |
| P063 | 0 | 0 | 0 | 0 | 0 | 0 |
| **Total (P036–P063, ex-P061)** | **8** | **6** | **6** | **63** | **5** | **88** |

---

## 6. Relationship to Canonical Aggregate

| Metric | Value |
|---|---|
| Canonical five-PDF aggregate (P001–P070, post-P070 run) | **1,543** |
| Canonical aggregate doc | `docs/evaluation/current_auditor_after_p070_evaluation.md` |
| P036–P063 contribution to canonical | **88** (P036: 55, P038: 16, P044: 7, P051: 3, P037: 3, P046: 2, P040: 1, P053: 1) |
| P061+P062+P063 contribution | 0 |
| Gap-fill results consistent with canonical? | **Yes** — all per-rule counts match canonical aggregate |

The gap-fill evaluation was run with the current auditor (P001–P072) and produces results
consistent with the P070-era canonical aggregate. No rule behavior changed; P036–P063 findings
in this gap-fill match what the canonical aggregate already records for those rules.

---

## 7. Generated-Output Path

Generated outputs (Sebastian Fine extracted PDF, raw findings JSON) are at:
`data/evaluation/generated/p036_p063_gap_fill/`

This path is gitignored. Contents:
- `sebastian_fine_clean.pdf` — extracted from tracked ZIP; not committed
- `raw_findings.json` — per-file, per-rule finding metadata; not committed

---

## 8. Privacy Protections

- No dissertation body text, EF comment text, TOC/LoT/LoF entry text, author names, reference entries, signature text, approval-page text, captions, DOI/URL strings, or bio-sketch text is quoted anywhere in this document.
- File metadata (size, page count, member name) only.
- Real dissertation files remain in `data/raw/ester/` (tracked, high privacy risk).
- Sebastian Fine extracted PDF stays in gitignored `data/evaluation/generated/`; not committed.
- No OCR performed. No external network calls made.

---

## 9. Limitations

- **Five-PDF set is small.** 27 rules evaluated on 5 files; zero findings do not prove compliance.
- **No OCR.** Rules relying on machine-readable text layers may produce 0 findings on flattened or image-embedded sections.
- **Text-layer limitations.** Yin H 2nd (flattened) has collapsed inter-word spacing; body-start patterns fail; many rules skip or are limited.
- **No complete raw/commented pairs.** Sebastian Fine is clean baseline only; Cibaku and Yin Haotian are the only extractable-EF files.
- **Rules gate conservatively.** Many rules require specific page-type detection (DEDICATION, BIOGRAPHICAL SKETCH, APPENDIX headings) that fails on this dataset — zero findings reflect detection limits, not proven compliance.
- **P036–P043 previously unavailable:** these eight rules were implemented when the EF PDFs were unavailable in the workspace. Now evaluated for the first time; no prior dataset results exist for comparison.
- **P044–P063 previously 4/5 only:** Sebastian Fine adds the fifth file; results are fully canonical for the first time.

---

## 10. Related Docs

- Post-P072 strategy doc: `docs/status/post_p072_backlog_and_data_strategy.md`
- Canonical aggregate: `docs/evaluation/current_auditor_after_p070_evaluation.md` (1,543)
- P061 current-dataset evaluation (adequate): `docs/evaluation/p061_current_dataset_evaluation.md`
- Per-rule synthetic validation docs: `docs/evaluation/p036_toc_list_entry_spacing_synthetic_validation.md` and corresponding files for P037–P063
- Rolling status: `docs/status/current_project_state_and_next_steps.md`
- Evaluation data manifest: `docs/status/evaluation_data_manifest.md`
