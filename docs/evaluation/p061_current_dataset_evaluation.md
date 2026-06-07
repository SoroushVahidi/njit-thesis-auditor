# P061 Current-Dataset Evaluation — LoT/LoF Cross-Page Entry-Number Ordering

- **Date:** 2026-06-07
- **Rule:** P061 — LoT/LoF cross-page entry-number ordering check
- **Planned module:** `src/njit_auditor/rules/pdf_lot_lof_cross_page_entry_ordering.py`
- **Baseline main at evaluation time:** `fcc9151` (PR #200 — docs refresh; P061 scoped only, not implemented)
- **Validation at evaluation time:** ruff, mypy, **729 pytest** passed
- **Evaluation type:** Structural inventory on all five evaluation PDFs; **formal P061 audit not run** (rule module absent)

## 1. Purpose and scope

Document a privacy-safe current-dataset assessment for P061 on the five evaluation PDFs
referenced in `data/processed/evaluation_data_manifest.json`. Because P061 is scoped but
**not implemented** on `main`, the PDF auditor cannot emit P061 findings. This note records:

1. File availability (including Sebastian Fine Revision 3 extracted locally from the tracked ZIP)
2. LoT/LoF page-run detection and comparable-entry metadata gathered with existing P059 parsing helpers
3. Why projected P061 counts are **0** under current gates

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

## 3. Formal P061 audit status

| Item | Status |
|---|---|
| P061 implemented on `main`? | **No** — scope doc only (`docs/planning/p061_scope_and_design.md`, PR #199) |
| `njit-audit pdf` P061 findings | **Not available** |
| Gitignored structural inventory | **Yes** — `data/evaluation/generated/p061_evaluation/structural_inventory.json` |

## 4. Structural inventory summary

Inventory logic mirrors planned P061 gates: consecutive same-type LoT/LoF page runs, combined
comparable entry numbers (P059 `_parse_entry_num` helper), skip mixed sequential+chapter-based
sections, require ≥2 pages, ≥3 combined comparable entries, and ≥2 inversions before a finding.

| File label | LoT runs | LoF runs | Comparable entries | Inversions | P061 count | Pages (LoT/LoF) | Notes |
|---|---:|---:|---:|---:|---:|---|---|
| Cibaku Elson 1st review | 0 | 0 | 0 | 0 | **N/A** | — | No LoT/LoF pages detected |
| Yin H 2nd review (flattened) | 0 | 0 | 0 | 0 | **N/A** | — | No LoT/LoF pages detected |
| Yin Haotian 2nd review | 0 | 0 | 0 | 0 | **N/A** | — | No LoT/LoF pages detected |
| Yin H 4th review (compressed) | 1 (single-page) | 2 (1 multi-page) | 0 | 0 | **N/A** | LoT p.14; LoF pp.15, 17–18 | Multi-page LoF run (pp.17–18) present but **0 comparable entries** (sparse text-layer extraction) |
| Sebastian Fine clean baseline | 1 (single-page) | 1 (single-page) | 0 | 0 | **N/A** | LoT/LoF each 1 page | Single-page sections only — outside P061 scope (requires ≥2 pages) |

**Projected P061 findings if implemented today:** **0** across all five files (no run met all
gates). **Formal P061 count:** **N/A** until the rule module is wired into the auditor.

### Outcome categories (conservative)

| Category | Files |
|---|---|
| No LoT/LoF pages detected | Cibaku, Yin H 2nd flat, Yin Haotian 2nd |
| LoT/LoF detected but single-page only | Sebastian (both); Yin H 4th LoT |
| Multi-page run but insufficient comparable entries | Yin H 4th LoF (pages 17–18; 0 parseable entries) |
| Comparable sequence with ≥2 cross-page inversions | **None** |
| P061 findings would emit | **None** (module absent; inventory gates not met) |

## 5. Related within-page ordering context (P059)

For reference, P059 (within-page LoT/LoF entry-number ordering) also produced **0** findings on
all five files when run with the current text-layer pipeline. This is consistent with sparse
LoT/LoF detection/extraction on several evaluation PDFs and does not prove compliance.

## 6. Interpretation

- **Does not prove compliance.** Zero projected P061 findings mainly reflect missing multi-page
  qualifying sequences and/or insufficient parseable entry numbers — not verified cross-page order.
- **Detection limits dominate.** Three of five PDFs had no detected LoT/LoF pages; Yin H 4th
  (compressed) shows a two-page LoF run but no comparable entries under P059 parsing gates.
- **Usefulness (preliminary):** P061 targets a real gap left by P059 (cross-page boundary
  inversions), but current-dataset signal is **low** until LoT/LoF text extraction improves and
  the rule is implemented.
- **Noise risk (design expectation):** Conservative gates (≥3 entries, ≥2 inversions, skip mixed
  formats) should limit false positives; cannot assess empirical FP rate without implementation.

## 7. Canonical aggregate status

| Metric | Value |
|---|---|
| Prior canonical five-PDF grand total (pre-P035 baseline) | **1,446** |
| `generated_for_commit` baseline | **`00b9c2d`** (unchanged) |
| P061 increment to canonical total | **None** — formal audit not run |

Do **not** update the **1,446** canonical total from this note.

## 8. Limitations

- P061 module not present; inventory is a pre-implementation structural probe only.
- Text-layer geometry only; compressed/flattened PDFs may under-detect LoT/LoF pages and entry numbers.
- Sebastian PDF extracted locally; not committed as a standalone tracked file.
- No OCR; no entry text quoted in this doc or gitignored JSON.
- Full auditor P061 issue-type mix unavailable until implementation lands.

## 9. Next steps

1. Implement P061 per `docs/planning/p061_scope_and_design.md`.
2. Re-run `njit-audit pdf` on all five evaluation PDFs; write outputs only under
   `data/evaluation/generated/p061_evaluation/`.
3. Refresh this doc with formal P061 finding counts and issue-type mix (aggregate only).

## 10. Related docs

- Design: `docs/planning/p061_scope_and_design.md`
- Within-page companion: `docs/evaluation/p059_current_dataset_evaluation.md`
- Synthetic validation (post-implementation): to be added with P061 implementation PR
