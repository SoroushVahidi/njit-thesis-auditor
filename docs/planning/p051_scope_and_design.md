# P051 Scope and Design

- **Date:** 2026-06-04
- **Status:** **Implemented**
- **Baseline main:** `4ee5bd3` (PR #148 — post-P050 documentation consistency; P001–P050 implemented)

---

## Current state

| Area | State |
|------|-------|
| P-rules | **50/50** implemented (`P001`–`P050`) |
| Copyright page checks | **P034** — top-margin header (Q009), year match (Q010), author match (Q011); heuristic; year extracted on ~1/5 evaluation PDFs; author extracted on ~2/5 |
| Copyright year remaining gap | Q010 year extraction misses compressed/flattened pages and PDFs where year is embedded in a run-together copyright line without clear whitespace |
| Remaining automatable Q-rule gaps | Q026/Q027/Q030 (bio sketch content — medium-high risk); Q033/Q034 (dedication visual — high FP); Q039–Q043 (acknowledgements semantic — high FP/privacy); no low-risk unimplemented items remain |

P034 already handles Q009/Q010/Q011, but year and author extraction recall is low. P051 should be the narrow copyright page **year-format refinement** that improves Q010 coverage without changing P034's existing detection behavior.

---

## Selected P051 scope

### Rule title

**P051 — PDF copyright page year-format refinement (Q010 improvement)**

### Source basis

- **Q010:** The visible copyright year on the Copyright Page must exactly match the graduation year shown on the Title Page.

### Scope included

1. Reuse `_find_copyright_page` and `_extract_title_page_year` from P034 module.
2. Extend copyright year extraction to handle additional line formats:
   - "©YYYY" with no space between symbol and year
   - "Copyright YYYY" where "Copyright" and "YYYY" appear on separate lines but adjacent in text order
   - Unicode variants of © (U+00A9) already covered; also handle "All Rights Reserved, YYYY" patterns
   - Multi-span lines where year is in a different span from the copyright symbol
3. Add a conservative "copyright year line not found" signal: if the copyright page is confidently detected but no year token is found anywhere in the page text, emit a low-confidence advisory finding (distinct issue type from P034's year-mismatch finding).
4. Only emit year-format findings when the copyright page is confidently detected (existing P034 gate).
5. Skip compressed, image-only, or flattened pages where no text layer is present.
6. Do not reproduce copyright text, author names, or any dissertation body text in findings.

### Scope excluded

- No changes to P034's existing year-mismatch or author-mismatch logic.
- No changes to Q011 (author match) — author extraction recall improvement deferred.
- No alignment or spacing checks (covered by P034's Q009 check).
- Implementation: extended `pdf_copyright_page.py` with `_extract_copyright_year_adjacent_lines` helper and `check_pdf_copyright_year_format` (P051). Wired into CLI and evaluation mapping. 9 synthetic tests added.

### Expected module path

Extend `src/njit_auditor/rules/pdf_copyright_page.py` (same module as P034) or create a focused sub-function within that module. Do not create a new module.

### Expected issue types

- `copyright_year_not_found` — copyright page detected but no year token found; low-confidence advisory (only when year is completely absent from page text)

### Expected evaluation category

`title_page_metadata`

---

## Conservative gates

| Risk | Mitigation |
|------|------------|
| Copyright page not confidently detected | Reuse P034's `_find_copyright_page`; skip if None |
| Year present but in unexpected format | Broaden `_COPYRIGHT_YEAR_LINE_RE` conservatively; prefer false negatives |
| Overlap with P034 year-mismatch finding | Only emit `copyright_year_not_found` when year is completely absent; P034 emits year-mismatch when year IS found but doesn't match |
| Image-only / compressed copyright pages | `_page_has_meaningful_text` already gates this; maintain existing gate |
| Noisy false positives | Emit advisory at `triage_tier: low`; do not change P034 severity |

---

## Acceptance criteria for implementation

1. Emits `copyright_year_not_found` when copyright page is detected but no year token is present in page text.
2. Does NOT emit `copyright_year_not_found` when P034 already detected a year (avoids double-finding).
3. Improved year extraction recall: handles "©YYYY" (no space) and "Copyright\nYYYY" (adjacent lines) patterns.
4. No changes to P034 behavior or existing findings.
5. Findings contain only privacy-safe metadata (no copyright text, no author names).
6. Skips compressed/image-only copyright pages.

---

## Validation plan

| Scope | Command |
|-------|---------|
| Inventory | `python -m pytest tests/test_rule_inventory.py -q` |
| Focused P051 tests | `python -m pytest tests/test_pdf_rules.py -q -k "p051 or copyright_year"` |
| Lint | `ruff check .` |
| Types | `mypy src` |
| Full suite | `python -m pytest` |

---

## Safety

- Do not commit generated outputs under `data/evaluation/generated/`.
- Do not claim a canonical five-PDF current-dataset rerun unless all five PDFs are directly available and rerun.
- Findings and docs must remain aggregate/metadata-only; do not quote copyright text, author names, or dissertation content.
- Canonical aggregate remains 1,446; generated_for_commit remains `00b9c2d`.
