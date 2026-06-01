# P035 Current Dataset Evaluation (Local Subset)

- **Date:** 2026-06-01
- **Implementation commit:** `c31dfd5` (PR #83 — P035 figure/table body layout)
- **Auditor scope:** P001–P035 (P035 only reported here)
- **Evaluation type:** **Local four-PDF subset** — not a canonical five-PDF aggregate rerun

## 1. Purpose and scope

Document a **local post-implementation audit** of P035 on the four evaluation PDFs
available in the workspace at refresh time. This is **not** a replacement for the
canonical full five-PDF snapshot at `docs/evaluation/current_auditor_after_p034_evaluation.md`
(**1,446** total findings, baseline `00b9c2d`, pre-P035 detection counts).

Reporting is **aggregate-only**. No caption text, figure/table body text, author names,
title text, or dissertation prose is quoted.

Generated JSON/MD under `data/evaluation/generated/` were **not** committed.

## 2. Files evaluated (4 available)

| File label | P035 findings |
|---|---:|
| Cibaku Elson 1st review | 0 |
| Yin H 2nd review (flattened) | 0 |
| Yin Haotian 2nd review | 0 |
| Yin H 4th review (compressed) | **13** |

**Subset total:** **13** P035 findings (all on Yin H 4th compressed).

Sebastian Fine clean baseline (fifth PDF in the canonical five-PDF set) was not rerun in
this local subset pass.

## 3. Issue-type mix (flagged pages only)

| `issue_type` | Count |
|---|---:|
| `figure_caption_not_below_body` | 7 |
| `table_caption_not_above_body` | 5 |
| `table_body_not_centered` | 1 |
| `figure_body_not_centered` | 0 |

## 4. Interpretation

- P035 v1 checks **text-layer** float bodies only; **image-only figures are skipped**.
- Zero findings on three PDFs may reflect skips (no confident adjacent text-layer body
  clusters) as much as compliance.
- Yin H 4th compressed concentrates P035 warnings — consistent with dense caption/body
  text-layer signal on that file; manual review still required.

## 5. Canonical aggregate status

| Metric | Value |
|---|---|
| Prior canonical five-PDF grand total (pre-P035) | **1,446** |
| Full canonical P001–P035 rerun performed? | **No** |
| This doc's subset P035 increment | **+13** (Yin H 4th only; 4/5 PDFs checked) |

Do **not** add 13 to 1,446 as an updated canonical total until a full five-PDF P001–P035
audit is rerun, documented, and (if appropriate) written to a new gitignored generated path
(e.g. `data/evaluation/generated/current_auditor_after_p035/`).

## 6. Related docs

- Synthetic validation: `docs/evaluation/p035_figure_table_layout_synthetic_validation.md`
- Design: `docs/planning/p035_scope_and_design.md`
- Canonical pre-P035 snapshot: `docs/evaluation/current_auditor_after_p034_evaluation.md`
