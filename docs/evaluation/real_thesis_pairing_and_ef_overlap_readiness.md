# Real Thesis Pairing and EF Overlap Readiness

- **Date:** 2026-06-07
- **Auditor scope:** P001–P063 implemented; 889 pytest
- **Source docs:** `data/processed/evaluation_data_manifest.json`,
  `docs/status/evaluation_data_manifest.md`,
  `docs/status/data_inventory_and_evaluation_sources.md`,
  `docs/sources/ester_materials.md`,
  `docs/evaluation/current_ef_comment_vs_tool_comparison.md`,
  `docs/evaluation/current_auditor_after_p061_evaluation.md`
- **Privacy:** All reporting is aggregate-only. No dissertation body text,
  title text, author names, committee names, or captions are quoted anywhere in
  this document.

---

## 1. Data Inventory Table

### 1a. Tracked committed files in `data/raw/ester/`

| Label | File type | Category | Comment status | Pages | Privacy |
|---|---|---|---|---|---|
| Cibaku Elson 1st Review | PDF | EF-commented dissertation | extractable (78) | 99 | high |
| Yin H 2nd Review (flattened) | PDF | EF-commented dissertation | flattened (0 extractable) | 108 | high |
| Yin Haotian 2nd Review | PDF | EF-commented dissertation | extractable (65) | 108 | high |
| Yin H 4th Review (compressed) | PDF | EF-commented dissertation | compressed/flattened (0 extractable) | 137 | high |
| Clean baseline ZIP | ZIP | no-feedback archive | n/a (no EF comments) | — | high |
| Rule matrix | XLSX | rule-source artifact | n/a | — | low |

### 1b. Archive-contained files (inside tracked ZIP)

| Label | Archive | Category | Comment status | Pages | Local availability |
|---|---|---|---|---|---|
| Sebastian Fine clean baseline (Revision 3) | Clean baseline ZIP | clean/no-feedback dissertation | n/a | 29 | archive-contained; extract locally for eval runs |

### 1c. Referenced but not standalone tracked

| Label | Category | Comment status | Local availability |
|---|---|---|---|
| Sebastian Fine 1st Review (EF annotated) | EF-commented dissertation | unknown | not verified as standalone tracked path |

### 1d. Original-archive-only (not committed; available from Google Drive RAR)

Ten additional EF-annotated dissertation PDFs/DOCXs and two process presentation files.
See `docs/sources/ester_materials.md` for the full list.
None of these files are locally present in the working tree without manual extraction from the
original archive bundle. Do not assume local availability without path evidence.

| Count | Types | Comment status known? |
|---|---|---|
| 8 PDF | EF-commented dissertations | not verified (extraction required) |
| 2 DOCX | EF-commented dissertations (tracked changes) | not verified |
| 2 PPTX | process/admin references | n/a |

### 1e. Generated and gitignored paths

| Path | Status | Contents |
|---|---|---|
| `data/evaluation/generated/` | gitignored | local audit JSON/MD snapshots, EF overlap summaries, refinement run outputs |
| `data/evaluation/private/` | gitignored (directory may be absent) | reserved for sensitive local-only analysis |

---

## 2. Raw/Commented Pair Table

A "pair" consists of a clean/uncommented dissertation version and a corresponding
EF-annotated/reviewed version of the same student's document.

