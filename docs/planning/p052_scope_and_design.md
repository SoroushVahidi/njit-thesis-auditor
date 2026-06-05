# P052 Scope and Design

- **Date:** 2026-06-04
- **Status:** **Implemented**
- **Baseline main:** `7efdf20` (PR #152 — post-P051 documentation consistency; P001–P051 implemented)

---

## Current state

| Area | State |
|------|-------|
| P-rules | **52/52** implemented (`P001`–`P052`) |
| Copyright page checks | **P034** — top-margin header (Q009), year match (Q010), author match (Q011); heuristic; year extracted on ~1/5 evaluation PDFs; author extracted on ~2/5 |
| **P051** | Copyright page year-format refinement — year-not-found advisory, adjacent-line year extraction; implemented 2026-06-04 |
| Copyright author remaining gap | Q011 author extraction recall is low; `_extract_copyright_author` only finds author when on the same line as the copyright marker; author on the next line is not currently detected |
| Remaining automatable Q-rule gaps | Q033/Q034 (dedication visual — high FP); Q039–Q043 (acknowledgements semantic — high FP/privacy); Q023–Q025 (bio sketch content — privacy); Q011 (author recall — low risk, addressable) |

P034 already handles Q011 but author extraction recall is low (~2/5 evaluation PDFs). P052 should be the narrow copyright page **author-format refinement** that improves Q011 coverage without changing P034's existing detection behavior.

---

## Selected P052 scope

### Rule title

**P052 — PDF copyright page author-format refinement (Q011 improvement)**

### Source basis

- **Q011:** The author name on the Copyright Page must match the author name on the Title Page.

### Scope included

1. Reuse `_find_copyright_page`, `_extract_title_page_author`, and `_extract_copyright_author` from P034 module.
2. Add `_extract_copyright_author_adjacent_lines`: when a copyright line contains a year but no author, check if the next line contains a plausible author-like string (no copyright marker, 2+ words, no year, no noise patterns). Return a `(normalized, hash)` pair if confident.
3. Add a conservative `copyright_author_not_found` advisory: if the copyright page is confidently detected and the copyright year was found (confirming it is a real copyright page) but no author can be extracted from either pattern, emit an advisory (distinct from P034's `copyright_author_mismatch`).
4. Only emit author-format findings when the copyright page is confidently detected (existing P034 gate).
5. Do not reproduce author names, copyright text, or dissertation body text in findings; use hashes only.
6. Skip image-only pages and compressed pages.

### Scope excluded

- No changes to P034's existing author-mismatch or year-mismatch logic.
- No changes to Q009 (top-margin header) or Q010 (year match).
- No alignment or spacing checks.
- Implementation: extended `pdf_copyright_page.py` with `_extract_copyright_author_adjacent_lines` helper and `check_pdf_copyright_author_format` (P052). Also extended `_AUTHOR_NOISE_RE` to exclude "all rights reserved" phrases. Wired into CLI and evaluation mapping. 9 synthetic tests added.

### Expected module path

Extend `src/njit_auditor/rules/pdf_copyright_page.py` (same module as P034/P051). Do not create a new module.

### Expected issue types

- `copyright_author_not_found` — copyright page and copyright year detected, but no author string found on copyright page; low-confidence advisory (only when author is completely absent)

### Expected evaluation category

`title_page_metadata`

---

## Conservative gates

| Risk | Mitigation |
|------|------------|
| Copyright page not confidently detected | Reuse P034's `_find_copyright_page`; skip if None |
| Author present but in unexpected format | Require 2+ words, no copyright marker, no year, no noise; prefer false negatives |
| Overlap with P034 author-mismatch finding | Only emit `copyright_author_not_found` when no author is extractable from page; P034 emits mismatch when author IS found but differs |
| Names in findings | Never include author names; use hash-only representation |
| Image-only / compressed copyright pages | `_page_has_meaningful_text` already gates this |
| Noisy false positives | Emit advisory at `triage_tier: low` only when year IS found (confirming real copyright page) but author is absent |

---

## Acceptance criteria for implementation

1. Emits `copyright_author_not_found` when copyright page is detected, year is found, but no author string is extractable.
2. Does NOT emit `copyright_author_not_found` when P034 already detected an author.
3. Improved author extraction recall: handles "©YYYY\nAuthor Name" adjacent-line patterns.
4. No changes to P034 behavior or existing findings.
5. Findings contain only privacy-safe metadata: no author names, hashes only, no copyright text.
6. Skips compressed/image-only copyright pages.

---

## Validation plan

| Scope | Command |
|-------|---------|
| Inventory | `python -m pytest tests/test_rule_inventory.py -q` |
| Focused P052 tests | `python -m pytest tests/test_pdf_rules.py -q -k "p052 or copyright_author"` |
| Lint | `ruff check .` |
| Types | `mypy src` |
| Full suite | `python -m pytest` |

---

## Safety

- Do not commit generated outputs under `data/evaluation/generated/`.
- Do not claim a canonical five-PDF current-dataset rerun unless all five PDFs are directly available and rerun.
- Findings and docs must remain aggregate/metadata-only; do not quote author names, copyright text, or dissertation content.
- Canonical aggregate remains 1,446; generated_for_commit remains `00b9c2d`.
