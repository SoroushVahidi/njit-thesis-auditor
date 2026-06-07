# P061 Current-Dataset Evaluation — LoT/LoF Cross-Page Entry-Number Ordering

- **Date:** 2026-06-07
- **Rule:** P061 — LoT/LoF cross-page entry-number ordering check
- **Module:** `src/njit_auditor/rules/pdf_lot_lof_cross_page_entry_ordering.py`
- **Implementation commit:** `82e8361` (PR #202)
- **Validation at evaluation time:** ruff, mypy, **744 pytest** passed
- **Evaluation type:** Formal post-implementation audit on all five evaluation PDFs (local subset; not a canonical five-PDF P001–P061 aggregate rerun)

## 1. Purpose and scope

Document a privacy-safe current-dataset evaluation of P061 after implementation. PR #201
recorded a pre-implementation structural inventory when the rule module was absent. This note
reports formal P061 findings from `check_pdf_lot_lof_cross_page_entry_ordering()` on the five
evaluation PDFs in `data/processed/evaluation_data_manifest.json`.

Reporting is **aggregate/metadata-only**. No entry text, captions, dissertation body text, title
text, author names, or committee names are quoted.

Generated outputs under `data/evaluation/generated/p061_evaluation/` were **not** committed.

## 2. Evaluation PDFs (5 available)

| File label | Access |
|---|---|
| Cibaku Elson 1st review | Tracked standalone PDF |
| Yin H 2nd review (flattened) | Tracked standalone PDF |
| Yin Haotian 2nd review | Tracked standalone PDF |
| Yin H 4th review (compressed) | Tracked standalone PDF |
| Sebastian Fine clean baseline | Extracted locally from tracked ZIP to gitignored `.extracted/` path |

## 3. Formal P061 audit results

| File label | LoT pages | LoF pages | Multi-page LoT runs | Multi-page LoF runs | P061 count | Pages | Notes |
|---|---:|---:|---:|---:|---:|---|---|
| Cibaku Elson 1st review | 0 | 0 | 0 | 0 | **0** | — | No LoT/LoF pages detected |
| Yin H 2nd review (flattened) | 0 | 0 | 0 | 0 | **0** | — | No LoT/LoF pages detected |
| Yin Haotian 2nd review | 0 | 0 | 0 | 0 | **0** | — | No LoT/LoF pages detected |
| Yin H 4th review (compressed) | 1 | 3 | 0 | 1 | **0** | — | One 2-page LoF run (pp. 17–18); P061 gates not met (insufficient comparable entries and/or inversions) |
| Sebastian Fine clean baseline | 1 | 1 | 0 | 0 | **0** | — | Single-page LoT/LoF only — outside P061 scope |

**Subset total:** **0** P061 findings across five files.

**Issue-type mix:** none.

## 4. Outcome categories (conservative)

| Category | Files |
|---|---|
| No LoT/LoF pages detected | Cibaku, Yin H 2nd flat, Yin Haotian 2nd |
| LoT/LoF detected but no multi-page same-type run | Sebastian (single-page LoT and LoF) |
| Multi-page run present but P061 gates not met | Yin H 4th (2-page LoF run; sparse comparable entry extraction) |
| P061 findings emitted | **None** |

## 5. Interpretation

- **Does not prove compliance.** Zero findings mainly reflect missing multi-page qualifying
  sequences and/or insufficient parseable entry numbers on compressed/flattened PDFs.
- **Consistent with pre-implementation inventory (PR #201).** Formal P061 audit confirms the
  same structural picture once the rule module is wired.
- **Usefulness signal is low on this dataset.** P061 targets a real cross-page gap left by P059,
  but evaluation PDFs provide limited multi-page LoT/LoF text-layer signal.
- **Noise risk:** Cannot assess empirical false-positive rate from this run (no positive findings).

## 6. Canonical aggregate status

| Metric | Value |
|---|---|
| Prior canonical five-PDF grand total (pre-P035 baseline) | **1,446** |
| `generated_for_commit` baseline | **`00b9c2d`** (unchanged) |
| P061 increment to canonical total | **None** — local five-PDF P061-only subset, not a full P001–P061 canonical rerun |

Do **not** update the **1,446** canonical total from this note.

## 7. Limitations

- Text-layer geometry only; compressed/flattened PDFs may under-detect LoT/LoF pages and entry numbers.
- Sebastian PDF extracted locally; not committed as a standalone tracked file.
- Not a full `njit-audit pdf` P001–P061 aggregate rerun — P061 counts only.
- No OCR; no entry text quoted in this doc or gitignored JSON.

## 8. Related docs

- Design: `docs/planning/p061_scope_and_design.md`
- Within-page companion: `docs/evaluation/p059_current_dataset_evaluation.md`
- Synthetic tests: `tests/test_p061_lot_lof_cross_page_entry_ordering.py` (15 tests)