| Pair label | Clean/raw version | EF-commented version | Both locally available? | Comment extractability | Suitable for auditor-vs-EF comparison? | Caveats |
|---|---|---|---|---|---|---|
| Sebastian Fine pair | Archive-contained (Revision 3; 29 pages; extracted from tracked ZIP) | 1st Review EF version — referenced but not standalone tracked | Clean: yes (via ZIP extraction). EF version: no (not verified locally) | Unknown for EF version | Not currently suitable — EF version not locally available | EF-annotated version must be extracted from original Google Drive RAR to enable comparison |
| Yin Haotian pair | None tracked — no standalone clean Yin Haotian draft is tracked or referenced | Yin Haotian 2nd Review (extractable, 65 comments) + Yin H 2nd Review flattened + Yin H 4th Review compressed | Clean draft: not present | 2nd extractable variant: 65 comments usable. Flattened and compressed: 0 extractable | EF-vs-tool overlap already performed on extractable 2nd review; no clean/raw counterpart for false-positive baseline | Multiple review rounds present but no corresponding uncommented draft is committed or referenced |
| Cibaku Elson pair | None tracked | Cibaku Elson 1st Review (extractable, 78 comments) | Clean draft: not present | 78 comments extractable | EF-vs-tool overlap already performed; no clean/raw counterpart | No clean version available for before/after comparison |

**Summary:** There are no currently committed raw/uncommented drafts that are paired with a
committed EF-commented version for the same document. The Sebastian Fine pair is the nearest
candidate, but the EF-annotated version is not locally accessible. The existing EF-overlap
work uses EF-commented PDFs directly, comparing audit findings against extracted annotations.

---

## 3. Expert Comment Extraction Status

| Label | Tracked? | Comment status | Extractable count | Classification | Notes |
|---|---|---|---|---|---|
| Cibaku Elson 1st Review | tracked | extractable | 78 | extractable annotations | Used in EF overlap comparisons; fully machine-readable annotations |
| Yin Haotian 2nd Review | tracked | extractable | 65 | extractable annotations | Used in EF overlap comparisons; fully machine-readable annotations |
| Yin H 2nd Review (flattened) | tracked | flattened | 0 | flattened/non-extractable | Comments rendered as page content; no PDF annotation objects |
| Yin H 4th Review (compressed) | tracked | compressed_flattened | 0 | flattened/non-extractable | Compressed PDF; comments non-extractable; PDF coordinate artifacts inflate P011 |
| Sebastian Fine 1st Review (EF annotated) | not standalone tracked | unknown | null | unknown/not locally available | Not verified as a standalone tracked path; original-archive-only |
| Archive-only EF PDFs (8) | original_archive_only | not verified | null | unknown/not locally available | Require extraction from original Google Drive RAR before any evaluation |
| Archive-only EF DOCXs (2) | original_archive_only | likely tracked-changes | null | unknown/not locally available | DOCX files likely contain tracked changes and embedded reviewer comments; require extraction |

---

## 4. Auditor Evaluation Status (P001–P062)

### Full five-PDF aggregate (from `docs/evaluation/current_auditor_after_p061_evaluation.md`)

