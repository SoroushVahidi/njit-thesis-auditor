# P054 Scope and Design

- **Date:** 2026-06-05
- **Status:** **Implemented**
- **Baseline main:** `4c9c3f5` (PR #166 — Polish web GUI deployment docs; P001–P053 implemented; web UI added)
- **Implementation commit:** (PR #167 — Implement P054 TOC terminal-period check)

---

## Current state

| Area | State |
|------|-------|
| P-rules | **53/53** implemented (`P001`–`P053`) |
| LoF terminal punctuation | **P040** — warns when LoF complete entries lack `.`/`?`/`!` (Q075) |
| LoT terminal-period absence | **P053** — warns when LoT complete entries end with `.` (Q065 refinement) |
| TOC terminal-period gap | Q050 (L2 entries title case) and Q049 (L1 entries all-caps) implicitly require no terminal period on TOC entries; no explicit terminal-period absence check exists for TOC pages |
| Remaining automatable Q-rule gaps | Q023/Q024/Q025 (bio sketch content — high privacy risk); Q033/Q034 (dedication centering/italic — high FP); Q039–Q043 (acknowledgements semantic — high FP/privacy). All medium-FP addressable gaps covered through P053. |

P053 checks that LoT entries do not end with a terminal period. The natural symmetric extension is the Table of Contents itself: TOC entries at all levels (CHAPTER headings, subsection titles) should not end with a terminal period either. The same shared infrastructure (`detect_toc_like_pages`, `extract_toc_entry_lines`) already handles TOC pages (`page_type == "table_of_contents"`), making implementation straightforward.

---

## Selected P054 scope

### Rule title

**P054 — TOC entry terminal-period absence check (Q050 refinement)**

### Source basis

- **Q049:** TOC L1 entries (CHAPTER headings) are in all-caps — no terminal period implied.
- **Q050:** TOC L2 entries use title case — no terminal period implied.
- **Q051:** TOC L3 entries use sentence case — no terminal period implied.

NJIT TOC formatting guidelines show entries without terminal punctuation at all levels. A stray trailing period on any TOC entry is a formatting error analogous to the LoT case (P053) and is detectable with very low false-positive risk.

### Scope included

1. Create `pdf_toc_terminal_period.py` (new module; mirrors `pdf_lot_terminal_period.py` structure).
2. Add `_extract_toc_entry_text` helper: strip page-number token, leader dots, and any recognized level-prefix ("CHAPTER X", "A.", etc.) from entry text; return `None` if too short.
3. Add `_check_toc_terminal_period_page`: for each complete TOC entry (with `page_number_token`), check if the cleaned text ends with `.`; if yes, emit advisory.
4. Add `check_pdf_toc_terminal_period` (P054): iterate TOC pages (`page_type == "table_of_contents"`), skip pages with fewer than 2 entries, collect per-page findings.
5. Gate: only check entries with `page_number_token is not None`; skip entries shorter than 10 chars after stripping; skip wrap-continuation lines; do not process LoT or LoF pages.
6. Emit findings at `triage_tier: medium`; issue type `toc_entry_has_terminal_period`.
7. Privacy-safe: findings include only structural metadata (page, entry index, entry level if detectable); no heading text.
8. Register P054 in `project_added_rules.json`, wire into CLI, add evaluation category mapping.

### Scope excluded

- No changes to P053 (LoT), P040 (LoF), P024 (TOC case), or P027 (L3 case) behavior.
- No title-case or all-caps enforcement (high FP; handled by P024).
- LoT and LoF excluded (P053 and P040 handle those).
- No check for `?` or `!` at end of TOC entries (unusual; not explicitly prohibited).
- No entry text in findings.

### Expected module path

`src/njit_auditor/rules/pdf_toc_terminal_period.py` (new module)

### Expected issue types

- `toc_entry_has_terminal_period` — a complete TOC entry ends with a period; NJIT guidelines (Q049/Q050/Q051) require no terminal punctuation on TOC entries

### Expected evaluation category

`toc_list_formatting`

---

## Conservative gates

| Risk | Mitigation |
|------|------------|
| TOC page misclassified | Reuse `detect_toc_like_pages` from P018/P032/P053; only process `table_of_contents` pages |
| Wrap-continuation lines flagged | Only process entries with `page_number_token is not None` |
| Short fragments produce false positives | Skip entries with fewer than 10 chars after stripping |
| Leader dots mistaken for terminal period | Strip trailing leader dots (`.. . .`) before checking |
| Abbreviations produce false positives | Conservative: require at least 10 chars of cleaned text before period check; abbreviations are typically shorter or occur mid-entry |
| High false-positive rate | Advisory-only at `triage_tier: medium`; gate: ≥ 2 entries on page |

---

## Acceptance criteria for implementation

1. Emits `toc_entry_has_terminal_period` when a complete TOC entry ends with `.`.
2. Does NOT flag LoT entries, LoF entries, or TOC entries without a `page_number_token`.
3. Does NOT flag the TOC page-header line ("TABLE OF CONTENTS").
4. Skips pages with fewer than 2 detected entries.
5. Findings contain only structural metadata — no heading text.
6. All P001–P053 existing tests continue to pass.

---

## Test plan (9 synthetic tests)

| Test name | Expected outcome |
|-----------|-----------------|
| `test_p054_toc_entry_no_period_no_finding` | Clean TOC entries → no findings |
| `test_p054_toc_entry_with_period_warns` | Complete entry ending in `.` → 1 finding |
| `test_p054_wrap_continuation_skipped` | Continuation line (no page token) → no finding |
| `test_p054_no_toc_page_no_finding` | PDF with only LoT page → no findings |
| `test_p054_lot_page_not_checked` | LoT pages excluded from P054 scope → no findings |
| `test_p054_sparse_page_skipped` | Page with only 1 entry → no findings (gate) |
| `test_p054_finding_metadata_privacy_safe` | Finding details contain no entry text |
| `test_p054_import_and_wiring` | `check_pdf_toc_terminal_period` importable and callable via CLI path |
| `test_p054_p053_unaffected` | P053 still fires correctly for LoT after P054 added |

---

## Relationship to existing rules

| Rule | Page type | Punctuation requirement | Direction |
|------|-----------|------------------------|-----------|
| P040 | LoF | Must HAVE `.`/`?`/`!` | Absence warns |
| P053 | LoT | Must NOT have `.` | Presence warns |
| **P054** | TOC | Must NOT have `.` | Presence warns |
