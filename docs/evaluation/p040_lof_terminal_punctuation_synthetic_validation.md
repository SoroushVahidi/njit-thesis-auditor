# P040 LoF Terminal Punctuation — Synthetic Validation

- **Date:** 2026-06-03
- **Implementation commit:** rules/p040-lof-terminal-punctuation
- **Auditor scope:** P001–P040
- **Validation type:** Synthetic (programmatically generated PDF fixtures)

## 1. Purpose

Confirm that P040 (`check_pdf_lof_terminal_punctuation`) correctly flags List of Figures
entries lacking terminal punctuation, skips wrap-continuation lines and non-LoF pages, and
produces privacy-safe findings.

All synthetic PDFs are generated at test time using PyMuPDF (`fitz`). No real dissertation
content, author names, or figure description text is used.

## 2. Test matrix

| # | Test | Expected outcome |
|---|------|-----------------|
| 1 | LoF entry ending with `.` (3 entries) | No P040 finding |
| 2 | LoF entry ending with `?` | No P040 finding |
| 3 | One LoF entry missing terminal punctuation | `lof_entry_missing_terminal_punctuation` |
| 4 | Three LoF entries all missing punctuation | Multiple P040 findings (≥2) |
| 5 | Wrapped entry: continuation line without page token | Skipped; no false-positive |
| 6 | LIST OF TABLES page | No P040 finding (LoF-only rule) |
| 7 | TABLE OF CONTENTS page | No P040 finding |
| 8 | Finding details privacy check | No entry text in finding details |
| 9 | CLI integration | P040 present in JSON report when triggered |

All 9 tests pass on implementation commit.

## 3. Finding details schema

P040 findings contain only geometric/count metadata — no figure description text:

| Field | Type | Example |
|-------|------|---------|
| `issue_type` | str | `lof_entry_missing_terminal_punctuation` |
| `page_number` | str | `"1"` |
| `entry_index` | str | `"1"` |
| `line_y` | str | `"161.4"` |
| `terminal_punctuation_required` | str | `"., ?, or !"` |
| `triage_tier` | str | `"medium"` |
| `source_q_rule_id` | str | `"Q075"` |

No figure description text, captions, titles, or other dissertation content is included.

## 4. v1 known limitations

| Limitation | Notes |
|---|---|
| Page-number-token filter | Only entries with `page_number_token is not None` are checked; wrapped entries are only checked on their last line (where the page number appears) |
| Minimum text length | Entries shorter than 10 characters after prefix and page-token stripping are skipped |
| LoF-only | TOC and LoT pages are excluded by design |
| Figure prefix stripping | Only "Figure N." / "Fig. N." prefixes are stripped; other numbering schemes may leave the prefix in the text, but terminal punctuation check is unaffected |
| Leader-dot stripping | Two-or-more consecutive dots are stripped; a single trailing period is treated as terminal punctuation (no false positive) |
| Compressed PDFs | Coordinate and text extraction may be unreliable on compressed/flattened PDFs |

## 5. Privacy notes

- Test fixtures use synthetic placeholder text ("An Example Figure With Correct Punctuation.", "Entry Without Punctuation", etc.) — no real dissertation content.
- P040 findings contain only numeric/metadata values — no figure description text.
- No caption text, dissertation titles, or author names appear in findings.

## 6. Current-dataset evaluation

**Not performed** — evaluation PDFs unavailable in workspace. No P040 counts exist
against the five-PDF canonical set. Do not update the **1,446** pre-P035/P036/P037/P038/P039
canonical total until a full P001–P040 rerun is performed locally when evaluation PDFs
are available, documented in a privacy-safe evaluation note, and written to a new gitignored
generated path (e.g. `data/evaluation/generated/current_auditor_after_p040/`).

When evaluation PDFs are available:

1. Run `njit-audit pdf` on each file in the five-PDF evaluation set.
2. Write outputs only under gitignored `data/evaluation/generated/current_auditor_after_p040/`.
3. Update a privacy-safe current-dataset doc with aggregate P040 counts and issue-type mix only.
4. Do not quote LoF entry text or any dissertation prose.