The P061-era full-rerun snapshot covers P011–P061 across all five evaluation PDFs.
P062 was implemented after this snapshot (PR #220); a post-P062 full aggregate run
has not yet been performed.

| File label | Availability | Total findings (P011–P061) | P001–P010 status | Notes |
|---|---|---:|---|---|
| Cibaku Elson 1st Review | tracked | 325 | not included (TeX-only rules) | P061-era snapshot |
| Yin H 2nd Review (flattened) | tracked | 281 | not included | P061-era snapshot |
| Yin Haotian 2nd Review | tracked | 346 | not included | P061-era snapshot |
| Yin H 4th Review (compressed) | tracked | 579 | not included | P061-era snapshot; highest finding count |
| Sebastian Fine clean baseline | archive-extracted | 56 | not included | extracted from ZIP for eval; not committed standalone |

Grand total P011–P061 across five files: **1,587**

### Per-rule current-dataset evaluation status

| Rule range | Status |
|---|---|
| P011–P034 | Run; P034-era canonical snapshot (1,446 findings) plus P061-era full rerun (1,587 findings) |
| P035 | Run on local 4-PDF subset only (13 findings on Yin H 4th); not canonical five-PDF |
| P036–P043 | Not run — evaluation PDFs were unavailable in workspace when these rules were added |
| P044–P062 | Not run — only 4 of 5 evaluation PDFs directly accessible; full five-PDF run not performed |
| P001–P010 (TeX) | Not included in PDF evaluation runs; only applicable to TeX/ZIP inputs |
| P062 | Not run on current dataset — implemented in PR #220 after last full five-PDF aggregate |

---

## 5. Overlap/Comparison Readiness Table

| Label / pair | EF comments extractable? | Raw/clean version available? | Readiness classification | Notes |
|---|---|---|---|---|
| Cibaku Elson 1st Review | yes (78) | no clean version | **ready for EF overlap comparison now** | No clean/raw counterpart; auditor-vs-EF comparison done on EF-commented PDF directly; see `docs/evaluation/current_ef_comment_vs_tool_comparison.md` |
| Yin Haotian 2nd Review | yes (65) | no clean version | **ready for EF overlap comparison now** | Same approach as Cibaku; auditor-vs-EF comparison already performed; see `docs/evaluation/current_ef_comment_vs_tool_comparison.md` |
| Yin H 2nd Review (flattened) | no (0) | no clean version | **comments are flattened — not suitable for extractable-comment comparison** | Usable only for aggregate finding counts; cannot extract EF annotations |
| Yin H 4th Review (compressed) | no (0) | no clean version | **comments are flattened — not suitable for extractable-comment comparison** | Highest finding count (579); P011 inflated by compression artifacts; aggregate use only |
| Sebastian Fine pair | unknown (EF version not local) | yes (Revision 3 via ZIP) | **pair missing or uncertain** | Clean baseline available for false-positive profiling; EF-annotated version requires archive extraction |
| Archive-only EF files (10) | not verified | no clean counterparts tracked | **needs commented file extraction** | Require Google Drive RAR extraction; comment extractability unknown until verified locally |

---

## 6. Quality Assessment (Based on Existing Evaluation Docs)

### Where the auditor aligns with expert comments

- **Page-level coverage:** On both extractable-comment PDFs (Cibaku and Yin Haotian), every page
  that has an EF comment also has at least one tool finding (EF-only pages = 0 on both files).
  The auditor does not miss any EF-commented page entirely.
- **Indentation:** Yin Haotian shows 2 pages of overlap in the `indentation` category between
  EF comments and tool findings (P015).
- **Margin overflow:** Yin Haotian shows 1 page of overlap in `margin_or_overflow` (P011).
- **Geometric/structural layout signals:** Best alignment is in categories with direct
  geometry/text-structure constraints (indentation, margin overflow, limited spacing checks).

### Where the auditor is high-volume or noisy

| Rule | Total findings (five PDFs) | Assessment |
|---|---:|---|
| P013 — page-number candidates | 461 | High volume by design; grouping refinement (one warning per page) reduced individual count but page coverage unchanged |
| P026 — font compliance | 415 | High volume; real noncompliance but broad output; triage rollup added |
| P011 — margin overflow | 169 | Compressed PDF inflates to 70 (down from 150 with artifact guard); normal PDFs 21–33 |
| P012 — PDF annotations | 143 | Only fires on EF-commented PDFs; expected high volume on reviewed documents |
| P036 — TOC/list entry spacing | 77 | Concentrated on Yin H 4th compressed only |

### Where expert comments indicate missing rule coverage

From `docs/evaluation/current_ef_comment_vs_tool_comparison.md`:

| EF category | EF comment count (Cibaku / Yin Haotian) | Tool coverage | Gap assessment |
|---|---|---|---|
| unclear_or_other | 53 / 35 | not addressable deterministically | semantic/editorial feedback; out of scope for deterministic rules |
| references_citations | 5 / 4 | 0 / 0 | no dedicated rule; requires semantic content-level analysis |
| committee_approval_page | 3 / 2 | 0 / 0 | partial structural checks only (P025, P038); semantic committee-rank/order checks manual-only |
| table_format | 1 / 6 | partial (P017, P035) | EF feedback on table formatting often semantic/editorial |
| heading_title | 11 / 6 | 1 / 1 | P014/P020/P027/P038 cover structure; many EF heading comments are phrasing/editorial |
| list_of_tables_figures_toc | 0 / 4 | 0 / 0 (at P029 era) | P030–P036 and P039–P062 expand this; remains partially covered |

### Which P-rules were already refined from EF overlap

| Round | Rule(s) affected | Change | Outcome |
|---|---|---|---|
| Round 1 | P013 | Page-level grouping; one warning per page with candidates; structured triage fields | Reduced count noise; page coverage and EF-overlap unchanged |
| Round 2 | P018, P024 | Expanded TOC/List heading variant detection (trailing punctuation, CONTINUED suffixes) | No count change on current extractable PDFs; improved robustness for variant headings |

### Remaining gaps for P063+

Based on EF comment categories with zero or near-zero tool coverage, and on Q-rule inventory gaps:

1. **References/citations structural checks** — EF comments flag formatting issues in reference
   lists; no dedicated deterministic rule currently exists; partial automatable coverage possible
   for common citation-format indicators.
2. **Committee/approval-page structural checks** — P025/P038 cover heading presence; committee
   rank/order, signature-line layout, and approval-page completeness remain manual-only.
3. **Heading phrase/content refinement** — EF heading comments often semantic; P020/P027/P038
   address structure/style; exact APA-compliant wording within headings is not checked.
4. **Table and figure content checks** — P017/P035 address caption punctuation and placement;
   table-width, column-header style, and table-title positioning refinements are partial.
5. **LoT/LoF and TOC entry-extraction recall** — P059–P062 ordering rules find sparse
   comparable entries on compressed PDFs; improving entry-text extraction recall on compressed
   and multi-column layouts would improve coverage.
6. **Figure/table centering on image-heavy pages** — P035 is text-layer-only in v1; image-only
   floats are skipped.

---

## 7. Recommended Recurring Evaluation Workflow

This workflow should be run after every 3–5 new rules implemented.

### Step 1 — Run full auditor on raw/uncommented PDFs

```
python -m njit_auditor pdf \
    data/raw/ester/[tracked-pdf-1] \
    data/raw/ester/[tracked-pdf-2] \
    ... \
    --json-out data/evaluation/generated/post_PXXX_snapshot/ \
    --md-out data/evaluation/generated/post_PXXX_snapshot/
```

- Include all four tracked EF-commented PDFs and the Sebastian Fine clean baseline (extracted
  from the tracked ZIP into a gitignored local path).
- Do NOT commit the generated JSON/MD outputs.

### Step 2 — Extract expert comments from extractable-comment PDFs

```
python scripts/evaluate_ester_pdf_comments.py \
    "data/raw/ester/250218 Cibaku Elson First Review.pdf" \
    data/evaluation/generated/post_PXXX_snapshot/cibaku_elson_first_review_comments.json

python scripts/evaluate_ester_pdf_comments.py \
    "data/raw/ester/Yin_Haotian_Second_R_with_EF_Feedback.pdf" \
    data/evaluation/generated/post_PXXX_snapshot/yin_haotian_second_review_comments.json
```

- Only run on PDFs with `comment_status: extractable`.
- Do NOT attempt extraction on flattened/compressed PDFs.

### Step 3 — Compare by page/category/rule

```
python scripts/evaluate_current_ef_comment_overlap.py
```

- Adjust `ComparisonInput` paths to point to the new snapshot directory.
- Outputs go to `data/evaluation/generated/` (gitignored).

### Step 4 — Produce privacy-safe aggregate doc

- From the generated overlap summary JSON, write a new
  `docs/evaluation/current_auditor_after_PXXX_evaluation.md` with:
  - aggregate finding counts per rule per file (no body text, no titles, no author names)
  - category overlap table (counts and page counts only)
  - before/after comparison vs the prior snapshot
  - interpretation: noise sources, new coverage, remaining gaps
- Commit only this curated doc (not the generated JSON/MD raw outputs).

### Step 5 — Update rule backlog

- Update `docs/status/current_project_state_and_next_steps.md`:
  - mark any new current-dataset evaluation as complete
  - update validation counts (pytest, ruff, mypy)
  - note any EF-overlap changes from the new rules
- Update `data/processed/evaluation_data_manifest.json` if the rule count or
  evaluation status has changed.

### Step 6 — Housekeeping

- Confirm `data/evaluation/generated/` remains gitignored.
- Do not commit extracted raw dissertation PDFs.
- Preserve the canonical pre-P035 snapshot (`00b9c2d`, 1,446 findings) as the historical
  baseline; only replace the canonical baseline when a verified full five-PDF rerun is
  available.

---

## 8. Next Actions

### Immediate (before P063+)

1. **Run full five-PDF P001–P062 aggregate** — A post-P062 canonical snapshot has not been
   produced. Sebastian Fine clean baseline requires local extraction from the tracked ZIP.
   When all five PDFs are accessible, run the full auditor and produce a curated
   `docs/evaluation/current_auditor_after_p062_evaluation.md`.

2. **Produce P062 current-dataset evaluation doc** — `docs/evaluation/p062_current_dataset_evaluation.md`
   is referenced in `docs/status/current_project_state_and_next_steps.md` as not yet run.
   Run after full five-PDF access is restored.

3. **Update `data/processed/evaluation_data_manifest.json` for P062** — The JSON manifest
   still references P001–P061 as the implemented rule set. Update
   `auditor_rule_state.p_rules_implemented` to `P001-P062` and add the P062 current-dataset
   note. Also update `pytest_count_at_last_doc_refresh` to 876.

### Near-term (expand EF overlap set)

4. **Verify Sebastian Fine EF-annotated version** — Extract `250128 Sebastian.Fine Revised 1st
   Dissertation Draft EF.pdf` from the original Google Drive RAR locally. If annotation-based
   comments are extractable, add it to the EF overlap comparison. This would expand the
   extractable comparison set from 2 files to 3.

5. **Assess archive-only EF PDFs for extractability** — Extract one or two additional archive
   files (e.g., Pennock or Kang) locally and test comment extraction. If extractable, they can
   be added to the EF overlap comparison set, improving metric stability across document styles.
   Keep extracted files in gitignored local paths; do not commit.

### Longer-term (after P063+)

6. **Per-category precision/recall tracking** — After each EF overlap refresh, record the
   per-category overlap improvement in a running comparison doc. This enables data-driven
   prioritization of P063+ rules.

7. **Improve ordering rule entry extraction** — P059–P062 consistently find 0 comparable
   entries on compressed/multi-column PDFs. Before implementing additional ordering rules,
   investigate whether shared extraction improvements can increase comparable-entry yield.

---

## Cross-References

- Machine-readable manifest: `data/processed/evaluation_data_manifest.json`
- Evaluation data inventory: `docs/status/data_inventory_and_evaluation_sources.md`
- Evaluation data manifest (human-readable): `docs/status/evaluation_data_manifest.md`
- Ester materials catalog: `docs/sources/ester_materials.md`
- EF comment-vs-tool comparison (P001–P029 scope): `docs/evaluation/current_ef_comment_vs_tool_comparison.md`
- P061-era full five-PDF snapshot: `docs/evaluation/current_auditor_after_p061_evaluation.md`
- EF overlap round 1 refinement: `docs/evaluation/ef_overlap_driven_refinement_evaluation.md`
- EF overlap round 2 refinement: `docs/evaluation/ef_overlap_refinement_round2_evaluation.md`
- Project state and next steps: `docs/status/current_project_state_and_next_steps.md`
- EF overlap comparison script: `scripts/evaluate_current_ef_comment_overlap.py`
- EF comment extraction script: `scripts/evaluate_ester_pdf_comments.py`
