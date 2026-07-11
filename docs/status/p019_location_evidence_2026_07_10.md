# P019 Page-Numbering Location Evidence — 2026-07-10

## 1. Audited commit

`237452a4c20cc7197c21e155efdf623e9f5c1080` (origin/main, PR #501 merged; PR #502 open, not merged).

## 2. P019 inventory

Ran the full pipeline on 4 curated samples + 5 non-curated real dissertations. Every visible P019 finding was recorded privacy-safely (issue_type, page, confidence, bbox presence, action_kind, related P013/P028 findings). Raw inventory kept in the session scratchpad, not committed (generated reports are not committed per this repo's AGENTS.md unless requested).

Summary: 21 raw P019 findings across the 9 documents, spanning `missing_page_number`, `duplicate_or_ambiguous_page_number`, `wrong_page_number_location`, `wrong_page_numbering_style` (page-level and document-level), `wrong_page_number_sequence`.

## 3. Root cause of missing location evidence

Traced directly in `src/njit_auditor/rules/pdf_page_numbers.py`. Two real, reproducible detector bugs, both losses at **detector creation** (not serialization, grouping, or view-model construction):

- **Per-page `mixed_numbering_style`**: the code already builds `plausible` (the page's candidate list, each with a `bbox`) to detect the style conflict, but never attached any candidate's bbox to the finding's `details`. The evidence existed in scope and was simply discarded.
- **Roman-numeral `sequence_gap`**: the Arabic and Roman sequence-gap blocks are near-identical ~35-line blocks. The Arabic block attaches `primary.bbox`; the Roman block, written just below it, is missing that line entirely — a code-duplication drift bug.

`missing_page_number` correctly has no bbox (there is no token to point to) and correctly falls back to the original-page action — this is the expected "document-level by nature" case, not a bug.

## 4. Location contract by issue type

| Issue type | Minimum evidence | Status |
|---|---|---|
| Wrong style, one page | exact page, token, style, expected style, bbox when a trustworthy candidate exists | Fixed (bbox now attached) |
| Sequence break | exact page before/after, observed/expected values, bbox | Fixed (bbox on both Arabic and Roman; previous/next **page numbers** now recorded, not just values) |
| Ambiguous/multiple candidates | exact page, each candidate, bbox of the primary | Already correct pre-existing behavior (`multiple_page_numbers`) |
| Front-matter/body boundary problem | last front-matter page, first body page | Covered by P028 (regime-specific); P019's role here is document-wide consistency, see below |
| Document-wide mixed style | exact transition page(s) when identifiable, else neutral wording with confidence Low | Improved: `transition_pages` computed and named in wording when the transition is unambiguous; generic wording (with an explicit "could not be determined automatically" statement) preserved as a documented fallback otherwise |

## 5. Before/after exact-location rate

Real-corpus comparison (`git show HEAD:...` used to extract the pre-change file versions, not stash, per this repo's AGENTS.md constraint):

| Document | Raw P019 (before=after) | Visible P019 (before=after) | Exact-location (bbox present) before → after |
|---|---|---|---|
| curated_a/b/c | 1/1/1 | 1/1/1 | 0→0 (no page-specific style/sequence findings on these docs) |
| curated_d | 4 | 4 | 2 → 3 |
| noncurated_1/2/3 | 2/1/1 | 2/1/1 | 0→0 |
| noncurated_4 | 5 | 5 | 2 → 4 |
| noncurated_5 | 6 | 6 | 3 → 5 |

Raw and visible finding counts are **identical before and after on every document** — confirmed detector decisions did not change, only the structured evidence attached to already-firing findings. Confidence distribution unchanged on every document. Zero unrelated-rule count changes on any document.

## 6. Before/after highlight rate

Directly tracks §5 (bbox presence drives `has_highlight`): every one of the 6 newly-bbox-bearing findings across `curated_d`/`noncurated_4`/`noncurated_5` now renders a real "Open highlighted PDF page" action instead of an original-page fallback.

## 7. Wording improvements

- `wrong_page_number_sequence`: neighbor clauses now name the exact page ("previous detected page number: 8 (page 6)") instead of only the value.
- Document-wide `wrong_page_numbering_style`: now says "The page-numbering style changes from lowercase Roman numerals (page 17) to Arabic numerals (page 18) across the document" when the transition is identifiable, replacing the fully generic "Verify the numbering-style boundary between front matter and body" (kept only as an explicit fallback, now stating "the exact transition page could not be determined automatically" so the reduced certainty is visible rather than silently glossed over).
- Fixed a "this page" reference that was grammatically inconsistent when `page is None` (was: "...reported above for this page" with no page in scope).

All improvements manually inspected end-to-end on the real documents where they fired (§5); see the diff for exact before/after text.

## 8. P019/P028 overlap analysis

Confirmed 4 real co-firing pages across 2 documents (same finding as PR #502's independent audit). After this fix, P019's and P028's bboxes on these pages are now **identical coordinates** (both point at the same physical token), but their `suggested_fix` differs in scope: P028 says "Update the page-numbering style for this section" (fix this one page); P019 says "Verify the numbering-style boundary between front matter and body, then correct any inconsistent pages" (a broader, section-boundary-scoped check). Classified as **"same evidence, different remediation scope"** — condition 3 of the no-suppress checklist (same student action) is not met, so per this task's explicit rule, **no suppression or merge was implemented**. Documented for Esther's decision (§12).

## 9. Detector bugs discovered

1. Per-page `mixed_numbering_style` missing bbox (fixed).
2. Roman `sequence_gap` missing bbox — a code-duplication drift from the Arabic block (fixed).

Both fixes are purely additive (new `details` keys only); no existing key, message, severity, confidence, or firing condition changed. Confirmed via the full real-corpus before/after (§5) and the full test suite.

## 10. Tests added

- `tests/test_p019_location_evidence.py` — 14 tests: bbox attachment (both bug fixes), `previous_sequence_page`/`next_sequence_page` presence and correctness, `transition_pages` computation and wording, and 6 detector-invariance checks (clean transition, skipped Arabic/Roman, duplicate candidates, body numeric ID not misread, no-text-layer document).
- `tests/test_p019_pdf_link_crawl.py` — 6 tests: desktop + mobile highlighted-PDF link crawl (status/content-type/`%PDF` magic bytes), desktop/mobile link parity, and confirmation that a genuinely bbox-less finding never produces a fake highlight link.

Full suite: 2742 passed (baseline 2722 + 20 new), `ruff check .` clean, `mypy src` clean.

## 11. Anti-overfitting audit

Grepped the full diff and both new test files for real names, sample IDs, filenames, hashes, and page-number-as-production-condition. Zero matches (two matches on `f.page == 1` are test assertions against a synthetic 1-page fixture, not production logic).

## 12. Remaining questions requiring Esther's decision

- Should P019 and P028 ever be presented as one card (primary + secondary note) when they co-fire on the same token with the same normalized wording, given their remediation scopes differ ("fix this page" vs. "verify the section boundary")? Not implemented here — documented only, per this task's explicit instruction not to suppress without proven equivalence.
- Should `missing_page_number` ever attempt a "this general area is where the number should be" approximate highlight (e.g. the bottom-center zone) rather than page-only? Not attempted here — speculative geometry without a real candidate token risks a misleading highlight.
