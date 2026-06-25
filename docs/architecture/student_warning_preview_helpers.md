# Student warning preview helpers

Presentation-layer modules that shape **student-facing** warning cards without changing
detector logic, rule IDs, thresholds, or canonical rules JSON.

## Purpose

Recent warning-clarity work (#363–#372) added small helper modules so `report_view.py`,
`report_outputs.py`, and related presentation code can:

- shorten main-card text (location, likely problem, suggested fix);
- strip unsafe or noisy snippets (leader dots, export timestamps, structural column labels);
- deduplicate visibly identical cards;
- build privacy-safe entry/heading previews for highlights and location labels.

Detectors in `src/njit_auditor/rules/` emit raw findings. Helpers prepare what students
see in the web UI and Markdown export.

## Naming pattern

`*_student_preview.py` under `src/njit_auditor/`:

| Module | Focus |
|---|---|
| `toc_list_student_preview.py` | TOC/LoT/LoF entry snippets, gap highlight geometry, P018/P036 short wording, structural-label and export-metadata skips |
| `title_case_student_preview.py` | P020 short cards, duplicate suppression keys |
| `page_number_student_preview.py` | Page-number location phrasing |
| `p011_student_preview.py` | P011 margin/overflow presentation |
| `p012_student_preview.py` | P012 annotation rollup presentation |
| `p026_student_preview.py` | P026 font rollup presentation |
| `high_volume_student_preview.py` | Shared high-volume group notes |

New helpers should follow the same pattern: **presentation only**, unit-tested, no
detector imports from rules back into helpers unless passing through already-computed
metadata.

## What belongs here vs detector code

| Belongs in `*_student_preview.py` | Belongs in `rules/` detectors |
|---|---|
| Short location suffixes and entry previews | Whether a finding is emitted |
| Leader-dot stripping, timestamp/metadata skips for **display or entry parsing recall** when explicitly scoped | Thresholds, clustering, bbox extraction policy |
| Dedup keys for visible cards | Issue types and rule IDs |
| Short `likely problem` / `suggested fix` strings | Raw `message` and `details` from audit |

Narrow false-positive skips that affect **entry extraction** (e.g. export timestamps in
`pdf_toc_alignment.py`) are allowed only when clearly safe and covered by tests; prefer
presentation skips when possible.

## Student-facing safety rules

Helpers and presentation code must **not** expose:

- raw coordinates or bbox tuples in student prose;
- filesystem paths or repo-relative paths;
- raw reviewer annotations or comment text;
- long private document paragraphs;
- raw LaTeX or private dissertation body text.

Use short, collapsed snippets (typically ≤72 characters for TOC/list entries). Technical
metrics (gap points, ratios, counts) belong in **detailed explanations**, not the main
card comment.

## Main-card brevity pattern

For P018, P020, P036, and similar live-review rules:

1. **Location** — page + section + short entry/heading snippet when available.
2. **Likely problem** — one plain-language sentence.
3. **Suggested fix** — one actionable sentence (not repeated in the main card body).
4. **Detailed explanation** — metrics, counts, and triage context (`finding_explanations.py`).

## Highlights vs original-page fallback

- When a drawable bbox exists, the web UI should offer a **highlight** action.
- When only the page is known, use **Open original PDF page** — not a fake highlight.
- P018 affected-entry warnings should highlight the entry bbox when `details.bbox` is
  present after enrichment.

## Deduplication expectations

Visible cards may be deduplicated when they would look identical to students (same rule,
issue type, page, normalized preview, and flagged token). Dedup must not hide legitimately
distinct problems on the same page (different entries, words, or reasons).

P020 duplicate suppression keys include normalized `line_preview` plus flagged/corrected
word — not bbox alone.

## Consolidation note

These modules are intentionally separate for now. A future explicit refactor query may
consolidate shared preview utilities; do not move or merge them during documentation-only
passes.
