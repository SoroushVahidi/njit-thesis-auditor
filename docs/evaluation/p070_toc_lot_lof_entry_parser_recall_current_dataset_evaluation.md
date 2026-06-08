# P070 TOC/LoT/LoF Entry Parser Recall — Current-Dataset Evaluation

- **Date:** 2026-06-08
- **Baseline commit:** `f0d8294` (merge PR #252 — P070 implemented)
- **Comparator baseline:** P069-era five-PDF aggregate (`e045817`; 1,590 findings)
- **Auditor scope:** P001–P070 implemented
- **P070 type:** Infrastructure-only (`infrastructure_refinement`); no standalone findings
- **Validation:** ruff clean, mypy 87 source files, **988 pytest** passed
- **Privacy:** Aggregate-only reporting; no TOC/LoT/LoF entry text quoted
- **Generated outputs (gitignored):** `data/evaluation/generated/p070_evaluation/`

---

## Purpose

Measure parser-reach and dependent-rule impact of P070 on the documented five-PDF
evaluation set. Compare post-P070 parser entry counts against pre-P070 parser semantics
(`69e9beb` comparator) and post-P070 full-audit totals against the documented P069-era
aggregate.

---

## Five-PDF accessibility

| File label | Accessible | Auditable | TOC detected | LoT detected | LoF detected | Notes |
|---|---|---|---|---|---|---|
| Cibaku Elson 1st Review | Yes | Yes | No | No | No | Tracked PDF |
| Yin H 2nd Review (flattened) | Yes | Yes | No | No | No | Tracked PDF |
| Yin Haotian 2nd Review | Yes | Yes | No | No | No | Tracked PDF |
| Yin H 4th Review (compressed) | Yes | Yes | Yes (3 pp.) | Yes (1 p.) | Yes (3 pp.) | Tracked PDF |
| Sebastian Fine clean baseline | Yes | Yes | Yes (1 p.) | Yes (1 p.) | Yes (1 p.) | Extracted from tracked ZIP locally; not committed |

All five PDFs were accessible. Sebastian Fine was extracted from
`data/raw/ester/Dissertations with no Feedback -20260529T012213Z-3-001.zip` into the
gitignored `p070_evaluation/` folder.

---

## Parser entry recall (pre-P070 vs post-P070)

Comparator uses pre-P070 `extract_toc_entry_lines()` semantics from commit `69e9beb`.
Counts are aggregate entry totals on detected TOC/LoT/LoF pages only.

| File label | Pre-P070 entries | Post-P070 entries | Delta |
|---|---:|---:|---:|
| Cibaku Elson 1st Review | 0 | 0 | 0 |
| Yin H 2nd Review (flattened) | 0 | 0 | 0 |
| Yin Haotian 2nd Review | 0 | 0 | 0 |
| Yin H 4th Review (compressed) | 166 | 145 | −21 |
| Sebastian Fine clean baseline | 19 | 22 | +3 |
| **Five-PDF total** | **185** | **167** | **−18** |

On Yin H 4th, post-P070 counts are lower because repeated-heading skips and prose-like
line guards reject false positives that the pre-P070 parser accepted. On Sebastian Fine,
prefix-tolerant gates recover additional short entries (+3).

---

## Parser recovery mechanism counts (five-PDF aggregate)

| Recovery mechanism | Count |
|---|---:|
| Multi-line merge (`is_wrapped=True`) | 4 |
| Split page-number pairing (entry gained token vs pre-P070) | 4 |
| Prefix-tolerant gates (new entry keys only in post-P070) | 9 |
| Page runs (`group_toc_page_runs()`) | 7 |
| Multi-page runs | 2 |

All recovery counts occur on Yin H 4th Review (compressed) and/or Sebastian Fine clean
baseline — the only files with detected TOC/LoT/LoF pages.

---

## Post-P070 full-audit aggregate vs P069-era baseline

| Metric | P069-era | Post-P070 | Delta |
|---|---:|---:|---:|
| Total findings (5-PDF) | 1,590 | 1,543 | −47 |
| `list_of_tables_figures_toc` category | 130 | 84 | −46 |

Per-file total findings: Cibaku 325 (0), Yin H 2nd flat 281 (0), Yin Haotian 2nd 346 (0),
Yin H 4th comp 580→532 (−48), Sebastian Fine 58→59 (+1).

---

## Affected rule finding-count deltas (P069-era → post-P070)

| Rule / category | P069-era | Post-P070 | Delta |
|---|---:|---:|---:|
| P036 | 77 | 55 | −22 |
| P040 | 13 | 1 | −12 |
| P018 | 19 | 13 | −6 |
| P024 | 12 | 10 | −2 |
| P048 | 1 | 0 | −1 |
| P049 | 1 | 0 | −1 |
| P053 | 2 | 1 | −1 |
| P054 | 1 | 0 | −1 |
| P058 | 1 | 0 | −1 |
| P027–P032, P046, P055–P056, P059–P062 | unchanged | unchanged | 0 |

All deltas occur on Yin H 4th Review (compressed), which is the only file with dense
TOC/LoT/LoF text-layer content on this dataset. P070 infrastructure emits no standalone
findings; dependent-rule decreases reflect fewer spurious parsed entries feeding spacing,
alignment, and punctuation checks — not a rollback of P070 parser intent.

---

## `list_of_tables_figures_toc` interpretation

Category total fell from 130 to 84 (−46), driven almost entirely by Yin H 4th (−48 file
delta in total findings, with P036 −22 and several smaller TOC/LoF rule decreases).
Cibaku and Yin Haotian 2nd Review — the EF-overlap comparison PDFs — still show **zero**
TOC/LoT/LoF pages detected and **zero** `list_of_tables_figures_toc` findings. EF-overlap
gaps for `list_of_tables_figures_toc` on the two extractable-comment PDFs are **not
expected to change** from P070 on this dataset.

---

## EF-overlap expectation

No EF-overlap refresh is required for P070 alone: comparison PDFs (Cibaku, Yin Haotian)
have no detected TOC/LoT/LoF pages and no category findings before or after P070. Parser
changes on Yin H 4th do not affect the two-file EF-overlap set.

---

## Generated outputs

Gitignored local artifacts under `data/evaluation/generated/p070_evaluation/`:

- `p070_parser_recall_summary.json` — aggregate parser and audit summary
- `aggregate.json` — post-P070 five-PDF rule/category totals
- Per-file audit JSON (`cibaku.json`, `yin_h_2nd_flat.json`, etc.)
- `sebastian_fine.extracted.pdf` — ephemeral ZIP extraction (not committed)

Do not commit generated JSON/Markdown/PDF files.

---

## Privacy protections

- No TOC/LoT/LoF entry titles, figure/table captions, chapter text, author names, or EF
  comment text quoted.
- Reporting uses safe file labels, page counts, booleans, aggregate entry counts, and rule
  IDs only.
- Generated per-file audit JSON remains gitignored.

---

## Limitations

- No OCR; image-only list pages remain undetectable (3/5 files show no TOC/LoT/LoF pages).
- Parser recall depends on PDF text-layer quality; compressed/flattened layouts may still
  under-detect pages or entries.
- Pre-P070 comparator reimplements `69e9beb` parser semantics locally; it is not a git
  checkout rerun.
- Small five-PDF sample; zero deltas on a file do not prove compliance.
- Entry-count decreases on Yin H 4th reflect conservative false-positive rejection as well
  as recall improvements; net entry delta is −18 on the two files with list pages.
- P061/P062 remain 0 — no qualifying cross-page comparable sequences despite LoF page
  detection on Yin H 4th.

---

## Cross-references

- Synthetic validation: `docs/evaluation/p070_toc_lot_lof_entry_parser_recall_synthetic_validation.md`
- P070 scope: `docs/planning/p070_toc_lot_lof_entry_parser_recall_refinement_scope_and_design.md`
- P069-era aggregate baseline: `docs/evaluation/current_auditor_after_p069_evaluation.md`
