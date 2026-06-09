# Sebastian Fine EF Archive Recovery — Search and Status

- **Date:** 2026-06-09
- **Baseline commit:** `e3ca516` (PR #264 — post-P072 backlog and data strategy)
- **Auditor scope:** P001–P072 implemented; **1014 pytest**
- **Purpose:** Document the attempt to recover the Sebastian Fine EF-annotated dissertation PDF
  from locally available archives, per the primary recommendation in
  `docs/status/post_p072_backlog_and_data_strategy.md`.
- **Privacy:** Aggregate-only. No dissertation body text, author names, EF comment text, or other
  private content quoted. File metadata (sizes, member names) only.

---

## 1. Background

`docs/status/post_p072_backlog_and_data_strategy.md` identified data acquisition as the
highest-priority next step after P072: recovering the Sebastian Fine EF-annotated dissertation
PDF to expand the EF comparison set from **2** to potentially **3** extractable-comment files.

The current comparison set (Cibaku Elson 1st Review and Yin Haotian 2nd Review) is the main
bottleneck for all remaining EF gap analysis. A third file would improve metric stability and
potentially provide new data points for the `list_of_tables_figures_toc` category (4 EF comments,
0 tool findings), which is entirely from Yin Haotian.

---

## 2. Search Locations

The following locations were searched systematically:

| Location | Status |
|---|---|
| `data/raw/ester/` (tracked PDFs) | Searched — no Sebastian Fine EF version |
| `data/raw/ester/Dissertations with no Feedback -20260529T012213Z-3-001.zip` | Listed members — clean baseline only |
| `data/evaluation/generated/` (gitignored) | Searched — clean variants only, no EF-annotated version |
| `data/evaluation/private/` (gitignored) | Absent/empty |
| Home directory (`/home/soroush/`, depth ≤ 5) | Searched for `*sebastian*`, `*fine*`, `*EF*`, `*ester*`, `*dissertation*`, `*thesis*` — no match outside repo |
| System-level ZIP/RAR archives (home, depth ≤ 5) | No dissertation-related archives found outside repo |

---

## 3. What Was Found

### 3a. Tracked ZIP — clean baseline only

The only locally available Sebastian Fine artifact is the **clean/no-feedback baseline**:

| Item | Details |
|---|---|
| Archive | `data/raw/ester/Dissertations with no Feedback -20260529T012213Z-3-001.zip` |
| Archive member | `Dissertations with no Feedback /Sebastian.Fine Revised 1st Dissertation Draft_Revision3.pdf` |
| Uncompressed size | 331,787 bytes |
| Category | Clean baseline — no EF comments |
| EF annotations | None (no-feedback archive by definition) |
| Already used in evaluation | Yes — five-PDF aggregate (29-page baseline); audit finding counts in all canonical snapshots |

This file is the **Revision 3** clean version. It is not an EF-annotated/reviewed document.

### 3b. Tracked EF PDFs — no Sebastian Fine EF version

The four tracked EF-commented PDFs in `data/raw/ester/` are:

| Label | Size | EF comment status |
|---|---|---|
| Cibaku Elson 1st Review | 5,694,327 bytes | extractable (78 annotations) |
| Yin H 2nd Review (flattened) | 16,674,405 bytes | flattened (0 extractable) |
| Yin Haotian 2nd Review | 16,774,267 bytes | extractable (65 annotations) |
| Yin H 4th Review (compressed) | 1,420,387 bytes | compressed/flattened (0 extractable) |

No Sebastian Fine EF-annotated version is among the tracked files.

### 3c. Generated/cached paths — clean variants only

Multiple generated directories under `data/evaluation/generated/` contain extracted clean-baseline
copies of Sebastian Fine (from ZIP extraction for evaluation runs). All are labeled `clean`,
`clean_baseline`, or `revision3` variants. None are EF-annotated.

### 3d. No original-archive RAR found locally

The `docs/sources/ester_materials.md` and manifest reference a **Google Drive RAR archive** as the
original source bundle that contains additional EF-annotated dissertation PDFs (10 files) including
`250128 Sebastian.Fine Revised 1st Dissertation Draft EF.pdf`. This RAR is **not present** in any
locally searched location (repository tree, home directory, Downloads). It was not downloaded and
is not available for extraction without manual access to the original Google Drive bundle.

---

## 4. Recovery Status: BLOCKED

| Question | Answer |
|---|---|
| Is the Sebastian Fine EF-annotated PDF locally available? | **No** |
| Is the clean baseline locally available? | Yes (ZIP-contained; already used in evaluation) |
| Is the original Google Drive RAR present locally? | **No** |
| Can recovery proceed without external action? | **No** |
| Blocker type | External archive access required (no network calls; manual retrieval needed) |

**Root cause:** The EF-annotated version (`250128 Sebastian.Fine Revised 1st Dissertation Draft EF.pdf`)
exists only in the original Google Drive RAR bundle. This bundle is not committed and was not
downloaded to any locally searchable path on this machine. Recovery requires the repository owner to
manually download the original archive from Google Drive and either:
1. Extract the EF PDF locally to `data/evaluation/private/` (gitignored), or
2. Confirm the file does not exist or is inaccessible in the current archive

---

## 5. Comparison Set Remains at 2 Files

Because the Sebastian Fine EF PDF is not locally available, the comparison set for EF-overlap
evaluation remains:

| File | EF comment status | Used in overlap |
|---|---|---|
| Cibaku Elson 1st Review | 78 extractable | Yes |
| Yin Haotian 2nd Review | 65 extractable | Yes |

**Total EF annotations:** 143 (unchanged)  
**Comparison set size:** 2 extractable-comment PDFs (unchanged from P072 era)

---

## 6. What External/Manual Action Is Needed

To unblock the Sebastian Fine EF recovery:

1. **Access the original Google Drive archive.** The bundle is referenced in `docs/sources/ester_materials.md`
   and was the original source for files currently in `data/raw/ester/`. The RAR must be downloaded
   manually — no external network calls are made by the auditor.
2. **Extract locally to `data/evaluation/private/`** (gitignored path) — do not commit the PDF.
3. **Run annotation extraction** using `njit_auditor.pdf_comments.extract_pdf_annotations` to count
   annotations and verify extractability.
4. **If extractable:** run the three-file EF-overlap evaluation (aggregate counts only; no comment
   text); document results in `docs/evaluation/ef_overlap_with_sebastian_fine_evaluation.md`.
5. **If not extractable (flattened/compressed):** update this doc accordingly and document the
   definitive comparison-set constraint.

---

## 7. Future Evaluation Plan (If Recovery Succeeds)

When the EF-annotated PDF becomes available locally:

- **Branch:** `docs/ef-overlap-with-sebastian-fine`
- **Comparison set:** 3 extractable-comment PDFs (Cibaku, Yin Haotian, Sebastian Fine)
- **Key question:** Does Sebastian Fine have detected LoT/LoF list pages? If yes, test whether
  `list_of_tables_figures_toc` gap closes or narrows.
- **Generated outputs:** `data/evaluation/generated/ef_overlap_with_sebastian_fine/` (gitignored)
- **All reporting:** aggregate counts only — no comment text, no dissertation body text
- **Privacy constraint:** Sebastian Fine EF PDF stays in `data/evaluation/private/` — never committed

---

## 8. Generated Output Path

No generated outputs were produced by this recovery attempt (no file extraction occurred — the
target file was not locally present). The path `data/evaluation/generated/sebastian_fine_recovery/`
was not created.

---

## 9. Privacy and Caveats

- No dissertation body text, EF comment text, names, or private content quoted.
- File metadata (sizes, member names) reported only for non-private archive structure verification.
- Real dissertation files remain in `data/raw/ester/` (tracked, high privacy risk).
- Generated and private paths remain gitignored and uncommitted.
- No OCR was performed. No external network calls were made.

---

## Cross-References

- Post-P072 backlog and strategy: `docs/status/post_p072_backlog_and_data_strategy.md`
- Real thesis pairing readiness: `docs/evaluation/real_thesis_pairing_and_ef_overlap_readiness.md`
- Data inventory: `docs/status/data_inventory_and_evaluation_sources.md`
- EF overlap (current, P072 era): `docs/evaluation/ef_overlap_after_p072_evaluation.md`
- Original-archive catalog: `docs/sources/ester_materials.md`
- Evaluation data manifest: `docs/status/evaluation_data_manifest.md`
