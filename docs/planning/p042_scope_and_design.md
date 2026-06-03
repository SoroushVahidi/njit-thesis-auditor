# P042 Scope and Design

- **Date:** 2026-06-03
- **Status:** **Scoped — not yet implemented**
- **Baseline main:** `eaea12c` (PR #110 — post-P041 consistency audit; P001–P041 implemented)

---

## Current state

| Area | State |
|------|--------|
| P-rules | **41/41** implemented (`P001`–`P041`) |
| Q-rules (raw inventory) | **79** total — **2** implemented, **11** partially_implemented, **66** not_implemented |
| TOC entry classification | **P024** and **P039** — both classify L1 entries via `_CHAPTER_RE = re.compile(r"^(?:chapter\|appendix)\b", re.IGNORECASE)`; appendix entries treated as L1 |
| TOC appendix entry format | **Not implemented** — Q058/Q059 completely unaddressed |
| TOC leader style | **P018** — `inconsistent_leader_dots` check (Q052 partially covered) |
| TOC column alignment | **P018** — page-number right-column and indent-outlier checks (Q068/Q069/Q078/Q079 partially) |
| Abstract indentation | **P015** — covers all pages including Abstract (Q002/Q003 functionally partial) |
| Dedication page header | **P041** — Q032 top-margin check (implemented) |

**Unaddressed gap:** Q058/Q059 ask whether TOC appendix entries use the correct format depending on whether there is one or multiple appendices. P024 and P039 both detect appendix entries via `_CHAPTER_RE` but neither checks the formatting pattern (single vs. letter-identified multiple).

---

## Candidate comparison

### Candidate 1 — TOC appendix entry format (Q058, Q059) ← RECOMMENDED

| Field | Detail |
|-------|--------|
| **Q-rule basis** | Q058: single appendix → entry begins with "APPENDIX" plus title; Q059: multiple appendices → each identified by a letter |
| **Proposed rule** | **P042** — TOC appendix entry format check |
| **Module** | `src/njit_auditor/rules/pdf_toc_appendix_format.py` |
| **Issue types** | `multiple_appendices_missing_letter_suffix`, `single_appendix_missing_title` |
| **Implementation risk** | **Low** — reuses `detect_toc_like_pages`, `extract_toc_entry_lines`, and `_CHAPTER_RE` from P024/P039; classification is already proven; new logic is a text-pattern check on matched entries |
| **Noise risk** | **Low** — only fires when appendix entries are found in the TOC; pattern check (`^appendix\s+[A-Z]\b`) is deterministic; gate: at least 2 appendix entries for Q059 check |
| **Privacy** | **Low** — findings contain only page number, issue type, entry count, appendix count; no TOC entry titles, no body text, no appendix content |
| **Likely tests** | (1) Two appendix entries with letters ("APPENDIX A Title", "APPENDIX B Title") → no finding; (2) Two appendix entries without letters ("APPENDIX Title One", "APPENDIX Title Two") → `multiple_appendices_missing_letter_suffix`; (3) Single appendix with title → no finding; (4) Single appendix with no title text → `single_appendix_missing_title`; (5) No appendix entries in TOC → no finding; (6) Non-TOC pages → no finding; (7) Privacy metadata check; (8) CLI integration |
| **Finding count impact** | Low: only fires when appendix entries exist in the TOC and are formatted incorrectly |
| **Why selected** | Q058/Q059 are completely unimplemented; `_CHAPTER_RE` already identifies appendix entries in P024/P039 — P042 adds a check that was never applied to those classified entries; clear Q-rule basis; low privacy risk; complements P024 and P039 naturally; specific enough to implement cleanly |

### Candidate 2 — Abstract indentation (Q002, Q003)

| Field | Detail |
|-------|--------|
| **Q-rule basis** | Q002: first Abstract paragraph flush-left; Q003: subsequent Abstract paragraphs indented |
| **Implementation risk** | **Low** — P015 already covers all pages including Abstract |
| **Why not recommended** | P015 functionally covers Q002/Q003 for the Abstract page already; a standalone P042 would largely duplicate P015 behavior with no incremental detector change; low value |

### Candidate 3 — TOC leader style (Q052)

| Field | Detail |
|-------|--------|
| **Q-rule basis** | Q052: consistent leader style from entry to page number |
| **Implementation risk** | **Low** — P018 already checks `inconsistent_leader_dots` |
| **Why not recommended** | P018 already covers the core Q052 requirement (leader-dot consistency check); incremental value too low |

### Candidate 4 — LoT/LoF number and page-number column alignment (Q068–Q069, Q078–Q079)

| Field | Detail |
|-------|--------|
| **Q-rule basis** | Q068/Q078: number left column; Q069/Q079: page-number right column |
| **Implementation risk** | **Low-medium** — P018 already checks right-column and indent-outlier; left-column consistency would add value but overlaps existing P018 checks |
| **Why not recommended** | P018's `inconsistent_hierarchy_indent` already catches left-column outliers; adding an explicit Q068/Q078 check risks emitting P042 + P018 findings for the same violation |

### Candidate 5 — LoT/LoF column label bold/alignment (Q063–Q064, Q072–Q073)

| Field | Detail |
|-------|--------|
| **Q-rule basis** | Q063/Q072: label bold + left-aligned; Q064/Q073: Page label bold + right-aligned |
| **Implementation risk** | **Medium** — P031 covers presence; bold metadata often absent in PDFs |
| **Why not recommended** | Bold metadata unreliable; high false-negative rate undermines value; deferred from P039/P040/P041 scoping for the same reason |

### Candidate 6 — TOC continued-heading format (Q048, Q062, Q071)

| Field | Detail |
|-------|--------|
| **Q-rule basis** | Q048/Q062/Q071: continued headings bold and centered on continuation pages |
| **Implementation risk** | **Medium** — P030 covers presence; format check overlaps P014 |
| **Why not recommended** | P030 covers the core requirement; format check (bold/centered) would duplicate P014 logic for a narrow edge case |

### Candidate 7 — Copyright page recall refinement (Q010, Q011)

| Field | Detail |
|-------|--------|
| **Q-rule basis** | Q010: year matches title page; Q011: author name matches title page |
| **Source basis** | P034 covers these but runs comparison on 2/5 files (author) and 1/5 (year) |
| **Why not recommended** | Not a new Q-rule; P034 refinement task; candidate recall expansion is lower priority than new Q-rule coverage |

### Additional deferred candidates

| Candidate | Why deferred |
|-----------|-------------|
| Q033/Q034 (Dedication centering/italic) | High FP; deferred multiple times |
| Q044/Q045 (Acknowledgements indentation) | P015 already covers; low incremental value |
| Q023–Q030 (Bio-sketch) | Semantic; manual-only; high privacy risk |
| Full canonical rerun | PDFs unavailable; evaluation-only |

---

## Ranking

| Rank | Candidate | Q-rule | Risk | Value |
|------|-----------|--------|------|-------|
| **1** | **TOC appendix entry format** | **Q058, Q059** | **Low** | **Medium** |
| 2 | LoT/LoF column alignment | Q068–Q069, Q078–Q079 | Low-med | Medium (overlaps P018) |
| 3 | Abstract indentation | Q002, Q003 | Low | Low (overlaps P015) |
| 4 | TOC leader style | Q052 | Low | Low (overlaps P018) |
| 5 | P034 copyright recall | Q010, Q011 | Low | Low (P034 refinement) |
| 6 | LoT/LoF column label bold | Q063–Q064, Q072–Q073 | Medium | Low (bold unreliable) |
| 7 | TOC continued heading format | Q048, Q062, Q071 | Medium | Low (overlaps P030/P014) |

---

## Selected P042 scope

### Rule title

**P042 — PDF TOC appendix entry format check**

### Source basis

- **Q058**: "If only one appendix is listed, does it begin with 'APPENDIX' plus title?"
- **Q059**: "If multiple appendices are listed, are they identified by letters?"
- Complements **P024** (TOC capitalization) and **P039** (TOC indentation hierarchy); reuses their `_CHAPTER_RE` pattern

### Scope included

1. **TOC pages only** — apply only to pages classified as `table_of_contents` by `detect_toc_like_pages`.
2. **Appendix entry identification** — find all `TocEntryLine` entries whose `cleaned_text` matches `^appendix\b` (case-insensitive), analogous to the L1 classification in P024/P039.
3. **Q059 check (multiple appendices)** — if 2 or more appendix entries are found: each entry should match `^appendix\s+[A-Z]\b` (case-insensitive) immediately after "APPENDIX". If any entry lacks the letter suffix, emit `multiple_appendices_missing_letter_suffix`.
4. **Q058 check (single appendix)** — if exactly 1 appendix entry is found: after stripping the word "APPENDIX" (and optional punctuation), the remaining text should be non-empty (i.e., there is a title). If the entry is just "APPENDIX" with no further content, emit `single_appendix_missing_title`.
5. **One finding per page per check type** — emit at most one finding per issue type per detected TOC page.
6. **Privacy-safe findings** — include only `page_number`, `issue_type`, `appendix_entry_count`, `source_q_rule_id`. No TOC entry titles, no appendix content.

### Scope excluded

- LoT and LoF pages — TOC-only.
- Appendix entry capitalization — owned by **P024** (Q049 L1 check via `_CHAPTER_RE`).
- Chapter entry format — not asked by Q058/Q059.
- Appendix body content or numbering — out of scope.
- Body chapter headings outside the TOC — out of scope.

### Expected module path

`src/njit_auditor/rules/pdf_toc_appendix_format.py`

Imports from:
- `pdf_toc_alignment.py` — `detect_toc_like_pages`, `extract_toc_entry_lines`, `TocEntryLine`, `TocPageContext`

### Expected CLI / report / evaluation wiring

| Surface | Change |
|---------|--------|
| `src/njit_auditor/cli.py` | Import and call `check_pdf_toc_appendix_format()` after `check_pdf_toc_entry_hierarchy` |
| `data/processed/rules/project_added_rules.json` | Add **P042** entry (`implementation_status: implemented` after code lands) |
| `src/njit_auditor/evaluation.py` | Map P042 → `list_of_tables_figures_toc` (same as P024/P036/P039/P040) |
| Reports | Standard `AuditFinding` details; no new triage rollup in v1 |

### Expected tests

| Test | Expectation |
|------|-------------|
| TOC with "APPENDIX A Title" + "APPENDIX B Title" (2 appendices with letters) | No P042 finding |
| TOC with "APPENDIX Title One" + "APPENDIX Title Two" (2 without letters) | `multiple_appendices_missing_letter_suffix` |
| TOC with single "APPENDIX My Long Title" | No P042 finding (Q058 passes: has title) |
| TOC with single "APPENDIX" alone (no title text) | `single_appendix_missing_title` |
| TOC with no appendix entries | No P042 finding |
| Non-TOC page (LoT or LoF) | No P042 finding |
| Finding metadata privacy check | No TOC entry title text in details |
| CLI integration | P042 in JSON output when triggered |

Update `tests/test_rule_inventory.py` count to **42** when implemented.

### Privacy constraints

- Findings include only: `page_number`, `issue_type`, `appendix_entry_count`, `source_q_rule_id`.
- No TOC entry titles, appendix body content, or dissertation prose in findings.
- Test fixtures use synthetic placeholder appendix labels, not real dissertation content.

### Acceptance criteria

1. P042 emits `multiple_appendices_missing_letter_suffix` when 2+ appendix entries lack letter identifiers.
2. P042 emits `single_appendix_missing_title` when a single appendix entry has no title after "APPENDIX".
3. P042 emits nothing when appendix entries are correctly formatted.
4. P042 emits nothing when no appendix entries are present in the TOC.
5. P042 does not fire on LoT or LoF pages.
6. P042 does not duplicate P024, P039, or P018 issue types.
7. CLI runs P042 without changing P001–P041 behavior.
8. All existing 482 tests pass; new P042 synthetic tests added.
9. `project_added_rules.json` lists P042 (implementation PR only).

### Known false-positive risks

- **Non-standard appendix labeling**: Some theses may use "APPENDIX I", "APPENDIX II" (Roman numerals) instead of letters. The pattern `^appendix\s+[A-Z]\b` would not match these, causing `multiple_appendices_missing_letter_suffix` even though the format is reasonable. Mitigation: accept uppercase single characters A-Z; note Roman numeral limitation in design doc.
- **"APPENDIX" as a section heading within a chapter**: If a chapter inside the TOC has a section named "Appendix", it would be detected. Mitigation: the `_CHAPTER_RE` only matches at the START of a cleaned entry line, so mid-sentence "appendix" references are excluded.
- **Compressed PDFs**: Text extraction may not capture appendix entries; gate (no entries detected) silently skips.

### Local evaluation rerun (not committed)

After implementation, rerun five-PDF audit locally into gitignored
`data/evaluation/generated/current_auditor_after_p042/` and add
`docs/evaluation/p042_current_dataset_evaluation.md` with aggregate P042 counts only.

Do **not** commit generated JSON/MD. Do **not** update `generated_for_commit` or the
pre-P035/.../P041 canonical **1,446** aggregate.

---

## Implementation plan (next task)

1. Create `src/njit_auditor/rules/pdf_toc_appendix_format.py`:
   - Import from `pdf_toc_alignment.py`
   - Define `_APPENDIX_RE = re.compile(r"^appendix\b", re.IGNORECASE)`
   - Define `_APPENDIX_WITH_LETTER_RE = re.compile(r"^appendix\s+[A-Z]\b", re.IGNORECASE)`
   - Implement `_check_toc_appendix_format_page(context, entries) -> list[AuditFinding]`
   - Implement `check_pdf_toc_appendix_format(pdf_document) -> list[AuditFinding]`
2. Wire CLI after P039 call.
3. Add P042 entry to `data/processed/rules/project_added_rules.json`.
4. Map P042 → `list_of_tables_figures_toc` in `src/njit_auditor/evaluation.py`.
5. Add synthetic tests; update `tests/test_rule_inventory.py` to 42 rules.
6. Run full validation.
7. Optional: local evaluation doc.

No changes to P001–P041 detector behavior.

---

## Validation plan

| Step | Command |
|------|---------|
| Inventory | `python -m pytest tests/test_rule_inventory.py -q` |
| P042 synthetics | `python -m pytest tests/test_pdf_rules.py -k p042 -q` |
| Full suite | `ruff check .`, `mypy src`, `python -m pytest` |

---

## Privacy notes

- Findings report only count and issue type — no TOC entry text.
- Test fixtures use synthetic appendix labels ("APPENDIX A Introduction").
- No real dissertation content used.

## Generated-output safety

- Outputs under `data/evaluation/generated/` stay gitignored.
- Do not commit audit JSON or per-PDF reports.
