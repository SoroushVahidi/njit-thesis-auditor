# P053 Scope and Design

- **Date:** 2026-06-04
- **Status:** **Implemented**
- **Baseline main:** `0f46dc9` (PR #156 — post-P052 documentation consistency; P001–P052 implemented)

---

## Current state

| Area | State |
|------|-------|
| P-rules | **53/53** implemented (`P001`–`P053`) |
| LoF terminal punctuation | **P040** — emits warning when LoF complete entries lack `.`/`?`/`!` (Q075); 9 synthetic tests |
| LoT terminal punctuation gap | Q065 requires "no terminal period" on LoT titles; P024 partially covers title case but does not explicitly check for a stray trailing period on LoT entries |
| Remaining automatable Q-rule gaps | Q023/Q024/Q025 (bio sketch content — high privacy risk); Q033/Q034 (dedication centering/italic — high FP); Q039–Q043 (acknowledgements semantic — high FP/privacy). All medium-FP addressable gaps have now been covered through P052. |

P040 checks that LoF entries have terminal punctuation. The symmetric gap for LoT is Q065: table titles in the List of Tables should NOT end with a terminal period. This is a conservative, low-FP check that mirrors P040's structure.

---

## Selected P053 scope

### Rule title

**P053 — LoT entry terminal-period check (Q065 refinement)**

### Source basis

- **Q065:** List of Tables entries should be in title case and should not have a terminal period.

### Scope included

1. Create `pdf_lot_terminal_period.py` (new module; mirrors `pdf_lof_terminal_punctuation.py` structure).
2. Add `_extract_lot_entry_text` helper: strip page-number token, leaders, and "Table X" prefix from entry text; return `None` if too short.
3. Add `_check_lot_terminal_period_page`: for each complete LoT entry (with `page_number_token`), check if the cleaned text ends with `.`. If yes, emit advisory.
4. Add `check_pdf_lot_terminal_period` (P053): iterate LoT pages, skip pages with fewer than 2 entries, collect per-page findings.
5. Gate: only check entries with `page_number_token is not None` (complete / last-wrapped-line entries); skip lines shorter than 10 chars after stripping; skip wrap-continuation lines.
6. Emit findings at `triage_tier: medium`; issue type `lot_entry_has_terminal_period`.
7. Privacy-safe: findings include only structural metadata (page, entry index, y-position); no table title text.
8. Register P053 in `project_added_rules.json`, wire into CLI, add evaluation category mapping.

### Scope excluded

- No changes to P040 or P024 behavior.
- No title-case enforcement (partially handled by P024; high FP without reliable font metadata).
- LoF, TOC excluded.
- No check for `?` or `!` at end of LoT entries (unusual but not explicitly prohibited).
- No entry text in findings.

### Expected module path

`src/njit_auditor/rules/pdf_lot_terminal_period.py` (new module)

### Expected issue types

- `lot_entry_has_terminal_period` — LoT complete entry ends with a period; Q065 requires no terminal period on table titles

### Expected evaluation category

`toc_list_formatting`

---

## Conservative gates

| Risk | Mitigation |
|------|------------|
| LoT page misclassified | Reuse `detect_toc_like_pages` from P040/P018; only process `list_of_tables` pages |
| Wrap-continuation lines flagged | Only process entries with `page_number_token is not None` |
| Short fragments produce false positives | Skip entries with fewer than 10 chars after stripping |
| Leader dots mistaken for terminal period | Strip trailing leader dots (`.. . .`) before checking |
| High false-positive rate | Advisory-only at `triage_tier: medium`; gate: ≥ 2 entries on page |

---

## Acceptance criteria for implementation

1. Emits `lot_entry_has_terminal_period` when a complete LoT entry ends with `.`.
2. Does NOT flag LoF entries, TOC entries, or LoT entries without a page-number token.
3. Skips entries shorter than 10 chars after stripping.
4. Strips leader dots before checking for terminal period.
5. Findings contain only privacy-safe metadata: no entry text, no table titles.
6. Existing P040, P024, P031 behavior unchanged.
7. Registered in `project_added_rules.json` with `implementation_status: implemented`.

---

## Validation plan

| Scope | Command |
|-------|---------|
| Inventory | `python -m pytest tests/test_rule_inventory.py -q` |
| Focused P053 tests | `python -m pytest tests/test_pdf_rules.py -q -k "p053 or lot_terminal"` |
| Lint | `ruff check .` |
| Types | `mypy src` |
| Full suite | `python -m pytest` |

---

## Safety

- Do not commit generated outputs under `data/evaluation/generated/`.
- Do not claim a canonical five-PDF current-dataset rerun unless all five PDFs are directly available and rerun.
- Findings and docs must remain aggregate/metadata-only; do not quote table title text, entry text, or dissertation content.
- Canonical aggregate remains 1,446; generated_for_commit remains `00b9c2d`.
