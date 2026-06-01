# P034 Author-Hash Mismatch Investigation

- **Date:** 2026-06-01
- **Investigation baseline:** `99b9c7d` (post–PR #66 current-dataset evaluation)
- **Implementation refinement:** yes (middle-initial tolerance in author comparison)

## 1. What was investigated

PR #66 reported **2** P034 `copyright_author_mismatch` findings on page 4:

| File label | Page | Title-page author hash | Copyright-page author hash |
|---|---:|---|---|
| Yin H 4th review (compressed) | 4 | `6e6ce54e3711859c` | `16312471b3877411` |
| Sebastian Fine clean baseline | 4 | `8a2fc39a277bcd15` | `c8ffd26bf8d35f7d` |

No raw author names, title text, or body content appears in this document.

## 2. Reproduction (structural metadata)

Both findings were reproduced on the evaluation PDFs with the pre-refinement P034 logic.

| File label | Author comparison ran | Sequence similarity (normalized) | Title token count | Copyright token count | Shared tokens | Copyright-only tokens |
|---|---|---:|---:|---:|---:|---:|
| Yin H 4th review (compressed) | yes | 0.88 | 2 | 3 | 2 | 1 |
| Sebastian Fine clean baseline | yes | 0.90 | 2 | 3 | 2 | 1 |

**Extraction sources (both files):**

| Side | Source | Structural detail |
|---|---|---|
| Title Page | Line immediately after `by` | 2-word span; high confidence |
| Copyright Page | First ©/year line matching `© YEAR …` regex | 3-word remainder after year; high confidence |

**Copyright-only extra token (both files):**

- Exactly **one** extra token on the © line versus the Title Page `by` line.
- Token length **2 characters** after normalization.
- Position: **prepended** before the two tokens that match the Title Page span (not appended).
- No `All Rights Reserved` phrase left in the parsed remainder (`has_all_rights_phrase`: false).

## 3. Cross-file comparison

| Aspect | Yin H 4th | Sebastian Fine clean baseline |
|---|---|---|
| False-positive pattern | Same | Same |
| Title-page extraction issue | No — `by` + next line used as designed | No |
| Copyright-page extraction issue | Partial — regex captured an extra leading token | Partial — same |
| Token-count mismatch | 2 vs 3 | 2 vs 3 |
| Year comparison | Ran; years matched (2026) | Skipped (title graduation year not extracted) |
| Confidence | high / high | high / high |

**Conclusion:** Both findings share one structural cause — **not** independent true author inconsistencies.

## 4. Decision

**Classification:** Likely **false positives** from copyright-line author extraction including a **leading middle initial** that the Title Page `by` line omits.

**Not chosen:**

- True author-name inconsistency — token overlap shows all Title Page tokens appear on the © line; only one short leading token differs.
- Ambiguous/manual-only — structural evidence is consistent across both files.

**Implementation change (conservative):**

Added `_authors_match_with_middle_initial_tolerance` in `pdf_copyright_page.py`:

- When the copyright normalized author is the title author plus **exactly one** extra token,
- And that token is prepended or appended,
- And the extra token has length ≤ 2 (middle initial) or is a known suffix (`jr`, `sr`, `ii`, `iii`, `iv`),
- Treat as a match and **do not** emit `copyright_author_mismatch`.

Synthetic test: `test_p034_copyright_middle_initial_matches_title_no_finding`.

**Post-refinement re-check on evaluation PDFs:**

| File label | P034 count (after refinement) |
|---|---:|
| Yin H 4th review (compressed) | 0 |
| Sebastian Fine clean baseline | 0 |

## 5. Limitations

- Tolerance applies only to a **single** short initial/suffix token; multi-token or longer extra spans still flag.
- Does not verify that the initial/suffix is correct for the student — only that the layout pattern is common.
- Other author layouts (institution names in © line, reversed name order, hyphenated surnames split across lines) may still false-positive or false-negative.
- Manual review remains required for Q011 compliance.

## 6. Related docs

- Current-dataset evaluation: `docs/evaluation/p034_current_dataset_evaluation.md`
- Synthetic validation: `docs/evaluation/p034_copyright_page_synthetic_validation.md`
