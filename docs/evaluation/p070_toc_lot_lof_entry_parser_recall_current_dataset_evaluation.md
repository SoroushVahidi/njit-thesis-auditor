# P070 TOC/LoT/LoF Entry Parser Recall — Current-Dataset Evaluation

- **Date:** 2026-06-08
- **Baseline commit:** `69e9beb` (post PR #251 — P070 scope)
- **Implementation commit:** same PR as P070 implementation
- **Auditor scope:** P001–P070 implemented
- **Validation:** ruff clean, mypy 87 source files, **988 pytest** passed
- **Privacy:** Aggregate-only reporting; no entry text quoted.

---

## Status

**Not run in this workspace.** The five documented evaluation PDFs are not present
under `data/raw/ester/` in the current working tree. A privacy-safe before/after
parser-reach evaluation is **pending** until those files (or archive extraction paths)
are available locally.

Generated outputs would live under `data/evaluation/generated/p070_evaluation/` (gitignored).

---

## Planned evaluation (when PDFs are available)

| Metric | Method |
|---|---|
| TOC/LoT/LoF pages detected | `detect_toc_like_pages()` per safe file label |
| Entries per page | `len(extract_toc_entry_lines())` aggregate counts only |
| Wrapped recoveries | Count entries with `is_wrapped=True` |
| Split-column recoveries | Count entries gaining `page_number_token` after pairing |
| Dependent-rule deltas | Before/after finding counts for P036, P046, P058–P062 |
| Category delta | `list_of_tables_figures_toc` aggregate on five-PDF set |
| EF overlap | Re-run two-file comparison if category counts change |

---

## Expected interpretation

- Parser recall improvements may increase dependent-rule reach on wrapped/split-column layouts.
- Zero delta on comparison PDFs would not prove EF comments were incorrect — text-layer
  and image-only limitations may persist.
- Full five-PDF aggregate rerun is recommended only if dependent-rule totals change.

---

## Cross-references

- Synthetic validation: `docs/evaluation/p070_toc_lot_lof_entry_parser_recall_synthetic_validation.md`
- P070 scope: `docs/planning/p070_toc_lot_lof_entry_parser_recall_refinement_scope_and_design.md`
- Post-P069 aggregate baseline: `docs/evaluation/current_auditor_after_p069_evaluation.md` (1,590 findings)
