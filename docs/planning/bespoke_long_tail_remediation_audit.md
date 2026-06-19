# Bespoke Long-Tail Remediation Audit — 2026-06-19

**Branch:** `fix/bespoke-long-tail-remediations`  
**Baseline:** `main` @ `028585571c402413c8205815c73e3797c845bbc0`  
**Scope:** Presentation-layer wording only (`polished_comments.py`, `finding_explanations.py`, `issue_type_explanations.py`, tests).

---

## 1. Summary

This pass upgrades **39 high-impact `(rule_id, issue_type)` pairs** from the improved generic safety-net wording (`This check (P…) found a possible … issue`) to bespoke, student-facing remediation templates aligned with Ester's one-check/one-remediation approach.

No detector thresholds, rule IDs, canonical rule JSON, highlight policy, problem numbering, or PDF action behavior were changed.

---

## 2. Priority method

Issue types were prioritized by:

1. **Frequency / visibility in sample audits** — captions (P017), figure/table layout (P035), TOC/LoT/LoF alignment and formatting (P018, P024, P039, P053–P055, P058, P060) appear often on student-facing front matter and body pages.
2. **Ester YES/NO matrix alignment** — front-matter structure (P025 graduation month, P041 dedication header, P043/P044 paragraph indentation, P068 approval page blocks).
3. **Generic wording risk** — issue types whose humanized fallback produced awkward phrasing (e.g. "possible possible sentence case issue issue").
4. **Safe heuristics** — only issue types where the detector signal supports specific observed/expected/fix guidance without quoting dissertation body text.

---

## 3. Upgraded issue types (39)

| Rule | Issue type | Matrix / category tie-in |
|---|---|---|
| P015 | `unexpected_opening_indent` | Body indentation (EF overlap: indentation) |
| P015 | `missing_later_indent` | Body indentation |
| P017 | `unexpected_terminal_period` | Captions / list punctuation |
| P017 | `missing_terminal_punctuation` | Captions / list punctuation |
| P017 | `possible_sentence_case_issue` | Captions |
| P017 | `possible_title_case_issue` | Captions |
| P018 | `misaligned_page_number_column` | TOC/LoT/LoF alignment |
| P018 | `missing_page_number` | TOC/LoT/LoF alignment |
| P018 | `inconsistent_leader_dots` | TOC/LoT/LoF alignment |
| P018 | `inconsistent_hierarchy_indent` | TOC/LoT/LoF alignment |
| P021 | `abstract_word_count_exceeded` | Abstract length (matrix) |
| P024 | `toc_level_capitalization` | TOC capitalization |
| P024 | `list_of_tables_title_case` | LoT title case |
| P024 | `list_of_figures_sentence_case` | LoF sentence case |
| P024 | `unexpected_terminal_punctuation` | TOC/LoT/LoF punctuation |
| P025 | `title_page_graduation_month_invalid` | Title page graduation month |
| P035 | `table_caption_not_above_body` | Figure/table layout |
| P035 | `figure_caption_not_below_body` | Figure/table layout |
| P035 | `table_body_not_centered` | Figure/table layout |
| P035 | `figure_body_not_centered` | Figure/table layout |
| P039 | `toc_l2_not_indented_relative_to_l1` | TOC hierarchy indent |
| P039 | `toc_l3_not_indented_relative_to_l2` | TOC hierarchy indent |
| P040 | `lof_entry_missing_terminal_punctuation` | LoF terminal punctuation |
| P041 | `dedication_top_margin_header_text` | Dedication header text |
| P043 | `acknowledgements_first_paragraph_indented` | Acknowledgements indent |
| P043 | `acknowledgements_subsequent_paragraph_not_indented` | Acknowledgements indent |
| P044 | `abstract_first_paragraph_indented` | Abstract indent |
| P044 | `abstract_subsequent_paragraph_not_indented` | Abstract indent |
| P053 | `lot_entry_has_terminal_period` | LoT terminal period |
| P054 | `toc_entry_has_terminal_period` | TOC terminal period |
| P055 | `lot_entry_is_figure` | LoT/LoF entry type |
| P055 | `lof_entry_is_table` | LoT/LoF entry type |
| P058 | `toc_page_numbers_not_nondecreasing` | TOC page-number order |
| P060 | `toc_entry_numbers_not_nondecreasing` | TOC section-number order |
| P064 | `references_section_heading_not_detected` | References structure |
| P064 | `references_entry_indentation_inconsistent` | References structure |
| P064 | `references_entry_spacing_inconsistent` | References structure |
| P068 | `approval_page_advisor_role_label_missing` | Approval page (matrix Q013 area) |
| P068 | `approval_page_signature_blocks_sparse` | Approval page (matrix Q013 area) |

---

## 4. Remaining generic issue types (deferred)

Roughly **47 `(rule_id, issue_type)` pairs** still use the generic polished-comment safety net (rule-level catalog remediation appended, no banned "Formatting check … flagged issue type" phrase). Deferred because they are lower volume, infrastructure-only, experimental, or need additional detector detail keys before safe bespoke wording:

- **LoT/LoF column header alignment family** (P031, P049, P050, P056, P057, P061) — many subtypes share layout geometry signals; needs volume triage before one-remediation splitting.
- **Biographical Sketch family** (P045, P047, P066, P067) — ordering/spacing heuristics with sparse detail keys.
- **Copyright refinements** (P051, P052 duplicates of P034 subtypes) — overlap with existing P034 bespoke coverage.
- **Appendix TOC format** (P042) — overlaps P063 appendix heading rules.
- **Wrapped list spacing** (P032) — lower student confusion risk.
- **Experimental / infrastructure rules** (P069–P073, P076+) — not shown on public web UI.

Future docs cleanup (out of scope for this PR): `docs/planning/finding_actionability_matrix.md` and `data/processed/rules/njit_rule_inventory.json` remain stale planning artifacts.

---

## 5. Example improved wording

**Before (P017 `unexpected_terminal_period`):**
> Review needed: This check (P017) found a possible unexpected terminal period in caption issue on page 5. …

**After:**
> Review needed: Likely problem: A table caption on page 5 appears to end with a terminal period where NJIT expects no ending punctuation for this caption type. Remove the trailing period unless the caption is written as a full sentence that requires one. …

**Before (P068 `approval_page_advisor_role_label_missing`):**
> Review needed: This check (P068) found a possible approval page advisor role label missing issue on page 5. …

**After:**
> Review needed: Problem: The Approval Page on page 5 may be missing a recognizable advisor role label (for example, 'Dissertation Advisor' or 'Major Professor'). Add the required advisor role label. …

---

## 6. Validation

| Check | Result |
|---|---|
| `ruff check .` | passed |
| `mypy src` | passed (93 source files) |
| `python -m pytest -q` | **1736 passed, 1 warning** |
| New tests | `tests/test_bespoke_long_tail_remediations.py` (120 parametrized assertions + action-label regression) |

The single warning is the intentional duplicate-member ZIP test in `test_upload_handling.py`.

---

## 7. Recommended next action

Mark stale planning docs as historical/refreshed, then rebase PR #305 if stale-PR cleanup is still desired.
