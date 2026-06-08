# Real Thesis Pairing and EF Overlap Readiness

- **Date:** 2026-06-08 (refreshed after P068 aggregate snapshot)
- **Auditor scope:** P001–P068 implemented; **963 pytest**
- **Latest main (scope refresh):** `4b5b003` (PR #246 — P069 scoped)
- **Current full aggregate:** `docs/evaluation/current_auditor_after_p068_evaluation.md` — **1,590** findings (commit `5d8ebaf`)
- **Source docs:** `data/processed/evaluation_data_manifest.json`,
  `docs/status/evaluation_data_manifest.md`,
  `docs/status/data_inventory_and_evaluation_sources.md`,
  `docs/sources/ester_materials.md`,
  `docs/evaluation/current_ef_comment_vs_tool_comparison.md`,
  `docs/evaluation/ef_overlap_after_p063_evaluation.md`,
  `docs/evaluation/current_auditor_after_p068_evaluation.md`
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

**Tracked real dissertation PDF count:** 4  
**Tracked evaluation-support artifacts:** 2 (ZIP + XLSX)

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
| `data/evaluation/generated/` | gitignored | local audit JSON/MD snapshots, EF overlap summaries, refinement run outputs; canonical post-P068 aggregate at `current_auditor_after_p068/` |
| `data/evaluation/private/` | gitignored (directory may be absent) | reserved for sensitive local-only analysis |

---

## 2. Raw/Commented Pair Table

A "pair" consists of a clean/uncommented dissertation version and a corresponding
EF-annotated/reviewed version of the same student's document.

| Pair label | Clean/raw version | EF-commented version | Both locally available? | Comment extractability | Suitable for auditor-vs-EF comparison? | Caveats |
|---|---|---|---|---|---|---|
| Sebastian Fine pair | Archive-contained (Revision 3; 29 pages; extracted from tracked ZIP) | 1st Review EF version — referenced but not standalone tracked | Clean: yes (via ZIP extraction). EF version: no (not verified locally) | Unknown for EF version | **Not currently suitable** — EF version not locally available | EF-annotated version must be extracted from original Google Drive RAR to enable comparison |
| Yin Haotian pair | None tracked — no standalone clean Yin Haotian draft is tracked or referenced | Yin Haotian 2nd Review (extractable, 65 comments) + Yin H 2nd Review flattened + Yin H 4th Review compressed | Clean draft: not present | 2nd extractable variant: 65 comments usable. Flattened and compressed: 0 extractable | **EF-vs-tool overlap already performed** on extractable 2nd review; no clean/raw counterpart for false-positive baseline | Multiple review rounds present but no corresponding uncommented draft is committed or referenced |
| Cibaku Elson pair | None tracked | Cibaku Elson 1st Review (extractable, 78 comments) | Clean draft: not present | 78 comments extractable | **EF-vs-tool overlap already performed**; no clean/raw counterpart | No clean version available for before/after comparison |

**Summary:** There are **no** currently committed raw/uncommented drafts paired with a
committed EF-commented version for the same document. The Sebastian Fine pair is the nearest
candidate, but the EF-annotated version is not locally accessible. Existing EF-overlap
work uses EF-commented PDFs directly, comparing audit findings against extracted annotations.

**Raw/commented pair count (complete pairs):** **0**  
**Partial pairs (clean or commented only):** **3** (Sebastian Fine, Yin Haotian, Cibaku Elson)

---

## 3. Expert Comment Extraction Status

Verified locally on 2026-06-08 via `njit_auditor.pdf_comments.extract_pdf_annotations`.

| Label | Tracked? | Comment status | Extractable count | Classification | Notes |
|---|---|---|---|---|---|
| Cibaku Elson 1st Review | tracked | extractable | 78 | extractable annotations | Used in EF overlap comparisons; fully machine-readable annotations |
| Yin Haotian 2nd Review | tracked | extractable | 65 | extractable annotations | Used in EF overlap comparisons; fully machine-readable annotations |
| Yin H 2nd Review (flattened) | tracked | flattened | 0 | flattened/non-extractable | Comments rendered as page content; no PDF annotation objects |
| Yin H 4th Review (compressed) | tracked | compressed_flattened | 0 | flattened/non-extractable | Compressed PDF; comments non-extractable; PDF coordinate artifacts inflate P011 |
| Sebastian Fine 1st Review (EF annotated) | not standalone tracked | unknown | null | unknown/not locally available | Not verified as a standalone tracked path; original-archive-only |
| Archive-only EF PDFs (8) | original_archive_only | not verified | null | unknown/not locally available | Require extraction from original Google Drive RAR before any evaluation |
| Archive-only EF DOCXs (2) | original_archive_only | likely tracked-changes | null | unknown/not locally available | DOCX files likely contain tracked changes and embedded reviewer comments; require extraction |

**Extractable-comment pair count:** **2** (Cibaku + Yin Haotian 2nd Review)  
**Total extractable EF annotation objects:** **143** (78 + 65)

---

## 4. Auditor Evaluation Status (P001–P068)

### Full five-PDF aggregate (P068-era)

Canonical snapshot: `docs/evaluation/current_auditor_after_p068_evaluation.md`  
Generated outputs (gitignored): `data/evaluation/generated/current_auditor_after_p068/`

| File label | Availability | Total findings (P011–P068) | P068 findings | Notes |
|---|---|---:|---:|---|
| Cibaku Elson 1st Review | tracked | 325 | 0 | P068 skipped at APPROVAL PAGE gate |
| Yin H 2nd Review (flattened) | tracked | 281 | 0 | P068 skipped at APPROVAL PAGE gate |
| Yin Haotian 2nd Review | tracked | 346 | 0 | P068 skipped at APPROVAL PAGE gate |
| Yin H 4th Review (compressed) | tracked | 580 | 1 | P068 structural finding; highest finding count |
| Sebastian Fine clean baseline | archive-extracted | 58 | 2 | extracted from ZIP for eval; not committed standalone |

Grand total P011–P068 across five files: **1,590** (+3 vs P067-era 1,587)

### Per-rule current-dataset evaluation status

| Rule range | Status |
|---|---|
| P011–P034 | Run; P034-era canonical snapshot (1,446 findings) plus P068-era full rerun (1,590 findings) |
| P035–P068 | Current-dataset evaluation docs exist for P035–P068; full five-PDF aggregate refreshed through P068 |
| P001–P010 (TeX) | Not included in PDF evaluation runs; only applicable to TeX/ZIP inputs |

### Historical aggregate baselines (preserved)

| Era | Commit | Total findings | Doc |
|---|---|---:|---|
| Pre-P035 | `00b9c2d` | 1,446 | `docs/evaluation/current_auditor_after_p034_full_triage_refresh.md` |
| P061-era | `ffea4e3` | 1,587 | `docs/evaluation/current_auditor_after_p061_evaluation.md` |
| P067-era | `afe4ef6` | 1,587 | `docs/evaluation/current_auditor_after_p067_evaluation.md` |
| P068-era (current) | `5d8ebaf` | 1,590 | `docs/evaluation/current_auditor_after_p068_evaluation.md` |

---

## 5. Overlap/Comparison Readiness Table

| Label / pair | EF comments extractable? | Raw/clean version available? | Readiness classification | Notes |
|---|---|---|---|---|
| Cibaku Elson 1st Review | yes (78) | no clean version | **ready for EF overlap comparison now** | Auditor-vs-EF comparison done at P029 and P063 eras; refresh recommended after P068 |
| Yin Haotian 2nd Review | yes (65) | no clean version | **ready for EF overlap comparison now** | Same approach as Cibaku; comparison done at P029 and P063 eras; refresh recommended after P068 |
| Yin H 2nd Review (flattened) | no (0) | no clean version | **comments are flattened — not suitable for extractable-comment comparison** | Usable only for aggregate finding counts; cannot extract EF annotations |
| Yin H 4th Review (compressed) | no (0) | no clean version | **comments are flattened — not suitable for extractable-comment comparison** | Highest finding count (580); P011 inflated by compression artifacts; aggregate use only |
| Sebastian Fine pair | unknown (EF version not local) | yes (Revision 3 via ZIP) | **pair missing or uncertain** | Clean baseline available for false-positive profiling; EF-annotated version requires archive extraction |
| Archive-only EF files (10) | not verified | no clean counterparts tracked | **needs commented file extraction** | Require Google Drive RAR extraction; comment extractability unknown until verified locally |

**Pairs ready for auditor-vs-expert comparison now:** **2** (Cibaku Elson 1st Review, Yin Haotian 2nd Review)

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

From `docs/evaluation/ef_overlap_after_p063_evaluation.md` (last formal EF overlap refresh):

| EF category | EF comment count (Cibaku / Yin Haotian) | Tool coverage after P068 | Gap assessment |
|---|---|---|---|
| unclear_or_other | 53 / 35 | not addressable deterministically | semantic/editorial feedback; out of scope for deterministic rules |
| references_citations | 5 / 4 | 0 / 0 on comparison PDFs | P064 implemented but 0 findings on extractable comparison PDFs; style semantics remain manual |
| committee_approval_page | 3 / 2 | 0 / 0 on comparison PDFs | P068 adds structural checks; 3 findings on Sebastian Fine + Yin H 4th only; comparison PDFs skipped at heading gate |
| table_format | 1 / 6 | partial (P017, P035) | EF feedback on table formatting often semantic/editorial |
| heading_title | 11 / 6 | 1 / 1 | P014/P020/P027/P038 cover structure; many EF heading comments are phrasing/editorial |
| list_of_tables_figures_toc | 0 / 4 | 0 / 0 on comparison PDFs | P030–P062 expand coverage; remains sparse on comparison PDFs |

**Note:** P064–P068 were implemented after the P063-era EF overlap refresh. A post-P068
EF overlap refresh is needed to measure whether `references_citations` and
`committee_approval_page` coverage improved on the two extractable-comment PDFs.

### Which P-rules were already refined from EF overlap

| Round | Rule(s) affected | Change | Outcome |
|---|---|---|---|
| Round 1 | P013 | Page-level grouping; one warning per page with candidates; structured triage fields | Reduced count noise; page coverage and EF-overlap unchanged |
| Round 2 | P018, P024 | Expanded TOC/List heading variant detection (trailing punctuation, CONTINUED suffixes) | No count change on current extractable PDFs; improved robustness for variant headings |

### Rules implemented from EF-overlap backlog (P064–P068)

| Rule | Category | P068-era five-PDF findings | EF overlap impact (preliminary) |
|---|---|---:|---|
| P064 | references_citations structural | 0 | No findings on comparison PDFs; gate skips on 3/5 files |
| P065 | dedication centering/italic | 0 | All 5 files skipped at DEDICATION heading gate |
| P066 | Bio Sketch degree ordering | 0 | 3/5 skipped at BIOGRAPHICAL SKETCH gate |
| P067 | Bio Sketch publication ordering | 0 | 0/5 reached qualifying Publications boundary |
| P068 | Approval Page committee blocks | 3 | New `committee_approval_page` category (3 findings); comparison PDFs skipped at gate |

### Remaining gaps guiding P069+

1. **Shared front-matter heading gate recall (P069 — scoped)** — repeated 3/5 skip pattern
   across P065–P068; infrastructure refinement before additional front-matter content rules.
2. **LoT/LoF entry extraction recall** — P059–P062 ordering rules find sparse comparable
   entries on compressed/multi-column PDFs; separate parser track from heading gates.
3. **References/citations structural recall** — P064 implemented but zero findings on
   comparison PDFs; heading/entry detection gates may need refinement.
4. **EF overlap refresh after P068** — re-run page/category overlap on the two extractable
   PDFs to measure P064–P068 impact.
5. **Expand extractable-comment set** — Sebastian Fine EF version and archive-only PDFs
   would improve metric stability across document styles.

---

## 7. Recommended Recurring Evaluation Workflow

This workflow should be run after every 3–5 new rules implemented.

### Step 1 — Run full auditor on evaluation PDFs

```bash
# Run on all four tracked EF-commented PDFs plus Sebastian Fine clean baseline
# (extract clean baseline from tracked ZIP into a gitignored local path first)
python -m njit_auditor pdf \
    "data/raw/ester/250218 Cibaku Elson First Review.pdf" \
    "data/raw/ester/260415 Yin H _2nd_review with EF Comments.pdf" \
    "data/raw/ester/Yin_Haotian_Second_R_with_EF_Feedback.pdf" \
    "data/raw/ester/Yin_H_4th_Review_with_EF_comments_compressed.pdf" \
    data/evaluation/generated/post_PXXX_snapshot/extracted/sebastian_fine_clean.pdf \
    --json-out data/evaluation/generated/post_PXXX_snapshot/ \
    --md-out data/evaluation/generated/post_PXXX_snapshot/
```

- Do NOT commit the generated JSON/MD outputs.

### Step 2 — Extract expert comments from extractable-comment PDFs

```python
from pathlib import Path
from njit_auditor.pdf_comments import extract_pdf_annotations

for pdf in [
    Path("data/raw/ester/250218 Cibaku Elson First Review.pdf"),
    Path("data/raw/ester/Yin_Haotian_Second_R_with_EF_Feedback.pdf"),
]:
    annotations = extract_pdf_annotations(pdf)
    # Write to gitignored path; aggregate counts only in committed docs
```

- Only run on PDFs with `comment_status: extractable`.
- Do NOT attempt extraction on flattened/compressed PDFs.

### Step 3 — Compare by page/category/rule

```bash
python scripts/evaluate_current_ef_comment_overlap.py
```

- Adjust `ComparisonInput` paths to point to the new snapshot directory.
- Outputs go to `data/evaluation/generated/` (gitignored).

### Step 4 — Produce privacy-safe aggregate doc

- From the generated overlap summary JSON, write a new
  `docs/evaluation/ef_overlap_after_PXXX_evaluation.md` with:
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
  baseline; update the current canonical baseline only when a verified full five-PDF rerun is
  available (currently `5d8ebaf` / 1,590 at P068-era).

---

## 8. Next Actions

### Immediate

1. **EF overlap after P071 complete** — See `docs/evaluation/ef_overlap_after_p071_evaluation.md`.
   P064 now reaches 2/2 comparison PDFs; `references_citations` gap unchanged (9 EF, 0 tool).
   Prior baseline: `docs/evaluation/ef_overlap_after_p068_evaluation.md`.

2. **Implement P069 heading gate recall** — Scoped infrastructure refinement to reduce repeated
   P065–P068 skip pattern; see
   `docs/planning/p069_frontmatter_heading_gate_recall_refinement_scope_and_design.md`.

### Near-term (expand EF overlap set)

3. **Verify Sebastian Fine EF-annotated version** — Extract `250128 Sebastian.Fine Revised 1st
   Dissertation Draft EF.pdf` from the original Google Drive RAR locally. If annotation-based
   comments are extractable, add it to the EF overlap comparison. This would expand the
   extractable comparison set from 2 files to 3.

4. **Assess archive-only EF PDFs for extractability** — Extract one or two additional archive
   files (e.g., Pennock or Kang) locally and test comment extraction. If extractable, they can
   be added to the EF overlap comparison set, improving metric stability across document styles.
   Keep extracted files in gitignored local paths; do not commit.

### Longer-term

5. **Per-category precision/recall tracking** — After each EF overlap refresh, record the
   per-category overlap improvement in a running comparison doc. This enables data-driven
   prioritization of P069+ rules.

6. **Improve ordering rule entry extraction** — P059–P062 consistently find 0 comparable
   entries on compressed/multi-column PDFs. Before implementing additional ordering rules,
   investigate whether shared extraction improvements can increase comparable-entry yield.

---

## Cross-References

- Machine-readable manifest: `data/processed/evaluation_data_manifest.json`
- Evaluation data inventory: `docs/status/data_inventory_and_evaluation_sources.md`
- Evaluation data manifest (human-readable): `docs/status/evaluation_data_manifest.md`
- Ester materials catalog: `docs/sources/ester_materials.md`
- EF comment-vs-tool comparison (P001–P029 scope): `docs/evaluation/current_ef_comment_vs_tool_comparison.md`
- EF overlap after P063: `docs/evaluation/ef_overlap_after_p063_evaluation.md`
- EF overlap after P068: `docs/evaluation/ef_overlap_after_p068_evaluation.md`
- P068-era full five-PDF snapshot: `docs/evaluation/current_auditor_after_p068_evaluation.md`
- EF overlap round 1 refinement: `docs/evaluation/ef_overlap_driven_refinement_evaluation.md`
- EF overlap round 2 refinement: `docs/evaluation/ef_overlap_refinement_round2_evaluation.md`
- P069 scope (next infrastructure task): `docs/planning/p069_frontmatter_heading_gate_recall_refinement_scope_and_design.md`
- Project state and next steps: `docs/status/current_project_state_and_next_steps.md`
- EF overlap comparison script: `scripts/evaluate_current_ef_comment_overlap.py`
- EF comment extraction utility: `scripts/evaluate_ester_pdf_comments.py` (hardcoded demo; use `njit_auditor.pdf_comments.extract_pdf_annotations` for general extraction)
